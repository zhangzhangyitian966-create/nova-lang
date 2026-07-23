"""
MIR -> LIR 降级器

将 MIR（Mid-Level IR）降级为 LIR（Low-Level IR）-- 接近机器码的表示。
这是编译管道的第三步，输出用于 Cranelift 和 WasmGC 后端。
"""

from .ir_nodes import (
    BOOL_TYPE,
    INT_TYPE,
    UNIT_TYPE,
    LIRBinOp,
    LIRBranch,
    LIRBuildADT,
    LIRBuildList,
    LIRBuildMap,
    LIRBuildTuple,
    LIRCall,
    LIRData,
    LIRFieldAccess,
    LIRFunction,
    LIRGlobal,
    LIRIndex,
    LIRJump,
    LIRLabel,
    LIRListAppend,
    LIRLoadConst,
    LIRLoadGlobal,
    LIRLoadReg,
    LIRModule,
    LIRPanic,
    LIRReturn,
    LIRStoreGlobal,
    LIRSwitch,
    LIRUnaryOp,
    MIRADTBuild,
    MIRBinOp,
    MIRBranch,
    MIRCall,
    MIRClosureCreate,
    MIRConst,
    MIRFieldAccess,
    MIRIndexAccess,
    MIRJump,
    MIRListAppend,
    MIRListBuild,
    MIRLoad,
    MIRMapBuild,
    MIRMatchJump,
    MIRPanic,
    MIRPhi,
    MIRReturn,
    MIRStore,
    MIRSwitch,
    MIRTupleBuild,
    MIRUnaryOp,
)


class LIRLoweringError(Exception):
    pass


