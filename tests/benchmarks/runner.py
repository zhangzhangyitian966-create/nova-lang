"""
Nova 基准测试运行器

提供标准化的编译器性能基准测试，支持：
- 编译时间测量（前端 + IR 降级 + 优化 + 代码生成）
- 执行时间测量（VM 解释执行）
- 多后端对比（VM / C / Wasm）
- 优化效果量化（开/关优化对比）
- 结果验证（确保各后端输出一致）

MVP 版本主要支持 VM 后端，后续可扩展 C 和 Wasm 后端。
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class BenchmarkCase:
    """基准测试用例"""

    name: str
    source: str
    description: str = ""
    expected_output: str = ""
    category: str = "general"  # arithmetic, loop, recursive, data_structure, etc.
    warmup: int = 1  # 预热次数
    iterations: int = 5  # 正式测量次数


@dataclass
class BenchmarkResult:
    """基准测试结果"""

    case_name: str
    backend: str
    compile_time_ms: float = 0.0  # 编译时间（毫秒）
    execute_time_ms: float = 0.0  # 执行时间（毫秒）
    total_time_ms: float = 0.0  # 总时间（毫秒）
    output: str = ""
    success: bool = True
    error: str = ""
    iterations: int = 0
    compile_times: List[float] = field(default_factory=list)
    execute_times: List[float] = field(default_factory=list)

    @property
    def avg_compile_ms(self) -> float:
        if not self.compile_times:
            return 0.0
        return sum(self.compile_times) / len(self.compile_times)

    @property
    def avg_execute_ms(self) -> float:
        if not self.execute_times:
            return 0.0
        return sum(self.execute_times) / len(self.execute_times)

    @property
    def min_execute_ms(self) -> float:
        if not self.execute_times:
            return 0.0
        return min(self.execute_times)

    @property
    def max_execute_ms(self) -> float:
        if not self.execute_times:
            return 0.0
        return max(self.execute_times)


class BenchmarkRunner:
    """基准测试运行器"""

    def __init__(self, backends: Optional[List[str]] = None):
        """
        初始化基准测试运行器

        Args:
            backends: 要测试的后端列表，默认 ["vm"]
                      支持: "vm", "c", "wasm"
        """
        self.backends = backends or ["vm"]

    def run_case(self, case: BenchmarkCase, backend: str = "vm") -> BenchmarkResult:
        """
        运行单个基准用例

        Args:
            case: 基准测试用例
            backend: 后端名称

        Returns:
            BenchmarkResult 结果对象
        """
        result = BenchmarkResult(case_name=case.name, backend=backend)

        try:
            if backend == "vm":
                self._run_vm(case, result)
            elif backend == "c":
                self._run_c(case, result)
            elif backend == "wasm":
                self._run_wasm(case, result)
            else:
                result.success = False
                result.error = f"未知后端: {backend}"

            result.iterations = len(result.execute_times)
            result.compile_time_ms = result.avg_compile_ms
            result.execute_time_ms = result.avg_execute_ms
            result.total_time_ms = result.compile_time_ms + result.execute_time_ms

        except Exception as e:
            result.success = False
            result.error = str(e)

        return result

    def run_all(self, cases: List[BenchmarkCase]) -> Dict[str, List[BenchmarkResult]]:
        """
        运行所有基准用例

        Returns:
            {backend_name: [result1, result2, ...]}
        """
        results: Dict[str, List[BenchmarkResult]] = {}
        for backend in self.backends:
            results[backend] = []
            for case in cases:
                result = self.run_case(case, backend)
                results[backend].append(result)
        return results

    def _run_vm(self, case: BenchmarkCase, result: BenchmarkResult):
        """使用 VM 字节码解释器运行"""
        # 延迟导入，避免循环依赖
        from nova.lexer import Lexer
        from nova.parser import Parser
        from nova.type_checker import TypeChecker
        from nova.compiler import BytecodeCompiler
        from nova.vm import NovaVM

        output_lines = []

        # 预热 + 编译阶段
        for i in range(case.warmup + case.iterations):
            # 编译阶段
            compile_start = time.perf_counter()
            tokens = Lexer(case.source).tokenize()
            ast = Parser(tokens).parse()
            TypeChecker().check_program(ast)
            bytecode = BytecodeCompiler().compile(ast)
            compile_end = time.perf_counter()
            compile_ms = (compile_end - compile_start) * 1000

            # 执行阶段
            execute_start = time.perf_counter()
            vm = NovaVM(bytecode)
            vm.run()
            execute_end = time.perf_counter()
            execute_ms = (execute_end - execute_start) * 1000

            # 记录输出（只取最后一次）
            output_lines.append("\n".join(vm.get_output()) + "\n" if vm.get_output() else "")

            # 跳过预热，只记录正式测量
            if i >= case.warmup:
                result.compile_times.append(compile_ms)
                result.execute_times.append(execute_ms)

        result.output = output_lines[-1] if output_lines else ""

        # 验证结果
        if case.expected_output and case.expected_output.strip() != result.output.strip():
            result.success = False
            result.error = (
                f"输出不匹配\n期望: {repr(case.expected_output.strip())}\n"
                f"实际: {repr(result.output.strip())}"
            )

    def _run_c(self, case: BenchmarkCase, result: BenchmarkResult):
        """使用 C 后端运行（MVP 版本：仅测量编译时间，不运行）"""
        # 延迟导入
        from nova.backend.compiler_pipeline import NovaCompilerPipeline, BACKEND_C

        # 只测量编译时间，运行需要系统 C 编译器，MVP 版本暂不支持
        for i in range(case.warmup + case.iterations):
            compile_start = time.perf_counter()
            pipeline = NovaCompilerPipeline(target=BACKEND_C, optimize_level=2)
            # 编译到内存中的 C 代码
            from nova.lexer import Lexer
            from nova.parser import Parser
            from nova.type_checker import TypeChecker
            from nova.ir.hir_lowering import HIRLowering
            from nova.ir.mir_lowering import MIRLowering
            from nova.ir.lir_lowering import LIRLowering
            from nova.backend.lir_c_backend import LIRCBackend

            tokens = Lexer(case.source).tokenize()
            ast = Parser(tokens).parse()
            TypeChecker().check_program(ast)
            hir = HIRLowering().lower(ast)
            mir = MIRLowering().lower(hir)
            lir = LIRLowering().lower(mir)
            c_code = LIRCBackend().compile(lir)
            compile_end = time.perf_counter()
            compile_ms = (compile_end - compile_start) * 1000

            if i >= case.warmup:
                result.compile_times.append(compile_ms)
                result.execute_times.append(0.0)  # C 后端执行时间暂不测量

        result.output = "(C 后端执行时间未测量)"

    def _run_wasm(self, case: BenchmarkCase, result: BenchmarkResult):
        """使用 Wasm 后端运行（MVP 版本：仅测量编译时间，不运行）"""
        # 延迟导入
        from nova.lexer import Lexer
        from nova.parser import Parser
        from nova.type_checker import TypeChecker
        from nova.ir.hir_lowering import HIRLowering
        from nova.ir.mir_lowering import MIRLowering
        from nova.ir.lir_lowering import LIRLowering
        from nova.backend.wasm_backend import WasmGCBackend

        for i in range(case.warmup + case.iterations):
            compile_start = time.perf_counter()
            tokens = Lexer(case.source).tokenize()
            ast = Parser(tokens).parse()
            TypeChecker().check_program(ast)
            hir = HIRLowering().lower(ast)
            mir = MIRLowering().lower(hir)
            lir = LIRLowering().lower(mir)
            wasm_code = WasmGCBackend().compile(lir)
            compile_end = time.perf_counter()
            compile_ms = (compile_end - compile_start) * 1000

            if i >= case.warmup:
                result.compile_times.append(compile_ms)
                result.execute_times.append(0.0)  # Wasm 后端执行时间暂不测量

        result.output = "(Wasm 后端执行时间未测量)"


# ============================================================
# 内置基准用例
# ============================================================

_BUILTIN_CASES: List[BenchmarkCase] = []


def _register_case(case: BenchmarkCase):
    """注册内置基准用例"""
    _BUILTIN_CASES.append(case)
    return case


# ---- 算术密集型 ----

_register_case(BenchmarkCase(
    name="fibonacci_recursive",
    description="递归斐波那契数列（第20项）",
    category="recursive",
    source="""
