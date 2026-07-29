"""
Evaluator 单元测试基线

为 evaluator.py（1017行）建立独立单元测试，覆盖语言求值语义核心路径。
测试策略：直接构造 AST 节点树绕过解析器，精确验证 Evaluator 内部逻辑。
覆盖：字面量求值、运算、控制流、模式匹配、内置函数、数据结构、闭包。
"""

import math
import unittest

from nova.evaluator import (
    Evaluator,
    NovaClosure,
    NovaADTValue,
    BuiltinFn,
    UNIT_VALUE,
)
from nova.environment import Environment
from nova.errors import RuntimeError_, BreakSignal, ContinueSignal
from nova.ast_nodes import (
    Assignment,
    BinaryOp,
    Block,
    BoolLiteral,
    BreakExpr,
    CharLiteral,
    ContinueExpr,
    FnCall,
    FnDef,
    ForExpr,
    Identifier,
    IfExpr,
    FloatLiteral,
    IntLiteral,
    Lambda,
    LetBinding,
    ListComprehension,
    ListExpr,
    MatchArm,
    MatchExpr,
    MutBinding,
    Param,
    PatternBool,
    PatternConstructor,
    PatternFloat,
    PatternIdentifier,
    PatternInt,
    PatternList,
    PatternString,
    PatternTuple,
    PatternWildcard,
    PipeExpr,
    StringLiteral,
    TryExpr,
    TupleExpr,
    UnaryOp,
    UnitLiteral,
    WhileExpr,
    FieldAccess,
)


def make_eval():
    """创建一个全新的 Evaluator 实例"""
    return Evaluator(check_types=False)


def make_param(name, type_annotation=None):
    """快捷创建参数"""
    p = Param(name=name)
    p.type_annotation = type_annotation
    return p


# ============================================================
# 1. 字面量求值
# ============================================================


class TestLiteralEval(unittest.TestCase):
    """测试字面量表达式求值"""

    def test_int_literal(self):
        """整数字面量求值返回 Python int"""
        ev = make_eval()
        self.assertEqual(ev.eval_expr(IntLiteral(42)), 42)
        self.assertEqual(ev.eval_expr(IntLiteral(0)), 0)
        self.assertEqual(ev.eval_expr(IntLiteral(-7)), -7)

    def test_float_literal(self):
        """浮点数字面量求值返回 Python float"""
        ev = make_eval()
        self.assertAlmostEqual(ev.eval_expr(FloatLiteral(3.14)), 3.14)
        self.assertEqual(ev.eval_expr(FloatLiteral(0.0)), 0.0)

    def test_string_literal(self):
        """字符串字面量求值返回 Python str"""
        ev = make_eval()
        self.assertEqual(ev.eval_expr(StringLiteral("hello")), "hello")
        self.assertEqual(ev.eval_expr(StringLiteral("")), "")

    def test_char_literal(self):
        """字符字面量求值返回单字符 str"""
        ev = make_eval()
        self.assertEqual(ev.eval_expr(CharLiteral("a")), "a")

    def test_bool_literal(self):
        """布尔字面量求值返回 Python bool"""
        ev = make_eval()
        self.assertTrue(ev.eval_expr(BoolLiteral(True)))
        self.assertFalse(ev.eval_expr(BoolLiteral(False)))

    def test_unit_literal(self):
        """Unit 字面量求值返回 UNIT_VALUE 单例"""
        ev = make_eval()
        self.assertIs(ev.eval_expr(UnitLiteral()), UNIT_VALUE)


# ============================================================
# 2. 标识符与环境
# ============================================================


class TestIdentifierEval(unittest.TestCase):
    """测试标识符查找和环境管理"""

    def test_lookup_defined_var(self):
        """查找已定义的变量返回其值"""
        ev = make_eval()
        ev.env.define("x", 42)
        self.assertEqual(ev.eval_expr(Identifier("x")), 42)

    def test_lookup_undefined_var_raises(self):
        """查找未定义的变量抛出 RuntimeError_"""
        ev = make_eval()
        with self.assertRaises(RuntimeError_):
            ev.eval_expr(Identifier("nonexistent"))

    def test_lookup_in_child_scope(self):
        """子作用域可以查找父作用域的变量"""
        ev = make_eval()
        ev.env.define("outer", 100)
        child = ev.env.child()
        ev.env = child
        self.assertEqual(ev.eval_expr(Identifier("outer")), 100)

    def test_shadow_in_child_scope(self):
        """子作用域中的同名绑定遮蔽父作用域"""
        ev = make_eval()
        ev.env.define("x", 1)
        child = ev.env.child()
        child.define("x", 2)
        ev.env = child
        self.assertEqual(ev.eval_expr(Identifier("x")), 2)


# ============================================================
# 3. 二元运算
# ============================================================


