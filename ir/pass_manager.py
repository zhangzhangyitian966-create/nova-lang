"""
Nova Pass 管理器

支持在 HIR/MIR/LIR 各层插入优化 Pass。
Pass 管理器负责按序运行各层 Pass，并在达到不动点（无新变化）时停止。
"""

from typing import List
from ir_nodes import (
    IRType, NovaType,
    INT_TYPE, FLOAT_TYPE, BOOL_TYPE,
    HIRModule, HIRFnDecl, HIRLetDecl,
    HIRExpr,
    HIRIntLiteral, HIRFloatLiteral, HIRBoolLiteral, HIRStringLiteral,
    HIRBinaryOp, HIRBlockExpr, HIRCallExpr, HIRIfExpr, HIRUnitLiteral,
    MIRModule,
    LIRModule,
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

        if isinstance(expr.left, HIRIntLiteral) and isinstance(expr.right, HIRIntLiteral):
            result = self._eval_int_binop(expr.op, expr.left.value, expr.right.value)
            if result is not None:
                expr.__class__ = HIRIntLiteral
                expr.value = result
                expr.ir_type = INT_TYPE
                del expr.op
                del expr.left
                del expr.right
                return True

        if isinstance(expr.left, HIRFloatLiteral) and isinstance(expr.right, HIRFloatLiteral):
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
    """函数内联"""
    name = "inlining"

    def run(self, hir_module):
        return False


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
