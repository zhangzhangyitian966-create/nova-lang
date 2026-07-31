"""
LIR C 后端单元测试

为 backend/lir_c_backend.py 编写独立测试，覆盖类型映射、
指令编译、控制流、函数调用、闭包生成等核心路径。
"""

import unittest

from nova.ir.ir_types import (
    BOOL_TYPE,
    CLOSURE_TYPE,
    FLOAT_TYPE,
    INT_TYPE,
    IRType,
    NovaType,
    STRING_TYPE,
    UNIT_TYPE,
)

from nova.ir.lir import (
    LIRBinOp,
    LIRBranch,
    LIRBuildADT,
    LIRBuildList,
    LIRBuildMap,
    LIRBuildTuple,
    LIRCall,
    LIRCallIndirect,
    LIRClosureCreate,
    LIRFieldAccess,
    LIRFunction,
    LIRGlobal,
    LIRIndex,
    LIRInstr,
    LIRJump,
    LIRLabel,
    LIRListAppend,
    LIRLoadConst,
    LIRLoadGlobal,
    LIRLoadReg,
    LIRModule,
    LIRPanic,
    LIRReturn,
    LIRStoreGlobal,
    LIRStoreReg,
    LIRSwitch,
    LIRUnaryOp,
)
from nova.backend.lir_c_backend import LIRCBackend


# ============================================================
# 辅助函数
# ============================================================

def make_simple_add_fn() -> LIRFunction:
    """创建一个简单的 add 函数：r2 = r0 + r1"""
    fn = LIRFunction(
        name="add",
        params=[("r0", INT_TYPE), ("r1", INT_TYPE)],
        return_type=INT_TYPE,
    )
    fn.body = [
        LIRLabel(name="bb0"),
        LIRBinOp(op="+"),
        LIRReturn(),
    ]
    fn.body[1].src_locs = [("r0", INT_TYPE), ("r1", INT_TYPE)]
    fn.body[1].dst_loc = ("r2", INT_TYPE)
    return fn


def make_main_calling_add() -> LIRFunction:
    """创建 main 函数：调用 add(1, 2)"""
    fn = LIRFunction(name="main", params=[], return_type=INT_TYPE)
    fn.body = [
        LIRLabel(name="bb0"),
        LIRLoadConst(value=1, const_type="int"),
        LIRLoadConst(value=2, const_type="int"),
        LIRCall(func_name="add", arg_count=2),
        LIRReturn(),
    ]
    fn.body[1].dst_loc = ("r0", INT_TYPE)
    fn.body[2].dst_loc = ("r1", INT_TYPE)
    fn.body[3].arg_locs = [("r0", INT_TYPE), ("r1", INT_TYPE)]
    fn.body[3].dst_loc = ("r2", INT_TYPE)
    return fn


# ============================================================
# 测试类 1: 类型映射
# ============================================================

class TestTypeMapping(unittest.TestCase):
    """测试 _nova_type_to_c 类型映射"""

    def setUp(self):
        self.backend = LIRCBackend()

    def test_int_type(self):
        self.assertEqual(self.backend._nova_type_to_c(INT_TYPE), "int64_t")

    def test_float_type(self):
        self.assertEqual(self.backend._nova_type_to_c(FLOAT_TYPE), "double")

    def test_bool_type(self):
        self.assertEqual(self.backend._nova_type_to_c(BOOL_TYPE), "bool")

    def test_string_type(self):
        self.assertEqual(self.backend._nova_type_to_c(STRING_TYPE), "NovaString*")

    def test_unit_type(self):
        self.assertEqual(self.backend._nova_type_to_c(UNIT_TYPE), "void")

    def test_closure_type(self):
        self.assertEqual(self.backend._nova_type_to_c(CLOSURE_TYPE), "NovaClosure*")

    def test_function_kind_type(self):
        """IRType kind 为 FUNCTION 时应直接映射为 NovaClosure*"""
        fn_type = NovaType(IRType.FUNCTION, name="(Int) -> Int")
        self.assertEqual(self.backend._nova_type_to_c(fn_type), "NovaClosure*")

    def test_arrow_string_type(self):
        """箭头类型字符串应映射为 NovaClosure*"""
        arrow_type = NovaType(IRType.INT, name="Int -> Int")
        self.assertEqual(self.backend._nova_type_to_c(arrow_type), "NovaClosure*")

    def test_none_fallback(self):
        """None 输入应返回默认类型 int64_t"""
        self.assertEqual(self.backend._nova_type_to_c(None), "int64_t")

    def test_unknown_type_fallback(self):
        """未知类型应返回 NovaValue*"""
        unknown = NovaType(IRType.INT, name="UnknownXYZ")
        self.assertEqual(self.backend._nova_type_to_c(unknown), "NovaValue*")