class TestBinaryOpEval(unittest.TestCase):
    """测试二元运算符求值"""

    def test_addition(self):
        """加法运算"""
        ev = make_eval()
        self.assertEqual(ev.eval_expr(BinaryOp("+", IntLiteral(1), IntLiteral(2))), 3)

    def test_subtraction(self):
        """减法运算"""
        ev = make_eval()
        self.assertEqual(ev.eval_expr(BinaryOp("-", IntLiteral(10), IntLiteral(4))), 6)

    def test_multiplication(self):
        """乘法运算"""
        ev = make_eval()
        self.assertEqual(ev.eval_expr(BinaryOp("*", IntLiteral(3), IntLiteral(7))), 21)

    def test_modulo(self):
        """取模运算"""
        ev = make_eval()
        self.assertEqual(ev.eval_expr(BinaryOp("%", IntLiteral(10), IntLiteral(3))), 1)

    def test_int_division(self):
        """整数除法返回整除结果"""
        ev = make_eval()
        self.assertEqual(ev.eval_expr(BinaryOp("/", IntLiteral(10), IntLiteral(3))), 3)

    def test_float_division(self):
        """浮点除法返回浮点结果"""
        ev = make_eval()
        result = ev.eval_expr(BinaryOp("/", FloatLiteral(10.0), FloatLiteral(4.0)))
        self.assertAlmostEqual(result, 2.5)

    def test_division_by_zero(self):
        """整数除零抛出 RuntimeError_"""
        ev = make_eval()
        with self.assertRaises(RuntimeError_):
            ev.eval_expr(BinaryOp("/", IntLiteral(10), IntLiteral(0)))

    def test_string_concat(self):
        """字符串拼接运算 ++"""
        ev = make_eval()
        result = ev.eval_expr(BinaryOp("++", StringLiteral("a"), StringLiteral("b")))
        self.assertEqual(result, "ab")

    def test_comparison_operators(self):
        """比较运算符返回 bool"""
        ev = make_eval()
        self.assertTrue(ev.eval_expr(BinaryOp("<", IntLiteral(1), IntLiteral(2))))
        self.assertFalse(ev.eval_expr(BinaryOp("<", IntLiteral(2), IntLiteral(1))))
        self.assertTrue(ev.eval_expr(BinaryOp("==", IntLiteral(1), IntLiteral(1))))
        self.assertFalse(ev.eval_expr(BinaryOp("!=", IntLiteral(1), IntLiteral(1))))
        self.assertTrue(ev.eval_expr(BinaryOp(">=", IntLiteral(2), IntLiteral(2))))
        self.assertTrue(ev.eval_expr(BinaryOp("<=", IntLiteral(2), IntLiteral(2))))

    def test_and_short_circuit(self):
        """&& 短路求值：左操作数为 False 时不求值右操作数"""
        ev = make_eval()
        ev.env.define("x", 0)
        result = ev.eval_expr(
            BinaryOp("&&", BoolLiteral(False), Identifier("x"))
        )
        self.assertFalse(result)

    def test_and_returns_right_when_true(self):
        """&& 左操作数为 True 时返回右操作数的值"""
        ev = make_eval()
        result = ev.eval_expr(
            BinaryOp("&&", BoolLiteral(True), BoolLiteral(True))
        )
        self.assertTrue(result)

    def test_or_short_circuit(self):
        """|| 短路求值：左操作数为 True 时不求值右操作数"""
        ev = make_eval()
        ev.env.define("x", 0)
        result = ev.eval_expr(
            BinaryOp("||", BoolLiteral(True), Identifier("x"))
        )
        self.assertTrue(result)

    def test_or_returns_right_when_false(self):
        """|| 左操作数为 False 时返回右操作数的值"""
        ev = make_eval()
        result = ev.eval_expr(
            BinaryOp("||", BoolLiteral(False), BoolLiteral(True))
        )
        self.assertTrue(result)

    def test_unknown_operator_raises(self):
        """未知运算符抛出 RuntimeError_"""
        ev = make_eval()
        with self.assertRaises(RuntimeError_):
            ev.eval_expr(BinaryOp("@@", IntLiteral(1), IntLiteral(2)))


# ============================================================
# 4. 一元运算
# ============================================================


class TestUnaryOpEval(unittest.TestCase):
    """测试一元运算符求值"""

    def test_unary_minus(self):
        """一元负号"""
        ev = make_eval()
        self.assertEqual(ev.eval_expr(UnaryOp("-", IntLiteral(5))), -5)

    def test_unary_not(self):
        """一元逻辑非"""
        ev = make_eval()
        self.assertFalse(ev.eval_expr(UnaryOp("!", BoolLiteral(True))))
        self.assertTrue(ev.eval_expr(UnaryOp("!", BoolLiteral(False))))

    def test_unary_unknown_raises(self):
        """未知一元运算符抛出 RuntimeError_"""
        ev = make_eval()
        with self.assertRaises(RuntimeError_):
            ev.eval_expr(UnaryOp("@", IntLiteral(1)))


# ============================================================
# 5. 控制流
# ============================================================


