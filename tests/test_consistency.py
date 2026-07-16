"""
Nova 编程语言 - Evaluator vs VM 一致性测试套件

确保解释器（Evaluator）和字节码虚拟机（VM）两个后端
在核心语言特性上产生完全一致的语义。

审查日志 P0 问题第 8 条：无 Evaluator vs VM 一致性测试。
"""

import unittest
import sys
import os

from nova.lexer import Lexer
from nova.parser import Parser
from nova.type_checker import TypeChecker
from nova.evaluator import Evaluator
from nova.compiler import BytecodeCompiler
from nova.vm import NovaVM


# ============================================================
# 辅助函数：双后端运行与比较
# ============================================================

def _parse_and_check(source: str, check_types: bool = True):
    """词法分析 + 语法分析 + 可选类型检查"""
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    if check_types:
        TypeChecker().check_program(ast)
    return ast


def run_both(source: str, check_types: bool = True):
    """同时用 Evaluator 和 VM 运行同一段代码。

    返回一个字典，包含：
    - evaluator_vars: Dict[str, Any]  Evaluator 端的全局变量快照
    - vm_vars: Dict[str, Any]       VM 端的全局变量快照
    - evaluator_output: List[str]   Evaluator 端的 print 输出
    - vm_output: List[str]         VM 端的 print 输出
    """
    ast = _parse_and_check(source, check_types=check_types)

    # --- Evaluator 端 ---
    evaluator = Evaluator(check_types=check_types)
    evaluator.eval_program(ast)
    evaluator_vars = evaluator.env.all_bindings()  # 所有作用域的绑定
    evaluator_output = list(evaluator._output)

    # --- VM 端 ---
    # 需要重新 parse（因为 ast 可能被 type checker 修改过）
    ast2 = _parse_and_check(source, check_types=check_types)
    compiler = BytecodeCompiler()
    bytecode = compiler.compile(ast2)
    vm = NovaVM(bytecode)
    vm.run()
    vm_vars = dict(vm.globals)
    vm_output = list(vm.output)

    return {
        "evaluator_vars": evaluator_vars,
        "vm_vars": vm_vars,
        "evaluator_output": evaluator_output,
        "vm_output": vm_output,
    }


def _normalize_value(value):
    """将值规范化为可比较的形式。

    由于 Evaluator 和 VM 使用不同的类来表示 ADT、闭包、字符、Unit 等，
    需要将它们转换为统一的可比较形式。
    """
    # 基本类型直接返回
    if value is None:
        return None
    if isinstance(value, (int, float, str, bool)):
        return value

    # 列表：递归规范化每个元素
    if isinstance(value, list):
        return [_normalize_value(v) for v in value]

    # 元组：递归规范化每个元素
    if isinstance(value, tuple):
        return tuple(_normalize_value(v) for v in value)

    # ADT 值（两边各自的 NovaADTValue 类）
    if hasattr(value, 'type_name') and hasattr(value, 'variant_name') and hasattr(value, 'fields'):
        return ('ADT', value.type_name, value.variant_name, _normalize_value(value.fields))

    # 字符值
    if hasattr(value, 'value') and hasattr(value, '__class__'):
        cls_name = value.__class__.__name__
        if cls_name == 'NovaChar':
            return ('Char', value.value)

    # Unit 值
    cls_name = value.__class__.__name__
    if cls_name in ('_UnitValue', 'UNIT_TYPE'):
        return ('Unit',)

    # 闭包：只比较名称和参数数量
    if cls_name == 'NovaClosure':
        if hasattr(value, 'name'):
            return ('Closure', value.name, len(value.params) if hasattr(value, 'params') else value.param_count)
        if hasattr(value, 'func_name'):
            return ('Closure', value.func_name, value.param_count)

    # 内置函数
    if cls_name in ('BuiltinFn', 'NovaBuiltinFn'):
        return ('Builtin', value.name if hasattr(value, 'name') else str(value))

    # 其他类型：转为字符串比较（避免直接比较失败）
    return ('Other', cls_name, str(value))


