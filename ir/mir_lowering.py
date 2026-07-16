"""
HIR -> MIR 降级器

将 HIR（High-Level IR）转换为 MIR（Mid-Level IR）—— SSA + CFG 形式。
这是编译管道的第二步。
"""

from ir_nodes import (
    UNIT_TYPE,
    HIRADTConstructor,
    HIRAssignExpr,
    HIRBinaryOp,
    HIRBlockExpr,
    HIRBoolLiteral,
    HIRBreakExpr,
    HIRCallExpr,
    HIRCharLiteral,
    HIRContinueExpr,
    HIRFieldExpr,
    HIRFloatLiteral,
    HIRFnDecl,
    HIRForExpr,
    HIRIdentifier,
    HIRIfExpr,
    HIRIndexExpr,
    HIRIntLiteral,
    HIRLambda,
    HIRLetDecl,
    HIRListComprehension,
    HIRListExpr,
    HIRMapExpr,
    HIRMatchExpr,
    HIRPipeExpr,
    HIRStringLiteral,
    HIRTupleExpr,
    HIRUnaryOp,
    HIRUnitLiteral,
    HIRUnwrapExpr,
    HIRWhileExpr,
    MIRADTBuild,
    MIRBasicBlock,
    MIRBinOp,
    MIRBranch,
    MIRCall,
    MIRClosureCreate,
    MIRConst,
    MIRFieldAccess,
    MIRFunction,
    MIRGlobal,
    MIRIndexAccess,
    MIRJump,
    MIRListAppend,
    MIRListBuild,
    MIRMapBuild,
    MIRModule,
    MIRPanic,
    MIRPhi,
    MIRReturn,
    MIRStore,
    MIRTupleBuild,
    MIRUnaryOp,
)


class MIRLoweringError(Exception):
    pass


