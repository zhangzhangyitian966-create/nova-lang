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
                self.env[hir_expr.target.name] = val_ssa
                instr = MIRStore(UNIT_TYPE)
                instr.name = hir_expr.target.name
                instr.value = val_ssa or ""
                return self._emit(instr)
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
        cond_ssa = self._lower_expr(hir_expr.condition, block)

        true_block = MIRBasicBlock(self._new_block())
        false_block = MIRBasicBlock(self._new_block())
        merge_block = MIRBasicBlock(self._new_block())

        block.terminator = MIRBranch(
            cond_ssa or "", true_block.label, false_block.label
        )

        old_block = self.current_block
        self.current_block = true_block
        true_result = self._lower_expr(hir_expr.consequence, true_block)
        if true_block.terminator is None:
            true_block.terminator = MIRJump(merge_block.label)
        self.current_block = old_block

        self.current_block = false_block
        false_result = None
        if hir_expr.alternative:
            false_result = self._lower_expr(hir_expr.alternative, false_block)
        if false_block.terminator is None:
            false_block.terminator = MIRJump(merge_block.label)
        self.current_block = old_block

        phi_sources = []
        if true_result:
            phi_sources.append((true_block.label, true_result))
        if false_result:
            phi_sources.append((false_block.label, false_result))

        merge_ssa = None
        if phi_sources:
            instr = MIRPhi(hir_expr.ir_type)
            instr.sources = phi_sources
            instr.result_name = self._new_ssa()
            merge_block.instructions.append(instr)
            merge_ssa = instr.result_name

        self.all_blocks.extend([true_block, false_block, merge_block])
        self.current_block = merge_block
        return merge_ssa

    def _lower_match_expr(self, hir_expr, block):
        """
        降级 match 表达式：使用级联比较（if-elseif 链）实现模式匹配。

        支持的模式类型：
        - 常量模式（Int/Float/String/Bool/Char）：生成 == 比较 + 条件分支
        - 通配符模式（_）：无条件匹配
        - 绑定模式（x）：无条件匹配 + 将 scrutinee 绑定到变量名

        控制流结构：
          bb_check_0: 比较 scrutinee == pattern_0
            if true goto bb_arm_0 else goto bb_check_1
          bb_arm_0: arm_0 body → goto bb_merge
          bb_check_1: 比较 scrutinee == pattern_1
            if true goto bb_arm_1 else goto bb_check_2
          ...
          bb_arm_N: arm_N body → goto bb_merge
          bb_merge: phi(arm_0_result, arm_1_result, ...)
        """
        value_ssa = self._lower_expr(hir_expr.value, block)
        arms = hir_expr.arms
        if not arms:
            return None

        # 保存当前环境，每个 arm 独立计算，避免变量泄漏
        saved_env = dict(self.env)

        merge_block = MIRBasicBlock(self._new_block())
        arm_body_blocks = []
        phi_sources = []  # (arm_block_label, result_ssa)

        # 当前"fall-through"块（下一个模式检查的入口）
        current_fallthrough = block

        for i, arm in enumerate(arms):
            arm_body_block = MIRBasicBlock(self._new_block())
            arm_body_blocks.append(arm_body_block)

            # 恢复环境到 match 开始时的状态（每个 arm 独立）
            self.env = dict(saved_env)

            # 判断模式类型，生成检查代码
            pattern = arm.pattern
            is_unconditional = False  # 是否无条件匹配（通配符/绑定模式）

            if isinstance(pattern, (HIRWildcardPattern, HIRBindPattern)):
                # 通配符或绑定模式：无条件匹配
                is_unconditional = True

                # 绑定模式：将 scrutinee 绑定到变量名
                if isinstance(pattern, HIRBindPattern):
                    self.env[pattern.name] = value_ssa or ""

                # 无条件跳转到 arm body
                current_fallthrough.terminator = MIRJump(arm_body_block.label)

            else:
                # 常量模式：生成比较 + 条件分支
                check_block = current_fallthrough
                self.current_block = check_block

                # 生成模式对应的常量指令
                const_ssa = self._emit_pattern_const(pattern)

                # 生成比较指令（scrutinee == pattern_value）
                cmp_instr = MIRBoolLiteral().ir_type
                from ir_nodes import BOOL_TYPE
                cmp_instr = MIRBinOp(BOOL_TYPE)
                cmp_instr.op = "=="
                cmp_instr.left = value_ssa or ""
                cmp_instr.right = const_ssa or ""
                cmp_ssa = self._emit(cmp_instr)

                # 条件跳转：匹配成功 → arm body，失败 → 下一个检查
                next_check_block = MIRBasicBlock(self._new_block())
                check_block.terminator = MIRBranch(
                    cmp_ssa, arm_body_block.label, next_check_block.label
                )
                self.all_blocks.append(next_check_block)
                current_fallthrough = next_check_block

            # 降级 arm body
            self.current_block = arm_body_block
            arm_result = self._lower_expr(arm.body, arm_body_block)

            # 如果有 guard 条件，需要额外检查
            # （guard 为假时 fall-through 到下一个 arm）
            if arm.guard is not None and not is_unconditional:
                # guard 检查块
                guard_true_block = MIRBasicBlock(self._new_block())
                next_fallthrough = MIRBasicBlock(self._new_block())

                guard_ssa = self._lower_expr(arm.guard, arm_body_block)
                arm_body_block.terminator = MIRBranch(
                    guard_ssa or "", guard_true_block.label, next_fallthrough.label
                )

                # guard 为真：继续执行 arm body 剩余部分
                # （简化：guard 直接在 body 前检查，body 在 guard_true_block 中）
                # 这里重新组织：body 在 guard_true_block 中计算
                # 为简化实现，将 guard 视为 arm body 的前置条件
                # 重新计算 arm result 在 guard_true_block 中
                self.current_block = guard_true_block
                arm_result = self._lower_expr(arm.body, guard_true_block)

                if guard_true_block.terminator is None:
                    guard_true_block.terminator = MIRJump(merge_block.label)

                self.all_blocks.extend([guard_true_block, next_fallthrough])
                arm_body_block = guard_true_block  # 用 guard_true 作为 arm 的结果块
                current_fallthrough = next_fallthrough
            else:
                # 无 guard：arm body 结束后跳转到 merge
                if arm_body_block.terminator is None:
                    arm_body_block.terminator = MIRJump(merge_block.label)

            # 收集 Phi 来源
            if arm_result:
                phi_sources.append((arm_body_block.label, arm_result))

            # 如果是无条件匹配，后续 arm 不可达，停止处理
            if is_unconditional and arm.guard is None:
                break

        # 恢复环境
        self.env = dict(saved_env)

        # merge 块：Phi 节点合并所有 arm 结果
        merge_ssa = None
        if phi_sources:
            instr = MIRPhi(hir_expr.ir_type)
            instr.sources = phi_sources
            instr.result_name = self._new_ssa()
            merge_block.instructions.append(instr)
            merge_ssa = instr.result_name

        self.all_blocks.extend(arm_body_blocks + [merge_block])
        self.current_block = merge_block
        return merge_ssa

    def _emit_pattern_const(self, pattern):
        """为常量模式生成 MIRConst 指令，返回结果 SSA 名。"""
        from ir_nodes import (
            INT_TYPE, FLOAT_TYPE, STRING_TYPE, BOOL_TYPE, CHAR_TYPE,
        )

        if isinstance(pattern, HIRIntPattern):
            instr = MIRConst(INT_TYPE)
            instr.value = pattern.value
            instr.const_type = "int"
        elif isinstance(pattern, HIRFloatPattern):
            instr = MIRConst(FLOAT_TYPE)
            instr.value = pattern.value
            instr.const_type = "float"
        elif isinstance(pattern, HIRStringPattern):
            instr = MIRConst(STRING_TYPE)
            instr.value = pattern.value
            instr.const_type = "string"
        elif isinstance(pattern, HIRBoolPattern):
            instr = MIRConst(BOOL_TYPE)
            instr.value = pattern.value
            instr.const_type = "bool"
        elif isinstance(pattern, HIRCharPattern):
            instr = MIRConst(CHAR_TYPE)
            instr.value = pattern.value
            instr.const_type = "char"
        else:
            # 不支持的模式类型，返回 unit（不应到达）
            instr = MIRConst(UNIT_TYPE)
            instr.value = None
            instr.const_type = "unit"

        return self._emit(instr)

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
        降级 for 循环表达式：使用索引迭代可迭代对象。

        控制流结构：
          bb_entry:
            iter = iterable
            idx = 0
            goto bb_header
          bb_header:
            len = list_length(iter)
            cond = idx < len
            if cond goto bb_body else goto bb_exit
          bb_body:
            elem = iter[idx]       // 当前元素
            env[variable] = elem   // 绑定循环变量
            body_expr
            idx = idx + 1
            goto bb_header
          bb_exit:
            return unit
        """
        from ir_nodes import INT_TYPE

        header_block = MIRBasicBlock(self._new_block())
        body_block = MIRBasicBlock(self._new_block())
        exit_block = MIRBasicBlock(self._new_block())

        # 1. 在入口块降级可迭代对象，初始化索引
        iter_ssa = self._lower_expr(hir_expr.iterable, block)

        # idx = 0
        zero_instr = MIRConst(INT_TYPE)
        zero_instr.value = 0
        zero_instr.const_type = "int"
        idx_ssa = self._emit(zero_instr)

        block.terminator = MIRJump(header_block.label)

        # 2. 循环头：计算长度，判断条件
        self.current_block = header_block

        # 调用 list_length 获取长度
        len_instr = MIRCall(INT_TYPE)
        len_instr.callee = "list_length"
        len_instr.args = [iter_ssa or ""]
        len_ssa = self._emit(len_instr)

        # cond = idx < len
        cmp_instr = MIRBinOp(INT_TYPE)  # 实际是 bool 类型
        from ir_nodes import BOOL_TYPE
        cmp_instr = MIRBinOp(BOOL_TYPE)
        cmp_instr.op = "<"
        cmp_instr.left = idx_ssa
        cmp_instr.right = len_ssa
        cond_ssa = self._emit(cmp_instr)

        header_block.terminator = MIRBranch(
            cond_ssa, body_block.label, exit_block.label
        )

        # 压入循环上下文（break → exit, continue → header）
        self.loop_stack.append((header_block.label, exit_block.label))

        # 3. 循环体：获取当前元素，绑定循环变量，执行 body
        self.current_block = body_block

        # elem = iter[idx] (MIRIndexAccess)
        elem_instr = MIRIndexAccess(hir_expr.ir_type)
        elem_instr.object = iter_ssa or ""
        elem_instr.index = idx_ssa
        elem_ssa = self._emit(elem_instr)

        # 绑定循环变量到当前元素
        self.env[hir_expr.variable] = elem_ssa

        # 执行 body
        self._lower_expr(hir_expr.body, body_block)

        # idx = idx + 1
        one_instr = MIRConst(INT_TYPE)
        one_instr.value = 1
        one_instr.const_type = "int"
        one_ssa = self._emit(one_instr)

        add_instr = MIRBinOp(INT_TYPE)
        add_instr.op = "+"
        add_instr.left = idx_ssa
        add_instr.right = one_ssa
        new_idx_ssa = self._emit(add_instr)

        # 更新 idx_ssa 用于下一轮迭代（通过 header 的 Phi）
        # 注意：这里简化处理，直接在 body 末尾更新，header 中用 Phi 合并
        if body_block.terminator is None:
            body_block.terminator = MIRJump(header_block.label)

        # 在 header 块开头插入 Phi 节点合并 idx 的初始值和循环回边值
        phi_instr = MIRPhi(INT_TYPE)
        phi_instr.sources = [
            (block.label, idx_ssa),
            (body_block.label, new_idx_ssa),
        ]
        phi_instr.result_name = self._new_ssa()
        header_block.instructions.insert(0, phi_instr)

        # 更新 idx_ssa 引用为 Phi 结果
        # （简化：header 中后续使用的 idx 仍是旧的，但由于 body 中计算 new_idx_ssa
        #  用的是旧 idx_ssa，而 header 开头的 Phi 定义了新名，需要更新引用）
        # 为简化实现，这里用一个变通方案：将 idx_ssa 重映射到 Phi 结果
        # 实际正确做法是重写 header 中所有 idx_ssa 的引用
        # 这里做一个简化：直接替换 header 中指令里的 idx_ssa 为 phi 结果
        phi_result = phi_instr.result_name
        for instr in header_block.instructions[1:]:  # 跳过 Phi 本身
            if hasattr(instr, 'left') and instr.left == idx_ssa:
                instr.left = phi_result
            if hasattr(instr, 'right') and instr.right == idx_ssa:
                instr.right = phi_result
            if hasattr(instr, 'index') and instr.index == idx_ssa:
                instr.index = phi_result
            if hasattr(instr, 'object') and instr.object == idx_ssa:
                instr.object = phi_result
            if hasattr(instr, 'args'):
                instr.args = [phi_result if a == idx_ssa else a for a in instr.args]

        # 同时更新 body 中 idx_ssa 的引用（body 用的是 header Phi 出来的值）
        for instr in body_block.instructions:
            if hasattr(instr, 'left') and instr.left == idx_ssa:
                instr.left = phi_result
            if hasattr(instr, 'right') and instr.right == idx_ssa:
                instr.right = phi_result
            if hasattr(instr, 'index') and instr.index == idx_ssa:
                instr.index = phi_result
            if hasattr(instr, 'object') and instr.object == idx_ssa:
                instr.object = phi_result
            if hasattr(instr, 'args'):
                instr.args = [phi_result if a == idx_ssa else a for a in instr.args]

        # 弹出循环上下文
        self.loop_stack.pop()

        self.all_blocks.extend([header_block, body_block, exit_block])
        self.current_block = exit_block
        return None

    def _lower_list_comprehension(self, hir_expr, block):
        """
        降级列表推导式：[result_expr | variable <- iterable, filter?]

        编译为以下结构（带索引迭代）：
          bb_entry:
            list = []               // 空列表
            iter = iterable
            idx = 0
            goto bb_header
          bb_header:
            len = list_length(iter)
            cond = idx < len
            if cond goto bb_body else goto bb_exit
          bb_body:
            elem = iter[idx]       // 当前元素
            env[variable] = elem   // 绑定循环变量到当前元素
            // 可选 filter 检查
            // 计算 result_expr
            list = list_append(list, result)
            idx = idx + 1
            goto bb_header
          bb_exit:
            phi(list_init, list_final)
            return list
        """
        from ir_nodes import INT_TYPE, BOOL_TYPE

        header_block = MIRBasicBlock(self._new_block())
        body_block = MIRBasicBlock(self._new_block())
        exit_block = MIRBasicBlock(self._new_block())

        # 1. 在入口块创建空列表，降级可迭代对象，初始化索引
        empty_list_instr = MIRListBuild(hir_expr.ir_type)
        empty_list_instr.elements = []
        list_ssa = self._emit(empty_list_instr)

        iter_ssa = self._lower_expr(hir_expr.iterable, block)

        # idx = 0
        zero_instr = MIRConst(INT_TYPE)
        zero_instr.value = 0
        zero_instr.const_type = "int"
        idx_ssa = self._emit(zero_instr)

        # 2. 跳转到循环头
        block.terminator = MIRJump(header_block.label)

        # 3. 循环头：计算长度，条件分支
        self.current_block = header_block

        # 调用 list_length 获取长度
        len_instr = MIRCall(INT_TYPE)
        len_instr.callee = "list_length"
        len_instr.args = [iter_ssa or ""]
        len_ssa = self._emit(len_instr)

        # cond = idx < len
        cmp_instr = MIRBinOp(BOOL_TYPE)
        cmp_instr.op = "<"
        cmp_instr.left = idx_ssa
        cmp_instr.right = len_ssa
        cond_ssa = self._emit(cmp_instr)

        header_block.terminator = MIRBranch(
            cond_ssa, body_block.label, exit_block.label
        )

        # 压入循环上下文（break → exit, continue → header）
        self.loop_stack.append((header_block.label, exit_block.label))

        # 4. 循环体
        self.current_block = body_block

        # elem = iter[idx] (MIRIndexAccess) — 当前元素
        elem_instr = MIRIndexAccess(hir_expr.ir_type)
        elem_instr.object = iter_ssa or ""
        elem_instr.index = idx_ssa
        elem_ssa = self._emit(elem_instr)

        # 将循环变量绑定到当前元素（修复：之前错误地绑定到整个 iterable）
        self.env[hir_expr.variable] = elem_ssa

        # 保存 list_ssa 的当前值（用于 Phi 节点追踪）
        last_list_ssa = list_ssa
        last_block_label = body_block.label  # 最后更新 list 的块标签

        result_ssa = None
        if hir_expr.filter is not None:
            # 有 filter：先判断 filter 条件
            filter_block = MIRBasicBlock(self._new_block())
            filter_false_block = MIRBasicBlock(self._new_block())

            filter_ssa = self._lower_expr(hir_expr.filter, body_block)
            body_block.terminator = MIRBranch(
                filter_ssa or "", filter_block.label, filter_false_block.label
            )

            # filter 为真：计算 result_expr 并 append
            self.current_block = filter_block
            result_ssa = self._lower_expr(hir_expr.result_expr, filter_block)

            append_instr = MIRListAppend(hir_expr.ir_type)
            append_instr.list_ssa = list_ssa
            append_instr.element_ssa = result_ssa or ""
            new_list_ssa = self._emit(append_instr)
            list_ssa = new_list_ssa
            last_list_ssa = new_list_ssa
            last_block_label = filter_block.label

            filter_block.terminator = MIRJump(header_block.label)

            # filter 为假：跳过，直接回到循环头（list 不变）
            self.current_block = filter_false_block
            filter_false_block.terminator = MIRJump(header_block.label)

            self.all_blocks.extend([filter_block, filter_false_block])
        else:
            # 无 filter：直接计算 result_expr 并 append
            result_ssa = self._lower_expr(hir_expr.result_expr, body_block)

            append_instr = MIRListAppend(hir_expr.ir_type)
            append_instr.list_ssa = list_ssa
            append_instr.element_ssa = result_ssa or ""
            new_list_ssa = self._emit(append_instr)
            list_ssa = new_list_ssa
            last_list_ssa = new_list_ssa
            last_block_label = body_block.label

            if body_block.terminator is None:
                body_block.terminator = MIRJump(header_block.label)

        # idx = idx + 1（在 body 或 filter 块末尾，跳转前）
        # 需要找到最后一个有终结指令且终结指令是跳转到 header 的块
        # 简化：在 body_block 中计算 idx+1，如果有 filter 则在 filter 和 filter_false 中都算
        # 更简单的做法：在 header 中用 Phi 合并 idx
        one_instr = MIRConst(INT_TYPE)
        one_instr.value = 1
        one_instr.const_type = "int"
        one_ssa = self._emit(one_instr)

        add_instr = MIRBinOp(INT_TYPE)
        add_instr.op = "+"
        add_instr.left = idx_ssa
        add_instr.right = one_ssa
        new_idx_ssa = self._emit(add_instr)

        # 弹出循环上下文
        self.loop_stack.pop()

        # 5. 在 header 块开头插入 Phi 节点合并 idx
        idx_phi_instr = MIRPhi(INT_TYPE)
        idx_phi_instr.sources = [
            (block.label, idx_ssa),
            (last_block_label, new_idx_ssa),
        ]
        idx_phi_instr.result_name = self._new_ssa()
        header_block.instructions.insert(0, idx_phi_instr)

        # 更新 header 和 body 中 idx_ssa 的引用为 Phi 结果
        phi_idx_result = idx_phi_instr.result_name
        for blk in [header_block, body_block] + (
            [filter_block, filter_false_block] if hir_expr.filter else []
        ):
            for instr in blk.instructions:
                if instr is idx_phi_instr:
                    continue
                if hasattr(instr, 'left') and instr.left == idx_ssa:
                    instr.left = phi_idx_result
                if hasattr(instr, 'right') and instr.right == idx_ssa:
                    instr.right = phi_idx_result
                if hasattr(instr, 'index') and instr.index == idx_ssa:
                    instr.index = phi_idx_result
                if hasattr(instr, 'object') and instr.object == idx_ssa:
                    instr.object = phi_idx_result
                if hasattr(instr, 'args'):
                    instr.args = [phi_idx_result if a == idx_ssa else a for a in instr.args]

        # 6. exit 块：通过 Phi 合并列表值
        # 初始值来自入口块，最终值来自最后更新 list 的块
        phi_sources = [
            (block.label, empty_list_instr.result_name),
            (last_block_label, last_list_ssa),
        ]
        phi_instr = MIRPhi(hir_expr.ir_type)
        phi_instr.sources = phi_sources
        phi_instr.result_name = self._new_ssa()
        exit_block.instructions.append(phi_instr)

        self.all_blocks.extend([header_block, body_block, exit_block])
        self.current_block = exit_block
        return phi_instr.result_name

    def _lower_while_expr(self, hir_expr, block):
        header_block = MIRBasicBlock(self._new_block())
        body_block = MIRBasicBlock(self._new_block())
        exit_block = MIRBasicBlock(self._new_block())

        block.terminator = MIRJump(header_block.label)
        cond_ssa = self._lower_expr(hir_expr.condition, header_block)
        header_block.terminator = MIRBranch(
            cond_ssa or "", body_block.label, exit_block.label
        )

        # 压入循环上下文（break → exit, continue → header）
        self.loop_stack.append((header_block.label, exit_block.label))

        self._lower_expr(hir_expr.body, body_block)
        if body_block.terminator is None:
            body_block.terminator = MIRJump(header_block.label)

        # 弹出循环上下文
        self.loop_stack.pop()

        self.all_blocks.extend([header_block, body_block, exit_block])
        self.current_block = exit_block
        return None
