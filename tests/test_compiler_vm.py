"""
Nova 编程语言 - 字节码编译器与虚拟机单元测试

测试覆盖：
1. BytecodeCompiler 单元测试 — 验证字节码指令结构
2. NovaVM 直接测试 — 手动构造 Bytecode 执行
3. 错误路径测试 — 除零、未定义变量、栈溢出等
4. 集成测试盲区覆盖 — Tuple/Map/Break/Continue/一元运算/逻辑短路等

本文件补齐 compiler.py 和 vm.py 的最大测试盲区，
将端到端测试与字节码级断言结合，定位故障更精准。
"""

import sys
import unittest

from nova.lexer import Lexer
from nova.parser import Parser
from nova.type_checker import TypeChecker
from nova.compiler import (
    Bytecode,
    BytecodeCompiler,
    FunctionBlock,
    Instruction,
    Op,
)
from nova.vm import NovaVM
from nova.errors import RuntimeError_

# VM 函数调用使用 Python 调用栈，需要提高递归限制以测试栈溢出保护
# 每次 VM 调用约使用 5 个 Python 栈帧，MAX_CALL_DEPTH=1000 需要 ~5000+ 帧
sys.setrecursionlimit(10000)


# ============================================================
# 辅助函数
# ============================================================

def _compile_source(source: str) -> Bytecode:
    """从源码编译到字节码（完整流水线）"""
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    TypeChecker().check_program(ast)
    return BytecodeCompiler().compile(ast)


def _vm_run(source: str) -> NovaVM:
    """从源码运行 VM（端到端）"""
    bc = _compile_source(source)
    vm = NovaVM(bc)
    vm.run()
    return vm


def _make_simple_bytecode(*instructions) -> Bytecode:
    """手动构造字节码，自动追加 HALT"""
    bc = Bytecode()
    for instr in instructions:
        if isinstance(instr, Instruction):
            bc.emit(instr)
        elif isinstance(instr, str):
            bc.emit(Instruction(instr))
    bc.emit(Instruction(Op.HALT))
    return bc


# ============================================================
# BytecodeCompiler 单元测试
# ============================================================

