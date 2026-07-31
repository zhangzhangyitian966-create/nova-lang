"""
Nova Programming Language
=========================

Nova 是一种现代编程语言，具有简洁的语法和强大的表达能力。

本模块提供 Nova 语言的主要入口点，包括解释器、编译器和核心工具。

主要类:
    - Nova: 主入口类
    - Lexer: 词法分析器
    - Parser: 语法分析器
    - Evaluator: 解释器
    - Compiler: 编译器

示例:
    >>> from nova import Nova
    >>> nova = Nova()
    >>> nova.eval("1 + 1")
    2
"""

# Nova Programming Language Interpreter
# An expression-oriented, statically typed, functional-core language.

# REPL 辅助函数导出（供测试使用）
from .cli import _attach_source, _count_indent, _is_incomplete
from .lexer import Lexer
from .lexer import Token
from .lexer import TokenType
from .parser import Parser
from .evaluator import Evaluator
from .errors import LexerError
from .errors import ParseError
from .errors import ParseErrorGroup
from .errors import TypeCheckError
from .errors import RuntimeError_
from .ast_nodes import Program
from .environment import Environment
from .type_checker import TypeChecker
from .compiler import BytecodeCompiler
from .compiler import Bytecode
# 注：旧 CCodeGen (c_codegen.py AST→C 直译路径) 已在 v0.3.x 弃用
# (ARCHITECTURE_VISION.md §2.2「立即架构手术 B」)，
# 统一入口改为 nova.backend.lir_c_backend.LIRCBackend (通过 NovaCompilerPipeline)。
# 为避免包级 API 破坏性变更 + 增量门禁噪音，此处不再 re-export CCodeGen。
# 旧调用方仍可通过 nova.c_codegen.CCodeGen 直接访问（v0.5.0 正式删除文件前保留）。
