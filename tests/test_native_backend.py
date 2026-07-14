import unittest
import sys
import os
import struct

from nova.backend.x86_64 import (
    X86_64Emitter, RAX, RBX, RCX, RDX, RSP, RBP, RDI, RSI,
    R8, R9, R10, R11, R12, R13, R14, R15,
    XMM0, XMM1, CALLER_SAVED, CALLEE_SAVED, ARG_REGS, RETURN_REG,
)
from nova.backend.native_backend import (
    NativeCodeGen, LinearScanAllocator, LiveInterval,
    SimpleNativeCompiler,
)

# 直接导入 IR 节点
from nova.ir.ir_nodes import (
    LIRModule, LIRFunction, LIRLoadConst, LIRReturn,
    LIRCall, LIRBranch, LIRJump, LIRLabel,
    LIRLoadGlobal, LIRStoreGlobal, LIRLoadReg, LIRStoreReg,
    LIRCallIndirect, LIRIndex, LIRFieldAccess,
    LIRBuildList, LIRBuildTuple, LIRBuildADT, LIRBinOp, LIRUnaryOp,
    LIRGlobal, LIRData, LIRPanic,
    IRType, NovaType,
    INT_TYPE, FLOAT_TYPE, STRING_TYPE, BOOL_TYPE, UNIT_TYPE,
)


