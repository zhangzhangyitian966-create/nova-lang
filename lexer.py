"""
Nova 编程语言 - 词法分析器（Lexer / Tokenizer）

将源代码字符串转换为 Token 流。支持关键字、标识符、数字、
字符串、操作符、标点符号和注释的识别。
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional

from .errors import LexerError

# ============================================================
# Token 类型枚举
# ============================================================


class TokenType(Enum):
    # 字面量
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    CHAR = auto()
    BOOL = auto()  # true / false

    # 标识符
    IDENT = auto()

    # 关键字
    LET = auto()
    MUT = auto()
    FN = auto()
    IF = auto()
    THEN = auto()
    ELSE = auto()
    MATCH = auto()
    TYPE = auto()
    ALIAS = auto()
    IMPORT = auto()
    EXPORT = auto()

    # 循环相关关键字
    FOR = auto()
    WHILE = auto()
    BREAK = auto()
    CONTINUE = auto()
    IN = auto()
    STEP = auto()
    RANGE = auto()  # ..

    # 操作符
    PLUS = auto()  # +
    MINUS = auto()  # -
    STAR = auto()  # *
    SLASH = auto()  # /
    PERCENT = auto()  # %
    PLUSPLUS = auto()  # ++ (字符串拼接)
    EQ = auto()  # ==
    NEQ = auto()  # !=
    LT = auto()  # <
    GT = auto()  # >
    LTE = auto()  # <=
    GTE = auto()  # >=
    AND = auto()  # &&
    OR = auto()  # ||
    NOT = auto()  # !
    PIPE = auto()  # | (lambda 参数分隔)
    PIPE_GT = auto()  # |> (管道操作符)
    ARROW = auto()  # ->
    FAT_ARROW = auto()  # =>
    QUESTION = auto()  # ? (错误传播)
    ASSIGN = auto()  # =

    # 标点符号
    LPAREN = auto()  # (
    RPAREN = auto()  # )
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]
    LBRACE = auto()  # {
    RBRACE = auto()  # }
    COMMA = auto()  # ,
    SEMICOLON = auto()  # ;
    COLON = auto()  # :
    DOT = auto()  # .
    UNDERSCORE = auto()  # _ (通配符)
    PIPE_VARIANT = auto()  # | (ADT 变体分隔符，在 type 定义中使用)

    # 特殊
    UNIT = auto()  # () 空括号
    EOF = auto()


# ============================================================
# Token 数据类
# ============================================================


@dataclass
class Token:
    """词法单元"""

    type: TokenType
    value: str
    line: int
    column: int

    def __repr__(self):
        return (
            f"Token({self.type.name}, {self.value!r}, 行:{self.line}, 列:{self.column})"
        )


# ============================================================
# 关键字映射表
# ============================================================

KEYWORDS = {
    "let": TokenType.LET,
    "mut": TokenType.MUT,
    "fn": TokenType.FN,
    "if": TokenType.IF,
    "then": TokenType.THEN,
    "else": TokenType.ELSE,
    "match": TokenType.MATCH,
    "type": TokenType.TYPE,
    "alias": TokenType.ALIAS,
    "import": TokenType.IMPORT,
    "export": TokenType.EXPORT,
    "for": TokenType.FOR,
    "while": TokenType.WHILE,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    "in": TokenType.IN,
    "step": TokenType.STEP,
    "true": TokenType.BOOL,
    "false": TokenType.BOOL,
}


# ============================================================
# 词法分析器
# ============================================================


class Lexer:
    """Nova 词法分析器"""

    # 双字符操作符映射表（第一个字符 -> {第二个字符: TokenType}）
    _TWO_CHAR_TOKENS: Dict[str, Dict[str, TokenType]] = {
        ".": {".": TokenType.RANGE},
        "+": {"+": TokenType.PLUSPLUS},
        "-": {">": TokenType.ARROW},
        "=": {"=": TokenType.EQ, ">": TokenType.FAT_ARROW},
        "!": {"=": TokenType.NEQ},
        "<": {"=": TokenType.LTE},
        ">": {"=": TokenType.GTE},
        "&": {"&": TokenType.AND},
        "|": {"|": TokenType.OR, ">": TokenType.PIPE_GT},
    }

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

    def _make_error(self, message: str, line: int, column: int) -> LexerError:
        """创建 LexerError，自动附带源代码上下文"""
        return LexerError(message, line, column, source=self.source)

    def _peek(self) -> Optional[str]:
        """查看当前字符（不推进）"""
        if self.pos < len(self.source):
            return self.source[self.pos]
        return None

    def _peek_ahead(self, offset: int = 1) -> Optional[str]:
        """查看前方 offset 处的字符"""
        idx = self.pos + offset
        if idx < len(self.source):
            return self.source[idx]
        return None

    def _advance(self) -> str:
        """推进并返回当前字符"""
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _skip_whitespace_and_comments(self):
        """跳过空白字符和 // 注释"""
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            # 空白字符
            if ch in (" ", "\t", "\n", "\r"):
                self._advance()
            # // 单行注释
            elif ch == "/" and self._peek_ahead() == "/":
                self._advance()  # 跳过 /
                self._advance()  # 跳过 /
                while self.pos < len(self.source) and self.source[self.pos] != "\n":
                    self._advance()
            else:
                break

    def _read_number(self) -> Token:
        """读取数字（整数或浮点数）"""
        start_line = self.line
        start_col = self.column
        num_str = ""

        while self.pos < len(self.source) and self.source[self.pos].isdigit():
            num_str += self._advance()

        # 浮点数
        if (
            self.pos < len(self.source)
            and self.source[self.pos] == "."
            and self._peek_ahead() is not None
            and self._peek_ahead().isdigit()
        ):
            num_str += self._advance()  # 小数点
            while self.pos < len(self.source) and self.source[self.pos].isdigit():
                num_str += self._advance()
            return Token(TokenType.FLOAT, num_str, start_line, start_col)

        return Token(TokenType.INT, num_str, start_line, start_col)

    def _read_string(self) -> Token:
        """读取字符串字面量 "..." """
        start_line = self.line
        start_col = self.column
        self._advance()  # 跳过开始引号 "
        result = ""

        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch == '"':
                self._advance()  # 跳过结束引号
                return Token(TokenType.STRING, result, start_line, start_col)
            elif ch == "\\":
                self._advance()  # 跳过反斜杠
                esc = self._advance()
                # 处理转义字符
                if esc == "n":
                    result += "\n"
                elif esc == "t":
                    result += "\t"
                elif esc == "r":
                    result += "\r"
                elif esc == "\\":
                    result += "\\"
                elif esc == '"':
                    result += '"'
                else:
                    result += esc
            elif ch == "\n":
                raise self._make_error("未闭合的字符串字面量", start_line, start_col)
            else:
                result += self._advance()

        raise self._make_error("未闭合的字符串字面量", start_line, start_col)

    def _read_char(self) -> Token:
        """读取字符字面量 'x'"""
        start_line = self.line
        start_col = self.column
        self._advance()  # 跳过开始单引号 '

        if self.pos >= len(self.source):
            raise self._make_error("未闭合的字符字面量", start_line, start_col)

        ch = self.source[self.pos]
        if ch == "\\":
            self._advance()  # 跳过反斜杠
            esc = self._advance()
            if esc == "n":
                ch = "\n"
            elif esc == "t":
                ch = "\t"
            elif esc == "r":
                ch = "\r"
            elif esc == "\\":
                ch = "\\"
            elif esc == "'":
                ch = "'"
            else:
                ch = esc
        else:
            self._advance()

        if self.pos >= len(self.source) or self.source[self.pos] != "'":
            raise self._make_error("字符字面量应以 ' 结尾", start_line, start_col)

        self._advance()  # 跳过结束单引号 '
        return Token(TokenType.CHAR, ch, start_line, start_col)

    def _read_identifier(self) -> Token:
        """读取标识符或关键字"""
        start_line = self.line
        start_col = self.column
        name = ""

        while self.pos < len(self.source) and (
            self.source[self.pos].isalnum() or self.source[self.pos] == "_"
        ):
            name += self._advance()

        # 检查是否是关键字
        if name in KEYWORDS:
            tt = KEYWORDS[name]
            if tt == TokenType.BOOL:
                return Token(tt, name, start_line, start_col)
            return Token(tt, name, start_line, start_col)

        # 单独下划线是通配符
        if name == "_":
            return Token(TokenType.UNDERSCORE, "_", start_line, start_col)

        # _x 或 x_ 等含下划线的名称是普通标识符
        return Token(TokenType.IDENT, name, start_line, start_col)

    def _next_token(self) -> Token:
        """获取下一个 token"""
        self._skip_whitespace_and_comments()

        if self.pos >= len(self.source):
            return Token(TokenType.EOF, "", self.line, self.column)

        start_line = self.line
        start_col = self.column
        ch = self.source[self.pos]

        # 数字
        if ch.isdigit():
            return self._read_number()

        # 字符串
        if ch == '"':
            return self._read_string()

        # 字符
        if ch == "'":
            return self._read_char()

        # 标识符 / 关键字
        if ch.isalpha() or ch == "_":
            return self._read_identifier()

        # ( 始终为 LPAREN（UNIT 由 parser 处理）
        if ch == "(":
            self._advance()
            return Token(TokenType.LPAREN, "(", start_line, start_col)

        # 操作符和标点
        self._advance()

        # 双字符操作符（表驱动）
        next_ch = self._peek()
        if next_ch:
            second_map = self._TWO_CHAR_TOKENS.get(ch)
            if second_map and next_ch in second_map:
                token_type = second_map[next_ch]
                self._advance()
                return Token(token_type, ch + next_ch, start_line, start_col)

        # 单字符 token
        single_char_tokens = {
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.STAR,
            "/": TokenType.SLASH,
            "%": TokenType.PERCENT,
            "<": TokenType.LT,
            ">": TokenType.GT,
            "!": TokenType.NOT,
            "|": TokenType.PIPE,
            "?": TokenType.QUESTION,
            "=": TokenType.ASSIGN,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "[": TokenType.LBRACKET,
            "]": TokenType.RBRACKET,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            ",": TokenType.COMMA,
            ";": TokenType.SEMICOLON,
            ":": TokenType.COLON,
            ".": TokenType.DOT,
        }

        if ch in single_char_tokens:
            return Token(single_char_tokens[ch], ch, start_line, start_col)

        raise self._make_error(f"非法字符 '{ch}'", start_line, start_col)

    def tokenize(self) -> List[Token]:
        """将整个源代码转换为 token 列表"""
        tokens = []
        while True:
            token = self._next_token()
            tokens.append(token)
            if token.type == TokenType.EOF:
                break
        self.tokens = tokens
        return tokens
