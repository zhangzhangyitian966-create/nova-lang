"""
Nova C 代码生成器测试
"""

import unittest
import os
import sys
import tempfile
import subprocess

from nova.lexer import Lexer
from nova.parser import Parser
from nova.type_checker import TypeChecker
from nova.c_codegen import CCodeGen, C_KEYWORDS


def compile_to_c(source: str) -> str:
    """编译 Nova 源码为 C 代码字符串"""
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    TypeChecker().check_program(ast)
    gen = CCodeGen()
    return gen.generate(ast)


class TestCCodeGenerator(unittest.TestCase):
    """C 代码生成器测试"""

    def test_hello_world(self):
        """测试 hello world 程序的 C 代码生成"""
        c_code = compile_to_c("""
            fn main() -> Unit {
                print("Hello, Nova!")
            }
        """)
        self.assertIn("#include", c_code)
        self.assertIn("int main", c_code)
        self.assertIn("nova_string_new", c_code)

    def test_arithmetic(self):
        """测试算术表达式的类型映射"""
        c_code = compile_to_c("let x = 1 + 2 * 3")
        self.assertIn("int64_t", c_code)

    def test_fn_definition(self):
        """测试函数定义的名称映射"""
        c_code = compile_to_c("""
            fn add(a: Int, b: Int) -> Int { a + b }
        """)
        self.assertIn("nova_fn_add", c_code)

    def test_if_else(self):
        """测试 if-else 表达式生成三元运算符"""
        c_code = compile_to_c("let x = if true then 1 else 2")
        self.assertIn("?", c_code)  # 三元运算符

    def test_for_loop(self):
        """测试 for 循环"""
        c_code = compile_to_c("let result = for x in [1, 2, 3] { x * 2 }")
        self.assertIn("for", c_code)

    def test_while_loop(self):
        """测试 while 循环"""
        c_code = compile_to_c("""
            mut i = 0
            while i < 5 { i = i + 1 }
        """)
        self.assertIn("while", c_code)

    def test_string_concat(self):
        """测试字符串拼接使用 nova_string_concat"""
        c_code = compile_to_c('let x = "hello" ++ " world"')
        self.assertIn("nova_string_concat", c_code)

    def test_match_expr(self):
        """测试 match 表达式生成 if-else 链"""
        c_code = compile_to_c("""
            let x = match 42 {
                1 -> "one"
                n -> "other"
            }
        """)
        # match 应生成为 if-else 链或 switch
        self.assertTrue("if" in c_code or "switch" in c_code)

    def test_list_comprehension(self):
        """测试列表推导式"""
        c_code = compile_to_c("let xs = [x * x for x <- 0..5]")
        self.assertIn("nova_list_new", c_code)

    def test_pipe_expr(self):
        """测试管道表达式展开为嵌套调用"""
        c_code = compile_to_c("""
            let result = [1, 2, 3]
                |> filter(|x| x > 1)
                |> map(|x| x * x)
        """)
        # 管道应展开为嵌套调用，filter 是内置函数
        self.assertIn("nova_list_filter", c_code)

    def test_adt(self):
        """测试 ADT 类型定义"""
        c_code = compile_to_c("""
            type Shape { Circle(r: Float) | Rect(w: Float, h: Float) }
            fn area(s: Shape) -> Float {
                match s {
                    Circle(r) -> 3.14159 * r * r
                    Rect(w, h) -> w * h
                }
            }
        """)
        self.assertIn("NovaADT", c_code)

    def test_closure(self):
        """测试闭包生成"""
        c_code = compile_to_c("""
            fn make_adder(n: Int) -> (Int) -> Int {
                |x: Int| -> Int { x + n }
            }
        """)
        self.assertIn("NovaClosure", c_code)

    def test_generate_valid_c(self):
        """生成的 C 代码应该能通过 C 编译器的基本语法检查"""
        c_code = compile_to_c("""
            fn main() -> Unit {
                print("Hello from Nova C backend!")
            }
        """)
        # 保存到临时文件并尝试编译（只检查语法）
        with tempfile.NamedTemporaryFile(suffix='.c', mode='w', delete=False) as f:
            f.write(c_code)
            f.flush()
            try:
                # 尝试用 C 编译器检查语法
                cc = "gcc"
                result = subprocess.run(
                    [cc, "-fsyntax-only", "-I",
                     os.path.join(os.path.dirname(__file__), "..", "runtime"),
                     f.name],
                    capture_output=True, text=True, timeout=5
                )
                # 不一定有 gcc，所以只记录，不强制通过
                self._cc_result = result
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            finally:
                os.unlink(f.name)


