"""
Nova Pass 管理器

支持在 HIR/MIR/LIR 各层插入优化 Pass。
Pass 管理器负责按序运行各层 Pass，并在达到不动点（无新变化）时停止。
"""

from ir_nodes import (
    FLOAT_TYPE,
    INT_TYPE,
    HIRBinaryOp,
    HIRBlockExpr,
    HIRFloatLiteral,
    HIRFnDecl,
    HIRIdentifier,
    HIRIntLiteral,
    HIRLetDecl,
    HIRStringLiteral,
    HIRBoolLiteral,
    HIRCharLiteral,
    HIRUnitLiteral,
    HIRTupleExpr,
    HIRListExpr,
    HIRMapExpr,
    HIRFieldExpr,
    HIRIndexExpr,
    HIRUnaryOp,
    HIRIfExpr,
    HIRLambda,
    HIRCallExpr,
    HIRForExpr,
    HIRWhileExpr,
    HIRAssignExpr,
    HIRMatchExpr,
    HIRListComprehension,
    HIRPipeExpr,
    HIRADTConstructor,
    HIRUnwrapExpr,
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
    """死代码消除
    
    移除未使用的 let 绑定和无副作用的表达式语句。
    采用反向扫描：从块的最后一个表达式（结果）出发，
    收集所有被使用的变量，未被使用且无副作用的绑定被移除。
    """

    name = "dead_code_elimination"

    # 纯操作符（无副作用）
    PURE_BINOPS = {
        "+", "-", "*", "/", "%", "==", "!=", "<", ">", "<=", ">=",
        "&&", "||", "++", "::",
    }
    PURE_UNARYOPS = {"-", "!", "~"}

    def run(self, hir_module):
        changed = False
        for decl in hir_module.declarations:
            if isinstance(decl, HIRFnDecl):
                changed |= self._eliminate_fn(decl.fn_def)
            elif isinstance(decl, HIRLetDecl):
                # 顶层 let 不消除（可能是导出的）
                pass
        return changed

    def _eliminate_fn(self, fn):
        return self._eliminate_expr(fn.body)

    def _eliminate_expr(self, expr):
        """递归消除表达式中的死代码"""
        changed = False

        # BlockExpr: 反向扫描消除未使用的 let
        if isinstance(expr, HIRBlockExpr):
            changed |= self._eliminate_block(expr)
            # 继续递归处理剩余的表达式
            for sub in expr.exprs:
                changed |= self._eliminate_expr(sub)

        # If: 处理两个分支
        elif isinstance(expr, HIRIfExpr):
            changed |= self._eliminate_expr(expr.condition)
            changed |= self._eliminate_expr(expr.consequence)
            changed |= self._eliminate_expr(expr.alternative)

        # For: 处理迭代器和循环体
        elif isinstance(expr, HIRForExpr):
            changed |= self._eliminate_expr(expr.iterable)
            changed |= self._eliminate_expr(expr.body)
            if expr.step is not None:
                changed |= self._eliminate_expr(expr.step)

        # While: 处理条件和体
        elif isinstance(expr, HIRWhileExpr):
            changed |= self._eliminate_expr(expr.condition)
            changed |= self._eliminate_expr(expr.body)

        # Lambda: 处理体
        elif isinstance(expr, HIRLambda):
            changed |= self._eliminate_expr(expr.body)

        # Match: 处理 scrutinee 和每个 arm 的 body
        elif isinstance(expr, HIRMatchExpr):
            changed |= self._eliminate_expr(expr.scrutinee)
            for arm in expr.arms:
                changed |= self._eliminate_expr(arm.body)

        # Call: 处理 callee 和 args（函数调用有副作用，不消除）
        elif isinstance(expr, HIRCallExpr):
            changed |= self._eliminate_expr(expr.callee)
            for arg in expr.args:
                changed |= self._eliminate_expr(arg)

        # 二元/一元运算
        elif isinstance(expr, HIRBinaryOp):
            changed |= self._eliminate_expr(expr.left)
            changed |= self._eliminate_expr(expr.right)
        elif isinstance(expr, HIRUnaryOp):
            changed |= self._eliminate_expr(expr.operand)

        # 列表/元组/映射
        elif isinstance(expr, HIRListExpr):
            for item in expr.items:
                changed |= self._eliminate_expr(item)
        elif isinstance(expr, HIRTupleExpr):
            for item in expr.items:
                changed |= self._eliminate_expr(item)
        elif isinstance(expr, HIRMapExpr):
            for key, val in expr.pairs:
                changed |= self._eliminate_expr(key)
                changed |= self._eliminate_expr(val)

        # 字段/索引
        elif isinstance(expr, HIRFieldExpr):
            changed |= self._eliminate_expr(expr.object)
        elif isinstance(expr, HIRIndexExpr):
            changed |= self._eliminate_expr(expr.collection)
            changed |= self._eliminate_expr(expr.index)

        # 管道
        elif isinstance(expr, HIRPipeExpr):
            changed |= self._eliminate_expr(expr.left)
            changed |= self._eliminate_expr(expr.right)

        # 赋值（有副作用，不消除）
        elif isinstance(expr, HIRAssignExpr):
            changed |= self._eliminate_expr(expr.value)

        # ADT 构造（纯操作）
        elif isinstance(expr, HIRADTConstructor):
            for arg in expr.args:
                changed |= self._eliminate_expr(arg)

        # Unwrap（可能 panic，有副作用）
        elif isinstance(expr, HIRUnwrapExpr):
            changed |= self._eliminate_expr(expr.operand)

        # 列表推导式
        elif isinstance(expr, HIRListComprehension):
            changed |= self._eliminate_expr(expr.expr)
            changed |= self._eliminate_expr(expr.iterable)

        # 字面量/标识符：无子表达式
        # (HIRIntLiteral, HIRFloatLiteral, HIRStringLiteral, HIRBoolLiteral,
        #  HIRCharLiteral, HIRUnitLiteral, HIRIdentifier)

        return changed

    def _eliminate_block(self, block):
        """消除一个 BlockExpr 中的死代码
        
        策略：
        1. 最后一个表达式是块的值，总是保留
        2. 从后往前扫描，收集被使用的变量名
        3. 未被使用且无副作用的 let 绑定移除
        4. 无副作用且不是最后一个的表达式语句移除
        """
        if not isinstance(block, HIRBlockExpr):
            return False
        if not block.exprs or len(block.exprs) < 2:
            return False

        changed = False
        exprs = block.exprs

        # 收集最后一个表达式使用的变量（块的结果总是保留）
        used_names = set()
        self._collect_used_names(exprs[-1], used_names)

        # 从倒数第二个往前扫
        new_exprs = [exprs[-1]]  # 最后一个先放进去
        for i in range(len(exprs) - 2, -1, -1):
            expr = exprs[i]

            if isinstance(expr, HIRLetDecl):
                # let 绑定：检查名字是否被使用
                if expr.name in used_names:
                    # 被使用了，保留，并收集其 value 中使用的变量
                    new_exprs.append(expr)
                    self._collect_used_names(expr.value, used_names)
                elif self._has_side_effect(expr.value):
                    # 有副作用，即使未使用也保留
                    new_exprs.append(expr)
                    self._collect_used_names(expr.value, used_names)
                else:
                    # 未使用且无副作用 → 移除
                    changed = True
            else:
                # 普通表达式语句
                if self._has_side_effect(expr):
                    # 有副作用，保留
                    new_exprs.append(expr)
                    self._collect_used_names(expr, used_names)
                else:
                    # 无副作用的语句 → 移除
                    changed = True

        # 反转回正确顺序
        if changed:
            new_exprs.reverse()
            block.exprs = new_exprs

        return changed

    def _collect_used_names(self, expr, used):
        """收集表达式中所有被使用的变量名"""
        if isinstance(expr, HIRIdentifier):
            used.add(expr.name)
        elif isinstance(expr, HIRBinaryOp):
            self._collect_used_names(expr.left, used)
            self._collect_used_names(expr.right, used)
        elif isinstance(expr, HIRUnaryOp):
            self._collect_used_names(expr.operand, used)
        elif isinstance(expr, HIRBlockExpr):
            for sub in expr.exprs:
                self._collect_used_names(sub, used)
        elif isinstance(expr, HIRIfExpr):
            self._collect_used_names(expr.condition, used)
            self._collect_used_names(expr.consequence, used)
            self._collect_used_names(expr.alternative, used)
        elif isinstance(expr, HIRCallExpr):
            self._collect_used_names(expr.callee, used)
            for arg in expr.args:
                self._collect_used_names(arg, used)
        elif isinstance(expr, HIRLambda):
            self._collect_used_names(expr.body, used)
            # 注意：不把参数名加入 used（它们是新绑定）
        elif isinstance(expr, HIRForExpr):
            self._collect_used_names(expr.iterable, used)
            self._collect_used_names(expr.body, used)
            if expr.step:
                self._collect_used_names(expr.step, used)
        elif isinstance(expr, HIRWhileExpr):
            self._collect_used_names(expr.condition, used)
            self._collect_used_names(expr.body, used)
        elif isinstance(expr, HIRLetDecl):
            self._collect_used_names(expr.value, used)
        elif isinstance(expr, HIRListExpr):
            for item in expr.items:
                self._collect_used_names(item, used)
        elif isinstance(expr, HIRTupleExpr):
            for item in expr.items:
                self._collect_used_names(item, used)
        elif isinstance(expr, HIRMapExpr):
            for key, val in expr.pairs:
                self._collect_used_names(key, used)
                self._collect_used_names(val, used)
        elif isinstance(expr, HIRFieldExpr):
            self._collect_used_names(expr.object, used)
        elif isinstance(expr, HIRIndexExpr):
            self._collect_used_names(expr.collection, used)
            self._collect_used_names(expr.index, used)
        elif isinstance(expr, HIRMatchExpr):
            self._collect_used_names(expr.scrutinee, used)
            for arm in expr.arms:
                self._collect_used_names(arm.body, used)
        elif isinstance(expr, HIRAssignExpr):
            self._collect_used_names(expr.value, used)
            # 注意：赋值的目标也是一个使用（写使用）
            if isinstance(expr.target, HIRIdentifier):
                used.add(expr.target.name)
        elif isinstance(expr, HIRPipeExpr):
            self._collect_used_names(expr.left, used)
            self._collect_used_names(expr.right, used)
        elif isinstance(expr, HIRADTConstructor):
            for arg in expr.args:
                self._collect_used_names(arg, used)
        elif isinstance(expr, HIRUnwrapExpr):
            self._collect_used_names(expr.operand, used)
        elif isinstance(expr, HIRListComprehension):
            self._collect_used_names(expr.expr, used)
            self._collect_used_names(expr.iterable, used)
        # 字面量: 不添加任何名字

    def _has_side_effect(self, expr):
        """判断表达式是否有副作用"""
        # 函数调用有副作用
        if isinstance(expr, HIRCallExpr):
            return True
        # 赋值有副作用
        if isinstance(expr, HIRAssignExpr):
            return True
        # Unwrap 可能 panic
        if isinstance(expr, HIRUnwrapExpr):
            return True
        # For/While 循环体可能有副作用
        if isinstance(expr, HIRForExpr) or isinstance(expr, HIRWhileExpr):
            return True
        # 块：检查其中是否有副作用
        if isinstance(expr, HIRBlockExpr):
            return any(self._has_side_effect(e) for e in expr.exprs)
        # If：两个分支任一有副作用
        if isinstance(expr, HIRIfExpr):
            return self._has_side_effect(expr.consequence) or self._has_side_effect(expr.alternative)
        # 纯二元运算
        if isinstance(expr, HIRBinaryOp):
            if expr.op in self.PURE_BINOPS:
                return self._has_side_effect(expr.left) or self._has_side_effect(expr.right)
            return True  # 未知操作符，保守认为有副作用
        # 纯一元运算
        if isinstance(expr, HIRUnaryOp):
            if expr.op in self.PURE_UNARYOPS:
                return self._has_side_effect(expr.operand)
            return True
        # 字面量：无副作用
        if isinstance(expr, (
            HIRIntLiteral, HIRFloatLiteral, HIRStringLiteral,
            HIRBoolLiteral, HIRCharLiteral, HIRUnitLiteral,
            HIRIdentifier,
        )):
            return False
        # 列表/元组/映射：检查子表达式
        if isinstance(expr, HIRListExpr):
            return any(self._has_side_effect(e) for e in expr.items)
        if isinstance(expr, HIRTupleExpr):
            return any(self._has_side_effect(e) for e in expr.items)
        if isinstance(expr, HIRMapExpr):
            return any(self._has_side_effect(k) or self._has_side_effect(v) for k, v in expr.pairs)
        # 字段/索引访问：纯操作
        if isinstance(expr, HIRFieldExpr):
            return self._has_side_effect(expr.object)
        if isinstance(expr, HIRIndexExpr):
            return self._has_side_effect(expr.collection) or self._has_side_effect(expr.index)
        # Lambda 本身无副作用（调用才有）
        if isinstance(expr, HIRLambda):
            return False
        # Match：检查 scrutinee 和所有 arm
        if isinstance(expr, HIRMatchExpr):
            if self._has_side_effect(expr.scrutinee):
                return True
            return any(self._has_side_effect(arm.body) for arm in expr.arms)
        # ADT 构造：纯操作
        if isinstance(expr, HIRADTConstructor):
            return any(self._has_side_effect(a) for a in expr.args)
        # 管道：取决于两端
        if isinstance(expr, HIRPipeExpr):
            return self._has_side_effect(expr.left) or self._has_side_effect(expr.right)
        # 列表推导式
        if isinstance(expr, HIRListComprehension):
            return self._has_side_effect(expr.expr) or self._has_side_effect(expr.iterable)
        # let 声明：取决于 value
        if isinstance(expr, HIRLetDecl):
            return self._has_side_effect(expr.value)
        # 保守默认：有副作用
        return True


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
