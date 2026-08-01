"""
Nova 编程语言 - 语法分析器（Parser）

将 Token 流转换为抽象语法树（AST）。
支持：let/mut 绑定、fn 定义、if-then-else、match、lambda、管道操作符、
二元/一元操作符、字面量、ADT 定义、类型别名等。

采用递归下降解析（Recursive Descent Parsing）方法。
"""

from typing import List, Optional

from .ast_nodes import (
    AliasDef,
    Assignment,
    BinaryOp,
    Block,
    BoolLiteral,
    BreakExpr,
    CharLiteral,
    ContinueExpr,
    ErrorExpr,
    ExportDecl,
    FieldAccess,
    FloatLiteral,
    FnCall,
    FnDef,
    ForExpr,
    Identifier,
    IfExpr,
    ImportDecl,
    IntLiteral,
    Lambda,
    LetBinding,
    ListComprehension,
    ListExpr,
    MapExpr,
    MatchArm,
    MatchExpr,
    MutBinding,
    Param,
    PatternBool,
    PatternChar,
    PatternConstructor,
    PatternFloat,
    PatternIdentifier,
    PatternInt,
    PatternList,
    PatternString,
    PatternTuple,
    PatternWildcard,
    Program,
    Span,
    StringLiteral,
    TryExpr,
    TupleExpr,
    TypeBool,
    TypeChar,
    TypeDef,
    TypeFloat,
    TypeFn,
    TypeGeneric,
    TypeIdentifier,
    TypeInt,
    TypeString,
    TypeTuple,
    TypeUnit,
    UnaryOp,
    UnitLiteral,
    VariantDef,
    WhileExpr,
)
from .errors import ParseError, ParseErrorGroup
from .lexer import Token, TokenType