class TestControlFlowEval(unittest.TestCase):
    """测试控制流表达式求值"""

    def test_if_true_branch(self):
        """if 条件为 True 时执行 then 分支"""
        ev = make_eval()
        result = ev.eval_expr(IfExpr(BoolLiteral(True), IntLiteral(1), IntLiteral(2)))
        self.assertEqual(result, 1)

    def test_if_false_branch(self):
        """if 条件为 False 时执行 else 分支"""
        ev = make_eval()
        result = ev.eval_expr(IfExpr(BoolLiteral(False), IntLiteral(1), IntLiteral(2)))
        self.assertEqual(result, 2)

    def test_if_without_else_returns_unit(self):
        """if 无 else 分支且条件为 False 时返回 UNIT_VALUE"""
        ev = make_eval()
        result = ev.eval_expr(IfExpr(BoolLiteral(False), IntLiteral(1), None))
        self.assertIs(result, UNIT_VALUE)

    def test_while_loop_basic(self):
        """while 循环基本执行"""
        ev = make_eval()
        ev.env.define("i", 0, mutable=True)
        # while i < 3 { i = i + 1 }
        cond = BinaryOp("<", Identifier("i"), IntLiteral(3))
        body = Block([Assignment("i", BinaryOp("+", Identifier("i"), IntLiteral(1)))])
        result = ev.eval_expr(WhileExpr(cond, body))
        self.assertEqual(ev.env.lookup("i"), 3)

    def test_while_with_break(self):
        """while 循环中 break 提前退出"""
        ev = make_eval()
        ev.env.define("i", 0, mutable=True)
        cond = BinaryOp("<", Identifier("i"), IntLiteral(100))
        body = Block([
            Assignment("i", BinaryOp("+", Identifier("i"), IntLiteral(1))),
            IfExpr(
                BinaryOp("==", Identifier("i"), IntLiteral(5)),
                BreakExpr(),
                None,
            ),
        ])
        ev.eval_expr(WhileExpr(cond, body))
        self.assertEqual(ev.env.lookup("i"), 5)

    def test_for_range(self):
        """for 范围循环返回列表"""
        ev = make_eval()
        # for i <- 0..3 { i }
        expr = ForExpr("i", ("range", IntLiteral(0), IntLiteral(3), None), Identifier("i"))
        result = ev.eval_expr(expr)
        self.assertEqual(result, [0, 1, 2, 3])

    def test_for_range_with_step(self):
        """for 范围循环带步长"""
        ev = make_eval()
        # for i <- 0..10 step 3 { i }
        expr = ForExpr("i", ("range", IntLiteral(0), IntLiteral(10), IntLiteral(3)), Identifier("i"), step=IntLiteral(3))
        result = ev.eval_expr(expr)
        self.assertEqual(result, [0, 3, 6, 9])

    def test_for_iterable_list(self):
        """for 遍历列表"""
        ev = make_eval()
        # for x in [10, 20, 30] { x }
        expr = ForExpr("x", ListExpr([IntLiteral(10), IntLiteral(20), IntLiteral(30)]), Identifier("x"))
        result = ev.eval_expr(expr)
        self.assertEqual(result, [10, 20, 30])

    def test_break_expr_raises_signal(self):
        """break 表达式抛出 BreakSignal"""
        ev = make_eval()
        with self.assertRaises(BreakSignal):
            ev.eval_expr(BreakExpr())

    def test_continue_expr_raises_signal(self):
        """continue 表达式抛出 ContinueSignal"""
        ev = make_eval()
        with self.assertRaises(ContinueSignal):
            ev.eval_expr(ContinueExpr())


# ============================================================
# 6. 块与绑定
# ============================================================


class TestBlockAndBinding(unittest.TestCase):
    """测试块表达式和变量绑定"""

    def test_block_returns_tail(self):
        """块表达式返回尾部表达式"""
        ev = make_eval()
        block = Block([], IntLiteral(42))
        self.assertEqual(ev.eval_expr(block), 42)

    def test_block_with_statements(self):
        """块中语句依次执行，返回尾部表达式"""
        ev = make_eval()
        block = Block(
            [LetBinding("x", IntLiteral(10)), LetBinding("y", IntLiteral(20))],
            BinaryOp("+", Identifier("x"), Identifier("y")),
        )
        self.assertEqual(ev.eval_expr(block), 30)

    def test_block_scoping(self):
        """块内绑定的变量在块外不可见"""
        ev = make_eval()
        block = Block([LetBinding("inner", IntLiteral(99))], Identifier("inner"))
        ev.eval_expr(block)
        with self.assertRaises(RuntimeError_):
            ev.eval_expr(Identifier("inner"))

    def test_let_binding(self):
        """let 绑定定义不可变变量"""
        ev = make_eval()
        ev.eval_expr(LetBinding("x", IntLiteral(42)))
        self.assertEqual(ev.env.lookup("x"), 42)

    def test_mut_binding(self):
        """mut 绑定定义可变变量"""
        ev = make_eval()
        ev.eval_expr(MutBinding("counter", IntLiteral(0)))
        self.assertEqual(ev.env.lookup("counter"), 0)

    def test_assignment(self):
        """赋值表达式更新可变变量"""
        ev = make_eval()
        ev.env.define("x", 10, mutable=True)
        ev.eval_expr(Assignment("x", IntLiteral(99)))
        self.assertEqual(ev.env.lookup("x"), 99)

    def test_assignment_to_immutable_raises(self):
        """对不可变变量赋值抛出 RuntimeError_"""
        ev = make_eval()
        ev.env.define("x", 10, mutable=False)
        with self.assertRaises(RuntimeError_):
            ev.eval_expr(Assignment("x", IntLiteral(99)))


# ============================================================
# 7. 数据结构
# ============================================================


