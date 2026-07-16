"""
Nova 统一编译管道
Nova 源码 -> Tree-sitter 解析 -> HIR -> MIR -> LIR -> 目标代码
"""

import sys
import os

# 确保 ir/ 目录在路径上（ir 内的模块直接 import ir_nodes）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ir"))

from typing import Optional

from ir.ir_nodes import HIRModule, MIRModule, LIRModule
from ir.hir_lowering import HIRLowering
from ir.mir_lowering import MIRLowering
from ir.lir_lowering import LIRLowering
from ir.pass_manager import default_optimization_pipeline

# 编译目标常量
BACKEND_NATIVE = "native"
BACKEND_WASM = "wasm"
BACKEND_C = "c"


class NovaCompilerPipeline:
    """Nova 统一编译管道"""

    def __init__(self, target: str = BACKEND_NATIVE, optimize_level: int = 2):
        self.target = target
        self.optimize_level = optimize_level
        self.pass_manager = (
            default_optimization_pipeline() if optimize_level > 0 else None
        )

        # 选择后端
        if target == BACKEND_NATIVE:
            from backend.cranelift_backend import CraneliftBackend

            self.backend = CraneliftBackend()
        elif target == BACKEND_WASM:
            from backend.wasm_backend import WasmGCBackend

            self.backend = WasmGCBackend()
        else:
            from c_codegen import CCodeGen

            self.backend = CCodeGen()

    def compile_source(self, source: str, output_path: str) -> bool:
        """完整的编译管道：源码 -> 目标代码"""
        # 1. 前端解析（复用现有 Parser）
        from lexer import Lexer
        from parser import Parser
        from type_checker import TypeChecker

        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        TypeChecker().check_program(ast)

        # 2. AST -> HIR
        hir_module = HIRLowering().lower(ast)

        # 3. HIR 优化
        if self.pass_manager:
            self.pass_manager.run_hir_passes(hir_module)

        # 4. HIR -> MIR
        mir_module = MIRLowering().lower(hir_module)

        # 5. MIR 优化
        if self.pass_manager:
            self.pass_manager.run_mir_passes(mir_module)

        # 6. MIR -> LIR
        lir_module = LIRLowering().lower(mir_module)

        # 7. LIR 优化
        if self.pass_manager:
            self.pass_manager.run_lir_passes(lir_module)

        # 8. 后端代码生成
        if self.target == BACKEND_NATIVE:
            self.backend.compile_to_object(lir_module, output_path)
        elif self.target == BACKEND_WASM:
            return self.backend.compile_to_wasm(lir_module, output_path)
        elif self.target == BACKEND_C:
            # 生成 C 代码
            c_code = self.backend.generate(ast)
            with open(output_path, "w") as f:
                f.write(c_code)

        return True

    def compile_to_ir_text(self, source: str, level: str = "lir") -> str:
        """编译到指定 IR 层的文本输出（调试用）"""
        from lexer import Lexer
        from parser import Parser

        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()

        if level == "hir":
            hir = HIRLowering().lower(ast)
            return str(hir)
        elif level == "mir":
            hir = HIRLowering().lower(ast)
            mir = MIRLowering().lower(hir)
            return str(mir)
        elif level == "lir":
            hir = HIRLowering().lower(ast)
            mir = MIRLowering().lower(hir)
            lir = LIRLowering().lower(mir)
            return str(lir)
        return ""