class TestX86_64Emitter(unittest.TestCase):
    """x86_64 指令编码测试"""

    def test_mov_reg_imm64_small(self):
        """mov rax, 42 -- 使用 REX.W + C7 (mov r/m64, imm32) 零扩展编码"""
        e = X86_64Emitter()
        e.mov_reg_imm64(RAX, 42)
        code = e.get_code()
        # REX.W=0x48, opcode=0xC7, ModR/M=0xC0 (reg field 0, r/m=RAX=0)
        self.assertEqual(code[0], 0x48)    # REX.W
        self.assertEqual(code[1], 0xC7)    # MOV r/m64, imm32
        self.assertEqual(code[2], 0xC0)    # ModR/M: mod=11, reg=0, rm=0
        self.assertEqual(struct.unpack('<I', code[3:7])[0], 42)

    def test_mov_reg_imm64_large(self):
        """mov rax, 0xFFFFFFFF -- 超过 0x7FFFFFFF，使用 B8+rd + imm64"""
        e = X86_64Emitter()
        e.mov_reg_imm64(RAX, 0xFFFFFFFF)
        code = e.get_code()
        # REX.W=0x48, opcode=0xB8 (mov rax, imm64), 8字节立即数
        self.assertEqual(code[0], 0x48)    # REX.W
        self.assertEqual(code[1], 0xB8)    # MOV rax, imm64
        self.assertEqual(struct.unpack('<Q', code[2:10])[0], 0xFFFFFFFF)

    def test_mov_reg_reg(self):
        """mov rax, rbx"""
        e = X86_64Emitter()
        e.mov_reg_reg64(RAX, RBX)
        code = e.get_code()
        self.assertEqual(code[0], 0x48)  # REX.W
        self.assertEqual(code[1], 0x89)  # MOV r/m64, r64
        # ModR/M: mod=11, reg(src=RBX=3), rm(dst=RAX=0) = 0b11_011_000 = 0xD8
        self.assertEqual(code[2], 0xD8)

    def test_add_reg_reg(self):
        """add rax, rcx"""
        e = X86_64Emitter()
        e.add_reg_reg(RAX, RCX)
        code = e.get_code()
        self.assertEqual(code[0], 0x48)  # REX.W
        self.assertEqual(code[1], 0x01)  # ADD r/m64, r64
        # ModR/M: mod=11, reg(src=RCX=1), rm(dst=RAX=0) = 0b11_001_000 = 0xC8
        self.assertEqual(code[2], 0xC8)

    def test_sub_reg_reg(self):
        """sub rax, rdx"""
        e = X86_64Emitter()
        e.sub_reg_reg(RAX, RDX)
        code = e.get_code()
        self.assertEqual(code[0], 0x48)  # REX.W
        self.assertEqual(code[1], 0x29)  # SUB r/m64, r64
        # ModR/M: mod=11, reg(src=RDX=2), rm(dst=RAX=0) = 0b11_010_000 = 0xD0
        self.assertEqual(code[2], 0xD0)

    def test_imul_reg_reg(self):
        """imul rax, rcx"""
        e = X86_64Emitter()
        e.imul_reg_reg(RAX, RCX)
        code = e.get_code()
        self.assertEqual(code[0], 0x48)  # REX.W
        self.assertEqual(code[1], 0x0F)  # two-byte opcode
        self.assertEqual(code[2], 0xAF)  # IMUL r64, r/m64
        # ModR/M: mod=11, reg(dst=RAX=0), rm(src=RCX=1) = 0b11_000_001 = 0xC1
        self.assertEqual(code[3], 0xC1)

    def test_push_pop(self):
        """push rbx; pop rbx"""
        e = X86_64Emitter()
        e.push_reg(RBX)
        e.pop_reg(RBX)
        code = e.get_code()
        self.assertEqual(code[0], 0x53)  # push rbx
        self.assertEqual(code[1], 0x5B)  # pop rbx

    def test_ret(self):
        """ret"""
        e = X86_64Emitter()
        e.ret()
        self.assertEqual(e.get_code()[0], 0xC3)

    def test_jmp_rel32(self):
        """jmp rel32"""
        e = X86_64Emitter()
        e.jmp_rel32()
        self.assertEqual(e.get_code()[0], 0xE9)

    def test_call_rel32(self):
        """call rel32"""
        e = X86_64Emitter()
        e.call_rel32()
        self.assertEqual(e.get_code()[0], 0xE8)

    def test_cmp_reg_reg(self):
        """cmp rax, rbx"""
        e = X86_64Emitter()
        e.cmp_reg_reg(RAX, RBX)
        code = e.get_code()
        self.assertEqual(code[0], 0x48)  # REX.W
        self.assertEqual(code[1], 0x39)  # CMP r/m64, r64

    def test_neg_reg(self):
        """neg rax"""
        e = X86_64Emitter()
        e.neg_reg(RAX)
        code = e.get_code()
        self.assertEqual(code[0], 0x48)  # REX.W
        self.assertEqual(code[1], 0xF7)  # NEG group
        self.assertEqual(code[2], 0xD8)  # ModR/M: mod=11, /3, rm=RAX=0

    def test_idiv(self):
        """cqo; idiv rcx"""
        e = X86_64Emitter()
        e.cqo()
        e.idiv_reg(RCX)
        code = e.get_code()
        self.assertEqual(code[0], 0x48)  # REX.W (cqo)
        self.assertEqual(code[1], 0x99)  # cqo
        self.assertEqual(code[2], 0x48)  # REX.W (idiv)
        self.assertEqual(code[3], 0xF7)  # IDIV group
        self.assertEqual(code[4], 0xF9)  # ModR/M: mod=11, /7, rm=RCX=1

    def test_sub_rsp(self):
        """sub rsp, 32"""
        e = X86_64Emitter()
        e.sub_rsp_imm(32)
        code = e.get_code()
        self.assertEqual(code[0], 0x48)  # REX.W
        self.assertEqual(code[1], 0x83)  # SUB r/m64, imm8
        self.assertEqual(code[2], 0xEC)  # ModR/M: mod=11, /5, rm=RSP=4
        self.assertEqual(code[3], 32)

    def test_add_rsp(self):
        """add rsp, 32"""
        e = X86_64Emitter()
        e.add_rsp_imm(32)
        code = e.get_code()
        self.assertEqual(code[0], 0x48)  # REX.W
        self.assertEqual(code[1], 0x83)  # ADD r/m64, imm8
        self.assertEqual(code[2], 0xC4)  # ModR/M: mod=11, /0, rm=RSP=4
        self.assertEqual(code[3], 32)

    def test_syscall(self):
        """syscall"""
        e = X86_64Emitter()
        e.syscall()
        self.assertEqual(e.get_code()[0], 0x0F)
        self.assertEqual(e.get_code()[1], 0x05)

    def test_xorpd_zero(self):
        """xorpd xmm0, xmm0"""
        e = X86_64Emitter()
        e.xorpd_xmm(XMM0)
        code = e.get_code()
        self.assertEqual(code[0], 0x66)  # prefix
        self.assertEqual(code[1], 0x0F)  # two-byte opcode
        self.assertEqual(code[2], 0x57)  # XORPD

    def test_extended_registers(self):
        """mov r8, r9"""
        e = X86_64Emitter()
        e.mov_reg_reg64(R8, R9)
        code = e.get_code()
        # 需要 REX 前缀（r=1, b=1）
        self.assertEqual(code[0], 0x4D)  # REX.WRB
        self.assertEqual(code[1], 0x89)  # MOV r/m64, r64

    def test_patch_rel32(self):
        """回填跳转偏移"""
        e = X86_64Emitter()
        e.nop()       # offset 0, opcode 0x90
        jmp_pos = e.jmp_rel32()  # offset 1 (E9), offset 2-5 (placeholder)
        e.nop()       # offset 6, opcode 0x90
        target = 2    # 跳到第 2 个字节（nop 本身）
        e.patch_rel32(jmp_pos, target)
        code = e.get_code()
        # rel32 = target - (jmp_pos + 4) = 2 - (2 + 4) = -4
        rel = struct.unpack('<i', code[jmp_pos:jmp_pos+4])[0]
        self.assertEqual(rel, -4)

    def test_emit_bytes_multiple(self):
        """emit_bytes 批量写入"""
        e = X86_64Emitter()
        e.emit_bytes(0x48, 0x89, 0xD8)
        code = e.get_code()
        self.assertEqual(len(code), 3)
        self.assertEqual(code[0], 0x48)
        self.assertEqual(code[1], 0x89)
        self.assertEqual(code[2], 0xD8)

    def test_mov_reg_mem_positive_offset(self):
        """mov rax, [rbx + 16]"""
        e = X86_64Emitter()
        e.mov_reg_mem(RAX, RBX, 16)
        code = e.get_code()
        self.assertEqual(code[0], 0x48)  # REX.W
        self.assertEqual(code[1], 0x8B)  # MOV r64, r/m64
        self.assertEqual(code[2], 0x43)  # ModR/M: mod=01, reg=RAX, rm=RBX
        self.assertEqual(code[3], 16)

    def test_mov_reg_mem_large_offset(self):
        """mov rax, [rbx + 1000]"""
        e = X86_64Emitter()
        e.mov_reg_mem(RAX, RBX, 1000)
        code = e.get_code()
        self.assertEqual(code[0], 0x48)  # REX.W
        self.assertEqual(code[1], 0x8B)  # MOV r64, r/m64
        self.assertEqual(code[2], 0x83)  # ModR/M: mod=10, reg=RAX, rm=RBX
        offset_val = struct.unpack('<i', code[3:7])[0]
        self.assertEqual(offset_val, 1000)

    def test_and_or_xor(self):
        """and, or, xor 指令编码"""
        e = X86_64Emitter()
        e.and_reg_reg(RAX, RBX)
        e.or_reg_reg(RAX, RBX)
        e.xor_reg_reg(RAX, RBX)
        code = e.get_code()
        # 每条指令 3 字节: REX.W(0x48) + opcode + ModR/M
        self.assertEqual(code[0], 0x48)  # AND REX.W
        self.assertEqual(code[1], 0x21)  # AND opcode
        self.assertEqual(code[2], 0xD8)  # AND ModR/M
        self.assertEqual(code[3], 0x48)  # OR REX.W
        self.assertEqual(code[4], 0x09)  # OR opcode
        self.assertEqual(code[5], 0xD8)  # OR ModR/M
        self.assertEqual(code[6], 0x48)  # XOR REX.W
        self.assertEqual(code[7], 0x31)  # XOR opcode
        self.assertEqual(code[8], 0xD8)  # XOR ModR/M

    def test_setcc_instructions(self):
        """setcc 指令编码"""
        e = X86_64Emitter()
        e.sete(RAX)
        e.setne(RCX)
        e.setl(RDX)
        code = e.get_code()
        self.assertEqual(code[0], 0x0F)  # SETE
        self.assertEqual(code[1], 0x94)
        self.assertEqual(code[2], 0xC0)  # ModR/M: reg=0, rm=RAX
        self.assertEqual(code[3], 0x0F)  # SETNE
        self.assertEqual(code[4], 0x95)
        self.assertEqual(code[5], 0xC1)  # ModR/M: reg=0, rm=RCX=1
        self.assertEqual(code[6], 0x0F)  # SETL
        self.assertEqual(code[7], 0x9C)
        self.assertEqual(code[8], 0xC2)  # ModR/M: reg=0, rm=RDX=2

    def test_test_reg_reg(self):
        """test rax, rax"""
        e = X86_64Emitter()
        e.test_reg_reg(RAX, RAX)
        code = e.get_code()
        self.assertEqual(code[0], 0x48)  # REX.W
        self.assertEqual(code[1], 0x85)  # TEST r/m64, r64
        self.assertEqual(code[2], 0xC0)  # ModR/M: mod=11, reg=RAX, rm=RAX

    def test_je_rel32(self):
        """je rel32"""
        e = X86_64Emitter()
        e.je_rel32()
        code = e.get_code()
        self.assertEqual(code[0], 0x0F)
        self.assertEqual(code[1], 0x84)


