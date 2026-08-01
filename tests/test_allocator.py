"""
Nova 显式 Allocator API 单元测试（runtime/allocator.py 全面覆盖）

覆盖：
  1. 常量与工具函数（align_forward / _validate_alloc_args）
  2. 错误类型（AllocErrorKind / AllocError）
  3. 统计信息（AllocStats record_alloc/free/realloc/snapshot）
  4. LibcAllocator（alloc/free/realloc/try_*/stats/owns/get_allocation_size/reset）
  5. ArenaAllocator（bump分配 / free no-op / realloc / owns / reset / ContextManager）
  6. NovaBox（make/drop/get/set/clone/use-after-drop / __eq__ / __repr__）
  7. 便捷函数（get_global_libc_allocator / create_arena / box_value / unbox_value / set_box_value）

设计原则：
  - 测试互相独立（每个用例创建新 allocator，避免共享状态）
  - 避免依赖真实 libc 的精确地址值（只校验非空/对齐/统计）
  - 沙盒环境下 LibcAllocator 拿不到 libc handle 时走 Fallback 路径，测试同样适用
"""

from __future__ import annotations

import threading
import unittest
from typing import Optional

from nova.runtime.allocator import (
    DEFAULT_ALIGN,
    MAX_ALLOC_SIZE,
    AllocError,
    AllocErrorKind,
    AllocStats,
    Allocator,
    ArenaAllocator,
    LibcAllocator,
    NovaBox,
    align_forward,
    box_value,
    create_arena,
    get_global_libc_allocator,
    set_box_value,
    unbox_value,
)


# ============================================================
# 1. 常量与工具函数
# ============================================================
class TestConstantsAndUtils(unittest.TestCase):
    """常量定义 + align_forward + 参数合法性校验"""

    def test_default_align_is_8(self):
        """64-bit 平台自然对齐应为 8 字节"""
        self.assertEqual(DEFAULT_ALIGN, 8)

    def test_max_alloc_size_is_1tib(self):
        """MAX_ALLOC_SIZE = 1 << 40 = 1 TiB"""
        self.assertEqual(MAX_ALLOC_SIZE, 1 << 40)

    # ----------------------------------------------------------
    # align_forward
    # ----------------------------------------------------------
    def test_align_forward_aligned_no_change(self):
        """已对齐的地址不应被改变"""
        self.assertEqual(align_forward(16, 8), 16)
        self.assertEqual(align_forward(0, 16), 0)
        self.assertEqual(align_forward(32, 1), 32)

    def test_align_forward_rounds_up(self):
        """不对齐的地址应向上取整"""
        self.assertEqual(align_forward(17, 8), 24)
        self.assertEqual(align_forward(1, 16), 16)
        self.assertEqual(align_forward(7, 4), 8)
        self.assertEqual(align_forward(63, 64), 64)

    def test_align_forward_rejects_non_power_of_two(self):
        """非 2 的幂对齐应抛 ValueError"""
        with self.assertRaises(ValueError):
            align_forward(10, 3)
        with self.assertRaises(ValueError):
            align_forward(10, 0)
        with self.assertRaises(ValueError):
            align_forward(10, -4)