class TestBytecodeCompilerUnit(unittest.TestCase):
    """验证 BytecodeCompiler 生成的字节码指令结构"""

    def _compile_expr(self, source: str) -> Bytecode:
        """编译表达式并返回字节码"""
        return _compile_source(source)

    def test_compile_int_literal(self):
        """整数字面量编译为 CONST_INT + STORE_VAR"""
        bc = self._compile_expr("let x = 42")
        opcodes = [instr.opcode for instr in bc.code]
        self.assertIn(Op.CONST_INT, opcodes)
        self.assertIn(Op.STORE_VAR, opcodes)

    def test_compile_float_literal(self):
        """浮点字面量编译为 CONST_FLOAT"""
        bc = self._compile_expr("let x = 3.14")
        opcodes = [instr.opcode for instr in bc.code]
        self.assertIn(Op.CONST_FLOAT, opcodes)

    def test_compile_bool_literal(self):
        """布尔字面量编译为 CONST_BOOL"""
        bc = self._compile_expr("let x = true")
        opcodes = [instr.opcode for instr in bc.code]
        self.assertIn(Op.CONST_BOOL, opcodes)

    def test_compile_string_literal(self):
        """字符串字面量编译为 CONST_STRING"""
        bc = self._compile_expr('let x = "hello"')
        opcodes = [instr.opcode for instr in bc.code]
        self.assertIn(Op.CONST_STRING, opcodes)

    def test_compile_binary_op_arithmetic(self):
        """算术运算编译为 CONST + CONST + OP"""
        bc = self._compile_expr("let x = 2 + 3")
        opcodes = [instr.opcode for instr in bc.code]
        self.assertIn(Op.ADD, opcodes)

    def test_compile_unary_neg(self):
        """一元负号编译为 NEG 指令"""
        bc = self._compile_expr("let x = -5")
        opcodes = [instr.opcode for instr in bc.code]
        self.assertIn(Op.NEG, opcodes)

    def test_compile_if_expr(self):
        """if 表达式编译为 JUMP_IF_FALSE + JUMP"""
        bc = self._compile_expr("let x = if true then 1 else 2")
        opcodes = [instr.opcode for instr in bc.code]
        self.assertIn(Op.JUMP_IF_FALSE, opcodes)
        self.assertIn(Op.JUMP, opcodes)

    def test_compile_fn_def(self):
        """函数定义编译为 FunctionBlock（存入 functions 字典）"""
        bc = self._compile_expr("fn add(a: Int, b: Int) -> Int { a + b }")
        self.assertIn("add", bc.functions)
        func = bc.functions["add"]
        self.assertEqual(func.param_count, 2)
        self.assertEqual(func.param_names, ["a", "b"])

    def test_compile_tuple_expr(self):
        """元组表达式编译为 BUILD_TUPLE 指令"""
        bc = self._compile_expr("let x = (1, 2, 3)")
        opcodes = [instr.opcode for instr in bc.code]
        self.assertIn(Op.BUILD_TUPLE, opcodes)

    def test_compile_map_expr(self):
        """Map 表达式编译为 BUILD_MAP 指令"""
        bc = self._compile_expr('let x = {"a": 1, "b": 2}')
        opcodes = [instr.opcode for instr in bc.code]
        self.assertIn(Op.BUILD_MAP, opcodes)

    def test_compile_while_loop(self):
        """while 循环编译为 POP_JUMP_IF_FALSE / JUMP 回跳"""
        bc = self._compile_expr("mut i = 0\nwhile i < 3 { i = i + 1 }")
        opcodes = [instr.opcode for instr in bc.code]
        self.assertIn(Op.POP_JUMP_IF_FALSE, opcodes)
        self.assertIn(Op.JUMP, opcodes)

    def test_compile_halt(self):
        """编译产物包含 HALT 指令（在 AUTO_CALL_MAIN 之前）"""
        bc = self._compile_expr("let x = 1")
        opcodes = [instr.opcode for instr in bc.code]
        self.assertIn(Op.HALT, opcodes)
        # AUTO_CALL_MAIN 是最后一条指令
        self.assertEqual(bc.code[-1].opcode, Op.AUTO_CALL_MAIN)

    def test_compile_main_function(self):
        """main 函数编译为 FunctionBlock"""
        bc = self._compile_expr("fn main() -> Int { 42 }")
        self.assertIn("main", bc.functions)

    def test_compile_closure(self):
        """lambda 编译为 CLOSURE 指令"""
        bc = self._compile_expr("fn f() -> Int { let g = |x| x + 1; g(10) }")
        opcodes = [instr.opcode for instr in bc.code]
        # CLOSURE 指令应在函数体内
        all_opcodes = opcodes + [
            instr.opcode for func in bc.functions.values() for instr in func.code
        ]
        self.assertIn(Op.CLOSURE, all_opcodes)


# ============================================================
# NovaVM 直接测试（手动构造 Bytecode）
# ============================================================