class MIRLowering:
    """HIR -> MIR 降级器

    将 HIR Module 降级为 MIR Module。
    主要工作：
    1. 将每个函数体转换为基本块（CFG）
    2. 将变量赋值转换为 SSA 形式
    3. 将控制流（if/match/for/while）转换为跳转指令
    """

    def __init__(self):
        self.current_function = None
        self.current_block = None
        self.ssa_counter = 0
        self.block_counter = 0
        self.env = {}
        self.functions = {}
        self.all_blocks = []
        self.loop_stack = []  # 循环栈: [(header_label, exit_label), ...]

    def lower(self, hir_module):
        mir_module = MIRModule(name=hir_module.name)
        mir_module.type_defs = hir_module.type_defs

        for decl in hir_module.declarations:
            if isinstance(decl, HIRLetDecl):
                mir_module.globals[decl.name] = MIRGlobal(
                    decl.name, decl.ir_type, is_mutable=decl.is_mutable
                )
            elif isinstance(decl, HIRFnDecl):
                mir_module.functions[decl.fn_def.name] = self._lower_function(
                    decl.fn_def
                )

        return mir_module

    def _new_ssa(self):
        name = "v%d" % self.ssa_counter
        self.ssa_counter += 1
        return name

    def _new_block(self):
        name = "bb%d" % self.block_counter
        self.block_counter += 1
        return name

    def _emit(self, instr):
        ssa = self._new_ssa()
        instr.result_name = ssa
        self.current_block.instructions.append(instr)
        return ssa

    def _replace_ssa_in_instr(self, instr, old_ssa, new_ssa):
        """
        替换一条指令中的 SSA 引用。
        支持所有常见的指令字段。
        """
        # 跳过 Phi 自身的 result_name
        if hasattr(instr, "result_name") and instr.result_name == old_ssa:
            pass  # 不替换定义本身

        # 二元运算
        if hasattr(instr, "left") and instr.left == old_ssa:
            instr.left = new_ssa
        if hasattr(instr, "right") and instr.right == old_ssa:
            instr.right = new_ssa

        # 一元运算
        if hasattr(instr, "operand") and instr.operand == old_ssa:
            instr.operand = new_ssa

        # 函数调用
        if hasattr(instr, "callee") and instr.callee == old_ssa:
            instr.callee = new_ssa
        if hasattr(instr, "args"):
            instr.args = [new_ssa if a == old_ssa else a for a in instr.args]

        # 字段/索引访问
        if hasattr(instr, "object") and instr.object == old_ssa:
            instr.object = new_ssa
        if hasattr(instr, "index") and instr.index == old_ssa:
            instr.index = new_ssa
        if hasattr(instr, "value") and instr.value == old_ssa:
            instr.value = new_ssa

        # 列表/元组/Map 构建
        if hasattr(instr, "elements"):
            instr.elements = [new_ssa if e == old_ssa else e for e in instr.elements]
        if hasattr(instr, "entries"):
            instr.entries = [
                (new_ssa if k == old_ssa else k, new_ssa if v == old_ssa else v)
                for k, v in instr.entries
            ]
        if hasattr(instr, "fields"):
            instr.fields = {
                k: new_ssa if v == old_ssa else v for k, v in instr.fields.items()
            }

        # 列表操作
        if hasattr(instr, "list_ssa") and instr.list_ssa == old_ssa:
            instr.list_ssa = new_ssa
        if hasattr(instr, "element_ssa") and instr.element_ssa == old_ssa:
            instr.element_ssa = new_ssa

        # 全局变量加载/存储
        if hasattr(instr, "src") and instr.src == old_ssa:
            instr.src = new_ssa
        if hasattr(instr, "dst") and instr.dst == old_ssa:
            instr.dst = new_ssa

        # Phi 节点的 sources
        if hasattr(instr, "sources"):
            instr.sources = [
                (label, new_ssa if val == old_ssa else val)
                for label, val in instr.sources
            ]

    def _replace_ssa_in_terminator(self, terminator, old_ssa, new_ssa):
        """
        替换终结指令中的 SSA 引用。
        """
        if terminator is None:
            return

        # 分支条件
        if hasattr(terminator, "cond") and terminator.cond == old_ssa:
            terminator.cond = new_ssa

        # 跳转值（如 return）
        if hasattr(terminator, "value") and terminator.value == old_ssa:
            terminator.value = new_ssa

        # 函数调用参数
        if hasattr(terminator, "args"):
            terminator.args = [new_ssa if a == old_ssa else a for a in terminator.args]

    def _replace_ssa_in_block(self, block, old_ssa, new_ssa, skip_phi=False):
        """
        替换一个基本块中所有的 SSA 引用。
        skip_phi=True 时不替换 Phi 节点（用于替换 Phi 之前的引用）。
        """
        for instr in block.instructions:
            if skip_phi and hasattr(instr, "sources"):
                continue
            self._replace_ssa_in_instr(instr, old_ssa, new_ssa)
        self._replace_ssa_in_terminator(block.terminator, old_ssa, new_ssa)

    def _lower_function(self, hir_fn):
        self.ssa_counter = 0
        self.block_counter = 0
        self.env = {}
        self.all_blocks = []

        mir_fn = MIRFunction(hir_fn.name, [], hir_fn.return_type)

        entry = MIRBasicBlock("bb0")
        self.current_block = entry
        self.current_function = mir_fn

        param_list = []
        for i, (name, ty) in enumerate(hir_fn.params):
            ssa_name = self._new_ssa()
            param_list.append((name, ty, ssa_name))
            self.env[name] = ssa_name

        mir_fn.params = param_list

        result_ssa = self._lower_expr(hir_fn.body, entry)

        if entry.terminator is None:
            entry.terminator = MIRReturn(result_ssa)

        mir_fn.basic_blocks = [entry] + self.all_blocks
        mir_fn.entry_block = "bb0"

        return mir_fn

    def _lower_expr(self, hir_expr, block):
        if hir_expr is None:
            return None

        self.current_block = block

        if isinstance(hir_expr, HIRIntLiteral):
            instr = MIRConst(hir_expr.ir_type)
            instr.value = hir_expr.value
            instr.const_type = "int"
            return self._emit(instr)

        if isinstance(hir_expr, HIRFloatLiteral):
            instr = MIRConst(hir_expr.ir_type)
            instr.value = hir_expr.value
            instr.const_type = "float"
            return self._emit(instr)

        if isinstance(hir_expr, HIRStringLiteral):
            instr = MIRConst(hir_expr.ir_type)
            instr.value = hir_expr.value
            instr.const_type = "string"
            return self._emit(instr)

        if isinstance(hir_expr, HIRBoolLiteral):
            instr = MIRConst(hir_expr.ir_type)
            instr.value = hir_expr.value
            instr.const_type = "bool"
            return self._emit(instr)

        if isinstance(hir_expr, HIRCharLiteral):
            instr = MIRConst(hir_expr.ir_type)
            instr.value = hir_expr.value
            instr.const_type = "char"
            return self._emit(instr)

        if isinstance(hir_expr, HIRUnitLiteral):
            instr = MIRConst(UNIT_TYPE)
            instr.value = None
            instr.const_type = "unit"
            return self._emit(instr)

        if isinstance(hir_expr, HIRIdentifier):
            if hir_expr.name in self.env:
                return self.env[hir_expr.name]
            return None

        if isinstance(hir_expr, HIRBinaryOp):
            left_ssa = self._lower_expr(hir_expr.left, block)
            right_ssa = self._lower_expr(hir_expr.right, block)
            instr = MIRBinOp(hir_expr.ir_type)
            instr.op = hir_expr.op
            instr.left = left_ssa or ""
            instr.right = right_ssa or ""
            return self._emit(instr)

        if isinstance(hir_expr, HIRUnaryOp):
            operand_ssa = self._lower_expr(hir_expr.operand, block)
            instr = MIRUnaryOp(hir_expr.ir_type)
            instr.op = hir_expr.op
            instr.operand = operand_ssa or ""
            return self._emit(instr)

        if isinstance(hir_expr, HIRCallExpr):
            arg_ssas = []
            for arg in hir_expr.arguments:
                arg_ssa = self._lower_expr(arg, block)
                arg_ssas.append(arg_ssa or "")
            instr = MIRCall(hir_expr.ir_type)
            if isinstance(hir_expr.function, HIRIdentifier):
                instr.callee = hir_expr.function.name
            else:
                func_ssa = self._lower_expr(hir_expr.function, block)
                instr.callee = func_ssa or ""
            instr.args = arg_ssas
            return self._emit(instr)

        if isinstance(hir_expr, HIRIfExpr):
            return self._lower_if_expr(hir_expr, block)

        if isinstance(hir_expr, HIRMatchExpr):
            return self._lower_match_expr(hir_expr, block)

        if isinstance(hir_expr, HIRBlockExpr):
            result = None
            for expr in hir_expr.exprs:
                result = self._lower_expr(expr, block)
            return result

        if isinstance(hir_expr, HIRListExpr):
            elem_ssas = []
            for elem in hir_expr.elements:
                elem_ssas.append(self._lower_expr(elem, block) or "")
            instr = MIRListBuild(hir_expr.ir_type)
            instr.elements = elem_ssas
            return self._emit(instr)

        if isinstance(hir_expr, HIRTupleExpr):
            elem_ssas = []
            for elem in hir_expr.elements:
                elem_ssas.append(self._lower_expr(elem, block) or "")
            instr = MIRTupleBuild(hir_expr.ir_type)
            instr.elements = elem_ssas
            return self._emit(instr)

        if isinstance(hir_expr, HIRMapExpr):
            entry_ssas = []
            for key_expr, val_expr in hir_expr.entries:
                key_ssa = self._lower_expr(key_expr, block)
                val_ssa = self._lower_expr(val_expr, block)
                entry_ssas.append((key_ssa or "", val_ssa or ""))
            instr = MIRMapBuild(hir_expr.ir_type)
            instr.entries = entry_ssas
            return self._emit(instr)

        if isinstance(hir_expr, HIRFieldExpr):
            obj_ssa = self._lower_expr(hir_expr.object, block)
            instr = MIRFieldAccess(hir_expr.ir_type)
            instr.object = obj_ssa or ""
            instr.field_name = hir_expr.field_name
            return self._emit(instr)

        if isinstance(hir_expr, HIRIndexExpr):
            obj_ssa = self._lower_expr(hir_expr.object, block)
            idx_ssa = self._lower_expr(hir_expr.index, block)
            instr = MIRIndexAccess(hir_expr.ir_type)
            instr.object = obj_ssa or ""
            instr.index = idx_ssa or ""
            return self._emit(instr)

        if isinstance(hir_expr, HIRLambda):
            instr = MIRClosureCreate(hir_expr.ir_type)
            instr.fn_name = "<lambda_%d>" % self.ssa_counter
            return self._emit(instr)

        if isinstance(hir_expr, HIRPipeExpr):
            return self._lower_pipe_expr(hir_expr, block)

        if isinstance(hir_expr, HIRForExpr):
            return self._lower_for_expr(hir_expr, block)

        if isinstance(hir_expr, HIRWhileExpr):
            return self._lower_while_expr(hir_expr, block)

        if isinstance(hir_expr, HIRBreakExpr):
            if self.loop_stack:
                _, exit_label = self.loop_stack[-1]
                block.terminator = MIRJump(exit_label)
            else:
                # 不在循环内的 break → 降级为 panic
                block.terminator = MIRPanic("break outside loop")
            return None

        if isinstance(hir_expr, HIRContinueExpr):
            if self.loop_stack:
                header_label, _ = self.loop_stack[-1]
                block.terminator = MIRJump(header_label)
            else:
                # 不在循环内的 continue → 降级为 panic
                block.terminator = MIRPanic("continue outside loop")
            return None

        if isinstance(hir_expr, HIRAssignExpr):
            val_ssa = self._lower_expr(hir_expr.value, block)
            if isinstance(hir_expr.target, HIRIdentifier):
                # SSA 语义：赋值产生变量的新版本，用 MIRStore 的 result_name 标识
                # store 指令的结果就是存储后的值，类型与值的类型一致
                instr = MIRStore(hir_expr.value.ir_type)
                instr.name = hir_expr.target.name
                instr.value = val_ssa or ""
                store_ssa = self._emit(instr)
                # 将变量绑定到新版本（store 的结果 SSA 名）
                self.env[hir_expr.target.name] = store_ssa
                return store_ssa
            return val_ssa

        if isinstance(hir_expr, HIRListComprehension):
            return self._lower_list_comprehension(hir_expr, block)

        if isinstance(hir_expr, HIRADTConstructor):
            field_ssas = [self._lower_expr(f, block) or "" for f in hir_expr.fields]
            instr = MIRADTBuild(hir_expr.ir_type)
            instr.type_name = hir_expr.type_name
            instr.variant_name = hir_expr.variant_name
            instr.fields = field_ssas
            return self._emit(instr)

        if isinstance(hir_expr, HIRUnwrapExpr):
            operand_ssa = self._lower_expr(hir_expr.operand, block)
            instr = MIRFieldAccess(hir_expr.ir_type)
            instr.object = operand_ssa or ""
            instr.field_name = "value"
            instr.field_index = 0
            return self._emit(instr)

        return None

    def _lower_if_expr(self, hir_expr, block):
        """降级 if 表达式。

        SSA 语义：
        - true/false 分支在独立的 env 上下文中运行（分支隔离）
        - 两个分支都修改的变量，在 merge 块插入 Phi 节点
        - if 表达式的结果值也通过 Phi 合并
        """
        cond_ssa = self._lower_expr(hir_expr.condition, block)

        true_block = MIRBasicBlock(self._new_block())
        false_block = MIRBasicBlock(self._new_block())
        merge_block = MIRBasicBlock(self._new_block())

        block.terminator = MIRBranch(
            cond_ssa or "", true_block.label, false_block.label
        )

        # 保存进入分支前的 env 状态
        pre_env = dict(self.env)

        # --- true 分支 ---
        old_block = self.current_block
        self.current_block = true_block
        true_result = self._lower_expr(hir_expr.consequence, true_block)
        if true_block.terminator is None:
            true_block.terminator = MIRJump(merge_block.label)
        # 收集 true 分支修改的变量
        true_modified = {}
        for name, ssa in self.env.items():
            if name not in pre_env or pre_env[name] != ssa:
                true_modified[name] = ssa
        # 恢复 env 和 current_block
        self.env = dict(pre_env)
        self.current_block = old_block

        # --- false 分支 ---
        self.current_block = false_block
        false_result = None
        if hir_expr.alternative:
            false_result = self._lower_expr(hir_expr.alternative, false_block)
        if false_block.terminator is None:
            false_block.terminator = MIRJump(merge_block.label)
        # 收集 false 分支修改的变量
        false_modified = {}
        for name, ssa in self.env.items():
            if name not in pre_env or pre_env[name] != ssa:
                false_modified[name] = ssa
        # 恢复 env
        self.env = dict(pre_env)
        self.current_block = old_block

        # --- merge 块：为被修改的变量插入 Phi ---
        self.current_block = merge_block

        # 找出所有在任一分支中被修改的变量
        all_modified_names = set(true_modified.keys()) | set(false_modified.keys())

        for name in all_modified_names:
            phi_sources = []

            # true 分支：如果修改了就用修改后的值，否则用进入分支前的值
            if name in true_modified:
                phi_sources.append((true_block.label, true_modified[name]))
            elif name in pre_env:
                phi_sources.append((true_block.label, pre_env[name]))

            # false 分支：同理
            if name in false_modified:
                phi_sources.append((false_block.label, false_modified[name]))
            elif name in pre_env:
                phi_sources.append((false_block.label, pre_env[name]))

            # 只有当至少有两个不同来源时才需要 Phi
            if len(phi_sources) >= 2:
                instr = MIRPhi(UNIT_TYPE)  # 类型简化，后续类型检查会处理
                instr.sources = phi_sources
                instr.result_name = self._new_ssa()
                merge_block.instructions.append(instr)
                self.env[name] = instr.result_name

        # --- 表达式结果 Phi（if 表达式本身的值）---
        result_phi_sources = []
        if true_result:
            result_phi_sources.append((true_block.label, true_result))
        if false_result:
            result_phi_sources.append((false_block.label, false_result))

        merge_ssa = None
        if result_phi_sources:
            instr = MIRPhi(hir_expr.ir_type)
            instr.sources = result_phi_sources
            instr.result_name = self._new_ssa()
            merge_block.instructions.append(instr)
            merge_ssa = instr.result_name

        self.all_blocks.extend([true_block, false_block, merge_block])
        self.current_block = merge_block
        return merge_ssa

    def _lower_match_expr(self, hir_expr, block):
        """
        降级 match 表达式：实现真正的模式匹配分支逻辑。

        编译策略：
          - 每个 arm 生成一个"模式检查块" + "arm body 块"
          - 检查块中生成模式比较代码，匹配成功跳 body 块，失败跳下一个 arm 的检查块
          - 所有 body 块跳转到 merge 块，通过 Phi 节点合并结果
          - 支持模式：字面量模式(int/float/string/bool/char)、通配符(_)、
            绑定模式(x)、构造器模式(Variant(fields...))

        SSA 语义：
          - 每个 arm 在独立的 env 上下文中运行（arm 间隔离）
          - 多个 arm 都修改的变量，在 merge 块插入 Phi 节点
        """
        value_ssa = self._lower_expr(hir_expr.value, block)
        arms = hir_expr.arms
        if not arms:
            return None

        merge_block = MIRBasicBlock(self._new_block())
        arm_body_blocks = []  # 每个 arm 的 body 块，用于收集 Phi source
        arm_results = []  # 每个 arm body 的结果 SSA 名
        arm_modified_envs = []  # 每个 arm 修改的 env {name: ssa}

        # 为每个 arm 创建检查块和 body 块
        check_blocks = [MIRBasicBlock(self._new_block()) for _ in range(len(arms))]
        body_blocks = [MIRBasicBlock(self._new_block()) for _ in range(len(arms))]
        # 最后一个 arm 之后的失败块（理论上穷举匹配不会到达）
        fail_block = MIRBasicBlock(self._new_block())

        # 入口块跳转到第一个 arm 的检查块
        block.terminator = MIRJump(check_blocks[0].label)

        # 保存进入 match 前的 env 状态
        pre_env = dict(self.env)
        old_block = self.current_block

        for i, arm in enumerate(arms):
            # 每个 arm 开始前恢复 env（arm 间隔离）
            self.env = dict(pre_env)

            # --- 模式检查块 ---
            self.current_block = check_blocks[i]
            next_check = (
                check_blocks[i + 1].label if i + 1 < len(arms) else fail_block.label
            )

            self._lower_pattern(
                arm.pattern,
                value_ssa or "",
                check_blocks[i],
                body_blocks[i].label,
                next_check,
            )

            # 如果检查块没有被设置 terminator（比如通配符模式无条件匹配），
            # 默认跳转到 body 块
            if check_blocks[i].terminator is None:
                check_blocks[i].terminator = MIRJump(body_blocks[i].label)

            # --- arm body 块 ---
            self.current_block = body_blocks[i]
            arm_result = self._lower_expr(arm.body, body_blocks[i])
            if body_blocks[i].terminator is None:
                body_blocks[i].terminator = MIRJump(merge_block.label)

            arm_body_blocks.append(body_blocks[i])
            arm_results.append(arm_result)

            # 收集本 arm 修改的变量
            modified = {}
            for name, ssa in self.env.items():
                if name not in pre_env or pre_env[name] != ssa:
                    modified[name] = ssa
            arm_modified_envs.append(modified)

        # --- 失败块（理论不可达，放一个 panic） ---
        self.env = dict(pre_env)
        self.current_block = fail_block
        fail_block.terminator = MIRPanic("non-exhaustive match")

        # --- merge 块：为被修改的变量插入 Phi + 表达式结果 Phi ---
        self.current_block = merge_block
        self.env = dict(pre_env)

        # 找出所有在任一 arm 中被修改的变量
        all_modified_names = set()
        for modified in arm_modified_envs:
            all_modified_names.update(modified.keys())

        for name in all_modified_names:
            phi_sources = []

            for i, arm_block in enumerate(arm_body_blocks):
                if name in arm_modified_envs[i]:
                    # 本 arm 修改了该变量，用修改后的值
                    phi_sources.append((arm_block.label, arm_modified_envs[i][name]))
                elif name in pre_env:
                    # 本 arm 未修改，用进入 match 前的值
                    phi_sources.append((arm_block.label, pre_env[name]))

            # 至少两个不同来源才需要 Phi
            if len(phi_sources) >= 2:
                instr = MIRPhi(UNIT_TYPE)
                instr.sources = phi_sources
                instr.result_name = self._new_ssa()
                merge_block.instructions.append(instr)
                self.env[name] = instr.result_name

        # --- 表达式结果 Phi（match 表达式本身的值）---
        result_phi_sources = []
        for i, arm_block in enumerate(arm_body_blocks):
            if arm_results[i]:
                result_phi_sources.append((arm_block.label, arm_results[i]))

        merge_ssa = None
        if result_phi_sources:
            instr = MIRPhi(hir_expr.ir_type)
            instr.sources = result_phi_sources
            instr.result_name = self._new_ssa()
            merge_block.instructions.append(instr)
            merge_ssa = instr.result_name

        self.all_blocks.extend(check_blocks + body_blocks + [fail_block, merge_block])
        self.current_block = merge_block
        return merge_ssa

    def _lower_pattern(self, pattern, value_ssa, block, match_target, fail_target):
        """
        降级单个模式：在 block 中生成模式检查代码。
        匹配成功跳 match_target，失败跳 fail_target。

        对于绑定模式和通配符模式，由于总是匹配成功，
        直接在 block 中做绑定/什么都不做，调用方会跳 match_target。
        """
        from ir_nodes import (
            HIRBindPattern,
            HIRBoolPattern,
            HIRCharPattern,
            HIRConstructorPattern,
            HIRFloatPattern,
            HIRIntPattern,
            HIRStringPattern,
            HIRWildcardPattern,
        )

        if isinstance(pattern, HIRWildcardPattern):
            # 通配符总是匹配，什么都不用做
            return

        if isinstance(pattern, HIRBindPattern):
            # 绑定模式：总是匹配，将值绑定到变量名
            self.env[pattern.name] = value_ssa
            return

        if isinstance(
            pattern,
            (
                HIRIntPattern,
                HIRFloatPattern,
                HIRStringPattern,
                HIRBoolPattern,
                HIRCharPattern,
            ),
        ):
            # 字面量模式：生成比较 + 条件分支
            const_type_map = {
                HIRIntPattern: "int",
                HIRFloatPattern: "float",
                HIRStringPattern: "string",
                HIRBoolPattern: "bool",
                HIRCharPattern: "char",
            }
            const_instr = MIRConst(pattern.__class__)  # 类型不重要
            const_instr.value = pattern.value
            const_instr.const_type = const_type_map[type(pattern)]
            const_ssa = self._emit(const_instr)

            cmp_instr = MIRBinOp(UNIT_TYPE)  # 结果类型应为 Bool，简化处理
            cmp_instr.op = "=="
            cmp_instr.left = value_ssa
            cmp_instr.right = const_ssa
            cmp_ssa = self._emit(cmp_instr)

            block.terminator = MIRBranch(cmp_ssa, match_target, fail_target)
            return

        if isinstance(pattern, HIRConstructorPattern):
            # 构造器模式：比较 variant tag，匹配成功后递归绑定字段
            # 1. 先比较 variant 名称（通过 ADT 标签访问）
            tag_instr = MIRFieldAccess(UNIT_TYPE)
            tag_instr.object = value_ssa
            tag_instr.field_name = "tag"
            tag_instr.field_index = 0
            tag_ssa = self._emit(tag_instr)

            # 生成 variant 名常量做比较
            tag_const = MIRConst(UNIT_TYPE)
            tag_const.value = pattern.variant_name
            tag_const.const_type = "string"
            tag_const_ssa = self._emit(tag_const)

            tag_cmp = MIRBinOp(UNIT_TYPE)
            tag_cmp.op = "=="
            tag_cmp.left = tag_ssa
            tag_cmp.right = tag_const_ssa
            tag_cmp_ssa = self._emit(tag_cmp)

            # 如果字段模式为空，直接比较 tag 即可
            if not pattern.field_patterns:
                block.terminator = MIRBranch(tag_cmp_ssa, match_target, fail_target)
                return

            # 有字段模式：需要一个中间块来做字段绑定和递归检查
            field_check_block = MIRBasicBlock(self._new_block())
            block.terminator = MIRBranch(
                tag_cmp_ssa, field_check_block.label, fail_target
            )

            self.current_block = field_check_block
            # 递归处理每个字段模式
            current_target = match_target
            # 从后往前处理，这样 fail_target 可以串联起来
            for j in range(len(pattern.field_patterns) - 1, -1, -1):
                field_pat = pattern.field_patterns[j]
                field_name = f"field{j}"

                # 提取字段值
                field_instr = MIRFieldAccess(UNIT_TYPE)
                field_instr.object = value_ssa
                field_instr.field_name = field_name
                field_instr.field_index = j + 1  # tag 在 index 0
                field_ssa = self._emit(field_instr)

                # 为该字段创建检查块
                fblock = MIRBasicBlock(self._new_block())
                self.current_block = fblock

                self._lower_pattern(
                    field_pat, field_ssa, fblock, current_target, fail_target
                )

                if fblock.terminator is None:
                    fblock.terminator = MIRJump(current_target)

                self.all_blocks.append(fblock)
                current_target = fblock.label

            # field_check_block 跳转到第一个字段的检查块
            field_check_block.terminator = MIRJump(current_target)
            self.all_blocks.append(field_check_block)
            return

        # 不支持的模式：当作通配符处理（总是匹配）
        return

    def _lower_pipe_expr(self, hir_expr, block):
        result = self._lower_expr(hir_expr.stages[0], block)
        for stage in hir_expr.stages[1:]:
            stage_ssa = self._lower_expr(stage, block)
            instr = MIRCall(hir_expr.ir_type)
            instr.callee = stage_ssa or ""
            instr.args = [result or ""]
            result = self._emit(instr)
        return result

    def _lower_for_expr(self, hir_expr, block):
        """
        降级 for 循环表达式：用索引遍历实现，正确绑定循环变量。

        编译结构：
          iter = iterable          // 计算可迭代对象
          len = list_length(iter)  // 获取长度
          i = 0                    // 索引变量
          goto header
          header:
            phi_i = phi(entry: i, body: i_next)
            cond = phi_i < len
            if cond goto body else goto exit
          body:
            elem = list_get(iter, phi_i)   // 当前元素
            variable = elem                // 绑定循环变量
            body_expr...
            i_next = phi_i + 1
            goto header
          exit:
            return unit
        """
        header_block = MIRBasicBlock(self._new_block())
        body_block = MIRBasicBlock(self._new_block())
        exit_block = MIRBasicBlock(self._new_block())

        # 在入口块计算可迭代对象和长度
        iter_ssa = self._lower_expr(hir_expr.iterable, block)

        # 调用 list_length 获取长度
        len_instr = MIRCall(UNIT_TYPE)
        len_instr.callee = "list_length"
        len_instr.args = [iter_ssa or ""]
        len_ssa = self._emit(len_instr)

        # 索引变量初始值 0
        idx_init_instr = MIRConst(UNIT_TYPE)
        idx_init_instr.value = 0
        idx_init_instr.const_type = "int"
        idx_init_ssa = self._emit(idx_init_instr)

        # 跳转到循环头
        block.terminator = MIRJump(header_block.label)

        # --- 循环头：Phi 节点 + 条件判断 ---
        self.current_block = header_block

        # 索引变量的 Phi（先占位，body 处理完后补充 source）
        idx_phi = MIRPhi(UNIT_TYPE)
        idx_phi.result_name = self._new_ssa()
        idx_phi.sources = []  # 稍后填充
        header_block.instructions.append(idx_phi)
        idx_phi_ssa = idx_phi.result_name

        # 比较 i < len
        cmp_instr = MIRBinOp(UNIT_TYPE)
        cmp_instr.op = "<"
        cmp_instr.left = idx_phi_ssa
        cmp_instr.right = len_ssa
        cmp_ssa = self._emit(cmp_instr)

        header_block.terminator = MIRBranch(cmp_ssa, body_block.label, exit_block.label)

        # 压入循环上下文（break → exit, continue → header）
        self.loop_stack.append((header_block.label, exit_block.label))

        # --- 循环体 ---
        self.current_block = body_block

        # 获取当前元素: list_get(iter, i)
        get_instr = MIRCall(UNIT_TYPE)
        get_instr.callee = "list_get"
        get_instr.args = [iter_ssa or "", idx_phi_ssa]
        elem_ssa = self._emit(get_instr)

        # 绑定循环变量到当前元素
        self.env[hir_expr.variable] = elem_ssa

        self._lower_expr(hir_expr.body, body_block)

        # 索引递增: i = i + 1
        inc_instr = MIRBinOp(UNIT_TYPE)
        inc_instr.op = "+"
        inc_instr.left = idx_phi_ssa
        inc_right = MIRConst(UNIT_TYPE)
        inc_right.value = 1
        inc_right.const_type = "int"
        inc_right_ssa = self._emit(inc_right)
        inc_instr.right = inc_right_ssa
        inc_ssa = self._emit(inc_instr)

        if body_block.terminator is None:
            body_block.terminator = MIRJump(header_block.label)

        # 弹出循环上下文
        self.loop_stack.pop()

        # 填充 Phi 的 sources
        idx_phi.sources = [
            (block.label, idx_init_ssa),
            (body_block.label, inc_ssa),
        ]

        self.all_blocks.extend([header_block, body_block, exit_block])
        self.current_block = exit_block
        return None

    def _lower_list_comprehension(self, hir_expr, block):
        """
        降级列表推导式：[result_expr | variable <- iterable, filter?]

        用索引遍历实现，循环变量正确绑定到当前元素。
        编译结构：
          list = []                    // 空列表
          iter = iterable              // 可迭代对象
          len = list_length(iter)      // 长度
          i = 0                        // 索引
          goto header
          header:
            phi_i = phi(entry: i, latch: i_next)
            phi_list = phi(entry: list, latch: list_next)
            cond = phi_i < len
            if cond goto body else goto exit
          body:
            elem = list_get(iter, phi_i)   // 当前元素
            variable = elem                // 绑定循环变量
            // 可选 filter 检查
            // 计算 result_expr
            list_next = list_append(phi_list, result)
            i_next = phi_i + 1
            goto header
          exit:
            return phi_list
        """
        header_block = MIRBasicBlock(self._new_block())
        body_block = MIRBasicBlock(self._new_block())
        exit_block = MIRBasicBlock(self._new_block())

        # 1. 在入口块创建空列表、计算可迭代对象和长度
        empty_list_instr = MIRListBuild(hir_expr.ir_type)
        empty_list_instr.elements = []
        list_init_ssa = self._emit(empty_list_instr)

        iter_ssa = self._lower_expr(hir_expr.iterable, block)

        # 调用 list_length 获取长度
        len_instr = MIRCall(UNIT_TYPE)
        len_instr.callee = "list_length"
        len_instr.args = [iter_ssa or ""]
        len_ssa = self._emit(len_instr)

        # 索引变量初始值 0
        idx_init_instr = MIRConst(UNIT_TYPE)
        idx_init_instr.value = 0
        idx_init_instr.const_type = "int"
        idx_init_ssa = self._emit(idx_init_instr)

        # 2. 跳转到循环头
        block.terminator = MIRJump(header_block.label)

        # 3. 循环头：Phi 节点 + 条件分支
        self.current_block = header_block

        # 索引 Phi（先占位，稍后填充 sources）
        idx_phi = MIRPhi(UNIT_TYPE)
        idx_phi.result_name = self._new_ssa()
        idx_phi.sources = []
        header_block.instructions.append(idx_phi)
        idx_phi_ssa = idx_phi.result_name

        # 列表 Phi（循环携带的列表值）
        list_phi = MIRPhi(hir_expr.ir_type)
        list_phi.result_name = self._new_ssa()
        list_phi.sources = []
        header_block.instructions.append(list_phi)
        list_phi_ssa = list_phi.result_name

        # 比较 i < len
        cmp_instr = MIRBinOp(UNIT_TYPE)
        cmp_instr.op = "<"
        cmp_instr.left = idx_phi_ssa
        cmp_instr.right = len_ssa
        cmp_ssa = self._emit(cmp_instr)

        header_block.terminator = MIRBranch(cmp_ssa, body_block.label, exit_block.label)

        # 压入循环上下文（break → exit, continue → header）
        self.loop_stack.append((header_block.label, exit_block.label))

        # 4. 循环体
        self.current_block = body_block

        # 获取当前元素: list_get(iter, i)
        get_instr = MIRCall(UNIT_TYPE)
        get_instr.callee = "list_get"
        get_instr.args = [iter_ssa or "", idx_phi_ssa]
        elem_ssa = self._emit(get_instr)

        # 绑定循环变量到当前元素
        self.env[hir_expr.variable] = elem_ssa

        # 用于接收最终列表值的变量（可能经过 filter 分支）
        final_list_ssa = None
        # 索引递增的结果（在所有路径上都应该有）
        final_idx_ssa = None
        # 循环体尾部跳转到 header 的块
        latch_block = None

        if hir_expr.filter is not None:
            # 有 filter：先判断 filter 条件
            filter_block = MIRBasicBlock(self._new_block())
            filter_false_block = MIRBasicBlock(self._new_block())

            filter_ssa = self._lower_expr(hir_expr.filter, body_block)
            body_block.terminator = MIRBranch(
                filter_ssa or "", filter_block.label, filter_false_block.label
            )

            # --- filter 为真：计算 result_expr 并 append ---
            self.current_block = filter_block
            result_ssa = self._lower_expr(hir_expr.result_expr, filter_block)

            append_instr = MIRListAppend(hir_expr.ir_type)
            append_instr.list_ssa = list_phi_ssa
            append_instr.element_ssa = result_ssa or ""
            new_list_ssa = self._emit(append_instr)

            # 索引递增
            inc_instr_t = MIRBinOp(UNIT_TYPE)
            inc_instr_t.op = "+"
            inc_instr_t.left = idx_phi_ssa
            inc_const_t = MIRConst(UNIT_TYPE)
            inc_const_t.value = 1
            inc_const_t.const_type = "int"
            inc_const_ssa_t = self._emit(inc_const_t)
            inc_instr_t.right = inc_const_ssa_t
            inc_ssa_t = self._emit(inc_instr_t)

            filter_block.terminator = MIRJump(header_block.label)

            # --- filter 为假：跳过 append，索引仍然递增 ---
            self.current_block = filter_false_block

            inc_instr_f = MIRBinOp(UNIT_TYPE)
            inc_instr_f.op = "+"
            inc_instr_f.left = idx_phi_ssa
            inc_const_f = MIRConst(UNIT_TYPE)
            inc_const_f.value = 1
            inc_const_f.const_type = "int"
            inc_const_ssa_f = self._emit(inc_const_f)
            inc_instr_f.right = inc_const_ssa_f
            inc_ssa_f = self._emit(inc_instr_f)

            filter_false_block.terminator = MIRJump(header_block.label)

            self.all_blocks.extend([filter_block, filter_false_block])

            # 两个分支都跳回 header，Phi 有两个来源
            # 列表 Phi 的来源：filter 为真时是 new_list_ssa，为假时是 list_phi_ssa（不变）
            list_phi.sources = [
                (block.label, list_init_ssa),
                (filter_block.label, new_list_ssa),
                (filter_false_block.label, list_phi_ssa),
            ]
            # 索引 Phi 的来源
            idx_phi.sources = [
                (block.label, idx_init_ssa),
                (filter_block.label, inc_ssa_t),
                (filter_false_block.label, inc_ssa_f),
            ]
        else:
            # 无 filter：直接计算 result_expr 并 append
            result_ssa = self._lower_expr(hir_expr.result_expr, body_block)

            append_instr = MIRListAppend(hir_expr.ir_type)
            append_instr.list_ssa = list_phi_ssa
            append_instr.element_ssa = result_ssa or ""
            new_list_ssa = self._emit(append_instr)

            # 索引递增
            inc_instr = MIRBinOp(UNIT_TYPE)
            inc_instr.op = "+"
            inc_instr.left = idx_phi_ssa
            inc_const = MIRConst(UNIT_TYPE)
            inc_const.value = 1
            inc_const.const_type = "int"
            inc_const_ssa = self._emit(inc_const)
            inc_instr.right = inc_const_ssa
            inc_ssa = self._emit(inc_instr)

            if body_block.terminator is None:
                body_block.terminator = MIRJump(header_block.label)

            # 填充 Phi sources
            list_phi.sources = [
                (block.label, list_init_ssa),
                (body_block.label, new_list_ssa),
            ]
            idx_phi.sources = [
                (block.label, idx_init_ssa),
                (body_block.label, inc_ssa),
            ]

        # 弹出循环上下文
        self.loop_stack.pop()

        # 5. exit 块：列表 Phi 的值就是结果
        # 将 list_phi 从 header 移到 exit？不，list_phi 在 header 中定义是正确的，
        # 因为 header 支配 exit。但 header 有分支指令，Phi 应该在 header 开头。
        # 结果值就是 list_phi_ssa（header 中的 Phi）。
        # 但我们需要 exit 块里的结果值——实际上，从 exit 块看，
        # 列表的最终值在 header 的 Phi 中就已经可用（header 支配 exit）。
        # 为了清晰，在 exit 块放一个空的"结果"，直接返回 list_phi_ssa。
        # 由于 header 支配 exit，exit 可以引用 list_phi_ssa。

        self.all_blocks.extend([header_block, body_block, exit_block])
        self.current_block = exit_block
        return list_phi_ssa

    def _lower_while_expr(self, hir_expr, block):
        """
        降级 while 循环，带正确的 SSA Phi 节点。

        生成的 CFG 结构：
          entry:
            <lowered: any pre-loop code>
            goto header
          header:
            phi(x_init, x_back_edge)  // 循环中被修改的变量都有 Phi
            cond = <lower condition>
            if cond goto body else goto exit
          body:
            <lower body>
            x_new = <updated value>
            goto header
          exit:
            return unit

        SSA 策略：
        1. 进入循环前保存 env 快照（pre_env）
        2. 处理完循环体后，比较 env 找出被修改的变量
        3. 在 header 块开头为每个被修改的变量插入 Phi 节点
        4. Phi 的 sources: 入口边(pre值) + 回边(body末尾的值)
        5. 替换 header 和 body 中对这些变量的引用为 Phi 结果
        """
        header_block = MIRBasicBlock(self._new_block())
        body_block = MIRBasicBlock(self._new_block())
        exit_block = MIRBasicBlock(self._new_block())

        # 1. 进入循环前保存 env 快照
        pre_env = dict(self.env)

        block.terminator = MIRJump(header_block.label)

        # 2. 先降级条件（用初始 env 值，后面会替换为 Phi 结果）
        self.current_block = header_block
        cond_ssa = self._lower_expr(hir_expr.condition, header_block)
        header_block.terminator = MIRBranch(
            cond_ssa or "", body_block.label, exit_block.label
        )

        # 压入循环上下文（break → exit, continue → header）
        self.loop_stack.append((header_block.label, exit_block.label))

        # 3. 降级循环体
        self.current_block = body_block
        self._lower_expr(hir_expr.body, body_block)
        if body_block.terminator is None:
            body_block.terminator = MIRJump(header_block.label)

        # 弹出循环上下文
        self.loop_stack.pop()

        # 4. 找出循环中被修改的变量（比较 pre_env 和当前 env）
        modified_vars = {}
        for name, ssa_val in self.env.items():
            if name not in pre_env or pre_env[name] != ssa_val:
                modified_vars[name] = ssa_val

        # 5. 在 header 块开头为每个被修改的变量插入 Phi 节点
        phi_offset = 0
        for var_name, body_ssa in modified_vars.items():
            pre_ssa = pre_env.get(var_name)
            if pre_ssa is None:
                # 循环中新定义的变量，入口边没有值，跳过（理论上不应该出现）
                continue

            phi_instr = MIRPhi(UNIT_TYPE)  # 类型简化，后续类型检查会处理
            phi_instr.sources = [
                (block.label, pre_ssa),  # 入口边：循环前的值
                (body_block.label, body_ssa),  # 回边：循环体末尾的值
            ]
            phi_instr.result_name = self._new_ssa()
            header_block.instructions.insert(phi_offset, phi_instr)
            phi_offset += 1

            # 6. 替换 header 和 body 中对旧 SSA 的引用为 Phi 结果
            phi_result = phi_instr.result_name
            # header 中对 pre_ssa 的引用替换为 phi_result
            self._replace_ssa_in_block(header_block, pre_ssa, phi_result, skip_phi=True)
            # body 中对 pre_ssa 的引用替换为 phi_result
            self._replace_ssa_in_block(body_block, pre_ssa, phi_result, skip_phi=False)

            # 更新 env 中的值为 Phi 结果
            self.env[var_name] = phi_result

        self.all_blocks.extend([header_block, body_block, exit_block])
        self.current_block = exit_block
        return None
