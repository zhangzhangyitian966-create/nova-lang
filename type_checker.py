"""
Nova 编程语言 - 类型检查器

实现简化的 Hindley-Milner 类型推断。
检查类型正确性，推断表达式类型，报告类型错误。

类型系统：
- 基本类型：Int, Float, String, Bool, Char, Unit
- 复合类型：List[T], Map[K, V], Tuple[T1, ...], Fn(A, B) -> C
- 代数数据类型（ADT）
- 支持类型变量（TypeVar）进行推断
"""

from typing import Dict, List, Optional, Set

from .ast_nodes import (
    AliasDef,
    Assignment,
    BinaryOp,
    Block,
    BoolLiteral,
    BreakExpr,
    CharLiteral,
    ContinueExpr,
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
    MatchExpr,
    MutBinding,
    PipeExpr,
    Program,
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
    WhileExpr,
)
from .errors import TypeCheckError

# ============================================================
# 类型表示
# ============================================================


class NovaType:
    """Nova 类型基类"""

    pass


class PrimType(NovaType):
    """基本类型：Int, Float, String, Bool, Char, Unit"""

    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other):
        return isinstance(other, PrimType) and self.name == other.name

    def __hash__(self):
        return hash(("Prim", self.name))

    def __repr__(self):
        return self.name


class ListType(NovaType):
    """列表类型 List[ElemType]"""

    def __init__(self, elem_type: NovaType):
        self.elem_type = elem_type

    def __eq__(self, other):
        return isinstance(other, ListType) and self.elem_type == other.elem_type

    def __hash__(self):
        return hash(("List", self.elem_type))

    def __repr__(self):
        return f"List[{self.elem_type}]"


class MapType(NovaType):
    """Map 类型 Map[KeyType, ValueType]"""

    def __init__(self, key_type: NovaType, value_type: NovaType):
        self.key_type = key_type
        self.value_type = value_type

    def __eq__(self, other):
        return (
            isinstance(other, MapType)
            and self.key_type == other.key_type
            and self.value_type == other.value_type
        )

    def __hash__(self):
        return hash(("Map", self.key_type, self.value_type))

    def __repr__(self):
        return f"Map[{self.key_type}, {self.value_type}]"


class TupleType(NovaType):
    """元组类型 (T1, T2, ...)"""

    def __init__(self, elements: List[NovaType]):
        self.elements = elements

    def __eq__(self, other):
        return (
            isinstance(other, TupleType)
            and len(self.elements) == len(other.elements)
            and all(a == b for a, b in zip(self.elements, other.elements))
        )

    def __hash__(self):
        return hash(("Tuple", tuple(hash(e) for e in self.elements)))

    def __repr__(self):
        return f"({', '.join(str(e) for e in self.elements)})"


class FnType(NovaType):
    """函数类型 (T1, T2, ...) -> RetType"""

    def __init__(self, param_types: List[NovaType], return_type: NovaType):
        self.param_types = param_types
        self.return_type = return_type

    def __eq__(self, other):
        return (
            isinstance(other, FnType)
            and len(self.param_types) == len(other.param_types)
            and all(a == b for a, b in zip(self.param_types, other.param_types))
            and self.return_type == other.return_type
        )

    def __hash__(self):
        return hash(
            ("Fn", tuple(hash(p) for p in self.param_types), hash(self.return_type))
        )

    def __repr__(self):
        params = ", ".join(str(p) for p in self.param_types)
        return f"({params}) -> {self.return_type}"


class ADTType(NovaType):
    """代数数据类型"""

    def __init__(self, name: str, type_params: List[NovaType] = None):
        self.name = name
        self.type_params = type_params or []

    def __eq__(self, other):
        if not isinstance(other, ADTType) or self.name != other.name:
            return False
        if len(self.type_params) != len(other.type_params):
            return False
        return all(p1 == p2 for p1, p2 in zip(self.type_params, other.type_params))

    def __hash__(self):
        return hash(("ADT", self.name, tuple(self.type_params)))

    def __repr__(self):
        if self.type_params:
            return f"{self.name}[{', '.join(str(p) for p in self.type_params)}]"
        return self.name


class TypeVar(NovaType):
    """类型变量（用于推断）"""

    _counter = 0

    def __init__(self, name: str = None):
        if name is None:
            TypeVar._counter += 1
            self.name = f"T{TypeVar._counter}"
        else:
            self.name = name

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return hash(id(self))

    def __repr__(self):
        return self.name


# ============================================================
# 类型环境
# ============================================================