def assert_var_equal(result, var_name: str):
    """断言某个变量在 Evaluator 和 VM 中的值一致"""
    ev_val = result["evaluator_vars"].get(var_name)
    vm_val = result["vm_vars"].get(var_name)

    ev_norm = _normalize_value(ev_val)
    vm_norm = _normalize_value(vm_val)

    assert ev_norm == vm_norm, (
        f"变量 '{var_name}' 在两个后端的值不一致:\n"
        f"  Evaluator: {ev_val!r} (规范化: {ev_norm!r}\n"
        f"  VM:        {vm_val!r} (规范化: {vm_norm!r})"
    )


def assert_output_equal(result):
    """断言两个后端的 print 输出一致"""
    assert result["evaluator_output"] == result["vm_output"], (
        f"print 输出不一致:\n"
        f"  Evaluator: {result['evaluator_output']}\n"
        f"  VM:        {result['vm_output']}"
    )


def assert_consistent(source: str, var_name: str = None, check_output: bool = False, check_types: bool = True):
    """便捷断言：运行代码并检查变量值和/或输出一致。

    Args:
        source: Nova 源代码
        var_name: 要比较的变量名（None 表示不比较变量）
        check_output: 是否比较 print 输出
        check_types: 是否进行类型检查
    """
    result = run_both(source, check_types=check_types)
    if var_name is not None:
        assert_var_equal(result, var_name)
    if check_output:
        assert_output_equal(result)
    return result


# ============================================================
# 测试用例
# ============================================================

class TestArithmeticConsistency(unittest.TestCase):
    """基本算术运算一致性测试"""

    def test_integer_arithmetic(self):
        """整数四则运算 + - * / %"""
        assert_consistent("let x = 2 + 3 * 4 - 10 / 2 % 3", "x")

    def test_float_arithmetic(self):
        """浮点数运算"""
        assert_consistent("let x = 3.14 * 2.0 + 1.5", "x")

    def test_negation(self):
        """一元取反"""
        assert_consistent("let x = -42", "x")

    def test_comparison_operators(self):
        """比较运算符 == != < > <= >="""
        assert_consistent("let x = 1 < 2 && 3 > 2 || 1 == 1", "x")


class TestStringConsistency(unittest.TestCase):
    """字符串操作一致性测试"""

    def test_string_concat(self):
        """字符串拼接 ++"""
        assert_consistent('let x = "hello" ++ " " ++ "world"', "x")

    def test_string_equality(self):
        """字符串相等比较"""
        assert_consistent('let x = "abc" == "abc"', "x")

    def test_str_len_builtin(self):
        """str_len 内置函数"""
        assert_consistent('let x = str_len("hello world")', "x")

    def test_int_to_str(self):
        """int_to_str 内置函数"""
        assert_consistent('let x = int_to_str(42)', "x")


class TestListConsistency(unittest.TestCase):
    """列表操作一致性测试"""

    def test_list_literal(self):
        """列表字面量"""
        assert_consistent("let xs = [1, 2, 3, 4, 5]", "xs")

    def test_list_length(self):
        """list_length 内置函数"""
        assert_consistent("let x = list_length([10, 20, 30])", "x")

    def test_list_map(self):
        """map 高阶函数"""
        assert_consistent("let xs = map(|x| x * 2, [1, 2, 3])", "xs")

    def test_list_filter(self):
        """filter 高阶函数"""
        assert_consistent("let xs = filter(|x| x > 2, [1, 2, 3, 4, 5])", "xs")

    def test_list_sum(self):
        """sum 内置函数"""
        assert_consistent("let x = sum([1, 2, 3, 4, 5])", "x")

    def test_list_head(self):
        """head 内置函数"""
        assert_consistent("let x = head([10, 20, 30])", "x")

    def test_list_tail(self):
        """tail 内置函数"""
        assert_consistent("let xs = tail([1, 2, 3])", "xs")


class TestBoolLogicConsistency(unittest.TestCase):
    """布尔逻辑一致性测试"""

    def test_bool_and(self):
        """逻辑与 &&"""
        assert_consistent("let x = true && false", "x")

    def test_bool_or(self):
        """逻辑或 ||"""
        assert_consistent("let x = false || true", "x")

    def test_bool_not(self):
        """逻辑非 !"""
        assert_consistent("let x = !true", "x")

    def test_if_expression(self):
        """if 表达式"""
        assert_consistent("let x = if 1 > 0 then 42 else 0", "x")


