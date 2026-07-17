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

        # 第二阶段：生成 LIR 指令
        body = []
        for bb in mir_fn.basic_blocks:
            label_instr = LIRLabel(name=bb.label)
            body.append(label_instr)

            for instr in bb.instructions:
                # Phi 节点不在此处生成指令（在前驱块末尾插入拷贝）
                if isinstance(instr, MIRPhi):
                    continue
                lir_instrs = self._lower_instruction(instr)
                body.extend(lir_instrs)

            # 在终结指令前，为后继块的 Phi 节点插入拷贝指令
            if bb.terminator:
                # 找出当前块跳转到哪些后继块
                succ_blocks = self._get_successor_blocks(bb.terminator)
                # 为每个后继块的 Phi 节点插入拷贝
                for succ_label in succ_blocks:
                    if succ_label in phi_info:
                        for phi_result_name, phi_result_type, sources in phi_info[
                            succ_label
                        ]:
                            # 找到从前驱块（当前块）来的 source
                            src_ssa = None
                            for pred_label, ssa_name in sources:
                                if pred_label == bb.label:
                                    src_ssa = ssa_name
                                    break
                            if src_ssa and src_ssa in self.ssa_to_loc:
                                src_loc = self.ssa_to_loc[src_ssa]
                                dst_loc = self.ssa_to_loc[phi_result_name]
                                # 生成 LoadReg + StoreReg 实现拷贝
                                # 用 LIRLoadReg 从 src 加载，然后通过 StoreReg 存入 dst
                                # 实际上我们用 LIRLoadReg 的 dst 就是目标位置
                                # 但更简单的方式是：生成一条 LIRLoadReg，src 是源位置，dst 是目标位置
                                copy_instr = LIRLoadReg()
                                copy_instr.src_locs = [(src_loc, phi_result_type)]
                                copy_instr.dst_loc = (dst_loc, phi_result_type)
                                body.append(copy_instr)

                lir_term = self._lower_terminator(bb.terminator)
                body.append(lir_term)

        lir_fn.body = body
        lir_fn.reg_alloc = dict(self.ssa_to_loc)
        lir_fn.stack_size = self.loc_counter * 8

        return lir_fn

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
        result = []

        if instr.result_name:
            loc = self._new_loc()
            self.ssa_to_loc[instr.result_name] = loc
            self.ssa_types[instr.result_name] = instr.result_type

        if isinstance(instr, MIRConst):
            lir = LIRLoadConst()
            lir.value = instr.value
            lir.const_type = instr.const_type
            if instr.result_name:
                lir.dst_loc = (
                    self.ssa_to_loc.get(instr.result_name, ""),
                    instr.result_type,
                )
            result.append(lir)

        elif isinstance(instr, MIRLoad):
            lir = LIRLoadGlobal()
            lir.global_name = instr.name
            if instr.result_name:
                lir.dst_loc = (
                    self.ssa_to_loc.get(instr.result_name, ""),
                    instr.result_type,
                )
            result.append(lir)

        elif isinstance(instr, MIRStore):
            lir = LIRStoreGlobal()
            lir.global_name = instr.name
            if instr.value:
                lir.src_locs = [
                    (self.ssa_to_loc.get(instr.value, ""), instr.result_type)
                ]
            result.append(lir)

        elif isinstance(instr, MIRBinOp):
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

        elif isinstance(instr, MIRUnaryOp):
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

        elif isinstance(instr, MIRCall):
            lir = LIRCall()
            lir.func_name = instr.callee
            lir.arg_count = len(instr.args)
            if instr.result_name:
                lir.dst_loc = (
                    self.ssa_to_loc.get(instr.result_name, ""),
                    instr.result_type,
                )
            result.append(lir)

        elif isinstance(instr, MIRClosureCreate):
            lir = LIRLoadConst()
            lir.value = "<closure:%s>" % instr.fn_name
            lir.const_type = "closure"
            if instr.result_name:
                lir.dst_loc = (
                    self.ssa_to_loc.get(instr.result_name, ""),
                    instr.result_type,
                )
            result.append(lir)

        elif isinstance(instr, MIRListBuild):
            lir = LIRBuildList()
            lir.count = len(instr.elements)
            if instr.result_name:
                lir.dst_loc = (
                    self.ssa_to_loc.get(instr.result_name, ""),
                    instr.result_type,
                )
            result.append(lir)

        elif isinstance(instr, MIRListAppend):
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

        elif isinstance(instr, MIRTupleBuild):
            lir = LIRBuildTuple()
            lir.count = len(instr.elements)
            if instr.result_name:
                lir.dst_loc = (
                    self.ssa_to_loc.get(instr.result_name, ""),
                    instr.result_type,
                )
            result.append(lir)

        elif isinstance(instr, MIRMapBuild):
            lir = LIRBuildMap()
            lir.entry_count = len(instr.entries)
            if instr.result_name:
                lir.dst_loc = (
                    self.ssa_to_loc.get(instr.result_name, ""),
                    instr.result_type,
                )
            result.append(lir)

        elif isinstance(instr, MIRADTBuild):
            lir = LIRBuildADT()
            lir.field_count = len(instr.fields)
            if instr.result_name:
                lir.dst_loc = (
                    self.ssa_to_loc.get(instr.result_name, ""),
                    instr.result_type,
                )
            result.append(lir)

        elif isinstance(instr, MIRFieldAccess):
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

        elif isinstance(instr, MIRIndexAccess):
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

        return result

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
            lir = LIRJump(target=term.default_target)
            if term.value:
                lir.src_locs = [(self.ssa_to_loc.get(term.value, ""), INT_TYPE)]
            return lir

        if isinstance(term, MIRMatchJump):
            lir = LIRJump(target=term.default_target)
            if term.value:
                val_type = self.ssa_types.get(term.value, UNIT_TYPE)
                lir.src_locs = [(self.ssa_to_loc.get(term.value, ""), val_type)]
            return lir

        if isinstance(term, MIRPanic):
            return LIRPanic(message=term.message)

        return LIRReturn()