# ============================================================
# 2. 错误类型
# ============================================================
class TestAllocError(unittest.TestCase):
    """AllocErrorKind + AllocError dataclass"""

    def test_error_kind_values(self):
        """5 种错误类别枚举值应互不相同且 > 0"""
        kinds = [
            AllocErrorKind.OUT_OF_MEMORY,
            AllocErrorKind.INVALID_ALIGNMENT,
            AllocErrorKind.INVALID_SIZE,
            AllocErrorKind.INVALID_POINTER,
            AllocErrorKind.SIZE_MISMATCH,
        ]
        unique = set(int(k) for k in kinds)
        self.assertEqual(len(unique), 5, "错误枚举值应互不相同")
        for k in kinds:
            self.assertGreater(int(k), 0, "枚举值应为正数")
        # 校验命名
        self.assertEqual(AllocErrorKind.OUT_OF_MEMORY.name, "OUT_OF_MEMORY")
        self.assertEqual(AllocErrorKind.INVALID_ALIGNMENT.name, "INVALID_ALIGNMENT")

    def test_alloc_error_construction(self):
        """AllocError dataclass 字段应正确记录"""
        err = AllocError(
            kind=AllocErrorKind.INVALID_ALIGNMENT,
            message="align 必须是 2 的幂",
            size=1024,
            align=3,
        )
        self.assertIs(err.kind, AllocErrorKind.INVALID_ALIGNMENT)
        self.assertEqual(err.message, "align 必须是 2 的幂")
        self.assertEqual(err.size, 1024)
        self.assertEqual(err.align, 3)

    def test_alloc_error_repr_contains_kind(self):
        """__repr__ 输出应包含 kind 名和诊断信息"""
        err = AllocError(kind=AllocErrorKind.OUT_OF_MEMORY, message="OOM", size=10, align=8)
        s = repr(err)
        self.assertIn("OUT_OF_MEMORY", s)
        self.assertIn("size=10", s)
        self.assertIn("align=8", s)
        self.assertIn("OOM", s)


# ============================================================
# 3. AllocStats 统计信息
# ============================================================
class TestAllocStats(unittest.TestCase):
    """AllocStats 的计数逻辑 + snapshot 深拷贝"""

    def test_initial_state_zero(self):
        """新创建的统计对象所有字段应为 0"""
        s = AllocStats()
        self.assertEqual(s.total_allocs, 0)
        self.assertEqual(s.total_frees, 0)
        self.assertEqual(s.total_reallocs, 0)
        self.assertEqual(s.bytes_allocated, 0)
        self.assertEqual(s.bytes_freed, 0)
        self.assertEqual(s.current_bytes, 0)
        self.assertEqual(s.peak_bytes, 0)
        self.assertEqual(s.current_allocations, 0)
        self.assertEqual(s.peak_allocations, 0)
        self.assertEqual(s.oom_count, 0)
        self.assertEqual(s.invalid_count, 0)
        self.assertEqual(s.arena_blocks, 0)

    def test_record_alloc_success_updates_counters(self):
        """一次成功 alloc 应累计 total/bytes/current，并更新峰值"""
        s = AllocStats()
        s.record_alloc(100, True)
        self.assertEqual(s.total_allocs, 1)
        self.assertEqual(s.bytes_allocated, 100)
        self.assertEqual(s.current_bytes, 100)
        self.assertEqual(s.current_allocations, 1)
        self.assertEqual(s.peak_bytes, 100)
        self.assertEqual(s.peak_allocations, 1)
        self.assertEqual(s.oom_count, 0)

    def test_record_alloc_failure_counts_oom(self):
        """失败 alloc 应计入 oom_count，不影响字节数"""
        s = AllocStats()
        s.record_alloc(1024, False)
        self.assertEqual(s.total_allocs, 1)
        self.assertEqual(s.bytes_allocated, 0)
        self.assertEqual(s.current_bytes, 0)
        self.assertEqual(s.oom_count, 1)

    def test_record_free_success(self):
        """成功 free 应减少 current_bytes / current_allocations"""
        s = AllocStats()
        s.record_alloc(100, True)
        s.record_free(60, True)
        self.assertEqual(s.total_frees, 1)
        self.assertEqual(s.bytes_freed, 60)
        self.assertEqual(s.current_bytes, 40)
        self.assertEqual(s.current_allocations, 0)

    def test_record_free_failure_counts_invalid(self):
        """失败 free 计入 invalid_count，不影响字节"""
        s = AllocStats()
        s.record_free(10, False)
        self.assertEqual(s.total_frees, 1)
        self.assertEqual(s.bytes_freed, 0)
        self.assertEqual(s.invalid_count, 1)

    def test_record_realloc_growth(self):
        """realloc 扩容：new-old 的差额计入 bytes_allocated，current 增长"""
        s = AllocStats()
        s.record_alloc(100, True)
        s.record_realloc(100, 200, True)
        self.assertEqual(s.total_reallocs, 1)
        self.assertEqual(s.bytes_allocated, 200)  # +100 delta
        self.assertEqual(s.bytes_freed, 0)
        self.assertEqual(s.current_bytes, 200)

    def test_record_realloc_shrink(self):
        """realloc 缩容：old-new 的差额计入 bytes_freed，current 减少"""
        s = AllocStats()
        s.record_alloc(200, True)
        s.record_realloc(200, 50, True)
        self.assertEqual(s.bytes_allocated, 200)
        self.assertEqual(s.bytes_freed, 150)
        self.assertEqual(s.current_bytes, 50)

    def test_record_realloc_failure(self):
        """失败 realloc 计入 invalid_count（旧指针仍有效，不算 OOM）"""
        s = AllocStats()
        s.record_realloc(10, 100, False)
        self.assertEqual(s.total_reallocs, 1)
        self.assertEqual(s.invalid_count, 1)

    def test_snapshot_returns_independent_copy(self):
        """snapshot 应返回深拷贝，不与原对象共享引用"""
        s = AllocStats()
        s.record_alloc(50, True)
        snap = s.snapshot()
        # 修改原对象不应影响 snapshot
        s.record_alloc(50, True)
        self.assertEqual(snap.current_bytes, 50, "snapshot 不应跟随原对象更新")
        self.assertEqual(s.current_bytes, 100)

    def test_peak_never_decreases(self):
        """peak_bytes / peak_allocations 是单调递增的历史最大值"""
        s = AllocStats()
        s.record_alloc(100, True)  # peak = 100 / 1
        s.record_free(100, True)  # current = 0 / 0，但 peak 不变
        s.record_alloc(50, True)  # 重新 alloc 50 < 100
        self.assertEqual(s.peak_bytes, 100)
        self.assertEqual(s.peak_allocations, 1)


