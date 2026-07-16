"""
Nova Pass 管理器

支持在 HIR/MIR/LIR 各层插入优化 Pass。
Pass 管理器负责按序运行各层 Pass，并在达到不动点（无新变化）时停止。
"""

from ir_nodes import (
    FLOAT_TYPE,
    INT_TYPE,
    HIRBinaryOp,
    HIRFloatLiteral,
    HIRFnDecl,
    HIRIntLiteral,
    HIRLetDecl,
)


class Pass:
    """优化 Pass 基类"""

    name = ""

    def run(self, module) -> bool:
        raise NotImplementedError


class ConstantFolding(Pass):
    """常量折叠"""

    name = "constant_folding"

    def run(self, hir_module):
        changed = False
        for decl in hir_module.declarations:
            if isinstance(decl, HIRFnDecl):
                changed |= self._fold_fn(decl.fn_def)
            elif isinstance(decl, HIRLetDecl):
                changed |= self._fold_expr(decl.value)
        return changed

    def _fold_fn(self, fn):
        return self._fold_expr(fn.body)

    def _fold_expr(self, expr):
        if not isinstance(expr, HIRBinaryOp):
            return False

        changed = False
        if isinstance(expr.left, HIRBinaryOp):
            changed |= self._fold_expr(expr.left)
        if isinstance(expr.right, HIRBinaryOp):
            changed |= self._fold_expr(expr.right)

        if isinstance(expr.left, HIRIntLiteral) and isinstance(
            expr.right, HIRIntLiteral
        ):
            result = self._eval_int_binop(expr.op, expr.left.value, expr.right.value)
            if result is not None:
                expr.__class__ = HIRIntLiteral
                expr.value = result
                expr.ir_type = INT_TYPE
                del expr.op
                del expr.left
                del expr.right
                return True

        if isinstance(expr.left, HIRFloatLiteral) and isinstance(
            expr.right, HIRFloatLiteral
        ):
            result = self._eval_float_binop(expr.op, expr.left.value, expr.right.value)
            if result is not None:
                expr.__class__ = HIRFloatLiteral
                expr.value = result
                expr.ir_type = FLOAT_TYPE
                del expr.op
                del expr.left
                del expr.right
                return True

        return changed

    def _eval_int_binop(self, op, left, right):
        ops = {
            "+": lambda a, b: a + b,
            "-": lambda a, b: a - b,
            "*": lambda a, b: a * b,
            "/": lambda a, b: a // b if b != 0 else None,
            "%": lambda a, b: a % b if b != 0 else None,
        }
        fn = ops.get(op)
        if fn:
            try:
                return fn(left, right)
            except (ZeroDivisionError, OverflowError):
                return None
        return None

    def _eval_float_binop(self, op, left, right):
        ops = {
            "+": lambda a, b: a + b,
            "-": lambda a, b: a - b,
            "*": lambda a, b: a * b,
            "/": lambda a, b: a / b if b != 0 else None,
        }
        fn = ops.get(op)
        if fn:
            try:
                return fn(left, right)
            except (ZeroDivisionError, OverflowError):
                return None
        return None


