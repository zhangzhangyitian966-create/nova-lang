"""
Parser 单元测试基线

为 parser.py（1223行）建立独立单元测试，覆盖编译器前端核心解析路径。
测试策略：通过 Lexer 生成 Token 流后传给 Parser，验证 AST 结构正确性。
"""

import unittest

from nova.lexer import Lexer
from nova.parser import Parser
from nova.errors import ParseError, ParseErrorGroup
from nova.ast_nodes import (
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
    MatchArm,
    MatchExpr,
    MutBinding,
    Param,
    PatternBool,
    PatternConstructor,
    PatternIdentifier,
    PatternInt,
    PatternList,
    PatternTuple,
    PatternWildcard,
    PipeExpr,
    Program,
    StringLiteral,
    TryExpr,
    TupleExpr,
    TypeDef,
    TypeFn,
    TypeGeneric,
    TypeIdentifier,
    TypeInt,
    TypeTuple,
    UnaryOp,
    UnitLiteral,
    VariantDef,
    WhileExpr,
)


def parse(source: str) -> Program:
    """快捷解析：源代码 -> AST"""
    tokens = Lexer(source).tokenize()
    return Parser(tokens, source=source).parse()


def parse_single(source: str):
    """解析并返回单个顶层声明/表达式"""
    program = parse(source)
    assert len(program.declarations) == 1, f"期望1个声明，得到{len(program.declarations)}个"
    return program.declarations[0]


# ============================================================
# 1. 字面量解析
# ============================================================


class TestLiteralParsing(unittest.TestCase):
    """测试字面量解析"""

    def test_int_literal(self):
        decl = parse_single("42")
        self.assertIsInstance(decl, IntLiteral)
        self.assertEqual(decl.value, 42)

    def test_negative_int_literal(self):
        decl = parse_single("-42")
        self.assertIsInstance(decl, UnaryOp)
        self.assertEqual(decl.op, "-")
        self.assertIsInstance(decl.operand, IntLiteral)
        self.assertEqual(decl.operand.value, 42)

    def test_float_literal(self):
        decl = parse_single("3.14")
        self.assertIsInstance(decl, FloatLiteral)
        self.assertAlmostEqual(decl.value, 3.14)

    def test_string_literal(self):
        decl = parse_single('"hello world"')
        self.assertIsInstance(decl, StringLiteral)
        self.assertEqual(decl.value, "hello world")

    def test_char_literal(self):
        decl = parse_single("'a'")
        self.assertIsInstance(decl, CharLiteral)
        self.assertEqual(decl.value, "a")

    def test_bool_true(self):
        decl = parse_single("true")
        self.assertIsInstance(decl, BoolLiteral)
        self.assertTrue(decl.value)

    def test_bool_false(self):
        decl = parse_single("false")
        self.assertIsInstance(decl, BoolLiteral)
        self.assertFalse(decl.value)

    def test_unit_literal(self):
        decl = parse_single("()")
        self.assertIsInstance(decl, UnitLiteral)


# ============================================================
# 2. 标识符与基本表达式
# ============================================================


class TestIdentifierAndPrimary(unittest.TestCase):
    """测试标识符和基本表达式"""

    def test_identifier_expr(self):
        decl = parse_single("x")
        self.assertIsInstance(decl, Identifier)
        self.assertEqual(decl.name, "x")

    def test_break_expr(self):
        decl = parse_single("break")
        self.assertIsInstance(decl, BreakExpr)

    def test_continue_expr(self):
        decl = parse_single("continue")
        self.assertIsInstance(decl, ContinueExpr)

    def test_grouped_expr(self):
        decl = parse_single("(42)")
        self.assertIsInstance(decl, IntLiteral)
        self.assertEqual(decl.value, 42)

    def test_nested_grouped(self):
        decl = parse_single("((x))")
        self.assertIsInstance(decl, Identifier)
        self.assertEqual(decl.name, "x")


# ============================================================
# 3. 二元运算与优先级
# ============================================================