# ============================================================
# 4. LibcAllocator 基础测试
# ============================================================
class TestLibcAllocator(unittest.TestCase):
    """基于 libc（或 fallback）的通用分配器"""

    def _alloc(self, size: int, align: int = 8) -> Optional[int]:
        return LibcAllocator().alloc(size, align)

    # ----------------------------------------------------------
    # alloc 基本行为
    # ----------------------------------------------------------
    def test_alloc_basic_returns_nonzero(self):
        """成功 alloc 应返回非 0 地址（libc 或 fallback 模式都应满足）"""
        alloc = LibcAllocator()
        ptr = alloc.alloc(64)
        self.assertIsNotNone(ptr)
        self.assertNotEqual(ptr, 0)
        self.assertIsInstance(ptr, int)

    def test_alloc_size_zero_returns_none(self):
        """size=0 按 Zig 语义返回 None（合法 no-op）"""
        ptr = self._alloc(0)
        self.assertIsNone(ptr)

    def test_alloc_invalid_align_returns_none(self):
        """非法对齐值（非 2 的幂）返回 None"""
        self.assertIsNone(self._alloc(64, align=3))
        self.assertIsNone(self._alloc(64, align=0))
        self.assertIsNone(self._alloc(64, align=-8))

    def test_alloc_negative_size_returns_none(self):
        """负数 size 返回 None"""
        self.assertIsNone(self._alloc(-1))

    def test_alloc_over_max_size_returns_none(self):
        """超过 MAX_ALLOC_SIZE 返回 None"""
        self.assertIsNone(self._alloc(MAX_ALLOC_SIZE + 1))

    def test_alloc_address_aligned(self):
        """返回地址应对齐到请求的 align"""
        alloc = LibcAllocator()
        for align in (1, 2, 4, 8, 16, 32, 64):
            ptr = alloc.alloc(128, align=align)
            self.assertIsNotNone(ptr, f"align={align} alloc 应成功")
            self.assertEqual(ptr % align, 0, f"ptr={ptr} 未按 align={align} 对齐")

    # ----------------------------------------------------------
    # free 基本行为
    # ----------------------------------------------------------
    def test_free_null_ptr_is_noop(self):
        """free(0, ...) 是合法 no-op，返回 True"""
        alloc = LibcAllocator()
        self.assertTrue(alloc.free(0, 100))

    def test_free_updates_stats(self):
        """alloc + free 配对后 current_bytes 应归零"""
        alloc = LibcAllocator()
        ptr = alloc.alloc(128)
        self.assertIsNotNone(ptr)
        ok = alloc.free(ptr, 128)
        self.assertTrue(ok)
        s = alloc.stats
        self.assertEqual(s.total_allocs, 1)
        self.assertEqual(s.total_frees, 1)
        self.assertEqual(s.current_bytes, 0, "alloc+free 配对后 current_bytes 应为 0")
        self.assertEqual(s.current_allocations, 0)

    # ----------------------------------------------------------
    # realloc
    # ----------------------------------------------------------
    def test_realloc_null_ptr_equivalent_to_alloc(self):
        """realloc(ptr=0) 等价于 alloc(new_size)"""
        alloc = LibcAllocator()
        ptr = alloc.realloc(0, 0, 256)
        self.assertIsNotNone(ptr)
        self.assertNotEqual(ptr, 0)

    def test_realloc_newsize_zero_equivalent_to_free(self):
        """realloc(ptr, old, 0) ≡ free，返回 None"""
        alloc = LibcAllocator()
        ptr = alloc.alloc(128)
        self.assertIsNotNone(ptr)
        result = alloc.realloc(ptr, 128, 0)
        self.assertIsNone(result, "new_size=0 应 free 并返回 None")

    def test_realloc_grow_returns_valid_ptr(self):
        """扩容 realloc 应返回新的非空地址"""
        alloc = LibcAllocator()
        ptr1 = alloc.alloc(64)
        self.assertIsNotNone(ptr1)
        ptr2 = alloc.realloc(ptr1, 64, 1024)
        self.assertIsNotNone(ptr2, "realloc 扩容应成功")

    # ----------------------------------------------------------
    # try_* Result 风格
    # ----------------------------------------------------------
    def test_try_alloc_success(self):
        """try_alloc 成功时 (ptr, None)"""
        alloc = LibcAllocator()
        ptr, err = alloc.try_alloc(256)
        self.assertIsNotNone(ptr)
        self.assertIsNone(err)

    def test_try_alloc_invalid_align_returns_error(self):
        """非法对齐时 try_alloc 返回 AllocError(INVALID_ALIGNMENT)"""
        alloc = LibcAllocator()
        ptr, err = alloc.try_alloc(64, align=3)
        self.assertIsNone(ptr)
        self.assertIsNotNone(err)
        self.assertIs(err.kind, AllocErrorKind.INVALID_ALIGNMENT)

    def test_try_alloc_size_zero_returns_none_noerror(self):
        """size=0 返回 (None, None)，合法 no-op"""
        alloc = LibcAllocator()
        ptr, err = alloc.try_alloc(0)
        self.assertIsNone(ptr)
        self.assertIsNone(err)

    def test_try_free_null_is_ok(self):
        """try_free(0) 返回 (True, None)"""
        alloc = LibcAllocator()
        ok, err = alloc.try_free(0, 100)
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_try_realloc_invalid_newsize_error(self):
        """try_realloc 非法 new_size 返回 INVALID_SIZE 等错误"""
        alloc = LibcAllocator()
        ptr, err = alloc.try_realloc(0, 0, 1024, align=5)
        self.assertIsNone(ptr)
        self.assertIsNotNone(err)
        self.assertIs(err.kind, AllocErrorKind.INVALID_ALIGNMENT)

    # ----------------------------------------------------------
    # stats 统计正确性
    # ----------------------------------------------------------
    def test_stats_reflect_alloc_free(self):
        """多次 alloc/free 后统计值应正确"""
        alloc = LibcAllocator()
        ptrs = [alloc.alloc(100) for _ in range(5)]
        for p in ptrs:
            alloc.free(p, 100)
        s = alloc.stats
        self.assertEqual(s.total_allocs, 5)
        self.assertEqual(s.total_frees, 5)
        self.assertEqual(s.bytes_allocated, 500)
        self.assertEqual(s.bytes_freed, 500)
        self.assertEqual(s.current_bytes, 0)

    # ----------------------------------------------------------
    # 默认实现的方法
    # ----------------------------------------------------------
    def test_default_owns_always_false(self):
        """Allocator 默认 owns 永远返回 False（保守回答）"""
        alloc = LibcAllocator()
        ptr = alloc.alloc(8)
        # LibcAllocator 未覆写 owns，应保持默认行为
        # （LibcAllocator 确实没覆写 owns，测试设计目标：验证 trait 默认行为）
        base = Allocator
        self.assertFalse(base.owns(alloc, ptr))
        self.assertFalse(base.owns(alloc, 0xDEAD_BEEF))

    def test_reset_is_safe_noop(self):
        """reset 可被安全调用（默认空操作，无异常）"""
        alloc = LibcAllocator()
        alloc.alloc(100)
        # 不应抛异常
        result = alloc.reset()
        self.assertIsNone(result)