class TestTupleConsistency(unittest.TestCase):
    """元组一致性测试"""

    def test_tuple_literal(self):
        """元组字面量"""
        assert_consistent("let p = (1, 2, 3)", "p")

    def test_nested_tuple(self):
        """嵌套元组"""
        assert_consistent("let p = (1, (2, 3), 4)", "p")

    def test_tuple_equality(self):
        """元组相等比较"""
        assert_consistent("let x = (1, 2) == (1, 2)", "x")


class TestADTConsistency(unittest.TestCase):
    """ADT 构造与模式匹配一致性测试"""

    def test_adt_constructor_some(self):
        """Option.Some 构造"""
        assert_consistent("let x = Some(42)", "x", check_types=False)

    def test_adt_constructor_none(self):
        """Option.None 构造"""
        assert_consistent("let x = None", "x", check_types=False)

    def test_adt_constructor_ok(self):
        """Result.Ok 构造"""
        assert_consistent("let x = Ok(99)", "x", check_types=False)

    def test_adt_constructor_err(self):
        """Result.Err 构造"""
        assert_consistent("let x = Err(\"oops\")", "x", check_types=False)

    def test_custom_adt_constructor(self):
        """自定义 ADT 构造"""
        assert_consistent("""
            type Color { Red Green Blue }
            let c = Red
        """, "c", check_types=False)

    def test_custom_adt_with_fields(self):
        """带字段的自定义 ADT 构造"""
        assert_consistent("""
            type Shape { Circle(Float) Square(Float) }
            let s = Circle(5.0)
        """, "s", check_types=False)

    def test_match_on_adt(self):
        """ADT 模式匹配"""
        assert_consistent("""
            let x = match Some(42) {
                Some(n) -> n
                None -> 0
            }
        """, "x", check_types=False)

    def test_match_on_custom_adt(self):
        """自定义 ADT 模式匹配"""
        assert_consistent("""
            type Shape { Circle(Float) Square(Float) }
            let area = match Circle(3.0) {
                Circle(r) -> 3.14 * r * r
                Square(s) -> s * s
            }
        """, "area", check_types=False)


class TestFunctionConsistency(unittest.TestCase):
    """函数调用与闭包一致性测试"""

    def test_simple_function(self):
        """简单函数调用"""
        assert_consistent("""
            fn add(a: Int, b: Int) -> Int { a + b }
            let x = add(3, 4)
        """, "x")

    def test_recursive_function(self):
        """递归函数"""
        assert_consistent("""
            fn fact(n: Int) -> Int {
                if n <= 1 then 1 else n * fact(n - 1)
            }
            let x = fact(5)
        """, "x")

    def test_closure(self):
        """闭包捕获变量"""
        assert_consistent("""
            fn make_adder(n: Int) -> (Int) -> Int {
                |x: Int| -> Int { x + n }
            }
            let add5 = make_adder(5)
            let x = add5(10)
        """, "x")

    def test_higher_order_function(self):
        """高阶函数"""
        assert_consistent("""
            fn apply(f: (Int) -> Int, x: Int) -> Int { f(x) }
            let x = apply(|n: Int| -> Int { n * 2 }, 21)
        """, "x")

    def test_mutual_recursion(self):
        """相互递归"""
        assert_consistent("""
            fn is_even(n: Int) -> Bool {
                if n == 0 then true else is_odd(n - 1)
            }
            fn is_odd(n: Int) -> Bool {
                if n == 0 then false else is_even(n - 1)
            }
            let x = is_even(10)
        """, "x")


class TestPipeConsistency(unittest.TestCase):
    """管道操作一致性测试"""

    def test_pipe_filter_map_sum(self):
        """管道操作：filter |> map |> sum"""
        assert_consistent("""
            let result = [1, 2, 3, 4, 5]
                |> filter(|x| x > 2)
                |> map(|x| x * x)
                |> sum
        """, "result")

    def test_pipe_with_builtin(self):
        """管道操作与内置函数"""
        assert_consistent("""
            let result = [10, 20, 30]
                |> map(|x| x + 1)
                |> list_length
        """, "result")

    def test_pipe_string_ops(self):
        """管道操作：字符串处理"""
        assert_consistent("""
            let result = "hello"
                |> str_len
                |> int_to_str
        """, "result")


