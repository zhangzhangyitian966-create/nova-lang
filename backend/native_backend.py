"""
Nova 自研原生代码生成后端
将 LIR 直接编译为 x86_64 机器码 + ELF 可执行文件

零外部依赖 —— 不需要 gcc、clang、Cranelift、LLVM
"""

import os
import struct
import sys
from typing import Dict, List, Tuple

# 确保项目根目录和 ir 目录在路径上
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ir"))
from backend.x86_64 import (
    CALLEE_SAVED,
    R8,
    R9,
    R10,
    R11,
    R12,
    R13,
    R14,
    R15,
    RAX,
    RBX,
    RCX,
    RDI,
    RDX,
    RSP,
    XMM0,
    XMM1,
    XMM2,
    XMM3,
    XMM4,
    XMM5,
    XMM6,
    XMM7,
    X86_64Emitter,
)
from ir_nodes import (
    INT_TYPE,
    UNIT_TYPE,
    LIRBinOp,
    LIRBranch,
    LIRCall,
    LIRFunction,
    LIRJump,
    LIRLabel,
    LIRLoadConst,
    LIRModule,
    LIRPanic,
    LIRReturn,
    LIRUnaryOp,
)

# ============================================================
# 寄存器分配器（线性扫描算法）
# ============================================================


class LiveInterval:
    """活跃区间，表示一个虚拟寄存器的生命周期"""

    def __init__(self, vreg, start, end):
        self.vreg = vreg
        self.start = start
        self.end = end
        self.reg = None
        self.spill_slot = None


class LinearScanAllocator:
    """线性扫描寄存器分配器"""

    def __init__(self, available_regs):
        self.available = list(available_regs)
        self.spill_counter = 0

    def allocate(self, intervals: List[LiveInterval]) -> Tuple[Dict[str, int], int]:
        """分配寄存器，返回 (vreg -> reg, max_stack_slots)"""
        active = []  # 当前活跃的 intervals
        result = {}
        max_slot = 0

        # 按起始位置排序
        intervals.sort(key=lambda i: i.start)

        for interval in intervals:
            # 过期检查：移除已结束的区间
            active = [a for a in active if a.end > interval.start]

            # 尝试分配寄存器
            used_regs = {a.reg for a in active if a.reg is not None}
            free = [r for r in self.available if r not in used_regs]

            if free:
                interval.reg = free[0]
                result[interval.vreg] = interval.reg
            else:
                # 溢出到栈
                interval.spill_slot = self.spill_counter
                self.spill_counter += 1
                max_slot = max(max_slot, self.spill_counter)
                result[interval.vreg] = interval.spill_slot  # 负数表示 spill

            active.append(interval)
            active.sort(key=lambda a: a.end)

        return result, max_slot


# ============================================================
# 代码生成器
# ============================================================


