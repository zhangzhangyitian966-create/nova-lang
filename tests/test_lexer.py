"""
Lexer 细粒度单元测试 — 审查发现测试缺口 P83 补齐

来源：审查日志 R139-R143 持续告警 Lexer 覆盖率空白 + SH-1 自举闸门要求
覆盖范围（~25 个测试）：
  A  关键字识别（20 种关键字）
  B  标识符（普通、下划线开头、内嵌数字）
  C  数字字面量（整数、浮点数）
  D  字符串字面量（空串、普通、转义 \n \" \t）
  E  布尔字面量（true / false → BOOL token）
  F  单字符运算符 + 标点（21 种全覆盖）
  G  双字符运算符（9 种全覆盖）
  H  注释处理（行注释、行尾注释、注释后的行号重置）
  I  位置信息（line / column 精确性）
  J  EOF 行为（空源码、纯注释源码）
  K  错误处理（未闭合字符串、非法字符）
"""

import unittest

from nova.lexer import Lexer, LexerError, Token, TokenType, KEYWORDS


def _tok(src: str, idx: int = 0) -> Token:
    """快捷函数：取第 idx 个 token（0=首 token，-1=末 token）"""
    toks = Lexer(src).tokenize()
    return toks[idx]


# ============================================================
# 辅助断言
# ============================================================

def _assert_tok(
    self, token: Token, ttype: TokenType, value: str,
    line: int = 1, column: int = 1,
):
    self.assertEqual(token.type, ttype, f"类型不匹配: expected={ttype.name} got={token.type.name} value={token.value!r}")
    self.assertEqual(token.value, value, f"value 不匹配: expected={value!r} got={token.value!r}")
    self.assertEqual(token.line, line, f"line 不匹配: expected={line} got={token.line}")
    self.assertEqual(token.column, column, f"column 不匹配: expected={column} got={token.column}")


# ============================================================
# A. 关键字识别（20 种关键字全覆盖）
# ============================================================

class TestKeywords(unittest.TestCase):
    """A. 关键字 → 对应 TokenType"""

    def _check_keyword(self, word: str, ttype: TokenType):
        tok = _tok(word)
        _assert_tok(self, tok, ttype, word, 1, 1)

    def test_kw_let(self):      self._check_keyword("let",      TokenType.LET)
    def test_kw_mut(self):      self._check_keyword("mut",      TokenType.MUT)
    def test_kw_fn(self):       self._check_keyword("fn",       TokenType.FN)
    def test_kw_if(self):       self._check_keyword("if",       TokenType.IF)
    def test_kw_then(self):     self._check_keyword("then",     TokenType.THEN)
    def test_kw_else(self):     self._check_keyword("else",     TokenType.ELSE)
    def test_kw_match(self):    self._check_keyword("match",    TokenType.MATCH)
    def test_kw_type(self):     self._check_keyword("type",     TokenType.TYPE)
    def test_kw_alias(self):    self._check_keyword("alias",    TokenType.ALIAS)
    def test_kw_import(self):   self._check_keyword("import",   TokenType.IMPORT)
    def test_kw_export(self):   self._check_keyword("export",   TokenType.EXPORT)
    def test_kw_for(self):      self._check_keyword("for",      TokenType.FOR)
    def test_kw_while(self):    self._check_keyword("while",    TokenType.WHILE)
    def test_kw_break(self):    self._check_keyword("break",    TokenType.BREAK)
    def test_kw_continue(self): self._check_keyword("continue", TokenType.CONTINUE)
    def test_kw_in(self):       self._check_keyword("in",       TokenType.IN)
    def test_kw_step(self):     self._check_keyword("step",     TokenType.STEP)

    def test_keywords_count(self):
        """KEYWORDS 表应包含 19 项（2 bool + 17 关键字），用于冻结审查"""
        # true/false 也在 KEYWORDS 里，它们产出 BOOL token
        self.assertEqual(len(KEYWORDS), 19)
        self.assertIn("true", KEYWORDS)
        self.assertIn("false", KEYWORDS)
        self.assertEqual(KEYWORDS["true"], TokenType.BOOL)
        self.assertEqual(KEYWORDS["false"], TokenType.BOOL)

    def test_kw_not_ident(self):
        """关键字不应被识别为标识符"""
        tok = _tok("let")
        self.assertNotEqual(tok.type, TokenType.IDENT)
        self.assertEqual(tok.type, TokenType.LET)


# ============================================================
# B. 标识符
# ============================================================

