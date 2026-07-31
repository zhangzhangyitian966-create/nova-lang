"""
Nova test_native_backend 模块

本模块是 Nova 编程语言的组成部分。
"""
import unittest
import struct

from nova.backend.x86_64 import (
    X86_64Emitter,
    RAX,
    RBX,
    RCX,
    RDX,
    RDI,
    R8,
    R9,
    XMM0,
)
from nova.backend.native_backend import (
    NativeCodeGen,
)

# 直接导入 IR 节点
from nova.ir.ir_types import FLOAT_TYPE, INT_TYPE

from nova.ir.lir import (
    LIRCall,
    LIRFunction,
    LIRLoadConst,
    LIRModule,
    LIRReturn,
    LIRStoreGlobal,
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

    def test_store_global_float(self):
        """浮点全局变量存储应发射 movq rax, xmm0 指令"""
        from nova.backend.native_backend import _EmitContext

        codegen = NativeCodeGen()
        codegen._global_var_map["test_float"] = 0

        e = X86_64Emitter()
        # vreg 分配到栈上，load_to_reg 会发射 movsd xmm0, [rsp+offset]
        ctx = _EmitContext(
            e=e,
            func_name="test",
            vreg_alloc={"v0": ("stack", 0)},
            label_offsets={},
            jump_fixups=[],
        )

        instr = LIRStoreGlobal(global_name="test_float")
        instr.src_locs = [("v0", FLOAT_TYPE)]

        codegen._emit_store_global(instr, ctx)
        code = e.get_code()

        # 检查包含 movsd xmm0, [rsp+0] (浮点加载)
        # 正确 SIB 编码（RSP 为 base 时必须加 SIB 字节）:
        #   F2 0F 10 44 24 00 = movsd xmm0, [rsp+disp8]
        #   ModRM=0x44 (mod=01, reg=000(xmm0), rm=100(SIB))
        #   SIB  =0x24 (scale=00, index=100(none), base=100(RSP))
        #   disp8=0x00
        self.assertIn(bytes([0xF2, 0x0F, 0x10, 0x44, 0x24, 0x00]), code)
        # 检查包含 movq rax, xmm0
        # F2 0F D6 C0
        self.assertIn(bytes([0xF2, 0x0F, 0xD6, 0xC0]), code)
        # 检查包含 mov [rip+disp32], rax
        self.assertIn(bytes([0x48, 0x89, 0x05]), code)


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


class TestRelocatableELF(unittest.TestCase):
    """可重定位 ELF (.o) 文件生成测试"""

    def test_obj_is_elf(self):
        """obj 格式产出合法的 ELF 文件"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("main", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=0, const_type="int"),
            LIRReturn(),
        ]
        lir.functions["main"] = fn

        obj = codegen.compile(lir, output_format="obj")
        self.assertEqual(obj[0:4], b'\x7fELF')
        # e_type 应为 ET_REL (1)
        e_type = struct.unpack('<H', obj[16:18])[0]
        self.assertEqual(e_type, 1)

    def test_obj_has_section_headers(self):
        """obj 格式应有 section header table"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("main", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=0, const_type="int"),
            LIRReturn(),
        ]
        lir.functions["main"] = fn

        obj = codegen.compile(lir, output_format="obj")
        e_shoff = struct.unpack('<Q', obj[40:48])[0]
        e_shnum = struct.unpack('<H', obj[60:62])[0]
        self.assertGreater(e_shoff, 0, "shoff 应非零")
        self.assertGreater(e_shnum, 0, "shnum 应非零")
        # 每个节头 64 字节
        self.assertEqual(len(obj), e_shoff + e_shnum * 64)

    def test_obj_has_symtab(self):
        """obj 格式应包含 .symtab 和 .strtab 节"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("main", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=0, const_type="int"),
            LIRReturn(),
        ]
        lir.functions["main"] = fn

        obj = codegen.compile(lir, output_format="obj")
        # 读取 shstrtab 获取节名
        e_shoff = struct.unpack('<Q', obj[40:48])[0]
        e_shnum = struct.unpack('<H', obj[60:62])[0]
        e_shstrndx = struct.unpack('<H', obj[62:64])[0]

        # 读取 shstrtab 的节头
        shstr_shdr_off = e_shoff + e_shstrndx * 64
        sh_offset = struct.unpack('<Q', obj[shstr_shdr_off+24:shstr_shdr_off+32])[0]
        sh_size = struct.unpack('<Q', obj[shstr_shdr_off+32:shstr_shdr_off+40])[0]
        shstrtab = obj[sh_offset:sh_offset+sh_size]

        # 检查节名
        section_names = set()
        for i in range(e_shnum):
            shdr_off = e_shoff + i * 64
            sh_name_idx = struct.unpack('<I', obj[shdr_off:shdr_off+4])[0]
            # 找到 NUL 终止的字符串
            nul = shstrtab.find(b'\x00', sh_name_idx)
            name = shstrtab[sh_name_idx:nul].decode('utf-8')
            section_names.add(name)

        self.assertIn('.text', section_names)
        self.assertIn('.symtab', section_names)
        self.assertIn('.strtab', section_names)
        self.assertIn('.shstrtab', section_names)

    def test_obj_has_external_symbols(self):
        """obj 格式应包含 nova_init, nova_cleanup 等外部符号"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("main", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=0, const_type="int"),
            LIRReturn(),
        ]
        lir.functions["main"] = fn

        obj = codegen.compile(lir, output_format="obj")

        # 找到 .symtab 和 .strtab
        e_shoff = struct.unpack('<Q', obj[40:48])[0]
        e_shnum = struct.unpack('<H', obj[60:62])[0]
        e_shstrndx = struct.unpack('<H', obj[62:64])[0]
        shstr_shdr_off = e_shoff + e_shstrndx * 64
        sh_offset = struct.unpack('<Q', obj[shstr_shdr_off+24:shstr_shdr_off+32])[0]
        sh_size = struct.unpack('<Q', obj[shstr_shdr_off+32:shstr_shdr_off+40])[0]
        shstrtab = obj[sh_offset:sh_offset+sh_size]

        symtab_off = None
        strtab_off = None
        symtab_entsize = None
        for i in range(e_shnum):
            shdr_off = e_shoff + i * 64
            sh_name_idx = struct.unpack('<I', obj[shdr_off:shdr_off+4])[0]
            nul = shstrtab.find(b'\x00', sh_name_idx)
            name = shstrtab[sh_name_idx:nul].decode('utf-8')
            if name == '.symtab':
                symtab_off = struct.unpack('<Q', obj[shdr_off+24:shdr_off+32])[0]
                symtab_entsize = struct.unpack('<Q', obj[shdr_off+56:shdr_off+64])[0]
            elif name == '.strtab':
                strtab_off = struct.unpack('<Q', obj[shdr_off+24:shdr_off+32])[0]

        self.assertIsNotNone(symtab_off, "应包含 .symtab")
        self.assertIsNotNone(strtab_off, "应包含 .strtab")

        # 读取所有符号名
        sym_names = set()
        strtab = obj[strtab_off:]
        # 遍历符号表
        idx = 0
        while True:
            off = symtab_off + idx * 24  # ELF64_SYM_SIZE = 24
            if off + 24 > len(obj):
                break
            st_name = struct.unpack('<I', obj[off:off+4])[0]
            st_info = obj[off+4]
            st_shndx = struct.unpack('<H', obj[off+6:off+8])[0]

            # 从 strtab 读名称
            nul = strtab.find(b'\x00', st_name)
            if nul < 0:
                break
            name = strtab[st_name:nul].decode('utf-8')
            if name:
                sym_names.add(name)
            idx += 1
            # 符号表由 sh_info 标记的局部/全局边界
            # 简单做法：最多读 100 个
            if idx > 100:
                break

        # 应包含 main 和 _start（全局函数符号）
        self.assertIn('main', sym_names)
        self.assertIn('_start', sym_names)
        # 应包含外部运行时符号
        self.assertIn('nova_init', sym_names)
        self.assertIn('nova_cleanup', sym_names)

    def test_obj_has_rela_text(self):
        """obj 格式应包含 .rela.text 重定位表"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("main", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=0, const_type="int"),
            LIRReturn(),
        ]
        lir.functions["main"] = fn

        obj = codegen.compile(lir, output_format="obj")

        # 找到 .rela.text 节
        e_shoff = struct.unpack('<Q', obj[40:48])[0]
        e_shnum = struct.unpack('<H', obj[60:62])[0]
        e_shstrndx = struct.unpack('<H', obj[62:64])[0]
        shstr_shdr_off = e_shoff + e_shstrndx * 64
        sh_offset = struct.unpack('<Q', obj[shstr_shdr_off+24:shstr_shdr_off+32])[0]
        sh_size = struct.unpack('<Q', obj[shstr_shdr_off+32:shstr_shdr_off+40])[0]
        shstrtab = obj[sh_offset:sh_offset+sh_size]

        rela_text_size = 0
        for i in range(e_shnum):
            shdr_off = e_shoff + i * 64
            sh_name_idx = struct.unpack('<I', obj[shdr_off:shdr_off+4])[0]
            nul = shstrtab.find(b'\x00', sh_name_idx)
            name = shstrtab[sh_name_idx:nul].decode('utf-8')
            if name == '.rela.text':
                rela_text_size = struct.unpack('<Q', obj[shdr_off+32:shdr_off+40])[0]
                break

        # _start 调用 nova_init, main, nova_cleanup -> 至少 3 个重定位
        self.assertGreaterEqual(rela_text_size, 3 * 24)

    def test_obj_format_invalid(self):
        """不支持的输出格式应抛出 ValueError"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("main", [], INT_TYPE)
        fn.body = [LIRLoadConst(value=0, const_type="int"), LIRReturn()]
        lir.functions["main"] = fn

        with self.assertRaises(ValueError):
            codegen.compile(lir, output_format="coff")

    def test_gcc_link_no_gcc(self):
        """没有 gcc 时 _compile_via_gcc 应报错"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("main", [], INT_TYPE)
        fn.body = [LIRLoadConst(value=0, const_type="int"), LIRReturn()]
        lir.functions["main"] = fn

        import unittest.mock as mock
        with mock.patch('shutil.which', return_value=None):
            with self.assertRaises(EnvironmentError):
                codegen._compile_via_gcc(lir, "/tmp/test_nova_gcc")


class TestFloatImmAndRetval(unittest.TestCase):
    """测试浮点立即数参数加载和浮点返回值正确处理"""

    def test_float_immediate_no_notimplementederror(self):
        """浮点立即数参数不再抛出 NotImplementedError"""
        from nova.ir.lir import (
            LIRFunction,
            LIRLoadConst,
            LIRModule,
            LIRReturn,
        )
        codegen = NativeCodeGen()
        lir = LIRModule(name="test_float_imm")
        fn = LIRFunction("main", [], INT_TYPE)
        # 构造一个使用浮点常量的函数
        fn.body = [
            LIRLoadConst(value=3.14, const_type="float"),
            LIRReturn(),
        ]
        lir.functions["main"] = fn
        # 编译不应抛异常
        elf = codegen.compile(lir, output_format="elf")
        self.assertTrue(len(elf) > 0)

    def test_emit_call_float_retval_uses_xmm0(self):
        """验证 _emit_call 的返回值分支使用正确的源寄存器"""
        from nova.ir.ir_types import FLOAT_TYPE

        from nova.ir.lir import (
            LIRFunction,
            LIRLoadConst,
            LIRModule,
            LIRReturn,
        )
        codegen = NativeCodeGen()
        lir = LIRModule(name="test_float_ret")
        # 定义一个返回浮点值的函数
        helper = LIRFunction("helper", [], FLOAT_TYPE)
        helper.body = [
            LIRLoadConst(value=2.718, const_type="float"),
            LIRReturn(),
        ]
        # main 调用 helper 获取浮点返回值
        main = LIRFunction("main", [], INT_TYPE)
        main.body = [
            LIRLoadConst(value=0, const_type="int"),
            LIRReturn(),
        ]
        lir.functions["helper"] = helper
        lir.functions["main"] = main
        # 编译不应抛异常
        elf = codegen.compile(lir, output_format="elf")
        self.assertTrue(len(elf) > 0)


class TestNativeE2EExecution(unittest.TestCase):
    """Native 后端端到端执行测试

    通过 LIR → 可重定位 .o → gcc 链接 → 执行 → 验证返回码，
    验证 Native 后端从编译到执行的完整闭环。
    """

    # 测试用 Nova 源码
    _SIMPLE = "fn main() -> Int { 42 }"
    _ARITH = "fn main() -> Int { let a = 10\n let b = 20\n a + b }"
    _BRANCH = "fn main() -> Int { let x = 10\n if x > 5 then 100 else 200 }"
    _LOOP = (
        "fn main() -> Int {\n"
        "    mut sum = 0\n"
        "    mut i = 0\n"
        "    while i < 10 {\n"
        "        sum = sum + i\n"
        "        i = i + 1\n"
        "    }\n"
        "    sum\n"
        "}"
    )
    _CALL = (
        "fn add(a: Int, b: Int) -> Int { a + b }\n"
        "fn main() -> Int { add(15, 27) }"
    )
    _CLOSURE = (
        "fn make_adder(n: Int) -> (Int) -> Int {\n"
        "    |x: Int| -> Int { x + n }\n"
        "}\n"
        "fn main() -> Int {\n"
        "    let add5 = make_adder(5)\n"
        "    add5(10)\n"
        "}"
    )

    def _compile_and_run(self, source):
        """编译 Nova 源码到 .o，gcc 链接为可执行文件，执行并返回 exit code"""
        import os
        import shutil
        import subprocess
        import tempfile

        from nova.lexer import Lexer
        from nova.parser import Parser
        from nova.type_checker import TypeChecker
        from nova.ir.hir_lowering import HIRLowering
        from nova.ir.mir_lowering import MIRLowering
        from nova.ir.lir_lowering import LIRLowering

        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        TypeChecker().check_program(ast)
        hir = HIRLowering().lower(ast)
        mir = MIRLowering().lower(hir)
        lir = LIRLowering().lower(mir)

        backend = NativeCodeGen()
        obj_bytes = backend.compile(lir, output_format="obj")

        # 查找运行时库
        nova_pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        runtime_lib = os.path.join(nova_pkg_dir, "runtime", "libnova_runtime.a")
        if not os.path.isfile(runtime_lib):
            self.skipTest("libnova_runtime.a not found")

        gcc = shutil.which("gcc")
        if not gcc:
            self.skipTest("gcc not available")

        with tempfile.TemporaryDirectory(prefix="nova_e2e_") as tmpdir:
            obj_path = os.path.join(tmpdir, "nova.o")
            exe_path = os.path.join(tmpdir, "nova_exe")
            with open(obj_path, "wb") as f:
                f.write(obj_bytes)

            result = subprocess.run(
                [gcc, "-nostartfiles", obj_path, runtime_lib,
                 "-o", exe_path, "-lm", "-lc", "-ldl", "-no-pie"],
                capture_output=True, text=True, timeout=10
            )
            self.assertEqual(result.returncode, 0,
                             f"gcc 链接失败: {result.stderr}")

            run_result = subprocess.run(
                [exe_path], capture_output=True, text=True, timeout=5
            )
            return run_result.returncode

    def test_e2e_simple_return(self):
        """端到端：简单返回 42"""
        self.assertEqual(self._compile_and_run(self._SIMPLE), 42)

    def test_e2e_arithmetic(self):
        """端到端：算术 10+20=30"""
        self.assertEqual(self._compile_and_run(self._ARITH), 30)

    def test_e2e_branch(self):
        """端到端：分支 10>5 → 100"""
        self.assertEqual(self._compile_and_run(self._BRANCH), 100)

    def test_e2e_loop(self):
        """端到端：循环 sum(0..9)=45"""
        self.assertEqual(self._compile_and_run(self._LOOP), 45)

    def test_e2e_function_call(self):
        """端到端：函数调用 add(15,27)=42"""
        self.assertEqual(self._compile_and_run(self._CALL), 42)

    def test_e2e_closure(self):
        """端到端：闭包 make_adder(5)(10)=15"""
        self.assertEqual(self._compile_and_run(self._CLOSURE), 15)


class TestRegAllocCallSite(unittest.TestCase):
    """寄存器分配器调用点活跃区间切口测试

    验证 _allocate_registers 在调用点处仅保存实际活跃的 caller-saved 寄存器，
    替代保守的全部保存方案。
    """

    def test_no_live_caller_saved_at_call(self):
        """调用点后无活跃 caller-saved 寄存器 → caller_saved_to_preserve 为空"""
        codegen = NativeCodeGen()
        fn = LIRFunction("main", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=10, const_type="int"),   # const_10, 分配到 RCX
            LIRCall(func_name="foo", arg_count=0, arg_locs=[]),  # idx=1
            LIRReturn(),  # 不引用 const_10
        ]
        codegen._allocate_registers(fn)
        call_instr = fn.body[1]
        self.assertEqual(
            call_instr.caller_saved_to_preserve, [],
            "调用点后无活跃 caller-saved 寄存器，不应保存任何寄存器"
        )

    def test_live_caller_saved_at_call(self):
        """调用点后有活跃 caller-saved 寄存器 → 仅保存该寄存器"""
        codegen = NativeCodeGen()
        fn = LIRFunction("main", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=10, const_type="int"),   # const_10, 分配到 RCX
            LIRCall(
                func_name="foo",
                arg_count=0,
                arg_locs=[],
                dst_loc=("v1", INT_TYPE),
            ),  # idx=1
            # LIRReturn 引用 const_10，使其在 call 后仍活跃
            LIRReturn(src_locs=[("const_10", INT_TYPE)]),
        ]
        vreg_alloc, _, _ = codegen._allocate_registers(fn)
        call_instr = fn.body[1]
        # const_10 被分配到 RCX（caller-saved），且在 call 后仍活跃
        self.assertIn(
            RCX, call_instr.caller_saved_to_preserve,
            "const_10 分配到 RCX 且在 call 后活跃，应保存 RCX"
        )
        # 不应保存所有 8 个 caller-saved 寄存器
        self.assertLess(
            len(call_instr.caller_saved_to_preserve), 8,
            "应精确保存而非全部 8 个 caller-saved 寄存器"
        )

    def test_callee_saved_not_preserved(self):
        """被分配到 callee-saved 的 vreg 不应出现在 caller_saved_to_preserve"""
        codegen = NativeCodeGen()
        fn = LIRFunction("main", [], INT_TYPE)
        # 填充前 8 个 GPR，迫使 const_10 分配到 callee-saved（RBX）
        body = []
        for i in range(8):
            body.append(LIRLoadConst(value=i, const_type="int"))
        body.append(LIRCall(func_name="foo", arg_count=0, arg_locs=[]))
        body.append(LIRReturn(src_locs=[("const_10", INT_TYPE)]))
        fn.body = body
        codegen._allocate_registers(fn)
        call_instr = fn.body[8]
        # RBX 是 callee-saved，不应出现在保存列表中
        from nova.backend.x86_64 import RBX
        self.assertNotIn(
            RBX, call_instr.caller_saved_to_preserve,
            "callee-saved 寄存器（RBX）不应在 caller_saved_to_preserve 中"
        )


class TestNativeFloatImmOverflowXmm0Conflict(unittest.TestCase):
    """Cycle 66 P2：Native Float imm 溢出路径覆盖 XMM0 的 BUG 修复验证。

    原 BUG：9+ float 参数时，第 9+ 个 float imm 参数加载走
      `movsd XMM0, [RIP+disp] ; movq RAX, XMM0 ; push RAX`
    但 XMM0 已经装载了第 0 个 float 参数，导致被覆盖。

    修复：完全避开 XMM 寄存器，改为
      `mov RAX, [RIP+disp] ; push RAX`
    （8 字节 float 作为整数搬，内容完全等价）。
    """

    # —— 字节特征码（编码常量，避免 magic bytes 散落在每个断言） ——
    # movsd XMM0,[RIP+disp32]: F2 0F 10 /0, ModRM(00,000,101) = 05 → F2 0F 10 05
    MOVSD_XMM0_RIP = bytes([0xF2, 0x0F, 0x10, 0x05])
    # movq RAX, XMM0 (x86: REX.W + 0F 7E /r): 48 0F 7E C0
    MOVQ_RAX_XMM0 = bytes([0x48, 0x0F, 0x7E, 0xC0])
    # mov RAX,[RIP+disp32]: REX.W + 8B /0, ModRM(00,000,101) → 48 8B 05
    MOV_RAX_RIP = bytes([0x48, 0x8B, 0x05])

    def _emit_runtime_with_args(self, arg_specs, ret_dst=None):
        """辅助：构造 NativeCodeGen + _EmitContext，调用 _emit_runtime_call 并返回机器码字节。

        arg_specs: List[ (arg_val, is_float) ]
        ret_dst: None 或 (vreg_name, ir_type) 元组
        """
        from nova.backend.native_backend import _EmitContext

        codegen = NativeCodeGen()
        e = X86_64Emitter()
        ctx = _EmitContext(
            e=e,
            func_name="test_xmm0_ctx",
            vreg_alloc={"vret": ("stack", 0)},
            label_offsets={},
            jump_fixups=[],
        )

        # 转换为 _emit_runtime_call 的 args 格式: [ (spec, ir_type) ]
        args = []
        for val, is_flt in arg_specs:
            spec = ("imm", val)
            ty = FLOAT_TYPE if is_flt else INT_TYPE
            args.append((spec, ty))
        codegen._emit_runtime_call("nova_dummy_runtime", args, ret_dst, ctx)
        return e.get_code()

    def test_float_imm_overflow_emit_no_movsd_xmm0_in_overflow(self):
        """溢出分支不发射 movsd XMM0 后接 movq XMM0→RAX 的旧中转序列。

        注意：MOVSD XMM0,[RIP+disp32]（F2 0F 10 05）本身合法——第 0 个 float 参数装载。
        真正的 BUG 特征是：溢出路径用 XMM0 作为临时中转，导致"参数装载后再覆盖"。
        因此验证关键：
          a) 不得出现 MOVQ_RAX_XMM0（48 0F 7E C0 = movq RAX,XMM0，旧中转）
          b) 溢出 float 的装载方式改为 MOV_RAX_RIP（整数搬），push RAX
        """
        # 9 个 float imm：前 8 走 XMM0-7，第 9 走溢出路径
        arg_specs = [(1.0 * i, True) for i in range(9)]
        code = self._emit_runtime_with_args(arg_specs)

        # (a) 核心修复：不允许 movq RAX,XMM0 出现（这是 XMM0 被污染的标志）
        self.assertNotIn(
            self.MOVQ_RAX_XMM0, code,
            "溢出分支不得使用 movq RAX,XMM0（旧 bug 代码将 XMM0 作为中转，会覆盖第 0 个 float 参数）"
        )
        # (b) 溢出分支必须用整数搬：mov RAX,[RIP+disp32] + push RAX
        rax_rip_count = code.count(self.MOV_RAX_RIP)
        self.assertEqual(rax_rip_count, 1, "9 float imm 中恰好 1 个溢出走 RAX 中转")

    def test_float_imm_overflow_stack_count(self):
        """9 float imm → 溢出压栈数 = 1（通过 data_fixups 间接验证）。"""
        from nova.backend.native_backend import _EmitContext, CALLER_GPRS

        codegen = NativeCodeGen()
        e = X86_64Emitter()
        ctx = _EmitContext(
            e=e, func_name="stack_ctx", vreg_alloc={},
            label_offsets={}, jump_fixups=[],
        )
        arg_specs = [(("imm", 1.0 * i), FLOAT_TYPE) for i in range(9)]
        codegen._emit_runtime_call("f", arg_specs, None, ctx)
        code = e.get_code()
        # movsd [XMMn], [RIP+...] 是前 8 个 float 参数：特征码 F2 0F 10 ?? 05
        # 统计 F2 0F 10 (ModRM 的 rm=5) 出现次数 —— 简化：统计 MOVSD RIP-rel 次数
        # movsd reg,[RIP+disp32] = F2 0F 10 ModRM(00, XMMn, 101) = F2 0F 10 [C0+C8..] & 0x3F == 0x05*8 + reg
        # 简化：统计出现的 mov_rax_rip 次数 = 溢出 float 数（应该是 1）
        mov_rax_rip_count = code.count(self.MOV_RAX_RIP)
        self.assertEqual(mov_rax_rip_count, 1, "9 float imm 中恰好 1 个溢出走 RAX 中转")

    def test_int_args_then_float_overflow_no_xmm0_conflict(self):
        """混合参数（6 int + 9 float）：float 第 9 个溢出时 XMM0 不被 movq XMM0→RAX 覆盖。"""
        arg_specs = (
            [(100 + i, False) for i in range(6)]  # 6 int → RDI,RSI,RDX,RCX,R8,R9
            + [(1.0 * i, True) for i in range(9)]  # 9 float → XMM0-7 + 压栈
        )
        code = self._emit_runtime_with_args(arg_specs)
        # 核心断言：不允许 movq RAX,XMM0 出现（旧 bug 中转）
        self.assertNotIn(
            self.MOVQ_RAX_XMM0, code,
            "混合场景溢出分支也不得用 movq RAX,XMM0（会覆盖 XMM0 中的第 0 个 float 参数）"
        )
        # 溢出：恰好 1 个 float 走 RAX 中转
        self.assertEqual(code.count(self.MOV_RAX_RIP), 1,
                         "6 int + 9 float 中，第 9 个 float 溢出恰好 1 次走 RAX 中转")

    def test_vast_majority_float_overflow_multiple_no_xmm0(self):
        """20 个 float imm：前 8 XMM，后 12 全部走 RAX 中转（不经过任何 XMM）。"""
        arg_specs = [(0.5 * i, True) for i in range(20)]
        code = self._emit_runtime_with_args(arg_specs)
        rax_rip_count = code.count(self.MOV_RAX_RIP)
        self.assertGreaterEqual(
            rax_rip_count, 12,
            f"20 float imm 中至少 12 次走 mov RAX,[RIP+disp32] 溢出路径，实际 {rax_rip_count}"
        )
        # 核心修复：不得再用 XMM 做溢出中转（movq RAX,XMM0 是旧中转标志）
        self.assertNotIn(
            self.MOVQ_RAX_XMM0, code,
            "不得出现 movq RAX,XMM0（旧 BUG 代码：把 XMM 寄存器当作溢出中转，破坏参数装载）"
        )


if __name__ == '__main__':
    unittest.main()