class TestBinaryOperators(unittest.TestCase):
    """测试二元运算解析，重点关注优先级和结合性"""

    def test_simple_add(self):
        decl = parse_single("1 + 2")
        self.assertIsInstance(decl, BinaryOp)
        self.assertEqual(decl.op, "+")
        self.assertEqual(decl.left.value, 1)
        self.assertEqual(decl.right.value, 2)

    def test_precedence_mul_over_add(self):
        """1 + 2 * 3 应解析为 1 + (2 * 3)"""
        decl = parse_single("1 + 2 * 3")
        self.assertIsInstance(decl, BinaryOp)
        self.assertEqual(decl.op, "+")
        self.assertIsInstance(decl.right, BinaryOp)
        self.assertEqual(decl.right.op, "*")

    def test_precedence_add_over_eq(self):
        """1 + 2 == 3 应解析为 (1 + 2) == 3"""
        decl = parse_single("1 + 2 == 3")
        self.assertIsInstance(decl, BinaryOp)
        self.assertEqual(decl.op, "==")
        self.assertIsInstance(decl.left, BinaryOp)
        self.assertEqual(decl.left.op, "+")

    def test_precedence_and_over_or(self):
        """a && b || c 应解析为 (a && b) || c"""
        decl = parse_single("a && b || c")
        self.assertIsInstance(decl, BinaryOp)
        self.assertEqual(decl.op, "||")
        self.assertIsInstance(decl.left, BinaryOp)
        self.assertEqual(decl.left.op, "&&")

    def test_precedence_compare_over_and(self):
        """a < b && c < d 应解析为 (a < b) && (c < d)"""
        decl = parse_single("a < b && c < d")
        self.assertIsInstance(decl, BinaryOp)
        self.assertEqual(decl.op, "&&")
        self.assertIsInstance(decl.left, BinaryOp)
        self.assertEqual(decl.left.op, "<")
        self.assertIsInstance(decl.right, BinaryOp)
        self.assertEqual(decl.right.op, "<")

    def test_left_associativity_add(self):
        """1 + 2 + 3 应解析为 (1 + 2) + 3"""
        decl = parse_single("1 + 2 + 3")
        self.assertIsInstance(decl, BinaryOp)
        self.assertEqual(decl.op, "+")
        self.assertIsInstance(decl.left, BinaryOp)
        self.assertEqual(decl.left.op, "+")
        self.assertEqual(decl.left.left.value, 1)
        self.assertEqual(decl.left.right.value, 2)
        self.assertEqual(decl.right.value, 3)

    def test_string_concat(self):
        decl = parse_single('"a" ++ "b"')
        self.assertIsInstance(decl, BinaryOp)
        self.assertEqual(decl.op, "++")

    def test_pipe_operator(self):
        decl = parse_single("x |> f")
        self.assertIsInstance(decl, PipeExpr)
        self.assertIsInstance(decl.left, Identifier)
        self.assertIsInstance(decl.right, Identifier)

    def test_pipe_chain_left_associative(self):
        """x |> f |> g 应解析为 (x |> f) |> g"""
        decl = parse_single("x |> f |> g")
        self.assertIsInstance(decl, PipeExpr)
        self.assertIsInstance(decl.left, PipeExpr)
        self.assertEqual(decl.left.left.name, "x")
        self.assertEqual(decl.left.right.name, "f")
        self.assertEqual(decl.right.name, "g")

    def test_modulo_operator(self):
        decl = parse_single("10 % 3")
        self.assertIsInstance(decl, BinaryOp)
        self.assertEqual(decl.op, "%")

    def test_all_comparison_operators(self):
        for op in ["<", ">", "<=", ">=", "==", "!="]:
            with self.subTest(op=op):
                decl = parse_single(f"1 {op} 2")
                self.assertIsInstance(decl, BinaryOp)
                self.assertEqual(decl.op, op)


# ============================================================
# 4. 一元运算与后缀运算
# ============================================================


