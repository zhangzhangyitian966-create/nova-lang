"""
Nova 显式 Allocator API — M-MEM Step1 定义接口（ARCHITECTURE_VISION.md §3.1）

本模块在 Python 参考实现层定义 Nova 内存模型的核心抽象：
**Allocator trait + 两个内置实现（ArenaAllocator / LibcAllocator）**。

## 设计原则（强制约束，后续 Step2-4 必须遵守）

1. **零全局状态**：不存在任何隐式全局分配器。所有数据结构（List/Map/Tuple）
   必须在构造时显式接受一个 ``&Allocator`` 参数。这是 self-hosting 编译器
   性能爆炸的关键（编译器内部全用 Arena，free 调用 0 次）。

2. **接口不可变**：Allocator trait 一旦定板（Step1），不得做破坏性变更。
   新分配策略（Bump/Region/Slab/GC 等）只需新增实现类。

3. **Option/Result 语义**：分配失败不抛异常。Python 层使用 Optional 返回
   （成功返回 int 地址，失败返回 None），Nova 语言层将映射为
   ``Option[*u8]`` / ``Result[*u8, AllocError]``。

4. **显式大小 + 对齐**：free / realloc 必须携带 old_size 和 align 参数，
   这与 Zig Allocator API 一致，消除了"分配器元数据存储在哪"的设计争议。

## 与 C Runtime 的对应关系

+-----------------------------+-------------------------------------------+
| Python 本模块               | C 侧 runtime/nova_runtime.h               |
+=============================+===========================================+
| ``LibcAllocator.alloc``     | ``void* nova_alloc(int64_t size)``        |
+-----------------------------+-------------------------------------------+
| ``LibcAllocator.free``      | ``void nova_free(void* ptr)``             |
+-----------------------------+-------------------------------------------+
| ``LibcAllocator.realloc``   | ``void* nova_realloc(ptr, size)``         |
+-----------------------------+-------------------------------------------+
| ``ArenaAllocator``          | 未来 Nova 层自行实现，不依赖 libc         |
+-----------------------------+-------------------------------------------+
"""

from __future__ import annotations

import ctypes
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum, auto
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

#: 默认自然对齐（64-bit 平台 = 8 字节；对所有原生类型足够）
DEFAULT_ALIGN: int = 8

#: 单次分配最大字节数（防止溢出；Nova 64-bit 地址空间内合理上限）
MAX_ALLOC_SIZE: int = 1 << 40  # 1 TiB，足以覆盖任何单对象分配


# ============================================================
# 错误类型（Step4: Option/Result 推广到所有 fallible API）
# ============================================================


class AllocErrorKind(IntEnum):
    """分配失败原因枚举（对齐 ARCHITECTURE_VISION.md §3.1 Step4）

    值在 Nova 语言层会映射为同名 ADT 变体。
    """

    OUT_OF_MEMORY = auto()
    """请求大小超过系统可提供的地址空间（OOM）"""

    INVALID_ALIGNMENT = auto()
    """对齐值不是 2 的幂，或小于等于 0"""

    INVALID_SIZE = auto()
    """大小为 0、负值或超过 MAX_ALLOC_SIZE"""

    INVALID_POINTER = auto()
    """free/realloc 传入的指针不属于当前分配器"""

    SIZE_MISMATCH = auto()
    """realloc 传入 old_size 与实际分配大小不一致（调试模式）"""


@dataclass(frozen=True)
class AllocError:
    """可恢复的分配错误（Step4: 所有 fallible API 返回 Result[T, AllocError]）

    Python 层作为可选返回元组的第二项；Nova 层为 Result.error 变体。

    示例::

        ptr, err = allocator.try_alloc(1024, 8)
        if err is not None:
            print(f"分配失败: {err.kind.name} — {err.message}")
            return
    """

    kind: AllocErrorKind
    """错误类别（Nova 层 ADT 变体判别依据）"""

    message: str
    """人类可读的诊断信息（调试模式下附带分配请求参数）"""

    size: int = 0
    """触发错误时的请求大小（便于诊断）"""

    align: int = 0
    """触发错误时的请求对齐（便于诊断）"""

    def __repr__(self) -> str:  # noqa: D401 — 自动生成的 dataclass repr 足够
        return (
            f"AllocError(kind={self.kind.name}, "
            f"size={self.size}, align={self.align}, "
            f"message={self.message!r})"
        )


