"""
Nova 编程语言 - 语法分析器（Parser）

将 Token 流转换为抽象语法树（AST）。
支持：let/mut 绑定、fn 定义、if-then-else、match、lambda、管道操作符、
二元/一元操作符、字面量、ADT 定义、类型别名等。

采用递归下降解析（Recursive Descent Parsing）方法。
"""

from typing import List, Optional, Any

from nova.ast_nodes import (
    Span, Program, Block,
    IntLiteral, FloatLiteral, StringLiteral, CharLiteral, BoolLiteral, UnitLiteral,
    Identifier, BinaryOp, UnaryOp, PipeExpr, TryExpr,
    Param, Lambda, FnDef, FnCall,
    LetBinding, MutBinding, Assignment,
    IfExpr, MatchArm, MatchExpr,
    ForExpr, WhileExpr, BreakExpr, ContinueExpr,
    PatternWildcard, PatternInt, PatternFloat, PatternString,
    PatternBool, PatternChar, PatternIdentifier, PatternConstructor,
    PatternTuple, PatternList,
    ListExpr, ListComprehension, TupleExpr, MapExpr, FieldAccess, IndexExpr,
    ImportDecl, ExportDecl, TypeDef, VariantDef, AliasDef,
    TypeInt, TypeFloat, TypeString, TypeBool, TypeChar, TypeUnit,
    TypeIdentifier, TypeGeneric, TypeTuple, TypeFn,
)
from nova.lexer import Token, TokenType
from nova.errors import ParseError