class TestUnaryAndPostfix(unittest.TestCase):
    """测试一元运算和后缀运算"""

    def test_unary_minus(self):
        decl = parse_single("-42")
        self.assertIsInstance(decl, UnaryOp)
        self.assertEqual(decl.op, "-")

    def test_unary_not(self):
        decl = parse_single("!true")
        self.assertIsInstance(decl, UnaryOp)
        self.assertEqual(decl.op, "!")

    def test_fn_call_no_args(self):
        decl = parse_single("f()")
        self.assertIsInstance(decl, FnCall)
        self.assertEqual(len(decl.args), 0)

    def test_fn_call_multiple_args(self):
        decl = parse_single("f(1, 2, 3)")
        self.assertIsInstance(decl, FnCall)
        self.assertEqual(len(decl.args), 3)

    def test_fn_call_nested(self):
        decl = parse_single("f(g(1))")
        self.assertIsInstance(decl, FnCall)
        self.assertIsInstance(decl.args[0], FnCall)

    def test_field_access_name(self):
        decl = parse_single("x.name")
        self.assertIsInstance(decl, FieldAccess)
        self.assertIsInstance(decl.target, Identifier)
        self.assertEqual(decl.field, "name")

    def test_field_access_index(self):
        decl = parse_single("x.0")
        self.assertIsInstance(decl, FieldAccess)
        self.assertEqual(decl.field, "0")

    def test_try_expr(self):
        decl = parse_single("x?")
        self.assertIsInstance(decl, TryExpr)
        self.assertIsInstance(decl.expr, Identifier)


# ============================================================
# 5. 控制流解析
# ============================================================


class TestControlFlow(unittest.TestCase):
    """测试控制流表达式解析"""

    def test_if_then_else(self):
        decl = parse_single("if true then 1 else 2")
        self.assertIsInstance(decl, IfExpr)
        self.assertIsInstance(decl.condition, BoolLiteral)
        self.assertIsInstance(decl.then_branch, IntLiteral)
        self.assertIsInstance(decl.else_branch, IntLiteral)

    def test_if_without_else(self):
        decl = parse_single("if true then 1")
        self.assertIsInstance(decl, IfExpr)
        self.assertIsNone(decl.else_branch)

    def test_if_with_block_branches(self):
        decl = parse_single("if true then { 1 } else { 2 }")
        self.assertIsInstance(decl, IfExpr)
        self.assertIsInstance(decl.then_branch, Block)
        self.assertIsInstance(decl.else_branch, Block)

    def test_while_expr(self):
        decl = parse_single("while x < 10 { x + 1 }")
        self.assertIsInstance(decl, WhileExpr)
        self.assertIsInstance(decl.condition, BinaryOp)
        self.assertIsInstance(decl.body, Block)

    def test_for_in_expr(self):
        decl = parse_single("for x in xs { x + 1 }")
        self.assertIsInstance(decl, ForExpr)
        self.assertEqual(decl.var_name, "x")
        self.assertIsInstance(decl.iterable, Identifier)
        self.assertIsInstance(decl.body, Block)

    def test_for_range_expr(self):
        decl = parse_single("for i <- 0..10 { i + 1 }")
        self.assertIsInstance(decl, ForExpr)
        self.assertEqual(decl.var_name, "i")
        # 范围循环的 iterable 是 ("range", start, end, step) 元组
        self.assertIsInstance(decl.iterable, tuple)
        self.assertEqual(decl.iterable[0], "range")
        self.assertIsInstance(decl.iterable[1], IntLiteral)
        self.assertIsInstance(decl.iterable[2], IntLiteral)
        self.assertIsNone(decl.iterable[3])

    def test_for_range_step_expr(self):
        decl = parse_single("for i <- 0..10 step 2 { i + 1 }")
        self.assertIsInstance(decl, ForExpr)
        self.assertEqual(decl.var_name, "i")
        self.assertIsInstance(decl.iterable, tuple)
        self.assertEqual(decl.iterable[0], "range")
        self.assertIsNotNone(decl.iterable[3])
        self.assertEqual(decl.iterable[3].value, 2)