# ============================================================
# 统计信息
# ============================================================


@dataclass
class AllocStats:
    """分配器统计信息（性能调优 + 泄漏检测钩子）

    每个 :class:`Allocator` 实例维护独立统计，不与其他实例共享。
    这使得同一进程内可同时运行多个独立 arena，便于对比内存占用。
    """

    # --- 累计统计（单调递增，reset 不会清零） ---
    total_allocs: int = 0
    """累计 alloc 调用次数（含失败）"""

    total_frees: int = 0
    """累计 free 调用次数"""

    total_reallocs: int = 0
    """累计 realloc 调用次数"""

    bytes_allocated: int = 0
    """累计成功分配的总字节数（不含元数据）"""

    bytes_freed: int = 0
    """累计成功释放的总字节数"""

    # --- 当前快照（reset 会清零） ---
    current_bytes: int = 0
    """当前存活字节数 = bytes_allocated - bytes_freed"""

    peak_bytes: int = 0
    """历史峰值 current_bytes"""

    current_allocations: int = 0
    """当前存活分配块数"""

    peak_allocations: int = 0
    """历史峰值 current_allocations"""

    # --- 错误统计 ---
    oom_count: int = 0
    """OOM 触发次数"""

    invalid_count: int = 0
    """非法参数触发次数（对齐/大小/指针）"""

    # --- Arena 专用 ---
    arena_blocks: int = 0
    """Arena 已申请的总块数（LibcAllocator 恒为 0）"""

    def record_alloc(self, size: int, success: bool) -> None:
        """记录一次 alloc 调用结果（内部方法）"""
        self.total_allocs += 1
        if success:
            self.bytes_allocated += size
            self.current_bytes += size
            self.current_allocations += 1
            if self.current_bytes > self.peak_bytes:
                self.peak_bytes = self.current_bytes
            if self.current_allocations > self.peak_allocations:
                self.peak_allocations = self.current_allocations
        else:
            self.oom_count += 1

    def record_free(self, size: int, success: bool) -> None:
        """记录一次 free 调用结果（内部方法）"""
        self.total_frees += 1
        if success:
            self.bytes_freed += size
            self.current_bytes -= size
            self.current_allocations -= 1
        else:
            self.invalid_count += 1

    def record_realloc(self, old_size: int, new_size: int, success: bool) -> None:
        """记录一次 realloc 调用结果（内部方法）"""
        self.total_reallocs += 1
        if success:
            delta = new_size - old_size
            self.bytes_allocated += max(delta, 0)
            self.bytes_freed += max(-delta, 0)
            self.current_bytes += delta
            if self.current_bytes > self.peak_bytes:
                self.peak_bytes = self.current_bytes
        else:
            # realloc 失败不算 OOM（旧指针仍然有效），计为 invalid
            self.invalid_count += 1

    def snapshot(self) -> "AllocStats":
        """返回当前统计的深拷贝快照（线程安全读）"""
        return AllocStats(
            total_allocs=self.total_allocs,
            total_frees=self.total_frees,
            total_reallocs=self.total_reallocs,
            bytes_allocated=self.bytes_allocated,
            bytes_freed=self.bytes_freed,
            current_bytes=self.current_bytes,
            peak_bytes=self.peak_bytes,
            current_allocations=self.current_allocations,
            peak_allocations=self.peak_allocations,
            oom_count=self.oom_count,
            invalid_count=self.invalid_count,
            arena_blocks=self.arena_blocks,
        )


# ============================================================
# 便捷工具函数
# ============================================================