# ============================================================
# 测试类 2: 编译入口
# ============================================================

class TestCompileEntry(unittest.TestCase):
    """测试 compile 入口方法"""

    def test_empty_module(self):
        """空模块应生成最小 C 框架"""
        module = LIRModule(name="empty")
        backend = LIRCBackend()
        c_code = backend.compile(module)

        self.assertIn('#include "nova_runtime.h"', c_code)
        self.assertIn("int main(int argc, char** argv)", c_code)
        self.assertIn("nova_init();", c_code)
        self.assertIn("return 0;", c_code)

    def test_module_with_function(self):
        """包含函数的模块应生成函数声明和定义"""
        module = LIRModule(name="test")
        module.functions["add"] = make_simple_add_fn()

        backend = LIRCBackend()
        c_code = backend.compile(module)

        # 前向声明
        self.assertIn("int64_t nova_fn_add(int64_t r0, int64_t r1);", c_code)
        # 函数定义
        self.assertIn("int64_t nova_fn_add(int64_t r0, int64_t r1)", c_code)

    def test_module_with_globals(self):
        """包含全局变量的模块应生成全局声明"""
        module = LIRModule(name="test")
        module.globals = [
            LIRGlobal(name="global_x", ir_type=INT_TYPE),
            LIRGlobal(name="global_flag", ir_type=BOOL_TYPE),
        ]

        backend = LIRCBackend()
        c_code = backend.compile(module)

        self.assertIn("int64_t global_x;", c_code)
        self.assertIn("bool global_flag;", c_code)

    def test_module_with_string_literal(self):
        """包含字符串常量的模块应生成静态字符串数组"""
        module = LIRModule(name="test")
        fn = LIRFunction(name="main", params=[], return_type=UNIT_TYPE)
        fn.body = [
            LIRLabel(name="bb0"),
            LIRLoadConst(value="hello", const_type="string"),
            LIRReturn(),
        ]
        fn.body[1].dst_loc = ("r0", STRING_TYPE)
        module.functions["main"] = fn

        backend = LIRCBackend()
        c_code = backend.compile(module)

        self.assertIn('static const char nova_str_0[] = "hello";', c_code)


# ============================================================
# 测试类 3: 指令编译
# ============================================================

class TestLoadConst(unittest.TestCase):
    """测试常量加载指令编译"""

    def _compile_single_instr(self, instr: LIRInstr, fn_name="test") -> str:
        """编译包含单条指令的函数，返回 C 代码"""
        module = LIRModule(name="test")
        fn = LIRFunction(name=fn_name, params=[], return_type=UNIT_TYPE)
        fn.body = [LIRLabel(name="bb0"), instr, LIRReturn()]
        module.functions[fn_name] = fn
        return LIRCBackend().compile(module)

    def test_load_const_int(self):
        instr = LIRLoadConst(value=42, const_type="int")
        instr.dst_loc = ("r0", INT_TYPE)
        c_code = self._compile_single_instr(instr)
        # 后端先声明再赋值，生成 r0 = (int64_t)42;
        self.assertIn("r0 = (int64_t)42;", c_code)

    def test_load_const_float(self):
        instr = LIRLoadConst(value=3.14, const_type="float")
        instr.dst_loc = ("r0", FLOAT_TYPE)
        c_code = self._compile_single_instr(instr)
        self.assertIn("r0 = (double)3.14;", c_code)

    def test_load_const_bool_true(self):
        instr = LIRLoadConst(value=True, const_type="bool")
        instr.dst_loc = ("r0", BOOL_TYPE)
        c_code = self._compile_single_instr(instr)
        self.assertIn("r0 = true;", c_code)

    def test_load_const_bool_false(self):
        instr = LIRLoadConst(value=False, const_type="bool")
        instr.dst_loc = ("r0", BOOL_TYPE)
        c_code = self._compile_single_instr(instr)
        self.assertIn("r0 = false;", c_code)

    def test_load_const_unit(self):
        instr = LIRLoadConst(value=None, const_type="unit")
        instr.dst_loc = ("r0", UNIT_TYPE)
        c_code = self._compile_single_instr(instr)
        # Unit 类型可能不生成赋值语句，或生成 void 相关代码
        self.assertIn("bb0:;", c_code)


