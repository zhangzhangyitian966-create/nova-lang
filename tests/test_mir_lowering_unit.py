"""MIRLowering 单元测试基线

为 ir/mir_lowering.py 中的核心方法编写独立单元测试，
覆盖纯函数（自由变量收集、模式绑定收集）、类型推断、
字面量降级、SSA/Block 管理、调用降级等核心路径。

这些测试绕过解析器，直接构造 HIR 节点树进行测试，
确保 MIRLowering 的内部逻辑被精确验证。
"""

import unittest

from nova.ir.ir_nodes import (
    BOOL_TYPE,
    FLOAT_TYPE,
    INT_TYPE,
    STRING_TYPE,
    IRType,
    NovaType,
    HIRBinaryOp,
    HIRBindPattern,
    HIRBlockExpr,
    HIRBoolLiteral,
    HIRCallExpr,
    HIRCharLiteral,
    HIRConstructorPattern,
    HIRFloatLiteral,
    HIRForExpr,
    HIRIdentifier,
    HIRIntLiteral,
    HIRLambda,
    HIRLetDecl,
    HIRListComprehension,
    HIRListExpr,
    HIRListPattern,
    HIRMatchArm,
    HIRMatchExpr,
    HIRStringLiteral,
    HIRTuplePattern,
    HIRUnitLiteral,
    HIRUnaryOp,
    MIRBasicBlock,
    MIRBinOp,
    MIRCall,
    MIRConst,
    MIRFunction,
    MIRJump,
    MIRPanic,
    MIRUnaryOp,
)
from nova.ir.mir_lowering import MIRLowering


def make_lowerer():
    """创建一个预初始化的 MIRLowering 实例，带有空的基本块。"""
    lowerer = MIRLowering()
    lowerer.current_block = MIRBasicBlock("bb0")
    lowerer.current_function = MIRFunction("test", [], INT_TYPE)
    return lowerer


# ============================================================
# 测试类 1: 自由变量收集 (_collect_free_vars)
# ============================================================


