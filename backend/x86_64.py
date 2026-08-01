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
# Cycle 74: 扩展 XMM 寄存器常量（XMM8-XMM15 仅在 SSE 指令有 REX 前缀时可访问）
XMM8,  XMM9,  XMM10, XMM11 = 8,  9,  10, 11
XMM12, XMM13, XMM14, XMM15 = 12, 13, 14, 15
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
        self.code.extend(struct.pack("<I", v & 0xFFFFFFFF))

    def emit_uint64(self, v):
        self.code.extend(struct.pack("<Q", v & 0xFFFFFFFFFFFFFFFF))

    def emit_int32(self, v):
        self.code.extend(struct.pack("<i", v))

    def emit_int8(self, v):
        self.code.extend(struct.pack("<b", v))

    def current_offset(self):
        return len(self.code)

    # === ModR/M 编码 ===
    def _modrm(self, mod, reg, rm):
        return ((mod & 3) << 6) | ((reg & 7) << 3) | (rm & 7)

    def _sib(self, scale, index, base):
        """SIB 字节: scale(2) | index(3) | base(3)"""
        return ((scale & 3) << 6) | ((index & 7) << 3) | (base & 7)

    def _rex(self, w=0, r=0, x=0, b=0):
        rex = 0x40 | (w << 3) | (r << 2) | (x << 1) | b
        if rex != 0x40:
            self.emit_byte(rex)

    def _rex_w(self, r=0, b=0):
        self._rex(1, r, 0, b)

    def _rex_rb(self, r, b):
        """REX 前缀（64位操作），r 和 b 可以 >= 8"""
        self._rex(1, (r >> 3) & 1, 0, (b >> 3) & 1)

    def _rex_xmm(self, r_ext, b_ext):
        """REX 前缀（SSE/SSE2 指令专用，W=0）。

        注意：SSE 指令的操作宽度由 mandatory prefix（0xF2/0x66/0xF3）
        决定，不是由 REX.W 决定，所以 REX.W=0。
        仅在 r_ext 或 b_ext 不为 0 时才输出 REX 字节（与 _rex 保持一致：
        rex==0x40 时不输出）。

        参数:
            r_ext: ModR/M.reg 字段的扩展位（即 (reg_num >> 3) & 1，范围 0 或 1）
            b_ext: ModR/M.rm  字段的扩展位（即 (rm_num  >> 3) & 1，范围 0 或 1）
        """
        self._rex(0, r_ext & 1, 0, b_ext & 1)

    # === MOV 指令 ===
    def mov_reg_imm64(self, reg, imm):
        """mov reg, imm64"""
        if 0 <= imm <= 0x7FFFFFFF:
            # 使用 mov r/m64, imm32（REX.W + C7 + ModR/M + imm32）
            # 这会零扩展 32 位立即数到 64 位
            # Cycle 70 FIX: 原硬编码 0x48 忽略了 R8-R15（编号 ≥8）需要 REX.B=1，
            #   导致 r/m=reg&7=4 时 REX.B=0→RSP 而非 REX.B=1→R12，产生 SIGSEGV。
            #   用 _rex_rb(0, reg) 统一生成 W=1 + 正确 REX.B/R 位。
            self._rex_rb(0, reg)
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
        needs_sib = (base & 7) == RSP  # RSP/R12 需要 SIB 字节
        if -128 <= offset <= 127:
            self.emit_byte(0x8B)
            if needs_sib:
                self.emit_byte(self._modrm(0b01, reg & 7, 0b100))  # rm=SIB
                self.emit_byte(self._sib(0, 0b100, base & 7))      # scale=1, no index
                self.emit_int8(offset)
            else:
                self.emit_byte(self._modrm(0b01, reg & 7, base & 7))
                self.emit_int8(offset)
        else:
            self.emit_byte(0x8B)
            if needs_sib:
                self.emit_byte(self._modrm(0b10, reg & 7, 0b100))  # rm=SIB
                self.emit_byte(self._sib(0, 0b100, base & 7))      # scale=1, no index
                self.emit_int32(offset)
            else:
                self.emit_byte(self._modrm(0b10, reg & 7, base & 7))
                self.emit_int32(offset)

    def mov_mem_reg(self, base, offset, reg):
        """mov [base + offset], reg (64-bit)"""
        self._rex_rb(reg, base)
        needs_sib = (base & 7) == RSP  # RSP/R12 需要 SIB 字节
        if -128 <= offset <= 127:
            self.emit_byte(0x89)
            if needs_sib:
                self.emit_byte(self._modrm(0b01, reg & 7, 0b100))  # rm=SIB
                self.emit_byte(self._sib(0, 0b100, base & 7))      # scale=1, no index
                self.emit_int8(offset)
            else:
                self.emit_byte(self._modrm(0b01, reg & 7, base & 7))
                self.emit_int8(offset)
        else:
            self.emit_byte(0x89)
            if needs_sib:
                self.emit_byte(self._modrm(0b10, reg & 7, 0b100))  # rm=SIB
                self.emit_byte(self._sib(0, 0b100, base & 7))      # scale=1, no index
                self.emit_int32(offset)
            else:
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
        # Cycle 70 FIX: 原硬编码 0x48 忽略 R8-R15 需要 REX.B
        self._rex_w(0, (reg >> 3) & 1)
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
        # Cycle 70 FIX: 原硬编码 0x48 忽略 R8-R15 需要 REX.B
        self._rex_w(0, (reg >> 3) & 1)
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

    def shl_reg_imm(self, reg, imm):
        """shl reg, imm8 (64-bit)"""
        self._rex_w(0, (reg >> 3) & 1)
        if imm == 1:
            # D3 /4 无 imm8：shl reg, 1（但此形式与 shl reg,cl 共享；另用 C1 /4 ib 统一）
            pass
        # C1 /4 ib = shl r/m64, imm8（所有立即数都走该形式，imm=1 也合法）
        self.emit_byte(0xC1)
        self.emit_byte(self._modrm(0b11, 4, reg & 7))
        self.emit_byte(imm & 0xFF)

    def shr_reg_cl(self, reg):
        """shr reg, cl"""
        self._rex_w(0, (reg >> 3) & 1)
        self.emit_byte(0xD3)
        self.emit_byte(self._modrm(0b11, 5, reg & 7))

    def and_reg_imm(self, reg, imm):
        """and reg, imm (64-bit)"""
        # Cycle 70 FIX: 原硬编码 0x48 忽略 R8-R15 需要 REX.B
        self._rex_w(0, (reg >> 3) & 1)
        if -128 <= imm <= 127:
            self.emit_byte(0x83)
            self.emit_byte(self._modrm(0b11, 4, reg & 7))
            self.emit_int8(imm)
        else:
            self.emit_byte(0x81)
            self.emit_byte(self._modrm(0b11, 4, reg & 7))
            self.emit_int32(imm)

    def or_reg_imm(self, reg, imm):
        """or reg, imm (64-bit) — REG_FIELD = 1"""
        self._rex_w(0, (reg >> 3) & 1)
        if -128 <= imm <= 127:
            self.emit_byte(0x83)
            self.emit_byte(self._modrm(0b11, 1, reg & 7))
            self.emit_int8(imm)
        else:
            self.emit_byte(0x81)
            self.emit_byte(self._modrm(0b11, 1, reg & 7))
            self.emit_int32(imm)

    def xor_reg_imm(self, reg, imm):
        """xor reg, imm (64-bit) — REG_FIELD = 6"""
        self._rex_w(0, (reg >> 3) & 1)
        if -128 <= imm <= 127:
            self.emit_byte(0x83)
            self.emit_byte(self._modrm(0b11, 6, reg & 7))
            self.emit_int8(imm)
        else:
            self.emit_byte(0x81)
            self.emit_byte(self._modrm(0b11, 6, reg & 7))
            self.emit_int32(imm)

    def shr_reg_imm(self, reg, imm):
        """shr reg, imm8 (64-bit) — 逻辑右移，REG_FIELD = 5"""
        self._rex_w(0, (reg >> 3) & 1)
        # C1 /5 ib = shr r/m64, imm8
        self.emit_byte(0xC1)
        self.emit_byte(self._modrm(0b11, 5, reg & 7))
        self.emit_byte(imm & 0xFF)

    def sar_reg_cl(self, reg):
        """sar reg, cl — 算术右移（按 RCX 低 8 位），REG_FIELD = 7"""
        self._rex_w(0, (reg >> 3) & 1)
        # D3 /7 = sar r/m64, cl
        self.emit_byte(0xD3)
        self.emit_byte(self._modrm(0b11, 7, reg & 7))

    def sar_reg_imm(self, reg, imm):
        """sar reg, imm8 (64-bit) — 算术右移（符号位填充），REG_FIELD = 7"""
        self._rex_w(0, (reg >> 3) & 1)
        # C1 /7 ib = sar r/m64, imm8
        self.emit_byte(0xC1)
        self.emit_byte(self._modrm(0b11, 7, reg & 7))
        self.emit_byte(imm & 0xFF)

    # === 比较指令 ===
    def cmp_reg_reg(self, a, b):
        """cmp a, b"""
        self._rex_rb(b, a)
        self.emit_byte(0x39)
        self.emit_byte(self._modrm(0b11, b & 7, a & 7))

    def cmp_reg_imm(self, reg, imm):
        """cmp reg, imm (64-bit)"""
        # Cycle 70 FIX: 原硬编码 0x48 忽略 R8-R15 需要 REX.B
        self._rex_w(0, (reg >> 3) & 1)
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

        Cycle 74 FIX: 原实现当 reg>=8 时硬编码 `_rex(0, 0, 0, 1)`（REX.B=1），
        但 reg 位于 ModR/M.reg 字段（_modrm(0b00, reg&7, 5) 中第二个参数），
        需要 REX.R=(reg>>3)&1 而不是 REX.B。RIP-relative 的 rm=5（disp32 编码）
        固定为 5<8，不需要 REX.B。原错误编码会使 REX 扩展 rm 侧（低 3 位=5，
        加 B=1 后 rm=13→R13），在没有 R13 的场景下行为未定义。
        """
        self.emit_byte(0xF2)
        self._rex_xmm((reg >> 3) & 1, 0)  # reg 在 ModR/M.reg 侧
        self.emit_byte(0x0F)
        self.emit_byte(0x10)
        self.emit_byte(self._modrm(0b00, reg & 7, 5))  # RIP-relative
        self.emit_int32(0)  # 占位，后续回填
        # 记录需要回填的位置
        return self.current_offset() - 4

    # === RIP-relative MOV 指令 ===
    def mov_reg_rip(self, reg):
        """mov reg, [rip + disp32] (RIP-relative 64-bit load)
        返回需要回填的 32 位偏移位置
        """
        self._rex_rb(reg, 0)
        self.emit_byte(0x8B)
        self.emit_byte(self._modrm(0b00, reg & 7, 5))  # RIP-relative
        self.emit_int32(0)  # 占位
        return self.current_offset() - 4

    def mov_rip_reg(self, reg):
        """mov [rip + disp32], reg (RIP-relative 64-bit store)
        返回需要回填的 32 位偏移位置
        """
        self._rex_rb(reg, 0)
        self.emit_byte(0x89)
        self.emit_byte(self._modrm(0b00, reg & 7, 5))  # RIP-relative
        self.emit_int32(0)  # 占位
        return self.current_offset() - 4

    def movsd_reg_mem(self, reg, base, offset):
        """movsd reg, [base + offset]  （从内存加载双精度浮点数到 XMM 寄存器）"""
        self.emit_byte(0xF2)
        # REX 前缀：需要 base >= 8 或 reg >= 8 时扩展
        rex_r = (reg >> 3) & 1
        rex_b = (base >> 3) & 1
        if rex_r or rex_b:
            self._rex(0, rex_r, 0, rex_b)
        self.emit_byte(0x0F)
        self.emit_byte(0x10)  # movsd xmm, [mem]  opcode
        # 修复：RSP/R12（rm 低 3 位 = 4）必须加 SIB 字节
        needs_sib = (base & 7) == RSP
        if -128 <= offset <= 127:
            if needs_sib:
                self.emit_byte(self._modrm(0b01, reg & 7, 0b100))  # rm=SIB
                self.emit_byte(self._sib(0, 0b100, base & 7))
            else:
                self.emit_byte(self._modrm(0b01, reg & 7, base & 7))
            self.emit_int8(offset)
        else:
            if needs_sib:
                self.emit_byte(self._modrm(0b10, reg & 7, 0b100))  # rm=SIB
                self.emit_byte(self._sib(0, 0b100, base & 7))
            else:
                self.emit_byte(self._modrm(0b10, reg & 7, base & 7))
            self.emit_int32(offset)

    def movsd_mem_reg(self, base, offset, reg):
        """movsd [base + offset], reg  （将 XMM 寄存器中的双精度浮点数存储到内存）"""
        self.emit_byte(0xF2)
        # REX 前缀
        rex_r = (reg >> 3) & 1
        rex_b = (base >> 3) & 1
        if rex_r or rex_b:
            self._rex(0, rex_r, 0, rex_b)
        self.emit_byte(0x0F)
        self.emit_byte(0x11)  # movsd [mem], xmm  opcode
        # 修复：RSP/R12（rm 低 3 位 = 4）必须加 SIB 字节
        needs_sib = (base & 7) == RSP
        if -128 <= offset <= 127:
            if needs_sib:
                self.emit_byte(self._modrm(0b01, reg & 7, 0b100))  # rm=SIB
                self.emit_byte(self._sib(0, 0b100, base & 7))
            else:
                self.emit_byte(self._modrm(0b01, reg & 7, base & 7))
            self.emit_int8(offset)
        else:
            if needs_sib:
                self.emit_byte(self._modrm(0b10, reg & 7, 0b100))  # rm=SIB
                self.emit_byte(self._sib(0, 0b100, base & 7))
            else:
                self.emit_byte(self._modrm(0b10, reg & 7, base & 7))
            self.emit_int32(offset)

    def movq_xmm_gpr(self, xmm_reg, gpr_reg):
        """movq xmm_reg, gpr_reg  — 将 GPR 的低 64 位搬移到 XMM 寄存器"""
        self.emit_byte(0xF2)
        rex_r = (xmm_reg >> 3) & 1
        rex_b = (gpr_reg >> 3) & 1
        if rex_r or rex_b:
            self._rex(0, rex_r, 0, rex_b)
        self.emit_byte(0x0F)
        self.emit_byte(0x6E)  # movq xmm, r/m64
        self.emit_byte(self._modrm(0b11, xmm_reg & 7, gpr_reg & 7))

    def movq_gpr_xmm(self, gpr_reg, xmm_reg):
        """movq gpr_reg, xmm_reg  — 将 XMM 寄存器的低 64 位搬移到 GPR"""
        self.emit_byte(0xF2)
        rex_r = (xmm_reg >> 3) & 1
        rex_b = (gpr_reg >> 3) & 1
        if rex_r or rex_b:
            self._rex(0, rex_r, 0, rex_b)
        self.emit_byte(0x0F)
        self.emit_byte(0xD6)  # movq r/m64, xmm
        self.emit_byte(self._modrm(0b11, xmm_reg & 7, gpr_reg & 7))

    def addsd_reg_reg(self, dst, src):
        """addsd dst, src

        Cycle 74 FIX: 原实现缺少 REX 前缀，当 dst 或 src >= 8（XMM8-XMM15）
        时无法访问扩展寄存器，操作数静默被折叠为低 3 位（XMM0-XMM7）。
        修复：src 在 ModR/M.reg → REX.R；dst 在 ModR/M.rm → REX.B。
        """
        self.emit_byte(0xF2)
        self._rex_xmm((src >> 3) & 1, (dst >> 3) & 1)
        self.emit_byte(0x0F)
        self.emit_byte(0x58)
        self.emit_byte(self._modrm(0b11, src & 7, dst & 7))

    def subsd_reg_reg(self, dst, src):
        """subsd dst, src

        Cycle 74 FIX: 同 addsd——缺少 REX 前缀导致 XMM8-XMM15 静默折叠。
        """
        self.emit_byte(0xF2)
        self._rex_xmm((src >> 3) & 1, (dst >> 3) & 1)
        self.emit_byte(0x0F)
        self.emit_byte(0x5C)
        self.emit_byte(self._modrm(0b11, src & 7, dst & 7))

    def mulsd_reg_reg(self, dst, src):
        """mulsd dst, src

        Cycle 74 FIX: 同 addsd——缺少 REX 前缀导致 XMM8-XMM15 静默折叠。
        """
        self.emit_byte(0xF2)
        self._rex_xmm((src >> 3) & 1, (dst >> 3) & 1)
        self.emit_byte(0x0F)
        self.emit_byte(0x59)
        self.emit_byte(self._modrm(0b11, src & 7, dst & 7))

    def divsd_reg_reg(self, dst, src):
        """divsd dst, src

        Cycle 74 FIX: 同 addsd——缺少 REX 前缀导致 XMM8-XMM15 静默折叠。
        """
        self.emit_byte(0xF2)
        self._rex_xmm((src >> 3) & 1, (dst >> 3) & 1)
        self.emit_byte(0x0F)
        self.emit_byte(0x5E)
        self.emit_byte(self._modrm(0b11, src & 7, dst & 7))

    def xorpd_xmm(self, reg):
        """xorpd xmm_reg, xmm_reg (清零)

        Cycle 74 FIX: 原实现缺少 REX 前缀，XMM8-XMM15 无法正确自清零（被
        折叠为低 3 位）。reg 同时出现在 ModR/M.reg 和 ModR/M.rm 两侧，
        所以 REX.R 和 REX.B 都需要填 (reg>>3)&1。
        """
        self.emit_byte(0x66)
        self._rex_xmm((reg >> 3) & 1, (reg >> 3) & 1)
        self.emit_byte(0x0F)
        self.emit_byte(0x57)
        self.emit_byte(self._modrm(0b11, reg & 7, reg & 7))

    def cvtsi2sd(self, xmm_reg, gpr_reg):
        """cvtsi2sd xmm, gpr (int64 -> double)

        Cycle 74 FIX: 原实现只用 `_rex_rb(0, gpr_reg)`（REX.W=1, R=0,
        B=(gpr>>3)&1），丢失了 xmm 在 ModR/M.reg 侧的 REX.R 扩展。
        当 xmm_reg>=8 时，ModR/M.reg 的低 3 位被解释为 REX.R=0 下的寄存器，
        即 XMM0-XMM7，会写入错误的寄存器（例如 xmm=8 写 XMM0 而不是 XMM8）。
        正确的 REX 应为 W=1 + R=(xmm>>3)&1 + B=(gpr>>3)&1。注意 cvtsi2sd
        当源是 64 位 GPR 时**必须**有 REX.W=1（区别于 32 位版本），所以这里
        不能用 _rex_xmm（W=0）。
        """
        self.emit_byte(0xF2)
        self._rex(1, (xmm_reg >> 3) & 1, 0, (gpr_reg >> 3) & 1)
        self.emit_byte(0x0F)
        self.emit_byte(0x2A)
        self.emit_byte(self._modrm(0b11, xmm_reg & 7, gpr_reg & 7))

    def cvtsd2si(self, gpr_reg, xmm_reg):
        """cvttsd2si gpr, xmm (double -> int64, 截断)

        Cycle 74 FIX: 原实现用 `_rex_rb(gpr_reg, 0)` 计算 REX.R=(gpr>>3)&1
        和 REX.B=0，但 xmm 在 ModR/M.rm 侧，当 xmm>=8 时需要 REX.B=(xmm>>3)&1。
        原 B=0 会把 XMM8-XMM15 折叠成 XMM0-XMM7，读取错误的寄存器。
        注意：cvttsd2si 目标是 64 位 GPR 时必须 REX.W=1。
        """
        self.emit_byte(0xF2)
        self._rex(1, (gpr_reg >> 3) & 1, 0, (xmm_reg >> 3) & 1)
        self.emit_byte(0x0F)
        self.emit_byte(0x2C)
        self.emit_byte(self._modrm(0b11, gpr_reg & 7, xmm_reg & 7))

    def ucomisd(self, a, b):
        """ucomisd xmm_a, xmm_b

        Cycle 74 FIX: 原实现缺少 REX 前缀。ucomisd ModR/M.reg = b，ModR/M.rm = a，
        故 REX.R=(b>>3)&1，REX.B=(a>>3)&1。原 XMM8-XMM15 会静默折叠。
        """
        self.emit_byte(0x66)
        self._rex_xmm((b >> 3) & 1, (a >> 3) & 1)
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

    # 短跳（-128..+127，jcc rel8 编码）
    def je_rel8(self, offset=0):
        """je rel8"""
        self.emit_byte(0x74)
        pos = self.current_offset()
        self.emit_int8(offset)
        return pos

    def jne_rel8(self, offset=0):
        """jne rel8"""
        self.emit_byte(0x75)
        pos = self.current_offset()
        self.emit_int8(offset)
        return pos

    def jl_rel8(self, offset=0):
        """jl rel8"""
        self.emit_byte(0x7C)
        pos = self.current_offset()
        self.emit_int8(offset)
        return pos

    def jle_rel8(self, offset=0):
        """jle rel8"""
        self.emit_byte(0x7E)
        pos = self.current_offset()
        self.emit_int8(offset)
        return pos

    def jg_rel8(self, offset=0):
        """jg rel8"""
        self.emit_byte(0x7F)
        pos = self.current_offset()
        self.emit_int8(offset)
        return pos

    def jge_rel8(self, offset=0):
        """jge rel8"""
        self.emit_byte(0x7D)
        pos = self.current_offset()
        self.emit_int8(offset)
        return pos

    def jb_rel8(self, offset=0):
        """jb rel8（unsigned <）"""
        self.emit_byte(0x72)
        pos = self.current_offset()
        self.emit_int8(offset)
        return pos

    def jae_rel8(self, offset=0):
        """jae rel8（unsigned >=）"""
        self.emit_byte(0x73)
        pos = self.current_offset()
        self.emit_int8(offset)
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
        struct.pack_into("<i", self.code, offset, rel)

    def patch_imm32(self, offset, value):
        """回填 32 位立即数"""
        struct.pack_into("<I", self.code, offset, value)

    def get_code(self):
        return bytes(self.code)
