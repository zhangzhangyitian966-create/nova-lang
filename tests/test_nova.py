"""
Nova 编程语言 - 测试套件

测试覆盖：
1. 词法分析（Lexer）
2. 语法分析（Parser）
3. 类型检查（Type Checker）
4. 求值器（Evaluator）
5. 内置函数
6. 综合集成测试
"""

import unittest

from nova.lexer import Lexer, TokenType
from nova.parser import Parser
from nova.type_checker import TypeChecker
from nova.evaluator import Evaluator
from nova.errors import LexerError, ParseError, TypeCheckError, RuntimeError_
from nova.ast_nodes import (
    IntLiteral,
    FloatLiteral,
    StringLiteral,
    BoolLiteral,
    Identifier,
    BinaryOp,
    LetBinding,
    FnDef,
    IfExpr,
    MatchExpr,
    ListExpr,
    Lambda,
    FnCall,
    PipeExpr,
    Block,
)

# ============================================================
# 辅助函数
# ============================================================


def tokenize(source: str):
    """快捷 tokenize"""
    return Lexer(source).tokenize()


def parse(source: str):
    """快捷 parse"""
    tokens = tokenize(source)
    return Parser(tokens).parse()


def type_check(source: str):
    """快捷类型检查"""
    ast = parse(source)
    checker = TypeChecker()
    checker.check_program(ast)
    return checker


def eval_source(source: str, check_types: bool = True):
    """快捷求值"""
    tokens = tokenize(source)
    ast = Parser(tokens).parse()
    if check_types:
        checker = TypeChecker()
        checker.check_program(ast)
    evaluator = Evaluator(check_types=check_types)
    evaluator.eval_program(ast)
    return evaluator


# ============================================================
# 词法分析测试
# ============================================================


class TestLexer(unittest.TestCase):
    """词法分析器测试"""

    def test_integer_token(self):
        tokens = tokenize("42")
        self.assertEqual(len(tokens), 2)  # INT + EOF
        self.assertEqual(tokens[0].type, TokenType.INT)
        self.assertEqual(tokens[0].value, "42")

    def test_float_token(self):
        tokens = tokenize("3.14")
        self.assertEqual(tokens[0].type, TokenType.FLOAT)
        self.assertEqual(tokens[0].value, "3.14")

    def test_string_token(self):
        tokens = tokenize('"hello world"')
        self.assertEqual(tokens[0].type, TokenType.STRING)
        self.assertEqual(tokens[0].value, "hello world")

    def test_char_token(self):
        tokens = tokenize("'a'")
        self.assertEqual(tokens[0].type, TokenType.CHAR)
        self.assertEqual(tokens[0].value, "a")

    def test_bool_tokens(self):
        tokens = tokenize("true false")
        self.assertEqual(tokens[0].type, TokenType.BOOL)
        self.assertEqual(tokens[0].value, "true")
        self.assertEqual(tokens[1].type, TokenType.BOOL)
        self.assertEqual(tokens[1].value, "false")

    def test_identifiers(self):
        tokens = tokenize("foo bar_baz _x")
        self.assertEqual(tokens[0].type, TokenType.IDENT)
        self.assertEqual(tokens[0].value, "foo")
        self.assertEqual(tokens[1].type, TokenType.IDENT)
        self.assertEqual(tokens[1].value, "bar_baz")
        # _x 含有字母，是普通标识符
        self.assertEqual(tokens[2].type, TokenType.IDENT)
        self.assertEqual(tokens[2].value, "_x")

    def test_keywords(self):
        tokens = tokenize("let mut fn if then else match type import export")
        values = [t.value for t in tokens if t.type != TokenType.EOF]
        expected = [
            "let",
            "mut",
            "fn",
            "if",
            "then",
            "else",
            "match",
            "type",
            "import",
            "export",
        ]
        self.assertEqual(values, expected)

    def test_arithmetic_operators(self):
        tokens = tokenize("+ - * / %")
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        expected = [
            TokenType.PLUS,
            TokenType.MINUS,
            TokenType.STAR,
            TokenType.SLASH,
            TokenType.PERCENT,
        ]
        self.assertEqual(types, expected)

    def test_comparison_operators(self):
        tokens = tokenize("== != < > <= >=")
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        expected = [
            TokenType.EQ,
            TokenType.NEQ,
            TokenType.LT,
            TokenType.GT,
            TokenType.LTE,
            TokenType.GTE,
        ]
        self.assertEqual(types, expected)

    def test_logical_operators(self):
        tokens = tokenize("&& || !")
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        expected = [TokenType.AND, TokenType.OR, TokenType.NOT]
        self.assertEqual(types, expected)

    def test_pipe_operator(self):
        tokens = tokenize("|>")
        self.assertEqual(tokens[0].type, TokenType.PIPE_GT)

    def test_arrow_operators(self):
        tokens = tokenize("-> =>")
        self.assertEqual(tokens[0].type, TokenType.ARROW)
        self.assertEqual(tokens[1].type, TokenType.FAT_ARROW)

    def test_string_concat(self):
        tokens = tokenize("++")
        self.assertEqual(tokens[0].type, TokenType.PLUSPLUS)

    def test_punctuation(self):
        tokens = tokenize("( ) [ ] { } , ; : .")
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        expected = [
            TokenType.LPAREN,
            TokenType.RPAREN,
            TokenType.LBRACKET,
            TokenType.RBRACKET,
            TokenType.LBRACE,
            TokenType.RBRACE,
            TokenType.COMMA,
            TokenType.SEMICOLON,
            TokenType.COLON,
            TokenType.DOT,
        ]
        self.assertEqual(types, expected)

    def test_unit_token(self):
        tokens = tokenize("()")
        # () 在 lexer 中是 LPAREN + RPAREN，由 parser 组合为 UnitLiteral
        self.assertEqual(tokens[0].type, TokenType.LPAREN)
        self.assertEqual(tokens[1].type, TokenType.RPAREN)

    def test_question_token(self):
        tokens = tokenize("?")
        self.assertEqual(tokens[0].type, TokenType.QUESTION)

    def test_comments(self):
        tokens = tokenize("42 // this is a comment\n100")
        non_eof = [t for t in tokens if t.type != TokenType.EOF]
        self.assertEqual(len(non_eof), 2)
        self.assertEqual(non_eof[0].value, "42")
        self.assertEqual(non_eof[1].value, "100")

    def test_line_numbers(self):
        tokens = tokenize("1\n2\n3")
        self.assertEqual(tokens[0].line, 1)
        self.assertEqual(tokens[1].line, 2)
        self.assertEqual(tokens[2].line, 3)

    def test_string_escape(self):
        tokens = tokenize('"hello\\nworld"')
        self.assertEqual(tokens[0].value, "hello\nworld")

    def test_illegal_char(self):
        with self.assertRaises(LexerError):
            tokenize("@")


# ============================================================
# 语法分析测试
# ============================================================