# ============================================================
# 6. 绑定与函数定义
# ============================================================


class TestBindingsAndFunctions(unittest.TestCase):
    """测试 let/mut 绑定和函数定义"""

    def test_let_binding_simple(self):
        decl = parse_single("let x = 10")
        self.assertIsInstance(decl, LetBinding)
        self.assertEqual(decl.name, "x")
        self.assertIsNone(decl.type_annotation)

    def test_let_binding_with_type(self):
        decl = parse_single("let x: Int = 10")
        self.assertIsInstance(decl, LetBinding)
        self.assertIsNotNone(decl.type_annotation)
        self.assertIsInstance(decl.type_annotation, TypeInt)

    def test_mut_binding(self):
        decl = parse_single("mut counter = 0")
        self.assertIsInstance(decl, MutBinding)
        self.assertEqual(decl.name, "counter")

    def test_fn_def_simple(self):
        decl = parse_single("fn add(a: Int, b: Int) -> Int { a + b }")
        self.assertIsInstance(decl, FnDef)
        self.assertEqual(decl.name, "add")
        self.assertEqual(len(decl.params), 2)
        self.assertEqual(decl.params[0].name, "a")
        self.assertIsNotNone(decl.return_type)

    def test_fn_def_no_params(self):
        decl = parse_single("fn main() {}"
)
        self.assertIsInstance(decl, FnDef)
        self.assertEqual(len(decl.params), 0)
        self.assertIsNone(decl.return_type)

    def test_fn_def_with_block_body(self):
        decl = parse_single("fn foo() { let x = 1; x }")
        self.assertIsInstance(decl, FnDef)
        self.assertIsInstance(decl.body, Block)

    def test_fn_def_with_expr_body(self):
        decl = parse_single("fn foo() -> Int { 42 }")
        self.assertIsInstance(decl, FnDef)
        self.assertIsInstance(decl.body, Block)


# ============================================================
# 7. ADT 与类型定义
# ============================================================


class TestADTAndTypes(unittest.TestCase):
    """测试 ADT 类型定义和类型表达式"""

    def test_type_def_simple_variants(self):
        decl = parse_single("type Color { Red | Green | Blue }")
        self.assertIsInstance(decl, TypeDef)
        self.assertEqual(decl.name, "Color")
        self.assertEqual(len(decl.variants), 3)
        self.assertEqual(decl.variants[0].name, "Red")

    def test_type_def_with_fields(self):
        decl = parse_single("type Shape { Circle(r: Float) | Rect(w: Float, h: Float) }")
        self.assertIsInstance(decl, TypeDef)
        self.assertEqual(len(decl.variants), 2)
        circle = decl.variants[0]
        self.assertEqual(circle.name, "Circle")
        self.assertEqual(len(circle.fields), 1)
        rect = decl.variants[1]
        self.assertEqual(len(rect.fields), 2)

    def test_type_def_without_pipe(self):
        """变体定义可省略 | 分隔符"""
        decl = parse_single("type Status { Ok Err }")
        self.assertEqual(len(decl.variants), 2)

    def test_alias_def(self):
        decl = parse_single("alias Point = (Float, Float)")
        self.assertIsInstance(decl, AliasDef)
        self.assertEqual(decl.name, "Point")

    def test_type_expr_function(self):
        decl = parse_single("fn f(g: Int -> Int) -> Int { g(1) }")
        fn = decl
        self.assertIsInstance(fn.params[0].type_annotation, TypeFn)

    def test_type_expr_generic(self):
        decl = parse_single("fn f(x: List[Int]) -> Int { 1 }")
        fn = decl
        self.assertIsInstance(fn.params[0].type_annotation, TypeGeneric)
        self.assertEqual(fn.params[0].type_annotation.base, "List")

    def test_type_expr_tuple(self):
        decl = parse_single("fn f(x: (Int, String)) -> Int { 1 }")
        fn = decl
        self.assertIsInstance(fn.params[0].type_annotation, TypeTuple)
        self.assertEqual(len(fn.params[0].type_annotation.elements), 2)