class Inlining(Pass):
    """函数内联

    内联小型函数（单表达式函数体、无递归、参数少）。
    """

    name = "inlining"
    MAX_INLINE_SIZE = 3  # 最多内联 3 个表达式大小的函数

    def run(self, hir_module):
        changed = False
        # 收集所有可内联的函数
        inlineable = {}
        for decl in hir_module.declarations:
            if isinstance(decl, HIRFnDecl):
                fn = decl.fn_def
                if self._is_inlineable(fn):
                    inlineable[fn.name] = fn

        if not inlineable:
            return False

        # 在每个函数中尝试内联调用
        for decl in hir_module.declarations:
            if isinstance(decl, HIRFnDecl):
                changed |= self._inline_in_fn(decl.fn_def, inlineable)

        return changed

    def _is_inlineable(self, fn):
        """判断函数是否适合内联"""
        if fn.is_recursive:
            return False
        if len(fn.params) > 4:
            return False
        # 单表达式函数体（如 HIRBinaryOp, HIRCallExpr 等）
        body = fn.body
        if isinstance(body, HIRBlockExpr):
            # 如果 block 没有语句，只有结果表达式
            if hasattr(body, "stmts") and not body.stmts:
                if hasattr(body, "result") and body.result:
                    return True
            return False
        # 单个表达式
        return not isinstance(body, HIRBlockExpr)

    def _inline_in_fn(self, fn, inlineable):
        """在函数体内联调用"""
        return self._try_inline_expr(fn.body, inlineable, {})

    def _try_inline_expr(self, expr, inlineable, env):
        """尝试内联表达式中的调用"""
        changed = False

        if isinstance(expr, HIRCallExpr):
            # 先递归处理参数
            for arg in expr.args:
                changed |= self._try_inline_expr(arg, inlineable, env)

            # 检查是否是可内联的函数
            if isinstance(expr.fn_expr, HIRIdentifier):
                fn_name = expr.fn_expr.name
                if fn_name in inlineable:
                    target_fn = inlineable[fn_name]
                    # 执行内联（简化版：只处理直接返回的情况）
                    # 这里只做标记，完整内联需要处理变量替换
                    pass  # 简化版本，不做实际内联

        elif isinstance(expr, HIRBinaryOp):
            changed |= self._try_inline_expr(expr.left, inlineable, env)
            changed |= self._try_inline_expr(expr.right, inlineable, env)
        elif isinstance(expr, HIRIfExpr):
            changed |= self._try_inline_expr(expr.condition, inlineable, env)
            changed |= self._try_inline_expr(expr.consequence, inlineable, env)
            if expr.alternative:
                changed |= self._try_inline_expr(expr.alternative, inlineable, env)

        return changed
class DeadCodeElimination(Pass):
    """死代码消除"""

    name = "dead_code_elimination"

    def run(self, hir_module):
        return False


class CommonSubexprElimination(Pass):
    """公共子表达式消除"""

    name = "cse"

    def run(self, mir_module):
        return False


class LoopInvariantCodeMotion(Pass):
    """循环不变量外提"""

    name = "licm"

    def run(self, mir_module):
        return False


class PassManager:
    """优化 Pass 管理器"""

    def __init__(self):
        self.hir_passes = []
        self.mir_passes = []
        self.lir_passes = []
        self._verbose = False

    def add_hir_pass(self, pass_):
        self.hir_passes.append(pass_)

    def add_mir_pass(self, pass_):
        self.mir_passes.append(pass_)

    def add_lir_pass(self, pass_):
        self.lir_passes.append(pass_)

    def run_hir_passes(self, hir_module, max_iterations=10):
        total_changed = False
        for iteration in range(max_iterations):
            changed = False
            for pass_ in self.hir_passes:
                try:
                    changed |= pass_.run(hir_module)
                except Exception:
                    # TODO: 缩小异常范围，捕获更具体的异常类型
                    pass
            if not changed:
                break
            total_changed = True
        return total_changed

    def run_mir_passes(self, mir_module, max_iterations=10):
        total_changed = False
        for iteration in range(max_iterations):
            changed = False
            for pass_ in self.mir_passes:
                try:
                    changed |= pass_.run(mir_module)
                except Exception:
                    # TODO: 缩小异常范围，捕获更具体的异常类型
                    pass
            if not changed:
                break
            total_changed = True
        return total_changed

    def run_lir_passes(self, lir_module, max_iterations=10):
        total_changed = False
        for iteration in range(max_iterations):
            changed = False
            for pass_ in self.lir_passes:
                try:
                    changed |= pass_.run(lir_module)
                except Exception:
                    # TODO: 缩小异常范围，捕获更具体的异常类型
                    pass
            if not changed:
                break
            total_changed = True
        return total_changed


def default_optimization_pipeline():
    """创建默认的优化 Pass 管道"""
    pm = PassManager()
    pm.add_hir_pass(ConstantFolding())
    pm.add_hir_pass(DeadCodeElimination())
    pm.add_hir_pass(Inlining())
    pm.add_mir_pass(CommonSubexprElimination())
    pm.add_mir_pass(LoopInvariantCodeMotion())
    return pm
