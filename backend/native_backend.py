"""
Nova 自研原生代码生成后端
将 LIR 直接编译为 x86_64 机器码 + ELF 可执行文件

零外部依赖 —— 不需要 gcc、clang、Cranelift、LLVM
"""
import struct
import os
import sys
from typing import Dict, List, Tuple, Optional, Any

from nova.ir.ir_nodes import (
    LIRModule, LIRFunction, LIRGlobal, LIRData,
    LIRInstr, LIRLoadConst, LIRLoadGlobal, LIRStoreGlobal,
    LIRLoadReg, LIRStoreReg, LIRBinOp, LIRUnaryOp,
    LIRCall, LIRCallIndirect, LIRJump, LIRBranch, LIRReturn,
    LIRLabel, LIRIndex, LIRFieldAccess,
    LIRBuildList, LIRBuildTuple, LIRBuildADT, LIRPanic,
    IRType, NovaType,
    INT_TYPE, FLOAT_TYPE, STRING_TYPE, BOOL_TYPE, UNIT_TYPE,
)

from nova.backend.x86_64 import (
    X86_64Emitter, RAX, RCX, RDX, RBX, RSP, RBP, RSI, RDI,
    R8, R9, R10, R11, R12, R13, R14, R15,
    XMM0, XMM1, XMM2, XMM3, XMM4, XMM5, XMM6, XMM7,
    CALLER_SAVED, CALLEE_SAVED, ARG_REGS, RETURN_REG, XMM_ARG_REGS,
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
        self.float_constant_map = {}   # float_value -> data_offset
        self.string_constant_map = {}  # string_value -> data_offset
        self.symbols = {}          # name -> offset in code
        self.data_symbols = {}     # name -> offset in data
        self.rip_relocations = []  # [(func_name, code_offset_in_func, data_offset)]
        self.func_calls = {}       # {func_name: [(call_offset, target_name)]}
        self.link_calls = []       # [(code_offset, func_name)]

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
        self.float_constants = []
        self.string_constants = []
        self.float_constant_map = {}
        self.string_constant_map = {}
        for func in module.functions.values():
            for instr in func.body:
                if isinstance(instr, LIRLoadConst):
                    if instr.const_type == "float":
                        value = float(instr.value)
                        if value not in self.float_constant_map:
                            value_bytes = struct.pack('<d', value)
                            self.float_constants.append((value_bytes, offset))
                            self.float_constant_map[value] = offset
                            offset += len(value_bytes)
                            # 对齐到 8 字节
                            while offset % 8 != 0:
                                offset += 1
                    elif instr.const_type == "string":
                        value = instr.value
                        if value not in self.string_constant_map:
                            value_bytes = value.encode('utf-8') + b'\x00'
                            self.string_constants.append((value_bytes, offset))
                            self.string_constant_map[value] = offset
                            offset += len(value_bytes)

    def _alloc_vreg(self, name, vregs, free_gprs, free_xmms, is_float=False):
        """分配虚拟寄存器到物理寄存器"""
        if name not in vregs:
            if is_float and free_xmms:
                vregs[name] = free_xmms.pop(0)
            elif not is_float and free_gprs:
                vregs[name] = free_gprs.pop(0)
            else:
                vregs[name] = None
        return vregs[name]

    def _compile_const_float(self, e, instr, vregs, free_gprs, free_xmms, func_relocations):
        """编译浮点常量加载：通过 RIP-relative movsd 从数据段加载"""
        reg = self._alloc_vreg(f"fconst_{instr.value}", vregs, free_gprs, free_xmms, is_float=True)
        if reg is not None:
            value = float(instr.value)
            data_offset = self.float_constant_map.get(value)
            if data_offset is not None:
                rip_offset = e.movsd_reg_imm(reg, 0)
                func_relocations.append((rip_offset, data_offset))

    def _compile_const_string(self, e, instr, vregs, free_gprs, free_xmms, func_relocations):
        """编译字符串常量加载：通过 RIP-relative lea 获取地址"""
        reg = self._alloc_vreg(f"sconst_{instr.value}", vregs, free_gprs, free_xmms)
        if reg is not None:
            value = instr.value
            data_offset = self.string_constant_map.get(value)
            if data_offset is not None:
                rip_offset = e.lea_reg_rip(reg, 0)
                func_relocations.append((rip_offset, data_offset))

    def _compile_branch(self, e, instr, vregs, free_gprs, free_xmms,
                        label_positions, pending_branches):
        """编译条件分支：test + jne true_label + jmp false_label"""
        cond_reg = vregs.get(instr.cond_reg, RAX) if instr.cond_reg else RAX
        e.test_reg_reg(cond_reg, cond_reg)
        jne_offset = e.jne_rel32()
        jmp_offset = e.jmp_rel32()
        pending_branches.append((jne_offset, instr.true_label, jmp_offset, instr.false_label))

    def _compile_call(self, e, instr, vregs, free_gprs, free_xmms, func_name):
        """编译函数调用，按 System V AMD64 ABI 传递参数"""
        int_idx = 0
        float_idx = 0
        stack_gprs = []

        for loc, typ in instr.src_locs:
            src_reg = vregs.get(loc)
            if typ == FLOAT_TYPE:
                if float_idx < 8 and src_reg is not None:
                    e.movsd_reg_reg(XMM_ARG_REGS[float_idx], src_reg)
                float_idx += 1
            else:
                if int_idx < 6 and src_reg is not None:
                    e.mov_reg_reg64(ARG_REGS[int_idx], src_reg)
                int_idx += 1
                if int_idx > 6:
                    stack_gprs.append(src_reg)

        # 将超出寄存器限制的整型参数压栈（按反序）
        for src_reg in reversed(stack_gprs):
            if src_reg is not None:
                e.push_reg(src_reg)

        call_offset = e.call_rel32()
        if func_name not in self.func_calls:
            self.func_calls[func_name] = []
        self.func_calls[func_name].append((call_offset, instr.func_name))

        # 恢复栈指针
        if stack_gprs:
            e.add_rsp_imm(len(stack_gprs) * 8)

    def _compile_function(self, func: LIRFunction) -> bytes:
        """编译单个函数为机器码"""
        e = X86_64Emitter()
        label_positions = {}
        pending_jumps = []
        pending_branches = []
        func_relocations = []

        # 函数序言：保存 callee-saved，分配栈帧
        for reg in CALLEE_SAVED:
            e.push_reg(reg)

        if func.stack_size > 0:
            aligned = (func.stack_size + 15) & ~15
            e.sub_rsp_imm(aligned)

        # 编译函数体
        self._compile_body(e, func, label_positions, pending_jumps, pending_branches, func_relocations)

        # 函数尾声：恢复 callee-saved，返回
        if func.stack_size > 0:
            aligned = (func.stack_size + 15) & ~15
            e.add_rsp_imm(aligned)

        for reg in reversed(CALLEE_SAVED):
            e.pop_reg(reg)

        e.ret()

        # 回填标签跳转
        code = bytearray(e.code)
        for offset_pos, target_label in pending_jumps:
            target = label_positions.get(target_label, 0)
            rel = target - (offset_pos + 4)
            struct.pack_into('<i', code, offset_pos, rel)

        for jcc_offset, true_label, jmp_offset, false_label in pending_branches:
            true_target = label_positions.get(true_label, 0)
            false_target = label_positions.get(false_label, 0)
            rel_true = true_target - (jcc_offset + 4)
            rel_false = false_target - (jmp_offset + 4)
            struct.pack_into('<i', code, jcc_offset, rel_true)
            struct.pack_into('<i', code, jmp_offset, rel_false)

        # 记录 RIP-relative 重定位
        for offset_pos, data_offset in func_relocations:
            self.rip_relocations.append((func.name, offset_pos, data_offset))

        return bytes(code)

    def _compile_body(self, e: X86_64Emitter, func: LIRFunction,
                      label_positions: dict, pending_jumps: list,
                      pending_branches: list, func_relocations: list):
        """编译函数体指令"""
        vregs = {}
        free_gprs = [RAX, RCX, RDX, RBX, R8, R9, R10, R11, R12, R13, R14, R15]
        free_xmms = [XMM0, XMM1, XMM2, XMM3, XMM4, XMM5, XMM6, XMM7]

        for instr in func.body:
            if isinstance(instr, LIRLoadConst):
                if instr.const_type == "int":
                    reg = self._alloc_vreg(f"const_{instr.value}", vregs, free_gprs, free_xmms)
                    if reg is not None:
                        e.mov_reg_imm64(reg, int(instr.value))
                elif instr.const_type == "float":
                    self._compile_const_float(e, instr, vregs, free_gprs, free_xmms, func_relocations)
                elif instr.const_type == "bool":
                    reg = self._alloc_vreg(f"bconst_{instr.value}", vregs, free_gprs, free_xmms)
                    if reg is not None:
                        e.mov_reg_imm64(reg, 1 if instr.value else 0)
                elif instr.const_type == "string":
                    self._compile_const_string(e, instr, vregs, free_gprs, free_xmms, func_relocations)

            elif isinstance(instr, LIRBinOp):
                op = instr.op
                if op in ("+", "-", "*", "/", "%"):
                    dst = RAX
                    src = RCX
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
                self._compile_call(e, instr, vregs, free_gprs, free_xmms, func.name)

            elif isinstance(instr, LIRReturn):
                e.ret()

            elif isinstance(instr, LIRJump):
                jmp_offset = e.jmp_rel32()
                pending_jumps.append((jmp_offset, instr.target))

            elif isinstance(instr, LIRBranch):
                self._compile_branch(e, instr, vregs, free_gprs, free_xmms,
                                     label_positions, pending_branches)

            elif isinstance(instr, LIRLabel):
                label_positions[instr.name] = e.current_offset()

            elif isinstance(instr, LIRPanic):
                e.mov_reg_imm64(RDI, 1)
                e.mov_reg_imm64(RAX, 60)
                e.syscall()

    def _generate_start(self, func_code: Dict[str, bytes], module: LIRModule):
        """生成 _start 入口函数"""
        e = X86_64Emitter()
        self.func_calls["_start"] = []

        # 设置参数
        e.mov_reg_mem(RDI, RSP, 8)

        # 调用 nova_init
        call_init = e.call_rel32()
        self.func_calls["_start"].append((call_init, "nova_init"))

        # 调用 main
        if "main" in func_code:
            call_main = e.call_rel32()
            self.func_calls["_start"].append((call_main, "main"))

        # 调用 nova_cleanup
        call_cleanup = e.call_rel32()
        self.func_calls["_start"].append((call_cleanup, "nova_cleanup"))

        # exit(0)
        e.mov_reg_imm64(RDI, 0)
        e.mov_reg_imm64(RAX, 60)
        e.syscall()

        return bytes(e.code)

    # ============================================================
    # ELF 文件生成器
    # ============================================================

    def _patch_code(self, code: bytearray, func_offsets: Dict[str, int]):
        """回填函数调用和 RIP-relative 数据引用"""
        page_size = 0x1000
        data_dist = ((len(code) + page_size - 1) // page_size) * page_size

        # Patch 函数调用
        for func_name, calls in self.func_calls.items():
            func_base = 0 if func_name == "_start" else func_offsets.get(func_name, 0)
            for call_offset, target_name in calls:
                target_base = func_offsets.get(target_name, 0)
                abs_call_offset = func_base + call_offset
                rel = target_base - (abs_call_offset + 4)
                struct.pack_into('<i', code, abs_call_offset, rel)

        # Patch RIP-relative 数据引用
        for func_name, offset_in_func, data_offset in self.rip_relocations:
            func_base = 0 if func_name == "_start" else func_offsets.get(func_name, 0)
            abs_offset = func_base + offset_in_func
            rel = data_dist + data_offset - (abs_offset + 4)
            struct.pack_into('<i', code, abs_offset, rel)

    def _generate_elf(self, func_code: Dict[str, bytes], start_code: bytes,
                     module: LIRModule) -> bytes:
        """生成 Linux ELF 可执行文件"""

        # 1. 构建代码段
        code = bytearray()

        code_offset = 0
        code.extend(start_code)
        start_offset = 0
        code_offset = len(code)

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

        # 回填跳转和数据引用
        self._patch_code(code, func_offsets)

        # 3. ELF 头
        ehdr = self._make_elf_header(
            entry=start_offset,
            phoff=64,
            phnum=2,
            shoff=0,
        )

        # 4. Program headers
        page_size = 0x1000
        base_addr = 0x400000

        code_ph = self._make_program_header(
            p_type=1,
            p_offset=0,
            p_vaddr=base_addr,
            p_paddr=base_addr,
            p_filesz=len(code),
            p_memsz=len(code),
            p_flags=5,
            p_align=page_size,
        )

        data_offset = len(code)
        data_ph = self._make_program_header(
            p_type=1,
            p_offset=data_offset,
            p_vaddr=base_addr + ((data_offset + page_size - 1) // page_size) * page_size,
            p_paddr=base_addr + ((data_offset + page_size - 1) // page_size) * page_size,
            p_filesz=len(data),
            p_memsz=len(data),
            p_flags=6,
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
        e_ident[0:4] = b'\x7fELF'       # magic
        e_ident[4] = 2                     # 64-bit
        e_ident[5] = 1                     # little-endian
        e_ident[6] = 1                     # ELF version
        e_ident[7] = 0                     # OS/ABI (ELFOSABI_NONE)
        # rest zero

        header = bytearray(e_ident)
        header.extend(struct.pack('<H', 2))     # e_type: ET_EXEC
        header.extend(struct.pack('<H', 62))    # e_machine: EM_X86_64
        header.extend(struct.pack('<I', 1))     # e_version
        header.extend(struct.pack('<Q', entry)) # e_entry
        header.extend(struct.pack('<Q', phoff))  # e_phoff
        header.extend(struct.pack('<Q', shoff))  # e_shoff
        header.extend(struct.pack('<I', 0))     # e_flags
        header.extend(struct.pack('<H', 64))    # e_ehsize
        header.extend(struct.pack('<H', 56))    # e_phentsize
        header.extend(struct.pack('<H', phnum)) # e_phnum
        header.extend(struct.pack('<H', 0))     # e_shentsize
        header.extend(struct.pack('<H', 0))     # e_shnum
        header.extend(struct.pack('<H', 0))     # e_shstrndx

        return bytes(header)

    def _make_program_header(self, p_type, p_offset, p_vaddr, p_paddr,
                              p_filesz, p_memsz, p_flags, p_align):
        """生成 ELF64 Program Header"""
        ph = bytearray()
        ph.extend(struct.pack('<I', p_type))
        ph.extend(struct.pack('<I', p_flags))
        ph.extend(struct.pack('<Q', p_offset))
        ph.extend(struct.pack('<Q', p_vaddr))
        ph.extend(struct.pack('<Q', p_paddr))
        ph.extend(struct.pack('<Q', p_filesz))
        ph.extend(struct.pack('<Q', p_memsz))
        ph.extend(struct.pack('<Q', p_align))
        return bytes(ph)

    def compile_and_write(self, lir_module: LIRModule, output_path: str):
        """编译并写入 ELF 文件"""
        elf = self.compile(lir_module)
        with open(output_path, 'wb') as f:
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
        from nova.lexer import Lexer
        from nova.parser import Parser

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
            if hasattr(decl, 'name'):
                fn = LIRFunction(decl.name, [], INT_TYPE)
                fn.body = [LIRLoadConst(), LIRReturn()]
                lir.functions[decl.name] = fn

        # 简化的 _start
        lir.functions["_start"] = LIRFunction("_start", [], UNIT_TYPE)
        lir.functions["_start"].body = [
            LIRReturn()
        ]

        return lir