class Parser:
    """Nova 语法分析器（带错误恢复）"""

    # 顶层声明起始的关键字 token 类型，用于错误恢复时的同步标记
    _DECL_START_TOKENS = frozenset({
        TokenType.LET, TokenType.MUT, TokenType.FN, TokenType.TYPE,
        TokenType.ALIAS, TokenType.IMPORT, TokenType.EXPORT,
        TokenType.FOR, TokenType.WHILE,
    })
    # 语句边界 token 类型，用于块内错误恢复时的同步标记
    _STMT_BOUNDARY_TOKENS = frozenset({
        TokenType.LET, TokenType.MUT, TokenType.FOR, TokenType.WHILE,
        TokenType.IF, TokenType.MATCH, TokenType.RBRACE, TokenType.EOF,
        TokenType.PIPE,  # lambda 表达式起始符
    })
    # 顶层声明级最大连续错误数（超过则停止解析，防止雪崩式错误）
    _TOP_LEVEL_MAX_ERRORS = 5
    # 表达式递归链中最大嵌套错误数（超过则返回 ErrorExpr 占位符）
    _EXPR_MAX_NESTED_ERRORS = 3

    # ----------------------------------------------------------
    # SH-1 语法冻结对齐：14 个未来保留字（SYNTAX_FREEZE_v0.5 §2 表 #18-31）
    # 当前 v0.5 版本尚未作为关键字启用，但 parser 层面必须拦截为「不可用作标识符」。
    # ----------------------------------------------------------
    FUTURE_RESERVED_WORDS = frozenset({
        "class", "struct", "enum", "return", "yield",
        "async", "await", "pub", "priv", "self",
        "Self", "super", "where", "with",
    })

    def __init__(self, tokens: List[Token], source: str = ""):
        self.tokens = tokens
        self.pos = 0
        self._source = source
        self._errors: List[ParseError] = []  # 收集的所有解析错误
        self._primary_dispatch = self._build_primary_dispatch()
        self._expr_nested_errors: int = 0  # 表达式递归链嵌套错误计数（实例级跨调用传递）

    # ----------------------------------------------------------
    # 工具方法
    # ----------------------------------------------------------

    def _cur(self) -> Token:
        """当前 token"""
        return self.tokens[self.pos]

    def _peek_type(self) -> TokenType:
        """当前 token 的类型"""
        return self.tokens[self.pos].type

    def _peek_value(self) -> str:
        """当前 token 的值"""
        return self.tokens[self.pos].value

    def _advance(self) -> Token:
        """推进并返回当前 token"""
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def _expect(self, tt: TokenType, msg: str = "") -> Token:
        """期望当前 token 为指定类型，否则报错"""
        tok = self._cur()
        if tok.type != tt:
            detail = msg or f"期望 {tt.name}，但得到 {tok.type.name} ('{tok.value}')"
            raise ParseError(detail, tok.line, tok.column, source=self._source)
        return self._advance()

    def _match(self, tt: TokenType) -> Optional[Token]:
        """如果当前 token 类型匹配则推进，否则不推进"""
        if self._peek_type() == tt:
            return self._advance()
        return None

    def _span(self, tok: Token) -> Span:
        """从 token 创建 Span"""
        return Span(tok.line, tok.column)

    # ----------------------------------------------------------
    # 错误恢复
    # ----------------------------------------------------------

    def _synchronize_to_declaration_boundary(self):
        """Panic mode: 跳过 token 直到遇到下一个顶层声明起始关键字。

        用于 _parse_top_level 失败后恢复：丢弃当前有误的声明，
        定位到下一个声明开头，继续解析后续声明。
        """
        while self._peek_type() != TokenType.EOF:
            # 如果当前 token 是声明起始关键字，停止（不跳过它）
            if self._peek_type() in self._DECL_START_TOKENS:
                break
            # 也检查 IDENT（可能是表达式语句的开头）
            if self._peek_type() == TokenType.IDENT:
                break
            # PIPE 是 lambda 表达式的起始符，也应作为同步边界
            if self._peek_type() == TokenType.PIPE:
                break
            self._advance()

    def _synchronize_to_statement_boundary(self):
        """Panic mode: 在块内跳过 token 直到遇到语句边界。

        用于 _parse_block 内部语句失败后恢复：丢弃当前有误的语句，
        定位到下一条语句的开头或块的结尾。
        """
        while self._peek_type() != TokenType.EOF:
            if self._peek_type() in self._STMT_BOUNDARY_TOKENS:
                break
            # IDENT 可能是赋值语句或表达式语句的开头
            if self._peek_type() == TokenType.IDENT:
                break
            # SEMICOLON 本身是语句终止符，跳过它
            if self._peek_type() == TokenType.SEMICOLON:
                self._advance()
                break
            self._advance()

    # ----------------------------------------------------------
    # 表达式级增量恢复（非 Panic mode，仅替换单个失败子节点为 ErrorExpr）
    # ----------------------------------------------------------

    def _wrap_recover_right(self, parse_func, fallback_span_token=None, skip_tokens_on_error=0):
        """调用 parse_func() 解析右操作数，失败时返回 ErrorExpr 并收集错误。

        用于 BinOp 优先级链、管道操作符、后缀调用等场景的"左半部分已解析，
        右半部分 ParseError"情况：保留已解析的左半 AST，把右半部分替换为
        ErrorExpr 占位节点，避免整个表达式被顶层 Panic mode 丢弃。

        注意：本函数**不会**触发 `_expr_nested_errors` 熔断计数
        （因为我们已经就地精确恢复，不是嵌套雪崩）。

        参数:
            parse_func: 无参可调用对象，执行实际的右操作数解析
            fallback_span_token: 当 ParseError 自身的 line/column 无效时，
                用哪个 token 的 span 作为 ErrorExpr 的 fallback（通常是
                该层级的运算符 token，如 PLUS/STAR 等）
            skip_tokens_on_error: 解析失败后额外消费的 token 数。对于 BinOp
                场景（操作符已被 _advance() 消费）通常为 0；对于 Call 参数等
                场景（错误 token 仍在当前 pos，未被消费）需设为 1，防止
                后续的 _expect/while 判断读到同一个错误 token 引发二次错误。
        返回:
            (result_node, caught_error_flag: bool)
        """
        try:
            return parse_func(), False
        except ParseError as e:
            self._errors.append(e)
            if e.line >= 0 and e.column >= 0:
                err_span = Span(e.line, e.column)
            elif fallback_span_token is not None:
                err_span = self._span(fallback_span_token)
            else:
                err_span = self._span(self._cur())
            # 可选：消费错误 token 或后续 skip_tokens_on_error 个，
            # 使下一个 _peek_type() 不在同一个错误点上重复失败
            for _ in range(skip_tokens_on_error):
                if self._peek_type() == TokenType.EOF:
                    break
                self._advance()
            return ErrorExpr(error=e, span=err_span), True

    # ----------------------------------------------------------
    # 程序入口
    # ----------------------------------------------------------

    def parse(self) -> Program:
        """解析整个程序（带错误恢复，收集多个错误）"""
        decls = []
        self._errors = []
        top_level_errors = 0  # 顶层声明级连续错误计数（三级熔断之 TOP_LEVEL）

        while self._peek_type() != TokenType.EOF:
            try:
                decl = self._parse_top_level()
                if decl is not None:
                    decls.append(decl)
                # 合法声明/表达式语句解析成功 → 重置顶层错误计数器
                # （与 _parse_block 的 block_errors = 0 重置机制一致）
                top_level_errors = 0
            except ParseError as e:
                # 记录错误并同步到下一个声明边界
                self._errors.append(e)
                top_level_errors += 1
                # 若顶层错误过多，放弃剩余内容（防止雪崩式错误）
                if top_level_errors >= self._TOP_LEVEL_MAX_ERRORS:
                    last_err_line = getattr(e, "line", -1)
                    last_err_col = getattr(e, "column", -1)
                    self._errors.append(ParseError(
                        f"已达到顶层错误阈值（{self._TOP_LEVEL_MAX_ERRORS} 个），停止解析剩余内容。"
                        "请先修复上述语法错误后重试。",
                        line=last_err_line,
                        column=last_err_col,
                        source=self._source,
                    ))
                    break
                self._synchronize_to_declaration_boundary()

        # 保存部分解析结果（错误恢复场景下已成功解析的声明）
        # 便于上层通过 parser._partial_decls 获取错误前的解析成果
        self._partial_decls = decls
        # 如果收集了错误，统一抛出
        # 单个错误保持向后兼容直接抛 ParseError；
        # 多个错误用 ParseErrorGroup 包装，方便调用方获取完整诊断
        if self._errors:
            if len(self._errors) == 1:
                raise self._errors[0]
            raise ParseErrorGroup(self._errors)
        return Program(declarations=decls)

    def _parse_top_level(self):
        """解析顶层声明"""
        tt = self._peek_type()

        if tt == TokenType.LET:
            return self._parse_let_binding()
        elif tt == TokenType.MUT:
            return self._parse_mut_binding()
        elif tt == TokenType.FN:
            return self._parse_fn_def()
        elif tt == TokenType.TYPE:
            return self._parse_type_def()
        elif tt == TokenType.ALIAS:
            return self._parse_alias_def()
        elif tt == TokenType.IMPORT:
            return self._parse_import()
        elif tt == TokenType.EXPORT:
            return self._parse_export()
        elif tt == TokenType.FOR:
            return self._parse_for_expr()
        elif tt == TokenType.WHILE:
            return self._parse_while_expr()
        else:
            # 顶层表达式语句
            return self._parse_expression_statement()

    # ----------------------------------------------------------
    # import / export
    # ----------------------------------------------------------

    def _parse_import(self) -> ImportDecl:
        tok = self._expect(TokenType.IMPORT)
        name_tok = self._expect(TokenType.STRING)
        return ImportDecl(module_name=name_tok.value, span=self._span(tok))

    def _parse_export(self) -> ExportDecl:
        tok = self._expect(TokenType.EXPORT)
        name_tok = self._expect(TokenType.IDENT)
        return ExportDecl(name=name_tok.value, span=self._span(tok))

    # ----------------------------------------------------------
    # let / mut 绑定
    # ----------------------------------------------------------

    def _parse_let_binding(self) -> LetBinding:
        """解析不可变 let 绑定：let name [: Type] = expr。"""
        tok = self._expect(TokenType.LET)
        name_tok = self._expect(TokenType.IDENT)
        name = name_tok.value

        # 可选类型注解
        type_ann = None
        if self._match(TokenType.COLON):
            type_ann = self._parse_type_expr()

        self._expect(TokenType.ASSIGN)
        value = self._parse_expression()
        return LetBinding(
            name=name, value=value, type_annotation=type_ann, span=self._span(tok)
        )

    def _parse_mut_binding(self) -> MutBinding:
        """解析可变 mut 绑定：mut name [: Type] = expr。"""
        tok = self._expect(TokenType.MUT)
        name_tok = self._expect(TokenType.IDENT)
        name = name_tok.value

        type_ann = None
        if self._match(TokenType.COLON):
            type_ann = self._parse_type_expr()

        self._expect(TokenType.ASSIGN)
        value = self._parse_expression()
        return MutBinding(
            name=name, value=value, type_annotation=type_ann, span=self._span(tok)
        )

    # ----------------------------------------------------------
    # fn 定义
    # ----------------------------------------------------------

    def _parse_fn_def(self) -> FnDef:
        """解析函数定义：fn name(params) [-> RetType] body。"""
        tok = self._expect(TokenType.FN)
        name_tok = self._expect(TokenType.IDENT)
        name = name_tok.value

        # 参数列表
        self._expect(TokenType.LPAREN)
        params = self._parse_param_list()
        self._expect(TokenType.RPAREN)

        # 返回类型
        ret_type = None
        if self._match(TokenType.ARROW):
            ret_type = self._parse_type_expr()

        # 函数体
        body = self._parse_block_or_expr()

        return FnDef(
            name=name,
            params=params,
            return_type=ret_type,
            body=body,
            span=self._span(tok),
        )

    def _parse_param_list(self) -> List[Param]:
        """解析函数参数列表"""
        params = []
        if self._peek_type() == TokenType.RPAREN:
            return params
        params.append(self._parse_param())
        while self._match(TokenType.COMMA):
            params.append(self._parse_param())
        return params

    def _parse_param(self) -> Param:
        """解析单个函数参数：name [: Type]。"""
        tok = self._cur()
        name_tok = self._expect(TokenType.IDENT)
        type_ann = None
        if self._match(TokenType.COLON):
            type_ann = self._parse_type_expr()
        return Param(
            name=name_tok.value, type_annotation=type_ann, span=self._span(tok)
        )

    # ----------------------------------------------------------
    # type / alias 定义
    # ----------------------------------------------------------

    def _parse_type_def(self) -> TypeDef:
        """解析 ADT 类型定义：type Name { Variant1 | Variant2 ... }。"""
        tok = self._expect(TokenType.TYPE)
        name_tok = self._expect(TokenType.IDENT)
        name = name_tok.value
        self._expect(TokenType.LBRACE)

        variants = []
        if self._peek_type() != TokenType.RBRACE:
            variants.append(self._parse_variant_def())
            # 支持用 | 分隔或直接换行的变体定义
            while (
                self._peek_type() == TokenType.PIPE
                or self._peek_type() == TokenType.IDENT
            ):
                if self._peek_type() == TokenType.PIPE:
                    self._advance()
                variants.append(self._parse_variant_def())

        self._expect(TokenType.RBRACE)
        return TypeDef(name=name, variants=variants, span=self._span(tok))

    def _parse_variant_def(self) -> VariantDef:
        """解析单个 ADT 变体：VariantName [(field1: Type1, ...)]。"""
        tok = self._cur()
        name_tok = self._expect(TokenType.IDENT)
        fields = []

        if self._match(TokenType.LPAREN):
            if self._peek_type() != TokenType.RPAREN:
                # 第一个字段
                field_name = self._expect(TokenType.IDENT)
                self._expect(TokenType.COLON)
                field_type = self._parse_type_expr()
                fields.append((field_name.value, field_type))

                while self._match(TokenType.COMMA):
                    field_name = self._expect(TokenType.IDENT)
                    self._expect(TokenType.COLON)
                    field_type = self._parse_type_expr()
                    fields.append((field_name.value, field_type))

            self._expect(TokenType.RPAREN)

        return VariantDef(name=name_tok.value, fields=fields, span=self._span(tok))

    def _parse_alias_def(self) -> AliasDef:
        """解析类型别名：alias Name = TargetType。"""
        tok = self._expect(TokenType.ALIAS)
        name_tok = self._expect(TokenType.IDENT)
        self._expect(TokenType.ASSIGN)
        target = self._parse_type_expr()
        return AliasDef(name=name_tok.value, target_type=target, span=self._span(tok))

    # ----------------------------------------------------------
    # 类型表达式
    # ----------------------------------------------------------

    def _parse_type_expr(self):
        """解析类型表达式"""
        return self._parse_fn_type()

    def _parse_fn_type(self):
        """解析函数类型：(Int, String) -> Bool"""
        # 先尝试解析普通类型
        ty = self._parse_primary_type()

        if self._peek_type() == TokenType.ARROW:
            # 函数类型：(A, B) -> C
            # 这里 ty 可能是一个元组类型 (代表多参数) 或单个类型 (代表单参数)
            self._advance()  # skip ->
            ret = self._parse_type_expr()

            if isinstance(ty, TypeTuple):
                return TypeFn(param_types=ty.elements, return_type=ret, span=ty.span)
            else:
                return TypeFn(param_types=[ty], return_type=ret, span=ty.span)

        return ty

    def _parse_primary_type(self):
        """解析基础类型（CC 优化前 ≈13，拆分后主入口 CC≤3）

        拆分策略（按 Explore agent 建议）：
          - 主入口：仅负责 TokenType 分发（LPAREN / IDENT / 其他）
          - _parse_tuple_type：处理 (A, B, ...) 元组类型（CC=2）
          - _parse_named_type：处理所有标识符类型（CC=4，内部再分 4 路）
        最高 CC 从 13 降至 4，出榜 Top10 CC≤10 阈值。
        """
        tok = self._cur()
        if tok.type == TokenType.LPAREN:
            return self._parse_tuple_type(tok)
        if tok.type == TokenType.IDENT:
            return self._parse_named_type(tok)
        raise ParseError(
            f"期望类型表达式，但得到 '{tok.value}'",
            tok.line, tok.column, source=self._source,
        )

    # ---- _parse_primary_type 子方法 ----

    def _parse_tuple_type(self, tok):
        """解析元组类型：(Int, String, Bool) → TypeTuple（CC=2）"""
        self._advance()  # 消费 LPAREN
        elements = [self._parse_type_expr()]
        while self._match(TokenType.COMMA):
            elements.append(self._parse_type_expr())
        self._expect(TokenType.RPAREN)
        return TypeTuple(elements=elements, span=self._span(tok))

    # 类级常量：7 种基本类型名 → 构造器（避免每次调用重建 dict）
    _BASIC_TYPE_MAP = {
        "Int": TypeInt, "Float": TypeFloat, "String": TypeString,
        "Bool": TypeBool, "Char": TypeChar, "Unit": TypeUnit,
    }

    def _parse_named_type(self, tok):
        """解析标识符开头的类型：基本类型 / Fn[...] / 泛型 / 自定义（CC=4）"""
        name = tok.value
        # ① 基本类型：Int / Float / String / Bool / Char / Unit
        if name in self._BASIC_TYPE_MAP:
            self._advance()
            return self._BASIC_TYPE_MAP[name](span=self._span(tok))
        # ② Fn 类型：Fn[A, B] -> R（顶层 parse_fn_type 再处理 ->）
        if name == "Fn":
            self._advance()
            if self._match(TokenType.LBRACKET):
                params: list = []
                if self._peek_type() != TokenType.RBRACKET:
                    params.append(self._parse_type_expr())
                    while self._match(TokenType.COMMA):
                        params.append(self._parse_type_expr())
                self._expect(TokenType.RBRACKET)
                return TypeFn(
                    param_types=params,
                    return_type=TypeUnit(span=self._span(tok)),
                    span=self._span(tok),
                )
            return TypeIdentifier(name="Fn", span=self._span(tok))
        # ③ 泛型类型：List[Int] / Map[String, Int]
        self._advance()
        if self._match(TokenType.LBRACKET):
            params = [self._parse_type_expr()]
            while self._match(TokenType.COMMA):
                params.append(self._parse_type_expr())
            self._expect(TokenType.RBRACKET)
            return TypeGeneric(base=name, params=params, span=self._span(tok))
        # ④ 自定义类型标识符：Shape / Status / ...
        return TypeIdentifier(name=name, span=self._span(tok))

    # ----------------------------------------------------------
    # 语句
    # ----------------------------------------------------------

    def _parse_expression_statement(self):
        """解析表达式语句"""
        expr = self._parse_expression()
        return expr

    def _parse_block_or_expr(self):
        """解析代码块 { ... } 或单个表达式"""
        if self._peek_type() == TokenType.LBRACE:
            return self._parse_block()
        return self._parse_expression()

    # 块内语句解析允许的最大连续错误数，超过则放弃该块剩余内容
    _BLOCK_MAX_ERRORS = 3

    def _parse_block_statement(self) -> tuple:
        """解析代码块内的单条语句/表达式（从 _parse_block 拆分出的 dispatch helper）。

        返回值 (kind, payload) 共 4 种形态：
          ("stmt_assign", Assignment)  — 赋值语句，已消费分号
          ("stmt_binding", Let|Mut)    — let/mut 绑定声明，已消费分号
          ("stmt_semicolon", Any)      — 表达式语句（后跟分号 ;）
          ("tail_expression", Any)     — 块尾部表达式（后跟 RBRACE，未消费 RBRACE）
          ("stmt_append_nosep", Any)   — 表达式后无 ;/}/非法后继，作为宽松语句追加

        遇到缺分隔符的非法后继（RPAREN/RBRACKET/COMMA）时直接抛 ParseError，
        不在这里做错误恢复 — 错误恢复由外层 _parse_block 的 except 分支统一处理。
        """
        # 1) 赋值语句：ident = expr（lookahead 2 token）
        if (
            self._peek_type() == TokenType.IDENT
            and self.pos + 1 < len(self.tokens)
            and self.tokens[self.pos + 1].type == TokenType.ASSIGN
        ):
            node = self._parse_assignment()
            self._match(TokenType.SEMICOLON)
            return ("stmt_assign", node)

        # 2) let/mut 绑定声明
        if self._peek_type() in (TokenType.LET, TokenType.MUT):
            if self._peek_type() == TokenType.LET:
                node = self._parse_let_binding()
            else:
                node = self._parse_mut_binding()
            self._match(TokenType.SEMICOLON)
            return ("stmt_binding", node)

        # 3) 通用表达式 → 分号/尾部/非法后继 三路分类
        expr = self._parse_expression()
        if self._match(TokenType.SEMICOLON):
            return ("stmt_semicolon", expr)
        elif self._peek_type() == TokenType.RBRACE:
            # 注意：故意不消费 RBRACE，交给外层 while 条件判断退出循环
            return ("tail_expression", expr)
        else:
            # 检查下一个 token 是否是明显不能开始新表达式的符号
            # 是 → 缺分隔符 ParseError；否 → 宽松追加（兼容隐式语句分隔）
            next_tok = self.tokens[self.pos] if self.pos < len(self.tokens) else None
            if next_tok and next_tok.type in (
                TokenType.RPAREN, TokenType.RBRACKET, TokenType.COMMA
            ):
                raise ParseError(
                    f"缺少 ';' 或 '}}'，在语句结束后找到 {next_tok.type.name}",
                    next_tok.line,
                    next_tok.column,
                )
            return ("stmt_append_nosep", expr)

    def _handle_block_parse_error(self, e: ParseError, block_errors: int) -> int:
        """块内语句解析错误统一处理（从 _parse_block except 块拆分）。

        副作用：错误追加到 self._errors；必要时快进到 RBRACE/EOF 或 panic-mode
        同步到下一条语句边界；消费遗留分号。
        返回值：更新后的 block_errors 计数（供外层 while 循环使用）。
        """
        self._errors.append(e)
        block_errors += 1
        if block_errors >= self._BLOCK_MAX_ERRORS:
            # 错误过多熔断：放弃剩余，直接跳到块尾
            while self._peek_type() not in (TokenType.RBRACE, TokenType.EOF):
                self._advance()
            # 标记一个 sentinel：返回负数表示"已快进，外层应 break"
            return -1
        self._synchronize_to_statement_boundary()
        self._match(TokenType.SEMICOLON)  # 跳过分号（如果有）
        return block_errors

    def _parse_block(self) -> Block:
        """解析代码块（带语句级错误恢复）。

        CC 拆分说明（原 CC=14 → 当前 CC≈5）：
          - 语句级 dispatch 4 路 → 独立为 _parse_block_statement helper
          - 错误恢复 3 路（熔断/同步/消费分号）→ 独立为 _handle_block_parse_error
          - 主循环只剩：while 条件 + try/except + 4 元 kind dispatch + RBRACE expect
        """
        tok = self._expect(TokenType.LBRACE)
        stmts = []
        tail = None
        block_errors = 0

        while self._peek_type() != TokenType.RBRACE:
            try:
                kind, payload = self._parse_block_statement()
            except ParseError as e:
                updated = self._handle_block_parse_error(e, block_errors)
                if updated < 0:
                    break  # 已触发熔断快进，退出块循环
                block_errors = updated
                continue

            block_errors = 0  # 成功解析一条：错误计数清零
            if kind == "stmt_assign" or kind == "stmt_binding" or kind == "stmt_semicolon":
                stmts.append(payload)
            elif kind == "tail_expression":
                tail = payload
                break
            elif kind == "stmt_append_nosep":
                stmts.append(payload)

        self._expect(TokenType.RBRACE)
        return Block(statements=stmts, tail_expression=tail, span=self._span(tok))

    def _parse_assignment(self) -> Assignment:
        """解析赋值 x = expr"""
        tok = self._cur()
        name_tok = self._expect(TokenType.IDENT)
        self._expect(TokenType.ASSIGN)
        value = self._parse_expression()
        return Assignment(name=name_tok.value, value=value, span=self._span(tok))

    # ----------------------------------------------------------
    # 表达式（优先级从低到高）
    # ----------------------------------------------------------

    def _parse_expression(self):
        """表达式入口（带嵌套错误熔断，超过阈值时返回 ErrorExpr 占位符）

        三级熔断之 EXPR 级：表达式递归链中如果嵌套解析失败时累计计数，
        连续/嵌套错误达到 _EXPR_MAX_NESTED_ERRORS 时，不再抛出
        ErrorExpr 占位节点，阻止更深层级的雪崩式错误。
        """
        try:
            result = self._parse_pipe()
            # 合法表达式解析成功 → 重置表达式嵌套错误计数器
            self._expr_nested_errors = 0
            return result
        except ParseError as e:
            self._expr_nested_errors += 1
            if self._expr_nested_errors >= self._EXPR_MAX_NESTED_ERRORS:
                # 达到阈值：将当前错误记录到 self._errors，返回 ErrorExpr 占位
                self._errors.append(e)
                # 超阈值提示：附带位置来自原始错误位置（若不可用则 fallback 到当前 token）
                span = Span(e.line, e.column) if e.line >= 0 and e.column >= 0 else self._span(self._cur())
                # 添加"熔断提示性错误：让用户知道此表达式级的解析已被熔断
                self._errors.append(ParseError(
                    f"表达式嵌套错误过多（阈值 {self._EXPR_MAX_NESTED_ERRORS}），已在表达式级熔断停止解析更深子表达式。",
                    line=span.line,
                    column=span.column,
                    source=self._source,
                ))
                return ErrorExpr(error=e, span=span)
            # 未达阈值：继续向上抛出（让外层语句级/块级错误恢复继续处理）
            raise

    def _parse_pipe(self):
        """管道操作符 |> (优先级最低)

        SH-1 语法冻结对齐（SYNTAX_FREEZE_v0.5 §5）：parser 层 desugar
        为嵌套 FnCall，AST 中不保留独立 PipeExpr 节点。即：
            a |> f      →  FnCall(f,  [a])
            a |> f |> g →  FnCall(g,  [FnCall(f, [a])])
        """
        left = self._parse_for_while_expr()
        while self._match(TokenType.PIPE_GT):
            tok = self.tokens[self.pos - 1]
            # 增量恢复：管道右侧解析失败时（如 `a |> *`），用 ErrorExpr 替换，
            # 保留左侧已解析的表达式，避免整个管道链被 Panic mode 丢弃
            right, _ = self._wrap_recover_right(
                lambda: self._parse_for_while_expr(),
                fallback_span_token=tok,
                skip_tokens_on_error=1,
            )
            # desugar:  left |> right  ===  right(left)
            left = FnCall(callee=right, args=[left], span=self._span(tok))
        return left

    def _parse_for_while_expr(self):
        """for/while 表达式"""
        tt = self._peek_type()
        if tt == TokenType.FOR:
            return self._parse_for_expr()
        elif tt == TokenType.WHILE:
            return self._parse_while_expr()
        return self._parse_if_expr()

    def _parse_for_expr(self) -> ForExpr:
        """解析 for 循环表达式
        形式1: for x in expr { body }
        形式2: for i <- start..end { body }
        形式3: for i <- start..end step n { body }
        """
        tok = self._expect(TokenType.FOR)
        var_tok = self._expect(TokenType.IDENT)
        var_name = var_tok.value
        step_expr = None

        if self._match(TokenType.IN):
            # for x in list_expr { body }
            iterable = self._parse_expression()
        elif self._match(TokenType.LT):
            # for i <- start..end [step n] { body }
            self._expect(TokenType.MINUS)  # 消耗 '-' 构成 '<-'
            start_expr = self._parse_expression()
            self._expect(TokenType.RANGE)
            end_expr = self._parse_expression()

            step_expr = None
            if self._match(TokenType.STEP):
                step_expr = self._parse_expression()

            iterable = ("range", start_expr, end_expr, step_expr)
        else:
            raise ParseError(
                f"for 循环期望 'in' 或 '<-'，但得到 '{self._cur().value}'",
                self._cur().line,
                self._cur().column,
                source=self._source,
            )

        body = self._parse_block_or_expr()
        return ForExpr(
            var_name=var_name,
            iterable=iterable,
            body=body,
            step=step_expr,
            span=self._span(tok),
        )

    def _parse_while_expr(self) -> WhileExpr:
        """解析 while 循环表达式: while condition { body }"""
        tok = self._expect(TokenType.WHILE)
        condition = self._parse_expression()
        body = self._parse_block_or_expr()
        return WhileExpr(condition=condition, body=body, span=self._span(tok))

    def _parse_if_expr(self):
        """if-then-else 表达式"""
        if self._peek_type() != TokenType.IF:
            return self._parse_match_expr()

        tok = self._advance()  # if
        cond = self._parse_expression()
        self._expect(TokenType.THEN)
        then_branch = self._parse_block_or_expr()

        else_branch = None
        if self._match(TokenType.ELSE):
            else_branch = self._parse_block_or_expr()

        return IfExpr(
            condition=cond,
            then_branch=then_branch,
            else_branch=else_branch,
            span=self._span(tok),
        )

    def _parse_match_expr(self):
        """match 表达式"""
        if self._peek_type() != TokenType.MATCH:
            return self._parse_or_expr()

        tok = self._advance()  # match
        subject = self._parse_expression()
        self._expect(TokenType.LBRACE)

        arms = []
        if self._peek_type() != TokenType.RBRACE:
            arms.append(self._parse_match_arm())
            # 支持用逗号分隔或直接换行的分支
            while self._peek_type() == TokenType.COMMA or self._peek_type() in (
                TokenType.IDENT,
                TokenType.UNDERSCORE,
                TokenType.INT,
                TokenType.FLOAT,
                TokenType.STRING,
                TokenType.BOOL,
                TokenType.CHAR,
                TokenType.MINUS,
                TokenType.LPAREN,
                TokenType.LBRACKET,
            ):
                if self._peek_type() == TokenType.COMMA:
                    self._advance()
                arms.append(self._parse_match_arm())

        self._expect(TokenType.RBRACE)
        return MatchExpr(subject=subject, arms=arms, span=self._span(tok))

    def _parse_match_arm(self) -> MatchArm:
        """解析 match 分支，支持可选 guard 条件：pattern if guard -> body"""
        pattern = self._parse_pattern()
        guard = None
        # 检查是否有 guard（pattern 后紧跟 if 关键字，而非 ->）
        if self._peek_type() == TokenType.IF:
            self._advance()  # 消费 if
            guard = self._parse_expression()
        self._expect(TokenType.ARROW)
        body = self._parse_expression()
        return MatchArm(pattern=pattern, guard=guard, body=body)

    # ----------------------------------------------------------
    # 模式
    # ----------------------------------------------------------

    def _parse_pattern(self):
        """解析模式

        使用分发方法处理不同 TokenType 的模式：
        - 简单字面量（通配符、布尔、整数、浮点、字符串）
        - 负数模式
        - 列表模式 [...]
        - 元组模式 (a, b)
        - 构造器模式 Name(args...) 或标识符模式
        """
        tok = self._cur()

        # 简单字面量模式
        literal = self._parse_simple_literal_pattern(tok)
        if literal is not None:
            return literal

        # 负数模式
        if tok.type == TokenType.MINUS:
            return self._parse_negative_pattern(tok)

        # 列表模式 [...]
        if tok.type == TokenType.LBRACKET:
            return self._parse_list_pattern(tok)

        # 元组模式 (a, b)
        if tok.type == TokenType.LPAREN:
            return self._parse_tuple_pattern(tok)

        # 构造器模式 Name(args...) 或标识符
        if tok.type == TokenType.IDENT:
            return self._parse_constructor_or_identifier_pattern(tok)

        raise ParseError(
            f"无效的模式 '{tok.value}'", tok.line, tok.column, source=self._source
        )

    def _parse_simple_literal_pattern(self, tok: Token):
        """解析简单字面量模式（通配符、布尔、整数、浮点、字符串）

        如果当前 token 是简单字面量类型，消费 token 并返回对应 Pattern 节点；
        否则返回 None，由调用方继续尝试其他模式类型。
        """
        if tok.type == TokenType.UNDERSCORE:
            self._advance()
            return PatternWildcard(span=self._span(tok))
        if tok.type == TokenType.BOOL:
            self._advance()
            return PatternBool(value=(tok.value == "true"), span=self._span(tok))
        if tok.type == TokenType.INT:
            self._advance()
            return PatternInt(value=int(tok.value), span=self._span(tok))
        if tok.type == TokenType.FLOAT:
            self._advance()
            return PatternFloat(value=float(tok.value), span=self._span(tok))
        if tok.type == TokenType.STRING:
            self._advance()
            return PatternString(value=tok.value, span=self._span(tok))
        if tok.type == TokenType.CHAR:
            self._advance()
            return PatternChar(value=tok.value, span=self._span(tok))
        return None

    def _parse_negative_pattern(self, tok: Token):
        """解析负数模式（-N 或 -F）

        消费 MINUS token 后，要求下一个 token 必须是 INT 或 FLOAT，
        否则抛出 ParseError。
        """
        self._advance()
        next_tok = self._cur()
        if next_tok.type == TokenType.INT:
            self._advance()
            return PatternInt(value=-int(next_tok.value), span=self._span(tok))
        if next_tok.type == TokenType.FLOAT:
            self._advance()
            return PatternFloat(value=-float(next_tok.value), span=self._span(tok))
        raise ParseError(
            f"负数模式后应为整数或浮点数，得到 '{next_tok.value}'",
            next_tok.line, next_tok.column, source=self._source
        )

    def _parse_list_pattern(self, tok: Token):
        """解析列表模式 [elem1, elem2, ...]"""
        self._advance()
        elems = []
        if self._peek_type() != TokenType.RBRACKET:
            elems.append(self._parse_pattern())
            while self._match(TokenType.COMMA):
                elems.append(self._parse_pattern())
        self._expect(TokenType.RBRACKET)
        return PatternList(elements=elems, span=self._span(tok))

    def _parse_tuple_pattern(self, tok: Token):
        """解析元组模式 (a, b) 或括号表达式 (a)

        单个元素时退化为该元素本身（与表达式语法一致）。
        """
        self._advance()
        elems = []
        if self._peek_type() != TokenType.RPAREN:
            elems.append(self._parse_pattern())
            while self._match(TokenType.COMMA):
                elems.append(self._parse_pattern())
        self._expect(TokenType.RPAREN)
        if len(elems) == 1:
            return elems[0]
        return PatternTuple(elements=elems, span=self._span(tok))

    def _parse_constructor_or_identifier_pattern(self, tok: Token):
        """解析构造器模式 Name(args...) 或标识符模式 Name"""
        self._advance()
        name = tok.value
        if self._peek_type() == TokenType.LPAREN:
            self._advance()
            fields = []
            if self._peek_type() != TokenType.RPAREN:
                fields.append(self._parse_pattern())
                while self._match(TokenType.COMMA):
                    fields.append(self._parse_pattern())
            self._expect(TokenType.RPAREN)
            return PatternConstructor(
                name=name, fields=fields, span=self._span(tok)
            )
        return PatternIdentifier(name=name, span=self._span(tok))

    # ----------------------------------------------------------
    # 逻辑或 (||)
    # ----------------------------------------------------------

    def _parse_or_expr(self):
        left = self._parse_and_expr()
        while self._match(TokenType.OR):
            tok = self.tokens[self.pos - 1]
            right, _ = self._wrap_recover_right(
                lambda: self._parse_and_expr(),
                fallback_span_token=tok,
                skip_tokens_on_error=1,
            )
            left = BinaryOp(op="||", left=left, right=right, span=self._span(tok))
        return left

    # ----------------------------------------------------------
    # 逻辑与 (&&)
    # ----------------------------------------------------------

    def _parse_and_expr(self):
        left = self._parse_bitor_expr()
        while self._match(TokenType.AND):
            tok = self.tokens[self.pos - 1]
            right, _ = self._wrap_recover_right(
                lambda: self._parse_bitor_expr(),
                fallback_span_token=tok,
                skip_tokens_on_error=1,
            )
            left = BinaryOp(op="&&", left=left, right=right, span=self._span(tok))
        return left

    # ----------------------------------------------------------
    # 按位或 (|) — PIPE token 在二元上下文 = 按位或；在主表达式起始 = lambda 起始
    # ----------------------------------------------------------

    def _parse_bitor_expr(self):
        left = self._parse_bitxor_expr()
        while self._match(TokenType.PIPE):
            tok = self.tokens[self.pos - 1]
            right, _ = self._wrap_recover_right(
                lambda: self._parse_bitxor_expr(),
                fallback_span_token=tok,
                skip_tokens_on_error=1,
            )
            left = BinaryOp(op="|", left=left, right=right, span=self._span(tok))
        return left

    # ----------------------------------------------------------
    # 按位异或 (^)
    # ----------------------------------------------------------

    def _parse_bitxor_expr(self):
        left = self._parse_bitand_expr()
        while self._match(TokenType.XOR):
            tok = self.tokens[self.pos - 1]
            right, _ = self._wrap_recover_right(
                lambda: self._parse_bitand_expr(),
                fallback_span_token=tok,
                skip_tokens_on_error=1,
            )
            left = BinaryOp(op="^", left=left, right=right, span=self._span(tok))
        return left

    # ----------------------------------------------------------
    # 按位与 (&)
    # ----------------------------------------------------------

    def _parse_bitand_expr(self):
        left = self._parse_shift_expr()
        while self._match(TokenType.BAND):
            tok = self.tokens[self.pos - 1]
            right, _ = self._wrap_recover_right(
                lambda: self._parse_shift_expr(),
                fallback_span_token=tok,
                skip_tokens_on_error=1,
            )
            left = BinaryOp(op="&", left=left, right=right, span=self._span(tok))
        return left

    # ----------------------------------------------------------
    # 移位 (<<, >>, >>>)
    # ----------------------------------------------------------

    def _parse_shift_expr(self):
        left = self._parse_equality_expr()
        while self._peek_type() in (TokenType.SHL, TokenType.SHR, TokenType.SAR):
            tok = self._advance()
            right, _ = self._wrap_recover_right(
                lambda: self._parse_equality_expr(),
                fallback_span_token=tok,
                skip_tokens_on_error=1,
            )
            left = BinaryOp(op=tok.value, left=left, right=right, span=self._span(tok))
        return left

    # ----------------------------------------------------------
    # 相等性 (==, !=)
    # ----------------------------------------------------------

    def _parse_equality_expr(self):
        left = self._parse_comparison_expr()
        while self._peek_type() in (TokenType.EQ, TokenType.NEQ):
            tok = self._advance()
            right, _ = self._wrap_recover_right(
                lambda: self._parse_comparison_expr(),
                fallback_span_token=tok,
                skip_tokens_on_error=1,
            )
            left = BinaryOp(op=tok.value, left=left, right=right, span=self._span(tok))
        return left

    # ----------------------------------------------------------
    # 比较 (<, >, <=, >=)
    # ----------------------------------------------------------

    def _parse_comparison_expr(self):
        left = self._parse_cons_expr()
        while self._peek_type() in (
            TokenType.LT,
            TokenType.GT,
            TokenType.LTE,
            TokenType.GTE,
        ):
            tok = self._advance()
            right, _ = self._wrap_recover_right(
                lambda: self._parse_cons_expr(),
                fallback_span_token=tok,
                skip_tokens_on_error=1,
            )
            left = BinaryOp(op=tok.value, left=left, right=right, span=self._span(tok))
        return left

    def _parse_cons_expr(self):
        """预留 ++ (字符串拼接) 位置"""
        left = self._parse_additive_expr()
        while self._match(TokenType.PLUSPLUS):
            tok = self.tokens[self.pos - 1]
            right, _ = self._wrap_recover_right(
                lambda: self._parse_additive_expr(),
                fallback_span_token=tok,
                skip_tokens_on_error=1,
            )
            left = BinaryOp(op="++", left=left, right=right, span=self._span(tok))
        return left

    # ----------------------------------------------------------
    # 加减 (+, -)
    # ----------------------------------------------------------

    def _parse_additive_expr(self):
        left = self._parse_multiplicative_expr()
        while self._peek_type() in (TokenType.PLUS, TokenType.MINUS):
            tok = self._advance()
            right, _ = self._wrap_recover_right(
                lambda: self._parse_multiplicative_expr(),
                fallback_span_token=tok,
                skip_tokens_on_error=1,
            )
            left = BinaryOp(op=tok.value, left=left, right=right, span=self._span(tok))
        return left

    # ----------------------------------------------------------
    # 乘除模 (*, /, %)
    # ----------------------------------------------------------

    def _parse_multiplicative_expr(self):
        left = self._parse_unary_expr()
        while self._peek_type() in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            tok = self._advance()
            right, _ = self._wrap_recover_right(
                lambda: self._parse_unary_expr(),
                fallback_span_token=tok,
                skip_tokens_on_error=1,
            )
            left = BinaryOp(op=tok.value, left=left, right=right, span=self._span(tok))
        return left

    # ----------------------------------------------------------
    # 一元操作符 (-, !, ~)
    # ----------------------------------------------------------

    def _parse_unary_expr(self):
        tok = self._cur()
        if tok.type == TokenType.MINUS:
            self._advance()
            operand = self._parse_unary_expr()
            return UnaryOp(op="-", operand=operand, span=self._span(tok))
        if tok.type == TokenType.NOT:
            self._advance()
            operand = self._parse_unary_expr()
            return UnaryOp(op="!", operand=operand, span=self._span(tok))
        if tok.type == TokenType.BNOT:
            self._advance()
            operand = self._parse_unary_expr()
            return UnaryOp(op="~", operand=operand, span=self._span(tok))
        return self._parse_postfix_expr()

    # ----------------------------------------------------------
    # 后缀（函数调用, 字段访问）和 ? 操作符
    # ----------------------------------------------------------

    def _parse_postfix_expr(self):
        expr = self._parse_primary_expr()

        while True:
            # 函数调用 f(args...)
            if self._peek_type() == TokenType.LPAREN:
                paren_tok = self._advance()
                args = []
                if self._peek_type() != TokenType.RPAREN:
                    # 增量恢复：第一个参数解析失败时（如 `f(*)`），用 ErrorExpr 替换，
                    # 保留 callee 已解析的表达式。skip_tokens_on_error=1：
                    # 参数解析在 _parse_expression 内部失败通常没有消费错误 token，
                    # 需要手动跳过 1 个，使后续 _match(COMMA) / _expect(RPAREN) 正常。
                    arg0, _ = self._wrap_recover_right(
                        lambda: self._parse_expression(),
                        fallback_span_token=paren_tok,
                        skip_tokens_on_error=1,
                    )
                    args.append(arg0)
                    while self._match(TokenType.COMMA):
                        # 增量恢复：后续逗号参数单个失败不影响其他参数
                        # （如 `f(1, *, 3)` 保留 arg0=1 arg1=ErrorExpr arg2=3）
                        comma_tok = self.tokens[self.pos - 1]
                        argn, _ = self._wrap_recover_right(
                            lambda: self._parse_expression(),
                            fallback_span_token=comma_tok,
                            skip_tokens_on_error=1,
                        )
                        args.append(argn)
                tok = self._expect(TokenType.RPAREN)
                expr = FnCall(callee=expr, args=args, span=self._span(tok))
            # 字段访问 expr.field 或元组数字索引 expr.0
            elif self._peek_type() == TokenType.DOT:
                self._advance()
                # 支持两种形式：
                #   obj.field  — 标识符字段名（ADT/结构体）
                #   tuple.0    — 数字索引（元组）
                if self._peek_type() == TokenType.IDENT:
                    field_tok = self._advance()
                    field_name = field_tok.value
                elif self._peek_type() == TokenType.INT:
                    field_tok = self._advance()
                    field_name = field_tok.value
                else:
                    tok = self._cur()
                    raise ParseError(
                        f"点号后期望字段名或数字索引，实际得到 {tok.type.name} ('{tok.value}')",
                        tok.line, tok.column, source=self._source
                    )
                expr = FieldAccess(
                    target=expr, field=field_name, span=self._span(field_tok)
                )
            else:
                break

        # ? 错误传播
        if self._match(TokenType.QUESTION):
            tok = self.tokens[self.pos - 1]
            expr = TryExpr(expr=expr, span=self._span(tok))

        return expr

    # ----------------------------------------------------------
    # 基本表达式（字面量、标识符、lambda、列表、元组等）
    # ----------------------------------------------------------

    def _build_primary_dispatch(self):
        """构建 primary 表达式解析调度表（TokenType -> handler）。"""
        return {
            TokenType.INT: self._parse_int_literal,
            TokenType.FLOAT: self._parse_float_literal,
            TokenType.STRING: self._parse_string_literal,
            TokenType.CHAR: self._parse_char_literal,
            TokenType.BOOL: self._parse_bool_literal,
            TokenType.UNIT: self._parse_unit_literal,
            TokenType.IDENT: self._parse_identifier_expr,
            TokenType.BREAK: self._parse_break_expr,
            TokenType.CONTINUE: self._parse_continue_expr,
        }

    def _parse_int_literal(self, tok):
        """解析整数字面量。"""
        self._advance()
        return IntLiteral(value=int(tok.value), span=self._span(tok))

    def _parse_float_literal(self, tok):
        """解析浮点数字面量。"""
        self._advance()
        return FloatLiteral(value=float(tok.value), span=self._span(tok))

    def _parse_string_literal(self, tok):
        """解析字符串字面量。"""
        self._advance()
        return StringLiteral(value=tok.value, span=self._span(tok))

    def _parse_char_literal(self, tok):
        """解析字符字面量。"""
        self._advance()
        return CharLiteral(value=tok.value, span=self._span(tok))

    def _parse_bool_literal(self, tok):
        """解析布尔字面量。"""
        self._advance()
        return BoolLiteral(value=(tok.value == "true"), span=self._span(tok))

    def _parse_unit_literal(self, tok):
        """解析 Unit 字面量。"""
        self._advance()
        return UnitLiteral(span=self._span(tok))

    def _parse_identifier_expr(self, tok):
        """解析标识符表达式。

        SH-1 语法冻结对齐（SYNTAX_FREEZE_v0.5 §2）：14 个未来保留字
        （class/struct/enum/return/yield/async/await/pub/priv/self/Self/super/where/with）
        不作为 Token 产生，但禁止用作标识符，直接报 ParseError。
        """
        if tok.value in self.FUTURE_RESERVED_WORDS:
            raise ParseError(
                f"'{tok.value}' 是保留字，不可用作标识符",
                tok.line, tok.column, source=self._source,
            )
        self._advance()
        return Identifier(name=tok.value, span=self._span(tok))

    def _parse_break_expr(self, tok):
        """解析 break 表达式。"""
        self._advance()
        return BreakExpr(span=self._span(tok))

    def _parse_continue_expr(self, tok):
        """解析 continue 表达式。"""
        self._advance()
        return ContinueExpr(span=self._span(tok))

    def _parse_brace_primary(self):
        """解析 LBRACE 开头的 primary：代码块或 Map 字面量。

        使用**推测解析（speculative parsing）**消除 Map 与 Block 的歧义：
        Nova 语法中 `{` 开头的字面量可能是 Map `{k: v, ...}` 或代码块
        `{stmt1; stmt2; ...}`，两者语法在第一个 `}` 之前都以 `{` 开头，无法
        仅靠 LL(1) 预读一个 token 区分。

        消除算法（LL(*) 回溯）：
          1. 空 `{}` 特殊处理：直接判定为代码块（空 Map 可用 Map() 构造）。
          2. 保存解析器位置 saved_pos，消费 `{`，尝试解析一个表达式。
          3. 如果表达式成功且紧跟 COLON(`:`) → 第一个键值对形态匹配 Map 语法
             → 回滚到 saved_pos，调用 _parse_map_expr() 走完整 Map 解析路径。
          4. 如果表达式解析**抛出 ParseError**（例如输入是 `{ let x = 1; ... }`，
             `let` 不是合法表达式起始 → _parse_expression 抛错），或表达式成功但
             后续 token 不是 COLON → 推测失败，按代码块处理：
             → 回滚到 saved_pos，调用 _parse_block()。

        关于 except ParseError 的静默吞错：
          ⚠️ 此处 `except ParseError: pass` 是**有意设计**而非 bug。
          推测解析阶段的 ParseError 是歧义探测信号（"当前输入不匹配 Map 的
          k:v 首项形态"），而非需要向用户报告的真实语法错误。若在此处记录
          错误或向上抛出，会将所有代码块输入误判为"有语法错误的 Map"。
          真正的语法错误将在随后的 _parse_block() 路径中被重新检测并正确
          报告位置，不会因推测阶段的吞错而丢失。
        """
        # 空 {} 是代码块；非空且第一个表达式后是 COLON 则为 Map
        if self._peek_type() == TokenType.RBRACE:
            return self._parse_block()
        saved_pos = self.pos
        self._advance()  # skip {
        try:
            self._parse_expression()
            if self._peek_type() == TokenType.COLON:
                self.pos = saved_pos
                return self._parse_map_expr()
        except ParseError:
            # 静默吞错：推测解析失败 = 不匹配 Map 形态，回退到 Block
            # 真实错误将在 _parse_block() 中重新检测并报告
            pass
        self.pos = saved_pos
        return self._parse_block()

    def _parse_primary_expr(self):
        """解析 primary 表达式（字面量、标识符、控制流关键字、复合表达式）。"""
        tok = self._cur()

        # 调度表处理简单字面量和关键字
        handler = self._primary_dispatch.get(tok.type)
        if handler is not None:
            return handler(tok)

        # 特殊复合表达式
        if tok.type == TokenType.PIPE:
            return self._parse_lambda()
        if tok.type == TokenType.LBRACKET:
            return self._parse_list_expr()
        if tok.type == TokenType.LPAREN:
            return self._parse_tuple_or_grouped()
        if tok.type == TokenType.LBRACE:
            return self._parse_brace_primary()

        raise ParseError(
            f"意外的 token '{tok.value}'", tok.line, tok.column, source=self._source
        )

    def _parse_lambda(self) -> Lambda:
        """解析 Lambda 表达式 |params| -> Type { body } 或 |params| expr"""
        tok = self._advance()  # skip first |

        params = []
        if self._peek_type() != TokenType.PIPE:
            params.append(self._parse_param())
            while self._match(TokenType.COMMA):
                params.append(self._parse_param())

        self._expect(TokenType.PIPE)

        # 返回类型
        ret_type = None
        if self._match(TokenType.ARROW):
            ret_type = self._parse_type_expr()

        # 函数体
        body = self._parse_block_or_expr()
        return Lambda(
            params=params, return_type=ret_type, body=body, span=self._span(tok)
        )

    def _parse_list_expr(self):
        """解析列表表达式 [1, 2, 3] 或列表推导式 [expr for x in list]"""
        tok = self._expect(TokenType.LBRACKET)

        # 空列表
        if self._peek_type() == TokenType.RBRACKET:
            self._advance()
            return ListExpr(elements=[], span=self._span(tok))

        # 解析第一个表达式
        first_expr = self._parse_expression()

        # 检查是否是列表推导式: [expr for ...]
        if self._peek_type() == TokenType.FOR:
            return self._parse_list_comprehension(tok, first_expr)

        # 普通列表
        elems = [first_expr]
        while self._match(TokenType.COMMA):
            elems.append(self._parse_expression())
        self._expect(TokenType.RBRACKET)
        return ListExpr(elements=elems, span=self._span(tok))

    def _parse_map_expr(self):
        """解析 Map 字面量：{key: value, key2: value2, ...}"""
        tok = self._expect(TokenType.LBRACE)
        pairs = []

        if self._peek_type() != TokenType.RBRACE:
            key = self._parse_expression()
            self._expect(TokenType.COLON)
            value = self._parse_expression()
            pairs.append((key, value))

            while self._match(TokenType.COMMA):
                key = self._parse_expression()
                self._expect(TokenType.COLON)
                value = self._parse_expression()
                pairs.append((key, value))

        self._expect(TokenType.RBRACE)
        return MapExpr(pairs=pairs, span=self._span(tok))

    def _parse_list_comprehension(self, bracket_tok, expr) -> ListComprehension:
        """解析列表推导式的 for 部分及可选 if 过滤
        [expr for var in list]
        [expr for var <- start..end]
        [expr for var <- start..end if cond]
        """
        self._expect(TokenType.FOR)
        var_tok = self._expect(TokenType.IDENT)
        var_name = var_tok.value

        if self._match(TokenType.IN):
            iterable = self._parse_expression()
        elif self._match(TokenType.LT):
            # 范围: var <- start..end
            self._expect(TokenType.MINUS)  # 消耗 '-' 构成 '<-'
            start_expr = self._parse_expression()
            self._expect(TokenType.RANGE)
            end_expr = self._parse_expression()
            iterable = ("range", start_expr, end_expr, None)
        else:
            raise ParseError(
                f"列表推导式期望 'in' 或 '<-'",
                self._cur().line,
                self._cur().column,
                source=self._source,
            )

        # 可选过滤条件: if cond
        filter_cond = None
        if self._match(TokenType.IF):
            filter_cond = self._parse_expression()

        self._expect(TokenType.RBRACKET)
        return ListComprehension(
            expr=expr,
            var_name=var_name,
            iterable=iterable,
            filter_cond=filter_cond,
            span=self._span(bracket_tok),
        )

    def _parse_tuple_or_grouped(self):
        """解析元组 (a, b) 或括号分组 (a)"""
        tok = self._expect(TokenType.LPAREN)

        # 空括号是 Unit
        if self._peek_type() == TokenType.RPAREN:
            self._advance()
            return UnitLiteral(span=self._span(tok))

        # 增量恢复：括号内第一个表达式失败（典型：`(a + *)`），
        # 用 ErrorExpr 替换 first，保留括号外层的 BinOp/Call 结构。
        # skip_tokens_on_error=1：错误 token 未消费时跳过 1 个，
        # 保证后续 _match(COMMA) / _expect(RPAREN) 正常。
        first, _ = self._wrap_recover_right(
            lambda: self._parse_expression(),
            fallback_span_token=tok,
            skip_tokens_on_error=1,
        )

        if self._match(TokenType.COMMA):
            # 元组
            elems = [first]
            elem2, _ = self._wrap_recover_right(
                lambda: self._parse_expression(),
                fallback_span_token=self.tokens[self.pos - 1] if self.pos > 0 else None,
                skip_tokens_on_error=1,
            )
            elems.append(elem2)
            while self._match(TokenType.COMMA):
                elem_n, _ = self._wrap_recover_right(
                    lambda: self._parse_expression(),
                    fallback_span_token=self.tokens[self.pos - 1] if self.pos > 0 else None,
                    skip_tokens_on_error=1,
                )
                elems.append(elem_n)
            self._expect(TokenType.RPAREN)
            return TupleExpr(elements=elems, span=self._span(tok))
        else:
            # 分组表达式：即使 first 是 ErrorExpr 也正常检查 RPAREN
            # （skip_tokens_on_error 已消费 1 个错误 token，RPAREN 应该在当前位置）
            self._expect(TokenType.RPAREN)
            return first