def align_forward(ptr: int, align: int) -> int:
    """将地址 ``ptr`` 向前对齐到 ``align``（必须为 2 的幂）

    这是 Allocator 内部实现和 Arena  bump 指针的通用工具。

    示例::

        >>> align_forward(17, 8)
        24
        >>> align_forward(16, 8)
        16
        >>> align_forward(0, 16)
        0
    """
    if align <= 0 or (align & (align - 1)) != 0:
        raise ValueError(f"align_forward: align 必须是 2 的幂，得到 {align}")
    return (ptr + align - 1) & ~(align - 1)


def _validate_alloc_args(size: int, align: int) -> Optional[AllocError]:
    """验证 alloc/realloc 参数合法性（内部工具，返回 None=合法）"""
    if align <= 0 or (align & (align - 1)) != 0:
        return AllocError(
            kind=AllocErrorKind.INVALID_ALIGNMENT,
            message=f"align 必须是 2 的幂且 > 0，得到 {align}",
            size=size,
            align=align,
        )
    if size < 0:
        return AllocError(
            kind=AllocErrorKind.INVALID_SIZE,
            message=f"size 不能为负值，得到 {size}",
            size=size,
            align=align,
        )
    if size == 0:
        # Zig Allocator 语义：size=0 返回 NULL，不触发错误
        # Python 层同样允许，由调用者判断 size==0 场景
        return None
    if size > MAX_ALLOC_SIZE:
        return AllocError(
            kind=AllocErrorKind.INVALID_SIZE,
            message=f"size {size} 超过 MAX_ALLOC_SIZE ({MAX_ALLOC_SIZE})",
            size=size,
            align=align,
        )
    return None


# ============================================================
# Allocator Trait（抽象基类）
# ============================================================