class TestLinearScanAllocator(unittest.TestCase):
    """线性扫描寄存器分配器测试"""

    def test_basic_allocation(self):
        """基本分配"""
        intervals = [
            LiveInterval("v0", 0, 10),
            LiveInterval("v1", 5, 15),
            LiveInterval("v2", 0, 5),  # v0 和 v2 重叠但 v2 在 v0 结束前结束
        ]
        alloc = LinearScanAllocator([RAX, RBX, RCX])
        result, slots = alloc.allocate(intervals)
        self.assertIsNotNone(result.get("v0"))
        self.assertIsNotNone(result.get("v1"))
        self.assertIsNotNone(result.get("v2"))
        # v0 和 v2 重叠
        self.assertNotEqual(result.get("v0"), result.get("v2"))

    def test_spill_when_full(self):
        """溢出处理"""
        intervals = [
            LiveInterval("v0", 0, 100),
            LiveInterval("v1", 0, 100),
            LiveInterval("v2", 0, 100),
            LiveInterval("v3", 0, 100),
        ]
        alloc = LinearScanAllocator([RAX, RBX])  # 只有 2 个寄存器
        result, slots = alloc.allocate(intervals)
        # 前两个分配到寄存器，后两个溢出到栈
        self.assertEqual(slots, 2)

    def test_no_intervals(self):
        """空输入"""
        alloc = LinearScanAllocator([RAX, RBX])
        result, slots = alloc.allocate([])
        self.assertEqual(slots, 0)
        self.assertEqual(len(result), 0)

    def test_non_overlapping_intervals(self):
        """不重叠的区间应能复用寄存器"""
        intervals = [
            LiveInterval("v0", 0, 5),
            LiveInterval("v1", 5, 10),  # v0 结束后 v1 才开始
        ]
        alloc = LinearScanAllocator([RAX])
        result, slots = alloc.allocate(intervals)
        # 两个区间不重叠，应能复用同一寄存器
        self.assertEqual(result.get("v0"), result.get("v1"))
        self.assertEqual(slots, 0)  # 无溢出