# ============================================================
# 8. 复合表达式
# ============================================================


class TestCompoundExpressions(unittest.TestCase):
    """测试列表、Map、元组、lambda、块等复合表达式"""

    def test_list_empty(self):
        decl = parse_single("[]")
        self.assertIsInstance(decl, ListExpr)
        self.assertEqual(len(decl.elements), 0)

    def test_list_with_elements(self):
        decl = parse_single("[1, 2, 3]")
        self.assertIsInstance(decl, ListExpr)
        self.assertEqual(len(decl.elements), 3)

    def test_tuple_expr(self):
        decl = parse_single("(1, 2)")
        self.assertIsInstance(decl, TupleExpr)
        self.assertEqual(len(decl.elements), 2)

    def test_map_expr(self):
        decl = parse_single('{ "a": 1, "b": 2 }')
        self.assertIsInstance(decl, MapExpr)
        self.assertEqual(len(decl.pairs), 2)

    def test_lambda_simple(self):
        decl = parse_single("|x| x + 1")
        self.assertIsInstance(decl, Lambda)
        self.assertEqual(len(decl.params), 1)
        self.assertEqual(decl.params[0].name, "x")

    def test_lambda_multi_param(self):
        decl = parse_single("|x, y| x + y")
        self.assertIsInstance(decl, Lambda)
        self.assertEqual(len(decl.params), 2)

    def test_lambda_with_types(self):
        decl = parse_single("|x: Int| -> Int { x + 1 }")
        self.assertIsInstance(decl, Lambda)
        self.assertIsNotNone(decl.params[0].type_annotation)

    def test_block_expr(self):
        decl = parse_single("{ let x = 1; let y = 2; x + y }")
        self.assertIsInstance(decl, Block)
        self.assertEqual(len(decl.statements), 2)
        self.assertIsNotNone(decl.tail_expression)

    def test_block_expr_tail_only(self):
        decl = parse_single("{ 42 }")
        self.assertIsInstance(decl, Block)
        self.assertEqual(len(decl.statements), 0)
        self.assertIsInstance(decl.tail_expression, IntLiteral)

    def test_list_comprehension(self):
        decl = parse_single("[x * 2 for x in xs]")
        self.assertIsInstance(decl, ListComprehension)
        self.assertIsNotNone(decl.expr)
        self.assertEqual(decl.var_name, "x")
        self.assertIsNotNone(decl.iterable)


# ============================================================
# 9. Match 表达式与模式
# ============================================================


class TestPatternAndMatch(unittest.TestCase):
    """测试 match 表达式和模式解析"""

    def test_match_expr(self):
        decl = parse_single('match x { 1 -> "one", _ -> "other" }')
        self.assertIsInstance(decl, MatchExpr)
        self.assertEqual(len(decl.arms), 2)

    def test_match_with_guard(self):
        decl = parse_single("match x { n if n > 0 -> 1, _ -> 0 }")
        self.assertIsInstance(decl, MatchExpr)
        arm = decl.arms[0]
        self.assertIsNotNone(arm.guard)

    def test_match_arm_pattern_int(self):
        decl = parse_single('match x { 1 -> 1 }')
        arm = decl.arms[0]
        self.assertIsInstance(arm.pattern, PatternInt)

    def test_match_arm_pattern_bool(self):
        decl = parse_single('match x { true -> 1 }')
        arm = decl.arms[0]
        self.assertIsInstance(arm.pattern, PatternBool)

    def test_match_arm_pattern_wildcard(self):
        decl = parse_single('match x { _ -> 1 }')
        arm = decl.arms[0]
        self.assertIsInstance(arm.pattern, PatternWildcard)

    def test_match_arm_pattern_identifier(self):
        decl = parse_single('match x { n -> n }')
        arm = decl.arms[0]
        self.assertIsInstance(arm.pattern, PatternIdentifier)

    def test_match_arm_pattern_constructor(self):
        decl = parse_single('match x { Some(v) -> v }')
        arm = decl.arms[0]
        self.assertIsInstance(arm.pattern, PatternConstructor)
        self.assertEqual(arm.pattern.name, "Some")

    def test_match_arm_pattern_tuple(self):
        decl = parse_single('match x { (a, b) -> a + b }')
        arm = decl.arms[0]
        self.assertIsInstance(arm.pattern, PatternTuple)
        self.assertEqual(len(arm.pattern.elements), 2)

    def test_match_arm_pattern_list(self):
        decl = parse_single('match x { [a, b] -> a + b }')
        arm = decl.arms[0]
        self.assertIsInstance(arm.pattern, PatternList)
        self.assertEqual(len(arm.pattern.elements), 2)


