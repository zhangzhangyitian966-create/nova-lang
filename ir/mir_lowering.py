"""
HIR -> MIR 降级器

将 HIR（High-Level IR）转换为 MIR（Mid-Level IR）—— SSA + CFG 形式。
这是编译管道的第二步。
"""

from .ir_nodes import (
    BOOL_TYPE,
    INT_TYPE,
    STRING_TYPE,
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
from .cfg_utils import replace_instr_operands, replace_terminator_operands


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
        self.ssa_types = {}  # SSA 名 -> 类型映射，用于 Phi 节点类型推断
        self.type_defs = {}  # ADT 类型定义
        # 表达式降级调度表：HIR 节点类型 -> 降级方法
        self._expr_lowerers = self._build_expr_lowerers()

    def _build_expr_lowerers(self):
        """构建表达式降级调度表

        将每种 HIR 节点类型映射到对应的降级方法，
        替代原来的 if-isinstance 链，降低圈复杂度。
        """
        return {
            HIRIntLiteral: self._lower_int_literal,
            HIRFloatLiteral: self._lower_float_literal,
            HIRStringLiteral: self._lower_string_literal,
            HIRBoolLiteral: self._lower_bool_literal,
            HIRCharLiteral: self._lower_char_literal,
            HIRUnitLiteral: self._lower_unit_literal,
            HIRIdentifier: self._lower_identifier,
            HIRBinaryOp: self._lower_binary_op,
            HIRUnaryOp: self._lower_unary_op,
            HIRCallExpr: self._lower_call_expr,
            HIRIfExpr: self._lower_if_expr,
            HIRMatchExpr: self._lower_match_expr,
            HIRBlockExpr: self._lower_block_expr,
            HIRListExpr: self._lower_list_expr,
            HIRTupleExpr: self._lower_tuple_expr,
            HIRMapExpr: self._lower_map_expr,
            HIRFieldExpr: self._lower_field_expr,
            HIRIndexExpr: self._lower_index_expr,
            HIRLambda: self._lower_lambda,
            HIRPipeExpr: self._lower_pipe_expr,
            HIRForExpr: self._lower_for_expr,
            HIRWhileExpr: self._lower_while_expr,
            HIRBreakExpr: self._lower_break_expr,
            HIRContinueExpr: self._lower_continue_expr,
            HIRAssignExpr: self._lower_assign_expr,
            HIRListComprehension: self._lower_list_comprehension,
            HIRADTConstructor: self._lower_adt_constructor,
            HIRUnwrapExpr: self._lower_unwrap_expr,
        }

    def lower(self, hir_module):
        mir_module = MIRModule(name=hir_module.name)
        mir_module.type_defs = hir_module.type_defs
        self.type_defs = hir_module.type_defs

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
        # 记录 SSA 类型，用于 Phi 节点等的类型推断
        self.ssa_types[ssa] = instr.result_type
        return ssa

    def _replace_ssa_in_block(self, block, old_ssa, new_ssa, skip_phi=False):
        """
        替换一个基本块中所有的 SSA 引用。
        skip_phi=True 时不替换 Phi 节点（用于替换 Phi 之前的引用）。

        使用 cfg_utils 中的统一操作数替换 API，
        消除与 pass_manager.py 的重复代码。
        """
        replacements = {old_ssa: new_ssa}
        for instr in block.instructions:
            if skip_phi and hasattr(instr, "sources"):
                continue
            replace_instr_operands(instr, replacements)
        replace_terminator_operands(block.terminator, replacements)

    def _lower_function(self, hir_fn):
        self.ssa_counter = 0
        self.block_counter = 0
        self.env = {}
        self.all_blocks = []
        self.ssa_types = {}

        mir_fn = MIRFunction(hir_fn.name, [], hir_fn.return_type)

        entry = MIRBasicBlock("bb0")
        self.current_block = entry
        self.current_function = mir_fn

        param_list = []
        for i, (name, ty) in enumerate(hir_fn.params):
            ssa_name = self._new_ssa()
            param_list.append((name, ty, ssa_name))
            self.env[name] = ssa_name
            self.ssa_types[ssa_name] = ty

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

        # 调度表分发：根据 HIR 节点类型查找对应的降级方法
        lower_fn = self._expr_lowerers.get(type(hir_expr))
        if lower_fn:
            return lower_fn(hir_expr, block)

        return None

    # === 字面量类 ===

    def _lower_int_literal(self, hir_expr, block):
        instr = MIRConst(hir_expr.ir_type)
        instr.value = hir_expr.value
        instr.const_type = "int"
        return self._emit(instr)

    def _lower_float_literal(self, hir_expr, block):
        instr = MIRConst(hir_expr.ir_type)
        instr.value = hir_expr.value
        instr.const_type = "float"
        return self._emit(instr)

    def _lower_string_literal(self, hir_expr, block):
        instr = MIRConst(hir_expr.ir_type)
        instr.value = hir_expr.value
        instr.const_type = "string"
        return self._emit(instr)

    def _lower_bool_literal(self, hir_expr, block):
        instr = MIRConst(hir_expr.ir_type)
        instr.value = hir_expr.value
        instr.const_type = "bool"
        return self._emit(instr)

    def _lower_char_literal(self, hir_expr, block):
        instr = MIRConst(hir_expr.ir_type)
        instr.value = hir_expr.value
        instr.const_type = "char"
        return self._emit(instr)

    def _lower_unit_literal(self, hir_expr, block):
        instr = MIRConst(hir_expr.ir_type)
        instr.value = None
        instr.const_type = "unit"
        return self._emit(instr)

    # === 标识符 ===

    def _lower_identifier(self, hir_expr, block):
        if hir_expr.name in self.env:
            return self.env[hir_expr.name]
        return None

    # === 运算类 ===

    def _lower_binary_op(self, hir_expr, block):
        left_ssa = self._lower_expr(hir_expr.left, block)
        right_ssa = self._lower_expr(hir_expr.right, block)
        instr = MIRBinOp(hir_expr.ir_type)
        instr.op = hir_expr.op
        instr.left = left_ssa or ""
        instr.right = right_ssa or ""
        return self._emit(instr)

    def _lower_unary_op(self, hir_expr, block):
        operand_ssa = self._lower_expr(hir_expr.operand, block)
        instr = MIRUnaryOp(hir_expr.ir_type)
        instr.op = hir_expr.op
        instr.operand = operand_ssa or ""
        return self._emit(instr)

    # === 函数调用 ===

    def _lower_call_expr(self, hir_expr, block):
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

    # === 控制流（调用已有的独立方法） ===

    # _lower_if_expr 已在下方定义
    # _lower_match_expr 已在下方定义

    def _lower_block_expr(self, hir_expr, block):
        result = None
        for expr in hir_expr.exprs:
            result = self._lower_expr(expr, block)
        return result

    # === 数据结构构建 ===

    def _lower_list_expr(self, hir_expr, block):
        elem_ssas = []
        for elem in hir_expr.elements:
            elem_ssas.append(self._lower_expr(elem, block) or "")
        instr = MIRListBuild(hir_expr.ir_type)
        instr.elements = elem_ssas
        return self._emit(instr)

    def _lower_tuple_expr(self, hir_expr, block):
        elem_ssas = []
        for elem in hir_expr.elements:
            elem_ssas.append(self._lower_expr(elem, block) or "")
        instr = MIRTupleBuild(hir_expr.ir_type)
        instr.elements = elem_ssas
        return self._emit(instr)

    def _lower_map_expr(self, hir_expr, block):
        entry_ssas = []
        for key_expr, val_expr in hir_expr.entries:
            key_ssa = self._lower_expr(key_expr, block)
            val_ssa = self._lower_expr(val_expr, block)
            entry_ssas.append((key_ssa or "", val_ssa or ""))
        instr = MIRMapBuild(hir_expr.ir_type)
        instr.entries = entry_ssas
        return self._emit(instr)

    # === 访问类 ===

    def _lower_field_expr(self, hir_expr, block):
        obj_ssa = self._lower_expr(hir_expr.object, block)
        instr = MIRFieldAccess(hir_expr.ir_type)
        instr.object = obj_ssa or ""
        instr.field_name = hir_expr.field_name
        return self._emit(instr)

    def _lower_index_expr(self, hir_expr, block):
        obj_ssa = self._lower_expr(hir_expr.object, block)
        idx_ssa = self._lower_expr(hir_expr.index, block)
        instr = MIRIndexAccess(hir_expr.ir_type)
        instr.object = obj_ssa or ""
        instr.index = idx_ssa or ""
        return self._emit(instr)

    # === Lambda ===

    def _lower_lambda(self, hir_expr, block):
        instr = MIRClosureCreate(hir_expr.ir_type)
        instr.fn_name = "<lambda_%d>" % self.ssa_counter
        return self._emit(instr)

    # === 循环与控制流（调用已有的独立方法） ===

    # _lower_pipe_expr 已在下方定义
    # _lower_for_expr 已在下方定义
    # _lower_while_expr 已在下方定义

    def _lower_break_expr(self, hir_expr, block):
        if self.loop_stack:
            _, exit_label = self.loop_stack[-1]
            block.terminator = MIRJump(exit_label)
        else:
            # 不在循环内的 break → 降级为 panic
            block.terminator = MIRPanic("break outside loop")
        return None

    def _lower_continue_expr(self, hir_expr, block):
        if self.loop_stack:
            header_label, _ = self.loop_stack[-1]
            block.terminator = MIRJump(header_label)
        else:
            # 不在循环内的 continue → 降级为 panic
            block.terminator = MIRPanic("continue outside loop")
        return None

    # === 赋值 ===

    def _lower_assign_expr(self, hir_expr, block):
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

    # === 列表推导式（调用已有的独立方法） ===

    # _lower_list_comprehension 已在下方定义

    # === ADT ===

    def _lower_adt_constructor(self, hir_expr, block):
        field_ssas = [self._lower_expr(f, block) or "" for f in hir_expr.fields]
        instr = MIRADTBuild(hir_expr.ir_type)
        instr.type_name = hir_expr.type_name
        instr.variant_name = hir_expr.variant_name
        instr.fields = field_ssas
        return self._emit(instr)

    # === Unwrap ===

    def _lower_unwrap_expr(self, hir_expr, block):
        operand_ssa = self._lower_expr(hir_expr.operand, block)
        instr = MIRFieldAccess(hir_expr.ir_type)
        instr.object = operand_ssa or ""
        instr.field_name = "value"
        instr.field_index = 0
        return self._emit(instr)

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
                # 从第一个 source 的 SSA 类型推断 Phi 类型（SSA 保证所有来源类型一致）
                phi_type = UNIT_TYPE
                for _, src_ssa in phi_sources:
                    if src_ssa in self.ssa_types:
                        phi_type = self.ssa_types[src_ssa]
                        break
                instr = MIRPhi(phi_type)
                instr.sources = phi_sources
                instr.result_name = self._new_ssa()
                merge_block.instructions.append(instr)
                self.env[name] = instr.result_name
                self.ssa_types[instr.result_name] = phi_type

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
                # 从第一个 source 的 SSA 类型推断 Phi 类型
                phi_type = UNIT_TYPE
                for _, src_ssa in phi_sources:
                    if src_ssa in self.ssa_types:
                        phi_type = self.ssa_types[src_ssa]
                        break
                instr = MIRPhi(phi_type)
                instr.sources = phi_sources
                instr.result_name = self._new_ssa()
                merge_block.instructions.append(instr)
                self.env[name] = instr.result_name
                self.ssa_types[instr.result_name] = phi_type

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
        from .ir_nodes import (
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

            cmp_instr = MIRBinOp(BOOL_TYPE)  # 比较结果为布尔类型
            cmp_instr.op = "=="
            cmp_instr.left = value_ssa
            cmp_instr.right = const_ssa
            cmp_ssa = self._emit(cmp_instr)

            block.terminator = MIRBranch(cmp_ssa, match_target, fail_target)
            return

        if isinstance(pattern, HIRConstructorPattern):
            # 构造器模式：比较 variant tag，匹配成功后递归绑定字段
            # 1. 先比较 variant 名称（通过 ADT 标签访问）
            tag_instr = MIRFieldAccess(STRING_TYPE)  # tag 是 variant 名称（字符串）
            tag_instr.object = value_ssa
            tag_instr.field_name = "tag"
            tag_instr.field_index = 0
            tag_ssa = self._emit(tag_instr)

            # 生成 variant 名常量做比较
            tag_const = MIRConst(STRING_TYPE)
            tag_const.value = pattern.variant_name
            tag_const.const_type = "string"
            tag_const_ssa = self._emit(tag_const)

            tag_cmp = MIRBinOp(BOOL_TYPE)  # 比较结果为布尔类型
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

                # 从 ADT 定义中查找字段类型
                field_type = UNIT_TYPE
                if pattern.type_name in self.type_defs:
                    td = self.type_defs[pattern.type_name]
                    for variant in td.variants:
                        if variant.name == pattern.variant_name:
                            if j < len(variant.fields):
                                field_type = variant.fields[j][1]
                            break

                # 提取字段值
                field_instr = MIRFieldAccess(field_type)
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
            phi_x = phi(entry: x_init, body: x_next)  // 循环中被修改的变量
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

        SSA 策略（与 while 循环一致）：
        1. 进入循环前保存 env 快照（pre_env）
        2. 处理完循环体后，比较 env 找出被修改的变量
        3. 在 header 块开头为每个被修改的变量插入 Phi 节点
        4. Phi 的 sources: 入口边(pre值) + 回边(body末尾的值)
        5. 替换 header 和 body 中对这些变量的引用为 Phi 结果
        """
        header_block = MIRBasicBlock(self._new_block())
        body_block = MIRBasicBlock(self._new_block())
        exit_block = MIRBasicBlock(self._new_block())

        # 在入口块计算可迭代对象和长度
        iter_ssa = self._lower_expr(hir_expr.iterable, block)

        # 调用 list_length 获取长度
        len_instr = MIRCall(INT_TYPE)  # list_length 返回整数
        len_instr.callee = "list_length"
        len_instr.args = [iter_ssa or ""]
        len_ssa = self._emit(len_instr)

        # 索引变量初始值 0
        idx_init_instr = MIRConst(INT_TYPE)  # 索引是整数
        idx_init_instr.value = 0
        idx_init_instr.const_type = "int"
        idx_init_ssa = self._emit(idx_init_instr)

        # 1. 进入循环前保存 env 快照
        pre_env = dict(self.env)

        # 跳转到循环头
        block.terminator = MIRJump(header_block.label)

        # --- 循环头：Phi 节点 + 条件判断 ---
        self.current_block = header_block

        # 索引变量的 Phi（先占位，body 处理完后补充 source）
        idx_phi = MIRPhi(INT_TYPE)  # 索引是整数类型
        idx_phi.result_name = self._new_ssa()
        idx_phi.sources = []  # 稍后填充
        header_block.instructions.append(idx_phi)
        idx_phi_ssa = idx_phi.result_name
        self.ssa_types[idx_phi_ssa] = INT_TYPE

        # 比较 i < len
        cmp_instr = MIRBinOp(BOOL_TYPE)  # 比较结果为布尔类型
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
        # 元素类型从可迭代对象的列表类型中提取
        elem_type = UNIT_TYPE
        iter_type = hir_expr.iterable.ir_type
        if iter_type.kind.name == "LIST" and iter_type.params:
            elem_type = iter_type.params[0]
        get_instr = MIRCall(elem_type)
        get_instr.callee = "list_get"
        get_instr.args = [iter_ssa or "", idx_phi_ssa]
        elem_ssa = self._emit(get_instr)

        # 绑定循环变量到当前元素
        self.env[hir_expr.variable] = elem_ssa

        self._lower_expr(hir_expr.body, body_block)

        # 索引递增: i = i + 1
        inc_instr = MIRBinOp(INT_TYPE)  # 索引递增结果为整数
        inc_instr.op = "+"
        inc_instr.left = idx_phi_ssa
        inc_right = MIRConst(INT_TYPE)  # 常量 1 是整数
        inc_right.value = 1
        inc_right.const_type = "int"
        inc_right_ssa = self._emit(inc_right)
        inc_instr.right = inc_right_ssa
        inc_ssa = self._emit(inc_instr)

        if body_block.terminator is None:
            body_block.terminator = MIRJump(header_block.label)

        # 弹出循环上下文
        self.loop_stack.pop()

        # 2. 使用通用方法插入循环 Phi 节点
        latch_blocks = [(body_block, dict(self.env))]
        phi_results = self._insert_loop_phis(
            pre_env=pre_env,
            entry_block_label=block.label,
            header_block=header_block,
            latch_blocks=latch_blocks,
            phi_offset=1,  # idx_phi 在位置 0
            exclude_vars={hir_expr.variable},
        )

        # 更新 env 中的值为 Phi 结果
        for var_name, phi_result in phi_results.items():
            self.env[var_name] = phi_result

        # 填充 idx_phi 的 sources
        idx_phi.sources = [
            (block.label, idx_init_ssa),
            (body_block.label, inc_ssa),
        ]

        self.all_blocks.extend([header_block, body_block, exit_block])
        self.current_block = exit_block
        return None

    def _insert_loop_phis(
        self,
        pre_env,
        entry_block_label,
        header_block,
        latch_blocks,
        phi_offset=0,
        exclude_vars=None,
    ):
        """
        循环 SSA Phi 插入通用方法。

        为循环中被修改的变量在 header 块开头插入 Phi 节点，
        并替换 header 和所有 latch 块中的旧 SSA 引用。

        参数:
            pre_env: 循环前的 env 快照（dict: var_name -> ssa_name）
            entry_block_label: 循环入口块的标签（Phi 入口边的来源）
            header_block: 循环头基本块（MIRBasicBlock）
            latch_blocks: 回边块列表，每个元素为 (block_obj, latch_env_dict)
                - block_obj: MIRBasicBlock，该回边的基本块
                - latch_env_dict: dict，该回边路径末尾的 env 快照
            phi_offset: 在 header_block.instructions 中插入 Phi 的起始偏移
            exclude_vars: 排除的变量名集合（如循环变量，不参与 Phi 插入）

        返回:
            dict: {var_name: phi_result_ssa}，更新后的变量到 Phi 结果的映射

        副作用:
            - 在 header_block 中插入 Phi 节点
            - 替换 header 和所有 latch 块中的旧 SSA 引用
            - 更新 self.ssa_types
        """
        if exclude_vars is None:
            exclude_vars = set()

        # 1. 找出所有回边中被修改的变量
        modified_vars = set()
        for _, latch_env in latch_blocks:
            for name, ssa_val in latch_env.items():
                if name in exclude_vars:
                    continue
                pre_ssa = pre_env.get(name)
                if pre_ssa is None or pre_ssa != ssa_val:
                    modified_vars.add(name)

        # 2. 在 header 块开头为每个被修改的变量插入 Phi 节点
        current_offset = phi_offset
        phi_results = {}  # var_name -> phi_result_ssa

        for var_name in modified_vars:
            pre_ssa = pre_env.get(var_name)
            if pre_ssa is None:
                # 循环中新定义的变量，入口边没有值，跳过
                continue

            # 从入口边的 SSA 类型推断 Phi 类型
            phi_type = UNIT_TYPE
            if pre_ssa in self.ssa_types:
                phi_type = self.ssa_types[pre_ssa]

            phi_instr = MIRPhi(phi_type)
            # 收集所有 source：入口边 + 所有回边
            phi_sources = [(entry_block_label, pre_ssa)]  # 入口边
            for latch_block, latch_env in latch_blocks:
                latch_ssa = latch_env.get(var_name, pre_ssa)
                phi_sources.append((latch_block.label, latch_ssa))
            phi_instr.sources = phi_sources
            phi_instr.result_name = self._new_ssa()
            header_block.instructions.insert(current_offset, phi_instr)
            current_offset += 1
            self.ssa_types[phi_instr.result_name] = phi_type

            phi_result = phi_instr.result_name
            phi_results[var_name] = phi_result

            # 3. 替换 header 和所有 latch 块中对旧 SSA 的引用为 Phi 结果
            # header 中替换（跳过 Phi 节点自身）
            self._replace_ssa_in_block(header_block, pre_ssa, phi_result, skip_phi=True)
            # 所有 latch 块中替换
            for latch_block, _ in latch_blocks:
                self._replace_ssa_in_block(latch_block, pre_ssa, phi_result, skip_phi=False)

        return phi_results

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
            phi_x = phi(...)           // 循环中被修改的变量
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

        SSA 策略（与 while 循环/for 循环一致）：
        1. 进入循环前保存 env 快照（pre_env）
        2. 处理完循环体后，比较 env 找出被修改的变量
        3. 在 header 块开头为每个被修改的变量插入 Phi 节点
        4. Phi 的 sources: 入口边(pre值) + 所有回边(latch块的值)
        5. 替换 header 和 body 中对这些变量的引用为 Phi 结果
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
        len_instr = MIRCall(INT_TYPE)  # list_length 返回整数
        len_instr.callee = "list_length"
        len_instr.args = [iter_ssa or ""]
        len_ssa = self._emit(len_instr)

        # 索引变量初始值 0
        idx_init_instr = MIRConst(INT_TYPE)  # 索引是整数
        idx_init_instr.value = 0
        idx_init_instr.const_type = "int"
        idx_init_ssa = self._emit(idx_init_instr)

        # 进入循环前保存 env 快照
        pre_env = dict(self.env)

        # 2. 跳转到循环头
        block.terminator = MIRJump(header_block.label)

        # 3. 循环头：Phi 节点 + 条件分支
        self.current_block = header_block

        # 索引 Phi（先占位，稍后填充 sources）
        idx_phi = MIRPhi(INT_TYPE)  # 索引是整数类型
        idx_phi.result_name = self._new_ssa()
        idx_phi.sources = []
        header_block.instructions.append(idx_phi)
        idx_phi_ssa = idx_phi.result_name
        self.ssa_types[idx_phi_ssa] = INT_TYPE

        # 列表 Phi（循环携带的列表值）
        list_phi = MIRPhi(hir_expr.ir_type)
        list_phi.result_name = self._new_ssa()
        list_phi.sources = []
        header_block.instructions.append(list_phi)
        list_phi_ssa = list_phi.result_name
        self.ssa_types[list_phi_ssa] = hir_expr.ir_type

        # 比较 i < len
        cmp_instr = MIRBinOp(BOOL_TYPE)  # 比较结果为布尔类型
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
        # 元素类型从可迭代对象的列表类型中提取
        elem_type = UNIT_TYPE
        iter_type = hir_expr.iterable.ir_type
        if iter_type.kind.name == "LIST" and iter_type.params:
            elem_type = iter_type.params[0]
        get_instr = MIRCall(elem_type)
        get_instr.callee = "list_get"
        get_instr.args = [iter_ssa or "", idx_phi_ssa]
        elem_ssa = self._emit(get_instr)

        # 绑定循环变量到当前元素
        self.env[hir_expr.variable] = elem_ssa

        # 收集所有回边块及其对应的值
        # latch_blocks: [(block_obj, {var_name: ssa_val}), ...]
        latch_blocks = []
        # 每个 latch 块对应的索引递增 SSA 和列表值 SSA
        latch_inc_ssas = []
        latch_list_ssas = []

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
            inc_instr_t = MIRBinOp(INT_TYPE)  # 索引递增结果为整数
            inc_instr_t.op = "+"
            inc_instr_t.left = idx_phi_ssa
            inc_const_t = MIRConst(INT_TYPE)  # 常量 1 是整数
            inc_const_t.value = 1
            inc_const_t.const_type = "int"
            inc_const_ssa_t = self._emit(inc_const_t)
            inc_instr_t.right = inc_const_ssa_t
            inc_ssa_t = self._emit(inc_instr_t)

            filter_block.terminator = MIRJump(header_block.label)

            # 记录 filter_true 分支
            latch_blocks.append((filter_block, dict(self.env)))
            latch_inc_ssas.append(inc_ssa_t)
            latch_list_ssas.append(new_list_ssa)

            # --- filter 为假：跳过 append，索引仍然递增 ---
            self.current_block = filter_false_block

            inc_instr_f = MIRBinOp(INT_TYPE)  # 索引递增结果为整数
            inc_instr_f.op = "+"
            inc_instr_f.left = idx_phi_ssa
            inc_const_f = MIRConst(INT_TYPE)  # 常量 1 是整数
            inc_const_f.value = 1
            inc_const_f.const_type = "int"
            inc_const_ssa_f = self._emit(inc_const_f)
            inc_instr_f.right = inc_const_ssa_f
            inc_ssa_f = self._emit(inc_instr_f)

            filter_false_block.terminator = MIRJump(header_block.label)

            self.all_blocks.extend([filter_block, filter_false_block])

            # 记录 filter_false 分支
            latch_blocks.append((filter_false_block, dict(self.env)))
            latch_inc_ssas.append(inc_ssa_f)
            latch_list_ssas.append(list_phi_ssa)
        else:
            # 无 filter：直接计算 result_expr 并 append
            result_ssa = self._lower_expr(hir_expr.result_expr, body_block)

            append_instr = MIRListAppend(hir_expr.ir_type)
            append_instr.list_ssa = list_phi_ssa
            append_instr.element_ssa = result_ssa or ""
            new_list_ssa = self._emit(append_instr)

            # 索引递增
            inc_instr = MIRBinOp(INT_TYPE)  # 索引递增结果为整数
            inc_instr.op = "+"
            inc_instr.left = idx_phi_ssa
            inc_const = MIRConst(INT_TYPE)  # 常量 1 是整数
            inc_const.value = 1
            inc_const.const_type = "int"
            inc_const_ssa = self._emit(inc_const)
            inc_instr.right = inc_const_ssa
            inc_ssa = self._emit(inc_instr)

            if body_block.terminator is None:
                body_block.terminator = MIRJump(header_block.label)

            # 记录 body 分支
            latch_blocks.append((body_block, dict(self.env)))
            latch_inc_ssas.append(inc_ssa)
            latch_list_ssas.append(new_list_ssa)

        # 弹出循环上下文
        self.loop_stack.pop()

        # 5. 使用通用方法插入循环 Phi 节点
        phi_results = self._insert_loop_phis(
            pre_env=pre_env,
            entry_block_label=block.label,
            header_block=header_block,
            latch_blocks=latch_blocks,
            phi_offset=2,  # idx_phi 在 0，list_phi 在 1
            exclude_vars={hir_expr.variable},
        )

        # 更新 env 中的值为 Phi 结果
        for var_name, phi_result in phi_results.items():
            self.env[var_name] = phi_result

        # 填充 idx_phi 的 sources
        idx_phi_sources = [(block.label, idx_init_ssa)]
        for (latch_block, _), inc_ssa_val in zip(latch_blocks, latch_inc_ssas):
            idx_phi_sources.append((latch_block.label, inc_ssa_val))
        idx_phi.sources = idx_phi_sources

        # 填充 list_phi 的 sources
        list_phi_sources = [(block.label, list_init_ssa)]
        for (latch_block, _), list_val_ssa in zip(latch_blocks, latch_list_ssas):
            list_phi_sources.append((latch_block.label, list_val_ssa))
        list_phi.sources = list_phi_sources

        # 6. exit 块：列表 Phi 的值就是结果
        # 结果值就是 list_phi_ssa（header 中的 Phi）。
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

        # 4. 使用通用方法插入循环 Phi 节点
        latch_blocks = [(body_block, dict(self.env))]
        phi_results = self._insert_loop_phis(
            pre_env=pre_env,
            entry_block_label=block.label,
            header_block=header_block,
            latch_blocks=latch_blocks,
            phi_offset=0,
            exclude_vars=set(),
        )

        # 更新 env 中的值为 Phi 结果
        for var_name, phi_result in phi_results.items():
            self.env[var_name] = phi_result

        self.all_blocks.extend([header_block, body_block, exit_block])
        self.current_block = exit_block
        return None
