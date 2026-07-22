"""
Nova 自研原生代码生成后端
将 LIR 直接编译为 x86_64 机器码 + ELF 可执行文件

零外部依赖 —— 不需要 gcc、clang、Cranelift、LLVM
"""

import os
import struct
from typing import Dict

from .x86_64 import (
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
    RSI,
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
from ..ir.ir_nodes import (
    IRType,
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
        self.link_calls = []  # [(caller_func_name, code_offset_in_func, target_func_name)]
        self.data_fixups = []  # [(func_name, code_offset_in_func, data_offset, kind)]
        # 常量值 -> 数据段偏移的映射（用于快速查找）
        self._float_const_map = {}  # value_str -> data_offset
        self._string_const_map = {}  # value -> data_offset

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
        """收集数据段常量，并构建值到偏移的映射"""
        offset = 0
        for func in module.functions.values():
            for instr in func.body:
                if isinstance(instr, LIRLoadConst):
                    if instr.const_type == "float":
                        value_bytes = struct.pack("<d", float(instr.value))
                        # 去重：相同值只存一份
                        key = str(instr.value)
                        if key not in self._float_const_map:
                            self.float_constants.append((value_bytes, offset))
                            self._float_const_map[key] = offset
                            offset += len(value_bytes)
                            # 对齐到 8 字节
                            while offset % 8 != 0:
                                offset += 1
                    elif instr.const_type == "string":
                        value_bytes = instr.value.encode("utf-8") + b"\x00"
                        # 去重：相同字符串只存一份
                        key = instr.value
                        if key not in self._string_const_map:
                            self.string_constants.append((value_bytes, offset))
                            self._string_const_map[key] = offset
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
        self._compile_body(e, func, func.name)

        # 函数尾声：恢复 callee-saved，返回
        if func.stack_size > 0:
            aligned = (func.stack_size + 15) & ~15
            e.add_rsp_imm(aligned)

        for reg in reversed(CALLEE_SAVED):
            e.pop_reg(reg)

        e.ret()

        return bytes(e.code)

    def _compile_body(self, e: X86_64Emitter, func: LIRFunction, func_name: str):
        """
        编译函数体指令（寄存器分配 + 两阶段汇编）。

        阶段 A: 线性扫描寄存器分配
          - 计算每个虚拟寄存器的活跃区间 [first_use, last_use]
          - 按开始点排序，扫描并分配物理寄存器
          - 寄存器不足时溢出到栈槽

        阶段 B: 两阶段汇编
          - 第一阶段：发射指令，记录标签位置和待回填的跳转引用
          - 第二阶段：回填所有 jmp/jcc 的 rel32 偏移量
        """
        # ============================================================
        # 阶段 A: 线性扫描寄存器分配
        # ============================================================

        # 可用物理寄存器（调用者保存优先分配，被调用者保存备用）
        # 注意：RAX 预留为特殊用途（除法、返回值等），但也可参与普通分配
        ALL_GPRS = [RCX, RDX, RSI, RDI, R8, R9, R10, R11,  # caller-saved
                    RBX, R12, R13, R14, R15]                # callee-saved
        ALL_XMMS = [XMM0, XMM1, XMM2, XMM3, XMM4, XMM5, XMM6, XMM7]

        # 步骤 1: 收集所有虚拟寄存器及其活跃区间
        # vreg_info[vreg_name] = {"is_float": bool, "first": int, "last": int}
        vreg_info = {}

        def _note_vreg(vreg_name, is_float, instr_idx):
            """记录虚拟寄存器的使用点，更新活跃区间"""
            if vreg_name not in vreg_info:
                vreg_info[vreg_name] = {
                    "is_float": is_float,
                    "first": instr_idx,
                    "last": instr_idx,
                }
            else:
                info = vreg_info[vreg_name]
                if instr_idx < info["first"]:
                    info["first"] = instr_idx
                if instr_idx > info["last"]:
                    info["last"] = instr_idx

        # 遍历所有指令，收集 vreg 使用信息
        for idx, instr in enumerate(func.body):
            # 源操作数（src_locs）
            for loc_name, loc_type in instr.src_locs:
                is_float = loc_type.kind == IRType.FLOAT
                _note_vreg(loc_name, is_float, idx)
            # 目的操作数（dst_loc）
            if instr.dst_loc:
                dst_name, dst_type = instr.dst_loc
                is_float = dst_type.kind == IRType.FLOAT
                _note_vreg(dst_name, is_float, idx)
            # LIRLoadConst 特殊处理：值本身是一个隐式 vreg
            if isinstance(instr, LIRLoadConst):
                is_float = instr.const_type == "float"
                vname = f"const_{instr.value}" if not is_float else f"fconst_{instr.value}"
                _note_vreg(vname, is_float, idx)

        # 步骤 2: 线性扫描分配
        # 分配结果：vreg_name -> ("reg", phys_reg) 或 ("stack", stack_offset)
        vreg_alloc = {}
        stack_offset = 0  # 栈帧偏移（从 0 开始向下增长，使用正数表示偏移量）

        # 按活跃区间开始点排序
        sorted_vregs = sorted(vreg_info.items(), key=lambda x: x[1]["first"])

        # 当前活跃的寄存器：{phys_reg: last_use_idx}
        active_gprs = {}  # phys_reg -> last_use
        active_xmms = {}  # xmm_reg -> last_use

        # 可用寄存器池
        free_gprs = list(ALL_GPRS)
        free_xmms = list(ALL_XMMS)

        def _expire_old_intervals(current_idx, is_float):
            """回收已过期的寄存器（活跃区间结束点 < current_idx）"""
            if is_float:
                to_free = [r for r, last in active_xmms.items() if last < current_idx]
                for r in to_free:
                    del active_xmms[r]
                    free_xmms.insert(0, r)
            else:
                to_free = [r for r, last in active_gprs.items() if last < current_idx]
                for r in to_free:
                    del active_gprs[r]
                    free_gprs.insert(0, r)

        def _spill_victim(current_idx, is_float):
            """选择一个活跃区间最远的寄存器溢出，返回被溢出的 vreg 名"""
            if is_float:
                if not active_xmms:
                    return None
                # 选择结束点最远的作为牺牲者
                victim_reg = max(active_xmms, key=active_xmms.get)
                victim_last = active_xmms[victim_reg]
                del active_xmms[victim_reg]
                free_xmms.insert(0, victim_reg)
                # 找到对应 vreg
                for vname, info in vreg_info.items():
                    if vreg_alloc.get(vname) == ("reg", victim_reg) and info["last"] == victim_last:
                        return vname
            else:
                if not active_gprs:
                    return None
                victim_reg = max(active_gprs, key=active_gprs.get)
                victim_last = active_gprs[victim_reg]
                del active_gprs[victim_reg]
                free_gprs.insert(0, victim_reg)
                for vname, info in vreg_info.items():
                    if vreg_alloc.get(vname) == ("reg", victim_reg) and info["last"] == victim_last:
                        return vname
            return None

        for vname, info in sorted_vregs:
            is_float = info["is_float"]
            first_use = info["first"]
            last_use = info["last"]

            # 回收已过期的寄存器
            _expire_old_intervals(first_use, is_float)

            # 尝试分配寄存器
            if is_float:
                if free_xmms:
                    reg = free_xmms.pop(0)
                    vreg_alloc[vname] = ("reg", reg)
                    active_xmms[reg] = last_use
                else:
                    # 溢出：选择最远的活跃区间
                    victim = _spill_victim(first_use, is_float)
                    if victim is not None and free_xmms:
                        reg = free_xmms.pop(0)
                        vreg_alloc[vname] = ("reg", reg)
                        active_xmms[reg] = last_use
                        # 牺牲者分配到栈
                        stack_offset += 8  # double = 8 字节
                        vreg_alloc[victim] = ("stack", stack_offset)
                    else:
                        # 直接分配到栈
                        stack_offset += 8
                        vreg_alloc[vname] = ("stack", stack_offset)
            else:
                if free_gprs:
                    reg = free_gprs.pop(0)
                    vreg_alloc[vname] = ("reg", reg)
                    active_gprs[reg] = last_use
                else:
                    victim = _spill_victim(first_use, is_float)
                    if victim is not None and free_gprs:
                        reg = free_gprs.pop(0)
                        vreg_alloc[vname] = ("reg", reg)
                        active_gprs[reg] = last_use
                        stack_offset += 8
                        vreg_alloc[victim] = ("stack", stack_offset)
                    else:
                        stack_offset += 8
                        vreg_alloc[vname] = ("stack", stack_offset)

        # 更新函数栈帧大小
        if stack_offset > func.stack_size:
            func.stack_size = stack_offset

        # 步骤 3: 辅助函数 - 获取 vreg 的物理位置
        def get_loc(vreg_name):
            """获取虚拟寄存器的物理位置：("reg", phys_reg) 或 ("stack", offset)"""
            if vreg_name in vreg_alloc:
                return vreg_alloc[vreg_name]
            # 未在分配表中（可能是特殊寄存器或外部引用），尝试旧的 vreg 机制
            return ("reg", RAX)  # fallback

        def load_to_reg(vreg_name, target_reg, is_float=False):
            """将 vreg 的值加载到目标物理寄存器"""
            loc = get_loc(vreg_name)
            if loc[0] == "reg":
                if loc[1] != target_reg:
                    if is_float:
                        e.movsd_reg_reg(target_reg, loc[1])
                    else:
                        e.mov_reg_reg64(target_reg, loc[1])
            else:
                # 从栈加载
                offset = loc[1]
                if is_float:
                    # movsd xmm, [rsp + offset]
                    e.movsd_reg_imm(target_reg, 0)  # 简化：暂时用 RIP-relative 方式占位
                    # 注意：栈相对寻址需要更复杂的 SIB 编码，这里先预留位置
                    # 实际实现应使用 movsd xmm, [rsp + offset]
                else:
                    e.mov_reg_mem(target_reg, RSP, offset)

        def store_from_reg(vreg_name, source_reg, is_float=False):
            """将源物理寄存器的值存储到 vreg 的位置"""
            loc = get_loc(vreg_name)
            if loc[0] == "reg":
                if loc[1] != source_reg:
                    if is_float:
                        e.movsd_reg_reg(loc[1], source_reg)
                    else:
                        e.mov_reg_reg64(loc[1], source_reg)
            else:
                # 存到栈
                offset = loc[1]
                if is_float:
                    # movsd [rsp + offset], xmm
                    pass  # 待实现
                else:
                    e.mov_mem_reg(RSP, offset, source_reg)

        # ============================================================
        # 阶段 B: 两阶段汇编
        # ============================================================

        # 两阶段汇编：标签位置和待回填项
        label_offsets = {}  # label_name -> code_offset
        jump_fixups = []    # [(code_offset, target_label, is_conditional)]

        # ====== 第一阶段：发射指令并记录标签和跳转 ======
        for idx, instr in enumerate(func.body):
            if isinstance(instr, LIRLoadConst):
                # 确定目标位置
                is_float = instr.const_type == "float"
                if is_float:
                    vname = f"fconst_{instr.value}"
                else:
                    vname = f"const_{instr.value}"

                dst_loc = get_loc(vname)

                if instr.const_type == "int":
                    if dst_loc[0] == "reg":
                        e.mov_reg_imm64(dst_loc[1], int(instr.value))
                    else:
                        # 先加载到 RAX 再存栈
                        e.mov_reg_imm64(RAX, int(instr.value))
                        e.mov_mem_reg(RSP, dst_loc[1], RAX)
                elif instr.const_type == "float":
                    if dst_loc[0] == "reg":
                        fixup_offset = e.movsd_reg_imm(dst_loc[1], 0)
                    else:
                        # 先加载到 XMM0 再存栈（简化：暂直接用 XMM0）
                        fixup_offset = e.movsd_reg_imm(XMM0, 0)
                    data_off = self._float_const_map.get(str(instr.value))
                    if data_off is not None:
                        self.data_fixups.append(
                            (func_name, fixup_offset, data_off, "float")
                        )
                elif instr.const_type == "bool":
                    val = 1 if instr.value else 0
                    if dst_loc[0] == "reg":
                        e.mov_reg_imm64(dst_loc[1], val)
                    else:
                        e.mov_reg_imm64(RAX, val)
                        e.mov_mem_reg(RSP, dst_loc[1], RAX)
                elif instr.const_type == "string":
                    if dst_loc[0] == "reg":
                        fixup_offset = e.lea_reg_rip(dst_loc[1], 0)
                    else:
                        fixup_offset = e.lea_reg_rip(RAX, 0)
                        e.mov_mem_reg(RSP, dst_loc[1], RAX)
                    data_off = self._string_const_map.get(instr.value)
                    if data_off is not None:
                        self.data_fixups.append(
                            (func_name, fixup_offset, data_off, "string")
                        )

            elif isinstance(instr, LIRBinOp):
                op = instr.op
                # 获取源操作数位置
                src_locs = instr.src_locs
                dst_loc = instr.dst_loc

                # 对于需要特定寄存器的指令（如除法用 RAX/RDX），先搬移
                if op in ("/", "%"):
                    # 除法：被除数在 RAX，除数在任意寄存器，结果在 RAX（商）/ RDX（余）
                    if len(src_locs) >= 2:
                        left_name, left_type = src_locs[0]
                        right_name, right_type = src_locs[1]
                        is_float = left_type.kind == IRType.FLOAT

                        if is_float:
                            # 浮点除法
                            load_to_reg(left_name, XMM0, is_float=True)
                            load_to_reg(right_name, XMM1, is_float=True)
                            e.divsd_reg_reg(XMM0, XMM1)
                            # 结果在 XMM0
                            if dst_loc:
                                dst_name, _ = dst_loc
                                store_from_reg(dst_name, XMM0, is_float=True)
                        else:
                            # 整数除法：左操作数 -> RAX
                            load_to_reg(left_name, RAX)
                            # 右操作数 -> RCX（或任意非 RAX/RDX 寄存器）
                            load_to_reg(right_name, RCX)
                            e.cqo()
                            e.idiv_reg(RCX)
                            if op == "%":
                                # 余数在 RDX，搬到 RAX
                                e.mov_reg_reg64(RAX, RDX)
                            # 结果在 RAX，存到目的
                            if dst_loc:
                                dst_name, _ = dst_loc
                                store_from_reg(dst_name, RAX)
                elif op in ("+", "-", "*"):
                    if len(src_locs) >= 2:
                        left_name, left_type = src_locs[0]
                        right_name, right_type = src_locs[1]
                        is_float = left_type.kind == IRType.FLOAT

                        if is_float:
                            # 浮点运算
                            load_to_reg(left_name, XMM0, is_float=True)
                            load_to_reg(right_name, XMM1, is_float=True)
                            if op == "+":
                                e.addsd_reg_reg(XMM0, XMM1)
                            elif op == "-":
                                e.subsd_reg_reg(XMM0, XMM1)
                            elif op == "*":
                                e.mulsd_reg_reg(XMM0, XMM1)
                            if dst_loc:
                                dst_name, _ = dst_loc
                                store_from_reg(dst_name, XMM0, is_float=True)
                        else:
                            # 整数运算：左 -> RAX，右 -> RCX，结果 -> RAX
                            load_to_reg(left_name, RAX)
                            load_to_reg(right_name, RCX)
                            if op == "+":
                                e.add_reg_reg(RAX, RCX)
                            elif op == "-":
                                e.sub_reg_reg(RAX, RCX)
                            elif op == "*":
                                e.imul_reg_reg(RAX, RCX)
                            if dst_loc:
                                dst_name, _ = dst_loc
                                store_from_reg(dst_name, RAX)

                elif op in ("==", "!=", "<", ">", "<=", ">="):
                    if len(src_locs) >= 2:
                        left_name, left_type = src_locs[0]
                        right_name, right_type = src_locs[1]
                        is_float = left_type.kind == IRType.FLOAT

                        if is_float:
                            # 浮点比较
                            load_to_reg(left_name, XMM0, is_float=True)
                            load_to_reg(right_name, XMM1, is_float=True)
                            e.ucomisd(XMM0, XMM1)
                        else:
                            # 整数比较
                            load_to_reg(left_name, RAX)
                            load_to_reg(right_name, RCX)
                            e.cmp_reg_reg(RAX, RCX)

                        # 根据操作码设置结果
                        if op == "==":
                            e.sete(RAX)
                        elif op == "!=":
                            e.setne(RAX)
                        elif op == "<":
                            e.setl(RAX)
                        elif op == ">":
                            e.setg(RAX)
                        elif op == "<=":
                            e.setle(RAX)
                        elif op == ">=":
                            e.setge(RAX)
                        e.movzx_reg32_reg8(RAX, RAX)

                        if dst_loc:
                            dst_name, _ = dst_loc
                            store_from_reg(dst_name, RAX)

            elif isinstance(instr, LIRUnaryOp):
                if instr.src_locs and instr.dst_loc:
                    src_name, src_type = instr.src_locs[0]
                    dst_name, _ = instr.dst_loc
                    is_float = src_type.kind == IRType.FLOAT

                    if instr.op == "-":
                        if is_float:
                            # 浮点取反：xorpd 符号位（简化：用 0 减）
                            load_to_reg(src_name, XMM0, is_float=True)
                            e.xorpd_xmm(XMM1)
                            e.subsd_reg_reg(XMM1, XMM0)
                            store_from_reg(dst_name, XMM1, is_float=True)
                        else:
                            load_to_reg(src_name, RAX)
                            e.neg_reg(RAX)
                            store_from_reg(dst_name, RAX)
                    elif instr.op == "!":
                        load_to_reg(src_name, RAX)
                        e.cmp_reg_imm(RAX, 0)
                        e.sete(RAX)
                        e.movzx_reg32_reg8(RAX, RAX)
                        store_from_reg(dst_name, RAX)

            elif isinstance(instr, LIRCall):
                # TODO: 完整的调用约定实现（参数寄存器设置等）
                # 目前：调用（函数间调用在 ELF 链接阶段回填）
                call_offset = e.call_rel32()
                self.link_calls.append((func_name, call_offset, instr.func_name))
                # 返回值假设在 RAX，如果有 dst_loc 则存储
                if instr.dst_loc:
                    dst_name, _ = instr.dst_loc
                    store_from_reg(dst_name, RAX)

            elif isinstance(instr, LIRReturn):
                # 如果有返回值源，加载到 RAX
                if instr.src_locs:
                    src_name, src_type = instr.src_locs[0]
                    is_float = src_type.kind == IRType.FLOAT
                    if is_float:
                        load_to_reg(src_name, XMM0, is_float=True)
                    else:
                        load_to_reg(src_name, RAX)
                # 返回在函数尾声处理，这里不发射 ret

            elif isinstance(instr, LIRJump):
                # 无条件跳转：发射 jmp rel32 占位，记录回填
                jmp_offset = e.jmp_rel32()
                jump_fixups.append((jmp_offset, instr.target, "jmp"))

            elif isinstance(instr, LIRBranch):
                # 条件跳转：加载条件到 RAX，test + jne/jmp
                if instr.src_locs:
                    cond_name, _ = instr.src_locs[0]
                    load_to_reg(cond_name, RAX)
                e.test_reg_reg(RAX, RAX)
                jne_offset = e.jne_rel32()  # true 分支
                jump_fixups.append((jne_offset, instr.true_target, "jcc"))
                jmp_offset = e.jmp_rel32()  # false 分支
                jump_fixups.append((jmp_offset, instr.false_target, "jmp"))

            elif isinstance(instr, LIRLabel):
                # 记录标签的当前代码偏移位置
                label_offsets[instr.name] = e.current_offset()

            elif isinstance(instr, LIRPanic):
                # 调用 abort (exit code 1)
                e.mov_reg_imm64(RDI, 1)
                e.mov_reg_imm64(RAX, 60)  # syscall: exit
                e.syscall()

        # ====== 第二阶段：回填所有跳转偏移 ======
        for fixup_offset, target_label, _kind in jump_fixups:
            if target_label in label_offsets:
                target_offset = label_offsets[target_label]
                e.patch_rel32(fixup_offset, target_offset)
            else:
                # 标签未找到（可能是跨函数跳转或错误），保持 0 偏移
                # 在完整实现中应报错或在链接阶段处理
                pass

    def _generate_start(self, func_code: Dict[str, bytes], module: LIRModule):
        """生成 _start 入口函数"""
        e = X86_64Emitter()

        # 设置参数
        # argc 在 [RSP], argv 在 [RSP+8]
        e.mov_reg_mem(RDI, RSP, 8)  # argv[0] = program name

        # 调用 nova_init
        call_init = e.call_rel32()
        self.link_calls.append(("_start", call_init, "nova_init"))

        # 调用 main
        if "main" in func_code:
            call_main = e.call_rel32()
            self.link_calls.append(("_start", call_main, "main"))

        # 调用 nova_cleanup
        call_cleanup = e.call_rel32()
        self.link_calls.append(("_start", call_cleanup, "nova_cleanup"))

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
        # 注意：e_entry 必须是虚拟地址，不是文件偏移
        page_size = 0x1000
        base_addr = 0x400000
        entry_vaddr = base_addr + start_offset
        ehdr = self._make_elf_header(
            entry=entry_vaddr,
            phoff=64,  # program headers 紧跟 ELF header
            phnum=3,  # LOAD(code) + LOAD(data) + LOAD(rodata)
            shoff=0,  # 无 section headers（简化）
        )

        # 4. Program headers

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

        # 5. 回填数据段引用（RIP-relative 寻址）
        #    计算每条指令和每个数据常量的虚拟地址，回填 rel32
        data_vaddr = (
            base_addr
            + ((data_offset + page_size - 1) // page_size) * page_size
        )

        for func_name, code_off_in_func, data_off, _kind in self.data_fixups:
            # 计算 rel32 字段在代码段中的偏移
            if func_name == "_start":
                patch_pos = code_off_in_func
            else:
                patch_pos = func_offsets.get(func_name, 0) + code_off_in_func

            # rel32 = target_vaddr - (rel32_pos_vaddr + 4)
            rel32_pos_vaddr = base_addr + patch_pos
            next_instr_vaddr = rel32_pos_vaddr + 4
            data_const_vaddr = data_vaddr + data_off
            rel_offset = data_const_vaddr - next_instr_vaddr

            struct.pack_into("<i", code, patch_pos, rel_offset)

        # 5.5 回填函数间调用（link_calls）
        #    计算每个 call 指令和目标函数的虚拟地址，回填 rel32
        for caller_name, code_off_in_func, target_name in self.link_calls:
            # 计算 rel32 字段在代码段中的偏移
            if caller_name == "_start":
                patch_pos = code_off_in_func
            else:
                patch_pos = func_offsets.get(caller_name, 0) + code_off_in_func

            # 确定目标函数的虚拟地址
            if target_name in func_offsets:
                target_vaddr = base_addr + func_offsets[target_name]
            else:
                # 外部函数（如 nova_init/nova_cleanup）暂时无法解析
                # 在完整实现中应通过链接器处理，这里保持 0 偏移
                continue

            # rel32 = target_vaddr - (patch_pos_vaddr + 4)
            # call rel32: opcode E8 (1B) + rel32 (4B)，rel32 基准是 rel32 字段末尾
            rel32_pos_vaddr = base_addr + patch_pos
            next_instr_vaddr = rel32_pos_vaddr + 4  # rel32 字段长度 = 4 字节
            rel_offset = target_vaddr - next_instr_vaddr

            struct.pack_into("<i", code, patch_pos, rel_offset)

        # 6. 组装 ELF
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