class TestDataStructureEval(unittest.TestCase):
    """测试列表、元组等数据结构求值"""

    def test_empty_list(self):
        """空列表求值"""
        ev = make_eval()
        self.assertEqual(ev.eval_expr(ListExpr([])), [])

    def test_list_with_elements(self):
        """带元素的列表求值"""
        ev = make_eval()
        result = ev.eval_expr(ListExpr([IntLiteral(1), IntLiteral(2), IntLiteral(3)]))
        self.assertEqual(result, [1, 2, 3])

    def test_tuple_eval(self):
        """元组求值"""
        ev = make_eval()
        result = ev.eval_expr(TupleExpr([IntLiteral(1), StringLiteral("a")]))
        self.assertEqual(result, (1, "a"))

    def test_field_access_tuple(self):
        """元组字段访问"""
        ev = make_eval()
        ev.env.define("t", (10, 20, 30))
        result = ev.eval_expr(FieldAccess(Identifier("t"), "0"))
        self.assertEqual(result, 10)
        result = ev.eval_expr(FieldAccess(Identifier("t"), "2"))
        self.assertEqual(result, 30)

    def test_field_access_out_of_bounds(self):
        """元组索引越界抛出 RuntimeError_"""
        ev = make_eval()
        ev.env.define("t", (10, 20))
        with self.assertRaises(RuntimeError_):
            ev.eval_expr(FieldAccess(Identifier("t"), "5"))

    def test_list_comprehension_basic(self):
        """列表推导式基本求值"""
        ev = make_eval()
        # [x * 2 for x in [1, 2, 3]]
        expr = ListComprehension(
            expr=BinaryOp("*", Identifier("x"), IntLiteral(2)),
            var_name="x",
            iterable=ListExpr([IntLiteral(1), IntLiteral(2), IntLiteral(3)]),
        )
        self.assertEqual(ev.eval_expr(expr), [2, 4, 6])

    def test_list_comprehension_with_filter(self):
        """带过滤条件的列表推导式"""
        ev = make_eval()
        # [x for x in [1,2,3,4,5] if x > 2]
        expr = ListComprehension(
            expr=Identifier("x"),
            var_name="x",
            iterable=ListExpr([IntLiteral(1), IntLiteral(2), IntLiteral(3), IntLiteral(4), IntLiteral(5)]),
            filter_cond=BinaryOp(">", Identifier("x"), IntLiteral(2)),
        )
        self.assertEqual(ev.eval_expr(expr), [3, 4, 5])


# ============================================================
# 8. 函数与闭包
# ============================================================


class TestFunctionEval(unittest.TestCase):
    """测试函数定义、调用和闭包"""

    def test_fn_def_creates_closure(self):
        """fn 定义创建闭包"""
        ev = make_eval()
        fn = FnDef("add", [make_param("a"), make_param("b")], body=Block([], BinaryOp("+", Identifier("a"), Identifier("b"))))
        ev.eval_decl(fn)
        result = ev.env.lookup("add")
        self.assertIsInstance(result, NovaClosure)
        self.assertEqual(result.name, "add")

    def test_fn_call_basic(self):
        """基本函数调用"""
        ev = make_eval()
        fn = FnDef("add", [make_param("a"), make_param("b")], body=Block([], BinaryOp("+", Identifier("a"), Identifier("b"))))
        ev.eval_decl(fn)
        call = FnCall(Identifier("add"), [IntLiteral(3), IntLiteral(4)])
        self.assertEqual(ev.eval_expr(call), 7)

    def test_lambda_eval(self):
        """lambda 表达式求值创建闭包"""
        ev = make_eval()
        lam = Lambda([make_param("x")], body=BinaryOp("+", Identifier("x"), IntLiteral(1)))
        result = ev.eval_expr(lam)
        self.assertIsInstance(result, NovaClosure)
        self.assertEqual(result.name, "<lambda>")

    def test_lambda_call(self):
        """调用 lambda 闭包"""
        ev = make_eval()
        lam = Lambda([make_param("x")], body=BinaryOp("+", Identifier("x"), IntLiteral(1)))
        closure = ev.eval_expr(lam)
        result = ev._call_fn(closure, [41])
        self.assertEqual(result, 42)

    def test_closure_captures_env(self):
        """闭包捕获定义时的环境"""
        ev = make_eval()
        ev.env.define("n", 10)
        lam = Lambda([make_param("x")], body=BinaryOp("+", Identifier("x"), Identifier("n")))
        closure = ev.eval_expr(lam)
        # 在不同环境中调用
        ev.env = Environment()
        result = ev._call_fn(closure, [5])
        self.assertEqual(result, 15)

    def test_call_builtin_fn(self):
        """调用内置函数"""
        ev = make_eval()
        # abs(-5) == 5
        call = FnCall(Identifier("abs"), [UnaryOp("-", IntLiteral(5))])
        self.assertEqual(ev.eval_expr(call), 5.0)

    def test_call_non_function_raises(self):
        """调用非函数值抛出 RuntimeError_"""
        ev = make_eval()
        ev.env.define("x", 42)
        with self.assertRaises(RuntimeError_):
            ev._call_fn(42, [])

    def test_too_many_args_raises(self):
        """传入过多参数抛出 RuntimeError_"""
        ev = make_eval()
        fn = FnDef("f", [make_param("a")], body=Identifier("a"))
        ev.eval_decl(fn)
        with self.assertRaises(RuntimeError_):
            ev._call_fn(ev.env.lookup("f"), [1, 2, 3])


