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
        """降级 AST 表达式为 HIR 表达式"""
        if expr is None:
            return HIRUnitLiteral()

        if isinstance(expr, IntLiteral):
            return HIRIntLiteral(expr.value)

        elif isinstance(expr, FloatLiteral):
            return HIRFloatLiteral(expr.value)

        elif isinstance(expr, StringLiteral):
            return HIRStringLiteral(expr.value)

        elif isinstance(expr, CharLiteral):
            return HIRCharLiteral(expr.value)

        elif isinstance(expr, BoolLiteral):
            return HIRBoolLiteral(expr.value)

        elif isinstance(expr, UnitLiteral):
            return HIRUnitLiteral()

        elif isinstance(expr, Identifier):
            return HIRIdentifier(expr.name)

        elif isinstance(expr, BinaryOp):
            return HIRBinaryOp(
                expr.op,
                self._lower_expr(expr.left),
                self._lower_expr(expr.right),
            )

        elif isinstance(expr, UnaryOp):
            return HIRUnaryOp(expr.op, self._lower_expr(expr.operand))

        elif isinstance(expr, PipeExpr):
            stages = [self._lower_expr(expr.left)]
            stages.append(self._lower_expr(expr.right))
            return HIRPipeExpr(stages)

        elif isinstance(expr, TryExpr):
            return HIRUnwrapExpr(self._lower_expr(expr.expr))

        elif isinstance(expr, FnCall):
            return HIRCallExpr(
                self._lower_expr(expr.callee),
                [self._lower_expr(a) for a in expr.args],
            )

        elif isinstance(expr, Lambda):
            params = [(p.name, NovaType(IRType.TYPE_VAR)) for p in expr.params]
            body = self._lower_expr(expr.body)
            return HIRLambda(params, body)

        elif isinstance(expr, IfExpr):
            return HIRIfExpr(
                self._lower_expr(expr.condition),
                self._lower_expr(expr.then_branch),
                self._lower_expr(expr.else_branch) if expr.else_branch else None,
            )

        elif isinstance(expr, MatchExpr):
            arms = []
            for arm in expr.arms:
                pattern = self._lower_pattern(arm.pattern)
                body = self._lower_expr(arm.body) if arm.body else HIRUnitLiteral()
                guard = self._lower_expr(arm.guard) if arm.guard else None
                arms.append(HIRMatchArm(pattern, guard, body))
            return HIRMatchExpr(self._lower_expr(expr.subject), arms)

        elif isinstance(expr, ListExpr):
            return HIRListExpr([self._lower_expr(e) for e in expr.elements])

        elif isinstance(expr, TupleExpr):
            return HIRTupleExpr([self._lower_expr(e) for e in expr.elements])

        elif isinstance(expr, MapExpr):
            entries = [
                (self._lower_expr(k), self._lower_expr(v)) for k, v in expr.pairs
            ]
            return HIRMapExpr(entries)

        elif isinstance(expr, FieldAccess):
            return HIRFieldExpr(self._lower_expr(expr.target), expr.field)

        elif isinstance(expr, Block):
            stmts = [self._lower_expr(s) for s in expr.statements]
            tail = (
                self._lower_expr(expr.tail_expression) if expr.tail_expression else None
            )
            all_exprs = stmts
            if tail is not None:
                all_exprs.append(tail)
            return HIRBlockExpr(all_exprs)

        elif isinstance(expr, ForExpr):
            iterable = self._lower_iterable(expr.iterable, expr)
            body = self._lower_expr(expr.body)
            step = self._lower_expr(expr.step) if expr.step else None
            return HIRForExpr(expr.var_name, iterable, body, step=step)

        elif isinstance(expr, WhileExpr):
            return HIRWhileExpr(
                self._lower_expr(expr.condition),
                self._lower_expr(expr.body),
            )

        elif isinstance(expr, BreakExpr):
            return HIRBreakExpr()

        elif isinstance(expr, ContinueExpr):
            return HIRContinueExpr()

        elif isinstance(expr, ListComprehension):
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

        elif isinstance(expr, Assignment):
            return HIRAssignExpr(
                HIRIdentifier(expr.name),
                self._lower_expr(expr.value),
            )

        elif isinstance(expr, LetBinding):
            return HIRBlockExpr(
                [
                    HIRLetDecl(
                        expr.name,
                        NovaType(IRType.TYPE_VAR),
                        self._lower_expr(expr.value),
                    )
                ]
            )

        elif isinstance(expr, MutBinding):
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

        else:
            return HIRUnitLiteral()

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
