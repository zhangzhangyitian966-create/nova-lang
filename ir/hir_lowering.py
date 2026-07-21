"""
AST -> HIR 降级器

将现有手写 Parser 产生的 AST 节点（ast_nodes.py）转换为 HIR（High-Level IR）节点。
这是编译管道的第一步，接收 AST 产出 HIR Module。
"""

from ..ast_nodes import (
    AliasDef,
    Assignment,
    BinaryOp,
    Block,
    BoolLiteral,
    BreakExpr,
    CharLiteral,
    ContinueExpr,
    ExportDecl,
    FieldAccess,
    FloatLiteral,
    FnCall,
    FnDef,
    ForExpr,
    Identifier,
    IfExpr,
    ImportDecl,
    IntLiteral,
    Lambda,
    LetBinding,
    ListComprehension,
    ListExpr,
    MapExpr,
    MatchExpr,
    MutBinding,
    PatternBool,
    PatternChar,
    PatternConstructor,
    PatternFloat,
    PatternIdentifier,
    PatternInt,
    PatternList,
    PatternString,
    PatternTuple,
    PatternWildcard,
    PipeExpr,
    Program,
    StringLiteral,
    TryExpr,
    TupleExpr,
    TypeDef,
    UnaryOp,
    UnitLiteral,
    WhileExpr,
)
from .ir_nodes import (
    HIRAliasDecl,
    HIRAssignExpr,
    HIRBinaryOp,
    HIRBindPattern,
    HIRBlockExpr,
    HIRBoolLiteral,
    HIRBoolPattern,
    HIRBreakExpr,
    HIRCallExpr,
    HIRCharLiteral,
    HIRCharPattern,
    HIRConstructorPattern,
    HIRContinueExpr,
    HIRDecl,
    HIRExportDecl,
    HIRExpr,
    HIRFieldExpr,
    HIRFloatLiteral,
    HIRFloatPattern,
    HIRFnDecl,
    HIRForExpr,
    HIRFunction,
    HIRIdentifier,
    HIRIfExpr,
    HIRImportDecl,
    HIRIntLiteral,
    HIRIntPattern,
    HIRLambda,
    HIRLetDecl,
    HIRListComprehension,
    HIRListExpr,
    HIRListPattern,
    HIRMapExpr,
    HIRMatchArm,
    HIRMatchExpr,
    HIRModule,
    HIRPattern,
    HIRPipeExpr,
    HIRStringLiteral,
    HIRStringPattern,
    HIRTupleExpr,
    HIRTuplePattern,
    HIRTypeDecl,
    HIRTypeDef,
    HIRUnaryOp,
    HIRUnitLiteral,
    HIRUnwrapExpr,
    HIRVariant,
    HIRWhileExpr,
    HIRWildcardPattern,
    IRType,
    NovaType,
)


class HIRLoweringError(Exception):
    """HIR 降级过程中的错误"""

    pass