class TestParser(unittest.TestCase):
    """语法分析器测试"""

    def test_int_literal(self):
        ast = parse("42")
        self.assertIsInstance(ast.declarations[0], IntLiteral)
        self.assertEqual(ast.declarations[0].value, 42)

    def test_float_literal(self):
        ast = parse("3.14")
        self.assertIsInstance(ast.declarations[0], FloatLiteral)
        self.assertAlmostEqual(ast.declarations[0].value, 3.14)

    def test_string_literal(self):
        ast = parse('"hello"')
        self.assertIsInstance(ast.declarations[0], StringLiteral)
        self.assertEqual(ast.declarations[0].value, "hello")

    def test_bool_literal(self):
        ast = parse("true")
        self.assertIsInstance(ast.declarations[0], BoolLiteral)
        self.assertTrue(ast.declarations[0].value)

    def test_let_binding(self):
        ast = parse("let x = 10")
        decl = ast.declarations[0]
        self.assertIsInstance(decl, LetBinding)
        self.assertEqual(decl.name, "x")
        self.assertIsInstance(decl.value, IntLiteral)

    def test_let_with_type(self):
        ast = parse("let x: Int = 10")
        decl = ast.declarations[0]
        self.assertIsInstance(decl, LetBinding)
        self.assertIsNotNone(decl.type_annotation)

    def test_mut_binding(self):
        ast = parse("mut counter = 0")
        decl = ast.declarations[0]
        from nova.ast_nodes import MutBinding

        self.assertIsInstance(decl, MutBinding)
        self.assertEqual(decl.name, "counter")

    def test_fn_definition(self):
        ast = parse("fn add(a: Int, b: Int) -> Int { a + b }")
        decl = ast.declarations[0]
        self.assertIsInstance(decl, FnDef)
        self.assertEqual(decl.name, "add")
        self.assertEqual(len(decl.params), 2)
        self.assertEqual(decl.params[0].name, "a")
        self.assertEqual(decl.params[1].name, "b")

    def test_fn_no_params(self):
        ast = parse("fn main() -> Unit {}")
        decl = ast.declarations[0]
        self.assertIsInstance(decl, FnDef)
        self.assertEqual(decl.name, "main")
        self.assertEqual(len(decl.params), 0)

    def test_if_then_else(self):
        ast = parse("if true then 1 else 2")
        decl = ast.declarations[0]
        self.assertIsInstance(decl, IfExpr)
        self.assertIsInstance(decl.condition, BoolLiteral)
        self.assertIsInstance(decl.then_branch, IntLiteral)
        self.assertIsInstance(decl.else_branch, IntLiteral)

    def test_if_without_else(self):
        ast = parse("if true then 1")
        decl = ast.declarations[0]
        self.assertIsInstance(decl, IfExpr)
        self.assertIsNone(decl.else_branch)

    def test_binary_expr(self):
        ast = parse("1 + 2")
        decl = ast.declarations[0]
        self.assertIsInstance(decl, BinaryOp)
        self.assertEqual(decl.op, "+")
        self.assertEqual(decl.left.value, 1)
        self.assertEqual(decl.right.value, 2)

    def test_operator_precedence(self):
        """1 + 2 * 3 应解析为 1 + (2 * 3)"""
        ast = parse("1 + 2 * 3")
        decl = ast.declarations[0]
        self.assertIsInstance(decl, BinaryOp)
        self.assertEqual(decl.op, "+")
        self.assertIsInstance(decl.left, IntLiteral)
        self.assertIsInstance(decl.right, BinaryOp)
        self.assertEqual(decl.right.op, "*")

    def test_unary_minus(self):
        ast = parse("-42")
        from nova.ast_nodes import UnaryOp

        decl = ast.declarations[0]
        self.assertIsInstance(decl, UnaryOp)
        self.assertEqual(decl.op, "-")

    def test_unary_not(self):
        ast = parse("!true")
        from nova.ast_nodes import UnaryOp

        decl = ast.declarations[0]
        self.assertIsInstance(decl, UnaryOp)
        self.assertEqual(decl.op, "!")

    def test_list_expr(self):
        ast = parse("[1, 2, 3]")
        decl = ast.declarations[0]
        self.assertIsInstance(decl, ListExpr)
        self.assertEqual(len(decl.elements), 3)

    def test_fn_call(self):
        ast = parse("f(1, 2)")
        decl = ast.declarations[0]
        self.assertIsInstance(decl, FnCall)
        self.assertIsInstance(decl.callee, Identifier)
        self.assertEqual(len(decl.args), 2)

    def test_pipe_expr(self):
        ast = parse("x |> f")
        decl = ast.declarations[0]
        self.assertIsInstance(decl, PipeExpr)

    def test_match_expr(self):
        ast = parse('match x { 1 -> "one", _ -> "other" }')
        decl = ast.declarations[0]
        self.assertIsInstance(decl, MatchExpr)
        self.assertEqual(len(decl.arms), 2)

    def test_type_def(self):
        ast = parse("type Color { Red | Green | Blue }")
        from nova.ast_nodes import TypeDef

        decl = ast.declarations[0]
        self.assertIsInstance(decl, TypeDef)
        self.assertEqual(decl.name, "Color")
        self.assertEqual(len(decl.variants), 3)

    def test_type_def_with_fields(self):
        ast = parse("type Shape { Circle(r: Float) }")
        from nova.ast_nodes import TypeDef

        decl = ast.declarations[0]
        self.assertIsInstance(decl, TypeDef)
        self.assertEqual(decl.variants[0].name, "Circle")
        self.assertEqual(len(decl.variants[0].fields), 1)

    def test_alias_def(self):
        ast = parse("alias Point = (Float, Float)")
        from nova.ast_nodes import AliasDef

        decl = ast.declarations[0]
        self.assertIsInstance(decl, AliasDef)
        self.assertEqual(decl.name, "Point")

    def test_lambda(self):
        ast = parse("|x| x + 1")
        decl = ast.declarations[0]
        self.assertIsInstance(decl, Lambda)
        self.assertEqual(len(decl.params), 1)
        self.assertEqual(decl.params[0].name, "x")

    def test_lambda_with_types(self):
        ast = parse("|x: Int| -> Int { x + 1 }")
        decl = ast.declarations[0]
        self.assertIsInstance(decl, Lambda)
        self.assertIsNotNone(decl.params[0].type_annotation)

    def test_block(self):
        ast = parse("{ let x = 1; let y = 2; x + y }")
        decl = ast.declarations[0]
        self.assertIsInstance(decl, Block)
        self.assertEqual(len(decl.statements), 2)
        self.assertIsNotNone(decl.tail_expression)

    def test_import(self):
        ast = parse('import "math.nova"')
        from nova.ast_nodes import ImportDecl

        self.assertIsInstance(ast.declarations[0], ImportDecl)

    def test_export(self):
        ast = parse("export myFunc")
        from nova.ast_nodes import ExportDecl

        self.assertIsInstance(ast.declarations[0], ExportDecl)

    def test_string_concat(self):
        ast = parse('"a" ++ "b"')
        decl = ast.declarations[0]
        self.assertIsInstance(decl, BinaryOp)
        self.assertEqual(decl.op, "++")