# ============================================================
# 5. ArenaAllocator
# ============================================================
class TestArenaAllocator(unittest.TestCase):
    """Arena / Bump 风格分配器"""

    def test_initial_state_no_blocks(self):
        """新创建的 Arena 无分配块、无存活对象"""
        arena = ArenaAllocator(name="test")
        s = arena.stats
        self.assertEqual(s.arena_blocks, 0)
        self.assertEqual(s.current_allocations, 0)
        self.assertEqual(s.current_bytes, 0)
        self.assertEqual(arena.name, "test")

    def test_alloc_returns_aligned_address(self):
        """Arena alloc 应返回对齐地址"""
        arena = ArenaAllocator()
        for align in (1, 2, 4, 8, 16, 32, 64):
            ptr = arena.alloc(64, align=align)
            self.assertIsNotNone(ptr)
            self.assertEqual(ptr % align, 0, f"align={align} 失败 ptr={ptr}")

    def test_alloc_multiple_fits_in_one_block(self):
        """大量小对象应复用同一个块（arena_blocks 不应线性增长）"""
        arena = ArenaAllocator(block_size=64 * 1024)  # 64 KiB
        ptrs = []
        for _ in range(100):
            p = arena.alloc(64)  # 100 * 64 = 6.4 KiB < 64 KiB
            self.assertIsNotNone(p)
            ptrs.append(p)
        s = arena.stats
        # 应只有 1 个块
        self.assertEqual(s.arena_blocks, 1, f"100x64B 应在 1 个块内，实际 blocks={s.arena_blocks}")
        self.assertEqual(s.current_allocations, 100)
        self.assertEqual(s.bytes_allocated, 6400)

    def test_free_is_noop_returns_true_for_owned(self):
        """Arena 的 free 是语义 no-op：对自己分配的 ptr 返回 True"""
        arena = ArenaAllocator()
        ptr = arena.alloc(100)
        self.assertIsNotNone(ptr)
        ok = arena.free(ptr, 100)
        self.assertTrue(ok, "Arena.free(自有ptr) 应返回 True")
        # 物理未释放：current_bytes 仍存在（record_free(success=False)）
        s = arena.stats
        self.assertEqual(s.total_frees, 1)
        # current_allocations 不会真正减少（因为物理未释放）
        # 但 arena.free 里 record_free(size, False) → 不减少 current_bytes
        # 验证：record_free success=False 不会调 bytes_freed/current_bytes
        self.assertEqual(s.bytes_freed, 0, "Arena free 不应增加 bytes_freed")

    def test_free_invalid_ptr_returns_false(self):
        """非本 Arena 分配的 ptr 调用 free 返回 False"""
        arena = ArenaAllocator()
        self.assertFalse(arena.free(0xDEAD_BEEF, 8))

    def test_owns_for_allocated_ptr(self):
        """Arena.owns 对自己分配的 ptr 返回 True，对其他返回 False"""
        arena = ArenaAllocator()
        p1 = arena.alloc(8)
        p2 = arena.alloc(16)
        self.assertTrue(arena.owns(p1))
        self.assertTrue(arena.owns(p2))
        self.assertFalse(arena.owns(0xDEAD_BEEF))

    def test_get_allocation_size(self):
        """get_allocation_size 返回原始申请 size"""
        arena = ArenaAllocator()
        p = arena.alloc(42)
        self.assertEqual(arena.get_allocation_size(p), 42)
        self.assertIsNone(arena.get_allocation_size(0xCAFE))

    def test_reset_releases_all(self):
        """reset 后所有计数清零（arena_blocks/current 归零）"""
        arena = ArenaAllocator()
        for _ in range(10):
            arena.alloc(1024)
        self.assertGreater(arena.stats.arena_blocks, 0)
        self.assertGreater(arena.stats.current_bytes, 0)
        arena.reset()
        s = arena.stats
        self.assertEqual(s.arena_blocks, 0, "reset 后块数应为 0")
        self.assertEqual(s.current_bytes, 0)
        self.assertEqual(s.current_allocations, 0)

    def test_context_manager_calls_reset(self):
        """with create_arena(...) as a: 离开作用域时触发 reset"""
        with create_arena("ctx", block_size=4096) as arena:
            arena.alloc(1024)
            arena.alloc(2048)
            self.assertGreater(arena.stats.current_bytes, 0)
        # 离开 with 块 → reset() → 计数清零
        s = arena.stats
        self.assertEqual(s.current_bytes, 0, "离开 ctx 后 current_bytes 应归零")
        self.assertEqual(s.arena_blocks, 0)

    def test_invalid_block_size_raises(self):
        """block_size <= 0 应抛 ValueError"""
        with self.assertRaises(ValueError):
            ArenaAllocator(block_size=0)
        with self.assertRaises(ValueError):
            ArenaAllocator(block_size=-1)

    def test_realloc_grow_success(self):
        """Arena realloc 应返回合法 ptr（或就地扩展，或新块分配）"""
        arena = ArenaAllocator()
        p = arena.alloc(64)
        self.assertIsNotNone(p)
        p2 = arena.realloc(p, 64, 1024)
        self.assertIsNotNone(p2, "realloc 扩容应返回新地址")
        self.assertEqual(arena.stats.total_reallocs, 1)

    def test_size_zero_alloc_returns_none(self):
        """size=0 → 返回 None（与 Allocator trait 一致）"""
        arena = ArenaAllocator()
        self.assertIsNone(arena.alloc(0))

    def test_invalid_params_rejected(self):
        """非法 align / size 返回 None（参数校验）"""
        arena = ArenaAllocator()
        self.assertIsNone(arena.alloc(100, align=3))
        self.assertIsNone(arena.alloc(-1))