# ============================================================
# 9. 管道与错误传播
# ============================================================


class TestPipeAndTry(unittest.TestCase):
    """测试管道操作符和错误传播"""

    def test_pipe_basic(self):
        """管道操作符 x |> f 等价于 f(x)"""
        ev = make_eval()
        ev.env.define("inc", NovaClosure(
            name="inc",
            params=[make_param("x")],
            body=BinaryOp("+", Identifier("x"), IntLiteral(1)),
            env=ev.env,
        ))
        result = ev.eval_expr(PipeExpr(IntLiteral(41), Identifier("inc")))
        self.assertEqual(result, 42)

    def test_pipe_with_builtin(self):
        """管道操作符配合内置函数"""
        ev = make_eval()
        result = ev.eval_expr(PipeExpr(UnaryOp("-", IntLiteral(5)), Identifier("abs")))
        self.assertEqual(result, 5.0)

    def test_try_expr_ok(self):
        """try 表达式对 Ok 值提取内部值"""
        ev = make_eval()
        ev.env.define("x", NovaADTValue("Result", "Ok", [42]))
        result = ev.eval_expr(TryExpr(Identifier("x")))
        self.assertEqual(result, NovaADTValue("Result", "Ok", [42]))

    def test_try_expr_err(self):
        """try 表达式对 Err 值直接返回"""
        ev = make_eval()
        err_val = NovaADTValue("Result", "Err", ["error"])
        ev.env.define("x", err_val)
        result = ev.eval_expr(TryExpr(Identifier("x")))
        self.assertEqual(result, err_val)


# ============================================================
# 10. 模式匹配
# ============================================================


class TestPatternMatching(unittest.TestCase):
    """测试 match 表达式和模式匹配逻辑"""

    def test_match_int_pattern(self):
        """整数模式匹配"""
        ev = make_eval()
        expr = MatchExpr(
            IntLiteral(42),
            [MatchArm(PatternInt(42), body=IntLiteral(1)), MatchArm(PatternWildcard(), body=IntLiteral(0))],
        )
        self.assertEqual(ev.eval_expr(expr), 1)

    def test_match_wildcard_fallback(self):
        """通配符模式作为兜底"""
        ev = make_eval()
        expr = MatchExpr(
            IntLiteral(99),
            [MatchArm(PatternInt(1), body=IntLiteral(1)), MatchArm(PatternWildcard(), body=IntLiteral(0))],
        )
        self.assertEqual(ev.eval_expr(expr), 0)

    def test_match_identifier_binds(self):
        """标识符模式绑定变量"""
        ev = make_eval()
        expr = MatchExpr(
            IntLiteral(42),
            [MatchArm(PatternIdentifier("n"), body=Identifier("n"))],
        )
        self.assertEqual(ev.eval_expr(expr), 42)

    def test_match_bool_pattern(self):
        """布尔模式匹配"""
        ev = make_eval()
        expr = MatchExpr(
            BoolLiteral(True),
            [MatchArm(PatternBool(True), body=IntLiteral(1)), MatchArm(PatternBool(False), body=IntLiteral(0))],
        )
        self.assertEqual(ev.eval_expr(expr), 1)

    def test_match_string_pattern(self):
        """字符串模式匹配"""
        ev = make_eval()
        expr = MatchExpr(
            StringLiteral("hello"),
            [MatchArm(PatternString("hello"), body=IntLiteral(1)), MatchArm(PatternWildcard(), body=IntLiteral(0))],
        )
        self.assertEqual(ev.eval_expr(expr), 1)

    def test_match_float_pattern(self):
        """浮点数模式匹配"""
        ev = make_eval()
        expr = MatchExpr(
            FloatLiteral(3.14),
            [MatchArm(PatternFloat(3.14), body=IntLiteral(1)), MatchArm(PatternWildcard(), body=IntLiteral(0))],
        )
        self.assertEqual(ev.eval_expr(expr), 1)

    def test_match_constructor_pattern(self):
        """构造器模式匹配 ADT 值"""
        ev = make_eval()
        val = NovaADTValue("Option", "Some", [42])
        expr = MatchExpr(
            Identifier("x"),
            [MatchArm(
                PatternConstructor("Some", [PatternIdentifier("v")]),
                body=Identifier("v"),
            )],
        )
        ev.env.define("x", val)
        self.assertEqual(ev.eval_expr(expr), 42)

    def test_match_constructor_no_fields(self):
        """无字段构造器模式匹配"""
        ev = make_eval()
        val = NovaADTValue("Option", "None", [])
        expr = MatchExpr(
            Identifier("x"),
            [MatchArm(PatternConstructor("None", []), body=IntLiteral(0))],
        )
        ev.env.define("x", val)
        self.assertEqual(ev.eval_expr(expr), 0)

    def test_match_constructor_wrong_variant(self):
        """构造器模式不匹配不同的 variant"""
        ev = make_eval()
        val = NovaADTValue("Option", "None", [])
        expr = MatchExpr(
            Identifier("x"),
            [
                MatchArm(PatternConstructor("Some", [PatternIdentifier("v")]), body=IntLiteral(1)),
                MatchArm(PatternConstructor("None", []), body=IntLiteral(0)),
            ],
        )
        ev.env.define("x", val)
        self.assertEqual(ev.eval_expr(expr), 0)

    def test_match_tuple_pattern(self):
        """元组模式匹配"""
        ev = make_eval()
        expr = MatchExpr(
            TupleExpr([IntLiteral(1), IntLiteral(2)]),
            [MatchArm(
                PatternTuple([PatternIdentifier("a"), PatternIdentifier("b")]),
                body=BinaryOp("+", Identifier("a"), Identifier("b")),
            )],
        )
        self.assertEqual(ev.eval_expr(expr), 3)

    def test_match_list_pattern(self):
        """列表模式匹配"""
        ev = make_eval()
        expr = MatchExpr(
            ListExpr([IntLiteral(10), IntLiteral(20)]),
            [MatchArm(
                PatternList([PatternIdentifier("a"), PatternIdentifier("b")]),
                body=BinaryOp("+", Identifier("a"), Identifier("b")),
            )],
        )
        self.assertEqual(ev.eval_expr(expr), 30)

    def test_match_no_arms_raises(self):
        """无匹配分支抛出 RuntimeError_"""
        ev = make_eval()
        expr = MatchExpr(
            IntLiteral(42),
            [MatchArm(PatternInt(1), body=IntLiteral(1))],
        )
        with self.assertRaises(RuntimeError_):
            ev.eval_expr(expr)

    def test_match_with_guard(self):
        """带 guard 的 match 分支"""
        ev = make_eval()
        expr = MatchExpr(
            IntLiteral(5),
            [
                MatchArm(PatternIdentifier("n"), guard=BinaryOp(">", Identifier("n"), IntLiteral(3)), body=IntLiteral(1)),
                MatchArm(PatternIdentifier("n"), body=IntLiteral(0)),
            ],
        )
        self.assertEqual(ev.eval_expr(expr), 1)