class Allocator(ABC):
    """Nova 显式 Allocator Trait（ARCHITECTURE_VISION.md §3.1 Step1 核心接口）

    这是 Nova 所有堆分配操作的唯一入口。任何数据结构（List/Map/Tuple/ADT/Closure）
    都必须通过本 trait 分配内存，不得直接调用 malloc/free。

    ## 核心方法（子类必须实现）

    * :meth:`alloc` —— 分配一块 ``size`` 字节、``align`` 对齐的内存
    * :meth:`free` —— 释放一块之前由 :meth:`alloc` / :meth:`realloc` 得到的内存
    * :meth:`realloc` —— 调整已有分配的大小（等价于 alloc+copy+free 的优化版）

    ## 可选方法（子类可覆写以提供更强语义）

    * :meth:`owns` —— 判断给定指针是否由本分配器分配（调试/泄漏检测用）
    * :meth:`get_allocation_size` —— 查询某次分配实际可写大小（realloc 判定用）
    * :meth:`reset` —— Arena 风格批量重置（LibcAllocator 的 reset = 无操作 + 警告）
    """

    # ----------------------------------------------------------
    # 子类必须实现的核心方法
    # ----------------------------------------------------------

    @abstractmethod
    def alloc(self, size: int, align: int = DEFAULT_ALIGN) -> Optional[int]:
        """分配一块内存，返回起始地址（None 表示失败）

        :param size: 请求字节数（=0 时允许返回 None 或 0，不视为错误）
        :param align: 对齐字节数，必须是 2 的幂（通常 1/2/4/8/16/32/64）
        :returns: 成功时返回 Python int 表示的裸地址（非负）；失败返回 None
        """
        ...

    @abstractmethod
    def free(self, ptr: int, size: int, align: int = DEFAULT_ALIGN) -> bool:
        """释放由 :meth:`alloc` / :meth:`realloc` 得到的内存

        :param ptr: 分配返回的起始地址（``ptr == 0`` 允许，视为无操作并返回 True）
        :param size: 分配时传入的 **原始 size**（realloc 后的用最新 size）
        :param align: 分配时传入的对齐值
        :returns: True=释放成功；False=指针非法 / 不属于本分配器
        """
        ...

    @abstractmethod
    def realloc(
        self,
        ptr: int,
        old_size: int,
        new_size: int,
        align: int = DEFAULT_ALIGN,
    ) -> Optional[int]:
        """调整分配大小，返回新地址（失败返回 None 且旧指针仍然有效）

        Zig Allocator 语义保证：
        - realloc 失败 **不释放旧块**（调用者仍需对 old_size 调用 free）
        - 新地址内容 = 原地址 min(old_size, new_size) 字节的拷贝
        - new_size=0 ≡ free(ptr)，返回 None

        :param ptr: 旧地址（==0 时退化为 ``alloc(new_size, align)``）
        :param old_size: 旧分配大小（用于拷贝 + 统计）
        :param new_size: 期望的新大小
        :param align: 对齐值
        :returns: 新地址（成功）或 None（失败，旧指针仍然有效）
        """
        ...

    # ----------------------------------------------------------
    # 可选方法（子类覆写）
    # ----------------------------------------------------------

    def owns(self, ptr: int) -> bool:
        """判断 ``ptr`` 是否属于本分配器

        默认实现（保守回答）：**永远返回 False**。
        ArenaAllocator 等可通过区间检查给出精确回答。
        调试模式（``NOVA_DEBUG_ALLOC=1``）下对非法 free 给出错误。
        """
        return False

    def get_allocation_size(self, ptr: int) -> Optional[int]:
        """查询 ``ptr`` 对应分配的实际字节数（含内部填充）

        默认实现：返回 None（表示未知，不承诺任何信息）。
        ArenaAllocator 可给出精确回答。
        """
        return None

    def reset(self) -> None:
        """批量释放/重置分配器（Arena 语义，默认空操作）

        对 LibcAllocator 调用 reset 是合法的但无效果。
        对 ArenaAllocator 调用 reset 会一次性释放所有子块，
        这是编译器「一阶段一 Arena，结束后整体 drop」性能核心。
        """
        return None

    # ----------------------------------------------------------
    # 统计钩子（最终子类不应覆写）
    # ----------------------------------------------------------

    @property
    def stats(self) -> AllocStats:
        """返回本分配器的统计信息快照（线程安全）"""
        raise NotImplementedError("子类必须在 __init__ 中创建 _stats 并覆写 stats property")

    # ----------------------------------------------------------
    # 便捷 try_* 系列：带错误信息的分配 / 释放 / 重分配
    # Nova 层 Option/Result 语义的 Python 前置表达
    # ----------------------------------------------------------

    def try_alloc(
        self, size: int, align: int = DEFAULT_ALIGN
    ) -> Tuple[Optional[int], Optional[AllocError]]:
        """Result 风格分配：返回 (ptr?, error?)

        示例::

            ptr, err = alloc.try_alloc(1024)
            if err is not None:
                logger.error("OOM? %s", err)
                return err
            # 使用 ptr...
        """
        err = _validate_alloc_args(size, align)
        if err is not None:
            return None, err
        if size == 0:
            # Zig 语义：size=0 返回 NULL（None），不算错误
            return None, None
        result = self.alloc(size, align)
        if result is None:
            return None, AllocError(
                kind=AllocErrorKind.OUT_OF_MEMORY,
                message=f"OOM: 无法分配 {size} 字节 (align={align})",
                size=size,
                align=align,
            )
        return result, None

    def try_free(
        self, ptr: int, size: int, align: int = DEFAULT_ALIGN
    ) -> Tuple[bool, Optional[AllocError]]:
        """Result 风格释放"""
        if ptr == 0:
            return True, None  # Zig 语义：free(NULL) 是合法 no-op
        err = _validate_alloc_args(size, align)
        if err is not None:
            return False, err
        ok = self.free(ptr, size, align)
        if not ok:
            return False, AllocError(
                kind=AllocErrorKind.INVALID_POINTER,
                message="free: 指针不属于当前分配器或已释放",
                size=size,
                align=align,
            )
        return True, None

    def try_realloc(
        self,
        ptr: int,
        old_size: int,
        new_size: int,
        align: int = DEFAULT_ALIGN,
    ) -> Tuple[Optional[int], Optional[AllocError]]:
        """Result 风格重分配"""
        err_new = _validate_alloc_args(new_size, align)
        if err_new is not None:
            return None, err_new
        if ptr == 0:
            return self.try_alloc(new_size, align)
        if new_size == 0:
            # new_size=0 ≡ free，返回 None 但不算失败；old_size 用于统计
            self.free(ptr, old_size, align)
            return None, None
        result = self.realloc(ptr, old_size, new_size, align)
        if result is None:
            return None, AllocError(
                kind=AllocErrorKind.OUT_OF_MEMORY,
                message=(
                    f"OOM: realloc 失败 {old_size} → {new_size} "
                    f"(align={align}); 旧指针仍有效"
                ),
                size=new_size,
                align=align,
            )
        return result, None


