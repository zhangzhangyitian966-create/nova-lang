"""
NovaVM 独立单元测试

为 vm.py 栈式虚拟机建立直接单元测试基线，不依赖 Lexer/Parser/TypeChecker/Compiler，
直接构造 Bytecode + Instruction 执行验证。

覆盖范围：常量加载、变量存取、算术/比较/逻辑运算、控制流、函数调用、
数据结构、模式匹配、内置函数、辅助方法。
"""

import math
import unittest

from nova.compiler import Bytecode, FunctionBlock, Instruction, Op
from nova.errors import RuntimeError_
from nova.vm import (
    NovaADTValue,
    NovaBuiltinFn,
    NovaClosure,
    NovaConstructor,
    NovaPartialBuiltin,
    NovaVM,
    UNIT,
)


# ============================================================
# 辅助函数
# ============================================================


def _make_bc(*instructions):
    """构造 Bytecode，自动追加 HALT"""
    bc = Bytecode()
    for instr in instructions:
        bc.code.append(instr)
    bc.code.append(Instruction(Op.HALT))
    return bc


def _run_bc(*instructions):
    """构造 Bytecode 并执行，返回 VM 实例"""
    bc = _make_bc(*instructions)
    vm = NovaVM(bc)
    vm.run()
    return vm


def _make_fn(name, code, param_names=None, constants=None):
    """构造 FunctionBlock"""
    return FunctionBlock(
        name=name,
        param_count=len(param_names or []),
        code=code,
        constants=constants or [],
        param_names=param_names or [],
    )


# ============================================================
# 常量加载与变量存取
# ============================================================


class TestVMConstantsAndLoading(unittest.TestCase):
    """测试常量加载和变量存取指令"""

    def test_const_int(self):
        """CONST_INT 将整数值压入栈"""
        vm = _run_bc(Instruction(Op.CONST_INT, 42))
        self.assertEqual(vm.stack, [42])

    def test_const_float(self):
        """CONST_FLOAT 将浮点值压入栈"""
        vm = _run_bc(Instruction(Op.CONST_FLOAT, 3.14))
        self.assertEqual(vm.stack, [3.14])

    def test_const_string(self):
        """CONST_STRING 将字符串压入栈"""
        vm = _run_bc(Instruction(Op.CONST_STRING, "hello"))
        self.assertEqual(vm.stack, ["hello"])

    def test_const_bool_true(self):
        """CONST_BOOL 压入 True"""
        vm = _run_bc(Instruction(Op.CONST_BOOL, True))
        self.assertEqual(vm.stack, [True])

    def test_const_bool_false(self):
        """CONST_BOOL 压入 False"""
        vm = _run_bc(Instruction(Op.CONST_BOOL, False))
        self.assertEqual(vm.stack, [False])

    def test_const_unit(self):
        """CONST_UNIT 压入 UNIT 单例"""
        vm = _run_bc(Instruction(Op.CONST_UNIT))
        self.assertIs(vm.stack[0], UNIT)

    def test_load_const(self):
        """LOAD_CONST 从常量池加载值"""
        bc = Bytecode()
        bc.constants = ["a", "b"]
        bc.code = [
            Instruction(Op.LOAD_CONST, 0),
            Instruction(Op.LOAD_CONST, 1),
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.stack, ["a", "b"])

    def test_load_var_global(self):
        """LOAD_VAR 从全局变量加载"""
        bc = _make_bc(Instruction(Op.LOAD_VAR, "x"))
        vm = NovaVM(bc)
        vm.globals["x"] = 99
        vm.run()
        self.assertEqual(vm.stack, [99])

    def test_load_var_local(self):
        """LOAD_VAR 优先从当前帧局部变量加载"""
        bc = _make_bc(Instruction(Op.LOAD_VAR, "y"))
        vm = NovaVM(bc)
        from nova.vm import Frame

        frame = Frame(
            return_ip=0, base_sp=0, code=[], constants=[], locals_={"y": 88}
        )
        vm.call_stack.append(frame)
        vm.run()
        self.assertEqual(vm.stack, [88])

    def test_load_var_undefined(self):
        """LOAD_VAR 未定义变量抛出 RuntimeError_"""
        bc = _make_bc(Instruction(Op.LOAD_VAR, "undefined_var"))
        vm = NovaVM(bc)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("未定义", str(ctx.exception))

    def test_store_var_global(self):
        """STORE_VAR 将值存入全局变量"""
        vm = _run_bc(Instruction(Op.CONST_INT, 42), Instruction(Op.STORE_VAR, "x", False))
        self.assertEqual(vm.globals["x"], 42)

    def test_store_var_local(self):
        """STORE_VAR 优先更新当前帧局部变量"""
        bc = _make_bc(Instruction(Op.CONST_INT, 42), Instruction(Op.STORE_VAR, "y", False))
        vm = NovaVM(bc)
        from nova.vm import Frame

        frame = Frame(
            return_ip=0, base_sp=0, code=[], constants=[], locals_={"y": 0}
        )
        vm.call_stack.append(frame)
        vm.run()
        self.assertEqual(frame.locals["y"], 42)