# ============================================================
# 11. 内置函数
# ============================================================


class TestBuiltinFunctions(unittest.TestCase):
    """测试内置函数"""

    def test_builtin_abs(self):
        """abs 内置函数"""
        ev = make_eval()
        self.assertEqual(ev._builtin_abs(-5), 5.0)
        self.assertEqual(ev._builtin_abs(5), 5.0)

    def test_builtin_sqrt(self):
        """sqrt 内置函数"""
        ev = make_eval()
        self.assertAlmostEqual(ev._builtin_sqrt(4), 2.0)
        self.assertAlmostEqual(ev._builtin_sqrt(2), math.sqrt(2))

    def test_builtin_pow(self):
        """pow 内置函数"""
        ev = make_eval()
        self.assertAlmostEqual(ev._builtin_pow(2, 3), 8.0)

    def test_builtin_sum(self):
        """sum 内置函数"""
        ev = make_eval()
        self.assertEqual(ev._builtin_sum([1, 2, 3, 4, 5]), 15)

    def test_builtin_str_len(self):
        """str_len 内置函数"""
        ev = make_eval()
        self.assertEqual(ev._builtin_str_len("hello"), 5)
        self.assertEqual(ev._builtin_str_len(""), 0)

    def test_builtin_list_length(self):
        """list_length 内置函数"""
        ev = make_eval()
        self.assertEqual(ev._builtin_list_length([1, 2, 3]), 3)

    def test_builtin_head_some(self):
        """head 返回 Some"""
        ev = make_eval()
        result = ev._builtin_head([1, 2, 3])
        self.assertIsInstance(result, NovaADTValue)
        self.assertEqual(result.variant_name, "Some")
        self.assertEqual(result.fields, [1])

    def test_builtin_head_none(self):
        """head 空列表返回 None"""
        ev = make_eval()
        result = ev._builtin_head([])
        self.assertIsInstance(result, NovaADTValue)
        self.assertEqual(result.variant_name, "None")

    def test_builtin_tail_some(self):
        """tail 返回 Some（剩余列表）"""
        ev = make_eval()
        result = ev._builtin_tail([1, 2, 3])
        self.assertEqual(result.variant_name, "Some")
        self.assertEqual(result.fields, [[2, 3]])

    def test_builtin_tail_none(self):
        """tail 空列表返回 None"""
        ev = make_eval()
        result = ev._builtin_tail([])
        self.assertEqual(result.variant_name, "None")

    def test_builtin_int_to_str(self):
        """int_to_str 内置函数"""
        ev = make_eval()
        self.assertEqual(ev._builtin_int_to_str(42), "42")

    def test_builtin_str_to_int_some(self):
        """str_to_int 有效字符串返回 Some"""
        ev = make_eval()
        result = ev._builtin_str_to_int("123")
        self.assertEqual(result.variant_name, "Some")
        self.assertEqual(result.fields, [123])

    def test_builtin_str_to_int_none(self):
        """str_to_int 无效字符串返回 None"""
        ev = make_eval()
        result = ev._builtin_str_to_int("abc")
        self.assertEqual(result.variant_name, "None")

    def test_builtin_min_max(self):
        """min/max 内置函数"""
        ev = make_eval()
        self.assertEqual(ev._builtin_min(3, 7), 3.0)
        self.assertEqual(ev._builtin_max(3, 7), 7.0)

    def test_builtin_floor_ceil_round(self):
        """floor/ceil/round 内置函数"""
        ev = make_eval()
        self.assertEqual(ev._builtin_floor(3.7), 3.0)
        self.assertEqual(ev._builtin_ceil(3.2), 4.0)
        self.assertEqual(ev._builtin_round(3.5), 4.0)

    def test_builtin_pi(self):
        """pi 内置常量"""
        ev = make_eval()
        self.assertAlmostEqual(ev._builtin_pi(), math.pi)

    def test_builtin_print(self):
        """print 内置函数收集输出"""
        ev = make_eval()
        ev._builtin_print(42)
        ev._builtin_print("hello")
        self.assertEqual(ev.get_output(), ["42", "hello"])

    def test_builtin_json_parse(self):
        """json_parse 内置函数"""
        ev = make_eval()
        result = ev._builtin_json_parse('{"a": 1, "b": [2, 3]}')
        self.assertIsInstance(result, dict)
        self.assertEqual(result["a"], 1)
        self.assertEqual(result["b"], [2, 3])

    def test_builtin_json_stringify(self):
        """json_stringify 内置函数"""
        ev = make_eval()
        result = ev._builtin_json_stringify({"key": "value"})
        self.assertIn("key", result)
        self.assertIn("value", result)

    def test_builtin_filter(self):
        """filter 内置函数"""
        ev = make_eval()
        pred = NovaClosure(
            name="pred",
            params=[make_param("x")],
            body=BinaryOp(">", Identifier("x"), IntLiteral(2)),
            env=ev.env,
        )
        result = ev._builtin_filter(pred, [1, 2, 3, 4, 5])
        self.assertEqual(result, [3, 4, 5])

    def test_builtin_map(self):
        """map 内置函数"""
        ev = make_eval()
        map_fn = NovaClosure(
            name="double",
            params=[make_param("x")],
            body=BinaryOp("*", Identifier("x"), IntLiteral(2)),
            env=ev.env,
        )
        result = ev._builtin_map(map_fn, [1, 2, 3])
        self.assertEqual(result, [2, 4, 6])


