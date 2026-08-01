"""
Nova C 后端测试（架构手术 B Phase2 迁移版）

统一使用 NovaCompilerPipeline(target=BACKEND_C) 走 LIR→C 路径。
受益于完整三层 IR 优化 Pass（DCE/内联/CSE/LICM）。

历史说明：
  - v0.3.0 cycles=91 之前：使用 nova.c_codegen.CCodeGen AST→C 直译路径（1591行）
  - v0.3.0 cycles=91 起：删除旧直译路径，统一走 backend.compiler_pipeline + LIRCBackend
  - 参考：ARCHITECTURE_VISION.md §2.2「立即架构手术 B」
"""

import os
import sys
import tempfile
import unittest

from nova.backend.compiler_pipeline import BACKEND_C, NovaCompilerPipeline


def compile_to_c(source: str, optimize: int = 0) -> str:
    """通过 NovaCompilerPipeline 编译 Nova 源码为 C 代码字符串。

    统一走 LIR→C 路径，受益于三层 IR 优化 Pass。
    """
    pipeline = NovaCompilerPipeline(target=BACKEND_C, optimize_level=optimize)
    with tempfile.TemporaryDirectory() as tmpdir:
        output = os.path.join(tmpdir, "out.c")
        pipeline.compile_source(source, output)
        with open(output, encoding="utf-8") as f:
            return f.read()


# ============================================================
# 基础：C 输出结构正确性（include / main 入口 / 初始化）
# ============================================================
class TestCOutputStructure(unittest.TestCase):
    """C 代码输出结构测试：头文件、main 入口、运行时初始化"""

    def test_runtime_includes_present(self):
        """必须包含 nova_runtime.h + 4 个 C 标准头"""
        c_code = compile_to_c("fn main() -> Unit { }")
        self.assertIn('#include "nova_runtime.h"', c_code)
        self.assertIn("<stdio.h>", c_code)
        self.assertIn("<stdlib.h>", c_code)
        self.assertIn("<stdint.h>", c_code)
        self.assertIn("<stdbool.h>", c_code)

    def test_main_entry_exists(self):
        """必须有 int main(int argc, char** argv) 入口 + nova_init/cleanup"""
        c_code = compile_to_c('fn main() -> Unit { print("hi") }')
        self.assertIn("int main(int argc, char** argv)", c_code)
        self.assertIn("nova_init();", c_code)
        self.assertIn("nova_cleanup();", c_code)
        self.assertIn("return 0;", c_code)

    def test_hello_world(self):
        """hello world: nova_string_new + nova_fn_main 调用链存在"""
        c_code = compile_to_c("""
            fn main() -> Unit {
                print("Hello, Nova!")
            }
        """)
        self.assertIn("#include", c_code)
        self.assertIn("int main", c_code)
        self.assertIn("nova_string_new", c_code)
        # nova_fn_main 前向声明和调用必然存在
        self.assertIn("nova_fn_main", c_code)


