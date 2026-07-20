"""
Nova Pass 管理器

支持在 HIR/MIR/LIR 各层插入优化 Pass。
Pass 管理器负责按序运行各层 Pass，并在达到不动点（无新变化）时停止。
"""

import sys
import warnings

from .ir_nodes import (
    FLOAT_TYPE,
    INT_TYPE,
    HIRADTConstructor,
    HIRBinaryOp,
    HIRBlockExpr,
    HIRBoolLiteral,
    HIRCallExpr,
    HIRFnDecl,
    HIRIdentifier,
    HIRIntLiteral,
    HIRFloatLiteral,
    HIRLetDecl,
    HIRRewriter,
    HIRVisitor,
)


class Pass:
    """优化 Pass 基类"""

    name = ""

    def run(self, module) -> bool:
        raise NotImplementedError


class ConstantFolding(Pass, HIRRewriter):
    """常量折叠

    继承 HIRRewriter，只需重写 HIRBinaryOp 的变换逻辑，
    其余节点的递归遍历由基类 generic_rewrite 处理。
    """

    name = "constant_folding"

    def run(self, hir_module):
        changed = False
        for decl in hir_module.declarations:
            if isinstance(decl, HIRFnDecl):
                new_body, body_changed = self.rewrite(decl.fn_def.body)
                if body_changed:
                    decl.fn_def.body = new_body
                    changed = True
            elif isinstance(decl, HIRLetDecl):
                new_value, val_changed = self.rewrite(decl.value)
                if val_changed:
                    decl.value = new_value
                    changed = True
        return changed

    def rewrite_HIRBinaryOp(self, expr):
        """对二元运算做常量折叠"""
        # 先递归变换子表达式
        new_left, left_changed = self.rewrite(expr.left)
        new_right, right_changed = self.rewrite(expr.right)
        changed = left_changed or right_changed

        if changed:
            expr = HIRBinaryOp(expr.op, new_left, new_right)
            expr.ir_type = new_left.ir_type if hasattr(new_left, "ir_type") else expr.ir_type

        # int 常量折叠
        if isinstance(expr.left, HIRIntLiteral) and isinstance(
            expr.right, HIRIntLiteral
        ):
            result = self._eval_int_binop(expr.op, expr.left.value, expr.right.value)
            if result is not None:
                new_literal = HIRIntLiteral(result)
                new_literal.ir_type = INT_TYPE
                return new_literal, True

        # float 常量折叠
        if isinstance(expr.left, HIRFloatLiteral) and isinstance(
            expr.right, HIRFloatLiteral
        ):
            result = self._eval_float_binop(expr.op, expr.left.value, expr.right.value)
            if result is not None:
                new_literal = HIRFloatLiteral(result)
                new_literal.ir_type = FLOAT_TYPE
                return new_literal, True

        return expr, changed

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


class Inlining(Pass, HIRRewriter):
    """函数内联

    内联小型函数（单表达式函数体、无递归、参数少）。
    通过将函数调用替换为函数体（参数替换为实际参数）来减少函数调用开销。

    继承 HIRRewriter，只需重写 HIRCallExpr 的变换逻辑，
    其余节点的递归遍历由基类 generic_rewrite 处理。
    """

    name = "inlining"
    MAX_INLINE_SIZE = 3  # 最多内联 3 个表达式大小的函数

    def __init__(self):
        self._inlineable = {}  # 可内联函数字典

    def run(self, hir_module):
        changed = False
        # 收集所有可内联的函数
        self._inlineable = {}
        for decl in hir_module.declarations:
            if isinstance(decl, HIRFnDecl):
                fn = decl.fn_def
                if self._is_inlineable(fn):
                    self._inlineable[fn.name] = fn

        if not self._inlineable:
            return False

        # 在每个函数中尝试内联调用
        for decl in hir_module.declarations:
            if isinstance(decl, HIRFnDecl):
                new_body, body_changed = self.rewrite(decl.fn_def.body)
                if body_changed:
                    decl.fn_def.body = new_body
                    changed = True

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

    def rewrite_HIRCallExpr(self, expr):
        """对函数调用尝试内联"""
        # 先递归处理参数和 callee（由 generic_rewrite 处理）
        new_expr, args_changed = self.generic_rewrite(expr)

        # 检查是否是可内联的函数
        if isinstance(new_expr.function, HIRIdentifier):
            fn_name = new_expr.function.name
            if fn_name in self._inlineable:
                target_fn = self._inlineable[fn_name]
                # 执行内联：用参数替换后的函数体替换调用
                inlined = self._inline_function(target_fn, new_expr.arguments)
                if inlined is not None:
                    return inlined, True

        return new_expr, args_changed

    def _inline_function(self, target_fn, args):
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

        # 使用 ParamSubstitutor 进行参数替换
        substitutor = _ParamSubstitutor(param_map)
        result, _ = substitutor.rewrite(body_expr)
        return result


