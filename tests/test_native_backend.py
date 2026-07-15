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


class TestLiveIntervalAnalysis(unittest.TestCase):
    """活跃区间分析测试"""

    def test_analyze_simple_const(self):
        """简单常量加载的活跃区间分析"""
        codegen = NativeCodeGen()
        fn = LIRFunction("test", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=42, const_type="int"),
            LIRReturn(),
        ]
        gpr_intervals, xmm_intervals = codegen._analyze_live_intervals(fn)
        # 应有一个 GPR 区间（const_42）
        self.assertEqual(len(gpr_intervals), 1)
        self.assertEqual(len(xmm_intervals), 0)
        self.assertEqual(gpr_intervals[0].vreg, "const_42")
        # first_use = 0 (LIRLoadConst 定义), last_use = 0 (没有后续使用)
        self.assertEqual(gpr_intervals[0].start, 0)
        self.assertEqual(gpr_intervals[0].end, 0)

    def test_analyze_binop_vregs(self):
        """BinOp 操作数和目标的活跃区间"""
        codegen = NativeCodeGen()
        fn = LIRFunction("test", [], INT_TYPE)
        add_op = LIRBinOp(op="+")
        add_op.src_locs = [("a", INT_TYPE), ("b", INT_TYPE)]
        add_op.dst_loc = ("c", INT_TYPE)
        fn.body = [
            LIRLoadConst(value=1, const_type="int"),  # idx 0: const_1 defined
            LIRLoadConst(value=2, const_type="int"),  # idx 1: const_2 defined
            add_op,                                    # idx 2: uses const_1, const_2, defines c
            LIRReturn(),
        ]
        gpr_intervals, xmm_intervals = codegen._analyze_live_intervals(fn)
        # 应该有 3 个 GPR 区间: const_1, const_2, c
        vreg_names = {i.vreg for i in gpr_intervals}
        self.assertIn("const_1", vreg_names)
        self.assertIn("const_2", vreg_names)
        self.assertIn("c", vreg_names)

    def test_analyze_float_const(self):
        """浮点常量应归类为 XMM 区间"""
        codegen = NativeCodeGen()
        fn = LIRFunction("test", [], FLOAT_TYPE)
        fn.body = [
            LIRLoadConst(value=3.14, const_type="float"),
            LIRReturn(),
        ]
        gpr_intervals, xmm_intervals = codegen._analyze_live_intervals(fn)
        self.assertEqual(len(gpr_intervals), 0)
        self.assertEqual(len(xmm_intervals), 1)
        self.assertEqual(xmm_intervals[0].vreg, "fconst_3.14")

    def test_analyze_empty_body(self):
        """空函数体应返回空区间"""
        codegen = NativeCodeGen()
        fn = LIRFunction("test", [], INT_TYPE)
        fn.body = [
            LIRReturn(),
        ]
        gpr_intervals, xmm_intervals = codegen._analyze_live_intervals(fn)
        self.assertEqual(len(gpr_intervals), 0)
        self.assertEqual(len(xmm_intervals), 0)

    def test_analyze_loadreg_dst(self):
        """LIRLoadReg 的 dst_loc 应被追踪为定义"""
        codegen = NativeCodeGen()
        fn = LIRFunction("test", [], INT_TYPE)
        load_reg = LIRLoadReg()
        load_reg.src_locs = [("const_42", INT_TYPE)]
        load_reg.dst_loc = ("moved_val", INT_TYPE)
        fn.body = [
            LIRLoadConst(value=42, const_type="int"),
            load_reg,
            LIRReturn(),
        ]
        gpr_intervals, _ = codegen._analyze_live_intervals(fn)
        vreg_names = {i.vreg for i in gpr_intervals}
        self.assertIn("const_42", vreg_names)
        self.assertIn("moved_val", vreg_names)

    def test_analyze_branch_cond_reg(self):
        """LIRBranch 的 cond_reg 应被追踪为使用"""
        codegen = NativeCodeGen()
        fn = LIRFunction("test", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=1, const_type="int"),
            LIRBranch(cond_reg="const_1", true_label="yes", false_label="no"),
            LIRLabel(name="yes"),
            LIRReturn(),
            LIRLabel(name="no"),
            LIRReturn(),
        ]
        gpr_intervals, _ = codegen._analyze_live_intervals(fn)
        vreg_names = {i.vreg for i in gpr_intervals}
        self.assertIn("const_1", vreg_names)
        # const_1 的 last_use 应该在 branch 指令处
        const_1_interval = next(i for i in gpr_intervals if i.vreg == "const_1")
        self.assertEqual(const_1_interval.start, 0)
        self.assertEqual(const_1_interval.end, 1)  # idx 1 = LIRBranch