class TestCollectFreeVars(unittest.TestCase):
    """测试 MIRLowering._collect_free_vars 系列

    _collect_free_vars 是 lambda 捕获变量收集的核心逻辑，
    属于纯函数（仅依赖调度表，无外部状态副作用）。
    """

    def test_simple_free_var(self):
        """单个标识符引用：不在 bound_names 中即为自由变量"""
        lowerer = make_lowerer()
        expr = HIRIdentifier("x")
        result = lowerer._collect_free_vars(expr, set())
        self.assertEqual(result, {"x"})

    def test_bound_var_not_free(self):
        """标识符在 bound_names 中：不是自由变量"""
        lowerer = make_lowerer()
        expr = HIRIdentifier("x")
        result = lowerer._collect_free_vars(expr, {"x"})
        self.assertEqual(result, set())

    def test_multiple_free_vars(self):
        """二元运算中两个自由变量"""
        lowerer = make_lowerer()
        expr = HIRBinaryOp("+", HIRIdentifier("a"), HIRIdentifier("b"))
        result = lowerer._collect_free_vars(expr, set())
        self.assertEqual(result, {"a", "b"})

    def test_let_binds_variable(self):
        """let 声明：name 成为绑定，value 中的引用可能是自由的"""
        lowerer = make_lowerer()
        # let x = y + 1  →  y 是自由变量，x 在后续才绑定
        expr = HIRLetDecl("x", INT_TYPE, HIRBinaryOp("+", HIRIdentifier("y"), HIRIntLiteral(1)))
        result = lowerer._collect_free_vars(expr, set())
        self.assertEqual(result, {"y"})

    def test_block_tracks_let_bindings(self):
        """块表达式：前面的 let 绑定对后面的表达式可见"""
        lowerer = make_lowerer()
        # { let x = 1; x + y }  →  y 是自由变量，x 在块内绑定
        block = HIRBlockExpr([
            HIRLetDecl("x", INT_TYPE, HIRIntLiteral(1)),
            HIRBinaryOp("+", HIRIdentifier("x"), HIRIdentifier("y")),
        ])
        result = lowerer._collect_free_vars(block, set())
        self.assertEqual(result, {"y"})

    def test_lambda_params_are_bound(self):
        """lambda 参数在函数体内是绑定的"""
        lowerer = make_lowerer()
        # fn(x) => x + y  →  y 是自由变量，x 是参数（绑定）
        lam = HIRLambda(
            params=[("x", INT_TYPE)],
            body=HIRBinaryOp("+", HIRIdentifier("x"), HIRIdentifier("y")),
        )
        result = lowerer._collect_free_vars(lam, set())
        self.assertEqual(result, {"y"})

    def test_nested_lambda_captures_outer(self):
        """嵌套 lambda：内层 lambda 捕获外层 lambda 的参数"""
        lowerer = make_lowerer()
        # fn(x) => fn(y) => x + y  →  从最外层看，x 和 y 都不是自由变量
        inner = HIRLambda(
            params=[("y", INT_TYPE)],
            body=HIRBinaryOp("+", HIRIdentifier("x"), HIRIdentifier("y")),
        )
        outer = HIRLambda(params=[("x", INT_TYPE)], body=inner)
        result = lowerer._collect_free_vars(outer, set())
        self.assertEqual(result, set())

    def test_for_loop_variable_is_bound(self):
        """for 循环变量在循环体内是绑定的"""
        lowerer = make_lowerer()
        # for i in iter { i + y }  →  y 是自由变量，i 在循环内绑定
        loop = HIRForExpr(
            variable="i",
            iterable=HIRIdentifier("iter"),
            body=HIRBinaryOp("+", HIRIdentifier("i"), HIRIdentifier("y")),
        )
        result = lowerer._collect_free_vars(loop, set())
        self.assertEqual(result, {"iter", "y"})

    def test_listcomp_variable_is_bound(self):
        """列表推导式变量在结果表达式中是绑定的"""
        lowerer = make_lowerer()
        # [x + y for x in iter]  →  y 和 iter 是自由变量，x 在推导内绑定
        lc = HIRListComprehension(
            result_expr=HIRBinaryOp("+", HIRIdentifier("x"), HIRIdentifier("y")),
            variable="x",
            iterable=HIRIdentifier("iter"),
        )
        result = lowerer._collect_free_vars(lc, set())
        self.assertEqual(result, {"iter", "y"})

    def test_match_pattern_binds_variable(self):
        """match 分支的模式绑定在分支体内是绑定的"""
        lowerer = make_lowerer()
        # match val { Some(x) => x + y }  →  val 和 y 是自由变量，x 在分支内绑定
        match = HIRMatchExpr(
            value=HIRIdentifier("val"),
            arms=[
                HIRMatchArm(
                    pattern=HIRConstructorPattern("Option", "Some", [HIRBindPattern("x")]),
                    body=HIRBinaryOp("+", HIRIdentifier("x"), HIRIdentifier("y")),
                )
            ],
        )
        result = lowerer._collect_free_vars(match, set())
        self.assertEqual(result, {"val", "y"})

    def test_none_expr_returns_empty(self):
        """None 输入返回空集合"""
        lowerer = make_lowerer()
        result = lowerer._collect_free_vars(None, set())
        self.assertEqual(result, set())


# ============================================================
# 测试类 2: 模式绑定收集 (_collect_pattern_binds)
# ============================================================


