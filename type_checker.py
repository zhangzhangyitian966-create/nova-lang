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

from typing import Dict, List, Optional
import copy

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
        self.adt_variants: Dict[str, List[tuple]] = (
            {}
        )  # adt_name -> [(variant_name, [field_types])]
        self.aliases: Dict[str, NovaType] = {}

    def define(self, name: str, ty: NovaType):
        self.types[name] = ty

    def lookup(self, name: str) -> Optional[NovaType]:
        if name in self.types:
            return self.types[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

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
        # 类型合一的替换表：TypeVar 的 id -> 绑定的类型
        # 使用 union-find 结构，支持路径压缩
        self._subst: Dict[int, "NovaType"] = {}
        self._setup_builtins()

    def _setup_builtins(self):
        """注册内置函数和类型的类型签名"""
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
        """检查整个程序"""
        for decl in program.declarations:
            self.check_decl(decl)

    def check_decl(self, decl):
        """检查顶层声明"""
        if isinstance(decl, LetBinding):
            ty = self.check_expr(decl.value)
            if decl.type_annotation:
                annotated = self._from_ast_type(decl.type_annotation)
                if not self._unify_types(ty, annotated):
                    line = decl.span.line if decl.span else -1
                    col = decl.span.column if decl.span else -1
                    raise TypeCheckError(
                        f"let 绑定 '{decl.name}' 的推断类型 {ty} 与标注类型 {annotated} 不匹配",
                        line,
                        col,
                    )
            self.env.define(decl.name, self._unify_and_resolve(ty))

        elif isinstance(decl, MutBinding):
            ty = self.check_expr(decl.value)
            if decl.type_annotation:
                annotated = self._from_ast_type(decl.type_annotation)
                if not self._unify_types(ty, annotated):
                    raise TypeCheckError(
                        f"mut 绑定 '{decl.name}' 的推断类型 {ty} 与标注类型 {annotated} 不匹配"
                    )
            self.env.define(decl.name, self._unify_and_resolve(ty))

        elif isinstance(decl, FnDef):
            # 注册函数类型（支持递归）
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

        elif isinstance(decl, TypeDef):
            # 注册 ADT 类型
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

        elif isinstance(decl, AliasDef):
            target = self._from_ast_type(decl.target_type)
            self.env.aliases[decl.name] = target
            self.env.types[decl.name] = target

        elif isinstance(decl, (ImportDecl, ExportDecl)):
            pass  # 跳过导入/导出的类型检查

        else:
            # 顶层表达式
            self.check_expr(decl)

    def check_expr(self, expr) -> NovaType:
        """检查表达式并返回其类型（调度表模式）

        使用调度表替代巨型 if-elif 链，将单函数圈复杂度从 ~27 降至约 3。
        每种节点类型对应一个独立的 _check_* 方法，按类别组织。
        """
        checker = self._expr_checkers.get(type(expr))
        if checker is not None:
            return checker(expr)
        raise TypeCheckError(f"未知的表达式类型: {type(expr).__name__}")

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
            raise TypeCheckError(f"未定义的标识符 '{expr.name}'")
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
                raise TypeCheckError(
                    f"列表元素类型不一致：元素 0 为 {first}，元素 {i} 为 {et}"
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
                raise TypeCheckError(
                    f"Map 键类型不一致：键 0 为 {first_key}，键 {i} 为 {kt}"
                )
        for i, vt in enumerate(value_types[1:], 1):
            if not self._unify_types(vt, first_value):
                raise TypeCheckError(
                    f"Map 值类型不一致：值 0 为 {first_value}，值 {i} 为 {vt}"
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
            raise TypeCheckError(f"if 条件必须是 Bool 类型，得到 {cond_ty}")
        then_ty = self.check_expr(expr.then_branch)
        if expr.else_branch:
            else_ty = self.check_expr(expr.else_branch)
            if not self._unify_types(then_ty, else_ty):
                raise TypeCheckError(
                    f"if 分支类型不一致：then 为 {then_ty}，else 为 {else_ty}"
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
                raise TypeCheckError(
                    f"match 分支 {i} 类型 {arm_ty} 与第一个分支 {result_type} 不一致"
                )
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
        """
        # for 循环：返回 List[元素类型]
        if isinstance(expr.iterable, tuple) and expr.iterable[0] == "range":
            # 范围循环：iterable 是 ("range", start, end, step)
            start_ty = self.check_expr(expr.iterable[1])
            end_ty = self.check_expr(expr.iterable[2])
            if expr.iterable[3]:
                self.check_expr(expr.iterable[3])  # step
        else:
            # 列表遍历
            iter_ty = self.check_expr(expr.iterable)

        # 检查循环体类型
        child_env = self.env.child()
        child_env.define(expr.var_name, TypeVar("for_elem"))
        old_env = self.env
        self.env = child_env
        body_ty = self.check_expr(expr.body)
        self.env = old_env
        return ListType(body_ty)

    def _check_while_expr(self, expr) -> NovaType:
        cond_ty = self.check_expr(expr.condition)
        if not self._unify_types(cond_ty, BOOL_T):
            raise TypeCheckError(f"while 条件必须是 Bool 类型，得到 {cond_ty}")
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
                raise TypeCheckError(
                    f"let 绑定类型不匹配：推断为 {val_ty}，标注为 {annotated}"
                )
        self.env.define(expr.name, self._unify_and_resolve(val_ty))
        return UNIT_T

    def _check_mut_binding(self, expr) -> NovaType:
        """检查 mut 绑定表达式。若有类型注解，推断类型必须与注解兼容。返回 UNIT_T。"""
        val_ty = self.check_expr(expr.value)
        if expr.type_annotation:
            annotated = self._from_ast_type(expr.type_annotation)
            if not self._unify_types(val_ty, annotated):
                raise TypeCheckError(
                    f"mut 绑定类型不匹配：推断为 {val_ty}，标注为 {annotated}"
                )
        self.env.define(expr.name, self._unify_and_resolve(val_ty))
        return UNIT_T

    def _check_assignment(self, expr) -> NovaType:
        """检查赋值表达式，确保目标已定义且类型兼容。返回 UNIT_T。"""
        val_ty = self.check_expr(expr.value)
        existing = self.env.lookup(expr.name)
        if existing is None:
            raise TypeCheckError(f"赋值目标 '{expr.name}' 未定义")
        if not self._unify_types(val_ty, existing):
            raise TypeCheckError(
                f"赋值类型不匹配：'{expr.name}' 为 {existing}，值为 {val_ty}"
            )
        return UNIT_T

    # ------------------------------------------------------------------
    # 函数检查
    # ------------------------------------------------------------------

    def _check_fn_call(self, expr) -> NovaType:
        callee_ty = self.check_expr(expr.callee)
        arg_types = [self.check_expr(a) for a in expr.args]

        if isinstance(callee_ty, FnType):
            # 支持部分应用（参数数量少于声明的参数数量）
            if len(arg_types) > len(callee_ty.param_types):
                raise TypeCheckError(
                    f"函数期望至多 {len(callee_ty.param_types)} 个参数，但传入了 {len(arg_types)} 个"
                )
            # 使用合一算法进行参数类型匹配
            for i, (arg_t, param_t) in enumerate(
                zip(arg_types, callee_ty.param_types)
            ):
                if not self._unify(arg_t, param_t):
                    # 合一失败，应用替换后给出更精确的错误信息
                    expected = self._apply_subst(param_t)
                    actual = self._apply_subst(arg_t)
                    raise TypeCheckError(
                        f"参数 {i} 类型不匹配：期望 {expected}，得到 {actual}"
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
            # 未类型化的参数（duck typing）：允许任意调用
            # 返回一个 TypeVar 表示结果类型
            return TypeVar(f"ret_{callee_ty.name}")
        else:
            raise TypeCheckError(f"无法对非函数类型 {callee_ty} 进行调用")

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

        返回右侧函数的返回类型。
        """
        # expr |> f  等价于 f(expr)
        left_ty = self.check_expr(expr.left)
        right_ty = self.check_expr(expr.right)
        if isinstance(right_ty, FnType):
            if len(right_ty.param_types) >= 1:
                # 检查管道值是否与函数最后一个参数兼容
                # 因为管道的典型用法是 f(arg1) |> 等价于 f(piped_value)
                last_param = (
                    right_ty.param_types[-1] if right_ty.param_types else None
                )
                # 也检查第一个参数（直接调用场景）
                first_param = right_ty.param_types[0]
                if self._unify_types(
                    left_ty, last_param
                ) or self._unify_types(left_ty, first_param):
                    return self._unify_and_resolve(right_ty.return_type)
        # 如果无法确定，返回右侧类型
        return right_ty

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
                raise TypeCheckError(
                    f"元组访问需要数字索引，收到 '{field_name}'\n"
                    f"  提示：元组字段使用 .0, .1, .2 ... 形式访问"
                )

            # 检查索引越界
            tuple_len = len(target_ty.elements)
            if idx < 0 or idx >= tuple_len:
                raise TypeCheckError(
                    f"元组索引 {idx} 越界：元组有 {tuple_len} 个元素（索引范围 0~{tuple_len - 1}）"
                )

            return target_ty.elements[idx]

        # --- ADT 类型：静态阶段无法直接字段访问 ---
        if isinstance(target_ty, ADTType):
            raise TypeCheckError(
                f"无法直接访问 ADT 类型 {target_ty} 的字段 '{field_name}'\n"
                f"  提示：请使用 match 表达式进行模式匹配来访问 ADT 字段"
            )

        # --- 其他类型：不支持字段访问 ---
        raise TypeCheckError(
            f"类型 {target_ty} 不支持字段访问\n"
            f"  提示：只有元组类型支持 .N 形式的索引访问"
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
        
        # TypeVar 暂时放行（在合一实现前保持兼容）
        if isinstance(inner_ty, TypeVar):
            return TypeVar(f"try_{inner_ty.name}")
        
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
        
        raise TypeCheckError(
            f"? 操作符只能用于 Option 或 Result 类型，当前类型为 {inner_ty}"
        )

    def _check_list_comprehension(self, expr) -> NovaType:
        """检查列表推导式，验证迭代器和过滤条件类型，返回 List[expr_type]。

        过滤条件必须为 Bool 类型。
        """
        # 列表推导式：返回 List[expr 类型]
        if isinstance(expr.iterable, tuple) and expr.iterable[0] == "range":
            self.check_expr(expr.iterable[1])
            self.check_expr(expr.iterable[2])
        else:
            self.check_expr(expr.iterable)

        child_env = self.env.child()
        child_env.define(expr.var_name, TypeVar("lc_elem"))
        if expr.filter_cond:
            old_env = self.env
            self.env = child_env
            cond_ty = self.check_expr(expr.filter_cond)
            if not self._unify_types(cond_ty, BOOL_T):
                raise TypeCheckError(f"列表推导式过滤条件必须是 Bool 类型")
            self.env = old_env

        old_env = self.env
        self.env = child_env
        expr_ty = self.check_expr(expr.expr)
        self.env = old_env
        return ListType(expr_ty)

    def check_match_arm(
        self, arm, subject_type: NovaType, match_expr: MatchExpr
    ) -> NovaType:
        """检查 match 分支"""
        child_env = self.env.child()
        self._check_pattern(arm.pattern, subject_type, child_env, match_expr)
        old_env = self.env
        self.env = child_env
        body_ty = self.check_expr(arm.body)
        self.env = old_env
        return body_ty

    def _check_pattern(self, pattern, subject_type: NovaType, env: TypeEnv, match_expr):
        """检查模式与类型的匹配"""
        from .ast_nodes import (
            PatternBool,
            PatternConstructor,
            PatternIdentifier,
            PatternInt,
            PatternList,
            PatternString,
            PatternTuple,
            PatternWildcard,
        )

        if isinstance(pattern, PatternWildcard):
            return

        elif isinstance(pattern, PatternInt):
            if not self._unify_types(subject_type, INT_T):
                raise TypeCheckError(f"整数模式与类型 {subject_type} 不匹配")

        elif isinstance(pattern, PatternBool):
            if not self._unify_types(subject_type, BOOL_T):
                raise TypeCheckError(f"布尔模式与类型 {subject_type} 不匹配")

        elif isinstance(pattern, PatternString):
            if not self._unify_types(subject_type, STRING_T):
                raise TypeCheckError(f"字符串模式与类型 {subject_type} 不匹配")

        elif isinstance(pattern, PatternIdentifier):
            env.define(pattern.name, subject_type)

        elif isinstance(pattern, PatternConstructor):
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

        elif isinstance(pattern, PatternTuple):
            if not isinstance(subject_type, TupleType):
                raise TypeCheckError(f"元组模式与类型 {subject_type} 不匹配")
            if len(pattern.elements) != len(subject_type.elements):
                raise TypeCheckError("元组模式长度不匹配")
            for p, t in zip(pattern.elements, subject_type.elements):
                self._check_pattern(p, t, env, match_expr)

        elif isinstance(pattern, PatternList):
            if not isinstance(subject_type, ListType):
                raise TypeCheckError(f"列表模式与类型 {subject_type} 不匹配")
            for p in pattern.elements:
                self._check_pattern(p, subject_type.elem_type, env, match_expr)

    def _check_binary_op(self, expr: BinaryOp) -> NovaType:
        """检查二元操作"""
        left_ty = self.check_expr(expr.left)
        right_ty = self.check_expr(expr.right)

        # 算术操作
        if expr.op in ("+", "-", "*", "/"):
            if self._unify_types(left_ty, INT_T) and self._unify_types(
                right_ty, INT_T
            ):
                return INT_T
            if self._unify_types(left_ty, FLOAT_T) and self._unify_types(
                right_ty, FLOAT_T
            ):
                return FLOAT_T
            raise TypeCheckError(
                f"操作符 '{expr.op}' 的操作数类型不兼容：{left_ty} 和 {right_ty}"
            )

        if expr.op == "%":
            if self._unify_types(left_ty, INT_T) and self._unify_types(
                right_ty, INT_T
            ):
                return INT_T
            raise TypeCheckError(f"操作符 '%' 需要 Int 类型操作数")

        # 字符串拼接
        if expr.op == "++":
            if self._unify_types(left_ty, STRING_T) and self._unify_types(
                right_ty, STRING_T
            ):
                return STRING_T
            raise TypeCheckError(f"操作符 '++' 需要 String 类型操作数")

        # 比较操作
        if expr.op in ("==", "!=", "<", ">", "<=", ">="):
            # 所有比较操作都要求左右操作数类型兼容
            if not self._unify_types(left_ty, right_ty):
                raise TypeCheckError(
                    f"操作符 '{expr.op}' 的操作数类型不兼容：{left_ty} 和 {right_ty}"
                )
            # 有序比较（< > <= >=）额外要求数值类型
            if expr.op in ("<", ">", "<=", ">="):
                if not (
                    self._unify_types(left_ty, INT_T)
                    or self._unify_types(left_ty, FLOAT_T)
                ):
                    raise TypeCheckError(
                        f"操作符 '{expr.op}' 需要数值类型操作数，得到 {left_ty}"
                    )
            return BOOL_T

        # 逻辑操作
        if expr.op in ("&&", "||"):
            if not self._unify_types(left_ty, BOOL_T):
                raise TypeCheckError(f"'&&' 左侧必须是 Bool，得到 {left_ty}")
            if not self._unify_types(right_ty, BOOL_T):
                raise TypeCheckError(f"'&&' 右侧必须是 Bool，得到 {right_ty}")
            return BOOL_T

        raise TypeCheckError(f"未知的操作符 '{expr.op}'")

    def _check_unary_op(self, expr: UnaryOp) -> NovaType:
        """检查一元操作"""
        operand_ty = self.check_expr(expr.operand)
        if expr.op == "-":
            if self._unify_types(operand_ty, INT_T):
                return INT_T
            if self._unify_types(operand_ty, FLOAT_T):
                return FLOAT_T
            raise TypeCheckError(f"一元 '-' 需要 Int 或 Float，得到 {operand_ty}")
        if expr.op == "!":
            if self._unify_types(operand_ty, BOOL_T):
                return BOOL_T
            raise TypeCheckError(f"一元 '!' 需要 Bool，得到 {operand_ty}")
        raise TypeCheckError(f"未知的一元操作符 '{expr.op}'")

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

    def _from_ast_type(self, type_node) -> NovaType:
        """将 AST 中的类型注解转换为 NovaType"""
        if isinstance(type_node, TypeInt):
            return INT_T
        elif isinstance(type_node, TypeFloat):
            return FLOAT_T
        elif isinstance(type_node, TypeString):
            return STRING_T
        elif isinstance(type_node, TypeBool):
            return BOOL_T
        elif isinstance(type_node, TypeChar):
            return CHAR_T
        elif isinstance(type_node, TypeUnit):
            return UNIT_T
        elif isinstance(type_node, TypeIdentifier):
            name = type_node.name
            if name in self.env.aliases:
                return self.env.aliases[name]
            if name in self.env.types:
                return self.env.types[name]
            return PrimType(name)
        elif isinstance(type_node, TypeGeneric):
            base = type_node.base
            params = [self._from_ast_type(p) for p in type_node.params]
            if base == "List":
                return ListType(params[0]) if params else ListType(TypeVar("T"))
            elif base == "Map" and len(params) >= 2:
                return MapType(params[0], params[1])
            elif base == "Option":
                return ADTType("Option", params)
            elif base == "Result":
                return ADTType("Result", params)
            else:
                return ADTType(base, params)
        elif isinstance(type_node, TypeTuple):
            return TupleType([self._from_ast_type(e) for e in type_node.elements])
        elif isinstance(type_node, TypeFn):
            return FnType(
                [self._from_ast_type(p) for p in type_node.param_types],
                self._from_ast_type(type_node.return_type),
            )
        raise TypeCheckError(f"未知的类型注解: {type(type_node).__name__}")

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
        3. 否则按结构递归合一
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

        # 情况 4：基本类型
        if isinstance(a_root, PrimType) and isinstance(b_root, PrimType):
            return a_root.name == b_root.name

        # 情况 5：ListType
        if isinstance(a_root, ListType) and isinstance(b_root, ListType):
            return self._unify(a_root.elem_type, b_root.elem_type)

        # 情况 6：MapType
        if isinstance(a_root, MapType) and isinstance(b_root, MapType):
            return self._unify(a_root.key_type, b_root.key_type) and self._unify(
                a_root.value_type, b_root.value_type
            )

        # 情况 7：TupleType
        if isinstance(a_root, TupleType) and isinstance(b_root, TupleType):
            if len(a_root.elements) != len(b_root.elements):
                return False
            return all(
                self._unify(e1, e2)
                for e1, e2 in zip(a_root.elements, b_root.elements)
            )

        # 情况 8：FnType
        if isinstance(a_root, FnType) and isinstance(b_root, FnType):
            if len(a_root.param_types) != len(b_root.param_types):
                return False
            return all(
                self._unify(p1, p2)
                for p1, p2 in zip(a_root.param_types, b_root.param_types)
            ) and self._unify(a_root.return_type, b_root.return_type)

        # 情况 9：ADTType
        if isinstance(a_root, ADTType) and isinstance(b_root, ADTType):
            if a_root.name != b_root.name:
                return False
            if len(a_root.type_params) != len(b_root.type_params):
                return False
            return all(
                self._unify(p1, p2)
                for p1, p2 in zip(a_root.type_params, b_root.type_params)
            )

        # 情况 10：不兼容的类型构造器
        return False

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

    def _types_compatible(self, a: NovaType, b: NovaType) -> bool:
        """检查两个类型是否兼容（遗留方法，仅在非关键路径使用）。

        注意：此方法对 TypeVar 直接放行（鸭子类型），不产生类型约束。
        新代码应优先使用 _unify_types 进行合一驱动的类型检查。
        """
        if isinstance(a, TypeVar) or isinstance(b, TypeVar):
            return True
        if a == b:
            return True
        # 递归检查 FnType 参数兼容性
        if isinstance(a, FnType) and isinstance(b, FnType):
            if len(a.param_types) != len(b.param_types):
                return False
            return all(
                self._types_compatible(pa, pb)
                for pa, pb in zip(a.param_types, b.param_types)
            ) and self._types_compatible(a.return_type, b.return_type)
        # 递归检查 ListType
        if isinstance(a, ListType) and isinstance(b, ListType):
            return self._types_compatible(a.elem_type, b.elem_type)
        # 递归检查 MapType
        if isinstance(a, MapType) and isinstance(b, MapType):
            return self._types_compatible(a.key_type, b.key_type) and self._types_compatible(a.value_type, b.value_type)
        # 递归检查 TupleType
        if isinstance(a, TupleType) and isinstance(b, TupleType):
            if len(a.elements) != len(b.elements):
                return False
            return all(
                self._types_compatible(e1, e2)
                for e1, e2 in zip(a.elements, b.elements)
            )
        # 递归检查 ADTType
        if isinstance(a, ADTType) and isinstance(b, ADTType):
            if a.name != b.name or len(a.type_params) != len(b.type_params):
                return False
            return all(
                self._types_compatible(p1, p2)
                for p1, p2 in zip(a.type_params, b.type_params)
            )
        return False
