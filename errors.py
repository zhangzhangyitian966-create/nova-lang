"""
Nova 编程语言 - 错误类型定义

定义解释器各阶段可能产生的错误类型，包括词法分析错误、
语法分析错误、类型检查错误和运行时错误。

错误报告支持源码上下文显示，类似 Rust 的错误格式。
支持多行高亮、ANSI 颜色、严重程度和相关注释。
"""

import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from nova.ast_nodes import Span


# ============================================================
# 严重程度
# ============================================================

class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"
    HELP = "help"


# ============================================================
# ANSI 颜色
# ============================================================

class ANSI:
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @classmethod
    def enabled(cls) -> bool:
        return sys.stderr.isatty() and os.environ.get("NO_COLOR") is None

    @classmethod
    def colorize(cls, text: str, *codes: str) -> str:
        if not cls.enabled():
            return text
        return "".join(codes) + text + cls.RESET


# ============================================================
# SourceSpan 别名
# ============================================================

SourceSpan = Span


# ============================================================
# 相关注释
# ============================================================

@dataclass
class RelatedNote:
    """相关注释：指向其他位置的额外消息"""
    message: str
    span: Optional[Span] = None
    line: int = -1
    column: int = -1
    severity: Severity = Severity.NOTE


# ============================================================
# 错误基类
# ============================================================