class TestCollectPatternBinds(unittest.TestCase):
    """测试 MIRLowering._collect_pattern_binds

    递归收集模式中绑定的变量名，纯逻辑方法。
    """

    def test_bind_pattern(self):
        """简单绑定模式 x"""
        lowerer = make_lowerer()
        bound = set()
        lowerer._collect_pattern_binds(HIRBindPattern("x"), bound)
        self.assertEqual(bound, {"x"})

    def test_constructor_pattern_with_binds(self):
        """构造器模式 Some(a, b)"""
        lowerer = make_lowerer()
        bound = set()
        pattern = HIRConstructorPattern("Option", "Some", [
            HIRBindPattern("a"),
            HIRBindPattern("b"),
        ])
        lowerer._collect_pattern_binds(pattern, bound)
        self.assertEqual(bound, {"a", "b"})

    def test_tuple_pattern_with_binds(self):
        """元组模式 (a, b)"""
        lowerer = make_lowerer()
        bound = set()
        pattern = HIRTuplePattern([HIRBindPattern("a"), HIRBindPattern("b")])
        lowerer._collect_pattern_binds(pattern, bound)
        self.assertEqual(bound, {"a", "b"})

    def test_list_pattern_with_binds(self):
        """列表模式 [a, b, c]"""
        lowerer = make_lowerer()
        bound = set()
        pattern = HIRListPattern([
            HIRBindPattern("a"),
            HIRBindPattern("b"),
            HIRBindPattern("c"),
        ])
        lowerer._collect_pattern_binds(pattern, bound)
        self.assertEqual(bound, {"a", "b", "c"})

    def test_nested_constructor_pattern(self):
        """嵌套构造器模式 Some((a, b))"""
        lowerer = make_lowerer()
        bound = set()
        pattern = HIRConstructorPattern("Option", "Some", [
            HIRTuplePattern([HIRBindPattern("a"), HIRBindPattern("b")]),
        ])
        lowerer._collect_pattern_binds(pattern, bound)
        self.assertEqual(bound, {"a", "b"})

    def test_pattern_with_existing_binds_preserved(self):
        """已有的绑定不被清除"""
        lowerer = make_lowerer()
        bound = {"existing"}
        lowerer._collect_pattern_binds(HIRBindPattern("new"), bound)
        self.assertEqual(bound, {"existing", "new"})


# ============================================================
# 测试类 3: 类型推断 (_infer_binop_type)
# ============================================================


class TestInferBinopType(unittest.TestCase):
    """测试 MIRLowering._infer_binop_type

    根据操作数 SSA 类型推断二元运算结果类型。
    """

    def test_same_int_types_arithmetic(self):
        """两个 Int 类型做算术运算 → 返回 Int"""
        lowerer = make_lowerer()
        lowerer.ssa_types = {"v0": INT_TYPE, "v1": INT_TYPE}
        result = lowerer._infer_binop_type("v0", "v1", "+")
        self.assertEqual(result, INT_TYPE)

    def test_same_float_types_arithmetic(self):
        """两个 Float 类型做算术运算 → 返回 Float"""
        lowerer = make_lowerer()
        lowerer.ssa_types = {"v0": FLOAT_TYPE, "v1": FLOAT_TYPE}
        result = lowerer._infer_binop_type("v0", "v1", "*")
        self.assertEqual(result, FLOAT_TYPE)

    def test_same_string_types_concat(self):
        """两个 String 类型做 ++ 运算（不在已知操作符列表中）→ TYPE_VAR"""
        lowerer = make_lowerer()
        lowerer.ssa_types = {"v0": STRING_TYPE, "v1": STRING_TYPE}
        result = lowerer._infer_binop_type("v0", "v1", "++")
        self.assertEqual(result.kind, IRType.TYPE_VAR)

    def test_same_bool_types_logical(self):
        """两个 Bool 类型做逻辑运算 → 返回 Bool"""
        lowerer = make_lowerer()
        lowerer.ssa_types = {"v0": BOOL_TYPE, "v1": BOOL_TYPE}
        result = lowerer._infer_binop_type("v0", "v1", "&&")
        self.assertEqual(result, BOOL_TYPE)

    def test_different_types_returns_type_var(self):
        """Int 和 Float 类型不一致 → TYPE_VAR"""
        lowerer = make_lowerer()
        lowerer.ssa_types = {"v0": INT_TYPE, "v1": FLOAT_TYPE}
        result = lowerer._infer_binop_type("v0", "v1", "+")
        self.assertEqual(result.kind, IRType.TYPE_VAR)

    def test_missing_ssa_type_returns_type_var(self):
        """操作数 SSA 类型缺失 → TYPE_VAR"""
        lowerer = make_lowerer()
        lowerer.ssa_types = {"v0": INT_TYPE}
        result = lowerer._infer_binop_type("v0", "v1", "+")
        self.assertEqual(result.kind, IRType.TYPE_VAR)

    def test_unknown_operator_returns_type_var(self):
        """未知操作符 → TYPE_VAR"""
        lowerer = make_lowerer()
        lowerer.ssa_types = {"v0": INT_TYPE, "v1": INT_TYPE}
        result = lowerer._infer_binop_type("v0", "v1", "<<<")
        self.assertEqual(result.kind, IRType.TYPE_VAR)

    def test_comparison_op_preserves_type(self):
        """比较运算保持操作数类型"""
        lowerer = make_lowerer()
        lowerer.ssa_types = {"v0": INT_TYPE, "v1": INT_TYPE}
        for op in ("==", "!=", "<", ">", "<=", ">="):
            result = lowerer._infer_binop_type("v0", "v1", op)
            self.assertEqual(result, INT_TYPE, f"操作符 {op} 应保持 Int 类型")


