import unittest
import sys
import os
import struct

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ir'))

from backend.x86_64 import (
    X86_64Emitter, RAX, RBX, RCX, RDX, RSP, RBP, RDI, RSI,
    R8, R9, R10, R11, R12, R13, R14, R15,
    XMM0, XMM1, CALLER_SAVED, CALLEE_SAVED, ARG_REGS, RETURN_REG,
)
from backend.native_backend import (
    NativeCodeGen, LinearScanAllocator, LiveInterval,
)

# 直接导入 IR 节点
from ir_nodes import (
    LIRModule, LIRFunction, LIRLoadConst, LIRReturn,
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


if __name__ == '__main__':
    unittest.main()