class TestNativeCodeGen(unittest.TestCase):
    """原生代码生成器测试"""

    def test_elf_header(self):
        """ELF 头生成"""
        codegen = NativeCodeGen()
        header = codegen._make_elf_header(entry=0x400100, phoff=64, phnum=1)
        self.assertEqual(header[0:4], b'\x7fELF')
        self.assertEqual(header[4], 2)  # 64-bit
        self.assertEqual(header[5], 1)  # little-endian
        self.assertEqual(header[16:18], struct.pack('<H', 2))  # ET_EXEC
        self.assertEqual(header[18:20], struct.pack('<H', 62))  # EM_X86_64

    def test_program_header(self):
        """Program Header 生成"""
        codegen = NativeCodeGen()
        ph = codegen._make_program_header(
            p_type=1, p_offset=0, p_vaddr=0x400000, p_paddr=0x400000,
            p_filesz=100, p_memsz=100, p_flags=5, p_align=0x1000
        )
        self.assertEqual(len(ph), 56)  # ELF64 Phdr size
        p_type = struct.unpack('<I', ph[0:4])[0]
        self.assertEqual(p_type, 1)  # PT_LOAD

    def test_simple_function(self):
        """简单函数编译"""
        codegen = NativeCodeGen()

        lir = LIRModule(name="test")
        fn = LIRFunction("add", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=10, const_type="int"),
            LIRReturn(),
        ]
        lir.functions["add"] = fn

        # 编译（生成代码，不写文件）
        code = codegen._compile_function(fn)
        self.assertIsInstance(code, bytes)
        self.assertTrue(len(code) > 0)
        # 应包含 push (callee-saved) 和 ret
        self.assertIn(0xC3, code)  # ret opcode

    def test_basic_arithmetic(self):
        """算术运算编译"""
        e = X86_64Emitter()
        # mov rax, 10
        e.mov_reg_imm64(RAX, 10)
        # mov rcx, 3
        e.mov_reg_imm64(RCX, 3)
        # imul rax, rcx  (result: 30)
        e.imul_reg_reg(RAX, RCX)
        # ret
        e.ret()

        code = e.get_code()
        self.assertTrue(len(code) > 0)

    def test_collect_constants(self):
        """常量收集测试"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("main", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=3.14, const_type="float"),
            LIRLoadConst(value="hello", const_type="string"),
            LIRReturn(),
        ]
        lir.functions["main"] = fn

        codegen._collect_constants(lir)
        # 应收集到 1 个浮点常量和 1 个字符串常量
        self.assertEqual(len(codegen.float_constants), 1)
        self.assertEqual(len(codegen.string_constants), 1)
        self.assertEqual(codegen.float_constants[0][0],
                         struct.pack('<d', 3.14))
        self.assertEqual(codegen.string_constants[0][0],
                         b'hello\x00')

    def test_float_constant_compilation(self):
        """浮点常量加载编译：应生成 movsd (RIP-relative)"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("main", [], FLOAT_TYPE)
        fn.body = [
            LIRLoadConst(value=2.718, const_type="float"),
            LIRReturn(),
        ]
        lir.functions["main"] = fn

        codegen._collect_constants(lir)
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)
        # movsd 指令以 F2 前缀开头
        self.assertIn(0xF2, code)

    def test_string_constant_compilation(self):
        """字符串常量加载编译：应生成 lea (RIP-relative)"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("main", [], STRING_TYPE)
        fn.body = [
            LIRLoadConst(value="nova", const_type="string"),
            LIRReturn(),
        ]
        lir.functions["main"] = fn

        codegen._collect_constants(lir)
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)
        # lea 指令 opcode 为 8D
        self.assertIn(0x8D, code)

    def test_branch_compilation(self):
        """条件分支编译：应生成 test + jne + jmp"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("main", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=1, const_type="int"),
            LIRBranch(cond_reg="", true_label="then", false_label="else"),
            LIRLabel(name="then"),
            LIRLoadConst(value=42, const_type="int"),
            LIRJump(target="end"),
            LIRLabel(name="else"),
            LIRLoadConst(value=0, const_type="int"),
            LIRLabel(name="end"),
            LIRReturn(),
        ]
        lir.functions["main"] = fn

        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)
        # test 指令 (REX.W + 85)
        self.assertIn(0x85, code)
        # jne rel32 (0F 85)
        found_jne = False
        for i in range(len(code) - 1):
            if code[i] == 0x0F and code[i + 1] == 0x85:
                found_jne = True
                break
        self.assertTrue(found_jne, "Expected jne_rel32 (0F 85) in compiled code")

    def test_call_integer_args(self):
        """函数调用整型参数传递：应移动到 RDI, RSI, ..."""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")

        callee = LIRFunction("callee", [], INT_TYPE)
        callee.body = [LIRReturn()]
        lir.functions["callee"] = callee

        caller = LIRFunction("caller", [], INT_TYPE)
        caller.body = [
            LIRLoadConst(value=10, const_type="int"),
            LIRLoadConst(value=20, const_type="int"),
            LIRLoadConst(value=30, const_type="int"),
        ]
        call = LIRCall(func_name="callee", arg_count=3)
        call.src_locs = [
            ("const_10", INT_TYPE),
            ("const_20", INT_TYPE),
            ("const_30", INT_TYPE),
        ]
        caller.body.append(call)
        caller.body.append(LIRReturn())
        lir.functions["caller"] = caller

        code = codegen._compile_function(caller)
        self.assertTrue(len(code) > 0)
        # 应包含 mov 指令（参数移动到 ARG_REGS）
        # mov_reg_reg64 编码为 REX.W + 89 + ModR/M
        found_mov = False
        for i in range(len(code) - 2):
            if code[i] == 0x48 and code[i + 1] == 0x89:
                found_mov = True
                break
        self.assertTrue(found_mov, "Expected mov_reg_reg64 (48 89) for argument passing")

    def test_call_float_args(self):
        """函数调用浮点参数传递：应移动到 XMM0-XMM7"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")

        callee = LIRFunction("callee", [], FLOAT_TYPE)
        callee.body = [LIRReturn()]
        lir.functions["callee"] = callee

        caller = LIRFunction("caller", [], FLOAT_TYPE)
        caller.body = [
            LIRLoadConst(value=1.5, const_type="float"),
            LIRLoadConst(value=2.5, const_type="float"),
        ]
        call = LIRCall(func_name="callee", arg_count=2)
        call.src_locs = [
            ("fconst_1.5", FLOAT_TYPE),
            ("fconst_2.5", FLOAT_TYPE),
        ]
        caller.body.append(call)
        caller.body.append(LIRReturn())
        lir.functions["caller"] = caller

        codegen._collect_constants(lir)
        code = codegen._compile_function(caller)
        self.assertTrue(len(code) > 0)
        # 应包含 movsd_reg_reg (F2 0F 10)
        found_movsd = False
        for i in range(len(code) - 2):
            if code[i] == 0xF2 and code[i + 1] == 0x0F and code[i + 2] == 0x10:
                found_movsd = True
                break
        self.assertTrue(found_movsd, "Expected movsd_reg_reg (F2 0F 10) for float argument passing")

    def test_call_mixed_args(self):
        """函数调用混合参数：整型和浮点参数分别计数"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")

        callee = LIRFunction("callee", [], INT_TYPE)
        callee.body = [LIRReturn()]
        lir.functions["callee"] = callee

        caller = LIRFunction("caller", [], INT_TYPE)
        caller.body = [
            LIRLoadConst(value=1, const_type="int"),
            LIRLoadConst(value=1.5, const_type="float"),
            LIRLoadConst(value=2, const_type="int"),
        ]
        call = LIRCall(func_name="callee", arg_count=3)
        call.src_locs = [
            ("const_1", INT_TYPE),
            ("fconst_1.5", FLOAT_TYPE),
            ("const_2", INT_TYPE),
        ]
        caller.body.append(call)
        caller.body.append(LIRReturn())
        lir.functions["caller"] = caller

        codegen._collect_constants(lir)
        code = codegen._compile_function(caller)
        self.assertTrue(len(code) > 0)
        # 应同时包含整型 mov 和浮点 movsd
        found_mov = False
        found_movsd = False
        for i in range(len(code) - 2):
            if code[i] == 0x48 and code[i + 1] == 0x89:
                found_mov = True
            if code[i] == 0xF2 and code[i + 1] == 0x0F and code[i + 2] == 0x10:
                found_movsd = True
        self.assertTrue(found_mov, "Expected integer mov for mixed args")
        self.assertTrue(found_movsd, "Expected movsd for mixed args")

    def test_call_stack_args(self):
        """函数调用栈参数：超出 6 个整型寄存器限制的参数应压栈"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")

        callee = LIRFunction("callee", [], INT_TYPE)
        callee.body = [LIRReturn()]
        lir.functions["callee"] = callee

        caller = LIRFunction("caller", [], INT_TYPE)
        caller.body = []
        arg_locs = []
        for i in range(8):
            caller.body.append(LIRLoadConst(value=i + 1, const_type="int"))
            arg_locs.append((f"const_{i + 1}", INT_TYPE))

        call = LIRCall(func_name="callee", arg_count=8)
        call.src_locs = arg_locs
        caller.body.append(call)
        caller.body.append(LIRReturn())
        lir.functions["caller"] = caller

        code = codegen._compile_function(caller)
        self.assertTrue(len(code) > 0)
        # 超出 6 个的参数应通过 push 指令压栈
        # push_reg 编码：50 + reg 或 41 50 + reg
        found_push = False
        for b in code:
            if 0x50 <= b <= 0x57 or b == 0x41:
                # 简化检查：push 指令范围
                found_push = True
                break
        self.assertTrue(found_push, "Expected push instruction for stack arguments")


class TestEndToEndNative(unittest.TestCase):
    """端到端测试"""

    def test_minimal_elf(self):
        """最小 ELF 生成"""
        codegen = NativeCodeGen()

        lir = LIRModule(name="minimal")
        fn = LIRFunction("main", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=0, const_type="int"),
            LIRReturn(),
        ]
        lir.functions["main"] = fn

        elf = codegen.compile(lir)
        self.assertEqual(elf[0:4], b'\x7fELF')
        # ELF header(64) + 3 program headers(56*3=168) + code
        self.assertTrue(len(elf) > 128)

    def test_exit_program(self):
        """生成 exit(42) 程序的 ELF"""
        e = X86_64Emitter()
        # mov rdi, 42     (exit code)
        e.mov_reg_imm64(RDI, 42)
        # mov rax, 60     (syscall number: exit)
        e.mov_reg_imm64(RAX, 60)
        # syscall
        e.syscall()

        code = e.get_code()

        # 构建 ELF
        codegen = NativeCodeGen()
        header = codegen._make_elf_header(
            entry=0x400078, phoff=64, phnum=1
        )
        ph = codegen._make_program_header(
            p_type=1, p_offset=0, p_vaddr=0x400000, p_paddr=0x400000,
            p_filesz=len(code), p_memsz=len(code), p_flags=5, p_align=0x1000
        )

        elf = bytearray(header)
        elf.extend(ph)
        elf.extend(code)

        # 验证 ELF 格式
        self.assertEqual(elf[0:4], b'\x7fELF')

    def test_elf_header_size(self):
        """ELF 头大小应为 64 字节"""
        codegen = NativeCodeGen()
        header = codegen._make_elf_header(entry=0, phoff=64, phnum=0)
        self.assertEqual(len(header), 64)

    def test_program_header_size(self):
        """Program Header 大小应为 56 字节"""
        codegen = NativeCodeGen()
        ph = codegen._make_program_header(
            p_type=1, p_offset=0, p_vaddr=0, p_paddr=0,
            p_filesz=0, p_memsz=0, p_flags=0, p_align=0
        )
        self.assertEqual(len(ph), 56)


class TestNativeBackendUnimplemented(unittest.TestCase):
    """原生后端未实现功能测试 -- 仍应抛出 NotImplementedError 的指令"""

    def _compile_body_with_instr(self, instr):
        """辅助方法：编译包含指定指令的函数体"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_fn", [], INT_TYPE)
        fn.body = [instr, LIRReturn()]
        lir.functions["test_fn"] = fn
        codegen._compile_function(fn)

    def test_call_indirect_not_implemented(self):
        """LIRCallIndirect 应抛出 NotImplementedError"""
        with self.assertRaises(NotImplementedError):
            self._compile_body_with_instr(LIRCallIndirect())

    def test_index_not_implemented(self):
        """LIRIndex 应抛出 NotImplementedError"""
        with self.assertRaises(NotImplementedError):
            self._compile_body_with_instr(LIRIndex())

    def test_field_access_not_implemented(self):
        """LIRFieldAccess 应抛出 NotImplementedError"""
        with self.assertRaises(NotImplementedError):
            self._compile_body_with_instr(LIRFieldAccess(offset=0))

    def test_unknown_unaryop_not_implemented(self):
        """未知的 LIRUnaryOp 操作符应抛出 NotImplementedError"""
        instr = LIRUnaryOp(op="~")
        with self.assertRaises(NotImplementedError):
            self._compile_body_with_instr(instr)

    def test_unknown_const_type_not_implemented(self):
        """未知的 LIRLoadConst 常量类型应抛出 NotImplementedError"""
        instr = LIRLoadConst(value=(), const_type="unit")
        with self.assertRaises(NotImplementedError):
            self._compile_body_with_instr(instr)

    def test_simple_native_compiler_source_not_implemented(self):
        """SimpleNativeCompiler.compile_source 应抛出 NotImplementedError"""
        compiler = SimpleNativeCompiler()
        with self.assertRaises(NotImplementedError):
            compiler.compile_source("let x = 1", "/tmp/test")