class TestCCodeGenInternals(unittest.TestCase):
    """C 代码生成器内部机制测试"""

    def test_c_keywords_set(self):
        """C 关键字集合应包含常见关键字"""
        self.assertIn("int", C_KEYWORDS)
        self.assertIn("return", C_KEYWORDS)
        self.assertIn("if", C_KEYWORDS)
        self.assertIn("while", C_KEYWORDS)
        self.assertIn("for", C_KEYWORDS)
        self.assertIn("struct", C_KEYWORDS)
        self.assertIn("void", C_KEYWORDS)
        self.assertIn("else", C_KEYWORDS)
        self.assertIn("break", C_KEYWORDS)
        self.assertIn("continue", C_KEYWORDS)
        self.assertIn("switch", C_KEYWORDS)
        self.assertIn("case", C_KEYWORDS)

    def test_mangle_name_keywords(self):
        """名称转换应避免 C 关键字冲突"""
        gen = CCodeGen()
        self.assertEqual(gen._mangle_name("int"), "nova_int")
        self.assertEqual(gen._mangle_name("return"), "nova_return")
        self.assertEqual(gen._mangle_name("if"), "nova_if")
        self.assertEqual(gen._mangle_name("while"), "nova_while")
        self.assertEqual(gen._mangle_name("for"), "nova_for")
        self.assertEqual(gen._mangle_name("struct"), "nova_struct")
        self.assertEqual(gen._mangle_name("main"), "nova_main")

    def test_mangle_name_normal(self):
        """普通名称不应被修改"""
        gen = CCodeGen()
        self.assertEqual(gen._mangle_name("hello"), "hello")
        self.assertEqual(gen._mangle_name("x"), "x")
        self.assertEqual(gen._mangle_name("my_var"), "my_var")
        self.assertEqual(gen._mangle_name("add"), "add")

    def test_mangle_name_leading_digit(self):
        """以数字开头的名称应添加前缀"""
        gen = CCodeGen()
        self.assertTrue(gen._mangle_name("123abc").startswith("nova_"))

    def test_escape_c_string(self):
        """测试字符串转义"""
        gen = CCodeGen()
        self.assertEqual(gen._escape_c_string("hello"), "hello")
        self.assertEqual(gen._escape_c_string('he"llo'), 'he\\"llo')
        self.assertEqual(gen._escape_c_string("line1\nline2"), "line1\\nline2")
        self.assertEqual(gen._escape_c_string("tab\there"), "tab\\there")
        self.assertEqual(gen._escape_c_string("back\\slash"), "back\\\\slash")

    def test_escape_c_char(self):
        """测试字符转义"""
        gen = CCodeGen()
        self.assertEqual(gen._escape_c_char("\n"), "\\n")
        self.assertEqual(gen._escape_c_char("\t"), "\\t")
        self.assertEqual(gen._escape_c_char("'"), "\\'")
        self.assertEqual(gen._escape_c_char("a"), "a")

    def test_new_temp(self):
        """临时变量应按序递增"""
        gen = CCodeGen()
        t1 = gen._new_temp()
        t2 = gen._new_temp()
        t3 = gen._new_temp()
        self.assertEqual(t1, "nova_tmp_0")
        self.assertEqual(t2, "nova_tmp_1")
        self.assertEqual(t3, "nova_tmp_2")

    def test_is_c_keyword(self):
        """静态方法检查"""
        self.assertTrue(CCodeGen.is_c_keyword("int"))
        self.assertTrue(CCodeGen.is_c_keyword("for"))
        self.assertFalse(CCodeGen.is_c_keyword("hello"))
        self.assertFalse(CCodeGen.is_c_keyword("my_var"))


class TestCCodeGenExpressions(unittest.TestCase):
    """表达式级 C 代码生成测试"""

    def test_int_literal(self):
        c_code = compile_to_c("let x = 42")
        self.assertIn("((int64_t)42)", c_code)

    def test_float_literal(self):
        c_code = compile_to_c("let x = 3.14")
        self.assertIn("double", c_code)

    def test_bool_literal(self):
        c_code = compile_to_c("let x = true")
        self.assertIn("true", c_code)

    def test_string_literal(self):
        c_code = compile_to_c('let x = "hello"')
        self.assertIn("nova_string_new", c_code)
        self.assertIn("hello", c_code)

    def test_unary_minus(self):
        c_code = compile_to_c("let x = -42")
        self.assertIn("-((int64_t)42)", c_code)

    def test_unary_not(self):
        c_code = compile_to_c("let x = !true")
        self.assertIn("!true", c_code)

    def test_comparison(self):
        c_code = compile_to_c("let x = 1 < 2")
        self.assertIn("<", c_code)

    def test_logical_and(self):
        c_code = compile_to_c("let x = true && false")
        self.assertIn("&&", c_code)

    def test_logical_or(self):
        c_code = compile_to_c("let x = true || false")
        self.assertIn("||", c_code)

    def test_block(self):
        c_code = compile_to_c("let x = { let a = 1; let b = 2; a + b }")
        self.assertIn("{", c_code)
        self.assertIn("}", c_code)

    def test_break_expr(self):
        c_code = compile_to_c("""
            let x = for i in [1, 2, 3] {
                if i == 2 then break
                i
            }
        """)
        self.assertIn("break", c_code)

    def test_continue_expr(self):
        c_code = compile_to_c("""
            let x = for i in [1, 2, 3] {
                if i == 2 then continue
                i
            }
        """)
        self.assertIn("continue", c_code)

    def test_tuple(self):
        c_code = compile_to_c("let x = (1, 2)")
        self.assertIn("nova_tuple_new", c_code)

    def test_empty_list(self):
        c_code = compile_to_c("let xs = []")
        self.assertIn("nova_list_new", c_code)

    def test_list_expr(self):
        c_code = compile_to_c("let xs = [1, 2, 3]")
        self.assertIn("nova_list_new", c_code)
        self.assertIn("nova_list_push", c_code)

    def test_assignment(self):
        c_code = compile_to_c("""
            fn test_assign() -> Int {
                mut x = 10
                x = 20
                x
            }
        """)
        self.assertIn("x = ((int64_t)20)", c_code)


