#!/usr/bin/env python3
"""
Nova 基准测试运行脚本

用法:
    python3 -m tests.benchmarks.run_benchmarks
    python3 tests/benchmarks/run_benchmarks.py
"""

import sys
from pathlib import Path

# 确保项目根目录在路径中
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.benchmarks import run_all_benchmarks, list_builtin_cases


def print_results(results):
    """打印基准测试结果"""
    for backend, backend_results in results.items():
        print(f"\n{'='*60}")
        print(f"后端: {backend}")
        print(f"{'='*60}")
        print(f"{'用例':<30} {'编译(ms)':>10} {'执行(ms)':>10} {'总计(ms)':>10} {'状态':>8}")
        print("-" * 60)

        for r in backend_results:
            status = "✅" if r.success else "❌"
            print(
                f"{r.case_name:<30} "
                f"{r.avg_compile_ms:>10.2f} "
                f"{r.avg_execute_ms:>10.2f} "
                f"{r.total_time_ms:>10.2f} "
                f"{status:>8}"
            )
            if not r.success:
                print(f"  错误: {r.error}")

        # 统计
        successful = [r for r in backend_results if r.success]
        if successful:
            total_compile = sum(r.avg_compile_ms for r in successful)
            total_execute = sum(r.avg_execute_ms for r in successful)
            print("-" * 60)
            print(
                f"{'合计 (' + str(len(successful)) + '/' + str(len(backend_results)) + ')':<30} "
                f"{total_compile:>10.2f} "
                f"{total_execute:>10.2f} "
                f"{total_compile + total_execute:>10.2f}"
            )


def main():
    """主函数"""
    print("Nova 编程语言基准测试")
    print("=" * 60)

    # 列出可用用例
    cases = list_builtin_cases()
    print(f"可用基准用例: {len(cases)} 个")
    for case in cases:
        print(f"  - {case.name}: {case.description} [{case.category}]")

    # 运行所有基准（默认 VM 后端）
    backends = ["vm"]
    if "--c" in sys.argv:
        backends.append("c")
    if "--wasm" in sys.argv:
        backends.append("wasm")

    print(f"\n运行后端: {', '.join(backends)}")
    print("运行中...")

    results = run_all_benchmarks(backends)
    print_results(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