# ============================================================
# 算术运算
# ============================================================


class TestVMArithmetic(unittest.TestCase):
    """测试算术运算指令"""

    def test_add_int(self):
        """ADD 整数相加"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 10), Instruction(Op.CONST_INT, 20), Instruction(Op.ADD)
        )
        self.assertEqual(vm.stack, [30])

    def test_add_float(self):
        """ADD 浮点数相加"""
        vm = _run_bc(
            Instruction(Op.CONST_FLOAT, 1.5),
            Instruction(Op.CONST_FLOAT, 2.5),
            Instruction(Op.ADD),
        )
        self.assertEqual(vm.stack, [4.0])

    def test_sub_int(self):
        """SUB 整数相减"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 20), Instruction(Op.CONST_INT, 8), Instruction(Op.SUB)
        )
        self.assertEqual(vm.stack, [12])

    def test_mul_int(self):
        """MUL 整数相乘"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 6), Instruction(Op.CONST_INT, 7), Instruction(Op.MUL)
        )
        self.assertEqual(vm.stack, [42])

    def test_div_int(self):
        """DIV 整数相除（整除）"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 100), Instruction(Op.CONST_INT, 4), Instruction(Op.DIV)
        )
        self.assertEqual(vm.stack, [25])

    def test_div_float(self):
        """DIV 浮点数相除"""
        vm = _run_bc(
            Instruction(Op.CONST_FLOAT, 7.0),
            Instruction(Op.CONST_FLOAT, 2.0),
            Instruction(Op.DIV),
        )
        self.assertEqual(vm.stack, [3.5])

    def test_div_by_zero(self):
        """DIV 整数除零抛出 RuntimeError_"""
        bc = _make_bc(
            Instruction(Op.CONST_INT, 1), Instruction(Op.CONST_INT, 0), Instruction(Op.DIV)
        )
        vm = NovaVM(bc)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("除零", str(ctx.exception))

    def test_mod_int(self):
        """MOD 整数取模"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 17), Instruction(Op.CONST_INT, 5), Instruction(Op.MOD)
        )
        self.assertEqual(vm.stack, [2])

    def test_neg_int(self):
        """NEG 整数取反"""
        vm = _run_bc(Instruction(Op.CONST_INT, 42), Instruction(Op.NEG))
        self.assertEqual(vm.stack, [-42])

    def test_neg_float(self):
        """NEG 浮点取反"""
        vm = _run_bc(Instruction(Op.CONST_FLOAT, 3.14), Instruction(Op.NEG))
        self.assertEqual(vm.stack, [-3.14])

    def test_concat_strings(self):
        """CONCAT 字符串拼接"""
        vm = _run_bc(
            Instruction(Op.CONST_STRING, "hello"),
            Instruction(Op.CONST_STRING, "world"),
            Instruction(Op.CONCAT),
        )
        self.assertEqual(vm.stack, ["helloworld"])

    def test_concat_mixed(self):
        """CONCAT 混合类型转为字符串拼接"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.CONST_STRING, "x"),
            Instruction(Op.CONCAT),
        )
        self.assertEqual(vm.stack, ["42x"])


# ============================================================
# 比较与逻辑运算
# ============================================================