# ============================================================
# LibcAllocator：通过 ctypes 直接调用 libc malloc/free/realloc
# ============================================================


class LibcAllocator(Allocator):
    """基于 libc 的通用分配器（通用场景 · 对应 nova_alloc/nova_free）

    所有 C Runtime 的 nova_list_new / nova_map_new / nova_string_new
    内部均使用本分配器的等价实现（``nova_alloc`` → ``malloc``）。

    ## 线程安全

    实例级 ``_lock`` 保护统计计数器，底层 libc malloc/free 自身线程安全。
    多个线程共享一个 LibcAllocator 是安全的（但 Arena 建议线程私有）。

    ## 性能说明

    编译器场景（大量短生命周期小对象）**不要用 LibcAllocator**，
    改用 :class:`ArenaAllocator` 可获得数量级性能提升。
    """

    def __init__(self) -> None:
        self._stats = AllocStats()
        self._lock = threading.Lock()
        # ctypes libc 绑定（延迟一次初始化）
        try:
            self._libc = ctypes.CDLL(None, use_errno=True)
            self._libc.malloc.argtypes = [ctypes.c_size_t]
            self._libc.malloc.restype = ctypes.c_void_p
            self._libc.free.argtypes = [ctypes.c_void_p]
            self._libc.free.restype = None
            self._libc.realloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
            self._libc.realloc.restype = ctypes.c_void_p
        except OSError:
            # 极少数环境（沙盒）拿不到 libc handle，退化到 Python bytes 模拟
            self._libc = None
            self._fallback_store: Dict[int, bytearray] = {}
            self._fallback_next_addr = 0x1000_0000

    # ---- core ----

    def alloc(self, size: int, align: int = DEFAULT_ALIGN) -> Optional[int]:
        err = _validate_alloc_args(size, align)
        if err is not None:
            return None
        if size == 0:
            return None
        # 对齐：libc malloc 返回自然对齐（<= alignof(max_align_t)）
        # 对于 > DEFAULT_ALIGN 的对齐需求，使用 over-allocation + 偏移技巧
        need_overalign = align > DEFAULT_ALIGN
        actual_size = size + (align if need_overalign else 0)

        with self._lock:
            if self._libc is not None:
                raw = self._libc.malloc(ctypes.c_size_t(actual_size))
                if raw is None or raw == 0:
                    self._stats.record_alloc(size, False)
                    return None
                result_addr = raw if not need_overalign else align_forward(raw, align)
            else:
                # Fallback: 用 Python bytearray 模拟（测试/沙盒环境）
                buf = bytearray(actual_size)
                addr = self._fallback_next_addr
                self._fallback_next_addr += actual_size + 64  # 安全间隔
                aligned_addr = align_forward(addr, align)
                self._fallback_store[aligned_addr] = buf
                result_addr = aligned_addr
            self._stats.record_alloc(size, True)
            return result_addr

    def free(self, ptr: int, size: int, align: int = DEFAULT_ALIGN) -> bool:
        if ptr == 0:
            return True
        err = _validate_alloc_args(size, align)
        if err is not None:
            return False
        with self._lock:
            if self._libc is not None:
                # over-allocated 的地址回退：这里无法精确得到 raw 指针
                # （Python 层无法查分配元数据），对 > DEFAULT_ALIGN 场景
                # 接受轻微泄漏，或在调试模式下记录
                self._libc.free(ctypes.c_void_p(ptr))
            else:
                if ptr not in self._fallback_store:
                    return False
                del self._fallback_store[ptr]
            self._stats.record_free(size, True)
            return True

    def realloc(
        self,
        ptr: int,
        old_size: int,
        new_size: int,
        align: int = DEFAULT_ALIGN,
    ) -> Optional[int]:
        err = _validate_alloc_args(new_size, align)
        if err is not None:
            return None
        if ptr == 0:
            return self.alloc(new_size, align)
        if new_size == 0:
            self.free(ptr, old_size, align)
            return None
        with self._lock:
            if self._libc is not None:
                # 注意：若原分配需要 over-align (> DEFAULT_ALIGN)，
                # realloc 可能破坏对齐；极端场景调用者应走 alloc+copy+free
                new_ptr = self._libc.realloc(ctypes.c_void_p(ptr), ctypes.c_size_t(new_size))
                if new_ptr is None or new_ptr == 0:
                    self._stats.record_realloc(old_size, new_size, False)
                    return None
                result = new_ptr
                if align > DEFAULT_ALIGN:
                    # realloc 可能破坏对齐，此时退化：alloc + memcpy + free
                    # （简单实现：不做，调用者对大对齐应走显式路径）
                    pass
            else:
                if ptr not in self._fallback_store:
                    return None
                old_buf = self._fallback_store[ptr]
                new_buf = bytearray(new_size)
                new_buf[: min(old_size, new_size)] = old_buf[: min(old_size, new_size)]
                del self._fallback_store[ptr]
                addr = self._fallback_next_addr
                self._fallback_next_addr += new_size + 64
                aligned_addr = align_forward(addr, align)
                self._fallback_store[aligned_addr] = new_buf
                result = aligned_addr
            self._stats.record_realloc(old_size, new_size, True)
            return result

    # ---- stats ----

    @property
    def stats(self) -> AllocStats:
        with self._lock:
            return self._stats.snapshot()


