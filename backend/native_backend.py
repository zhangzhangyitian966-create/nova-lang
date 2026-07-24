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
    LIRBuildADT,
    LIRBuildList,
    LIRBuildMap,
    LIRBuildTuple,
    LIRCall,
    LIRCallIndirect,
    LIRClosureCreate,
    LIRFieldAccess,
    LIRFunction,
    LIRIndex,
    LIRJump,
    LIRLabel,
    LIRListAppend,
    LIRLoadConst,
    LIRLoadReg,
    LIRModule,
    LIRPanic,
    LIRReturn,
    LIRStoreReg,
    LIRSwitch,
    LIRUnaryOp,
)

# ============================================================
# 指令发射上下文（传递寄存器分配结果和汇编状态）
# ============================================================


class _EmitContext:
    """封装指令发射阶段的上下文：发射器、函数名、寄存器分配、跳转/标签信息。"""

    def __init__(self, e, func_name, vreg_alloc, label_offsets, jump_fixups):
        self.e = e
        self.func_name = func_name
        self.vreg_alloc = vreg_alloc
        self.label_offsets = label_offsets
        self.jump_fixups = jump_fixups

    def get_loc(self, vreg_name):
        """获取虚拟寄存器的物理位置：("reg", phys_reg) 或 ("stack", offset)"""
        if vreg_name in self.vreg_alloc:
            return self.vreg_alloc[vreg_name]
        raise ValueError(
            f"寄存器分配错误：虚拟寄存器 '{vreg_name}' 未找到分配记录。"
            f"已分配的 vreg: {list(self.vreg_alloc.keys())[:10]}..."
        )

    def load_to_reg(self, vreg_name, target_reg, is_float=False):
        """将 vreg 的值加载到目标物理寄存器。"""
        loc = self.get_loc(vreg_name)
        if loc[0] == "reg":
            if loc[1] != target_reg:
                if is_float:
                    self.e.movsd_reg_reg(target_reg, loc[1])
                else:
                    self.e.mov_reg_reg64(target_reg, loc[1])
        else:
            if is_float:
                self.e.movsd_reg_mem(target_reg, RSP, loc[1])
            else:
                self.e.mov_reg_mem(target_reg, RSP, loc[1])

    def store_from_reg(self, vreg_name, source_reg, is_float=False):
        """将源物理寄存器的值存储到 vreg 的位置。"""
        loc = self.get_loc(vreg_name)
        if loc[0] == "reg":
            if loc[1] != source_reg:
                if is_float:
                    self.e.movsd_reg_reg(loc[1], source_reg)
                else:
                    self.e.mov_reg_reg64(loc[1], source_reg)
        else:
            if is_float:
                self.e.movsd_mem_reg(RSP, loc[1], source_reg)
            else:
                self.e.mov_mem_reg(RSP, loc[1], source_reg)


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
        self.external_calls = []  # [(caller_func_name, code_offset_in_func, external_func_name)]
        # 常量值 -> 数据段偏移的映射（用于快速查找）
        self._float_const_map = {}  # value_str -> data_offset
        self._string_const_map = {}  # value -> data_offset

    def compile(self, lir_module: LIRModule) -> bytes:
        """编译 LIR Module 为 ELF 二进制"""
        # 0. 重置编译状态
        self.link_calls = []
        self.data_fixups = []
        self.external_calls = []

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
        """编译单个函数为机器码。

        栈帧布局（System V AMD64 ABI）：
          高地址
          ┌──────────────────┐
          │ 调用者栈帧        │ ← call 前 RSP
          │ 返回地址 (8B)     │ ← call 压入
          ├──────────────────┤ ← 函数入口 RSP ≡ 8 (mod 16)
          │ callee-saved (48B)│ ← 6 个 push (RBX, RBP, R12-15)
          ├──────────────────┤ ← push 后 RSP ≡ 8 (mod 16) (8+48=56)
          │ 对齐填充 (0-15B) │ ← 确保 sub 后 RSP ≡ 0 (mod 16)
          ├──────────────────┤
          │ 溢出槽区         │ ← 虚拟寄存器溢出位置
          │ [stack_offset]   │   RSP 正偏移寻址
          ├──────────────────┤ ← sub 后 RSP ≡ 0 (mod 16)
          │ (可能预留参数区) │
          └──────────────────┘ ← 当前 RSP
          低地址
        """
        e = X86_64Emitter()

        # 函数序言：保存 callee-saved 寄存器（6 个，48 字节）
        for reg in CALLEE_SAVED:
            e.push_reg(reg)

        # 计算 16 字节对齐的栈帧大小
        # push 6 个 callee-saved = 48 字节
        # 函数入口 RSP ≡ 8 (mod 16)，push 后 RSP ≡ 8 + 48 = 56 ≡ 8 (mod 16)
        # 需要 sub (stack_size + 8) 向上对齐到 16，使 RSP ≡ 0 (mod 16)
        if func.stack_size > 0:
            total = func.stack_size + 8  # +8 补偿 push 后的 8 (mod 16) 偏移
            aligned = (total + 15) & ~15
            func._native_frame_pad = aligned - 8  # 实际填充量（对齐贡献）
            e.sub_rsp_imm(aligned)
        else:
            func._native_frame_pad = 0

        # 编译函数体
        self._compile_body(e, func, func.name)

        # 函数尾声：恢复栈帧，恢复 callee-saved，返回
        if func.stack_size > 0:
            total = func.stack_size + 8
            aligned = (total + 15) & ~15
            e.add_rsp_imm(aligned)

        for reg in reversed(CALLEE_SAVED):
            e.pop_reg(reg)

        e.ret()

        return bytes(e.code)

    def _compile_body(self, e: X86_64Emitter, func: LIRFunction, func_name: str):
        """编译函数体指令（寄存器分配 + 两阶段汇编）。

        三阶段协调器：
        1. 线性扫描寄存器分配
        2. 发射指令（调度表分发）
        3. 回填跳转偏移
        """
        vreg_alloc, label_offsets, jump_fixups = self._allocate_registers(func)
        ctx = _EmitContext(
            e=e, func_name=func_name, vreg_alloc=vreg_alloc,
            label_offsets=label_offsets, jump_fixups=jump_fixups,
        )
        self._emit_instructions(func, ctx)
        self._fixup_jumps(ctx)

    # ============================================================
    # 阶段 A: 线性扫描寄存器分配
    # ============================================================

    def _allocate_registers(self, func: LIRFunction):
        """线性扫描寄存器分配，返回 (vreg_alloc, label_offsets, jump_fixups)。

        vreg_alloc: 虚拟寄存器到物理位置的映射
        label_offsets: 初始化为空 dict（供阶段 B 填充）
        jump_fixups: 初始化为空 list（供阶段 B 填充）
        """
        # 可用物理寄存器
        ALL_GPRS = [RCX, RDX, RSI, RDI, R8, R9, R10, R11,  # caller-saved
                    RBX, R12, R13, R14, R15]                # callee-saved
        ALL_XMMS = [XMM0, XMM1, XMM2, XMM3, XMM4, XMM5, XMM6, XMM7]

        # 步骤 1: 收集所有虚拟寄存器及其活跃区间
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

        for idx, instr in enumerate(func.body):
            for loc_name, loc_type in instr.src_locs:
                is_float = loc_type.kind == IRType.FLOAT
                _note_vreg(loc_name, is_float, idx)
            if instr.dst_loc:
                dst_name, dst_type = instr.dst_loc
                is_float = dst_type.kind == IRType.FLOAT
                _note_vreg(dst_name, is_float, idx)
            elif isinstance(instr, LIRLoadConst):
                is_float = instr.const_type == "float"
                vname = f"const_{instr.value}" if not is_float else f"fconst_{instr.value}"
                _note_vreg(vname, is_float, idx)

        # 步骤 2: 线性扫描分配
        vreg_alloc = {}
        stack_offset = 0
        sorted_vregs = sorted(vreg_info.items(), key=lambda x: x[1]["first"])

        active_gprs = {}  # phys_reg -> last_use
        active_xmms = {}  # xmm_reg -> last_use
        free_gprs = list(ALL_GPRS)
        free_xmms = list(ALL_XMMS)

        def _expire_old_intervals(current_idx, is_float):
            """回收已过期的寄存器（活跃区间结束点 < current_idx）"""
            active = active_xmms if is_float else active_gprs
            free = free_xmms if is_float else free_gprs
            to_free = [r for r, last in active.items() if last < current_idx]
            for r in to_free:
                del active[r]
                free.insert(0, r)

        def _spill_victim(is_float):
            """选择活跃区间最远的寄存器溢出，返回被溢出的 vreg 名"""
            active = active_xmms if is_float else active_gprs
            free = free_xmms if is_float else free_gprs
            if not active:
                return None
            victim_reg = max(active, key=active.get)
            victim_last = active[victim_reg]
            del active[victim_reg]
            free.insert(0, victim_reg)
            for vname, info in vreg_info.items():
                if vreg_alloc.get(vname) == ("reg", victim_reg) and info["last"] == victim_last:
                    return vname
            return None

        def _try_allocate(vname, is_float, last_use):
            """尝试为虚拟寄存器分配物理寄存器或栈槽"""
            nonlocal stack_offset
            active = active_xmms if is_float else active_gprs
            free = free_xmms if is_float else free_gprs
            if free:
                reg = free.pop(0)
                vreg_alloc[vname] = ("reg", reg)
                active[reg] = last_use
            else:
                victim = _spill_victim(is_float)
                if victim is not None and (free_xmms if is_float else free_gprs):
                    reg = (free_xmms if is_float else free_gprs).pop(0)
                    vreg_alloc[vname] = ("reg", reg)
                    active[reg] = last_use
                    stack_offset += 8
                    vreg_alloc[victim] = ("stack", stack_offset)
                else:
                    stack_offset += 8
                    vreg_alloc[vname] = ("stack", stack_offset)

        for vname, info in sorted_vregs:
            _expire_old_intervals(info["first"], info["is_float"])
            _try_allocate(vname, info["is_float"], info["last"])

        if stack_offset > func.stack_size:
            func.stack_size = stack_offset

        return vreg_alloc, {}, []

    # ============================================================
    # 阶段 B: 指令发射（调度表分发）
    # ============================================================

    def _emit_instructions(self, func: LIRFunction, ctx: "_EmitContext"):
        """发射所有指令，使用调度表按指令类型分发到具体编译方法。"""
        dispatch = self._build_native_instr_dispatch()
        for idx, instr in enumerate(func.body):
            handler = dispatch.get(type(instr))
            if handler:
                handler(instr, ctx)

    def _build_native_instr_dispatch(self):
        """构建指令编译调度表：LIR 指令类型 -> 编译方法。"""
        return {
            LIRLoadConst: self._emit_load_const,
            LIRBinOp: self._emit_binop,
            LIRUnaryOp: self._emit_unary_op,
            LIRCall: self._emit_call,
            LIRCallIndirect: self._emit_call_indirect,
            LIRReturn: self._emit_return,
            LIRJump: self._emit_jump,
            LIRBranch: self._emit_branch,
            LIRLabel: self._emit_label,
            LIRPanic: self._emit_panic,
            LIRLoadReg: self._emit_load_reg,
            LIRStoreReg: self._emit_store_reg,
            LIRBuildList: self._emit_build_list,
            LIRListAppend: self._emit_list_append,
            LIRBuildTuple: self._emit_build_tuple,
            LIRBuildMap: self._emit_build_map,
            LIRBuildADT: self._emit_build_adt,
            LIRFieldAccess: self._emit_field_access,
            LIRIndex: self._emit_index,
            LIRClosureCreate: self._emit_closure_create,
            LIRSwitch: self._emit_switch,
        }

    def _emit_load_const(self, instr, ctx: "_EmitContext"):
        """编译常量加载指令（int/float/bool/string）。"""
        e = ctx.e
        is_float = instr.const_type == "float"
        dst_name = (instr.dst_loc[0] if instr.dst_loc
                    else f"fconst_{instr.value}" if is_float
                    else f"const_{instr.value}")
        dst_loc = ctx.get_loc(dst_name)

        if instr.const_type == "int":
            if dst_loc[0] == "reg":
                e.mov_reg_imm64(dst_loc[1], int(instr.value))
            else:
                e.mov_reg_imm64(RAX, int(instr.value))
                e.mov_mem_reg(RSP, dst_loc[1], RAX)
        elif instr.const_type == "float":
            target = dst_loc[1] if dst_loc[0] == "reg" else XMM0
            fixup_offset = e.movsd_reg_imm(target, 0)
            if dst_loc[0] == "stack":
                e.movsd_mem_reg(RSP, dst_loc[1], XMM0)
            data_off = self._float_const_map.get(str(instr.value))
            if data_off is not None:
                self.data_fixups.append(
                    (ctx.func_name, fixup_offset, data_off, "float")
                )
        elif instr.const_type == "bool":
            val = 1 if instr.value else 0
            if dst_loc[0] == "reg":
                e.mov_reg_imm64(dst_loc[1], val)
            else:
                e.mov_reg_imm64(RAX, val)
                e.mov_mem_reg(RSP, dst_loc[1], RAX)
        elif instr.const_type == "string":
            target = dst_loc[1] if dst_loc[0] == "reg" else RAX
            fixup_offset = e.lea_reg_rip(target, 0)
            if dst_loc[0] == "stack":
                e.mov_mem_reg(RSP, dst_loc[1], RAX)
            data_off = self._string_const_map.get(instr.value)
            if data_off is not None:
                self.data_fixups.append(
                    (ctx.func_name, fixup_offset, data_off, "string")
                )

    def _emit_binop(self, instr, ctx: "_EmitContext"):
        """编译二元运算指令（算术/比较）。"""
        e = ctx.e
        op = instr.op
        src_locs = instr.src_locs
        dst_loc = instr.dst_loc
        if len(src_locs) < 2:
            return

        left_name, left_type = src_locs[0]
        right_name, right_type = src_locs[1]
        is_float = left_type.kind == IRType.FLOAT

        if op in ("/", "%"):
            self._emit_div_mod(op, left_name, right_name, is_float, dst_loc, ctx)
        elif op in ("+", "-", "*"):
            self._emit_arithmetic(op, left_name, right_name, is_float, dst_loc, ctx)
        elif op in ("==", "!=", "<", ">", "<=", ">="):
            self._emit_comparison(op, left_name, right_name, is_float, dst_loc, ctx)

    def _emit_div_mod(self, op, left_name, right_name, is_float, dst_loc, ctx):
        """编译除法/取模指令。"""
        e = ctx.e
        if is_float:
            ctx.load_to_reg(left_name, XMM0, is_float=True)
            ctx.load_to_reg(right_name, XMM1, is_float=True)
            e.divsd_reg_reg(XMM0, XMM1)
            if dst_loc:
                ctx.store_from_reg(dst_loc[0], XMM0, is_float=True)
        else:
            ctx.load_to_reg(left_name, RAX)
            ctx.load_to_reg(right_name, RCX)
            e.cqo()
            e.idiv_reg(RCX)
            if op == "%":
                e.mov_reg_reg64(RAX, RDX)
            if dst_loc:
                ctx.store_from_reg(dst_loc[0], RAX)

    def _emit_arithmetic(self, op, left_name, right_name, is_float, dst_loc, ctx):
        """编译算术运算（加/减/乘）。"""
        e = ctx.e
        if is_float:
            ctx.load_to_reg(left_name, XMM0, is_float=True)
            ctx.load_to_reg(right_name, XMM1, is_float=True)
            op_map = {"+": e.addsd_reg_reg, "-": e.subsd_reg_reg, "*": e.mulsd_reg_reg}
            op_map[op](XMM0, XMM1)
            if dst_loc:
                ctx.store_from_reg(dst_loc[0], XMM0, is_float=True)
        else:
            ctx.load_to_reg(left_name, RAX)
            ctx.load_to_reg(right_name, RCX)
            op_map = {"+": e.add_reg_reg, "-": e.sub_reg_reg, "*": e.imul_reg_reg}
            op_map[op](RAX, RCX)
            if dst_loc:
                ctx.store_from_reg(dst_loc[0], RAX)

    def _emit_comparison(self, op, left_name, right_name, is_float, dst_loc, ctx):
        """编译比较运算（==, !=, <, >, <=, >=）。"""
        e = ctx.e
        if is_float:
            ctx.load_to_reg(left_name, XMM0, is_float=True)
            ctx.load_to_reg(right_name, XMM1, is_float=True)
            e.ucomisd(XMM0, XMM1)
        else:
            ctx.load_to_reg(left_name, RAX)
            ctx.load_to_reg(right_name, RCX)
            e.cmp_reg_reg(RAX, RCX)

        # 比较结果设置
        cc_map = {
            "==": e.sete, "!=": e.setne,
            "<": e.setl, ">": e.setg,
            "<=": e.setle, ">=": e.setge,
        }
        cc_map[op](RAX)
        e.movzx_reg32_reg8(RAX, RAX)
        if dst_loc:
            ctx.store_from_reg(dst_loc[0], RAX)

    def _emit_unary_op(self, instr, ctx: "_EmitContext"):
        """编译一元运算指令（取负/逻辑非）。"""
        e = ctx.e
        if not instr.src_locs or not instr.dst_loc:
            return
        src_name, src_type = instr.src_locs[0]
        dst_name = instr.dst_loc[0]
        is_float = src_type.kind == IRType.FLOAT

        if instr.op == "-":
            if is_float:
                ctx.load_to_reg(src_name, XMM0, is_float=True)
                e.xorpd_xmm(XMM1)
                e.subsd_reg_reg(XMM1, XMM0)
                ctx.store_from_reg(dst_name, XMM1, is_float=True)
            else:
                ctx.load_to_reg(src_name, RAX)
                e.neg_reg(RAX)
                ctx.store_from_reg(dst_name, RAX)
        elif instr.op == "!":
            ctx.load_to_reg(src_name, RAX)
            e.cmp_reg_imm(RAX, 0)
            e.sete(RAX)
            e.movzx_reg32_reg8(RAX, RAX)
            ctx.store_from_reg(dst_name, RAX)

    def _emit_call(self, instr, ctx: "_EmitContext"):
        """编译函数调用指令，实现 System V AMD64 ABI 调用约定。

        包含：
        - 整数参数传递：RDI, RSI, RDX, RCX, R8, R9（前6个），其余栈传
        - 浮点参数传递：XMM0-XMM7（前8个），其余栈传
        - 返回值捕获：RAX（整数）/ XMM0（浮点）
        - caller-saved GPR 保存/恢复（保守方案）
        - 调用前 16 字节栈对齐
        """
        e = ctx.e
        INT_ARG_REGS = [RDI, RSI, RDX, RCX, R8, R9]
        FLOAT_ARG_REGS = [XMM0, XMM1, XMM2, XMM3, XMM4, XMM5, XMM6, XMM7]
        CALLER_GPRS = [RCX, RDX, RSI, RDI, R8, R9, R10, R11]

        has_return = instr.dst_loc is not None

        # 判断返回值目标是否在 caller-saved 中或是否为浮点
        dst_in_caller_saved = False
        dst_is_float = False
        if has_return:
            dst_name, dst_type = instr.dst_loc
            dst_loc = ctx.get_loc(dst_name)
            dst_in_caller_saved = dst_loc[0] == "reg" and dst_loc[1] in CALLER_GPRS
            dst_is_float = dst_type.kind == IRType.FLOAT

        # 1. 为返回值预留栈槽（如果目标在 caller-saved 中或浮点）
        need_retval_slot = has_return and (dst_in_caller_saved or dst_is_float)
        if need_retval_slot:
            e.sub_rsp_imm(8)

        # 2. 保存 caller-saved GPR（保守方案，确保 call 后活跃值不被破坏）
        for reg in CALLER_GPRS:
            e.push_reg(reg)

        # 3. 搬移参数到 ABI 寄存器/栈
        int_idx = 0
        float_idx = 0
        stack_args = []  # [(vreg_name, is_float), ...]

        for arg_vname, arg_type in instr.arg_locs:
            is_float = arg_type.kind == IRType.FLOAT
            if is_float:
                if float_idx < len(FLOAT_ARG_REGS):
                    ctx.load_to_reg(arg_vname, FLOAT_ARG_REGS[float_idx], is_float=True)
                    float_idx += 1
                else:
                    stack_args.append((arg_vname, True))
            else:
                if int_idx < len(INT_ARG_REGS):
                    ctx.load_to_reg(arg_vname, INT_ARG_REGS[int_idx], is_float=False)
                    int_idx += 1
                else:
                    stack_args.append((arg_vname, False))

        # 4. 栈对齐：System V ABI 要求 call 前 RSP ≡ 0 (mod 16)
        # 当前已调整：retval_slot(8) + caller_saved(64) + stack_args(8*n)
        # 需要总调整量 ≡ 0 (mod 16)，即 retval? + n ≡ 0 (mod 2)
        retval_bit = 1 if need_retval_slot else 0
        needs_align = (retval_bit + len(stack_args)) % 2 == 1
        if needs_align:
            e.sub_rsp_imm(8)

        # 5. 栈参数从右到左压栈
        for arg_vname, is_float in reversed(stack_args):
            ctx.load_to_reg(arg_vname, RAX, is_float=is_float)
            e.push_reg(RAX)

        # 6. 发射 call
        call_offset = e.call_rel32()
        self.link_calls.append((ctx.func_name, call_offset, instr.func_name))

        # 7. 清理栈参数
        if stack_args:
            e.add_rsp_imm(len(stack_args) * 8)
        if needs_align:
            e.add_rsp_imm(8)

        # 8. 保存返回值到预留槽（如果需要）
        if has_return:
            if need_retval_slot:
                if dst_is_float:
                    e.movsd_mem_reg(RSP, 64, XMM0)
                else:
                    e.mov_mem_reg(RSP, 64, RAX)
            else:
                # 目标在栈或 callee-saved 中，直接存储
                ctx.store_from_reg(dst_name, RAX, is_float=False)

        # 9. 恢复 caller-saved GPR
        for reg in reversed(CALLER_GPRS):
            e.pop_reg(reg)

        # 10. 从预留槽加载返回值并清理
        if need_retval_slot:
            if dst_is_float:
                e.movsd_reg_mem(XMM0, RSP, 0)
                ctx.store_from_reg(dst_name, XMM0, is_float=True)
            else:
                e.mov_reg_mem(RAX, RSP, 0)
                ctx.store_from_reg(dst_name, RAX, is_float=False)
            e.add_rsp_imm(8)

    def _emit_return(self, instr, ctx: "_EmitContext"):
        """编译返回指令（加载返回值到 RAX/XMM0，ret 在函数尾声处理）。"""
        if instr.src_locs:
            src_name, src_type = instr.src_locs[0]
            is_float = src_type.kind == IRType.FLOAT
            if is_float:
                ctx.load_to_reg(src_name, XMM0, is_float=True)
            else:
                ctx.load_to_reg(src_name, RAX)

    def _emit_jump(self, instr, ctx: "_EmitContext"):
        """编译无条件跳转指令。"""
        jmp_offset = ctx.e.jmp_rel32()
        ctx.jump_fixups.append((jmp_offset, instr.target, "jmp"))

    def _emit_branch(self, instr, ctx: "_EmitContext"):
        """编译条件跳转指令（true 分支 jne，false 分支 jmp）。"""
        e = ctx.e
        if instr.src_locs:
            ctx.load_to_reg(instr.src_locs[0][0], RAX)
        e.test_reg_reg(RAX, RAX)
        jne_offset = e.jne_rel32()
        ctx.jump_fixups.append((jne_offset, instr.true_target, "jcc"))
        jmp_offset = e.jmp_rel32()
        ctx.jump_fixups.append((jmp_offset, instr.false_target, "jmp"))

    def _emit_label(self, instr, ctx: "_EmitContext"):
        """记录标签的当前代码偏移位置。"""
        ctx.label_offsets[instr.name] = ctx.e.current_offset()

    def _emit_panic(self, instr, ctx: "_EmitContext"):
        """编译 panic 指令（调用 exit(1)）。"""
        e = ctx.e
        e.mov_reg_imm64(RDI, 1)
        e.mov_reg_imm64(RAX, 60)  # syscall: exit
        e.syscall()

    # ============================================================
    # 阶段 B.2: 寄存器传送指令（Phi 降级、变量拷贝）
    # ============================================================

    def _emit_load_reg(self, instr, ctx: "_EmitContext"):
        """编译寄存器间传送指令（Phi 降级后的值拷贝）。

        src_locs[0] -> dst_loc 的 mov 操作。
        这是 SSA Phi 节点降级为线性指令序列的关键指令。
        """
        if not instr.src_locs or not instr.dst_loc:
            return
        src_name, src_type = instr.src_locs[0]
        dst_name, dst_type = instr.dst_loc
        is_float = src_type.kind == IRType.FLOAT

        src_loc = ctx.get_loc(src_name)
        dst_loc = ctx.get_loc(dst_name)

        if dst_loc[0] == "reg":
            if src_loc[0] == "reg":
                # 寄存器 -> 寄存器
                if is_float:
                    ctx.e.movsd_reg_reg(dst_loc[1], src_loc[1])
                else:
                    ctx.e.mov_reg_reg64(dst_loc[1], src_loc[1])
            else:
                # 栈 -> 寄存器
                if is_float:
                    ctx.e.movsd_reg_mem(dst_loc[1], RSP, src_loc[1])
                else:
                    ctx.e.mov_reg_mem(dst_loc[1], RSP, src_loc[1])
        elif dst_loc[0] == "stack":
            if src_loc[0] == "reg":
                # 寄存器 -> 栈
                if is_float:
                    ctx.e.movsd_mem_reg(RSP, dst_loc[1], src_loc[1])
                else:
                    ctx.e.mov_mem_reg(RSP, dst_loc[1], src_loc[1])
            else:
                # 栈 -> 栈（通过寄存器中转）
                if is_float:
                    ctx.e.movsd_reg_mem(XMM0, RSP, src_loc[1])
                    ctx.e.movsd_mem_reg(RSP, dst_loc[1], XMM0)
                else:
                    ctx.e.mov_reg_mem(RAX, RSP, src_loc[1])
                    ctx.e.mov_mem_reg(RSP, dst_loc[1], RAX)

    def _emit_store_reg(self, instr, ctx: "_EmitContext"):
        """编译寄存器存储指令（与 LIRLoadReg 对称，确保 dst_loc 被写入）。"""
        if not instr.src_locs or not instr.dst_loc:
            return
        # 逻辑与 _emit_load_reg 相同：src_locs[0] -> dst_loc
        self._emit_load_reg(instr, ctx)

    # ============================================================
    # 阶段 B.3: 复合数据结构指令（调用运行时函数）
    # ============================================================

    def _emit_runtime_call(
        self, func_name: str, args: list, dst_loc_info, ctx: "_EmitContext"
    ):
        """通用运行时函数调用发射器。

        通过 System V ABI 调用外部运行时函数（nova_list_new 等）。
        调用链路：保存 caller-saved -> 设置参数 -> call -> 恢复 -> 取返回值。
        外部函数的 call rel32 在链接阶段暂不回填（保持 0 偏移）。

        参数格式：
          - 变量参数: (vreg_name, arg_type)
          - 立即数参数: (("imm", value), arg_type)
        """
        e = ctx.e
        has_return = dst_loc_info is not None
        dst_name, dst_type = dst_loc_info if has_return else (None, None)
        dst_in_caller_saved = False
        dst_is_float = False
        if has_return:
            dst_loc = ctx.get_loc(dst_name)
            dst_in_caller_saved = dst_loc[0] == "reg" and dst_loc[1] in CALLER_GPRS
            dst_is_float = dst_type.kind == IRType.FLOAT

        # 1. 预留返回值栈槽
        need_retval_slot = has_return and (dst_in_caller_saved or dst_is_float)
        if need_retval_slot:
            e.sub_rsp_imm(8)

        # 2. 保存 caller-saved GPR
        for reg in CALLER_GPRS:
            e.push_reg(reg)

        # 3. 设置参数（支持变量和立即数混合）
        int_idx = 0
        float_idx = 0
        stack_var_args = []  # 变量溢出参数（从右到左压栈）
        stack_arg_count = 0  # 总溢出参数数（含立即数）
        for arg_spec, arg_type in args:
            is_float = arg_type.kind == IRType.FLOAT
            if isinstance(arg_spec, tuple) and arg_spec[0] == "imm":
                imm_val = arg_spec[1]
                if is_float:
                    # 浮点立即数暂不支持（需要加载到临时内存再 movsd）
                    raise NotImplementedError("浮点立即数参数暂不支持")
                if int_idx < len(INT_ARG_REGS):
                    e.mov_reg_imm64(INT_ARG_REGS[int_idx], imm_val)
                    int_idx += 1
                else:
                    e.mov_reg_imm64(RAX, imm_val)
                    e.push_reg(RAX)
                    stack_arg_count += 1
            else:
                arg_vname = arg_spec
                if is_float:
                    if float_idx < len(FLOAT_ARG_REGS):
                        ctx.load_to_reg(arg_vname, FLOAT_ARG_REGS[float_idx], is_float=True)
                        float_idx += 1
                    else:
                        stack_var_args.append((arg_vname, True))
                        stack_arg_count += 1
                else:
                    if int_idx < len(INT_ARG_REGS):
                        ctx.load_to_reg(arg_vname, INT_ARG_REGS[int_idx], is_float=False)
                        int_idx += 1
                    else:
                        stack_var_args.append((arg_vname, False))
                        stack_arg_count += 1

        # 4. 栈对齐
        retval_bit = 1 if need_retval_slot else 0
        needs_align = (retval_bit + stack_arg_count) % 2 == 1
        if needs_align:
            e.sub_rsp_imm(8)

        # 5. 变量栈参数压栈（从右到左）
        for arg_vname, is_float in reversed(stack_var_args):
            ctx.load_to_reg(arg_vname, RAX, is_float=is_float)
            e.push_reg(RAX)

        # 6. 发射 call（外部函数，暂用 0 偏移）
        call_offset = e.call_rel32()
        self.external_calls.append((ctx.func_name, call_offset, func_name))

        # 7. 清理栈参数和对齐
        if stack_arg_count > 0:
            e.add_rsp_imm(stack_arg_count * 8)
        if needs_align:
            e.add_rsp_imm(8)

        # 8. 保存返回值
        if has_return:
            if need_retval_slot:
                if dst_is_float:
                    e.movsd_mem_reg(RSP, 64, XMM0)
                else:
                    e.mov_mem_reg(RSP, 64, RAX)
            else:
                ctx.store_from_reg(dst_name, RAX, is_float=False)

        # 9. 恢复 caller-saved GPR
        for reg in reversed(CALLER_GPRS):
            e.pop_reg(reg)

        # 10. 加载预留的返回值
        if need_retval_slot:
            if dst_is_float:
                e.movsd_reg_mem(XMM0, RSP, 0)
                ctx.store_from_reg(dst_name, XMM0, is_float=True)
            else:
                e.mov_reg_mem(RAX, RSP, 0)
                ctx.store_from_reg(dst_name, RAX, is_float=False)
            e.add_rsp_imm(8)

    def _emit_build_list(self, instr, ctx: "_EmitContext"):
        """编译列表构建：调用 nova_list_new(count)，然后 nova_list_push 逐个添加元素。"""
        dst_info = instr.dst_loc if instr.dst_loc else None

        # 先调用 nova_list_new(count)
        self._emit_runtime_call(
            "nova_list_new",
            [(("imm", instr.count), IRType.int_type())],
            dst_info,
            ctx,
        )

        # 循环 nova_list_push(list, elem)
        for i, (elem_loc, elem_type) in enumerate(instr.src_locs):
            if dst_info:
                self._emit_runtime_call(
                    "nova_list_push",
                    [dst_info, (elem_loc, elem_type)],
                    None,
                    ctx,
                )

    def _emit_list_append(self, instr, ctx: "_EmitContext"):
        """编译列表追加：调用 nova_list_push(list, elem)。"""
        if not instr.src_locs or len(instr.src_locs) < 2:
            return
        self._emit_runtime_call(
            "nova_list_push",
            [instr.src_locs[0], instr.src_locs[1]],
            instr.dst_loc,
            ctx,
        )

    def _emit_build_tuple(self, instr, ctx: "_EmitContext"):
        """编译元组构建：调用 nova_alloc(size)，然后逐字段填充。"""
        e = ctx.e
        NOVA_VALUE_SIZE = 8
        size = instr.count * NOVA_VALUE_SIZE
        dst_info = instr.dst_loc if instr.dst_loc else None

        # 调用 nova_alloc(size)
        e.push_reg(RDI)
        e.mov_reg_imm64(RDI, size)
        call_offset = e.call_rel32()
        self.external_calls.append((ctx.func_name, call_offset, "nova_alloc"))
        e.pop_reg(RDI)

        # 保存指针
        if dst_info:
            dst_name, _ = dst_info
            ctx.store_from_reg(dst_name, RAX)

        # 逐字段填充（元素值写入指针+offset）
        for i, (elem_loc, elem_type) in enumerate(instr.src_locs):
            byte_offset = i * NOVA_VALUE_SIZE
            is_float = elem_type.kind == IRType.FLOAT
            # 加载元素到临时寄存器
            ctx.load_to_reg(elem_loc, RCX, is_float=is_float)
            # 加载基址到 RAX
            if dst_info:
                base_l = ctx.get_loc(dst_info[0])
                if base_l[0] == "reg":
                    e.mov_reg_reg64(RAX, base_l[1])
                else:
                    e.mov_reg_mem(RAX, RSP, base_l[1])
            # 存储到 [base + offset]
            if is_float:
                e.movsd_mem_reg(RSP, -(i * 8 + 8), XMM0)  # 用临时栈做中转
                e.mov_reg_imm64(RDX, byte_offset)
                e.add_reg_reg(RAX, RDX)
                e.movsd_reg_mem(XMM0, RAX, 0)
            else:
                e.mov_mem_reg(RSP, -(i * 8 + 8), RCX)
                e.mov_reg_imm64(RDX, byte_offset)
                e.add_reg_reg(RAX, RDX)
                e.mov_reg_mem(RAX, 0, RCX)

    def _emit_build_map(self, instr, ctx: "_EmitContext"):
        """编译 Map 构建：调用 nova_map_new(entry_count)，然后逐对 nova_map_put。"""
        dst_info = instr.dst_loc if instr.dst_loc else None

        # 调用 nova_map_new(entry_count)
        self._emit_runtime_call(
            "nova_map_new",
            [(("imm", instr.entry_count), IRType.int_type())],
            dst_info,
            ctx,
        )

        # 循环 nova_map_put(map, key, value)
        for i in range(instr.entry_count):
            key_idx = i * 2
            val_idx = i * 2 + 1
            if key_idx < len(instr.src_locs) and val_idx < len(instr.src_locs):
                if dst_info:
                    self._emit_runtime_call(
                        "nova_map_put",
                        [
                            dst_info,
                            instr.src_locs[key_idx],
                            instr.src_locs[val_idx],
                        ],
                        None,
                        ctx,
                    )

    def _emit_build_adt(self, instr, ctx: "_EmitContext"):
        """编译 ADT 构建：调用 nova_adt_new(type_id, variant_tag, field_count)，然后填充字段。"""
        dst_info = instr.dst_loc if instr.dst_loc else None
        int_ty = IRType.int_type()

        # 调用 nova_adt_new(type_id, variant_tag, field_count)
        self._emit_runtime_call(
            "nova_adt_new",
            [
                (("imm", instr.type_tag), int_ty),
                (("imm", instr.type_tag), int_ty),
                (("imm", instr.field_count), int_ty),
            ],
            dst_info,
            ctx,
        )

        # 逐字段填充 nova_adt_set_field(adt, idx, value)
        for i, (field_loc, field_type) in enumerate(instr.src_locs):
            if dst_info:
                self._emit_runtime_call(
                    "nova_adt_set_field",
                    [
                        dst_info,
                        (("imm", i), int_ty),
                        (field_loc, field_type),
                    ],
                    None,
                    ctx,
                )

    def _emit_field_access(self, instr, ctx: "_EmitContext"):
        """编译字段访问：从基址+offset 加载值。

        offset 是字段索引，每个字段 8 字节（NovaValue 大小）。
        生成 base + offset 地址计算 + 内存加载。
        """
        if not instr.src_locs or not instr.dst_loc:
            return
        e = ctx.e
        src_name, src_type = instr.src_locs[0]
        dst_name, dst_type = instr.dst_loc
        NOVA_VALUE_SIZE = 8
        byte_offset = instr.offset * NOVA_VALUE_SIZE
        is_float = dst_type.kind == IRType.FLOAT

        # 加载基址到 RAX
        src_loc = ctx.get_loc(src_name)
        if src_loc[0] == "reg":
            e.mov_reg_reg64(RAX, src_loc[1])
        else:
            e.mov_reg_mem(RAX, RSP, src_loc[1])

        # 计算目标地址 RAX = base + byte_offset
        e.mov_reg_imm64(RDX, byte_offset)
        e.add_reg_reg(RAX, RDX)

        # 从 [RAX] 加载到目标
        if is_float:
            e.movsd_reg_mem(XMM0, RAX, 0)
            ctx.store_from_reg(dst_name, XMM0, is_float=True)
        else:
            e.mov_reg_mem(RAX, 0, RAX)  # mov RAX, [RAX]
            ctx.store_from_reg(dst_name, RAX)

    def _emit_index(self, instr, ctx: "_EmitContext"):
        """编译索引访问：调用 nova_list_get(list, index)。"""
        if not instr.src_locs or len(instr.src_locs) < 2 or not instr.dst_loc:
            return
        self._emit_runtime_call(
            "nova_list_get",
            [instr.src_locs[0], instr.src_locs[1]],
            instr.dst_loc,
            ctx,
        )

    def _emit_closure_create(self, instr, ctx: "_EmitContext"):
        """编译闭包创建（占位实现）。

        当前原生后端暂不支持完整的闭包运行时，
        生成零值占位，与 Wasm 后端行为一致。
        TODO: 接入 nova_closure_new 运行时函数。
        """
        if not instr.dst_loc:
            return
        dst_name, _ = instr.dst_loc
        ctx.store_from_reg(dst_name, RAX)

    def _emit_call_indirect(self, instr, ctx: "_EmitContext"):
        """编译间接调用（闭包/函数指针调用，占位实现）。

        当前原生后端暂不支持间接调用机制，
        需要运行时提供闭包 vtable 才能完成。
        TODO: 实现闭包对象解包 + 函数指针间接调用。
        """
        pass

    def _emit_switch(self, instr, ctx: "_EmitContext"):
        """编译 switch 多分支跳转。

        先加载条件值到 RAX，然后逐一比较并条件跳转。
        最后 fall through 到 default 分支。
        """
        e = ctx.e
        if instr.src_locs:
            ctx.load_to_reg(instr.src_locs[0][0], RAX)

        # 逐一比较 case 值并条件跳转
        for value, target in instr.cases:
            e.mov_reg_imm64(RDX, value)
            e.cmp_reg_reg(RAX, RDX)
            je_offset = e.je_rel32()
            ctx.jump_fixups.append((je_offset, target, "jcc"))

        # fall through 到 default 分支
        if instr.default_target:
            jmp_offset = e.jmp_rel32()
            ctx.jump_fixups.append((jmp_offset, instr.default_target, "jmp"))

    # ============================================================
    # 阶段 B: 跳转偏移回填
    # ============================================================

    def _fixup_jumps(self, ctx: "_EmitContext"):
        """回填所有跳转指令的 rel32 偏移量。"""
        for fixup_offset, target_label, _kind in ctx.jump_fixups:
            if target_label in ctx.label_offsets:
                target_offset = ctx.label_offsets[target_label]
                ctx.e.patch_rel32(fixup_offset, target_offset)

    def _generate_start(self, func_code: Dict[str, bytes], module: LIRModule):
        """生成 _start 入口函数。

        Linux 内核进入 _start 时 RSP 已 16 字节对齐（≡ 0 mod 16）。
        call 指令压入 8B 返回地址后，被调用函数看到 RSP ≡ 8 (mod 16)，
        符合 System V ABI 要求。因此直接 call 即可，无需额外对齐。
        """
        e = X86_64Emitter()

        # 设置参数：argc 在 [RSP], argv 在 [RSP+8]
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
            phnum=2,  # LOAD(code) + LOAD(data)
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