# ============================================================
# 测试类 4: SSA 与基本块管理
# ============================================================


class TestSSAAndBlockManagement(unittest.TestCase):
    """测试 MIRLowering 的 SSA 名生成和基本块管理"""

    def test_new_ssa_increments(self):
        """_new_ssa 生成递增的 SSA 名 v0, v1, v2"""
        lowerer = make_lowerer()
        self.assertEqual(lowerer._new_ssa(), "v0")
        self.assertEqual(lowerer._new_ssa(), "v1")
        self.assertEqual(lowerer._new_ssa(), "v2")

    def test_new_block_increments(self):
        """_new_block 生成递增的基本块名 bb0, bb1, bb2"""
        lowerer = make_lowerer()
        self.assertEqual(lowerer._new_block(), "bb0")
        self.assertEqual(lowerer._new_block(), "bb1")
        self.assertEqual(lowerer._new_block(), "bb2")

    def test_emit_appends_instruction(self):
        """_emit 将指令追加到当前基本块"""
        lowerer = make_lowerer()
        instr = MIRConst(INT_TYPE)
        instr.value = 42
        instr.const_type = "int"
        ssa = lowerer._emit(instr)
        self.assertEqual(ssa, "v0")
        self.assertEqual(len(lowerer.current_block.instructions), 1)
        self.assertIs(lowerer.current_block.instructions[0], instr)
        self.assertEqual(instr.result_name, "v0")

    def test_emit_records_ssa_type(self):
        """_emit 记录 SSA 名到类型的映射"""
        lowerer = make_lowerer()
        instr = MIRConst(STRING_TYPE)
        instr.value = "hello"
        instr.const_type = "string"
        ssa = lowerer._emit(instr)
        self.assertEqual(lowerer.ssa_types[ssa], STRING_TYPE)

    def test_emit_multiple_increments_ssa(self):
        """多次 _emit 生成不同 SSA 名"""
        lowerer = make_lowerer()
        instr1 = MIRConst(INT_TYPE)
        instr1.const_type = "int"
        instr2 = MIRConst(INT_TYPE)
        instr2.const_type = "int"
        ssa1 = lowerer._emit(instr1)
        ssa2 = lowerer._emit(instr2)
        self.assertEqual(ssa1, "v0")
        self.assertEqual(ssa2, "v1")
        self.assertEqual(len(lowerer.current_block.instructions), 2)


