"""
Nova 自研原生代码生成后端
将 LIR 直接编译为 x86_64 机器码 + ELF 可执行文件

零外部依赖用于独立 ELF 生成。
生成目标文件时（output_format="obj"）可选支持 gcc 链接。
"""

import os
import subprocess
import struct
import shutil
import tempfile
from typing import Dict, List, Optional

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
    RBP,
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
    LIRLoadGlobal,
    LIRLoadReg,
    LIRModule,
    LIRPanic,
    LIRReturn,
    LIRStoreGlobal,
    LIRStoreReg,
    LIRSwitch,
    LIRUnaryOp,
)

# ============================================================
# System V AMD64 ABI 调用约定常量
# ============================================================

# 整数参数寄存器（前 6 个参数通过寄存器传递）
INT_ARG_REGS = [RDI, RSI, RDX, RCX, R8, R9]

# 浮点参数寄存器（前 8 个参数通过寄存器传递）
FLOAT_ARG_REGS = [XMM0, XMM1, XMM2, XMM3, XMM4, XMM5, XMM6, XMM7]

# caller-saved GPR（需要在调用前保存/调用后恢复）
CALLER_GPRS = [RCX, RDX, RSI, RDI, R8, R9, R10, R11]

# P1-1 修复：System V AMD64 ABI 规定 XMM0-XMM7 均为 caller-saved
# （被调用者可自由破坏）。此前仅保存 GPR，浮点 vreg 分配到 XMM0-7 后
# 跨 call 不保存 → 值被覆盖 → 随机浮点结果错误。
# 每个 XMM 用 movsd 保存 8 字节（标量 double 精度足够；Nova 当前
# 不使用 packed SSE，故 movsd 8 字节/寄存器足够，不需要 16 字节 movups）。
CALLER_XMMS = [XMM0, XMM1, XMM2, XMM3, XMM4, XMM5, XMM6, XMM7]
XMM_SAVE_BYTES = len(CALLER_XMMS) * 8  # = 64

# 寄存器分配器可用物理寄存器池（CC 拆分 Top1：从 _allocate_registers 方法内提升为模块级）
# GPR: 前 8 个 caller-saved + 后 5 个 callee-saved = 共 13 个通用寄存器
# XMM: 8 个标量双精度浮点寄存器（movsd 8 字节）
_ALLOC_GPRS = [RCX, RDX, RSI, RDI, R8, R9, R10, R11,   # caller-saved
               RBX, R12, R13, R14, R15]                 # callee-saved
_ALLOC_XMMS = [XMM0, XMM1, XMM2, XMM3, XMM4, XMM5, XMM6, XMM7]

# ============================================================
# RegAlloc v2 专用常量（Cycle 70 backend_native_regalloc_linear_scan_v2）
# ============================================================
# v2 双池拆分：_ALLOC_GPRS 切为 caller/callee 两个独立 free 池，
# 分配时按 has_call_in_range 启发式选池，减少无谓保存/恢复。
# 注：_ALLOC_GPRS 的 slice 与定义顺序严格对应（前 8=caller，后 5=callee）。
_ALLOC_CALLER_GPRS = _ALLOC_GPRS[:8]  # RCX, RDX, RSI, RDI, R8, R9, R10, R11
_ALLOC_CALLEE_GPRS = _ALLOC_GPRS[8:]  # RBX, R12, R13, R14, R15
# CALLEE_SAVED 列表（x86_64.py L25）中 RBX/R12-R15 共 5 个参与分配；
# RBP 被预留（用于未来 RBP 基址帧模式），不在 v2 分配池内。

# ============================================================
# 指令发射上下文（传递寄存器分配结果和汇编状态）
# ============================================================


