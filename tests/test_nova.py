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

import sys
import os
import unittest

from nova.lexer import Lexer, TokenType
from nova.parser import Parser
from nova.type_checker import TypeChecker
from nova.evaluator import Evaluator
from nova.errors import LexerError, ParseError, TypeCheckError, RuntimeError_
from nova.ast_nodes import (
    IntLiteral, FloatLiteral, StringLiteral, BoolLiteral, Identifier,
    BinaryOp, LetBinding, FnDef, IfExpr, MatchExpr, ListExpr, Lambda, FnCall,
    PipeExpr, Block, UnitLiteral,
)
from nova.environment import Environment
from nova._cli import run_source


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
        expected = ["let", "mut", "fn", "if", "then", "else", "match", "type", "import", "export"]
        self.assertEqual(values, expected)

    def test_arithmetic_operators(self):
        tokens = tokenize("+ - * / %")
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        expected = [TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH, TokenType.PERCENT]
        self.assertEqual(types, expected)

    def test_comparison_operators(self):
        tokens = tokenize("== != < > <= >=")
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        expected = [TokenType.EQ, TokenType.NEQ, TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE]
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
            TokenType.LPAREN, TokenType.RPAREN, TokenType.LBRACKET, TokenType.RBRACKET,
            TokenType.LBRACE, TokenType.RBRACE, TokenType.COMMA, TokenType.SEMICOLON,
            TokenType.COLON, TokenType.DOT,
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
        """非法字符不再抛出 LexerError，而是记录到 self.errors 并跳过"""
        lexer = Lexer("@")
        lexer.tokenize()
        self.assertEqual(len(lexer.errors), 1)
        self.assertIn("非法字符 '@'", lexer.errors[0])


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

    def test_pipe_precedence_lower_than_equality(self):
        """a == b |> f 应解析为 (a == b) |> f（相等性优先级高于管道）"""
        ast = parse("a == b |> f")
        decl = ast.declarations[0]
        # 最外层应该是管道表达式
        self.assertIsInstance(decl, PipeExpr)
        # 管道的左操作数应该是相等比较 a == b
        self.assertIsInstance(decl.left, BinaryOp)
        self.assertEqual(decl.left.op, "==")
        self.assertIsInstance(decl.left.left, Identifier)
        self.assertEqual(decl.left.left.name, "a")
        self.assertIsInstance(decl.left.right, Identifier)
        self.assertEqual(decl.left.right.name, "b")
        # 管道的右操作数是 f
        self.assertIsInstance(decl.right, Identifier)
        self.assertEqual(decl.right.name, "f")

    def test_pipe_precedence_lower_than_comparison(self):
        """a < b |> f 应解析为 (a < b) |> f（比较优先级高于管道）"""
        ast = parse("a < b |> f")
        decl = ast.declarations[0]
        # 最外层应该是管道表达式
        self.assertIsInstance(decl, PipeExpr)
        # 管道的左操作数应该是比较 a < b
        self.assertIsInstance(decl.left, BinaryOp)
        self.assertEqual(decl.left.op, "<")
        self.assertIsInstance(decl.left.left, Identifier)
        self.assertEqual(decl.left.left.name, "a")
        self.assertIsInstance(decl.left.right, Identifier)
        self.assertEqual(decl.left.right.name, "b")
        # 管道的右操作数是 f
        self.assertIsInstance(decl.right, Identifier)
        self.assertEqual(decl.right.name, "f")

    def test_pipe_precedence_higher_than_and(self):
        """a && b |> f 应解析为 a && (b |> f)（管道优先级高于逻辑与）"""
        ast = parse("a && b |> f")
        decl = ast.declarations[0]
        # 最外层应该是逻辑与
        self.assertIsInstance(decl, BinaryOp)
        self.assertEqual(decl.op, "&&")
        # 左操作数是 a
        self.assertIsInstance(decl.left, Identifier)
        self.assertEqual(decl.left.name, "a")
        # 右操作数是管道表达式 b |> f
        self.assertIsInstance(decl.right, PipeExpr)
        self.assertIsInstance(decl.right.left, Identifier)
        self.assertEqual(decl.right.left.name, "b")
        self.assertIsInstance(decl.right.right, Identifier)
        self.assertEqual(decl.right.right.name, "f")

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
        ast = parse('export myFunc')
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
        ty = checker.check_expr(ListExpr(elements=[
            IntLiteral(value=1), IntLiteral(value=2), IntLiteral(value=3)
        ]))
        self.assertEqual(str(ty), "List[Int]")

    def test_arithmetic_types(self):
        checker = type_check("1 + 2")
        ty = checker.check_expr(BinaryOp(op="+", left=IntLiteral(1), right=IntLiteral(2)))
        self.assertEqual(str(ty), "Int")

    def test_comparison_type(self):
        checker = type_check("1 < 2")
        ty = checker.check_expr(BinaryOp(op="<", left=IntLiteral(1), right=IntLiteral(2)))
        self.assertEqual(str(ty), "Bool")

    def test_logical_type(self):
        checker = type_check("true && false")
        ty = checker.check_expr(BinaryOp(op="&&", left=BoolLiteral(True), right=BoolLiteral(False)))
        self.assertEqual(str(ty), "Bool")

    def test_string_concat_type(self):
        checker = type_check('"a" ++ "b"')
        ty = checker.check_expr(BinaryOp(op="++", left=StringLiteral("a"), right=StringLiteral("b")))
        self.assertEqual(str(ty), "String")

    def test_if_type(self):
        checker = type_check("if true then 1 else 2")
        ty = checker.check_expr(IfExpr(
            condition=BoolLiteral(True),
            then_branch=IntLiteral(1),
            else_branch=IntLiteral(2)
        ))
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

    # --- 算术运行时错误测试 ---

    def test_arithmetic_div_zero_int(self):
        """整数除法除零应抛出 RuntimeError_"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("let x = 10 / 0", check_types=False)
        self.assertIn("除零错误", str(ctx.exception))

    def test_arithmetic_div_zero_float(self):
        """浮点除法除零应抛出 RuntimeError_"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("let x = 10.0 / 0.0", check_types=False)
        self.assertIn("除零错误", str(ctx.exception))

    def test_arithmetic_mod_zero_int(self):
        """整数取模除零应抛出 RuntimeError_"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("let x = 10 % 0", check_types=False)
        self.assertIn("除零错误", str(ctx.exception))

    def test_arithmetic_mod_zero_float(self):
        """浮点取模除零应抛出 RuntimeError_"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("let x = 10.0 % 0.0", check_types=False)
        self.assertIn("除零错误", str(ctx.exception))

    def test_arithmetic_add_type_mismatch(self):
        """数字与字符串相加应抛出 RuntimeError_"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source('let x = 1 + "hello"', check_types=False)
        self.assertIn("必须是数字类型", str(ctx.exception))

    def test_arithmetic_sub_type_mismatch(self):
        """字符串与数字相减应抛出 RuntimeError_"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source('let x = "hello" - 1', check_types=False)
        self.assertIn("必须是数字类型", str(ctx.exception))

    def test_arithmetic_mul_type_mismatch(self):
        """字符串与数字相乘应抛出 RuntimeError_"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source('let x = "hello" * 2', check_types=False)
        self.assertIn("必须是数字类型", str(ctx.exception))

    def test_arithmetic_div_type_mismatch(self):
        """字符串与数字相除应抛出 RuntimeError_"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source('let x = "hello" / 2', check_types=False)
        self.assertIn("必须是数字类型", str(ctx.exception))

    def test_arithmetic_mod_type_mismatch(self):
        """字符串与数字取模应抛出 RuntimeError_"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source('let x = "hello" % 2', check_types=False)
        self.assertIn("必须是数字类型", str(ctx.exception))

    def test_unary_minus_type_mismatch(self):
        """对字符串取负应抛出 RuntimeError_"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source('let x = -"hello"', check_types=False)
        self.assertIn("必须是数字类型", str(ctx.exception))

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
        ev = eval_source("""
            mut x = 10
        """, check_types=False)
        # 测试 mut 绑定创建
        self.assertEqual(ev.env.lookup("x"), 10)

    def test_fn_call(self):
        ev = eval_source("""
            fn double(x: Int) -> Int { x * 2 }
            let result = double(5)
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), 10)

    def test_fn_recursive(self):
        ev = eval_source("""
            fn fib(n: Int) -> Int {
              if n <= 1 then n
              else fib(n - 1) + fib(n - 2)
            }
            let result = fib(10)
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), 55)

    def test_lambda(self):
        ev = eval_source("let add = |a, b| a + b", check_types=False)
        fn_val = ev.env.lookup("add")
        from nova.evaluator import NovaClosure
        self.assertIsInstance(fn_val, NovaClosure)

    def test_lambda_call(self):
        ev = eval_source("""
            let add = |a: Int, b: Int| -> Int { a + b }
            let result = add(3, 4)
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), 7)

    def test_list(self):
        ev = eval_source("let xs = [1, 2, 3]", check_types=False)
        self.assertEqual(ev.env.lookup("xs"), [1, 2, 3])

    def test_tuple(self):
        ev = eval_source("let p = (1, 2)", check_types=False)
        self.assertEqual(ev.env.lookup("p"), (1, 2))

    def test_closure(self):
        ev = eval_source("""
            fn make_adder(n: Int) -> (Int) -> Int {
              |x: Int| -> Int { x + n }
            }
            let add5 = make_adder(5)
            let result = add5(10)
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), 15)

    def test_partial_application_two_args(self):
        """双参数函数部分应用：f(3) 返回闭包，再调用得结果"""
        ev = eval_source("""
            fn add(x: Int, y: Int) -> Int { x + y }
            let add3 = add(3)
            let result = add3(7)
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), 10)

    def test_partial_application_three_args_chain(self):
        """三参数函数链式部分应用：f(1)(2)(3)"""
        ev = eval_source("""
            fn sum3(a: Int, b: Int, c: Int) -> Int { a + b + c }
            let sum1 = sum3(1)
            let sum12 = sum1(2)
            let result = sum12(3)
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), 6)

    def test_partial_application_lambda(self):
        """lambda 部分应用"""
        ev = eval_source("""
            let f = |x: Int, y: Int| -> Int { x * y }
            let f4 = f(4)
            let result = f4(5)
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), 20)

    def test_partial_application_with_closure_env(self):
        """部分应用应正确捕获闭包环境中的变量"""
        ev = eval_source("""
            fn make_multiplier(factor: Int) -> (Int, Int) -> Int {
              |x: Int, y: Int| -> Int { x * y * factor }
            }
            let mul_by_3 = make_multiplier(3)
            let mul_by_3_then_5 = mul_by_3(5)
            let result = mul_by_3_then_5(2)
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), 30)

    def test_match_int(self):
        ev = eval_source("""
            let x = match 1 {
                1 -> "one"
                2 -> "two"
                _ -> "other"
            }
        """, check_types=False)
        self.assertEqual(ev.env.lookup("x"), "one")

    def test_match_bool(self):
        ev = eval_source("""
            let x = match true {
                true  -> "yes"
                false -> "no"
            }
        """, check_types=False)
        self.assertEqual(ev.env.lookup("x"), "yes")

    def test_match_wildcard(self):
        ev = eval_source("""
            let x = match 42 {
                _ -> "anything"
            }
        """, check_types=False)
        self.assertEqual(ev.env.lookup("x"), "anything")

    def test_match_binding(self):
        ev = eval_source("""
            let x = match 42 {
                n -> n
            }
        """, check_types=False)
        self.assertEqual(ev.env.lookup("x"), 42)

    def test_match_tuple(self):
        ev = eval_source("""
            let x = match (1, 2) {
                (a, b) -> a + b
            }
        """, check_types=False)
        self.assertEqual(ev.env.lookup("x"), 3)


# ============================================================
# ADT 测试
# ============================================================

class TestADT(unittest.TestCase):
    """代数数据类型测试"""

    def test_adt_definition(self):
        ev = eval_source("""
            type Color { Red | Green | Blue }
            let c = Red
        """, check_types=False)
        from nova.evaluator import NovaADTValue
        self.assertIsInstance(ev.env.lookup("c"), NovaADTValue)
        self.assertEqual(ev.env.lookup("c").variant_name, "Red")

    def test_adt_with_fields(self):
        ev = eval_source("""
            type Shape { Circle(r: Float) | Rect(w: Float, h: Float) }
            let c = Circle(5.0)
        """, check_types=False)
        from nova.evaluator import NovaADTValue
        c = ev.env.lookup("c")
        self.assertEqual(c.variant_name, "Circle")
        self.assertEqual(len(c.fields), 1)
        self.assertAlmostEqual(c.fields[0], 5.0)

    def test_adt_match(self):
        ev = eval_source("""
            type Shape { Circle(r: Float) | Rect(w: Float, h: Float) }
            fn area(s: Shape) -> Float {
              match s {
                Circle(r)  -> 3.14159 * r * r
                Rect(w, h) -> w * h
              }
            }
            let c = Circle(5.0)
            let result = area(c)
        """, check_types=False)
        result = ev.env.lookup("result")
        self.assertAlmostEqual(result, 78.53975)

    def test_option_some(self):
        ev = eval_source("""
            let x = Some(42)
        """, check_types=False)
        from nova.evaluator import NovaADTValue
        x = ev.env.lookup("x")
        self.assertEqual(x.variant_name, "Some")
        self.assertEqual(x.fields[0], 42)

    def test_option_match(self):
        ev = eval_source("""
            let x = match Some(42) {
                Some(v) -> v
                None    -> 0
            }
        """, check_types=False)
        self.assertEqual(ev.env.lookup("x"), 42)

    def test_option_none_match(self):
        ev = eval_source("""
            let x = match None {
                Some(v) -> v
                None    -> 0
            }
        """, check_types=False)
        self.assertEqual(ev.env.lookup("x"), 0)

    def test_adt_same_variant_name_different_type(self):
        """不同 ADT 类型有同名 variant 时，模式匹配不应跨类型误匹配（evaluator 级别）"""
        from nova.evaluator import NovaADTValue, Evaluator
        from nova.ast_nodes import PatternConstructor, PatternIdentifier

        ev = Evaluator(check_types=False)
        # 注册两个 ADT 类型（模拟 type Color { Red } 和 type Fruit { Red }）
        ev._adt_constructors["Red"] = "Fruit"  # 最后注册的是 Fruit

        # 创建一个 Color.Red 值
        color_red = NovaADTValue("Color", "Red", [], [])

        # 创建一个 Red 构造器模式（编译时期望是 Fruit.Red）
        pattern = PatternConstructor(name="Red", fields=[])

        # 模式匹配应该失败：值是 Color.Red，但模式期望 Fruit.Red
        bindings = {}
        result = ev._match_pattern(pattern, color_red, bindings)
        self.assertFalse(result, "Color.Red 不应匹配 Fruit.Red 模式")

        # 创建一个 Fruit.Red 值
        fruit_red = NovaADTValue("Fruit", "Red", [], [])

        # 模式匹配应该成功
        bindings = {}
        result = ev._match_pattern(pattern, fruit_red, bindings)
        self.assertTrue(result, "Fruit.Red 应该匹配 Fruit.Red 模式")

    def test_adt_same_variant_with_fields_different_type(self):
        """不同 ADT 类型有同名带字段 variant 时，模式匹配不应跨类型误匹配（evaluator 级别）"""
        from nova.evaluator import NovaADTValue, Evaluator
        from nova.ast_nodes import PatternConstructor, PatternIdentifier

        ev = Evaluator(check_types=False)
        # 注册两个 ADT 类型，最后注册的是 Wheel
        ev._adt_constructors["Circle"] = "Wheel"

        # 创建 Shape.Circle(5.0) 值
        shape_circle = NovaADTValue("Shape", "Circle", [5.0], ["radius"])

        # 创建 Circle(r) 构造器模式（编译时期望是 Wheel.Circle）
        r_pattern = PatternIdentifier(name="r")
        pattern = PatternConstructor(name="Circle", fields=[r_pattern])

        # 模式匹配应该失败：值是 Shape.Circle，但模式期望 Wheel.Circle
        bindings = {}
        result = ev._match_pattern(pattern, shape_circle, bindings)
        self.assertFalse(result, "Shape.Circle 不应匹配 Wheel.Circle 模式")

        # 创建 Wheel.Circle(10.0) 值
        wheel_circle = NovaADTValue("Wheel", "Circle", [10.0], ["diameter"])

        # 模式匹配应该成功
        bindings = {}
        result = ev._match_pattern(pattern, wheel_circle, bindings)
        self.assertTrue(result, "Wheel.Circle 应该匹配 Wheel.Circle 模式")
        self.assertEqual(bindings["r"], 10.0)


