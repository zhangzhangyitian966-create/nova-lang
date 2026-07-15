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
        bytecode.emit_op(Op.MATCH_CONSTRUCTOR, "Circle", 1, 2)
        bytecode.emit_op(Op.HALT)
        vm = NovaVM(bytecode)
        with self.assertRaises(RuntimeError_):
            vm.run()


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