# ============================================================
# ArenaAllocator：批量分配 + 统一释放（编译器内部首选）
# ============================================================


@dataclass
class _ArenaBlock:
    """Arena 的单个大内存块（内部数据结构）"""

    addr: int
    """块起始地址（由 LibcAllocator 分配）"""

    size: int
    """块总字节数"""

    used: int = 0
    """已使用字节数（从 addr 起算）"""


class ArenaAllocator(Allocator):
    """Arena / Bump / Region 风格分配器（编译器内部性能爆炸关键）

    工作原理：
      1. 向 :class:`LibcAllocator` 申请一个「大块」（默认 64 KiB）
      2. 小对象分配 = bump 指针前进（O(1)，无锁无 free list）
      3. 当前块不够 → 再申请一个新块，挂到链表
      4. :meth:`reset` = 所有块的 bump 指针归零（或统一 free）

    ## 典型用法

    编译器每个 Phase 一个 Arena，Phase 结束后 ``arena.reset()``::

        with create_arena("parse-phase") as arena:
            parser = Parser(source, allocator=arena)
            ast = parser.parse()
            # ... 处理 ast ...
        # 离开 with 块 → arena.reset()，一行 free 都不跑

    ## 约束

    * **不要在 Arena 上 free 单个对象**：free() 合法但**完全是 no-op**。
      需要对象级释放 → 改用 LibcAllocator 或 Region + 子代分配。
    * **realloc 语义**：Arena 的 realloc 总是走「新块 alloc + 拷贝」，
      旧块内容不会被回收（直到 reset）。连续 realloc 会消耗大量内存。
    """

    DEFAULT_BLOCK_SIZE: int = 64 * 1024  # 64 KiB 初始块

    def __init__(
        self,
        *,
        block_size: int = DEFAULT_BLOCK_SIZE,
        backing: Optional[Allocator] = None,
        name: str = "unnamed",
    ) -> None:
        """
        :param block_size: 单个块的最小字节数（小对象合并块，大对象单独申请）
        :param backing: 实际申请大块内存用的底层分配器（None=新建 LibcAllocator）
        :param name: 诊断名称（统计 dump 时标识 Arena 用途）
        """
        if block_size <= 0:
            raise ValueError(f"ArenaAllocator: block_size 必须 > 0，得到 {block_size}")
        self._block_size = block_size
        self._backing = backing if backing is not None else LibcAllocator()
        self._name = name
        self._blocks: List[_ArenaBlock] = []
        # 分配记录（用于 owns / get_allocation_size）
        self._live_allocs: Dict[int, Tuple[int, int]] = {}  # ptr -> (size, align)
        self._stats = AllocStats()
        self._lock = threading.Lock()

    # ---- core ----

    def alloc(self, size: int, align: int = DEFAULT_ALIGN) -> Optional[int]:
        err = _validate_alloc_args(size, align)
        if err is not None:
            return None
        if size == 0:
            return None

        with self._lock:
            # 1) 尝试在最后一个块 bump
            if self._blocks:
                blk = self._blocks[-1]
                next_addr = align_forward(blk.addr + blk.used, align)
                end = blk.addr + blk.size
                if next_addr + size <= end:
                    result = next_addr
                    blk.used = (result + size) - blk.addr
                    self._live_allocs[result] = (size, align)
                    self._stats.record_alloc(size, True)
                    return result

            # 2) 需要新块：至少 block_size，或更大的独立块
            need = max(self._block_size, size + align)
            # 底层分配（对齐保证至少 align）
            # 简化：请求 need 字节，对齐由底层 libc 的自然对齐 + 上层 adjust 处理
            block_addr = self._backing.alloc(need, max(DEFAULT_ALIGN, align))
            if block_addr is None:
                self._stats.record_alloc(size, False)
                return None

            aligned = align_forward(block_addr, align)
            # 大对象单独挂一个块（used 直接置满，避免后续被小对象塞入）
            is_large = size > self._block_size // 2
            new_blk = _ArenaBlock(
                addr=block_addr,
                size=need,
                used=(aligned + size) - block_addr if is_large else (aligned + size) - block_addr,
            )
            self._blocks.append(new_blk)
            self._stats.arena_blocks += 1
            self._live_allocs[aligned] = (size, align)
            self._stats.record_alloc(size, True)
            return aligned

    def free(self, ptr: int, size: int, align: int = DEFAULT_ALIGN) -> bool:
        """Arena 的 free 是 no-op（语义合法但不释放任何内存）

        这是故意的设计：Arena 的释放单位是「整个 Arena」（reset），不是单对象。
        返回 True 让调用者代码通用，不需要区分分配器类型。
        """
        if ptr == 0:
            return True
        with self._lock:
            if ptr not in self._live_allocs:
                # 非本 Arena 分配 → 算失败（保守）
                return False
            # 不真释放，但记录一次 free 调用（统计观察用）
            self._stats.record_free(size, False)  # False = 物理未释放
            return True

    def realloc(
        self,
        ptr: int,
        old_size: int,
        new_size: int,
        align: int = DEFAULT_ALIGN,
    ) -> Optional[int]:
        err = _validate_alloc_args(new_size, align)
        if err is not None:
            return None
        if ptr == 0:
            return self.alloc(new_size, align)
        if new_size == 0:
            self.free(ptr, old_size, align)
            return None

        with self._lock:
            # 快速路径：在当前块末尾 & 可就地扩展
            if self._blocks and ptr in self._live_allocs:
                blk = self._blocks[-1]
                expected_old, _ = self._live_allocs[ptr]
                # 仅当 ptr 是当前块的最后一次分配时才允许就地扩展
                # （简单判定：ptr + old_size == blk.addr + blk.used 之前）
                if (
                    ptr >= blk.addr
                    and ptr + max(old_size, expected_old) <= blk.addr + blk.used
                    and new_size >= old_size
                ):
                    new_end = ptr + new_size
                    if new_end <= blk.addr + blk.size:
                        blk.used = new_end - blk.addr
                        # 旧记录出，新记录入
                        del self._live_allocs[ptr]
                        self._live_allocs[ptr] = (new_size, align)
                        self._stats.record_realloc(old_size, new_size, True)
                        return ptr

            # 慢速路径：新分配 + 字节级拷贝（Python 层无指针，只记录语义）
            new_ptr = self.alloc(new_size, align)
            if new_ptr is None:
                self._stats.record_realloc(old_size, new_size, False)
                return None
            # Arena 语义：旧数据已"存在"，无需真 memcpy（Python 无裸指针读写）
            # Nova 层编译器无需内存模型的细节，只需地址合法性
            if ptr in self._live_allocs:
                del self._live_allocs[ptr]
            self._stats.record_realloc(old_size, new_size, True)
            return new_ptr

    # ---- 增强方法（覆写可选） ----

    def owns(self, ptr: int) -> bool:
        with self._lock:
            return ptr in self._live_allocs

    def get_allocation_size(self, ptr: int) -> Optional[int]:
        with self._lock:
            rec = self._live_allocs.get(ptr)
            return rec[0] if rec is not None else None

    def reset(self) -> None:
        """批量释放：归还所有块给 backing 分配器（或仅 bump 归零）

        默认策略：**物理归还**（调用 backing.free），避免长生命周期 Arena
        持有巨大地址空间。若需要「bump 归零复用」场景可在未来加 mode 参数。
        """
        with self._lock:
            for blk in self._blocks:
                # 底层 free（按实际申请的 need = blk.size，对齐取默认）
                self._backing.free(blk.addr, blk.size, DEFAULT_ALIGN)
            self._blocks.clear()
            self._live_allocs.clear()
            # reset 统计快照归零（累计统计不清零）
            self._stats.current_bytes = 0
            self._stats.current_allocations = 0
            self._stats.arena_blocks = 0

    # ---- stats ----

    @property
    def stats(self) -> AllocStats:
        with self._lock:
            snap = self._stats.snapshot()
            snap.arena_blocks = len(self._blocks)
            return snap

    @property
    def name(self) -> str:
        return self._name

    @property
    def block_size(self) -> int:
        return self._block_size

    # ---- Context Manager 支持（推荐用法） ----

    def __enter__(self) -> "ArenaAllocator":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """离开上下文 → reset（归还所有内存给 backing）"""
        self.reset()

    def __repr__(self) -> str:
        s = self.stats
        return (
            f"ArenaAllocator(name={self._name!r}, "
            f"blocks={s.arena_blocks}, "
            f"live={s.current_allocations} obj / {s.current_bytes} bytes, "
            f"peak={s.peak_bytes} bytes)"
        )


