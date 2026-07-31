"""
Nova Runtime 包（Python 参考实现层）

本包提供 Nova 编程语言 Python 参考实现的运行时辅助模块，
对应 C 侧 ``runtime/nova_runtime.c/.h`` 的接口抽象层。

当前导出：
  * :mod:`allocator` —— M-MEM Step1 显式 Allocator API（ArenaAllocator / LibcAllocator）

设计约束（对齐 ARCHITECTURE_VISION.md §3.1）：
  1. **无全局分配器状态**：所有分配必须显式传入 allocator 参数。
  2. **接口不可变原则**：Allocator trait 一旦定板不做破坏性变更，
     新分配器策略只需新增实现类，无需修改数据结构代码。
  3. **Option/Result 风格返回**：分配失败不抛异常，返回 None 或元组。
"""

from .allocator import (
    # Trait
    Allocator,
    # 内置实现
    ArenaAllocator,
    LibcAllocator,
    # 统计
    AllocStats,
    # 结果/错误
    AllocError,
    AllocErrorKind,
    # 便捷函数
    get_global_libc_allocator,
    create_arena,
    align_forward,
    # 导出常量
    DEFAULT_ALIGN,
    MAX_ALLOC_SIZE,
    # --- M-MEM Step3 新增：Box<T> 运行时值 + 便捷函数 ---
    NovaBox,
    box_value,
    unbox_value,
    set_box_value,
    drop_box,
)

__all__ = [
    "Allocator",
    "ArenaAllocator",
    "LibcAllocator",
    "AllocStats",
    "AllocError",
    "AllocErrorKind",
    "get_global_libc_allocator",
    "create_arena",
    "align_forward",
    "DEFAULT_ALIGN",
    "MAX_ALLOC_SIZE",
    # --- M-MEM Step3 新增 ---
    "NovaBox",
    "box_value",
    "unbox_value",
    "set_box_value",
    "drop_box",
]