# ============================================================
# 6. NovaBox<T> 语义测试
# ============================================================
class TestNovaBox(unittest.TestCase):
    """Box<T> 的所有权 / 析构 / 借用检查模拟"""

    def test_make_creates_alive_box(self):
        """NovaBox.make 应创建 alive 状态的 Box，值可读取"""
        alloc = LibcAllocator()
        box = NovaBox.make(alloc, 42, inner_size=8)
        self.assertEqual(box.inner, 42)
        self.assertFalse(box._moved)
        self.assertEqual(box.get(), 42)
        self.assertEqual(box.inner_size, 8)
        self.assertEqual(box.inner_align, DEFAULT_ALIGN)

    def test_make_updates_allocator_stats(self):
        """make 内部调用 allocator.alloc，统计 +N 字节"""
        alloc = LibcAllocator()
        before = alloc.stats.bytes_allocated
        NovaBox.make(alloc, "hello", inner_size=64, inner_align=16)
        after = alloc.stats.bytes_allocated
        self.assertEqual(after - before, 64)

    def test_drop_marks_moved(self):
        """drop 后 _moved=True（free 计数：ptr=0 占位 no-op 不更新 Libc 统计，
        仅校验 move 标记语义；ArenaAllocator 等实现会更新，此处不强绑定）"""
        alloc = LibcAllocator()
        box = NovaBox.make(alloc, 99, inner_size=16)
        self.assertFalse(box._moved, "drop 前 _moved 应为 False")
        NovaBox.drop(box)
        self.assertTrue(box._moved, "drop 后 _moved 应被标记为 True")

    def test_drop_is_idempotent(self):
        """多次 drop 仅第一次会改变状态；_moved 始终为 True（幂等性）"""
        alloc = LibcAllocator()
        box = NovaBox.make(alloc, 0, inner_size=8)
        NovaBox.drop(box)
        first_moved = box._moved
        NovaBox.drop(box)
        NovaBox.drop(box)
        self.assertTrue(first_moved, "首次 drop 后应标记 moved")
        self.assertTrue(box._moved, "重复 drop 后仍保持 moved 状态")

    def test_get_after_drop_raises(self):
        """use-after-drop：get 应抛 RuntimeError"""
        box = NovaBox.make(LibcAllocator(), "x", inner_size=8)
        NovaBox.drop(box)
        with self.assertRaises(RuntimeError) as cm:
            box.get()
        self.assertIn("use-after-drop", str(cm.exception))

    def test_set_after_drop_raises(self):
        """use-after-drop：set 应抛 RuntimeError"""
        box = NovaBox.make(LibcAllocator(), 1, inner_size=8)
        NovaBox.drop(box)
        with self.assertRaises(RuntimeError):
            box.set(2)

    def test_set_changes_value_not_size(self):
        """set 替换 inner 值，但不改变分配大小"""
        box = NovaBox.make(LibcAllocator(), 10, inner_size=8)
        box.set(20)
        self.assertEqual(box.get(), 20)
        self.assertEqual(box.inner_size, 8, "set 不应改变 inner_size")

    def test_clone_returns_distinct_box(self):
        """clone 返回新的独立 Box（identity 不同，值相同）"""
        alloc = LibcAllocator()
        box1 = NovaBox.make(alloc, [1, 2, 3], inner_size=24)
        box2 = box1.clone()
        self.assertIsNot(box1, box2)
        self.assertEqual(box1.get(), box2.get())
        # 两次 alloc：统计应增加 2 个分配
        self.assertEqual(alloc.stats.total_allocs, 2)

    def test_clone_on_new_allocator(self):
        """clone 可指定新 allocator"""
        a1 = LibcAllocator()
        a2 = LibcAllocator()
        box1 = NovaBox.make(a1, "data", inner_size=8)
        box2 = box1.clone(new_allocator=a2)
        self.assertIs(box1.allocator, a1)
        self.assertIs(box2.allocator, a2)
        self.assertEqual(a1.stats.total_allocs, 1)
        self.assertEqual(a2.stats.total_allocs, 1)

    def test_eq_alive_boxes_equal_values(self):
        """alive 状态的两个 Box 按 inner/size/align 比较相等"""
        alloc = LibcAllocator()
        b1 = NovaBox.make(alloc, 5, inner_size=8)
        b2 = NovaBox.make(alloc, 5, inner_size=8)
        self.assertEqual(b1, b2)

    def test_eq_dropped_box_never_equal(self):
        """任意一方 drop 后 __eq__ 返回 False"""
        alloc = LibcAllocator()
        b1 = NovaBox.make(alloc, 5, inner_size=8)
        b2 = NovaBox.make(alloc, 5, inner_size=8)
        NovaBox.drop(b1)
        self.assertNotEqual(b1, b2)

    def test_hash_based_on_identity(self):
        """hash 基于 identity：两个值相等的 Box 不应 hash 相等"""
        alloc = LibcAllocator()
        b1 = NovaBox.make(alloc, 5, inner_size=8)
        b2 = NovaBox.make(alloc, 5, inner_size=8)
        self.assertNotEqual(hash(b1), hash(b2))

    def test_repr_contains_status_and_value(self):
        """__repr__ 输出应标识 alive/DROPED 状态并包含 inner"""
        alloc = LibcAllocator()
        b = NovaBox.make(alloc, 42, inner_size=8)
        self.assertIn("alive", repr(b))
        self.assertIn("42", repr(b))
        NovaBox.drop(b)
        self.assertIn("DROPED", repr(b))


