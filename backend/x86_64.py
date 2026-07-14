"""
x86_64 指令编码器
直接输出机器码字节，无需任何外部依赖
"""
import struct

# x86_64 寄存器编码
# RAX=0, RCX=1, RDX=2, RBX=3, RSP=4, RBP=5, RSI=6, RDI=7
# R8=8, R9=9, R10=10, R11=11, R12=12, R13=13, R14=14, R15=15

RAX, RCX, RDX, RBX = 0, 1, 2, 3
RSP, RBP, RSI, RDI = 4, 5, 6, 7
R8, R9, R10, R11 = 8, 9, 10, 11
R12, R13, R14, R15 = 12, 13, 14, 15

# 调用约定（System V AMD64 ABI）：
# 参数：RDI, RSI, RDX, RCX, R8, R9（整数/指针）
# 返回值：RAX
# 调用者保存：RAX, RCX, RDX, RSI, RDI, R8, R9, R10, R11
# 被调用者保存：RBX, RBP, R12, R13, R14, R15
# 栈指针对齐：16字节对齐

CALLER_SAVED = [RAX, RCX, RDX, RSI, RDI, R8, R9, R10, R11]
CALLEE_SAVED = [RBX, RBP, R12, R13, R14, R15]
ARG_REGS = [RDI, RSI, RDX, RCX, R8, R9]
RETURN_REG = RAX
XMM_RETURN_REG = 0  # XMM0

# XMM 浮点寄存器
XMM0, XMM1, XMM2, XMM3 = 0, 1, 2, 3
XMM4, XMM5, XMM6, XMM7 = 4, 5, 6, 7
XMM_ARG_REGS = [XMM0, XMM1, XMM2, XMM3, XMM4, XMM5, XMM6, XMM7]