# ============================================================
# 10. 顶层声明与模块结构
# ============================================================


class TestTopLevelAndModule(unittest.TestCase):
    """测试顶层声明和模块级结构"""

    def test_import_decl(self):
        decl = parse_single('import "math.nova"')
        self.assertIsInstance(decl, ImportDecl)
        self.assertEqual(decl.module_name, "math.nova")

    def test_export_decl(self):
        decl = parse_single("export myFunc")
        self.assertIsInstance(decl, ExportDecl)
        self.assertEqual(decl.name, "myFunc")

    def test_multiple_top_level_decls(self):
        program = parse("let x = 1\nfn foo() {}\n")
        self.assertEqual(len(program.declarations), 2)
        self.assertIsInstance(program.declarations[0], LetBinding)
        self.assertIsInstance(program.declarations[1], FnDef)

    def test_empty_program(self):
        program = parse("")
        self.assertEqual(len(program.declarations), 0)


# ============================================================
# 11. 错误处理
# ============================================================


class TestErrorRecovery(unittest.TestCase):
    """测试解析错误和错误恢复"""

    def test_unexpected_token_raises(self):
        with self.assertRaises(ParseError):
            parse("let = 1")

    def test_unclosed_block_raises(self):
        with self.assertRaises((ParseError, ParseErrorGroup)):
            parse("{ let x = 1")

    def test_invalid_top_level_raises(self):
        with self.assertRaises(ParseError):
            parse("+ 1")

    def test_missing_then_raises(self):
        with self.assertRaises(ParseError):
            parse("if true 1 else 2")

    def test_parse_error_has_location(self):
        with self.assertRaises(ParseError) as ctx:
            parse("let = 1")
        self.assertIsNotNone(ctx.exception.line)

    def test_block_error_recovery_counter_reset(self):
        """验证块内错误恢复计数器在正确语句后重置

        第 49 轮修复了 _parse_block 中 block_errors 计数器未重置的问题。
        此测试确保：错误语句之间的正确语句会重置计数器，不会过早触发
        _BLOCK_MAX_ERRORS（3 次）限制而放弃剩余块内容。
        """
        # block 内顺序：错误(let=1)、正确(let x=2)、错误(let=3)、正确(x 作为尾部)
        # 如果 block_errors 不重置，错误计数累积到 2 后，下一个错误就会触发放弃
        # 修复后，正确语句之间的错误不应累积
        code = "{ let = 1; let x = 2; let = 3; x }"
        tokens = Lexer(code).tokenize()
        parser = Parser(tokens, source=code)
        result = parser._parse_block()
        self.assertIsInstance(result, Block)
        # let x = 2 被成功解析为语句
        self.assertEqual(len(result.statements), 1)
        self.assertIsInstance(result.statements[0], LetBinding)
        self.assertEqual(result.statements[0].name, "x")
        # x 是尾部表达式
        self.assertIsInstance(result.tail_expression, Identifier)
        self.assertEqual(result.tail_expression.name, "x")
        # 验证收集了 2 个错误，但没有因为达到 _BLOCK_MAX_ERRORS 而放弃
        self.assertEqual(len(parser._errors), 2)


if __name__ == "__main__":
    unittest.main()