# ============================================================
# 类型检查测试
# ============================================================


class TestTypeChecker(unittest.TestCase):
    """类型检查器测试"""

    def test_int_type(self):
        checker = type_check("42")
        ty = checker.check_expr(IntLiteral(value=42))
        self.assertEqual(str(ty), "Int")

    def test_string_type(self):
        checker = type_check('"hello"')
        ty = checker.check_expr(StringLiteral(value="hello"))
        self.assertEqual(str(ty), "String")

    def test_bool_type(self):
        checker = type_check("true")
        ty = checker.check_expr(BoolLiteral(value=True))
        self.assertEqual(str(ty), "Bool")

    def test_list_type(self):
        checker = type_check("[1, 2, 3]")
        ty = checker.check_expr(
            ListExpr(
                elements=[IntLiteral(value=1), IntLiteral(value=2), IntLiteral(value=3)]
            )
        )
        self.assertEqual(str(ty), "List[Int]")

    def test_arithmetic_types(self):
        checker = type_check("1 + 2")
        ty = checker.check_expr(
            BinaryOp(op="+", left=IntLiteral(1), right=IntLiteral(2))
        )
        self.assertEqual(str(ty), "Int")

    def test_comparison_type(self):
        checker = type_check("1 < 2")
        ty = checker.check_expr(
            BinaryOp(op="<", left=IntLiteral(1), right=IntLiteral(2))
        )
        self.assertEqual(str(ty), "Bool")

    def test_logical_type(self):
        checker = type_check("true && false")
        ty = checker.check_expr(
            BinaryOp(op="&&", left=BoolLiteral(True), right=BoolLiteral(False))
        )
        self.assertEqual(str(ty), "Bool")

    def test_string_concat_type(self):
        checker = type_check('"a" ++ "b"')
        ty = checker.check_expr(
            BinaryOp(op="++", left=StringLiteral("a"), right=StringLiteral("b"))
        )
        self.assertEqual(str(ty), "String")

    def test_if_type(self):
        checker = type_check("if true then 1 else 2")
        ty = checker.check_expr(
            IfExpr(
                condition=BoolLiteral(True),
                then_branch=IntLiteral(1),
                else_branch=IntLiteral(2),
            )
        )
        self.assertEqual(str(ty), "Int")

    def test_fn_type(self):
        checker = type_check("fn add(a: Int, b: Int) -> Int { a + b }")
        ty = checker.env.lookup("add")
        self.assertIn("Int", str(ty))

    def test_type_mismatch(self):
        with self.assertRaises(TypeCheckError):
            type_check("1 + true")

    def test_undefined_identifier(self):
        with self.assertRaises(TypeCheckError):
            type_check("x")

    def test_list_type_mismatch(self):
        with self.assertRaises(TypeCheckError):
            type_check("[1, true]")


# ============================================================
# 求值器测试
# ============================================================