class X86_64Emitter:
    """x86_64 机器码发射器"""

    def __init__(self):
        self.code = bytearray()
        self.relocations = []  # [(offset, type, symbol, addend)]

    def emit_bytes(self, *bytes_):
        for b in bytes_:
            self.code.append(b & 0xFF)

    def emit_byte(self, b):
        self.code.append(b & 0xFF)

    def emit_uint32(self, v):
        self.code.extend(struct.pack('<I', v & 0xFFFFFFFF))

    def emit_uint64(self, v):
        self.code.extend(struct.pack('<Q', v & 0xFFFFFFFFFFFFFFFF))

    def emit_int32(self, v):
        self.code.extend(struct.pack('<i', v))

    def emit_int8(self, v):
        self.code.extend(struct.pack('<b', v))

    def current_offset(self):
        return len(self.code)

    # === ModR/M 编码 ===
    def _modrm(self, mod, reg, rm):
        return ((mod & 3) << 6) | ((reg & 7) << 3) | (rm & 7)

    def _rex(self, w=0, r=0, x=0, b=0):
        rex = 0x40 | (w << 3) | (r << 2) | (x << 1) | b
        if rex != 0x40:
            self.emit_byte(rex)

    def _rex_w(self, r=0, b=0):
        self._rex(1, r, 0, b)

    def _rex_rb(self, r, b):
        """REX 前缀（64位操作），r 和 b 可以 >= 8"""
        self._rex(1, (r >> 3) & 1, 0, (b >> 3) & 1)

    # === MOV 指令 ===
    def mov_reg_imm64(self, reg, imm):
        """mov reg, imm64"""
        if 0 <= imm <= 0x7FFFFFFF:
            # 使用 mov r/m64, imm32（REX.W + C7 + ModR/M + imm32）
            # 这会零扩展 32 位立即数到 64 位
            self.emit_byte(0x48)
            self.emit_byte(0xC7)
            self.emit_byte(self._modrm(0b11, 0, reg & 7))
            self.emit_uint32(imm)
        else:
            self._rex_rb(0, reg)
            self.emit_byte(0xB8 + (reg & 7))
            self.emit_uint64(imm)

    def mov_reg_reg64(self, dst, src):
        """mov dst, src (64-bit)"""
        self._rex_rb(src, dst)
        self.emit_byte(0x89)
        self.emit_byte(self._modrm(0b11, src & 7, dst & 7))

    def mov_reg_mem(self, reg, base, offset):
        """mov reg, [base + offset] (64-bit)"""
        self._rex_rb(reg, base)
        if -128 <= offset <= 127:
            self.emit_byte(0x8B)
            self.emit_byte(self._modrm(0b01, reg & 7, base & 7))
            self.emit_int8(offset)
        else:
            self.emit_byte(0x8B)
            self.emit_byte(self._modrm(0b10, reg & 7, base & 7))
            self.emit_int32(offset)

    def mov_mem_reg(self, base, offset, reg):
        """mov [base + offset], reg (64-bit)"""
        self._rex_rb(reg, base)
        if -128 <= offset <= 127:
            self.emit_byte(0x89)
            self.emit_byte(self._modrm(0b01, reg & 7, base & 7))
            self.emit_int8(offset)
        else:
            self.emit_byte(0x89)
            self.emit_byte(self._modrm(0b10, reg & 7, base & 7))
            self.emit_int32(offset)

    def mov_reg_imm32(self, reg, imm):
        """mov reg, imm32 (32-bit, 零扩展到 64)"""
        self.emit_byte(0xB8 + (reg & 7))
        self.emit_uint32(imm)

    # === 算术指令 ===
    def add_reg_reg(self, dst, src):
        """add dst, src (64-bit)"""
        self._rex_rb(src, dst)
        self.emit_byte(0x01)
        self.emit_byte(self._modrm(0b11, src & 7, dst & 7))

    def add_reg_imm(self, reg, imm):
        """add reg, imm (64-bit)"""
        self.emit_byte(0x48)  # REX.W
        if -128 <= imm <= 127:
            self.emit_byte(0x83)
            self.emit_byte(self._modrm(0b11, 0, reg & 7))
            self.emit_int8(imm)
        else:
            self.emit_byte(0x81)
            self.emit_byte(self._modrm(0b11, 0, reg & 7))
            self.emit_int32(imm)

    def sub_reg_reg(self, dst, src):
        """sub dst, src (64-bit)"""
        self._rex_rb(src, dst)
        self.emit_byte(0x29)
        self.emit_byte(self._modrm(0b11, src & 7, dst & 7))

    def sub_reg_imm(self, reg, imm):
        """sub reg, imm (64-bit)"""
        self.emit_byte(0x48)  # REX.W
        if -128 <= imm <= 127:
            self.emit_byte(0x83)
            self.emit_byte(self._modrm(0b11, 5, reg & 7))
            self.emit_int8(imm)
        else:
            self.emit_byte(0x81)
            self.emit_byte(self._modrm(0b11, 5, reg & 7))
            self.emit_int32(imm)

    def imul_reg_reg(self, dst, src):
        """imul dst, src (64-bit)"""
        self._rex_rb(src, dst)
        self.emit_byte(0x0F)
        self.emit_byte(0xAF)
        self.emit_byte(self._modrm(0b11, dst & 7, src & 7))

    def cqo(self):
        """符号扩展 RAX -> RDX:RAX"""
        self.emit_byte(0x48)
        self.emit_byte(0x99)

    def idiv_reg(self, reg):
        """idiv reg (有符号除法, RDX:RAX / reg)"""
        self._rex_w(0, (reg >> 3) & 1)
        self.emit_byte(0xF7)
        self.emit_byte(self._modrm(0b11, 7, reg & 7))

    def neg_reg(self, reg):
        """neg reg"""
        self._rex_w(0, (reg >> 3) & 1)
        self.emit_byte(0xF7)
        self.emit_byte(self._modrm(0b11, 3, reg & 7))

    def inc_reg(self, reg):
        """inc reg"""
        self._rex_w(0, (reg >> 3) & 1)
        self.emit_byte(0xFF)
        self.emit_byte(self._modrm(0b11, 0, reg & 7))

    def dec_reg(self, reg):
        """dec reg"""
        self._rex_w(0, (reg >> 3) & 1)
        self.emit_byte(0xFF)
        self.emit_byte(self._modrm(0b11, 1, reg & 7))

    # === 位运算 ===
    def and_reg_reg(self, dst, src):
        """and dst, src"""
        self._rex_rb(src, dst)
        self.emit_byte(0x21)
        self.emit_byte(self._modrm(0b11, src & 7, dst & 7))

    def or_reg_reg(self, dst, src):
        """or dst, src"""
        self._rex_rb(src, dst)
        self.emit_byte(0x09)
        self.emit_byte(self._modrm(0b11, src & 7, dst & 7))

    def xor_reg_reg(self, dst, src):
        """xor dst, src"""
        self._rex_rb(src, dst)
        self.emit_byte(0x31)
        self.emit_byte(self._modrm(0b11, src & 7, dst & 7))

    def not_reg(self, reg):
        """not reg"""
        self._rex_w(0, (reg >> 3) & 1)
        self.emit_byte(0xF7)
        self.emit_byte(self._modrm(0b11, 2, reg & 7))

    def shl_reg_cl(self, reg):
        """shl reg, cl"""
        self._rex_w(0, (reg >> 3) & 1)
        self.emit_byte(0xD3)
        self.emit_byte(self._modrm(0b11, 4, reg & 7))

    def shr_reg_cl(self, reg):
        """shr reg, cl"""
        self._rex_w(0, (reg >> 3) & 1)
        self.emit_byte(0xD3)
        self.emit_byte(self._modrm(0b11, 5, reg & 7))

    # === 比较指令 ===
    def cmp_reg_reg(self, a, b):
        """cmp a, b"""
        self._rex_rb(b, a)
        self.emit_byte(0x39)
        self.emit_byte(self._modrm(0b11, b & 7, a & 7))

    def cmp_reg_imm(self, reg, imm):
        """cmp reg, imm (64-bit)"""
        self.emit_byte(0x48)  # REX.W
        if -128 <= imm <= 127:
            self.emit_byte(0x83)
            self.emit_byte(self._modrm(0b11, 7, reg & 7))
            self.emit_int8(imm)
        else:
            self.emit_byte(0x81)
            self.emit_byte(self._modrm(0b11, 7, reg & 7))
            self.emit_int32(imm)

    def test_reg_reg(self, a, b):
        """test a, b"""
        self._rex_rb(b, a)
        self.emit_byte(0x85)
        self.emit_byte(self._modrm(0b11, b & 7, a & 7))

    # === 浮点指令 (SSE2) ===
    def movsd_reg_reg(self, dst, src):
        """movsd dst, src"""
        self.emit_byte(0xF2)
        if dst >= 8 or src >= 8:
            self._rex(0, (src >> 3) & 1, 0, (dst >> 3) & 1)
        self.emit_byte(0x0F)
        self.emit_byte(0x10)
        self.emit_byte(self._modrm(0b11, src & 7, dst & 7))

    def movsd_reg_imm(self, reg, value):
        """movsd reg, [rip + offset]  （加载浮点常量）
        返回需要回填的 32 位偏移位置
        """
        self.emit_byte(0xF2)
        if reg >= 8:
            self._rex(0, 0, 0, 1)
        self.emit_byte(0x0F)
        self.emit_byte(0x10)
        self.emit_byte(self._modrm(0b00, reg & 7, 5))  # RIP-relative
        self.emit_int32(0)  # 占位，后续回填
        # 记录需要回填的位置
        return self.current_offset() - 4

    def addsd_reg_reg(self, dst, src):
        """addsd dst, src"""
        self.emit_byte(0xF2)
        self.emit_byte(0x0F)
        self.emit_byte(0x58)
        self.emit_byte(self._modrm(0b11, src & 7, dst & 7))

    def subsd_reg_reg(self, dst, src):
        """subsd dst, src"""
        self.emit_byte(0xF2)
        self.emit_byte(0x0F)
        self.emit_byte(0x5C)
        self.emit_byte(self._modrm(0b11, src & 7, dst & 7))

    def mulsd_reg_reg(self, dst, src):
        """mulsd dst, src"""
        self.emit_byte(0xF2)
        self.emit_byte(0x0F)
        self.emit_byte(0x59)
        self.emit_byte(self._modrm(0b11, src & 7, dst & 7))

    def divsd_reg_reg(self, dst, src):
        """divsd dst, src"""
        self.emit_byte(0xF2)
        self.emit_byte(0x0F)
        self.emit_byte(0x5E)
        self.emit_byte(self._modrm(0b11, src & 7, dst & 7))

    def xorpd_xmm(self, reg):
        """xorpd xmm_reg, xmm_reg (清零)"""
        self.emit_byte(0x66)
        self.emit_byte(0x0F)
        self.emit_byte(0x57)
        self.emit_byte(self._modrm(0b11, reg & 7, reg & 7))

    def cvtsi2sd(self, xmm_reg, gpr_reg):
        """cvtsi2sd xmm, gpr (int64 -> double)"""
        self.emit_byte(0xF2)
        self._rex_rb(0, gpr_reg)
        self.emit_byte(0x0F)
        self.emit_byte(0x2A)
        self.emit_byte(self._modrm(0b11, xmm_reg & 7, gpr_reg & 7))

    def cvtsd2si(self, gpr_reg, xmm_reg):
        """cvttsd2si gpr, xmm (double -> int64, 截断)"""
        self.emit_byte(0xF2)
        self._rex_rb(gpr_reg, 0)
        self.emit_byte(0x0F)
        self.emit_byte(0x2C)
        self.emit_byte(self._modrm(0b11, gpr_reg & 7, xmm_reg & 7))

    def ucomisd(self, a, b):
        """ucomisd xmm_a, xmm_b"""
        self.emit_byte(0x66)
        self.emit_byte(0x0F)
        self.emit_byte(0x2E)
        self.emit_byte(self._modrm(0b11, b & 7, a & 7))

    # === 跳转指令 ===
    def jmp_rel32(self):
        """jmp rel32（返回 offset 供回填）"""
        self.emit_byte(0xE9)
        offset_pos = self.current_offset()
        self.emit_int32(0)  # 占位
        return offset_pos

    def jmp_rel8(self, offset=0):
        """jmp rel8"""
        self.emit_byte(0xEB)
        pos = self.current_offset()
        self.emit_int8(offset)
        return pos

    def je_rel32(self):
        """je rel32"""
        self.emit_byte(0x0F)
        self.emit_byte(0x84)
        pos = self.current_offset()
        self.emit_int32(0)
        return pos

    def jne_rel32(self):
        """jne rel32"""
        self.emit_byte(0x0F)
        self.emit_byte(0x85)
        pos = self.current_offset()
        self.emit_int32(0)
        return pos

    def jl_rel32(self):
        """jl rel32"""
        self.emit_byte(0x0F)
        self.emit_byte(0x8C)
        pos = self.current_offset()
        self.emit_int32(0)
        return pos

    def jle_rel32(self):
        """jle rel32"""
        self.emit_byte(0x0F)
        self.emit_byte(0x8E)
        pos = self.current_offset()
        self.emit_int32(0)
        return pos

    def jg_rel32(self):
        """jg rel32"""
        self.emit_byte(0x0F)
        self.emit_byte(0x8F)
        pos = self.current_offset()
        self.emit_int32(0)
        return pos

    def jge_rel32(self):
        """jge rel32"""
        self.emit_byte(0x0F)
        self.emit_byte(0x8D)
        pos = self.current_offset()
        self.emit_int32(0)
        return pos

    def sete(self, reg):
        """sete reg (byte register)"""
        self.emit_byte(0x0F)
        self.emit_byte(0x94)
        self.emit_byte(self._modrm(0b11, 0, reg & 7))

    def setne(self, reg):
        """setne reg"""
        self.emit_byte(0x0F)
        self.emit_byte(0x95)
        self.emit_byte(self._modrm(0b11, 0, reg & 7))

    def setl(self, reg):
        """setl reg"""
        self.emit_byte(0x0F)
        self.emit_byte(0x9C)
        self.emit_byte(self._modrm(0b11, 0, reg & 7))

    def setle(self, reg):
        """setle reg"""
        self.emit_byte(0x0F)
        self.emit_byte(0x9E)
        self.emit_byte(self._modrm(0b11, 0, reg & 7))

    def setg(self, reg):
        """setg reg"""
        self.emit_byte(0x0F)
        self.emit_byte(0x9F)
        self.emit_byte(self._modrm(0b11, 0, reg & 7))

    def setge(self, reg):
        """setge reg"""
        self.emit_byte(0x0F)
        self.emit_byte(0x9D)
        self.emit_byte(self._modrm(0b11, 0, reg & 7))

    def movzx_reg32_reg8(self, dst32, src8):
        """movzx dst32, src8 (零扩展)"""
        self.emit_byte(0x0F)
        self.emit_byte(0xB6)
        self.emit_byte(self._modrm(0b11, dst32 & 7, src8 & 7))

    # === 调用/返回 ===
    def call_rel32(self):
        """call rel32（返回 offset 供回填）"""
        self.emit_byte(0xE8)
        pos = self.current_offset()
        self.emit_int32(0)
        return pos

    def call_reg(self, reg):
        """call reg"""
        self._rex_w(0, (reg >> 3) & 1)
        self.emit_byte(0xFF)
        self.emit_byte(self._modrm(0b11, 2, reg & 7))

    def ret(self):
        """ret"""
        self.emit_byte(0xC3)

    # === 栈操作 ===
    def push_reg(self, reg):
        """push reg"""
        if reg >= 8:
            self.emit_byte(0x41)
        self.emit_byte(0x50 + (reg & 7))

    def pop_reg(self, reg):
        """pop reg"""
        if reg >= 8:
            self.emit_byte(0x41)
        self.emit_byte(0x58 + (reg & 7))

    def sub_rsp_imm(self, imm):
        """sub rsp, imm"""
        self.emit_byte(0x48)
        if -128 <= imm <= 127:
            self.emit_byte(0x83)
            self.emit_byte(0xEC)
            self.emit_int8(imm)
        else:
            self.emit_byte(0x81)
            self.emit_byte(0xEC)
            self.emit_int32(imm)

    def add_rsp_imm(self, imm):
        """add rsp, imm"""
        self.emit_byte(0x48)
        if -128 <= imm <= 127:
            self.emit_byte(0x83)
            self.emit_byte(0xC4)
            self.emit_int8(imm)
        else:
            self.emit_byte(0x81)
            self.emit_byte(0xC4)
            self.emit_int32(imm)

    # === NOP ===
    def nop(self):
        self.emit_byte(0x90)

    # === 系统调用 ===
    def syscall(self):
        """syscall"""
        self.emit_byte(0x0F)
        self.emit_byte(0x05)

    # === LEA 指令 ===
    def lea_reg_rip(self, reg, offset):
        """lea reg, [rip + offset] (RIP-relative LEA)
        返回需要回填的 32 位偏移位置
        """
        self._rex_rb(reg, 0)
        self.emit_byte(0x8D)
        self.emit_byte(self._modrm(0b00, reg & 7, 5))  # RIP-relative
        self.emit_int32(0)  # 占位
        return self.current_offset() - 4

    # === 回填跳转偏移 ===
    def patch_rel32(self, offset, target):
        """回填 32 位相对跳转"""
        rel = target - (offset + 4)
        struct.pack_into('<i', self.code, offset, rel)

    def patch_imm32(self, offset, value):
        """回填 32 位立即数"""
        struct.pack_into('<I', self.code, offset, value)

    def get_code(self):
        return bytes(self.code)