class _ParamSubstitutor(HIRRewriter):
    """参数替换器：将标识符替换为对应的实际参数表达式

    用于内联时的参数替换，继承 HIRRewriter 自动处理递归遍历。
    """

    def __init__(self, param_map):
        self.param_map = param_map

    def rewrite_HIRIdentifier(self, expr):
        """如果标识符在参数映射中，替换为实际参数"""
        if expr.name in self.param_map:
            return self.param_map[expr.name], True
        return expr, False


class DeadCodeElimination(Pass, HIRRewriter):
    """死代码消除

    移除未使用的 let 绑定和无副作用的表达式语句。
    采用反向扫描：从块的最后一个表达式（结果）出发，
    收集所有被使用的变量，未被使用且无副作用的绑定被移除。

    继承 HIRRewriter，Block 的消除逻辑重写在 rewrite_HIRBlockExpr 中，
    其余节点的递归遍历由基类 generic_rewrite 处理。
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
                new_body, body_changed = self.rewrite(decl.fn_def.body)
                if body_changed:
                    decl.fn_def.body = new_body
                    changed = True
            elif isinstance(decl, HIRLetDecl):
                # 顶层 let 不消除（可能是导出的）
                pass
        return changed

    def rewrite_HIRBlockExpr(self, expr):
        """对 Block 做死代码消除，然后递归处理子表达式"""
        # 先消除块内死代码
        block_changed = self._eliminate_block(expr)
        # 再递归处理剩余的表达式
        new_exprs = []
        exprs_changed = False
        for sub in expr.exprs:
            new_sub, sub_changed = self.rewrite(sub)
            new_exprs.append(new_sub)
            exprs_changed |= sub_changed
        if exprs_changed:
            expr.exprs = new_exprs
        return expr, block_changed or exprs_changed

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
        _collect_used_vars(exprs[-1], used_names)

        # 从倒数第二个往前扫
        new_exprs = [exprs[-1]]  # 最后一个先放进去
        for i in range(len(exprs) - 2, -1, -1):
            expr = exprs[i]

            if isinstance(expr, HIRLetDecl):
                # let 绑定：检查名字是否被使用
                if expr.name in used_names:
                    # 被使用了，保留，并收集其 value 中使用的变量
                    new_exprs.append(expr)
                    _collect_used_vars(expr.value, used_names)
                elif _has_side_effect_expr(expr.value, self.PURE_BINOPS, self.PURE_UNARYOPS):
                    # 有副作用，即使未使用也保留
                    new_exprs.append(expr)
                    _collect_used_vars(expr.value, used_names)
                else:
                    # 未使用且无副作用 → 移除
                    changed = True
            else:
                # 普通表达式语句
                if _has_side_effect_expr(expr, self.PURE_BINOPS, self.PURE_UNARYOPS):
                    # 有副作用，保留
                    new_exprs.append(expr)
                    _collect_used_vars(expr, used_names)
                else:
                    # 无副作用的语句 → 移除
                    changed = True

        # 反转回正确顺序
        if changed:
            new_exprs.reverse()
            block.exprs = new_exprs

        return changed


class _UsedNamesCollector(HIRVisitor):
    """变量使用收集器：遍历表达式，收集所有被使用的变量名"""

    def __init__(self):
        self.used = set()

    def visit_HIRIdentifier(self, expr):
        self.used.add(expr.name)

    def visit_HIRAssignExpr(self, expr):
        # 赋值的目标也是一个使用（写使用）
        if isinstance(expr.target, HIRIdentifier):
            self.used.add(expr.target.name)
        self.visit(expr.value)

    def visit_HIRLambda(self, expr):
        # Lambda 的参数是新绑定，不加入 used
        self.visit(expr.body)

    def visit_HIRForExpr(self, expr):
        # for 循环变量是新绑定，不加入 used
        self.visit(expr.iterable)
        self.visit(expr.body)
        if expr.step:
            self.visit(expr.step)

    def visit_HIRLetDecl(self, expr):
        # let 绑定的 name 是新绑定，不加入 used，只收集 value 中的使用
        self.visit(expr.value)


def _collect_used_vars(expr, used):
    """收集表达式中所有被使用的变量名（便捷函数）"""
    collector = _UsedNamesCollector()
    collector.used = used
    collector.visit(expr)


def _has_side_effect_expr(expr, pure_binops, pure_unaryops):
    """判断表达式是否有副作用

    使用递归方式，因为需要根据操作符类型做特殊判断。
    """
    # 函数调用有副作用
    if isinstance(expr, HIRCallExpr):
        return True
    # 赋值有副作用
    if isinstance(expr, HIRIdentifier) and False:
        pass  # 标识符无副作用
    if hasattr(expr, 'target') and hasattr(expr, 'value') and type(expr).__name__ == 'HIRAssignExpr':
        return True
    # Unwrap 可能 panic
    if type(expr).__name__ == 'HIRUnwrapExpr':
        return True
    # For/While 循环体可能有副作用
    if type(expr).__name__ in ('HIRForExpr', 'HIRWhileExpr'):
        return True
    # 块：检查其中是否有副作用
    if isinstance(expr, HIRBlockExpr):
        return any(_has_side_effect_expr(e, pure_binops, pure_unaryops) for e in expr.exprs)
    # If：两个分支任一有副作用
    if type(expr).__name__ == 'HIRIfExpr':
        return _has_side_effect_expr(expr.consequence, pure_binops, pure_unaryops) or _has_side_effect_expr(expr.alternative, pure_binops, pure_unaryops)
    # 纯二元运算
    if isinstance(expr, HIRBinaryOp):
        if expr.op in pure_binops:
            return _has_side_effect_expr(expr.left, pure_binops, pure_unaryops) or _has_side_effect_expr(expr.right, pure_binops, pure_unaryops)
        return True  # 未知操作符，保守认为有副作用
    # 纯一元运算
    if type(expr).__name__ == 'HIRUnaryOp':
        if expr.op in pure_unaryops:
            return _has_side_effect_expr(expr.operand, pure_binops, pure_unaryops)
        return True
    # 字面量/标识符：无副作用
    if isinstance(
        expr,
        (
            HIRIntLiteral,
            HIRFloatLiteral,
            HIRBoolLiteral,
            HIRIdentifier,
        ),
    ):
        return False
    if type(expr).__name__ in ('HIRStringLiteral', 'HIRCharLiteral', 'HIRUnitLiteral'):
        return False
    # 列表/元组/映射：检查子表达式
    if type(expr).__name__ in ('HIRListExpr', 'HIRTupleExpr'):
        return any(_has_side_effect_expr(e, pure_binops, pure_unaryops) for e in expr.elements)
    if type(expr).__name__ == 'HIRMapExpr':
        return any(
            _has_side_effect_expr(k, pure_binops, pure_unaryops) or _has_side_effect_expr(v, pure_binops, pure_unaryops)
            for k, v in expr.entries
        )
    # 字段/索引访问：纯操作
    if type(expr).__name__ == 'HIRFieldExpr':
        return _has_side_effect_expr(expr.object, pure_binops, pure_unaryops)
    if type(expr).__name__ == 'HIRIndexExpr':
        return _has_side_effect_expr(expr.object, pure_binops, pure_unaryops) or _has_side_effect_expr(expr.index, pure_binops, pure_unaryops)
    # Lambda 本身无副作用（调用才有）
    if type(expr).__name__ == 'HIRLambda':
        return False
    # Match：检查 scrutinee 和所有 arm
    if type(expr).__name__ == 'HIRMatchExpr':
        if _has_side_effect_expr(expr.value, pure_binops, pure_unaryops):
            return True
        return any(_has_side_effect_expr(arm.body, pure_binops, pure_unaryops) for arm in expr.arms)
    # ADT 构造：纯操作
    if isinstance(expr, HIRADTConstructor):
        return any(_has_side_effect_expr(a, pure_binops, pure_unaryops) for a in expr.fields)
    # 管道：取决于两端
    if type(expr).__name__ == 'HIRPipeExpr':
        return any(_has_side_effect_expr(s, pure_binops, pure_unaryops) for s in expr.stages)
    # 列表推导式
    if type(expr).__name__ == 'HIRListComprehension':
        return _has_side_effect_expr(expr.result_expr, pure_binops, pure_unaryops) or _has_side_effect_expr(expr.iterable, pure_binops, pure_unaryops)
    # let 声明：取决于 value
    if isinstance(expr, HIRLetDecl):
        return _has_side_effect_expr(expr.value, pure_binops, pure_unaryops)
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
        from .ir_nodes import (
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
        from .ir_nodes import (
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

        from .ir_nodes import MIRBranch, MIRMatchJump, MIRReturn, MIRSwitch

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
    """循环不变量外提（LICM）

    在 MIR 层识别循环结构，将循环体内不变的纯运算指令
    外提到循环前置头（pre-header）中，减少循环内的重复计算。

    实现策略：
    1. 使用 cfg_utils.analyze_loops 进行循环分析（支配树 + 回边 + 自然循环）
    2. 按嵌套层级从内到外处理循环
    3. 对每个循环：
       - 找到或创建 pre-header 块
       - 识别循环不变量：纯指令 + 所有操作数定义在循环外
       - 将不变指令移动到 pre-header 末尾
    4. 迭代直到不动点（外提可能产生新的不变量）

    仅外提纯指令（算术运算、字段访问、元组构建等），
    不移动有副作用的指令（函数调用、Store、Panic 等）。
    """

    name = "licm"

    def run(self, mir_module):
        """对 MIR 模块执行 LICM，返回是否发生了变化"""
        changed = False
        for fn_name, mir_fn in mir_module.functions.items():
            changed |= self._licm_function(mir_fn)
        return changed

    def _licm_function(self, mir_fn):
        """对单个函数执行 LICM"""
        from .cfg_utils import analyze_loops, build_block_map

        loop_info = analyze_loops(mir_fn)
        if not loop_info.loops:
            return False  # 没有循环

        block_map = build_block_map(mir_fn)
        total_changed = False

        # 迭代直到不动点（外提可能产生新的不变量）
        max_iterations = 10
        for _ in range(max_iterations):
            changed = False

            # 按嵌套层级从内到外处理循环
            # 内层循环的不变量先外提，然后外层循环可以进一步外提
            ordered_loops = self._get_loops_inner_first(loop_info)

            for loop in ordered_loops:
                loop_changed = self._licm_loop(mir_fn, loop, block_map)
                changed |= loop_changed

            total_changed |= changed
            if not changed:
                break

        return total_changed

    def _get_loops_inner_first(self, loop_info):
        """按嵌套层级从内到外返回循环列表（内层先处理）"""
        # 计算每个循环的深度
        depths = {}

        def compute_depth(header):
            if header in depths:
                return depths[header]
            loop = loop_info.get_loop(header)
            if loop is None:
                return 0
            if loop.parent is None:
                depths[header] = 1
            else:
                depths[header] = compute_depth(loop.parent) + 1
            return depths[header]

        for header in loop_info.loops:
            compute_depth(header)

        # 按深度从大到小排序（内层先处理）
        sorted_headers = sorted(depths.keys(), key=lambda h: depths[h], reverse=True)
        return [loop_info.loops[h] for h in sorted_headers]

    def _licm_loop(self, mir_fn, loop, block_map):
        """对单个循环执行 LICM，返回是否发生了变化"""
        # 1. 找到或创建 pre-header
        pre_header_label = self._get_or_create_pre_header(mir_fn, loop, block_map)
        if pre_header_label is None:
            return False  # 无法确定 pre-header

        pre_header = block_map[pre_header_label]

        # 2. 收集所有循环内的定义（SSA 名 -> 定义块）
        loop_defs = {}  # ssa_name -> block_label
        for block_label in loop.body:
            bb = block_map.get(block_label)
            if bb is None:
                continue
            for instr in bb.instructions:
                if hasattr(instr, "result_name") and instr.result_name:
                    loop_defs[instr.result_name] = block_label

        # 3. 识别循环不变指令并移动
        changed = False
        hoisted = []  # 被外提的指令

        # 遍历循环体中除 header 外的所有块
        # header 中的 Phi 不能移动，其他指令也可能有不变量
        for block_label in loop.body:
            bb = block_map.get(block_label)
            if bb is None:
                continue

            new_instrs = []
            for instr in bb.instructions:
                # 跳过 Phi 节点（必须在块开头）
                if hasattr(instr, "sources") and hasattr(instr, "result_name"):
                    new_instrs.append(instr)
                    continue

                # 检查是否是循环不变量
                if self._is_loop_invariant(instr, loop_defs, loop):
                    # 移动到 pre-header
                    hoisted.append(instr)
                    changed = True
                else:
                    new_instrs.append(instr)

            if changed:
                bb.instructions = new_instrs

        # 将外提的指令添加到 pre-header 末尾（在终结指令之前）
        if hoisted:
            # pre-header 的终结指令应该是跳转到 loop header
            # 把不变指令插入到终结指令之前
            if pre_header.terminator is not None:
                # 有终结指令，插入到它前面
                terminator = pre_header.terminator
                pre_header.terminator = None
                pre_header.instructions.extend(hoisted)
                pre_header.terminator = terminator
            else:
                pre_header.instructions.extend(hoisted)

        return changed

    def _is_loop_invariant(self, instr, loop_defs, loop):
        """
        判断一条指令是否是循环不变量。

        循环不变量的条件：
        1. 指令是纯的（无副作用）
        2. 指令有结果名（产生 SSA 值）
        3. 所有操作数都定义在循环外（即不在 loop_defs 中）

        注意：循环不变量的定义是"指令的结果在循环的每次迭代中都相同"。
        对于纯指令，如果所有操作数都是循环不变的，则指令本身也是循环不变的。
        由于我们迭代处理，第一次只外提操作数全在循环外的指令，
        后续迭代会外提依赖已外提指令的指令。
        """
        from .cfg_utils import get_instr_operands, is_instr_pure

        # 必须是纯指令
        if not is_instr_pure(instr):
            return False

        # 必须有结果名
        if not hasattr(instr, "result_name") or not instr.result_name:
            return False

        # 检查所有操作数是否都定义在循环外
        operands = get_instr_operands(instr)
        for op in operands:
            if op in loop_defs:
                # 操作数定义在循环内 → 不是不变量
                # （除非该操作数本身也是不变量，但这由迭代处理）
                return False

        return True

    def _get_or_create_pre_header(self, mir_fn, loop, block_map):
        """
        获取或创建循环的 pre-header 块。

        pre-header 是循环头的唯一前驱（在循环外），
        所有进入循环的路径都经过 pre-header。

        如果循环头有且仅有一个在循环外的前驱，直接使用它。
        如果有多个循环外前驱，创建一个新的 pre-header 块。
        """
        from .cfg_utils import build_predecessors

        header = loop.header
        preds = build_predecessors(mir_fn).get(header, [])

        # 筛选出在循环外的前驱
        outer_preds = [p for p in preds if p not in loop.body]

        if not outer_preds:
            # 没有外部前驱？可能是不可达循环，跳过
            return None

        if len(outer_preds) == 1:
            # 只有一个外部前驱，它就是 pre-header
            # 但需要确认它的唯一后继是 header（否则外提可能影响其他路径）
            # 简化处理：直接使用
            return outer_preds[0]
        else:
            # 多个外部前驱，需要创建新的 pre-header 块
            return self._create_pre_header(mir_fn, loop, block_map, outer_preds)

    def _create_pre_header(self, mir_fn, loop, block_map, outer_preds):
        """
        创建一个新的 pre-header 块。

        将所有外部前驱对 header 的跳转改为跳转到 pre-header，
        pre-header 再跳转到 header。
        """
        from .ir_nodes import MIRBasicBlock, MIRJump

        # 生成新的块标签
        header = loop.header
        new_label = f"{header}_pre"

        # 确保标签唯一
        existing_labels = {bb.label for bb in mir_fn.basic_blocks}
        if new_label in existing_labels:
            i = 0
            while f"{new_label}_{i}" in existing_labels:
                i += 1
            new_label = f"{new_label}_{i}"

        # 创建新块
        pre_header = MIRBasicBlock(label=new_label)
        pre_header.terminator = MIRJump(target=header)

        # 修改所有外部前驱的跳转目标
        for pred_label in outer_preds:
            pred_block = block_map.get(pred_label)
            if pred_block is None or pred_block.terminator is None:
                continue
            self._redirect_branch(pred_block.terminator, header, new_label)

        # 找到 header 在 basic_blocks 中的位置，插入到它前面
        header_idx = None
        for i, bb in enumerate(mir_fn.basic_blocks):
            if bb.label == header:
                header_idx = i
                break

        if header_idx is not None:
            mir_fn.basic_blocks.insert(header_idx, pre_header)
        else:
            mir_fn.basic_blocks.append(pre_header)

        # 更新 block_map
        block_map[new_label] = pre_header

        return new_label

    def _redirect_branch(self, terminator, old_target, new_target):
        """将终结指令中的 old_target 替换为 new_target"""
        from .ir_nodes import MIRBranch, MIRJump, MIRMatchJump, MIRSwitch

        if isinstance(terminator, MIRJump):
            if terminator.target == old_target:
                terminator.target = new_target
        elif isinstance(terminator, MIRBranch):
            if terminator.true_target == old_target:
                terminator.true_target = new_target
            if terminator.false_target == old_target:
                terminator.false_target = new_target
        elif isinstance(terminator, MIRSwitch):
            new_cases = []
            for val, target in terminator.cases:
                if target == old_target:
                    new_cases.append((val, new_target))
                else:
                    new_cases.append((val, target))
            terminator.cases = new_cases
            if terminator.default_target == old_target:
                terminator.default_target = new_target
        elif isinstance(terminator, MIRMatchJump):
            new_tests = []
            for vname, fields, target in terminator.variant_tests:
                if target == old_target:
                    new_tests.append((vname, fields, new_target))
                else:
                    new_tests.append((vname, fields, target))
            terminator.variant_tests = new_tests
            if terminator.default_target == old_target:
                terminator.default_target = new_target


class SSAVerifier(Pass):
    """SSA 验证器

    验证 MIR 模块是否满足基本的 SSA 性质：
    1. 每个基本块都有终结指令
    2. 每个 SSA 名只被定义一次
    3. 所有使用的 SSA 名都已定义（使用前定义）
    4. Phi 节点位于基本块开头
    5. Phi 的 source 块确实是当前块的前驱

    验证失败时返回 False（表示"未通过"，但不修改 IR）。
    详细错误信息可通过 errors 属性获取。
    """

    name = "ssa_verifier"

    def __init__(self):
        self.errors = []

    def run(self, mir_module):
        """执行 SSA 验证，返回 True 表示通过，False 表示有错误"""
        self.errors = []
        for fn_name, mir_fn in mir_module.functions.items():
            self._verify_function(fn_name, mir_fn)
        return len(self.errors) == 0

    def _verify_function(self, fn_name, mir_fn):
        """验证单个函数的 SSA 性质"""
        # 1. 收集所有定义的 SSA 名
        all_defs = {}  # ssa_name -> (block_label, instr_index)

        # 1.1 函数参数也是 SSA 定义（在入口块之前就已定义）
        for param_name, param_type, ssa_name in mir_fn.params:
            if ssa_name:
                all_defs[ssa_name] = ("<params>", -1)

        # 构建块名 -> 块对象的映射
        block_map = {}
        for bb in mir_fn.basic_blocks:
            block_map[bb.label] = bb

        # 构建前驱关系
        predecessors = {}  # block_label -> [predecessor_labels
        for bb in mir_fn.basic_blocks:
            predecessors[bb.label] = []
        for bb in mir_fn.basic_blocks:
            if bb.terminator is None:
                continue
            # 收集终结指令的后继
            succs = self._get_successors(bb.terminator)
            for succ_label in succs:
                if succ_label in predecessors:
                    predecessors[succ_label].append(bb.label)

        # 2. 检查每个基本块
        for bb in mir_fn.basic_blocks:
            # 2.1 终结指令检查
            if bb.terminator is None:
                self._error(fn_name, bb.label, -1, "基本块缺少终结指令")
                continue

            # 2.2 检查 Phi 位置：所有 Phi 必须在块开头
            seen_non_phi = False
            for idx, instr in enumerate(bb.instructions):
                is_phi = hasattr(instr, "sources") and hasattr(instr, "result_name")
                if is_phi:
                    if seen_non_phi:
                        self._error(fn_name, bb.label, idx, "Phi 节点不在基本块开头")
                else:
                    seen_non_phi = True

            # 2.3 收集定义
            for idx, instr in enumerate(bb.instructions):
                if hasattr(instr, "result_name") and instr.result_name:
                    ssa_name = instr.result_name
                    if ssa_name in all_defs:
                        self._error(
                            fn_name,
                            bb.label,
                            idx,
                            "SSA 名 %s 被多次定义（之前定义在 %s）"
                            % (ssa_name, all_defs[ssa_name][0]),
                        )
                    else:
                        all_defs[ssa_name] = (bb.label, idx)

        # 3. 检查使用
        for bb in mir_fn.basic_blocks:
            # 3.1 指令中的使用
            for idx, instr in enumerate(bb.instructions):
                used = self._get_used_ssa(instr)
                for used_name in used:
                    if used_name not in all_defs:
                        self._error(
                            fn_name,
                            bb.label,
                            idx,
                            "使用了未定义的 SSA 名: %s" % used_name,
                        )

            # 3.2 终结指令中的使用
            if bb.terminator is not None:
                used = self._get_terminator_used_ssa(bb.terminator)
                for used_name in used:
                    if used_name not in all_defs:
                        self._error(
                            fn_name,
                            bb.label,
                            -1,
                            "终结指令使用了未定义的 SSA 名: %s" % used_name,
                        )

        # 4. 检查 Phi 的 source 块是否是前驱
        for bb in mir_fn.basic_blocks:
            pred_labels = predecessors.get(bb.label, [])
            for idx, instr in enumerate(bb.instructions):
                if not (hasattr(instr, "sources") and hasattr(instr, "result_name")):
                    continue  # 不是 Phi
                if not hasattr(instr, "sources"):
                    continue
                src_blocks = [src[0] for src in instr.sources]
                for src_block in src_blocks:
                    if src_block not in pred_labels:
                        self._error(
                            fn_name,
                            bb.label,
                            idx,
                            "Phi 的 source 块 %s 不是当前块的前驱（前驱: %s）"
                            % (src_block, pred_labels),
                        )

    def _get_successors(self, terminator):
        """获取终结指令的后继块标签列表"""
        from .ir_nodes import MIRBranch, MIRCall, MIRJump, MIRReturn

        if isinstance(terminator, MIRJump):
            return [terminator.target]
        elif isinstance(terminator, MIRBranch):
            return [terminator.true_target, terminator.false_target]
        elif isinstance(terminator, MIRReturn):
            return []
        elif isinstance(terminator, MIRCall):
            return []
        else:
            return []

    def _get_used_ssa(self, instr):
        """获取一条指令使用的所有 SSA 名"""
        used = []

        # 二元运算
        if hasattr(instr, "left") and instr.left:
            used.append(instr.left)
        if hasattr(instr, "right") and instr.right:
            used.append(instr.right)

        # 一元运算
        if hasattr(instr, "operand") and instr.operand:
            used.append(instr.operand)

        # 函数调用
        if hasattr(instr, "callee") and instr.callee:
            # callee 可能是函数名字符串（不是 SSA 名），跳过
            pass
        if hasattr(instr, "args"):
            for arg in instr.args:
                if arg:
                    used.append(arg)

        # 字段/索引访问
        if hasattr(instr, "object") and instr.object:
            used.append(instr.object)
        if hasattr(instr, "index") and instr.index:
            used.append(instr.index)
        if hasattr(instr, "value") and instr.value:
            # value 可能是常量值而不是 SSA 名，需要判断
            # 这里保守处理：如果看起来像 SSA 名（以 v 开头）则加入
            if isinstance(instr.value, str) and instr.value:
                used.append(instr.value)

        # 列表/元组/Map 构建
        if hasattr(instr, "elements"):
            for elem in instr.elements:
                if elem:
                    used.append(elem)
        if hasattr(instr, "entries"):
            for k, v in instr.entries:
                if k:
                    used.append(k)
                if v:
                    used.append(v)
        if hasattr(instr, "fields"):
            for k, v in instr.fields.items():
                if v:
                    used.append(v)

        # 列表操作
        if hasattr(instr, "list_ssa") and instr.list_ssa:
            used.append(instr.list_ssa)
        if hasattr(instr, "element_ssa") and instr.element_ssa:
            used.append(instr.element_ssa)

        # 全局变量加载/存储
        if hasattr(instr, "src") and instr.src:
            used.append(instr.src)

        # Phi 的 sources（注意：Phi 的 source 值是使用，不是定义
        if hasattr(instr, "sources"):
            for label, val in instr.sources:
                if val:
                    used.append(val)

        return used

    def _get_terminator_used_ssa(self, terminator):
        """获取终结指令使用的 SSA 名"""
        used = []
        if hasattr(terminator, "cond") and terminator.cond:
            used.append(terminator.cond)
        if hasattr(terminator, "value") and terminator.value:
            used.append(terminator.value)
        if hasattr(terminator, "args"):
            for arg in terminator.args:
                if arg:
                    used.append(arg)
        return used

    def _error(self, fn_name, block_label, instr_idx, msg):
        """记录一个错误"""
        if instr_idx >= 0:
            self.errors.append("[%s] %s:%d %s" % (fn_name, block_label, instr_idx, msg))
        else:
            self.errors.append("[%s] %s %s" % (fn_name, block_label, msg))


class PassManager:
    """优化 Pass 管理器"""

    def __init__(self):
        self.hir_passes = []
        self.mir_passes = []
        self.lir_passes = []
        # 验证 Pass（不修改 IR，只做正确性检查）
        self.mir_verification_passes = []
        self._verbose = False
        # Pass 失败统计：{pass_name: 失败次数}
        self._pass_failures = {}
        # 验证失败统计：{pass_name: [错误信息列表]}
        self._verification_errors = {}

    def add_hir_pass(self, pass_):
        self.hir_passes.append(pass_)

    def add_mir_pass(self, pass_):
        self.mir_passes.append(pass_)

    def add_lir_pass(self, pass_):
        self.lir_passes.append(pass_)

    def add_mir_verification_pass(self, pass_):
        """添加 MIR 验证 Pass（不参与不动点迭代，优化完成后运行）"""
        self.mir_verification_passes.append(pass_)

    def set_verbose(self, verbose: bool):
        """设置是否输出详细日志"""
        self._verbose = verbose

    def get_failure_stats(self) -> dict:
        """获取 Pass 失败统计"""
        return dict(self._pass_failures)

    def get_verification_errors(self) -> dict:
        """获取验证 Pass 的错误信息"""
        return dict(self._verification_errors)

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
                # 优雅降级：单个 HIR 优化 Pass 失败不中断整体编译
                # Pass 可能抛出多种异常（TypeError, AttributeError, KeyError 等）
                # 通过 _record_pass_failure 统一记录和警告
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
                # 优雅降级：单个 MIR 优化 Pass 失败不中断整体编译
                # Pass 可能抛出多种异常（TypeError, AttributeError, KeyError 等）
                # 通过 _record_pass_failure 统一记录和警告
                except Exception as e:
                    self._record_pass_failure(pass_name, e)
            if not changed:
                break
            total_changed = True

        # 优化完成后运行验证 Pass
        for pass_ in self.mir_verification_passes:
            pass_name = pass_.__class__.__name__
            try:
                passed = pass_.run(mir_module)
                if not passed:
                    errors = getattr(pass_, "errors", [])
                    self._verification_errors[pass_name] = errors
                    if self._verbose:
                        print(f"[Verification] {pass_name} 未通过:", file=sys.stderr)
                        for err in errors:
                            print(f"  {err}", file=sys.stderr)
                    else:
                        import warnings

                        warnings.warn(
                            f"{pass_name} verification failed: {len(errors)} errors",
                            stacklevel=2,
                        )
            # 优雅降级：验证 Pass 失败不中断整体编译
            except Exception as e:
                self._record_pass_failure(pass_name, e)

        return total_changed

    def run_lir_passes(self, lir_module, max_iterations=10):
        total_changed = False
        for iteration in range(max_iterations):
            changed = False
            for pass_ in self.lir_passes:
                pass_name = pass_.__class__.__name__
                try:
                    changed |= pass_.run(lir_module)
                # 优雅降级：单个 LIR 优化 Pass 失败不中断整体编译
                # Pass 可能抛出多种异常（TypeError, AttributeError, KeyError 等）
                # 通过 _record_pass_failure 统一记录和警告
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
    # SSA 验证：优化完成后验证 MIR 的 SSA 性质
    pm.add_mir_verification_pass(SSAVerifier())
    return pm