fn fib(n: Int) -> Int {
    if n <= 1 then n
    else fib(n - 1) + fib(n - 2)
}

fn main() -> Unit {
    print(int_to_str(fib(20)))
}
""",
    expected_output="6765\n",
    warmup=1,
    iterations=5,
))

_register_case(BenchmarkCase(
    name="arithmetic_loop",
    description="循环累加 1 到 10000",
    category="loop",
    source="""
fn main() -> Unit {
    mut sum = 0
    mut i = 0
    while i < 10000 {
        sum = sum + i
        i = i + 1
    }
    print(int_to_str(sum))
}
""",
    expected_output="49995000\n",
    warmup=1,
    iterations=5,
))


# ---- 数据结构型 ----

_register_case(BenchmarkCase(
    name="list_build_append",
    description="构建 500 个元素的列表（使用 for 循环）",
    category="data_structure",
    source="""
fn main() -> Unit {
    let lst = for i <- 0..500 { i }
    print(int_to_str(list_length(lst)))
}
""",
    expected_output="501\n",
    warmup=1,
    iterations=5,
))

_register_case(BenchmarkCase(
    name="list_comprehension",
    description="列表推导式：生成 1 到 500 的平方数",
    category="data_structure",
    source="""
fn main() -> Unit {
    let squares = [i * i for i <- 1..500]
    print(int_to_str(list_length(squares)))
}
""",
    expected_output="500\n",
    warmup=1,
    iterations=5,
))


# ---- 控制流型 ----

_register_case(BenchmarkCase(
    name="nested_loop",
    description="嵌套循环（矩阵乘法简化版）",
    category="loop",
    source="""