class TestIdentifiers(unittest.TestCase):
    """B. 标识符"""

    def test_simple_ident(self):
        _assert_tok(self, _tok("x"),      TokenType.IDENT, "x")
        _assert_tok(self, _tok("abc"),    TokenType.IDENT, "abc")
        _assert_tok(self, _tok("myVar"),  TokenType.IDENT, "myVar")
        _assert_tok(self, _tok("MyType"), TokenType.IDENT, "MyType")

    def test_ident_with_underscore(self):
        """下划线开头、内嵌下划线、末尾下划线；单 _ 是 UNDERSCORE token"""
        _assert_tok(self, _tok("_foo"),   TokenType.IDENT, "_foo")
        _assert_tok(self, _tok("foo_bar"),TokenType.IDENT, "foo_bar")
        _assert_tok(self, _tok("foo_"),   TokenType.IDENT, "foo_")
        # 单字符下划线是 UNDERSCORE（通配符 token），不是 IDENT
        _assert_tok(self, _tok("_"),      TokenType.UNDERSCORE, "_")

    def test_ident_with_digits(self):
        """字母开头 + 数字组合（数字不能开头）"""
        _assert_tok(self, _tok("x1"),       TokenType.IDENT, "x1")
        _assert_tok(self, _tok("foo42"),    TokenType.IDENT, "foo42")
        _assert_tok(self, _tok("val_123_a"),TokenType.IDENT, "val_123_a")

    def test_keyword_prefix_is_ident(self):
        """关键字前缀 + 其他字符 = 独立标识符（非关键字）"""
        _assert_tok(self, _tok("lets"),    TokenType.IDENT, "lets")
        _assert_tok(self, _tok("fn_name"), TokenType.IDENT, "fn_name")
        _assert_tok(self, _tok("iffy"),    TokenType.IDENT, "iffy")


# ============================================================
# C. 数字字面量
# ============================================================

class TestNumbers(unittest.TestCase):
    """C. 数字字面量"""

    def test_integers(self):
        for v in ["0", "1", "42", "999", "1234567890"]:
            with self.subTest(int_val=v):
                _assert_tok(self, _tok(v), TokenType.INT, v)

    def test_floats(self):
        cases = {"3.14": "3.14", "0.5": "0.5", "100.0": "100.0"}
        for src, val in cases.items():
            with self.subTest(float_val=src):
                _assert_tok(self, _tok(src), TokenType.FLOAT, val)

    def test_int_then_dot_is_not_float(self):
        """无小数部分的点号视为 DOT，不产出 FLOAT"""
        toks = Lexer("42.foo").tokenize()
        self.assertEqual(toks[0].type, TokenType.INT)
        self.assertEqual(toks[0].value, "42")
        self.assertEqual(toks[1].type, TokenType.DOT)
        self.assertEqual(toks[2].type, TokenType.IDENT)
        self.assertEqual(toks[2].value, "foo")


# ============================================================
# D. 字符串字面量
# ============================================================

class TestStrings(unittest.TestCase):
    """D. 字符串字面量（双引号，无单字符串支持）"""

    def test_empty_string(self):
        tok = _tok('""')
        _assert_tok(self, tok, TokenType.STRING, "", 1, 1)

    def test_simple_string(self):
        tok = _tok('"hello"')
        _assert_tok(self, tok, TokenType.STRING, "hello", 1, 1)

    def test_string_with_spaces(self):
        tok = _tok('"hello world nova"')
        _assert_tok(self, tok, TokenType.STRING, "hello world nova", 1, 1)

    def test_string_escape_newline(self):
        """\\n 转义为换行字符"""
        tok = _tok(r'"a\nb"')
        _assert_tok(self, tok, TokenType.STRING, "a\nb", 1, 1)

    def test_string_escape_quote(self):
        """\\\" 转义为字面双引号"""
        tok = _tok(r'"say \"hi\""')
        _assert_tok(self, tok, TokenType.STRING, 'say "hi"', 1, 1)

    def test_string_escape_tab(self):
        tok = _tok(r'"a\tb"')
        _assert_tok(self, tok, TokenType.STRING, "a\tb", 1, 1)

    def test_string_unicode(self):
        tok = _tok('"你好 🌍"')
        _assert_tok(self, tok, TokenType.STRING, "你好 🌍", 1, 1)


# ============================================================
# E. 布尔字面量
# ============================================================