class TestVMComparisonAndLogic(unittest.TestCase):
    """测试比较和逻辑运算指令"""

    def test_eq_int_true(self):
        """EQ 整数相等为 True"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 5), Instruction(Op.CONST_INT, 5), Instruction(Op.EQ)
        )
        self.assertEqual(vm.stack, [True])

    def test_eq_int_false(self):
        """EQ 整数不等为 False"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 5), Instruction(Op.CONST_INT, 3), Instruction(Op.EQ)
        )
        self.assertEqual(vm.stack, [False])

    def test_neq(self):
        """NEQ 不等判断"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 5), Instruction(Op.CONST_INT, 3), Instruction(Op.NEQ)
        )
        self.assertEqual(vm.stack, [True])

    def test_lt(self):
        """LT 小于判断"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 3), Instruction(Op.CONST_INT, 5), Instruction(Op.LT)
        )
        self.assertEqual(vm.stack, [True])

    def test_gt(self):
        """GT 大于判断"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 10), Instruction(Op.CONST_INT, 5), Instruction(Op.GT)
        )
        self.assertEqual(vm.stack, [True])

    def test_lte_true(self):
        """LTE 小于等于为 True"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 3), Instruction(Op.CONST_INT, 3), Instruction(Op.LTE)
        )
        self.assertEqual(vm.stack, [True])

    def test_gte_true(self):
        """GTE 大于等于为 True"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 5), Instruction(Op.CONST_INT, 3), Instruction(Op.GTE)
        )
        self.assertEqual(vm.stack, [True])

    def test_and_true(self):
        """AND 两真为真"""
        vm = _run_bc(
            Instruction(Op.CONST_BOOL, True),
            Instruction(Op.CONST_BOOL, True),
            Instruction(Op.AND),
        )
        self.assertEqual(vm.stack, [True])

    def test_and_false(self):
        """AND 一假为假"""
        vm = _run_bc(
            Instruction(Op.CONST_BOOL, True),
            Instruction(Op.CONST_BOOL, False),
            Instruction(Op.AND),
        )
        self.assertEqual(vm.stack, [False])

    def test_or_true(self):
        """OR 一真为真"""
        vm = _run_bc(
            Instruction(Op.CONST_BOOL, False),
            Instruction(Op.CONST_BOOL, True),
            Instruction(Op.OR),
        )
        self.assertEqual(vm.stack, [True])

    def test_or_false(self):
        """OR 两假为假"""
        vm = _run_bc(
            Instruction(Op.CONST_BOOL, False),
            Instruction(Op.CONST_BOOL, False),
            Instruction(Op.OR),
        )
        self.assertEqual(vm.stack, [False])

    def test_not(self):
        """NOT 取反"""
        vm = _run_bc(Instruction(Op.CONST_BOOL, True), Instruction(Op.NOT))
        self.assertEqual(vm.stack, [False])


# ============================================================
# 控制流
# ============================================================


class TestVMControlFlow(unittest.TestCase):
    """测试跳转和循环指令"""

    def test_jump(self):
        """JUMP 无条件跳转"""
        bc = Bytecode()
        bc.code = [
            Instruction(Op.CONST_INT, 1),
            Instruction(Op.JUMP, 3),
            Instruction(Op.CONST_INT, 999),  # 被跳过
            Instruction(Op.CONST_INT, 2),
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.stack, [1, 2])

    def test_jump_if_false_true(self):
        """JUMP_IF_FALSE 条件为真时不跳转"""
        bc = Bytecode()
        bc.code = [
            Instruction(Op.CONST_BOOL, True),
            Instruction(Op.JUMP_IF_FALSE, 3),
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.stack, [42])

    def test_jump_if_false_false(self):
        """JUMP_IF_FALSE 条件为假时跳转"""
        bc = Bytecode()
        bc.code = [
            Instruction(Op.CONST_BOOL, False),
            Instruction(Op.JUMP_IF_FALSE, 3),
            Instruction(Op.CONST_INT, 999),  # 被跳过
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.stack, [42])

    def test_pop_jump_if_false_true(self):
        """POP_JUMP_IF_FALSE 条件为真时不跳转，栈弹出"""
        bc = Bytecode()
        bc.code = [
            Instruction(Op.CONST_BOOL, True),
            Instruction(Op.POP_JUMP_IF_FALSE, 3),
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.stack, [42])

    def test_pop_jump_if_false_false(self):
        """POP_JUMP_IF_FALSE 条件为假时跳转，栈弹出"""
        bc = Bytecode()
        bc.code = [
            Instruction(Op.CONST_BOOL, False),
            Instruction(Op.POP_JUMP_IF_FALSE, 3),
            Instruction(Op.CONST_INT, 999),  # 被跳过
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.stack, [42])

    def test_if_then_else_true(self):
        """组合 JUMP_IF_FALSE + JUMP 实现 if-then-else（条件为真）"""
        bc = Bytecode()
        bc.code = [
            Instruction(Op.CONST_BOOL, True),
            Instruction(Op.POP_JUMP_IF_FALSE, 4),
            Instruction(Op.CONST_INT, 1),  # then
            Instruction(Op.JUMP, 5),
            Instruction(Op.CONST_INT, 2),  # else
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.stack, [1])

    def test_if_then_else_false(self):
        """组合 JUMP_IF_FALSE + JUMP 实现 if-then-else（条件为假）"""
        bc = Bytecode()
        bc.code = [
            Instruction(Op.CONST_BOOL, False),
            Instruction(Op.POP_JUMP_IF_FALSE, 4),
            Instruction(Op.CONST_INT, 1),  # then（被跳过）
            Instruction(Op.JUMP, 5),
            Instruction(Op.CONST_INT, 2),  # else
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.stack, [2])

    def test_while_loop(self):
        """模拟 while 循环：i=0; while i<3 { i=i+1 }"""
        bc = Bytecode()
        bc.code = [
            Instruction(Op.CONST_INT, 0),
            Instruction(Op.STORE_VAR, "i", False),
            # loop start (ip=2)
            Instruction(Op.LOAD_VAR, "i"),
            Instruction(Op.CONST_INT, 3),
            Instruction(Op.LT),
            Instruction(Op.POP_JUMP_IF_FALSE, 11),  # exit to HALT
            Instruction(Op.LOAD_VAR, "i"),
            Instruction(Op.CONST_INT, 1),
            Instruction(Op.ADD),
            Instruction(Op.STORE_VAR, "i", False),
            Instruction(Op.JUMP, 2),  # back to loop start
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.globals["i"], 3)

    def test_loop_end_for_list(self):
        """LOOP_END 处理 for 列表循环迭代"""
        vm = NovaVM(Bytecode())
        vm.stack = [[1, 2, 3], [], 42]
        vm._op_loop_end(Instruction(Op.LOOP_END, 99))
        self.assertEqual(vm.stack, [[1, 2, 3], [42]])
        self.assertEqual(vm.ip, 99)

    def test_break(self):
        """BREAK 清理 for 循环栈并跳转"""
        vm = NovaVM(Bytecode())
        vm.stack = [[1, 2, 3], [10]]
        vm._op_break(Instruction(Op.BREAK, 99))
        self.assertEqual(vm.stack, [[10]])
        self.assertEqual(vm.ip, 99)


# ============================================================
# 函数调用
# ============================================================


class TestVMFunctionCalls(unittest.TestCase):
    """测试闭包、调用、返回、内置调用"""

    def test_closure_creation(self):
        """CLOSURE 创建 NovaClosure 压栈"""
        bc = Bytecode()
        bc.functions["add"] = _make_fn("add", [Instruction(Op.RETURN)], ["a", "b"])
        bc.code = [
            Instruction(Op.CLOSURE, "add", 0),
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertIsInstance(vm.stack[0], NovaClosure)
        self.assertEqual(vm.stack[0].func_name, "add")

    def test_call_builtin_direct(self):
        """CALL_BUILTIN 直接调用内置函数"""
        bc = Bytecode()
        bc.code = [
            Instruction(Op.CONST_INT, -5),
            Instruction(Op.CALL_BUILTIN, "abs", 1),
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.stack, [5.0])

    def test_call_closure(self):
        """CALL 调用闭包函数"""
        fn_code = [
            Instruction(Op.LOAD_VAR, "a"),
            Instruction(Op.RETURN),
        ]
        bc = Bytecode()
        bc.functions["identity"] = _make_fn("identity", fn_code, ["a"])
        bc.code = [
            Instruction(Op.CLOSURE, "identity", 1),
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.CALL, 1),
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.stack, [42])

    def test_return_value(self):
        """RETURN 返回栈顶值"""
        fn_code = [
            Instruction(Op.LOAD_VAR, "x"),
            Instruction(Op.RETURN),
        ]
        bc = Bytecode()
        bc.functions["get_x"] = _make_fn("get_x", fn_code, ["x"])
        bc.code = [
            Instruction(Op.CLOSURE, "get_x", 1),
            Instruction(Op.CONST_INT, 99),
            Instruction(Op.CALL, 1),
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.stack, [99])

    def test_return_empty_stack(self):
        """RETURN 空栈时返回 UNIT"""
        fn_code = [Instruction(Op.RETURN)]
        bc = Bytecode()
        bc.functions["empty"] = _make_fn("empty", fn_code, [])
        bc.code = [
            Instruction(Op.CLOSURE, "empty", 0),
            Instruction(Op.CALL, 0),
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.stack, [UNIT])

    def test_call_builtin_partial(self):
        """内置函数部分应用"""
        abs_fn = NovaBuiltinFn("abs", lambda *a: abs(a[0]), 1)
        partial = NovaPartialBuiltin(abs_fn, [])
        # 部分应用 0 个参数时 arity 不变
        self.assertEqual(partial.arity, 1)

    def test_call_constructor(self):
        """调用 NovaConstructor 构造 ADT 值"""
        ctor = NovaConstructor("Option", "Some", 1)
        bc = Bytecode()
        bc.code = [
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.MAKE_ADT, "Option", "Some", 1),
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        val = vm.stack[0]
        self.assertIsInstance(val, NovaADTValue)
        self.assertEqual(val.variant_name, "Some")
        self.assertEqual(val.fields, [42])

    def test_call_non_function(self):
        """调用非函数值抛出 RuntimeError_"""
        bc = Bytecode()
        bc.code = [
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.CONST_INT, 0),
            Instruction(Op.CALL, 0),  # 栈顶是 0 不是闭包
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("无法调用", str(ctx.exception))

    def test_nested_call(self):
        """嵌套函数调用"""
        inner_code = [
            Instruction(Op.LOAD_VAR, "x"),
            Instruction(Op.CONST_INT, 1),
            Instruction(Op.ADD),
            Instruction(Op.RETURN),
        ]
        outer_code = [
            Instruction(Op.CLOSURE, "inc", 1),
            Instruction(Op.LOAD_VAR, "y"),
            Instruction(Op.CALL, 1),
            Instruction(Op.RETURN),
        ]
        bc = Bytecode()
        bc.functions["inc"] = _make_fn("inc", inner_code, ["x"])
        bc.functions["outer"] = _make_fn("outer", outer_code, ["y"])
        bc.code = [
            Instruction(Op.CLOSURE, "outer", 1),
            Instruction(Op.CONST_INT, 5),
            Instruction(Op.CALL, 1),  # outer(5)
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.stack, [6])


# ============================================================
# 数据结构
# ============================================================


class TestVMDataStructures(unittest.TestCase):
    """测试列表、元组、字典、索引、字段访问等指令"""

    def test_build_list(self):
        """BUILD_LIST 构造列表"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 1),
            Instruction(Op.CONST_INT, 2),
            Instruction(Op.CONST_INT, 3),
            Instruction(Op.BUILD_LIST, 3),
        )
        self.assertEqual(vm.stack, [[1, 2, 3]])

    def test_build_empty_list(self):
        """BUILD_LIST 构造空列表"""
        vm = _run_bc(Instruction(Op.BUILD_LIST, 0))
        self.assertEqual(vm.stack, [[]])

    def test_build_tuple(self):
        """BUILD_TUPLE 构造元组"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 1),
            Instruction(Op.CONST_STRING, "a"),
            Instruction(Op.BUILD_TUPLE, 2),
        )
        self.assertEqual(vm.stack, [(1, "a")])

    def test_build_map(self):
        """BUILD_MAP 构造字典"""
        vm = _run_bc(
            Instruction(Op.CONST_STRING, "a"),
            Instruction(Op.CONST_INT, 1),
            Instruction(Op.CONST_STRING, "b"),
            Instruction(Op.CONST_INT, 2),
            Instruction(Op.BUILD_MAP, 2),
        )
        self.assertEqual(vm.stack, [{"a": 1, "b": 2}])

    def test_index_list(self):
        """INDEX 列表索引"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 10),
            Instruction(Op.CONST_INT, 20),
            Instruction(Op.CONST_INT, 30),
            Instruction(Op.BUILD_LIST, 3),
            Instruction(Op.CONST_INT, 1),
            Instruction(Op.INDEX),
        )
        self.assertEqual(vm.stack, [20])

    def test_index_map(self):
        """INDEX Map 索引"""
        vm = _run_bc(
            Instruction(Op.CONST_STRING, "key"),
            Instruction(Op.CONST_INT, 99),
            Instruction(Op.BUILD_MAP, 1),
            Instruction(Op.CONST_STRING, "key"),
            Instruction(Op.INDEX),
        )
        self.assertEqual(vm.stack, [99])

    def test_field_access_tuple(self):
        """FIELD_ACCESS 元组字段访问"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 10),
            Instruction(Op.CONST_INT, 20),
            Instruction(Op.BUILD_TUPLE, 2),
            Instruction(Op.FIELD_ACCESS, 1),
        )
        self.assertEqual(vm.stack, [20])

    def test_field_access_adt(self):
        """FIELD_ACCESS ADT 字段访问"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.MAKE_ADT, "Option", "Some", 1),
            Instruction(Op.FIELD_ACCESS, 0),
        )
        self.assertEqual(vm.stack, [42])

    def test_dup(self):
        """DUP 复制栈顶"""
        vm = _run_bc(Instruction(Op.CONST_INT, 42), Instruction(Op.DUP))
        self.assertEqual(vm.stack, [42, 42])

    def test_pop(self):
        """POP 弹出栈顶"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 1), Instruction(Op.CONST_INT, 2), Instruction(Op.POP)
        )
        self.assertEqual(vm.stack, [1])

    def test_build_range(self):
        """BUILD_RANGE 构造范围"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 1),
            Instruction(Op.CONST_INT, 5),
            Instruction(Op.CONST_INT, 2),
            Instruction(Op.BUILD_RANGE),
        )
        self.assertEqual(vm.stack, [("range", 1, 5, 2)])

    def test_for_iter_list(self):
        """FOR_ITER 遍历列表"""
        vm = NovaVM(Bytecode())
        vm.stack = [[10, 20], []]
        vm._op_for_iter(Instruction(Op.FOR_ITER, 99))
        # 首次迭代：压入 iterable, result_list, current_element
        self.assertEqual(len(vm.stack), 3)
        self.assertEqual(vm.stack[2], 10)


