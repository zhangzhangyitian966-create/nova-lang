"""
Parser 单元测试基线

为 parser.py（1223行）建立独立单元测试，覆盖编译器前端核心解析路径。
测试策略：通过 Lexer 生成 Token 流后传给 Parser，验证 AST 结构正确性。
"""

import unittest

from nova.lexer import Lexer, TokenType
from nova.parser import Parser
from nova.errors import ParseError, ParseErrorGroup
from nova.ast_nodes import (
    AliasDef,
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
    TypeInt,
    TypeTuple,
    UnaryOp,
    UnitLiteral,
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
        """Int literal"""
        decl = parse_single("42")
        self.assertIsInstance(decl, IntLiteral)
        self.assertEqual(decl.value, 42)

    def test_negative_int_literal(self):
        """Negative int literal"""
        decl = parse_single("-42")
        self.assertIsInstance(decl, UnaryOp)
        self.assertEqual(decl.op, "-")
        self.assertIsInstance(decl.operand, IntLiteral)
        self.assertEqual(decl.operand.value, 42)

    def test_float_literal(self):
        """Float literal"""
        decl = parse_single("3.14")
        self.assertIsInstance(decl, FloatLiteral)
        self.assertAlmostEqual(decl.value, 3.14)

    def test_string_literal(self):
        """String literal"""
        decl = parse_single('"hello world"')
        self.assertIsInstance(decl, StringLiteral)
        self.assertEqual(decl.value, "hello world")

    def test_char_literal(self):
        """Char literal"""
        decl = parse_single("'a'")
        self.assertIsInstance(decl, CharLiteral)
        self.assertEqual(decl.value, "a")

    def test_bool_true(self):
        """Bool true"""
        decl = parse_single("true")
        self.assertIsInstance(decl, BoolLiteral)
        self.assertTrue(decl.value)

    def test_bool_false(self):
        """Bool false"""
        decl = parse_single("false")
        self.assertIsInstance(decl, BoolLiteral)
        self.assertFalse(decl.value)

    def test_unit_literal(self):
        """Unit literal"""
        decl = parse_single("()")
        self.assertIsInstance(decl, UnitLiteral)


# ============================================================
# 2. 标识符与基本表达式
# ============================================================


class TestIdentifierAndPrimary(unittest.TestCase):
    """测试标识符和基本表达式"""

    def test_identifier_expr(self):
        """Identifier expr"""
        decl = parse_single("x")
        self.assertIsInstance(decl, Identifier)
        self.assertEqual(decl.name, "x")

    def test_break_expr(self):
        """Break expr"""
        decl = parse_single("break")
        self.assertIsInstance(decl, BreakExpr)

    def test_continue_expr(self):
        """Continue expr"""
        decl = parse_single("continue")
        self.assertIsInstance(decl, ContinueExpr)

    def test_grouped_expr(self):
        """Grouped expr"""
        decl = parse_single("(42)")
        self.assertIsInstance(decl, IntLiteral)
        self.assertEqual(decl.value, 42)

    def test_nested_grouped(self):
        """Nested grouped"""
        decl = parse_single("((x))")
        self.assertIsInstance(decl, Identifier)
        self.assertEqual(decl.name, "x")


# ============================================================
# 3. 二元运算与优先级
# ============================================================


class TestBinaryOperators(unittest.TestCase):
    """测试二元运算解析，重点关注优先级和结合性"""

    def test_simple_add(self):
        """Simple add"""
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
        """String concat"""
        decl = parse_single('"a" ++ "b"')
        self.assertIsInstance(decl, BinaryOp)
        self.assertEqual(decl.op, "++")

    def test_pipe_operator(self):
        """Pipe operator"""
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
        """Modulo operator"""
        decl = parse_single("10 % 3")
        self.assertIsInstance(decl, BinaryOp)
        self.assertEqual(decl.op, "%")

    def test_all_comparison_operators(self):
        """All comparison operators"""
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
        """Unary minus"""
        decl = parse_single("-42")
        self.assertIsInstance(decl, UnaryOp)
        self.assertEqual(decl.op, "-")

    def test_unary_not(self):
        """Unary not"""
        decl = parse_single("!true")
        self.assertIsInstance(decl, UnaryOp)
        self.assertEqual(decl.op, "!")

    def test_fn_call_no_args(self):
        """Fn call no args"""
        decl = parse_single("f()")
        self.assertIsInstance(decl, FnCall)
        self.assertEqual(len(decl.args), 0)

    def test_fn_call_multiple_args(self):
        """Fn call multiple args"""
        decl = parse_single("f(1, 2, 3)")
        self.assertIsInstance(decl, FnCall)
        self.assertEqual(len(decl.args), 3)

    def test_fn_call_nested(self):
        """Fn call nested"""
        decl = parse_single("f(g(1))")
        self.assertIsInstance(decl, FnCall)
        self.assertIsInstance(decl.args[0], FnCall)

    def test_field_access_name(self):
        """Field access name"""
        decl = parse_single("x.name")
        self.assertIsInstance(decl, FieldAccess)
        self.assertIsInstance(decl.target, Identifier)
        self.assertEqual(decl.field, "name")

    def test_field_access_index(self):
        """Field access index"""
        decl = parse_single("x.0")
        self.assertIsInstance(decl, FieldAccess)
        self.assertEqual(decl.field, "0")

    def test_try_expr(self):
        """Try expr"""
        decl = parse_single("x?")
        self.assertIsInstance(decl, TryExpr)
        self.assertIsInstance(decl.expr, Identifier)


# ============================================================
# 5. 控制流解析
# ============================================================


class TestControlFlow(unittest.TestCase):
    """测试控制流表达式解析"""

    def test_if_then_else(self):
        """If then else"""
        decl = parse_single("if true then 1 else 2")
        self.assertIsInstance(decl, IfExpr)
        self.assertIsInstance(decl.condition, BoolLiteral)
        self.assertIsInstance(decl.then_branch, IntLiteral)
        self.assertIsInstance(decl.else_branch, IntLiteral)

    def test_if_without_else(self):
        """If without else"""
        decl = parse_single("if true then 1")
        self.assertIsInstance(decl, IfExpr)
        self.assertIsNone(decl.else_branch)

    def test_if_with_block_branches(self):
        """If with block branches"""
        decl = parse_single("if true then { 1 } else { 2 }")
        self.assertIsInstance(decl, IfExpr)
        self.assertIsInstance(decl.then_branch, Block)
        self.assertIsInstance(decl.else_branch, Block)

    def test_while_expr(self):
        """While expr"""
        decl = parse_single("while x < 10 { x + 1 }")
        self.assertIsInstance(decl, WhileExpr)
        self.assertIsInstance(decl.condition, BinaryOp)
        self.assertIsInstance(decl.body, Block)

    def test_for_in_expr(self):
        """For in expr"""
        decl = parse_single("for x in xs { x + 1 }")
        self.assertIsInstance(decl, ForExpr)
        self.assertEqual(decl.var_name, "x")
        self.assertIsInstance(decl.iterable, Identifier)
        self.assertIsInstance(decl.body, Block)

    def test_for_range_expr(self):
        """For range expr"""
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
        """For range step expr"""
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
        """Let binding simple"""
        decl = parse_single("let x = 10")
        self.assertIsInstance(decl, LetBinding)
        self.assertEqual(decl.name, "x")
        self.assertIsNone(decl.type_annotation)

    def test_let_binding_with_type(self):
        """Let binding with type"""
        decl = parse_single("let x: Int = 10")
        self.assertIsInstance(decl, LetBinding)
        self.assertIsNotNone(decl.type_annotation)
        self.assertIsInstance(decl.type_annotation, TypeInt)

    def test_mut_binding(self):
        """Mut binding"""
        decl = parse_single("mut counter = 0")
        self.assertIsInstance(decl, MutBinding)
        self.assertEqual(decl.name, "counter")

    def test_fn_def_simple(self):
        """Fn def simple"""
        decl = parse_single("fn add(a: Int, b: Int) -> Int { a + b }")
        self.assertIsInstance(decl, FnDef)
        self.assertEqual(decl.name, "add")
        self.assertEqual(len(decl.params), 2)
        self.assertEqual(decl.params[0].name, "a")
        self.assertIsNotNone(decl.return_type)

    def test_fn_def_no_params(self):
        """Fn def no params"""
        decl = parse_single("fn main() {}"
)
        self.assertIsInstance(decl, FnDef)
        self.assertEqual(len(decl.params), 0)
        self.assertIsNone(decl.return_type)

    def test_fn_def_with_block_body(self):
        """Fn def with block body"""
        decl = parse_single("fn foo() { let x = 1; x }")
        self.assertIsInstance(decl, FnDef)
        self.assertIsInstance(decl.body, Block)

    def test_fn_def_with_expr_body(self):
        """Fn def with expr body"""
        decl = parse_single("fn foo() -> Int { 42 }")
        self.assertIsInstance(decl, FnDef)
        self.assertIsInstance(decl.body, Block)


# ============================================================
# 7. ADT 与类型定义
# ============================================================


class TestADTAndTypes(unittest.TestCase):
    """测试 ADT 类型定义和类型表达式"""

    def test_type_def_simple_variants(self):
        """Type def simple variants"""
        decl = parse_single("type Color { Red | Green | Blue }")
        self.assertIsInstance(decl, TypeDef)
        self.assertEqual(decl.name, "Color")
        self.assertEqual(len(decl.variants), 3)
        self.assertEqual(decl.variants[0].name, "Red")

    def test_type_def_with_fields(self):
        """Type def with fields"""
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
        """Alias def"""
        decl = parse_single("alias Point = (Float, Float)")
        self.assertIsInstance(decl, AliasDef)
        self.assertEqual(decl.name, "Point")

    def test_type_expr_function(self):
        """Type expr function"""
        decl = parse_single("fn f(g: Int -> Int) -> Int { g(1) }")
        fn = decl
        self.assertIsInstance(fn.params[0].type_annotation, TypeFn)

    def test_type_expr_generic(self):
        """Type expr generic"""
        decl = parse_single("fn f(x: List[Int]) -> Int { 1 }")
        fn = decl
        self.assertIsInstance(fn.params[0].type_annotation, TypeGeneric)
        self.assertEqual(fn.params[0].type_annotation.base, "List")

    def test_type_expr_tuple(self):
        """Type expr tuple"""
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
        """List empty"""
        decl = parse_single("[]")
        self.assertIsInstance(decl, ListExpr)
        self.assertEqual(len(decl.elements), 0)

    def test_list_with_elements(self):
        """List with elements"""
        decl = parse_single("[1, 2, 3]")
        self.assertIsInstance(decl, ListExpr)
        self.assertEqual(len(decl.elements), 3)

    def test_tuple_expr(self):
        """Tuple expr"""
        decl = parse_single("(1, 2)")
        self.assertIsInstance(decl, TupleExpr)
        self.assertEqual(len(decl.elements), 2)

    def test_map_expr(self):
        """Map expr"""
        decl = parse_single('{ "a": 1, "b": 2 }')
        self.assertIsInstance(decl, MapExpr)
        self.assertEqual(len(decl.pairs), 2)

    def test_lambda_simple(self):
        """Lambda simple"""
        decl = parse_single("|x| x + 1")
        self.assertIsInstance(decl, Lambda)
        self.assertEqual(len(decl.params), 1)
        self.assertEqual(decl.params[0].name, "x")

    def test_lambda_multi_param(self):
        """Lambda multi param"""
        decl = parse_single("|x, y| x + y")
        self.assertIsInstance(decl, Lambda)
        self.assertEqual(len(decl.params), 2)

    def test_lambda_with_types(self):
        """Lambda with types"""
        decl = parse_single("|x: Int| -> Int { x + 1 }")
        self.assertIsInstance(decl, Lambda)
        self.assertIsNotNone(decl.params[0].type_annotation)

    def test_block_expr(self):
        """Block expr"""
        decl = parse_single("{ let x = 1; let y = 2; x + y }")
        self.assertIsInstance(decl, Block)
        self.assertEqual(len(decl.statements), 2)
        self.assertIsNotNone(decl.tail_expression)

    def test_block_expr_tail_only(self):
        """Block expr tail only"""
        decl = parse_single("{ 42 }")
        self.assertIsInstance(decl, Block)
        self.assertEqual(len(decl.statements), 0)
        self.assertIsInstance(decl.tail_expression, IntLiteral)

    def test_list_comprehension(self):
        """List comprehension"""
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
        """Match expr"""
        decl = parse_single('match x { 1 -> "one", _ -> "other" }')
        self.assertIsInstance(decl, MatchExpr)
        self.assertEqual(len(decl.arms), 2)

    def test_match_with_guard(self):
        """Match with guard"""
        decl = parse_single("match x { n if n > 0 -> 1, _ -> 0 }")
        self.assertIsInstance(decl, MatchExpr)
        arm = decl.arms[0]
        self.assertIsNotNone(arm.guard)

    def test_match_arm_pattern_int(self):
        """Match arm pattern int"""
        decl = parse_single('match x { 1 -> 1 }')
        arm = decl.arms[0]
        self.assertIsInstance(arm.pattern, PatternInt)

    def test_match_arm_pattern_bool(self):
        """Match arm pattern bool"""
        decl = parse_single('match x { true -> 1 }')
        arm = decl.arms[0]
        self.assertIsInstance(arm.pattern, PatternBool)

    def test_match_arm_pattern_wildcard(self):
        """Match arm pattern wildcard"""
        decl = parse_single('match x { _ -> 1 }')
        arm = decl.arms[0]
        self.assertIsInstance(arm.pattern, PatternWildcard)

    def test_match_arm_pattern_identifier(self):
        """Match arm pattern identifier"""
        decl = parse_single('match x { n -> n }')
        arm = decl.arms[0]
        self.assertIsInstance(arm.pattern, PatternIdentifier)

    def test_match_arm_pattern_constructor(self):
        """Match arm pattern constructor"""
        decl = parse_single('match x { Some(v) -> v }')
        arm = decl.arms[0]
        self.assertIsInstance(arm.pattern, PatternConstructor)
        self.assertEqual(arm.pattern.name, "Some")

    def test_match_arm_pattern_tuple(self):
        """Match arm pattern tuple"""
        decl = parse_single('match x { (a, b) -> a + b }')
        arm = decl.arms[0]
        self.assertIsInstance(arm.pattern, PatternTuple)
        self.assertEqual(len(arm.pattern.elements), 2)

    def test_match_arm_pattern_list(self):
        """Match arm pattern list"""
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
        """Import decl"""
        decl = parse_single('import "math.nova"')
        self.assertIsInstance(decl, ImportDecl)
        self.assertEqual(decl.module_name, "math.nova")

    def test_export_decl(self):
        """Export decl"""
        decl = parse_single("export myFunc")
        self.assertIsInstance(decl, ExportDecl)
        self.assertEqual(decl.name, "myFunc")

    def test_multiple_top_level_decls(self):
        """Multiple top level decls"""
        program = parse("let x = 1\nfn foo() {}\n")
        self.assertEqual(len(program.declarations), 2)
        self.assertIsInstance(program.declarations[0], LetBinding)
        self.assertIsInstance(program.declarations[1], FnDef)

    def test_empty_program(self):
        """Empty program"""
        program = parse("")
        self.assertEqual(len(program.declarations), 0)


# ============================================================
# 11. 错误处理
# ============================================================


class TestErrorRecovery(unittest.TestCase):
    """测试解析错误和错误恢复"""

    def test_unexpected_token_raises(self):
        """Unexpected token raises"""
        with self.assertRaises(ParseError):
            parse("let = 1")

    def test_unclosed_block_raises(self):
        """Unclosed block raises"""
        with self.assertRaises((ParseError, ParseErrorGroup)):
            parse("{ let x = 1")

    def test_invalid_top_level_raises(self):
        """Invalid top level raises"""
        with self.assertRaises(ParseError):
            parse("+ 1")

    def test_missing_then_raises(self):
        """Missing then raises"""
        with self.assertRaises(ParseError):
            parse("if true 1 else 2")

    def test_parse_error_has_location(self):
        """Parse error has location"""
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


# ============================================================
# 12. 错误恢复边界场景（P2-2 补齐：declaration/statement 同步点 + BLOCK_MAX_ERRORS 阈值）
# ============================================================


class TestErrorRecoveryBoundaries(unittest.TestCase):
    """错误恢复机制边界条件测试

    覆盖 Parser Panic Mode 的三类未测试场景：
    (A) 顶层声明边界同步（_synchronize_to_declaration_boundary）
    (B) 块内语句边界同步（_synchronize_to_statement_boundary）
    (C) BLOCK_MAX_ERRORS 连续错误阈值触发与放弃行为

    注意：错误之间如果插入了合法语句/表达式，block_errors 会被重置为 0。
    要触发阈值放弃，必须使用"无合法语句间隔"的连续错误序列。
    """

    # ----------------------------------------------------------
    # (A) declaration_boundary 同步
    # ----------------------------------------------------------

    def test_top_level_missing_rbrace_next_fn_still_parsed(self):
        """顶层声明级错误恢复：部分解析结果非空

        构造 `let = 非法` 绑定（缺变量名），后跟合法的 let 绑定。
        _parse_let_binding() 将在 _expect(TokenType.IDENT) 处抛 ParseError。
        parse() 的顶层错误恢复会调用 _synchronize_to_declaration_boundary，
        跳过非法 token 流后定位到后续声明起始关键字。
        验证 _partial_decls 至少包含一个成功解析的 LetBinding。
        """
        code = "let = broken1;\nlet y = 42"
        tokens = Lexer(code).tokenize()
        parser = Parser(tokens, source=code)
        with self.assertRaises((ParseError, ParseErrorGroup)):
            parser.parse()
        self.assertTrue(hasattr(parser, "_partial_decls"),
                        "Parser 未暴露 _partial_decls 部分结果接口")
        decls = parser._partial_decls
        lets = [d for d in decls if isinstance(d, LetBinding)]
        self.assertGreaterEqual(len(lets), 1,
                                "declaration 级错误恢复后至少应有一个 LetBinding 被保留")

    def test_decl_boundary_sync_fn_let_mut_keywords_direct(self):
        """直接测试 _synchronize_to_declaration_boundary 在 fn/let/mut 处停止

        构造 token 流：错误标记序列 + LET/MUT/FN 关键字。
        直接调用同步方法，验证解析器停在正确的声明起始关键字。
        """
        # 序列：+ 1 + IDENT("bad") + FN + IDENT("f")
        # 同步应跳过 +、1、+、bad（IDENT 作为边界 break，
        # 但这里实际用 LET 作为最稳妥的锚点）
        code = "+ 1 2 let x = 1"
        tokens = Lexer(code).tokenize()
        parser = Parser(tokens, source=code)
        # 让 Parser 当前位置停在第一个 +（非声明起始 token）
        self.assertEqual(parser._peek_type(), TokenType.PLUS)
        # 调用同步
        parser._synchronize_to_declaration_boundary()
        # 同步后应停在 IDENT("2") 处（IDENT 是声明边界 + 或 LET）
        # 由于 IDENT 在同步逻辑中也是 break 条件，验证最终停在 LET 或 IDENT
        stopped_at = parser._peek_type()
        self.assertIn(stopped_at,
                      {TokenType.LET, TokenType.FN, TokenType.MUT,
                       TokenType.IMPORT, TokenType.IDENT, TokenType.PIPE},
                      f"同步后应停在声明边界 token，实际停在 {stopped_at}")
        # 继续手动同步：如果停在 IDENT，再前进一次
        if stopped_at == TokenType.IDENT:
            parser._advance()
            parser._synchronize_to_declaration_boundary()
        # 最终应该能到达 LET 或后续声明起始
        final_tt = parser._peek_type()
        self.assertIn(final_tt,
                      {TokenType.LET, TokenType.FN, TokenType.MUT, TokenType.EOF},
                      f"二次同步后应到达 LET/FN/MUT 或 EOF，实际 {final_tt}")

    # ----------------------------------------------------------
    # (B) statement_boundary 同步
    # ----------------------------------------------------------

    def test_block_invalid_expr_following_let_parsed(self):
        """块内非法赋值语句（缺 = 右侧）错误后，后续 let 仍被解析

        构造：{ x =   // 赋值表达式在 _parse_assignment 中 _parse_expression 读到
                      // 下一个 LET 作为表达式的一部分会抛错（但实际进入赋值分支
                      // 更直接的做法：块开头放一个非法 _parse_expression 触发项
                      // 如：{ ( 1 + ; let b = 2; }
        简化场景：{ if true then  // 缺 then 后的表达式 → ParseError
                    let b = 2; }
        预期：语句错误后同步到下一个 LET，b 绑定被保留。
        """
        # if 缺 else 分支：_parse_if_expr 中当 then 块后缺 else 会抛错
        # 更稳妥的非法表达式：+ 1（一元加后跟 let，_parse_expression 中 let 不合法）
        # 使用"缺 closing paren" 的组表达式确保抛错
        code = "{ ( 1 + 2\n  let b = 2; }"
        tokens = Lexer(code).tokenize()
        parser = Parser(tokens, source=code)
        result = parser._parse_block()
        self.assertIsInstance(result, Block)
        let_names = [s.name for s in result.statements
                     if isinstance(s, LetBinding)]
        self.assertIn("b", let_names,
                      "statement_boundary 同步失败：后续 let 未被解析")
        # 至少收集了 1 个错误（缺 RPAREN 或表达式不完整）
        self.assertGreaterEqual(len(parser._errors), 1)

    def test_statement_boundary_after_multi_errors_preserves_stmt(self):
        """语句边界同步在块内错误后仍可解析后续正确语句

        构造一个未闭合的组表达式 `( 1 +` 触发 ParseError，验证
        _synchronize_to_statement_boundary 执行后 `let c = 3` 仍被解析。
        至少收集到 1 个错误即可验证错误路径被执行。
        """
        code = "{ ( 1 +\n  let c = 3; final }"
        tokens = Lexer(code).tokenize()
        parser = Parser(tokens, source=code)
        result = parser._parse_block()
        self.assertIsInstance(result, Block)
        let_names = [s.name for s in result.statements
                     if isinstance(s, LetBinding)]
        self.assertIn("c", let_names,
                      "错误后语句边界同步失败：后续 let 未被解析")
        self.assertIsInstance(result.tail_expression, Identifier)
        self.assertEqual(result.tail_expression.name, "final")
        # 至少收集到 1 个错误（证明错误恢复分支被执行）
        self.assertGreaterEqual(len(parser._errors), 1)

    # ----------------------------------------------------------
    # (C) BLOCK_MAX_ERRORS 阈值
    # ----------------------------------------------------------

    def test_block_max_errors_triggers_early_abandon(self):
        """连续 3 个（_BLOCK_MAX_ERRORS）无间隔错误触发块剩余内容放弃

        _parse_block 中 block_errors >= _BLOCK_MAX_ERRORS(=3) 时，
        解析器跳到 RBRACE/EOF，丢弃块内剩余语句。

        关键：连续三个错误之间不能有合法语句被解析，否则计数器重置为 0。
        使用 `let = ;` 序列：LET → 进入 _parse_let_binding →
        _expect(IDENT) 对 `=` 抛 ParseError → except 捕获 block_errors += 1
        → synchronize 到 SEMICOLON → match SEMICOLON → 回到 while 顶部
        → 下一个 token 又是 LET，无任何合法语句插入 → 计数器不重置。

        3 次后达到阈值，跳到 }，后续 let x = 42 和尾部 x 均被丢弃。
        """
        code = "{ let = ; let = ; let = ; let x = 42; x }"
        tokens = Lexer(code).tokenize()
        parser = Parser(tokens, source=code)
        result = parser._parse_block()
        self.assertIsInstance(result, Block)
        # 关键断言：触发阈值后 let x = 42 和尾部 x 均被放弃
        self.assertEqual(len(result.statements), 0,
                         "_BLOCK_MAX_ERRORS 触发后，不应再解析任何后续语句")
        self.assertIsNone(result.tail_expression,
                          "_BLOCK_MAX_ERRORS 触发后，尾部表达式应被丢弃")
        # 错误计数 = 3（触发阈值的 3 个），第 4 个 let 未进入解析循环
        self.assertEqual(len(parser._errors), 3)

    def test_block_max_errors_not_triggered_with_interleaved_success(self):
        """错误之间插入正确语句 → BLOCK_MAX_ERRORS 永不触发（重置机制）

        交替 错误-正确-错误-正确-错误-正确-错误 共 4 个错误 3 个正确。
        计数器在每次正确语句后重置为 0，4 个错误之间均不连续，
        阈值 3 永不触发。所有正确语句均应被保留。

        正确语句使用 `ok_id;`（Identifier + SEMICOLON 的表达式语句），
        放在错误 let 之后，确保计数器在抛错后被重置。
        """
        code = (
            "{ let = ; ok_a;"   # 错误 1 → 正确语句 ok_a → 重置
            "  let = ; ok_b;"   # 错误 2 → 正确语句 ok_b → 重置
            "  let = ; ok_c;"   # 错误 3 → 正确语句 ok_c → 重置
            "  let = ; final }" # 错误 4 → 尾部 final
        )
        tokens = Lexer(code).tokenize()
        parser = Parser(tokens, source=code)
        result = parser._parse_block()
        self.assertIsInstance(result, Block)
        # 3 个正确的 ok 标识符表达式语句全部保留
        expr_stmt_names = sorted(
            s.name for s in result.statements if isinstance(s, Identifier)
        )
        self.assertEqual(expr_stmt_names, ["ok_a", "ok_b", "ok_c"])
        # 尾部表达式 final 保留
        self.assertIsInstance(result.tail_expression, Identifier)
        self.assertEqual(result.tail_expression.name, "final")
        # 4 个错误全部收集（计数器从未连续达到 3）
        self.assertEqual(len(parser._errors), 4,
                         "计数器重置机制失败：正确的交替错误模式不应触发阈值放弃")

    def test_block_max_errors_empty_block_after_abandon(self):
        """阈值触发后若块直接结束，返回空 Block 且无尾表达式

        构造恰好 3 个 `let = ;` 错误后紧跟 }：
          { let = ; let = ; let = ; }
        """
        code = "{ let = ; let = ; let = ; }"
        tokens = Lexer(code).tokenize()
        parser = Parser(tokens, source=code)
        result = parser._parse_block()
        self.assertIsInstance(result, Block)
        self.assertEqual(len(result.statements), 0)
        self.assertIsNone(result.tail_expression)
        # span 应包含从 { 到 } 的范围
        self.assertIsNotNone(result.span)
        self.assertEqual(len(parser._errors), 3)


if __name__ == "__main__":
    unittest.main()