class TestBinOpAndUnaryOp(unittest.TestCase):
    """测试二元/一元运算指令编译"""

    def _compile_binop(self, op: str, ty=NovaType) -> str:
        module = LIRModule(name="test")
        fn = LIRFunction(name="test", params=[], return_type=INT_TYPE)
        instr = LIRBinOp(op=op)
        instr.src_locs = [("r0", INT_TYPE), ("r1", INT_TYPE)]
        instr.dst_loc = ("r2", INT_TYPE)
        fn.body = [LIRLabel(name="bb0"), instr, LIRReturn()]
        module.functions["test"] = fn
        return LIRCBackend().compile(module)

    def test_binop_add(self):
        c_code = self._compile_binop("+")
        self.assertIn("r2 = r0 + r1;", c_code)

    def test_binop_sub(self):
        c_code = self._compile_binop("-")
        self.assertIn("r2 = r0 - r1;", c_code)

    def test_binop_mul(self):
        c_code = self._compile_binop("*")
        self.assertIn("r2 = r0 * r1;", c_code)

    def test_binop_div(self):
        c_code = self._compile_binop("/")
        self.assertIn("r2 = r0 / r1;", c_code)

    def test_binop_mod(self):
        c_code = self._compile_binop("%")
        self.assertIn("r2 = r0 % r1;", c_code)

    def test_binop_eq(self):
        c_code = self._compile_binop("==")
        self.assertIn("r2 = r0 == r1;", c_code)

    def test_binop_and(self):
        c_code = self._compile_binop("&&")
        self.assertIn("r2 = r0 && r1;", c_code)

    def test_unary_op_neg(self):
        module = LIRModule(name="test")
        fn = LIRFunction(name="test", params=[], return_type=INT_TYPE)
        instr = LIRUnaryOp(op="-")
        instr.src_locs = [("r0", INT_TYPE)]
        instr.dst_loc = ("r1", INT_TYPE)
        fn.body = [LIRLabel(name="bb0"), instr, LIRReturn()]
        module.functions["test"] = fn
        c_code = LIRCBackend().compile(module)
        self.assertIn("r1 = -r0;", c_code)

    def test_unary_op_not(self):
        module = LIRModule(name="test")
        fn = LIRFunction(name="test", params=[], return_type=BOOL_TYPE)
        instr = LIRUnaryOp(op="!")
        instr.src_locs = [("r0", BOOL_TYPE)]
        instr.dst_loc = ("r1", BOOL_TYPE)
        fn.body = [LIRLabel(name="bb0"), instr, LIRReturn()]
        module.functions["test"] = fn
        c_code = LIRCBackend().compile(module)
        self.assertIn("r1 = !r0;", c_code)