class HIRLowering:
    """AST -> HIR 降级器

    将手写 Parser 产生的 AST Program 转换为 HIR Module。
    在此阶段，类型信息尚未确定（标记为 TYPE_VAR），
    后续的类型检查 Pass 会填充具体类型。
    """

    def __init__(self):
        self.functions: dict = {}
        self.type_defs: dict = {}
        self.globals: list = []
        self.errors: list = []
        # 表达式降级调度表：AST 节点类型 -> 降级方法
        self._expr_lowerers = self._build_expr_lowerers()

    def _build_expr_lowerers(self):
        """构建表达式降级调度表

        将每种 AST 节点类型映射到对应的降级方法，
        替代原来的 if-isinstance 链，降低圈复杂度。
        """
        return {
            IntLiteral: self._lower_int_literal,
            FloatLiteral: self._lower_float_literal,
            StringLiteral: self._lower_string_literal,
            CharLiteral: self._lower_char_literal,
            BoolLiteral: self._lower_bool_literal,
            UnitLiteral: self._lower_unit_literal,
            Identifier: self._lower_identifier,
            BinaryOp: self._lower_binary_op,
            UnaryOp: self._lower_unary_op,
            PipeExpr: self._lower_pipe_expr,
            TryExpr: self._lower_try_expr,
            FnCall: self._lower_fn_call,
            Lambda: self._lower_lambda,
            IfExpr: self._lower_if_expr,
            MatchExpr: self._lower_match_expr,
            ListExpr: self._lower_list_expr,
            TupleExpr: self._lower_tuple_expr,
            MapExpr: self._lower_map_expr,
            FieldAccess: self._lower_field_access,
            Block: self._lower_block,
            ForExpr: self._lower_for_expr,
            WhileExpr: self._lower_while_expr,
            BreakExpr: self._lower_break_expr,
            ContinueExpr: self._lower_continue_expr,
            ListComprehension: self._lower_list_comprehension,
            Assignment: self._lower_assignment,
            LetBinding: self._lower_let_binding,
            MutBinding: self._lower_mut_binding,
        }

    def lower(self, program: Program) -> HIRModule:
        """将 AST Program 降级为 HIR Module"""
        module = HIRModule(name="main")

        for decl in program.declarations:
            try:
                hir_decl = self._lower_decl(decl, module)
                if hir_decl is not None:
                    module.declarations.append(hir_decl)
            except HIRLoweringError as e:
                self.errors.append(str(e))

        return module

    def _lower_decl(self, decl, module: HIRModule) -> HIRDecl:
        """降级单个顶层声明"""
        if isinstance(decl, FnDef):
            fn = self._lower_fn(decl)
            self.functions[fn.name] = fn
            return HIRFnDecl(fn)

        elif isinstance(decl, LetBinding):
            value = self._lower_expr(decl.value)
            return HIRLetDecl(
                decl.name, NovaType(IRType.TYPE_VAR), value, is_mutable=False
            )

        elif isinstance(decl, MutBinding):
            value = self._lower_expr(decl.value)
            return HIRLetDecl(
                decl.name, NovaType(IRType.TYPE_VAR), value, is_mutable=True
            )

        elif isinstance(decl, TypeDef):
            td = self._lower_type_def(decl)
            module.type_defs[td.name] = td
            return HIRTypeDecl(td)

        elif isinstance(decl, AliasDef):
            return HIRAliasDecl(decl.name, NovaType(IRType.TYPE_VAR))

        elif isinstance(decl, ImportDecl):
            module.imports.append(decl.module_name)
            return HIRImportDecl(decl.module_name)

        elif isinstance(decl, ExportDecl):
            module.exports.append(decl.name)
            return HIRExportDecl(decl.name)

        elif isinstance(decl, ForExpr):
            return self._lower_for_as_decl(decl)

        elif isinstance(decl, WhileExpr):
            body = self._lower_expr(decl.body)
            return HIRWhileExpr(self._lower_expr(decl.condition), body)

        else:
            # 顶层表达式语句
            expr = self._lower_expr(decl)
            return HIRLetDecl("_expr", NovaType(IRType.TYPE_VAR), expr)

    def _lower_fn(self, fn_def: FnDef) -> HIRFunction:
        """降级函数定义"""
        params = [(p.name, NovaType(IRType.TYPE_VAR)) for p in fn_def.params]
        body = self._lower_expr(fn_def.body)
        return HIRFunction(
            name=fn_def.name,
            params=params,
            return_type=NovaType(IRType.TYPE_VAR),
            body=body,
        )

    def _lower_type_def(self, td: TypeDef) -> HIRTypeDef:
        """降级类型定义"""
        variants = []
        for v in td.variants:
            fields = [(f[0], NovaType(IRType.TYPE_VAR)) for f in v.fields]
            variants.append(HIRVariant(v.name, fields))
        return HIRTypeDef(td.name, variants)

    def _lower_for_as_decl(self, for_expr: ForExpr) -> HIRDecl:
        """将 for 循环作为顶层声明降级"""
        iterable = self._lower_iterable(for_expr.iterable, for_expr)
        body = self._lower_expr(for_expr.body)
        step = self._lower_expr(for_expr.step) if for_expr.step else None
        hir_for = HIRForExpr(for_expr.var_name, iterable, body, step=step)
        return HIRLetDecl("_for_result", NovaType(IRType.TYPE_VAR), hir_for)

    def _lower_iterable(self, iterable, for_expr) -> HIRExpr:
        """降级 for 循环的可迭代对象"""
        if isinstance(iterable, tuple) and iterable[0] == "range":
            return HIRIdentifier("_range")
        else:
            return self._lower_expr(iterable)

    def _lower_expr(self, expr) -> HIRExpr:
        """降级 AST 表达式为 HIR 表达式

        使用调度表模式根据 AST 节点类型分发到对应的降级方法，
        替代原来的 if-isinstance 链，降低圈复杂度。
        """
        if expr is None:
            return HIRUnitLiteral()

        lower_fn = self._expr_lowerers.get(type(expr))
        if lower_fn:
            return lower_fn(expr)

        # 未知类型，返回 unit 字面量作为降级处理
        return HIRUnitLiteral()

    # ---- 字面量 ----

    def _lower_int_literal(self, expr) -> HIRExpr:
        """降级整数字面量"""
        return HIRIntLiteral(expr.value)

    def _lower_float_literal(self, expr) -> HIRExpr:
        """降级浮点数字面量"""
        return HIRFloatLiteral(expr.value)

    def _lower_string_literal(self, expr) -> HIRExpr:
        """降级字符串字面量"""
        return HIRStringLiteral(expr.value)

    def _lower_char_literal(self, expr) -> HIRExpr:
        """降级字符字面量"""
        return HIRCharLiteral(expr.value)

    def _lower_bool_literal(self, expr) -> HIRExpr:
        """降级布尔字面量"""
        return HIRBoolLiteral(expr.value)

    def _lower_unit_literal(self, expr) -> HIRExpr:
        """降级 unit 字面量"""
        return HIRUnitLiteral()

    # ---- 标识符与运算 ----

    def _lower_identifier(self, expr) -> HIRExpr:
        """降级标识符"""
        return HIRIdentifier(expr.name)

    def _lower_binary_op(self, expr) -> HIRExpr:
        """降级二元运算"""
        return HIRBinaryOp(
            expr.op,
            self._lower_expr(expr.left),
            self._lower_expr(expr.right),
        )

    def _lower_unary_op(self, expr) -> HIRExpr:
        """降级一元运算"""
        return HIRUnaryOp(expr.op, self._lower_expr(expr.operand))

    def _lower_pipe_expr(self, expr) -> HIRExpr:
        """降级管道表达式"""
        stages = [self._lower_expr(expr.left)]
        stages.append(self._lower_expr(expr.right))
        return HIRPipeExpr(stages)

    def _lower_try_expr(self, expr) -> HIRExpr:
        """降级 try 表达式（映射为 unwrap）"""
        return HIRUnwrapExpr(self._lower_expr(expr.expr))

    # ---- 函数与调用 ----

    def _lower_fn_call(self, expr) -> HIRExpr:
        """降级函数调用"""
        return HIRCallExpr(
            self._lower_expr(expr.callee),
            [self._lower_expr(a) for a in expr.args],
        )

    def _lower_lambda(self, expr) -> HIRExpr:
        """降级 Lambda 表达式"""
        params = [(p.name, NovaType(IRType.TYPE_VAR)) for p in expr.params]
        body = self._lower_expr(expr.body)
        return HIRLambda(params, body)

    # ---- 控制流 ----

    def _lower_if_expr(self, expr) -> HIRExpr:
        """降级 if 表达式"""
        return HIRIfExpr(
            self._lower_expr(expr.condition),
            self._lower_expr(expr.then_branch),
            self._lower_expr(expr.else_branch) if expr.else_branch else None,
        )

    def _lower_match_expr(self, expr) -> HIRExpr:
        """降级 match 表达式"""
        arms = []
        for arm in expr.arms:
            pattern = self._lower_pattern(arm.pattern)
            body = self._lower_expr(arm.body) if arm.body else HIRUnitLiteral()
            guard = self._lower_expr(arm.guard) if arm.guard else None
            arms.append(HIRMatchArm(pattern, guard, body))
        return HIRMatchExpr(self._lower_expr(expr.subject), arms)

    # ---- 数据结构 ----

    def _lower_list_expr(self, expr) -> HIRExpr:
        """降级列表表达式"""
        return HIRListExpr([self._lower_expr(e) for e in expr.elements])

    def _lower_tuple_expr(self, expr) -> HIRExpr:
        """降级元组表达式"""
        return HIRTupleExpr([self._lower_expr(e) for e in expr.elements])

    def _lower_map_expr(self, expr) -> HIRExpr:
        """降级映射表达式"""
        entries = [
            (self._lower_expr(k), self._lower_expr(v)) for k, v in expr.pairs
        ]
        return HIRMapExpr(entries)

    def _lower_field_access(self, expr) -> HIRExpr:
        """降级字段访问"""
        return HIRFieldExpr(self._lower_expr(expr.target), expr.field)

    # ---- 块与循环 ----

    def _lower_block(self, expr) -> HIRExpr:
        """降级代码块"""
        stmts = [self._lower_expr(s) for s in expr.statements]
        tail = (
            self._lower_expr(expr.tail_expression) if expr.tail_expression else None
        )
        all_exprs = stmts
        if tail is not None:
            all_exprs.append(tail)
        return HIRBlockExpr(all_exprs)

    def _lower_for_expr(self, expr) -> HIRExpr:
        """降级 for 循环表达式"""
        iterable = self._lower_iterable(expr.iterable, expr)
        body = self._lower_expr(expr.body)
        step = self._lower_expr(expr.step) if expr.step else None
        return HIRForExpr(expr.var_name, iterable, body, step=step)

    def _lower_while_expr(self, expr) -> HIRExpr:
        """降级 while 循环表达式"""
        return HIRWhileExpr(
            self._lower_expr(expr.condition),
            self._lower_expr(expr.body),
        )

    def _lower_break_expr(self, expr) -> HIRExpr:
        """降级 break 表达式"""
        return HIRBreakExpr()

    def _lower_continue_expr(self, expr) -> HIRExpr:
        """降级 continue 表达式"""
        return HIRContinueExpr()

    # ---- 列表推导式与赋值 ----

    def _lower_list_comprehension(self, expr) -> HIRExpr:
        """降级列表推导式"""
        iterable = self._lower_iterable(expr.iterable, expr)
        filter_expr = (
            self._lower_expr(expr.filter_cond) if expr.filter_cond else None
        )
        return HIRListComprehension(
            self._lower_expr(expr.expr),
            expr.var_name,
            iterable,
            filter=filter_expr,
        )

    def _lower_assignment(self, expr) -> HIRExpr:
        """降级赋值表达式"""
        return HIRAssignExpr(
            HIRIdentifier(expr.name),
            self._lower_expr(expr.value),
        )

    def _lower_let_binding(self, expr) -> HIRExpr:
        """降级 let 绑定（包装为块表达式）"""
        return HIRBlockExpr(
            [
                HIRLetDecl(
                    expr.name,
                    NovaType(IRType.TYPE_VAR),
                    self._lower_expr(expr.value),
                )
            ]
        )

    def _lower_mut_binding(self, expr) -> HIRExpr:
        """降级 mut 绑定（包装为块表达式）"""
        return HIRBlockExpr(
            [
                HIRLetDecl(
                    expr.name,
                    NovaType(IRType.TYPE_VAR),
                    self._lower_expr(expr.value),
                    is_mutable=True,
                )
            ]
        )

    def _lower_pattern(self, pattern) -> HIRPattern:
        """降级 AST 模式为 HIR 模式"""
        if pattern is None:
            return HIRWildcardPattern()

        if isinstance(pattern, PatternInt):
            return HIRIntPattern(pattern.value)

        elif isinstance(pattern, PatternFloat):
            return HIRFloatPattern(pattern.value)

        elif isinstance(pattern, PatternString):
            return HIRStringPattern(pattern.value)

        elif isinstance(pattern, PatternBool):
            return HIRBoolPattern(pattern.value)

        elif isinstance(pattern, PatternChar):
            return HIRCharPattern(pattern.value)

        elif isinstance(pattern, PatternWildcard):
            return HIRWildcardPattern()

        elif isinstance(pattern, PatternIdentifier):
            return HIRBindPattern(pattern.name)

        elif isinstance(pattern, PatternConstructor):
            field_patterns = [self._lower_pattern(f) for f in pattern.fields]
            return HIRConstructorPattern("", pattern.name, field_patterns)

        elif isinstance(pattern, PatternTuple):
            return HIRTuplePattern([self._lower_pattern(e) for e in pattern.elements])

        elif isinstance(pattern, PatternList):
            return HIRListPattern([self._lower_pattern(e) for e in pattern.elements])

        else:
            return HIRWildcardPattern()