# ============================================================
# 测试类 5: 字面量降级
# ============================================================


class TestLiteralLowering(unittest.TestCase):
    """测试字面量表达式的 MIR 降级

    每种字面量应生成对应的 MIRConst 指令，
    并正确设置 value 和 const_type 字段。
    """

    def test_int_literal(self):
        """整数字面量降级为 MIRConst(int)"""
        lowerer = make_lowerer()
        ssa = lowerer._lower_expr(HIRIntLiteral(42), lowerer.current_block)
        self.assertEqual(ssa, "v0")
        instr = lowerer.current_block.instructions[0]
        self.assertIsInstance(instr, MIRConst)
        self.assertEqual(instr.value, 42)
        self.assertEqual(instr.const_type, "int")
        self.assertEqual(instr.result_type, INT_TYPE)

    def test_float_literal(self):
        """浮点数字面量降级为 MIRConst(float)"""
        lowerer = make_lowerer()
        ssa = lowerer._lower_expr(HIRFloatLiteral(3.14), lowerer.current_block)
        self.assertEqual(ssa, "v0")
        instr = lowerer.current_block.instructions[0]
        self.assertIsInstance(instr, MIRConst)
        self.assertEqual(instr.value, 3.14)
        self.assertEqual(instr.const_type, "float")

    def test_string_literal(self):
        """字符串字面量降级为 MIRConst(string)"""
        lowerer = make_lowerer()
        ssa = lowerer._lower_expr(HIRStringLiteral("hello"), lowerer.current_block)
        instr = lowerer.current_block.instructions[0]
        self.assertEqual(instr.value, "hello")
        self.assertEqual(instr.const_type, "string")

    def test_bool_literal(self):
        """布尔字面量降级为 MIRConst(bool)"""
        lowerer = make_lowerer()
        lowerer._lower_expr(HIRBoolLiteral(True), lowerer.current_block)
        instr = lowerer.current_block.instructions[0]
        self.assertEqual(instr.value, True)
        self.assertEqual(instr.const_type, "bool")

    def test_char_literal(self):
        """字符字面量降级为 MIRConst(char)"""
        lowerer = make_lowerer()
        lowerer._lower_expr(HIRCharLiteral("A"), lowerer.current_block)
        instr = lowerer.current_block.instructions[0]
        self.assertEqual(instr.value, "A")
        self.assertEqual(instr.const_type, "char")

    def test_unit_literal(self):
        """Unit 字面量降级为 MIRConst(unit)"""
        lowerer = make_lowerer()
        lowerer._lower_expr(HIRUnitLiteral(), lowerer.current_block)
        instr = lowerer.current_block.instructions[0]
        self.assertIsNone(instr.value)
        self.assertEqual(instr.const_type, "unit")


# ============================================================
# 测试类 6: 标识符与运算降级
# ============================================================


