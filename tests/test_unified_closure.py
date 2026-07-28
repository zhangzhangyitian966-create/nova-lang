"""
三后端统一闭包执行测试矩阵

建立同一 Nova 闭包程序在 C / Native / Wasm 三后端上的统一验证基线。
这是后端端到端正确性的核心保障。
"""

import os
import subprocess
import tempfile
import unittest

from nova.backend.compiler_pipeline import (
    NovaCompilerPipeline,
    BACKEND_C,
)

# ============================================================
# 统一测试用例
# ============================================================

MAKE_ADDER_SOURCE = """
fn make_adder(n: Int) -> (Int) -> Int {
    |x: Int| -> Int { x + n }
}
fn main() -> Int {
    let add5 = make_adder(5)
    add5(10)
}
"""

MULTI_CAPTURE_SOURCE = """
fn make_combined(a: Int, b: Int) -> (Int) -> Int {
    |x: Int| -> Int { x + a + b }
}
fn main() -> Int {
    let f = make_combined(10, 20)
    f(5)
}
"""

RUNTIME_DIR = os.path.join(os.path.dirname(__file__), "..", "runtime")
RUNTIME_C = os.path.join(RUNTIME_DIR, "nova_runtime.c")


def _compile_c_source(source: str, output_path: str) -> None:
    """通过 C 后端编译 Nova 源码到 C 文件"""
    pipeline = NovaCompilerPipeline(target=BACKEND_C, optimize_level=0)
    pipeline.compile_source(source, output_path)