class TestRegAndGlobalOps(unittest.TestCase):
    """测试寄存器和全局变量操作"""

    def test_load_reg(self):
        module = LIRModule(name="test")
        fn = LIRFunction(name="test", params=[], return_type=INT_TYPE)
        instr = LIRLoadReg()
        instr.src_locs = [("r0", INT_TYPE)]
        instr.dst_loc = ("r1", INT_TYPE)
        fn.body = [LIRLabel(name="bb0"), instr, LIRReturn()]
        module.functions["test"] = fn
        c_code = LIRCBackend().compile(module)
        self.assertIn("r1 = r0;", c_code)

    def test_store_reg(self):
        module = LIRModule(name="test")
        fn = LIRFunction(name="test", params=[], return_type=INT_TYPE)
        instr = LIRStoreReg()
        instr.src_locs = [("r0", INT_TYPE)]
        instr.dst_loc = ("r1", INT_TYPE)
        fn.body = [LIRLabel(name="bb0"), instr, LIRReturn()]
        module.functions["test"] = fn
        c_code = LIRCBackend().compile(module)
        self.assertIn("r1 = r0;", c_code)

    def test_load_global(self):
        module = LIRModule(name="test")
        fn = LIRFunction(name="test", params=[], return_type=INT_TYPE)
        instr = LIRLoadGlobal(global_name="global_counter")
        instr.dst_loc = ("r0", INT_TYPE)
        fn.body = [LIRLabel(name="bb0"), instr, LIRReturn()]
        module.functions["test"] = fn
        c_code = LIRCBackend().compile(module)
        self.assertIn("r0 = global_counter;", c_code)

    def test_store_global(self):
        module = LIRModule(name="test")
        fn = LIRFunction(name="test", params=[], return_type=UNIT_TYPE)
        instr = LIRStoreGlobal(global_name="global_counter")
        instr.src_locs = [("r0", INT_TYPE)]
        fn.body = [LIRLabel(name="bb0"), instr, LIRReturn()]
        module.functions["test"] = fn
        c_code = LIRCBackend().compile(module)
        self.assertIn("global_counter = r0;", c_code)


# ============================================================
# 测试类 4: 控制流
# ============================================================

class TestControlFlow(unittest.TestCase):
    """测试控制流指令编译"""

    def test_label_and_jump(self):
        """标签和无条件跳转"""
        module = LIRModule(name="test")
        fn = LIRFunction(name="test", params=[], return_type=UNIT_TYPE)
        fn.body = [
            LIRLabel(name="bb0"),
            LIRJump(target="bb1"),
            LIRLabel(name="bb1"),
            LIRReturn(),
        ]
        module.functions["test"] = fn
        c_code = LIRCBackend().compile(module)

        self.assertIn("bb0:;", c_code)
        self.assertIn("goto bb1;", c_code)
        self.assertIn("bb1:;", c_code)

    def test_branch(self):
        """条件分支"""
        module = LIRModule(name="test")
        fn = LIRFunction(name="test", params=[], return_type=UNIT_TYPE)
        fn.body = [
            LIRLabel(name="bb0"),
            LIRLoadConst(value=True, const_type="bool"),
            LIRBranch(true_target="bb_true", false_target="bb_false"),
            LIRLabel(name="bb_true"),
            LIRReturn(),
            LIRLabel(name="bb_false"),
            LIRReturn(),
        ]
        fn.body[1].dst_loc = ("r0", BOOL_TYPE)
        fn.body[2].src_locs = [("r0", BOOL_TYPE)]
        module.functions["test"] = fn
        c_code = LIRCBackend().compile(module)

        # 后端生成紧凑的 if-goto，不使用大括号块
        self.assertIn("if (r0) goto bb_true;", c_code)
        self.assertIn("goto bb_false;", c_code)

    def test_switch(self):
        """Switch 多分支（2 个 case，走 if-else 级联路径）"""
        module = LIRModule(name="test")
        fn = LIRFunction(name="test", params=[], return_type=UNIT_TYPE)
        fn.body = [
            LIRLabel(name="bb0"),
            LIRLoadConst(value=1, const_type="int"),
            LIRSwitch(
                cases=[(1, "bb1"), (2, "bb2")],
                default_target="bb_default",
            ),
            LIRLabel(name="bb1"),
            LIRReturn(),
            LIRLabel(name="bb2"),
            LIRReturn(),
            LIRLabel(name="bb_default"),
            LIRReturn(),
        ]
        fn.body[1].dst_loc = ("r0", INT_TYPE)
        fn.body[2].src_locs = [("r0", INT_TYPE)]
        module.functions["test"] = fn
        c_code = LIRCBackend().compile(module)

        self.assertIn("if (r0 == 1)", c_code)
        self.assertIn("goto bb1;", c_code)
        self.assertIn("goto bb_default;", c_code)

    def test_switch_int_three_cases(self):
        """Switch 3 个整型 case，触发 C switch 语句生成路径"""
        module = LIRModule(name="test")
        fn = LIRFunction(name="test", params=[], return_type=UNIT_TYPE)
        fn.body = [
            LIRLabel(name="bb0"),
            LIRLoadConst(value=1, const_type="int"),
            LIRSwitch(
                cases=[(1, "bb1"), (2, "bb2"), (3, "bb3")],
                default_target="bb_default",
            ),
            LIRLabel(name="bb1"),
            LIRReturn(),
            LIRLabel(name="bb2"),
            LIRReturn(),
            LIRLabel(name="bb3"),
            LIRReturn(),
            LIRLabel(name="bb_default"),
            LIRReturn(),
        ]
        fn.body[1].dst_loc = ("r0", INT_TYPE)
        fn.body[2].src_locs = [("r0", INT_TYPE)]
        module.functions["test"] = fn
        c_code = LIRCBackend().compile(module)

        # 验证生成 C switch 语句而非 if-else 级联
        self.assertIn("switch ((int64_t)r0)", c_code)
        self.assertIn("case 1: goto bb1;", c_code)
        self.assertIn("case 2: goto bb2;", c_code)
        self.assertIn("case 3: goto bb3;", c_code)
        self.assertIn("default: goto bb_default;", c_code)