# ============================================================
# 管道操作测试
# ============================================================

class TestPipe(unittest.TestCase):
    """管道操作测试"""

    def test_simple_pipe(self):
        ev = eval_source("""
            fn double(x: Int) -> Int { x * 2 }
            let result = 5 |> double
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), 10)

    def test_chained_pipe(self):
        ev = eval_source("""
            let result = [1, 2, 3, 4, 5]
                |> filter(|x| x > 2)
                |> map(|x| x * x)
                |> sum
        """, check_types=False)
        # filter > 2: [3,4,5], map * x: [9,16,25], sum: 50
        self.assertEqual(ev.env.lookup("result"), 50)

    def test_pipe_with_lambda(self):
        ev = eval_source("""
            let result = 10 |> (|x| x + 5)
        """, check_types=False)
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
        ev = eval_source('fn main() -> Unit { print(int_to_str(42)) }', check_types=False)
        self.assertEqual(ev.get_output(), ["42"])

    def test_float_to_str(self):
        ev = eval_source('fn main() -> Unit { print(float_to_str(3.14)) }', check_types=False)
        self.assertEqual(ev.get_output(), ["3.14"])

    def test_str_len(self):
        ev = eval_source('let n = str_len("hello")', check_types=False)
        self.assertEqual(ev.env.lookup("n"), 5)

    def test_list_length(self):
        ev = eval_source('let n = list_length([1, 2, 3])', check_types=False)
        self.assertEqual(ev.env.lookup("n"), 3)

    def test_filter(self):
        ev = eval_source('let xs = filter(|x| x > 2, [1, 2, 3, 4])', check_types=False)
        self.assertEqual(ev.env.lookup("xs"), [3, 4])

    def test_map(self):
        ev = eval_source('let xs = map(|x| x * 2, [1, 2, 3])', check_types=False)
        self.assertEqual(ev.env.lookup("xs"), [2, 4, 6])

    def test_sum(self):
        ev = eval_source('let s = sum([1, 2, 3, 4, 5])', check_types=False)
        self.assertEqual(ev.env.lookup("s"), 15)

    def test_head_some(self):
        ev = eval_source('let x = head([1, 2, 3])', check_types=False)
        from nova.evaluator import NovaADTValue
        x = ev.env.lookup("x")
        self.assertEqual(x.variant_name, "Some")
        self.assertEqual(x.fields[0], 1)

    def test_head_none(self):
        ev = eval_source('let x = head([])', check_types=False)
        from nova.evaluator import NovaADTValue
        x = ev.env.lookup("x")
        self.assertEqual(x.variant_name, "None")

    def test_tail_some(self):
        ev = eval_source('let x = tail([1, 2, 3])', check_types=False)
        from nova.evaluator import NovaADTValue
        x = ev.env.lookup("x")
        self.assertEqual(x.variant_name, "Some")
        self.assertEqual(x.fields[0], [2, 3])

    def test_tail_none(self):
        ev = eval_source('let x = tail([])', check_types=False)
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
        ev = eval_source("""
            fn apply(f, x) -> Int { f(x) }
            fn main() -> Unit {
              let result = apply(|n| n * n, 5)
              print(int_to_str(result))
            }
        """, check_types=False)
        self.assertEqual(ev.get_output(), ["25"])

    def test_nested_let(self):
        ev = eval_source("""
            let x = 10
            let y = {
              let a = 20
              let b = 30
              a + b
            }
            let z = x + y
        """, check_types=False)
        self.assertEqual(ev.env.lookup("z"), 60)

    def test_scoping(self):
        ev = eval_source("""
            let x = 1
            let y = {
              let x = 2
              x
            }
        """, check_types=False)
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
        """非法字符不再抛出 LexerError，而是记录到 self.errors 并跳过"""
        lexer = Lexer("@")
        lexer.tokenize()
        self.assertEqual(len(lexer.errors), 1)
        self.assertIn("非法字符 '@'", lexer.errors[0])

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
            eval_source("""
                let x = match 3 {
                    1 -> "one"
                    2 -> "two"
                }
            """, check_types=False)

    def test_try_expr_non_adt_error(self):
        """:`?` 操作符作用于非 ADT 值应抛 RuntimeError_"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("""
                let x = 42?
            """, check_types=False)
        self.assertIn("? 操作符只能在 Option 或 Result 类型上使用", str(ctx.exception))

    def test_try_expr_non_adt_string_error(self):
        """:`?` 操作符作用于字符串应抛 RuntimeError_"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("""
                let x = "hello"?
            """, check_types=False)
        self.assertIn("? 操作符只能在 Option 或 Result 类型上使用", str(ctx.exception))

    def test_try_expr_unknown_adt_variant_error(self):
        """:`?` 操作符作用于非 Option/Result 的 ADT 值应抛 RuntimeError_"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("""
                type Color { Red | Green | Blue }
                let x = Red?
            """, check_types=False)
        self.assertIn("? 操作符只能在 Option 或 Result 类型上使用", str(ctx.exception))

    def test_try_expr_unknown_adt_with_fields_error(self):
        """:`?` 操作符作用于带字段的非 Option/Result ADT 应抛 RuntimeError_"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("""
                type Shape { Circle(r: Float) | Rect(w: Float, h: Float) }
                let x = Circle(5.0)?
            """, check_types=False)
        self.assertIn("? 操作符只能在 Option 或 Result 类型上使用", str(ctx.exception))

    # === TRY_UNWRAP type_name 检查 ===

    def test_try_expr_custom_adt_some_variant_error(self):
        """自定义 ADT 有 Some variant，用 ? 操作符时报错"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("""
                type MyOption { Some(Int) | Nothing }
                let x = Some(42)?
            """, check_types=False)
        self.assertIn("? 操作符只能在 Option 或 Result 类型上使用", str(ctx.exception))

    def test_try_expr_custom_adt_err_variant_error(self):
        """自定义 ADT 有 Err variant，用 ? 操作符时报错"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("""
                type MyResult { Ok(Int) | Err(String) }
                let x = Err("oops")?
            """, check_types=False)
        self.assertIn("? 操作符只能在 Option 或 Result 类型上使用", str(ctx.exception))

    def test_try_expr_option_some_unwrap_ok(self):
        """Option.Some 正常解包（回归测试）"""
        ev = eval_source("""
            fn unwrap_it() -> Int {
                let x = Some(42)?
                x
            }
            let result = unwrap_it()
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), 42)

    def test_try_expr_result_ok_unwrap_ok(self):
        """Result.Ok 正常解包（回归测试）"""
        ev = eval_source("""
            type Result[T, E] { Ok(T) Err(E) }
            fn unwrap_it() -> Int {
                let x = Ok(99)?
                x
            }
            let result = unwrap_it()
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), 99)

    # === 顶层 ? 操作符保护 ===

    def test_try_expr_top_level_let_err_raises_runtime_error(self):
        """顶层 let 绑定中使用 ? (Err) 应报 RuntimeError_ 而非崩溃"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("""
                let x = Err("oops")?
            """, check_types=False)
        self.assertIn("? 操作符不能在顶层使用", str(ctx.exception))

    def test_try_expr_top_level_let_none_raises_runtime_error(self):
        """顶层 let 绑定中使用 ? (None) 应报 RuntimeError_ 而非崩溃"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("""
                let x = None?
            """, check_types=False)
        self.assertIn("? 操作符不能在顶层使用", str(ctx.exception))

    def test_try_expr_top_level_expr_err_raises_runtime_error(self):
        """顶层表达式中使用 ? (Err) 应报 RuntimeError_ 而非崩溃"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("""
                Err("fail")?
            """, check_types=False)
        self.assertIn("? 操作符不能在顶层使用", str(ctx.exception))

    def test_try_expr_top_level_expr_none_raises_runtime_error(self):
        """顶层表达式中使用 ? (None) 应报 RuntimeError_ 而非崩溃"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("""
                None?
            """, check_types=False)
        self.assertIn("? 操作符不能在顶层使用", str(ctx.exception))

    def test_try_expr_in_fn_still_works(self):
        """函数内使用 ? 保持正常工作（回归测试）"""
        ev = eval_source("""
            fn div(a: Int, b: Int) -> Option[Int] {
                if b == 0 then None else Some(a / b)
            }
            fn compute() -> Option[Int] {
                let x = div(10, 2)?
                let y = div(x, 2)?
                Some(y)
            }
            let result = compute()
        """, check_types=False)
        from nova.evaluator import NovaADTValue
        result = ev.env.lookup("result")
        self.assertIsInstance(result, NovaADTValue)
        self.assertEqual(result.variant_name, "Some")
        self.assertEqual(result.fields[0], 2)

    def test_break_top_level_raises_runtime_error(self):
        """顶层使用 break 应报 RuntimeError_ 而非崩溃"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("""
                break
            """, check_types=False)
        self.assertIn("break 不能在顶层使用", str(ctx.exception))

    def test_continue_top_level_raises_runtime_error(self):
        """顶层使用 continue 应报 RuntimeError_ 而非崩溃"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("""
                continue
            """, check_types=False)
        self.assertIn("continue 不能在顶层使用", str(ctx.exception))

    # === 算术运算 bool 检查 ===

    def test_arithmetic_bool_add_error(self):
        """True + 1 应报错"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("let x = true + 1", check_types=False)
        self.assertIn("算术运算 '+' 的操作数不能是 Bool 类型", str(ctx.exception))

    def test_arithmetic_bool_mul_error(self):
        """false * 5 应报错"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("let x = false * 5", check_types=False)
        self.assertIn("算术运算 '*' 的操作数不能是 Bool 类型", str(ctx.exception))

    def test_arithmetic_bool_div_error(self):
        """true / 2 应报错"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("let x = true / 2", check_types=False)
        self.assertIn("算术运算 '/' 的操作数不能是 Bool 类型", str(ctx.exception))

    def test_arithmetic_bool_neg_error(self):
        """-true（一元负）应报错"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("let x = -true", check_types=False)
        self.assertIn("算术运算 '-' 的操作数不能是 Bool 类型", str(ctx.exception))

    def test_arithmetic_int_still_works(self):
        """正常 Int 运算仍然正确（回归测试）"""
        ev = eval_source("""
            let a = 10 + 5
            let b = 10 - 3
            let c = 4 * 3
            let d = 20 / 4
            let e = 10 % 3
            let f = -7
        """, check_types=False)
        self.assertEqual(ev.env.lookup("a"), 15)
        self.assertEqual(ev.env.lookup("b"), 7)
        self.assertEqual(ev.env.lookup("c"), 12)
        self.assertEqual(ev.env.lookup("d"), 5)
        self.assertEqual(ev.env.lookup("e"), 1)
        self.assertEqual(ev.env.lookup("f"), -7)

    # === 短路逻辑运算类型检查 ===

    def test_short_circuit_and_left_non_bool_error(self):
        """42 && true 应报错"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("let x = 42 && true", check_types=False)
        self.assertIn("逻辑运算 '&&' 的操作数必须是 Bool 类型", str(ctx.exception))

    def test_short_circuit_or_left_non_bool_error(self):
        '"" || false 应报错'
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source('let x = "" || false', check_types=False)
        self.assertIn("逻辑运算 '||' 的操作数必须是 Bool 类型", str(ctx.exception))

    def test_short_circuit_and_right_non_bool_error(self):
        """true && 42 应报错（右操作数类型检查）"""
        with self.assertRaises(RuntimeError_) as ctx:
            eval_source("let x = true && 42", check_types=False)
        self.assertIn("逻辑运算 '&&' 的操作数必须是 Bool 类型", str(ctx.exception))

    def test_short_circuit_bool_ops_still_work(self):
        """正常 Bool 运算仍然正确（回归测试）"""
        ev = eval_source("""
            let a = true && true
            let b = true && false
            let c = false || true
            let d = false || false
        """, check_types=False)
        self.assertTrue(ev.env.lookup("a"))
        self.assertFalse(ev.env.lookup("b"))
        self.assertTrue(ev.env.lookup("c"))
        self.assertFalse(ev.env.lookup("d"))


if __name__ == "__main__":
    unittest.main()


# ============================================================
# 循环测试
# ============================================================

class TestLoops(unittest.TestCase):
    """循环语法测试"""

    def test_for_loop_list(self):
        """for x in [1, 2, 3] { x * 2 } == [2, 4, 6]"""
        ev = eval_source("""
            let result = for x in [1, 2, 3] { x * 2 }
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), [2, 4, 6])

    def test_for_range(self):
        """for i <- 0..5 { i } == [0, 1, 2, 3, 4, 5]"""
        ev = eval_source("""
            let result = for i <- 0..5 { i }
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), [0, 1, 2, 3, 4, 5])

    def test_for_range_step(self):
        """for i <- 0..10 step 2 { i } == [0, 2, 4, 6, 8, 10]"""
        ev = eval_source("""
            let result = for i <- 0..10 step 2 { i }
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), [0, 2, 4, 6, 8, 10])

    def test_for_range_negative_step(self):
        """for i <- 5..0 step -1 { i } == [5, 4, 3, 2, 1, 0]（负步长闭区间）"""
        ev = eval_source("""
            let result = for i <- 5..0 step -1 { i }
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), [5, 4, 3, 2, 1, 0])

    def test_for_range_negative_step_by_two(self):
        """for i <- 10..0 step -2 { i } == [10, 8, 6, 4, 2, 0]（负步长步长为2）"""
        ev = eval_source("""
            let result = for i <- 10..0 step -2 { i }
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), [10, 8, 6, 4, 2, 0])

    def test_while_loop(self):
        """while 计数"""
        ev = eval_source("""
            mut sum = 0
            mut i = 1
            while i <= 5 {
              sum = sum + i
              i = i + 1
            }
        """, check_types=False)
        self.assertEqual(ev.env.lookup("sum"), 15)
        self.assertEqual(ev.env.lookup("i"), 6)

    def test_break_in_for(self):
        """break 跳出循环"""
        ev = eval_source("""
            let result = for x in [1, 2, 3, 4, 5] {
              if x == 3 then break
              x
            }
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), [1, 2])

    def test_continue_in_for(self):
        """continue 跳过迭代"""
        ev = eval_source("""
            let result = for x in [1, 2, 3, 4, 5] {
              if x == 3 then continue
              x
            }
        """, check_types=False)
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
        ev = eval_source(f"""
            fn main() -> Unit {{
              write_file("{path}", "Hello Nova!")
            }}
        """, check_types=False)
        ev2 = eval_source(f"""
            fn main() -> Unit {{
              let content = read_file("{path}")
              print(content)
            }}
        """, check_types=False)
        self.assertEqual(ev2.get_output(), ["Hello Nova!"])

    def test_file_exists(self):
        """检查文件存在性"""
        import os
        path = os.path.join(self.tmpdir, "exists_test.txt")
        # 先写入文件
        ev = eval_source(f"""
            fn main() -> Unit {{ write_file("{path}", "test") }}
        """, check_types=False)
        # 检查存在
        ev2 = eval_source(f"""
            let exists = file_exists("{path}")
        """, check_types=False)
        self.assertTrue(ev2.env.lookup("exists"))

    def test_read_file_not_found(self):
        """读取不存在的文件"""
        import os
        path = os.path.join(self.tmpdir, "nonexistent.txt")
        with self.assertRaises(RuntimeError_):
            eval_source(f"""
                fn main() -> Unit {{
                    read_file("{path}")
                }}
            """, check_types=False)


