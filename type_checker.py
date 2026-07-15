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

from typing import Dict, Optional, List, Any

from nova.ast_nodes import (
    Program, Block,
    IntLiteral, FloatLiteral, StringLiteral, CharLiteral, BoolLiteral, UnitLiteral,
    Identifier, BinaryOp, UnaryOp, PipeExpr, TryExpr,
    Param, Lambda, FnDef, FnCall,
    LetBinding, MutBinding, Assignment,
    IfExpr, MatchArm, MatchExpr,
    ForExpr, WhileExpr, BreakExpr, ContinueExpr,
    ListExpr, ListComprehension, TupleExpr, FieldAccess, IndexExpr, MapExpr,
    TypeDef, VariantDef, AliasDef,
    ImportDecl, ExportDecl,
    TypeInt, TypeFloat, TypeString, TypeBool, TypeChar, TypeUnit,
    TypeIdentifier, TypeGeneric, TypeTuple, TypeFn, Span,
)
from nova.errors import TypeCheckError, NovaError, ErrorCollector


# ============================================================
# 类型表示
# ============================================================

class NovaType:
    """Nova 类型基类"""
    pass


class ErrorType(NovaType):
    """错误类型，用于错误收集模式下避免级联错误"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __eq__(self, other):
        return isinstance(other, ErrorType)

    def __hash__(self):
        return hash("<error>")

    def __repr__(self):
        return "<error>"


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
        return (isinstance(other, MapType)
                and self.key_type == other.key_type
                and self.value_type == other.value_type)

    def __hash__(self):
        return hash(("Map", self.key_type, self.value_type))

    def __repr__(self):
        return f"Map[{self.key_type}, {self.value_type}]"


class TupleType(NovaType):
    """元组类型 (T1, T2, ...)"""
    def __init__(self, elements: List[NovaType]):
        self.elements = elements

    def __eq__(self, other):
        return (isinstance(other, TupleType)
                and len(self.elements) == len(other.elements)
                and all(a == b for a, b in zip(self.elements, other.elements)))

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
        return (isinstance(other, FnType)
                and len(self.param_types) == len(other.param_types)
                and all(a == b for a, b in zip(self.param_types, other.param_types))
                and self.return_type == other.return_type)

    def __hash__(self):
        return hash(("Fn", tuple(hash(p) for p in self.param_types), hash(self.return_type)))

    def __repr__(self):
        params = ", ".join(str(p) for p in self.param_types)
        return f"({params}) -> {self.return_type}"


class ADTType(NovaType):
    """代数数据类型"""
    def __init__(self, name: str, type_params: List[NovaType] = None):
        self.name = name
        self.type_params = type_params or []

    def __eq__(self, other):
        return (isinstance(other, ADTType)
                and self.name == other.name
                and len(self.type_params) == len(other.type_params)
                and all(a == b for a, b in zip(self.type_params, other.type_params)))

    def __hash__(self):
        return hash(("ADT", self.name, tuple(hash(p) for p in self.type_params)))

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
        return isinstance(other, TypeVar) and self.name == other.name

    def __hash__(self):
        return hash(("TypeVar", self.name))

    def __repr__(self):
        return self.name


# ============================================================
# 类型环境
# ============================================================

class TypeEnv:
    """类型环境"""

    def __init__(self, parent: Optional['TypeEnv'] = None):
        self.parent = parent
        self.types: Dict[str, NovaType] = {}
        self.adt_variants: Dict[str, List[tuple]] = {}  # adt_name -> [(variant_name, [(field_name, field_type), ...])]
        self.adt_type_params: Dict[str, List[str]] = {}  # adt_name -> [param_names]
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

    def get_all_adt_type_params(self) -> Dict[str, List[str]]:
        """获取当前环境及所有父环境的 ADT 泛型参数信息"""
        result = {}
        if self.parent:
            result.update(self.parent.get_all_adt_type_params())
        result.update(self.adt_type_params)
        return result

    def child(self) -> 'TypeEnv':
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
ERROR_TYPE = ErrorType()


class TypeChecker:
    """Nova 类型检查器"""

    def __init__(self, source: str = "", collect_errors: bool = False,
                 module_manager=None, current_file: str = None):
        self.env = TypeEnv()
        self._source = source
        self._collect_errors = collect_errors
        self.error_collector = ErrorCollector()
        self._module_manager = module_manager  # ModuleManager 实例
        self._current_file = current_file      # 当前文件路径
        self._exported_names: set = set()      # 本模块导出的名称
        self._setup_builtins()

    def _report_error(self, message: str, node=None):
        """报告类型错误：收集模式或立即抛出"""
        line, col, span = -1, -1, None
        if node is not None and hasattr(node, 'span') and node.span:
            line = node.span.line
            col = node.span.column
            if node.span.end_line is not None and node.span.end_column is not None:
                span = Span(node.span.line, node.span.column,
                            node.span.end_line, node.span.end_column)
            else:
                span = Span(node.span.line, node.span.column)
        err = TypeCheckError(message, line, col, source=self._source, span=span)
        if self._collect_errors:
            self.error_collector.add(err)
        else:
            raise err

    def _setup_builtins(self):
        """注册内置函数和类型的类型签名"""
        # 内置 Option 和 Result
        self.env.adt_variants["Option"] = [("Some", [("value", TypeVar("T"))]), ("None", [])]
        self.env.adt_variants["Result"] = [("Ok", [("value", TypeVar("T"))]), ("Err", [("error", TypeVar("E"))])]
        self.env.adt_type_params["Option"] = ["T"]
        self.env.adt_type_params["Result"] = ["T", "E"]

        # 注册内置 ADT 构造函数类型签名
        t_opt = TypeVar("opt_t")
        self.env.define("Some", FnType([t_opt], ADTType("Option", [t_opt])))
        self.env.define("None", ADTType("Option", [TypeVar("opt_t")]))
        ok_t = TypeVar("ok_t")
        ok_err_t = TypeVar("ok_err_t")
        self.env.define("Ok", FnType([ok_t], ADTType("Result", [ok_t, ok_err_t])))
        err_ok_t = TypeVar("err_ok_t")
        err_err_t = TypeVar("err_err_t")
        self.env.define("Err", FnType([err_err_t], ADTType("Result", [err_ok_t, err_err_t])))

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
        self.env.define("filter", FnType([FnType([t1], BOOL_T), ListType(t1)], ListType(t1)))

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
        self.env.define("tail", FnType([ListType(t3)], ADTType("Option", [ListType(t3)])))

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
        """检查整个程序（两遍扫描：先收集声明，再检查函数体）

        第一遍：收集所有函数、ADT、类型别名的签名到环境中
        第二遍：检查所有函数体和 let/mut 绑定的值表达式
        这样支持前向引用和相互递归
        """
        # 跟踪本程序中用户定义的名称（用于重复定义检测，不包含内置）
        self._user_defined_names: set = set()
        self._user_defined_types: set = set()

        # 第一遍：收集所有顶层声明的签名
        for decl in program.declarations:
            self._collect_decl(decl)

        # 第二遍：检查所有函数体和绑定的值
        for decl in program.declarations:
            self._check_decl_body(decl)

    def _collect_decl(self, decl):
        """第一遍：收集声明签名到环境中（不检查函数体）"""
        if isinstance(decl, FnDef):
            # 检查重复定义（只检查用户在本程序中定义的名称）
            if decl.name in self._user_defined_names:
                self._report_error(
                    f"函数 '{decl.name}' 重复定义",
                    decl
                )
            self._user_defined_names.add(decl.name)
            fn_type = self._infer_fn_type(decl)
            self.env.define(decl.name, fn_type)

        elif isinstance(decl, TypeDef):
            # 检查重复 ADT 定义（只检查用户在本程序中定义的类型）
            if decl.name in self._user_defined_types:
                self._report_error(
                    f"类型 '{decl.name}' 重复定义",
                    decl
                )
            self._user_defined_types.add(decl.name)
            type_params = [TypeVar(tp) for tp in decl.type_params]
            adt_ty = ADTType(decl.name, type_params)
            self.env.types[decl.name] = adt_ty
            self.env.adt_type_params[decl.name] = decl.type_params
            # 为字段类型解析提供局部类型参数映射
            local_types = {tp: TypeVar(tp) for tp in decl.type_params}
            variants = []
            for variant in decl.variants:
                field_info = []
                for fname, ftype_ast in variant.fields:
                    field_type = self._from_ast_type(ftype_ast, local_types=local_types)
                    field_info.append((fname, field_type))
                variants.append((variant.name, field_info))
            self.env.adt_variants[decl.name] = variants

            # 注册每个变体为构造函数
            for vname, field_info in variants:
                if field_info:
                    ftypes = [ft for _fn, ft in field_info]
                    self.env.define(vname, FnType(ftypes, adt_ty))
                else:
                    self.env.define(vname, adt_ty)

        elif isinstance(decl, AliasDef):
            target = self._from_ast_type(decl.target_type)
            self.env.aliases[decl.name] = target
            self.env.types[decl.name] = target

        elif isinstance(decl, (LetBinding, MutBinding)):
            # 对于 let/mut 绑定，我们也需要在第一遍注册（支持前向引用绑定）
            # 但值的类型需要在第二遍检查
            # 这里先注册一个类型变量作为占位符
            if decl.type_annotation:
                annotated = self._from_ast_type(decl.type_annotation)
                self.env.define(decl.name, annotated)
            else:
                # 没有类型标注的 let/mut，使用类型变量占位
                self.env.define(decl.name, TypeVar(f"let_{decl.name}"))

        elif isinstance(decl, ImportDecl):
            # 导入声明：第一遍处理导入模块的类型
            self._handle_import_decl(decl)

        elif isinstance(decl, ExportDecl):
            # 导出声明：标记名称为已导出
            self._exported_names.add(decl.name)

        # 顶层表达式在第一遍不处理（第二遍也不处理函数体检查时会处理）
        else:
            pass

    def _handle_import_decl(self, decl: ImportDecl):
        """处理导入声明（类型级别）"""
        if self._module_manager is None:
            return  # 没有模块管理器时跳过

        module_path = decl.module_name

        # 解析并加载模块
        from nova.modules import ModuleResolver
        resolver = ModuleResolver(self._module_manager.search_paths, self._current_file)
        file_path = resolver.resolve(module_path)

        if not file_path:
            self._report_error(f"找不到模块: {module_path}", decl)
            return

        # 检查缓存
        if file_path in self._module_manager.modules:
            module_info = self._module_manager.modules[file_path]
        else:
            # 加载模块（仅类型检查）
            try:
                module_info = self._module_manager.load_module(
                    module_path, self._current_file, check_types=True
                )
            except NovaError as e:
                self._report_error(str(e), decl)
                return

        if module_info is None:
            self._report_error(f"无法加载模块: {module_path}", decl)
            return

        # 将导出的类型导入到当前环境
        for name in module_info.exported_names:
            ty = module_info.type_env.lookup(name)
            if ty is not None:
                self.env.define(name, ty)
                self._user_defined_names.add(name)

        # 同时导入 ADT 变体信息
        for adt_name, variants in module_info.type_env.get_all_adt_variants().items():
            if adt_name in module_info.exported_names:
                if adt_name not in self.env.adt_variants:
                    self.env.adt_variants[adt_name] = variants
                self.env.adt_type_params[adt_name] = module_info.type_env.get_all_adt_type_params().get(adt_name, [])

        # 导入导出的类型别名
        for alias_name, alias_ty in module_info.type_env.aliases.items():
            if alias_name in module_info.exported_names:
                self.env.aliases[alias_name] = alias_ty
                self.env.types[alias_name] = alias_ty
                self._user_defined_types.add(alias_name)

    def _check_decl_body(self, decl):
        """第二遍：检查声明的主体表达式"""
        if isinstance(decl, LetBinding):
            ty = self.check_expr(decl.value)
            if decl.type_annotation:
                annotated = self._from_ast_type(decl.type_annotation)
                if not self._types_compatible(ty, annotated):
                    self._report_error(
                        f"let 绑定 '{decl.name}' 的推断类型 {ty} 与标注类型 {annotated} 不匹配",
                        decl
                    )
            # 更新环境中的类型（用推断的实际类型替换占位符）
            self.env.define(decl.name, ty)

        elif isinstance(decl, MutBinding):
            ty = self.check_expr(decl.value)
            if decl.type_annotation:
                annotated = self._from_ast_type(decl.type_annotation)
                if not self._types_compatible(ty, annotated):
                    self._report_error(
                        f"mut 绑定 '{decl.name}' 的推断类型 {ty} 与标注类型 {annotated} 不匹配",
                        decl
                    )
            self.env.define(decl.name, ty)

        elif isinstance(decl, FnDef):
            # 检查函数体（函数类型已在第一遍注册）
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
                if not self._types_compatible(body_type, expected):
                    self._report_error(
                        f"函数 '{decl.name}' 返回类型 {body_type} 与声明的 {expected} 不匹配",
                        decl.body
                    )

        elif isinstance(decl, (TypeDef, AliasDef)):
            pass  # 这些在第一遍已处理

        elif isinstance(decl, ImportDecl):
            pass  # 导入在第一遍已处理

        elif isinstance(decl, ExportDecl):
            pass  # 导出在第一遍已标记

        else:
            # 顶层表达式
            self.check_expr(decl)

    @property
    def exported_names(self) -> set:
        """获取本模块导出的名称集合"""
        return self._exported_names

    def check_expr(self, expr) -> NovaType:
        """检查表达式并返回其类型"""

        if isinstance(expr, IntLiteral):
            return INT_T

        elif isinstance(expr, FloatLiteral):
            return FLOAT_T

        elif isinstance(expr, StringLiteral):
            return STRING_T

        elif isinstance(expr, CharLiteral):
            return CHAR_T

        elif isinstance(expr, BoolLiteral):
            return BOOL_T

        elif isinstance(expr, UnitLiteral):
            return UNIT_T

        elif isinstance(expr, Identifier):
            ty = self.env.lookup(expr.name)
            if ty is None:
                self._report_error(f"未定义的标识符 '{expr.name}'", expr)
                return ERROR_TYPE
            return ty

        elif isinstance(expr, ListExpr):
            if not expr.elements:
                return ListType(TypeVar("unknown_list_elem"))
            elem_types = [self.check_expr(e) for e in expr.elements]
            first = elem_types[0]
            for i, et in enumerate(elem_types[1:], 1):
                if not self._types_compatible(et, first):
                    self._report_error(
                        f"列表元素类型不一致：元素 0 为 {first}，元素 {i} 为 {et}",
                        expr.elements[i]
                    )
            return ListType(first)

        elif isinstance(expr, TupleExpr):
            elem_types = [self.check_expr(e) for e in expr.elements]
            return TupleType(elem_types)

        elif isinstance(expr, MapExpr):
            # Map 表达式：{ key => value, ... }，返回 Map[K, V]
            if not expr.pairs:
                return MapType(TypeVar("unknown_map_key"),
                               TypeVar("unknown_map_value"))
            key_types = []
            value_types = []
            for key_expr, value_expr in expr.pairs:
                key_types.append(self.check_expr(key_expr))
                value_types.append(self.check_expr(value_expr))
            # 检查所有键类型一致
            first_key = key_types[0]
            for i, kt in enumerate(key_types[1:], 1):
                if not self._types_compatible(kt, first_key):
                    self._report_error(
                        f"map 键类型不一致：键 0 为 {first_key}，键 {i} 为 {kt}",
                        expr.pairs[i][0]
                    )
            # 检查所有值类型一致
            first_val = value_types[0]
            for i, vt in enumerate(value_types[1:], 1):
                if not self._types_compatible(vt, first_val):
                    self._report_error(
                        f"map 值类型不一致：值 0 为 {first_val}，值 {i} 为 {vt}",
                        expr.pairs[i][1]
                    )
            return MapType(first_key, first_val)

        elif isinstance(expr, BinaryOp):
            return self._check_binary_op(expr)

        elif isinstance(expr, UnaryOp):
            return self._check_unary_op(expr)

        elif isinstance(expr, IfExpr):
            cond_ty = self.check_expr(expr.condition)
            if not self._types_compatible(cond_ty, BOOL_T):
                self._report_error(f"if 条件必须是 Bool 类型，得到 {cond_ty}", expr.condition)
            then_ty = self.check_expr(expr.then_branch)
            if expr.else_branch:
                else_ty = self.check_expr(expr.else_branch)
                if not self._types_compatible(then_ty, else_ty):
                    self._report_error(
                        f"if 分支类型不一致：then 为 {then_ty}，else 为 {else_ty}",
                        expr
                    )
                return then_ty
            return UNIT_T

        elif isinstance(expr, MatchExpr):
            subject_ty = self.check_expr(expr.subject)
            result_type = None
            for i, arm in enumerate(expr.arms):
                arm_ty = self.check_match_arm(arm, subject_ty, expr)
                if result_type is None:
                    result_type = arm_ty
                elif not self._types_compatible(arm_ty, result_type):
                    self._report_error(
                        f"match 分支 {i} 类型 {arm_ty} 与第一个分支 {result_type} 不一致",
                        arm.body
                    )
            return result_type or UNIT_T

        elif isinstance(expr, Lambda):
            param_types = []
            child_env = self.env.child()
            for i, param in enumerate(expr.params):
                if param.type_annotation:
                    ptype = self._from_ast_type(param.type_annotation)
                else:
                    ptype = TypeVar(f"lambda_param_{i}")
                param_types.append(ptype)
                child_env.define(param.name, ptype)

            old_env = self.env
            self.env = child_env
            body_ty = self.check_expr(expr.body)
            self.env = old_env

            return FnType(param_types, body_ty)

        elif isinstance(expr, FnCall):
            callee_ty = self.check_expr(expr.callee)
            arg_types = [self.check_expr(a) for a in expr.args]

            if isinstance(callee_ty, FnType):
                # 支持部分应用（参数数量少于声明的参数数量）
                if len(arg_types) > len(callee_ty.param_types):
                    self._report_error(
                        f"函数期望至多 {len(callee_ty.param_types)} 个参数，但传入了 {len(arg_types)} 个",
                        expr
                    )
                    return ERROR_TYPE
                # 收集类型变量绑定
                bindings: Dict[TypeVar, NovaType] = {}
                for arg_t, param_t in zip(arg_types, callee_ty.param_types):
                    self._collect_type_bindings(arg_t, param_t, bindings)

                for i, (arg_t, param_t) in enumerate(zip(arg_types, callee_ty.param_types)):
                    substituted = self._substitute_type_vars(param_t, bindings)
                    if not self._types_compatible(arg_t, substituted):
                        self._report_error(
                            f"参数 {i} 类型不匹配：期望 {substituted}，得到 {arg_t}",
                            expr.args[i]
                        )
                if len(arg_types) == len(callee_ty.param_types):
                    return self._substitute_type_vars(callee_ty.return_type, bindings)
                else:
                    # 部分应用：返回剩余参数 -> 返回值 的函数类型
                    remaining = [self._substitute_type_vars(p, bindings) for p in callee_ty.param_types[len(arg_types):]]
                    ret = self._substitute_type_vars(callee_ty.return_type, bindings)
                    return FnType(remaining, ret)
            elif isinstance(callee_ty, TypeVar):
                # 未类型化的参数（duck typing）：允许任意调用
                # 返回一个 TypeVar 表示结果类型
                # 报告类型推断不完整，但不阻止编译
                self.error_collector.add(TypeCheckError(
                    f"无法对未确定类型的值进行函数调用",
                    expr.span.line if expr.span else -1,
                    expr.span.column if expr.span else -1,
                    source=self._source,
                ))
                return TypeVar(f"ret_{callee_ty.name}")
            else:
                self._report_error(f"无法对非函数类型 {callee_ty} 进行调用", expr)
                return ERROR_TYPE

        elif isinstance(expr, PipeExpr):
            # expr |> f  等价于 f(expr)
            left_ty = self.check_expr(expr.left)
            right_ty = self.check_expr(expr.right)
            if isinstance(right_ty, FnType):
                if len(right_ty.param_types) >= 1:
                    # 检查管道值是否与函数最后一个参数兼容
                    # 因为管道的典型用法是 f(arg1) |> 等价于 f(piped_value)
                    last_param = right_ty.param_types[-1] if right_ty.param_types else None
                    # 也检查第一个参数（直接调用场景）
                    first_param = right_ty.param_types[0]
                    if (self._types_compatible(left_ty, last_param)
                            or self._types_compatible(left_ty, first_param)):
                        return right_ty.return_type
            # 如果无法确定，返回右侧类型
            return right_ty

        elif isinstance(expr, Block):
            for stmt in expr.statements:
                self.check_expr(stmt)
            if expr.tail_expression:
                return self.check_expr(expr.tail_expression)
            return UNIT_T

        elif isinstance(expr, LetBinding):
            val_ty = self.check_expr(expr.value)
            if expr.type_annotation:
                annotated = self._from_ast_type(expr.type_annotation)
                if not self._types_compatible(val_ty, annotated):
                    self._report_error(
                        f"let 绑定类型不匹配：推断为 {val_ty}，标注为 {annotated}",
                        expr
                    )
            self.env.define(expr.name, val_ty)
            return UNIT_T

        elif isinstance(expr, MutBinding):
            val_ty = self.check_expr(expr.value)
            self.env.define(expr.name, val_ty)
            return UNIT_T

        elif isinstance(expr, Assignment):
            val_ty = self.check_expr(expr.value)
            existing = self.env.lookup(expr.name)
            if existing is None:
                self._report_error(f"赋值目标 '{expr.name}' 未定义", expr)
                return UNIT_T
            if not self._types_compatible(val_ty, existing):
                self._report_error(
                    f"赋值类型不匹配：'{expr.name}' 为 {existing}，值为 {val_ty}",
                    expr
                )
            return UNIT_T

        elif isinstance(expr, FieldAccess):
            target_ty = self.check_expr(expr.target)
            if isinstance(target_ty, TupleType):
                try:
                    idx = int(expr.field)
                    if 0 <= idx < len(target_ty.elements):
                        return target_ty.elements[idx]
                except ValueError:
                    pass
                self._report_error(f"元组索引 '{expr.field}' 越界", expr)
                return ERROR_TYPE
            elif isinstance(target_ty, ADTType):
                # ADT 字段访问：检查所有变体是否有同名字段且类型相同（product-like access）
                variants = self.env.get_all_adt_variants().get(target_ty.name, [])
                if not variants:
                    self._report_error(f"未知的 ADT 类型 '{target_ty.name}'", expr)
                    return ERROR_TYPE

                # 尝试按索引访问（数字字段名）
                try:
                    idx = int(expr.field)
                    common_type = None
                    all_have_idx = True
                    type_param_map = dict(zip(
                        [TypeVar(tp) for tp in self.env.get_all_adt_type_params().get(target_ty.name, [])],
                        target_ty.type_params
                    ))
                    for _vname, field_info in variants:
                        if idx < 0 or idx >= len(field_info):
                            all_have_idx = False
                            break
                        field_type = field_info[idx][1]
                        substituted = self._substitute_type_vars(field_type, type_param_map)
                        if common_type is None:
                            common_type = substituted
                        elif not self._types_compatible(substituted, common_type):
                            self._report_error(
                                f"ADT 字段索引 {idx} 在不同变体中类型不一致",
                                expr
                            )
                            return ERROR_TYPE
                    if all_have_idx and common_type is not None:
                        return common_type
                    self._report_error(f"ADT 字段索引 {idx} 不是所有变体都有", expr)
                    return ERROR_TYPE
                except ValueError:
                    pass

                # 按名称访问
                field_name = expr.field
                common_type = None
                all_have_field = True
                type_param_map = dict(zip(
                    [TypeVar(tp) for tp in self.env.get_all_adt_type_params().get(target_ty.name, [])],
                    target_ty.type_params
                ))
                for _vname, field_info in variants:
                    found = False
                    for fname, ftype in field_info:
                        if fname == field_name:
                            substituted = self._substitute_type_vars(ftype, type_param_map)
                            if common_type is None:
                                common_type = substituted
                            elif not self._types_compatible(substituted, common_type):
                                self._report_error(
                                    f"ADT 字段 '{field_name}' 在不同变体中类型不一致",
                                    expr
                                )
                                return ERROR_TYPE
                            found = True
                            break
                    if not found:
                        all_have_field = False
                        break

                if all_have_field and common_type is not None:
                    return common_type
                self._report_error(
                    f"ADT 类型 '{target_ty.name}' 没有所有变体共有的字段 '{field_name}'",
                    expr
                )
                return ERROR_TYPE
            self._report_error(f"无法对类型 {target_ty} 进行字段访问", expr)
            return ERROR_TYPE

        elif isinstance(expr, IndexExpr):
            target_ty = self.check_expr(expr.target)
            idx_ty = self.check_expr(expr.index)
            if isinstance(target_ty, ListType):
                if not self._types_compatible(idx_ty, INT_T):
                    self._report_error(
                        f"列表索引必须是 Int 类型，得到 {idx_ty}",
                        expr
                    )
                return target_ty.elem_type
            elif isinstance(target_ty, MapType):
                if not self._types_compatible(idx_ty, target_ty.key_type):
                    self._report_error(
                        f"Map 键类型不匹配：期望 {target_ty.key_type}，得到 {idx_ty}",
                        expr
                    )
                return target_ty.value_type
            elif target_ty == STRING_T:
                if not self._types_compatible(idx_ty, INT_T):
                    self._report_error(
                        f"字符串索引必须是 Int 类型，得到 {idx_ty}",
                        expr
                    )
                return CHAR_T
            else:
                self._report_error(
                    f"类型错误: 无法对 {target_ty} 进行索引操作",
                    expr
                )
                return ERROR_TYPE

        elif isinstance(expr, TryExpr):
            # ? 操作符：解包 Result[T, E] -> T 或 Option[T] -> T
            inner_ty = self.check_expr(expr.expr)
            if isinstance(inner_ty, ADTType):
                if inner_ty.name == "Result" and len(inner_ty.type_params) >= 1:
                    return inner_ty.type_params[0]
                elif inner_ty.name == "Option" and len(inner_ty.type_params) >= 1:
                    return inner_ty.type_params[0]
            self._report_error(
                f"? 操作符只能在 Option 或 Result 类型上使用，得到 {inner_ty}",
                expr
            )
            return ERROR_TYPE

        elif isinstance(expr, ForExpr):
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

        elif isinstance(expr, WhileExpr):
            cond_ty = self.check_expr(expr.condition)
            if not self._types_compatible(cond_ty, BOOL_T):
                self._report_error(f"while 条件必须是 Bool 类型，得到 {cond_ty}", expr.condition)
            return self.check_expr(expr.body)

        elif isinstance(expr, BreakExpr):
            return UNIT_T

        elif isinstance(expr, ContinueExpr):
            return UNIT_T

        elif isinstance(expr, ListComprehension):
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
                if not self._types_compatible(cond_ty, BOOL_T):
                    self._report_error(f"列表推导式过滤条件必须是 Bool 类型", expr.filter_cond)
                self.env = old_env

            old_env = self.env
            self.env = child_env
            expr_ty = self.check_expr(expr.expr)
            self.env = old_env
            return ListType(expr_ty)

        else:
            self._report_error(f"未知的表达式类型: {type(expr).__name__}", expr)
            return ERROR_TYPE

    def check_match_arm(self, arm, subject_type: NovaType, match_expr: MatchExpr) -> NovaType:
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
        from nova.ast_nodes import (
            PatternWildcard, PatternInt, PatternFloat, PatternString,
            PatternBool, PatternChar, PatternIdentifier, PatternConstructor, PatternTuple, PatternList,
        )

        if isinstance(pattern, PatternWildcard):
            return

        elif isinstance(pattern, PatternInt):
            if not self._types_compatible(subject_type, INT_T):
                self._report_error(f"整数模式与类型 {subject_type} 不匹配", pattern)

        elif isinstance(pattern, PatternFloat):
            if not self._types_compatible(subject_type, FLOAT_T):
                self._report_error(f"浮点数模式与类型 {subject_type} 不匹配", pattern)

        elif isinstance(pattern, PatternBool):
            if not self._types_compatible(subject_type, BOOL_T):
                self._report_error(f"布尔模式与类型 {subject_type} 不匹配", pattern)

        elif isinstance(pattern, PatternString):
            if not self._types_compatible(subject_type, STRING_T):
                self._report_error(f"字符串模式与类型 {subject_type} 不匹配", pattern)

        elif isinstance(pattern, PatternChar):
            if not self._types_compatible(subject_type, CHAR_T):
                self._report_error(f"字符模式与类型 {subject_type} 不匹配", pattern)

        elif isinstance(pattern, PatternIdentifier):
            env.define(pattern.name, subject_type)

        elif isinstance(pattern, PatternConstructor):
            # 查找构造器对应的类型
            variants_info = None
            for adt_name, variants in self.env.get_all_adt_variants().items():
                for vname, finfo in variants:
                    if vname == pattern.name:
                        variants_info = (adt_name, finfo)
                        break
                if variants_info:
                    break

            if variants_info is None:
                self._report_error(f"未知的构造器 '{pattern.name}'", pattern)
                return

            adt_name, field_info = variants_info
            field_types = [ft for _fn, ft in field_info]

            # 如果 subject_type 是带类型参数的 ADTType，替换 field_types 中的类型变量
            if isinstance(subject_type, ADTType) and subject_type.type_params:
                type_param_map = dict(zip(
                    [TypeVar(tp) for tp in self.env.get_all_adt_type_params().get(adt_name, [])],
                    subject_type.type_params
                ))
                field_types = [self._substitute_type_vars(ft, type_param_map) for ft in field_types]

            if len(pattern.fields) != len(field_types):
                self._report_error(
                    f"构造器 '{pattern.name}' 期望 {len(field_types)} 个字段，得到 {len(pattern.fields)} 个",
                    pattern
                )
                return
            for p, ft in zip(pattern.fields, field_types):
                self._check_pattern(p, ft, env, match_expr)

        elif isinstance(pattern, PatternTuple):
            if not isinstance(subject_type, TupleType):
                self._report_error(f"元组模式与类型 {subject_type} 不匹配", pattern)
                return
            if len(pattern.elements) != len(subject_type.elements):
                self._report_error("元组模式长度不匹配", pattern)
                return
            for p, t in zip(pattern.elements, subject_type.elements):
                self._check_pattern(p, t, env, match_expr)

        elif isinstance(pattern, PatternList):
            if not isinstance(subject_type, ListType):
                self._report_error(f"列表模式与类型 {subject_type} 不匹配", pattern)
                return
            for p in pattern.elements:
                self._check_pattern(p, subject_type.elem_type, env, match_expr)

    def _check_binary_op(self, expr: BinaryOp) -> NovaType:
        """检查二元操作"""
        left_ty = self.check_expr(expr.left)
        right_ty = self.check_expr(expr.right)

        # 算术操作
        if expr.op in ("+", "-", "*", "/"):
            if self._types_compatible(left_ty, INT_T) and self._types_compatible(right_ty, INT_T):
                return INT_T
            if self._types_compatible(left_ty, FLOAT_T) and self._types_compatible(right_ty, FLOAT_T):
                return FLOAT_T
            self._report_error(
                f"操作符 '{expr.op}' 的操作数类型不兼容：{left_ty} 和 {right_ty}",
                expr
            )
            return ERROR_TYPE

        if expr.op == "%":
            if self._types_compatible(left_ty, INT_T) and self._types_compatible(right_ty, INT_T):
                return INT_T
            self._report_error(f"操作符 '%' 需要 Int 类型操作数", expr)
            return ERROR_TYPE

        # 字符串拼接
        if expr.op == "++":
            if self._types_compatible(left_ty, STRING_T) and self._types_compatible(right_ty, STRING_T):
                return STRING_T
            self._report_error(f"操作符 '++' 需要 String 类型操作数", expr)
            return ERROR_TYPE

        # 比较操作
        if expr.op in ("==", "!=", "<", ">", "<=", ">="):
            if expr.op in ("<", ">", "<=", ">="):
                if not (self._types_compatible(left_ty, INT_T) and self._types_compatible(right_ty, INT_T)
                        or self._types_compatible(left_ty, FLOAT_T) and self._types_compatible(right_ty, FLOAT_T)):
                    self._report_error(f"操作符 '{expr.op}' 需要数值类型操作数", expr)
                    return ERROR_TYPE
            return BOOL_T

        # 逻辑操作
        if expr.op in ("&&", "||"):
            has_error = False
            if not self._types_compatible(left_ty, BOOL_T):
                self._report_error(f"'&&' 左侧必须是 Bool，得到 {left_ty}", expr.left)
                has_error = True
            if not self._types_compatible(right_ty, BOOL_T):
                self._report_error(f"'&&' 右侧必须是 Bool，得到 {right_ty}", expr.right)
                has_error = True
            return ERROR_TYPE if has_error else BOOL_T

        self._report_error(f"未知的操作符 '{expr.op}'", expr)
        return ERROR_TYPE

    def _check_unary_op(self, expr: UnaryOp) -> NovaType:
        """检查一元操作"""
        operand_ty = self.check_expr(expr.operand)
        if expr.op == "-":
            if self._types_compatible(operand_ty, INT_T):
                return INT_T
            if self._types_compatible(operand_ty, FLOAT_T):
                return FLOAT_T
            self._report_error(f"一元 '-' 需要 Int 或 Float，得到 {operand_ty}", expr)
            return ERROR_TYPE
        if expr.op == "!":
            if self._types_compatible(operand_ty, BOOL_T):
                return BOOL_T
            self._report_error(f"一元 '!' 需要 Bool，得到 {operand_ty}", expr)
            return ERROR_TYPE
        self._report_error(f"未知的一元操作符 '{expr.op}'", expr)
        return ERROR_TYPE

    def _substitute_type_vars(self, ty: NovaType, bindings: Dict[TypeVar, NovaType]) -> NovaType:
        """替换类型中的类型变量"""
        if isinstance(ty, TypeVar):
            return bindings.get(ty, ty)
        if isinstance(ty, ListType):
            return ListType(self._substitute_type_vars(ty.elem_type, bindings))
        if isinstance(ty, MapType):
            return MapType(
                self._substitute_type_vars(ty.key_type, bindings),
                self._substitute_type_vars(ty.value_type, bindings)
            )
        if isinstance(ty, TupleType):
            return TupleType([self._substitute_type_vars(e, bindings) for e in ty.elements])
        if isinstance(ty, FnType):
            return FnType(
                [self._substitute_type_vars(p, bindings) for p in ty.param_types],
                self._substitute_type_vars(ty.return_type, bindings)
            )
        if isinstance(ty, ADTType):
            return ADTType(ty.name, [self._substitute_type_vars(p, bindings) for p in ty.type_params])
        return ty

    def _collect_type_bindings(self, actual: NovaType, expected: NovaType, bindings: Dict[TypeVar, NovaType]):
        """从实际类型和期望类型中收集类型变量绑定"""
        if isinstance(expected, TypeVar):
            if expected not in bindings:
                bindings[expected] = actual
        elif isinstance(expected, ListType) and isinstance(actual, ListType):
            self._collect_type_bindings(actual.elem_type, expected.elem_type, bindings)
        elif isinstance(expected, MapType) and isinstance(actual, MapType):
            self._collect_type_bindings(actual.key_type, expected.key_type, bindings)
            self._collect_type_bindings(actual.value_type, expected.value_type, bindings)
        elif isinstance(expected, TupleType) and isinstance(actual, TupleType):
            for ae, ee in zip(actual.elements, expected.elements):
                self._collect_type_bindings(ae, ee, bindings)
        elif isinstance(expected, FnType) and isinstance(actual, FnType):
            for ae, ee in zip(actual.param_types, expected.param_types):
                self._collect_type_bindings(ae, ee, bindings)
            self._collect_type_bindings(actual.return_type, expected.return_type, bindings)
        elif isinstance(expected, ADTType) and isinstance(actual, ADTType):
            if expected.name == actual.name:
                for ap, ep in zip(actual.type_params, expected.type_params):
                    self._collect_type_bindings(ap, ep, bindings)

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

    def _from_ast_type(self, type_node, _alias_stack: set = None, local_types: Dict[str, NovaType] = None) -> NovaType:
        """将 AST 中的类型注解转换为 NovaType"""
        if _alias_stack is None:
            _alias_stack = set()
        if local_types is None:
            local_types = {}

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
            if name in local_types:
                return local_types[name]
            if name in self.env.aliases:
                if name in _alias_stack:
                    raise TypeCheckError(f"类型别名 '{name}' 存在循环定义")
                _alias_stack = _alias_stack | {name}
                return self._expand_alias(self.env.aliases[name], _alias_stack)
            if name in self.env.types:
                return self.env.types[name]
            self._report_error(f"未知类型名 '{name}'", type_node)
            return ERROR_TYPE
        elif isinstance(type_node, TypeGeneric):
            base = type_node.base
            params = [self._from_ast_type(p, _alias_stack, local_types) for p in type_node.params]
            if base == "List":
                if len(params) != 1:
                    self._report_error(f"List 期望 1 个类型参数，得到 {len(params)} 个", type_node)
                return ListType(params[0]) if params else ListType(TypeVar("T"))
            elif base == "Map":
                if len(params) != 2:
                    self._report_error(f"Map 期望 2 个类型参数，得到 {len(params)} 个", type_node)
                return MapType(params[0], params[1]) if len(params) >= 2 else MapType(TypeVar("K"), TypeVar("V"))
            elif base == "Option":
                if len(params) != 1:
                    self._report_error(f"Option 期望 1 个类型参数，得到 {len(params)} 个", type_node)
                return ADTType("Option", params)
            elif base == "Result":
                if len(params) != 2:
                    self._report_error(f"Result 期望 2 个类型参数，得到 {len(params)} 个", type_node)
                return ADTType("Result", params)
            else:
                adt_params = self.env.get_all_adt_type_params().get(base)
                if adt_params is not None and len(params) != len(adt_params):
                    self._report_error(
                        f"类型 '{base}' 期望 {len(adt_params)} 个类型参数，得到 {len(params)} 个",
                        type_node
                    )
                return ADTType(base, params)
        elif isinstance(type_node, TypeTuple):
            return TupleType([self._from_ast_type(e, _alias_stack, local_types) for e in type_node.elements])
        elif isinstance(type_node, TypeFn):
            return FnType(
                [self._from_ast_type(p, _alias_stack, local_types) for p in type_node.param_types],
                self._from_ast_type(type_node.return_type, _alias_stack, local_types)
            )
        self._report_error(f"未知的类型注解: {type(type_node).__name__}", type_node)
        return ERROR_TYPE

    def _expand_alias(self, ty: NovaType, _alias_stack: set) -> NovaType:
        """递归展开类型中的别名引用"""
        if isinstance(ty, ListType):
            return ListType(self._expand_alias(ty.elem_type, _alias_stack))
        if isinstance(ty, MapType):
            return MapType(
                self._expand_alias(ty.key_type, _alias_stack),
                self._expand_alias(ty.value_type, _alias_stack)
            )
        if isinstance(ty, TupleType):
            return TupleType([self._expand_alias(e, _alias_stack) for e in ty.elements])
        if isinstance(ty, FnType):
            return FnType(
                [self._expand_alias(p, _alias_stack) for p in ty.param_types],
                self._expand_alias(ty.return_type, _alias_stack)
            )
        if isinstance(ty, ADTType):
            return ADTType(ty.name, [self._expand_alias(p, _alias_stack) for p in ty.type_params])
        return ty

    def _types_compatible(self, a: NovaType, b: NovaType) -> bool:
        """检查两个类型是否兼容"""
        if isinstance(a, ErrorType) or isinstance(b, ErrorType):
            return True
        if isinstance(a, TypeVar) or isinstance(b, TypeVar):
            return True
        if a == b:
            return True
        # 递归检查 FnType 参数兼容性
        if isinstance(a, FnType) and isinstance(b, FnType):
            if len(a.param_types) != len(b.param_types):
                return False
            return (all(self._types_compatible(pa, pb) for pa, pb in zip(a.param_types, b.param_types))
                    and self._types_compatible(a.return_type, b.return_type))
        # 递归检查 ListType
        if isinstance(a, ListType) and isinstance(b, ListType):
            return self._types_compatible(a.elem_type, b.elem_type)
        # 递归检查 MapType
        if isinstance(a, MapType) and isinstance(b, MapType):
            return (self._types_compatible(a.key_type, b.key_type)
                    and self._types_compatible(a.value_type, b.value_type))
        # 递归检查 ADTType
        if isinstance(a, ADTType) and isinstance(b, ADTType):
            if a.name != b.name:
                return False
            if len(a.type_params) != len(b.type_params):
                return False
            return all(self._types_compatible(pa, pb) for pa, pb in zip(a.type_params, b.type_params))
        return False