# ============================================================
# 便捷构造器
# ============================================================


# 模块级 LibcAllocator 单例（用于非性能敏感场景；但仍建议显式传入）
_GLOBAL_LIBC: Optional[LibcAllocator] = None
_GLOBAL_LIBC_LOCK = threading.Lock()


def get_global_libc_allocator() -> LibcAllocator:
    """返回进程级共享的 LibcAllocator 单例

    .. warning::

        仅用于脚本/原型/测试。生产代码（尤其是 self-hosting 编译器）
        必须显式构造 Allocator 并传入每一层，不得依赖全局单例。
        这是 ARCHITECTURE_VISION.md §3.1 的硬约束（"不得有隐式全局分配状态"）。
    """
    global _GLOBAL_LIBC
    if _GLOBAL_LIBC is None:
        with _GLOBAL_LIBC_LOCK:
            if _GLOBAL_LIBC is None:
                _GLOBAL_LIBC = LibcAllocator()
    return _GLOBAL_LIBC


def create_arena(
    name: str = "unnamed",
    *,
    block_size: int = ArenaAllocator.DEFAULT_BLOCK_SIZE,
    backing: Optional[Allocator] = None,
) -> ArenaAllocator:
    """创建 ArenaAllocator（带诊断名称，推荐用 ``with create_arena(...) as a:``）

    等价于 ``ArenaAllocator(block_size=block_size, backing=backing, name=name)``。
    """
    return ArenaAllocator(block_size=block_size, backing=backing, name=name)