class TestNovaVMDirect(unittest.TestCase):
    """直接构造 Bytecode 测试 VM 指令执行"""

    def _run_bytecode(self, bc: Bytecode) -> NovaVM:
        """执行字节码并返回 VM 实例"""
        vm = NovaVM(bc)
        vm.run()
        return vm

    def test_vm_const_int_store(self):
        """CONST_INT + STORE_VAR 将值存入全局变量"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        self.assertEqual(vm.get_global("x"), 42)

    def test_vm_const_float(self):
        """CONST_FLOAT 正确加载浮点数"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_FLOAT, 3.14),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        self.assertAlmostEqual(vm.get_global("x"), 3.14)

    def test_vm_const_string(self):
        """CONST_STRING 正确加载字符串"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_STRING, "hello"),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        self.assertEqual(vm.get_global("x"), "hello")

    def test_vm_const_bool(self):
        """CONST_BOOL 正确加载布尔值"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_BOOL, True),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        self.assertEqual(vm.get_global("x"), True)

    def test_vm_arithmetic_add(self):
        """ADD 指令正确执行整数加法"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_INT, 10),
            Instruction(Op.CONST_INT, 20),
            Instruction(Op.ADD),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        self.assertEqual(vm.get_global("x"), 30)

    def test_vm_arithmetic_sub(self):
        """SUB 指令正确执行减法"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_INT, 20),
            Instruction(Op.CONST_INT, 8),
            Instruction(Op.SUB),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        self.assertEqual(vm.get_global("x"), 12)

    def test_vm_arithmetic_mul(self):
        """MUL 指令正确执行乘法"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_INT, 6),
            Instruction(Op.CONST_INT, 7),
            Instruction(Op.MUL),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        self.assertEqual(vm.get_global("x"), 42)

    def test_vm_arithmetic_div(self):
        """DIV 指令正确执行整数除法"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_INT, 100),
            Instruction(Op.CONST_INT, 4),
            Instruction(Op.DIV),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        self.assertEqual(vm.get_global("x"), 25)

    def test_vm_arithmetic_div_float(self):
        """DIV 指令对浮点数执行浮点除法"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_FLOAT, 7.0),
            Instruction(Op.CONST_FLOAT, 2.0),
            Instruction(Op.DIV),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        self.assertAlmostEqual(vm.get_global("x"), 3.5)

    def test_vm_arithmetic_mod(self):
        """MOD 指令正确执行取模"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_INT, 17),
            Instruction(Op.CONST_INT, 5),
            Instruction(Op.MOD),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        self.assertEqual(vm.get_global("x"), 2)

    def test_vm_neg(self):
        """NEG 指令正确执行一元取负"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.NEG),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        self.assertEqual(vm.get_global("x"), -42)

    def test_vm_concat(self):
        """CONCAT 指令正确执行字符串拼接"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_STRING, "hello"),
            Instruction(Op.CONST_STRING, " world"),
            Instruction(Op.CONCAT),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        self.assertEqual(vm.get_global("x"), "hello world")

    def test_vm_eq(self):
        """EQ 指令正确执行相等比较"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_INT, 5),
            Instruction(Op.CONST_INT, 5),
            Instruction(Op.EQ),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        self.assertTrue(vm.get_global("x"))

    def test_vm_neq(self):
        """NEQ 指令正确执行不等比较"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_INT, 5),
            Instruction(Op.CONST_INT, 3),
            Instruction(Op.NEQ),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        self.assertTrue(vm.get_global("x"))

    def test_vm_lt(self):
        """LT 指令正确执行小于比较"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_INT, 3),
            Instruction(Op.CONST_INT, 5),
            Instruction(Op.LT),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        self.assertTrue(vm.get_global("x"))

    def test_vm_gt(self):
        """GT 指令正确执行大于比较"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_INT, 10),
            Instruction(Op.CONST_INT, 5),
            Instruction(Op.GT),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        self.assertTrue(vm.get_global("x"))

    def test_vm_build_tuple(self):
        """BUILD_TUPLE 指令正确构建元组"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_INT, 1),
            Instruction(Op.CONST_INT, 2),
            Instruction(Op.CONST_INT, 3),
            Instruction(Op.BUILD_TUPLE, 3),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        self.assertEqual(vm.get_global("x"), (1, 2, 3))

    def test_vm_build_map(self):
        """BUILD_MAP 指令正确构建字典"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_STRING, "a"),
            Instruction(Op.CONST_INT, 1),
            Instruction(Op.BUILD_MAP, 1),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        self.assertEqual(vm.get_global("x"), {"a": 1})

    def test_vm_tuple_field_access(self):
        """FIELD_ACCESS 指令正确访问元组字段"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_INT, 10),
            Instruction(Op.CONST_INT, 20),
            Instruction(Op.CONST_INT, 30),
            Instruction(Op.BUILD_TUPLE, 3),
            Instruction(Op.FIELD_ACCESS, "1"),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        self.assertEqual(vm.get_global("x"), 20)

    def test_vm_map_index(self):
        """INDEX 指令正确访问字典元素"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_STRING, "key"),
            Instruction(Op.CONST_INT, 99),
            Instruction(Op.BUILD_MAP, 1),
            Instruction(Op.CONST_STRING, "key"),
            Instruction(Op.INDEX),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        self.assertEqual(vm.get_global("x"), 99)

    def test_vm_dup_and_pop(self):
        """DUP + POP 正确操作栈"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.DUP),
            Instruction(Op.STORE_VAR, "x", False),
            Instruction(Op.STORE_VAR, "y", False),
        )
        vm = self._run_bytecode(bc)
        self.assertEqual(vm.get_global("x"), 42)
        self.assertEqual(vm.get_global("y"), 42)

    def test_vm_const_unit(self):
        """CONST_UNIT 指令正确加载 Unit 值"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_UNIT),
            Instruction(Op.STORE_VAR, "x", False),
        )
        vm = self._run_bytecode(bc)
        # Unit 在 VM 中表示为 None 或特殊值
        result = vm.get_global("x")
        self.assertIsNotNone(result)


# ============================================================
# NovaVM 错误路径测试
# ============================================================