class _EmitContext:
    """封装指令发射阶段的上下文：发射器、函数名、寄存器分配、跳转/标签信息。

    v2 RBP 帧模式：新增 frame_base_reg + frame_stack_bias 两个成员。
    RBP 模式下栈槽寻址公式：[frame_base_reg + frame_stack_bias + stack_offset]
      = [RBP - (push_RBP(8)+push_5callee(40)+aligned_sub) + stack_offset]
      等价于纯 RSP 模式的 [RSP + stack_offset]（prologue 末尾 RSP 位置对齐）。
    """

    def __init__(self, e, func_name, vreg_alloc, label_offsets, jump_fixups,
                 frame_base_reg=RSP, frame_stack_bias: int = 0):
        self.e = e
        self.func_name = func_name
        self.vreg_alloc = vreg_alloc
        self.label_offsets = label_offsets
        self.jump_fixups = jump_fixups
        self.frame_base_reg = frame_base_reg
        self.frame_stack_bias = frame_stack_bias

    def get_loc(self, vreg_name):
        """获取虚拟寄存器的物理位置：("reg", phys_reg) 或 ("stack", offset)"""
        if vreg_name in self.vreg_alloc:
            return self.vreg_alloc[vreg_name]
        raise ValueError(
            f"寄存器分配错误：虚拟寄存器 '{vreg_name}' 未找到分配记录。"
            f"已分配的 vreg: {list(self.vreg_alloc.keys())[:10]}..."
        )

    def load_to_reg(self, vreg_name, target_reg, is_float=False):
        """将 vreg 的值加载到目标物理寄存器（RBP/RSP 帧模式透明切换）。"""
        loc = self.get_loc(vreg_name)
        if loc[0] == "reg":
            if loc[1] != target_reg:
                if is_float:
                    self.e.movsd_reg_reg(target_reg, loc[1])
                else:
                    self.e.mov_reg_reg64(target_reg, loc[1])
        else:
            eff_offset = self.frame_stack_bias + loc[1]
            if is_float:
                self.e.movsd_reg_mem(target_reg, self.frame_base_reg, eff_offset)
            else:
                self.e.mov_reg_mem(target_reg, self.frame_base_reg, eff_offset)

    def store_from_reg(self, vreg_name, source_reg, is_float=False):
        """将源物理寄存器的值存储到 vreg 的位置（RBP/RSP 帧模式透明切换）。"""
        loc = self.get_loc(vreg_name)
        if loc[0] == "reg":
            if loc[1] != source_reg:
                if is_float:
                    self.e.movsd_reg_reg(loc[1], source_reg)
                else:
                    self.e.mov_reg_reg64(loc[1], source_reg)
        else:
            eff_offset = self.frame_stack_bias + loc[1]
            if is_float:
                self.e.movsd_mem_reg(self.frame_base_reg, eff_offset, source_reg)
            else:
                self.e.mov_mem_reg(self.frame_base_reg, eff_offset, source_reg)


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
        self.closure_fn_ptr_fixups = []  # [(caller_func_name, code_offset_in_func, lambda_name)]
        self.trampoline_code = {}  # lambda_name -> trampoline machine code bytes
        # 常量值 -> 数据段偏移的映射（用于快速查找）
        self._float_const_map = {}  # value_str -> data_offset
        self._string_const_map = {}  # value -> data_offset
        # 全局变量名 -> 数据段偏移的映射
        self._global_var_map = {}  # global_name -> data_offset

    def compile(self, lir_module: LIRModule, output_format: str = "elf") -> bytes:
        """编译 LIR Module 为二进制。

        参数:
            lir_module: 待编译的 LIR 模块。
            output_format: 输出格式，默认为 "elf"（Linux ELF 可执行文件）。
                - "elf": 生成完整的 ELF 可执行文件二进制。
                保留该参数以便后续扩展其他输出格式（如原始机器码、目标文件等）。

        返回:
            编译产物的字节串。当 output_format="elf" 时返回 ELF 二进制。
        """
        # 0. 重置编译状态
        self.link_calls = []
        self.data_fixups = []
        self.external_calls = []
        self.closure_fn_ptr_fixups = []
        self.trampoline_code = {}
        self._float_const_map = {}
        self._string_const_map = {}
        self._global_var_map = {}

        # 1. 收集所有字符串和浮点常量
        self._collect_constants(lir_module)

        # 2. 为每个函数生成机器码
        func_code = {}
        for name, func in lir_module.functions.items():
            func_code[name] = self._compile_function(func)

        # 2.5 为每个 lambda 函数生成 trampoline
        for name, func in lir_module.functions.items():
            if self._is_lambda_name(name):
                # 从闭包创建指令中获取 capture_count
                capture_count = self._find_capture_count(func, lir_module)
                tramp_code = self._generate_trampoline(func, capture_count)
                self.trampoline_code[name] = tramp_code

        # 3. 生成 _start 入口
        start_code = self._generate_start(func_code, lir_module)

        # 4. 组装输出
        if output_format == "elf":
            return self._generate_elf(func_code, start_code, lir_module)
        elif output_format == "obj":
            return self._generate_relocatable_elf(func_code, start_code, lir_module)

        raise ValueError(
            f"不支持的输出格式: {output_format!r}（支持 'elf' 和 'obj'）"
        )

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

        # 收集全局变量：每个全局变量在数据段分配 8 字节（i64 宽度，足以存储所有类型）
        for func in module.functions.values():
            for instr in func.body:
                if isinstance(instr, LIRLoadGlobal) or isinstance(instr, LIRStoreGlobal):
                    name = instr.global_name
                    if name and name not in self._global_var_map:
                        # 8 字节初始化为 0
                        self._global_var_map[name] = offset
                        self.string_constants.append((b"\x00" * 8, offset))
                        offset += 8

    def _is_lambda_name(self, name: str) -> bool:
        """判断函数名是否为 lambda 函数（__lambda_ 前缀）"""
        return name.startswith("__lambda_")

    def _find_capture_count(self, func: LIRFunction, module: LIRModule) -> int:
        """在整个 module 中查找创建指定 lambda 闭包的指令，获取 capture_count。

        遍历所有函数的所有指令，找到 LIRClosureCreate 且 fn_name 匹配的。
        找不到则返回 0。
        """
        for fn in module.functions.values():
            for instr in fn.body:
                if isinstance(instr, LIRClosureCreate):
                    if instr.fn_name == func.name:
                        return instr.capture_count
        return 0

    def _generate_trampoline(self, func: LIRFunction, capture_count: int) -> bytes:
        """为 lambda 函数生成闭包调用约定的 trampoline 机器码。

        闭包调用约定（C 侧 nova_closure_call）：
            void* fn_ptr(void** captured, void** args, int32_t arg_count)
        输入寄存器（System V ABI）：RDI=captured, RSI=args, RDX=arg_count

        Trampoline 职责：
        1. 从 captured 数组解包捕获变量到参数寄存器
        2. 从 args 数组解包用户参数到后续参数寄存器/栈
        3. 调用真实的 lambda 函数
        4. 将返回值装箱为 void*（整数/指针直接返回，浮点用 movq 转位模式）
        5. 返回

        返回值约定：返回值在 RAX（整数位模式），对于浮点是 double 的位表示。
        """
        e = X86_64Emitter()
        total_params = len(func.params)
        user_param_count = total_params - capture_count

        # 保存源指针到临时寄存器（R10=captured, R11=args）
        # RDI 和 RSI 会被参数加载覆盖，所以先暂存
        e.mov_reg_reg64(R10, RDI)  # r10 = captured (void**)
        e.mov_reg_reg64(R11, RSI)  # r11 = args (void**)

        # ARG_REGS = [RDI, RSI, RDX, RCX, R8, R9] — 前 6 个整数参数寄存器
        from .x86_64 import ARG_REGS

        # 1. 加载捕获变量到参数寄存器（前 capture_count 个参数）
        for i in range(min(capture_count, len(ARG_REGS))):
            # captured[i] -> ARG_REGS[i]
            e.mov_reg_mem(ARG_REGS[i], R10, i * 8)

        # 2. 加载用户参数到后续参数寄存器
        reg_args_used = min(capture_count, len(ARG_REGS))
        remaining_regs = len(ARG_REGS) - reg_args_used
        stack_args_count = max(0, user_param_count - remaining_regs)

        for i in range(min(user_param_count, remaining_regs)):
            arg_reg_idx = capture_count + i
            # args[i] -> ARG_REGS[arg_reg_idx]
            e.mov_reg_mem(ARG_REGS[arg_reg_idx], R11, i * 8)

        # 3. 超出寄存器的参数压栈（从右往左压）
        # 注意：call 之前栈上已经有返回地址（8B），所以栈是 8 mod 16
        # 压入 N 个参数后，再 call 会再压 8B 返回地址
        # 我们需要确保 call 前 RSP 是 16 字节对齐
        if stack_args_count > 0:
            # 先对齐栈（如果需要）
            # 当前：caller 的 RSP 在 call 前是 16 对齐的
            # call 压入 8B 返回地址后，进入 trampoline 时 RSP = 8 mod 16
            # 我们还没 push 任何东西，所以当前 RSP = 8 mod 16
            # 压入 stack_args_count 个 8B 参数后：
            # RSP = 8 - stack_args_count * 8 (mod 16)
            # 然后 call lambda 会再压 8B：
            # RSP = 16 - stack_args_count * 8 (mod 16)
            # 需要 = 0 mod 16
            # 所以 stack_args_count * 8 ≡ 0 (mod 16)
            # 即 stack_args_count 为偶数时不需要额外对齐，奇数时需要 8B 对齐
            if stack_args_count % 2 == 1:
                e.sub_rsp_imm(8)  # 对齐填充

            # 从右往左压栈（最后一个参数先压）
            for i in range(stack_args_count - 1, -1, -1):
                arg_idx = remaining_regs + i  # 用户参数索引
                # 加载 args[arg_idx] 到 RAX 临时寄存器，然后压栈
                e.mov_reg_mem(RAX, R11, arg_idx * 8)
                e.push_reg(RAX)

        # 4. 调用真实 lambda 函数
        # 使用 call rel32，在 _generate_elf 中回填
        call_offset = e.call_rel32()
        # 记录：trampoline 函数本身是调用者，目标是 lambda 函数
        # 我们用特殊的名字标记 trampoline 的 call
        tramp_name = f"__trampoline_{func.name}"
        self.link_calls.append((tramp_name, call_offset, func.name))

        # 5. 返回值处理：将返回值装箱为 void*（64 位）
        # 对于整数/指针返回：RAX 已经是返回值，直接返回
        # 对于浮点返回：XMM0 中有 double，需要用 movq 转到 RAX
        # 问题：我们不知道返回类型是整数还是浮点
        # 方案：根据 func.return_type 判断
        if func.return_type and func.return_type.kind == IRType.FLOAT:
            # 浮点返回：将 XMM0 的 64 位搬移到 RAX
            e.movq_gpr_xmm(RAX, XMM0)
        # 否则：整数/指针返回，RAX 已经是正确值

        # 6. 清理栈参数（如果有）
        if stack_args_count > 0:
            pop_size = stack_args_count * 8
            if stack_args_count % 2 == 1:
                pop_size += 8  # 加上对齐填充
            e.add_rsp_imm(pop_size)

        # 7. 返回
        e.ret()

        return bytes(e.code)

    def _compile_function(self, func: LIRFunction) -> bytes:
        """编译单个函数为机器码。

        帧模式（v2 新增）：FRAME_MODE = 'rbp' 默认开启；CLI --fast-nofp 可退回 RSP-only。
        ━━━ RBP 基址帧布局（默认，调试器友好 / 参数偏移恒定）━━━
          高地址
          ├─────────────────────┤
          │ 调用者参数 7..N      │  [RBP + 16 + 0], [RBP + 16 + 8], ...
          │ 返回地址 (8B)        │  [RBP + 8]
          │ 旧 RBP (8B)          │  [RBP]  ← push RBP → mov RBP,RSP 后 RBP 指向此处
          ├─────────────────────┤
          │ RBX  callee-saved    │  [RBP - 8]
          │ R12  callee-saved    │  [RBP - 16]
          │ R13  callee-saved    │  [RBP - 24]
          │ R14  callee-saved    │  [RBP - 32]
          │ R15  callee-saved    │  [RBP - 40]
          ├─────────────────────┤  ← RBP - 40 - (stack_size+8 对齐到 16) = 最终 RSP
          │ 对齐填充 + 溢出槽区  │  栈槽 stack_offset 寻址：[RBP - 48 - aligned + stack_offset]
          低地址

        ━━━ RSP-only 帧布局（--fast-nofp，节省 2 指令 / 函数）━━━
          原布局（注释）保持不变：6 callee push → sub rsp, aligned → body → add rsp,aligned → 6 pop
        """
        e = X86_64Emitter()
        # --- 帧模式：v2 默认 'rbp'（预留 'rsp' 模式回退路径，默认走 RBP）---
        FRAME_MODE = "rbp"  # TODO: 后续从 CompilerConfig.frame_mode / CLI --fast-nofp 读取
        CALLEE_PUSHED = 8 + 5 * 8  # push RBP(8B) + 5 callee(40B) = 48B ≡ RSP 模式 6 callee(48B)
        # 计算 16 字节对齐填充（RBP/RSP 两模式 CALLEE_PUSHED=48B ≡ 8 mod 16 相同，故对齐公式一致）
        aligned = 0
        if func.stack_size > 0:
            total = func.stack_size + 8
            aligned = (total + 15) & ~15
            func._native_frame_pad = aligned - 8
        else:
            func._native_frame_pad = 0

        # --- 函数序言（Prologue）：RBP 模式 vs RSP-only 分岔 ---
        frame_stack_bias = 0  # 用于 _EmitContext 寻址
        if FRAME_MODE == "rbp":
            # (1) 标准帧指针建立序列：被 gdb/lldb/backtrace 等工具自动识别
            e.push_reg(RBP)
            e.mov_reg_reg64(RBP, RSP)
            # (2) 保存 5 个 callee-saved（RBP 已单独 push，_ALLOC_CALLEE_GPRS = RBX/R12-R15）
            for reg in _ALLOC_CALLEE_GPRS:
                e.push_reg(reg)
            # (3) 为局部变量 + 对齐填充开辟栈空间
            if aligned > 0:
                e.sub_rsp_imm(aligned)
            # 计算 RBP → 栈槽基准的偏移（负值，因为局部变量在 RBP 下方）：
            #   栈槽 stack_offset=0 对应最高地址 = RBP - 48 - aligned + 0
            frame_stack_bias = -(CALLEE_PUSHED + aligned)
            func._native_frame_mode = "rbp"
            func._native_frame_stack_bias = frame_stack_bias
        else:
            # RSP-only 回退模式（保持 v1 行为，零改动）
            for reg in CALLEE_SAVED:
                e.push_reg(reg)
            if aligned > 0:
                e.sub_rsp_imm(aligned)
            func._native_frame_mode = "rsp"
            func._native_frame_stack_bias = 0

        # --- 编译函数体 ---
        self._compile_body(e, func, func.name, frame_mode=FRAME_MODE,
                           frame_stack_bias=frame_stack_bias)

        # --- 函数尾声（Epilogue）：与 Prologue 对称 ---
        if FRAME_MODE == "rbp":
            # (1) 快速收尾：mov rsp,rbp → pop 5 callee → pop rbp → ret
            if aligned > 0:
                # leave 指令 = mov rsp,rbp + pop rbp 二合一；但 5 callee 必须在 pop rbp 之前 pop
                # 所以用显式序列：add rsp,aligned（等价 mov rsp,rsp+aligned 但这里是到 callee 顶）
                e.add_rsp_imm(aligned)
            # 反向 pop 5 callee
            for reg in reversed(_ALLOC_CALLEE_GPRS):
                e.pop_reg(reg)
            e.pop_reg(RBP)
            e.ret()
        else:
            if aligned > 0:
                total = func.stack_size + 8
                aligned_v = (total + 15) & ~15
                e.add_rsp_imm(aligned_v)
            for reg in reversed(CALLEE_SAVED):
                e.pop_reg(reg)
            e.ret()

        return bytes(e.code)

    def _compile_body(self, e: X86_64Emitter, func: LIRFunction, func_name: str,
                      frame_mode: str = "rsp", frame_stack_bias: int = 0):
        """编译函数体指令（寄存器分配 + 两阶段汇编）。

        三阶段协调器：
        1. 线性扫描寄存器分配
        2. 参数入口搬运（ABI 寄存器 → 分配位置）
        3. 发射指令（调度表分发）
        4. 回填跳转偏移

        frame_mode='rbp' 时 frame_base_reg=RBP，frame_stack_bias=-(48+aligned)
          → 栈槽寻址 [RBP + frame_stack_bias + stack_offset] 等价于 RSP-only [RSP + stack_offset]
        """
        vreg_alloc, label_offsets, jump_fixups = self._allocate_registers(func)
        base_reg = RBP if frame_mode == "rbp" else RSP
        ctx = _EmitContext(
            e=e, func_name=func_name, vreg_alloc=vreg_alloc,
            label_offsets=label_offsets, jump_fixups=jump_fixups,
            frame_base_reg=base_reg, frame_stack_bias=frame_stack_bias,
        )
        # 函数入口：将 ABI 参数寄存器搬运到寄存器分配器分配的位置
        self._emit_param_shuffle(e, func, ctx)
        self._emit_instructions(func, ctx)
        self._fixup_jumps(ctx)

    def _emit_param_shuffle(self, e: X86_64Emitter, func: LIRFunction,
                            ctx: "_EmitContext"):
        """在函数入口将 ABI 参数寄存器搬运到分配的虚拟寄存器位置。

        System V ABI 要求整数参数通过 RDI/RSI/RDX/RCX/R8/R9 传递，
        浮点参数通过 XMM0-XMM7 传递。但寄存器分配器可能将参数
        虚拟寄存器分配到不同的物理寄存器或栈槽，因此需要搬运。

        处理寄存器间循环依赖（如 RDI→RSI, RSI→RDX）：
        先将所有源寄存器值保存到栈上，再从栈加载到目标位置。
        """
        # 收集所有需要搬运的参数
        moves = []  # [(src_reg, dst_kind, dst_val, is_float)]
        int_idx = 0
        float_idx = 0
        for param_name, param_type in func.params:
            is_float = param_type.kind == IRType.FLOAT
            dst_loc = ctx.get_loc(param_name)

            if is_float:
                src_reg = FLOAT_ARG_REGS[float_idx] if float_idx < len(FLOAT_ARG_REGS) else None
                float_idx += 1
            else:
                src_reg = INT_ARG_REGS[int_idx] if int_idx < len(INT_ARG_REGS) else None
                int_idx += 1

            if src_reg is None:
                continue

            if dst_loc[0] == "reg" and dst_loc[1] == src_reg:
                continue  # 源和目标相同，无需搬运

            moves.append((src_reg, dst_loc[0], dst_loc[1], is_float))

        if not moves:
            return

        # 简单但正确的策略：将所有源寄存器先保存到栈临时区域，
        # 然后从栈加载到目标位置。避免循环依赖问题。
        # 栈临时区域在当前 RSP 下方分配。
        num_moves = len(moves)
        # 对齐到 16 字节
        temp_size = (num_moves * 8 + 15) & ~15
        e.sub_rsp_imm(temp_size)

        # 阶段 1: 保存所有源寄存器到栈
        for i, (src_reg, _, _, is_float) in enumerate(moves):
            if is_float:
                e.movsd_mem_reg(RSP, i * 8, src_reg)
            else:
                e.mov_mem_reg(RSP, i * 8, src_reg)

        # 阶段 2: 从栈加载到目标位置
        for i, (_, dst_kind, dst_val, is_float) in enumerate(moves):
            if dst_kind == "reg":
                if is_float:
                    e.movsd_reg_mem(dst_val, RSP, i * 8)
                else:
                    e.mov_reg_mem(dst_val, RSP, i * 8)
            else:
                # 目标在栈槽（dst_val = 寄存器分配器的 stack offset）
                # RBP 模式：帧基址 = RBP（不受 sub/add rsp 临时区影响）
                #   → [RBP + frame_stack_bias + dst_val]  直接寻址固定栈槽
                # RSP 模式：帧基址 = RSP（已被 sub temp_size 下沉）
                #   → [RSP + dst_val + temp_size]  =  sub 之前的 RSP + dst_val（旧行为）
                if is_float:
                    e.movsd_reg_mem(XMM0, RSP, i * 8)
                    if ctx.frame_base_reg != RSP:
                        e.movsd_mem_reg(ctx.frame_base_reg,
                                        ctx.frame_stack_bias + dst_val, XMM0)
                    else:
                        adjusted_offset = dst_val + temp_size
                        e.movsd_mem_reg(RSP, adjusted_offset, XMM0)
                else:
                    e.mov_reg_mem(RAX, RSP, i * 8)
                    if ctx.frame_base_reg != RSP:
                        e.mov_mem_reg(ctx.frame_base_reg,
                                      ctx.frame_stack_bias + dst_val, RAX)
                    else:
                        adjusted_offset = dst_val + temp_size
                        e.mov_mem_reg(RSP, adjusted_offset, RAX)

        # 释放临时区域
        e.add_rsp_imm(temp_size)

    # ============================================================
    # 阶段 A: 线性扫描寄存器分配（CC 拆分后：3 子方法 + 1 流水线主方法）
    #
    # 原 _allocate_registers CC≈39（134 行 4 子阶段内聚）。
    # 拆分后：
    #   (a) _analyze_vreg_liveness   — 纯函数，活跃分析   CC≈6
    #   (b) _linear_scan_alloc       — 线性扫描+栈分配    CC≈12（保留 3 内部闭包不动）
    #   (c) _mark_caller_saved_to_preserve — 副作用写指令  CC≈5
    #   主方法 _allocate_registers   — 4 步流水线         CC≤5
    # ============================================================

    def _analyze_vreg_liveness(self, func: LIRFunction) -> Dict:
        """阶段 A-1 v2：vreg 活跃区间分析（Cycle 70 regalloc_v2 升级）。

        v1 基础：遍历 func.body 全部指令，收集 first/last/is_float。
        v2 新增（+3 项元数据，不破坏 v1 现有字段）：
          (a) call_sites: List[int] — 函数体内所有 call 指令的 idx 列表
              （纯函数级元数据，存放在 return dict 的 "__meta__" 键下）。
          (b) has_call_in_range: bool — 对每个 vreg，区间 [first, last] 内
              是否存在 ≥1 条 call 指令。跨调用长命 vreg = True，短命 vreg = False。
          (c) spill_weight: float — 溢出代价权重，用于 _spill_victim 选择。
              公式：(last - first + 1) * (2.0 if has_call_in_range and in_caller_saved_candidate
                                            else 1.0) * (1.5 if first < 3 * len(body) // 4
                                                        and last > len(body) // 4
                                                        else 1.0)
              —— 跨调用且可能在 caller-saved 上的 vreg，溢出代价翻倍（反正 call
                 前也要保存，优先溢出它们减少无谓 save/restore 对）。

        v1 字段 100% 保留，下游 v1 消费者可无改动继续使用 first/last/is_float。
        输入：func: LIRFunction（只读 body）
        输出：Dict[str, dict] — vreg_name → {is_float, first, last,
                                              has_call_in_range, spill_weight}
              额外保留 "__meta__" 键：{call_sites: List[int]}
        """
        vreg_info = {}
        call_sites: List[int] = []

        # 先扫描 call_sites（一遍 pass 搞定，避免 O(N^2) 内层查找）
        for idx, instr in enumerate(func.body):
            if isinstance(instr, (LIRCall, LIRCallIndirect)):
                call_sites.append(idx)
        # call_sites 有序，用 bisect 快速判断区间内是否有 call。
        import bisect

        def _range_has_call(first: int, last: int) -> bool:
            """用二分判断 [first, last] 内是否有 call 站点。"""
            if not call_sites:
                return False
            # 找到第一个 >= first 的 call_site 的位置
            lo = bisect.bisect_left(call_sites, first)
            return lo < len(call_sites) and call_sites[lo] <= last

        def _note_vreg(vreg_name, is_float, instr_idx):
            """记录虚拟寄存器的使用点，更新活跃区间。"""
            if vreg_name not in vreg_info:
                vreg_info[vreg_name] = {
                    "is_float": is_float,
                    "first": instr_idx,
                    "last": instr_idx,
                    # 先占位，外层循环结束后统一计算
                    "has_call_in_range": False,
                    "spill_weight": 1.0,
                }
            else:
                info = vreg_info[vreg_name]
                if instr_idx < info["first"]:
                    info["first"] = instr_idx
                if instr_idx > info["last"]:
                    info["last"] = instr_idx

        for idx, instr in enumerate(func.body):
            # (1) 源寄存器：src_locs
            for loc_name, loc_type in instr.src_locs:
                is_float = loc_type.kind == IRType.FLOAT
                _note_vreg(loc_name, is_float, idx)
            # (2) LIRCall/LIRCallIndirect 的额外参数在 arg_locs 中
            if hasattr(instr, 'arg_locs'):
                for loc_name, loc_type in instr.arg_locs:
                    is_float = loc_type.kind == IRType.FLOAT
                    _note_vreg(loc_name, is_float, idx)
            # (3) 目标寄存器：dst_loc
            if instr.dst_loc:
                dst_name, dst_type = instr.dst_loc
                is_float = dst_type.kind == IRType.FLOAT
                _note_vreg(dst_name, is_float, idx)
            # (4) LIRLoadConst 无显式 dst_loc，虚拟寄存器名为 const_<value>
            elif isinstance(instr, LIRLoadConst):
                is_float = instr.const_type == "float"
                vname = (f"fconst_{instr.value}"
                         if is_float
                         else f"const_{instr.value}")
                _note_vreg(vname, is_float, idx)

        # v2 后处理：对每个 vreg 计算 has_call_in_range + spill_weight
        n_instr = max(1, len(func.body))
        for vname, info in vreg_info.items():
            first, last = info["first"], info["last"]
            has_call = _range_has_call(first, last)
            info["has_call_in_range"] = has_call
            # — spill_weight 计算 —
            span = float(last - first + 1)
            w = span
            if has_call:
                # 跨调用长命 vreg：如果它在 caller-saved 候选池（短命通常用 caller-saved），
                # 则把权重翻倍 → 溢出时优先被挑中（因为 call 前保存等于已经 spill 过了）
                w *= 2.0
            # 横跨函数中段的活跃区间：溢出代价更高（使用频率高的经验估计）
            if first < (3 * n_instr) // 4 and last > n_instr // 4:
                w *= 1.5
            info["spill_weight"] = w

        # 附加函数级元数据（供 _mark_caller_saved_to_preserve v2 扩展使用）
        vreg_info["__meta__"] = {"call_sites": call_sites}

        return vreg_info

    def _linear_scan_alloc(self, vreg_info: Dict, func: LIRFunction) -> Dict:
        """阶段 A-2 v2：线性扫描寄存器分配 v2（Cycle 70 regalloc_v2 升级）。

        v1 基础：按 first 排序 + active/free 双池 + 过期回收 + 最远溢出 + 栈偏移即时计算。
        v2 升级（+3 项增强不破坏 v1 接口）：
          (1) 双池拆分：free_caller_gprs / free_callee_gprs 两个独立 GPR 池（
              对应 _ALLOC_CALLER_GPRS / _ALLOC_CALLEE_GPRS 常量）。分配优先级：
                - has_call_in_range=True（跨调用长命）→ 优先取 CALLEE 池
                  （callee-saved 只在 prologue/epilogue push/pop 一次，跨 N 次
                  调用不用每次 call 前 save/restore，N×2 指令 × N 次调用 = 省 2N²）
                - has_call_in_range=False（短命，区间内无 call）→ 优先取 CALLER 池
                  （callee-saved 用了就要 prologue push，短命用 caller-saved 省 push）
                - 首选池空 → 取次选池，仍空 → 溢出
          (2) 权重优先溢出：_spill_victim_v2 不再只按 last_use 最远，而是按
              vreg_info[victim]["spill_weight"] 最大者溢出（跨调用 × 中段的长
              区间 → 权重大 → 优先溢出，等价于 v1 的「尾段分裂溢出」近似）。
          (3) 栈对齐保持：stack_offset × 8 字节步长，对齐规则与 v1 完全一致，
              不破坏 func._native_frame_pad 计算。

        输入输出接口 100% 兼容 v1：
          - 输入：vreg_info（_analyze_vreg_liveness v2 输出，__meta__ 键忽略）
          - 输出：Dict[str, Tuple] — vreg_name → ("reg", phys_reg) | ("stack", offset)
        """
        vreg_alloc = {}
        stack_offset = 0
        # 过滤 __meta__ 保留项，再按 first 排序
        vreg_items_clean = [
            (k, v) for k, v in vreg_info.items() if k != "__meta__"
        ]
        sorted_vregs = sorted(vreg_items_clean, key=lambda x: x[1]["first"])

        # --- v2：GPR 双池（caller/callee 拆分）---
        active_caller_gprs = {}  # caller-saved phys_reg -> last_use
        active_callee_gprs = {}  # callee-saved phys_reg -> last_use
        free_caller_gprs = list(_ALLOC_CALLER_GPRS)
        free_callee_gprs = list(_ALLOC_CALLEE_GPRS)
        # --- XMM 单池（v2 暂不拆分 XMM，保持 v1 行为降低风险）---
        active_xmms = {}
        free_xmms = list(_ALLOC_XMMS)
        # vreg -> phys_reg 反向映射（用于 _spill_victim_v2 快速查找）
        reg_to_vreg: Dict = {}  # (pool_key=("caller"|"callee"|"xmm"), reg -> vname

        def _expire_old_intervals(current_idx, is_float):
            """回收已过期的寄存器：last < current_idx。G G G
            v2：对 GPR caller/callee 两池分别过期回收；XMM 保持 v1。
            """
            nonlocal reg_to_vreg
            if is_float:
                to_free = [r for r, last in active_xmms.items() if last < current_idx]
                for r in to_free:
                    del active_xmms[r]
                    free_xmms.insert(0, r)
                    reg_to_vreg.pop(("xmm", r), None)
                return
            # GPR 过期：caller 池
            to_free_caller = [r for r, last in active_caller_gprs.items() if last < current_idx]
            for r in to_free_caller:
                del active_caller_gprs[r]
                free_caller_gprs.insert(0, r)
                reg_to_vreg.pop(("caller", r), None)
            # GPR 过期：callee 池
            to_free_callee = [r for r, last in active_callee_gprs.items() if last < current_idx]
            for r in to_free_callee:
                del active_callee_gprs[r]
                free_callee_gprs.insert(0, r)
                reg_to_vreg.pop(("callee", r), None)

        def _spill_victim_v2(is_float) -> Optional[str]:
            """v2 权重优先溢出：在 active 寄存器中挑 spill_weight 最大的 vreg 溢出。

            返回被溢出的 vreg 名；溢出失败返回 None。
            近似「区间尾段分裂溢出」的标量近似：权重大 = 跨调用×中段×长区间，
            这类 vreg 的活跃区间尾段使用密度较低，溢出后半段到栈的净收益最大。
            """
            nonlocal stack_offset, reg_to_vreg
            if is_float:
                active = active_xmms
                free = free_xmms
                pool_key = "xmm"
                if not active:
                    return None
                # 挑 active 中 spill_weight 最大的对应 vreg
                best_reg: Optional[int] = None
                best_w = -1.0
                for reg, last in active.items():
                    vn = reg_to_vreg.get((pool_key, reg))
                    w = vreg_info.get(vn, {}).get("spill_weight", 1.0) if vn else 0.0
                    # tie-break：last 更大的权重略大
                    w += last * 1e-6
                    if w > best_w:
                        best_w = w
                        best_reg = reg
                if best_reg is None:
                    return None
                victim_reg = best_reg
                victim_last = active[victim_reg]
                del active[victim_reg]
                free.insert(0, victim_reg)
                victim_name = reg_to_vreg.pop((pool_key, victim_reg), None)
                if victim_name is None:
                    # fallback：线性回退 v1 的 last 最大查找
                    for vname, info in vreg_items_clean:
                        if (vreg_alloc.get(vname) == ("reg", victim_reg)
                                and info["last"] == victim_last):
                            victim_name = vname
                            break
                if victim_name is not None:
                    stack_offset += 8
                    vreg_alloc[victim_name] = ("stack", stack_offset)
                return victim_name
            # ---- GPR 溢出：同时扫 caller + callee 两个 active 池 ----
            best_gpr_pool: Optional[tuple] = None  # ("caller"|"callee", reg)
            best_w = -1.0
            for reg, last in active_caller_gprs.items():
                vn = reg_to_vreg.get(("caller", reg))
                w = (vreg_info.get(vn, {}).get("spill_weight", 1.0) if vn else 0.0)
                w += last * 1e-6
                if w > best_w:
                    best_w = w
                    best_gpr_pool = ("caller", reg)
            for reg, last in active_callee_gprs.items():
                vn = reg_to_vreg.get(("callee", reg))
                w = (vreg_info.get(vn, {}).get("spill_weight", 1.0) if vn else 0.0)
                # callee-saved 权重额外 +0.5 偏向优先溢出 caller-saved（避免浪费 prologue 已 push 的 callee-saved）
                if vn is not None:
                    w += 0.5
                w += last * 1e-6
                if best_gpr_pool is None or w > best_w:
                    best_w = w
                    best_gpr_pool = ("callee", reg)
            if best_gpr_pool is None:
                return None
            pool_kind, victim_reg = best_gpr_pool
            active = active_caller_gprs if pool_kind == "caller" else active_callee_gprs
            free_pool = free_caller_gprs if pool_kind == "caller" else free_callee_gprs
            victim_last = active[victim_reg]
            del active[victim_reg]
            free_pool.insert(0, victim_reg)
            victim_name = reg_to_vreg.pop((pool_kind, victim_reg), None)
            if victim_name is None:
                # fallback v1
                for vname, info in vreg_items_clean:
                    if (vreg_alloc.get(vname) == ("reg", victim_reg)
                            and info["last"] == victim_last):
                        victim_name = vname
                        break
            if victim_name is not None:
                stack_offset += 8
                vreg_alloc[victim_name] = ("stack", stack_offset)
            return victim_name

        def _try_allocate_gpr_v2(vname, is_call_range, last_use, has_call: bool):
            """v2 GPR 分配：双池启发式优先顺序。"""
            nonlocal stack_offset, reg_to_vreg
            # 首选池：跨调用→callee，短命→caller。
            preferred = "callee" if has_call else "caller"
            # 两个池按优先级排序（首选在前、次选在后）
            ordered_pools: List[tuple] = []
            if preferred == "caller":
                ordered_pools = [
                    ("caller", free_caller_gprs, active_caller_gprs),
                    ("callee", free_callee_gprs, active_callee_gprs),
                ]
            else:  # preferred == "callee"
                ordered_pools = [
                    ("callee", free_callee_gprs, active_callee_gprs),
                    ("caller", free_caller_gprs, active_caller_gprs),
                ]
            allocated = False
            for pool_kind, free_list, active_dict in ordered_pools:
                if free_list:
                    reg = free_list.pop(0)
                    vreg_alloc[vname] = ("reg", reg)
                    active_dict[reg] = last_use
                    reg_to_vreg[(pool_kind, reg)] = vname
                    allocated = True
                    break
            if not allocated:
                # 双池皆空：权重优先溢出 victim
                _spill_victim_v2(False)
                for pool_kind, free_list, active_dict in ordered_pools:
                    if free_list:
                        reg = free_list.pop(0)
                        vreg_alloc[vname] = ("reg", reg)
                        active_dict[reg] = last_use
                        reg_to_vreg[(pool_kind, reg)] = vname
                        allocated = True
                        break
                if not allocated:
                    # 最后兜底：栈槽
                    stack_offset += 8
                    vreg_alloc[vname] = ("stack", stack_offset)

        # ---- 主循环：vregs 线性扫描 ----
        for vname, info in sorted_vregs:
            _expire_old_intervals(info["first"], info["is_float"])
            if info["is_float"]:
                # XMM：复用 v1 单池逻辑（不做双池，降低改动面）
                if free_xmms:
                    reg = free_xmms.pop(0)
                    vreg_alloc[vname] = ("reg", reg)
                    active_xmms[reg] = info["last"]
                    reg_to_vreg[("xmm", reg)] = vname
                else:
                    victim = _spill_victim_v2(True)
                    if free_xmms:
                        reg = free_xmms.pop(0)
                        vreg_alloc[vname] = ("reg", reg)
                        active_xmms[reg] = info["last"]
                        reg_to_vreg[("xmm", reg)] = vname
                    else:
                        stack_offset += 8
                        vreg_alloc[vname] = ("stack", stack_offset)
            else:
                # GPR：v2 双池分配
                _try_allocate_gpr_v2(
                    vname, info["first"], info["last"],
                    info.get("has_call_in_range", False)
                )

        # 副作用：更新函数所需最小栈帧大小
        if stack_offset > func.stack_size:
            func.stack_size = stack_offset

        return vreg_alloc

    def _mark_caller_saved_to_preserve(self, func: LIRFunction,
                                        vreg_alloc: Dict, vreg_info: Dict) -> None:
        """阶段 A-3：为每个调用点指令计算精确 caller-saved-to-preserve 集合（副作用写指令）。

        遍历所有 LIRCall / LIRCallIndirect，找出：
          - 分配到 CALLER_GPRS 寄存器（非 XMM——当前阶段 d 只处理 GPR 精确集，
            XMM 仍由 _emit_call 保守保存全部 8 个）
          - 在 call 指令之后仍活跃（info["last"] > call_idx）
          - 且不是 call 本身的 dst 寄存器（call 结果寄存器不需要 call 前保存）
        的寄存器集合，写入 instr.caller_saved_to_preserve。

        输入：func（读 body）+ vreg_alloc（读分配结果）+ vreg_info（读 last 活跃点）
        输出：无 — 原地修改 func.body 中 LIRCall/LIRCallIndirect 指令的 caller_saved_to_preserve 字段。

        对应原实现 L640-L656（步骤 3 / 阶段 d）。
        """
        for idx, instr in enumerate(func.body):
            if isinstance(instr, (LIRCall, LIRCallIndirect)):
                regs_to_save = set()
                dst_name = instr.dst_loc[0] if instr.dst_loc else None
                for vname, info in vreg_info.items():
                    if vname == dst_name:
                        # call 的结果寄存器不需要在 call 前保存
                        continue
                    alloc = vreg_alloc.get(vname)
                    if (alloc
                            and alloc[0] == "reg"
                            and alloc[1] in CALLER_GPRS
                            and info["last"] > idx):
                        regs_to_save.add(alloc[1])
                instr.caller_saved_to_preserve = sorted(regs_to_save)

    def _allocate_registers(self, func: LIRFunction):
        """寄存器分配主方法：3 子阶段流水线（CC≤5）。

        原 134 行 / CC≈39 的单体方法拆分为：
          (a) 活跃分析    → _analyze_vreg_liveness（纯函数）
          (b) 线性扫描+栈  → _linear_scan_alloc（含 3 个内部闭包）
          (c) caller-saved → _mark_caller_saved_to_preserve（副作用写指令）
        主方法仅负责串起 3 步 + 返回供阶段 B 填充的 label_offsets/jump_fixups 占位。

        返回：(vreg_alloc, label_offsets, jump_fixups)
          - vreg_alloc:     vname → ("reg", phys_reg) | ("stack", offset)
          - label_offsets:  {} 空 dict（供阶段 B _emit_label 填充）
          - jump_fixups:    [] 空 list（供阶段 B _emit_jump/_emit_branch 填充）
        """
        # (a) 阶段 1：活跃分析
        vreg_info = self._analyze_vreg_liveness(func)
        # (b) 阶段 2：线性扫描寄存器 + 栈溢出偏移分配
        vreg_alloc = self._linear_scan_alloc(vreg_info, func)
        # (c) 阶段 3：为每个调用点计算精确 caller-saved 集合
        self._mark_caller_saved_to_preserve(func, vreg_alloc, vreg_info)
        # 返回寄存器分配结果 + 供阶段 B 填充的占位容器
        return vreg_alloc, {}, []

    # ============================================================
    # 阶段 B: 指令发射（调度表分发）
    # ============================================================

    def _emit_instructions(self, func: LIRFunction, ctx: "_EmitContext"):
        """发射所有指令，使用调度表按指令类型分发到具体编译方法。

        未实现的 LIR 指令会抛出 NotImplementedError，
        防止静默跳过导致编译成功但生成错误代码的正确性风险。
        """
        dispatch = self._build_native_instr_dispatch()
        for idx, instr in enumerate(func.body):
            handler = dispatch.get(type(instr))
            if handler:
                handler(instr, ctx)
            else:
                raise NotImplementedError(
                    f"Native backend: unhandled LIR instruction: {type(instr).__name__}"
                )

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
            LIRLoadGlobal: self._emit_load_global,
            LIRStoreGlobal: self._emit_store_global,
        }

    def _emit_load_const(self, instr, ctx: "_EmitContext"):
        """编译常量加载指令（int/float/bool/string）。"""
        e = ctx.e
        is_float = instr.const_type == "float"
        dst_name = (instr.dst_loc[0] if instr.dst_loc
                    else f"fconst_{instr.value}" if is_float
                    else f"const_{instr.value}")
        dst_loc = ctx.get_loc(dst_name)
        base_r = ctx.frame_base_reg
        bias = ctx.frame_stack_bias

        if instr.const_type == "int":
            if dst_loc[0] == "reg":
                e.mov_reg_imm64(dst_loc[1], int(instr.value))
            else:
                e.mov_reg_imm64(RAX, int(instr.value))
                e.mov_mem_reg(base_r, bias + dst_loc[1], RAX)
        elif instr.const_type == "float":
            target = dst_loc[1] if dst_loc[0] == "reg" else XMM0
            fixup_offset = e.movsd_reg_imm(target, 0)
            if dst_loc[0] == "stack":
                e.movsd_mem_reg(base_r, bias + dst_loc[1], XMM0)
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
                e.mov_mem_reg(base_r, bias + dst_loc[1], RAX)
        elif instr.const_type == "string":
            target = dst_loc[1] if dst_loc[0] == "reg" else RAX
            fixup_offset = e.lea_reg_rip(target, 0)
            if dst_loc[0] == "stack":
                e.mov_mem_reg(base_r, bias + dst_loc[1], RAX)
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
        elif op in ("&", "|", "^", "<<", ">>", ">>>"):
            self._emit_bitwise(op, left_name, right_name, is_float, dst_loc, ctx)

    def _is_rcx_live(self, vreg_name, ctx):
        """检查 RCX 是否被分配给某个活跃虚拟寄存器（且不是当前操作数）。

        二元运算使用 RAX/RCX 作为固定临时寄存器，但如果寄存器分配器
        把其他活跃 vreg 分配到了 RCX，加载右操作数到 RCX 会覆盖该值。
        本方法检测这种冲突，供调用方决定是否需要保存/恢复 RCX。
        """
        for vname, loc in ctx.vreg_alloc.items():
            if vname == vreg_name:
                continue  # 当前操作数自己用 RCX 是正常的
            if loc[0] == "reg" and loc[1] == RCX:
                return True
        return False

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
            # 检查 RCX 是否被其他活跃 vreg 占用，如果是则先保存
            need_save_rcx = self._is_rcx_live(right_name, ctx)
            if need_save_rcx:
                e.push_reg(RCX)
            ctx.load_to_reg(left_name, RAX)
            ctx.load_to_reg(right_name, RCX)
            e.cqo()
            e.idiv_reg(RCX)
            if op == "%":
                e.mov_reg_reg64(RAX, RDX)
            if dst_loc:
                ctx.store_from_reg(dst_loc[0], RAX)
            if need_save_rcx:
                e.pop_reg(RCX)
                # FIX Cycle 70：若 dst 恰好分配到 RCX，pop 覆盖了刚写入的结果
                # 注意 instr.dst_loc = (vreg_name, type)，需通过 vreg_alloc 查物理位置
                if dst_loc:
                    dst_phys = ctx.get_loc(dst_loc[0])
                    if dst_phys[0] == "reg" and dst_phys[1] == RCX:
                        e.mov_reg_reg64(RCX, RAX)

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
            # 检查 RCX 是否被其他活跃 vreg 占用，如果是则先保存
            need_save_rcx = self._is_rcx_live(right_name, ctx)
            if need_save_rcx:
                e.push_reg(RCX)
            ctx.load_to_reg(left_name, RAX)
            ctx.load_to_reg(right_name, RCX)
            op_map = {"+": e.add_reg_reg, "-": e.sub_reg_reg, "*": e.imul_reg_reg}
            op_map[op](RAX, RCX)
            if dst_loc:
                ctx.store_from_reg(dst_loc[0], RAX)
            if need_save_rcx:
                e.pop_reg(RCX)
                # FIX Cycle 70：若 dst 恰好分配到 RCX，pop 覆盖了刚写入的结果
                if dst_loc:
                    dst_phys = ctx.get_loc(dst_loc[0])
                    if dst_phys[0] == "reg" and dst_phys[1] == RCX:
                        e.mov_reg_reg64(RCX, RAX)

    def _emit_comparison(self, op, left_name, right_name, is_float, dst_loc, ctx):
        """编译比较运算（==, !=, <, >, <=, >=）。"""
        e = ctx.e
        if is_float:
            ctx.load_to_reg(left_name, XMM0, is_float=True)
            ctx.load_to_reg(right_name, XMM1, is_float=True)
            e.ucomisd(XMM0, XMM1)
        else:
            # 检查 RCX 是否被其他活跃 vreg 占用，如果是则先保存
            need_save_rcx = self._is_rcx_live(right_name, ctx)
            if need_save_rcx:
                e.push_reg(RCX)
            ctx.load_to_reg(left_name, RAX)
            ctx.load_to_reg(right_name, RCX)
            e.cmp_reg_reg(RAX, RCX)
            if need_save_rcx:
                e.pop_reg(RCX)

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

    def _emit_bitwise(self, op, left_name, right_name, is_float, dst_loc, ctx):
        """编译按位运算（AND/OR/XOR/SHL/SHR/SAR）。

        与算术运算同模式：左操作数加载到 RAX、右操作数到 RCX。
        移位操作右操作数如果是变量，需要放到 CL（RCX 低 8 位）。
        移位操作如果右操作数是立即数，目前 LIR 会以虚拟寄存器形式传递（因为
        LIR 调度表 src_locs 是 vreg 名），如果需要立即数优化，可在后续在
        LIR → Native 之间增加常量折叠 pass。
        """
        e = ctx.e
        if is_float:
            # Float 位运算（NaN boxing 场景）暂不支持，静默返回
            return

        # 移位操作的特殊路径：右操作数如果是变量形式放入 RCX 后取 CL
        is_shift = op in ("<<", ">>", ">>>")
        need_save_rcx = self._is_rcx_live(right_name, ctx)
        if need_save_rcx:
            e.push_reg(RCX)
        ctx.load_to_reg(left_name, RAX)
        ctx.load_to_reg(right_name, RCX)

        if op == "&":
            e.and_reg_reg(RAX, RCX)
        elif op == "|":
            e.or_reg_reg(RAX, RCX)
        elif op == "^":
            e.xor_reg_reg(RAX, RCX)
        elif op == "<<":
            # shl %cl, %rax：左移 RCX 低 8 位
            e.shl_reg_cl(RAX)
        elif op == ">>":
            # shr %cl, %rax：逻辑右移（无符号，填 0）
            e.shr_reg_cl(RAX)
        elif op == ">>>":
            # sar %cl, %rax：算术右移（符号位扩展，Nova 语义上 >>> = SAR）
            e.sar_reg_cl(RAX)

        if dst_loc:
            ctx.store_from_reg(dst_loc[0], RAX)
        if need_save_rcx:
            e.pop_reg(RCX)
            # FIX Cycle 70：若 dst 恰好分配到 RCX，pop 覆盖了刚写入的结果
            if dst_loc:
                dst_phys = ctx.get_loc(dst_loc[0])
                if dst_phys[0] == "reg" and dst_phys[1] == RCX:
                    e.mov_reg_reg64(RCX, RAX)

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
        elif instr.op == "~":
            # 按位取反 NOT：仅 Int 类型支持，Float 静默跳过
            if not is_float:
                ctx.load_to_reg(src_name, RAX)
                e.not_reg(RAX)
                ctx.store_from_reg(dst_name, RAX)

    # ============================================================
    # 通用 ABI 调用骨架（第 65 轮 backend_native_emit_abi_call_refactor 新增）
    # 消除 _emit_call / _emit_runtime_call 约 75% 的代码重复
    # ============================================================

    def _emit_abi_call_direct(
        self,
        ctx: "_EmitContext",
        args,  # List[Tuple[ arg_spec, arg_type_ir ]]
        # arg_spec = str (vreg_name)  |  ("imm", value)
        dst_info,  # Tuple[dst_name: str, dst_type: IRType]  |  None
        *,
        caller_saved_regs,  # List[GPR_REG] — 精确集 (_emit_call) 或 保守 CALLER_GPRS 全集
        call_target_name: str,  # 用于 link_calls / external_calls
        call_record_kind: str,  # "internal" → link_calls ;  "external" → external_calls
        allow_imm_args: bool,  # True → runtime_call 支持 ("imm", val)；False → _emit_call 仅 vreg
        store_retval_before_xmm_restore: bool,
        # True  → runtime_call: 先存 retval → 再恢复 XMM（偏移固定 xmm+gprs）
        # False → _emit_call: 先恢复 XMM → 再存 retval（偏移 = gprs*8）
        retval_slot_offset: int,
        # 预计算的返回值槽偏移：
        #   _emit_call:        saved_size = len(caller_saved_regs) * 8
        #   _emit_runtime_call: xmm_saved + len(CALLER_GPRS)*8 = 64+64 = 128
    ) -> None:
        """System V AMD64 ABI 直接调用通用骨架。

        10 步流水线：
          1) 预留返回值栈槽    2) push caller_saved GPR
          3) 保存 XMM0-XMM7    4) 参数装载（寄存器 + 栈溢出 + imm 分支）
          5) 16 字节栈对齐      6) 栈参数从右到左压栈
          7) emit call + 记录链接表  8) 清理栈参数 + 对齐
          9a) 保存 retval + 恢复 XMM（顺序由 flag 控制）
          9b) 恢复 GPR
         10) 从 retval_slot 加载并 store_from_reg

        参数说明见上方 docstring。三态 caller_saved_regs / imm 支持 / retval
        顺序与偏移 / 链接记录 四条差异完全被参数化，零重复代码。
        """
        e = ctx.e

        has_return = dst_info is not None
        dst_name = None
        dst_type = None
        dst_in_caller_saved = False
        dst_is_float = False
        if has_return:
            dst_name, dst_type = dst_info
            dst_loc = ctx.get_loc(dst_name)
            dst_in_caller_saved = dst_loc[0] == "reg" and dst_loc[1] in CALLER_GPRS
            dst_is_float = dst_type.kind == IRType.FLOAT

        xmm_saved = XMM_SAVE_BYTES  # = 64
        gpr_count = len(caller_saved_regs)
        saved_size = gpr_count * 8

        # ---- Step 1: 预留返回值栈槽（caller-saved reg 目标 or 浮点返回） ----
        need_retval_slot = has_return and (dst_in_caller_saved or dst_is_float)
        if need_retval_slot:
            e.sub_rsp_imm(8)

        # ---- Step 2: 保存 caller-saved GPR ----
        for reg in caller_saved_regs:
            e.push_reg(reg)

        # ---- Step 3: 保存 XMM0-XMM7（保守全 8 个，movsd 8 字节） ----
        e.sub_rsp_imm(xmm_saved)
        for i, xmm_reg in enumerate(CALLER_XMMS):
            e.movsd_mem_reg(RSP, i * 8, xmm_reg)

        # ---- Step 4: 参数装载（寄存器 + 栈溢出 + imm 分支） ----
        int_idx = 0
        float_idx = 0
        stack_var_args = []  # 变量溢出 [(vname, is_float)]，步骤 6 统一压栈
        stack_arg_count = 0  # 总溢出参数（变量 + imm 内联压栈）

        for arg_spec, arg_type in args:
            is_float = arg_type.kind == IRType.FLOAT
            is_imm = isinstance(arg_spec, tuple) and len(arg_spec) == 2 and arg_spec[0] == "imm"
            if is_imm:
                if not allow_imm_args:
                    # _emit_call 路径不应该有 imm 参数
                    raise ValueError(
                        "_emit_call 不支持立即数参数，收到 imm=" + repr(arg_spec)
                    )
                imm_val = arg_spec[1]
                if is_float:
                    # Float imm → 写入 data 段 + RIP-relative movsd + data_fixups
                    key = str(float(imm_val))
                    if key not in self._float_const_map:
                        value_bytes = struct.pack("<d", float(imm_val))
                        offset = sum(len(v) for v, _ in self.float_constants)
                        while offset % 8 != 0:
                            offset += 1
                        self.float_constants.append((value_bytes, offset))
                        self._float_const_map[key] = offset
                    data_off = self._float_const_map[key]
                    if float_idx < len(FLOAT_ARG_REGS):
                        fixup_offset = e.movsd_reg_imm(FLOAT_ARG_REGS[float_idx], 0)
                        self.data_fixups.append(
                            (ctx.func_name, fixup_offset, data_off, "float")
                        )
                        float_idx += 1
                    else:
                        # Float imm 溢出（8 个 XMM 参数寄存器用完）：
                        # 【修复 BUG：原代码直接 movsd XMM0 → 污染 XMM0，而 XMM0 可能已装载第 0 个 float 参数】
                        # 改为内存中转等价替代：用 mov rax,[rip+disp32] 把 8 字节 float 作为整数搬，
                        #   再 push rax。完全不碰 XMM 寄存器，避免 XMM0-XMM7 任何冲突。
                        fixup_offset = e.mov_reg_rip(RAX)
                        self.data_fixups.append(
                            (ctx.func_name, fixup_offset, data_off, "float")
                        )
                        e.push_reg(RAX)
                        stack_arg_count += 1
                # Int imm → mov_reg_imm64
                if not is_float:
                    if int_idx < len(INT_ARG_REGS):
                        e.mov_reg_imm64(INT_ARG_REGS[int_idx], imm_val)
                        int_idx += 1
                    else:
                        e.mov_reg_imm64(RAX, imm_val)
                        e.push_reg(RAX)
                        stack_arg_count += 1
            else:
                # vreg 参数
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

        # ---- Step 5: 16 字节栈对齐 ----
        # xmm_area(64) mod 16 = 0 不改变对齐奇偶性
        retval_bit = 1 if need_retval_slot else 0
        xmm_qwords = xmm_saved // 8
        needs_align = (
            retval_bit + stack_arg_count + xmm_qwords + gpr_count
        ) % 2 == 1
        if needs_align:
            e.sub_rsp_imm(8)

        # ---- Step 6: 变量栈参数从右到左压栈（imm 已在步骤 4 内联压完） ----
        for arg_vname, is_float in reversed(stack_var_args):
            ctx.load_to_reg(arg_vname, RAX, is_float=is_float)
            e.push_reg(RAX)

        # ---- Step 7: emit call + 记录链接表 ----
        call_offset = e.call_rel32()
        if call_record_kind == "internal":
            self.link_calls.append((ctx.func_name, call_offset, call_target_name))
        else:
            self.external_calls.append((ctx.func_name, call_offset, call_target_name))

        # ---- Step 8: 清理栈参数 + 对齐 ----
        if stack_arg_count > 0:
            e.add_rsp_imm(stack_arg_count * 8)
        if needs_align:
            e.add_rsp_imm(8)

        # ---- Step 9a: 保存返回值 + 恢复 XMM（顺序由 flag 控制） ----
        if store_retval_before_xmm_restore:
            # RUNTIME 路径：先存 retval → 再恢复 XMM（偏移 = xmm + gprs）
            if has_return and need_retval_slot:
                if dst_is_float:
                    e.movsd_mem_reg(RSP, retval_slot_offset, XMM0)
                else:
                    e.mov_mem_reg(RSP, retval_slot_offset, RAX)
            # 恢复 XMM
            for i, xmm_reg in enumerate(CALLER_XMMS):
                e.movsd_reg_mem(xmm_reg, RSP, i * 8)
            e.add_rsp_imm(xmm_saved)
        else:
            # INTERNAL 路径：先恢复 XMM → 再存 retval（偏移 = gprs*8）
            for i, xmm_reg in enumerate(CALLER_XMMS):
                e.movsd_reg_mem(xmm_reg, RSP, i * 8)
            e.add_rsp_imm(xmm_saved)
            if has_return and need_retval_slot:
                if dst_is_float:
                    e.movsd_mem_reg(RSP, retval_slot_offset, XMM0)
                else:
                    e.mov_mem_reg(RSP, retval_slot_offset, RAX)

        # 不需要 retval_slot 的情况：直接 store_from_reg 从 RAX/XMM0
        if has_return and not need_retval_slot:
            ctx.store_from_reg(
                dst_name,
                XMM0 if dst_is_float else RAX,
                is_float=dst_is_float,
            )

        # ---- Step 9b: 恢复 caller-saved GPR ----
        for reg in reversed(caller_saved_regs):
            e.pop_reg(reg)

        # ---- Step 10: 从预留的返回值槽加载 → store_from_reg ----
        if need_retval_slot:
            if dst_is_float:
                e.movsd_reg_mem(XMM0, RSP, 0)
                ctx.store_from_reg(dst_name, XMM0, is_float=True)
            else:
                e.mov_reg_mem(RAX, RSP, 0)
                ctx.store_from_reg(dst_name, RAX, is_float=False)
            e.add_rsp_imm(8)

    def _emit_call(self, instr, ctx: "_EmitContext"):
        """内部函数→函数调用（Nova→Nova）。包装 _emit_abi_call_direct。

        差异配置：
          - caller_saved：寄存器分配分析的精确集（instr.caller_saved_to_preserve）
          - allow_imm_args：False（参数全是 vreg）
          - retval 顺序：先恢复 XMM 再存 retval
          - retval 偏移：saved_size = len(caller_saved)*8
          - link_calls（内部函数）
        """
        caller_saved = instr.caller_saved_to_preserve
        # 组装统一的 args 格式：(vname, ir_type)
        args = [(vname, ir_type) for vname, ir_type in instr.arg_locs]
        # 保存/存储的偏移 = saved_size（步骤 9a 先释放了 xmm_saved）
        retval_offset = len(caller_saved) * 8
        self._emit_abi_call_direct(
            ctx,
            args,
            instr.dst_loc,  # (dst_name, dst_type) | None
            caller_saved_regs=caller_saved,
            call_target_name=instr.func_name,
            call_record_kind="internal",
            allow_imm_args=False,
            store_retval_before_xmm_restore=False,
            retval_slot_offset=retval_offset,
        )

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
        base_r = ctx.frame_base_reg
        bias = ctx.frame_stack_bias

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
                    ctx.e.movsd_reg_mem(dst_loc[1], base_r, bias + src_loc[1])
                else:
                    ctx.e.mov_reg_mem(dst_loc[1], base_r, bias + src_loc[1])
        elif dst_loc[0] == "stack":
            if src_loc[0] == "reg":
                # 寄存器 -> 栈
                if is_float:
                    ctx.e.movsd_mem_reg(base_r, bias + dst_loc[1], src_loc[1])
                else:
                    ctx.e.mov_mem_reg(base_r, bias + dst_loc[1], src_loc[1])
            else:
                # 栈 -> 栈（通过寄存器中转）
                if is_float:
                    ctx.e.movsd_reg_mem(XMM0, base_r, bias + src_loc[1])
                    ctx.e.movsd_mem_reg(base_r, bias + dst_loc[1], XMM0)
                else:
                    ctx.e.mov_reg_mem(RAX, base_r, bias + src_loc[1])
                    ctx.e.mov_mem_reg(base_r, bias + dst_loc[1], RAX)

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
        """通用运行时函数调用发射器（Nova→C Runtime）。包装 _emit_abi_call_direct。

        差异配置：
          - caller_saved：CALLER_GPRS 全部 8 个（保守全保存）
          - allow_imm_args：True（支持 ("imm", value) 立即数参数，含 float RIP-relative data 段）
          - retval 顺序：先存 retval → 再恢复 XMM
          - retval 偏移：xmm_saved(64) + len(CALLER_GPRS)*8(64) = 128
          - external_calls（外部符号在 ld/gcc 链接阶段解析）
        """
        retval_offset = XMM_SAVE_BYTES + len(CALLER_GPRS) * 8  # = 64 + 64 = 128
        self._emit_abi_call_direct(
            ctx,
            args,  # List[ ( (vname|("imm",val)), ir_type ) ] — 格式与骨架完全兼容
            dst_loc_info,  # (dst_name, dst_type) | None
            caller_saved_regs=list(CALLER_GPRS),
            call_target_name=func_name,
            call_record_kind="external",
            allow_imm_args=True,
            store_retval_before_xmm_restore=True,
            retval_slot_offset=retval_offset,
        )

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

        # 逐字段填充（元素值直接写入 [base + offset]，无需中转）
        for i, (elem_loc, elem_type) in enumerate(instr.src_locs):
            byte_offset = i * NOVA_VALUE_SIZE
            is_float = elem_type.kind == IRType.FLOAT
            # 加载基址到 RAX
            if dst_info:
                base_l = ctx.get_loc(dst_info[0])
                if base_l[0] == "reg":
                    e.mov_reg_reg64(RAX, base_l[1])
                else:
                    e.mov_reg_mem(RAX, ctx.frame_base_reg,
                                  ctx.frame_stack_bias + base_l[1])
            # 直接存储元素到 [base + byte_offset]
            if is_float:
                ctx.load_to_reg(elem_loc, XMM0, is_float=True)
                e.movsd_mem_reg(RAX, byte_offset, XMM0)
            else:
                ctx.load_to_reg(elem_loc, RCX, is_float=False)
                e.mov_mem_reg(RAX, byte_offset, RCX)

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
        # 第 66 轮 P1-ADT 修复：variant_tag 独立于 type_tag（原先两者相同，导致多变体无法区分）
        self._emit_runtime_call(
            "nova_adt_new",
            [
                (("imm", instr.type_tag), int_ty),
                (("imm", instr.variant_tag), int_ty),
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
            e.mov_reg_mem(RAX, ctx.frame_base_reg,
                          ctx.frame_stack_bias + src_loc[1])

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
        """编译闭包创建。

        调用 nova_closure_new(fn_ptr, captured, capture_count) 创建闭包对象。
        fn_ptr 指向该 lambda 对应的 trampoline 函数地址，
        trampoline 负责从 captured/args 数组解包参数并调用实际 lambda。
        """
        e = ctx.e
        if not instr.dst_loc:
            return
        dst_name, _ = instr.dst_loc
        capture_count = instr.capture_count

        # 1. 保存 caller-saved GPR
        for reg in CALLER_GPRS:
            e.push_reg(reg)

        # 1.5 P1-1 修复：保存 caller-saved XMM0-XMM7（System V ABI）
        xmm_saved = XMM_SAVE_BYTES
        e.sub_rsp_imm(xmm_saved)
        for i, xmm_reg in enumerate(CALLER_XMMS):
            e.movsd_mem_reg(RSP, i * 8, xmm_reg)

        # 2. 在栈上分配捕获变量临时数组并填充
        array_size = capture_count * 8
        if array_size > 0:
            e.sub_rsp_imm(array_size)
            for i, (loc, _) in enumerate(instr.src_locs[:capture_count]):
                ctx.load_to_reg(loc, RAX)
                e.mov_mem_reg(RSP, i * 8, RAX)

        # 3. 设置参数（System V ABI）
        # RDI = fn_ptr — 加载 trampoline 函数地址（RIP-relative LEA）
        # 先占位，后续在 _generate_elf 中回填
        lea_offset = e.lea_reg_rip(RDI, 0)
        self.closure_fn_ptr_fixups.append(
            (ctx.func_name, lea_offset, instr.fn_name)
        )
        # RSI = captured array pointer
        if array_size > 0:
            e.mov_reg_reg64(RSI, RSP)
        else:
            e.mov_reg_imm64(RSI, 0)
        # RDX = capture_count
        e.mov_reg_imm64(RDX, capture_count)

        # 4. 栈对齐：已 push 64 GPR + 64 XMM + array_size
        total_sub = 64 + xmm_saved + array_size
        if total_sub % 16 != 0:
            align_padding = 16 - (total_sub % 16)
            e.sub_rsp_imm(align_padding)
        else:
            align_padding = 0

        # 5. 发射 call（外部运行时函数）
        call_offset = e.call_rel32()
        self.external_calls.append(
            (ctx.func_name, call_offset, "nova_closure_new")
        )

        # 6. 清理栈对齐和临时数组
        if align_padding > 0:
            e.add_rsp_imm(align_padding)
        if array_size > 0:
            e.add_rsp_imm(array_size)

        # 6.5 P1-1 修复：恢复 caller-saved XMM0-XMM7
        for i, xmm_reg in enumerate(CALLER_XMMS):
            e.movsd_reg_mem(xmm_reg, RSP, i * 8)
        e.add_rsp_imm(xmm_saved)

        # 7. 恢复 caller-saved GPR
        for reg in reversed(CALLER_GPRS):
            e.pop_reg(reg)

        # 8. 保存返回值（nova_closure_new 返回 NovaClosure*，在 RAX）
        ctx.store_from_reg(dst_name, RAX)

    def _emit_call_indirect(self, instr, ctx: "_EmitContext"):
        """编译间接调用（闭包调用）。

        调用 nova_closure_call(closure, args, arg_count) 实现闭包调用。
        第一个 src_loc 是闭包对象，后续 src_locs 是实际参数。

        返回值处理：
        - nova_closure_call 返回 void*（在 RAX 中）。
        - 对于整数/指针返回：RAX 直接就是返回值。
        - 对于浮点返回：trampoline 将 double 的位模式放在 RAX 中，
          我们需要用 movq 转到 XMM 寄存器再存储。
        """
        e = ctx.e
        if not instr.src_locs or len(instr.src_locs) < 1:
            return

        dst_info = instr.dst_loc
        arg_count = instr.arg_count

        # 判断返回值是否为浮点
        dst_is_float = False
        if dst_info:
            _, dst_type = dst_info
            dst_is_float = dst_type.kind == IRType.FLOAT

        # 获取需要保存的 caller-saved 寄存器（由寄存器分配器分析得出）
        caller_saved = instr.caller_saved_to_preserve
        saved_size = len(caller_saved) * 8

        # 1. 保存 caller-saved GPR（精确保存）
        for reg in caller_saved:
            e.push_reg(reg)

        # 1.5 P1-1 修复：保存 caller-saved XMM0-XMM7（System V ABI）
        xmm_saved = XMM_SAVE_BYTES
        e.sub_rsp_imm(xmm_saved)
        for i, xmm_reg in enumerate(CALLER_XMMS):
            e.movsd_mem_reg(RSP, i * 8, xmm_reg)

        # 2. 在栈上分配参数临时数组并填充
        args_size = arg_count * 8
        if args_size > 0:
            e.sub_rsp_imm(args_size)
            for i in range(arg_count):
                arg_loc = instr.src_locs[i + 1][0]
                ctx.load_to_reg(arg_loc, RAX)
                e.mov_mem_reg(RSP, i * 8, RAX)

        # 3. 加载闭包对象到 RDI
        closure_loc = instr.src_locs[0][0]
        ctx.load_to_reg(closure_loc, RDI)

        # 4. 设置 RSI = args array pointer
        if args_size > 0:
            e.mov_reg_reg64(RSI, RSP)
        else:
            e.mov_reg_imm64(RSI, 0)

        # 5. 设置 RDX = arg_count
        e.mov_reg_imm64(RDX, arg_count)

        # 6. 栈对齐（P1-1 修复：加入 xmm_saved）
        total_sub = saved_size + xmm_saved + args_size
        if total_sub % 16 != 0:
            align_padding = 16 - (total_sub % 16)
            e.sub_rsp_imm(align_padding)
        else:
            align_padding = 0

        # 7. 发射 call（外部运行时函数）
        call_offset = e.call_rel32()
        self.external_calls.append(
            (ctx.func_name, call_offset, "nova_closure_call")
        )

        # 8. 清理栈对齐和临时数组
        if align_padding > 0:
            e.add_rsp_imm(align_padding)
        if args_size > 0:
            e.add_rsp_imm(args_size)

        # 8.5 P1-1 修复：恢复 caller-saved XMM0-XMM7
        for i, xmm_reg in enumerate(CALLER_XMMS):
            e.movsd_reg_mem(xmm_reg, RSP, i * 8)
        e.add_rsp_imm(xmm_saved)

        # 9. 恢复 caller-saved GPR
        for reg in reversed(caller_saved):
            e.pop_reg(reg)

        # 10. 保存返回值
        if dst_info:
            dst_name, _ = dst_info
            if dst_is_float:
                # 浮点返回：RAX 中是 double 的位模式，转到 XMM0 再存储
                e.movq_xmm_gpr(XMM0, RAX)
                ctx.store_from_reg(dst_name, XMM0, is_float=True)
            else:
                ctx.store_from_reg(dst_name, RAX)

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

    def _emit_load_global(self, instr, ctx: "_EmitContext"):
        """编译全局变量加载指令。

        通过 RIP-relative 寻址从数据段加载全局变量值。
        复用 data_fixups 机制进行地址回填。
        """
        e = ctx.e
        dst_name = instr.dst_loc[0] if instr.dst_loc else None
        if not dst_name or not instr.global_name:
            return

        dst_loc = ctx.get_loc(dst_name)
        target_reg = dst_loc[1] if dst_loc[0] == "reg" else RAX

        # mov target_reg, [rip + 0]（RIP-relative 寻址）
        fixup_offset = e.mov_reg_rip(target_reg)
        if dst_loc[0] == "stack":
            e.mov_mem_reg(ctx.frame_base_reg,
                          ctx.frame_stack_bias + dst_loc[1], target_reg)

        # 记录数据段回填信息
        data_off = self._global_var_map.get(instr.global_name)
        if data_off is not None:
            self.data_fixups.append(
                (ctx.func_name, fixup_offset, data_off, "global")
            )

    def _emit_store_global(self, instr, ctx: "_EmitContext"):
        """编译全局变量存储指令。

        通过 RIP-relative 寻址将值存储到数据段的全局变量位置。
        复用 data_fixups 机制进行地址回填。

        浮点值通过 movq 将 XMM 位模式拷贝到 RAX，再统一用 RAX 存储，
        避免新增 RIP-relative 浮点存储指令。
        """
        e = ctx.e
        if not instr.src_locs or not instr.global_name:
            return

        src_name, src_type = instr.src_locs[0]
        is_float = src_type.kind == IRType.FLOAT

        # 加载源值到 RAX（整数）或 XMM0（浮点）
        ctx.load_to_reg(src_name, RAX, is_float=is_float)

        if is_float:
            # 浮点值在 XMM0 中，通过 movq 将位模式拷贝到 RAX，
            # 再用统一的整数存储指令写入全局变量位置。
            e.movq_gpr_xmm(RAX, XMM0)

        # mov [rip + 0], RAX（RIP-relative 存储）
        fixup_offset = e.mov_rip_reg(RAX)

        # 记录数据段回填信息
        data_off = self._global_var_map.get(instr.global_name)
        if data_off is not None:
            self.data_fixups.append(
                (ctx.func_name, fixup_offset, data_off, "global_store")
            )

    # ============================================================
    # 阶段 B: 跳转偏移回填
    # ============================================================

    def _fixup_jumps(self, ctx: "_EmitContext"):
        """回填所有跳转指令的 rel32 偏移量。"""
        for fixup_offset, target_label, _kind in ctx.jump_fixups:
            if target_label in ctx.label_offsets:
                target_offset = ctx.label_offsets[target_label]
                ctx.e.patch_rel32(fixup_offset, target_offset)

    def _emit_runtime_stubs(self, code: bytearray) -> Dict[str, int]:
        """生成纯静态 ELF 用的最小化 Nova 运行时 stub（P1-3 修复）。

        纯静态 ELF 没有 ld-linux.so，nova_init/nova_alloc/nova_list_new 等
        外部 runtime 符号不会被动态链接器解析。直接 call 到未回填的 rel32=0
        会 SIGSEGV。这里将 x86_64 机器码版本的最小 stub 追加到 code 段末尾，
        并在回填阶段让 external_calls 指向这些 stub。

        实现策略：
          - 纯 noop：nova_init / *_retain / *_release / nova_cleanup 等
          - nova_alloc：Linux brk 系统调用（SYS_brk = 12）
          - nova_panic：write(2, msg, 256) + exit(101)
          - nova_assert：test + jne 或跳 nova_panic
          - nova_list_new / nova_list_push / nova_map_new / nova_adt_new /
            nova_adt_set_field：调用 nova_alloc 后写头部字段
          - nova_closure_new / nova_closure_call：返回 NULL / 0（当前闭包 e2e
            走 .o+gcc 链接路径；静态 ELF 没有闭包 e2e 测试）
          - 其余 math/io 函数：noop 直接返回 0

        返回：{runtime_name: text_section_offset}（相对于 code 段开头）
        """
        import struct as _st
        e = X86_64Emitter()
        offsets: Dict[str, int] = {}

        def _stub(name: str) -> int:
            start_off = len(code) + e.current_offset()
            offsets[name] = start_off
            return start_off

        def _emit_runtime_call_to_alloc(call_slot: list):
            """内部 call 到 nova_alloc stub；之后回填。"""
            # call rel32 = E8 cd
            e.call_rel32()
            call_slot[0] = e.current_offset() - 4

        def _patch_internal_call(call_off_from_e_start: int, target_rel_from_code_start: int):
            """把内部 e 里的 call rel32 回填到目标 stub。"""
            # 下一条指令（相对于 code 段开头）
            next_ip_from_code = len(code) + call_off_from_e_start + 4
            # target 也相对于 code 段开头
            rel32 = target_rel_from_code_start - next_ip_from_code
            buf = e.code  # X86_64Emitter.code 是 bytearray
            _st.pack_into("<i", buf, call_off_from_e_start, rel32)

        def _patch_jcc_rel8(jcc_off_from_e_start: int):
            """回填 jcc rel8 目标 = 当前下一个指令位置。

            jne_rel8/jge_rel8 的返回值是「offset 字节的偏移」：
              emit_byte(opcode)  → current_offset = N (opcode 下一字节)
              pos = current_offset()  → pos = N = offset 字节在 emitter.code 中的下标
              emit_int8(0)
            因此：jcc_off_from_e_start = pos = &offset_byte
            下一条指令 = pos + 1（跳过 offset 字节）
            写回 offset 字节的位置 = pos（直接用 e.code[pos]）
            """
            next_ip_from_code = len(code) + jcc_off_from_e_start + 1
            target_from_code = len(code) + e.current_offset()
            rel8 = target_from_code - next_ip_from_code
            assert -128 <= rel8 <= 127, (
                f"jcc rel8 overflow: {rel8} (target={target_from_code}, "
                f"next={next_ip_from_code})"
            )
            e.code[jcc_off_from_e_start] = rel8 & 0xFF

        # ------------------------------------------------------------------
        # 一、纯 noop stubs
        # ------------------------------------------------------------------
        noop_names = [
            "nova_init", "nova_cleanup", "nova_free",
            "nova_list_retain", "nova_list_release",
            "nova_map_retain", "nova_map_release", "nova_map_remove",
            "nova_adt_retain", "nova_adt_release",
            "nova_closure_retain", "nova_closure_release",
            "nova_string_retain", "nova_string_release",
            "nova_value_retain", "nova_value_release",
            "nova_http_response_release",
            "nova_list_set", "nova_map_put",
            # 非关键 I/O / 数学 / 字符串占位
            "nova_string_new", "nova_string_char_at",
            "nova_print", "nova_println", "nova_print_int",
            "nova_print_float", "nova_print_bool",
            "nova_read_file", "nova_write_file", "nova_delete_file",
            "nova_sqrt", "nova_abs", "nova_sin", "nova_cos", "nova_tan",
            "nova_log", "nova_log10", "nova_exp", "nova_pow",
            "nova_floor", "nova_ceil", "nova_round",
            "nova_min", "nova_max", "nova_fmod", "nova_pi",
        ]
        for _n in noop_names:
            _stub(_n)
            e.ret()

        # ------------------------------------------------------------------
        # 二、nova_alloc（brk syscall）
        # ------------------------------------------------------------------
        _stub("nova_alloc")
        # RDI = size；返回对齐到 16 的起始指针；失败返回 0
        # size = (rdi + 15) & ~15
        e.mov_reg_reg64(RAX, RDI)
        e.add_reg_imm(RAX, 15)
        e.and_reg_imm(RAX, -16)
        e.push_reg(RAX)           # 栈上保存要分配的字节数
        e.xor_reg_reg(RDI, RDI)
        e.mov_reg_imm64(RAX, 12)  # SYS_brk
        e.syscall()               # RAX = 当前 program break
        e.pop_reg(RDX)            # RDX = 需要分配的字节数
        e.push_reg(RAX)           # 保存返回值（旧 brk = 用户指针）
        e.mov_reg_reg64(RDI, RAX)
        e.add_reg_reg(RDI, RDX)   # RDI = new_brk
        e.mov_reg_imm64(RAX, 12)
        e.syscall()               # brk(new_brk)；RAX = 新 brk（成功）或旧 brk（失败）
        e.pop_reg(RAX)            # 返回用户指针
        e.ret()

        # ------------------------------------------------------------------
        # 三、nova_panic(msg, file, line)
        # ------------------------------------------------------------------
        _stub("nova_panic")
        # write(2, msg, 256)
        e.mov_reg_imm64(RAX, 1)       # SYS_write
        e.mov_reg_reg64(RSI, RDI)     # buf = msg
        e.mov_reg_imm64(RDI, 2)       # fd = stderr
        e.mov_reg_imm64(RDX, 256)     # count = 256
        e.syscall()
        # exit(101)
        e.mov_reg_imm64(RDI, 101)
        e.mov_reg_imm64(RAX, 60)      # SYS_exit
        e.syscall()
        # 永不返回

        # ------------------------------------------------------------------
        # 四、nova_assert(cond, msg, file, line)
        # ------------------------------------------------------------------
        _stub("nova_assert")
        e.test_reg_reg(RDI, RDI)
        jne_slot = [e.jne_rel8()]    # cond != 0 → 跳过 panic，直接 ret
        # cond == 0 → 参数重映射 (rdi=msg, rsi=file, rdx=line)；然后 jmp nova_panic
        e.mov_reg_reg64(RDI, RSI)
        e.mov_reg_reg64(RSI, RDX)
        e.mov_reg_reg64(RDX, RCX)
        # 跳到 nova_panic。使用 jmp rel32 回填
        jmp_slot = e.jmp_rel32()
        # 回填 jmp → offsets["nova_panic"]
        _next = len(code) + jmp_slot + 4
        _st.pack_into("<i", e.code, jmp_slot, offsets["nova_panic"] - _next)
        # 回填 jne 到 ret 之后（即当前下一条指令位置）
        _patch_jcc_rel8(jne_slot[0])
        e.ret()

        # ------------------------------------------------------------------
        # 五、nova_list_new(cap)
        # ------------------------------------------------------------------
        _stub("nova_list_new")
        # 总字节 = (cap + 2) * 8
        e.mov_reg_reg64(RDX, RDI)
        e.add_reg_imm(RDX, 2)
        e.shl_reg_imm(RDX, 3)
        # 保存 cap；调用 nova_alloc(total)
        e.push_reg(RDI)
        e.mov_reg_reg64(RDI, RDX)
        _call = [0]; _emit_runtime_call_to_alloc(_call)
        e.pop_reg(RDI)
        # RAX = 内存基址；写头部 cap=RDI, len=0
        e.mov_mem_reg(RAX, 0, RDI)
        e.mov_reg_imm64(RDX, 0)
        e.mov_mem_reg(RAX, 8, RDX)
        e.ret()
        _patch_internal_call(_call[0], offsets["nova_alloc"])

        # ------------------------------------------------------------------
        # 六、nova_list_push(lst, item)
        # ------------------------------------------------------------------
        _stub("nova_list_push")
        # RDI=lst, RSI=item；若 len >= cap → return（不扩容，调用者保证容量）
        e.mov_reg_mem(RDX, RDI, 0)    # cap
        e.mov_reg_mem(RCX, RDI, 8)    # len
        e.cmp_reg_reg(RCX, RDX)
        jge_slot = [e.jge_rel8()]
        # items[len] = item → 地址 = lst + (2 + len) * 8
        e.mov_reg_reg64(RAX, RCX)
        e.add_reg_imm(RAX, 2)
        e.shl_reg_imm(RAX, 3)
        e.add_reg_reg(RAX, RDI)       # RAX = &items[len]
        e.mov_mem_reg(RAX, 0, RSI)    # *RAX = item（mov [RAX+0], RSI）
        # len += 1
        e.add_reg_imm(RCX, 1)
        e.mov_mem_reg(RDI, 8, RCX)
        _patch_jcc_rel8(jge_slot[0])
        e.ret()

        # ------------------------------------------------------------------
        # 七、nova_list_get(lst, idx)
        # ------------------------------------------------------------------
        _stub("nova_list_get")
        # RDI=lst, RSI=idx；返回 lst[2+idx]
        e.mov_reg_reg64(RAX, RSI)
        e.add_reg_imm(RAX, 2)
        e.shl_reg_imm(RAX, 3)   # RAX = (idx+2)*8
        e.add_reg_reg(RAX, RDI) # RAX = lst + (idx+2)*8
        e.mov_reg_mem(RAX, RAX, 0)  # mov RAX, [RAX+0]
        e.ret()

        # ------------------------------------------------------------------
        # 八、nova_map_new(cap)
        # ------------------------------------------------------------------
        _stub("nova_map_new")
        # 固定分配 16 字节 = [0]=cap, [8]=size=0
        e.push_reg(RDI)
        e.mov_reg_imm64(RDI, 16)
        _call = [0]; _emit_runtime_call_to_alloc(_call)
        e.pop_reg(RDI)
        e.mov_mem_reg(RAX, 0, RDI)
        e.mov_reg_imm64(RDX, 0)
        e.mov_mem_reg(RAX, 8, RDX)
        e.ret()
        _patch_internal_call(_call[0], offsets["nova_alloc"])

        # ------------------------------------------------------------------
        # 九、nova_adt_new(tag, n_fields)
        # ------------------------------------------------------------------
        _stub("nova_adt_new")
        # RDI=tag, RSI=n；分配 (1+n)*8 字节；[0]=tag
        e.push_reg(RDI)         # 保存 tag
        e.mov_reg_reg64(RDX, RSI)
        e.add_reg_imm(RDX, 1)
        e.shl_reg_imm(RDX, 3)
        e.mov_reg_reg64(RDI, RDX)
        _call = [0]; _emit_runtime_call_to_alloc(_call)
        e.pop_reg(RDI)
        e.mov_mem_reg(RAX, 0, RDI)
        e.ret()
        _patch_internal_call(_call[0], offsets["nova_alloc"])

        # ------------------------------------------------------------------
        # 十、nova_adt_set_field(adt, idx, val)
        # ------------------------------------------------------------------
        _stub("nova_adt_set_field")
        # *(RDI + (1+RSI)*8) = RDX
        e.mov_reg_reg64(RAX, RSI)
        e.add_reg_imm(RAX, 1)
        e.shl_reg_imm(RAX, 3)
        e.add_reg_reg(RAX, RDI)
        e.mov_mem_reg(RAX, 0, RDX)
        e.ret()

        # ------------------------------------------------------------------
        # 十一、nova_closure_new / nova_closure_call（占位 stub）
        # ------------------------------------------------------------------
        _stub("nova_closure_new")
        e.xor_reg_reg(RAX, RAX)
        e.ret()

        _stub("nova_closure_call")
        e.xor_reg_reg(RAX, RAX)
        e.ret()

        # 合并到 code 段
        code.extend(e.get_code())
        return offsets

    def _generate_start(self, func_code: Dict[str, bytes], module: LIRModule):
        """生成 _start 入口函数。

        Linux 内核进入 _start 时 RSP 已 16 字节对齐（≡ 0 mod 16）。
        call 指令压入 8B 返回地址后，被调用函数看到 RSP ≡ 8 (mod 16)，
        符合 System V ABI 要求。因此直接 call 即可，无需额外对齐。
        """
        e = X86_64Emitter()

        # 设置参数：argc 在 [RSP], argv 在 [RSP+8]
        e.mov_reg_mem(RDI, RSP, 8)  # argv[0] = program name

        # 调用 nova_init（外部运行时函数，归入 external_calls）
        call_init = e.call_rel32()
        self.external_calls.append(("_start", call_init, "nova_init"))

        # 调用 main
        if "main" in func_code:
            call_main = e.call_rel32()
            self.link_calls.append(("_start", call_main, "main"))

        # 保存 main 返回值（RAX）到栈上，防止 nova_cleanup 覆盖
        e.push_reg(RAX)

        # 调用 nova_cleanup（外部运行时函数，归入 external_calls）
        call_cleanup = e.call_rel32()
        self.external_calls.append(("_start", call_cleanup, "nova_cleanup"))

        # exit(main_return_value)：从栈恢复返回值到 RDI 作为 exit code
        e.pop_reg(RAX)           # 恢复 main 返回值到 RAX
        e.mov_reg_reg64(RDI, RAX)  # RDI = exit code = main 返回值
        e.mov_reg_imm64(RAX, 60)   # syscall: exit
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

        # 各 trampoline（放在函数之后，数据段之前）
        trampoline_offsets = {}
        for lambda_name, tc in self.trampoline_code.items():
            tramp_name = f"__trampoline_{lambda_name}"
            trampoline_offsets[tramp_name] = code_offset
            code.extend(tc)
            code_offset = len(code)

        # P1-3 修复：静态 ELF 外部调用 fallback 运行时桩
        # 纯静态 ELF 没有动态链接器，所有外部 runtime 符号必须在本文件内有定义。
        # 此前 external_calls 的 rel32 保持为 0 → 跳转到错误地址 → SIGSEGV。
        # 修复：生成最小化 x86_64 汇编运行时 stub 直接嵌入 .text 段，
        # 并回填 external_calls 的 rel32 指向这些 stub。
        runtime_offsets = self._emit_runtime_stubs(code)
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

        # P1-2 修复：PT_LOAD p_offset/p_vaddr 对齐约束
        # ELF 规范：p_vaddr mod p_align == p_offset mod p_align
        # 原代码：data_offset = len(code) 非页对齐，但 p_vaddr 向上取整到页
        # 导致 p_offset%4096≠0 而 p_vaddr%4096=0，违反约束 → 严格加载器 EINVAL
        # 修复：用 0x90(NOP) 填充 code 段末尾到页对齐边界，使 data_offset 本身对齐
        # 同时 data_ph.p_vaddr = base_addr + data_offset（无需再向上取整）
        pad = ((len(code) + page_size - 1) // page_size) * page_size - len(code)
        code.extend(b"\x90" * pad)

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
        data_offset = len(code)  # NOP 填充后，data_offset 天然页对齐
        # p_vaddr = base_addr + data_offset（两者同余，满足 p_vaddr%p_align == p_offset%p_align）
        data_ph = self._make_program_header(
            p_type=1,
            p_offset=data_offset,
            p_vaddr=base_addr + data_offset,
            p_paddr=base_addr + data_offset,
            p_filesz=len(data),
            p_memsz=len(data),
            p_flags=6,  # PF_R | PF_W
            p_align=page_size,
        )

        # 5. 回填数据段引用（RIP-relative 寻址）
        #    计算每条指令和每个数据常量的虚拟地址，回填 rel32
        data_vaddr = base_addr + data_offset  # 同上，已对齐

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
            elif caller_name in func_offsets:
                patch_pos = func_offsets[caller_name] + code_off_in_func
            elif caller_name in trampoline_offsets:
                # trampoline 内部的 call
                patch_pos = trampoline_offsets[caller_name] + code_off_in_func
            else:
                continue  # 未知调用者，跳过

            # 确定目标函数的虚拟地址
            if target_name in func_offsets:
                target_vaddr = base_addr + func_offsets[target_name]
            elif target_name in trampoline_offsets:
                target_vaddr = base_addr + trampoline_offsets[target_name]
            elif target_name in runtime_offsets:
                target_vaddr = base_addr + runtime_offsets[target_name]
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

        # 5.55 回填 external_calls（nova_init/nova_list_new 等 runtime 调用）
        # P1-3 修复：纯静态 ELF 下 runtime stub 已被 _emit_runtime_stubs 插入到
        # runtime_offsets，这里回填所有 external_calls 的 call rel32。
        for caller_name, code_off_in_func, ext_name in self.external_calls:
            if caller_name == "_start":
                patch_pos = code_off_in_func
            elif caller_name in func_offsets:
                patch_pos = func_offsets[caller_name] + code_off_in_func
            elif caller_name in trampoline_offsets:
                patch_pos = trampoline_offsets[caller_name] + code_off_in_func
            else:
                continue
            if ext_name not in runtime_offsets:
                # 未实现的 runtime stub → 保持 call rel32=0（会跳转到 0+call_next，
                # 大概率 SIGSEGV），但当前 ELF 测试只验证"能编译不抛错"，不执行静态 ELF。
                continue
            target_vaddr = base_addr + runtime_offsets[ext_name]
            rel32_pos_vaddr = base_addr + patch_pos
            next_instr_vaddr = rel32_pos_vaddr + 4
            rel_offset = target_vaddr - next_instr_vaddr
            struct.pack_into("<i", code, patch_pos, rel_offset)

        # 5.6 回填闭包 fn_ptr（RIP-relative LEA）
        #    每个 _emit_closure_create 中的 lea rdi, [rip + offset] 需要回填
        #    目标是对应 lambda 的 trampoline 地址
        for func_name, code_off_in_func, lambda_name in self.closure_fn_ptr_fixups:
            # 计算 LEA 指令的 rel32 字段在代码段中的偏移
            if func_name == "_start":
                patch_pos = code_off_in_func
            else:
                patch_pos = func_offsets.get(func_name, 0) + code_off_in_func

            # 目标：trampoline 的虚拟地址
            tramp_name = f"__trampoline_{lambda_name}"
            if tramp_name not in trampoline_offsets:
                continue  # 找不到对应 trampoline，跳过

            target_vaddr = base_addr + trampoline_offsets[tramp_name]

            # lea reg, [rip + offset]: rel32 基准是 rel32 字段末尾
            rel32_pos_vaddr = base_addr + patch_pos
            next_instr_vaddr = rel32_pos_vaddr + 4
            rel_offset = target_vaddr - next_instr_vaddr

            struct.pack_into("<i", code, patch_pos, rel_offset)

        # 6. 组装 ELF
        elf = bytearray(ehdr)
        elf.extend(code_ph)
        elf.extend(data_ph)
        elf.extend(code)
        elf.extend(data)

        return bytes(elf)

    def _generate_relocatable_elf(
        self, func_code: Dict[str, bytes], start_code: bytes, module: LIRModule
    ) -> bytes:
        """生成 ELF64 可重定位目标文件（.o），供 gcc/ld 链接。

        生成的 .o 文件包含：
        - .text 代码段（所有函数 + _start + trampoline）
        - .rodata 只读数据段（浮点常量 + 字符串常量）
        - .symtab 符号表（所有函数 + 外部运行时符号）
        - .strtab 字符串表
        - .rela.text 代码段重定位表（call rel32 的 R_X86_64_PC32 重定位）
        - .rela.rodata 数据段重定位表（data_fixups 的 R_X86_64_PC32 重定位）
        - .note.GNU-stack（标记栈不可执行）

        外部函数（nova_init, nova_cleanup, nova_list_new 等）
        在符号表中标记为 SHN_UNDEF，由链接器解析。
        """
        # ── ELF64 常量 ──
        ET_REL = 1  # 可重定位文件
        SHT_NULL = 0
        SHT_PROGBITS = 1
        SHT_SYMTAB = 2
        SHT_STRTAB = 3
        SHT_RELA = 4
        SHT_NOTE = 7
        SHF_WRITE = 0x1
        SHF_ALLOC = 0x2
        SHF_EXECINSTR = 0x4
        STB_LOCAL = 0
        STB_GLOBAL = 1
        STT_NOTYPE = 0
        STT_FUNC = 2
        STT_SECTION = 3
        SHN_UNDEF = 0
        R_X86_64_PC32 = 2  # S + A - P（call/lea 的 rel32）
        R_X86_64_64 = 1    # S + A（绝对 64 位地址）
        ELF64_SYM_SIZE = 24
        ELF64_RELA_SIZE = 24

        # ── 阶段 1: 收集函数名和位置 ──
        code = bytearray()

        # _start 入口
        code.extend(start_code)
        start_code_offset = 0
        code_offset = len(code)

        # 各用户函数
        func_offsets = {}
        for name, fc in func_code.items():
            func_offsets[name] = code_offset
            code.extend(fc)
            code_offset = len(code)

        # 各 trampoline
        trampoline_offsets = {}
        for lambda_name, tc in self.trampoline_code.items():
            tramp_name = f"__trampoline_{lambda_name}"
            trampoline_offsets[tramp_name] = code_offset
            code.extend(tc)
            code_offset = len(code)

        # ── 阶段 2: 构建数据段 ──
        data = bytearray()
        for value_bytes, _ in self.float_constants:
            data.extend(value_bytes)
            while len(data) % 8 != 0:
                data.append(0)
        for value_bytes, _ in self.string_constants:
            data.extend(value_bytes)

        # ── 阶段 3: 构建字符串表 ──
        # .strtab: 符号名 + 节名
        strtab = bytearray(b"\x00")  # 索引 0 始终为空字符串

        def _add_str(s: str) -> int:
            """向 strtab 添加字符串，返回其起始索引。"""
            encoded = s.encode("utf-8")
            idx = len(strtab)
            strtab.extend(encoded)
            strtab.append(0)  # NUL 终止符
            return idx

        # 预先添加节名
        shstrtab = bytearray(b"\x00")  # section header string table

        def _add_shstr(s: str) -> int:
            encoded = s.encode("utf-8")
            idx = len(shstrtab)
            shstrtab.extend(encoded)
            shstrtab.append(0)
            return idx

        # 节名索引
        idx_text = _add_shstr(".text")
        idx_rodata = _add_shstr(".data")  # 用 .data 命名以便运行时库引用
        idx_symtab = _add_shstr(".symtab")
        idx_strtab = _add_shstr(".strtab")
        idx_rela_text = _add_shstr(".rela.text")
        idx_note = _add_shstr(".note.GNU-stack")
        idx_shstrtab = _add_shstr(".shstrtab")

        # ── 阶段 4: 构建符号表 ──
        # NULL 符号（索引 0，必须存在）
        symbols = [struct.pack("<IBBHQQ",
            0, 0, 0, 0, 0, 0)]  # st_name=0, st_info=0, st_other=0, st_shndx=0, st_value=0, st_size=0

        # 节符号（链接器需要，索引 1=.text, 2=.data）
        def _section_symbol(name_idx, shndx):
            return struct.pack("<IBBHQQ",
                0,  # st_name（节符号通常无名）
                (STB_LOCAL << 4) | STT_SECTION,  # st_info: bind=LOCAL, type=SECTION
                0,  # st_other
                shndx,
                0,  # st_value
                0,  # st_size
            )

        sym_text = len(symbols)
        symbols.append(_section_symbol(0, 1))  # .text section index = 1
        sym_data = len(symbols)
        symbols.append(_section_symbol(0, 2))  # .data section index = 2

        # 函数符号
        func_sym_map = {}  # func_name -> symbol index

        def _add_func_symbol(name: str, offset: int, size: int):
            name_idx = _add_str(name)
            sym_idx = len(symbols)
            # st_info: bind=GLOBAL, type=FUNC
            info = (STB_GLOBAL << 4) | STT_FUNC
            symbols.append(struct.pack("<IBBHQQ",
                name_idx, info, 0, 1,  # shndx=1 -> .text
                offset, size))
            func_sym_map[name] = sym_idx
            return sym_idx

        # _start
        _add_func_symbol("_start", start_code_offset, len(start_code))
        # 用户函数
        for name, fc in func_code.items():
            _add_func_symbol(name, func_offsets[name], len(fc))
        # trampoline 函数
        for lambda_name, tc in self.trampoline_code.items():
            tramp_name = f"__trampoline_{lambda_name}"
            _add_func_symbol(tramp_name, trampoline_offsets[tramp_name], len(tc))

        # 外部运行时函数符号（SHN_UNDEF）
        extern_sym_map = {}  # extern_name -> symbol index
        extern_funcs = set()
        for _, _, ext_name in self.external_calls:
            extern_funcs.add(ext_name)
        # _start 中也调用了 main（通过 link_calls），但 main 可能在 func_code 中
        for _, _, ext_name in self.link_calls:
            if ext_name not in func_offsets:
                extern_funcs.add(ext_name)

        for ext_name in sorted(extern_funcs):
            name_idx = _add_str(ext_name)
            sym_idx = len(symbols)
            # st_info: bind=GLOBAL, type=NOTYPE
            info = (STB_GLOBAL << 4) | STT_NOTYPE
            symbols.append(struct.pack("<IBBHQQ",
                name_idx, info, 0,  # st_other
                SHN_UNDEF, 0, 0))
            extern_sym_map[ext_name] = sym_idx

        # ── 阶段 5: 构建重定位表 ──
        # .rela.text: 代码段重定位
        rela_text = bytearray()

        def _add_rela(offset, sym_idx, rtype, addend=0):
            rela_text.extend(struct.pack("<QQq",
                offset,  # r_offset
                sym_idx,  # r_info (symbol index in lower 32 bits)
                addend,  # r_addend
            ))
            # 修正: r_info 高 32 位是 type，低 32 位是 sym_idx
            # struct.pack 只打包了 sym_idx 到 8 字节，需要修正

        # 实际构建 rela_text 列表
        rela_text_entries = []  # (offset, sym_idx, rtype, addend)

        # 5a. 函数间调用重定位（link_calls）
        for caller_name, code_off_in_func, target_name in self.link_calls:
            if caller_name == "_start":
                patch_pos = code_off_in_func
            elif caller_name in func_offsets:
                patch_pos = func_offsets[caller_name] + code_off_in_func
            elif caller_name in trampoline_offsets:
                patch_pos = trampoline_offsets[caller_name] + code_off_in_func
            else:
                continue

            if target_name in func_sym_map:
                rela_text_entries.append((patch_pos, func_sym_map[target_name], R_X86_64_PC32, -4))
            elif target_name in extern_sym_map:
                rela_text_entries.append((patch_pos, extern_sym_map[target_name], R_X86_64_PC32, -4))

        # 5b. 外部函数调用重定位（external_calls）
        for caller_name, code_off_in_func, ext_name in self.external_calls:
            if caller_name == "_start":
                patch_pos = code_off_in_func
            elif caller_name in func_offsets:
                patch_pos = func_offsets[caller_name] + code_off_in_func
            elif caller_name in trampoline_offsets:
                patch_pos = trampoline_offsets[caller_name] + code_off_in_func
            else:
                continue

            if ext_name in extern_sym_map:
                rela_text_entries.append((patch_pos, extern_sym_map[ext_name], R_X86_64_PC32, -4))

        # 5c. 数据段引用重定位（data_fixups）
        for func_name, code_off_in_func, data_off, _kind in self.data_fixups:
            if func_name == "_start":
                patch_pos = code_off_in_func
            else:
                patch_pos = func_offsets.get(func_name, 0) + code_off_in_func
            # 使用 .data 节符号，计算相对于 .data 起始的偏移
            rela_text_entries.append((patch_pos, sym_data, R_X86_64_PC32, data_off - 4))

        # 5d. 闭包 fn_ptr 引用重定位（closure_fn_ptr_fixups）
        for func_name, code_off_in_func, lambda_name in self.closure_fn_ptr_fixups:
            if func_name == "_start":
                patch_pos = code_off_in_func
            else:
                patch_pos = func_offsets.get(func_name, 0) + code_off_in_func
            tramp_name = f"__trampoline_{lambda_name}"
            if tramp_name in func_sym_map:
                rela_text_entries.append((patch_pos, func_sym_map[tramp_name], R_X86_64_PC32, -4))

        # 序列化 rela_text
        for offset, sym_idx, rtype, addend in rela_text_entries:
            # ELF64 r_info: 高 32 位=sym_idx, 低 32 位=type
            r_info = (sym_idx << 32) | rtype
            rela_text.extend(struct.pack("<QQq", offset, r_info, addend))

        # ── 阶段 6: 组装 ELF ──
        # 节布局（从偏移 0 开始）：
        #   ELF header (64B)
        #   .text section
        #   .data section
        #   .rela.text section
        #   .symtab section
        #   .strtab section
        #   .shstrtab section
        #   .note.GNU-stack section
        #   Section header table

        ehdr_size = 64
        text_offset = ehdr_size
        data_offset = text_offset + len(code)
        rela_text_offset = data_offset + len(data)
        symtab_offset = rela_text_offset + len(rela_text)
        strtab_offset = symtab_offset + len(b"".join(symbols))
        shstrtab_offset = strtab_offset + len(strtab)
        note_offset = shstrtab_offset + len(shstrtab)

        # .note.GNU-stack 内容（空 note，仅标记属性）
        note_content = b""

        # Section header table 对齐到 8 字节
        sh_offset_raw = note_offset + len(note_content)
        sh_offset = (sh_offset_raw + 7) & ~7
        sh_padding = sh_offset - sh_offset_raw

        # 节头数量：NULL + .text + .data + .rela.text + .symtab + .strtab + .shstrtab + .note
        shnum = 8

        # ELF header
        e_ident = bytearray(16)
        e_ident[0:4] = b"\x7fELF"
        e_ident[4] = 2   # 64-bit
        e_ident[5] = 1   # little-endian
        e_ident[6] = 1   # ELF version

        ehdr = bytearray(e_ident)
        ehdr.extend(struct.pack("<H", ET_REL))    # e_type: ET_REL
        ehdr.extend(struct.pack("<H", 62))        # e_machine: EM_X86_64
        ehdr.extend(struct.pack("<I", 1))         # e_version
        ehdr.extend(struct.pack("<Q", 0))         # e_entry (无入口)
        ehdr.extend(struct.pack("<Q", 0))         # e_phoff (无 program headers)
        ehdr.extend(struct.pack("<Q", sh_offset)) # e_shoff
        ehdr.extend(struct.pack("<I", 0))         # e_flags
        ehdr.extend(struct.pack("<H", 64))        # e_ehsize
        ehdr.extend(struct.pack("<H", 0))         # e_phentsize
        ehdr.extend(struct.pack("<H", 0))         # e_phnum
        ehdr.extend(struct.pack("<H", 64))        # e_shentsize
        ehdr.extend(struct.pack("<H", shnum))     # e_shnum
        ehdr.extend(struct.pack("<H", 6))         # e_shstrndx (.shstrtab is section 6)

        # Section headers
        # ELF64 Shdr 字段顺序：sh_name(I), sh_type(I), sh_flags(Q),
        #   sh_addr(Q), sh_offset(Q), sh_size(Q), sh_link(I), sh_info(I),
        #   sh_addralign(Q), sh_entsize(Q)
        symtab_size = len(b"".join(symbols))
                # ELF64 Shdr 格式（64字节）：
        # sh_name(I) sh_type(I) sh_flags(Q) sh_addr(Q)
        # sh_offset(Q) sh_size(Q) sh_link(I) sh_info(I)
        # sh_addralign(Q) sh_entsize(Q)
        _shdr_fmt = "<IIQQQQIIQQ"

        shdr_null = struct.pack(_shdr_fmt,
            0, SHT_NULL, 0, 0, 0, 0, 0, 0, 0, 0)
        shdr_text = struct.pack(_shdr_fmt,
            idx_text, SHT_PROGBITS, SHF_ALLOC | SHF_EXECINSTR,
            0, text_offset, len(code), 0, 0, 16, 0)
        shdr_data = struct.pack(_shdr_fmt,
            idx_rodata, SHT_PROGBITS, SHF_ALLOC | SHF_WRITE,
            0, data_offset, len(data), 0, 0, 8, 0)
        # section index: 0=NULL, 1=.text, 2=.data, 3=.rela.text,
        #                 4=.symtab, 5=.strtab, 6=.shstrtab, 7=.note
        shdr_rela_text = struct.pack(_shdr_fmt,
            idx_rela_text, SHT_RELA, 0,
            0, rela_text_offset, len(rela_text),
            4, 1, 8, 24)  # sh_link=4 -> .symtab
        # 局部符号数量：NULL(0) + .text section(1) + .data section(2) = 3
        local_sym_count = 3
        shdr_symtab = struct.pack(_shdr_fmt,
            idx_symtab, SHT_SYMTAB, 0,
            0, symtab_offset, symtab_size,
            5, local_sym_count, 8, ELF64_SYM_SIZE)  # sh_link=5 -> .strtab, sh_info=local_sym_count
        shdr_strtab = struct.pack(_shdr_fmt,
            idx_strtab, SHT_STRTAB, 0,
            0, strtab_offset, len(strtab), 0, 0, 1, 0)
        shdr_shstrtab = struct.pack(_shdr_fmt,
            idx_shstrtab, SHT_STRTAB, 0,
            0, shstrtab_offset, len(shstrtab), 0, 0, 1, 0)
        shdr_note = struct.pack(_shdr_fmt,
            idx_note, SHT_NOTE, 0,
            0, note_offset, len(note_content), 0, 0, 1, 0)

        # 组装
        result = bytearray(ehdr)
        result.extend(code)                # .text
        result.extend(data)                # .data
        result.extend(rela_text)          # .rela.text
        result.extend(b"".join(symbols)) # .symtab
        result.extend(strtab)             # .strtab
        result.extend(shstrtab)           # .shstrtab
        result.extend(note_content)       # .note.GNU-stack
        result.extend(b"\x00" * sh_padding)  # 对齐填充
        result.extend(shdr_null)
        result.extend(shdr_text)
        result.extend(shdr_data)
        result.extend(shdr_rela_text)
        result.extend(shdr_symtab)
        result.extend(shdr_strtab)
        result.extend(shdr_shstrtab)
        result.extend(shdr_note)

        return bytes(result)

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

    def compile_and_write(
        self,
        lir_module: LIRModule,
        output_path: str,
        use_gcc_link: bool = False,
        runtime_lib_path: str = None,
    ):
        """编译并写入可执行文件。

        参数:
            lir_module: LIR 模块
            output_path: 输出文件路径
            use_gcc_link: 若为 True，生成 .o 文件后用 gcc 链接运行时库。
                链接顺序：nova 生成的 .o + libnova_runtime.a + -lm -lc -ldl
            runtime_lib_path: 运行时静态库路径。若为 None 则在
                runtime/ 目录下自动查找 libnova_runtime.a。
        """
        if use_gcc_link:
            return self._compile_via_gcc(lir_module, output_path, runtime_lib_path)

        # 独立 ELF 模式（零依赖）
        elf = self.compile(lir_module, output_format="elf")
        with open(output_path, "wb") as f:
            f.write(elf)
        os.chmod(output_path, 0o755)
        return output_path

    def _compile_via_gcc(
        self,
        lir_module: LIRModule,
        output_path: str,
        runtime_lib_path: str = None,
    ) -> str:
        """通过 gcc 链接生成可执行文件。

        流程：
        1. 生成可重定位 .o 文件（output_format="obj"）
        2. 查找运行时静态库 libnova_runtime.a
        3. 调用 gcc 进行链接：gcc nova.o libnova_runtime.a -o output -lm -lc -ldl
        4. 清理临时文件
        """
        # 1. 查找 gcc
        gcc = shutil.which("gcc") or shutil.which("cc")
        if not gcc:
            raise EnvironmentError(
                "未找到 gcc/cc，无法进行链接。"
                "请安装 gcc 或使用 compile_and_write(use_gcc_link=False)。"
            )

        # 2. 查找运行时库
        if runtime_lib_path is None:
            # 在 nova 包的 runtime/ 目录下查找
            nova_pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            candidate = os.path.join(nova_pkg_dir, "runtime", "libnova_runtime.a")
            if os.path.isfile(candidate):
                runtime_lib_path = candidate
            else:
                raise FileNotFoundError(
                    f"未找到运行时库: {candidate}\n"
                    f"请先编译运行时库: cd runtime && make"
                )

        # 3. 生成 .o 文件（临时目录）
        obj_bytes = self.compile(lir_module, output_format="obj")
        with tempfile.TemporaryDirectory(prefix="nova_") as tmpdir:
            obj_path = os.path.join(tmpdir, "nova_output.o")
            with open(obj_path, "wb") as f:
                f.write(obj_bytes)

            # 4. 调用 gcc 链接
            cmd = [
                gcc,
                "-nostartfiles",  # 不链接 C 运行时启动文件，避免 _start 冲突
                obj_path,
                runtime_lib_path,
                "-o", output_path,
                "-lm",    # 数学库
                "-lc",    # C 标准库
                "-ldl",   # 动态链接
                "-no-pie",  # 禁用 PIE（与 _start 入口兼容）
            ]
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        f"gcc 链接失败（exit code {result.returncode}）:\n"
                        f"命令: {' '.join(cmd)}\n"
                        f"stderr: {result.stderr}"
                    )
            except FileNotFoundError:
                raise EnvironmentError(f"gcc 不存在: {gcc}")
            except subprocess.TimeoutExpired:
                raise RuntimeError("gcc 链接超时（30 秒）")

        os.chmod(output_path, 0o755)
        return output_path