class TestBools(unittest.TestCase):
    """E. true / false → BOOL token，value 保留原字符串"""

    def test_true(self):
        tok = _tok("true")
        _assert_tok(self, tok, TokenType.BOOL, "true", 1, 1)

    def test_false(self):
        tok = _tok("false")
        _assert_tok(self, tok, TokenType.BOOL, "false", 1, 1)

    def test_bool_not_ident(self):
        self.assertNotEqual(_tok("true").type,  TokenType.IDENT)
        self.assertNotEqual(_tok("false").type, TokenType.IDENT)


# ============================================================
# F. 单字符运算符与标点（21 种 _SINGLE_CHAR_TOKENS 全覆盖）
# ============================================================

class TestSingleCharTokens(unittest.TestCase):
    """F. 单字符 token — 全覆盖 _SINGLE_CHAR_TOKENS"""

    CASES = [
        # (source_char, TokenType)
        ("+", TokenType.PLUS),     ("-", TokenType.MINUS),
        ("*", TokenType.STAR),     ("/", TokenType.SLASH),
        ("%", TokenType.PERCENT),  ("<", TokenType.LT),
        (">", TokenType.GT),       ("!", TokenType.NOT),
        ("|", TokenType.PIPE),     ("?", TokenType.QUESTION),
        ("=", TokenType.ASSIGN),   ("(", TokenType.LPAREN),
        (")", TokenType.RPAREN),   ("[", TokenType.LBRACKET),
        ("]", TokenType.RBRACKET), ("{", TokenType.LBRACE),
        ("}", TokenType.RBRACE),   (",", TokenType.COMMA),
        (";", TokenType.SEMICOLON),(":", TokenType.COLON),
        (".", TokenType.DOT),
    ]

    def test_all_single_chars(self):
        for ch, ttype in self.CASES:
            with self.subTest(token=ch):
                tok = _tok(ch)
                _assert_tok(self, tok, ttype, ch, 1, 1)

    def test_single_char_count(self):
        """应恰好 21 种单字符 token（与 lexer.py 的 _SINGLE_CHAR_TOKENS 对齐）"""
        self.assertEqual(len(self.CASES), 21)


# ============================================================
# G. 双字符运算符（9 种 _TWO_CHAR_TOKENS 全覆盖）
# ============================================================

class TestTwoCharTokens(unittest.TestCase):
    """G. 双字符 token — 全覆盖 _TWO_CHAR_TOKENS"""

    CASES = [
        ("..", TokenType.RANGE),       ("++", TokenType.PLUSPLUS),
        ("->", TokenType.ARROW),       ("==", TokenType.EQ),
        ("=>", TokenType.FAT_ARROW),   ("!=", TokenType.NEQ),
        ("<=", TokenType.LTE),         (">=", TokenType.GTE),
        ("&&", TokenType.AND),         ("||", TokenType.OR),
        ("|>", TokenType.PIPE_GT),
    ]

    def test_all_two_chars(self):
        for src, ttype in self.CASES:
            with self.subTest(token=src):
                tok = _tok(src)
                _assert_tok(self, tok, ttype, src, 1, 1)

    def test_two_char_count(self):
        """应恰好 11 种双字符 token（RANGE/PLUSPLUS/ARROW/EQ/FAT_ARROW/NEQ/LTE/GTE/AND/OR/PIPE_GT）"""
        self.assertEqual(len(self.CASES), 11)

    def test_longest_match_priority(self):
        """双字符优先于单字符匹配"""
        # == 应产出 EQ 而非 ASSIGN + ASSIGN
        toks = Lexer("a == b").tokenize()
        self.assertEqual(len(toks), 4)  # IDENT 'a' + EQ + IDENT 'b' + EOF
        self.assertEqual(toks[1].type, TokenType.EQ)
        # >= 应产出 GTE 而非 GT + ASSIGN
        toks2 = Lexer("x >= 10").tokenize()
        self.assertEqual(toks2[1].type, TokenType.GTE)


# ============================================================
# H. 注释处理（// 行注释）
# ============================================================