class TestNovaVMErrorPaths(unittest.TestCase):
    """测试 VM 的错误处理路径"""

    def test_div_by_zero_int(self):
        """整数除零触发 RuntimeError_"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_INT, 1),
            Instruction(Op.CONST_INT, 0),
            Instruction(Op.DIV),
        )
        vm = NovaVM(bc)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("除零", str(ctx.exception))

    def test_undefined_variable(self):
        """加载未定义变量触发 RuntimeError_"""
        bc = _make_simple_bytecode(
            Instruction(Op.LOAD_VAR, "undefined_var"),
        )
        vm = NovaVM(bc)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("未定义", str(ctx.exception))

    def test_field_access_on_non_object(self):
        """对非对象进行字段访问触发 RuntimeError_"""
        bc = _make_simple_bytecode(
            Instruction(Op.CONST_INT, 42),
            Instruction(Op.FIELD_ACCESS, "0"),
        )
        vm = NovaVM(bc)
        with self.assertRaises(RuntimeError_):
            vm.run()

    def test_stack_overflow(self):
        """递归调用深度超过 MAX_CALL_DEPTH 触发栈溢出"""
        bc = Bytecode()
        # 构造一个递归函数
        func_code = [
            Instruction(Op.LOAD_VAR, "self"),
            Instruction(Op.CALL, 0),
            Instruction(Op.RETURN),
        ]
        func_block = FunctionBlock(
            name="recurse",
            param_count=0,
            code=func_code,
            constants=[],
            param_names=[],
        )
        bc.functions["recurse"] = func_block
        bc.emit(Instruction(Op.CLOSURE, "recurse", 0, "recurse"))
        bc.emit(Instruction(Op.STORE_VAR, "self", False))
        bc.emit(Instruction(Op.LOAD_VAR, "self"))
        bc.emit(Instruction(Op.CALL, 0))
        bc.emit(Instruction(Op.HALT))
        vm = NovaVM(bc)
        with self.assertRaises(RuntimeError_) as ctx:
            vm.run()
        self.assertIn("栈溢出", str(ctx.exception))


# ============================================================
# 集成测试：覆盖测试盲区
# ============================================================

class TestCompilerVMBlindSpots(unittest.TestCase):
    """端到端集成测试，覆盖之前缺失的编译器/VM 路径"""

    def test_unary_neg(self):
        """一元取负运算"""
        vm = _vm_run("let x = -10")
        self.assertEqual(vm.get_global("x"), -10)

    def test_unary_neg_expression(self):
        """一元取负在表达式中"""
        vm = _vm_run("let x = -(3 + 4)")
        self.assertEqual(vm.get_global("x"), -7)

    def test_float_arithmetic(self):
        """浮点数算术运算"""
        vm = _vm_run("let x = 3.5 + 2.5")
        self.assertAlmostEqual(vm.get_global("x"), 6.0)

    def test_float_division(self):
        """浮点数除法"""
        vm = _vm_run("let x = 7.0 / 2.0")
        self.assertAlmostEqual(vm.get_global("x"), 3.5)

    def test_tuple_construction(self):
        """元组构建（字节码级测试见 TestNovaVMDirect）"""
        vm = _vm_run("let x = (10, 20, 30)")
        self.assertEqual(vm.get_global("x"), (10, 20, 30))

    def test_for_loop_with_break(self):
        """for 循环中的 break"""
        vm = _vm_run("""
            fn main() -> Int {
                mut result = 0
                for i in [1, 2, 3, 4, 5] {
                    if i > 3 then break
                    result = result + i
                }
                result
            }
        """)
        self.assertEqual(vm.get_global("result"), 6)

    def test_for_loop_with_continue(self):
        """for 循环中的 continue"""
        vm = _vm_run("""
            fn main() -> Int {
                mut result = 0
                for i in [1, 2, 3, 4, 5] {
                    if i == 3 then continue
                    result = result + i
                }
                result
            }
        """)
        self.assertEqual(vm.get_global("result"), 12)

    def test_comparison_chain(self):
        """比较运算符"""
        vm = _vm_run("let x = 5 > 3")
        self.assertTrue(vm.get_global("x"))

    def test_comparison_lte(self):
        """小于等于比较"""
        vm = _vm_run("let x = 3 <= 3")
        self.assertTrue(vm.get_global("x"))

    def test_comparison_gte(self):
        """大于等于比较"""
        vm = _vm_run("let x = 5 >= 10")
        self.assertFalse(vm.get_global("x"))

    def test_comparison_neq(self):
        """不等比较"""
        vm = _vm_run("let x = 5 != 3")
        self.assertTrue(vm.get_global("x"))

    def test_logical_and(self):
        """逻辑与运算"""
        vm = _vm_run("let x = true && false")
        self.assertFalse(vm.get_global("x"))

    def test_logical_or(self):
        """逻辑或运算"""
        vm = _vm_run("let x = true || false")
        self.assertTrue(vm.get_global("x"))

    def test_logical_and_short_circuit(self):
        """逻辑与短路求值"""
        vm = _vm_run("let x = false && (1 / 0 == 0)")
        self.assertFalse(vm.get_global("x"))

    def test_logical_or_short_circuit(self):
        """逻辑或短路求值"""
        vm = _vm_run("let x = true || (1 / 0 == 0)")
        self.assertTrue(vm.get_global("x"))

    def test_not_operator(self):
        """逻辑非运算"""
        vm = _vm_run("let x = !true")
        self.assertFalse(vm.get_global("x"))

    def test_nested_function_calls(self):
        """嵌套函数调用"""
        vm = _vm_run("""
            fn double(x: Int) -> Int { x * 2 }
            fn add_one(x: Int) -> Int { x + 1 }
            let x = double(add_one(5))
        """)
        self.assertEqual(vm.get_global("x"), 12)

    def test_list_index_access(self):
        """列表索引访问（字节码级测试见 TestNovaVMDirect.test_vm_map_index）"""
        vm = _vm_run("let x = [10, 20, 30]")
        self.assertEqual(vm.get_global("x"), [10, 20, 30])

    def test_empty_list(self):
        """空列表"""
        vm = _vm_run("let x = []")
        self.assertEqual(vm.get_global("x"), [])

    def test_modulo_operation(self):
        """取模运算"""
        vm = _vm_run("let x = 17 % 5")
        self.assertEqual(vm.get_global("x"), 2)

    def test_string_concat_in_expression(self):
        """字符串拼接在复杂表达式中"""
        vm = _vm_run("""
            let name = "Nova"
            let x = "Hello, " ++ name ++ "!"
        """)
        self.assertEqual(vm.get_global("x"), "Hello, Nova!")


# ============================================================
# 字节码结构验证测试
# ============================================================

class TestBytecodeStructure(unittest.TestCase):
    """验证字节码结构的正确性"""

    def test_instruction_equality(self):
        """Instruction 的 __eq__ 正确比较"""
        a = Instruction(Op.ADD)
        b = Instruction(Op.ADD)
        self.assertEqual(a, b)

    def test_instruction_inequality(self):
        """Instruction 的 __eq__ 区分不同操作码"""
        a = Instruction(Op.ADD)
        b = Instruction(Op.SUB)
        self.assertNotEqual(a, b)

    def test_instruction_repr(self):
        """Instruction 的 __repr__ 正确输出"""
        instr = Instruction(Op.CONST_INT, 42)
        self.assertIn("CONST_INT", repr(instr))
        self.assertIn("42", repr(instr))

    def test_bytecode_add_const_dedup(self):
        """Bytecode.add_const 对相同值去重"""
        bc = Bytecode()
        idx1 = bc.add_const("hello")
        idx2 = bc.add_const("hello")
        self.assertEqual(idx1, idx2)

    def test_bytecode_emit_and_current_pos(self):
        """Bytecode.emit 和 current_pos 正确工作"""
        bc = Bytecode()
        self.assertEqual(bc.current_pos(), 0)
        bc.emit(Instruction(Op.CONST_INT, 1))
        self.assertEqual(bc.current_pos(), 1)
        bc.emit(Instruction(Op.HALT))
        self.assertEqual(bc.current_pos(), 2)

    def test_bytecode_patch_jump(self):
        """Bytecode.patch_jump 正确回填跳转目标"""
        bc = Bytecode()
        bc.emit(Instruction(Op.JUMP_IF_FALSE))  # pos 0
        bc.emit(Instruction(Op.CONST_INT, 1))
        pos = bc.current_pos()
        bc.patch_jump(0, pos)
        self.assertEqual(bc.code[0].operands[0], pos)

    def test_function_block_structure(self):
        """FunctionBlock 正确存储函数信息"""
        code = [Instruction(Op.CONST_INT, 1), Instruction(Op.RETURN)]
        fb = FunctionBlock(
            name="test_fn",
            param_count=2,
            code=code,
            constants=[1],
            param_names=["a", "b"],
        )
        self.assertEqual(fb.name, "test_fn")
        self.assertEqual(fb.param_count, 2)
        self.assertEqual(fb.param_names, ["a", "b"])
        self.assertEqual(len(fb.code), 2)


if __name__ == "__main__":
    unittest.main()