class TestIdentifierAndOpLowering(unittest.TestCase):
    """测试标识符查找和运算表达式降级"""

    def test_identifier_in_env(self):
        """标识符在 env 中 → 返回对应 SSA 名"""
        lowerer = make_lowerer()
        lowerer.env["x"] = "v5"
        result = lowerer._lower_expr(HIRIdentifier("x"), lowerer.current_block)
        self.assertEqual(result, "v5")

    def test_identifier_not_in_env(self):
        """标识符不在 env 中 → 返回 None"""
        lowerer = make_lowerer()
        result = lowerer._lower_expr(HIRIdentifier("unknown"), lowerer.current_block)
        self.assertIsNone(result)

    def test_binary_op_generates_mirbinop(self):
        """二元运算生成 MIRBinOp 指令"""
        lowerer = make_lowerer()
        # 预设 env 和 ssa_types，模拟已降级的标识符
        lowerer.env["a"] = "v0"
        lowerer.env["b"] = "v1"
        lowerer.ssa_types["v0"] = INT_TYPE
        lowerer.ssa_types["v1"] = INT_TYPE
        # 标识符在 env 中直接返回，不生成新 SSA，所以二元运算是第一个 emit
        expr = HIRBinaryOp("+", HIRIdentifier("a"), HIRIdentifier("b"))
        ssa = lowerer._lower_expr(expr, lowerer.current_block)
        self.assertEqual(ssa, "v0")
        instr = lowerer.current_block.instructions[0]
        self.assertIsInstance(instr, MIRBinOp)
        self.assertEqual(instr.op, "+")
        self.assertEqual(instr.left, "v0")
        self.assertEqual(instr.right, "v1")
        self.assertEqual(instr.result_type, INT_TYPE)

    def test_unary_op_generates_mirunaryop(self):
        """一元运算生成 MIRUnaryOp 指令"""
        lowerer = make_lowerer()
        lowerer.env["x"] = "v0"
        expr = HIRUnaryOp("!", HIRIdentifier("x"))
        ssa = lowerer._lower_expr(expr, lowerer.current_block)
        instr = lowerer.current_block.instructions[0]
        self.assertIsInstance(instr, MIRUnaryOp)
        self.assertEqual(instr.op, "!")
        self.assertEqual(instr.operand, "v0")


# ============================================================
# 测试类 7: 函数调用降级 (_lower_call_expr)
# ============================================================


class TestLowerCallExpr(unittest.TestCase):
    """测试 MIRLowering._lower_call_expr

    验证三种调用类型：直接调用、闭包间接调用、表达式调用。
    """

    def test_direct_call_uses_function_name(self):
        """直接调用：callee 是函数名字符串，从 functions 表查返回类型"""
        lowerer = make_lowerer()
        lowerer.functions["add"] = INT_TYPE
        expr = HIRCallExpr(
            function=HIRIdentifier("add"),
            arguments=[HIRIntLiteral(1), HIRIntLiteral(2)],
        )
        ssa = lowerer._lower_expr(expr, lowerer.current_block)
        self.assertIsNotNone(ssa)
        # 最后一条指令应该是 MIRCall
        call_instr = lowerer.current_block.instructions[-1]
        self.assertIsInstance(call_instr, MIRCall)
        self.assertEqual(call_instr.callee, "add")
        self.assertEqual(len(call_instr.args), 2)
        self.assertEqual(call_instr.result_type, INT_TYPE)

    def test_closure_call_uses_ssa_value(self):
        """闭包调用：callee 是 SSA 值（变量在 env 中）"""
        lowerer = make_lowerer()
        # 模拟一个闭包变量：env 中有 f -> v10，v10 的类型是 Int->Int
        # 使用 v10 避免与参数降级生成的 SSA 名冲突
        fn_type = NovaType(IRType.FUNCTION, [INT_TYPE, INT_TYPE])
        lowerer.env["f"] = "v10"
        lowerer.ssa_types["v10"] = fn_type
        expr = HIRCallExpr(
            function=HIRIdentifier("f"),
            arguments=[HIRIntLiteral(42)],
        )
        ssa = lowerer._lower_expr(expr, lowerer.current_block)
        call_instr = lowerer.current_block.instructions[-1]
        self.assertIsInstance(call_instr, MIRCall)
        # callee 应该是 SSA 值 "v10"，不是函数名字符串
        self.assertEqual(call_instr.callee, "v10")
        self.assertEqual(call_instr.result_type, INT_TYPE)

    def test_call_with_unknown_function_returns_type_var(self):
        """调用未知函数：返回类型回退到 TYPE_VAR"""
        lowerer = make_lowerer()
        expr = HIRCallExpr(
            function=HIRIdentifier("unknown_fn"),
            arguments=[HIRIntLiteral(1)],
        )
        ssa = lowerer._lower_expr(expr, lowerer.current_block)
        call_instr = lowerer.current_block.instructions[-1]
        self.assertIsInstance(call_instr, MIRCall)
        self.assertEqual(call_instr.callee, "unknown_fn")
        self.assertEqual(call_instr.result_type.kind, IRType.TYPE_VAR)

    def test_call_args_lowered(self):
        """调用参数被正确降级为 SSA 值"""
        lowerer = make_lowerer()
        lowerer.functions["id"] = INT_TYPE
        expr = HIRCallExpr(
            function=HIRIdentifier("id"),
            arguments=[HIRIntLiteral(99)],
        )
        lowerer._lower_expr(expr, lowerer.current_block)
        call_instr = lowerer.current_block.instructions[-1]
        self.assertIsInstance(call_instr, MIRCall)
        # 参数应该是前面降级的 SSA 名
        self.assertEqual(len(call_instr.args), 1)
        self.assertTrue(call_instr.args[0].startswith("v"))