class TestLinearScanIntegration(unittest.TestCase):
    """LinearScanAllocator 集成到编译流程的测试"""

    def test_linear_scan_used_in_compilation(self):
        """编译函数时应使用 LinearScanAllocator 分配寄存器

        通过验证非重叠 vreg 复用同一物理寄存器来确认
        LinearScanAllocator 确实在工作。
        """
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_reuse", [], INT_TYPE)

        # 构造两个不重叠的虚拟寄存器：
        # const_10 在指令 0 定义，在指令 1 使用（然后不再使用）
        # const_20 在指令 2 定义，在指令 3 使用
        # LinearScanAllocator 应该能复用寄存器
        load1 = LIRLoadConst(value=10, const_type="int")

        # 用掉 const_10，使其生命周期结束
        use1 = LIRUnaryOp(op="-")
        use1.src_locs = [("const_10", INT_TYPE)]
        use1.dst_loc = ("neg_10", INT_TYPE)

        # 加载另一个常量（应该能复用 const_10 的寄存器）
        load2 = LIRLoadConst(value=20, const_type="int")

        use2 = LIRUnaryOp(op="-")
        use2.src_locs = [("const_20", INT_TYPE)]
        use2.dst_loc = ("neg_20", INT_TYPE)

        fn.body = [load1, use1, load2, use2, LIRReturn()]
        lir.functions["test_reuse"] = fn

        # 运行活跃区间分析验证
        gpr_intervals, _ = codegen._analyze_live_intervals(fn)
        vreg_map = {i.vreg: i for i in gpr_intervals}

        # const_10 的区间应该在 const_20 开始前结束
        # （这样 LinearScanAllocator 才能复用寄存器）
        const_10_end = vreg_map["const_10"].end
        const_20_start = vreg_map["const_20"].start
        self.assertLessEqual(const_10_end, const_20_start,
            "const_10 should end before or at const_20 start for register reuse")

        # 验证编译成功
        code = codegen._compile_function(fn)
        self.assertIsInstance(code, bytes)
        self.assertTrue(len(code) > 0)

    def test_run_linear_scan_success(self):
        """_run_linear_scan_alloc 成功时返回 vreg 映射"""
        codegen = NativeCodeGen()
        fn = LIRFunction("test", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=10, const_type="int"),
            LIRLoadConst(value=20, const_type="int"),
            LIRReturn(),
        ]
        result = codegen._run_linear_scan_alloc(fn)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
        # 应该有两个 vreg 的分配
        self.assertIn("const_10", result)
        self.assertIn("const_20", result)
        # 两者都应分配到有效寄存器（非 None）
        self.assertIsNotNone(result["const_10"])
        self.assertIsNotNone(result["const_20"])

    def test_run_linear_scan_empty_function(self):
        """空函数的线性扫描分配应返回空映射"""
        codegen = NativeCodeGen()
        fn = LIRFunction("test", [], INT_TYPE)
        fn.body = [
            LIRReturn(),
        ]
        result = codegen._run_linear_scan_alloc(fn)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 0)

    def test_multiple_vregs_register_reuse(self):
        """多虚拟寄存器场景下寄存器正确复用

        当多个虚拟寄存器的活跃区间不重叠时，
        LinearScanAllocator 应复用物理寄存器，
        从而减少实际使用的物理寄存器数量。
        """
        codegen = NativeCodeGen()
        fn = LIRFunction("test_reuse", [], INT_TYPE)

        # 构造一系列不重叠的 vreg，它们应能复用少量物理寄存器
        instructions = []
        vreg_names = []

        for i in range(20):
            # 每个 vreg 定义后立即被"消耗"（用于 unary op）
            load = LIRLoadConst(value=i, const_type="int")
            neg = LIRUnaryOp(op="-")
            neg.src_locs = [(f"const_{i}", INT_TYPE)]
            neg.dst_loc = (f"neg_{i}", INT_TYPE)
            instructions.append(load)
            instructions.append(neg)
            vreg_names.append(f"const_{i}")
            vreg_names.append(f"neg_{i}")

        instructions.append(LIRReturn())
        fn.body = instructions

        # 运行线性扫描分配
        result = codegen._run_linear_scan_alloc(fn)
        self.assertIsNotNone(result,
            "Allocation should succeed with 20 sequential vregs and 12 GPRs")

        # 统计使用的不同物理寄存器数量
        used_regs = set(result.values())
        # 20 个顺序（不重叠）的 vreg 应该能用很少的物理寄存器
        # （理论上最少只需要 2 个：const_i 和 neg_i 同时活跃）
        self.assertLess(len(used_regs), 10,
            f"Expected significant register reuse, but used {len(used_regs)} regs for 20 vregs")

        # 验证编译成功
        code = codegen._compile_function(fn)
        self.assertIsInstance(code, bytes)
        self.assertTrue(len(code) > 0)

    def test_fallback_when_registers_insufficient(self):
        """寄存器不足时 fallback 到按需分配策略

        当活跃 vreg 数量超过可用寄存器时，
        _run_linear_scan_alloc 应返回 None，
        _compile_function 应 fallback 到按需分配，
        确保编译仍然成功（不崩溃）。
        """
        codegen = NativeCodeGen()
        fn = LIRFunction("test_fallback", [], INT_TYPE)

        # 构造大量同时活跃的 vreg（超过可用 GPR 数量 12）
        # 通过让它们都在最后一条指令中被使用来实现同时活跃
        instructions = []
        src_locs = []

        for i in range(20):
            load = LIRLoadConst(value=i, const_type="int")
            instructions.append(load)
            src_locs.append((f"const_{i}", INT_TYPE))

        # 用一个 call 指令"使用"所有 vreg，使它们都同时活跃
        # （call 使用所有 src_locs 的 vreg）
        call = LIRCall(func_name="dummy", arg_count=20)
        call.src_locs = src_locs
        instructions.append(call)
        instructions.append(LIRReturn())

        fn.body = instructions

        # 线性扫描分配应该失败（返回 None），因为 20 个 vreg 同时活跃
        # 而可用 GPR 只有 12 个
        result = codegen._run_linear_scan_alloc(fn)
        self.assertIsNone(result,
            "Linear scan should fail (return None) when 20 vregs are live simultaneously with 12 GPRs")

        # 但编译应该仍然成功（fallback 到按需分配）
        code = codegen._compile_function(fn)
        self.assertIsInstance(code, bytes)
        self.assertTrue(len(code) > 0)

    def test_preallocated_vregs_used_in_body(self):
        """_compile_body 应正确使用预分配的 vreg 映射"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_prealloc", [], INT_TYPE)

        load = LIRLoadConst(value=42, const_type="int")
        fn.body = [load, LIRReturn()]
        lir.functions["test_prealloc"] = fn

        # 手动构造预分配映射，强制 const_42 使用 R15
        # （正常按需分配会使用 RAX）
        preallocated = {"const_42": R15}

        from nova.backend.x86_64 import X86_64Emitter
        e = X86_64Emitter()
        vregs = {}
        free_gprs = [RAX, RCX, RDX, RBX, R8, R9, R10, R11, R12, R13, R14, R15]
        free_xmms = []

        # 使用预分配的映射调用 _alloc_vreg
        reg = codegen._alloc_vreg("const_42", vregs, free_gprs, free_xmms,
                                  preallocated=preallocated)
        self.assertEqual(reg, R15,
            "preallocated vreg should use the pre-assigned register")
        # 验证 free_gprs 没有弹出 R15（因为是预分配的）
        self.assertIn(R15, free_gprs)

    def test_compile_with_preallocated_none(self):
        """preallocated=None 时应使用按需分配（fallback 模式）"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_fallback_mode", [], INT_TYPE)

        fn.body = [
            LIRLoadConst(value=42, const_type="int"),
            LIRReturn(),
        ]
        lir.functions["test_fallback_mode"] = fn

        from nova.backend.x86_64 import X86_64Emitter
        e = X86_64Emitter()

        # 显式传入 preallocated=None
        codegen._compile_body(e, fn, {}, [], [], [], preallocated=None)
        code = bytes(e.code)
        self.assertTrue(len(code) > 0)

    def test_collect_vreg_info_loadconst(self):
        """_collect_vreg_info 对 LIRLoadConst 返回正确的 defined vreg"""
        codegen = NativeCodeGen()
        instr = LIRLoadConst(value=42, const_type="int")
        used, defined = codegen._collect_vreg_info(instr)
        self.assertEqual(len(used), 0)
        self.assertEqual(len(defined), 1)
        self.assertEqual(defined[0][0], "const_42")
        self.assertFalse(defined[0][1])  # is_float = False

    def test_collect_vreg_info_float(self):
        """_collect_vreg_info 对浮点常量标记 is_float=True"""
        codegen = NativeCodeGen()
        instr = LIRLoadConst(value=3.14, const_type="float")
        used, defined = codegen._collect_vreg_info(instr)
        self.assertEqual(len(defined), 1)
        self.assertTrue(defined[0][1])  # is_float = True

    def test_collect_vreg_info_binop(self):
        """_collect_vreg_info 对 LIRBinOp 正确提取 src 和 dst"""
        codegen = NativeCodeGen()
        instr = LIRBinOp(op="+")
        instr.src_locs = [("a", INT_TYPE), ("b", INT_TYPE)]
        instr.dst_loc = ("c", INT_TYPE)
        used, defined = codegen._collect_vreg_info(instr)
        used_names = [u[0] for u in used]
        def_names = [d[0] for d in defined]
        self.assertIn("a", used_names)
        self.assertIn("b", used_names)
        self.assertIn("c", def_names)

    def test_collect_vreg_info_label_jump(self):
        """LIRLabel 和 LIRJump 不涉及 vreg"""
        codegen = NativeCodeGen()
        used1, def1 = codegen._collect_vreg_info(LIRLabel(name="test"))
        self.assertEqual(len(used1), 0)
        self.assertEqual(len(def1), 0)

        used2, def2 = codegen._collect_vreg_info(LIRJump(target="test"))
        self.assertEqual(len(used2), 0)
        self.assertEqual(len(def2), 0)


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
        """辅助方法：编译包含指定指令的函数体，返回编译后的机器码"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_fn", [], INT_TYPE)
        fn.body = [instr, LIRReturn()]
        lir.functions["test_fn"] = fn
        return codegen._compile_function(fn)

    def test_call_indirect_compilation(self):
        """LIRCallIndirect 应成功编译，生成 call *%r11 间接调用指令"""
        # 无 src_locs 时直接返回（无函数指针）
        code = self._compile_body_with_instr(LIRCallIndirect())
        self.assertIsNotNone(code)
        self.assertTrue(len(code) > 0)

    def test_call_indirect_with_args(self):
        """LIRCallIndirect 带参数时应生成参数传递 + call *%r11 指令"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_fn", [], INT_TYPE)
        fn.body = [
            LIRLoadConst(value=10, const_type="int"),
            LIRLoadConst(value=20, const_type="int"),
        ]
        call = LIRCallIndirect()
        call.src_locs = [
            ("const_10", INT_TYPE),   # 函数指针
            ("const_20", INT_TYPE),   # 参数1
        ]
        fn.body.append(call)
        fn.body.append(LIRReturn())
        lir.functions["test_fn"] = fn
        code = codegen._compile_function(fn)
        self.assertIsNotNone(code)
        self.assertTrue(len(code) > 0)
        # 应包含 call_reg 指令 (FF D3 = call *%r11)
        found = False
        for i in range(len(code) - 2):
            if code[i] == 0xFF and code[i + 1] == 0xD3:
                found = True
                break
        self.assertTrue(found, "Expected call *%r11 (FF D3) for LIRCallIndirect")

    def test_index_compilation(self):
        """LIRIndex 应成功编译（不再抛出 NotImplementedError）"""
        # 无 src_locs 时默认取偏移 LIST_HEADER_SIZE 处的元素
        code = self._compile_body_with_instr(LIRIndex())
        self.assertIsNotNone(code)
        self.assertTrue(len(code) > 0)
        # 应包含 mov_reg_mem 指令 (48 8B)
        found = False
        for i in range(len(code) - 2):
            if code[i] == 0x48 and code[i + 1] == 0x8B:
                found = True
                break
        self.assertTrue(found, "Expected mov_reg_mem (48 8B) for LIRIndex default element access")

    def test_field_access_compilation(self):
        """LIRFieldAccess 应编译成功"""
        instr = LIRFieldAccess(offset=8)
        instr.src_locs = [("RAX", INT_TYPE)]
        instr.dst_loc = ("RBX", INT_TYPE)
        code = self._compile_body_with_instr(instr)
        self.assertIsInstance(code, bytes)
        self.assertGreater(len(code), 0)

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