# ============================================================
# 模式匹配
# ============================================================


class TestVMPatternMatching(unittest.TestCase):
    """测试模式匹配指令"""

    def test_match_start(self):
        """MATCH_START 不崩溃"""
        vm = _run_bc(Instruction(Op.CONST_INT, 42), Instruction(Op.MATCH_START))
        self.assertEqual(vm.stack, [42])

    def test_match_test_int_match(self):
        """MATCH_TEST_INT 值匹配时不跳转"""
        bc = Bytecode()
        bc.code = [
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.MATCH_TEST_INT, 42, 3),  # value, jump_target
            Instruction(Op.CONST_INT, 1),  # 匹配时执行
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.stack, [42, 1])

    def test_match_test_int_fail(self):
        """MATCH_TEST_INT 值不匹配时跳转"""
        bc = Bytecode()
        bc.code = [
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.MATCH_TEST_INT, 99, 3),  # 不匹配，跳转到 ip=4
            Instruction(Op.CONST_INT, 1),  # 被跳过
            Instruction(Op.CONST_INT, 0),  # 跳转到这里
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.stack, [42, 0])

    def test_match_test_bool_match(self):
        """MATCH_TEST_BOOL 布尔匹配"""
        bc = Bytecode()
        bc.code = [
            Instruction(Op.CONST_BOOL, True),
            Instruction(Op.MATCH_TEST_BOOL, True, 3),
            Instruction(Op.CONST_INT, 1),
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.stack, [True, 1])

    def test_match_test_string_match(self):
        """MATCH_TEST_STRING 字符串匹配"""
        bc = Bytecode()
        bc.code = [
            Instruction(Op.CONST_STRING, "hi"),
            Instruction(Op.MATCH_TEST_STRING, "hi", 3),
            Instruction(Op.CONST_INT, 1),
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.stack, ["hi", 1])

    def test_match_wildcard(self):
        """MATCH_WILDCARD 总是通过"""
        vm = _run_bc(Instruction(Op.CONST_INT, 42), Instruction(Op.MATCH_WILDCARD))
        self.assertEqual(vm.stack, [42])

    def test_match_bind(self):
        """MATCH_BIND 将值绑定到变量"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.MATCH_BIND, "x"),
            Instruction(Op.HALT),
        )
        self.assertEqual(vm.globals["x"], 42)

    def test_match_constructor_match(self):
        """MATCH_CONSTRUCTOR 构造器名称匹配"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.MAKE_ADT, "Option", "Some", 1),
            Instruction(Op.MATCH_CONSTRUCTOR, "Some", 1, 99),
        )
        # 匹配成功：弹出 subject，将字段压栈
        self.assertEqual(vm.stack, [42])

    def test_match_end(self):
        """MATCH_END 不崩溃"""
        vm = _run_bc(Instruction(Op.CONST_INT, 42), Instruction(Op.MATCH_END))
        self.assertEqual(vm.stack, [42])

    def test_full_match_int_arm(self):
        """完整 match：整数 arm"""
        bc = Bytecode()
        bc.code = [
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.MATCH_START),
            Instruction(Op.MATCH_TEST_INT, 42, 7),
            Instruction(Op.POP),  # 匹配成功，弹出 subject
            Instruction(Op.CONST_INT, 1),
            Instruction(Op.MATCH_END),
            Instruction(Op.JUMP, 11),
            Instruction(Op.MATCH_WILDCARD),
            Instruction(Op.POP),
            Instruction(Op.CONST_INT, 0),
            Instruction(Op.MATCH_END),
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.stack, [1])