# ============================================================
# 7. 便捷函数
# ============================================================
class TestHelperFunctions(unittest.TestCase):
    """get_global_libc_allocator / create_arena / box_value / unbox_value / set_box_value"""

    def test_global_libc_singleton(self):
        """两次 get_global_libc_allocator() 应返回同一实例（单例）"""
        a1 = get_global_libc_allocator()
        a2 = get_global_libc_allocator()
        self.assertIs(a1, a2)
        self.assertIsInstance(a1, LibcAllocator)

    def test_create_arena_correct_defaults(self):
        """create_arena 应返回 ArenaAllocator 实例，默认 block_size 正确"""
        arena = create_arena("my_arena")
        self.assertIsInstance(arena, ArenaAllocator)
        self.assertEqual(arena.name, "my_arena")
        self.assertEqual(arena.block_size, ArenaAllocator.DEFAULT_BLOCK_SIZE)

    def test_create_arena_custom_block_size(self):
        """自定义 block_size 应被正确保留"""
        arena = create_arena("small", block_size=1024)
        self.assertEqual(arena.block_size, 1024)

    def test_box_value_makes_box(self):
        """box_value 等价于 NovaBox.make，返回 NovaBox 实例"""
        alloc = LibcAllocator()
        box = box_value(alloc, 3.14, size=8, align=8)
        self.assertIsInstance(box, NovaBox)
        self.assertEqual(box.get(), 3.14)

    def test_unbox_value_returns_inner(self):
        """unbox_value 等价于 box.get()"""
        alloc = LibcAllocator()
        box = NovaBox.make(alloc, "data", inner_size=8)
        self.assertEqual(unbox_value(box), "data")

    def test_unbox_value_type_check(self):
        """非 Box 传入 unbox_value 应抛 TypeError"""
        with self.assertRaises(TypeError):
            unbox_value(42)

    def test_set_box_value_updates_inner(self):
        """set_box_value 等价于 box.set"""
        alloc = LibcAllocator()
        box = NovaBox.make(alloc, 10, inner_size=8)
        set_box_value(box, 99)
        self.assertEqual(box.get(), 99)


