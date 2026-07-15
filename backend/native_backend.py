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
    """Nova 自研 x86_64 代码生成器

    目前支持的操作：
    - 常量加载：整数、浮点、布尔、字符串
    - 基本算术：+ - * / %
    - 比较运算：== != < > <= >=
    - 一元运算：- !
    - 函数调用（直接调用，System V AMD64 ABI）
    - 控制流：跳转、条件分支、标签、返回
    - 函数序言/尾声（callee-saved 寄存器保存/恢复）
    - ELF 可执行文件生成

    尚未支持的操作将抛出 NotImplementedError。
    """

    # ADT 在内存中的布局:
    #   [0]:    tag (int64, variant discriminator)
    #   [8]:    field_0
    #   [8+N*8]: field_{N-1}
    # 总大小 = 8 + field_count * 8 (8 字节对齐)
    ADT_TAG_SIZE = 8
    ADT_FIELD_SIZE = 8

    # List 在内存中的布局:
    #   [0]: count (int64)
    #   [8]: elem_0 pointer
    #   [16]: elem_1 pointer
    #   ...
    # 总大小 = 8 + count * 8
    LIST_HEADER_SIZE = 8
    LIST_ELEM_SIZE = 8

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
        self.closure_relocations = []  # [(func_name, code_offset_in_func, target_func_name)]
        self.global_symbols = {}   # global_name -> offset in data section
        self.global_data = []      # [(name, bytes_value, offset)]

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
        self.global_symbols = {}
        self.global_data = []

        # 先收集全局变量的初始值
        for global_var in module.globals:
            name = global_var.name
            if name not in self.global_symbols:
                # 全局变量在数据段占 8 字节（一个 qword）
                self.global_symbols[name] = offset
                if global_var.data is not None:
                    data_val = global_var.data.value
                else:
                    data_val = b'\x00' * 8
                # 填充到 8 字节
                while len(data_val) < 8:
                    data_val += b'\x00'
                self.global_data.append((name, data_val[:8], offset))
                offset += 8

        # 再收集字符串和浮点常量
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

    def _alloc_vreg(self, name, vregs, free_gprs, free_xmms, is_float=False,
                    preallocated=None):
        """分配虚拟寄存器到物理寄存器

        如果提供了 preallocated 映射（来自 LinearScanAllocator），
        则优先使用预分配结果；否则从 free_gprs/free_xmms 按需分配。
        """
        if name not in vregs:
            if preallocated is not None and name in preallocated:
                reg = preallocated[name]
                vregs[name] = reg
                # 从对应的 free 列表中移除预分配的寄存器，避免重复分配
                if is_float:
                    if reg in free_xmms:
                        free_xmms.remove(reg)
                else:
                    if reg in free_gprs:
                        free_gprs.remove(reg)
            elif is_float and free_xmms:
                vregs[name] = free_xmms.pop(0)
            elif not is_float and free_gprs:
                vregs[name] = free_gprs.pop(0)
            else:
                vregs[name] = None
        return vregs[name]

    # ============================================================
    # 活跃区间分析与线性扫描寄存器分配
    # ============================================================

    def _collect_vreg_info(self, instr):
        """从一条 LIR 指令中提取所有引用的虚拟寄存器名及其类型。

        返回 (used_vregs, defined_vregs)，每个元素是 (name, is_float) 的列表。
        used_vregs: 被读取的虚拟寄存器
        defined_vregs: 被写入的虚拟寄存器
        """
        used = []
        defined = []

        if isinstance(instr, LIRLoadConst):
            # 常量加载：定义一个虚拟寄存器
            is_float = (instr.const_type == "float")
            if instr.const_type == "float":
                name = f"fconst_{instr.value}"
            elif instr.const_type == "string":
                name = f"sconst_{instr.value}"
            elif instr.const_type == "bool":
                name = f"bconst_{instr.value}"
            elif instr.const_type == "closure":
                name = f"closure_{instr.value}"
            else:
                name = f"const_{instr.value}"
            defined.append((name, is_float))

        elif isinstance(instr, LIRBinOp):
            # 二元运算：使用 src_locs，定义 dst_loc
            if instr.src_locs:
                for loc, typ in instr.src_locs:
                    is_float = (typ == FLOAT_TYPE)
                    used.append((loc, is_float))
            if instr.dst_loc:
                dst_name, dst_type = instr.dst_loc
                is_float = (dst_type == FLOAT_TYPE)
                defined.append((dst_name, is_float))

        elif isinstance(instr, LIRUnaryOp):
            # 一元运算：使用 src_locs，定义 dst_loc
            if instr.src_locs:
                for loc, typ in instr.src_locs:
                    is_float = (typ == FLOAT_TYPE)
                    used.append((loc, is_float))
            if instr.dst_loc:
                dst_name, dst_type = instr.dst_loc
                is_float = (dst_type == FLOAT_TYPE)
                defined.append((dst_name, is_float))

        elif isinstance(instr, LIRCall):
            # 函数调用：使用 src_locs 作为参数
            if instr.src_locs:
                for loc, typ in instr.src_locs:
                    is_float = (typ == FLOAT_TYPE)
                    used.append((loc, is_float))

        elif isinstance(instr, LIRCallIndirect):
            # 间接调用：使用 src_locs（第一个是函数指针，其余是参数）
            if instr.src_locs:
                for loc, typ in instr.src_locs:
                    is_float = (typ == FLOAT_TYPE)
                    used.append((loc, is_float))

        elif isinstance(instr, LIRLoadGlobal):
            # 加载全局变量：定义 global_<name>
            name = f"global_{instr.global_name}"
            defined.append((name, False))

        elif isinstance(instr, LIRStoreGlobal):
            # 存储全局变量：使用 global_<name>
            name = f"global_{instr.global_name}"
            used.append((name, False))

        elif isinstance(instr, LIRLoadReg):
            # 寄存器传送：使用 src_locs，定义 dst_loc
            if instr.src_locs:
                for loc, typ in instr.src_locs:
                    is_float = (typ == FLOAT_TYPE)
                    used.append((loc, is_float))
            if instr.dst_loc:
                dst_name, dst_type = instr.dst_loc
                is_float = (dst_type == FLOAT_TYPE)
                defined.append((dst_name, is_float))

        elif isinstance(instr, LIRStoreReg):
            # 存储到寄存器：使用 src_locs，定义 dst_loc
            if instr.src_locs:
                for loc, typ in instr.src_locs:
                    is_float = (typ == FLOAT_TYPE)
                    used.append((loc, is_float))
            if instr.dst_loc:
                dst_name, dst_type = instr.dst_loc
                is_float = (dst_type == FLOAT_TYPE)
                defined.append((dst_name, is_float))

        elif isinstance(instr, LIRIndex):
            # 索引操作：使用 src_locs，定义 dst_loc
            if instr.src_locs:
                for loc, typ in instr.src_locs:
                    is_float = (typ == FLOAT_TYPE)
                    used.append((loc, is_float))
            if instr.dst_loc:
                dst_name, dst_type = instr.dst_loc
                is_float = (dst_type == FLOAT_TYPE)
                defined.append((dst_name, is_float))

        elif isinstance(instr, LIRFieldAccess):
            # 字段访问：使用 src_locs，定义 dst_loc
            if instr.src_locs:
                for loc, typ in instr.src_locs:
                    is_float = (typ == FLOAT_TYPE)
                    used.append((loc, is_float))
            if instr.dst_loc:
                dst_name, dst_type = instr.dst_loc
                is_float = (dst_type == FLOAT_TYPE)
                defined.append((dst_name, is_float))

        elif isinstance(instr, (LIRBuildList, LIRBuildTuple, LIRBuildADT)):
            # 数据结构构建：使用 src_locs
            if instr.src_locs:
                for loc, typ in instr.src_locs:
                    is_float = (typ == FLOAT_TYPE)
                    used.append((loc, is_float))

        elif isinstance(instr, LIRBranch):
            # 条件分支：使用 cond_reg
            if instr.cond_reg:
                used.append((instr.cond_reg, False))

        elif isinstance(instr, LIRReturn):
            # 返回：使用 src_locs（返回值）
            if instr.src_locs:
                for loc, typ in instr.src_locs:
                    is_float = (typ == FLOAT_TYPE)
                    used.append((loc, is_float))

        # LIRLabel, LIRJump, LIRPanic 不涉及虚拟寄存器

        return used, defined

    def _analyze_live_intervals(self, func: LIRFunction):
        """分析函数中所有虚拟寄存器的活跃区间。

        返回 (gpr_intervals, xmm_intervals)，分别是整型和浮点虚拟寄存器的
        LiveInterval 列表。
        """
        # vreg_name -> (first_use, last_use, is_float)
        vreg_info = {}

        for idx, instr in enumerate(func.body):
            used, defined = self._collect_vreg_info(instr)

            # 处理使用的 vreg
            for name, is_float in used:
                if name not in vreg_info:
                    vreg_info[name] = [idx, idx, is_float]
                else:
                    # 更新 last_use
                    vreg_info[name][1] = idx

            # 处理定义的 vreg
            for name, is_float in defined:
                if name not in vreg_info:
                    vreg_info[name] = [idx, idx, is_float]
                else:
                    # 更新 last_use（定义也是活跃区间的一部分）
                    vreg_info[name][1] = idx

        # 构建 GPR 和 XMM 的活跃区间列表
        gpr_intervals = []
        xmm_intervals = []

        for name, (first, last, is_float) in vreg_info.items():
            interval = LiveInterval(name, first, last)
            if is_float:
                xmm_intervals.append(interval)
            else:
                gpr_intervals.append(interval)

        return gpr_intervals, xmm_intervals

    def _run_linear_scan_alloc(self, func: LIRFunction):
        """运行线性扫描寄存器分配。

        返回 vreg_map (Dict[str, int]) 表示成功，返回 None 表示分配失败
        （寄存器不足，需要 fallback 到按需分配）。
        """
        gpr_intervals, xmm_intervals = self._analyze_live_intervals(func)

        if not gpr_intervals and not xmm_intervals:
            return {}  # 没有虚拟寄存器，返回空映射

        # 可用寄存器（与 _compile_body 中使用的列表一致）
        available_gprs = [RAX, RCX, RDX, RBX, R8, R9, R10, R11, R12, R13, R14, R15]
        available_xmms = [XMM0, XMM1, XMM2, XMM3, XMM4, XMM5, XMM6, XMM7]

        vreg_map = {}

        # 分配 GPR
        if gpr_intervals:
            gpr_alloc = LinearScanAllocator(available_gprs)
            gpr_result, gpr_slots = gpr_alloc.allocate(gpr_intervals)
            if gpr_slots > 0:
                # 有溢出，分配失败
                return None
            vreg_map.update(gpr_result)

        # 分配 XMM
        if xmm_intervals:
            xmm_alloc = LinearScanAllocator(available_xmms)
            xmm_result, xmm_slots = xmm_alloc.allocate(xmm_intervals)
            if xmm_slots > 0:
                # 有溢出，分配失败
                return None
            vreg_map.update(xmm_result)

        return vreg_map

    def _get_vreg(self, vregs, name):
        """获取虚拟寄存器对应的物理寄存器，未分配时抛出错误"""
        if name not in vregs or vregs[name] is None:
            raise ValueError(f"Native 后端：虚拟寄存器 '{name}' 未分配")
        return vregs[name]

    def _compile_const_float(self, e, instr, vregs, free_gprs, free_xmms,
                             func_relocations, preallocated=None):
        """编译浮点常量加载：通过 RIP-relative movsd 从数据段加载"""
        reg = self._alloc_vreg(f"fconst_{instr.value}", vregs, free_gprs, free_xmms,
                               is_float=True, preallocated=preallocated)
        if reg is not None:
            value = float(instr.value)
            data_offset = self.float_constant_map.get(value)
            if data_offset is not None:
                rip_offset = e.movsd_reg_imm(reg, 0)
                func_relocations.append((rip_offset, data_offset))

    def _compile_const_string(self, e, instr, vregs, free_gprs, free_xmms,
                              func_relocations, preallocated=None):
        """编译字符串常量加载：通过 RIP-relative lea 获取地址"""
        reg = self._alloc_vreg(f"sconst_{instr.value}", vregs, free_gprs, free_xmms,
                               preallocated=preallocated)
        if reg is not None:
            value = instr.value
            data_offset = self.string_constant_map.get(value)
            if data_offset is not None:
                rip_offset = e.lea_reg_rip(reg, 0)
                func_relocations.append((rip_offset, data_offset))

    def _compile_const_closure(self, e, instr, vregs, free_gprs, free_xmms,
                               func_name, preallocated=None):
        """编译闭包常量加载：通过 RIP-relative lea 获取函数地址作为函数指针。

        instr.value 格式为 "<closure:fn_name>"，解析出目标函数名，
        使用 RIP-relative LEA 加载函数符号地址到目标寄存器。
        记录重定位条目，类型为函数符号引用（代码段内相对寻址）。
        """
        # 解析函数名："<closure:fn_name>" -> "fn_name"
        value = instr.value
        if value.startswith("<closure:") and value.endswith(">"):
            target_func = value[len("<closure:"):-1]
        else:
            target_func = value  # fallback，直接用 value 作为函数名

        reg = self._alloc_vreg(f"closure_{instr.value}", vregs, free_gprs, free_xmms,
                               preallocated=preallocated)
        if reg is not None:
            rip_offset = e.lea_reg_rip(reg, 0)
            self.closure_relocations.append((func_name, rip_offset, target_func))

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

    def _compile_call_indirect(self, e, instr, vregs, free_gprs, free_xmms):
        """编译间接调用（通过函数指针），按 System V AMD64 ABI 传递参数。

        src_locs 布局:
          [0] = 函数指针（寄存器/SSA 值）
          [1:] = 调用参数
        """
        if not instr.src_locs:
            return

        # 第一个 src_loc 是函数指针
        func_ptr_loc, func_ptr_type = instr.src_locs[0]
        func_ptr_reg = vregs.get(func_ptr_loc)

        # 将函数指针移入 R11（间接调用专用寄存器，caller-saved）
        # R11 不会与参数寄存器冲突
        if func_ptr_reg is not None and func_ptr_reg != R11:
            e.mov_reg_reg64(R11, func_ptr_reg)
        elif func_ptr_reg is None:
            e.mov_reg_imm64(R11, 0)

        # 剩余 src_locs 是调用参数，按 System V AMD64 ABI 传递
        int_idx = 0
        float_idx = 0
        stack_gprs = []

        for loc, typ in instr.src_locs[1:]:
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

        # 发射间接调用指令：call *%r11
        e.call_reg(R11)

        # 恢复栈指针
        if stack_gprs:
            e.add_rsp_imm(len(stack_gprs) * 8)

    def _emit_epilogue(self, e: X86_64Emitter, func: LIRFunction):
        """发射函数尾声：恢复栈帧 + 弹出 callee-saved 寄存器 + ret。

        显式 return（LIRReturn）与函数末尾的 fall-through 都复用此方法，
        确保任何退出路径都正确恢复栈帧，避免使用显式 return 时栈损坏。
        必须与 _compile_function 中的 prologue（push callee-saved + sub rsp）配对。
        """
        if func.stack_size > 0:
            aligned = (func.stack_size + 15) & ~15
            e.add_rsp_imm(aligned)
        for reg in reversed(CALLEE_SAVED):
            e.pop_reg(reg)
        e.ret()

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

        # 尝试使用 LinearScanAllocator 进行预分配
        # 如果分配失败（寄存器不足），fallback 到按需分配
        preallocated_vregs = self._run_linear_scan_alloc(func)

        # 编译函数体
        self._compile_body(e, func, label_positions, pending_jumps,
                           pending_branches, func_relocations,
                           preallocated=preallocated_vregs)

        # 函数尾声：恢复栈帧 + 弹出 callee-saved + ret（复用统一方法）
        self._emit_epilogue(e, func)

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
                      pending_branches: list, func_relocations: list,
                      preallocated: Optional[Dict[str, int]] = None):
        """编译函数体指令

        Args:
            preallocated: 预分配的 vreg -> 物理寄存器映射（来自 LinearScanAllocator）。
                         为 None 时使用按需分配策略（fallback）。
        """
        vregs = {}
        free_gprs = [RAX, RCX, RDX, RBX, R8, R9, R10, R11, R12, R13, R14, R15]
        free_xmms = [XMM0, XMM1, XMM2, XMM3, XMM4, XMM5, XMM6, XMM7]

        for instr in func.body:
            if isinstance(instr, LIRLoadConst):
                if instr.const_type == "int":
                    reg = self._alloc_vreg(f"const_{instr.value}", vregs, free_gprs, free_xmms,
                                           preallocated=preallocated)
                    if reg is not None:
                        e.mov_reg_imm64(reg, int(instr.value))
                elif instr.const_type == "float":
                    self._compile_const_float(e, instr, vregs, free_gprs, free_xmms,
                                              func_relocations, preallocated=preallocated)
                elif instr.const_type == "bool":
                    reg = self._alloc_vreg(f"bconst_{instr.value}", vregs, free_gprs, free_xmms,
                                           preallocated=preallocated)
                    if reg is not None:
                        e.mov_reg_imm64(reg, 1 if instr.value else 0)
                elif instr.const_type == "string":
                    self._compile_const_string(e, instr, vregs, free_gprs, free_xmms,
                                               func_relocations, preallocated=preallocated)
                elif instr.const_type == "closure":
                    self._compile_const_closure(e, instr, vregs, free_gprs, free_xmms,
                                                func.name, preallocated=preallocated)
                else:
                    raise NotImplementedError(
                        f"LIRLoadConst const_type '{instr.const_type}' is not yet implemented in native backend"
                    )

            elif isinstance(instr, LIRBinOp):
                op = instr.op
                # 从 vregs 中查找操作数寄存器
                left_reg = RAX
                right_reg = RCX
                is_float_left = False
                is_float_right = False
                if instr.src_locs:
                    if len(instr.src_locs) >= 1:
                        left_name, left_type = instr.src_locs[0]
                        left_reg = self._get_vreg(vregs, left_name)
                        is_float_left = (left_type == FLOAT_TYPE)
                    if len(instr.src_locs) >= 2:
                        right_name, right_type = instr.src_locs[1]
                        right_reg = self._get_vreg(vregs, right_name)
                        is_float_right = (right_type == FLOAT_TYPE)

                # 操作数是否为浮点（两个操作数类型应一致）
                is_float_op = is_float_left or is_float_right

                # 确定目标寄存器：默认结果留在左操作数寄存器中
                dst_reg = left_reg
                is_float_dst = False
                if instr.dst_loc:
                    dst_name, dst_type = instr.dst_loc
                    is_float_dst = (dst_type == FLOAT_TYPE)
                    dst_reg = self._alloc_vreg(dst_name, vregs, free_gprs, free_xmms,
                                               is_float=is_float_dst, preallocated=preallocated)
                    if dst_reg is None:
                        raise ValueError(
                            f"Native 后端：无法为目标虚拟寄存器 '{dst_name}' 分配物理寄存器"
                        )

                if op in ("+", "-", "*", "/", "%"):
                    if is_float_op:
                        # 浮点算术运算：使用 SSE2 指令
                        dst = left_reg
                        src = right_reg
                        if op == "+":
                            e.addsd_reg_reg(dst, src)
                        elif op == "-":
                            e.subsd_reg_reg(dst, src)
                        elif op == "*":
                            e.mulsd_reg_reg(dst, src)
                        elif op == "/":
                            e.divsd_reg_reg(dst, src)
                        elif op == "%":
                            raise NotImplementedError(
                                "LIRBinOp float '%' is not yet implemented in native backend"
                            )
                    else:
                        # 整数算术运算
                        dst = left_reg
                        src = right_reg
                        if op == "+":
                            e.add_reg_reg(dst, src)
                        elif op == "-":
                            e.sub_reg_reg(dst, src)
                        elif op == "*":
                            e.imul_reg_reg(dst, src)
                        elif op == "/":
                            # idiv 要求被除数在 RDX:RAX
                            if dst != RAX:
                                e.mov_reg_reg64(RAX, dst)
                            e.cqo()
                            e.idiv_reg(src)
                            if dst != RAX:
                                e.mov_reg_reg64(dst, RAX)
                        elif op == "%":
                            if dst != RAX:
                                e.mov_reg_reg64(RAX, dst)
                            e.cqo()
                            e.idiv_reg(src)
                            e.mov_reg_reg64(dst, RDX)
                elif op in ("==", "!=", "<", ">", "<=", ">="):
                    if is_float_op:
                        # 浮点比较：ucomisd + setcc
                        # 比较结果为布尔值（0/1），存储在左操作数寄存器（整型）
                        e.ucomisd(left_reg, right_reg)
                        if op == "==":
                            e.sete(left_reg)
                        elif op == "!=":
                            e.setne(left_reg)
                        elif op == "<":
                            e.setb(left_reg)
                        elif op == ">":
                            e.seta(left_reg)
                        elif op == "<=":
                            e.setbe(left_reg)
                        elif op == ">=":
                            e.setae(left_reg)
                        e.movzx_reg32_reg8(left_reg, left_reg)
                    else:
                        # 整数比较
                        if op == "==":
                            e.cmp_reg_reg(left_reg, right_reg)
                            e.sete(left_reg)
                            e.movzx_reg32_reg8(left_reg, left_reg)
                        elif op == "!=":
                            e.cmp_reg_reg(left_reg, right_reg)
                            e.setne(left_reg)
                            e.movzx_reg32_reg8(left_reg, left_reg)
                        elif op == "<":
                            e.cmp_reg_reg(left_reg, right_reg)
                            e.setl(left_reg)
                            e.movzx_reg32_reg8(left_reg, left_reg)
                        elif op == ">":
                            e.cmp_reg_reg(left_reg, right_reg)
                            e.setg(left_reg)
                            e.movzx_reg32_reg8(left_reg, left_reg)
                        elif op == "<=":
                            e.cmp_reg_reg(left_reg, right_reg)
                            e.setle(left_reg)
                            e.movzx_reg32_reg8(left_reg, left_reg)
                        elif op == ">=":
                            e.cmp_reg_reg(left_reg, right_reg)
                            e.setge(left_reg)
                            e.movzx_reg32_reg8(left_reg, left_reg)
                elif op in ("&&", "||"):
                    # 逻辑运算：先将操作数规范化为 0/1 布尔值，再执行位运算。
                    # 注意：LIR 层两个操作数已求值完毕，无法实现真正的短路求值，
                    # 但通过 test+setne 规范化后，and/or 在 0/1 上等价于布尔 AND/OR。
                    e.test_reg_reg(left_reg, left_reg)
                    e.setne(left_reg)
                    e.movzx_reg32_reg8(left_reg, left_reg)
                    e.test_reg_reg(right_reg, right_reg)
                    e.setne(right_reg)
                    e.movzx_reg32_reg8(right_reg, right_reg)
                    if op == "&&":
                        e.and_reg_reg(left_reg, right_reg)
                    else:
                        e.or_reg_reg(left_reg, right_reg)
                else:
                    raise NotImplementedError(
                        f"LIRBinOp operator '{op}' is not yet implemented in native backend"
                    )

                # 如果目标寄存器与左操作数寄存器不同，将结果移动到目标寄存器
                if instr.dst_loc and dst_reg != left_reg:
                    if is_float_dst:
                        e.movsd_reg_reg(dst_reg, left_reg)
                    else:
                        e.mov_reg_reg64(dst_reg, left_reg)

            elif isinstance(instr, LIRUnaryOp):
                # 从 vregs 中查找操作数寄存器
                operand_reg = RAX
                if instr.src_locs:
                    operand_name = instr.src_locs[0][0]
                    operand_reg = self._get_vreg(vregs, operand_name)

                # 确定目标寄存器：默认结果留在操作数寄存器中
                dst_reg = operand_reg
                is_float_dst = False
                if instr.dst_loc:
                    dst_name, dst_type = instr.dst_loc
                    is_float_dst = (dst_type == FLOAT_TYPE)
                    dst_reg = self._alloc_vreg(dst_name, vregs, free_gprs, free_xmms,
                                               is_float=is_float_dst, preallocated=preallocated)
                    if dst_reg is None:
                        raise ValueError(
                            f"Native 后端：无法为目标虚拟寄存器 '{dst_name}' 分配物理寄存器"
                        )

                if instr.op == "-":
                    e.neg_reg(operand_reg)
                elif instr.op == "!":
                    e.cmp_reg_imm(operand_reg, 0)
                    e.sete(operand_reg)
                    e.movzx_reg32_reg8(operand_reg, operand_reg)
                elif instr.op == "NOT":
                    # 按位取反: NOT reg
                    e.not_reg(operand_reg)
                elif instr.op == "FLOAT_NEG":
                    # 浮点取反：0.0 - operand
                    temp_xmm = free_xmms.pop(0) if free_xmms else XMM7
                    e.xorpd_xmm(temp_xmm)  # temp = +0.0
                    e.subsd_reg_reg(temp_xmm, operand_reg)  # temp = 0.0 - operand
                    e.movsd_reg_reg(operand_reg, temp_xmm)  # operand = -operand
                    if temp_xmm != XMM7:
                        free_xmms.insert(0, temp_xmm)
                else:
                    raise NotImplementedError(
                        f"LIRUnaryOp operator '{instr.op}' is not yet implemented in native backend"
                    )

                # 如果目标寄存器与操作数寄存器不同，将结果移动到目标寄存器
                if instr.dst_loc and dst_reg != operand_reg:
                    if is_float_dst:
                        e.movsd_reg_reg(dst_reg, operand_reg)
                    else:
                        e.mov_reg_reg64(dst_reg, operand_reg)

            elif isinstance(instr, LIRCall):
                self._compile_call(e, instr, vregs, free_gprs, free_xmms, func.name)

            elif isinstance(instr, LIRReturn):
                # 从 src_locs 获取返回值，确保它在正确的返回寄存器中
                # 整数返回 -> RAX, 浮点返回 -> XMM0
                if instr.src_locs:
                    src_name, src_type = instr.src_locs[0]
                    is_float_ret = (src_type == FLOAT_TYPE)
                    src_reg = vregs.get(src_name)
                    if src_reg is not None:
                        if is_float_ret:
                            if src_reg != XMM0:
                                e.movsd_reg_reg(XMM0, src_reg)
                        else:
                            if src_reg != RAX:
                                e.mov_reg_reg64(RAX, src_reg)
                # 发射完整尾声（恢复栈帧 + pop callee-saved + ret），而非裸 ret。
                # 否则显式 return 会跳过栈帧恢复，导致栈损坏。
                self._emit_epilogue(e, func)

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

            # === 全局变量访问 ===
            elif isinstance(instr, LIRLoadGlobal):
                self._compile_load_global(e, instr, vregs, free_gprs, func_relocations,
                                          preallocated=preallocated)

            elif isinstance(instr, LIRStoreGlobal):
                self._compile_store_global(e, instr, vregs, free_gprs, func_relocations)

            # === 寄存器/栈传送 ===
            elif isinstance(instr, LIRLoadReg):
                self._compile_load_reg(e, instr, vregs, free_gprs, free_xmms,
                                       preallocated=preallocated)

            elif isinstance(instr, LIRStoreReg):
                self._compile_store_reg(e, instr, vregs, free_gprs, free_xmms)

            # === 间接调用 ===
            elif isinstance(instr, LIRCallIndirect):
                self._compile_call_indirect(e, instr, vregs, free_gprs, free_xmms)

            # === 索引操作 ===
            elif isinstance(instr, LIRIndex):
                self._compile_index(e, instr, vregs, free_gprs, free_xmms)

            # === 字段访问 ===
            elif isinstance(instr, LIRFieldAccess):
                self._compile_field_access(e, instr, vregs, free_gprs, free_xmms)

            # === 数据结构构建 ===
            elif isinstance(instr, LIRBuildList):
                self._compile_build_list(e, instr, vregs, free_gprs, free_xmms)

            elif isinstance(instr, LIRBuildTuple):
                self._compile_build_tuple(e, instr, vregs, free_gprs, free_xmms)

            elif isinstance(instr, LIRBuildADT):
                self._compile_build_adt(e, instr, vregs, free_gprs, free_xmms)

            else:
                raise NotImplementedError(
                    f"LIR instruction {type(instr).__name__} is not yet implemented in native backend"
                )

    # ============================================================
    # 全局变量编译
    # ============================================================

    def _compile_load_global(self, e: X86_64Emitter, instr: LIRLoadGlobal,
                              vregs: dict, free_gprs: list, func_relocations: list,
                              preallocated=None):
        """编译全局变量加载：通过 RIP-relative 寻址从数据段加载"""
        global_name = instr.global_name
        data_offset = self.global_symbols.get(global_name)

        if data_offset is None:
            # 全局变量未注册，尝试动态分配
            data_offset = len(self.global_data) * 8
            self.global_symbols[global_name] = data_offset
            self.global_data.append((global_name, b'\x00' * 8, data_offset))

        # 目标寄存器
        vreg_name = f"global_{global_name}"
        dst_reg = self._alloc_vreg(vreg_name, vregs, free_gprs, [], preallocated=preallocated)
        if dst_reg is None:
            dst_reg = RAX

        # mov dst_reg, [rip + offset]
        rip_offset = e.lea_reg_rip(dst_reg, 0)
        func_relocations.append((rip_offset, data_offset))
        # 然后加载实际值
        e.mov_reg_mem(dst_reg, dst_reg, 0)

    def _compile_store_global(self, e: X86_64Emitter, instr: LIRStoreGlobal,
                               vregs: dict, free_gprs: list, func_relocations: list):
        """编译全局变量存储：通过 RIP-relative 寻址存储到数据段"""
        global_name = instr.global_name
        data_offset = self.global_symbols.get(global_name)

        if data_offset is None:
            data_offset = len(self.global_data) * 8
            self.global_symbols[global_name] = data_offset
            self.global_data.append((global_name, b'\x00' * 8, data_offset))

        # 源值在 RAX（默认）
        src_reg = vregs.get(f"global_{global_name}", RAX)

        # 使用 RBX 作为临时地址寄存器
        # lea rbx, [rip + data_offset]
        rip_offset = e.lea_reg_rip(RBX, 0)
        func_relocations.append((rip_offset, data_offset))
        # mov [rbx], src_reg
        e.mov_mem_reg(RBX, 0, src_reg)

    # ============================================================
    # 寄存器/栈传送
    # ============================================================

    def _compile_load_reg(self, e: X86_64Emitter, instr: LIRLoadReg,
                           vregs: dict, free_gprs: list, free_xmms: list,
                           preallocated=None):
        """编译寄存器间传送：从 src_loc 移动到 dst_loc"""
        # 如果有源和目标位置信息
        if instr.src_locs:
            src_name, src_type = instr.src_locs[0]
            src_reg = vregs.get(src_name, RAX)
        else:
            src_reg = RAX

        if instr.dst_loc:
            dst_name, dst_type = instr.dst_loc
            is_float = (dst_type == FLOAT_TYPE)
            dst_reg = self._alloc_vreg(dst_name, vregs, free_gprs, free_xmms,
                                       is_float, preallocated=preallocated)
            if dst_reg is not None and dst_reg != src_reg:
                if is_float:
                    e.movsd_reg_reg(dst_reg, src_reg)
                else:
                    e.mov_reg_reg64(dst_reg, src_reg)

    def _compile_store_reg(self, e: X86_64Emitter, instr: LIRStoreReg,
                            vregs: dict, free_gprs: list, free_xmms: list):
        """编译存储到寄存器/栈：将当前值保存到目标位置"""
        # 值当前在 RAX（整数）或 XMM0（浮点）
        if instr.src_locs:
            src_name, src_type = instr.src_locs[0]
            is_float = (src_type == FLOAT_TYPE)
            src_reg = vregs.get(src_name, XMM0 if is_float else RAX)
        else:
            src_reg = RAX

        if instr.dst_loc:
            dst_name, dst_type = instr.dst_loc
            vregs[dst_name] = src_reg

    # ============================================================
    # 索引操作编译
    # ============================================================

    def _compile_index(self, e: X86_64Emitter, instr: LIRIndex,
                        vregs: dict, free_gprs: list, free_xmms: list):
        """编译索引操作：从 List/数组中加载指定位置的元素。

        List 内存布局: [count: int64][elem_0: ptr][elem_1: ptr]...
        偏移计算: LIST_HEADER_SIZE + index * LIST_ELEM_SIZE

        src_locs[0]: 数组/List 基址寄存器名（可选）
        src_locs[1]: 索引值寄存器名（可选）

        生成的 x86_64 代码（有索引时）:
          mov  rcx, index_reg          ; 索引值
          mov  rdx, ELEM_SIZE          ; 8
          imul rcx, rdx                ; rcx = index * 8
          add  rcx, HEADER_SIZE        ; rcx = 8 + index * 8
          add  base_reg, rcx           ; base_reg 指向目标元素
          mov  rax, [base_reg]         ; 加载元素

        无 src_locs 时默认取偏移 0 处的元素（即第一个元素）。
        """
        if not instr.src_locs:
            # 无操作数：默认取 List 偏移 LIST_HEADER_SIZE 处的第一个元素
            # mov rax, [rax + LIST_HEADER_SIZE]
            e.mov_reg_mem(RAX, RAX, self.LIST_HEADER_SIZE)
            return

        # 获取数组基址寄存器
        base_reg = vregs.get(instr.src_locs[0][0], RAX)

        if len(instr.src_locs) >= 2:
            # 有显式索引值
            index_reg = vregs.get(instr.src_locs[1][0], RCX)

            # 使用 RDX 作为临时寄存器计算 index * LIST_ELEM_SIZE
            e.mov_reg_imm64(RDX, self.LIST_ELEM_SIZE)
            # mov rcx, index_reg
            e.mov_reg_reg64(RCX, index_reg)
            # imul rcx, rdx  =>  rcx = index * ELEM_SIZE
            e.imul_reg_reg(RCX, RDX)
            # add rcx, LIST_HEADER_SIZE  =>  rcx = 8 + index * 8
            e.add_reg_imm(RCX, self.LIST_HEADER_SIZE)
            # 将偏移加到基址上：base_reg += rcx
            e.add_reg_reg(base_reg, RCX)
            # 加载元素: mov rax, [base_reg + 0]
            e.mov_reg_mem(RAX, base_reg, 0)
        else:
            # 有基址但无索引，取第一个元素
            e.mov_reg_mem(RAX, base_reg, self.LIST_HEADER_SIZE)

    def _compile_field_access(self, e: X86_64Emitter, instr: LIRFieldAccess,
                              vregs: dict, free_gprs: list, free_xmms: list):
        """编译 ADT/结构体字段访问：从基址 + 偏移处加载字段值。"""
        base_reg = vregs.get(instr.src_locs[0][0], RAX) if instr.src_locs else RAX
        dest_reg = vregs.get(instr.dst_loc[0], RAX) if instr.dst_loc else RAX
        # 加载字段: mov dest, [base + offset]
        e.mov_reg_mem(dest_reg, base_reg, instr.offset)

    # ============================================================
    # 数据结构构建
    # ============================================================

    def _compile_build_list(self, e: X86_64Emitter, instr: LIRBuildList,
                            vregs: dict, free_gprs: list, free_xmms: list):
        """编译列表构建：

        内存布局: [count: int64][elem_0: ptr][elem_1: ptr]...
        在栈上分配空间，填充 count 和各元素指针，RAX 指向列表头部。
        """
        count = instr.count
        total_size = self.LIST_HEADER_SIZE + count * self.LIST_ELEM_SIZE

        # 在栈上分配空间（栈向低地址增长）
        e.sub_rsp_imm(total_size)
        # RAX 现在指向列表头部
        e.mov_reg_reg64(RAX, RSP)

        # 写入 count
        e.mov_mem_imm64(RSP, 0, count)

        # 写入各元素指针
        # src_locs 包含元素寄存器名，按顺序排列
        for i, (loc, typ) in enumerate(instr.src_locs):
            src_reg = vregs.get(loc, RAX)
            elem_offset = self.LIST_HEADER_SIZE + i * self.LIST_ELEM_SIZE
            e.mov_mem_reg(RSP, elem_offset, src_reg)

    def _compile_build_tuple(self, e: X86_64Emitter, instr: LIRBuildTuple,
                              vregs: dict, free_gprs: list, free_xmms: list):
        """编译元组构建：

        内存布局: [field_0][field_1]... (每个 8 字节)
        在栈上分配空间，填充各字段值，RAX 指向元组头部。
        """
        count = instr.count
        total_size = count * 8

        e.sub_rsp_imm(total_size)
        e.mov_reg_reg64(RAX, RSP)

        for i, (loc, typ) in enumerate(instr.src_locs):
            src_reg = vregs.get(loc, RAX)
            field_offset = i * 8
            e.mov_mem_reg(RSP, field_offset, src_reg)

    def _compile_build_adt(self, e: X86_64Emitter, instr: LIRBuildADT,
                            vregs: dict, free_gprs: list, free_xmms: list):
        """编译 ADT 构建：

        内存布局: [tag: int64][field_0: val][field_1: val]...
        在栈上分配空间，写入 tag 和各字段值，RAX 指向 ADT 结构头部。
        """
        tag = instr.type_tag
        field_count = instr.field_count
        total_size = self.ADT_TAG_SIZE + field_count * self.ADT_FIELD_SIZE

        e.sub_rsp_imm(total_size)
        e.mov_reg_reg64(RAX, RSP)

        # 写入 tag (variant discriminator)
        e.mov_mem_imm64(RSP, 0, tag)

        # 写入各字段值
        for i, (loc, typ) in enumerate(instr.src_locs):
            src_reg = vregs.get(loc, RAX)
            field_offset = self.ADT_TAG_SIZE + i * self.ADT_FIELD_SIZE
            e.mov_mem_reg(RSP, field_offset, src_reg)

    # ============================================================
    # 循环编译辅助
    # ============================================================

    def _compile_counted_loop(self, e: X86_64Emitter, loop_instrs: list,
                              vregs: dict, free_gprs: list, free_xmms: list,
                              label_positions: dict, pending_jumps: list,
                              pending_branches: list, func_relocations: list):
        """编译计数循环。

        预期的指令模式：
          LIRLabel("loop_start")
          LIRLoadConst(counter_start, "int")
          LIRLoadConst(counter_end, "int")
          LIRBinOp("<")          # counter < end
          LIRBranch(cond, "loop_body", "loop_end")
          LIRLabel("loop_body")
          ... (循环体)
          LIRJump("loop_start")
          LIRLabel("loop_end")

        由 _compile_body 中的通用标签/跳转机制自动处理，
        此方法提供文档说明和额外的循环优化接口。
        """
        # 循环编译已由 _compile_body 的通用机制处理
        # 标签 + 跳转 + 条件分支 的组合自然形成循环
        pass

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

        # Patch closure (函数指针) RIP-relative 引用
        for func_name, offset_in_func, target_name in self.closure_relocations:
            func_base = 0 if func_name == "_start" else func_offsets.get(func_name, 0)
            abs_offset = func_base + offset_in_func
            target_base = func_offsets.get(target_name, 0)
            rel = target_base - (abs_offset + 4)
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
        # 先写入全局变量数据
        for name, value_bytes, _ in self.global_data:
            data.extend(value_bytes)
            # 全局变量已固定 8 字节
        # 再写入浮点常量
        for value_bytes, _ in self.float_constants:
            data.extend(value_bytes)
            while len(data) % 8 != 0:
                data.append(0)
        # 再写入字符串常量
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
    直接从 LIR 构建编译为 x86_64 ELF 可执行文件
    用于快速验证机器码生成是否正确
    """

    def __init__(self):
        self.codegen = NativeCodeGen()

    def compile(self, output_path: str) -> str:
        """构建包含所有新特性的 LIR 程序并编译为 ELF"""
        lir = self._build_comprehensive_lir()
        return self.codegen.compile_and_write(lir, output_path)

    def compile_source(self, source: str, output_path: str) -> str:
        """将 Nova 源码编译为 x86_64 ELF（AST to LIR 尚未实现）"""
        raise NotImplementedError(
            "SimpleNativeCompiler.compile_source is not yet implemented: "
            "AST to LIR lowering is not available in the native backend"
        )

    def _build_comprehensive_lir(self) -> LIRModule:
        """构建包含所有已实现特性的 LIR 程序

        该程序演示：
        1. 常量加载（整数、浮点、布尔、字符串）
        2. 算术运算（+、-、*、/）
        3. 比较运算（<、<=、>、>=、==、!=）
        4. 一元运算（NEG、NOT）
        5. 条件分支
        6. 循环（计数循环：LIRLabel + LIRBinOp + LIRBranch + LIRJump）
        7. 函数调用
        8. ADT 构建
        9. List 构建
        10. 全局变量
        11. 返回值
        """
        lir = LIRModule(name="comprehensive")

        # --- 全局变量 ---
        global_x = LIRGlobal(name="global_counter", ir_type=INT_TYPE, data=LIRData(name="global_counter", value=b'\x00' * 8))
        lir.globals.append(global_x)

        # --- 辅助函数：compute_sum(a, b) ---
        fn_compute = LIRFunction("compute_sum", [], INT_TYPE)
        fn_compute.body = [
            LIRLoadConst(value=10, const_type="int"),
            LIRLoadConst(value=20, const_type="int"),
            LIRBinOp(op="+"),
            LIRReturn(),
        ]
        lir.functions["compute_sum"] = fn_compute

        # --- 主函数：main ---
        fn_main = LIRFunction("main", [], INT_TYPE)
        fn_main.body = [
            # 1. 常量加载
            LIRLoadConst(value=0, const_type="int"),

            # 2. 比较运算：10 < 20
            LIRLoadConst(value=10, const_type="int"),
            LIRLoadConst(value=20, const_type="int"),
            LIRBinOp(op="<"),
            LIRBranch(cond_reg="", true_label="less_than", false_label="not_less"),

            # 3. 条件分支
            LIRLabel(name="less_than"),
            LIRLoadConst(value=1, const_type="int"),
            LIRJump(target="after_compare"),
            LIRLabel(name="not_less"),
            LIRLoadConst(value=0, const_type="int"),
            LIRLabel(name="after_compare"),

            # 4. 一元运算：NOT
            LIRUnaryOp(op="!"),

            # 5. 循环：从 0 计数到 5
            LIRLabel(name="loop_start"),
            LIRLoadConst(value=0, const_type="int"),   # counter
            LIRLoadConst(value=5, const_type="int"),    # limit
            LIRBinOp(op="<"),
            LIRBranch(cond_reg="", true_label="loop_body", false_label="loop_end"),

            LIRLabel(name="loop_body"),
            # 循环体：使用全局变量
            LIRLoadGlobal(global_name="global_counter"),
            LIRLoadConst(value=1, const_type="int"),
            LIRBinOp(op="+"),
            LIRStoreGlobal(global_name="global_counter"),
            LIRJump(target="loop_start"),
            LIRLabel(name="loop_end"),

            # 6. ADT 构建：tag=0, 1 个字段
            LIRBuildADT(type_tag=0, field_count=1),
            LIRLoadConst(value=42, const_type="int"),

            # 7. List 构建：3 个元素
            LIRLoadConst(value=100, const_type="int"),
            LIRLoadConst(value=200, const_type="int"),
            LIRLoadConst(value=300, const_type="int"),
            LIRBuildList(count=3),

            # 8. 函数调用
            LIRCall(func_name="compute_sum", arg_count=0),

            # 9. 返回
            LIRReturn(),
        ]
        lir.functions["main"] = fn_main

        return lir

    def _build_simple_lir(self, ast):
        """从 AST 构建简单的 LIR（占位实现，尚未完成）"""
        raise NotImplementedError(
            "SimpleNativeCompiler._build_simple_lir is not yet implemented: "
            "AST to LIR lowering is not available in the native backend"
        )