# ============================================================
# JSON 测试
# ============================================================

class TestJSON(unittest.TestCase):
    """JSON 解析/序列化测试"""

    def test_json_parse(self):
        """解析 JSON 字符串"""
        ev = eval_source('let result = json_parse("{\\"key\\": \\"value\\"}")', check_types=False)
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
        ev = eval_source('let result = json_stringify(42)', check_types=False)
        self.assertEqual(ev.env.lookup("result"), "42")

    def test_json_stringify_map(self):
        """序列化字典"""
        ev = eval_source("""
            fn main() -> Unit {
              let m = json_parse("{\\"key\\": \\"value\\"}")
              let result = json_stringify(m)
              print(result)
            }
        """, check_types=False)
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
        ev = eval_source("""
            let result = [x * 2 for x in [1, 2, 3]]
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), [2, 4, 6])

    def test_list_comprehension_range(self):
        """[x * x for x <- 0..5]"""
        ev = eval_source("""
            let result = [x * x for x <- 0..5]
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), [0, 1, 4, 9, 16, 25])

    def test_list_comprehension_filter(self):
        """[x for x <- 1..10 if x % 2 == 0]"""
        ev = eval_source("""
            let result = [x for x <- 1..10 if x % 2 == 0]
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), [2, 4, 6, 8, 10])

    def test_list_comprehension_negative_step(self):
        """[x * x for x <- 5..0 step -1]（负步长闭区间）- 直接构造 AST 测试"""
        from nova.ast_nodes import ListComprehension, IntLiteral, BinaryOp
        # 手动构造 ListComprehension AST，range 元组带负步长
        lc = ListComprehension(
            expr=BinaryOp(left=Identifier("x"), op="*", right=Identifier("x")),
            var_name="x",
            iterable=("range", IntLiteral(5), IntLiteral(0), IntLiteral(-1)),
            filter_cond=None,
        )
        ev = Evaluator(check_types=False)
        result = ev.eval_expr(lc)
        self.assertEqual(result, [25, 16, 9, 4, 1, 0])

    def test_list_comprehension_negative_step_filter(self):
        """[x for x <- 10..0 step -2 if x > 4]（负步长带过滤）- 直接构造 AST 测试"""
        from nova.ast_nodes import ListComprehension, IntLiteral, BinaryOp
        lc = ListComprehension(
            expr=Identifier("x"),
            var_name="x",
            iterable=("range", IntLiteral(10), IntLiteral(0), IntLiteral(-2)),
            filter_cond=BinaryOp(left=Identifier("x"), op=">", right=IntLiteral(4)),
        )
        ev = Evaluator(check_types=False)
        result = ev.eval_expr(lc)
        self.assertEqual(result, [10, 8, 6])

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
        from nova._cli import _is_incomplete
        self.assertTrue(_is_incomplete("fn add(a) {"))
        self.assertFalse(_is_incomplete("42"))
        self.assertTrue(_is_incomplete("if true then {"))
        self.assertTrue(_is_incomplete("let x = ["))
        self.assertTrue(_is_incomplete("let x = ("))
        self.assertFalse(_is_incomplete("let x = 42"))
        self.assertFalse(_is_incomplete("fn add(a: Int) -> Int { a + b }"))

    def test_multiline_with_braces(self):
        """花括号闭合后完成"""
        from nova._cli import _is_incomplete
        self.assertTrue(_is_incomplete("{"))
        self.assertFalse(_is_incomplete("{}"))
        self.assertTrue(_is_incomplete("{{"))
        self.assertFalse(_is_incomplete("{{}}"))

    def test_multiline_with_parens(self):
        """括号闭合后完成"""
        from nova._cli import _is_incomplete
        self.assertTrue(_is_incomplete("("))
        self.assertFalse(_is_incomplete("()"))
        self.assertTrue(_is_incomplete("(1 + "))
        self.assertFalse(_is_incomplete("(1 + 2)"))

    def test_multiline_with_brackets(self):
        """方括号闭合后完成"""
        from nova._cli import _is_incomplete
        self.assertTrue(_is_incomplete("["))
        self.assertFalse(_is_incomplete("[]"))
        self.assertTrue(_is_incomplete("[1, 2, "))
        self.assertFalse(_is_incomplete("[1, 2, 3]"))

    def test_multiline_string_ignored(self):
        """字符串内的括号不影响检测"""
        from nova._cli import _is_incomplete
        self.assertFalse(_is_incomplete('"{"'))
        self.assertFalse(_is_incomplete('"(()"'))
        self.assertFalse(_is_incomplete('let x = "("'))
        # 但转义引号内内容不影响
        self.assertFalse(_is_incomplete('"hello \\"world\\""'))

    def test_count_indent(self):
        """缩进级别计算"""
        from nova._cli import _count_indent
        self.assertEqual(_count_indent("fn add() {"), 1)
        self.assertEqual(_count_indent("fn add() { x + "), 1)
        self.assertEqual(_count_indent("fn add() { x + }"), 0)
        self.assertEqual(_count_indent("{{inner}}"), 0)
        self.assertEqual(_count_indent("{ { }"), 1)

    def test_attach_source(self):
        """_attach_source 为错误附加源码"""
        from nova._cli import _attach_source
        from nova.errors import NovaError
        err = NovaError("test", line=1, column=1)
        self.assertIsNone(err.source_code)
        _attach_source(err, "let x = 42")
        self.assertEqual(err.source_code, "let x = 42")

    def test_attach_source_idempotent(self):
        """_attach_source 不覆盖已有源码"""
        from nova._cli import _attach_source
        from nova.errors import NovaError
        err = NovaError("test", line=1, column=1)
        err.source_code = "original"
        _attach_source(err, "new")
        self.assertEqual(err.source_code, "original")

    def test_error_backwards_compatibility(self):
        """NovaError 的 source_code 和 highlight_span 是可选的"""
        from nova.errors import NovaError, LexerError, ParseError, TypeCheckError, RuntimeError_

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

    def test_vm_while_continue(self):
        """while 循环中的 continue 应跳过当前迭代"""
        vm = self._vm_run("""
            mut sum = 0
            mut i = 0
            while i < 5 {
                i = i + 1
                if i == 2 then continue
                sum = sum + i
            }
        """)
        self.assertEqual(vm.get_global("i"), 5)
        self.assertEqual(vm.get_global("sum"), 13)

    def test_vm_while_continue_first_iteration(self):
        """首次迭代即触发 continue 不应崩溃（VM-7-1 修复验证）"""
        vm = self._vm_run("""
            mut sum = 0
            mut i = 0
            while i < 5 {
                i = i + 1
                if i == 1 then continue
                sum = sum + i
            }
        """)
        self.assertEqual(vm.get_global("i"), 5)
        self.assertEqual(vm.get_global("sum"), 14)

    def test_vm_while_break(self):
        """while 循环中的 break 应正确跳出循环并清理栈"""
        vm = self._vm_run("""
            mut sum = 0
            mut i = 1
            while i <= 10 {
                if i == 5 then break
                sum = sum + i
                i = i + 1
            }
        """)
        self.assertEqual(vm.get_global("i"), 5)
        self.assertEqual(vm.get_global("sum"), 10)

    def test_vm_while_break_first_iteration(self):
        """首次迭代即触发 break 不应崩溃且栈应正确清理"""
        vm = self._vm_run("""
            mut sum = 0
            mut i = 1
            while i <= 10 {
                break
                sum = sum + i
                i = i + 1
            }
        """)
        self.assertEqual(vm.get_global("i"), 1)
        self.assertEqual(vm.get_global("sum"), 0)

    def test_vm_while_break_nested(self):
        """嵌套 while 循环中 break 应只跳出内层，_while_loops 栈不泄漏"""
        vm = self._vm_run("""
            mut outer_sum = 0
            mut i = 1
            while i <= 3 {
                mut inner_sum = 0
                mut j = 1
                while j <= 10 {
                    if j == 4 then break
                    inner_sum = inner_sum + j
                    j = j + 1
                }
                outer_sum = outer_sum + inner_sum
                i = i + 1
            }
        """)
        self.assertEqual(vm.get_global("i"), 4)
        self.assertEqual(vm.get_global("outer_sum"), 18)  # 3 * (1+2+3) = 18

    def test_vm_while_break_with_mutation_after(self):
        """while break 后继续执行其他代码应正常（验证栈未被污染）"""
        vm = self._vm_run("""
            mut result = 0
            mut i = 1
            {
                while i <= 5 {
                    if i == 3 then break
                    result = result + i
                    i = i + 1
                }
                result = result * 10
                result = result + 99
            }
        """)
        self.assertEqual(vm.get_global("result"), 129)  # (1+2)*10 + 99 = 129

    def test_vm_while_break_stack_balance(self):
        """while break 后栈应保持平衡（深度为 base_sp），验证 off-by-one 修复"""
        vm = self._vm_run("""
            mut i = 1
            while i <= 10 {
                if i == 5 then break
                i = i + 1
            }
        """)
        # 栈在 break 后应完全清理，最终栈深度应为 0
        self.assertEqual(len(vm.stack), 0,
                         f"while break 后栈未平衡，有 {len(vm.stack)} 个残留元素: {vm.stack}")
        self.assertEqual(vm.get_global("i"), 5)

    def test_vm_while_continue_stack_balance(self):
        """while continue 后栈应保持平衡（深度为 base_sp），验证 off-by-one 修复"""
        vm = self._vm_run("""
            mut sum = 0
            mut i = 0
            while i < 5 {
                i = i + 1
                if i == 2 then continue
                sum = sum + i
            }
        """)
        # 栈在每次 continue 后应完全清理，最终栈深度应为 0
        self.assertEqual(len(vm.stack), 0,
                         f"while continue 后栈未平衡，有 {len(vm.stack)} 个残留元素: {vm.stack}")
        self.assertEqual(vm.get_global("sum"), 13)
        self.assertEqual(vm.get_global("i"), 5)

    def test_vm_while_break_nested_stack_balance(self):
        """嵌套 while 循环中 break 后栈应保持平衡（多层 off-by-one 会累积）"""
        vm = self._vm_run("""
            mut outer = 0
            mut i = 1
            while i <= 3 {
                mut j = 1
                while j <= 10 {
                    if j == 4 then break
                    j = j + 1
                }
                outer = outer + j
                i = i + 1
            }
        """)
        self.assertEqual(len(vm.stack), 0,
                         f"嵌套 while break 后栈未平衡，有 {len(vm.stack)} 个残留元素: {vm.stack}")
        self.assertEqual(vm.get_global("outer"), 12)  # 3 * 4 = 12

    def test_vm_while_continue_nested_stack_balance(self):
        """嵌套 while 循环中 continue 后栈应保持平衡"""
        vm = self._vm_run("""
            mut outer_sum = 0
            mut i = 0
            while i < 3 {
                i = i + 1
                mut inner_sum = 0
                mut j = 0
                while j < 5 {
                    j = j + 1
                    if j == 2 then continue
                    inner_sum = inner_sum + j
                }
                outer_sum = outer_sum + inner_sum
            }
        """)
        self.assertEqual(len(vm.stack), 0,
                         f"嵌套 while continue 后栈未平衡，有 {len(vm.stack)} 个残留元素: {vm.stack}")
        # 每次内层: 1+3+4+5 = 13 (跳过 2)
        self.assertEqual(vm.get_global("outer_sum"), 39)  # 3 * 13 = 39

    def test_vm_while_break_in_function_stack_balance(self):
        """函数内 while break 后栈应平衡，函数返回值应正确"""
        vm = self._vm_run("""
            fn find_first_even(max: Int) -> Int {
                mut i = 1
                mut result = 0
                while i <= max {
                    if i % 2 == 0 then {
                        result = i
                        break
                    }
                    i = i + 1
                }
                result
            }
            let x = find_first_even(10)
        """)
        self.assertEqual(vm.get_global("x"), 2)
        # 验证顶层栈平衡
        self.assertEqual(len(vm.stack), 0,
                         f"函数内 while break 后顶层栈未平衡: {len(vm.stack)} 个残留元素")

    def test_vm_while_continue_in_function_stack_balance(self):
        """函数内 while continue 后栈应平衡，函数返回值应正确"""
        vm = self._vm_run("""
            fn sum_odds(n: Int) -> Int {
                mut i = 0
                mut sum = 0
                while i < n {
                    i = i + 1
                    if i % 2 == 0 then continue
                    sum = sum + i
                }
                sum
            }
            let x = sum_odds(10)
        """)
        self.assertEqual(vm.get_global("x"), 25)  # 1+3+5+7+9 = 25
        self.assertEqual(len(vm.stack), 0,
                         f"函数内 while continue 后顶层栈未平衡: {len(vm.stack)} 个残留元素")

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
            fn apply(f: (Int) -> Int, x: Int) -> Int { f(x) }
            let x = apply(|n| n * n, 5)
        """)
        self.assertEqual(vm.get_global("x"), 25)

    def test_vm_empty_for_loop_list(self):
        """空列表 for 循环应返回空列表"""
        vm = self._vm_run("""
            let result = for x in [] { x * 2 }
        """)
        self.assertEqual(vm.get_global("result"), [])

    def test_vm_empty_for_loop_range(self):
        """空范围 for 循环（start > end，正步长）应返回空列表"""
        vm = self._vm_run("""
            let result = for i <- 5..0 { i }
        """)
        self.assertEqual(vm.get_global("result"), [])

    def test_vm_empty_for_loop_zero_step(self):
        """空范围 for 循环（0..-1，负步长）应返回空列表"""
        vm = self._vm_run("""
            let result = for i <- 0..-10 step -2 { i }
        """)
        self.assertEqual(vm.get_global("result"), [0, -2, -4, -6, -8, -10])

    def test_vm_adt_match_multi_branch(self):
        """多分支 ADT 模式匹配：第一个分支失败时应正确匹配第二个分支"""
        vm = self._vm_run("""
            type Shape { Circle(r: Float) | Rect(w: Float, h: Float) | Square(s: Float) }
            fn area(s: Shape) -> Float {
                match s {
                    Circle(r)   -> 3.14159 * r * r
                    Rect(w, h)  -> w * h
                    Square(s)   -> s * s
                }
            }
            let r = Rect(3.0, 4.0)
            let area_rect = area(r)
            let sq = Square(5.0)
            let area_sq = area(sq)
        """)
        self.assertAlmostEqual(vm.get_global("area_rect"), 12.0)
        self.assertAlmostEqual(vm.get_global("area_sq"), 25.0)

    def test_vm_option_match_none_first(self):
        """Option 匹配：None 在前时 Some 值应正确匹配后面的分支"""
        vm = self._vm_run("""
            let x = match Some(42) {
                None    -> 0
                Some(v) -> v
            }
        """)
        self.assertEqual(vm.get_global("x"), 42)

    def test_vm_adt_match_falls_through_to_wildcard(self):
        """ADT 匹配失败应正确落到通配符分支"""
        vm = self._vm_run("""
            type Shape { Circle(r: Float) | Rect(w: Float, h: Float) }
            fn describe(s: Shape) -> String {
                match s {
                    Circle(r) -> "circle"
                    _         -> "other"
                }
            }
            let r = Rect(2.0, 3.0)
            let d = describe(r)
        """)
        self.assertEqual(vm.get_global("d"), "other")

    # ---- P1 Bug #7: 零字段 ADT 变体的模式匹配 ----

    def test_vm_match_option_none_arm(self):
        """匹配 Option[Int]：None 分支应正确匹配"""
        vm = self._vm_run("""
            let x = match None {
                Some(v) -> v
                None    -> 0
            }
        """)
        self.assertEqual(vm.get_global("x"), 0)

    def test_vm_match_option_none_first_arm(self):
        """匹配 Option[Int]：None 是第一个分支时，Some 应正确匹配后续分支"""
        vm = self._vm_run("""
            let x = match Some(42) {
                None    -> 0
                Some(v) -> v
            }
        """)
        self.assertEqual(vm.get_global("x"), 42)

    def test_vm_match_zero_field_variant(self):
        """用户自定义零字段变体应正确匹配（非第一个分支）"""
        vm = self._vm_run("""
            type Color { Red | Green | Blue }
            let c = Green
            let x = match c {
                Red   -> 1
                Green -> 2
                Blue  -> 3
            }
        """)
        self.assertEqual(vm.get_global("x"), 2)

    def test_vm_match_zero_field_variant_last_arm(self):
        """用户自定义零字段变体在最后一个分支应正确匹配"""
        vm = self._vm_run("""
            type Color { Red | Green | Blue }
            let c = Blue
            let x = match c {
                Red   -> 1
                Green -> 2
                Blue  -> 3
            }
        """)
        self.assertEqual(vm.get_global("x"), 3)

    def test_vm_match_zero_field_with_wildcard(self):
        """零字段变体不匹配时应正确落到通配符"""
        vm = self._vm_run("""
            type Color { Red | Green | Blue }
            let c = Blue
            let x = match c {
                Red   -> "red"
                Green -> "green"
                _     -> "other"
            }
        """)
        self.assertEqual(vm.get_global("x"), "other")

    def test_vm_match_mixed_adt_variants(self):
        """混合零字段和带字段变体的匹配"""
        vm = self._vm_run("""
            type Shape { Circle(r: Float) | Point | Square(s: Float) }
            fn describe(s: Shape) -> String {
                match s {
                    Circle(r) -> "circle"
                    Point     -> "point"
                    Square(s) -> "square"
                }
            }
            let p = Point
            let d = describe(p)
        """)
        self.assertEqual(vm.get_global("d"), "point")

    def test_vm_match_same_variant_name_different_type(self):
        """不同 ADT 类型有同名 variant 时，MATCH_CONSTRUCTOR 应检查 type_name"""
        from nova.compiler import Bytecode, Op, Instruction
        from nova.vm import NovaVM

        # 手动构造字节码来测试 type_name 检查
        bc = Bytecode()
        # 创建 Color.Red (零字段)
        bc.emit_op(Op.MAKE_ADT, "Color", "Red", 0, ())
        # MATCH_START: arm_count=1
        bc.emit_op(Op.MATCH_START, 1)
        # MATCH_ARM_START
        bc.emit_op(Op.MATCH_ARM_START)
        # MATCH_CONSTRUCTOR: 期望 Fruit.Red，应匹配失败跳转到 fail_ip
        fail_pos = len(bc.code)
        bc.emit_op(Op.MATCH_CONSTRUCTOR, "Fruit", "Red", 0, 0)
        # 匹配成功：返回 "matched"
        idx_matched = bc.add_const("matched")
        bc.emit_op(Op.LOAD_CONST, idx_matched)
        bc.emit_op(Op.MATCH_END)
        bc.emit_op(Op.HALT)
        # 失败分支（第二个 arm / fallback）
        fail_ip = len(bc.code)
        bc.emit_op(Op.MATCH_ARM_START)
        bc.emit_op(Op.MATCH_WILDCARD)
        idx_not_matched = bc.add_const("not-matched")
        bc.emit_op(Op.LOAD_CONST, idx_not_matched)
        bc.emit_op(Op.MATCH_END)
        bc.emit_op(Op.HALT)

        # 回填 fail_ip
        bc.patch_match_fail(fail_pos, fail_ip)

        vm = NovaVM(bc)
        vm.run()
        # Color.Red 不应匹配 Fruit.Red 模式，应落到通配符分支
        result = vm.stack[-1] if vm.stack else None
        self.assertEqual(result, "not-matched")

    def test_vm_match_same_variant_same_type(self):
        """同类型同名 variant 应正确匹配"""
        from nova.compiler import Bytecode, Op
        from nova.vm import NovaVM

        bc = Bytecode()
        # 创建 Color.Red
        bc.emit_op(Op.MAKE_ADT, "Color", "Red", 0, ())
        # MATCH_START: arm_count=1
        bc.emit_op(Op.MATCH_START, 1)
        # MATCH_ARM_START
        bc.emit_op(Op.MATCH_ARM_START)
        # MATCH_CONSTRUCTOR: 期望 Color.Red，应匹配成功
        fail_pos = len(bc.code)
        bc.emit_op(Op.MATCH_CONSTRUCTOR, "Color", "Red", 0, 0)
        # 匹配成功
        idx_matched = bc.add_const("matched")
        bc.emit_op(Op.LOAD_CONST, idx_matched)
        bc.emit_op(Op.MATCH_END)
        bc.emit_op(Op.HALT)
        # 失败分支
        fail_ip = len(bc.code)
        bc.emit_op(Op.MATCH_ARM_START)
        bc.emit_op(Op.MATCH_WILDCARD)
        idx_not_matched = bc.add_const("not-matched")
        bc.emit_op(Op.LOAD_CONST, idx_not_matched)
        bc.emit_op(Op.MATCH_END)
        bc.emit_op(Op.HALT)

        bc.patch_match_fail(fail_pos, fail_ip)

        vm = NovaVM(bc)
        vm.run()
        result = vm.stack[-1] if vm.stack else None
        self.assertEqual(result, "matched")

    def test_vm_match_same_variant_with_fields_different_type(self):
        """不同类型同名字段 variant 应检查 type_name"""
        from nova.compiler import Bytecode, Op
        from nova.vm import NovaVM

        bc = Bytecode()
        # 压入字段值 5.0
        idx_5 = bc.add_const(5.0)
        bc.emit_op(Op.LOAD_CONST, idx_5)
        # 创建 Shape.Circle(5.0)
        bc.emit_op(Op.MAKE_ADT, "Shape", "Circle", 1, ("radius",))
        # MATCH_START
        bc.emit_op(Op.MATCH_START, 1)
        bc.emit_op(Op.MATCH_ARM_START)
        # MATCH_CONSTRUCTOR: 期望 Wheel.Circle(1)，应匹配失败
        fail_pos = len(bc.code)
        bc.emit_op(Op.MATCH_CONSTRUCTOR, "Wheel", "Circle", 1, 0)
        # 匹配成功
        idx_matched = bc.add_const("matched")
        bc.emit_op(Op.LOAD_CONST, idx_matched)
        bc.emit_op(Op.MATCH_END)
        bc.emit_op(Op.HALT)
        # 失败分支
        fail_ip = len(bc.code)
        bc.emit_op(Op.MATCH_ARM_START)
        bc.emit_op(Op.MATCH_WILDCARD)
        idx_not_matched = bc.add_const("not-matched")
        bc.emit_op(Op.LOAD_CONST, idx_not_matched)
        bc.emit_op(Op.MATCH_END)
        bc.emit_op(Op.HALT)

        bc.patch_match_fail(fail_pos, fail_ip)

        vm = NovaVM(bc)
        vm.run()
        result = vm.stack[-1] if vm.stack else None
        self.assertEqual(result, "not-matched")

    # ---- P1 Bug #8: for 循环 + break 栈布局 ----

    def test_vm_for_break_returns_correct_list(self):
        """for 循环中 break 应返回正确的累积列表"""
        vm = self._vm_run("""
            let result = for x in [1, 2, 3, 4, 5] {
                if x == 3 then break
                x
            }
        """)
        self.assertEqual(vm.get_global("result"), [1, 2])

    def test_vm_for_break_first_iteration(self):
        """第一次迭代就 break 应返回空列表"""
        vm = self._vm_run("""
            let result = for x in [1, 2, 3] {
                break
                x
            }
        """)
        self.assertEqual(vm.get_global("result"), [])

    def test_vm_for_break_empty_result(self):
        """break 在第一次迭代时返回空列表（range 版本）"""
        vm = self._vm_run("""
            let result = for i <- 1..5 {
                break
                i
            }
        """)
        self.assertEqual(vm.get_global("result"), [])

    def test_vm_for_break_with_range(self):
        """范围 for 循环中 break 应返回正确结果"""
        vm = self._vm_run("""
            let result = for i <- 1..10 {
                if i > 5 then break
                i * i
            }
        """)
        self.assertEqual(vm.get_global("result"), [1, 4, 9, 16, 25])

    def test_vm_nested_for_break(self):
        """嵌套 for 循环中 break 应只跳出内层循环"""
        vm = self._vm_run("""
            let result = for x in [1, 2, 3] {
                for y in [10, 20, 30] {
                    if y == 20 then break
                    x + y
                }
            }
        """)
        self.assertEqual(vm.get_global("result"), [[11], [12], [13]])

    def test_vm_for_continue_works(self):
        """for 循环中 continue 应正确跳过迭代"""
        vm = self._vm_run("""
            let result = for x in [1, 2, 3, 4, 5] {
                if x == 3 then continue
                x
            }
        """)
        self.assertEqual(vm.get_global("result"), [1, 2, 4, 5])

    # ---- P2 Bug #13: ADT 字段访问 ----

    def test_vm_adt_named_field_access(self):
        """ADT 命名字段访问（单变体）"""
        vm = self._vm_run("""
            type Point { Point(x: Int, y: Int) }
            let p = Point(3, 4)
            let px = p.x
            let py = p.y
        """)
        self.assertEqual(vm.get_global("px"), 3)
        self.assertEqual(vm.get_global("py"), 4)

    def test_vm_adt_index_field_access(self):
        """ADT 索引字段访问"""
        vm = self._vm_run("""
            type Point { Point(x: Int, y: Int) }
            let p = Point(10, 20)
            let first = p.0
            let second = p.1
        """)
        self.assertEqual(vm.get_global("first"), 10)
        self.assertEqual(vm.get_global("second"), 20)

    def test_vm_adt_shared_field_access(self):
        """多变体共享同名字段的访问"""
        vm = self._vm_run("""
            type Shape { Circle(radius: Float) | Square(radius: Float) }
            fn get_radius(s: Shape) -> Float { s.radius }
            let c = Circle(5.0)
            let r = get_radius(c)
        """)
        self.assertAlmostEqual(vm.get_global("r"), 5.0)

    def test_vm_some_value_field_type_error(self):
        """Some(x).value 在类型检查阶段应报错（None 没有 value 字段）"""
        from nova.errors import TypeCheckError
        with self.assertRaises(TypeCheckError):
            self._vm_run("""
                let s = Some(42)
                let v = s.value
            """)

    def test_vm_adt_field_access_in_expression(self):
        """ADT 字段访问在表达式中使用"""
        vm = self._vm_run("""
            type Point { Point(x: Int, y: Int) }
            let p = Point(3, 4)
            let sum = p.x + p.y
        """)
        self.assertEqual(vm.get_global("sum"), 7)

    # ---- P2 Bug #14: MATCH_* 栈操作约定统一 ----

    def test_vm_match_int_multi_branch(self):
        """多分支整数匹配：前几个分支失败时应正确匹配后续分支"""
        vm = self._vm_run("""
            let x = match 3 {
                1 -> "one"
                2 -> "two"
                3 -> "three"
                4 -> "four"
                _ -> "other"
            }
        """)
        self.assertEqual(vm.get_global("x"), "three")

    def test_vm_match_int_first_branch(self):
        """整数匹配第一个分支成功"""
        vm = self._vm_run("""
            let x = match 1 {
                1 -> "one"
                2 -> "two"
                _ -> "other"
            }
        """)
        self.assertEqual(vm.get_global("x"), "one")

    def test_vm_match_int_last_branch(self):
        """整数匹配最后一个字面量分支"""
        vm = self._vm_run("""
            let x = match 5 {
                1 -> "one"
                2 -> "two"
                3 -> "three"
                5 -> "five"
            }
        """)
        self.assertEqual(vm.get_global("x"), "five")

    def test_vm_match_bool_multi_branch(self):
        """多分支布尔匹配"""
        vm = self._vm_run("""
            let x = match false {
                true -> "yes"
                false -> "no"
            }
        """)
        self.assertEqual(vm.get_global("x"), "no")

    def test_vm_match_string_multi_branch(self):
        """多分支字符串匹配：前几个失败后应正确匹配"""
        vm = self._vm_run("""
            let x = match "banana" {
                "apple" -> 1
                "orange" -> 2
                "banana" -> 3
                _ -> 0
            }
        """)
        self.assertEqual(vm.get_global("x"), 3)

    def test_vm_match_string_first_branch(self):
        """字符串匹配第一个分支成功"""
        vm = self._vm_run("""
            let x = match "apple" {
                "apple" -> 1
                "banana" -> 2
                _ -> 0
            }
        """)
        self.assertEqual(vm.get_global("x"), 1)

    def test_vm_match_wildcard_fallback(self):
        """所有字面量分支失败后落到通配符"""
        vm = self._vm_run("""
            let x = match 99 {
                1 -> "one"
                2 -> "two"
                3 -> "three"
                _ -> "many"
            }
        """)
        self.assertEqual(vm.get_global("x"), "many")

    def test_vm_match_bind_fallback(self):
        """所有字面量分支失败后落到变量绑定"""
        vm = self._vm_run("""
            let x = match 42 {
                1 -> "one"
                2 -> "two"
                n -> int_to_str(n)
            }
        """)
        self.assertEqual(vm.get_global("x"), "42")

    def test_vm_match_mixed_types_fallback(self):
        """混合类型匹配：整数失败后到变量绑定"""
        vm = self._vm_run("""
            let x = match "hello" {
                "world" -> 1
                s -> str_len(s)
            }
        """)
        self.assertEqual(vm.get_global("x"), 5)

    def test_vm_match_adt_constructor_multi_branch(self):
        """多分支 ADT 构造器匹配：验证栈操作一致性"""
        vm = self._vm_run("""
            type Shape { Circle(r: Float) | Rect(w: Float, h: Float) | Square(s: Float) }
            fn area(s: Shape) -> Float {
                match s {
                    Circle(r)   -> 3.14159 * r * r
                    Rect(w, h)  -> w * h
                    Square(s)   -> s * s
                }
            }
            let c = Circle(2.0)
            let a1 = area(c)
            let r = Rect(3.0, 4.0)
            let a2 = area(r)
            let sq = Square(5.0)
            let a3 = area(sq)
        """)
        self.assertAlmostEqual(vm.get_global("a1"), 12.56636)
        self.assertAlmostEqual(vm.get_global("a2"), 12.0)
        self.assertAlmostEqual(vm.get_global("a3"), 25.0)

    def test_vm_match_zero_field_constructor_multi_branch(self):
        """零字段构造器多分支匹配"""
        vm = self._vm_run("""
            type Color { Red | Green | Blue | Yellow }
            fn to_int(c: Color) -> Int {
                match c {
                    Red    -> 1
                    Green  -> 2
                    Blue   -> 3
                    Yellow -> 4
                }
            }
            let r = to_int(Red)
            let g = to_int(Green)
            let b = to_int(Blue)
            let y = to_int(Yellow)
        """)
        self.assertEqual(vm.get_global("r"), 1)
        self.assertEqual(vm.get_global("g"), 2)
        self.assertEqual(vm.get_global("b"), 3)
        self.assertEqual(vm.get_global("y"), 4)

    def test_vm_match_constructor_field_subpattern_mismatch(self):
        """构造器字段子模式不匹配：Some(0) 不应匹配 Some(42)"""
        vm = self._vm_run("""
            let result = match Some(42) {
                Some(0)  -> "zero"
                _        -> "other"
            }
        """)
        self.assertEqual(vm.get_global("result"), "other")

    def test_vm_match_constructor_field_subpattern_match(self):
        """构造器字段子模式匹配：Some(42) 应匹配 Some(42)"""
        vm = self._vm_run("""
            let result = match Some(42) {
                Some(42) -> "yes"
                _        -> "no"
            }
        """)
        self.assertEqual(vm.get_global("result"), "yes")

    def test_vm_match_custom_adt_field_subpattern(self):
        """自定义 ADT 构造器字段子模式匹配"""
        vm = self._vm_run("""
            type Shape { Circle(r: Float) | Rect(w: Float, h: Float) }
            let s = Rect(3.0, 4.0)
            let result = match s {
                Rect(3.0, h) -> h * 10.0
                Circle(r)    -> r
                _            -> 0.0
            }
        """)
        self.assertAlmostEqual(vm.get_global("result"), 40.0)

    def test_vm_match_constructor_nested_field_subpattern(self):
        """嵌套构造器字段子模式匹配：Some(Ok(42)) 匹配 Some(Ok(42))"""
        vm = self._vm_run("""
            type Result[T, E] { Ok(T) Err(E) }
            let x = Some(Ok(42))
            let result = match x {
                Some(Ok(42)) -> "found"
                Some(Err(_)) -> "error"
                None         -> "none"
                _            -> "other"
            }
        """)
        self.assertEqual(vm.get_global("result"), "found")

    # ============================================================
    # 多字段混合模式测试（修复栈错位 Bug）
    # ============================================================

    def test_vm_match_constructor_bind_then_literal(self):
        """构造器模式：先绑定后字面量（T(a, 20)），验证栈不错位"""
        vm = self._vm_run("""
            type Pair { P(Int, Int) }
            let p = P(10, 20)
            let result = match p {
                P(a, 20) -> a * 2
                _        -> 0
            }
        """)
        self.assertEqual(vm.get_global("result"), 20)

    def test_vm_match_constructor_literal_then_bind(self):
        """构造器模式：先字面量后绑定（P(10, b)），验证正常工作"""
        vm = self._vm_run("""
            type Pair { P(Int, Int) }
            let p = P(10, 20)
            let result = match p {
                P(10, b) -> b * 2
                _        -> 0
            }
        """)
        self.assertEqual(vm.get_global("result"), 40)

    def test_vm_match_constructor_three_field_mixed(self):
        """三字段构造器混合模式：T3(a, 20, c)，中间有字面量，验证栈不错位"""
        vm = self._vm_run("""
            type Triple { T3(Int, Int, Int) }
            let t = T3(10, 20, 30)
            let result = match t {
                T3(a, 20, c) -> a + c
                _             -> 0
            }
        """)
        self.assertEqual(vm.get_global("result"), 40)

    def test_vm_match_constructor_three_field_mixed_wildcard(self):
        """三字段构造器混合模式：T3(_, 20, c)，包含通配符，验证栈不错位"""
        vm = self._vm_run("""
            type Triple { T3(Int, Int, Int) }
            let t = T3(10, 20, 30)
            let result = match t {
                T3(_, 20, c) -> c * 2
                _             -> 0
            }
        """)
        self.assertEqual(vm.get_global("result"), 60)

    def test_vm_match_constructor_mixed_first_literal_fails(self):
        """构造器混合模式：第一个字段字面量不匹配，正确fallback"""
        vm = self._vm_run("""
            type Triple { T3(Int, Int, Int) }
            let t = T3(10, 20, 30)
            let result = match t {
                T3(99, b, c) -> b + c
                _             -> -1
            }
        """)
        self.assertEqual(vm.get_global("result"), -1)

    def test_vm_match_tuple_mixed_bind_literal(self):
        """元组模式：混合绑定和字面量（(a, 20, c)），验证栈不错位"""
        vm = self._vm_run("""
            let t = (10, 20, 30)
            let result = match t {
                (a, 20, c) -> a + c
                _          -> 0
            }
        """)
        self.assertEqual(vm.get_global("result"), 40)

    def test_vm_match_tuple_mixed_literal_bind(self):
        """元组模式：先字面量后绑定（(10, b, 30)），验证正常"""
        vm = self._vm_run("""
            let t = (10, 20, 30)
            let result = match t {
                (10, b, 30) -> b * 2
                _           -> 0
            }
        """)
        self.assertEqual(vm.get_global("result"), 40)

    def test_vm_match_tuple_mixed_wildcard(self):
        """元组模式：混合通配符和字面量（(_, 20, c)），验证栈不错位"""
        vm = self._vm_run("""
            let t = (10, 20, 30)
            let result = match t {
                (_, 20, c) -> c * 2
                _          -> 0
            }
        """)
        self.assertEqual(vm.get_global("result"), 60)

    def test_vm_match_list_mixed_bind_literal(self):
        """列表模式：混合绑定和字面量（[a, 20, c]），验证栈不错位"""
        vm = self._vm_run("""
            let xs = [10, 20, 30]
            let result = match xs {
                [a, 20, c] -> a + c
                _          -> 0
            }
        """)
        self.assertEqual(vm.get_global("result"), 40)

    def test_vm_match_list_mixed_wildcard_literal(self):
        """列表模式：混合通配符、字面量和绑定（[_, 20, c]），验证栈不错位"""
        vm = self._vm_run("""
            let xs = [10, 20, 30]
            let result = match xs {
                [_, 20, c] -> c * 2
                _          -> 0
            }
        """)
        self.assertEqual(vm.get_global("result"), 60)

    def test_vm_match_nested_constructor_mixed(self):
        """嵌套构造器混合模式：外层字面量+绑定，内层绑定+字面量，验证栈不错位"""
        vm = self._vm_run("""
            type Triple { T3(Int, Int, Int) }
            type Wrapper { W(Int, Triple) }
            let w = W(1, T3(10, 20, 30))
            let result = match w {
                W(1, T3(a, 20, c)) -> a + c
                _                   -> 0
            }
        """)
        self.assertEqual(vm.get_global("result"), 40)

    # ============================================================
    # 空循环测试
    # ============================================================

    def test_vm_empty_range_for(self):
        """for i <- 1..0 { i } returns []（空范围）"""
        output = run_source("""
            let result = for i <- 1..0 { i }
            print(result)
        """, use_vm=True, capture_output=True)
        self.assertEqual(output, ["[]"])

    def test_vm_empty_list_for(self):
        """for x in [] { x } returns []"""
        output = run_source("""
            let result = for x in [] { x }
            print(result)
        """, use_vm=True, capture_output=True)
        self.assertEqual(output, ["[]"])

    def test_vm_empty_negative_range(self):
        """空范围 for 循环：正步长返回 []，负步长正确迭代"""
        output1 = run_source("""
            let result = for i <- 5..0 { i }
            print(result)
        """, use_vm=True, capture_output=True)
        self.assertEqual(output1, ["[]"])
        output2 = run_source("""
            let result = for i <- 5..0 step -1 { i }
            print(result)
        """, use_vm=True, capture_output=True)
        self.assertEqual(output2, ["[5, 4, 3, 2, 1, 0]"])

    def test_vm_empty_range_with_break(self):
        """for i <- 0..0 { if i == 0 then break } returns []"""
        output = run_source("""
            let result = for i <- 0..0 { if i == 0 then break }
            print(result)
        """, use_vm=True, capture_output=True)
        self.assertEqual(output, ["[]"])

    def test_vm_range_zero_to_zero(self):
        """for i <- 0..0 { i } returns [0]（inclusive range，单元素）"""
        output = run_source("""
            let result = for i <- 0..0 { i }
            print(result)
        """, use_vm=True, capture_output=True)
        self.assertEqual(output, ["[0]"])

    def test_vm_empty_list_for_identity(self):
        """for x in [] { x } returns []"""
        output = run_source("""
            let result = for x in [] { x }
            print(result)
        """, use_vm=True, capture_output=True)
        self.assertEqual(output, ["[]"])

    # ============================================================
    # 嵌套循环测试
    # ============================================================

    def test_vm_nested_for(self):
        """嵌套 for 循环应正确生成嵌套列表"""
        output = run_source("""
            let result = for x in [1, 2] {
                for y in [10, 20] {
                    x + y
                }
            }
            print(result)
        """, use_vm=True, capture_output=True)
        self.assertEqual(output, ["[[11, 21], [12, 22]]"])

    def test_vm_nested_for_break_inner(self):
        """break 在内层循环应只跳出内层"""
        output = run_source("""
            let result = for x in [1, 2, 3] {
                for y in [10, 20, 30] {
                    if y == 20 then break
                    x + y
                }
            }
            print(result)
        """, use_vm=True, capture_output=True)
        self.assertEqual(output, ["[[11], [12], [13]]"])

    def test_vm_nested_for_break_outer(self):
        """break 在外层循环体（不在内层中）应跳出外层"""
        output = run_source("""
            let result = for x in [1, 2, 3] {
                if x == 2 then break
                for y in [10, 20] {
                    x + y
                }
            }
            print(result)
        """, use_vm=True, capture_output=True)
        self.assertEqual(output, ["[[11, 21]]"])

    def test_vm_nested_for_continue(self):
        """continue 在嵌套循环中应作用于当前层"""
        output = run_source("""
            let result = for x in [1, 2, 3] {
                for y in [10, 20, 30] {
                    if y == 20 then continue
                    x + y
                }
            }
            print(result)
        """, use_vm=True, capture_output=True)
        self.assertEqual(output, ["[[11, 31], [12, 32], [13, 33]]"])

    # ============================================================
    # 多分支 ADT 匹配测试
    # ============================================================

    def test_vm_match_three_branches(self):
        """三分支 ADT，每个分支都应正确匹配"""
        output = run_source("""
            type Color { Red | Green | Blue }
            fn to_int(c: Color) -> Int {
                match c {
                    Red   -> 1
                    Green -> 2
                    Blue  -> 3
                }
            }
            print(to_int(Red))
            print(to_int(Green))
            print(to_int(Blue))
        """, use_vm=True, capture_output=True)
        self.assertEqual(output, ["1", "2", "3"])

    def test_vm_match_first_branch_fails(self):
        """第一个分支不匹配时应正确匹配后续分支"""
        output = run_source("""
            type Shape { Circle(r: Float) | Rect(w: Float, h: Float) }
            fn area(s: Shape) -> Float {
                match s {
                    Circle(r)  -> 3.14159 * r * r
                    Rect(w, h) -> w * h
                }
            }
            print(area(Rect(3.0, 4.0)))
        """, use_vm=True, capture_output=True)
        self.assertEqual(output, ["12.0"])

    def test_vm_match_all_branches_fail_to_wildcard(self):
        """所有构造器分支失败后通配符应捕获"""
        output = run_source("""
            type Shape { Circle(r: Float) | Rect(w: Float, h: Float) }
            fn describe(s: Shape) -> String {
                match s {
                    Circle(r) -> "circle"
                    _         -> "other"
                }
            }
            print(describe(Rect(3.0, 4.0)))
        """, use_vm=True, capture_output=True)
        self.assertEqual(output, ["other"])

    def test_vm_match_nested_adt(self):
        """嵌套 ADT 模式匹配（通过显式嵌套 match）"""
        output = run_source("""
            type Inner { A(x: Int) | B(y: String) }
            type Outer { Wrap(i: Inner) | Unwrap }
            fn get(o: Outer) -> String {
                match o {
                    Wrap(inner) -> match inner {
                        A(x) -> int_to_str(x)
                        B(y) -> y
                    }
                    Unwrap -> "none"
                }
            }
            print(get(Wrap(A(42))))
            print(get(Wrap(B("hello"))))
            print(get(Unwrap))
        """, use_vm=True, capture_output=True)
        self.assertEqual(output, ["42", "hello", "none"])

    # ============================================================
    # For 循环 + 复杂循环体测试
    # ============================================================

    def test_vm_for_with_if(self):
        """for 循环体包含 if 表达式"""
        output = run_source("""
            let result = for x in [1, 2, 3, 4, 5] {
                if x % 2 == 0 then x * 10 else x
            }
            print(result)
        """, use_vm=True, capture_output=True)
        self.assertEqual(output, ["[1, 20, 3, 40, 5]"])

    def test_vm_for_with_match(self):
        """for 循环体包含 match 表达式"""
        output = run_source("""
            let items = [Some(1), None, Some(3)]
            let result = for opt in items {
                match opt {
                    Some(v) -> v * 10
                    None    -> 0
                }
            }
            print(result)
        """, use_vm=True, capture_output=True)
        self.assertEqual(output, ["[10, 0, 30]"])

    def test_vm_for_with_closure(self):
        """for 循环捕获外部闭包变量"""
        output = run_source("""
            let offset = 10
            let result = for x in [1, 2, 3] {
                x + offset
            }
            print(result)
        """, use_vm=True, capture_output=True)
        self.assertEqual(output, ["[11, 12, 13]"])

    def test_vm_for_accumulate(self):
        """for 循环中累加可变变量"""
        output = run_source("""
            mut sum = 0
            for x in [1, 2, 3, 4, 5] {
                sum = sum + x
                sum
            }
            print(sum)
        """, use_vm=True, capture_output=True)
        self.assertEqual(output, ["15"])

    # ============================================================
    # 栈压力测试
    # ============================================================

    def test_vm_deeply_nested_calls(self):
        """深层嵌套函数调用"""
        output = run_source("""
            fn f1(x: Int) -> Int { x + 1 }
            fn f2(x: Int) -> Int { f1(x) + 1 }
            fn f3(x: Int) -> Int { f2(x) + 1 }
            fn f4(x: Int) -> Int { f3(x) + 1 }
            fn f5(x: Int) -> Int { f4(x) + 1 }
            fn f6(x: Int) -> Int { f5(x) + 1 }
            fn f7(x: Int) -> Int { f6(x) + 1 }
            fn f8(x: Int) -> Int { f7(x) + 1 }
            fn f9(x: Int) -> Int { f8(x) + 1 }
            fn f10(x: Int) -> Int { f9(x) + 1 }
            print(f10(0))
        """, use_vm=True, capture_output=True)
        self.assertEqual(output, ["10"])

    def test_vm_many_locals(self):
        """函数包含大量局部变量"""
        output = run_source("""
            fn many_locals() -> Int {
                let a1 = 1
                let a2 = 2
                let a3 = 3
                let a4 = 4
                let a5 = 5
                let a6 = 6
                let a7 = 7
                let a8 = 8
                let a9 = 9
                let a10 = 10
                let a11 = 11
                let a12 = 12
                let a13 = 13
                let a14 = 14
                let a15 = 15
                let a16 = 16
                let a17 = 17
                let a18 = 18
                let a19 = 19
                let a20 = 20
                a1 + a2 + a3 + a4 + a5 + a6 + a7 + a8 + a9 + a10 +
                a11 + a12 + a13 + a14 + a15 + a16 + a17 + a18 + a19 + a20
            }
            print(many_locals())
        """, use_vm=True, capture_output=True)
        self.assertEqual(output, ["210"])

    def test_vm_recursion_depth(self):
        """递归函数到合理深度"""
        output = run_source("""
            fn count(n: Int) -> Int {
                if n <= 0 then 0
                else 1 + count(n - 1)
            }
            print(count(100))
        """, use_vm=True, capture_output=True)
        self.assertEqual(output, ["100"])

    # ============================================================
    # 类型安全测试
    # ============================================================

    def _vm_run_no_check(self, source):
        """用 VM 模式运行源码（不进行类型检查）"""
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        from nova.compiler import BytecodeCompiler
        from nova.vm import NovaVM
        compiler = BytecodeCompiler()
        bytecode = compiler.compile(ast)
        vm = NovaVM(bytecode)
        vm.run()
        return vm

    # --- TRY_UNWRAP type_name 检查 ---

    def test_vm_try_unwrap_custom_adt_some_variant_error(self):
        """VM: 自定义 ADT 有 Some variant 但 type_name 不是 Option，用 ? 操作符应报错"""
        from nova.compiler import Bytecode, Op
        from nova.vm import NovaVM, NovaADTValue
        bytecode = Bytecode()
        # 压入一个自定义 ADT 值（type_name="MyOption", variant_name="Some"）
        custom_some = NovaADTValue("MyOption", "Some", [42], ["value"])
        bytecode.constants.append(custom_some)
        bytecode.emit_op(Op.LOAD_CONST, 0)
        bytecode.emit_op(Op.TRY_UNWRAP)
        bytecode.emit_op(Op.HALT)
        vm = NovaVM(bytecode)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("? 操作符只能在 Option 或 Result 类型上使用", str(ctx.exception))

    def test_vm_try_unwrap_custom_adt_err_variant_error(self):
        """VM: 自定义 ADT 有 Err variant 但 type_name 不是 Result，用 ? 操作符应报错"""
        from nova.compiler import Bytecode, Op
        from nova.vm import NovaVM, NovaADTValue
        bytecode = Bytecode()
        # 压入一个自定义 ADT 值（type_name="MyResult", variant_name="Err"）
        custom_err = NovaADTValue("MyResult", "Err", ["oops"], ["error"])
        bytecode.constants.append(custom_err)
        bytecode.emit_op(Op.LOAD_CONST, 0)
        bytecode.emit_op(Op.TRY_UNWRAP)
        bytecode.emit_op(Op.HALT)
        vm = NovaVM(bytecode)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("? 操作符只能在 Option 或 Result 类型上使用", str(ctx.exception))

    def test_vm_try_unwrap_option_some_ok(self):
        """VM: Option.Some 正常解包（回归测试）"""
        vm = self._vm_run_no_check("""
            fn f() -> Int {
                let x = Some(42)?
                x
            }
            let result = f()
        """)
        self.assertEqual(vm.get_global("result"), 42)

    def test_vm_try_unwrap_result_ok_ok(self):
        """VM: Result.Ok 正常解包（回归测试）"""
        vm = self._vm_run_no_check("""
            type Result[T, E] { Ok(T) Err(E) }
            fn f() -> Int {
                let x = Ok(99)?
                x
            }
            let result = f()
        """)
        self.assertEqual(vm.get_global("result"), 99)

    # --- 算术运算 bool 检查 ---

    def test_vm_arithmetic_bool_add_error(self):
        """VM: true + 1 应报错"""
        from nova.errors import RuntimeError_
        with self.assertRaises(RuntimeError_) as ctx:
            self._vm_run_no_check("let x = true + 1")
        self.assertIn("算术运算 '+' 的操作数不能是 Bool 类型", str(ctx.exception))

    def test_vm_arithmetic_bool_mul_error(self):
        """VM: false * 5 应报错"""
        from nova.errors import RuntimeError_
        with self.assertRaises(RuntimeError_) as ctx:
            self._vm_run_no_check("let x = false * 5")
        self.assertIn("算术运算 '*' 的操作数不能是 Bool 类型", str(ctx.exception))

    def test_vm_arithmetic_bool_div_error(self):
        """VM: true / 2 应报错"""
        from nova.errors import RuntimeError_
        with self.assertRaises(RuntimeError_) as ctx:
            self._vm_run_no_check("let x = true / 2")
        self.assertIn("算术运算 '/' 的操作数不能是 Bool 类型", str(ctx.exception))

    def test_vm_arithmetic_bool_neg_error(self):
        """VM: -true（一元负）应报错"""
        from nova.errors import RuntimeError_
        with self.assertRaises(RuntimeError_) as ctx:
            self._vm_run_no_check("let x = -true")
        self.assertIn("算术运算 '-' 的操作数不能是 Bool 类型", str(ctx.exception))

    def test_vm_arithmetic_int_still_works(self):
        """VM: 正常 Int 运算仍然正确（回归测试）"""
        vm = self._vm_run_no_check("""
            let a = 10 + 5
            let b = 10 - 3
            let c = 4 * 3
            let d = 20 / 4
            let e = 10 % 3
            let f = -7
        """)
        self.assertEqual(vm.get_global("a"), 15)
        self.assertEqual(vm.get_global("b"), 7)
        self.assertEqual(vm.get_global("c"), 12)
        self.assertEqual(vm.get_global("d"), 5)
        self.assertEqual(vm.get_global("e"), 1)
        self.assertEqual(vm.get_global("f"), -7)

    # ============================================================
    # 边界情况（曾导致崩溃）
    # ============================================================

    def test_vm_loop_end_empty_stack(self):
        """LOOP_END 在空栈时不应崩溃，应抛出可控错误"""
        from nova.compiler import Bytecode, Op
        from nova.vm import NovaVM
        bytecode = Bytecode()
        bytecode.emit_op(Op.LOOP_END, 0)
        bytecode.emit_op(Op.HALT)
        vm = NovaVM(bytecode)
        with self.assertRaises(RuntimeError_):
            vm.run()

    def test_vm_match_constructor_no_subject(self):
        """MATCH_CONSTRUCTOR 在栈空时不应崩溃，应抛出可控错误"""
        from nova.compiler import Bytecode, Op
        from nova.vm import NovaVM
        bytecode = Bytecode()
        bytecode.emit_op(Op.MATCH_CONSTRUCTOR, "Shape", "Circle", 1, 2)
        bytecode.emit_op(Op.HALT)
        vm = NovaVM(bytecode)
        with self.assertRaises(RuntimeError_):
            vm.run()

    def test_vm_closure_too_many_args(self):
        """闭包调用时实参数量多于形参应抛出错误，而非静默丢弃多余参数"""
        from nova.compiler import Bytecode, Op, FunctionBlock
        from nova.vm import NovaVM, NovaClosure
        bytecode = Bytecode()

        # 构造一个接受 1 个参数的函数（直接返回该参数）
        from nova.compiler import Instruction
        func_code = [
            Instruction(Op.LOAD_VAR, ("x",)),
            Instruction(Op.RETURN, ()),
        ]
        func_block = FunctionBlock("test_fn", 1, func_code, [], param_names=["x"])
        bytecode.functions["test_fn"] = func_block

        # 主程序：创建闭包，然后用 3 个参数调用（应报错）
        bytecode.emit_op(Op.CLOSURE, "test_fn", 1, "test_fn")
        bytecode.emit_op(Op.CONST_INT, 10)
        bytecode.emit_op(Op.CONST_INT, 20)
        bytecode.emit_op(Op.CONST_INT, 30)
        bytecode.emit_op(Op.CALL, 3)
        bytecode.emit_op(Op.HALT)

        vm = NovaVM(bytecode)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("期望 1 个参数，但传入了 3 个", str(ctx.exception))

    def test_vm_closure_partial_application(self):
        """VM 闭包部分应用：参数不足时返回捕获已提供参数的新闭包"""
        vm = self._vm_run("""
            fn add(x: Int, y: Int) -> Int { x + y }
            let add3 = add(3)
            let result = add3(7)
        """)
        self.assertEqual(vm.get_global("result"), 10)  # 3 + 7 = 10

    def test_vm_closure_partial_application_chain(self):
        """VM 闭包链式部分应用：三参数函数链式部分应用"""
        vm = self._vm_run("""
            fn sum3(a: Int, b: Int, c: Int) -> Int { a + b + c }
            let s1 = sum3(1)
            let s2 = s1(2)
            let result = s2(3)
        """)
        self.assertEqual(vm.get_global("result"), 6)  # 1 + 2 + 3 = 6

    def test_vm_closure_pipe_call_too_many_args(self):
        """管道调用闭包时实参数量过多也应抛出错误"""
        from nova.compiler import Bytecode, Op, FunctionBlock
        from nova.vm import NovaVM
        bytecode = Bytecode()

        # 构造一个接受 1 个参数的函数
        from nova.compiler import Instruction
        func_code = [
            Instruction(Op.LOAD_VAR, ("x",)),
            Instruction(Op.RETURN, ()),
        ]
        func_block = FunctionBlock("pipe_fn", 1, func_code, [], param_names=["x"])
        bytecode.functions["pipe_fn"] = func_block

        # 主程序：管道值 + 2 个额外参数 + 闭包，共 3 个实参调用 1 形参函数（应报错）
        bytecode.emit_op(Op.CONST_INT, 100)   # pipe value
        bytecode.emit_op(Op.CONST_INT, 10)    # extra arg 1
        bytecode.emit_op(Op.CONST_INT, 20)    # extra arg 2
        bytecode.emit_op(Op.CLOSURE, "pipe_fn", 1, "pipe_fn")
        bytecode.emit_op(Op.PIPE_CALL, 2)     # 2 extra args + pipe value = 3 args
        bytecode.emit_op(Op.HALT)

        vm = NovaVM(bytecode)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("期望 1 个参数，但传入了 3 个", str(ctx.exception))

    # ---- 问题1：内置函数超额参数检查 ----

    def test_vm_builtin_excess_args(self):
        """内置函数传入过多参数应报错"""
        # 使用 pipe_call 路径测试，因为直接 call_builtin 也走 _call_fn
        from nova.compiler import Bytecode, Instruction, Op
        bytecode = Bytecode()
        bytecode.constants = []
        bytecode.emit_op(Op.CONST_INT, 42)
        bytecode.emit_op(Op.CONST_INT, 43)
        bytecode.emit_op(Op.CALL_BUILTIN, "abs", 2)  # abs 只接受 1 个参数，传 2 个应报错
        bytecode.emit_op(Op.HALT)

        from nova.vm import NovaVM
        vm = NovaVM(bytecode)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("期望 1 个参数，得到 2 个", str(ctx.exception))

    def test_vm_partial_builtin_excess_args(self):
        """部分应用的内置函数传入过多参数应报错"""
        from nova.compiler import Bytecode, Instruction, Op
        bytecode = Bytecode()
        bytecode.constants = []
        # pow 的 arity 是 2，先传 1 个得到部分应用，再传 2 个（总共 3 个）应报错
        bytecode.emit_op(Op.CONST_FLOAT, 2.0)
        bytecode.emit_op(Op.CALL_BUILTIN, "pow", 1)  # 部分应用：pow(2.0)
        bytecode.emit_op(Op.CONST_FLOAT, 3.0)
        bytecode.emit_op(Op.CONST_FLOAT, 4.0)
        bytecode.emit_op(Op.CALL, 2)  # 再传 2 个参数，总共 3 个，应报错
        bytecode.emit_op(Op.HALT)

        from nova.vm import NovaVM
        vm = NovaVM(bytecode)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("期望 2 个参数，得到 3 个", str(ctx.exception))

    # ---- 问题2：STORE_VAR 函数体内静默创建全局 ----

    def test_vm_let_binding_is_local_in_function(self):
        """函数中的 let 绑定应该是局部变量，不污染全局作用域"""
        vm = self._vm_run("""
            fn test() -> Int {
                let x = 42
                x
            }
            let result = test()
        """)
        self.assertEqual(vm.get_global("result"), 42)
        # x 应该是函数局部变量，不应该出现在全局作用域中
        self.assertIsNone(vm.get_global("x"))

    def test_vm_function_cannot_modify_global_via_undefined(self):
        """函数中不能通过 STORE_VAR 隐式创建全局变量"""
        # 通过直接构造字节码测试：函数中对不存在的变量执行 STORE_VAR
        # （在类型检查通过的代码中不会出现这种情况，但 VM 应该正确处理）
        from nova.compiler import Bytecode, FunctionBlock, Instruction, Op
        bytecode = Bytecode()
        bytecode.constants = []

        # 函数体：let x = 42（STORE_VAR x, False）
        fn_code = [
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.STORE_VAR, "x", False),
            Instruction(Op.LOAD_VAR, "x"),
            Instruction(Op.RETURN),
        ]
        fn_block = FunctionBlock("test_fn", 0, fn_code, [], ["x"])
        bytecode.functions["test_fn"] = fn_block

        # 主代码：调用函数
        bytecode.emit_op(Op.CLOSURE, "test_fn", 0, "test_fn")
        bytecode.emit_op(Op.CALL, 0)
        bytecode.emit_op(Op.STORE_VAR, "result", False)
        bytecode.emit_op(Op.HALT)

        from nova.vm import NovaVM
        vm = NovaVM(bytecode)
        vm.run()

        # result 是全局的（顶层 let）
        self.assertEqual(vm.get_global("result"), 42)
        # x 应该是函数局部的，不应该出现在全局
        self.assertIsNone(vm.get_global("x"))

    # ---- 问题3：MATCH_BIND 失败分支绑定残留 ----

    def test_vm_match_bind_scope_isolation(self):
        """模式匹配中失败分支的绑定变量不应残留到后续分支"""
        # 通过构造字节码验证：第一个 arm 绑定变量后 guard 失败，
        # 第二个 arm 中不应能读到第一个 arm 的绑定
        from nova.compiler import Bytecode, FunctionBlock, Instruction, Op
        bytecode = Bytecode()
        bytecode.constants = []

        # 构造一个 match 表达式，有两个 arm
        # match 42 {
        #   n if n > 100 -> n * 2  // arm1: 匹配但 guard 失败，绑定了 n
        #   m -> m + 1             // arm2: 应该绑定 m，而不是读到 n
        # }
        # 结果应该是 43（42 + 1），而不是 84（42 * 2）

        # 函数体中执行 match
        fn_code = [
            # subject = 42                            # 0
            Instruction(Op.CONST_INT, 42),          # 0
            Instruction(Op.MATCH_START, 2),         # 1

            # --- Arm 1: n if n > 100 -> n * 2 ---
            Instruction(Op.MATCH_ARM_START,),       # 2
            Instruction(Op.DUP,),                   # 3
            # 模式测试：标识符 n 总是匹配（无测试指令）
            # 绑定 n
            Instruction(Op.MATCH_BIND, "n"),        # 4
            # guard: n > 100
            Instruction(Op.LOAD_VAR, "n"),          # 5
            Instruction(Op.CONST_INT, 100),         # 6
            Instruction(Op.GT,),                    # 7
            # guard 失败跳 arm2_start
            Instruction(Op.JUMP_IF_FALSE, 14),      # 8  跳到 arm2 的 MATCH_ARM_START
            # 弹出 subject
            Instruction(Op.POP,),                   # 9
            # body: n * 2
            Instruction(Op.LOAD_VAR, "n"),          # 10
            Instruction(Op.CONST_INT, 2),           # 11
            Instruction(Op.MUL,),                   # 12
            # 跳到 match_end
            Instruction(Op.JUMP, 22),               # 13

            # --- Arm 2: m -> m + 1 ---
            Instruction(Op.MATCH_ARM_START,),       # 14
            Instruction(Op.DUP,),                   # 15
            # 模式测试：标识符 m 总是匹配
            # 绑定 m
            Instruction(Op.MATCH_BIND, "m"),        # 16
            # 弹出 subject
            Instruction(Op.POP,),                   # 17
            # body: m + 1
            Instruction(Op.LOAD_VAR, "m"),          # 18
            Instruction(Op.CONST_INT, 1),           # 19
            Instruction(Op.ADD,),                   # 20
            # 跳到 match_end
            Instruction(Op.JUMP, 22),               # 21

            # match_end
            Instruction(Op.MATCH_END,),             # 22
            Instruction(Op.RETURN,),                # 23
        ]
        fn_block = FunctionBlock("test_match", 0, fn_code, [], [])
        bytecode.functions["test_match"] = fn_block

        # 主代码
        bytecode.emit_op(Op.CLOSURE, "test_match", 0, "test_match")
        bytecode.emit_op(Op.CALL, 0)
        bytecode.emit_op(Op.STORE_VAR, "result", False)
        bytecode.emit_op(Op.HALT)

        from nova.vm import NovaVM
        vm = NovaVM(bytecode)
        vm.run()

        # 应该是 42 + 1 = 43，而不是 42 * 2 = 84
        self.assertEqual(vm.get_global("result"), 43)

    def test_vm_match_end_cleans_bindings(self):
        """match 结束后，绑定变量不应残留在函数局部作用域中"""
        from nova.compiler import Bytecode, FunctionBlock, Instruction, Op
        bytecode = Bytecode()
        bytecode.constants = []

        # 函数中执行 match，然后尝试访问 match 中绑定的变量
        # match 42 { n -> n + 1 }
        # 之后访问 n 应该报错（因为 n 是 match 局部的）
        fn_code = [
            # subject = 42
            Instruction(Op.CONST_INT, 42),          # 0
            Instruction(Op.MATCH_START, 1),         # 1

            # Arm 1: n -> n + 1
            Instruction(Op.MATCH_ARM_START,),       # 2
            Instruction(Op.DUP,),                   # 3
            Instruction(Op.MATCH_BIND, "n"),        # 4
            Instruction(Op.POP,),                   # 5  弹出 subject
            Instruction(Op.LOAD_VAR, "n"),          # 6
            Instruction(Op.CONST_INT, 1),           # 7
            Instruction(Op.ADD,),                   # 8
            Instruction(Op.JUMP, 10),               # 9  跳到 MATCH_END

            # match_end
            Instruction(Op.MATCH_END,),             # 10
            # 把结果存到 result
            Instruction(Op.STORE_VAR, "result", False),  # 11
            # 尝试访问 n：应该是未定义的（因为 match 结束后清理了）
            Instruction(Op.LOAD_VAR, "n"),          # 12
            Instruction(Op.RETURN,),                # 13
        ]
        fn_block = FunctionBlock("test_match_scope", 0, fn_code, [], [])
        bytecode.functions["test_match_scope"] = fn_block

        # 主代码
        bytecode.emit_op(Op.CLOSURE, "test_match_scope", 0, "test_match_scope")
        bytecode.emit_op(Op.CALL, 0)
        bytecode.emit_op(Op.STORE_VAR, "final_result", False)
        bytecode.emit_op(Op.HALT)

        from nova.vm import NovaVM
        vm = NovaVM(bytecode)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("未定义的变量 'n'", str(ctx.exception))

    # ---- 局部变量可变性检查 ----

    def test_vm_let_binding_immutable_assign_error(self):
        """函数内 let 绑定的不可变变量，再次赋值应报错"""
        # 使用字节码直接构造，绕过类型检查（因为类型检查可能已阻止此操作）
        from nova.compiler import Bytecode, FunctionBlock, Instruction, Op
        bytecode = Bytecode()
        bytecode.constants = []

        # 函数体：let x = 10; x = 20; return x
        fn_code = [
            Instruction(Op.CONST_INT, 10),
            Instruction(Op.STORE_VAR, "x", False),   # let x = 10 (不可变)
            Instruction(Op.CONST_INT, 20),
            Instruction(Op.STORE_VAR, "x", True, True),  # x = 20 (赋值操作)
            Instruction(Op.LOAD_VAR, "x"),
            Instruction(Op.RETURN),
        ]
        fn_block = FunctionBlock("test_fn", 0, fn_code, [], ["x"])
        bytecode.functions["test_fn"] = fn_block

        # 主代码：调用函数
        bytecode.emit_op(Op.CLOSURE, "test_fn", 0, "test_fn")
        bytecode.emit_op(Op.CALL, 0)
        bytecode.emit_op(Op.STORE_VAR, "result", False)
        bytecode.emit_op(Op.HALT)

        from nova.vm import NovaVM
        vm = NovaVM(bytecode)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("Cannot assign to immutable variable 'x'", str(ctx.exception))

    # --- 顶层 TRY_UNWRAP 保护 ---

    def test_vm_top_level_try_unwrap_none_raises(self):
        """VM: 顶层使用 ? (None) 应抛出 RuntimeError_ 而非静默退出"""
        from nova.compiler import Bytecode, Op
        from nova.vm import NovaVM, NovaADTValue
        bytecode = Bytecode()
        none_val = NovaADTValue("Option", "None", [], [])
        bytecode.constants.append(none_val)
        bytecode.emit_op(Op.LOAD_CONST, 0)
        bytecode.emit_op(Op.TRY_UNWRAP)
        bytecode.emit_op(Op.HALT)
        vm = NovaVM(bytecode)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("? 操作符不能在顶层使用", str(ctx.exception))

    def test_vm_top_level_try_unwrap_err_raises(self):
        """VM: 顶层使用 ? (Err) 应抛出 RuntimeError_ 而非静默退出"""
        from nova.compiler import Bytecode, Op
        from nova.vm import NovaVM, NovaADTValue
        bytecode = Bytecode()
        err_val = NovaADTValue("Result", "Err", ["oops"], ["error"])
        bytecode.constants.append(err_val)
        bytecode.emit_op(Op.LOAD_CONST, 0)
        bytecode.emit_op(Op.TRY_UNWRAP)
        bytecode.emit_op(Op.HALT)
        vm = NovaVM(bytecode)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("? 操作符不能在顶层使用", str(ctx.exception))

    # --- FIELD_ACCESS 索引越界 ---

    def test_vm_field_access_tuple_index_out_of_bounds(self):
        """VM: 元组字段索引越界应抛出 RuntimeError_ 而非 IndexError"""
        vm = self._vm_run_no_check("let t = (1, 2, 3)")
        # 手动构造越界访问
        from nova.compiler import Bytecode, Op
        from nova.vm import NovaVM
        bytecode = Bytecode()
        bytecode.constants.append((1, 2, 3))
        bytecode.emit_op(Op.LOAD_CONST, 0)
        bytecode.emit_op(Op.FIELD_ACCESS, 5)
        bytecode.emit_op(Op.HALT)
        vm = NovaVM(bytecode)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("元组索引", str(ctx.exception))
        self.assertIn("越界", str(ctx.exception))

    def test_vm_field_access_adt_index_out_of_bounds(self):
        """VM: ADT 字段索引越界应抛出 RuntimeError_ 而非 IndexError"""
        from nova.compiler import Bytecode, Op
        from nova.vm import NovaVM, NovaADTValue
        bytecode = Bytecode()
        adt_val = NovaADTValue("MyType", "Foo", [10, 20], ["a", "b"])
        bytecode.constants.append(adt_val)
        bytecode.emit_op(Op.LOAD_CONST, 0)
        bytecode.emit_op(Op.FIELD_ACCESS, 5)
        bytecode.emit_op(Op.HALT)
        vm = NovaVM(bytecode)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("ADT 字段索引", str(ctx.exception))
        self.assertIn("越界", str(ctx.exception))

    # --- BUILD_MAP 不可哈希键 ---

    def test_vm_build_map_unhashable_key(self):
        """VM: BUILD_MAP 不可哈希键应抛出 RuntimeError_ 而非 TypeError"""
        from nova.compiler import Bytecode, Op
        from nova.vm import NovaVM
        bytecode = Bytecode()
        bytecode.constants.append([1, 2, 3])  # 列表是不可哈希的
        bytecode.constants.append(42)
        bytecode.emit_op(Op.LOAD_CONST, 0)  # key = [1,2,3]
        bytecode.emit_op(Op.LOAD_CONST, 1)  # val = 42
        bytecode.emit_op(Op.BUILD_MAP, 1)
        bytecode.emit_op(Op.HALT)
        vm = NovaVM(bytecode)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("可哈希", str(ctx.exception))

    def test_vm_mut_binding_assign_works(self):
        """函数内 mut 绑定的可变变量，再次赋值应正常工作"""
        from nova.compiler import Bytecode, FunctionBlock, Instruction, Op
        bytecode = Bytecode()
        bytecode.constants = []

        # 函数体：mut x = 10; x = 20; return x
        fn_code = [
            Instruction(Op.CONST_INT, 10),
            Instruction(Op.STORE_VAR, "x", True),    # mut x = 10 (可变)
            Instruction(Op.CONST_INT, 20),
            Instruction(Op.STORE_VAR, "x", True, True),  # x = 20 (赋值操作)
            Instruction(Op.LOAD_VAR, "x"),
            Instruction(Op.RETURN),
        ]
        fn_block = FunctionBlock("test_fn", 0, fn_code, [], ["x"])
        bytecode.functions["test_fn"] = fn_block

        bytecode.emit_op(Op.CLOSURE, "test_fn", 0, "test_fn")
        bytecode.emit_op(Op.CALL, 0)
        bytecode.emit_op(Op.STORE_VAR, "result", False)
        bytecode.emit_op(Op.HALT)

        from nova.vm import NovaVM
        vm = NovaVM(bytecode)
        vm.run()
        self.assertEqual(vm.get_global("result"), 20)

    def test_vm_function_param_immutable_assign_error(self):
        """函数参数默认不可变，对参数赋值应报错"""
        from nova.compiler import Bytecode, FunctionBlock, Instruction, Op
        bytecode = Bytecode()
        bytecode.constants = []

        # 函数体：x = x + 1 (尝试修改参数 x)
        fn_code = [
            Instruction(Op.LOAD_VAR, "x"),
            Instruction(Op.CONST_INT, 1),
            Instruction(Op.ADD),
            Instruction(Op.STORE_VAR, "x", True, True),  # x = x + 1 (赋值操作)
            Instruction(Op.LOAD_VAR, "x"),
            Instruction(Op.RETURN),
        ]
        fn_block = FunctionBlock("test_fn", 1, fn_code, [], ["x"])
        bytecode.functions["test_fn"] = fn_block

        bytecode.emit_op(Op.CLOSURE, "test_fn", 1, "test_fn")
        bytecode.emit_op(Op.CONST_INT, 5)
        bytecode.emit_op(Op.CALL, 1)
        bytecode.emit_op(Op.STORE_VAR, "result", False)
        bytecode.emit_op(Op.HALT)

        from nova.vm import NovaVM
        vm = NovaVM(bytecode)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("Cannot assign to immutable variable 'x'", str(ctx.exception))

    def test_vm_closure_captured_mutable_assign_works(self):
        """闭包捕获的可变变量，在闭包内赋值应正常工作"""
        from nova.compiler import Bytecode, FunctionBlock, Instruction, Op
        bytecode = Bytecode()
        bytecode.constants = []

        # 内层函数（闭包）：counter = counter + 1; return counter
        inner_code = [
            Instruction(Op.LOAD_VAR, "counter"),
            Instruction(Op.CONST_INT, 1),
            Instruction(Op.ADD),
            Instruction(Op.STORE_VAR, "counter", True, True),  # counter = counter + 1
            Instruction(Op.LOAD_VAR, "counter"),
            Instruction(Op.RETURN),
        ]
        inner_block = FunctionBlock("increment", 0, inner_code, [], ["counter"])
        bytecode.functions["increment"] = inner_block

        # 外层函数：mut counter = 0; let f = fn() { counter = counter + 1; counter }; f()
        outer_code = [
            Instruction(Op.CONST_INT, 0),
            Instruction(Op.STORE_VAR, "counter", True),   # mut counter = 0
            Instruction(Op.CLOSURE, "increment", 0, "increment"),
            Instruction(Op.STORE_VAR, "f", False),        # let f = closure
            Instruction(Op.LOAD_VAR, "f"),
            Instruction(Op.CALL, 0),
            Instruction(Op.RETURN),
        ]
        outer_block = FunctionBlock("outer", 0, outer_code, [], ["counter", "f"])
        bytecode.functions["outer"] = outer_block

        bytecode.emit_op(Op.CLOSURE, "outer", 0, "outer")
        bytecode.emit_op(Op.CALL, 0)
        bytecode.emit_op(Op.STORE_VAR, "result", False)
        bytecode.emit_op(Op.HALT)

        from nova.vm import NovaVM
        vm = NovaVM(bytecode)
        vm.run()
        self.assertEqual(vm.get_global("result"), 1)

    def test_vm_closure_captured_immutable_assign_error(self):
        """闭包捕获的不可变变量，在闭包内赋值应报错"""
        from nova.compiler import Bytecode, FunctionBlock, Instruction, Op
        bytecode = Bytecode()
        bytecode.constants = []

        # 内层函数（闭包）：尝试修改捕获的不可变变量 x
        inner_code = [
            Instruction(Op.CONST_INT, 99),
            Instruction(Op.STORE_VAR, "x", True, True),  # x = 99 (赋值操作)
            Instruction(Op.LOAD_VAR, "x"),
            Instruction(Op.RETURN),
        ]
        inner_block = FunctionBlock("inner_fn", 0, inner_code, [], ["x"])
        bytecode.functions["inner_fn"] = inner_block

        # 外层函数：let x = 10; let f = closure; f()
        outer_code = [
            Instruction(Op.CONST_INT, 10),
            Instruction(Op.STORE_VAR, "x", False),       # let x = 10 (不可变)
            Instruction(Op.CLOSURE, "inner_fn", 0, "inner_fn"),
            Instruction(Op.STORE_VAR, "f", False),
            Instruction(Op.LOAD_VAR, "f"),
            Instruction(Op.CALL, 0),
            Instruction(Op.RETURN),
        ]
        outer_block = FunctionBlock("outer", 0, outer_code, [], ["x", "f"])
        bytecode.functions["outer"] = outer_block

        bytecode.emit_op(Op.CLOSURE, "outer", 0, "outer")
        bytecode.emit_op(Op.CALL, 0)
        bytecode.emit_op(Op.STORE_VAR, "result", False)
        bytecode.emit_op(Op.HALT)

        from nova.vm import NovaVM
        vm = NovaVM(bytecode)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("Cannot assign to immutable variable 'x'", str(ctx.exception))

    def test_vm_match_non_exhaustive_raises_error(self):
        """非穷尽模式匹配在 VM 中应抛出 MatchFailure 错误"""
        from nova.errors import MatchFailure
        with self.assertRaises(MatchFailure):
            self._vm_run("""
                let x = match 3 {
                    1 -> "one"
                    2 -> "two"
                }
            """)

    def test_vm_match_wildcard_does_not_fail(self):
        """带通配符的模式匹配不应触发 MatchFailure"""
        vm = self._vm_run("""
            let x = match 42 {
                1 -> "one"
                _ -> "other"
            }
        """)
        self.assertEqual(vm.get_global("x"), "other")

    def test_vm_list_comprehension_filter_with_nested_loop(self):
        """带过滤条件的列表推导式在嵌套循环中应正确处理 break/continue"""
        vm = self._vm_run("""
            let result = for i <- 1..3 {
                let inner = [x * 2 for x <- 1..4 if x > 2]
                inner
            }
            let x = result[1]
        """)
        self.assertEqual(vm.get_global("x"), [6, 8])

    def test_vm_list_comprehension_filter_basic(self):
        """带过滤条件的列表推导式基本功能测试"""
        vm = self._vm_run("""
            let evens = [x for x <- 1..10 if x % 2 == 0]
        """)
        self.assertEqual(vm.get_global("evens"), [2, 4, 6, 8, 10])