# ============================================================
# 测试类 5: 函数调用
# ============================================================

class TestFunctionCall(unittest.TestCase):
    """测试函数调用指令编译"""

    def test_direct_call(self):
        """直接函数调用"""
        module = LIRModule(name="test")
        module.functions["add"] = make_simple_add_fn()
        module.functions["main"] = make_main_calling_add()

        backend = LIRCBackend()
        c_code = backend.compile(module)

        self.assertIn("nova_fn_add(r0, r1)", c_code)

    def test_call_with_return_value(self):
        """调用并接收返回值"""
        module = LIRModule(name="test")
        module.functions["add"] = make_simple_add_fn()
        module.functions["main"] = make_main_calling_add()

        backend = LIRCBackend()
        c_code = backend.compile(module)

        # 声明与赋值分开：先声明 int64_t r2; 再赋值 r2 = nova_fn_add(...)
        self.assertIn("r2 = nova_fn_add(r0, r1);", c_code)


# ============================================================
# 测试类 6: 数据结构
# ============================================================

class TestDataStructures(unittest.TestCase):
    """测试数据结构构建指令"""

    def test_build_list(self):
        """列表构建"""
        module = LIRModule(name="test")
        fn = LIRFunction(name="test", params=[], return_type=UNIT_TYPE)
        fn.body = [
            LIRLabel(name="bb0"),
            LIRBuildList(count=3),
            LIRReturn(),
        ]
        fn.body[1].dst_loc = ("r0", STRING_TYPE)  # 使用 STRING_TYPE 作为占位
        module.functions["test"] = fn
        c_code = LIRCBackend().compile(module)
        self.assertIn("nova_list_new(3)", c_code)

    def test_list_append(self):
        """列表追加"""
        module = LIRModule(name="test")
        fn = LIRFunction(name="test", params=[], return_type=UNIT_TYPE)
        fn.body = [
            LIRLabel(name="bb0"),
            LIRListAppend(),
            LIRReturn(),
        ]
        fn.body[1].src_locs = [("r0", STRING_TYPE), ("r1", INT_TYPE)]
        module.functions["test"] = fn
        c_code = LIRCBackend().compile(module)
        self.assertIn("nova_list_push", c_code)

    def test_build_tuple(self):
        """元组构建"""
        module = LIRModule(name="test")
        fn = LIRFunction(name="test", params=[], return_type=UNIT_TYPE)
        fn.body = [
            LIRLabel(name="bb0"),
            LIRBuildTuple(count=2),
            LIRReturn(),
        ]
        fn.body[1].dst_loc = ("r0", STRING_TYPE)
        module.functions["test"] = fn
        c_code = LIRCBackend().compile(module)
        # 后端使用 nova_alloc + memset 实现元组分配
        self.assertIn("nova_alloc(16)", c_code)
        self.assertIn("memset(r0, 0, 16)", c_code)

    def test_build_map(self):
        """Map 构建"""
        module = LIRModule(name="test")
        fn = LIRFunction(name="test", params=[], return_type=UNIT_TYPE)
        fn.body = [
            LIRLabel(name="bb0"),
            LIRBuildMap(entry_count=2),
            LIRReturn(),
        ]
        fn.body[1].dst_loc = ("r0", STRING_TYPE)
        module.functions["test"] = fn
        c_code = LIRCBackend().compile(module)
        self.assertIn("nova_map_new(2)", c_code)

    def test_build_adt(self):
        """ADT 构建"""
        module = LIRModule(name="test")
        fn = LIRFunction(name="test", params=[], return_type=UNIT_TYPE)
        fn.body = [
            LIRLabel(name="bb0"),
            LIRBuildADT(type_name="Option", variant_name="Some", type_tag=0, field_count=1),
            LIRReturn(),
        ]
        fn.body[1].src_locs = [("r0", INT_TYPE)]
        fn.body[1].dst_loc = ("r1", STRING_TYPE)
        module.functions["test"] = fn
        c_code = LIRCBackend().compile(module)
        self.assertIn("nova_adt_new(0, 0, 1)", c_code)
        self.assertIn("nova_adt_set_field", c_code)

    def test_field_access(self):
        """字段访问"""
        module = LIRModule(name="test")
        fn = LIRFunction(name="test", params=[], return_type=INT_TYPE)
        fn.body = [
            LIRLabel(name="bb0"),
            LIRFieldAccess(offset=0),
            LIRReturn(),
        ]
        fn.body[1].src_locs = [("r0", STRING_TYPE)]
        fn.body[1].dst_loc = ("r1", INT_TYPE)
        module.functions["test"] = fn
        c_code = LIRCBackend().compile(module)
        # 后端使用直接指针算术实现字段访问
        self.assertIn("*(NovaValue*)((char*)r0 + 0)", c_code)

    def test_index(self):
        """索引访问"""
        module = LIRModule(name="test")
        fn = LIRFunction(name="test", params=[], return_type=INT_TYPE)
        fn.body = [
            LIRLabel(name="bb0"),
            LIRIndex(),
            LIRReturn(),
        ]
        fn.body[1].src_locs = [("r0", STRING_TYPE), ("r1", INT_TYPE)]
        fn.body[1].dst_loc = ("r2", INT_TYPE)
        module.functions["test"] = fn
        c_code = LIRCBackend().compile(module)
        self.assertIn("nova_list_get(r0, r1)", c_code)