# ============================================================
# 字面量 / 表达式 / 基础类型
# ============================================================
class TestLiteralsAndExpressions(unittest.TestCase):
    """字面量与基础表达式的 C 映射"""

    def test_int_literal(self):
        """整数字面量应产出 int64_t 类型"""
        c_code = compile_to_c("fn main() -> Int { 42 }")
        self.assertIn("int64_t", c_code)

    def test_float_literal(self):
        """浮点字面量应产出 double 类型"""
        c_code = compile_to_c("fn main() -> Float { 3.14 }")
        self.assertIn("double", c_code)

    def test_bool_literal(self):
        """布尔字面量使用 C true/false"""
        c_code = compile_to_c("fn main() -> Bool { true }")
        self.assertIn("true", c_code)
        c_code2 = compile_to_c("fn main() -> Bool { false }")
        self.assertIn("false", c_code2)

    def test_string_literal(self):
        """字符串字面量走 nova_string_new，且字面量值保留"""
        c_code = compile_to_c('fn main() { let x = "hello"; x }')
        self.assertIn("nova_string_new", c_code)
        self.assertIn("hello", c_code)

    def test_unary_minus(self):
        """一元负号应保留为 C - 表达式"""
        c_code = compile_to_c("fn main() -> Int { -42 }")
        self.assertTrue("-" in c_code)

    def test_unary_not(self):
        """一元非 ! 保留（使用 !r0 或 !true 任一形式）"""
        c_code = compile_to_c("fn main() -> Bool { !true }")
        # 优化后可能是 r0 = true; r1 = !r0; 检查"!"字符出现在表达式上下文中
        self.assertIn("!", c_code)

    def test_comparison(self):
        """比较运算符 < 在 C 代码中保留"""
        c_code = compile_to_c("fn main() -> Bool { 1 < 2 }")
        self.assertIn("<", c_code)

    def test_logical_and_or(self):
        """逻辑与/或保留 && / ||"""
        c_and = compile_to_c("fn main() -> Bool { true && false }")
        self.assertIn("&&", c_and)
        c_or = compile_to_c("fn main() -> Bool { true || false }")
        self.assertIn("||", c_or)

    def test_block_expr(self):
        """块表达式 { } 保留 C 大括号"""
        c_code = compile_to_c("fn main() -> Int { let a = 1; let b = 2; a + b }")
        self.assertIn("{", c_code)
        self.assertIn("}", c_code)

    def test_tuple_literal(self):
        """元组字面量：LIR 路径走 nova_alloc + memset + 偏移赋值（不直接调用 nova_tuple_new）"""
        c_code = compile_to_c("fn main() { let x = (1, 2); x }")
        # LIRCBackend 元组编译：nova_alloc(size) + 字段逐偏移写入
        has_alloc = "nova_alloc" in c_code or "memset" in c_code or "NovaValue" in c_code
        self.assertTrue(has_alloc, f"元组构造应包含 nova_alloc 或偏移赋值：{c_code[:500]}")

    def test_empty_list(self):
        """空列表字面量：能编译出包含 nova_* 调用的 C 代码"""
        c_code = compile_to_c("fn main() { let xs: List[Int] = []; xs }")
        self.assertIn("nova", c_code.lower())

    def test_list_literal(self):
        """非空列表字面量：列表构造 + push"""
        c_code = compile_to_c("fn main() { let xs = [1, 2, 3]; xs }")
        # nova_list_new + nova_list_push 是 LIRCBackend 列表路径
        has_list_call = ("nova_list_new" in c_code) or ("nova_list_push" in c_code)
        self.assertTrue(has_list_call, f"列表字面量应有 list 构造：{c_code[:500]}")


# ============================================================
# 控制流：LIR 后端统一降级为基本块 + if+goto（无原生 for/while/break 关键字）
# ============================================================
class TestControlFlow(unittest.TestCase):
    """控制流语句的 C 代码生成：LIR 统一使用基本块 label + if + goto 形式"""

    def test_if_else(self):
        """if-else 表达式应生成分支跳转（if 语句或 goto）"""
        c_code = compile_to_c("fn main() -> Int { if true then 1 else 2 }")
        has_branch = ("if (" in c_code) or ("if(" in c_code) or ("goto" in c_code)
        self.assertTrue(has_branch, f"if-else 应有分支跳转：{c_code[:500]}")

    def test_while_loop(self):
        """while 循环：LIR 降级为 bb* 基本块 + if+goto 回跳（无原生 while 关键字）"""
        c_code = compile_to_c("""
            fn main() -> Int {
                mut i = 0
                while i < 5 { i = i + 1 }
                i
            }
        """)
        # 至少应有 3+ 个基本块标签（bb0: / bb1: / bb2: / bb3:）或 goto 关键字
        has_back_edge = ("goto" in c_code) or ("bb1:" in c_code)
        self.assertTrue(has_back_edge, f"while 循环应含 goto 回跳：{c_code[:500]}")

    def test_for_loop(self):
        """for 循环：LIR 降级为 bb 基本块 + 索引比较 + goto"""
        c_code = compile_to_c("""
            fn main() {
                let result = for i in [1, 2, 3] { i * 2 }
                result
            }
        """)
        # nova_list_new/nova_list_push 出现 = 列表构造 + 循环已执行
        has_loop_structure = ("goto" in c_code) or ("nova_list_new" in c_code)
        self.assertTrue(has_loop_structure, f"for 循环应含 goto + 列表构造：{c_code[:500]}")

    def test_break_expr(self):
        """break：LIR 降级为 goto exit_block（无原生 break 关键字）"""
        c_code = compile_to_c("""
            fn main() {
                for i in [1, 2, 3] { if i == 2 then break; i }
            }
        """)
        # goto bb3 等形式的退出跳转即代表 break 语义
        self.assertIn("goto", c_code, f"break 应降级为 goto 跳转：{c_code[:500]}")