# ============================================================
# 8. 线程安全基础验证
# ============================================================
class TestThreadSafety(unittest.TestCase):
    """LibcAllocator / ArenaAllocator 的计数器在并发下不丢失更新"""

    def _run_concurrent(self, alloc: Allocator, n_threads: int, n_per_thread: int):
        def worker():
            for _ in range(n_per_thread):
                p = alloc.alloc(128)
                if p is not None:
                    alloc.free(p, 128)

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def test_libc_concurrent_alloc_free_matches_count(self):
        """LibcAllocator 并发 N 次 alloc+free 后计数应精确等于 N"""
        alloc = LibcAllocator()
        N_THREADS = 8
        N_PER = 200
        expected = N_THREADS * N_PER
        self._run_concurrent(alloc, N_THREADS, N_PER)
        s = alloc.stats
        self.assertEqual(s.total_allocs, expected, "并发 alloc 计数丢失")
        self.assertEqual(s.total_frees, expected, "并发 free 计数丢失")

    def test_arena_concurrent_alloc_no_crash(self):
        """Arena 并发 alloc 不抛异常、不返回错位值（不保证统计精确，只求无崩溃）"""
        arena = ArenaAllocator(block_size=1024 * 1024)  # 1 MiB 块，避免频繁新块
        errors = []

        def worker():
            try:
                for _ in range(100):
                    p = arena.alloc(64)
                    if p is not None:
                        # 至少对齐检查一次
                        self.assertEqual(p % 8, 0)
            except Exception as e:  # noqa: BLE001 — 捕获以便收集
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [], f"并发异常: {errors}")


if __name__ == "__main__":
    unittest.main()