# ============================================================
# 已实现的新特性测试
# ============================================================

class TestComparisonOps(unittest.TestCase):
    """比较运算编译测试"""

    def _compile_comparison(self, op):
        """辅助：编译包含指定比较运算的函数"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_cmp", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=10, const_type="int"),
            LIRLoadConst(value=20, const_type="int"),
            LIRBinOp(op=op),
            LIRReturn(),
        ]
        lir.functions["test_cmp"] = fn
        return codegen._compile_function(fn)

    def test_eq_compilation(self):
        """== 比较应生成 cmp + sete 指令"""
        code = self._compile_comparison("==")
        self.assertTrue(len(code) > 0)
        # sete = 0F 94
        found = False
        for i in range(len(code) - 1):
            if code[i] == 0x0F and code[i + 1] == 0x94:
                found = True
                break
        self.assertTrue(found, "Expected sete (0F 94) for == comparison")

    def test_neq_compilation(self):
        """!= 比较应生成 cmp + setne 指令"""
        code = self._compile_comparison("!=")
        self.assertTrue(len(code) > 0)
        # setne = 0F 95
        found = False
        for i in range(len(code) - 1):
            if code[i] == 0x0F and code[i + 1] == 0x95:
                found = True
                break
        self.assertTrue(found, "Expected setne (0F 95) for != comparison")

    def test_lt_compilation(self):
        """< 比较应生成 cmp + setl 指令"""
        code = self._compile_comparison("<")
        self.assertTrue(len(code) > 0)
        # setl = 0F 9C
        found = False
        for i in range(len(code) - 1):
            if code[i] == 0x0F and code[i + 1] == 0x9C:
                found = True
                break
        self.assertTrue(found, "Expected setl (0F 9C) for < comparison")

    def test_gt_compilation(self):
        """> 比较应生成 cmp + setg 指令"""
        code = self._compile_comparison(">")
        self.assertTrue(len(code) > 0)
        # setg = 0F 9F
        found = False
        for i in range(len(code) - 1):
            if code[i] == 0x0F and code[i + 1] == 0x9F:
                found = True
                break
        self.assertTrue(found, "Expected setg (0F 9F) for > comparison")

    def test_le_compilation(self):
        """<= 比较应生成 cmp + setle 指令"""
        code = self._compile_comparison("<=")
        self.assertTrue(len(code) > 0)
        # setle = 0F 9E
        found = False
        for i in range(len(code) - 1):
            if code[i] == 0x0F and code[i + 1] == 0x9E:
                found = True
                break
        self.assertTrue(found, "Expected setle (0F 9E) for <= comparison")

    def test_ge_compilation(self):
        """>= 比较应生成 cmp + setge 指令"""
        code = self._compile_comparison(">=")
        self.assertTrue(len(code) > 0)
        # setge = 0F 9D
        found = False
        for i in range(len(code) - 1):
            if code[i] == 0x0F and code[i + 1] == 0x9D:
                found = True
                break
        self.assertTrue(found, "Expected setge (0F 9D) for >= comparison")


class TestUnaryOps(unittest.TestCase):
    """一元运算编译测试"""

    def test_neg_compilation(self):
        """NEG 应生成 neg 指令"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_neg", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=42, const_type="int"),
            LIRUnaryOp(op="-"),
            LIRReturn(),
        ]
        lir.functions["test_neg"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)
        # neg 指令: REX.W + F7 + ModR/M(/3)
        found = False
        for i in range(len(code) - 2):
            if code[i] == 0x48 and code[i + 1] == 0xF7:
                found = True
                break
        self.assertTrue(found, "Expected neg instruction (48 F7) for NEG unary op")

    def test_not_compilation(self):
        """! (逻辑非) 应生成 cmp + sete"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_not", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=0, const_type="int"),
            LIRUnaryOp(op="!"),
            LIRReturn(),
        ]
        lir.functions["test_not"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)
        # 应包含 cmp 指令 (48 83 F8 for cmp reg, 0)
        found_cmp = False
        for i in range(len(code) - 2):
            if code[i] == 0x48 and code[i + 1] == 0x83:
                found_cmp = True
                break
        self.assertTrue(found_cmp, "Expected cmp instruction for ! unary op")

    def test_bitwise_not_compilation(self):
        """NOT (按位取反) 应生成 not 指令"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_bnot", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=42, const_type="int"),
            LIRUnaryOp(op="NOT"),
            LIRReturn(),
        ]
        lir.functions["test_bnot"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)
        # not 指令: REX.W + F7 + ModR/M(/2)
        found = False
        for i in range(len(code) - 2):
            if code[i] == 0x48 and code[i + 1] == 0xF7:
                modrm = code[i + 2]
                # /2 = ModR/M reg field is 2
                if (modrm >> 3) & 7 == 2:
                    found = True
                    break
        self.assertTrue(found, "Expected not instruction (48 F7 /2) for NOT unary op")


