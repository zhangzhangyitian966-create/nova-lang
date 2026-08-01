"""
HIR -> MIR 降级器

将 HIR（High-Level IR）转换为 MIR（Mid-Level IR）—— SSA + CFG 形式。
这是编译管道的第二步。
"""

from typing import Optional

from .ir_nodes import (
    BOOL_TYPE,
    INT_TYPE,
    IRType,
    NovaType,
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
    HIRFunction,
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
    _iter_hir_children,
)
from .cfg_utils import replace_instr_operands, replace_terminator_operands


# ---------------------------------------------------------------------------
# Phi 节点类型一致性（code_audit_60 P1-4 修复）
# ---------------------------------------------------------------------------

def _ir_types_compatible(t1: NovaType, t2: NovaType) -> bool:
    """MIR 层轻量级类型兼容检查（不依赖前端 TypeChecker，避免循环引入。

    判定规则（宽容策略，保证不出现假阳性）：
    1. 结构完全相等（NovaType __eq__）→ 兼容
    2. 任一方为 UNIT（找不到类型的占位）→ 视为兼容（保持原 UNIT fallback 语义）
    3. 任一方为 TYPE_VAR（泛型实例化残留类型变量）→ 视为兼容（保持宽容性）
    4. kind 不同（如 INT vs FLOAT / STRING vs BOOL）→ 不兼容（正确性核心判定）
    5. 参数化类型（LIST / MAP / TUPLE / FUNCTION / ADT）：
       - params 长度不同 → 不兼容
       - ADT 要求 name 相同 → 否则不兼容
       - 递归逐对 params 验证
    6. PTR（LIR 层低级指针）→ 视为与任意 PTR 兼容（LIR 层不追具体类型）

    返回 True 表示"在 MIR 层可以安全共用同一 Phi 槽位。
    """
    if t1 == t2:
        return True
    # UNIT 占位宽容：任一为找不到类型时的 fallback
    if t1.kind == IRType.UNIT or t2.kind == IRType.UNIT:
        return True
    # TYPE_VAR 宽容：泛型实例化未完全的类型变量
    if t1.kind == IRType.TYPE_VAR or t2.kind == IRType.TYPE_VAR:
        return True
    # PTR 宽容：LIR 层指针不追具体指向类型
    if t1.kind == IRType.PTR or t2.kind == IRType.PTR:
        return t1.kind == t2.kind
    # kind 严格不同 → 不兼容
    if t1.kind != t2.kind:
        return False
    # 参数化类型递归校验
    if len(t1.params) != len(t2.params):
        return False
    if t1.kind == IRType.ADT and t1.name != t2.name:
        return False
    return all(_ir_types_compatible(p1, p2) for p1, p2 in zip(t1.params, t2.params))