# ============================================================
# 12. 值格式化与辅助方法
# ============================================================


class TestFormatAndHelpers(unittest.TestCase):
    """测试 _format_value 和其他辅助方法"""

    def test_format_int(self):
        """格式化整数"""
        ev = make_eval()
        self.assertEqual(ev._format_value(42), "42")

    def test_format_string(self):
        """格式化字符串"""
        ev = make_eval()
        self.assertEqual(ev._format_value("hello"), "hello")

    def test_format_bool(self):
        """格式化布尔值"""
        ev = make_eval()
        self.assertEqual(ev._format_value(True), "true")
        self.assertEqual(ev._format_value(False), "false")

    def test_format_unit(self):
        """格式化 Unit 值"""
        ev = make_eval()
        self.assertEqual(ev._format_value(UNIT_VALUE), "()")

    def test_format_list(self):
        """格式化列表"""
        ev = make_eval()
        self.assertEqual(ev._format_value([1, 2, 3]), "[1, 2, 3]")

    def test_format_tuple(self):
        """格式化元组"""
        ev = make_eval()
        self.assertEqual(ev._format_value((1, "a")), "(1, a)")

    def test_format_closure(self):
        """格式化闭包"""
        ev = make_eval()
        c = NovaClosure("myfn", [], None, ev.env)
        self.assertEqual(ev._format_value(c), "<fn myfn>")

    def test_format_adt_value(self):
        """格式化 ADT 值"""
        ev = make_eval()
        v = NovaADTValue("Option", "Some", [42])
        self.assertEqual(ev._format_value(v), "Some(42)")

    def test_to_float(self):
        """_to_float 辅助方法"""
        ev = make_eval()
        self.assertEqual(ev._to_float(5), 5.0)
        self.assertEqual(ev._to_float(5.5), 5.5)
        # bool 不应转换为 float
        self.assertTrue(ev._to_float(True) is True)

    def test_call_fn_partial_application(self):
        """内置函数部分应用（柯里化）"""
        ev = make_eval()
        builtin = BuiltinFn("add", lambda a, b: a + b, 2)
        curried = ev._call_fn(builtin, [3])
        self.assertIsInstance(curried, BuiltinFn)
        self.assertEqual(curried.fn(4), 7)


# ============================================================
# 13. ADT 值与类型定义
# ============================================================