# ============================================================
# 前向引用测试（P1 Bug #9）
# ============================================================

class TestForwardReferences(unittest.TestCase):
    """函数前向引用和相互递归测试"""

    # ---- 求值器测试 ----

    def test_evaluator_forward_reference(self):
        """函数 a 调用函数 b，但 b 定义在 a 之后"""
        ev = eval_source("""
            fn a(x: Int) -> Int { b(x) + 1 }
            fn b(x: Int) -> Int { x * 2 }
            let result = a(5)
        """, check_types=False)
        self.assertEqual(ev.env.lookup("result"), 11)

    def test_evaluator_mutual_recursion(self):
        """相互递归：even/odd 函数"""
        ev = eval_source("""
            fn even(n: Int) -> Bool {
              if n == 0 then true
              else odd(n - 1)
            }
            fn odd(n: Int) -> Bool {
              if n == 0 then false
              else even(n - 1)
            }
            let r1 = even(4)
            let r2 = odd(5)
            let r3 = even(5)
            let r4 = odd(4)
        """, check_types=False)
        self.assertTrue(ev.env.lookup("r1"))
        self.assertTrue(ev.env.lookup("r2"))
        self.assertFalse(ev.env.lookup("r3"))
        self.assertFalse(ev.env.lookup("r4"))

    def test_evaluator_three_way_forward(self):
        """三个函数的链式前向引用：a -> b -> c"""
        ev = eval_source("""
            fn a(x: Int) -> Int { b(x) + 1 }
            fn b(x: Int) -> Int { c(x) * 2 }
            fn c(x: Int) -> Int { x - 3 }
            let result = a(10)
        """, check_types=False)
        # a(10) = b(10) + 1 = (c(10) * 2) + 1 = ((10 - 3) * 2) + 1 = 7 * 2 + 1 = 15
        self.assertEqual(ev.env.lookup("result"), 15)

    # ---- 类型检查器测试 ----

    def test_type_checker_forward_reference(self):
        """类型检查器应支持函数前向引用"""
        checker = type_check("""
            fn a(x: Int) -> Int { b(x) + 1 }
            fn b(x: Int) -> Int { x * 2 }
        """)
        ty_a = checker.env.lookup("a")
        ty_b = checker.env.lookup("b")
        self.assertIsNotNone(ty_a)
        self.assertIsNotNone(ty_b)

    def test_type_checker_mutual_recursion(self):
        """类型检查器应支持相互递归"""
        checker = type_check("""
            fn even(n: Int) -> Bool {
              if n == 0 then true
              else odd(n - 1)
            }
            fn odd(n: Int) -> Bool {
              if n == 0 then false
              else even(n - 1)
            }
        """)
        ty_even = checker.env.lookup("even")
        ty_odd = checker.env.lookup("odd")
        self.assertIsNotNone(ty_even)
        self.assertIsNotNone(ty_odd)

    def test_type_checker_forward_with_type_mismatch(self):
        """前向引用函数但类型不匹配应报错"""
        from nova.errors import TypeCheckError
        with self.assertRaises(TypeCheckError):
            type_check("""
                fn a(x: Int) -> Int { b(x) + 1 }
                fn b(x: String) -> String { x }
            """)

    # ---- VM 测试 ----

    def _vm_run_no_check(self, source):
        """用 VM 模式运行源码（不进行类型检查）"""
        from nova.lexer import Lexer
        from nova.parser import Parser
        from nova.compiler import BytecodeCompiler
        from nova.vm import NovaVM
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        compiler = BytecodeCompiler()
        bytecode = compiler.compile(ast)
        vm = NovaVM(bytecode)
        vm.run()
        return vm

    def test_vm_forward_reference(self):
        """VM 应支持函数前向引用"""
        vm = self._vm_run_no_check("""
            fn a(x: Int) -> Int { b(x) + 1 }
            fn b(x: Int) -> Int { x * 2 }
            let result = a(5)
        """)
        self.assertEqual(vm.get_global("result"), 11)

    def test_vm_mutual_recursion(self):
        """VM 应支持相互递归"""
        vm = self._vm_run_no_check("""
            fn even(n: Int) -> Bool {
              if n == 0 then true
              else odd(n - 1)
            }
            fn odd(n: Int) -> Bool {
              if n == 0 then false
              else even(n - 1)
            }
            fn main() -> Unit {
              print("done")
            }
        """)
        # 通过 main 触发执行，然后检查全局
        # 直接调用 even/odd 通过全局变量
        # 这里用 main 中的 print 确认程序能运行
        self.assertIn("done", vm.get_output())

    def test_vm_mutual_recursion_result(self):
        """VM 中相互递归的 even/odd 返回正确结果"""
        vm = self._vm_run_no_check("""
            fn even(n: Int) -> Bool {
              if n == 0 then true
              else odd(n - 1)
            }
            fn odd(n: Int) -> Bool {
              if n == 0 then false
              else even(n - 1)
            }
            let r1 = even(4)
            let r2 = odd(5)
            let r3 = even(5)
            let r4 = odd(4)
        """)
        self.assertTrue(vm.get_global("r1"))
        self.assertTrue(vm.get_global("r2"))
        self.assertFalse(vm.get_global("r3"))
        self.assertFalse(vm.get_global("r4"))

    # ---- 类型检查 + VM 集成测试 ----

    def test_forward_ref_with_type_check(self):
        """前向引用与类型检查一起工作"""
        from nova.lexer import Lexer
        from nova.parser import Parser
        from nova.type_checker import TypeChecker
        from nova.compiler import BytecodeCompiler
        from nova.vm import NovaVM
        source = """
            fn a(x: Int) -> Int { b(x) + 1 }
            fn b(x: Int) -> Int { x * 2 }
            let result = a(5)
        """
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        TypeChecker().check_program(ast)
        compiler = BytecodeCompiler()
        bytecode = compiler.compile(ast)
        vm = NovaVM(bytecode)
        vm.run()
        self.assertEqual(vm.get_global("result"), 11)

    def test_mutual_recursion_with_type_check(self):
        """相互递归与类型检查一起工作"""
        from nova.lexer import Lexer
        from nova.parser import Parser
        from nova.type_checker import TypeChecker
        from nova.compiler import BytecodeCompiler
        from nova.vm import NovaVM
        source = """
            fn even(n: Int) -> Bool {
              if n == 0 then true
              else odd(n - 1)
            }
            fn odd(n: Int) -> Bool {
              if n == 0 then false
              else even(n - 1)
            }
            let r = even(10)
        """
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        TypeChecker().check_program(ast)
        compiler = BytecodeCompiler()
        bytecode = compiler.compile(ast)
        vm = NovaVM(bytecode)
        vm.run()
        self.assertTrue(vm.get_global("r"))