class TypeEnv:
    """类型环境"""

    def __init__(self, parent: Optional["TypeEnv"] = None):
        self.parent = parent
        self.types: Dict[str, NovaType] = {}
        self.mutables: Set[str] = set()  # 可变绑定的名称集合
        self.adt_variants: Dict[str, List[tuple]] = (
            {}
        )  # adt_name -> [(variant_name, [field_types])]
        self.aliases: Dict[str, NovaType] = {}

    def define(self, name: str, ty: NovaType, mutable: bool = False):
        self.types[name] = ty
        if mutable:
            self.mutables.add(name)

    def lookup(self, name: str) -> Optional[NovaType]:
        if name in self.types:
            return self.types[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def is_mutable(self, name: str) -> bool:
        """检查绑定是否可变（mut）。向上查找所有父环境。"""
        if name in self.mutables:
            return True
        if self.parent:
            return self.parent.is_mutable(name)
        return False

    def get_all_adt_variants(self) -> Dict[str, List[tuple]]:
        """获取当前环境及所有父环境的 ADT 变体信息"""
        result = {}
        if self.parent:
            result.update(self.parent.get_all_adt_variants())
        result.update(self.adt_variants)
        return result

    def child(self) -> "TypeEnv":
        return TypeEnv(parent=self)


# ============================================================
# 类型检查器
# ============================================================

INT_T = PrimType("Int")
FLOAT_T = PrimType("Float")
STRING_T = PrimType("String")
BOOL_T = PrimType("Bool")
CHAR_T = PrimType("Char")
UNIT_T = PrimType("Unit")


class TypeChecker:
    """Nova 类型检查器"""

    def __init__(self, source: str = ""):
        self.env = TypeEnv()
        self._source = source
        self._expr_checkers = self._build_expr_checkers()
        self._pattern_checkers = self._build_pattern_checkers()
        self._decl_checkers = self._build_decl_checkers()
        # 类型合一的替换表：TypeVar 的 id -> 绑定的类型
        # 使用 union-find 结构，支持路径压缩
        self._subst: Dict[int, "NovaType"] = {}
        self._setup_builtins()

    def _error(self, message: str, expr=None, span=None):
        """统一的 TypeCheckError 抛出方法，自动从 expr/span 提取位置信息。

        优先级：显式 span 参数 > AST 节点的 span 属性 > 无位置。
        位置信息包含源码（self._source）时支持带上下文的错误显示。
        """
        line = -1
        column = -1
        # 1. 优先使用显式 span 参数
        if span is not None:
            line = getattr(span, "line", -1)
            column = getattr(span, "column", -1)
        # 2. 其次从 expr.span 提取
        elif expr is not None:
            expr_span = getattr(expr, "span", None)
            if expr_span is not None:
                line = getattr(expr_span, "line", -1)
                column = getattr(expr_span, "column", -1)
        # 3. 尝试从 expr 直接拿 line/column（兼容旧节点）
        if line == -1 and expr is not None:
            line = getattr(expr, "line", -1)
            column = getattr(expr, "column", -1)
        source = self._source if self._source else None
        raise TypeCheckError(message, line=line, column=column, source=source)

    def _setup_builtins(self):
        """注册内置函数和类型的类型签名"""
        # 注册基本类型到环境中（供 _from_ast_type 查找）
        self.env.types["Int"] = INT_T
        self.env.types["Float"] = FLOAT_T
        self.env.types["String"] = STRING_T
        self.env.types["Bool"] = BOOL_T
        self.env.types["Char"] = CHAR_T
        self.env.types["Unit"] = UNIT_T

        # 内置 Option 和 Result
        self.env.adt_variants["Option"] = [("Some", [TypeVar("T")]), ("None", [])]
        self.env.adt_variants["Result"] = [
            ("Ok", [TypeVar("T")]),
            ("Err", [TypeVar("E")]),
        ]

        # print: (a) -> Unit
        a = TypeVar("a")
        self.env.define("print", FnType([a], UNIT_T))

        # read_line: () -> String
        self.env.define("read_line", FnType([], STRING_T))

        # int_to_str: (Int) -> String
        self.env.define("int_to_str", FnType([INT_T], STRING_T))

        # float_to_str: (Float) -> String
        self.env.define("float_to_str", FnType([FLOAT_T], STRING_T))

        # str_to_int: (String) -> Option[Int]
        self.env.define("str_to_int", FnType([STRING_T], ADTType("Option", [INT_T])))

        # str_len: (String) -> Int
        self.env.define("str_len", FnType([STRING_T], INT_T))

        # list_length: (List[T]) -> Int
        t = TypeVar("T")
        self.env.define("list_length", FnType([ListType(t)], INT_T))

        # filter: (Fn[T, Bool], List[T]) -> List[T]
        t1 = TypeVar("T1")
        self.env.define(
            "filter", FnType([FnType([t1], BOOL_T), ListType(t1)], ListType(t1))
        )

        # map: (Fn[A, B], List[A]) -> List[B]
        a2 = TypeVar("A")
        b2 = TypeVar("B")
        self.env.define("map", FnType([FnType([a2], b2), ListType(a2)], ListType(b2)))

        # sum: (List[Int]) -> Int
        self.env.define("sum", FnType([ListType(INT_T)], INT_T))

        # head: (List[T]) -> Option[T]
        t2 = TypeVar("T2")
        self.env.define("head", FnType([ListType(t2)], ADTType("Option", [t2])))

        # tail: (List[T]) -> Option[List[T]]
        t3 = TypeVar("T3")
        self.env.define(
            "tail", FnType([ListType(t3)], ADTType("Option", [ListType(t3)]))
        )

        # ====== 文件 I/O ======
        # read_file: (String) -> String
        self.env.define("read_file", FnType([STRING_T], STRING_T))
        # write_file: (String, String) -> Unit
        self.env.define("write_file", FnType([STRING_T, STRING_T], UNIT_T))
        # file_exists: (String) -> Bool
        self.env.define("file_exists", FnType([STRING_T], BOOL_T))
        # list_dir: (String) -> List[String]
        self.env.define("list_dir", FnType([STRING_T], ListType(STRING_T)))

        # ====== JSON ======
        # json_parse: (String) -> Any (简化为不严格检查)
        self.env.define("json_parse", FnType([STRING_T], TypeVar("json_value")))
        # json_stringify: (a) -> String
        a_json = TypeVar("a_json")
        self.env.define("json_stringify", FnType([a_json], STRING_T))

        # ====== 数学函数 ======
        # 所有数学函数接受 Float（Int 自动转换），返回 Float
        self.env.define("abs", FnType([FLOAT_T], FLOAT_T))
        self.env.define("sqrt", FnType([FLOAT_T], FLOAT_T))
        self.env.define("pow", FnType([FLOAT_T, FLOAT_T], FLOAT_T))
        self.env.define("log", FnType([FLOAT_T], FLOAT_T))
        self.env.define("log10", FnType([FLOAT_T], FLOAT_T))
        self.env.define("exp", FnType([FLOAT_T], FLOAT_T))
        self.env.define("sin", FnType([FLOAT_T], FLOAT_T))
        self.env.define("cos", FnType([FLOAT_T], FLOAT_T))
        self.env.define("tan", FnType([FLOAT_T], FLOAT_T))
        self.env.define("floor", FnType([FLOAT_T], FLOAT_T))
        self.env.define("ceil", FnType([FLOAT_T], FLOAT_T))
        self.env.define("round", FnType([FLOAT_T], FLOAT_T))
        self.env.define("min", FnType([FLOAT_T, FLOAT_T], FLOAT_T))
        self.env.define("max", FnType([FLOAT_T, FLOAT_T], FLOAT_T))
        self.env.define("pi", FnType([], FLOAT_T))

    def check_program(self, program: Program):
        """检查整个程序

        使用三遍扫描支持相互递归：
        1. 先注册所有 TypeDef / AliasDef（供函数签名引用）
        2. 预注册所有 FnDef 的函数类型（支持相互递归）
        3. 完整检查所有声明（包括函数体）
        """
        # 第一遍：注册类型定义（ADT、别名）
        for decl in program.declarations:
            if isinstance(decl, (TypeDef, AliasDef)):
                self.check_decl(decl)

        # 第二遍：预注册函数类型（支持相互递归）
        for decl in program.declarations:
            if isinstance(decl, FnDef):
                fn_type = self._infer_fn_type(decl)
                self.env.define(decl.name, fn_type)

        # 第三遍：完整检查所有声明
        for decl in program.declarations:
            self.check_decl(decl)

    def check_decl(self, decl):
        """检查顶层声明（调度表模式）

        使用调度表替代巨型 if-elif 链，将单函数圈复杂度从 ~20 降至约 3。
        每种声明类型对应一个独立的 _check_*_decl 方法。
        """
        checker = self._decl_checkers.get(type(decl))
        if checker is not None:
            checker(decl)
        else:
            # 顶层表达式
            self.check_expr(decl)

    def _build_decl_checkers(self):
        """构建声明类型检查调度表"""
        return {
            LetBinding: self._check_let_decl,
            MutBinding: self._check_mut_decl,
            FnDef: self._check_fn_decl,
            TypeDef: self._check_type_decl,
            AliasDef: self._check_alias_decl,
            ImportDecl: self._check_import_export_decl,
            ExportDecl: self._check_import_export_decl,
        }

    def _check_binding_decl(self, decl, mutable: bool):
        """检查 let / mut 绑定声明的通用逻辑。

        Args:
            decl: LetBinding 或 MutBinding 节点。
            mutable: 是否为可变绑定。
        """
        ty = self.check_expr(decl.value)
        if decl.type_annotation:
            annotated = self._from_ast_type(decl.type_annotation)
            if not self._unify_types(ty, annotated):
                line = decl.span.line if decl.span else -1
                col = decl.span.column if decl.span else -1
                kind = "mut" if mutable else "let"
                raise TypeCheckError(
                    f"{kind} 绑定 '{decl.name}' 的推断类型 {ty} 与标注类型 {annotated} 不匹配",
                    line,
                    col,
                )
        self.env.define(decl.name, self._unify_and_resolve(ty), mutable=mutable)

    def _check_let_decl(self, decl):
        """检查 let 绑定声明。"""
        self._check_binding_decl(decl, mutable=False)

    def _check_mut_decl(self, decl):
        """检查 mut 绑定声明。"""
        self._check_binding_decl(decl, mutable=True)

    def _check_fn_decl(self, decl):
        """检查函数定义声明。

        注册函数类型（支持递归和相互递归），检查参数类型，
        并在新环境中检查函数体返回类型。
        """
        # 若 check_program 预注册时未写入（如独立调用 check_decl），则补充注册
        if self.env.lookup(decl.name) is None:
            fn_type = self._infer_fn_type(decl)
            self.env.define(decl.name, fn_type)
        # 检查函数体
        child_env = self.env.child()
        for param in decl.params:
            if param.type_annotation:
                ptype = self._from_ast_type(param.type_annotation)
            else:
                ptype = TypeVar(f"param_{decl.name}_{param.name}")
            child_env.define(param.name, ptype)
        old_env = self.env
        self.env = child_env
        body_type = self.check_expr(decl.body)
        self.env = old_env

        if decl.return_type:
            expected = self._from_ast_type(decl.return_type)
            if not self._unify_types(body_type, expected):
                raise TypeCheckError(
                    f"函数 '{decl.name}' 返回类型 {body_type} 与声明的 {expected} 不匹配"
                )

    def _check_type_decl(self, decl):
        """检查 ADT 类型定义声明。

        注册 ADT 类型及其变体，并将每个变体注册为构造函数。
        """
        adt_ty = ADTType(decl.name)
        self.env.types[decl.name] = adt_ty
        variants = []
        for variant in decl.variants:
            field_types = []
            for fname, ftype_ast in variant.fields:
                field_types.append(self._from_ast_type(ftype_ast))
            variants.append((variant.name, field_types))
        self.env.adt_variants[decl.name] = variants

        # 注册每个变体为构造函数
        for vname, ftypes in variants:
            if ftypes:
                self.env.define(vname, FnType(ftypes, adt_ty))
            else:
                self.env.define(vname, adt_ty)

    def _check_alias_decl(self, decl):
        """检查类型别名声明。"""
        target = self._from_ast_type(decl.target_type)
        self.env.aliases[decl.name] = target
        self.env.types[decl.name] = target

    def _check_import_export_decl(self, decl):
        """检查导入/导出声明（当前跳过类型检查）。"""
        pass

    def check_expr(self, expr) -> NovaType:
        """检查表达式并返回其类型（调度表模式）

        使用调度表替代巨型 if-elif 链，将单函数圈复杂度从 ~27 降至约 3。
        每种节点类型对应一个独立的 _check_* 方法，按类别组织。
        """
        checker = self._expr_checkers.get(type(expr))
        if checker is not None:
            return checker(expr)
        self._error(f"未知的表达式类型: {type(expr).__name__}", expr=expr)

    def _build_expr_checkers(self):
        """构建表达式类型检查调度表"""
        return {
            # 字面量
            IntLiteral: self._check_int_literal,
            FloatLiteral: self._check_float_literal,
            StringLiteral: self._check_string_literal,
            CharLiteral: self._check_char_literal,
            BoolLiteral: self._check_bool_literal,
            UnitLiteral: self._check_unit_literal,
            # 标识符
            Identifier: self._check_identifier,
            # 数据结构
            ListExpr: self._check_list_expr,
            TupleExpr: self._check_tuple_expr,
            MapExpr: self._check_map_expr,
            # 运算
            BinaryOp: self._check_binary_op,
            UnaryOp: self._check_unary_op,
            # 控制流
            IfExpr: self._check_if_expr,
            MatchExpr: self._check_match_expr,
            Block: self._check_block,
            ForExpr: self._check_for_expr,
            WhileExpr: self._check_while_expr,
            BreakExpr: self._check_break_expr,
            ContinueExpr: self._check_continue_expr,
            # 绑定与赋值
            LetBinding: self._check_let_binding,
            MutBinding: self._check_mut_binding,
            Assignment: self._check_assignment,
            # 函数
            FnCall: self._check_fn_call,
            Lambda: self._check_lambda,
            # 其他
            PipeExpr: self._check_pipe_expr,
            FieldAccess: self._check_field_access,
            TryExpr: self._check_try_expr,
            ListComprehension: self._check_list_comprehension,
        }

    def _build_pattern_checkers(self):
        """构建模式类型检查调度表

        按模式节点类型映射到对应的检查方法，替代 if-isinstance 链。
        新增模式类型时只需在调度表中添加一条映射。
        """
        from .ast_nodes import (
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
        )

        return {
            PatternWildcard: self._check_pattern_wildcard,
            PatternInt: self._check_pattern_int,
            PatternFloat: self._check_pattern_float,
            PatternBool: self._check_pattern_bool,
            PatternString: self._check_pattern_string,
            PatternChar: self._check_pattern_char,
            PatternIdentifier: self._check_pattern_identifier,
            PatternConstructor: self._check_pattern_constructor,
            PatternTuple: self._check_pattern_tuple,
            PatternList: self._check_pattern_list,
        }

    # ------------------------------------------------------------------
    # 字面量检查
    # ------------------------------------------------------------------

    def _check_int_literal(self, expr) -> NovaType:
        return INT_T

    def _check_float_literal(self, expr) -> NovaType:
        return FLOAT_T

    def _check_string_literal(self, expr) -> NovaType:
        return STRING_T

    def _check_char_literal(self, expr) -> NovaType:
        return CHAR_T

    def _check_bool_literal(self, expr) -> NovaType:
        return BOOL_T

    def _check_unit_literal(self, expr) -> NovaType:
        return UNIT_T

    # ------------------------------------------------------------------
    # 标识符检查
    # ------------------------------------------------------------------

    def _check_identifier(self, expr) -> NovaType:
        """查找标识符的类型，泛型类型进行 let-polymorphism 实例化。

        若标识符未定义则抛出 TypeCheckError。
        若类型包含 TypeVar，创建 fresh 副本以支持多态使用。
        """
        ty = self.env.lookup(expr.name)
        if ty is None:
            self._error(f"未定义的标识符 '{expr.name}'", expr=expr)
        # 泛型实例化（let-polymorphism）：
        # 如果类型包含 TypeVar（即泛型），每次引用时创建 fresh 副本
        # 这样不同调用点可以独立实例化出不同的类型
        if self._contains_typevar(ty):
            return self._instantiate(ty)
        return ty

    def _contains_typevar(self, ty: "NovaType") -> bool:
        """检查类型中是否包含未绑定的类型变量（用于判断是否需要实例化）。"""
        if isinstance(ty, TypeVar):
            root = self._find(ty)
            return isinstance(root, TypeVar)
        if isinstance(ty, ListType):
            return self._contains_typevar(ty.elem_type)
        if isinstance(ty, MapType):
            return self._contains_typevar(ty.key_type) or self._contains_typevar(
                ty.value_type
            )
        if isinstance(ty, TupleType):
            return any(self._contains_typevar(e) for e in ty.elements)
        if isinstance(ty, FnType):
            return any(
                self._contains_typevar(p) for p in ty.param_types
            ) or self._contains_typevar(ty.return_type)
        if isinstance(ty, ADTType):
            return any(self._contains_typevar(p) for p in ty.type_params)
        return False

    # ------------------------------------------------------------------
    # 数据结构检查
    # ------------------------------------------------------------------

    def _check_list_expr(self, expr) -> NovaType:
        """检查列表表达式的元素类型一致性，返回统一元素类型的 ListType。

        空列表返回 ListType(TypeVar("unknown_list_elem"))。
        """
        if not expr.elements:
            return ListType(TypeVar("unknown_list_elem"))
        elem_types = [self.check_expr(e) for e in expr.elements]
        first = elem_types[0]
        for i, et in enumerate(elem_types[1:], 1):
            if not self._unify_types(et, first):
                self._error(
                    f"列表元素类型不一致：元素 0 为 {first}，元素 {i} 为 {et}",
                    expr=expr
                )
        return ListType(self._unify_and_resolve(first))

    def _check_tuple_expr(self, expr) -> NovaType:
        elem_types = [self.check_expr(e) for e in expr.elements]
        return TupleType(elem_types)

    def _check_map_expr(self, expr) -> NovaType:
        """检查 Map 表达式的键类型一致性和值类型一致性，返回 MapType。

        空 Map 返回 MapType(TypeVar("unknown_map_key"), TypeVar("unknown_map_value"))。
        """
        if not expr.pairs:
            return MapType(
                TypeVar("unknown_map_key"), TypeVar("unknown_map_value")
            )
        key_types = [self.check_expr(k) for k, _ in expr.pairs]
        value_types = [self.check_expr(v) for _, v in expr.pairs]
        first_key = key_types[0]
        first_value = value_types[0]
        for i, kt in enumerate(key_types[1:], 1):
            if not self._unify_types(kt, first_key):
                self._error(
                    f"Map 键类型不一致：键 0 为 {first_key}，键 {i} 为 {kt}",
                    expr=expr
                )
        for i, vt in enumerate(value_types[1:], 1):
            if not self._unify_types(vt, first_value):
                self._error(
                    f"Map 值类型不一致：值 0 为 {first_value}，值 {i} 为 {vt}",
                    expr=expr
                )
        return MapType(self._unify_and_resolve(first_key), self._unify_and_resolve(first_value))

    # ------------------------------------------------------------------
    # 运算检查
    # ------------------------------------------------------------------

    def _check_if_expr(self, expr) -> NovaType:
        """检查 if 表达式：条件必须为 Bool，then/else 分支类型一致。

        无 else 分支时返回 UNIT_T。
        """
        cond_ty = self.check_expr(expr.condition)
        if not self._unify_types(cond_ty, BOOL_T):
            self._error(f"if 条件必须是 Bool 类型，得到 {cond_ty}", expr=expr)
        then_ty = self.check_expr(expr.then_branch)
        if expr.else_branch:
            else_ty = self.check_expr(expr.else_branch)
            if not self._unify_types(then_ty, else_ty):
                self._error(
                    f"if 分支类型不一致：then 为 {then_ty}，else 为 {else_ty}",
                    expr=expr
                )
            return self._unify_and_resolve(then_ty)
        return UNIT_T

    def _check_match_expr(self, expr) -> NovaType:
        """检查 match 表达式，验证各分支体类型一致。

        返回各分支的统一类型；无分支时返回 UNIT_T。
        """
        subject_ty = self.check_expr(expr.subject)
        result_type = None
        for i, arm in enumerate(expr.arms):
            arm_ty = self.check_match_arm(arm, subject_ty, expr)
            if result_type is None:
                result_type = arm_ty
            elif not self._unify_types(arm_ty, result_type):
                self._error(
                    f"match 分支 {i} 类型 {arm_ty} 与第一个分支 {result_type} 不一致",
                    expr=expr
                )
        # 检查模式匹配完备性
        self._check_match_exhaustiveness(subject_ty, expr.arms, expr)
        return self._unify_and_resolve(result_type) if result_type else UNIT_T

    def _check_block(self, expr) -> NovaType:
        for stmt in expr.statements:
            self.check_expr(stmt)
        if expr.tail_expression:
            return self.check_expr(expr.tail_expression)
        return UNIT_T

    def _check_for_expr(self, expr) -> NovaType:
        """检查 for 表达式（range 和列表遍历），返回 List[body_type]。

        range 循环验证起止步类型；列表遍历验证迭代器类型。
        循环变量类型与 iterable 的元素类型合一。
        """
        # 推断循环变量的元素类型
        if isinstance(expr.iterable, tuple) and expr.iterable[0] == "range":
            # 范围循环：iterable 是 ("range", start, end, step)
            start_ty = self.check_expr(expr.iterable[1])
            end_ty = self.check_expr(expr.iterable[2])
            if expr.step:
                self.check_expr(expr.step)  # step
            # range 产生整数序列，循环变量为 Int
            elem_ty = INT_T
        else:
            # 列表遍历：提取 iterable 的元素类型
            iter_ty = self.check_expr(expr.iterable)
            if isinstance(iter_ty, ListType):
                elem_ty = iter_ty.elem_type
            else:
                elem_ty = TypeVar("for_elem")

        # 检查循环体类型
        child_env = self.env.child()
        child_env.define(expr.var_name, elem_ty)
        old_env = self.env
        self.env = child_env
        body_ty = self.check_expr(expr.body)
        self.env = old_env
        return ListType(body_ty)

    def _check_while_expr(self, expr) -> NovaType:
        cond_ty = self.check_expr(expr.condition)
        if not self._unify_types(cond_ty, BOOL_T):
            self._error(f"while 条件必须是 Bool 类型，得到 {cond_ty}", expr=expr)
        return self.check_expr(expr.body)

    def _check_break_expr(self, expr) -> NovaType:
        return UNIT_T

    def _check_continue_expr(self, expr) -> NovaType:
        return UNIT_T

    # ------------------------------------------------------------------
    # 绑定与赋值检查
    # ------------------------------------------------------------------

    def _check_let_binding(self, expr) -> NovaType:
        """检查 let 绑定，验证值类型与注解一致性，绑定到环境。

        若有类型注解，推断类型必须与注解兼容。返回 UNIT_T。
        """
        val_ty = self.check_expr(expr.value)
        if expr.type_annotation:
            annotated = self._from_ast_type(expr.type_annotation)
            if not self._unify_types(val_ty, annotated):
                line = expr.span.line if expr.span else -1
                col = expr.span.column if expr.span else -1
                raise TypeCheckError(
                    f"let 绑定类型不匹配：推断为 {val_ty}，标注为 {annotated}",
                    line,
                    col,
                )
        self.env.define(expr.name, self._unify_and_resolve(val_ty), mutable=False)
        return UNIT_T

    def _check_mut_binding(self, expr) -> NovaType:
        """检查 mut 绑定表达式。若有类型注解，推断类型必须与注解兼容。返回 UNIT_T。"""
        val_ty = self.check_expr(expr.value)
        if expr.type_annotation:
            annotated = self._from_ast_type(expr.type_annotation)
            if not self._unify_types(val_ty, annotated):
                line = expr.span.line if expr.span else -1
                col = expr.span.column if expr.span else -1
                raise TypeCheckError(
                    f"mut 绑定类型不匹配：推断为 {val_ty}，标注为 {annotated}",
                    line,
                    col,
                )
        self.env.define(expr.name, self._unify_and_resolve(val_ty), mutable=True)
        return UNIT_T

    def _check_assignment(self, expr) -> NovaType:
        """检查赋值表达式，确保目标是 mut 绑定且类型兼容。返回 UNIT_T。"""
        val_ty = self.check_expr(expr.value)
        existing = self.env.lookup(expr.name)
        if existing is None:
            line = expr.span.line if expr.span else -1
            col = expr.span.column if expr.span else -1
            raise TypeCheckError(
                f"赋值目标 '{expr.name}' 未定义", line, col
            )
        if not self.env.is_mutable(expr.name):
            line = expr.span.line if expr.span else -1
            col = expr.span.column if expr.span else -1
            raise TypeCheckError(
                f"无法赋值给不可变绑定 '{expr.name}'（使用 mut 声明可变变量）",
                line,
                col,
            )
        if not self._unify_types(val_ty, existing):
            line = expr.span.line if expr.span else -1
            col = expr.span.column if expr.span else -1
            raise TypeCheckError(
                f"赋值类型不匹配：'{expr.name}' 为 {existing}，值为 {val_ty}",
                line,
                col,
            )
        return UNIT_T

    # ------------------------------------------------------------------
    # 函数检查
    # ------------------------------------------------------------------

    def _check_fn_call(self, expr) -> NovaType:
        callee_ty = self._apply_subst(self.check_expr(expr.callee))
        arg_types = [self.check_expr(a) for a in expr.args]

        if isinstance(callee_ty, FnType):
            # 支持部分应用（参数数量少于声明的参数数量）
            if len(arg_types) > len(callee_ty.param_types):
                self._error(
                    f"函数期望至多 {len(callee_ty.param_types)} 个参数，但传入了 {len(arg_types)} 个",
                    expr=expr
                )
            # 使用合一算法进行参数类型匹配
            for i, (arg_t, param_t) in enumerate(
                zip(arg_types, callee_ty.param_types)
            ):
                if not self._unify(arg_t, param_t):
                    # 合一失败，应用替换后给出更精确的错误信息
                    expected = self._apply_subst(param_t)
                    actual = self._apply_subst(arg_t)
                    self._error(
                        f"参数 {i} 类型不匹配：期望 {expected}，得到 {actual}",
                        expr=expr.args[i] if i < len(expr.args) else expr
                    )
            if len(arg_types) == len(callee_ty.param_types):
                # 完全应用：返回应用替换后的返回类型
                return self._apply_subst(callee_ty.return_type)
            else:
                # 部分应用：返回剩余参数 -> 返回值 的函数类型（应用替换后）
                remaining_params = [
                    self._apply_subst(p)
                    for p in callee_ty.param_types[len(arg_types) :]
                ]
                ret_ty = self._apply_subst(callee_ty.return_type)
                return FnType(remaining_params, ret_ty)
        elif isinstance(callee_ty, TypeVar):
            # TypeVar callee：将其合一为与调用匹配的函数类型
            # 而非无条件 duck typing（类型安全漏洞）
            ret_tv = TypeVar(f"ret_{callee_ty.name}")
            inferred_fn = FnType(arg_types, ret_tv)
            if not self._unify(callee_ty, inferred_fn):
                self._error(
                    f"无法将类型变量 {callee_ty.name} 推断为接受 "
                    f"{len(arg_types)} 个参数的函数类型",
                    expr=expr
                )
            return ret_tv
        else:
            self._error(f"无法对非函数类型 {callee_ty} 进行调用", expr=expr)

    def _check_lambda(self, expr) -> NovaType:
        """检查 lambda 表达式，在子作用域中解析参数类型，返回 FnType。

        有注解用注解类型，否则用 TypeVar 占位。
        """
        param_types = []
        child_env = self.env.child()
        for param in expr.params:
            if param.type_annotation:
                ptype = self._from_ast_type(param.type_annotation)
            else:
                ptype = TypeVar(f"lambda_param")
            param_types.append(ptype)
            child_env.define(param.name, ptype)

        old_env = self.env
        self.env = child_env
        body_ty = self.check_expr(expr.body)
        self.env = old_env

        return FnType(param_types, body_ty)

    # ------------------------------------------------------------------
    # 其他表达式检查
    # ------------------------------------------------------------------

    def _check_pipe_expr(self, expr) -> NovaType:
        """检查管道表达式 expr |> f，验证左侧值与右侧函数参数兼容。

        语义明确：expr |> f 等价于 f(expr)，即左侧值作为函数第一个参数。
        返回右侧函数的返回类型。
        """
        left_ty = self.check_expr(expr.left)
        right_ty = self.check_expr(expr.right)

        if not isinstance(right_ty, FnType):
            # 右侧不是函数，无法管道
            self._error(
                f"管道操作符右侧必须是函数类型，得到 {right_ty}",
                expr=expr
            )

        if len(right_ty.param_types) < 1:
            self._error("管道操作符右侧函数不接受任何参数", expr=expr)

        # 语义：expr |> f ≡ f(expr)，左侧值匹配函数第一个参数。
        # 使用快照回滚机制避免 unify 失败时污染替换表：
        # _unify_types 成功会写 self._subst，若直接用 or 短路，
        # 第一次失败但途中绑定了 TypeVar 会污染第二次检查。
        first_param = right_ty.param_types[0]
        saved_subst = dict(self._subst)  # 快照
        if self._unify_types(left_ty, first_param):
            return self._unify_and_resolve(right_ty.return_type)

        # 合一失败：回滚替换表，然后报错
        self._subst = saved_subst
        expected = self._apply_subst(first_param)
        actual = self._apply_subst(left_ty)
        self._error(
            f"管道操作符类型不匹配：左侧 {actual} 无法匹配函数第一个参数 {expected}",
            expr=expr
        )

    def _check_field_access(self, expr) -> NovaType:
        """字段访问的类型检查。

        支持元组的数字索引访问（tuple.0, tuple.1）。
        对于 ADT 类型，静态检查无法确定具体变体，字段访问需要通过模式匹配进行。
        所有错误路径均给出精确的错误信息，无不透明的异常吞噬。
        """
        target_ty = self.check_expr(expr.target)
        field_name = expr.field

        # --- 元组类型：支持数字索引访问 ---
        if isinstance(target_ty, TupleType):
            # 尝试将字段名解析为整数索引
            try:
                idx = int(field_name)
            except ValueError:
                self._error(
                    f"元组访问需要数字索引，收到 '{field_name}'\n"
                    f"  提示：元组字段使用 .0, .1, .2 ... 形式访问",
                    expr=expr
                )

            # 检查索引越界
            tuple_len = len(target_ty.elements)
            if idx < 0 or idx >= tuple_len:
                self._error(
                    f"元组索引 {idx} 越界：元组有 {tuple_len} 个元素（索引范围 0~{tuple_len - 1}）",
                    expr=expr
                )

            return target_ty.elements[idx]

        # --- ADT 类型：静态阶段无法直接字段访问 ---
        if isinstance(target_ty, ADTType):
            self._error(
                f"无法直接访问 ADT 类型 {target_ty} 的字段 '{field_name}'\n"
                f"  提示：请使用 match 表达式进行模式匹配来访问 ADT 字段",
                expr=expr
            )

        # --- 其他类型：不支持字段访问 ---
        self._error(
            f"类型 {target_ty} 不支持字段访问\n"
            f"  提示：只有元组类型支持 .N 形式的索引访问",
            expr=expr
        )

    def _check_try_expr(self, expr) -> NovaType:
        """
        ? 操作符的类型检查。
        
        ? 只能用于 Option 或 Result 类型：
        - Option[T]? => T（若为 None 则提前返回 None）
        - Result[T, E]? => T（若为 Err 则提前返回 Err）
        
        非 Option/Result 类型使用 ? 会报类型错误。
        """
        inner_ty = self.check_expr(expr.expr)
        
        # TypeVar 尝试约束为 Option/Result，若无法推断则报错
        if isinstance(inner_ty, TypeVar):
            # 合一算法已就绪，但 TypeVar 在此点无法确定是 Option 还是 Result
            # 返回 error 类型，要求用户显式标注类型
            # 从 AST 节点的 span 获取位置信息（兼容无 span 的情况）
            span = getattr(expr.expr, 'span', None)
            raise TypeCheckError(
                f"无法推断 '{expr.expr}' 的类型为 Option 或 Result，"
                f"请为变量添加显式类型标注",
                span.line if span else -1,
                span.column if span else -1,
            )
        
        if isinstance(inner_ty, ADTType):
            if inner_ty.name == "Option":
                # Option[T]? => T
                if len(inner_ty.type_params) >= 1:
                    return inner_ty.type_params[0]
                # 没有类型参数时返回 TypeVar 占位
                return TypeVar("option_value")
            elif inner_ty.name == "Result":
                # Result[T, E]? => T
                if len(inner_ty.type_params) >= 1:
                    return inner_ty.type_params[0]
                return TypeVar("result_value")
        
        raise self._error(
            f"? 操作符只能用于 Option 或 Result 类型，当前类型为 {inner_ty}",
            expr=expr
        )

    def _check_list_comprehension(self, expr) -> NovaType:
        """检查列表推导式，验证迭代器和过滤条件类型，返回 List[expr_type]。

        过滤条件必须为 Bool 类型。
        循环变量类型与 iterable 的元素类型合一。
        """
        # 推断循环变量的元素类型
        if isinstance(expr.iterable, tuple) and expr.iterable[0] == "range":
            self.check_expr(expr.iterable[1])
            self.check_expr(expr.iterable[2])
            # range 产生整数序列，循环变量为 Int
            elem_ty = INT_T
        else:
            iter_ty = self.check_expr(expr.iterable)
            if isinstance(iter_ty, ListType):
                elem_ty = iter_ty.elem_type
            else:
                elem_ty = TypeVar("lc_elem")

        child_env = self.env.child()
        child_env.define(expr.var_name, elem_ty)
        if expr.filter_cond:
            old_env = self.env
            self.env = child_env
            cond_ty = self.check_expr(expr.filter_cond)
            if not self._unify_types(cond_ty, BOOL_T):
                self._error(f"列表推导式过滤条件必须是 Bool 类型", expr=expr)
            self.env = old_env

        old_env = self.env
        self.env = child_env
        expr_ty = self.check_expr(expr.expr)
        self.env = old_env
        return ListType(expr_ty)

    def check_match_arm(
        self, arm, subject_type: NovaType, match_expr: MatchExpr
    ) -> NovaType:
        """检查 match 分支，包括可选的 guard 条件类型检查"""
        child_env = self.env.child()
        self._check_pattern(arm.pattern, subject_type, child_env, match_expr)
        # 检查 guard 条件（必须为 Bool 类型）
        if arm.guard is not None:
            old_env = self.env
            self.env = child_env
            guard_ty = self.check_expr(arm.guard)
            if not self._unify_types(guard_ty, BOOL_T):
                raise TypeCheckError(
                    f"match 分支的 guard 条件必须是 Bool 类型，实际为 {guard_ty}",
                    line=arm.guard.span.line if arm.guard.span else -1,
                    column=arm.guard.span.column if arm.guard.span else -1,
                )
            self.env = old_env
        old_env = self.env
        self.env = child_env
        body_ty = self.check_expr(arm.body)
        self.env = old_env
        return body_ty

    def _is_wildcard_like(self, pat) -> bool:
        """检查模式是否为通配符或变量绑定（匹配所有值）。

        通配符 _ 和变量绑定 x 都匹配任意值，
        在完备性分析中视为完全覆盖。
        """
        from .ast_nodes import PatternWildcard, PatternIdentifier

        return isinstance(pat, (PatternWildcard, PatternIdentifier))

    def _check_patterns_exhaustive(
        self, patterns: List, subject_type: NovaType
    ) -> bool:
        """递归检查一组模式是否集体完备地覆盖给定类型的所有值。

        采用类型分发策略，将不同类型的完备性检查委托给专属子方法：
        - ADT 构造器 → _check_adt_exhaustive
        - Bool → _check_bool_exhaustive
        - 元组 → _check_tuple_exhaustive
        - 列表 → _check_list_exhaustive
        - Int/Float/String/Char → 无限值域，无通配符则不完备

        通配符 _ 和变量绑定 x 匹配任意值，在完备性分析中视为完全覆盖。
        """
        # 通配符/变量绑定 → 完备
        for p in patterns:
            if self._is_wildcard_like(p):
                return True

        # 按类型分发到专属检查方法
        if isinstance(subject_type, ADTType):
            return self._check_adt_exhaustive(patterns, subject_type)
        if isinstance(subject_type, PrimType) and subject_type.name == "Bool":
            return self._check_bool_exhaustive(patterns)
        if isinstance(subject_type, TupleType):
            return self._check_tuple_exhaustive(patterns, subject_type)
        if isinstance(subject_type, ListType):
            return self._check_list_exhaustive(patterns, subject_type)

        # Int/Float/String/Char：无限值域，无通配符则不完备
        return False

    def _check_adt_exhaustive(
        self, patterns: List, subject_type: ADTType
    ) -> bool:
        """检查 ADT 构造器模式是否覆盖所有变体。

        遍历所有构造器变体，收集每个变体的子模式列表，
        递归验证每个变体的子模式是否集体完备。
        """
        from .ast_nodes import PatternConstructor

        all_variants = self.env.get_all_adt_variants()
        variants = all_variants.get(subject_type.name)
        if not variants:
            return True  # 无法确定变体信息，假设完备

        # 收集每个构造器的子模式列表
        covered = {}  # constructor_name -> List[List[Pattern]]
        for p in patterns:
            if isinstance(p, PatternConstructor):
                if p.name in {vname for vname, _ in variants}:
                    if p.name not in covered:
                        covered[p.name] = []
                    covered[p.name].append(p.fields)

        for vname, ftypes in variants:
            if vname not in covered:
                return False  # 构造器未覆盖
            # 递归检查子模式是否集体完备
            if not self._check_sub_patterns_exhaustive(
                covered[vname], ftypes
            ):
                return False
        return True

    def _check_bool_exhaustive(self, patterns: List) -> bool:
        """检查 Bool 模式是否同时覆盖 true 和 false。

        收集所有 PatternBool 的值，验证 True 和 False 都被覆盖。
        """
        from .ast_nodes import PatternBool

        covered_bools = set()
        for p in patterns:
            if isinstance(p, PatternBool):
                covered_bools.add(str(p.value))
        return "True" in covered_bools and "False" in covered_bools

    def _check_tuple_exhaustive(
        self, patterns: List, subject_type: TupleType
    ) -> bool:
        """检查元组模式是否覆盖每个位置的子类型。

        对每个元素位置，收集所有 PatternTuple 在该位置的子模式，
        递归调用 _check_patterns_exhaustive 验证每个位置是否完备。
        """
        from .ast_nodes import PatternTuple

        tuple_patterns = [p for p in patterns if isinstance(p, PatternTuple)]
        if not tuple_patterns:
            return False
        for i, elem_type in enumerate(subject_type.elements):
            pos_patterns = [
                p.elements[i]
                for p in tuple_patterns
                if i < len(p.elements)
            ]
            if not self._check_patterns_exhaustive(pos_patterns, elem_type):
                return False
        return True

    def _check_list_exhaustive(
        self, patterns: List, subject_type: ListType
    ) -> bool:
        """检查列表模式的完备性并存储分析信息。

        列表长度无限，固定长度的 PatternList 无法覆盖所有长度。
        进行精细分析：
        1. 收集所有 PatternList 模式，按长度分组
        2. 检查每个长度组的元素模式是否集体完备
        3. 即使所有已知长度都完备，由于列表长度无限，整体仍不完备
           （除非有 cons/rest 模式，但 Nova 当前不支持）

        分析结果存储在 self._last_list_exhaustive_info 中用于错误消息。
        无论结果如何，恒返回 False（列表长度无限）。
        """
        from .ast_nodes import PatternList

        list_patterns = [p for p in patterns if isinstance(p, PatternList)]
        if list_patterns:
            # 按长度分组
            by_length: Dict[int, List] = {}
            for p in list_patterns:
                n = len(p.elements)
                if n not in by_length:
                    by_length[n] = []
                by_length[n].append(p)

            # 检查每个长度组的元素是否完备
            lengths_covered = set()
            for length, pats in by_length.items():
                if length == 0:
                    # 空列表：只要有一个 [] 模式就覆盖了
                    lengths_covered.add(0)
                else:
                    # 非空列表：检查每个位置的元素模式是否集体完备
                    all_positions_complete = True
                    for i in range(length):
                        pos_patterns = [
                            p.elements[i]
                            for p in pats
                            if i < len(p.elements)
                        ]
                        if not self._check_patterns_exhaustive(
                            pos_patterns, subject_type.elem_type
                        ):
                            all_positions_complete = False
                            break
                    if all_positions_complete:
                        lengths_covered.add(length)

            # 存储分析结果供错误消息使用
            self._last_list_exhaustive_info = {
                "lengths_covered": sorted(lengths_covered),
                "total_length_groups": len(by_length),
            }
        else:
            self._last_list_exhaustive_info = {
                "lengths_covered": [],
                "total_length_groups": 0,
            }
        # 列表长度无限，固定长度模式永远无法完全覆盖
        return False

    def _check_sub_patterns_exhaustive(
        self, sub_patterns_list: List[List], field_types: List[NovaType]
    ) -> bool:
        """检查同一构造器的多个分支的子模式是否集体完备。

        对每个字段位置，收集所有分支在该位置的子模式，
        递归调用 _check_patterns_exhaustive 检查是否完备。
        """
        if not sub_patterns_list:
            return False

        for i, field_type in enumerate(field_types):
            pos_patterns = [
                sp[i] for sp in sub_patterns_list if i < len(sp)
            ]
            if not self._check_patterns_exhaustive(pos_patterns, field_type):
                return False
        return True

    def _classify_arm_pattern(self, arm):
        """分类 match arm 的模式，返回 (kind, key, value, has_guard) 元组。

        kind 取值：
        - 'wildcard': PatternWildcard 或 PatternIdentifier（无 guard）
        - 'guarded_wildcard': PatternWildcard 或 PatternIdentifier（有 guard）
        - 'literal': 字面量模式（int/float/string/char/bool），key 为类型标识，
          value 为字面量值（NaN 返回 None 表示不可比较）
        - 'other': 其他模式类型（如 PatternConstructor），不参与冗余检测

        此方法消除了 6 种字面量类型的重复 isinstance 分发链，
        将原来每种类型约 8 行的分支逻辑统一为一张映射表。
        """
        from .ast_nodes import (
            PatternBool,
            PatternChar,
            PatternFloat,
            PatternIdentifier,
            PatternInt,
            PatternString,
            PatternWildcard,
        )

        pat = arm.pattern
        has_guard = arm.guard is not None

        # 通配符/变量绑定
        if isinstance(pat, (PatternWildcard, PatternIdentifier)):
            kind = "guarded_wildcard" if has_guard else "wildcard"
            return (kind, None, None, has_guard)

        # 字面量类型 → (kind, type_key, literal_value, has_guard) 映射表
        # 消除 6 段重复的 isinstance 分支
        _LITERAL_TYPE_MAP = {
            PatternBool: ("literal", "bool", lambda p: str(p.value)),
            PatternInt: ("literal", "int", lambda p: p.value),
            PatternFloat: ("literal", "float", lambda p: p.value if p.value == p.value else None),
            PatternString: ("literal", "string", lambda p: p.value),
            PatternChar: ("literal", "char", lambda p: p.value),
        }

        for pat_cls, (kind, key, val_fn) in _LITERAL_TYPE_MAP.items():
            if isinstance(pat, pat_cls):
                val = val_fn(pat)
                return (kind, key, val, has_guard)

        return ("other", None, None, has_guard)

    def _detect_redundant_arms(self, arms):
        """检测 match 表达式中的冗余分支。

        冗余规则：
        - 多个无 guard 通配符/变量绑定：第二个及之后的冗余
        - 重复的字面量值（同类型）：后出现的冗余
        - NaN 不视为冗余（NaN != NaN）

        返回 (redundant_indices, has_wildcard_or_var) 元组。
        """
        seen_literals = {}  # key: 类型标识, value: set of seen values
        has_wildcard_or_var = False
        redundant = []

        for i, arm in enumerate(arms):
            kind, key, val, has_guard = self._classify_arm_pattern(arm)

            if kind == "wildcard":
                if has_wildcard_or_var:
                    redundant.append(i)
                else:
                    has_wildcard_or_var = True
            elif kind == "literal" and not has_guard and val is not None:
                # NaN 安全：val is None 表示 NaN，不参与冗余比较
                if key not in seen_literals:
                    seen_literals[key] = set()
                if val in seen_literals[key]:
                    redundant.append(i)
                else:
                    seen_literals[key].add(val)

        return (redundant, has_wildcard_or_var)

    def _generate_missing_message(self, subject_type, all_patterns, line, column):
        """根据 subject_type 生成匹配不完备的详细错误消息。

        按 ADT/Bool/Tuple/其他 四种类型分别生成有针对性的提示，
        帮助用户快速定位缺失的分支。
        """
        from .ast_nodes import PatternConstructor

        if isinstance(subject_type, ADTType):
            all_variants = self.env.get_all_adt_variants()
            variants = all_variants.get(subject_type.name)
            if variants:
                covered_names = {
                    p.name
                    for p in all_patterns
                    if isinstance(p, PatternConstructor)
                }
                expected = {vname for vname, _ in variants}
                missing = expected - covered_names
                if missing:
                    missing_list = ", ".join(sorted(missing))
                    raise TypeCheckError(
                        f"match 表达式不完备：缺失构造器 {missing_list}",
                        line=line,
                        column=column,
                    )
                raise TypeCheckError(
                    "match 表达式不完备：构造器的子模式未完全覆盖所有情况，"
                    "考虑添加通配符子模式（如 Some(_)）",
                    line=line,
                    column=column,
                )
        elif isinstance(subject_type, PrimType) and subject_type.name == "Bool":
            raise TypeCheckError(
                "match 表达式不完备：缺失 true 或 false 分支",
                line=line,
                column=column,
            )
        elif isinstance(subject_type, TupleType):
            raise TypeCheckError(
                "match 表达式不完备：元组模式的元素位置未完全覆盖，"
                "考虑添加通配符元素（如 (_, _)）",
                line=line,
                column=column,
            )
        elif isinstance(subject_type, ListType):
            # 列表类型：根据精细分析结果给出针对性提示
            info = getattr(self, "_last_list_exhaustive_info", None)
            if info and info["total_length_groups"] > 0:
                lengths = info["lengths_covered"]
                if lengths:
                    lengths_str = ", ".join(str(n) for n in lengths)
                    raise TypeCheckError(
                        f"match 表达式不完备：列表模式仅覆盖了长度为 {lengths_str} 的情况，"
                        f"列表长度可以是任意值，考虑添加通配符分支 (_)",
                        line=line,
                        column=column,
                    )
                else:
                    raise TypeCheckError(
                        "match 表达式不完备：列表模式的元素位置未完全覆盖，"
                        "且列表长度可以是任意值，考虑添加通配符分支 (_)",
                        line=line,
                        column=column,
                    )
            else:
                raise TypeCheckError(
                    "match 表达式不完备：列表长度可以是任意值，"
                    "固定长度模式无法覆盖所有情况，考虑添加通配符分支 (_)",
                    line=line,
                    column=column,
                )
        else:
            raise TypeCheckError(
                "match 表达式可能不完备：考虑添加通配符分支 (_) "
                "确保覆盖所有情况",
                line=line,
                column=column,
            )

    def _check_match_exhaustiveness(
        self, subject_type: NovaType, arms: List, match_expr: MatchExpr
    ):
        """检查 match 表达式的模式覆盖是否完备。

        支持嵌套模式完备性检查：
        - ADT 类型：递归检查所有构造器及其子模式的完备性
        - Bool 类型：确保 true 和 false 都被覆盖
        - 元组类型：递归检查每个位置的完备性
        - 列表类型：基本完备性检查
        - 通配符 (_) 和变量绑定视为覆盖所有剩余情况
        - 检测冗余分支（通配符/变量绑定之后的分支）
        - 检测字面量模式冗余（重复的字面量值）

        编排逻辑：冗余检测 → 快速返回 → 递归完备性 → 错误消息
        """
        # 提取行号列号用于报错
        line = match_expr.span.line if match_expr.span else -1
        column = match_expr.span.column if match_expr.span else -1

        # 阶段 1: 冗余分支检测
        redundant_arms, has_wildcard_or_var = self._detect_redundant_arms(arms)
        if redundant_arms:
            first = redundant_arms[0]
            raise TypeCheckError(
                f"match 分支 {first} 是冗余的：之前的分支已经覆盖了所有情况",
                line=line,
                column=column,
            )

        # 阶段 2: 无 guard 通配符/变量绑定视为完备
        if has_wildcard_or_var:
            return

        # 阶段 3: 空分支视为不完备
        if not arms:
            raise TypeCheckError(
                "match 表达式必须至少有一个分支",
                line=line,
                column=column,
            )

        # 阶段 4: 递归检查模式完备性（支持嵌套模式）
        all_patterns = [arm.pattern for arm in arms]
        if not self._check_patterns_exhaustive(all_patterns, subject_type):
            self._generate_missing_message(subject_type, all_patterns, line, column)

    def _check_pattern(self, pattern, subject_type: NovaType, env: TypeEnv, match_expr):
        """检查模式与类型的匹配

        使用调度表模式分发到对应的检查方法，圈复杂度 O(1)。
        """
        checker = self._pattern_checkers.get(type(pattern))
        if checker is not None:
            return checker(pattern, subject_type, env, match_expr)
        raise TypeCheckError(f"未知的模式类型: {type(pattern).__name__}")

    # --- 模式检查方法 ---

    def _check_pattern_wildcard(self, pattern, subject_type: NovaType, env: TypeEnv, match_expr):
        """通配符 _ 匹配任何类型"""
        return

    def _check_pattern_int(self, pattern, subject_type: NovaType, env: TypeEnv, match_expr):
        """整数模式要求 subject 为 Int 类型"""
        if not self._unify_types(subject_type, INT_T):
            raise TypeCheckError(f"整数模式与类型 {subject_type} 不匹配")

    def _check_pattern_float(self, pattern, subject_type: NovaType, env: TypeEnv, match_expr):
        """浮点数模式要求 subject 为 Float 类型"""
        if not self._unify_types(subject_type, FLOAT_T):
            raise TypeCheckError(f"浮点数模式与类型 {subject_type} 不匹配")

    def _check_pattern_bool(self, pattern, subject_type: NovaType, env: TypeEnv, match_expr):
        """布尔模式要求 subject 为 Bool 类型"""
        if not self._unify_types(subject_type, BOOL_T):
            raise TypeCheckError(f"布尔模式与类型 {subject_type} 不匹配")

    def _check_pattern_string(self, pattern, subject_type: NovaType, env: TypeEnv, match_expr):
        """字符串模式要求 subject 为 String 类型"""
        if not self._unify_types(subject_type, STRING_T):
            raise TypeCheckError(f"字符串模式与类型 {subject_type} 不匹配")

    def _check_pattern_char(self, pattern, subject_type: NovaType, env: TypeEnv, match_expr):
        """字符模式要求 subject 为 Char 类型"""
        if not self._unify_types(subject_type, CHAR_T):
            raise TypeCheckError(f"字符模式与类型 {subject_type} 不匹配")

    def _check_pattern_identifier(self, pattern, subject_type: NovaType, env: TypeEnv, match_expr):
        """标识符模式将 subject 类型绑定到变量名"""
        env.define(pattern.name, subject_type)

    def _check_pattern_constructor(self, pattern, subject_type: NovaType, env: TypeEnv, match_expr):
        """构造器模式：查找 ADT 定义，递归检查字段类型"""
        # 查找构造器对应的类型
        variants_info = None
        for adt_name, variants in self.env.get_all_adt_variants().items():
            for vname, ftypes in variants:
                if vname == pattern.name:
                    variants_info = (adt_name, ftypes)
                    break
            if variants_info:
                break

        if variants_info is None:
            raise TypeCheckError(f"未知的构造器 '{pattern.name}'")

        adt_name, field_types = variants_info
        if len(pattern.fields) != len(field_types):
            raise TypeCheckError(
                f"构造器 '{pattern.name}' 期望 {len(field_types)} 个字段，得到 {len(pattern.fields)} 个"
            )
        for p, ft in zip(pattern.fields, field_types):
            self._check_pattern(p, ft, env, match_expr)

    def _check_pattern_tuple(self, pattern, subject_type: NovaType, env: TypeEnv, match_expr):
        """元组模式要求 subject 为 Tuple 类型，且长度匹配"""
        if not isinstance(subject_type, TupleType):
            raise TypeCheckError(f"元组模式与类型 {subject_type} 不匹配")
        if len(pattern.elements) != len(subject_type.elements):
            raise TypeCheckError("元组模式长度不匹配")
        for p, t in zip(pattern.elements, subject_type.elements):
            self._check_pattern(p, t, env, match_expr)

    def _check_pattern_list(self, pattern, subject_type: NovaType, env: TypeEnv, match_expr):
        """列表模式要求 subject 为 List 类型"""
        if not isinstance(subject_type, ListType):
            raise TypeCheckError(f"列表模式与类型 {subject_type} 不匹配")
        for p in pattern.elements:
            self._check_pattern(p, subject_type.elem_type, env, match_expr)

    # 二元操作分发表：操作符 -> 检查方法
    # 将原来 60+ 行的 _check_binary_op 拆分为按操作类别分发的辅助方法，
    # 使主方法圈复杂度从 20 降至 3 左右。
    _BINARY_OP_HANDLERS = {
        "+": "_check_arithmetic_op",
        "-": "_check_arithmetic_op",
        "*": "_check_arithmetic_op",
        "/": "_check_arithmetic_op",
        "%": "_check_modulo_op",
        "++": "_check_string_concat_op",
        "==": "_check_comparison_op",
        "!=": "_check_comparison_op",
        "<": "_check_comparison_op",
        ">": "_check_comparison_op",
        "<=": "_check_comparison_op",
        ">=": "_check_comparison_op",
        "&&": "_check_logical_op",
        "||": "_check_logical_op",
    }

    def _check_binary_op(self, expr: BinaryOp) -> NovaType:
        """检查二元操作

        使用分发表将不同操作符路由到对应的辅助检查方法，
        避免在主方法中堆积大量 if-elif 分支。

        对辅助方法抛出的 TypeCheckError 统一补充 span 位置信息。
        """
        left_ty = self.check_expr(expr.left)
        right_ty = self.check_expr(expr.right)

        handler_name = self._BINARY_OP_HANDLERS.get(expr.op)
        if handler_name is None:
            self._error(f"未知的操作符 '{expr.op}'", expr=expr)

        handler = getattr(self, handler_name)
        try:
            return handler(expr.op, left_ty, right_ty)
        except TypeCheckError as e:
            # 辅助方法没有位置信息，在此统一补全
            if e.line < 0 and expr.span:
                e.line = expr.span.line
                e.column = expr.span.column
            if self._source and e.source_code is None:
                e.source_code = self._source
            raise

    def _check_arithmetic_op(self, op: str, left_ty: NovaType, right_ty: NovaType) -> NovaType:
        """检查算术操作 (+, -, *, /)：要求两侧同为 Int 或同为 Float"""
        if self._unify_types(left_ty, INT_T) and self._unify_types(right_ty, INT_T):
            return INT_T
        if self._unify_types(left_ty, FLOAT_T) and self._unify_types(right_ty, FLOAT_T):
            return FLOAT_T
        raise TypeCheckError(
            f"操作符 '{op}' 的操作数类型不兼容：{left_ty} 和 {right_ty}"
        )

    def _check_modulo_op(self, op: str, left_ty: NovaType, right_ty: NovaType) -> NovaType:
        """检查取模操作 (%)：要求两侧均为 Int"""
        if self._unify_types(left_ty, INT_T) and self._unify_types(right_ty, INT_T):
            return INT_T
        raise TypeCheckError(f"操作符 '%' 需要 Int 类型操作数")

    def _check_string_concat_op(self, op: str, left_ty: NovaType, right_ty: NovaType) -> NovaType:
        """检查字符串拼接 (++)：要求两侧均为 String"""
        if self._unify_types(left_ty, STRING_T) and self._unify_types(right_ty, STRING_T):
            return STRING_T
        raise TypeCheckError(f"操作符 '++' 需要 String 类型操作数")

    def _check_comparison_op(self, op: str, left_ty: NovaType, right_ty: NovaType) -> NovaType:
        """检查比较操作 (==, !=, <, >, <=, >=)"""
        # 所有比较操作都要求左右操作数类型兼容
        if not self._unify_types(left_ty, right_ty):
            raise TypeCheckError(
                f"操作符 '{op}' 的操作数类型不兼容：{left_ty} 和 {right_ty}"
            )
        # 有序比较（< > <= >=）额外要求数值类型
        if op in ("<", ">", "<=", ">="):
            if not (
                self._unify_types(left_ty, INT_T)
                or self._unify_types(left_ty, FLOAT_T)
            ):
                raise TypeCheckError(
                    f"操作符 '{op}' 需要数值类型操作数，得到 {left_ty}"
                )
        return BOOL_T

    def _check_logical_op(self, op: str, left_ty: NovaType, right_ty: NovaType) -> NovaType:
        """检查逻辑操作 (&&, ||)：要求两侧均为 Bool"""
        if not self._unify_types(left_ty, BOOL_T):
            raise TypeCheckError(f"'{op}' 左侧必须是 Bool，得到 {left_ty}")
        if not self._unify_types(right_ty, BOOL_T):
            raise TypeCheckError(f"'{op}' 右侧必须是 Bool，得到 {right_ty}")
        return BOOL_T

    def _check_unary_op(self, expr: UnaryOp) -> NovaType:
        """检查一元操作"""
        operand_ty = self.check_expr(expr.operand)
        if expr.op == "-":
            if self._unify_types(operand_ty, INT_T):
                return INT_T
            if self._unify_types(operand_ty, FLOAT_T):
                return FLOAT_T
            self._error(f"一元 '-' 需要 Int 或 Float，得到 {operand_ty}", expr=expr)
        if expr.op == "!":
            if self._unify_types(operand_ty, BOOL_T):
                return BOOL_T
            self._error(f"一元 '!' 需要 Bool，得到 {operand_ty}", expr=expr)
        self._error(f"未知的一元操作符 '{expr.op}'", expr=expr)

    def _infer_fn_type(self, fn: FnDef) -> FnType:
        """推断函数类型"""
        param_types = []
        for p in fn.params:
            if p.type_annotation:
                param_types.append(self._from_ast_type(p.type_annotation))
            else:
                param_types.append(TypeVar(f"param_{fn.name}_{p.name}"))
        ret_type = UNIT_T
        if fn.return_type:
            ret_type = self._from_ast_type(fn.return_type)
        else:
            ret_type = TypeVar(f"ret_{fn.name}")
        return FnType(param_types, ret_type)

    # 基本类型映射表：AST 类型节点类 -> NovaType 常量
    _BASIC_TYPE_MAP = {
        TypeInt: INT_T,
        TypeFloat: FLOAT_T,
        TypeString: STRING_T,
        TypeBool: BOOL_T,
        TypeChar: CHAR_T,
        TypeUnit: UNIT_T,
    }

    def _from_ast_type(self, type_node) -> NovaType:
        """将 AST 中的类型注解转换为 NovaType（调度表模式）

        使用类型映射表和独立辅助方法替代长 if-elif 链，
        将单函数圈复杂度从 ~18 降至约 3。
        """
        node_type = type(type_node)
        # 1. 基本类型：直接查表
        basic = self._BASIC_TYPE_MAP.get(node_type)
        if basic is not None:
            return basic
        # 2. 标识符类型：别名/环境查找
        if isinstance(type_node, TypeIdentifier):
            return self._resolve_type_identifier(type_node.name)
        # 3. 泛型类型：List/Map/Option/Result/其他 ADT
        if isinstance(type_node, TypeGeneric):
            params = [self._from_ast_type(p) for p in type_node.params]
            return self._make_generic_type(type_node.base, params)
        # 4. 元组类型
        if isinstance(type_node, TypeTuple):
            return TupleType([self._from_ast_type(e) for e in type_node.elements])
        # 5. 函数类型
        if isinstance(type_node, TypeFn):
            return FnType(
                [self._from_ast_type(p) for p in type_node.param_types],
                self._from_ast_type(type_node.return_type),
            )
        raise TypeCheckError(f"未知的类型注解: {type(type_node).__name__}")

    def _resolve_type_identifier(self, name: str) -> NovaType:
        """解析类型标识符名称为具体的 NovaType。

        查找顺序：别名 -> 环境类型（ADT、基本类型等）。
        若均不存在则抛出 TypeCheckError。

        Args:
            name: 类型标识符名称。

        Returns:
            解析后的 NovaType。

        Raises:
            TypeCheckError: 未知类型名。
        """
        if name in self.env.aliases:
            return self.env.aliases[name]
        if name in self.env.types:
            return self.env.types[name]
        raise TypeCheckError(
            f"未知的类型 '{name}'（检查是否拼写正确，或是否缺少类型定义）"
        )

    def _make_generic_type(self, base: str, params: List[NovaType]) -> NovaType:
        """根据泛型基名和参数构建对应的 NovaType。

        支持 List、Map、Option、Result 及自定义 ADT。
        对内置泛型类型进行参数数量校验，防止静默降级。

        Args:
            base: 泛型基名（如 "List", "Option"）。
            params: 泛型参数类型列表。

        Returns:
            构建好的泛型 NovaType。

        Raises:
            TypeCheckError: 参数数量不匹配时抛出。
        """
        if base == "List":
            if len(params) != 1:
                raise TypeCheckError(
                    f"List 需要恰好 1 个类型参数，实际得到 {len(params)} 个"
                )
            return ListType(params[0])
        if base == "Map":
            if len(params) != 2:
                raise TypeCheckError(
                    f"Map 需要恰好 2 个类型参数，实际得到 {len(params)} 个"
                )
            return MapType(params[0], params[1])
        if base == "Option":
            if len(params) != 1:
                raise TypeCheckError(
                    f"Option 需要恰好 1 个类型参数，实际得到 {len(params)} 个"
                )
            return ADTType("Option", params)
        if base == "Result":
            if len(params) != 2:
                raise TypeCheckError(
                    f"Result 需要恰好 2 个类型参数，实际得到 {len(params)} 个"
                )
            return ADTType("Result", params)
        # 自定义 ADT（当前不支持类型参数）
        if params:
            raise TypeCheckError(
                f"类型 '{base}' 不支持类型参数，实际得到 {len(params)} 个"
            )
        return ADTType(base, params)

    # ------------------------------------------------------------------
    # 类型合一（Unification）算法
    # ------------------------------------------------------------------

    def _find(self, tv: "TypeVar") -> "NovaType":
        """查找类型变量的最终绑定（union-find 路径压缩）。

        如果类型变量已被绑定，返回其最终代表元；否则返回自身。
        路径压缩：将查找路径上的所有节点直接指向根，加速后续查找。
        """
        current = tv
        path = []
        while isinstance(current, TypeVar) and id(current) in self._subst:
            path.append(id(current))
            current = self._subst[id(current)]
        # 路径压缩
        for vid in path:
            self._subst[vid] = current
        return current

    def _occur_check(self, tv: "TypeVar", ty: "NovaType") -> bool:
        """检查类型变量 tv 是否出现在类型 ty 中（用于防止递归类型）。

        返回 True 表示 tv 出现在 ty 中（即发生检查失败，不能合一）。
        """
        ty_root = self._find(ty) if isinstance(ty, TypeVar) else ty
        if isinstance(ty_root, TypeVar):
            return tv is ty_root
        if isinstance(ty_root, ListType):
            return self._occur_check(tv, ty_root.elem_type)
        if isinstance(ty_root, MapType):
            return self._occur_check(tv, ty_root.key_type) or self._occur_check(
                tv, ty_root.value_type
            )
        if isinstance(ty_root, TupleType):
            return any(self._occur_check(tv, e) for e in ty_root.elements)
        if isinstance(ty_root, FnType):
            return any(
                self._occur_check(tv, p) for p in ty_root.param_types
            ) or self._occur_check(tv, ty_root.return_type)
        if isinstance(ty_root, ADTType):
            return any(self._occur_check(tv, p) for p in ty_root.type_params)
        return False

    def _unify(self, a: "NovaType", b: "NovaType") -> bool:
        """合一两个类型，返回是否合一成功。

        合一成功后，替换表 self._subst 会被更新。
        合一失败时返回 False（不抛异常，由调用者决定错误处理）。

        算法：
        1. 首先通过 _find 找到两个类型的根
        2. 如果任一根是 TypeVar，则将其绑定到另一个类型
        3. 否则按结构递归合一（通过 _UNIFY_DISPATCH 调度表分发）
        4. 发生检查：防止创建无限递归类型
        """
        a_root = self._find(a) if isinstance(a, TypeVar) else a
        b_root = self._find(b) if isinstance(b, TypeVar) else b

        # 情况 1：两侧都是未绑定的 TypeVar
        if isinstance(a_root, TypeVar) and isinstance(b_root, TypeVar):
            if a_root is b_root:
                return True  # 同一个变量，无需绑定
            # 将较小 id 的绑定到较大 id 的（任意选择，保持稳定）
            self._subst[id(a_root)] = b_root
            return True

        # 情况 2：左侧是未绑定的 TypeVar
        if isinstance(a_root, TypeVar):
            if self._occur_check(a_root, b_root):
                return False  # 无限类型
            self._subst[id(a_root)] = b_root
            return True

        # 情况 3：右侧是未绑定的 TypeVar
        if isinstance(b_root, TypeVar):
            if self._occur_check(b_root, a_root):
                return False  # 无限类型
            self._subst[id(b_root)] = a_root
            return True

        # 情况 4-9：结构类型合一，通过调度表分发
        if type(a_root) is type(b_root):
            handler_name = _UNIFY_DISPATCH.get(type(a_root))
            if handler_name is not None:
                return getattr(self, handler_name)(a_root, b_root)

        # 情况 10：不兼容的类型构造器
        return False

    # ------------------------------------------------------------------
    # 结构类型合一 handler（被 _UNIFY_DISPATCH 调度表调用）
    # ------------------------------------------------------------------

    def _unify_prim(self, a: PrimType, b: PrimType) -> bool:
        """合一两个基本类型"""
        return a.name == b.name

    def _unify_list(self, a: ListType, b: ListType) -> bool:
        """合一两个列表类型"""
        return self._unify(a.elem_type, b.elem_type)

    def _unify_map(self, a: MapType, b: MapType) -> bool:
        """合一两个 Map 类型"""
        return self._unify(a.key_type, b.key_type) and self._unify(
            a.value_type, b.value_type
        )

    def _unify_tuple(self, a: TupleType, b: TupleType) -> bool:
        """合一两个元组类型"""
        if len(a.elements) != len(b.elements):
            return False
        return all(
            self._unify(e1, e2) for e1, e2 in zip(a.elements, b.elements)
        )

    def _unify_fn(self, a: FnType, b: FnType) -> bool:
        """合一两个函数类型"""
        if len(a.param_types) != len(b.param_types):
            return False
        return all(
            self._unify(p1, p2)
            for p1, p2 in zip(a.param_types, b.param_types)
        ) and self._unify(a.return_type, b.return_type)

    def _unify_adt(self, a: ADTType, b: ADTType) -> bool:
        """合一两个代数数据类型"""
        if a.name != b.name:
            return False
        if len(a.type_params) != len(b.type_params):
            return False
        return all(
            self._unify(p1, p2)
            for p1, p2 in zip(a.type_params, b.type_params)
        )

    def _apply_subst(self, ty: "NovaType") -> "NovaType":
        """将替换表应用到类型上，返回所有类型变量都被替换后的类型。

        递归遍历类型结构，将每个 TypeVar 替换为其最终绑定（通过 _find）。
        如果 TypeVar 未绑定，则保持不变。
        """
        if isinstance(ty, TypeVar):
            root = self._find(ty)
            if root is ty:
                return ty  # 未绑定，返回自身
            return self._apply_subst(root)  # 递归应用（确保完全展开）
        if isinstance(ty, ListType):
            return ListType(self._apply_subst(ty.elem_type))
        if isinstance(ty, MapType):
            return MapType(
                self._apply_subst(ty.key_type), self._apply_subst(ty.value_type)
            )
        if isinstance(ty, TupleType):
            return TupleType([self._apply_subst(e) for e in ty.elements])
        if isinstance(ty, FnType):
            return FnType(
                [self._apply_subst(p) for p in ty.param_types],
                self._apply_subst(ty.return_type),
            )
        if isinstance(ty, ADTType):
            return ADTType(ty.name, [self._apply_subst(p) for p in ty.type_params])
        # PrimType 等不可变类型直接返回
        return ty

    def _fresh_type_var(self, prefix: str = "t") -> "TypeVar":
        """创建一个新的类型变量（带唯一计数器）。"""
        return TypeVar(f"{prefix}_{TypeVar._counter}")

    def _instantiate(self, ty: "NovaType") -> "NovaType":
        """泛型实例化：创建类型的一个 fresh 副本，将其中所有 TypeVar 替换为新的 TypeVar。

        用于 let-polymorphism：每次引用泛型函数时，创建一个新的实例，
        使不同调用点可以有不同的类型实例。
        """
        mapping: Dict[int, "TypeVar"] = {}

        def instantiate_rec(t: "NovaType") -> "NovaType":
            if isinstance(t, TypeVar):
                if id(t) not in mapping:
                    mapping[id(t)] = TypeVar(f"inst_{t.name}")
                return mapping[id(t)]
            if isinstance(t, ListType):
                return ListType(instantiate_rec(t.elem_type))
            if isinstance(t, MapType):
                return MapType(
                    instantiate_rec(t.key_type), instantiate_rec(t.value_type)
                )
            if isinstance(t, TupleType):
                return TupleType([instantiate_rec(e) for e in t.elements])
            if isinstance(t, FnType):
                return FnType(
                    [instantiate_rec(p) for p in t.param_types],
                    instantiate_rec(t.return_type),
                )
            if isinstance(t, ADTType):
                return ADTType(t.name, [instantiate_rec(p) for p in t.type_params])
            return t

        return instantiate_rec(ty)

    def _unify_types(self, a: NovaType, b: NovaType) -> bool:
        """合一驱动的类型兼容检查。

        先展开替换表中的类型变量，再尝试合一。
        成功时替换表会被更新（产生新的类型约束），失败时返回 False。
        这是对旧 _types_compatible 的升级版本，TypeVar 不再被直接放行。
        """
        a_resolved = self._apply_subst(a)
        b_resolved = self._apply_subst(b)
        return self._unify(a_resolved, b_resolved)

    def _unify_and_resolve(self, ty: NovaType) -> NovaType:
        """合一后解析类型：应用替换表，获得最终的完全展开类型。"""
        return self._apply_subst(ty)

# ============================================================
# 类型合一调度表
# ============================================================

_UNIFY_DISPATCH = {
    PrimType: "_unify_prim",
    ListType: "_unify_list",
    MapType: "_unify_map",
    TupleType: "_unify_tuple",
    FnType: "_unify_fn",
    ADTType: "_unify_adt",
}