class NovaError(Exception):
    """Nova 语言错误基类"""

    def __init__(self, message: str, line: int = -1, column: int = -1,
                 source: Optional[str] = None,
                 span: Optional[Span] = None,
                 severity: Severity = Severity.ERROR):
        self.message = message
        self.line = line
        self.column = column
        self.source_code: Optional[str] = source
        self.highlight_span: Optional[Tuple[int, int]] = None  # (start_col, end_col) 旧格式兼容
        self.span = span
        self.severity = severity
        self.related_notes: List[RelatedNote] = []

        # 如果提供了 span，用它更新 line/column 和 highlight_span
        if span is not None:
            self.line = span.line
            self.column = span.column
            if span.end_line is not None and span.end_column is not None:
                if span.line == span.end_line:
                    self.highlight_span = (span.column, span.end_column)

        super().__init__(message)

    def add_note(self, message: str, line: int = -1, column: int = -1,
                 span: Optional[Span] = None):
        """添加相关注释"""
        note = RelatedNote(message=message, line=line, column=column,
                           span=span, severity=Severity.NOTE)
        self.related_notes.append(note)
        return self

    def add_help(self, message: str, line: int = -1, column: int = -1,
                 span: Optional[Span] = None):
        """添加帮助提示"""
        note = RelatedNote(message=message, line=line, column=column,
                           span=span, severity=Severity.HELP)
        self.related_notes.append(note)
        return self

    def __str__(self) -> str:
        return self._format()

    def format(self) -> str:
        return self._format()

    def _format(self) -> str:
        if self.source_code and self.line >= 0:
            return self._format_with_context()
        if self.line >= 0 and self.column >= 0:
            return f"[行 {self.line}, 列 {self.column}] {self.message}"
        elif self.line >= 0:
            return f"[行 {self.line}] {self.message}"
        return self.message

    def _severity_label(self) -> str:
        labels = {
            Severity.ERROR: "错误",
            Severity.WARNING: "警告",
            Severity.NOTE: "注释",
            Severity.HELP: "帮助",
        }
        return labels.get(self.severity, "错误")

    def _severity_color(self, text: str) -> str:
        colors = {
            Severity.ERROR: ANSI.colorize(text, ANSI.RED, ANSI.BOLD),
            Severity.WARNING: ANSI.colorize(text, ANSI.YELLOW, ANSI.BOLD),
            Severity.NOTE: ANSI.colorize(text, ANSI.BLUE, ANSI.BOLD),
            Severity.HELP: ANSI.colorize(text, ANSI.GREEN, ANSI.BOLD),
        }
        return colors.get(self.severity, text)

    def _format_with_context(self) -> str:
        """带源码上下文的友好格式，类似 Rust 错误输出"""
        lines = self.source_code.split('\n')

        # 确定错误涉及的范围
        start_line = self.line
        start_col = self.column
        end_line = self.line
        end_col = self.column + 1

        if self.span and self.span.end_line is not None:
            start_line = self.span.line
            start_col = self.span.column
            end_line = self.span.end_line
            end_col = self.span.end_column
        elif self.highlight_span:
            start_col, end_col = self.highlight_span
            end_line = start_line

        # 提取出错行及其前后各 1 行
        err_line_idx = max(0, start_line - 1)
        ctx_start = max(0, err_line_idx - 1)
        ctx_end = min(len(lines), end_line + 1)

        parts = []
        label = self._severity_label()
        colored_label = self._severity_color(f"{label}: {self.message}")
        parts.append(colored_label)

        loc_text = f"  --> 第{start_line}行"
        if start_line == end_line:
            loc_text += f"，第{start_col}列"
        else:
            loc_text += f" 到 第{end_line}行，第{end_col}列"
        parts.append(ANSI.colorize(loc_text, ANSI.BLUE))
        parts.append("   |")

        max_line_num_width = len(str(ctx_end))

        for i in range(ctx_start, ctx_end):
            line_num = i + 1
            line_content = lines[i] if i < len(lines) else ""
            line_prefix = f" {line_num:>{max_line_num_width}} | "
            parts.append(ANSI.colorize(line_prefix, ANSI.DIM) + line_content)

            underline = self._compute_underline(
                line_content, line_num,
                start_line, start_col, end_line, end_col
            )
            if underline:
                underline_prefix = f" {' ' * max_line_num_width} | "
                colored_underline = self._severity_color(underline)
                parts.append(
                    ANSI.colorize(underline_prefix, ANSI.DIM) + colored_underline
                )

        # 相关注释
        for note in self.related_notes:
            parts.append("")
            note_label = {
                Severity.NOTE: "注释",
                Severity.HELP: "帮助",
            }.get(note.severity, "注释")
            if note.severity == Severity.NOTE:
                colored_note_label = ANSI.colorize(
                    f"{note_label}: {note.message}", ANSI.BLUE, ANSI.BOLD
                )
            elif note.severity == Severity.HELP:
                colored_note_label = ANSI.colorize(
                    f"{note_label}: {note.message}", ANSI.GREEN, ANSI.BOLD
                )
            else:
                colored_note_label = f"{note_label}: {note.message}"
            parts.append(colored_note_label)

            note_line = note.line if note.line >= 0 else (
                note.span.line if note.span else -1
            )
            if note_line >= 0 and self.source_code:
                note_col = note.column if note.column >= 0 else (
                    note.span.column if note.span else 1
                )
                parts.append(ANSI.colorize(
                    f"  --> 第{note_line}行，第{note_col}列", ANSI.BLUE
                ))
                parts.append("   |")
                note_idx = max(0, note_line - 1)
                note_start = max(0, note_idx - 0)
                note_end = min(len(lines), note_idx + 2)
                for j in range(note_start, note_end):
                    ln = j + 1
                    lc = lines[j] if j < len(lines) else ""
                    lp = f" {ln:>{max_line_num_width}} | "
                    parts.append(ANSI.colorize(lp, ANSI.DIM) + lc)
                    if j == note_idx:
                        up = f" {' ' * max_line_num_width} | "
                        if (note.span and note.span.end_line == note.span.line
                                and note.span.end_column is not None):
                            ul = (
                                " " * (note.span.column - 1)
                                + "^" * (note.span.end_column - note.span.column)
                            )
                        else:
                            ul = " " * (note_col - 1) + "^"
                        parts.append(ANSI.colorize(up, ANSI.DIM) + ANSI.colorize(ul, ANSI.BLUE))

        return "\n".join(parts)

    def _compute_underline(self, line_content: str, line_num: int,
                           start_line: int, start_col: int,
                           end_line: int, end_col: int) -> str:
        if line_num < start_line or line_num > end_line:
            return ""

        if start_line == end_line:
            u_start = start_col - 1
            u_end = end_col - 1
            return " " * u_start + "^" * max(1, u_end - u_start)

        # 多行
        if line_num == start_line:
            u_start = start_col - 1
            return " " * u_start + "^" * max(1, len(line_content) - u_start)
        elif line_num == end_line:
            return "^" * max(1, end_col - 1)
        else:
            return "^" * max(1, len(line_content))


# ============================================================
# 具体错误类型
# ============================================================

class LexerError(NovaError):
    """词法分析错误：非法字符、未闭合字符串等"""

    def __init__(self, message: str, line: int, column: int,
                 source: Optional[str] = None,
                 span: Optional[Span] = None):
        super().__init__(f"词法错误: {message}", line, column,
                         source=source, span=span)