# ============================================================
# 管道与 ADT
# ============================================================


class TestVMPipeAndADT(unittest.TestCase):
    """测试管道操作和 ADT 相关指令"""

    def test_pipe_call_no_args(self):
        """PIPE_CALL 无参数管道调用"""
        fn_code = [Instruction(Op.LOAD_VAR, "x"), Instruction(Op.RETURN)]
        bc = Bytecode()
        bc.functions["identity"] = _make_fn("identity", fn_code, ["x"])
        bc.code = [
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.CLOSURE, "identity", 1),
            Instruction(Op.PIPE_CALL, 0),
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.stack, [42])

    def test_make_adt_no_fields(self):
        """MAKE_ADT 无字段构造器"""
        vm = _run_bc(Instruction(Op.MAKE_ADT, "Option", "None", 0))
        val = vm.stack[0]
        self.assertIsInstance(val, NovaADTValue)
        self.assertEqual(val.variant_name, "None")
        self.assertEqual(val.fields, [])

    def test_try_unwrap_some(self):
        """TRY_UNWRAP Some 值保持"""
        vm = _run_bc(
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.MAKE_ADT, "Option", "Some", 1),
            Instruction(Op.TRY_UNWRAP),
        )
        self.assertEqual(vm.stack[0].variant_name, "Some")

    def test_try_unwrap_none(self):
        """TRY_UNWRAP None 保持"""
        vm = _run_bc(Instruction(Op.MAKE_ADT, "Option", "None", 0), Instruction(Op.TRY_UNWRAP))
        self.assertEqual(vm.stack[0].variant_name, "None")

    def test_halt(self):
        """HALT 停止执行"""
        bc = Bytecode()
        bc.code = [
            Instruction(Op.CONST_INT, 1),
            Instruction(Op.HALT),
            Instruction(Op.CONST_INT, 2),  # 不应执行
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.stack, [1])

    def test_auto_call_main(self):
        """AUTO_CALL_MAIN 触发 run() 中自动调用 main"""
        fn_code = [
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.STORE_VAR, "result", False),
            Instruction(Op.RETURN),
        ]
        bc = Bytecode()
        bc.functions["main"] = _make_fn("main", fn_code, [])
        bc.code = [
            Instruction(Op.CLOSURE, "main", 0),
            Instruction(Op.STORE_VAR, "main", False),
            Instruction(Op.AUTO_CALL_MAIN),
            Instruction(Op.HALT),
        ]
        vm = NovaVM(bc)
        vm.run()
        self.assertEqual(vm.globals["result"], 42)

    def test_print(self):
        """PRINT 输出到 output 列表"""
        vm = _run_bc(Instruction(Op.CONST_INT, 42), Instruction(Op.PRINT))
        self.assertEqual(vm.output, ["42"])

    def test_register_ctor(self):
        """REGISTER_CTOR 注册构造器到全局"""
        vm = _run_bc(
            Instruction(Op.REGISTER_CTOR, "Option", "Some", 1, "Some"),
            Instruction(Op.STORE_VAR, "Some", False),
            Instruction(Op.HALT),
        )
        self.assertIsInstance(vm.globals["Some"], NovaConstructor)


