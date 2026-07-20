"""
Nova 基准测试框架

提供标准化的编译器性能基准测试，支持各后端的性能对比和优化效果量化。
"""

from .runner import (
    BenchmarkCase,
    BenchmarkResult,
    BenchmarkRunner,
    list_builtin_cases,
    run_benchmark,
    run_all_benchmarks,
)

__all__ = [
    "BenchmarkCase",
    "BenchmarkResult",
    "BenchmarkRunner",
    "list_builtin_cases",
    "run_benchmark",
    "run_all_benchmarks",
]