class TestLoopSupport(unittest.TestCase):
    """循环支持测试：验证 Label + Branch + Jump 形成循环结构"""

    def test_counted_loop_compilation(self):
        """计数循环：LIRLabel + LIRBinOp + LIRBranch + LIRJump"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_loop", [], INT_TYPE)
        fn.body = [
            # loop_start:
            LIRLabel(name="loop_start"),
            # counter = 0
            LIRLoadConst(value=0, const_type="int"),
            # limit = 5
            LIRLoadConst(value=5, const_type="int"),
            # counter < limit
            LIRBinOp(op="<"),
            # if true -> loop_body, else -> loop_end
            LIRBranch(cond_reg="", true_label="loop_body", false_label="loop_end"),
            # loop_body:
            LIRLabel(name="loop_body"),
            # (循环体内容)
            LIRLoadConst(value=1, const_type="int"),
            # jmp loop_start
            LIRJump(target="loop_start"),
            # loop_end:
            LIRLabel(name="loop_end"),
            LIRReturn(),
        ]
        lir.functions["test_loop"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)
        # 应包含 jmp rel32 (0xE9) 用于回跳
        self.assertIn(0xE9, code)

    def test_while_loop_pattern(self):
        """while 循环模式：先判断后执行"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_while", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=1, const_type="bool"),
            # while_start:
            LIRLabel(name="while_start"),
            # condition test
            LIRBranch(cond_reg="", true_label="while_body", false_label="while_end"),
            # while_body:
            LIRLabel(name="while_body"),
            LIRLoadConst(value=42, const_type="int"),
            LIRJump(target="while_start"),
            # while_end:
            LIRLabel(name="while_end"),
            LIRReturn(),
        ]
        lir.functions["test_while"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)
        # 应同时包含 jne 和 jmp
        has_jne = False
        has_jmp = False
        for i in range(len(code)):
            if code[i] == 0xE9:
                has_jmp = True
            if i < len(code) - 1 and code[i] == 0x0F and code[i + 1] == 0x85:
                has_jne = True
        self.assertTrue(has_jmp, "Expected jmp for loop back-edge")
        self.assertTrue(has_jne, "Expected jne for while condition")

    def test_nested_labels(self):
        """嵌套标签的正确回填"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_nested", [], INT_TYPE)
        fn.body = [
            LIRLabel(name="outer_start"),
            LIRBranch(cond_reg="", true_label="outer_body", false_label="outer_end"),
            LIRLabel(name="outer_body"),
            LIRLabel(name="inner_start"),
            LIRBranch(cond_reg="", true_label="inner_body", false_label="inner_end"),
            LIRLabel(name="inner_body"),
            LIRLoadConst(value=1, const_type="int"),
            LIRJump(target="inner_start"),
            LIRLabel(name="inner_end"),
            LIRJump(target="outer_start"),
            LIRLabel(name="outer_end"),
            LIRReturn(),
        ]
        lir.functions["test_nested"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)


class TestADTConstruction(unittest.TestCase):
    """ADT 构建测试"""

    def test_adt_construction_compilation(self):
        """ADT 构建应分配栈空间并写入 tag 和字段"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_adt", [], INT_TYPE)
        build = LIRBuildADT(type_tag=1, field_count=2)
        build.src_locs = [
            ("const_10", INT_TYPE),
            ("const_20", INT_TYPE),
        ]
        fn.body = [
            LIRLoadConst(value=10, const_type="int"),
            LIRLoadConst(value=20, const_type="int"),
            build,
            LIRReturn(),
        ]
        lir.functions["test_adt"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)
        # 应包含 sub rsp (栈分配) 和 mov_mem_reg (写入字段)
        # sub rsp 编码: 48 83 EC 或 48 81 EC
        found_sub = False
        for i in range(len(code) - 2):
            if code[i] == 0x48 and code[i + 1] == 0x83 and code[i + 2] == 0xEC:
                found_sub = True
                break
        self.assertTrue(found_sub, "Expected sub rsp for ADT stack allocation")

    def test_adt_zero_fields(self):
        """无字段的 ADT (仅 tag)"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_adt_empty", [], INT_TYPE)
        fn.body = [
            LIRBuildADT(type_tag=0, field_count=0),
            LIRReturn(),
        ]
        lir.functions["test_adt_empty"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)

    def test_adt_multiple_fields(self):
        """多字段 ADT"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_adt_multi", [], INT_TYPE)
        build = LIRBuildADT(type_tag=3, field_count=4)
        build.src_locs = [
            ("const_1", INT_TYPE),
            ("const_2", INT_TYPE),
            ("const_3", INT_TYPE),
            ("const_4", INT_TYPE),
        ]
        fn.body = [
            LIRLoadConst(value=1, const_type="int"),
            LIRLoadConst(value=2, const_type="int"),
            LIRLoadConst(value=3, const_type="int"),
            LIRLoadConst(value=4, const_type="int"),
            build,
            LIRReturn(),
        ]
        lir.functions["test_adt_multi"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)