fn main() -> Unit {
    let n = 50
    mut result = 0
    mut i = 0
    while i < n {
        mut j = 0
        while j < n {
            mut k = 0
            while k < n {
                result = result + 1
                k = k + 1
            }
            j = j + 1
        }
        i = i + 1
    }
    print(int_to_str(result))
}
""",
    expected_output="125000\n",
    warmup=1,
    iterations=5,
))


# ---- 高阶函数型 ----

_register_case(BenchmarkCase(
    name="higher_order_map",
    description="高阶函数：map + sum 组合",
    category="functional",
    source="""
fn add_one(x: Int) -> Int {
    x + 1
}

fn main() -> Unit {
    let data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    let mapped = map(add_one, data)
    let total = sum(mapped)
    print(int_to_str(total))
}
""",
    expected_output="65\n",
    warmup=1,
    iterations=5,
))


def list_builtin_cases() -> List[BenchmarkCase]:
    """获取所有内置基准用例"""
    return list(_BUILTIN_CASES)


def run_benchmark(case_name: str, backend: str = "vm") -> Optional[BenchmarkResult]:
    """
    运行指定名称的基准用例

    Args:
        case_name: 用例名称
        backend: 后端名称

    Returns:
        BenchmarkResult 或 None（用例不存在）
    """
    for case in _BUILTIN_CASES:
        if case.name == case_name:
            runner = BenchmarkRunner([backend])
            return runner.run_case(case, backend)
    return None


def run_all_benchmarks(backends: Optional[List[str]] = None) -> Dict[str, List[BenchmarkResult]]:
    """
    运行所有内置基准用例

    Args:
        backends: 后端列表，默认 ["vm"]

    Returns:
        {backend_name: [result1, result2, ...]}
    """
    runner = BenchmarkRunner(backends)
    return runner.run_all(_BUILTIN_CASES)