class LIRLowering:
    """MIR -> LIR 降级器"""

    def __init__(self):
        self.ssa_to_loc = {}
        self.ssa_types = {}  # SSA 名 -> 类型映射
        self.loc_counter = 0
        self.functions = {}
        self._instr_dispatch = self._build_instr_dispatch_table()

    def _build_instr_dispatch_table(self):
        """
        构建 MIR 指令 -> LIR 降级方法的调度表。

        采用调度表模式替代 if-isinstance 链，
        降低圈复杂度，提升可扩展性。
        """
        return {
            MIRConst: self._lower_const,
            MIRLoad: self._lower_load_global,
            MIRStore: self._lower_store_global,
            MIRBinOp: self._lower_binop,
            MIRUnaryOp: self._lower_unaryop,
            MIRCall: self._lower_call,
            MIRClosureCreate: self._lower_closure_create,
            MIRListBuild: self._lower_list_build,
            MIRListAppend: self._lower_list_append,
            MIRTupleBuild: self._lower_tuple_build,
            MIRMapBuild: self._lower_map_build,
            MIRADTBuild: self._lower_adt_build,
            MIRFieldAccess: self._lower_field_access,
            MIRIndexAccess: self._lower_index_access,
        }

    def lower(self, mir_module):
        lir_module = LIRModule(name=mir_module.name)

        for name, mir_global in mir_module.globals.items():
            lir_global = LIRGlobal(name, mir_global.ir_type)
            if mir_global.init_value:
                init_str = (
                    str(mir_global.init_value.value)
                    if mir_global.init_value.value
                    else ""
                )
                lir_global.data = LIRData("data_%s" % name, init_str.encode("utf-8"))
            lir_module.globals.append(lir_global)

        for name, mir_fn in mir_module.functions.items():
            lir_module.functions[name] = self._lower_function(mir_fn)

        return lir_module

    def _new_loc(self):
        loc = "r%d" % self.loc_counter
        self.loc_counter += 1
        return loc

    def _lower_function(self, mir_fn):
        self.ssa_to_loc = {}
        self.ssa_types = {}
        self.loc_counter = 0

        lir_fn = LIRFunction(
            name=mir_fn.name,
            params=[],
            return_type=mir_fn.return_type,
        )

        for param_name, param_type, ssa_name in mir_fn.params:
            loc = self._new_loc()
            self.ssa_to_loc[ssa_name] = loc
            self.ssa_types[ssa_name] = param_type
            lir_fn.params.append((loc, param_type))

        # 第一阶段：为所有 Phi 节点分配目标位置
        # （必须在 lowering 前完成，因为 Phi 的结果可能被后续指令引用）
        phi_info = {}  # bb_label -> [(phi_result_name, phi_result_type, sources)]
        for bb in mir_fn.basic_blocks:
            phi_list = []
            for instr in bb.instructions:
                if isinstance(instr, MIRPhi) and instr.result_name:
                    loc = self._new_loc()
                    self.ssa_to_loc[instr.result_name] = loc
                    self.ssa_types[instr.result_name] = instr.result_type
                    phi_list.append(
                        (instr.result_name, instr.result_type, instr.sources)
                    )
            if phi_list:
                phi_info[bb.label] = phi_list

        # 第二阶段 + 第三阶段：生成 LIR 指令，处理 Phi 节点拷贝
        #
        # Phi 节点降级策略：critical edge splitting
        # - 无条件跳转（单后继）：Phi 拷贝放在前驱块末尾（跳转前）
        # - 条件分支/switch（多后继）：插入边缘块（edge block）
        #   Phi 拷贝放在对应的边缘块中，确保每条路径只执行自己的拷贝
        #
        # 背景：原来的实现把所有后继的 Phi 拷贝都放在前驱块末尾（终结指令前），
        # 这在条件分支场景下是错误的——两条互斥路径的 Phi 拷贝都会被执行。
        final_body = []
        edge_block_counter = 0

        for bb in mir_fn.basic_blocks:
            # 添加标签
            final_body.append(LIRLabel(name=bb.label))

            # 添加非终结指令
            for instr in bb.instructions:
                if isinstance(instr, MIRPhi):
                    continue
                lir_instrs = self._lower_instruction(instr)
                final_body.extend(lir_instrs)

            # 处理终结指令和 Phi 拷贝
            if bb.terminator:
                succ_blocks = self._get_successor_blocks(bb.terminator)

                # 检查是否需要边缘块：
                # 如果有多个后继（条件分支）且任一后继有 Phi 节点，则需要边缘块
                needs_edge_blocks = len(succ_blocks) > 1 and any(
                    s in phi_info for s in succ_blocks
                )

                if needs_edge_blocks:
                    # 条件分支 + 后继有 Phi：创建边缘块
                    # 将原终结指令改为跳转到边缘块
                    # 边缘块中执行 Phi 拷贝，然后跳转到真正的目标

                    if isinstance(bb.terminator, MIRBranch):
                        true_target = bb.terminator.true_target
                        false_target = bb.terminator.false_target

                        # 创建 true 分支边缘块
                        true_edge_label = f"_edge_true_{edge_block_counter}"
                        edge_block_counter += 1
                        # 创建 false 分支边缘块
                        false_edge_label = f"_edge_false_{edge_block_counter}"
                        edge_block_counter += 1

                        # 修改条件分支：跳转到边缘块
                        lir_branch = LIRBranch()
                        lir_branch.true_target = true_edge_label
                        lir_branch.false_target = false_edge_label
                        if bb.terminator.condition:
                            lir_branch.src_locs = [
                                (
                                    self.ssa_to_loc.get(bb.terminator.condition, ""),
                                    BOOL_TYPE,
                                )
                            ]
                        final_body.append(lir_branch)

                        # 生成 true 边缘块（Phi 拷贝 + 跳转到真正目标）
                        final_body.append(LIRLabel(name=true_edge_label))
                        self._insert_phi_copies(
                            final_body, bb.label, true_target, phi_info
                        )
                        final_body.append(LIRJump(target=true_target))

                        # 生成 false 边缘块（Phi 拷贝 + 跳转到真正目标）
                        final_body.append(LIRLabel(name=false_edge_label))
                        self._insert_phi_copies(
                            final_body, bb.label, false_target, phi_info
                        )
                        final_body.append(LIRJump(target=false_target))

                    elif isinstance(bb.terminator, (MIRSwitch, MIRMatchJump)):
                        # switch 也有多后继，处理方式类似
                        # 对于 switch，每个 case 和 default 都可能需要边缘块
                        targets = self._get_successor_blocks(bb.terminator)
                        edge_labels = {}
                        for tgt in targets:
                            edge_label = f"_edge_switch_{edge_block_counter}"
                            edge_block_counter += 1
                            edge_labels[tgt] = edge_label

                        # 生成修改目标后的终结指令
                        lir_term = self._lower_terminator_with_targets(
                            bb.terminator, edge_labels
                        )
                        final_body.append(lir_term)

                        # 生成每个边缘块
                        for tgt in targets:
                            final_body.append(LIRLabel(name=edge_labels[tgt]))
                            self._insert_phi_copies(
                                final_body, bb.label, tgt, phi_info
                            )
                            final_body.append(LIRJump(target=tgt))
                    else:
                        # 其他多后继情况，降级处理
                        lir_term = self._lower_terminator(bb.terminator)
                        final_body.append(lir_term)
                else:
                    # 单后继或后继无 Phi：直接在前驱块末尾插入 Phi 拷贝
                    for succ_label in succ_blocks:
                        if succ_label in phi_info:
                            self._insert_phi_copies(
                                final_body, bb.label, succ_label, phi_info
                            )
                    # 添加终结指令
                    lir_term = self._lower_terminator(bb.terminator)
                    final_body.append(lir_term)
            # 无终结指令的块（理论上不应该有）

        lir_fn.body = final_body
        lir_fn.reg_alloc = dict(self.ssa_to_loc)
        lir_fn.stack_size = self.loc_counter * 8

        return lir_fn

    def _insert_phi_copies(self, body, pred_label, succ_label, phi_info):
        """在 body 末尾插入从前驱 pred_label 到后继 succ_label 的所有 Phi 拷贝指令。"""
        if succ_label not in phi_info:
            return
        for phi_result_name, phi_result_type, sources in phi_info[succ_label]:
            # 找到从前驱块来的 source
            src_ssa = None
            for src_pred_label, ssa_name in sources:
                if src_pred_label == pred_label:
                    src_ssa = ssa_name
                    break
            if src_ssa and src_ssa in self.ssa_to_loc:
                src_loc = self.ssa_to_loc[src_ssa]
                dst_loc = self.ssa_to_loc[phi_result_name]
                # 生成 LIRLoadReg 实现寄存器到寄存器的拷贝
                copy_instr = LIRLoadReg()
                copy_instr.src_locs = [(src_loc, phi_result_type)]
                copy_instr.dst_loc = (dst_loc, phi_result_type)
                body.append(copy_instr)

    def _lower_terminator_with_targets(self, term, target_map):
        """降低终结指令，但将目标标签替换为 target_map 中的映射（用于边缘块）。"""
        if isinstance(term, MIRSwitch):
            lir = LIRSwitch()
            lir.default_target = target_map.get(term.default_target, term.default_target)
            if term.value:
                lir.src_locs = [(self.ssa_to_loc.get(term.value, ""), INT_TYPE)]
            lir.cases = [(val, target_map.get(tgt, tgt)) for val, tgt in term.cases]
            return lir
        elif isinstance(term, MIRMatchJump):
            lir = LIRSwitch()
            lir.default_target = target_map.get(term.default_target, term.default_target)
            if term.value:
                val_type = self.ssa_types.get(term.value, UNIT_TYPE)
                lir.src_locs = [(self.ssa_to_loc.get(term.value, ""), val_type)]
            lir.cases = [
                (variant_name, target_map.get(tgt, tgt))
                for variant_name, _fields, tgt in term.variant_tests
            ]
            return lir
        return self._lower_terminator(term)

    def _get_successor_blocks(self, terminator):
        """获取终结指令跳转到的后继块标签列表"""
        if isinstance(terminator, MIRJump):
            return [terminator.target]
        elif isinstance(terminator, MIRBranch):
            return [terminator.true_target, terminator.false_target]
        elif isinstance(terminator, MIRSwitch):
            targets = [terminator.default_target] if terminator.default_target else []
            for _, target in terminator.cases:
                targets.append(target)
            return targets
        elif isinstance(terminator, MIRMatchJump):
            return [terminator.default_target] if terminator.default_target else []
        elif isinstance(terminator, MIRReturn):
            return []
        elif isinstance(terminator, MIRPanic):
            return []
        return []

    def _lower_instruction(self, instr):
        """
        降级一条 MIR 指令为 LIR 指令（调度表模式）。

        先分配结果位置，再通过调度表调用对应的降级方法。
        """
        result = []

        if instr.result_name:
            loc = self._new_loc()
            self.ssa_to_loc[instr.result_name] = loc
            self.ssa_types[instr.result_name] = instr.result_type

        # 通过调度表查找对应的降级方法
        handler = self._instr_dispatch.get(type(instr))
        if handler is not None:
            handler(instr, result)

        return result

    # --------------------------------------------------------
    # 指令降级方法（按类别分组）
    # --------------------------------------------------------

    # ---- 常量与加载 ----

    def _lower_const(self, instr, result):
        """降级常量加载"""
        lir = LIRLoadConst()
        lir.value = instr.value
        lir.const_type = instr.const_type
        if instr.result_name:
            lir.dst_loc = (
                self.ssa_to_loc.get(instr.result_name, ""),
                instr.result_type,
            )
        result.append(lir)

    def _lower_load_global(self, instr, result):
        """降级全局变量加载"""
        lir = LIRLoadGlobal()
        lir.global_name = instr.name
        if instr.result_name:
            lir.dst_loc = (
                self.ssa_to_loc.get(instr.result_name, ""),
                instr.result_type,
            )
        result.append(lir)

    def _lower_store_global(self, instr, result):
        """降级全局变量存储"""
        lir = LIRStoreGlobal()
        lir.global_name = instr.name
        if instr.value:
            lir.src_locs = [
                (self.ssa_to_loc.get(instr.value, ""), instr.result_type)
            ]
        result.append(lir)

    # ---- 运算 ----

    def _lower_binop(self, instr, result):
        """降级二元运算"""
        lir = LIRBinOp()
        lir.op = instr.op
        if instr.left:
            lir.src_locs = [
                (self.ssa_to_loc.get(instr.left, ""), instr.result_type)
            ]
        if instr.right:
            lir.src_locs.append(
                (self.ssa_to_loc.get(instr.right, ""), instr.result_type)
            )
        if instr.result_name:
            lir.dst_loc = (
                self.ssa_to_loc.get(instr.result_name, ""),
                instr.result_type,
            )
        result.append(lir)

    def _lower_unaryop(self, instr, result):
        """降级一元运算"""
        lir = LIRUnaryOp()
        lir.op = instr.op
        if instr.operand:
            lir.src_locs = [
                (self.ssa_to_loc.get(instr.operand, ""), instr.result_type)
            ]
        if instr.result_name:
            lir.dst_loc = (
                self.ssa_to_loc.get(instr.result_name, ""),
                instr.result_type,
            )
        result.append(lir)

    # ---- 函数调用 ----

    def _lower_call(self, instr, result):
        """降级函数调用"""
        lir = LIRCall()
        lir.callee = instr.callee  # 使用统一命名
        # 传递参数位置信息（从 ssa_to_loc 映射）
        lir.arg_locs = [
            (self.ssa_to_loc.get(arg_ssa, ""), self.ssa_types.get(arg_ssa, UNIT_TYPE))
            for arg_ssa in instr.args
        ]
        lir.arg_count = len(instr.args)
        if instr.result_name:
            lir.dst_loc = (
                self.ssa_to_loc.get(instr.result_name, ""),
                instr.result_type,
            )
        result.append(lir)

    def _lower_closure_create(self, instr, result):
        """降级闭包创建（作为常量处理）"""
        lir = LIRLoadConst()
        lir.value = "<closure:%s>" % instr.fn_name
        lir.const_type = "closure"
        if instr.result_name:
            lir.dst_loc = (
                self.ssa_to_loc.get(instr.result_name, ""),
                instr.result_type,
            )
        result.append(lir)

    # ---- 数据结构构建 ----

    def _lower_list_build(self, instr, result):
        """降级列表构建

        将所有元素通过 src_locs 传递，后端负责循环填充。
        每个元素的类型从 ssa_types 中查找，找不到则用 INT_TYPE 占位。
        """
        lir = LIRBuildList()
        lir.count = len(instr.elements)
        # 传递所有元素的位置和类型
        for elem_ssa in instr.elements:
            elem_loc = self.ssa_to_loc.get(elem_ssa, "")
            elem_type = self.ssa_types.get(elem_ssa, INT_TYPE)
            lir.src_locs.append((elem_loc, elem_type))
        if instr.result_name:
            lir.dst_loc = (
                self.ssa_to_loc.get(instr.result_name, ""),
                instr.result_type,
            )
        result.append(lir)

    def _lower_list_append(self, instr, result):
        """降级列表追加元素"""
        lir = LIRListAppend()
        if instr.list_ssa:
            lir.src_locs = [
                (self.ssa_to_loc.get(instr.list_ssa, ""), instr.result_type)
            ]
        if instr.element_ssa:
            lir.src_locs.append(
                (self.ssa_to_loc.get(instr.element_ssa, ""), instr.result_type)
            )
        if instr.result_name:
            lir.dst_loc = (
                self.ssa_to_loc.get(instr.result_name, ""),
                instr.result_type,
            )
        result.append(lir)

    def _lower_tuple_build(self, instr, result):
        """降级元组构建

        将所有元素通过 src_locs 传递，后端负责循环填充。
        """
        lir = LIRBuildTuple()
        lir.count = len(instr.elements)
        # 传递所有元素的位置和类型
        for elem_ssa in instr.elements:
            elem_loc = self.ssa_to_loc.get(elem_ssa, "")
            elem_type = self.ssa_types.get(elem_ssa, INT_TYPE)
            lir.src_locs.append((elem_loc, elem_type))
        if instr.result_name:
            lir.dst_loc = (
                self.ssa_to_loc.get(instr.result_name, ""),
                instr.result_type,
            )
        result.append(lir)

    def _lower_map_build(self, instr, result):
        """降级 Map 构建

        将键值对通过 src_locs 传递（key, value, key, value... 交替排列），
        后端负责循环插入。
        """
        lir = LIRBuildMap()
        lir.entry_count = len(instr.entries)
        # 交替传递 key 和 value
        for key_ssa, val_ssa in instr.entries:
            key_loc = self.ssa_to_loc.get(key_ssa, "")
            key_type = self.ssa_types.get(key_ssa, INT_TYPE)
            lir.src_locs.append((key_loc, key_type))
            val_loc = self.ssa_to_loc.get(val_ssa, "")
            val_type = self.ssa_types.get(val_ssa, INT_TYPE)
            lir.src_locs.append((val_loc, val_type))
        if instr.result_name:
            lir.dst_loc = (
                self.ssa_to_loc.get(instr.result_name, ""),
                instr.result_type,
            )
        result.append(lir)

    def _lower_adt_build(self, instr, result):
        """降级 ADT 构建

        将所有字段通过 src_locs 传递，后端负责循环填充。
        type_name 和 variant_name 作为附加信息通过 type_tag 暂存
        （后端可通过类型表查询）。
        """
        lir = LIRBuildADT()
        lir.field_count = len(instr.fields)
        lir.type_name = instr.type_name
        lir.variant_name = instr.variant_name
        # 传递所有字段的位置和类型
        for field_ssa in instr.fields:
            field_loc = self.ssa_to_loc.get(field_ssa, "")
            field_type = self.ssa_types.get(field_ssa, INT_TYPE)
            lir.src_locs.append((field_loc, field_type))
        if instr.result_name:
            lir.dst_loc = (
                self.ssa_to_loc.get(instr.result_name, ""),
                instr.result_type,
            )
        result.append(lir)

    # ---- 访问操作 ----

    def _lower_field_access(self, instr, result):
        """降级字段访问"""
        lir = LIRFieldAccess()
        lir.offset = instr.field_index
        if instr.object:
            lir.src_locs = [
                (self.ssa_to_loc.get(instr.object, ""), instr.result_type)
            ]
        if instr.result_name:
            lir.dst_loc = (
                self.ssa_to_loc.get(instr.result_name, ""),
                instr.result_type,
            )
        result.append(lir)

    def _lower_index_access(self, instr, result):
        """降级索引访问"""
        lir = LIRIndex()
        if instr.object:
            lir.src_locs = [
                (self.ssa_to_loc.get(instr.object, ""), instr.result_type)
            ]
        if instr.index:
            lir.src_locs.append(
                (self.ssa_to_loc.get(instr.index, ""), instr.result_type)
            )
        if instr.result_name:
            lir.dst_loc = (
                self.ssa_to_loc.get(instr.result_name, ""),
                instr.result_type,
            )
        result.append(lir)

    def _lower_terminator(self, term):
        if isinstance(term, MIRJump):
            return LIRJump(target=term.target)

        if isinstance(term, MIRBranch):
            lir = LIRBranch()
            lir.true_target = term.true_target
            lir.false_target = term.false_target
            if term.condition:
                lir.src_locs = [(self.ssa_to_loc.get(term.condition, ""), BOOL_TYPE)]
            return lir

        if isinstance(term, MIRReturn):
            lir = LIRReturn()
            if term.value and term.value in self.ssa_to_loc:
                ret_type = self.ssa_types.get(term.value, UNIT_TYPE)
                lir.src_locs = [(self.ssa_to_loc.get(term.value, ""), ret_type)]
            return lir

        if isinstance(term, MIRSwitch):
            # 正确降级 MIRSwitch 为 LIRSwitch，保留所有 case 信息
            lir = LIRSwitch()
            lir.default_target = term.default_target
            if term.value:
                lir.src_locs = [(self.ssa_to_loc.get(term.value, ""), INT_TYPE)]
            # 复制 cases 列表: [(value, target_block), ...]
            lir.cases = list(term.cases)
            return lir

        if isinstance(term, MIRMatchJump):
            # 降级 MIRMatchJump 为 LIRSwitch（基于 variant tag 的 switch）
            # variant_tests: [(variant_name, fields, target_block), ...]
            # 转换为 case 列表: [(variant_name, target_block), ...]
            lir = LIRSwitch()
            lir.default_target = term.default_target
            if term.value:
                val_type = self.ssa_types.get(term.value, UNIT_TYPE)
                lir.src_locs = [(self.ssa_to_loc.get(term.value, ""), val_type)]
            # 将 variant_tests 转换为 cases：variant_name 作为 case 值
            lir.cases = [
                (variant_name, target)
                for variant_name, _fields, target in term.variant_tests
            ]
            return lir

        if isinstance(term, MIRPanic):
            return LIRPanic(message=term.message)

        return LIRReturn()