class TestListConstruction(unittest.TestCase):
    """List 构建测试"""

    def test_list_construction_compilation(self):
        """List 构建应分配栈空间并写入 count 和元素"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_list", [], INT_TYPE)
        build = LIRBuildList(count=3)
        build.src_locs = [
            ("const_1", INT_TYPE),
            ("const_2", INT_TYPE),
            ("const_3", INT_TYPE),
        ]
        fn.body = [
            LIRLoadConst(value=100, const_type="int"),
            LIRLoadConst(value=200, const_type="int"),
            LIRLoadConst(value=300, const_type="int"),
            build,
            LIRReturn(),
        ]
        lir.functions["test_list"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)
        # 应包含 sub rsp (分配 count + elements 的空间)
        found_sub = False
        for i in range(len(code) - 2):
            if code[i] == 0x48 and code[i + 1] == 0x83 and code[i + 2] == 0xEC:
                found_sub = True
                break
        self.assertTrue(found_sub, "Expected sub rsp for List stack allocation")

    def test_empty_list(self):
        """空 List"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_empty_list", [], INT_TYPE)
        fn.body = [
            LIRBuildList(count=0),
            LIRReturn(),
        ]
        lir.functions["test_empty_list"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)


class TestTupleConstruction(unittest.TestCase):
    """Tuple 构建测试"""

    def test_tuple_construction_compilation(self):
        """Tuple 构建应分配栈空间并写入字段"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_tuple", [], INT_TYPE)
        build = LIRBuildTuple(count=2)
        build.src_locs = [
            ("const_10", INT_TYPE),
            ("const_20", INT_TYPE),
        ]
        fn.body = [
            LIRLoadConst(value=10, const_type="int"),
            LIRLoadConst(value=20, const_type="int"),
            build,
            LIRReturn(),
        ]
        lir.functions["test_tuple"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)

    def test_empty_tuple(self):
        """空 Tuple"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_empty_tuple", [], INT_TYPE)
        fn.body = [
            LIRBuildTuple(count=0),
            LIRReturn(),
        ]
        lir.functions["test_empty_tuple"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)


class TestGlobalVariables(unittest.TestCase):
    """全局变量测试"""

    def test_load_global_compilation(self):
        """加载全局变量应生成 lea + mov 指令"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        global_var = LIRGlobal(name="x", ir_type=INT_TYPE, data=LIRData(name="x", value=b'\x05\x00\x00\x00\x00\x00\x00\x00'))
        lir.globals.append(global_var)
        fn = LIRFunction("test_load_global", [], INT_TYPE)
        fn.body = [
            LIRLoadGlobal(global_name="x"),
            LIRReturn(),
        ]
        lir.functions["test_load_global"] = fn
        codegen._collect_constants(lir)
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)
        # 应包含 lea 指令 (8D)
        self.assertIn(0x8D, code)

    def test_store_global_compilation(self):
        """存储全局变量应生成 lea + mov [mem], reg"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        global_var = LIRGlobal(name="x", ir_type=INT_TYPE, data=LIRData(name="x", value=b'\x00' * 8))
        lir.globals.append(global_var)
        fn = LIRFunction("test_store_global", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=42, const_type="int"),
            LIRStoreGlobal(global_name="x"),
            LIRReturn(),
        ]
        lir.functions["test_store_global"] = fn
        codegen._collect_constants(lir)
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)

    def test_load_global_auto_register(self):
        """未注册的全局变量应自动在数据段分配"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_auto_global", [], INT_TYPE)
        fn.body = [
            LIRLoadGlobal(global_name="unregistered_var"),
            LIRReturn(),
        ]
        lir.functions["test_auto_global"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)

    def test_global_data_in_elf(self):
        """全局变量应出现在 ELF 数据段中"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        global_var = LIRGlobal(name="g", ir_type=INT_TYPE, data=LIRData(name="g", value=b'\x2A\x00\x00\x00\x00\x00\x00\x00'))
        lir.globals.append(global_var)
        fn = LIRFunction("main", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=0, const_type="int"),
            LIRReturn(),
        ]
        lir.functions["main"] = fn
        codegen._collect_constants(lir)
        # 验证全局变量数据被收集
        self.assertIn("g", codegen.global_symbols)
        self.assertEqual(len(codegen.global_data), 1)
        self.assertEqual(codegen.global_data[0][1][0], 0x2A)


