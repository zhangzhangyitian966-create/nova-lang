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
        value_ssa = self._lower_expr(hir_expr.value, block)
        arms = hir_expr.arms
        if not arms:
            return None

        arm_blocks = [MIRBasicBlock(self._new_block()) for _ in range(len(arms))]
        merge_block = MIRBasicBlock(self._new_block())

        current = block
        for i in range(len(arms)):
            current.terminator = MIRJump(arm_blocks[i].label)
            arm_result = self._lower_expr(arms[i].body, arm_blocks[i])
            if arm_blocks[i].terminator is None:
                arm_blocks[i].terminator = MIRJump(merge_block.label)
            current = arm_blocks[i]

        phi_sources = []
        for arm_block in arm_blocks:
            if arm_block.instructions:
                last_instr = arm_block.instructions[-1]
                phi_sources.append((arm_block.label, last_instr.result_name))

        merge_ssa = None
        if phi_sources:
            instr = MIRPhi(hir_expr.ir_type)
            instr.sources = phi_sources
            instr.result_name = self._new_ssa()
            merge_block.instructions.append(instr)
            merge_ssa = instr.result_name

        self.all_blocks.extend(arm_blocks + [merge_block])
        self.current_block = merge_block
        return merge_ssa

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
        header_block = MIRBasicBlock(self._new_block())
        body_block = MIRBasicBlock(self._new_block())
        exit_block = MIRBasicBlock(self._new_block())

        block.terminator = MIRJump(header_block.label)
        iter_ssa = self._lower_expr(hir_expr.iterable, header_block)
        header_block.terminator = MIRBranch(
            iter_ssa or "", body_block.label, exit_block.label
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

    def _lower_list_comprehension(self, hir_expr, block):
        """
        降级列表推导式：[result_expr | variable <- iterable, filter?]

        编译为以下结构：
          list = []               // 空列表
          header:                 // 循环头
            iter = iterable       // 获取迭代器（此处简化为直接判断 iterable）
            if iter goto body else goto exit
          body:
            // 可选 filter 检查
            // 计算 result_expr
            list = list_append(list, result)
            goto header
          exit:
            return list
        """
        header_block = MIRBasicBlock(self._new_block())
        body_block = MIRBasicBlock(self._new_block())
        exit_block = MIRBasicBlock(self._new_block())

        # 1. 在入口块创建空列表
        empty_list_instr = MIRListBuild(hir_expr.ir_type)
        empty_list_instr.elements = []
        list_ssa = self._emit(empty_list_instr)

        # 2. 跳转到循环头
        block.terminator = MIRJump(header_block.label)

        # 3. 循环头：降级可迭代对象，条件分支
        self.current_block = header_block
        iter_ssa = self._lower_expr(hir_expr.iterable, header_block)
        header_block.terminator = MIRBranch(
            iter_ssa or "", body_block.label, exit_block.label
        )

        # 压入循环上下文（break → exit, continue → header）
        self.loop_stack.append((header_block.label, exit_block.label))

        # 4. 循环体
        self.current_block = body_block

        # 将循环变量绑定到环境（简化：绑定到 iterable 本身，后续可迭代器化）
        self.env[hir_expr.variable] = iter_ssa or ""

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

            filter_block.terminator = MIRJump(header_block.label)

            # filter 为假：跳过，直接回到循环头
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

            if body_block.terminator is None:
                body_block.terminator = MIRJump(header_block.label)

        # 弹出循环上下文
        self.loop_stack.pop()

        # 5. exit 块：通过 Phi 合并列表值
        phi_sources = [
            (block.label, empty_list_instr.result_name),
            (header_block.label, list_ssa),
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
