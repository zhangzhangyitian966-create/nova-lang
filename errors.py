"""
Nova 编程语言 - 错误类型定义

定义解释器各阶段可能产生的错误类型，包括词法分析错误、
语法分析错误、类型检查错误和运行时错误。

错误报告支持源码上下文显示，类似 Rust 的错误格式。
"""

from typing import Optional, Tuple


class NovaError(Exception):
    """Nova 语言错误基类"""

    def __init__(self, message: str, line: int = -1, column: int = -1):
        self.message = message
        self.line = line
        self.column = column
        self.source_code: Optional[str] = None
        self.highlight_span: Optional[Tuple[int, int]] = None  # (start_col, end_col)
        super().__init__(message)

    def __str__(self) -> str:
        return self._format()

    def _format(self) -> str:
        if self.source_code and self.line >= 0:
            return self._format_with_context()
        if self.line >= 0 and self.column >= 0:
            return f"[行 {self.line}, 列 {self.column}] {self.message}"
        elif self.line >= 0:
            return f"[行 {self.line}] {self.message}"
        return self.message

    def _format_with_context(self) -> str:
        """带源码上下文的友好格式，类似 Rust 错误输出"""
        lines = self.source_code.split('\n')

        # 提取出错行及其前后各 1 行
        err_line_idx = max(0, self.line - 1)  # 转换为 0-based
        start = max(0, err_line_idx - 1)
        end = min(len(lines), err_line_idx + 2)  # 不包含 end

        parts = []
        parts.append(f"错误: {self.message}")
        parts.append(f"  --> 第{self.line}行，第{self.column}列")
        parts.append("   |")

        for i in range(start, end):
            line_num = i + 1  # 1-based 行号
            line_content = lines[i] if i < len(lines) else ""
            parts.append(f" {line_num:>2} | {line_content}")

            if i == err_line_idx:
                # 标记出错位置
                if self.highlight_span:
                    start_col, end_col = self.highlight_span
                    indent = " " * (self.column + 3)
                    underline = "^" * (end_col - start_col)
                    parts.append(f"     |{indent}{underline}")
                else:
                    indent = " " * (self.column + 3)
                    parts.append(f"     |{indent}^")

        return "\n".join(parts)


class LexerError(NovaError):
    """词法分析错误：非法字符、未闭合字符串等"""

    def __init__(self, message: str, line: int, column: int, source: Optional[str] = None):
        super().__init__(f"词法错误: {message}", line, column)
        if source is not None:
            self.source_code = source


class ParseError(NovaError):
    """语法分析错误：意外的 token、不完整的表达式等"""

    def __init__(self, message: str, line: int = -1, column: int = -1,
                 source: Optional[str] = None):
        super().__init__(f"语法错误: {message}", line, column)
        if source is not None:
            self.source_code = source


class TypeCheckError(NovaError):
    """类型检查错误：类型不匹配、未定义变量、类型推断失败等"""

    def __init__(self, message: str, line: int = -1, column: int = -1,
                 source: Optional[str] = None):
        super().__init__(f"类型错误: {message}", line, column)
        if source is not None:
            self.source_code = source


class RuntimeError_(NovaError):
    """运行时错误：除零、未绑定变量、模式匹配失败等"""

    def __init__(self, message: str, line: int = -1, column: int = -1,
                 source: Optional[str] = None):
        super().__init__(f"运行时错误: {message}", line, column)
        if source is not None:
            self.source_code = source


class BreakSignal(Exception):
    """break 信号：用于跳出循环"""

    def __init__(self, value=None):
        self.value = value


class ContinueSignal(Exception):
    """continue 信号：用于跳过当前迭代"""

    pass