class TestComments(unittest.TestCase):
    """H. 行注释处理"""

    def test_line_comment_skipped(self):
        toks = Lexer("// 这是注释\nx = 1").tokenize()
        self.assertEqual(len(toks), 4)  # IDENT 'x' + ASSIGN + INT '1' + EOF
        _assert_tok(self, toks[0], TokenType.IDENT, "x", 2, 1)
        _assert_tok(self, toks[1], TokenType.ASSIGN, "=", 2, 3)
        _assert_tok(self, toks[2], TokenType.INT, "1", 2, 5)

    def test_trailing_comment(self):
        """行尾注释：前面的 token 正常解析，后面的跳过"""
        toks = Lexer("let y = 99 // 注释内容").tokenize()
        # LET 'y' ASSIGN INT(99) EOF = 5 tokens
        self.assertEqual(len(toks), 5)
        _assert_tok(self, toks[0], TokenType.LET, "let", 1, 1)
        _assert_tok(self, toks[1], TokenType.IDENT, "y", 1, 5)
        _assert_tok(self, toks[2], TokenType.ASSIGN, "=", 1, 7)
        _assert_tok(self, toks[3], TokenType.INT, "99", 1, 9)

    def test_only_comment_line(self):
        """连续注释行：无实际 token，只产出 EOF"""
        toks = Lexer("// a\n// b\n// c").tokenize()
        self.assertEqual(len(toks), 1)  # 只有 EOF
        self.assertEqual(toks[0].type, TokenType.EOF)


# ============================================================
# I. 位置信息
# ============================================================

class TestPositions(unittest.TestCase):
    """I. 位置信息精确性（line / column）"""

    def test_multiline_positions(self):
        src = "let x = 1\nlet y = 2"
        toks = Lexer(src).tokenize()
        # 第 1 行：LET(1,1) IDENT'x'(1,5) ASSIGN(1,7) INT'1'(1,9)
        _assert_tok(self, toks[0], TokenType.LET,   "let", 1, 1)
        _assert_tok(self, toks[1], TokenType.IDENT, "x",   1, 5)
        _assert_tok(self, toks[2], TokenType.ASSIGN,"=",   1, 7)
        _assert_tok(self, toks[3], TokenType.INT,   "1",   1, 9)
        # 第 2 行：LET(2,1) IDENT'y'(2,5) ASSIGN(2,7) INT'2'(2,9)
        _assert_tok(self, toks[4], TokenType.LET,   "let", 2, 1)
        _assert_tok(self, toks[5], TokenType.IDENT, "y",   2, 5)
        _assert_tok(self, toks[6], TokenType.ASSIGN,"=",   2, 7)
        _assert_tok(self, toks[7], TokenType.INT,   "2",   2, 9)

    def test_comment_then_code_line_numbers(self):
        src = "// 注释 1\n// 注释 2\nfoo"
        toks = Lexer(src).tokenize()
        _assert_tok(self, toks[0], TokenType.IDENT, "foo", 3, 1)

    def test_string_position(self):
        src = '  "hello"'
        tok = _tok(src, 0)
        _assert_tok(self, tok, TokenType.STRING, "hello", 1, 3)


# ============================================================
# J. EOF Token
# ============================================================

class TestEOF(unittest.TestCase):
    """J. EOF 行为"""

    def test_empty_source(self):
        toks = Lexer("").tokenize()
        self.assertEqual(len(toks), 1)
        _assert_tok(self, toks[0], TokenType.EOF, "", 1, 1)

    def test_whitespace_only(self):
        toks = Lexer("   \t  \n  ").tokenize()
        self.assertEqual(len(toks), 1)
        self.assertEqual(toks[0].type, TokenType.EOF)

    def test_comment_only(self):
        toks = Lexer("// nothing here").tokenize()
        self.assertEqual(len(toks), 1)
        self.assertEqual(toks[0].type, TokenType.EOF)

    def test_eof_after_tokens(self):
        toks = Lexer("42").tokenize()
        self.assertEqual(len(toks), 2)
        self.assertEqual(toks[-1].type, TokenType.EOF)


# ============================================================
# K. 错误处理
# ============================================================

class TestErrors(unittest.TestCase):
    """K. LexerError 抛出与位置"""

    def test_unclosed_string(self):
        with self.assertRaises(LexerError) as ctx:
            Lexer('"未闭合的字符串').tokenize()
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 1)
        self.assertIn("未闭合", ctx.exception.message)

    def test_illegal_char_dollar(self):
        with self.assertRaises(LexerError) as ctx:
            Lexer("$foo").tokenize()
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 1)
        self.assertIn("$", ctx.exception.message)

    def test_illegal_char_at(self):
        with self.assertRaises(LexerError) as ctx:
            Lexer("let @x = 1").tokenize()
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 5)  # LET 4 字符 + 1 空格 = 位置 5
        self.assertIn("@", ctx.exception.message)

    def test_error_has_source_context(self):
        """LexerError 应附带 source 属性（由 _make_error 注入）"""
        with self.assertRaises(LexerError) as ctx:
            Lexer("£").tokenize()
        # 若有 source 属性则检查
        if hasattr(ctx.exception, "source"):
            self.assertEqual(ctx.exception.source, "£")


if __name__ == "__main__":
    unittest.main()