# ============================================================
# 重复定义检测测试（P2 Bug #11）
# ============================================================

class TestDuplicateDefinitions(unittest.TestCase):
    """重复函数/类型定义检测测试"""

    def test_duplicate_function(self):
        """重复定义函数应报错"""
        from nova.errors import TypeCheckError
        with self.assertRaises(TypeCheckError) as ctx:
            type_check("""
                fn foo(x: Int) -> Int { x + 1 }
                fn foo(x: Int) -> Int { x + 2 }
            """)
        self.assertIn("重复定义", str(ctx.exception))

    def test_duplicate_function_different_sig(self):
        """即使签名不同，重复函数名也应报错"""
        from nova.errors import TypeCheckError
        with self.assertRaises(TypeCheckError) as ctx:
            type_check("""
                fn bar(x: Int) -> Int { x }
                fn bar(x: Int, y: Int) -> Int { x + y }
            """)
        self.assertIn("重复定义", str(ctx.exception))

    def test_duplicate_adt_definition(self):
        """重复定义 ADT 类型应报错"""
        from nova.errors import TypeCheckError
        with self.assertRaises(TypeCheckError) as ctx:
            type_check("""
                type Color { Red | Green | Blue }
                type Color { Cyan | Magenta | Yellow }
            """)
        self.assertIn("重复定义", str(ctx.exception))

    def test_no_duplicate_error_for_builtin_shadow(self):
        """用户定义与内置同名的类型/函数不应误报重复"""
        # 用户可以重新定义 Option（覆盖内置版本）
        checker = type_check("""
            type Option[T] { Some(T) None }
            let x: Option[Int] = Some(42)
        """)
        self.assertIn("Option", checker.env.types)

    def test_three_duplicate_functions(self):
        """三个同名函数也应报错"""
        from nova.errors import TypeCheckError
        with self.assertRaises(TypeCheckError):
            type_check("""
                fn f() -> Int { 1 }
                fn f() -> Int { 2 }
                fn f() -> Int { 3 }
            """)

    def test_valid_unique_functions(self):
        """不同名称的函数不应触发重复定义错误"""
        checker = type_check("""
            fn add(x: Int, y: Int) -> Int { x + y }
            fn sub(x: Int, y: Int) -> Int { x - y }
            fn mul(x: Int, y: Int) -> Int { x * y }
            let r = add(1, 2)
        """)
        self.assertIsNotNone(checker.env.lookup("add"))
        self.assertIsNotNone(checker.env.lookup("sub"))
        self.assertIsNotNone(checker.env.lookup("mul"))