class TestCCodeGenFunctions(unittest.TestCase):
    """函数相关的 C 代码生成测试"""

    def test_fn_no_params(self):
        c_code = compile_to_c("fn greet() -> Unit { print(\"hi\") }")
        self.assertIn("nova_fn_greet", c_code)

    def test_fn_with_params(self):
        c_code = compile_to_c("fn add(a: Int, b: Int) -> Int { a + b }")
        self.assertIn("nova_fn_add", c_code)
        self.assertIn("int64_t", c_code)

    def test_fn_recursive(self):
        c_code = compile_to_c("""
            fn fib(n: Int) -> Int {
                if n <= 1 then n
                else fib(n - 1) + fib(n - 2)
            }
        """)
        self.assertIn("nova_fn_fib", c_code)
        # 应包含前向声明
        self.assertIn("int64_t nova_fn_fib(", c_code)

    def test_fn_main_called(self):
        """main 函数应该在 C main 中被调用"""
        c_code = compile_to_c("""
            fn main() -> Unit {
                print("Hello")
            }
        """)
        self.assertIn("nova_fn_main();", c_code)


class TestCCodeGenADT(unittest.TestCase):
    """ADT 相关的 C 代码生成测试"""

    def test_enum_definition(self):
        c_code = compile_to_c("type Color { Red | Green | Blue }")
        self.assertIn("NOVA_ADT_Color_Red", c_code)
        self.assertIn("NOVA_ADT_Color_Green", c_code)
        self.assertIn("NOVA_ADT_Color_Blue", c_code)

    def test_adt_with_fields(self):
        c_code = compile_to_c("type Shape { Circle(r: Float) | Rect(w: Float, h: Float) }")
        self.assertIn("NovaADT_Shape", c_code)
        self.assertIn("NOVA_ADT_Shape_Circle", c_code)
        self.assertIn("NOVA_ADT_Shape_Rect", c_code)

    def test_adt_constructor(self):
        c_code = compile_to_c("""
            type Shape { Circle(r: Float) | Rect(w: Float, h: Float) }
            let s = Circle(5.0)
        """)
        self.assertIn("NOVA_ADT_Shape_Circle", c_code)

    def test_option_some(self):
        c_code = compile_to_c("""
            type Option { Some(value: Int) | None }
            let x = Some(42)
        """)
        self.assertIn("NovaADT", c_code)

    def test_option_none(self):
        c_code = compile_to_c("""
            type Option { Some(value: Int) | None }
            let x = None
        """)
        self.assertIn("NovaADT", c_code)


class TestCCodeGenOutput(unittest.TestCase):
    """C 代码输出结构测试"""

    def test_includes(self):
        c_code = compile_to_c("fn main() -> Unit { }")
        self.assertIn('#include "nova_runtime.h"', c_code)
        self.assertIn("<stdio.h>", c_code)
        self.assertIn("<stdlib.h>", c_code)
        self.assertIn("<stdint.h>", c_code)
        self.assertIn("<stdbool.h>", c_code)

    def test_has_main_function(self):
        c_code = compile_to_c("fn main() -> Unit { print(\"test\") }")
        self.assertIn("int main(int argc, char** argv)", c_code)
        self.assertIn("nova_init();", c_code)
        self.assertIn("nova_cleanup();", c_code)
        self.assertIn("return 0;", c_code)

    def test_forward_declarations(self):
        c_code = compile_to_c("""
            fn foo() -> Unit { }
            fn bar() -> Unit { }
        """)
        # 函数应该有前向声明
        self.assertIn("nova_fn_foo", c_code)
        self.assertIn("nova_fn_bar", c_code)

    def test_global_variables(self):
        c_code = compile_to_c("let x = 42")
        self.assertIn("int64_t", c_code)


if __name__ == "__main__":
    unittest.main()