class TestReturnValue(unittest.TestCase):
    """返回值测试"""

    def test_return_after_int_computation(self):
        """整型计算后返回（值在 RAX）"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_ret_int", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=42, const_type="int"),
            LIRLoadConst(value=8, const_type="int"),
            LIRBinOp(op="+"),
            LIRReturn(),
        ]
        lir.functions["test_ret_int"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)
        # 最后一个 ret (0xC3)
        self.assertEqual(code[-1], 0xC3)

    def test_return_after_comparison(self):
        """比较后返回（0 或 1 在 RAX）"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_ret_cmp", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=10, const_type="int"),
            LIRLoadConst(value=10, const_type="int"),
            LIRBinOp(op="=="),
            LIRReturn(),
        ]
        lir.functions["test_ret_cmp"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)
        self.assertEqual(code[-1], 0xC3)

    def test_return_after_unary(self):
        """一元运算后返回"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_ret_neg", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=42, const_type="int"),
            LIRUnaryOp(op="-"),
            LIRReturn(),
        ]
        lir.functions["test_ret_neg"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)
        self.assertEqual(code[-1], 0xC3)


class TestRegisterTransfer(unittest.TestCase):
    """寄存器传送测试"""

    def test_load_reg_with_types(self):
        """LIRLoadReg 带类型信息"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_loadreg", [], INT_TYPE)
        load = LIRLoadReg()
        load.src_locs = [("const_42", INT_TYPE)]
        load.dst_loc = ("dest_var", INT_TYPE)
        fn.body = [
            LIRLoadConst(value=42, const_type="int"),
            load,
            LIRReturn(),
        ]
        lir.functions["test_loadreg"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)

    def test_store_reg(self):
        """LIRStoreReg"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_storereg", [], INT_TYPE)
        store = LIRStoreReg()
        store.src_locs = [("const_42", INT_TYPE)]
        store.dst_loc = ("saved_var", INT_TYPE)
        fn.body = [
            LIRLoadConst(value=42, const_type="int"),
            store,
            LIRReturn(),
        ]
        lir.functions["test_storereg"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)


class TestSimpleNativeCompiler(unittest.TestCase):
    """SimpleNativeCompiler 测试"""

    def test_compile_produces_elf(self):
        """compile() 应生成 ELF 文件"""
        import tempfile
        compiler = SimpleNativeCompiler()
        with tempfile.NamedTemporaryFile(suffix=".elf", delete=False) as f:
            output_path = f.name
        try:
            result = compiler.compile(output_path)
            self.assertEqual(result, output_path)
            with open(output_path, 'rb') as f:
                elf = f.read()
            self.assertEqual(elf[0:4], b'\x7fELF')
            self.assertTrue(len(elf) > 128)
        finally:
            os.unlink(output_path)

    def test_compile_source_not_implemented(self):
        """compile_source 仍然抛出 NotImplementedError"""
        compiler = SimpleNativeCompiler()
        with self.assertRaises(NotImplementedError):
            compiler.compile_source("let x = 1", "/tmp/test")


class TestLogicalOps(unittest.TestCase):
    """逻辑运算测试"""

    def test_and_op(self):
        """&& 逻辑与"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_and", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=1, const_type="int"),
            LIRLoadConst(value=1, const_type="int"),
            LIRBinOp(op="&&"),
            LIRReturn(),
        ]
        lir.functions["test_and"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)
        # and 指令: 48 21
        found = False
        for i in range(len(code) - 1):
            if code[i] == 0x48 and code[i + 1] == 0x21:
                found = True
                break
        self.assertTrue(found, "Expected and instruction for &&")

    def test_or_op(self):
        """|| 逻辑或"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_or", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=0, const_type="int"),
            LIRLoadConst(value=1, const_type="int"),
            LIRBinOp(op="||"),
            LIRReturn(),
        ]
        lir.functions["test_or"] = fn
        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)
        # or 指令: 48 09
        found = False
        for i in range(len(code) - 1):
            if code[i] == 0x48 and code[i + 1] == 0x09:
                found = True
                break
        self.assertTrue(found, "Expected or instruction for ||")


class TestADTLayout(unittest.TestCase):
    """ADT 内存布局测试"""

    def test_adt_layout_constants(self):
        """验证 ADT 布局常量"""
        codegen = NativeCodeGen()
        self.assertEqual(codegen.ADT_TAG_SIZE, 8)
        self.assertEqual(codegen.ADT_FIELD_SIZE, 8)

    def test_list_layout_constants(self):
        """验证 List 布局常量"""
        codegen = NativeCodeGen()
        self.assertEqual(codegen.LIST_HEADER_SIZE, 8)
        self.assertEqual(codegen.LIST_ELEM_SIZE, 8)


class TestELFWithNewFeatures(unittest.TestCase):
    """包含新特性的端到端 ELF 生成测试"""

    def test_elf_with_comprehensive_features(self):
        """包含所有新特性的 ELF 生成"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="full_test")

        # 全局变量
        g = LIRGlobal(name="g", ir_type=INT_TYPE, data=LIRData(name="g", value=b'\x00' * 8))
        lir.globals.append(g)

        # 辅助函数
        helper = LIRFunction("helper", [], INT_TYPE)
        helper.body = [LIRReturn()]
        lir.functions["helper"] = helper

        # 主函数
        main = LIRFunction("main", [], INT_TYPE)
        main.body = [
            # 比较
            LIRLoadConst(value=1, const_type="int"),
            LIRLoadConst(value=2, const_type="int"),
            LIRBinOp(op="<"),
            LIRBranch(cond_reg="", true_label="yes", false_label="no"),
            LIRLabel(name="yes"),
            # 一元
            LIRUnaryOp(op="-"),
            LIRJump(target="end"),
            LIRLabel(name="no"),
            LIRLoadConst(value=0, const_type="int"),
            LIRLabel(name="end"),
            # 循环
            LIRLabel(name="lp"),
            LIRLoadConst(value=0, const_type="int"),
            LIRLoadConst(value=1, const_type="int"),
            LIRBinOp(op="=="),
            LIRBranch(cond_reg="", true_label="lp_end", false_label="lp_body"),
            LIRLabel(name="lp_body"),
            LIRJump(target="lp"),
            LIRLabel(name="lp_end"),
            # ADT
            LIRBuildADT(type_tag=0, field_count=1),
            # List
            LIRBuildList(count=1),
            # 全局
            LIRLoadGlobal(global_name="g"),
            # 返回
            LIRReturn(),
        ]
        lir.functions["main"] = main

        elf = codegen.compile(lir)
        self.assertEqual(elf[0:4], b'\x7fELF')
        self.assertTrue(len(elf) > 128)


if __name__ == '__main__':
    unittest.main()