# ============================================================
# 内置函数
# ============================================================


class TestVMBuiltins(unittest.TestCase):
    """测试 VM 内置函数实现"""

    def test_builtin_str_to_int_some(self):
        """str_to_int 成功返回 Some"""
        vm = NovaVM(Bytecode())
        result = vm.globals["str_to_int"].fn("123")
        self.assertIsInstance(result, NovaADTValue)
        self.assertEqual(result.variant_name, "Some")
        self.assertEqual(result.fields, [123])

    def test_builtin_str_to_int_none(self):
        """str_to_int 失败返回 None"""
        vm = NovaVM(Bytecode())
        result = vm.globals["str_to_int"].fn("abc")
        self.assertEqual(result.variant_name, "None")

    def test_builtin_filter(self):
        """filter 过滤列表"""
        vm = NovaVM(Bytecode())
        pred = NovaBuiltinFn("pred", lambda *a: a[0] > 2, 1)
        result = vm.globals["filter"].fn(pred, [1, 2, 3, 4])
        self.assertEqual(result, [3, 4])

    def test_builtin_map(self):
        """map 映射列表"""
        vm = NovaVM(Bytecode())
        fn = NovaBuiltinFn("double", lambda *a: a[0] * 2, 1)
        result = vm.globals["map"].fn(fn, [1, 2, 3])
        self.assertEqual(result, [2, 4, 6])

    def test_builtin_head_some(self):
        """head 非空列表返回 Some"""
        vm = NovaVM(Bytecode())
        result = vm.globals["head"].fn([1, 2])
        self.assertEqual(result.variant_name, "Some")
        self.assertEqual(result.fields, [1])

    def test_builtin_head_none(self):
        """head 空列表返回 None"""
        vm = NovaVM(Bytecode())
        result = vm.globals["head"].fn([])
        self.assertEqual(result.variant_name, "None")

    def test_builtin_tail_some(self):
        """tail 非空列表返回 Some"""
        vm = NovaVM(Bytecode())
        result = vm.globals["tail"].fn([1, 2, 3])
        self.assertEqual(result.variant_name, "Some")
        self.assertEqual(result.fields, [[2, 3]])

    def test_builtin_tail_none(self):
        """tail 空列表返回 None"""
        vm = NovaVM(Bytecode())
        result = vm.globals["tail"].fn([])
        self.assertEqual(result.variant_name, "None")

    def test_builtin_math_sqrt(self):
        """sqrt 计算平方根"""
        vm = NovaVM(Bytecode())
        result = vm.globals["sqrt"].fn(4.0)
        self.assertEqual(result, 2.0)

    def test_builtin_math_pi(self):
        """pi 返回 math.pi"""
        vm = NovaVM(Bytecode())
        result = vm.globals["pi"].fn()
        self.assertEqual(result, math.pi)