class MIRLoweringError(Exception):
    """HIR -> MIR 降级过程中的错误"""
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
        self.lambda_functions = {}  # 收集 lambda 生成的独立 MIRFunction
        # 表达式降级调度表：HIR 节点类型 -> 降级方法
        self._expr_lowerers = self._build_expr_lowerers()
        # 自由变量收集调度表：HIR 节点类型 -> 收集方法
        self._collect_dispatch = self._build_collect_dispatch()

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

    def _build_collect_dispatch(self):
        """构建自由变量收集调度表

        将引入新绑定的 HIR 节点类型映射到专属收集方法，
        替代 _collect_idents 中的 isinstance 链，降低圈复杂度。
        """
        return {
            HIRIdentifier: self._collect_ident_ref,
            HIRLetDecl: self._collect_let,
            HIRBlockExpr: self._collect_block,
            HIRLambda: self._collect_lambda_idents,
            HIRForExpr: self._collect_for,
            HIRListComprehension: self._collect_listcomp,
            HIRMatchExpr: self._collect_match,
        }

    def lower(self, hir_module):
        """将 HIR 模块降级为 MIR 模块。

        遍历 HIR 模块中的声明，将顶层 let 绑定转为 MIR 全局变量，
        将函数定义降级为 MIR 函数（基本块 + SSA 指令）。

        参数:
            hir_module: HIRModule 实例

        返回:
            MIRModule 实例
        """
        mir_module = MIRModule(name=hir_module.name)
        mir_module.type_defs = hir_module.type_defs
        self.type_defs = hir_module.type_defs
        self.lambda_functions = {}  # 重置 lambda 函数收集器

        # 预扫描：收集所有函数的显式返回类型（供调用点类型推断使用）
        # 对于带显式返回类型注解的函数，此处即可获取到具体类型；
        # 无注解的函数在 _lower_function 完成后会回填推断结果。
        self.functions = {}
        for decl in hir_module.declarations:
            if isinstance(decl, HIRFnDecl):
                self.functions[decl.fn_def.name] = decl.fn_def.return_type

        for decl in hir_module.declarations:
            if isinstance(decl, HIRLetDecl):
                mir_module.globals[decl.name] = MIRGlobal(
                    decl.name, decl.ir_type, is_mutable=decl.is_mutable
                )
            elif isinstance(decl, HIRFnDecl):
                mir_fn = self._lower_function(decl.fn_def)
                # 回填推断后的返回类型（处理无注解函数）
                self.functions[decl.fn_def.name] = mir_fn.return_type
                mir_module.functions[decl.fn_def.name] = mir_fn

        # 注册所有 lambda 函数到模块（编译过程中收集的）
        for name, fn in self.lambda_functions.items():
            mir_module.functions[name] = fn

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

    def _emit_idx_increment(self, idx_ssa: str) -> str:
        """生成索引自增指令 ``idx_ssa + 1``，返回结果 SSA 名。

        从 :meth:`_lower_list_comprehension` 三处重复的索引递增代码
        （filter_true / filter_false / 无filter 分支）中提取，
        原单处 8 行 → 调用 1 行，三处合计消除约 21 行重复代码并降低圈复杂度。

        :param idx_ssa: 要递增的索引 SSA 名（类型为 INT_TYPE）
        :return: 递增结果的 SSA 名（INT_TYPE）
        """
        inc_instr = MIRBinOp(INT_TYPE)
        inc_instr.op = "+"
        inc_instr.left = idx_ssa
        inc_const = MIRConst(INT_TYPE)
        inc_const.value = 1
        inc_const.const_type = "int"
        inc_const_ssa = self._emit(inc_const)
        inc_instr.right = inc_const_ssa
        return self._emit(inc_instr)

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
        self.block_counter = 1  # 入口块是 bb0，新块从 bb1 开始
        self.env = {}
        self.all_blocks = []
        self.ssa_types = {}

        mir_fn = MIRFunction(hir_fn.name, [], hir_fn.return_type)
        # 动态属性：Phi 类型不一致计数器、标记位等（不修改 MIRFunction dataclass，保持跨模块兼容）
        mir_fn.annotation = {}

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

        # 函数体降级后，当前块（可能不是 entry）如果没有终止符，
        # 需要添加隐式 return 返回函数体结果值。
        # 这在 if/then/else、match 等表达式作为函数尾表达式时发生。
        if self.current_block.terminator is None:
            self.current_block.terminator = MIRReturn(result_ssa)
        elif entry.terminator is None:
            # entry 本身没有终止符（简单表达式函数体）
            entry.terminator = MIRReturn(result_ssa)

        # 如果函数返回类型未指定（TYPE_VAR），从函数体结果推断
        if mir_fn.return_type.kind == IRType.TYPE_VAR and result_ssa:
            inferred = self.ssa_types.get(result_ssa)
            if inferred and inferred.kind != IRType.TYPE_VAR:
                mir_fn.return_type = inferred

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

    def _infer_binop_type(self, left_ssa: str, right_ssa: str, op: str) -> NovaType:
        """根据操作数 SSA 类型推断二元运算结果类型

        如果操作数类型已知且一致，返回对应类型；
        否则返回 TYPE_VAR 占位。
        """
        left_ty = self.ssa_types.get(left_ssa)
        right_ty = self.ssa_types.get(right_ssa)
        if left_ty and right_ty and left_ty.kind == right_ty.kind:
            # 算术/比较/按位运算保持操作数类型
            if op in ("+", "-", "*", "/", "%", "==", "!=", "<", ">", "<=", ">=", "&&", "||",
                       "&", "|", "^", "<<", ">>", ">>>"):
                return left_ty
        return NovaType(IRType.TYPE_VAR)

    def _lower_binary_op(self, hir_expr, block):
        left_ssa = self._lower_expr(hir_expr.left, block)
        right_ssa = self._lower_expr(hir_expr.right, block)
        # 优先从操作数类型推断结果类型，HIR 中的 ir_type 可能仍是 TYPE_VAR
        result_ty = self._infer_binop_type(left_ssa, right_ssa, hir_expr.op)
        if result_ty.kind == IRType.TYPE_VAR:
            result_ty = hir_expr.ir_type
        instr = MIRBinOp(result_ty)
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

    def _infer_call_return_type(self, callee_ssa, default_ty):
        """从 callee 的 SSA 类型推断调用返回类型。

        如果 callee 的类型是函数类型（IRType.FUNCTION），
        则 params[-1] 是返回类型；否则回退到 default_ty。

        参数:
            callee_ssa: callee 的 SSA 名（用于查 ssa_types）
            default_ty: 无法推断时的回退类型

        返回:
            NovaType: 推断出的返回类型
        """
        callee_ty = self.ssa_types.get(callee_ssa)
        if callee_ty and callee_ty.kind == IRType.FUNCTION and callee_ty.params:
            # 函数类型的 params[-1] 是返回类型
            return callee_ty.params[-1]
        return default_ty

    def _lower_call_expr(self, hir_expr, block):
        """降级函数调用表达式。

        根据 callee 形态推断调用结果类型：
        - 直接调用（callee 是函数名字符串）：从 self.functions 查返回类型
        - 闭包调用（callee 是 SSA 值）：从 callee 的函数类型 params[-1] 取返回类型
        - 无法确定时回退到 hir_expr.ir_type（可能仍是 TYPE_VAR）
        """
        arg_ssas = []
        for arg in hir_expr.arguments:
            arg_ssa = self._lower_expr(arg, block)
            arg_ssas.append(arg_ssa or "")

        # 推断调用结果类型（替代直接使用 hir_expr.ir_type，后者始终是 TYPE_VAR）
        result_ty = hir_expr.ir_type

        if isinstance(hir_expr.function, HIRIdentifier):
            name = hir_expr.function.name
            # 判断是函数名（直接调用）还是变量（如闭包，间接调用）
            if name in self.env:
                # 变量（闭包）-> 使用 SSA 值，间接调用
                callee_ssa = self.env[name]
                instr_callee = callee_ssa
                # 从闭包 SSA 类型推断返回类型
                result_ty = self._infer_call_return_type(callee_ssa, result_ty)
            else:
                # 函数名 -> 使用字符串，直接调用
                instr_callee = name
                # 从函数表查返回类型
                fn_ret = self.functions.get(name)
                if fn_ret and fn_ret.kind != IRType.TYPE_VAR:
                    result_ty = fn_ret
        else:
            func_ssa = self._lower_expr(hir_expr.function, block)
            instr_callee = func_ssa or ""
            # 从 callee SSA 类型推断返回类型
            result_ty = self._infer_call_return_type(func_ssa, result_ty)

        instr = MIRCall(result_ty)
        instr.callee = instr_callee
        instr.args = arg_ssas
        return self._emit(instr)

    # === 控制流（调用已有的独立方法） ===

    # _lower_if_expr 已在下方定义
    # _lower_match_expr 已在下方定义

    def _lower_block_expr(self, hir_expr, block):
        """
        降级代码块表达式。

        处理块中的表达式和声明（如 HIRLetDecl），
        返回最后一个表达式的结果 SSA 名。
        正确处理控制流：每个表达式降级后，后续表达式在当前块继续。
        """
        result = None
        current_block = block
        for expr in hir_expr.exprs:
            if isinstance(expr, HIRLetDecl):
                # 处理 let 绑定声明
                value_ssa = self._lower_expr(expr.value, current_block)
                if value_ssa:
                    self.env[expr.name] = value_ssa
                    # 仅当声明有更具体的类型注解时才覆盖
                    # 避免用 TYPE_VAR 覆盖 _lower_call_expr 已推断的具体类型
                    existing_ty = self.ssa_types.get(value_ssa)
                    if (expr.ir_type.kind != IRType.TYPE_VAR and
                            (existing_ty is None or
                             existing_ty.kind == IRType.TYPE_VAR)):
                        self.ssa_types[value_ssa] = expr.ir_type
                result = None  # 声明不产生值
            else:
                result = self._lower_expr(expr, current_block)
            # 表达式可能改变了当前块（如循环、if 等）
            # 后续表达式在新的当前块继续
            current_block = self.current_block
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
        # 根据 object 的 ADT 类型推断 field_index（index 0 = tag，实际字段从 1 开始）
        obj_type = getattr(hir_expr.object, "ir_type", None)
        if obj_type is not None and obj_type.kind == IRType.ADT:
            type_name = obj_type.name
            if type_name and type_name in self.type_defs:
                idx = self._find_field_index(type_name, hir_expr.field_name)
                if idx is not None:
                    instr.field_index = idx
        return self._emit(instr)

    def _find_field_index(self, type_name: str, field_name: str) -> Optional[int]:
        """
        在 ADT 类型定义中查找字段名对应的索引（tag在index 0，实际字段从1开始）。

        逻辑：遍历所有变体的所有字段，返回第一个匹配 field_name 的位置 + 1。
        如果同一字段名在多个变体中索引不一致，返回 None（保守回退）。
        """
        td = self.type_defs[type_name]
        found_idx: Optional[int] = None
        for variant in td.variants:
            for j, (fname, _) in enumerate(variant.fields):
                if fname == field_name:
                    current_idx = j + 1  # tag 在 index 0
                    if found_idx is None:
                        found_idx = current_idx
                    elif found_idx != current_idx:
                        # 同一字段名在不同变体中索引不同，保守不设置
                        return None
        return found_idx

    def _lower_index_expr(self, hir_expr, block):
        obj_ssa = self._lower_expr(hir_expr.object, block)
        idx_ssa = self._lower_expr(hir_expr.index, block)
        instr = MIRIndexAccess(hir_expr.ir_type)
        instr.object = obj_ssa or ""
        instr.index = idx_ssa or ""
        return self._emit(instr)

    # === Lambda ===

    def _lower_lambda(self, hir_expr, block):
        """降级 lambda 表达式：编译 lambda 函数体为独立 MIRFunction。

        步骤：
        1. 生成唯一的 lambda 函数名
        2. 分析 lambda 体中的自由变量（需从外层捕获的变量）
        3. 保存外层编译上下文
        4. 为 lambda 创建独立 MIRFunction（捕获变量作为隐式前缀参数）
        5. 编译 lambda 函数体
        6. 注册 lambda 函数到收集器
        7. 恢复外层上下文
        8. 生成 MIRClosureCreate 指令（携带函数名和捕获变量 SSA 名）
        """
        # 1. 生成唯一的 lambda 函数名
        lambda_name = "__lambda_%d" % self.ssa_counter

        # 2. 收集 lambda 参数名，分析自由变量
        param_names = {name for name, _ in hir_expr.params}
        free_vars = self._collect_free_vars(hir_expr.body, param_names)

        # 确定捕获变量：自由变量中存在于当前 env 的
        # 按 sorted 顺序保证确定性
        captures = []  # [(var_name, enclosing_ssa, var_type)]
        for var_name in sorted(free_vars):
            if var_name in self.env:
                enc_ssa = self.env[var_name]
                var_type = self.ssa_types.get(enc_ssa, UNIT_TYPE)
                captures.append((var_name, enc_ssa, var_type))

        # 3. 保存外层编译上下文
        saved = self._save_context()

        # 4. 构造 HIRFunction（捕获变量作为前缀隐式参数 + lambda 自身参数）
        # 优先使用 lambda 上显式标注的返回类型，否则从 ir_type 推断
        return_type = hir_expr.return_type
        # 防御式检查：return_type 可能为 None（前端未正确填充时）
        if return_type is None or return_type.kind == IRType.TYPE_VAR:
            fn_type = hir_expr.ir_type
            if fn_type and fn_type.params:
                return_type = fn_type.params[-1]
            else:
                return_type = UNIT_TYPE
        all_params = [(name, ty) for name, _, ty in captures] + list(hir_expr.params)
        hir_fn = HIRFunction(
            name=lambda_name,
            params=all_params,
            return_type=return_type,
            body=hir_expr.body,
        )

        # 5. 编译 lambda 函数体（复用 _lower_function 逻辑）
        mir_fn = self._lower_function(hir_fn)

        # 6. 注册 lambda 函数
        self.lambda_functions[lambda_name] = mir_fn

        # 7. 恢复外层上下文
        self._restore_context(saved)

        # 8. 生成 MIRClosureCreate 指令
        # 构造携带返回类型的函数类型（替代裸 CLOSURE_TYPE）
        # params = [参数类型...] + [返回类型]，使调用点能通过 params[-1] 获取返回类型
        closure_params = [ty for _, _, ty in captures] + [ty for _, ty in hir_expr.params]
        closure_params.append(return_type)
        closure_ty = NovaType(
            IRType.FUNCTION, params=closure_params, name="Closure"
        )
        instr = MIRClosureCreate(closure_ty)
        instr.fn_name = lambda_name
        instr.captures = [enc_ssa for _, enc_ssa, _ in captures]
        return self._emit(instr)

    def _save_context(self):
        """保存当前编译上下文（用于 lambda 编译时的上下文切换）。"""
        return {
            "env": dict(self.env),
            "ssa_counter": self.ssa_counter,
            "block_counter": self.block_counter,
            "all_blocks": self.all_blocks,
            "current_block": self.current_block,
            "current_function": self.current_function,
            "ssa_types": dict(self.ssa_types),
            "loop_stack": list(self.loop_stack),
        }

    def _restore_context(self, state):
        """恢复之前保存的编译上下文。"""
        self.env = state["env"]
        self.ssa_counter = state["ssa_counter"]
        self.block_counter = state["block_counter"]
        self.all_blocks = state["all_blocks"]
        self.current_block = state["current_block"]
        self.current_function = state["current_function"]
        self.ssa_types = state["ssa_types"]
        self.loop_stack = state["loop_stack"]

    # === 自由变量分析（用于 lambda 捕获变量收集）===

    def _collect_free_vars(self, hir_expr, bound_names):
        """递归收集 HIR 表达式中的自由变量名称。

        自由变量 = 在表达式中引用但不在 bound_names 中的标识符。
        用于确定 lambda 需要从外层作用域捕获的变量。

        参数:
            hir_expr: HIR 表达式
            bound_names: 当前作用域已绑定的变量名集合

        返回:
            set: 自由变量名集合
        """
        free_vars = set()
        self._collect_idents(hir_expr, bound_names, free_vars)
        return free_vars

    def _collect_idents(self, expr, bound_names, free_vars):
        """递归遍历 HIR 树，收集标识符引用。

        对引入新绑定的结构（let/lambda/for/match pattern），
        在递归子表达式时将新绑定加入 bound_names。

        通过调度表分发到类型专属 handler，降低圈复杂度。
        """
        if expr is None:
            return

        # 调度表分发：查找类型专属 handler
        handler = self._collect_dispatch.get(type(expr))
        if handler is not None:
            handler(expr, bound_names, free_vars)
            return

        # 通用兜底：通过 _iter_hir_children 遍历所有子节点
        # _iter_hir_children 产出元组末元素恒为子表达式，无需 kind 分支
        for item in _iter_hir_children(expr):
            self._collect_idents(item[-1], bound_names, free_vars)

    def _collect_ident_ref(self, expr, bound_names, free_vars):
        """处理标识符引用：检查是否为自由变量"""
        if expr.name not in bound_names:
            free_vars.add(expr.name)

    def _collect_let(self, expr, bound_names, free_vars):
        """处理 let 声明：value 中引用的是外层变量，name 是新绑定"""
        self._collect_idents(expr.value, bound_names, free_vars)

    def _collect_block(self, expr, bound_names, free_vars):
        """处理块表达式：逐个处理，跟踪 let 引入的新绑定"""
        block_bound = set(bound_names)
        for sub in expr.exprs:
            if isinstance(sub, HIRLetDecl):
                self._collect_idents(sub.value, block_bound, free_vars)
                block_bound.add(sub.name)
            else:
                self._collect_idents(sub, block_bound, free_vars)

    def _collect_lambda_idents(self, expr, bound_names, free_vars):
        """处理嵌套 lambda：其参数在内部是 bound 的"""
        lambda_bound = set(bound_names)
        for name, _ in expr.params:
            lambda_bound.add(name)
        self._collect_idents(expr.body, lambda_bound, free_vars)

    def _collect_for(self, expr, bound_names, free_vars):
        """处理 for 循环：循环变量在新作用域中绑定"""
        self._collect_idents(expr.iterable, bound_names, free_vars)
        for_bound = set(bound_names)
        for_bound.add(expr.variable)
        self._collect_idents(expr.body, for_bound, free_vars)
        if expr.step:
            self._collect_idents(expr.step, for_bound, free_vars)

    def _collect_listcomp(self, expr, bound_names, free_vars):
        """处理列表推导式：推导变量在新作用域中绑定"""
        self._collect_idents(expr.iterable, bound_names, free_vars)
        lc_bound = set(bound_names)
        lc_bound.add(expr.variable)
        self._collect_idents(expr.result_expr, lc_bound, free_vars)
        if expr.filter:
            self._collect_idents(expr.filter, lc_bound, free_vars)

    def _collect_match(self, expr, bound_names, free_vars):
        """处理 match 表达式：模式可能绑定变量"""
        self._collect_idents(expr.value, bound_names, free_vars)
        for arm in expr.arms:
            arm_bound = set(bound_names)
            self._collect_pattern_binds(arm.pattern, arm_bound)
            if arm.guard:
                self._collect_idents(arm.guard, arm_bound, free_vars)
            self._collect_idents(arm.body, arm_bound, free_vars)

    def _collect_pattern_binds(self, pattern, bound_names):
        """收集模式中绑定的变量名，加入 bound_names 集合。"""
        from .ir_nodes import (
            HIRBindPattern,
            HIRConstructorPattern,
            HIRListPattern,
            HIRTuplePattern,
        )

        if isinstance(pattern, HIRBindPattern):
            bound_names.add(pattern.name)
        elif isinstance(pattern, HIRConstructorPattern):
            for fp in pattern.field_patterns:
                self._collect_pattern_binds(fp, bound_names)
        elif isinstance(pattern, HIRTuplePattern):
            for ep in pattern.elements:
                self._collect_pattern_binds(ep, bound_names)
        elif isinstance(pattern, HIRListPattern):
            for ep in pattern.elements:
                self._collect_pattern_binds(ep, bound_names)

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

        pre_env = dict(self.env)

        true_result, true_modified = self._lower_branch_body(
            hir_expr.consequence, true_block, merge_block, pre_env
        )
        false_result, false_modified = self._lower_branch_body(
            hir_expr.alternative, false_block, merge_block, pre_env
        )

        self.current_block = merge_block
        self._insert_merge_phis(
            pre_env, true_modified, false_modified, true_block, false_block, merge_block
        )

        merge_ssa = self._insert_result_phi(
            true_result, false_result, hir_expr.ir_type, true_block, false_block, merge_block
        )

        self.all_blocks.extend([true_block, false_block, merge_block])
        self.current_block = merge_block
        return merge_ssa

    def _lower_branch_body(self, hir_expr, branch_block, merge_block, pre_env):
        """降级单个分支（true 或 false），返回 (result, modified_vars)。

        在独立的环境中降级分支表达式，收集被修改的变量，
        并在分支未设置终结器时自动添加跳转到 merge 块的 Jump。
        """
        old_block = self.current_block
        self.current_block = branch_block

        result = None
        if hir_expr:
            result = self._lower_expr(hir_expr, branch_block)

        if branch_block.terminator is None:
            branch_block.terminator = MIRJump(merge_block.label)

        modified = {}
        for name, ssa in self.env.items():
            if name not in pre_env or pre_env[name] != ssa:
                modified[name] = ssa

        self.env = dict(pre_env)
        self.current_block = old_block
        return result, modified

    # ------------------------------------------------------------------
    # Phi 节点类型一致性（code_audit_60 P1-4 修复）
    # ------------------------------------------------------------------

    def _resolve_phi_type(self, phi_sources, context_label=""):
        """统一的 Phi 节点类型解析与一致性校验（修复 P1-4：第一个命中即 break 的 bug）。

        处理流程：
        1. 遍历所有 phi_sources，收集在 ssa_types 中注册的类型
        2. 过滤掉 UNIT_TYPE（占位 fallback），得到"候选有效类型列表"
        3. 若候选为空 → 返回 UNIT_TYPE（保持与旧行为一致的 fallback）
        4. 候选非空：两两调用 _ir_types_compatible 做一致性校验
           - 全部兼容 → 取第一个非 UNIT 非 TYPE_VAR 作为 phi_type（与旧行为最小化差异）
           - 存在不兼容对 → 第一阶段发出警告但不抛异常，仍取第一个有效类型
             （待 1-2 轮观察确认零假阳性后再升级为 raise MIRLoweringError）

        Args:
            phi_sources: [(block_label, ssa_name), ...] 待合并的前驱源列表
            context_label: 可选的上下文标签（如 merge_block.label），用于错误消息定位

        Returns:
            (phi_type: NovaType, has_inconsistency: bool)
            phi_type: 选定的最终 Phi 类型
            has_inconsistency: 是否检测到类型不一致（未来升级 fatal 时使用）
        """
        # 1. 收集所有注册类型
        all_typed = []
        for src_block, src_ssa in phi_sources:
            if src_ssa in self.ssa_types:
                all_typed.append((src_block, self.ssa_types[src_ssa]))

        # 2. 过滤 UNIT 占位 fallback
        valid_candidates = [(b, t) for b, t in all_typed if t.kind != IRType.UNIT]

        # 3. 无候选 → 保持 UNIT fallback
        if not valid_candidates:
            return UNIT_TYPE, False

        # 4. 两两一致性校验
        has_inconsistency = False
        n = len(valid_candidates)
        for i in range(n):
            for j in range(i + 1, n):
                b_i, t_i = valid_candidates[i]
                b_j, t_j = valid_candidates[j]
                if not _ir_types_compatible(t_i, t_j):
                    has_inconsistency = True
                    # 观察期（cycle 61-65）已确认零假阳性，正式升级为 fail-fast
                    # 结束 5 轮观察期（cycle 61→65，原计划 1-2 轮超期 3 轮）
                    # 报告内容含：上下文标签 + 两个前驱块标签名 + 各自类型（便于用户定位）
                    ctx = f" @ {context_label}" if context_label else " @ unknown_context"
                    raise MIRLoweringError(
                        f"Phi 类型不一致{ctx}: "
                        f"前驱块 {b_i} (类型 {t_i}, kind={t_i.kind.name}) 与 "
                        f"前驱块 {b_j} (类型 {t_j}, kind={t_j.kind.name}) 不兼容"
                    )

        # 5. 选取 phi_type：优先取第一个非 UNIT 非 TYPE_VAR 的候选；若全是 TYPE_VAR → 取第一个
        def _priority_rank(item):
            _, t = item
            if t.kind == IRType.TYPE_VAR:
                return 2  # 类型变量优先级最低
            return 0  # 其他类型（INT/FLOAT/LIST/...）优先级最高

        sorted_candidates = sorted(valid_candidates, key=_priority_rank)
        phi_type = sorted_candidates[0][1]
        return phi_type, has_inconsistency

    def _insert_merge_phis(self, pre_env, true_modified, false_modified,
                           true_block, false_block, merge_block):
        """为被修改的变量在 merge 块插入 Phi 节点。"""
        all_modified_names = set(true_modified.keys()) | set(false_modified.keys())

        for name in all_modified_names:
            phi_sources = []

            if name in true_modified:
                phi_sources.append((true_block.label, true_modified[name]))
            elif name in pre_env:
                phi_sources.append((true_block.label, pre_env[name]))

            if name in false_modified:
                phi_sources.append((false_block.label, false_modified[name]))
            elif name in pre_env:
                phi_sources.append((false_block.label, pre_env[name]))

            if len(phi_sources) >= 2:
                # 修复 P1-4：用统一的 _resolve_phi_type 替代"第一个命中即 break"
                # 显式消费 has_inconsistency：写入 current_function.annotation 作为可追踪标记，
                # 后续 emit 阶段或代码生成可读取此标记生成告警或终止（当前先保留计数）
                phi_type, has_incon = self._resolve_phi_type(
                    phi_sources,
                    context_label=f"merge_block[{merge_block.label}]::var[{name}]"
                )
                if has_incon:
                    # （注意：raise 路径下 has_incon=True 但不会执行到这里）
                    self.current_function.annotation["phi_inconsistency_count"] = (
                        self.current_function.annotation.get("phi_inconsistency_count", 0) + 1
                    )

                instr = MIRPhi(phi_type)
                instr.sources = phi_sources
                instr.result_name = self._new_ssa()
                merge_block.instructions.append(instr)
                self.env[name] = instr.result_name
                self.ssa_types[instr.result_name] = phi_type

    def _insert_result_phi(self, true_result, false_result, ir_type,
                           true_block, false_block, merge_block):
        """为 if 表达式结果插入 Phi 节点，返回结果 SSA 名或 None。"""
        result_phi_sources = []
        if true_result:
            result_phi_sources.append((true_block.label, true_result))
        if false_result:
            result_phi_sources.append((false_block.label, false_result))

        if result_phi_sources:
            instr = MIRPhi(ir_type)
            instr.sources = result_phi_sources
            instr.result_name = self._new_ssa()
            merge_block.instructions.append(instr)
            return instr.result_name
        return None


    def _collect_arm_modifications(self, arm_body_blocks, pre_env):
        """收集每个 arm body 块中相对于 pre_env 的变量修改。

        返回列表，每个元素是 {name: modified_ssa} 字典，
        表示该 arm 修改了哪些变量以及修改后的 SSA 名。
        """
        modified_envs = []
        for body_block in arm_body_blocks:
            modified = {}
            for name, ssa in self.env.items():
                if name not in pre_env or pre_env[name] != ssa:
                    modified[name] = ssa
            modified_envs.append(modified)
            # 恢复 env 到 pre_env，为下一个 arm 准备
            self.env = dict(pre_env)
        return modified_envs

    def _build_merge_phis(self, merge_block, hir_expr, arm_body_blocks,
                         arm_modified_envs, arm_results, pre_env):
        """在 merge 块中为所有被修改的变量和表达式结果构建 Phi 节点。

        阶段一：变量 Phi — 找出所有在任一 arm 中被修改的变量，
        收集每个 arm 的来源值（修改后的值或进入 match 前的值），
        至少两个不同来源时插入 Phi。

        阶段二：结果 Phi — 收集各 arm 的表达式结果 SSA，
        构建 match 表达式本身的值 Phi。

        返回 merge_ssa（match 表达式的结果 SSA 名，可能为 None）。
        """
        # 找出所有在任一 arm 中被修改的变量
        all_modified_names = set()
        for modified in arm_modified_envs:
            all_modified_names.update(modified.keys())

        # 阶段一：变量 Phi
        for name in all_modified_names:
            phi_sources = []
            for i, arm_block in enumerate(arm_body_blocks):
                if name in arm_modified_envs[i]:
                    phi_sources.append((arm_block.label, arm_modified_envs[i][name]))
                elif name in pre_env:
                    phi_sources.append((arm_block.label, pre_env[name]))

            if len(phi_sources) >= 2:
                # 修复 P1-4：用统一的 _resolve_phi_type 替代"第一个命中即 break"
                # 显式消费 has_inconsistency：写入 current_function.annotation 计数器
                phi_type, has_incon = self._resolve_phi_type(
                    phi_sources,
                    context_label=f"match_merge[{merge_block.label}]::var[{name}]"
                )
                if has_incon:
                    self.current_function.annotation["phi_inconsistency_count"] = (
                        self.current_function.annotation.get("phi_inconsistency_count", 0) + 1
                    )
                instr = MIRPhi(phi_type)
                instr.sources = phi_sources
                instr.result_name = self._new_ssa()
                merge_block.instructions.append(instr)
                self.env[name] = instr.result_name
                self.ssa_types[instr.result_name] = phi_type

        # 阶段二：表达式结果 Phi
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

        编排流程：块创建 → arm 循环(检查+body) → 失败块 → merge Phi
        """
        value_ssa = self._lower_expr(hir_expr.value, block)
        arms = hir_expr.arms
        if not arms:
            return None

        merge_block = MIRBasicBlock(self._new_block())
        fail_block = MIRBasicBlock(self._new_block())

        # 为每个 arm 创建检查块和 body 块
        check_blocks = [MIRBasicBlock(self._new_block()) for _ in range(len(arms))]
        body_blocks = [MIRBasicBlock(self._new_block()) for _ in range(len(arms))]

        # 入口块跳转到第一个 arm 的检查块
        block.terminator = MIRJump(check_blocks[0].label)

        # 保存进入 match 前的 env 状态
        pre_env = dict(self.env)
        self.current_block = block

        # --- arm 循环：模式检查 + body 降级 ---
        arm_results = []
        arm_body_blocks = []

        for i, arm in enumerate(arms):
            self.env = dict(pre_env)

            # 模式检查块：生成模式比较代码
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
            # 通配符模式可能未设置 terminator，默认跳转到 body 块
            if check_blocks[i].terminator is None:
                check_blocks[i].terminator = MIRJump(body_blocks[i].label)

            # arm body 块：降级 arm 表达式
            self.current_block = body_blocks[i]
            arm_result = self._lower_expr(arm.body, body_blocks[i])
            if body_blocks[i].terminator is None:
                body_blocks[i].terminator = MIRJump(merge_block.label)

            arm_body_blocks.append(body_blocks[i])
            arm_results.append(arm_result)

        # --- 失败块（理论不可达）---
        self.env = dict(pre_env)
        self.current_block = fail_block
        fail_block.terminator = MIRPanic("non-exhaustive match")

        # --- 收集 arm 变量修改 ---
        arm_modified_envs = self._collect_arm_modifications(arm_body_blocks, pre_env)

        # --- merge 块：Phi 节点 ---
        self.current_block = merge_block
        self.env = dict(pre_env)
        merge_ssa = self._build_merge_phis(
            merge_block, hir_expr, arm_body_blocks,
            arm_modified_envs, arm_results, pre_env
        )

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

            # 收集所有 source：入口边 + 所有回边（先构建 phi_sources，再统一解析类型）
            phi_sources = [(entry_block_label, pre_ssa)]  # 入口边
            for latch_block, latch_env in latch_blocks:
                latch_ssa = latch_env.get(var_name, pre_ssa)
                phi_sources.append((latch_block.label, latch_ssa))

            # Loop Phi 统一走 _resolve_phi_type：不再只取入口边 pre_ssa 的类型（第一个命中即 break 的旧逻辑）。
            # 覆盖 for/while/list_comprehension 三类循环的循环变量 Phi，
            # 若入口边类型与回边类型不兼容（如入口边 INT 回边 FLOAT）→ fail-fast 报错。
            phi_type, has_incon = self._resolve_phi_type(
                phi_sources,
                context_label=f"loop_header[{header_block.label}]::var[{var_name}]"
            )
            if has_incon:
                self.current_function.annotation["phi_inconsistency_count"] = (
                    self.current_function.annotation.get("phi_inconsistency_count", 0) + 1
                )

            phi_instr = MIRPhi(phi_type)
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


    # ── _lower_list_comprehension 拆分 helpers（CC=13 → 主函数 ≤4） ──

    def _lc_setup_entry(self, hir_expr, block):
        """列表推导式 Helper A：入口块初始化（空列表/可迭代对象/长度/索引=0/env快照）。

        返回 (list_init_ssa, iter_ssa, len_ssa, idx_init_ssa, pre_env,
               header_block, body_block, exit_block) 共 8 元组，
               并设置 block.terminator = Jump(header_block)。
        """
        header_block = MIRBasicBlock(self._new_block())
        body_block = MIRBasicBlock(self._new_block())
        exit_block = MIRBasicBlock(self._new_block())

        # 空列表 MIRListBuild
        empty_list_instr = MIRListBuild(hir_expr.ir_type)
        empty_list_instr.elements = []
        list_init_ssa = self._emit(empty_list_instr)

        # 可迭代对象降级
        iter_ssa = self._lower_expr(hir_expr.iterable, block)

        # 调用 list_length 获取长度
        len_instr = MIRCall(INT_TYPE)
        len_instr.callee = "list_length"
        len_instr.args = [iter_ssa or ""]
        len_ssa = self._emit(len_instr)

        # 索引初始值 0
        idx_init_instr = MIRConst(INT_TYPE)
        idx_init_instr.value = 0
        idx_init_instr.const_type = "int"
        idx_init_ssa = self._emit(idx_init_instr)

        # 进入循环前保存 env 快照
        pre_env = dict(self.env)

        # 跳转到循环头
        block.terminator = MIRJump(header_block.label)
        return (
            list_init_ssa, iter_ssa, len_ssa, idx_init_ssa, pre_env,
            header_block, body_block, exit_block,
        )

    def _lc_build_header(self, header_block, idx_init_ssa, list_init_ssa, len_ssa,
                         body_block, exit_block, list_ir_type):
        """列表推导式 Helper B：循环头构建（idx_phi + list_phi + i<len 比较 + Branch）。

        返回 (idx_phi, list_phi, idx_phi_ssa, list_phi_ssa)。
        副作用：设置 header_block.terminator = MIRBranch。
        """
        self.current_block = header_block

        # 索引 Phi（占位，sources 稍后由 _lc_fill_phis 填充）
        idx_phi = MIRPhi(INT_TYPE)
        idx_phi.result_name = self._new_ssa()
        idx_phi.sources = []
        header_block.instructions.append(idx_phi)
        idx_phi_ssa = idx_phi.result_name
        self.ssa_types[idx_phi_ssa] = INT_TYPE

        # 列表 Phi（循环携带的列表值）
        list_phi = MIRPhi(list_ir_type)
        list_phi.result_name = self._new_ssa()
        list_phi.sources = []
        header_block.instructions.append(list_phi)
        list_phi_ssa = list_phi.result_name
        self.ssa_types[list_phi_ssa] = list_ir_type

        # i < len 比较 + 条件分支
        cmp_instr = MIRBinOp(BOOL_TYPE)
        cmp_instr.op = "<"
        cmp_instr.left = idx_phi_ssa
        cmp_instr.right = len_ssa
        cmp_ssa = self._emit(cmp_instr)
        header_block.terminator = MIRBranch(cmp_ssa, body_block.label, exit_block.label)
        return idx_phi, list_phi, idx_phi_ssa, list_phi_ssa

    def _lc_build_body_and_latches(self, hir_expr, header_block, body_block,
                                   exit_block, iter_ssa, idx_phi_ssa, list_phi_ssa):
        """列表推导式 Helper C：循环体构建（元素绑定 + filter 双分支/单分支 + latch 收集）。

        返回 (latch_blocks, latch_inc_ssas, latch_list_ssas) 三元组。
        副作用：压入/弹出 loop_stack；如有 filter_true/filter_false 块则加入 all_blocks。
        """
        # ── 元素类型推导 + list_get 绑定循环变量 ──
        self.current_block = body_block
        elem_type = UNIT_TYPE
        iter_type = hir_expr.iterable.ir_type
        if iter_type.kind.name == "LIST" and iter_type.params:
            elem_type = iter_type.params[0]
        get_instr = MIRCall(elem_type)
        get_instr.callee = "list_get"
        get_instr.args = [iter_ssa or "", idx_phi_ssa]
        elem_ssa = self._emit(get_instr)
        self.env[hir_expr.variable] = elem_ssa

        # 收集 latch 块
        latch_blocks = []
        latch_inc_ssas = []
        latch_list_ssas = []

        # 压入循环上下文（break → exit, continue → header）
        self.loop_stack.append((header_block.label, exit_block.label))

        if hir_expr.filter is not None:
            # ── 有 filter：filter_true + filter_false 双分支 ──
            filter_block = MIRBasicBlock(self._new_block())
            filter_false_block = MIRBasicBlock(self._new_block())

            filter_ssa = self._lower_expr(hir_expr.filter, body_block)
            body_block.terminator = MIRBranch(
                filter_ssa or "", filter_block.label, filter_false_block.label
            )

            # filter 为真：result_expr + append + idx++
            self.current_block = filter_block
            result_ssa = self._lower_expr(hir_expr.result_expr, filter_block)
            append_instr = MIRListAppend(hir_expr.ir_type)
            append_instr.list_ssa = list_phi_ssa
            append_instr.element_ssa = result_ssa or ""
            new_list_ssa_t = self._emit(append_instr)
            inc_ssa_t = self._emit_idx_increment(idx_phi_ssa)
            filter_block.terminator = MIRJump(header_block.label)
            latch_blocks.append((filter_block, dict(self.env)))
            latch_inc_ssas.append(inc_ssa_t)
            latch_list_ssas.append(new_list_ssa_t)

            # filter 为假：仅 idx++（list 值不变 = list_phi_ssa）
            self.current_block = filter_false_block
            inc_ssa_f = self._emit_idx_increment(idx_phi_ssa)
            filter_false_block.terminator = MIRJump(header_block.label)
            self.all_blocks.extend([filter_block, filter_false_block])
            latch_blocks.append((filter_false_block, dict(self.env)))
            latch_inc_ssas.append(inc_ssa_f)
            latch_list_ssas.append(list_phi_ssa)
        else:
            # ── 无 filter：直接 result_expr + append + idx++ ──
            result_ssa = self._lower_expr(hir_expr.result_expr, body_block)
            append_instr = MIRListAppend(hir_expr.ir_type)
            append_instr.list_ssa = list_phi_ssa
            append_instr.element_ssa = result_ssa or ""
            new_list_ssa = self._emit(append_instr)
            inc_ssa = self._emit_idx_increment(idx_phi_ssa)
            if body_block.terminator is None:
                body_block.terminator = MIRJump(header_block.label)
            latch_blocks.append((body_block, dict(self.env)))
            latch_inc_ssas.append(inc_ssa)
            latch_list_ssas.append(new_list_ssa)

        # 弹出循环上下文
        self.loop_stack.pop()
        return latch_blocks, latch_inc_ssas, latch_list_ssas

    def _lc_fill_phis_and_finish(self, idx_phi, list_phi, entry_block,
                                 idx_init_ssa, list_init_ssa,
                                 latch_blocks, latch_inc_ssas, latch_list_ssas,
                                 pre_env, header_block_obj, hir_expr_variable,
                                 body_block_obj, exit_block_obj):
        """列表推导式 Helper D：通用循环 Phi 插入 + idx/list Phi sources 回填 + 收尾。

        返回 list_phi.result_ssa（最终表达式结果）。
        副作用：env 更新为 Phi 结果；header/body/exit 三块加入 all_blocks；
        current_block 切换到 exit_block。
        """
        # 5. 通用方法插入用户变量的循环 Phi（跳过 idx/list 两个系统 Phi，exclude 循环变量）
        phi_results = self._insert_loop_phis(
            pre_env=pre_env,
            entry_block_label=entry_block.label,
            header_block=header_block_obj,
            latch_blocks=latch_blocks,
            phi_offset=2,
            exclude_vars={hir_expr_variable},
        )

        # env 中的用户变量值 → Phi 结果
        for var_name, phi_result in phi_results.items():
            self.env[var_name] = phi_result

        # 填充 idx_phi sources: entry(idx_init) + N latch(idx_inc)
        idx_phi.sources = [(entry_block.label, idx_init_ssa)] + [
            (lb.label, inc_val) for (lb, _), inc_val in zip(latch_blocks, latch_inc_ssas)
        ]
        # 填充 list_phi sources: entry(list_init) + N latch(list_val)
        list_phi.sources = [(entry_block.label, list_init_ssa)] + [
            (lb.label, lv) for (lb, _), lv in zip(latch_blocks, latch_list_ssas)
        ]

        # 收尾：三块注册 + current_block 切换
        self.all_blocks.extend([header_block_obj, body_block_obj, exit_block_obj])
        self.current_block = exit_block_obj
        return list_phi.result_name

    def _lower_list_comprehension(self, hir_expr, block):
        """
        降级列表推导式：[result_expr | variable <- iterable, filter?]

        编译结构（索引遍历，与 for/while SSA 策略一致）：
          entry: list=[]; iter=X; len=length(iter); i=0; goto header
          header: phi_i, phi_list, phi_user_vars...; if i<len goto body else goto exit
          body:   elem = list_get(iter, i); bind variable;
                  filter? filter_true(result+append) / filter_false(no append)
                          : direct result+append;
                  i++; goto header
          exit:   return phi_list

        【CC=13 → ≤4 拆分说明】
        原 217 行单体函数拆为 4 个语义清晰的 helper，主函数仅含 4 次顺序调用：
          _lc_setup_entry（初始化+三空块） → _lc_build_header（Phi+Branch）
          → _lc_build_body_and_latches（元素绑定+filter分支+latch收集）
          → _lc_fill_phis_and_finish（通用Phi插入+sources回填+收尾）
        所有 if/for 等控制流全部移入 helper，主函数仅剩顺序结构，CC≤4 出榜。
        """
        # Step 1: 入口初始化（空列表/iter/len/i=0/pre_env + 三块创建 + Jump header）
        (list_init, iter_ssa, len_ssa, idx_init, pre_env,
         hdr_blk, body_blk, exit_blk) = self._lc_setup_entry(hir_expr, block)

        # Step 2: 循环头 Phi 节点 + i<len 条件分支
        idx_phi, list_phi, idx_phi_ssa, list_phi_ssa = self._lc_build_header(
            hdr_blk, idx_init, list_init, len_ssa, body_blk, exit_blk, hir_expr.ir_type
        )

        # Step 3: 循环体（元素绑定 + filter 双分支/单分支 + latch 收集）
        latch_blocks, latch_inc_ssas, latch_list_ssas = self._lc_build_body_and_latches(
            hir_expr, hdr_blk, body_blk, exit_blk, iter_ssa, idx_phi_ssa, list_phi_ssa
        )

        # Step 4: 通用用户变量 Phi + idx/list Phi sources 回填 + 收尾
        return self._lc_fill_phis_and_finish(
            idx_phi=idx_phi, list_phi=list_phi, entry_block=block,
            idx_init_ssa=idx_init, list_init_ssa=list_init,
            latch_blocks=latch_blocks, latch_inc_ssas=latch_inc_ssas, latch_list_ssas=latch_list_ssas,
            pre_env=pre_env, header_block_obj=hdr_blk, hir_expr_variable=hir_expr.variable,
            body_block_obj=body_blk, exit_block_obj=exit_blk,
        )

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