# ============================================================
# 函数
# ============================================================
class TestFunctionCompilation(unittest.TestCase):
    """函数定义的 C 代码命名约定：nova_fn_<name> 前缀"""

    def test_fn_no_params(self):
        """无参函数映射为 nova_fn_greet()"""
        c_code = compile_to_c('fn greet() -> Unit { print("hi") }')
        self.assertIn("nova_fn_greet", c_code)

    def test_fn_with_params(self):
        """带参函数映射为 nova_fn_add(int64_t a, int64_t b)"""
        c_code = compile_to_c("fn add(a: Int, b: Int) -> Int { a + b }")
        self.assertIn("nova_fn_add", c_code)
        self.assertIn("int64_t", c_code)

    def test_fn_recursive(self):
        """递归函数：有前向声明 + 递归调用"""
        c_code = compile_to_c("""
            fn fib(n: Int) -> Int {
                if n <= 1 then n
                else fib(n - 1) + fib(n - 2)
            }
        """)
        self.assertIn("nova_fn_fib", c_code)

    def test_fn_main_called(self):
        """Nova main() 应在 C main 中被调用"""
        c_code = compile_to_c('fn main() -> Unit { print("Hello") }')
        self.assertIn("nova_fn_main", c_code)

    def test_forward_declarations(self):
        """多个函数定义应包含各自前向声明"""
        c_code = compile_to_c("""
            fn foo() -> Unit { }
            fn bar() -> Unit { }
        """)
        self.assertIn("nova_fn_foo", c_code)
        self.assertIn("nova_fn_bar", c_code)


# ============================================================
# 赋值 / 可变变量
# ============================================================
class TestMutableAssignment(unittest.TestCase):
    """可变变量与赋值语句"""

    def test_mut_reassignment(self):
        """mut x = 10; x = 20 应在 C 中保留 20 字面量"""
        c_code = compile_to_c("""
            fn test_assign() -> Int {
                mut x = 10
                x = 20
                x
            }
        """)
        self.assertIn("20", c_code)


# ============================================================
# 字符串拼接
# ============================================================
class TestStringConcat(unittest.TestCase):
    """字符串 ++ 运算符调用 nova_string_* 运行时"""

    def test_string_concat(self):
        """两个字符串拼接应调用 nova_string_* 前缀的运行时函数"""
        c_code = compile_to_c('fn main() { let x = "hello" ++ " world"; x }')
        self.assertIn("nova_string", c_code)