# ============================================================
# 辅助方法
# ============================================================


class TestVMHelpers(unittest.TestCase):
    """测试 VM 辅助方法"""

    def test_format_int(self):
        """_format_value 格式化整数"""
        vm = NovaVM(Bytecode())
        self.assertEqual(vm._format_value(42), "42")

    def test_format_string(self):
        """_format_value 格式化字符串"""
        vm = NovaVM(Bytecode())
        self.assertEqual(vm._format_value("hello"), "hello")

    def test_format_bool(self):
        """_format_value 格式化布尔值"""
        vm = NovaVM(Bytecode())
        self.assertEqual(vm._format_value(True), "true")
        self.assertEqual(vm._format_value(False), "false")

    def test_format_unit(self):
        """_format_value 格式化 UNIT"""
        vm = NovaVM(Bytecode())
        self.assertEqual(vm._format_value(UNIT), "()")

    def test_format_list(self):
        """_format_value 格式化列表"""
        vm = NovaVM(Bytecode())
        self.assertEqual(vm._format_value([1, 2, 3]), "[1, 2, 3]")

    def test_format_tuple(self):
        """_format_value 格式化元组"""
        vm = NovaVM(Bytecode())
        self.assertEqual(vm._format_value((1, "a")), "(1, a)")

    def test_format_adt(self):
        """_format_value 格式化 ADT 值"""
        vm = NovaVM(Bytecode())
        val = NovaADTValue("Option", "Some", [42])
        self.assertEqual(vm._format_value(val), "Some(42)")

    def test_format_closure(self):
        """_format_value 格式化闭包"""
        vm = NovaVM(Bytecode())
        closure = NovaClosure("add", 2, {})
        self.assertEqual(vm._format_value(closure), "<fn add>")

    def test_to_float_int(self):
        """_to_float 整数转浮点"""
        vm = NovaVM(Bytecode())
        self.assertEqual(vm._to_float(5), 5.0)

    def test_to_float_bool(self):
        """_to_float 布尔值保持"""
        vm = NovaVM(Bytecode())
        self.assertEqual(vm._to_float(True), True)

    def test_convert_json_to_nova_null(self):
        """_convert_json_to_nova None 转 None ADT"""
        vm = NovaVM(Bytecode())
        result = vm._convert_json_to_nova(None)
        self.assertIsInstance(result, NovaADTValue)
        self.assertEqual(result.variant_name, "None")

    def test_convert_nova_to_json_unit(self):
        """_convert_nova_to_json UNIT 转 None"""
        vm = NovaVM(Bytecode())
        self.assertIsNone(vm._convert_nova_to_json(UNIT))

    def test_convert_nova_to_json_some(self):
        """_convert_nova_to_json Some 解包"""
        vm = NovaVM(Bytecode())
        val = NovaADTValue("Option", "Some", [42])
        self.assertEqual(vm._convert_nova_to_json(val), 42)

    def test_convert_nova_to_json_adt(self):
        """_convert_nova_to_json 一般 ADT 转字典"""
        vm = NovaVM(Bytecode())
        val = NovaADTValue("Shape", "Circle", [5.0])
        result = vm._convert_nova_to_json(val)
        self.assertEqual(result["_variant"], "Circle")
        self.assertEqual(result["_fields"], [5.0])