class NativeCodeGen:
    """Nova 自研 x86_64 代码生成器"""

    def __init__(self):
        self.emitter = X86_64Emitter()
        self.code = bytearray()
        self.data_section = bytearray()
        self.float_constants = []  # [(value_bytes, offset_in_data)]
        self.string_constants = []  # [(string_bytes, offset_in_data)]
        self.symbols = {}  # name -> offset in code
        self.data_symbols = {}  # name -> offset in data
        self.relocations = []  # [(code_offset, symbol, addend)]
        self.link_calls = []  # [(code_offset, func_name)]

    def compile(self, lir_module: LIRModule) -> bytes:
        """编译 LIR Module 为 ELF 二进制"""
        # 1. 收集所有字符串和浮点常量
        self._collect_constants(lir_module)

        # 2. 为每个函数生成机器码
        func_code = {}
        for name, func in lir_module.functions.items():
            func_code[name] = self._compile_function(func)

        # 3. 生成 _start 入口
        start_code = self._generate_start(func_code, lir_module)

        # 4. 组装为 ELF
        return self._generate_elf(func_code, start_code, lir_module)

    def _collect_constants(self, module):
        """收集数据段常量"""
        offset = 0
        for func in module.functions.values():
            for instr in func.body:
                if isinstance(instr, LIRLoadConst):
                    if instr.const_type == "float":
                        value_bytes = struct.pack("<d", float(instr.value))
                        self.float_constants.append((value_bytes, offset))
                        offset += len(value_bytes)
                        # 对齐到 8 字节
                        while offset % 8 != 0:
                            offset += 1
                    elif instr.const_type == "string":
                        value_bytes = instr.value.encode("utf-8") + b"\x00"
                        self.string_constants.append((value_bytes, offset))
                        offset += len(value_bytes)

    def _compile_function(self, func: LIRFunction) -> bytes:
        """编译单个函数为机器码"""
        e = X86_64Emitter()

        # 函数序言：保存 callee-saved，分配栈帧
        for reg in CALLEE_SAVED:
            e.push_reg(reg)

        if func.stack_size > 0:
            # 对齐到 16 字节
            aligned = (func.stack_size + 15) & ~15
            e.sub_rsp_imm(aligned)

        # 编译函数体
        self._compile_body(e, func)

        # 函数尾声：恢复 callee-saved，返回
        if func.stack_size > 0:
            aligned = (func.stack_size + 15) & ~15
            e.add_rsp_imm(aligned)

        for reg in reversed(CALLEE_SAVED):
            e.pop_reg(reg)

        e.ret()

        return bytes(e.code)

    def _compile_body(self, e: X86_64Emitter, func: LIRFunction):
        """编译函数体指令"""
        # 虚拟寄存器 -> 物理寄存器映射
        vregs = {}  # vreg_name -> phys_reg

        # 分配虚拟寄存器
        free_gprs = [RAX, RCX, RDX, RBX, R8, R9, R10, R11, R12, R13, R14, R15]
        free_xmms = [XMM0, XMM1, XMM2, XMM3, XMM4, XMM5, XMM6, XMM7]

        def get_reg(is_float=False):
            if is_float:
                if free_xmms:
                    return free_xmms.pop(0)
            else:
                if free_gprs:
                    return free_gprs.pop(0)
            return None  # 需要溢出处理

        def alloc_vreg(name, is_float=False):
            if name not in vregs:
                vregs[name] = get_reg(is_float)
            return vregs[name]

        for instr in func.body:
            if isinstance(instr, LIRLoadConst):
                if instr.const_type == "int":
                    reg = alloc_vreg(f"const_{instr.value}")
                    if reg is not None:
                        e.mov_reg_imm64(reg, int(instr.value))
                elif instr.const_type == "float":
                    reg = alloc_vreg(f"fconst_{instr.value}", is_float=True)
                    if reg is not None:
                        # 加载浮点常量（通过 rip-relative 寻址）
                        # 实际实现需要数据段引用，此处为占位
                        pass
                elif instr.const_type == "bool":
                    reg = alloc_vreg(f"bconst_{instr.value}")
                    if reg is not None:
                        e.mov_reg_imm64(reg, 1 if instr.value else 0)
                elif instr.const_type == "string":
                    reg = alloc_vreg(f"sconst_{instr.value}")
                    if reg is not None:
                        # lea reg, [rip + string_offset]
                        pass

            elif isinstance(instr, LIRBinOp):
                op = instr.op
                if op in ("+", "-", "*", "/", "%"):
                    # 简化：使用固定寄存器
                    dst = RAX  # 结果在 RAX
                    src = RCX  # 操作数在 RCX
                    if op == "+":
                        e.add_reg_reg(dst, src)
                    elif op == "-":
                        e.sub_reg_reg(dst, src)
                    elif op == "*":
                        e.imul_reg_reg(dst, src)
                    elif op == "/":
                        e.cqo()
                        e.idiv_reg(src)
                    elif op == "%":
                        e.cqo()
                        e.idiv_reg(src)
                        # 余数在 RDX
                        e.mov_reg_reg64(RAX, RDX)
                elif op == "==":
                    e.cmp_reg_reg(RAX, RCX)
                    e.sete(RAX)
                    e.movzx_reg32_reg8(RAX, RAX)
                elif op == "!=":
                    e.cmp_reg_reg(RAX, RCX)
                    e.setne(RAX)
                    e.movzx_reg32_reg8(RAX, RAX)
                elif op == "<":
                    e.cmp_reg_reg(RAX, RCX)
                    e.setl(RAX)
                    e.movzx_reg32_reg8(RAX, RAX)
                elif op == ">":
                    e.cmp_reg_reg(RCX, RAX)
                    e.setl(RAX)
                    e.movzx_reg32_reg8(RAX, RAX)
                elif op == "<=":
                    e.cmp_reg_reg(RAX, RCX)
                    e.setle(RAX)
                    e.movzx_reg32_reg8(RAX, RAX)
                elif op == ">=":
                    e.cmp_reg_reg(RCX, RAX)
                    e.setle(RAX)
                    e.movzx_reg32_reg8(RAX, RAX)

            elif isinstance(instr, LIRUnaryOp):
                if instr.op == "-":
                    e.neg_reg(RAX)
                elif instr.op == "!":
                    e.cmp_reg_imm(RAX, 0)
                    e.sete(RAX)
                    e.movzx_reg32_reg8(RAX, RAX)

            elif isinstance(instr, LIRCall):
                # 设置参数
                for i in range(min(instr.arg_count, 6)):
                    # 将第 i 个参数放到 ARG_REGS[i]
                    pass  # 实际需要从虚拟寄存器加载

                # 调用
                call_offset = e.call_rel32()
                self.link_calls.append((call_offset, instr.func_name))

            elif isinstance(instr, LIRReturn):
                # 返回值已在 RAX
                e.ret()

            elif isinstance(instr, LIRJump):
                # jmp label
                jmp_offset = e.jmp_rel32()
                # 记录标签跳转，后续回填

            elif isinstance(instr, LIRBranch):
                # if (RAX != 0) jmp true; else jmp false
                e.test_reg_reg(RAX, RAX)
                jne_offset = e.jne_rel32()
                jmp_offset = e.jmp_rel32()
                # 记录分支跳转

            elif isinstance(instr, LIRLabel):
                pass  # 标签在回填阶段处理

            elif isinstance(instr, LIRPanic):
                # 调用 abort (exit code 1)
                e.mov_reg_imm64(RDI, 1)
                e.mov_reg_imm64(RAX, 60)  # syscall: exit
                e.syscall()

    def _generate_start(self, func_code: Dict[str, bytes], module: LIRModule):
        """生成 _start 入口函数"""
        e = X86_64Emitter()

        # 设置参数
        # argc 在 [RSP], argv 在 [RSP+8]
        e.mov_reg_mem(RDI, RSP, 8)  # argv[0] = program name

        # 调用 nova_init
        call_init = e.call_rel32()
        self.link_calls.append((call_init, "nova_init"))

        # 调用 main
        if "main" in func_code:
            call_main = e.call_rel32()
            self.link_calls.append((call_main, "main"))

        # 调用 nova_cleanup
        call_cleanup = e.call_rel32()
        self.link_calls.append((call_cleanup, "nova_cleanup"))

        # exit(0)
        e.mov_reg_imm64(RDI, 0)  # exit code
        e.mov_reg_imm64(RAX, 60)  # syscall: exit
        e.syscall()

        return bytes(e.code)

    # ============================================================
    # ELF 文件生成器
    # ============================================================

    def _generate_elf(
        self, func_code: Dict[str, bytes], start_code: bytes, module: LIRModule
    ) -> bytes:
        """生成 Linux ELF 可执行文件"""

        # 1. 构建代码段
        code = bytearray()

        # 记录所有函数位置
        code_offset = 0

        # _start 入口
        code.extend(start_code)
        start_offset = 0
        code_offset = len(code)

        # 各函数
        func_offsets = {}
        for name, fc in func_code.items():
            func_offsets[name] = code_offset
            code.extend(fc)
            code_offset = len(code)

        # 2. 构建数据段
        data = bytearray()
        for value_bytes, _ in self.float_constants:
            data.extend(value_bytes)
            while len(data) % 8 != 0:
                data.append(0)
        for value_bytes, _ in self.string_constants:
            data.extend(value_bytes)

        # 3. ELF 头 (64 bytes)
        ehdr = self._make_elf_header(
            entry=start_offset,
            phoff=64,  # program headers 紧跟 ELF header
            phnum=3,  # LOAD(code) + LOAD(data) + LOAD(rodata)
            shoff=0,  # 无 section headers（简化）
        )

        # 4. Program headers
        page_size = 0x1000
        base_addr = 0x400000

        # LOAD: 代码段 (RWX)
        code_ph = self._make_program_header(
            p_type=1,  # PT_LOAD
            p_offset=0,
            p_vaddr=base_addr,
            p_paddr=base_addr,
            p_filesz=len(code),
            p_memsz=len(code),
            p_flags=5,  # PF_R | PF_X
            p_align=page_size,
        )

        # LOAD: 数据段 (RW)
        data_offset = len(code)
        data_ph = self._make_program_header(
            p_type=1,
            p_offset=data_offset,
            p_vaddr=base_addr
            + ((data_offset + page_size - 1) // page_size) * page_size,
            p_paddr=base_addr
            + ((data_offset + page_size - 1) // page_size) * page_size,
            p_filesz=len(data),
            p_memsz=len(data),
            p_flags=6,  # PF_R | PF_W
            p_align=page_size,
        )

        # 5. 组装 ELF
        elf = bytearray(ehdr)
        elf.extend(code_ph)
        elf.extend(data_ph)
        elf.extend(code)
        elf.extend(data)

        return bytes(elf)

    def _make_elf_header(self, entry, phoff, phnum, shoff=0):
        """生成 ELF64 头"""
        e_ident = bytearray(16)
        e_ident[0:4] = b"\x7fELF"  # magic
        e_ident[4] = 2  # 64-bit
        e_ident[5] = 1  # little-endian
        e_ident[6] = 1  # ELF version
        e_ident[7] = 0  # OS/ABI (ELFOSABI_NONE)
        # rest zero

        header = bytearray(e_ident)
        header.extend(struct.pack("<H", 2))  # e_type: ET_EXEC
        header.extend(struct.pack("<H", 62))  # e_machine: EM_X86_64
        header.extend(struct.pack("<I", 1))  # e_version
        header.extend(struct.pack("<Q", entry))  # e_entry
        header.extend(struct.pack("<Q", phoff))  # e_phoff
        header.extend(struct.pack("<Q", shoff))  # e_shoff
        header.extend(struct.pack("<I", 0))  # e_flags
        header.extend(struct.pack("<H", 64))  # e_ehsize
        header.extend(struct.pack("<H", 56))  # e_phentsize
        header.extend(struct.pack("<H", phnum))  # e_phnum
        header.extend(struct.pack("<H", 0))  # e_shentsize
        header.extend(struct.pack("<H", 0))  # e_shnum
        header.extend(struct.pack("<H", 0))  # e_shstrndx

        return bytes(header)

    def _make_program_header(
        self, p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags, p_align
    ):
        """生成 ELF64 Program Header"""
        ph = bytearray()
        ph.extend(struct.pack("<I", p_type))
        ph.extend(struct.pack("<I", p_flags))
        ph.extend(struct.pack("<Q", p_offset))
        ph.extend(struct.pack("<Q", p_vaddr))
        ph.extend(struct.pack("<Q", p_paddr))
        ph.extend(struct.pack("<Q", p_filesz))
        ph.extend(struct.pack("<Q", p_memsz))
        ph.extend(struct.pack("<Q", p_align))
        return bytes(ph)

    def compile_and_write(self, lir_module: LIRModule, output_path: str):
        """编译并写入 ELF 文件"""
        elf = self.compile(lir_module)
        with open(output_path, "wb") as f:
            f.write(elf)
        os.chmod(output_path, 0o755)
        return output_path


# ============================================================
# 简化的直接编译器（不经过 LIR，直接从源码生成 x86_64）
# ============================================================


class SimpleNativeCompiler:
    """
    简化版原生编译器
    直接将 Nova 源码编译为 x86_64 ELF 可执行文件
    用于快速验证机器码生成是否正确
    """

    def __init__(self):
        self.codegen = NativeCodeGen()

    def compile_source(self, source: str, output_path: str) -> str:
        """将 Nova 源码编译为 x86_64 ELF"""
        # 1. 前端解析（复用现有）
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from parser import Parser

        from lexer import Lexer

        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()

        # 2. 构建简单的 LIR
        lir = self._build_simple_lir(ast)

        # 3. 编译为 ELF
        self.codegen.compile_and_write(lir, output_path)
        return output_path

    def _build_simple_lir(self, ast):
        """从 AST 构建简单的 LIR（仅支持整数运算和函数调用）"""
        lir = LIRModule(name="nova_program")

        # 构建 main 函数
        main_fn = LIRFunction("main", [], UNIT_TYPE)
        main_fn.body = []

        # 构建用户函数
        for decl in ast.declarations:
            if hasattr(decl, "name"):
                fn = LIRFunction(decl.name, [], INT_TYPE)
                fn.body = [LIRLoadConst(), LIRReturn()]
                lir.functions[decl.name] = fn

        # 简化的 _start
        lir.functions["_start"] = LIRFunction("_start", [], UNIT_TYPE)
        lir.functions["_start"].body = [LIRReturn()]

        return lir