class TestRangeIterationConsistency(unittest.TestCase):
    """范围迭代一致性测试"""

    def test_for_range_basic(self):
        """for 范围迭代基本用法"""
        assert_consistent("""
            mut sum = 0
            for i <- 0..4 {
                sum = sum + i
            }
        """, "sum", check_types=False)

    def test_for_range_with_step(self):
        """for 范围迭代带步长"""
        # 测试 0..10 步长为 2 的累加
        assert_consistent("""
            mut result = 0
            for i <- 0..10 step 2 {
                result = result + i
            }
        """, "result", check_types=False)

    def test_while_loop(self):
        """while 循环"""
        assert_consistent("""
            mut i = 0
            mut s = 0
            while i < 5 {
                s = s + i
                i = i + 1
            }
        """, "s", check_types=False)

    def test_list_comprehension(self):
        """列表推导式"""
        assert_consistent("""
            let xs = [x * 2 for x <- 0..4]
        """, "xs", check_types=False)


class TestErrorPropagationConsistency(unittest.TestCase):
    """错误传播（? 操作符）一致性测试"""

    def test_try_unwrap_option_some(self):
        """? 操作符解包 Option.Some"""
        assert_consistent("""
            fn f() -> Int {
                let x = Some(42)?
                x
            }
            let result = f()
        """, "result", check_types=False)

    def test_try_unwrap_result_ok(self):
        """? 操作符解包 Result.Ok"""
        assert_consistent("""
            type Result[T, E] { Ok(T) Err(E) }
            fn f() -> Int {
                let x = Ok(99)?
                x
            }
            let result = f()
        """, "result", check_types=False)

    def test_try_unwrap_none_returns_none(self):
        """? 操作符遇到 None 提前返回"""
        assert_consistent("""
            fn f() -> Option[Int] {
                let x = None?
                Some(x)
            }
            let result = f()
        """, "result", check_types=False)

    def test_try_unwrap_err_returns_err(self):
        """? 操作符遇到 Err 提前返回"""
        assert_consistent("""
            type Result[T, E] { Ok(T) Err(E) }
            fn f() -> Result[Int, String] {
                let x = Err("failed")?
                Ok(x)
            }
            let result = f()
        """, "result", check_types=False)

    def test_try_chain(self):
        """? 操作符链式调用"""
        assert_consistent("""
            fn f() -> Int {
                let a = Some(10)?
                let b = Some(20)?
                a + b
            }
            let result = f()
        """, "result", check_types=False)


class TestPrintOutputConsistency(unittest.TestCase):
    """print 输出一致性测试"""

    def test_print_int(self):
        """print 整数"""
        assert_consistent('fn main() -> Unit { print(42) }', check_output=True)

    def test_print_string(self):
        """print 字符串"""
        assert_consistent('fn main() -> Unit { print("hello") }', check_output=True)

    def test_multiple_prints(self):
        """多次 print"""
        assert_consistent('''
            fn main() -> Unit {
                print("one")
                print("two")
                print("three")
            }
        ''', check_output=True)

    def test_print_in_function(self):
        """函数内 print"""
        assert_consistent('''
            fn greet(name: String) -> Unit {
                print("Hello, " ++ name)
            }
            fn main() -> Unit {
                greet("World")
            }
        ''', check_output=True)


class TestEdgeCasesConsistency(unittest.TestCase):
    """边界情况一致性测试"""

    def test_unit_value(self):
        """Unit 值"""
        assert_consistent("let x = ()", "x", check_types=False)

    def test_nested_if(self):
        """嵌套 if 表达式"""
        assert_consistent("""
            let x = if true then
                if false then 1 else 2
            else
                3
        """, "x")

    def test_let_shadowing(self):
        """变量遮蔽"""
        assert_consistent("""
            let x = 10
            let x = x + 5
            let y = x
        """, "y", check_types=False)

    def test_block_expression(self):
        """块表达式"""
        assert_consistent("""
            let x = {
                let a = 1
                let b = 2
                a + b
            }
        """, "x", check_types=False)

    def test_match_integer_pattern(self):
        """整数模式匹配"""
        assert_consistent("""
            let x = match 2 {
                1 -> "one"
                2 -> "two"
                3 -> "three"
                _ -> "other"
            }
        """, "x", check_types=False)

    def test_match_wildcard(self):
        """通配符模式匹配"""
        assert_consistent("""
            let x = match 99 {
                1 -> "one"
                _ -> "other"
            }
        """, "x", check_types=False)


# ============================================================
# 主入口
# ============================================================

if __name__ == "__main__":
    unittest.main()