# ============================================================
# 测试类 8: break/continue 降级
# ============================================================


class TestBreakContinueLowering(unittest.TestCase):
    """测试 break/continue 表达式降级"""

    def test_break_inside_loop_jumps_to_exit(self):
        """循环内 break 生成跳转到 exit 标签"""
        lowerer = make_lowerer()
        lowerer.loop_stack = [("bb_header", "bb_exit")]
        lowerer._lower_expr(HIRIdentifier("__dummy__"), lowerer.current_block)
        # 直接调用 _lower_break_expr
        lowerer._lower_break_expr(None, lowerer.current_block)
        self.assertIsInstance(lowerer.current_block.terminator, MIRJump)
        self.assertEqual(lowerer.current_block.terminator.target, "bb_exit")

    def test_continue_inside_loop_jumps_to_header(self):
        """循环内 continue 生成跳转到 header 标签"""
        lowerer = make_lowerer()
        lowerer.loop_stack = [("bb_header", "bb_exit")]
        lowerer._lower_continue_expr(None, lowerer.current_block)
        self.assertIsInstance(lowerer.current_block.terminator, MIRJump)
        self.assertEqual(lowerer.current_block.terminator.target, "bb_header")

    def test_break_outside_loop_panics(self):
        """循环外 break 生成 panic"""
        lowerer = make_lowerer()
        lowerer.loop_stack = []
        lowerer._lower_break_expr(None, lowerer.current_block)
        self.assertIsInstance(lowerer.current_block.terminator, MIRPanic)

    def test_continue_outside_loop_panics(self):
        """循环外 continue 生成 panic"""
        lowerer = make_lowerer()
        lowerer.loop_stack = []
        lowerer._lower_continue_expr(None, lowerer.current_block)
        self.assertIsInstance(lowerer.current_block.terminator, MIRPanic)


# ============================================================
# 测试类 9: 列表表达式降级
# ============================================================


class TestListExprLowering(unittest.TestCase):
    """测试列表表达式降级"""

    def test_empty_list(self):
        """空列表生成 MIRListBuild with 0 args"""
        lowerer = make_lowerer()
        expr = HIRListExpr([])
        ssa = lowerer._lower_expr(expr, lowerer.current_block)
        self.assertIsNotNone(ssa)
        instr = lowerer.current_block.instructions[0]
        # 应该是某种 list build 指令
        self.assertTrue(hasattr(instr, "args") or hasattr(instr, "elements"))

    def test_list_with_elements(self):
        """含元素的列表降级所有元素"""
        lowerer = make_lowerer()
        expr = HIRListExpr([HIRIntLiteral(1), HIRIntLiteral(2), HIRIntLiteral(3)])
        lowerer._lower_expr(expr, lowerer.current_block)
        # 应该有 3 个常量指令 + 1 个 list build 指令
        self.assertGreaterEqual(len(lowerer.current_block.instructions), 4)


if __name__ == "__main__":
    unittest.main()