# ============================================================
# 错误路径
# ============================================================


class TestVMErrorPaths(unittest.TestCase):
    """测试错误处理路径"""

    def test_unknown_opcode(self):
        """未知操作码抛出 RuntimeError_"""
        bc = Bytecode()
        bc.code = [Instruction("UNKNOWN_OP")]
        vm = NovaVM(bc)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("未知", str(ctx.exception))

    def test_stack_overflow(self):
        """调用深度超过限制抛出 RuntimeError_"""
        vm = NovaVM(Bytecode())
        closure = NovaClosure("rec", 0, {})
        # 手动填充 call_stack 到上限
        from nova.vm import Frame
        for _ in range(vm.MAX_CALL_DEPTH):
            vm.call_stack.append(Frame(0, 0, [], [], {}))
        with self.assertRaises(RuntimeError_) as ctx:
            vm._call_closure(closure, [])
        self.assertIn("栈溢出", str(ctx.exception))

    def test_constructor_wrong_arity(self):
        """构造器参数数量不匹配抛出 RuntimeError_"""
        ctor = NovaConstructor("Option", "Some", 1)
        vm = NovaVM(Bytecode())
        with self.assertRaises(RuntimeError_) as ctx:
            vm._call_fn(ctor, [1, 2])
        self.assertIn("参数", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