class Parser:
    """Nova 语法分析器"""

    def __init__(self, tokens: List[Token], source: str = ""):
        self.tokens = tokens
        self.pos = 0
        self._source = source

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
            span = None
            if tok.end_line is not None and tok.end_col is not None:
                span = Span(tok.line, tok.column, tok.end_line, tok.end_col)
            raise ParseError(detail, tok.line, tok.column, source=self._source, span=span)
        return self._advance()

    def _match(self, tt: TokenType) -> Optional[Token]:
        """如果当前 token 类型匹配则推进，否则不推进"""
        if self._peek_type() == tt:
            return self._advance()
        return None

    def _span(self, tok: Token) -> Span:
        """从 token 创建 Span"""
        if tok.end_line is not None and tok.end_col is not None:
            return Span(tok.line, tok.column, tok.end_line, tok.end_col)
        return Span(tok.line, tok.column)

    # ----------------------------------------------------------
    # 程序入口
    # ----------------------------------------------------------

    def parse(self) -> Program:
        """解析整个程序"""
        decls = []
        while self._peek_type() != TokenType.EOF:
            decls.append(self._parse_top_level())
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
        tok = self._expect(TokenType.LET)
        name_tok = self._expect(TokenType.IDENT)
        name = name_tok.value

        # 可选类型注解
        type_ann = None
        if self._match(TokenType.COLON):
            type_ann = self._parse_type_expr()

        self._expect(TokenType.ASSIGN)
        value = self._parse_expression()
        return LetBinding(name=name, value=value, type_annotation=type_ann, span=self._span(tok))

    def _parse_mut_binding(self) -> MutBinding:
        tok = self._expect(TokenType.MUT)
        name_tok = self._expect(TokenType.IDENT)
        name = name_tok.value

        type_ann = None
        if self._match(TokenType.COLON):
            type_ann = self._parse_type_expr()

        self._expect(TokenType.ASSIGN)
        value = self._parse_expression()
        return MutBinding(name=name, value=value, type_annotation=type_ann, span=self._span(tok))

    # ----------------------------------------------------------
    # fn 定义
    # ----------------------------------------------------------

    def _parse_fn_def(self) -> FnDef:
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

        return FnDef(name=name, params=params, return_type=ret_type, body=body, span=self._span(tok))

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
        tok = self._cur()
        name_tok = self._expect(TokenType.IDENT)
        type_ann = None
        if self._match(TokenType.COLON):
            type_ann = self._parse_type_expr()
        return Param(name=name_tok.value, type_annotation=type_ann, span=self._span(tok))

    # ----------------------------------------------------------
    # type / alias 定义
    # ----------------------------------------------------------

    def _parse_type_def(self) -> TypeDef:
        tok = self._expect(TokenType.TYPE)
        name_tok = self._expect(TokenType.IDENT)
        name = name_tok.value

        # 解析可选的泛型参数列表：type Option[T] { ... }
        type_params = []
        if self._match(TokenType.LBRACKET):
            param_tok = self._expect(TokenType.IDENT)
            type_params.append(param_tok.value)
            while self._match(TokenType.COMMA):
                param_tok = self._expect(TokenType.IDENT)
                type_params.append(param_tok.value)
            self._expect(TokenType.RBRACKET)

        self._expect(TokenType.LBRACE)

        variants = []
        if self._peek_type() != TokenType.RBRACE:
            variants.append(self._parse_variant_def())
            # 支持用 | 分隔或直接换行的变体定义
            while self._peek_type() == TokenType.PIPE or self._peek_type() == TokenType.IDENT:
                if self._peek_type() == TokenType.PIPE:
                    self._advance()
                variants.append(self._parse_variant_def())

        self._expect(TokenType.RBRACE)
        return TypeDef(name=name, variants=variants, type_params=type_params, span=self._span(tok))

    def _parse_variant_def(self) -> VariantDef:
        tok = self._cur()
        name_tok = self._expect(TokenType.IDENT)
        fields = []

        if self._match(TokenType.LPAREN):
            if self._peek_type() != TokenType.RPAREN:
                # 判断是命名字段 (name: Type) 还是匿名字段 (Type)
                saved_pos = self.pos
                first_ident = self._expect(TokenType.IDENT)
                if self._peek_type() == TokenType.COLON:
                    # 命名字段
                    self._advance()  # skip :
                    field_type = self._parse_type_expr()
                    fields.append((first_ident.value, field_type))

                    while self._match(TokenType.COMMA):
                        field_name = self._expect(TokenType.IDENT)
                        self._expect(TokenType.COLON)
                        field_type = self._parse_type_expr()
                        fields.append((field_name.value, field_type))
                else:
                    # 匿名字段，回退并解析为类型表达式
                    self.pos = saved_pos
                    field_type = self._parse_type_expr()
                    fields.append((None, field_type))

                    while self._match(TokenType.COMMA):
                        field_type = self._parse_type_expr()
                        fields.append((None, field_type))

            self._expect(TokenType.RPAREN)

        return VariantDef(name=name_tok.value, fields=fields, span=self._span(tok))

    def _parse_alias_def(self) -> AliasDef:
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
        """解析基础类型"""
        tok = self._cur()

        # 元组类型: (Int, String)
        if tok.type == TokenType.LPAREN:
            self._advance()
            elements = [self._parse_type_expr()]
            while self._match(TokenType.COMMA):
                elements.append(self._parse_type_expr())
            self._expect(TokenType.RPAREN)
            return TypeTuple(elements=elements, span=self._span(tok))

        # 基本类型名
        basic_types = {
            "Int": TypeInt, "Float": TypeFloat, "String": TypeString,
            "Bool": TypeBool, "Char": TypeChar, "Unit": TypeUnit,
        }
        if tok.type == TokenType.IDENT and tok.value in basic_types:
            self._advance()
            return basic_types[tok.value](span=self._span(tok))

        # Fn 类型
        if tok.type == TokenType.IDENT and tok.value == "Fn":
            self._advance()
            if self._match(TokenType.LBRACKET):
                params = []
                if self._peek_type() != TokenType.RBRACKET:
                    params.append(self._parse_type_expr())
                    while self._match(TokenType.COMMA):
                        params.append(self._parse_type_expr())
                self._expect(TokenType.RBRACKET)
                return TypeFn(param_types=params, return_type=TypeUnit(span=self._span(tok)),
                             span=self._span(tok))
            return TypeIdentifier(name="Fn", span=self._span(tok))

        # 泛型类型或自定义类型
        if tok.type == TokenType.IDENT:
            self._advance()
            name = tok.value
            if self._match(TokenType.LBRACKET):
                params = [self._parse_type_expr()]
                while self._match(TokenType.COMMA):
                    params.append(self._parse_type_expr())
                self._expect(TokenType.RBRACKET)
                return TypeGeneric(base=name, params=params, span=self._span(tok))
            return TypeIdentifier(name=name, span=self._span(tok))

        span = Span(tok.line, tok.column, tok.end_line, tok.end_col) if tok.end_line is not None else Span(tok.line, tok.column)
        raise ParseError(f"期望类型表达式，但得到 '{tok.value}'", tok.line, tok.column, source=self._source, span=span)

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

    def _parse_block(self) -> Block:
        """解析代码块"""
        tok = self._expect(TokenType.LBRACE)
        stmts = []
        tail = None

        while self._peek_type() != TokenType.RBRACE:
            # 检查赋值：ident = expr
            if (self._peek_type() == TokenType.IDENT
                    and self.pos + 1 < len(self.tokens)
                    and self.tokens[self.pos + 1].type == TokenType.ASSIGN):
                stmts.append(self._parse_assignment())
                self._match(TokenType.SEMICOLON)
                continue

            # 检查 let/mut 绑定
            if self._peek_type() in (TokenType.LET, TokenType.MUT):
                if self._peek_type() == TokenType.LET:
                    stmts.append(self._parse_let_binding())
                else:
                    stmts.append(self._parse_mut_binding())
                self._match(TokenType.SEMICOLON)
                continue

            expr = self._parse_expression()

            # 用分号分隔语句
            if self._match(TokenType.SEMICOLON):
                stmts.append(expr)
            elif self._peek_type() == TokenType.RBRACE:
                tail = expr
                break
            else:
                stmts.append(expr)

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
        """表达式入口"""
        return self._parse_for_while_expr()

    def _parse_pipe(self):
        """管道操作符 |> (优先级：低于相等性，高于逻辑与)"""
        left = self._parse_equality_expr()
        while self._match(TokenType.PIPE_GT):
            tok = self.tokens[self.pos - 1]
            right = self._parse_equality_expr()
            left = PipeExpr(left=left, right=right, span=self._span(tok))
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

            if self._match(TokenType.STEP):
                step_expr = self._parse_expression()

            iterable = ("range", start_expr, end_expr, step_expr)
        else:
            tok = self._cur()
            span = Span(tok.line, tok.column, tok.end_line, tok.end_col) if tok.end_line is not None else Span(tok.line, tok.column)
            raise ParseError(f"for 循环期望 'in' 或 '<-'，但得到 '{tok.value}'",
                           tok.line, tok.column, source=self._source, span=span)

        body = self._parse_block_or_expr()
        return ForExpr(var_name=var_name, iterable=iterable, body=body,
                       step=step_expr, span=self._span(tok))

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

        return IfExpr(condition=cond, then_branch=then_branch,
                       else_branch=else_branch, span=self._span(tok))

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
            while self._peek_type() == TokenType.COMMA or self._peek_type() in (TokenType.IDENT, TokenType.UNDERSCORE, TokenType.INT, TokenType.FLOAT, TokenType.STRING, TokenType.BOOL, TokenType.LPAREN, TokenType.LBRACKET):
                if self._peek_type() == TokenType.COMMA:
                    self._advance()
                arms.append(self._parse_match_arm())

        self._expect(TokenType.RBRACE)
        return MatchExpr(subject=subject, arms=arms, span=self._span(tok))

    def _parse_match_arm(self) -> MatchArm:
        """解析 match 分支"""
        pattern = self._parse_pattern()
        guard = None
        if self._peek_type() == TokenType.IF:
            self._advance()  # consume 'if'
            guard = self._parse_expression()
        self._expect(TokenType.ARROW)
        body = self._parse_expression()
        return MatchArm(pattern=pattern, guard=guard, body=body)

    # ----------------------------------------------------------
    # 模式
    # ----------------------------------------------------------

    def _parse_pattern(self):
        """解析模式"""
        tok = self._cur()

        # 通配符 _
        if tok.type == TokenType.UNDERSCORE:
            self._advance()
            return PatternWildcard(span=self._span(tok))

        # 布尔
        if tok.type == TokenType.BOOL:
            self._advance()
            return PatternBool(value=(tok.value == "true"), span=self._span(tok))

        # 整数
        if tok.type == TokenType.INT:
            self._advance()
            return PatternInt(value=int(tok.value), span=self._span(tok))

        # 浮点数
        if tok.type == TokenType.FLOAT:
            self._advance()
            return PatternFloat(value=float(tok.value), span=self._span(tok))

        # 字符串
        if tok.type == TokenType.STRING:
            self._advance()
            return PatternString(value=tok.value, span=self._span(tok))

        # 字符
        if tok.type == TokenType.CHAR:
            self._advance()
            return PatternChar(value=tok.value, span=self._span(tok))

        # 负数模式
        if tok.type == TokenType.MINUS:
            self._advance()
            next_tok = self._cur()
            if next_tok.type == TokenType.INT:
                self._advance()
                return PatternInt(value=-int(next_tok.value), span=self._span(tok))
            if next_tok.type == TokenType.FLOAT:
                self._advance()
                return PatternFloat(value=-float(next_tok.value), span=self._span(tok))

        # 列表模式 [...]
        if tok.type == TokenType.LBRACKET:
            self._advance()
            elems = []
            if self._peek_type() != TokenType.RBRACKET:
                elems.append(self._parse_pattern())
                while self._match(TokenType.COMMA):
                    elems.append(self._parse_pattern())
            self._expect(TokenType.RBRACKET)
            return PatternList(elements=elems, span=self._span(tok))

        # 元组模式 (a, b)
        if tok.type == TokenType.LPAREN:
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

        # 构造器模式 Name(args...) 或标识符
        if tok.type == TokenType.IDENT:
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
                return PatternConstructor(name=name, fields=fields, span=self._span(tok))
            return PatternIdentifier(name=name, span=self._span(tok))

        span = Span(tok.line, tok.column, tok.end_line, tok.end_col) if tok.end_line is not None else Span(tok.line, tok.column)
        raise ParseError(f"无效的模式 '{tok.value}'", tok.line, tok.column, source=self._source, span=span)

    # ----------------------------------------------------------
    # 逻辑或 (||)
    # ----------------------------------------------------------

    def _parse_or_expr(self):
        left = self._parse_and_expr()
        while self._match(TokenType.OR):
            tok = self.tokens[self.pos - 1]
            right = self._parse_and_expr()
            left = BinaryOp(op="||", left=left, right=right, span=self._span(tok))
        return left

    # ----------------------------------------------------------
    # 逻辑与 (&&)
    # ----------------------------------------------------------

    def _parse_and_expr(self):
        left = self._parse_pipe()
        while self._match(TokenType.AND):
            tok = self.tokens[self.pos - 1]
            right = self._parse_pipe()
            left = BinaryOp(op="&&", left=left, right=right, span=self._span(tok))
        return left

    # ----------------------------------------------------------
    # 相等性 (==, !=)
    # ----------------------------------------------------------

    def _parse_equality_expr(self):
        left = self._parse_comparison_expr()
        while self._peek_type() in (TokenType.EQ, TokenType.NEQ):
            tok = self._advance()
            right = self._parse_comparison_expr()
            left = BinaryOp(op=tok.value, left=left, right=right, span=self._span(tok))
        return left

    # ----------------------------------------------------------
    # 比较 (<, >, <=, >=)
    # ----------------------------------------------------------

    def _parse_comparison_expr(self):
        left = self._parse_cons_expr()
        while self._peek_type() in (TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE):
            tok = self._advance()
            right = self._parse_cons_expr()
            left = BinaryOp(op=tok.value, left=left, right=right, span=self._span(tok))
        return left

    def _parse_cons_expr(self):
        """预留 ++ (字符串拼接) 位置"""
        left = self._parse_additive_expr()
        while self._match(TokenType.PLUSPLUS):
            tok = self.tokens[self.pos - 1]
            right = self._parse_additive_expr()
            left = BinaryOp(op="++", left=left, right=right, span=self._span(tok))
        return left

    # ----------------------------------------------------------
    # 加减 (+, -)
    # ----------------------------------------------------------

    def _parse_additive_expr(self):
        left = self._parse_multiplicative_expr()
        while self._peek_type() in (TokenType.PLUS, TokenType.MINUS):
            tok = self._advance()
            right = self._parse_multiplicative_expr()
            left = BinaryOp(op=tok.value, left=left, right=right, span=self._span(tok))
        return left

    # ----------------------------------------------------------
    # 乘除模 (*, /, %)
    # ----------------------------------------------------------

    def _parse_multiplicative_expr(self):
        left = self._parse_unary_expr()
        while self._peek_type() in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            tok = self._advance()
            right = self._parse_unary_expr()
            left = BinaryOp(op=tok.value, left=left, right=right, span=self._span(tok))
        return left

    # ----------------------------------------------------------
    # 一元操作符 (-, !)
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
        return self._parse_postfix_expr()

    # ----------------------------------------------------------
    # 后缀（函数调用, 字段访问）和 ? 操作符
    # ----------------------------------------------------------

    def _parse_postfix_expr(self):
        expr = self._parse_primary_expr()

        while True:
            # 函数调用 f(args...)
            if self._peek_type() == TokenType.LPAREN:
                self._advance()
                args = []
                if self._peek_type() != TokenType.RPAREN:
                    args.append(self._parse_expression())
                    while self._match(TokenType.COMMA):
                        args.append(self._parse_expression())
                tok = self._expect(TokenType.RPAREN)
                expr = FnCall(callee=expr, args=args, span=self._span(tok))
            # 字段访问 expr.field 或 expr.0 (索引访问)
            elif self._peek_type() == TokenType.DOT:
                self._advance()
                if self._peek_type() == TokenType.INT:
                    field_tok = self._advance()
                else:
                    field_tok = self._expect(TokenType.IDENT)
                expr = FieldAccess(target=expr, field=field_tok.value, span=self._span(field_tok))
            # 索引访问 expr[index]
            elif self._peek_type() == TokenType.LBRACKET:
                self._advance()
                idx = self._parse_expression()
                tok = self._expect(TokenType.RBRACKET)
                expr = IndexExpr(target=expr, index=idx, span=self._span(tok))
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

    def _parse_primary_expr(self):
        tok = self._cur()

        # 整数字面量
        if tok.type == TokenType.INT:
            self._advance()
            return IntLiteral(value=int(tok.value), span=self._span(tok))

        # 浮点数字面量
        if tok.type == TokenType.FLOAT:
            self._advance()
            return FloatLiteral(value=float(tok.value), span=self._span(tok))

        # 字符串字面量
        if tok.type == TokenType.STRING:
            self._advance()
            return StringLiteral(value=tok.value, span=self._span(tok))

        # 字符字面量
        if tok.type == TokenType.CHAR:
            self._advance()
            return CharLiteral(value=tok.value, span=self._span(tok))

        # 布尔字面量
        if tok.type == TokenType.BOOL:
            self._advance()
            return BoolLiteral(value=(tok.value == "true"), span=self._span(tok))

        # Unit 字面量
        if tok.type == TokenType.UNIT:
            self._advance()
            return UnitLiteral(span=self._span(tok))

        # 标识符
        if tok.type == TokenType.IDENT:
            self._advance()
            return Identifier(name=tok.value, span=self._span(tok))

        # break
        if tok.type == TokenType.BREAK:
            self._advance()
            return BreakExpr(span=self._span(tok))

        # continue
        if tok.type == TokenType.CONTINUE:
            self._advance()
            return ContinueExpr(span=self._span(tok))

        # Lambda: |params| body
        if tok.type == TokenType.PIPE:
            return self._parse_lambda()

        # 列表: [elem, ...] 或列表推导式 [expr for ...]
        if tok.type == TokenType.LBRACKET:
            return self._parse_list_expr()

        # 元组: (elem, ...)
        if tok.type == TokenType.LPAREN:
            return self._parse_tuple_or_grouped()

        # 代码块或 map 字面量
        if tok.type == TokenType.LBRACE:
            if self._is_map_literal():
                return self._parse_map_expr()
            return self._parse_block()

        span = Span(tok.line, tok.column, tok.end_line, tok.end_col) if tok.end_line is not None else Span(tok.line, tok.column)
        raise ParseError(f"意外的 token '{tok.value}'", tok.line, tok.column, source=self._source, span=span)

    def _is_map_literal(self) -> bool:
        """判断当前位置的 `{` 是 map 字面量还是代码块。

        Nova 的 map 语法为 ``{ key => value, ... }``（见 ast_nodes.MapExpr 文档）。
        由于 ``=>`` (FAT_ARROW) 在 Nova 语法中仅用于 map 条目分隔，不会出现在
        代码块的顶层，因此可以安全地用它来区分：

        - ``{}``（紧跟 ``}``）视为空 map；
        - 在匹配的 ``{ ... }`` 内部顶层（深度为 1）出现 ``=>`` 视为 map；
        - 否则视为代码块。

        扫描时会跟踪括号/方括号/花括号深度，避免误把嵌套结构（如
        ``{ let m = { "a" => 1 }; m }`` 中内层 map 的 ``=>``）当作外层的
        map 条目。
        """
        # 当前 token 必须是 {
        # 空 map: { }
        if (self.pos + 1 < len(self.tokens)
                and self.tokens[self.pos + 1].type == TokenType.RBRACE):
            return True

        depth = 1  # 已经进入 { 内部
        i = self.pos + 1
        n = len(self.tokens)
        open_tokens = (TokenType.LBRACE, TokenType.LPAREN, TokenType.LBRACKET)
        close_tokens = (TokenType.RBRACE, TokenType.RPAREN, TokenType.RBRACKET)
        while i < n:
            t = self.tokens[i].type
            if t == TokenType.EOF:
                return False
            if t in open_tokens:
                depth += 1
            elif t in close_tokens:
                depth -= 1
                if depth == 0:
                    # 到达匹配的 }，且未在顶层发现 =>
                    return False
            elif t == TokenType.FAT_ARROW and depth == 1:
                return True
            i += 1
        return False

    def _parse_map_expr(self) -> MapExpr:
        """解析 map 字面量：``{ key => value, key => value, ... }``

        key 和 value 都是表达式；支持空 map ``{}`` 和尾随逗号。
        """
        tok = self._expect(TokenType.LBRACE)
        pairs: List[tuple] = []

        if self._peek_type() != TokenType.RBRACE:
            key = self._parse_expression()
            self._expect(TokenType.FAT_ARROW)
            value = self._parse_expression()
            pairs.append((key, value))

            while self._match(TokenType.COMMA):
                # 允许尾随逗号: { "a" => 1, }
                if self._peek_type() == TokenType.RBRACE:
                    break
                key = self._parse_expression()
                self._expect(TokenType.FAT_ARROW)
                value = self._parse_expression()
                pairs.append((key, value))

        self._expect(TokenType.RBRACE)
        return MapExpr(pairs=pairs, span=self._span(tok))

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
        return Lambda(params=params, return_type=ret_type, body=body, span=self._span(tok))

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
            tok = self._cur()
            span = Span(tok.line, tok.column, tok.end_line, tok.end_col) if tok.end_line is not None else Span(tok.line, tok.column)
            raise ParseError(f"列表推导式期望 'in' 或 '<-'",
                           tok.line, tok.column, source=self._source, span=span)

        # 可选过滤条件: if cond
        filter_cond = None
        if self._match(TokenType.IF):
            filter_cond = self._parse_expression()

        self._expect(TokenType.RBRACKET)
        return ListComprehension(expr=expr, var_name=var_name, iterable=iterable,
                                  filter_cond=filter_cond, span=self._span(bracket_tok))

    def _parse_tuple_or_grouped(self):
        """解析元组 (a, b) 或括号分组 (a)"""
        tok = self._expect(TokenType.LPAREN)

        # 空括号是 Unit
        if self._peek_type() == TokenType.RPAREN:
            self._advance()
            return UnitLiteral(span=self._span(tok))

        first = self._parse_expression()

        if self._match(TokenType.COMMA):
            # 元组
            elems = [first]
            elems.append(self._parse_expression())
            while self._match(TokenType.COMMA):
                elems.append(self._parse_expression())
            self._expect(TokenType.RPAREN)
            return TupleExpr(elements=elems, span=self._span(tok))
        else:
            # 分组表达式
            self._expect(TokenType.RPAREN)
            return first