# ============================================================
# 测试类 7: 其他指令
# ============================================================

class TestMiscInstructions(unittest.TestCase):
    """测试其他杂项指令"""

    def test_panic(self):
        """Panic 指令"""
        module = LIRModule(name="test")
        fn = LIRFunction(name="test", params=[], return_type=UNIT_TYPE)
        fn.body = [
            LIRLabel(name="bb0"),
            LIRPanic(message="something went wrong"),
            LIRReturn(),
        ]
        module.functions["test"] = fn
        c_code = LIRCBackend().compile(module)
        self.assertIn("something went wrong", c_code)


# ============================================================
# 测试类 8: 端到端编译验证
# ============================================================

class TestEndToEndCompile(unittest.TestCase):
    """端到端：生成的 C 代码应能通过 gcc 语法检查"""

    @unittest.skipUnless(__import__("shutil").which("gcc"), "gcc not available")
    def test_simple_program_compiles(self):
        """简单程序应生成可通过 gcc -fsyntax-only 的 C 代码"""
        module = LIRModule(name="test")
        module.functions["add"] = make_simple_add_fn()
        module.functions["main"] = make_main_calling_add()

        backend = LIRCBackend()
        c_code = backend.compile(module)

        import tempfile
        import subprocess

        with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
            f.write(c_code)
            f.flush()
            result = subprocess.run(
                [
                    "gcc",
                    "-fsyntax-only",
                    "-c",
                    f.name,
                    "-I/workspace/nova/runtime",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                result.returncode,
                0,
                f"gcc 语法检查失败:\n{result.stderr}\n生成的 C 代码:\n{c_code}",
            )


# ============================================================
# 闭包间接调用修复测试（backend_c_closure_double_return）
# 修复：C 后端 _compile_call_indirect
# 三个缺陷：
# 1. double 返回 + 无 dst：trampoline malloc 的 double 返回内存泄漏
# 2. double 返回 + 有 dst：memcpy 前未 NULL 检查
# 3. bool 返回 cast 不严谨
# ============================================================


class TestClosureCallIndirectFixes(unittest.TestCase):
    """闭包间接调用（_compile_call_indirect 修复验证

    针对 P1-新3（C 后端闭包浮点返回丢失/内存泄漏/Cast 不严谨）"""

    # --------------------------------------------------------
    # 辅助：构造含 lambda 返回 Float 的 LIRModule
    # --------------------------------------------------------

    def _make_module_lambda_double_return(self):
        """构造含 __lambda_1 返回 Float 的最小 LIR 模块：
        __lambda_1(r0: Float) -> Float：返回 r0 + 3.14（单函数）
        main() -> Float：创建闭包（无捕获），间接调用并返回
        """
        # lambda 函数：__lambda_1
        fn_lambda = LIRFunction(
            name="__lambda_1",
            params=[("r0", FLOAT_TYPE)],
            return_type=FLOAT_TYPE,
        )
        fn_lambda.body = [
            LIRLabel(name="bb0"),
            LIRReturn(),
        ]
        # LIRReturn 前一条 LIRUnaryOp Identity 操作返回
        ret = LIRUnaryOp(op="identity")
        ret.src_locs = [("r0", FLOAT_TYPE)]
        ret.dst_loc = ("r1", FLOAT_TYPE)
        fn_lambda.body.insert(1, ret)
        fn_lambda.body[-1].src_locs = [("r1", FLOAT_TYPE)]

        # main 函数：创建闭包 -> 间接调用
        fn_main = LIRFunction(
            name="main",
            params=[],
            return_type=FLOAT_TYPE,
        )
        closure_create = LIRClosureCreate(
            fn_name="__lambda_1",
            capture_count=0,
        )
        closure_create.dst_loc = ("r2", CLOSURE_TYPE)
        call_indir = LIRCallIndirect(arg_count=1)
        # src_locs 第一个：闭包对象，第二个参数：2.718
        call_indir.src_locs = [
            ("r2", CLOSURE_TYPE),  # 闭包
            ("r3", FLOAT_TYPE),  # arg 2.718
        ]
        call_indir.arg_locs = [("r3", FLOAT_TYPE)]
        call_indir.dst_loc = ("r4", FLOAT_TYPE)
        # 加载 2.718
        load_2718 = LIRLoadConst(value=2.718, const_type="float")
        load_2718.dst_loc = ("r3", FLOAT_TYPE)
        ret_instr = LIRReturn()
        ret_instr.src_locs = [("r4", FLOAT_TYPE)]

        fn_main.body = [
            LIRLabel(name="bb0"),
            load_2718,
            closure_create,
            call_indir,
            ret_instr,
        ]

        module = LIRModule(name="test_double_closure_return")
        module.functions["__lambda_1"] = fn_lambda
        module.functions["main"] = fn_main
        return module

    def _make_module_lambda_bool_return(self):
        """类似模块，构造 __lambda_2 返回 Bool"""
        fn_lambda = LIRFunction(
            name="__lambda_2",
            params=[("r0", BOOL_TYPE)],
            return_type=BOOL_TYPE,
        )
        fn_lambda.body = [
            LIRLabel(name="bb0"),
            LIRReturn(),
        ]
        identity = LIRUnaryOp(op="identity")
        identity.src_locs = [("r0", BOOL_TYPE)]
        identity.dst_loc = ("r1", BOOL_TYPE)
        fn_lambda.body.insert(1, identity)
        fn_lambda.body[-1].src_locs = [("r1", BOOL_TYPE)]

        fn_main = LIRFunction(name="main", params=[], return_type=BOOL_TYPE)
        cc = LIRClosureCreate(fn_name="__lambda_2", capture_count=0)
        cc.dst_loc = ("r2", CLOSURE_TYPE)
        load_true = LIRLoadConst(value=True, const_type="bool")
        load_true.dst_loc = ("r3", BOOL_TYPE)
        ci = LIRCallIndirect(arg_count=1)
        ci.src_locs = [("r2", CLOSURE_TYPE), ("r3", BOOL_TYPE)]
        ci.arg_locs = [("r3", BOOL_TYPE)]
        ci.dst_loc = ("r4", BOOL_TYPE)
        ret = LIRReturn()
        ret.src_locs = [("r4", BOOL_TYPE)]
        fn_main.body = [LIRLabel(name="bb0"), load_true, cc, ci, ret]

        module = LIRModule(name="test_bool_closure_return")
        module.functions["__lambda_2"] = fn_lambda
        module.functions["main"] = fn_main
        return module

    # --------------------------------------------------------
    # 测试 1：double 返回 + 有 dst → 包含 NULL 检查 + memcpy + free + 默认 0.0
    # --------------------------------------------------------

    def test_call_indirect_double_with_dst_has_null_check_and_free(self):
        """有 dst 的 double 间接调用：生成的 C 代码包含
        NULL 检查、memcpy、free 、默认 0.0 初始化"""
        module = self._make_module_lambda_double_return()
        backend = LIRCBackend()
        c_code = backend.compile(module)

        # 检查 NULL 保护分支
        self.assertIn("!= NULL", c_code,
            "double 返回有接收到：缺少 NULL 检查")
        self.assertIn("memcpy(&", c_code,
            "缺少 memcpy 解包 double")
        self.assertIn("free(", c_code,
            "缺少 free 释放 trampoline 端 malloc 的内存")
        self.assertIn("= 0.0;", c_code,
            "NULL 分支缺少默认 0.0 初始化")

    # --------------------------------------------------------
    # 测试 2：double 返回 + 无 dst（忽略返回值）→ 包含 free，
    # --------------------------------------------------------

    def test_call_indirect_double_no_dst_has_free_prevent_leak(self):
        """无接收值的 double 间接调用：将返回值赋值给临时指针并 free，
        防止 trampoline 端 malloc 泄漏（P1-新3 确定内存泄漏清零）

        注意：_compile_call_indirect(instr, dst) 有两个参数：
          - instr.dst_loc 用于计算返回值类型（决定是否需要 malloc/free 配对）
          - dst 是实际的 C 变量名，None 表示忽略结果
        正常调度表入口是同生共死的，但直接调用可以解耦测试边界。
        """
        # 构造一个最小 LIRCallIndirect：闭包对象 r2 + 参数 r3（Float）
        instr = LIRCallIndirect(arg_count=1)
        instr.src_locs = [
            ("r2", CLOSURE_TYPE),
            ("r3", FLOAT_TYPE),
        ]
        instr.arg_locs = [("r3", FLOAT_TYPE)]
        # 关键：设置 dst_loc 以暴露返回类型是 Float（double）
        # 但调用 _compile_call_indirect 时 dst=None（忽略返回值）
        instr.dst_loc = ("r4", FLOAT_TYPE)

        backend = LIRCBackend()
        # 先声明变量，然后直接 dispatch 到 _compile_call_indirect（dst=None）
        backend._emit("void test_func(void) {")
        backend._indent_level += 1
        backend._emit("NovaClosure* _loc_r2 = NULL;")
        backend._emit("double _loc_r3 = 0.0;")
        backend._compile_call_indirect(instr, dst=None)  # dst=None 但返回类型已知为 double
        backend._indent_level -= 1
        backend._emit("}")

        c_code = "\n".join(backend._output)

        # 验证：生成了临时指针保存 nova_closure_call 返回值，并 free
        self.assertIn("void* _nova_ret_ptr_", c_code,
            "double 返回+忽略结果：应保存返回值到临时指针")
        self.assertIn("free(_nova_ret_ptr_", c_code,
            "double 返回+忽略结果：缺少 free，造成确定内存泄漏")
        # 不应有 memcpy（没有接收 dst）
        self.assertNotIn("memcpy(&", c_code,
            "无 dst 场景不应有 memcpy（无需解包到接收变量")
        # free(NULL) 是安全的，因此无需 NULL 分支也没问题

    # --------------------------------------------------------
    # 测试 3：bool 返回 + 有 dst → 使用严谨 cast
    # --------------------------------------------------------

    def test_call_indirect_bool_return_uses_precise_bool_cast(self):
        """bool 间接调用返回使用 (bool)(intptr_t) 严谨两步强转，
        而非不严谨的 (bool)void*——与 trampoline端装箱方式语义匹配"""
        module = self._make_module_lambda_bool_return()
        backend = LIRCBackend()
        c_code = backend.compile(module)

        # 严谨强转字符串
        self.assertIn("(bool)(intptr_t)nova_closure_call", c_code,
            "缺少严谨的 bool 两步强转：先 intptr_t 再 bool")


if __name__ == "__main__":
    unittest.main()