class ParseError(NovaError):
    """语法分析错误：意外的 token、不完整的表达式等"""

    def __init__(self, message: str, line: int = -1, column: int = -1,
                 source: Optional[str] = None,
                 span: Optional[Span] = None):
        super().__init__(f"语法错误: {message}", line, column,
                         source=source, span=span)


class TypeCheckError(NovaError):
    """类型检查错误：类型不匹配、未定义变量、类型推断失败等"""

    def __init__(self, message: str, line: int = -1, column: int = -1,
                 source: Optional[str] = None,
                 span: Optional[Span] = None):
        super().__init__(f"类型错误: {message}", line, column,
                         source=source, span=span)


class RuntimeError_(NovaError):
    """运行时错误：除零、未绑定变量、模式匹配失败等"""

    def __init__(self, message: str, line: int = -1, column: int = -1,
                 source: Optional[str] = None,
                 span: Optional[Span] = None):
        super().__init__(f"运行时错误: {message}", line, column,
                         source=source, span=span)


class MatchFailure(RuntimeError_):
    """模式匹配失败错误：非穷尽 match 表达式运行时没有匹配的分支"""

    def __init__(self, line: int = -1, column: int = -1,
                 source: Optional[str] = None,
                 span: Optional[Span] = None):
        super().__init__("模式匹配失败：没有匹配的分支（考虑添加 _ 通配符）",
                         line, column, source=source, span=span)


class PassError(NovaError):
    """Pass 执行错误：某个优化 Pass 在运行时抛出异常

    包含失败 Pass 的名称、类型（HIR/MIR/LIR）、迭代轮次和原始异常，
    用于提供更丰富的错误上下文，便于定位问题。
    """

    def __init__(self, pass_name: str, pass_type: str, iteration: int,
                 original_error: Exception):
        self.pass_name = pass_name
        self.pass_type = pass_type
        self.iteration = iteration
        self.original_error = original_error
        message = (
            f"{pass_type} Pass '{pass_name}' 在第 {iteration} 轮迭代失败: "
            f"{original_error}"
        )
        super().__init__(message)

    def __str__(self) -> str:
        return self.message


# ============================================================
# 控制流信号
# ============================================================

class BreakSignal(Exception):
    """break 信号：用于跳出循环"""

    def __init__(self, value=None):
        self.value = value


class ContinueSignal(Exception):
    """continue 信号：用于跳过当前迭代"""

    pass


class ReturnSignal(Exception):
    """return 信号：用于函数提前返回（包括 ? 错误传播）"""

    def __init__(self, value=None):
        self.value = value


# ============================================================
# 错误收集器
# ============================================================

class ErrorCollector:
    """收集多个错误而不立即抛出，用于一次性报告所有错误"""

    def __init__(self):
        self.errors: List[NovaError] = []
        self.warnings: List[NovaError] = []

    def add(self, error: NovaError):
        """添加一个错误到收集器"""
        if error.severity == Severity.WARNING:
            self.warnings.append(error)
        else:
            self.errors.append(error)

    def add_error(self, error: NovaError):
        """添加错误"""
        self.errors.append(error)

    def add_warning(self, warning: NovaError):
        """添加警告"""
        self.warnings.append(warning)

    def has_errors(self) -> bool:
        """是否有错误（警告不算）"""
        return len(self.errors) > 0

    def has_any(self) -> bool:
        """是否有任何错误或警告"""
        return len(self.errors) > 0 or len(self.warnings) > 0

    def get_errors(self) -> List[NovaError]:
        """获取所有错误"""
        return self.errors.copy()

    def get_warnings(self) -> List[NovaError]:
        """获取所有警告"""
        return self.warnings.copy()

    def get_all(self) -> List[NovaError]:
        """按顺序获取所有错误和警告"""
        return self.errors + self.warnings

    def raise_first(self):
        """抛出第一个错误（如果有）"""
        if self.errors:
            raise self.errors[0]

    def raise_all(self):
        """抛出所有错误，以第一个为主"""
        if self.errors:
            primary = self.errors[0]
            for note in self.errors[1:]:
                primary.add_note(note.format())
            raise primary

    def format_all(self) -> str:
        """格式化所有收集到的错误"""
        parts = []
        for err in self.errors:
            parts.append(str(err))
        for warn in self.warnings:
            parts.append(str(warn))
        return "\n\n".join(parts)

    def __len__(self) -> int:
        return len(self.errors) + len(self.warnings)

    def __bool__(self) -> bool:
        return self.has_any()