class TestUnifiedClosureMatrix(unittest.TestCase):
    """三后端统一闭包执行测试矩阵"""

    # --------------------------------------------------------
    # C 后端
    # --------------------------------------------------------

    @unittest.skipUnless(
        __import__("shutil").which("gcc"),
        "gcc not available"
    )
    def test_c_backend_make_adder_e2e(self):
        """C 后端：make_adder(5)(10) 应返回 15"""
        with tempfile.NamedTemporaryFile(
            suffix=".c", mode="w", delete=False
        ) as f:
            f.write("")
            f.flush()
            c_file = f.name
            exe_file = c_file.replace(".c", "")
            try:
                _compile_c_source(MAKE_ADDER_SOURCE, c_file)
                result = subprocess.run(
                    ["gcc", "-o", exe_file, "-I", RUNTIME_DIR,
                     c_file, RUNTIME_C, "-lm"],
                    capture_output=True, text=True, timeout=10
                )
                self.assertEqual(
                    result.returncode, 0,
                    f"GCC 编译失败: {result.stderr}"
                )
                run_result = subprocess.run(
                    [exe_file], capture_output=True, text=True, timeout=5
                )
                self.assertEqual(
                    run_result.returncode, 15,
                    f"C 后端闭包执行结果应为 15，实际: {run_result.returncode}"
                )
            finally:
                if os.path.exists(c_file):
                    os.unlink(c_file)
                if os.path.exists(exe_file):
                    os.unlink(exe_file)

    @unittest.skipUnless(
        __import__("shutil").which("gcc"),
        "gcc not available"
    )
    def test_c_backend_multi_capture_e2e(self):
        """C 后端：多变量捕获 make_combined(10,20)(5) 应返回 35"""
        with tempfile.NamedTemporaryFile(
            suffix=".c", mode="w", delete=False
        ) as f:
            f.write("")
            f.flush()
            c_file = f.name
            exe_file = c_file.replace(".c", "")
            try:
                _compile_c_source(MULTI_CAPTURE_SOURCE, c_file)
                result = subprocess.run(
                    ["gcc", "-o", exe_file, "-I", RUNTIME_DIR,
                     c_file, RUNTIME_C, "-lm"],
                    capture_output=True, text=True, timeout=10
                )
                self.assertEqual(
                    result.returncode, 0,
                    f"GCC 编译失败: {result.stderr}"
                )
                run_result = subprocess.run(
                    [exe_file], capture_output=True, text=True, timeout=5
                )
                self.assertEqual(
                    run_result.returncode, 35,
                    f"C 后端多捕获执行结果应为 35，实际: {run_result.returncode}"
                )
            finally:
                if os.path.exists(c_file):
                    os.unlink(c_file)
                if os.path.exists(exe_file):
                    os.unlink(exe_file)

    # --------------------------------------------------------
    # Native 后端（gcc 链接模式）
    # --------------------------------------------------------
    # 注：Native 后端可重定位 ELF 的链接仍有底层格式问题待修复
    # （数据段重定位类型、main 符号导出），当前测试建立编译基线。

    @unittest.skipUnless(
        __import__("shutil").which("gcc"),
        "gcc not available"
    )
    def test_native_backend_make_adder_compiles(self):
        """Native 后端：make_adder 应成功编译为可重定位 .o 文件

        验证 compiler_pipeline use_gcc_link 路径能生成 .o 文件，
        且包含闭包相关的 trampoline 符号和重定位表。
        端到端执行待 ELF 链接格式修复后启用。
        """
        from nova.backend.native_backend import NativeCodeGen
        from nova.lexer import Lexer
        from nova.parser import Parser
        from nova.type_checker import TypeChecker
        from nova.ir.hir_lowering import HIRLowering
        from nova.ir.mir_lowering import MIRLowering
        from nova.ir.lir_lowering import LIRLowering

        tokens = Lexer(MAKE_ADDER_SOURCE).tokenize()
        ast = Parser(tokens).parse()
        TypeChecker().check_program(ast)
        hir = HIRLowering().lower(ast)
        mir = MIRLowering().lower(hir)
        lir = LIRLowering().lower(mir)

        backend = NativeCodeGen()
        obj_bytes = backend.compile(lir, output_format="obj")

        # 验证是合法的 ELF 文件
        self.assertEqual(obj_bytes[:4], b"\x7fELF")
        # 验证包含闭包 trampoline 符号
        self.assertIn(b"__trampoline_", obj_bytes)
        # 验证包含重定位表
        self.assertIn(b".rela.text", obj_bytes)

    @unittest.skipUnless(
        __import__("shutil").which("gcc"),
        "gcc not available"
    )
    def test_native_backend_multi_capture_compiles(self):
        """Native 后端：多变量捕获应成功编译为 .o 文件"""
        from nova.backend.native_backend import NativeCodeGen
        from nova.lexer import Lexer
        from nova.parser import Parser
        from nova.type_checker import TypeChecker
        from nova.ir.hir_lowering import HIRLowering
        from nova.ir.mir_lowering import MIRLowering
        from nova.ir.lir_lowering import LIRLowering

        tokens = Lexer(MULTI_CAPTURE_SOURCE).tokenize()
        ast = Parser(tokens).parse()
        TypeChecker().check_program(ast)
        hir = HIRLowering().lower(ast)
        mir = MIRLowering().lower(hir)
        lir = LIRLowering().lower(mir)

        backend = NativeCodeGen()
        obj_bytes = backend.compile(lir, output_format="obj")

        self.assertEqual(obj_bytes[:4], b"\x7fELF")
        self.assertIn(b"__trampoline_", obj_bytes)

    # --------------------------------------------------------
    # Wasm 后端
    # --------------------------------------------------------

    def test_wasm_backend_make_adder_generates(self):
        """Wasm 后端：make_adder 应成功编译并包含闭包结构"""
        from nova.lexer import Lexer
        from nova.parser import Parser
        from nova.type_checker import TypeChecker
        from nova.ir.hir_lowering import HIRLowering
        from nova.ir.mir_lowering import MIRLowering
        from nova.ir.lir_lowering import LIRLowering
        from nova.backend.wasm_backend import WasmGCBackend

        tokens = Lexer(MAKE_ADDER_SOURCE).tokenize()
        ast = Parser(tokens).parse()
        TypeChecker().check_program(ast)
        hir = HIRLowering().lower(ast)
        mir = MIRLowering().lower(hir)
        lir = LIRLowering().lower(mir)

        backend = WasmGCBackend()
        wat = backend.compile(lir)

        # 验证闭包相关结构存在
        self.assertIn("nova_closure_new", wat)
        self.assertIn("table", wat)
        self.assertIn("funcref", wat)
        self.assertIn("elem", wat)

    def test_wasm_backend_multi_capture_generates(self):
        """Wasm 后端：多变量捕获应成功编译"""
        from nova.lexer import Lexer
        from nova.parser import Parser
        from nova.type_checker import TypeChecker
        from nova.ir.hir_lowering import HIRLowering
        from nova.ir.mir_lowering import MIRLowering
        from nova.ir.lir_lowering import LIRLowering
        from nova.backend.wasm_backend import WasmGCBackend

        tokens = Lexer(MULTI_CAPTURE_SOURCE).tokenize()
        ast = Parser(tokens).parse()
        TypeChecker().check_program(ast)
        hir = HIRLowering().lower(ast)
        mir = MIRLowering().lower(hir)
        lir = LIRLowering().lower(mir)

        backend = WasmGCBackend()
        wat = backend.compile(lir)

        # 验证闭包相关结构存在
        self.assertIn("nova_closure_new", wat)
        self.assertIn("table", wat)


if __name__ == "__main__":
    unittest.main()
