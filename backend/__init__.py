"""Nova 后端（立即架构手术已激活）

本模块提供 Nova 编程语言的多后端编译目标支持。

.. warning::
    根据 ARCHITECTURE_VISION.md §2.3「立即架构手术 C」，
    **Cranelift 后端已正式弃用**（v0.3.x → v0.5.0 移除），
    实例化 :class:`~.cranelift_backend.CraneliftBackend` 会触发
    :exc:`DeprecationWarning`。

当前受支持的后端路径（3 条活跃管线）：

.. list-table:: 活跃后端一览
   :widths: 15 28 28 29
   :header-rows: 1

   * - 后端
     - 入口类
     - 输出格式
     - 适用场景
   * - **Native x86_64**
     - :class:`~.native_backend.NativeCodeGen`
     - ELF 64-bit 可执行文件 / 重定位 .o
     - 自举 SH-3 目标、零外部依赖、性能最优
   * - **C 源码**
     - :class:`~.lir_c_backend.LIRCBackend`
     - ISO C11 源码 → GCC/Clang 编译
     - 跨平台、调试友好、运行时完整
   * - **WasmGC**
     - :class:`~.wasm_backend.WasmGCBackend`
     - WasmGC 字节码（.wasm）
     - 浏览器 / WASI 环境部署

统一编译管道入口：:mod:`~.compiler_pipeline`（推荐）

架构手术进度（M-ARCH 里程碑，cycles=80 已完成 **5/5** 🎉）：

- 手术 A · 拆分 ir/ir_nodes.py：✅ **本轮完成**（a1 类型 + a2 按层 + a3 瘦身 三步全部完成）
- 手术 B · 统一 C 后端：✅ **本轮完成**（Phase1 路径隔离 + DeprecationWarning 挂接 + 入口点全部转到 LIRCBackend）
- 手术 C · 弃用 Cranelift 后端：✅ 上轮完成（DeprecationWarning 已挂接）
"""

__all__ = [
    # 三条活跃后端路径
    "native_backend",
    "lir_c_backend",
    "wasm_backend",
    # 统一编译管道（推荐使用）
    "compiler_pipeline",
    # Cranelift 后端（已弃用，保留导出至 v0.5.0 以兼容旧代码）
    "cranelift_backend",
]