class TestBinOpDstLoc(unittest.TestCase):
    """LIRBinOp dst_loc 正确性测试"""

    def test_binop_dst_loc_different_from_left(self):
        """BinOp 结果写入 dst_loc 指定的目标寄存器，而非 left_reg

        当左操作数在 BinOp 之后仍被使用时，
        dst_loc 必须分配到不同的物理寄存器，
        因此会产生 mov 指令将结果移到目标寄存器。
        """
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_binop_dst", [], INT_TYPE)

        # 加载两个常量到不同的虚拟寄存器
        load_a = LIRLoadConst(value=10, const_type="int")
        load_b = LIRLoadConst(value=20, const_type="int")

        # BinOp: a + b，结果写入 result_sum
        add_op = LIRBinOp(op="+")
        add_op.src_locs = [("const_10", INT_TYPE), ("const_20", INT_TYPE)]
        add_op.dst_loc = ("result_sum", INT_TYPE)

        # 关键：在加法之后继续使用 const_10，使其活跃区间跨越加法指令
        # 这样 const_10 和 result_sum 必须分配不同的物理寄存器
        second_add = LIRBinOp(op="+")
        second_add.src_locs = [("result_sum", INT_TYPE), ("const_10", INT_TYPE)]
        second_add.dst_loc = ("final_result", INT_TYPE)

        fn.body = [load_a, load_b, add_op, second_add, LIRReturn()]
        lir.functions["test_binop_dst"] = fn

        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)

        # 验证包含加法指令 (48 01 = add r/m64, r64)
        found_add = False
        for i in range(len(code) - 2):
            if code[i] == 0x48 and code[i + 1] == 0x01:
                found_add = True
                break
        self.assertTrue(found_add, "Expected add instruction in compiled code")

        # 验证 result_sum 对应的 vreg 被正确追踪
        # 由于 const_10 在加法后仍被使用，result_sum 必须在不同寄存器中
        # 因此至少有一次 mov 用于将结果从左操作数寄存器移到目标寄存器
        mov_count = 0
        for i in range(len(code) - 2):
            if code[i] == 0x48 and code[i + 1] == 0x89:
                mov_count += 1
        self.assertGreaterEqual(mov_count, 1,
            "Expected at least one mov_reg_reg64 when src is still live")

    def test_multiple_binop_different_vregs(self):
        """连续多个 BinOp 操作不同虚拟寄存器时结果正确写入各自目标"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_multi_binop", [], INT_TYPE)

        # 加载三个常量
        load_a = LIRLoadConst(value=10, const_type="int")
        load_b = LIRLoadConst(value=20, const_type="int")
        load_c = LIRLoadConst(value=5, const_type="int")

        # add1: a + b -> sum_ab
        add1 = LIRBinOp(op="+")
        add1.src_locs = [("const_10", INT_TYPE), ("const_20", INT_TYPE)]
        add1.dst_loc = ("sum_ab", INT_TYPE)

        # add2: sum_ab + c -> total  (使用前一步的结果)
        add2 = LIRBinOp(op="+")
        add2.src_locs = [("sum_ab", INT_TYPE), ("const_5", INT_TYPE)]
        add2.dst_loc = ("total", INT_TYPE)

        fn.body = [load_a, load_b, load_c, add1, add2, LIRReturn()]
        lir.functions["test_multi_binop"] = fn

        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)

        # 验证编译成功且包含加法指令 (48 01 = add r/m64, r64)
        found_add = False
        for i in range(len(code) - 2):
            if code[i] == 0x48 and code[i + 1] == 0x01:
                found_add = True
                break
        self.assertTrue(found_add, "Expected add instruction in compiled code")

    def test_binop_comparison_dst_loc(self):
        """比较运算结果写入 dst_loc 指定的目标寄存器"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_cmp_dst", [], INT_TYPE)

        load_a = LIRLoadConst(value=10, const_type="int")
        load_b = LIRLoadConst(value=20, const_type="int")

        cmp_op = LIRBinOp(op="<")
        cmp_op.src_locs = [("const_10", INT_TYPE), ("const_20", INT_TYPE)]
        cmp_op.dst_loc = ("cmp_result", INT_TYPE)

        fn.body = [load_a, load_b, cmp_op, LIRReturn()]
        lir.functions["test_cmp_dst"] = fn

        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)

        # 验证包含 setl 指令 (0F 9C)
        found_setl = False
        for i in range(len(code) - 1):
            if code[i] == 0x0F and code[i + 1] == 0x9C:
                found_setl = True
                break
        self.assertTrue(found_setl, "Expected setl instruction for < comparison")

    def test_binop_logical_and_dst_loc(self):
        """逻辑与运算结果写入 dst_loc 指定的目标寄存器"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_and_dst", [], INT_TYPE)

        load_a = LIRLoadConst(value=1, const_type="int")
        load_b = LIRLoadConst(value=1, const_type="int")

        and_op = LIRBinOp(op="&&")
        and_op.src_locs = [("const_1", INT_TYPE), ("const_1", INT_TYPE)]
        and_op.dst_loc = ("and_result", INT_TYPE)

        fn.body = [load_a, load_b, and_op, LIRReturn()]
        lir.functions["test_and_dst"] = fn

        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)


class TestUnaryOpDstLoc(unittest.TestCase):
    """LIRUnaryOp dst_loc 正确性测试"""

    def test_unary_neg_dst_loc(self):
        """一元取反结果写入 dst_loc 指定的目标寄存器，而非修改操作数

        当源操作数在 UnaryOp 之后仍被使用时，
        dst_loc 必须分配到不同的物理寄存器，
        因此会产生 mov 指令将结果移到目标寄存器。
        """
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_neg_dst", [], INT_TYPE)

        load_val = LIRLoadConst(value=42, const_type="int")

        neg_op = LIRUnaryOp(op="-")
        neg_op.src_locs = [("const_42", INT_TYPE)]
        neg_op.dst_loc = ("neg_result", INT_TYPE)

        # 关键：在取反之后继续使用 const_42，使其活跃区间跨越取反指令
        # 这样 const_42 和 neg_result 必须分配不同的物理寄存器
        add_op = LIRBinOp(op="+")
        add_op.src_locs = [("neg_result", INT_TYPE), ("const_42", INT_TYPE)]
        add_op.dst_loc = ("final_result", INT_TYPE)

        fn.body = [load_val, neg_op, add_op, LIRReturn()]
        lir.functions["test_neg_dst"] = fn

        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)

        # 验证包含 neg 指令 (48 F7 /3)
        found_neg = False
        for i in range(len(code) - 2):
            if code[i] == 0x48 and code[i + 1] == 0xF7:
                found_neg = True
                break
        self.assertTrue(found_neg, "Expected neg instruction for unary -")

        # 验证有 mov 指令将结果移到目标寄存器
        # 由于 const_42 在取反后仍被使用，neg_result 必须在不同寄存器中
        mov_count = 0
        for i in range(len(code) - 2):
            if code[i] == 0x48 and code[i + 1] == 0x89:
                mov_count += 1
        self.assertGreaterEqual(mov_count, 1,
            "Expected mov to move neg result to dst register when src is still live")

    def test_unary_not_logical_dst_loc(self):
        """逻辑非运算结果写入 dst_loc 指定的目标寄存器"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_not_dst", [], INT_TYPE)

        load_val = LIRLoadConst(value=0, const_type="int")

        not_op = LIRUnaryOp(op="!")
        not_op.src_locs = [("const_0", INT_TYPE)]
        not_op.dst_loc = ("not_result", INT_TYPE)

        fn.body = [load_val, not_op, LIRReturn()]
        lir.functions["test_not_dst"] = fn

        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)

        # 验证包含 cmp 指令 (48 83)
        found_cmp = False
        for i in range(len(code) - 2):
            if code[i] == 0x48 and code[i + 1] == 0x83:
                found_cmp = True
                break
        self.assertTrue(found_cmp, "Expected cmp instruction for ! unary op")

    def test_unary_bitwise_not_dst_loc(self):
        """按位取反结果写入 dst_loc 指定的目标寄存器"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_bnot_dst", [], INT_TYPE)

        load_val = LIRLoadConst(value=42, const_type="int")

        bnot_op = LIRUnaryOp(op="NOT")
        bnot_op.src_locs = [("const_42", INT_TYPE)]
        bnot_op.dst_loc = ("bnot_result", INT_TYPE)

        fn.body = [load_val, bnot_op, LIRReturn()]
        lir.functions["test_bnot_dst"] = fn

        code = codegen._compile_function(fn)
        self.assertTrue(len(code) > 0)

        # 验证包含 not 指令 (48 F7 /2)
        found_not = False
        for i in range(len(code) - 2):
            if code[i] == 0x48 and code[i + 1] == 0xF7:
                modrm = code[i + 2]
                if (modrm >> 3) & 7 == 2:
                    found_not = True
                    break
        self.assertTrue(found_not, "Expected not instruction (48 F7 /2) for NOT unary op")


class TestVRegNotAllocatedError(unittest.TestCase):
    """虚拟寄存器未分配时应报错而非静默回退"""

    def test_binop_left_vreg_not_allocated_raises(self):
        """LIRBinOp 左操作数虚拟寄存器未分配时应抛出 ValueError"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_err", [], INT_TYPE)

        # 只加载一个常量，但 BinOp 引用了不存在的 vreg
        load_a = LIRLoadConst(value=10, const_type="int")
        add_op = LIRBinOp(op="+")
        add_op.src_locs = [("nonexistent_vreg", INT_TYPE), ("const_10", INT_TYPE)]
        add_op.dst_loc = ("result", INT_TYPE)

        fn.body = [load_a, add_op, LIRReturn()]
        lir.functions["test_err"] = fn

        with self.assertRaises(ValueError) as ctx:
            codegen._compile_function(fn)
        self.assertIn("未分配", str(ctx.exception))
        self.assertIn("nonexistent_vreg", str(ctx.exception))

    def test_binop_right_vreg_not_allocated_raises(self):
        """LIRBinOp 右操作数虚拟寄存器未分配时应抛出 ValueError"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_err", [], INT_TYPE)

        load_a = LIRLoadConst(value=10, const_type="int")
        add_op = LIRBinOp(op="+")
        add_op.src_locs = [("const_10", INT_TYPE), ("missing_vreg", INT_TYPE)]
        add_op.dst_loc = ("result", INT_TYPE)

        fn.body = [load_a, add_op, LIRReturn()]
        lir.functions["test_err"] = fn

        with self.assertRaises(ValueError) as ctx:
            codegen._compile_function(fn)
        self.assertIn("未分配", str(ctx.exception))
        self.assertIn("missing_vreg", str(ctx.exception))

    def test_unary_op_vreg_not_allocated_raises(self):
        """LIRUnaryOp 操作数虚拟寄存器未分配时应抛出 ValueError"""
        codegen = NativeCodeGen()
        lir = LIRModule(name="test")
        fn = LIRFunction("test_err", [], INT_TYPE)

        neg_op = LIRUnaryOp(op="-")
        neg_op.src_locs = [("unknown_vreg", INT_TYPE)]
        neg_op.dst_loc = ("result", INT_TYPE)

        fn.body = [neg_op, LIRReturn()]
        lir.functions["test_err"] = fn

        with self.assertRaises(ValueError) as ctx:
            codegen._compile_function(fn)
        self.assertIn("未分配", str(ctx.exception))
        self.assertIn("unknown_vreg", str(ctx.exception))

    def test_get_vreg_helper_none_raises(self):
        """_get_vreg 辅助函数对 None 值也应报错"""
        codegen = NativeCodeGen()
        vregs = {"v1": None}  # 存在但值为 None（分配失败的情况）
        with self.assertRaises(ValueError) as ctx:
            codegen._get_vreg(vregs, "v1")
        self.assertIn("未分配", str(ctx.exception))
        self.assertIn("v1", str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
