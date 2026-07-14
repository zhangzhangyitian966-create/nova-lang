"""
测试 Nova 增强错误报告系统的新功能。
"""

import pytest
from nova.errors import (
    NovaError, LexerError, ParseError, TypeCheckError, RuntimeError_,
    SourceSpan, ErrorCollector, Severity, ANSI, RelatedNote,
)
from nova.ast_nodes import Span
from nova.lexer import Lexer
from nova.parser import Parser
from nova.type_checker import TypeChecker


def parse(source: str):
    """辅助函数：将源代码解析为 AST"""
    tokens = Lexer(source).tokenize()
    return Parser(tokens, source=source).parse()


# ============================================================
# SourceSpan / Span 增强
# ============================================================

class TestSourceSpan:
    def test_span_with_end_position(self):
        span = Span(2, 5, 2, 10)
        assert span.line == 2
        assert span.column == 5
        assert span.end_line == 2
        assert span.end_column == 10

    def test_span_backward_compatible(self):
        span = Span(1, 1)
        assert span.end_line is None
        assert span.end_column is None

    def test_error_with_span_sets_line_col(self):
        span = Span(3, 7, 3, 12)
        err = NovaError("test", span=span)
        assert err.line == 3
        assert err.column == 7
        assert err.span is span

    def test_error_span_sets_highlight_span_single_line(self):
        span = Span(2, 5, 2, 10)
        err = NovaError("test", span=span)
        assert err.highlight_span == (5, 10)

    def test_error_multi_line_span_no_highlight_span(self):
        span = Span(2, 5, 4, 10)
        err = NovaError("test", span=span)
        assert err.highlight_span is None


# ============================================================
# 错误收集器
# ============================================================

class TestErrorCollector:
    def test_collect_multiple_errors(self):
        collector = ErrorCollector()
        err1 = TypeCheckError("错误 1", 1, 1)
        err2 = TypeCheckError("错误 2", 2, 2)
        collector.add(err1)
        collector.add(err2)
        assert collector.has_errors()
        assert len(collector) == 2
        assert len(collector.get_errors()) == 2

    def test_collect_warnings_separately(self):
        collector = ErrorCollector()
        warn = NovaError("警告", 1, 1, severity=Severity.WARNING)
        err = NovaError("错误", 2, 2, severity=Severity.ERROR)
        collector.add(warn)
        collector.add(err)
        assert collector.has_errors()
        assert len(collector.get_warnings()) == 1
        assert len(collector.get_errors()) == 1

    def test_raise_first(self):
        collector = ErrorCollector()
        collector.add(TypeCheckError("第一个", 1, 1))
        collector.add(TypeCheckError("第二个", 2, 2))
        with pytest.raises(TypeCheckError) as exc_info:
            collector.raise_first()
        assert "第一个" in str(exc_info.value)

    def test_format_all(self):
        collector = ErrorCollector()
        collector.add(TypeCheckError("错误 A", 1, 1))
        collector.add(TypeCheckError("错误 B", 2, 2))
        text = collector.format_all()
        assert "错误 A" in text
        assert "错误 B" in text

    def test_bool_truthiness(self):
        collector = ErrorCollector()
        assert not collector
        collector.add(TypeCheckError("x", 1, 1))
        assert collector


# ============================================================
# 严重程度与相关注释
# ============================================================

class TestSeverityAndNotes:
    def test_error_severity_levels(self):
        err = NovaError("msg", severity=Severity.ERROR)
        warn = NovaError("msg", severity=Severity.WARNING)
        note = NovaError("msg", severity=Severity.NOTE)
        help_ = NovaError("msg", severity=Severity.HELP)
        assert err.severity == Severity.ERROR
        assert warn.severity == Severity.WARNING
        assert note.severity == Severity.NOTE
        assert help_.severity == Severity.HELP

    def test_add_related_note(self):
        err = NovaError("主错误", line=1, column=1)
        err.add_note("这里出了问题", line=2, column=5)
        assert len(err.related_notes) == 1
        assert err.related_notes[0].message == "这里出了问题"
        assert err.related_notes[0].severity == Severity.NOTE

    def test_add_help(self):
        err = NovaError("主错误", line=1, column=1)
        err.add_help("尝试添加类型注解", line=3, column=1)
        assert len(err.related_notes) == 1
        assert err.related_notes[0].severity == Severity.HELP

    def test_related_note_with_span(self):
        err = NovaError("主错误", line=1, column=1)
        note_span = Span(2, 3, 2, 8)
        err.add_note("相关", span=note_span)
        assert err.related_notes[0].span == note_span


# ============================================================
# ANSI 颜色输出
# ============================================================