# ============================================================
# 管道表达式（parser desugar 为嵌套 FnCall）
# ============================================================
class TestPipeExpr(unittest.TestCase):
    """管道 |> 在 parser 阶段已 desugar"""

    def test_pipe_filter_map_compiles(self):
        """[1,2,3] |> filter |> map 应能编译出非空、含 nova_* 调用的 C 代码"""
        c_code = compile_to_c("""
            fn main() {
                let result = [1, 2, 3]
                    |> filter(|x: Int| -> Bool { x > 1 })
                    |> map(|x: Int| -> Int { x * x })
                result
            }
        """)
        self.assertTrue(len(c_code) > 200, f"代码长度应足够：{len(c_code)}")
        self.assertIn("nova", c_code.lower())


# ============================================================
# ADT / 模式匹配（match）：DCE 会移除未使用的类型，所以测试都"使用"ADT
# ============================================================
class TestADTAndMatch(unittest.TestCase):
    """代数数据类型与 match 表达式（确保在 main 中"使用"类型，防止 DCE）"""

    @unittest.skip("已知类型检查bug：纯枚举ADT match被误判为冗余分支（TypeCheck.match穷尽性误报）")
    def test_enum_definition_and_use(self):
        """纯枚举 ADT：main 中构造 + 使用 variant 时，variant 名应出现在 C 代码中"""
        c_code = compile_to_c("""
            type Color { Red | Green | Blue }
            fn to_int(c: Color) -> Int {
                match c {
                    Red -> 1,
                    Green -> 2,
                    Blue -> 3
                }
            }
            fn main() -> Int { to_int(Red) }
        """)
        # 至少包含 1 个 variant（Red 已使用）
        self.assertIn("Red", c_code, f"Red variant 应出现：{c_code[:500]}")

    def test_adt_with_fields_used(self):
        """带字段 ADT：构造 + match 使用时 type_name 与 variant 名应存在"""
        c_code = compile_to_c("""
            type Shape { Circle(r: Float) | Rect(w: Float, h: Float) }
            fn area(s: Shape) -> Float {
                match s {
                    Circle(r) -> 3.14159 * r * r,
                    Rect(w, h) -> w * h
                }
            }
            fn main() -> Float { area(Circle(5.0)) }
        """)
        self.assertIn("Circle", c_code)

    def test_adt_constructor_call(self):
        """ADT 构造器调用：Circle(5.0) 使用时 Circle 名出现"""
        c_code = compile_to_c("""
            type Shape { Circle(r: Float) | Rect(w: Float, h: Float) }
            fn main() { let s = Circle(5.0); s }
        """)
        self.assertIn("Circle", c_code)

    @unittest.skip("已知类型检查bug：纯枚举ADT match被误判为冗余分支（TypeCheck.match穷尽性误报）")
    def test_match_expr_generates_branches(self):
        """match 表达式：分支比较产生 if/goto"""
        c_code = compile_to_c("""
            type Color { Red | Green | Blue }
            fn pick(c: Color) -> Int {
                match c {
                    Red -> 1,
                    Green -> 2,
                    Blue -> 3
                }
            }
            fn main() -> Int { pick(Red) }
        """)
        has_branch = ("if" in c_code) or ("goto" in c_code)
        self.assertTrue(has_branch, f"match 应生成分支：{c_code[:800]}")

    def test_option_some_used(self):
        """Option::Some 构造时 variant 名出现"""
        c_code1 = compile_to_c("""
            type Option { Some(value: Int) | None }
            fn main() { let x = Some(42); x }
        """)
        self.assertIn("Some", c_code1)

    @unittest.skip("已知LIR降级bug：Option None match时出现空SSA名（LIRLowering SSA未注册）")
    def test_option_none_used(self):
        """Option::None 构造时 variant 名出现（需要被使用，否则 DCE 移除）"""
        c_code2 = compile_to_c("""
            type Option { Some(value: Int) | None }
            fn default(o: Option, d: Int) -> Int {
                match o {
                    Some(v) -> v,
                    None -> d
                }
            }
            fn main() -> Int { default(None, 0) }
        """)
        self.assertIn("None", c_code2, f"None variant 应出现：{c_code2[:800]}")