class TestADTValues(unittest.TestCase):
    """测试 ADT 值和类型定义求值"""

    def test_adt_value_repr_with_fields(self):
        """带字段的 ADT 值 repr"""
        v = NovaADTValue("Option", "Some", [42])
        self.assertEqual(repr(v), "Some(42)")

    def test_adt_value_repr_without_fields(self):
        """无字段的 ADT 值 repr"""
        v = NovaADTValue("Option", "None", [])
        self.assertEqual(repr(v), "None")

    def test_adt_value_equality(self):
        """ADT 值相等性比较"""
        v1 = NovaADTValue("Option", "Some", [1])
        v2 = NovaADTValue("Option", "Some", [1])
        v3 = NovaADTValue("Option", "Some", [2])
        v4 = NovaADTValue("Result", "Ok", [1])
        self.assertEqual(v1, v2)
        self.assertNotEqual(v1, v3)
        self.assertNotEqual(v1, v4)

    def test_typedef_registers_constructors(self):
        """TypeDef 注册构造器"""
        from nova.ast_nodes import TypeDef, VariantDef
        ev = make_eval()
        td = TypeDef(
            name="Color",
            variants=[
                VariantDef("Red", []),
                VariantDef("Green", []),
                VariantDef("Blue", []),
            ],
        )
        ev.eval_decl(td)
        # 无字段构造器应为 NovaADTValue
        red = ev.env.lookup("Red")
        self.assertIsInstance(red, NovaADTValue)
        self.assertEqual(red.variant_name, "Red")

    def test_typedef_with_fields_creates_function(self):
        """带字段的 TypeDef 构造器是函数"""
        from nova.ast_nodes import TypeDef, VariantDef
        ev = make_eval()
        td = TypeDef(
            name="Shape",
            variants=[
                VariantDef("Circle", [("r", None)]),
            ],
        )
        ev.eval_decl(td)
        circle = ev.env.lookup("Circle")
        self.assertIsInstance(circle, BuiltinFn)
        # 调用构造器
        result = circle.fn(5.0)
        self.assertIsInstance(result, NovaADTValue)
        self.assertEqual(result.variant_name, "Circle")
        self.assertEqual(result.fields, [5.0])


# ============================================================
# 14. JSON 转换
# ============================================================


class TestJsonConversion(unittest.TestCase):
    """测试 JSON 与 Nova 值之间的转换"""

    def test_convert_json_to_nova_int(self):
        """JSON int 转换为 Nova int"""
        ev = make_eval()
        self.assertEqual(ev._convert_json_to_nova(42), 42)

    def test_convert_json_to_nova_string(self):
        """JSON string 转换为 Nova string"""
        ev = make_eval()
        self.assertEqual(ev._convert_json_to_nova("hello"), "hello")

    def test_convert_json_to_nova_null(self):
        """JSON null 转换为 Nova None ADT"""
        ev = make_eval()
        result = ev._convert_json_to_nova(None)
        self.assertIsInstance(result, NovaADTValue)
        self.assertEqual(result.variant_name, "None")

    def test_convert_json_to_nova_list(self):
        """JSON list 转换为 Nova list"""
        ev = make_eval()
        self.assertEqual(ev._convert_json_to_nova([1, 2, 3]), [1, 2, 3])

    def test_convert_json_to_nova_dict(self):
        """JSON dict 转换为 Python dict"""
        ev = make_eval()
        result = ev._convert_json_to_nova({"a": 1, "b": 2})
        self.assertEqual(result, {"a": 1, "b": 2})

    def test_convert_nova_to_json_unit(self):
        """UNIT_VALUE 转换为 JSON null"""
        ev = make_eval()
        self.assertIsNone(ev._convert_nova_to_json(UNIT_VALUE))

    def test_convert_nova_to_json_none_adt(self):
        """None ADT 转换为 JSON null"""
        ev = make_eval()
        none_val = NovaADTValue("Option", "None", [])
        self.assertIsNone(ev._convert_nova_to_json(none_val))

    def test_convert_nova_to_json_some_adt(self):
        """Some ADT 转换为内部值"""
        ev = make_eval()
        some_val = NovaADTValue("Option", "Some", [42])
        self.assertEqual(ev._convert_nova_to_json(some_val), 42)

    def test_convert_nova_to_json_list(self):
        """Nova list 转换为 JSON list"""
        ev = make_eval()
        self.assertEqual(ev._convert_nova_to_json([1, 2, 3]), [1, 2, 3])

    def test_convert_nova_to_json_tuple(self):
        """Nova tuple 转换为 JSON list"""
        ev = make_eval()
        self.assertEqual(ev._convert_nova_to_json((1, 2)), [1, 2])

    def test_convert_nova_to_json_dict(self):
        """Nova dict 转换为 JSON dict"""
        ev = make_eval()
        self.assertEqual(ev._convert_nova_to_json({"a": 1}), {"a": 1})


# ============================================================
# 15. 程序求值
# ============================================================


class TestProgramEval(unittest.TestCase):
    """测试顶层程序求值"""

    def test_eval_program_with_let(self):
        """程序中 let 绑定注册到全局环境"""
        from nova.ast_nodes import Program
        ev = make_eval()
        prog = Program([LetBinding("x", IntLiteral(42))])
        ev.eval_program(prog)
        self.assertEqual(ev.env.lookup("x"), 42)

    def test_eval_program_calls_main(self):
        """程序自动调用 main 函数"""
        from nova.ast_nodes import Program
        ev = make_eval()
        main_fn = FnDef("main", [], body=Block([], IntLiteral(99)))
        prog = Program([main_fn])
        ev.eval_program(prog)
        # main 被调用后，如果返回值被 print 则在输出中
        # 这里 main 返回 99 但没有 print，所以输出为空
        self.assertEqual(ev.get_output(), [])

    def test_eval_program_without_main(self):
        """没有 main 函数时程序正常结束"""
        from nova.ast_nodes import Program
        ev = make_eval()
        prog = Program([LetBinding("x", IntLiteral(1))])
        ev.eval_program(prog)  # 不应抛出异常


if __name__ == "__main__":
    unittest.main()