class TestANSIColors:
    def test_colorize_when_disabled(self, monkeypatch):
        monkeypatch.setattr(ANSI, "enabled", lambda: False)
        result = ANSI.colorize("text", ANSI.RED, ANSI.BOLD)
        assert result == "text"

    def test_colorize_when_enabled(self, monkeypatch):
        monkeypatch.setattr(ANSI, "enabled", lambda: True)
        result = ANSI.colorize("text", ANSI.RED)
        assert result.startswith("\033[31m")
        assert result.endswith("\033[0m")

    def test_error_output_contains_ansi_when_enabled(self, monkeypatch):
        monkeypatch.setattr(ANSI, "enabled", lambda: True)
        err = TypeCheckError("类型错误", 1, 1)
        err.source_code = "let x: Int = true"
        text = str(err)
        assert "\033[" in text

    def test_error_output_no_ansi_when_disabled(self, monkeypatch):
        monkeypatch.setattr(ANSI, "enabled", lambda: False)
        err = TypeCheckError("类型错误", 1, 1)
        err.source_code = "let x: Int = true"
        text = str(err)
        assert "\033[" not in text


# ============================================================
# 多行错误高亮
# ============================================================

class TestMultiLineHighlight:
    def test_multi_line_underline(self):
        source = "line1\nsecond line here\nthird line here\nfourth"
        span = Span(2, 3, 3, 8)
        err = NovaError("多行错误", span=span)
        err.source_code = source
        text = str(err)
        assert "第2行 到 第3行，第8列" in text
        assert "second line here" in text
        assert "third line here" in text
        # 检查第2行有下划线
        lines = text.split("\n")
        underline_line2 = [l for l in lines if "^" in l and "second" not in l]
        assert len(underline_line2) >= 1

    def test_single_line_underline_from_span(self):
        source = "let x = 42"
        span = Span(1, 5, 1, 10)
        err = NovaError("范围错误", span=span)
        err.source_code = source
        text = str(err)
        assert "^^^^^" in text

    def test_old_highlight_span_still_works(self):
        err = NovaError("旧格式", line=2, column=5)
        err.source_code = "line1\nabcDEFGhij\nline3"
        err.highlight_span = (5, 10)
        text = str(err)
        assert "^^^^^" in text


# ============================================================
# 集成：错误收集 + 类型检查器
# ============================================================

class TestTypeCheckerErrorCollection:
    def test_collect_multiple_type_errors(self):
        source = """
let x: Int = true
let y: String = 42
let z = undefined_var
"""
        ast = parse(source)
        checker = TypeChecker(source=source, collect_errors=True)
        checker.check_program(ast)
        assert checker.error_collector.has_errors()
        errors = checker.error_collector.get_errors()
        assert len(errors) >= 3
        messages = [e.message for e in errors]
        assert any("Int" in m for m in messages)
        assert any("String" in m for m in messages)
        assert any("undefined_var" in m or "未定义" in m for m in messages)

    def test_default_mode_raises_immediately(self):
        source = "let x: Int = true"
        ast = parse(source)
        checker = TypeChecker(source=source, collect_errors=False)
        with pytest.raises(TypeCheckError):
            checker.check_program(ast)

    def test_collect_errors_does_not_raise_by_default(self):
        source = "let x: Int = true\nlet y: String = 42"
        ast = parse(source)
        checker = TypeChecker(source=source, collect_errors=True)
        # 不应抛出
        checker.check_program(ast)
        assert len(checker.error_collector.get_errors()) == 2


# ============================================================
# 集成：增强错误与 Lexer / Parser
# ============================================================

class TestEnhancedLexerParserErrors:
    def test_lexer_error_has_span(self):
        """非法字符不再抛出 LexerError，而是记录到 self.errors 并跳过"""
        lexer = Lexer("let x = @")
        lexer.tokenize()
        assert len(lexer.errors) == 1
        assert "非法字符 '@'" in lexer.errors[0]

    def test_parser_error_has_span(self):
        with pytest.raises(ParseError) as exc_info:
            parse("let = 42")
        err = exc_info.value
        assert err.span is not None


# ============================================================
# 错误格式化边界情况
# ============================================================

class TestErrorFormattingEdgeCases:
    def test_error_without_source_or_line(self):
        err = NovaError("无位置")
        assert str(err) == "无位置"

    def test_error_line_only(self):
        err = NovaError("仅行号", line=5)
        assert str(err) == "[行 5] 仅行号"

    def test_related_note_without_source(self):
        err = NovaError("主错误", line=1, column=1)
        err.add_note("提示", line=2, column=3)
        text = str(err)
        # 没有 source_code 时不应崩溃
        assert "主错误" in text

    def test_empty_source_code(self):
        err = NovaError("空源码", line=1, column=1)
        err.source_code = ""
        text = str(err)
        assert "空源码" in text