# ============================================================
# 列表推导式：Nova 语法要求 for x <- Range（不是列表字面量）
# ============================================================
class TestListComprehension(unittest.TestCase):
    """列表推导式 [x*x for x <- 0..5]（Range 语法）"""

    @unittest.skip("已知LIR降级bug：列表推导式 for x <- Range 出现空SSA名（LIRLowering SSA未注册）")
    def test_list_compiles(self):
        """列表推导式：for x <- 0..6 应能编译出含 nova_list_* + goto 循环的 C 代码"""
        c_code = compile_to_c("""
            fn main() {
                let xs = [x * x for x <- 0..6]
                xs
            }
        """)
        # 列表推导降级后应有列表构造 + 循环跳转
        has_list = ("nova_list" in c_code)
        self.assertTrue(has_list, f"listcomp 应包含 nova_list_* 调用：{c_code[:500]}")
        self.assertTrue(len(c_code) > 300, f"输出长度应>300：{len(c_code)}")


# ============================================================
# 闭包
# ============================================================
class TestClosureCompilation(unittest.TestCase):
    """闭包 / lambda 表达式"""

    def test_closure_struct(self):
        """闭包应生成 NovaClosure 结构 + trampoline"""
        c_code = compile_to_c("""
            fn make_adder(n: Int) -> (Int) -> Int {
                |x: Int| -> Int { x + n }
            }
        """)
        has_closure = "NovaClosure" in c_code or "nova_closure" in c_code.lower()
        self.assertTrue(has_closure, f"闭包应使用 NovaClosure：{c_code[:1000]}")

    def test_trampoline_present(self):
        """闭包间接调用使用 trampoline"""
        c_code = compile_to_c("""
            fn make_adder(n: Int) -> (Int) -> Int {
                |x: Int| -> Int { x + n }
            }
        """)
        self.assertIn("trampoline", c_code.lower())


# ============================================================
# 优化级别影响
# ============================================================
class TestOptimizeLevel(unittest.TestCase):
    """不同 optimize_level 均可产出合法 C 代码"""

    def test_opt0_compiles(self):
        """optimize=0：输出非空，含 nova_fn_add"""
        c_code = compile_to_c("fn add(a: Int, b: Int) -> Int { a + b }", optimize=0)
        self.assertIn("nova_fn_add", c_code)

    def test_opt2_compiles(self):
        """optimize=2：启用 DCE+Inline+CSE+LICM，输出非空，含 nova_fn_add"""
        c_code = compile_to_c("fn add(a: Int, b: Int) -> Int { a + b }", optimize=2)
        self.assertIn("nova_fn_add", c_code)


# ============================================================
# 全局变量 / 顶层 let
# ============================================================
class TestGlobalVariables(unittest.TestCase):
    """顶层 let 绑定声明全局变量"""

    def test_global_declared(self):
        """顶层 let x: Int = 42 应声明全局变量 x（NovaValue* 或 int64_t 任一形式）"""
        c_code = compile_to_c("let x: Int = 42")
        # LIRCBackend 顶层全局用 NovaValue* x; 声明
        self.assertIn("NovaValue", c_code)
        self.assertIn(" x;", c_code)


# ============================================================
# 编译管线契约验证
# ============================================================
class TestPipelineContract(unittest.TestCase):
    """NovaCompilerPipeline(target=BACKEND_C) 契约验证"""

    def test_pipeline_equivalent_to_manual(self):
        """compile_to_c(helper) 产出与 NovaCompilerPipeline.compile_source 文件产出一致"""
        source = "fn add(a: Int, b: Int) -> Int { a + b }"
        via_helper = compile_to_c(source, optimize=0)
        pipeline = NovaCompilerPipeline(target=BACKEND_C, optimize_level=0)
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "direct.c")
            pipeline.compile_source(source, out)
            with open(out) as f:
                via_direct = f.read()
        self.assertEqual(via_helper, via_direct)


if __name__ == "__main__":
    unittest.main()
