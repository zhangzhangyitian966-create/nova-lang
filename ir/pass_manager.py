"""
Nova Pass 管理器

支持在 HIR/MIR/LIR 各层插入优化 Pass。
Pass 管理器负责按序运行各层 Pass，并在达到不动点（无新变化）时停止。
"""

import sys
import warnings

from ir_nodes import (
    FLOAT_TYPE,
    INT_TYPE,
    HIRADTConstructor,
    HIRAssignExpr,
    HIRBinaryOp,
    HIRBlockExpr,
    HIRBoolLiteral,
    HIRCallExpr,
    HIRCharLiteral,
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
    通过将函数调用替换为函数体（参数替换为实际参数）来减少函数调用开销。
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
            # 如果 block 只有一个表达式（单表达式块）
            if len(body.exprs) == 1:
                return True
            return False
        # 单个表达式
        return True

    def _inline_in_fn(self, fn, inlineable):
        """在函数体内联调用"""
        new_body, changed = self._try_inline_expr(fn.body, inlineable)
        if changed:
            fn.body = new_body
        return changed

    def _try_inline_expr(self, expr, inlineable):
        """尝试内联表达式中的调用，返回 (new_expr, changed)"""
        changed = False

        if isinstance(expr, HIRCallExpr):
            # 先递归处理参数
            new_args = []
            for arg in expr.arguments:
                new_arg, arg_changed = self._try_inline_expr(arg, inlineable)
                new_args.append(new_arg)
                changed |= arg_changed

            # 检查是否是可内联的函数
            if isinstance(expr.function, HIRIdentifier):
                fn_name = expr.function.name
                if fn_name in inlineable:
                    target_fn = inlineable[fn_name]
                    # 执行内联：用参数替换后的函数体替换调用
                    inlined = self._inline_function(target_fn, new_args, inlineable)
                    if inlined is not None:
                        return inlined, True

            # 不可内联，返回更新后的调用
            if changed:
                new_call = HIRCallExpr(expr.function, new_args)
                new_call.ir_type = expr.ir_type
                return new_call, True
            return expr, False

        elif isinstance(expr, HIRBinaryOp):
            new_left, left_changed = self._try_inline_expr(expr.left, inlineable)
            new_right, right_changed = self._try_inline_expr(expr.right, inlineable)
            if left_changed or right_changed:
                new_expr = HIRBinaryOp(expr.op, new_left, new_right)
                new_expr.ir_type = expr.ir_type
                return new_expr, True
            return expr, False

        elif isinstance(expr, HIRUnaryOp):
            new_operand, op_changed = self._try_inline_expr(expr.operand, inlineable)
            if op_changed:
                new_expr = HIRUnaryOp(expr.op, new_operand)
                new_expr.ir_type = expr.ir_type
                return new_expr, True
            return expr, False

        elif isinstance(expr, HIRIfExpr):
            new_cond, cond_changed = self._try_inline_expr(expr.condition, inlineable)
            new_cons, cons_changed = self._try_inline_expr(expr.consequence, inlineable)
            new_alt = None
            alt_changed = False
            if expr.alternative:
                new_alt, alt_changed = self._try_inline_expr(
                    expr.alternative, inlineable
                )
            if cond_changed or cons_changed or alt_changed:
                new_expr = HIRIfExpr(new_cond, new_cons, new_alt)
                new_expr.ir_type = expr.ir_type
                return new_expr, True
            return expr, False

        elif isinstance(expr, HIRBlockExpr):
            new_exprs = []
            block_changed = False
            for e in expr.exprs:
                new_e, e_changed = self._try_inline_expr(e, inlineable)
                new_exprs.append(new_e)
                block_changed |= e_changed
            if block_changed:
                new_block = HIRBlockExpr(new_exprs)
                new_block.ir_type = expr.ir_type
                return new_block, True
            return expr, False

        elif isinstance(expr, HIRLetDecl):
            # 处理 let 绑定的值表达式
            new_value, val_changed = self._try_inline_expr(expr.value, inlineable)
            if val_changed:
                new_let = HIRLetDecl(
                    expr.name, new_value, expr.ir_type, is_mutable=expr.is_mutable
                )
                return new_let, True
            return expr, False

        elif isinstance(expr, HIRAssignExpr):
            new_val, val_changed = self._try_inline_expr(expr.value, inlineable)
            if val_changed:
                new_assign = HIRAssignExpr(expr.target, new_val)
                new_assign.ir_type = expr.ir_type
                return new_assign, True
            return expr, False

        elif isinstance(expr, HIRListExpr):
            new_elems = []
            list_changed = False
            for e in expr.elements:
                new_e, e_changed = self._try_inline_expr(e, inlineable)
                new_elems.append(new_e)
                list_changed |= e_changed
            if list_changed:
                new_list = HIRListExpr(new_elems)
                new_list.ir_type = expr.ir_type
                return new_list, True
            return expr, False

        elif isinstance(expr, HIRTupleExpr):
            new_elems = []
            tup_changed = False
            for e in expr.elements:
                new_e, e_changed = self._try_inline_expr(e, inlineable)
                new_elems.append(new_e)
                tup_changed |= e_changed
            if tup_changed:
                new_tup = HIRTupleExpr(new_elems)
                new_tup.ir_type = expr.ir_type
                return new_tup, True
            return expr, False

        elif isinstance(expr, HIRFieldExpr):
            new_obj, obj_changed = self._try_inline_expr(expr.object, inlineable)
            if obj_changed:
                new_field = HIRFieldExpr(new_obj, expr.field_name)
                new_field.ir_type = expr.ir_type
                return new_field, True
            return expr, False

        elif isinstance(expr, HIRIndexExpr):
            new_obj, obj_changed = self._try_inline_expr(expr.object, inlineable)
            new_idx, idx_changed = self._try_inline_expr(expr.index, inlineable)
            if obj_changed or idx_changed:
                new_idx_expr = HIRIndexExpr(new_obj, new_idx)
                new_idx_expr.ir_type = expr.ir_type
                return new_idx_expr, True
            return expr, False

        elif isinstance(expr, HIRPipeExpr):
            new_stages = []
            pipe_changed = False
            for s in expr.stages:
                new_s, s_changed = self._try_inline_expr(s, inlineable)
                new_stages.append(new_s)
                pipe_changed |= s_changed
            if pipe_changed:
                new_pipe = HIRPipeExpr(new_stages)
                new_pipe.ir_type = expr.ir_type
                return new_pipe, True
            return expr, False

        elif isinstance(expr, HIRMatchExpr):
            new_val, val_changed = self._try_inline_expr(expr.value, inlineable)
            new_arms = []
            arms_changed = False
            for arm in expr.arms:
                new_body, body_changed = self._try_inline_expr(arm.body, inlineable)
                if body_changed:
                    arms_changed = True
                    new_arm = type(arm)(arm.pattern, new_body)
                    new_arms.append(new_arm)
                else:
                    new_arms.append(arm)
            if val_changed or arms_changed:
                new_match = HIRMatchExpr(new_val, new_arms)
                new_match.ir_type = expr.ir_type
                return new_match, True
            return expr, False

        elif isinstance(expr, HIRForExpr):
            new_iter, iter_changed = self._try_inline_expr(expr.iterable, inlineable)
            new_body, body_changed = self._try_inline_expr(expr.body, inlineable)
            if iter_changed or body_changed:
                new_for = HIRForExpr(expr.variable, new_iter, new_body)
                new_for.ir_type = expr.ir_type
                return new_for, True
            return expr, False

        elif isinstance(expr, HIRWhileExpr):
            new_cond, cond_changed = self._try_inline_expr(expr.condition, inlineable)
            new_body, body_changed = self._try_inline_expr(expr.body, inlineable)
            if cond_changed or body_changed:
                new_while = HIRWhileExpr(new_cond, new_body)
                new_while.ir_type = expr.ir_type
                return new_while, True
            return expr, False

        elif isinstance(expr, HIRListComprehension):
            new_result, result_changed = self._try_inline_expr(
                expr.result_expr, inlineable
            )
            new_iter, iter_changed = self._try_inline_expr(expr.iterable, inlineable)
            new_filter = None
            filter_changed = False
            if expr.filter:
                new_filter, filter_changed = self._try_inline_expr(
                    expr.filter, inlineable
                )
            if result_changed or iter_changed or filter_changed:
                new_lc = HIRListComprehension(
                    new_result, expr.variable, new_iter, filter=new_filter
                )
                new_lc.ir_type = expr.ir_type
                return new_lc, True
            return expr, False

        # 叶子节点（字面量、标识符等）直接返回
        return expr, False

    def _inline_function(self, target_fn, args, inlineable):
        """
        将函数体内联展开，用实际参数替换形参。
        返回内联后的表达式，如果无法内联返回 None。
        """
        body = target_fn.body
        params = target_fn.params

        # 构建参数映射：参数名 -> 实际参数表达式
        param_map = {}
        for i, (param_name, _) in enumerate(params):
            if i < len(args):
                param_map[param_name] = args[i]

        # 如果是 block，取第一个（也是唯一一个）表达式
        if isinstance(body, HIRBlockExpr) and len(body.exprs) == 1:
            body_expr = body.exprs[0]
        else:
            body_expr = body

        # 深拷贝并替换参数
        return self._substitute_params(body_expr, param_map)

    def _substitute_params(self, expr, param_map):
        """
        递归替换表达式中的参数引用为实际参数。
        这是一个浅拷贝 + 递归替换的过程。
        """
        if isinstance(expr, HIRIdentifier):
            if expr.name in param_map:
                # 返回参数表达式（注意：这是直接引用，不是深拷贝
                # 对于简单内联来说足够，因为参数在调用点只出现一次
                return param_map[expr.name]
            return expr

        elif isinstance(expr, HIRCallExpr):
            new_function = self._substitute_params(expr.function, param_map)
            new_args = [self._substitute_params(a, param_map) for a in expr.arguments]
            if new_function is not expr.function or any(
                a is not old for a, old in zip(new_args, expr.arguments)
            ):
                new_call = HIRCallExpr(new_function, new_args)
                new_call.ir_type = expr.ir_type
                return new_call
            return expr

        elif isinstance(expr, HIRBinaryOp):
            new_left = self._substitute_params(expr.left, param_map)
            new_right = self._substitute_params(expr.right, param_map)
            if new_left is not expr.left or new_right is not expr.right:
                new_expr = HIRBinaryOp(expr.op, new_left, new_right)
                new_expr.ir_type = expr.ir_type
                return new_expr
            return expr

        elif isinstance(expr, HIRUnaryOp):
            new_operand = self._substitute_params(expr.operand, param_map)
            if new_operand is not expr.operand:
                new_expr = HIRUnaryOp(expr.op, new_operand)
                new_expr.ir_type = expr.ir_type
                return new_expr
            return expr

        elif isinstance(expr, HIRIfExpr):
            new_cond = self._substitute_params(expr.condition, param_map)
            new_cons = self._substitute_params(expr.consequence, param_map)
            new_alt = (
                self._substitute_params(expr.alternative, param_map)
                if expr.alternative
                else None
            )
            if (
                new_cond is not expr.condition
                or new_cons is not expr.consequence
                or new_alt is not expr.alternative
            ):
                new_expr = HIRIfExpr(new_cond, new_cons, new_alt)
                new_expr.ir_type = expr.ir_type
                return new_expr
            return expr

        elif isinstance(expr, HIRBlockExpr):
            new_exprs = [self._substitute_params(e, param_map) for e in expr.exprs]
            if any(n is not o for n, o in zip(new_exprs, expr.exprs)):
                new_block = HIRBlockExpr(new_exprs)
                new_block.ir_type = expr.ir_type
                return new_block
            return expr

        elif isinstance(expr, HIRListExpr):
            new_elems = [self._substitute_params(e, param_map) for e in expr.elements]
            if any(n is not o for n, o in zip(new_elems, expr.elements)):
                new_list = HIRListExpr(new_elems)
                new_list.ir_type = expr.ir_type
                return new_list
            return expr

        # 其他类型（字面量等）直接返回
        return expr


class DeadCodeElimination(Pass):
    """死代码消除

    移除未使用的 let 绑定和无副作用的表达式语句。
    采用反向扫描：从块的最后一个表达式（结果）出发，
    收集所有被使用的变量，未被使用且无副作用的绑定被移除。
    """

    name = "dead_code_elimination"

    # 纯操作符（无副作用）
    PURE_BINOPS = {
        "+",
        "-",
        "*",
        "/",
        "%",
        "==",
        "!=",
        "<",
        ">",
        "<=",
        ">=",
        "&&",
        "||",
        "++",
        "::",
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
            changed |= self._eliminate_expr(expr.value)
            for arm in expr.arms:
                changed |= self._eliminate_expr(arm.body)

        # Call: 处理 callee 和 args（函数调用有副作用，不消除）
        elif isinstance(expr, HIRCallExpr):
            changed |= self._eliminate_expr(expr.function)
            for arg in expr.arguments:
                changed |= self._eliminate_expr(arg)

        # 二元/一元运算
        elif isinstance(expr, HIRBinaryOp):
            changed |= self._eliminate_expr(expr.left)
            changed |= self._eliminate_expr(expr.right)
        elif isinstance(expr, HIRUnaryOp):
            changed |= self._eliminate_expr(expr.operand)

        # 列表/元组/映射
        elif isinstance(expr, HIRListExpr):
            for item in expr.elements:
                changed |= self._eliminate_expr(item)
        elif isinstance(expr, HIRTupleExpr):
            for item in expr.elements:
                changed |= self._eliminate_expr(item)
        elif isinstance(expr, HIRMapExpr):
            for key, val in expr.entries:
                changed |= self._eliminate_expr(key)
                changed |= self._eliminate_expr(val)

        # 字段/索引
        elif isinstance(expr, HIRFieldExpr):
            changed |= self._eliminate_expr(expr.object)
        elif isinstance(expr, HIRIndexExpr):
            changed |= self._eliminate_expr(expr.object)
            changed |= self._eliminate_expr(expr.index)

        # 管道
        elif isinstance(expr, HIRPipeExpr):
            for stage in expr.stages:
                changed |= self._eliminate_expr(stage)

        # 赋值（有副作用，不消除）
        elif isinstance(expr, HIRAssignExpr):
            changed |= self._eliminate_expr(expr.value)

        # ADT 构造（纯操作）
        elif isinstance(expr, HIRADTConstructor):
            for arg in expr.fields:
                changed |= self._eliminate_expr(arg)

        # Unwrap（可能 panic，有副作用）
        elif isinstance(expr, HIRUnwrapExpr):
            changed |= self._eliminate_expr(expr.operand)

        # 列表推导式
        elif isinstance(expr, HIRListComprehension):
            changed |= self._eliminate_expr(expr.result_expr)
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
            self._collect_used_names(expr.function, used)
            for arg in expr.arguments:
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
            for item in expr.elements:
                self._collect_used_names(item, used)
        elif isinstance(expr, HIRTupleExpr):
            for item in expr.elements:
                self._collect_used_names(item, used)
        elif isinstance(expr, HIRMapExpr):
            for key, val in expr.entries:
                self._collect_used_names(key, used)
                self._collect_used_names(val, used)
        elif isinstance(expr, HIRFieldExpr):
            self._collect_used_names(expr.object, used)
        elif isinstance(expr, HIRIndexExpr):
            self._collect_used_names(expr.object, used)
            self._collect_used_names(expr.index, used)
        elif isinstance(expr, HIRMatchExpr):
            self._collect_used_names(expr.value, used)
            for arm in expr.arms:
                self._collect_used_names(arm.body, used)
        elif isinstance(expr, HIRAssignExpr):
            self._collect_used_names(expr.value, used)
            # 注意：赋值的目标也是一个使用（写使用）
            if isinstance(expr.target, HIRIdentifier):
                used.add(expr.target.name)
        elif isinstance(expr, HIRPipeExpr):
            for stage in expr.stages:
                self._collect_used_names(stage, used)
        elif isinstance(expr, HIRADTConstructor):
            for arg in expr.fields:
                self._collect_used_names(arg, used)
        elif isinstance(expr, HIRUnwrapExpr):
            self._collect_used_names(expr.operand, used)
        elif isinstance(expr, HIRListComprehension):
            self._collect_used_names(expr.result_expr, used)
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
            return self._has_side_effect(expr.consequence) or self._has_side_effect(
                expr.alternative
            )
        # 纯二元运算
        if isinstance(expr, HIRBinaryOp):
            if expr.op in self.PURE_BINOPS:
                return self._has_side_effect(expr.left) or self._has_side_effect(
                    expr.right
                )
            return True  # 未知操作符，保守认为有副作用
        # 纯一元运算
        if isinstance(expr, HIRUnaryOp):
            if expr.op in self.PURE_UNARYOPS:
                return self._has_side_effect(expr.operand)
            return True
        # 字面量：无副作用
        if isinstance(
            expr,
            (
                HIRIntLiteral,
                HIRFloatLiteral,
                HIRStringLiteral,
                HIRBoolLiteral,
                HIRCharLiteral,
                HIRUnitLiteral,
                HIRIdentifier,
            ),
        ):
            return False
        # 列表/元组/映射：检查子表达式
        if isinstance(expr, HIRListExpr):
            return any(self._has_side_effect(e) for e in expr.elements)
        if isinstance(expr, HIRTupleExpr):
            return any(self._has_side_effect(e) for e in expr.elements)
        if isinstance(expr, HIRMapExpr):
            return any(
                self._has_side_effect(k) or self._has_side_effect(v)
                for k, v in expr.entries
            )
        # 字段/索引访问：纯操作
        if isinstance(expr, HIRFieldExpr):
            return self._has_side_effect(expr.object)
        if isinstance(expr, HIRIndexExpr):
            return self._has_side_effect(expr.object) or self._has_side_effect(
                expr.index
            )
        # Lambda 本身无副作用（调用才有）
        if isinstance(expr, HIRLambda):
            return False
        # Match：检查 scrutinee 和所有 arm
        if isinstance(expr, HIRMatchExpr):
            if self._has_side_effect(expr.value):
                return True
            return any(self._has_side_effect(arm.body) for arm in expr.arms)
        # ADT 构造：纯操作
        if isinstance(expr, HIRADTConstructor):
            return any(self._has_side_effect(a) for a in expr.fields)
        # 管道：取决于两端
        if isinstance(expr, HIRPipeExpr):
            return any(self._has_side_effect(s) for s in expr.stages)
        # 列表推导式
        if isinstance(expr, HIRListComprehension):
            return self._has_side_effect(expr.result_expr) or self._has_side_effect(
                expr.iterable
            )
        # let 声明：取决于 value
        if isinstance(expr, HIRLetDecl):
            return self._has_side_effect(expr.value)
        # 保守默认：有副作用
        return True


class CommonSubexprElimination(Pass):
    """公共子表达式消除（CSE）

    在 MIR 层执行基于值编号的局部公共子表达式消除。
    对于每个基本块内的纯运算指令，如果相同的表达式已被计算过，
    则直接复用之前的结果，避免重复计算。

    支持的可消除指令：
    - MIRBinOp: 二元运算（算术、比较、逻辑）
    - MIRUnaryOp: 一元运算
    - MIRFieldAccess: 字段访问（对象不可变时安全）
    - MIRIndexAccess: 索引访问（列表不可变时安全）
    - MIRTupleBuild: 元组构建（元素相同则元组相同）
    """

    name = "cse"

    def run(self, mir_module):
        """对 MIR 模块执行 CSE，返回是否发生了变化"""
        changed = False
        for fn_name, mir_fn in mir_module.functions.items():
            changed |= self._cse_function(mir_fn)
        return changed

    def _cse_function(self, mir_fn):
        """对单个函数执行 CSE"""
        changed = False
        for bb in mir_fn.basic_blocks:
            changed |= self._cse_basic_block(bb)
        return changed

    def _cse_basic_block(self, bb):
        """对单个基本块执行局部 CSE

        使用值编号：维护表达式指纹 -> SSA 名 的映射。
        如果发现重复的表达式，将后续指令中对该结果的引用替换为已有的 SSA 名。
        """
        changed = False
        # 值编号表: 表达式指纹 -> 已存在的 SSA 名
        value_table = {}
        # 替换映射: 被消除的 SSA 名 -> 复用的 SSA 名
        replacements = {}

        new_instructions = []
        for instr in bb.instructions:
            # 先替换指令中引用的 SSA 名（处理之前被消除的指令）
            self._replace_instr_operands(instr, replacements)

            # 尝试计算表达式指纹
            fingerprint = self._compute_fingerprint(instr)

            if fingerprint is not None and instr.result_name:
                if fingerprint in value_table:
                    # 找到相同的表达式，复用已有的结果
                    existing_ssa = value_table[fingerprint]
                    replacements[instr.result_name] = existing_ssa
                    changed = True
                    # 跳过这条指令（不加入 new_instructions）
                    continue
                else:
                    # 新的表达式，加入值编号表
                    value_table[fingerprint] = instr.result_name

            new_instructions.append(instr)

        # 如果有变化，更新基本块的指令列表
        if changed:
            bb.instructions = new_instructions

            # 更新终结指令中的操作数引用
            if bb.terminator:
                self._replace_terminator_operands(bb.terminator, replacements)

        return changed

    def _compute_fingerprint(self, instr):
        """计算指令的表达式指纹，用于判断是否为重复的公共子表达式

        返回 None 表示该指令不可做 CSE（有副作用或不适合）。
        """
        # 延迟导入，避免循环依赖
        from ir_nodes import (
            MIRBinOp,
            MIRFieldAccess,
            MIRIndexAccess,
            MIRTupleBuild,
            MIRUnaryOp,
        )

        if isinstance(instr, MIRBinOp):
            # 可交换运算（+、*、==、!=）不区分左右顺序
            commutative_ops = {"+", "*", "==", "!=", "&&", "||"}
            if instr.op in commutative_ops and instr.left > instr.right:
                return ("binop", instr.op, instr.right, instr.left)
            return ("binop", instr.op, instr.left, instr.right)

        elif isinstance(instr, MIRUnaryOp):
            return ("unaryop", instr.op, instr.operand)

        elif isinstance(instr, MIRFieldAccess):
            return ("field", instr.object, instr.field_name, instr.field_index)

        elif isinstance(instr, MIRIndexAccess):
            return ("index", instr.object, instr.index)

        elif isinstance(instr, MIRTupleBuild):
            # 元组构建：元素顺序相同则相同
            return ("tuple", tuple(instr.elements))

        # 其他类型不做 CSE
        return None

    def _replace_instr_operands(self, instr, replacements):
        """替换指令中的操作数 SSA 名

        将出现在 replacements 中的 SSA 名替换为对应的值。
        """
        if not replacements:
            return

        # 延迟导入
        from ir_nodes import (
            MIRADTBuild,
            MIRBinOp,
            MIRCall,
            MIRClosureCreate,
            MIRFieldAccess,
            MIRIndexAccess,
            MIRListAppend,
            MIRListBuild,
            MIRMapBuild,
            MIRPhi,
            MIRStore,
            MIRTupleBuild,
            MIRUnaryOp,
        )

        if isinstance(instr, MIRBinOp):
            if instr.left in replacements:
                instr.left = replacements[instr.left]
            if instr.right in replacements:
                instr.right = replacements[instr.right]

        elif isinstance(instr, MIRUnaryOp):
            if instr.operand in replacements:
                instr.operand = replacements[instr.operand]

        elif isinstance(instr, MIRCall):
            instr.args = [
                replacements[a] if a in replacements else a for a in instr.args
            ]
            if instr.callee in replacements:
                instr.callee = replacements[instr.callee]

        elif isinstance(instr, MIRFieldAccess):
            if instr.object in replacements:
                instr.object = replacements[instr.object]

        elif isinstance(instr, MIRIndexAccess):
            if instr.object in replacements:
                instr.object = replacements[instr.object]
            if instr.index in replacements:
                instr.index = replacements[instr.index]

        elif isinstance(instr, MIRListBuild):
            instr.elements = [
                replacements[e] if e in replacements else e for e in instr.elements
            ]

        elif isinstance(instr, MIRListAppend):
            if instr.list_ssa in replacements:
                instr.list_ssa = replacements[instr.list_ssa]
            if instr.element_ssa in replacements:
                instr.element_ssa = replacements[instr.element_ssa]

        elif isinstance(instr, MIRTupleBuild):
            instr.elements = [
                replacements[e] if e in replacements else e for e in instr.elements
            ]

        elif isinstance(instr, MIRMapBuild):
            instr.entries = [
                (
                    replacements[k] if k in replacements else k,
                    replacements[v] if v in replacements else v,
                )
                for k, v in instr.entries
            ]

        elif isinstance(instr, MIRADTBuild):
            instr.fields = [
                replacements[f] if f in replacements else f for f in instr.fields
            ]

        elif isinstance(instr, MIRClosureCreate):
            instr.captures = [
                replacements[c] if c in replacements else c for c in instr.captures
            ]

        elif isinstance(instr, MIRStore):
            if instr.value in replacements:
                instr.value = replacements[instr.value]

        elif isinstance(instr, MIRPhi):
            instr.sources = [
                (label, replacements[ssa] if ssa in replacements else ssa)
                for label, ssa in instr.sources
            ]

    def _replace_terminator_operands(self, terminator, replacements):
        """替换终结指令中的操作数 SSA 名"""
        if not replacements:
            return

        from ir_nodes import MIRBranch, MIRMatchJump, MIRReturn, MIRSwitch

        if isinstance(terminator, MIRBranch):
            if terminator.condition in replacements:
                terminator.condition = replacements[terminator.condition]

        elif isinstance(terminator, MIRSwitch):
            if terminator.value in replacements:
                terminator.value = replacements[terminator.value]

        elif isinstance(terminator, MIRReturn):
            if terminator.value and terminator.value in replacements:
                terminator.value = replacements[terminator.value]

        elif isinstance(terminator, MIRMatchJump):
            if terminator.value in replacements:
                terminator.value = replacements[terminator.value]


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
        # Pass 失败统计：{pass_name: 失败次数}
        self._pass_failures = {}

    def add_hir_pass(self, pass_):
        self.hir_passes.append(pass_)

    def add_mir_pass(self, pass_):
        self.mir_passes.append(pass_)

    def add_lir_pass(self, pass_):
        self.lir_passes.append(pass_)

    def set_verbose(self, verbose: bool):
        """设置是否输出详细日志"""
        self._verbose = verbose

    def get_failure_stats(self) -> dict:
        """获取 Pass 失败统计"""
        return dict(self._pass_failures)

    def _record_pass_failure(self, pass_name: str, exc: Exception):
        """记录 Pass 失败并输出警告"""
        self._pass_failures[pass_name] = self._pass_failures.get(pass_name, 0) + 1
        count = self._pass_failures[pass_name]
        msg = f"[PassWarning] {pass_name} 执行失败 (第{count}次): {type(exc).__name__}: {exc}"
        if self._verbose:
            print(msg, file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)
        else:
            warnings.warn(msg, stacklevel=3)

    def run_hir_passes(self, hir_module, max_iterations=10):
        total_changed = False
        for iteration in range(max_iterations):
            changed = False
            for pass_ in self.hir_passes:
                pass_name = pass_.__class__.__name__
                try:
                    changed |= pass_.run(hir_module)
                except Exception as e:
                    self._record_pass_failure(pass_name, e)
            if not changed:
                break
            total_changed = True
        return total_changed

    def run_mir_passes(self, mir_module, max_iterations=10):
        total_changed = False
        for iteration in range(max_iterations):
            changed = False
            for pass_ in self.mir_passes:
                pass_name = pass_.__class__.__name__
                try:
                    changed |= pass_.run(mir_module)
                except Exception as e:
                    self._record_pass_failure(pass_name, e)
            if not changed:
                break
            total_changed = True
        return total_changed

    def run_lir_passes(self, lir_module, max_iterations=10):
        total_changed = False
        for iteration in range(max_iterations):
            changed = False
            for pass_ in self.lir_passes:
                pass_name = pass_.__class__.__name__
                try:
                    changed |= pass_.run(lir_module)
                except Exception as e:
                    self._record_pass_failure(pass_name, e)
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