class TestEvaluator(unittest.TestCase):
    """求值器测试"""

    def test_int_literal(self):
        ev = eval_source("42", check_types=False)
        result = ev.env.lookup("42") if False else None
        # 顶层表达式不创建绑定，用另一种方式测试
        ev2 = eval_source("let x = 42", check_types=False)
        self.assertEqual(ev2.env.lookup("x"), 42)

    def test_float_literal(self):
        ev = eval_source("let x = 3.14", check_types=False)
        self.assertAlmostEqual(ev.env.lookup("x"), 3.14)

    def test_string_literal(self):
        ev = eval_source('let x = "hello"', check_types=False)
        self.assertEqual(ev.env.lookup("x"), "hello")

    def test_bool_literal(self):
        ev = eval_source("let x = true", check_types=False)
        self.assertTrue(ev.env.lookup("x"))

    def test_unit_literal(self):
        ev = eval_source("let x = ()", check_types=False)
        from nova.evaluator import UNIT_VALUE

        self.assertEqual(ev.env.lookup("x"), UNIT_VALUE)

    def test_arithmetic_add(self):
        ev = eval_source("let x = 1 + 2", check_types=False)
        self.assertEqual(ev.env.lookup("x"), 3)

    def test_arithmetic_sub(self):
        ev = eval_source("let x = 10 - 3", check_types=False)
        self.assertEqual(ev.env.lookup("x"), 7)

    def test_arithmetic_mul(self):
        ev = eval_source("let x = 4 * 5", check_types=False)
        self.assertEqual(ev.env.lookup("x"), 20)

    def test_arithmetic_div(self):
        ev = eval_source("let x = 10 / 3", check_types=False)
        self.assertEqual(ev.env.lookup("x"), 3)

    def test_arithmetic_mod(self):
        ev = eval_source("let x = 10 % 3", check_types=False)
        self.assertEqual(ev.env.lookup("x"), 1)

    def test_string_concat(self):
        ev = eval_source('let x = "hello" ++ " " ++ "world"', check_types=False)
        self.assertEqual(ev.env.lookup("x"), "hello world")

    def test_comparison_eq(self):
        ev = eval_source("let x = 1 == 1", check_types=False)
        self.assertTrue(ev.env.lookup("x"))

    def test_comparison_neq(self):
        ev = eval_source("let x = 1 != 2", check_types=False)
        self.assertTrue(ev.env.lookup("x"))

    def test_comparison_lt(self):
        ev = eval_source("let x = 1 < 2", check_types=False)
        self.assertTrue(ev.env.lookup("x"))

    def test_comparison_gt(self):
        ev = eval_source("let x = 2 > 1", check_types=False)
        self.assertTrue(ev.env.lookup("x"))

    def test_comparison_lte(self):
        ev = eval_source("let x = 1 <= 1", check_types=False)
        self.assertTrue(ev.env.lookup("x"))

    def test_comparison_gte(self):
        ev = eval_source("let x = 2 >= 2", check_types=False)
        self.assertTrue(ev.env.lookup("x"))

    def test_logical_and(self):
        ev = eval_source("let x = true && true", check_types=False)
        self.assertTrue(ev.env.lookup("x"))

    def test_logical_and_shortcircuit(self):
        ev = eval_source("let x = false && true", check_types=False)
        self.assertFalse(ev.env.lookup("x"))

    def test_logical_or(self):
        ev = eval_source("let x = false || true", check_types=False)
        self.assertTrue(ev.env.lookup("x"))

    def test_logical_or_shortcircuit(self):
        ev = eval_source("let x = true || false", check_types=False)
        self.assertTrue(ev.env.lookup("x"))

    def test_unary_minus(self):
        ev = eval_source("let x = -42", check_types=False)
        self.assertEqual(ev.env.lookup("x"), -42)

    def test_unary_not(self):
        ev = eval_source("let x = !true", check_types=False)
        self.assertFalse(ev.env.lookup("x"))

    def test_if_then_else(self):
        ev = eval_source("let x = if true then 1 else 2", check_types=False)
        self.assertEqual(ev.env.lookup("x"), 1)

    def test_if_then_false(self):
        ev = eval_source("let x = if false then 1 else 2", check_types=False)
        self.assertEqual(ev.env.lookup("x"), 2)

    def test_let_binding(self):
        ev = eval_source("let x = 10", check_types=False)
        self.assertEqual(ev.env.lookup("x"), 10)

    def test_mut_binding(self):
        ev = eval_source(
            """
            mut x = 10
        """,
            check_types=False,
        )
        # 测试 mut 绑定创建
        self.assertEqual(ev.env.lookup("x"), 10)

    def test_fn_call(self):
        ev = eval_source(
            """
            fn double(x: Int) -> Int { x * 2 }
            let result = double(5)
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("result"), 10)

    def test_fn_recursive(self):
        ev = eval_source(
            """
            fn fib(n: Int) -> Int {
              if n <= 1 then n
              else fib(n - 1) + fib(n - 2)
            }
            let result = fib(10)
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("result"), 55)

    def test_lambda(self):
        ev = eval_source("let add = |a, b| a + b", check_types=False)
        fn_val = ev.env.lookup("add")
        from nova.evaluator import NovaClosure

        self.assertIsInstance(fn_val, NovaClosure)

    def test_lambda_call(self):
        ev = eval_source(
            """
            let add = |a: Int, b: Int| -> Int { a + b }
            let result = add(3, 4)
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("result"), 7)

    def test_list(self):
        ev = eval_source("let xs = [1, 2, 3]", check_types=False)
        self.assertEqual(ev.env.lookup("xs"), [1, 2, 3])

    def test_tuple(self):
        ev = eval_source("let p = (1, 2)", check_types=False)
        self.assertEqual(ev.env.lookup("p"), (1, 2))

    def test_closure(self):
        ev = eval_source(
            """
            fn make_adder(n: Int) -> (Int) -> Int {
              |x: Int| -> Int { x + n }
            }
            let add5 = make_adder(5)
            let result = add5(10)
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("result"), 15)

    def test_match_int(self):
        ev = eval_source(
            """
            let x = match 1 {
                1 -> "one"
                2 -> "two"
                _ -> "other"
            }
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("x"), "one")

    def test_match_bool(self):
        ev = eval_source(
            """
            let x = match true {
                true  -> "yes"
                false -> "no"
            }
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("x"), "yes")

    def test_match_wildcard(self):
        ev = eval_source(
            """
            let x = match 42 {
                _ -> "anything"
            }
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("x"), "anything")

    def test_match_binding(self):
        ev = eval_source(
            """
            let x = match 42 {
                n -> n
            }
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("x"), 42)

    def test_match_tuple(self):
        ev = eval_source(
            """
            let x = match (1, 2) {
                (a, b) -> a + b
            }
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("x"), 3)


# ============================================================
# ADT 测试
# ============================================================


class TestADT(unittest.TestCase):
    """代数数据类型测试"""

    def test_adt_definition(self):
        ev = eval_source(
            """
            type Color { Red | Green | Blue }
            let c = Red
        """,
            check_types=False,
        )
        from nova.evaluator import NovaADTValue

        self.assertIsInstance(ev.env.lookup("c"), NovaADTValue)
        self.assertEqual(ev.env.lookup("c").variant_name, "Red")

    def test_adt_with_fields(self):
        ev = eval_source(
            """
            type Shape { Circle(r: Float) | Rect(w: Float, h: Float) }
            let c = Circle(5.0)
        """,
            check_types=False,
        )
        from nova.evaluator import NovaADTValue

        c = ev.env.lookup("c")
        self.assertEqual(c.variant_name, "Circle")
        self.assertEqual(len(c.fields), 1)
        self.assertAlmostEqual(c.fields[0], 5.0)

    def test_adt_match(self):
        ev = eval_source(
            """
            type Shape { Circle(r: Float) | Rect(w: Float, h: Float) }
            fn area(s: Shape) -> Float {
              match s {
                Circle(r)  -> 3.14159 * r * r
                Rect(w, h) -> w * h
              }
            }
            let c = Circle(5.0)
            let result = area(c)
        """,
            check_types=False,
        )
        result = ev.env.lookup("result")
        self.assertAlmostEqual(result, 78.53975)

    def test_option_some(self):
        ev = eval_source(
            """
            let x = Some(42)
        """,
            check_types=False,
        )
        from nova.evaluator import NovaADTValue

        x = ev.env.lookup("x")
        self.assertEqual(x.variant_name, "Some")
        self.assertEqual(x.fields[0], 42)

    def test_option_match(self):
        ev = eval_source(
            """
            let x = match Some(42) {
                Some(v) -> v
                None    -> 0
            }
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("x"), 42)

    def test_option_none_match(self):
        ev = eval_source(
            """
            let x = match None {
                Some(v) -> v
                None    -> 0
            }
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("x"), 0)


# ============================================================
# 管道操作测试
# ============================================================


class TestPipe(unittest.TestCase):
    """管道操作测试"""

    def test_simple_pipe(self):
        ev = eval_source(
            """
            fn double(x: Int) -> Int { x * 2 }
            let result = 5 |> double
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("result"), 10)

    def test_chained_pipe(self):
        ev = eval_source(
            """
            let result = [1, 2, 3, 4, 5]
                |> filter(|x| x > 2)
                |> map(|x| x * x)
                |> sum
        """,
            check_types=False,
        )
        # filter > 2: [3,4,5], map * x: [9,16,25], sum: 50
        self.assertEqual(ev.env.lookup("result"), 50)

    def test_pipe_with_lambda(self):
        ev = eval_source(
            """
            let result = 10 |> (|x| x + 5)
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("result"), 15)


# ============================================================
# 内置函数测试
# ============================================================


class TestBuiltins(unittest.TestCase):
    """内置函数测试"""

    def test_print(self):
        ev = eval_source('fn main() -> Unit { print("Hello") }', check_types=False)
        self.assertEqual(ev.get_output(), ["Hello"])

    def test_int_to_str(self):
        ev = eval_source(
            "fn main() -> Unit { print(int_to_str(42)) }", check_types=False
        )
        self.assertEqual(ev.get_output(), ["42"])

    def test_float_to_str(self):
        ev = eval_source(
            "fn main() -> Unit { print(float_to_str(3.14)) }", check_types=False
        )
        self.assertEqual(ev.get_output(), ["3.14"])

    def test_str_len(self):
        ev = eval_source('let n = str_len("hello")', check_types=False)
        self.assertEqual(ev.env.lookup("n"), 5)

    def test_list_length(self):
        ev = eval_source("let n = list_length([1, 2, 3])", check_types=False)
        self.assertEqual(ev.env.lookup("n"), 3)

    def test_filter(self):
        ev = eval_source("let xs = filter(|x| x > 2, [1, 2, 3, 4])", check_types=False)
        self.assertEqual(ev.env.lookup("xs"), [3, 4])

    def test_map(self):
        ev = eval_source("let xs = map(|x| x * 2, [1, 2, 3])", check_types=False)
        self.assertEqual(ev.env.lookup("xs"), [2, 4, 6])

    def test_sum(self):
        ev = eval_source("let s = sum([1, 2, 3, 4, 5])", check_types=False)
        self.assertEqual(ev.env.lookup("s"), 15)

    def test_head_some(self):
        ev = eval_source("let x = head([1, 2, 3])", check_types=False)
        from nova.evaluator import NovaADTValue

        x = ev.env.lookup("x")
        self.assertEqual(x.variant_name, "Some")
        self.assertEqual(x.fields[0], 1)

    def test_head_none(self):
        ev = eval_source("let x = head([])", check_types=False)
        from nova.evaluator import NovaADTValue

        x = ev.env.lookup("x")
        self.assertEqual(x.variant_name, "None")

    def test_tail_some(self):
        ev = eval_source("let x = tail([1, 2, 3])", check_types=False)
        from nova.evaluator import NovaADTValue

        x = ev.env.lookup("x")
        self.assertEqual(x.variant_name, "Some")
        self.assertEqual(x.fields[0], [2, 3])

    def test_tail_none(self):
        ev = eval_source("let x = tail([])", check_types=False)
        from nova.evaluator import NovaADTValue

        x = ev.env.lookup("x")
        self.assertEqual(x.variant_name, "None")

    def test_str_to_int_success(self):
        ev = eval_source('let x = str_to_int("42")', check_types=False)
        from nova.evaluator import NovaADTValue

        x = ev.env.lookup("x")
        self.assertEqual(x.variant_name, "Some")
        self.assertEqual(x.fields[0], 42)

    def test_str_to_int_fail(self):
        ev = eval_source('let x = str_to_int("abc")', check_types=False)
        from nova.evaluator import NovaADTValue

        x = ev.env.lookup("x")
        self.assertEqual(x.variant_name, "None")


# ============================================================
# 综合集成测试
# ============================================================


class TestIntegration(unittest.TestCase):
    """集成测试 - 完整程序测试"""

    def test_hello_world(self):
        ev = eval_source("""
            fn main() -> Unit {
              print("Hello, Nova!")
            }
        """)
        self.assertEqual(ev.get_output(), ["Hello, Nova!"])

    def test_fibonacci(self):
        ev = eval_source("""
            fn fib(n: Int) -> Int {
              if n <= 1 then n
              else fib(n - 1) + fib(n - 2)
            }
            fn main() -> Unit {
              print(int_to_str(fib(10)))
            }
        """)
        self.assertEqual(ev.get_output(), ["55"])

    def test_factorial(self):
        ev = eval_source("""
            fn factorial(n: Int) -> Int {
              if n <= 1 then 1
              else n * factorial(n - 1)
            }
            fn main() -> Unit {
              print(int_to_str(factorial(5)))
            }
        """)
        self.assertEqual(ev.get_output(), ["120"])

    def test_higher_order(self):
        ev = eval_source(
            """
            fn apply(f, x) -> Int { f(x) }
            fn main() -> Unit {
              let result = apply(|n| n * n, 5)
              print(int_to_str(result))
            }
        """,
            check_types=False,
        )
        self.assertEqual(ev.get_output(), ["25"])

    def test_nested_let(self):
        ev = eval_source(
            """
            let x = 10
            let y = {
              let a = 20
              let b = 30
              a + b
            }
            let z = x + y
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("z"), 60)

    def test_scoping(self):
        ev = eval_source(
            """
            let x = 1
            let y = {
              let x = 2
              x
            }
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("y"), 2)
        self.assertEqual(ev.env.lookup("x"), 1)

    def test_pattern_match_full_program(self):
        ev = eval_source("""
            type Shape {
              Circle(r: Float)
              Rect(w: Float, h: Float)
            }
            fn describe(s: Shape) -> String {
              match s {
                Circle(r)    -> "Circle"
                Rect(w, h)   -> "Rectangle"
              }
            }
            fn main() -> Unit {
              let c = Circle(5.0)
              print(describe(c))
            }
        """)
        self.assertEqual(ev.get_output(), ["Circle"])

    def test_pipe_full_program(self):
        ev = eval_source("""
            fn main() -> Unit {
              let result = [1, 2, 3, 4, 5]
                |> filter(|x| x > 2)
                |> map(|x| x * x)
                |> sum
              print(int_to_str(result))
            }
        """)
        # filter > 2: [3,4,5], map * x: [9,16,25], sum: 50
        self.assertEqual(ev.get_output(), ["50"])


# ============================================================
# 错误处理测试
# ============================================================


class TestErrors(unittest.TestCase):
    """错误处理测试"""

    def test_lexer_error(self):
        with self.assertRaises(LexerError):
            tokenize("@")

    def test_parse_error(self):
        with self.assertRaises(ParseError):
            parse("let = 42")

    def test_type_error_add_int_bool(self):
        with self.assertRaises(TypeCheckError):
            type_check("1 + true")

    def test_type_error_if_cond(self):
        with self.assertRaises(TypeCheckError):
            type_check("if 42 then 1 else 2")

    def test_type_error_undefined(self):
        with self.assertRaises(TypeCheckError):
            type_check("x + 1")

    def test_runtime_error_division_by_zero(self):
        with self.assertRaises(RuntimeError_):
            eval_source("let x = 10 / 0", check_types=False)

    def test_match_exhaustiveness_error(self):
        """没有匹配分支应该报运行时错误"""
        with self.assertRaises(RuntimeError_):
            eval_source(
                """
                let x = match 3 {
                    1 -> "one"
                    2 -> "two"
                }
            """,
                check_types=False,
            )


if __name__ == "__main__":
    unittest.main()


# ============================================================
# 循环测试
# ============================================================


class TestLoops(unittest.TestCase):
    """循环语法测试"""

    def test_for_loop_list(self):
        """for x in [1, 2, 3] { x * 2 } == [2, 4, 6]"""
        ev = eval_source(
            """
            let result = for x in [1, 2, 3] { x * 2 }
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("result"), [2, 4, 6])

    def test_for_range(self):
        """for i <- 0..5 { i } == [0, 1, 2, 3, 4, 5]"""
        ev = eval_source(
            """
            let result = for i <- 0..5 { i }
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("result"), [0, 1, 2, 3, 4, 5])

    def test_for_range_step(self):
        """for i <- 0..10 step 2 { i } == [0, 2, 4, 6, 8, 10]"""
        ev = eval_source(
            """
            let result = for i <- 0..10 step 2 { i }
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("result"), [0, 2, 4, 6, 8, 10])

    def test_while_loop(self):
        """while 计数"""
        ev = eval_source(
            """
            mut sum = 0
            mut i = 1
            while i <= 5 {
              sum = sum + i
              i = i + 1
            }
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("sum"), 15)
        self.assertEqual(ev.env.lookup("i"), 6)

    def test_break_in_for(self):
        """break 跳出循环"""
        ev = eval_source(
            """
            let result = for x in [1, 2, 3, 4, 5] {
              if x == 3 then break
              x
            }
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("result"), [1, 2])

    def test_continue_in_for(self):
        """continue 跳过迭代"""
        ev = eval_source(
            """
            let result = for x in [1, 2, 3, 4, 5] {
              if x == 3 then continue
              x
            }
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("result"), [1, 2, 4, 5])

    def test_for_loop_type_check(self):
        """for 循环类型检查"""
        checker = type_check("""
            let result = for x in [1, 2, 3] { x * 2 }
        """)
        ty = checker.env.lookup("result")
        self.assertIn("List", str(ty))


# ============================================================
# 文件 I/O 测试
# ============================================================


class TestFileIO(unittest.TestCase):
    """文件 I/O 测试"""

    def setUp(self):
        import tempfile

        self.tmpdir = tempfile.mkdtemp()

    def test_write_and_read_file(self):
        """写入再读取文件"""
        import os

        path = os.path.join(self.tmpdir, "test_write.txt")
        ev = eval_source(
            f"""
            fn main() -> Unit {{
              write_file("{path}", "Hello Nova!")
            }}
        """,
            check_types=False,
        )
        ev2 = eval_source(
            f"""
            fn main() -> Unit {{
              let content = read_file("{path}")
              print(content)
            }}
        """,
            check_types=False,
        )
        self.assertEqual(ev2.get_output(), ["Hello Nova!"])

    def test_file_exists(self):
        """检查文件存在性"""
        import os

        path = os.path.join(self.tmpdir, "exists_test.txt")
        # 先写入文件
        ev = eval_source(
            f"""
            fn main() -> Unit {{ write_file("{path}", "test") }}
        """,
            check_types=False,
        )
        # 检查存在
        ev2 = eval_source(
            f"""
            let exists = file_exists("{path}")
        """,
            check_types=False,
        )
        self.assertTrue(ev2.env.lookup("exists"))

    def test_read_file_not_found(self):
        """读取不存在的文件"""
        import os

        path = os.path.join(self.tmpdir, "nonexistent.txt")
        with self.assertRaises(RuntimeError_):
            eval_source(
                f"""
                fn main() -> Unit {{
                    read_file("{path}")
                }}
            """,
                check_types=False,
            )


# ============================================================
# JSON 测试
# ============================================================


class TestJSON(unittest.TestCase):
    """JSON 解析/序列化测试"""

    def test_json_parse(self):
        """解析 JSON 字符串"""
        ev = eval_source(
            'let result = json_parse("{\\"key\\": \\"value\\"}")', check_types=False
        )
        parsed = ev.env.lookup("result")
        self.assertIsInstance(parsed, dict)
        self.assertEqual(parsed["key"], "value")

    def test_json_parse_number(self):
        """解析 JSON 数字"""
        ev = eval_source('let result = json_parse("42")', check_types=False)
        self.assertEqual(ev.env.lookup("result"), 42)

    def test_json_parse_array(self):
        """解析 JSON 数组"""
        ev = eval_source('let result = json_parse("[1, 2, 3]")', check_types=False)
        self.assertEqual(ev.env.lookup("result"), [1, 2, 3])

    def test_json_stringify(self):
        """序列化为 JSON 字符串"""
        ev = eval_source("let result = json_stringify(42)", check_types=False)
        self.assertEqual(ev.env.lookup("result"), "42")

    def test_json_stringify_map(self):
        """序列化字典"""
        ev = eval_source(
            """
            fn main() -> Unit {
              let m = json_parse("{\\"key\\": \\"value\\"}")
              let result = json_stringify(m)
              print(result)
            }
        """,
            check_types=False,
        )
        import json

        self.assertEqual(json.loads(ev.get_output()[0]), {"key": "value"})


# ============================================================
# 数学库测试
# ============================================================


class TestMath(unittest.TestCase):
    """数学基础库测试"""

    def test_math_sqrt(self):
        ev = eval_source("let r = sqrt(16.0)", check_types=False)
        self.assertAlmostEqual(ev.env.lookup("r"), 4.0)

    def test_math_sin(self):
        ev = eval_source("let r = sin(0.0)", check_types=False)
        self.assertAlmostEqual(ev.env.lookup("r"), 0.0, places=10)

    def test_math_cos(self):
        ev = eval_source("let r = cos(0.0)", check_types=False)
        self.assertAlmostEqual(ev.env.lookup("r"), 1.0, places=10)

    def test_math_pow(self):
        ev = eval_source("let r = pow(2.0, 10.0)", check_types=False)
        self.assertAlmostEqual(ev.env.lookup("r"), 1024.0)

    def test_math_floor(self):
        ev = eval_source("let r = floor(3.7)", check_types=False)
        self.assertEqual(ev.env.lookup("r"), 3.0)

    def test_math_ceil(self):
        ev = eval_source("let r = ceil(3.2)", check_types=False)
        self.assertEqual(ev.env.lookup("r"), 4.0)

    def test_math_round(self):
        ev = eval_source("let r = round(3.5)", check_types=False)
        self.assertEqual(ev.env.lookup("r"), 4.0)

    def test_math_min(self):
        ev = eval_source("let r = min(3.0, 5.0)", check_types=False)
        self.assertEqual(ev.env.lookup("r"), 3.0)

    def test_math_max(self):
        ev = eval_source("let r = max(3.0, 5.0)", check_types=False)
        self.assertEqual(ev.env.lookup("r"), 5.0)

    def test_math_pi(self):
        ev = eval_source("let r = pi()", check_types=False)
        self.assertAlmostEqual(ev.env.lookup("r"), 3.141592653589793)

    def test_math_abs(self):
        ev = eval_source("let r = abs(-5.0)", check_types=False)
        self.assertEqual(ev.env.lookup("r"), 5.0)

    def test_math_abs_int(self):
        """abs 支持 Int 输入"""
        ev = eval_source("let r = abs(-5)", check_types=False)
        self.assertEqual(ev.env.lookup("r"), 5.0)

    def test_math_log(self):
        ev = eval_source("let r = log(1.0)", check_types=False)
        self.assertAlmostEqual(ev.env.lookup("r"), 0.0, places=10)

    def test_math_log10(self):
        ev = eval_source("let r = log10(100.0)", check_types=False)
        self.assertAlmostEqual(ev.env.lookup("r"), 2.0)

    def test_math_exp(self):
        ev = eval_source("let r = exp(0.0)", check_types=False)
        self.assertAlmostEqual(ev.env.lookup("r"), 1.0, places=10)


# ============================================================
# 列表推导式测试
# ============================================================


class TestListComprehension(unittest.TestCase):
    """列表推导式测试"""

    def test_list_comprehension_basic(self):
        """[x * 2 for x in [1, 2, 3]]"""
        ev = eval_source(
            """
            let result = [x * 2 for x in [1, 2, 3]]
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("result"), [2, 4, 6])

    def test_list_comprehension_range(self):
        """[x * x for x <- 0..5]"""
        ev = eval_source(
            """
            let result = [x * x for x <- 0..5]
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("result"), [0, 1, 4, 9, 16, 25])

    def test_list_comprehension_filter(self):
        """[x for x <- 1..10 if x % 2 == 0]"""
        ev = eval_source(
            """
            let result = [x for x <- 1..10 if x % 2 == 0]
        """,
            check_types=False,
        )
        self.assertEqual(ev.env.lookup("result"), [2, 4, 6, 8, 10])

    def test_list_comprehension_type_check(self):
        """列表推导式类型检查"""
        checker = type_check("""
            let result = [x * 2 for x in [1, 2, 3]]
        """)
        ty = checker.env.lookup("result")
        self.assertIn("List", str(ty))


# ============================================================
# 错误格式测试
# ============================================================


class TestErrorFormatting(unittest.TestCase):
    """错误格式测试"""

    def test_error_with_source_context(self):
        """错误信息包含源码上下文"""
        from nova.errors import NovaError

        err = NovaError("测试错误", line=2, column=5)
        err.source_code = "line1\nline2 error here\nline3"
        formatted = str(err)
        # 应包含源码行
        self.assertIn("line2", formatted)
        self.assertIn("^", formatted)

    def test_error_with_source_context_first_line(self):
        """错误在第一行时也能正确显示"""
        from nova.errors import NovaError

        err = NovaError("第一行错误", line=1, column=3)
        err.source_code = "first line\nsecond line"
        formatted = str(err)
        self.assertIn("first line", formatted)
        self.assertIn("^", formatted)

    def test_error_with_source_context_last_line(self):
        """错误在最后一行时也能正确显示"""
        from nova.errors import NovaError

        err = NovaError("最后一行错误", line=3, column=1)
        err.source_code = "line1\nline2\nline3 error"
        formatted = str(err)
        self.assertIn("line3", formatted)
        self.assertIn("^", formatted)

    def test_error_without_source_fallback(self):
        """没有源码时使用传统格式"""
        from nova.errors import NovaError

        err = NovaError("简单错误", line=5, column=10)
        formatted = str(err)
        self.assertIn("[行 5, 列 10]", formatted)
        self.assertIn("简单错误", formatted)

    def test_error_no_line_info(self):
        """没有行列号时只显示消息"""
        from nova.errors import NovaError

        err = NovaError("无位置错误")
        formatted = str(err)
        self.assertEqual(formatted, "无位置错误")

    def test_error_highlight_span(self):
        """使用 highlight_span 标记范围"""
        from nova.errors import NovaError

        err = NovaError("范围错误", line=2, column=5)
        err.source_code = "line1\nabcDEFGhij\nline3"
        err.highlight_span = (5, 10)
        formatted = str(err)
        # 10 - 5 = 5 个 ^
        self.assertIn("^^^^^", formatted)

    def test_lexer_error_with_source(self):
        """词法分析错误自动附带源码"""
        from nova.errors import LexerError

        err = LexerError("非法字符", 1, 1, source="let x = @")
        formatted = str(err)
        self.assertIn("let x = @", formatted)
        self.assertIn("^", formatted)

    def test_parse_error_with_source(self):
        """语法分析错误附带源码"""
        from nova.errors import ParseError

        err = ParseError("意外 token", 1, 5, source="let = 42")
        formatted = str(err)
        self.assertIn("let = 42", formatted)

    def test_type_check_error_with_source(self):
        """类型检查错误附带源码"""
        from nova.errors import TypeCheckError

        err = TypeCheckError("类型不匹配", 1, 3, source="let x: Int = true")
        formatted = str(err)
        self.assertIn("let x: Int = true", formatted)

    def test_runtime_error_with_source(self):
        """运行时错误附带源码"""
        from nova.errors import RuntimeError_

        err = RuntimeError_("除零错误", 1, 10, source="let x = 10 / 0")
        formatted = str(err)
        self.assertIn("10 / 0", formatted)

    def test_error_context_shows_previous_line(self):
        """上下文显示前一行"""
        from nova.errors import NovaError

        err = NovaError("错误", line=2, column=1)
        err.source_code = "prev\nerror\nnext"
        formatted = str(err)
        self.assertIn("prev", formatted)

    def test_error_context_shows_next_line(self):
        """上下文显示后一行"""
        from nova.errors import NovaError

        err = NovaError("错误", line=2, column=1)
        err.source_code = "prev\nerror\nnext"
        formatted = str(err)
        self.assertIn("next", formatted)


# ============================================================
# REPL 功能测试
# ============================================================


class TestREPLFeatures(unittest.TestCase):
    """REPL 功能测试"""

    def test_multiline_detection(self):
        """多行检测"""
        from nova import _is_incomplete

        self.assertTrue(_is_incomplete("fn add(a) {"))
        self.assertFalse(_is_incomplete("42"))
        self.assertTrue(_is_incomplete("if true then {"))
        self.assertTrue(_is_incomplete("let x = ["))
        self.assertTrue(_is_incomplete("let x = ("))
        self.assertFalse(_is_incomplete("let x = 42"))
        self.assertFalse(_is_incomplete("fn add(a: Int) -> Int { a + b }"))

    def test_multiline_with_braces(self):
        """花括号闭合后完成"""
        from nova import _is_incomplete

        self.assertTrue(_is_incomplete("{"))
        self.assertFalse(_is_incomplete("{}"))
        self.assertTrue(_is_incomplete("{{"))
        self.assertFalse(_is_incomplete("{{}}"))

    def test_multiline_with_parens(self):
        """括号闭合后完成"""
        from nova import _is_incomplete

        self.assertTrue(_is_incomplete("("))
        self.assertFalse(_is_incomplete("()"))
        self.assertTrue(_is_incomplete("(1 + "))
        self.assertFalse(_is_incomplete("(1 + 2)"))

    def test_multiline_with_brackets(self):
        """方括号闭合后完成"""
        from nova import _is_incomplete

        self.assertTrue(_is_incomplete("["))
        self.assertFalse(_is_incomplete("[]"))
        self.assertTrue(_is_incomplete("[1, 2, "))
        self.assertFalse(_is_incomplete("[1, 2, 3]"))

    def test_multiline_string_ignored(self):
        """字符串内的括号不影响检测"""
        from nova import _is_incomplete

        self.assertFalse(_is_incomplete('"{"'))
        self.assertFalse(_is_incomplete('"(()"'))
        self.assertFalse(_is_incomplete('let x = "("'))
        # 但转义引号内内容不影响
        self.assertFalse(_is_incomplete('"hello \\"world\\""'))

    def test_count_indent(self):
        """缩进级别计算"""
        from nova import _count_indent

        self.assertEqual(_count_indent("fn add() {"), 1)
        self.assertEqual(_count_indent("fn add() { x + "), 1)
        self.assertEqual(_count_indent("fn add() { x + }"), 0)
        self.assertEqual(_count_indent("{{inner}}"), 0)
        self.assertEqual(_count_indent("{ { }"), 1)

    def test_attach_source(self):
        """_attach_source 为错误附加源码"""
        from nova import _attach_source
        from nova.errors import NovaError

        err = NovaError("test", line=1, column=1)
        self.assertIsNone(err.source_code)
        _attach_source(err, "let x = 42")
        self.assertEqual(err.source_code, "let x = 42")

    def test_attach_source_idempotent(self):
        """_attach_source 不覆盖已有源码"""
        from nova import _attach_source
        from nova.errors import NovaError

        err = NovaError("test", line=1, column=1)
        err.source_code = "original"
        _attach_source(err, "new")
        self.assertEqual(err.source_code, "original")

    def test_error_backwards_compatibility(self):
        """NovaError 的 source_code 和 highlight_span 是可选的"""
        from nova.errors import (
            NovaError,
            LexerError,
            ParseError,
            TypeCheckError,
            RuntimeError_,
        )

        # 旧式创建（无 source）仍然工作
        err1 = NovaError("msg", 1, 1)
        self.assertIsNone(err1.source_code)
        self.assertIsNone(err1.highlight_span)

        err2 = LexerError("msg", 1, 1)
        self.assertIsNone(err2.source_code)

        err3 = ParseError("msg", 1, 1)
        self.assertIsNone(err3.source_code)

        err4 = TypeCheckError("msg", 1, 1)
        self.assertIsNone(err4.source_code)

        err5 = RuntimeError_("msg", 1, 1)
        self.assertIsNone(err5.source_code)


# ============================================================
# 字节码虚拟机测试
# ============================================================


class TestBytecodeVM(unittest.TestCase):
    """字节码虚拟机测试"""

    def _vm_run(self, source):
        """用 VM 模式运行源码"""
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        TypeChecker().check_program(ast)
        from nova.compiler import BytecodeCompiler
        from nova.vm import NovaVM

        compiler = BytecodeCompiler()
        bytecode = compiler.compile(ast)
        vm = NovaVM(bytecode)
        vm.run()
        return vm

    def test_vm_int_literal(self):
        vm = self._vm_run("let x = 42")
        self.assertEqual(vm.get_global("x"), 42)

    def test_vm_arithmetic(self):
        vm = self._vm_run("let x = 2 + 3 * 4")
        self.assertEqual(vm.get_global("x"), 14)

    def test_vm_string(self):
        vm = self._vm_run('let x = "hello" ++ " world"')
        self.assertEqual(vm.get_global("x"), "hello world")

    def test_vm_if_else(self):
        vm = self._vm_run("let x = if true then 1 else 2")
        self.assertEqual(vm.get_global("x"), 1)

    def test_vm_fn_call(self):
        vm = self._vm_run("""
            fn add(a: Int, b: Int) -> Int { a + b }
            let x = add(3, 4)
        """)
        self.assertEqual(vm.get_global("x"), 7)

    def test_vm_recursive(self):
        vm = self._vm_run("""
            fn fib(n: Int) -> Int {
                if n <= 1 then n
                else fib(n-1) + fib(n-2)
            }
            let x = fib(10)
        """)
        self.assertEqual(vm.get_global("x"), 55)

    def test_vm_closure(self):
        vm = self._vm_run("""
            fn make_adder(n: Int) -> (Int) -> Int {
                |x: Int| -> Int { x + n }
            }
            let add5 = make_adder(5)
            let x = add5(10)
        """)
        self.assertEqual(vm.get_global("x"), 15)

    def test_vm_list(self):
        vm = self._vm_run("let xs = [1, 2, 3]")
        self.assertEqual(vm.get_global("xs"), [1, 2, 3])

    def test_vm_match(self):
        vm = self._vm_run("""
            let x = match 42 {
                1 -> "one"
                n -> "other"
            }
        """)
        self.assertEqual(vm.get_global("x"), "other")

    def test_vm_pipe(self):
        vm = self._vm_run("""
            let result = [1, 2, 3, 4, 5]
                |> filter(|x| x > 2)
                |> map(|x| x * x)
                |> sum
        """)
        self.assertEqual(vm.get_global("result"), 50)

    def test_vm_print(self):
        vm = self._vm_run('fn main() -> Unit { print("Hello VM!") }')
        self.assertEqual(vm.get_output(), ["Hello VM!"])

    def test_vm_hello_world(self):
        vm = self._vm_run("""
            fn main() -> Unit {
                print("Hello, Nova!")
            }
        """)
        self.assertEqual(vm.get_output(), ["Hello, Nova!"])

    def test_vm_for_loop(self):
        vm = self._vm_run("""
            let result = for x in [1, 2, 3] { x * 2 }
        """)
        self.assertEqual(vm.get_global("result"), [2, 4, 6])

    def test_vm_while_loop(self):
        vm = self._vm_run("""
            mut sum = 0
            mut i = 1
            while i <= 5 {
                sum = sum + i
                i = i + 1
            }
        """)
        self.assertEqual(vm.get_global("sum"), 15)

    def test_vm_adt(self):
        vm = self._vm_run("""
            type Shape { Circle(r: Float) | Rect(w: Float, h: Float) }
            fn area(s: Shape) -> Float {
                match s {
                    Circle(r)  -> 3.14159 * r * r
                    Rect(w, h) -> w * h
                }
            }
            let c = Circle(5.0)
            let x = area(c)
        """)
        self.assertAlmostEqual(vm.get_global("x"), 78.53975)

    def test_vm_list_comprehension(self):
        vm = self._vm_run("""
            let result = [x * x for x <- 0..5]
        """)
        self.assertEqual(vm.get_global("result"), [0, 1, 4, 9, 16, 25])

    def test_vm_math(self):
        vm = self._vm_run("let x = sqrt(16.0)")
        self.assertAlmostEqual(vm.get_global("x"), 4.0)

    def test_vm_factorial(self):
        vm = self._vm_run("""
            fn factorial(n: Int) -> Int {
                if n <= 1 then 1
                else n * factorial(n - 1)
            }
            let x = factorial(10)
        """)
        self.assertEqual(vm.get_global("x"), 3628800)

    def test_vm_higher_order(self):
        vm = self._vm_run("""
            fn apply(f, x) -> Int { f(x) }
            let x = apply(|n| n * n, 5)
        """)
        self.assertEqual(vm.get_global("x"), 25)
