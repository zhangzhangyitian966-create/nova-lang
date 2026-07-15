"""
Nova 编程语言 - 求值器（解释器核心）

遍历 AST 执行求值，管理运行时环境。
支持：闭包、模式匹配、管道操作、ADT 构造/解构、内置函数等。

运行时值表示：
- Python int    -> Nova Int
- Python float  -> Nova Float
- Python str    -> Nova String
- Python bool   -> Nova Bool
- Python list   -> Nova List
- Python tuple  -> Nova Tuple
- None          -> Nova Unit / None variant
- NovaClosure   -> 函数值（闭包）
- NovaADTValue  -> ADT 构造值
"""

import math
import json
import os
from typing import Dict, List, Optional, Any, Callable

from nova.ast_nodes import (
    Program, Block, Span,
    IntLiteral, FloatLiteral, StringLiteral, CharLiteral, BoolLiteral, UnitLiteral,
    Identifier, BinaryOp, UnaryOp, PipeExpr, TryExpr,
    Param, Lambda, FnDef, FnCall,
    LetBinding, MutBinding, Assignment,
    IfExpr, MatchArm, MatchExpr,
    ForExpr, WhileExpr, BreakExpr, ContinueExpr,
    ListExpr, ListComprehension, TupleExpr, FieldAccess, IndexExpr, MapExpr,
    ImportDecl, ExportDecl, TypeDef, VariantDef, AliasDef,
    PatternWildcard, PatternInt, PatternFloat, PatternString,
    PatternBool, PatternChar, PatternIdentifier, PatternConstructor,
    PatternTuple, PatternList,
)
from nova.environment import Environment
from nova.errors import RuntimeError_, BreakSignal, ContinueSignal, ReturnSignal


# ============================================================
# 运行时值
# ============================================================

class NovaClosure:
    """Nova 函数闭包值"""

    def __init__(self, name: str, params: List[Param], body, env: Environment):
        self.name = name
        self.params = params
        self.body = body
        self.env = env  # 闭包捕获的环境

    def __repr__(self):
        return f"<fn {self.name}>"


class NovaADTValue:
    """ADT 构造值：如 Some(42), Circle(5.0), None"""

    def __init__(self, type_name: str, variant_name: str, fields: List[Any],
                 field_names: List[str] = None):
        self.type_name = type_name
        self.variant_name = variant_name
        self.fields = fields
        self.field_names = field_names or []

    def __repr__(self):
        if self.fields:
            field_strs = ", ".join(repr(f) for f in self.fields)
            return f"{self.variant_name}({field_strs})"
        return self.variant_name

    def __eq__(self, other):
        return (isinstance(other, NovaADTValue)
                and self.type_name == other.type_name
                and self.variant_name == other.variant_name
                and self.fields == other.fields)

    def __hash__(self):
        return hash((self.type_name, self.variant_name, tuple(self.fields)))

class BuiltinFn:
    """内置函数包装"""

    def __init__(self, name: str, fn: Callable, arity: int = -1):
        self.name = name
        self.fn = fn
        self.arity = arity  # -1 表示可变参数

    def __repr__(self):
        return f"<builtin {self.name}>"


# ============================================================
# 求值器
# ============================================================

# Unit 单例
class _UnitValue:
    """Unit 类型的运行时单例值"""
    def __repr__(self): return "()"
    def __bool__(self): return False

UNIT_VALUE = _UnitValue()


class Evaluator:
    """Nova 解释器求值器"""

    def __init__(self, check_types: bool = True,
                 module_manager=None, current_file: str = None):
        self.env = Environment()
        self.check_types = check_types
        self._output: List[str] = []  # 收集 print 输出
        self._module_manager = module_manager  # ModuleManager 实例
        self._current_file = current_file      # 当前文件路径
        self._exported_names: set = set()      # 本模块导出的名称
        self._call_depth = 0                   # 当前递归调用深度
        self.MAX_CALL_DEPTH = 1000             # 最大递归调用深度（与 VM 一致）
        self._setup_builtins()

    def _setup_builtins(self):
        """注册内置函数"""
        self.env.define("print", BuiltinFn("print", self._builtin_print, 1))
        self.env.define("read_line", BuiltinFn("read_line", self._builtin_read_line, 0))
        self.env.define("int_to_str", BuiltinFn("int_to_str", self._builtin_int_to_str, 1))
        self.env.define("float_to_str", BuiltinFn("float_to_str", self._builtin_float_to_str, 1))
        self.env.define("str_to_int", BuiltinFn("str_to_int", self._builtin_str_to_int, 1))
        self.env.define("str_len", BuiltinFn("str_len", self._builtin_str_len, 1))
        self.env.define("list_length", BuiltinFn("list_length", self._builtin_list_length, 1))
        self.env.define("filter", BuiltinFn("filter", self._builtin_filter, 2))
        self.env.define("map", BuiltinFn("map", self._builtin_map, 2))
        self.env.define("sum", BuiltinFn("sum", self._builtin_sum, 1))
        self.env.define("head", BuiltinFn("head", self._builtin_head, 1))
        self.env.define("tail", BuiltinFn("tail", self._builtin_tail, 1))

        # ====== 文件 I/O ======
        self.env.define("read_file", BuiltinFn("read_file", self._builtin_read_file, 1))
        self.env.define("write_file", BuiltinFn("write_file", self._builtin_write_file, 2))
        self.env.define("file_exists", BuiltinFn("file_exists", self._builtin_file_exists, 1))
        self.env.define("list_dir", BuiltinFn("list_dir", self._builtin_list_dir, 1))

        # ====== JSON ======
        self.env.define("json_parse", BuiltinFn("json_parse", self._builtin_json_parse, 1))
        self.env.define("json_stringify", BuiltinFn("json_stringify", self._builtin_json_stringify, 1))

        # ====== 数学函数 ======
        self.env.define("abs", BuiltinFn("abs", self._builtin_abs, 1))
        self.env.define("sqrt", BuiltinFn("sqrt", self._builtin_sqrt, 1))
        self.env.define("pow", BuiltinFn("pow", self._builtin_pow, 2))
        self.env.define("log", BuiltinFn("log", self._builtin_log, 1))
        self.env.define("log10", BuiltinFn("log10", self._builtin_log10, 1))
        self.env.define("exp", BuiltinFn("exp", self._builtin_exp, 1))
        self.env.define("sin", BuiltinFn("sin", self._builtin_sin, 1))
        self.env.define("cos", BuiltinFn("cos", self._builtin_cos, 1))
        self.env.define("tan", BuiltinFn("tan", self._builtin_tan, 1))
        self.env.define("floor", BuiltinFn("floor", self._builtin_floor, 1))
        self.env.define("ceil", BuiltinFn("ceil", self._builtin_ceil, 1))
        self.env.define("round", BuiltinFn("round", self._builtin_round, 1))
        self.env.define("min", BuiltinFn("min", self._builtin_min, 2))
        self.env.define("max", BuiltinFn("max", self._builtin_max, 2))
        self.env.define("pi", BuiltinFn("pi", self._builtin_pi, 0))

        # 注册内置 Option 和 Result 的构造函数
        self.env.define("Some", BuiltinFn("Some", lambda *args: NovaADTValue("Option", "Some", list(args), ["value"]), 1))
        self.env.define("None", NovaADTValue("Option", "None", [], []))
        self.env.define("Ok", BuiltinFn("Ok", lambda *args: NovaADTValue("Result", "Ok", list(args), ["value"]), 1))
        self.env.define("Err", BuiltinFn("Err", lambda *args: NovaADTValue("Result", "Err", list(args), ["error"]), 1))

    # ----------------------------------------------------------
    # 内置函数实现
    # ----------------------------------------------------------

    def _builtin_print(self, *args):
        val = self._format_value(args[0])
        print(val)
        self._output.append(val)
        return UNIT_VALUE

    def _builtin_read_line(self, *args):
        try:
            return input()
        except EOFError:
            return ""

    def _builtin_int_to_str(self, *args):
        return str(args[0])

    def _builtin_float_to_str(self, *args):
        return str(args[0])

    def _builtin_str_to_int(self, *args):
        try:
            return NovaADTValue("Option", "Some", [int(args[0])], ["value"])
        except ValueError:
            return NovaADTValue("Option", "None", [], [])

    def _builtin_str_len(self, *args):
        return len(args[0])

    def _builtin_list_length(self, *args):
        return len(args[0])

    def _builtin_filter(self, *args):
        pred_fn, lst = args[0], args[1]
        return [item for item in lst if self._call_fn(pred_fn, [item]) is True]

    def _builtin_map(self, *args):
        map_fn, lst = args[0], args[1]
        return [self._call_fn(map_fn, [item]) for item in lst]

    def _builtin_sum(self, *args):
        return sum(args[0])

    def _builtin_head(self, *args):
        lst = args[0]
        if lst:
            return NovaADTValue("Option", "Some", [lst[0]], field_names=["value"])
        return NovaADTValue("Option", "None", [], field_names=["value"])

    def _builtin_tail(self, *args):
        lst = args[0]
        if len(lst) > 0:
            return NovaADTValue("Option", "Some", [lst[1:]], field_names=["value"])
        return NovaADTValue("Option", "None", [], field_names=["value"])

    # ----------------------------------------------------------
    # 文件 I/O 内置函数
    # ----------------------------------------------------------

    def _builtin_read_file(self, *args):
        path = args[0]
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise RuntimeError_(f"文件 '{path}' 不存在")

    def _builtin_write_file(self, *args):
        path, content = args[0], args[1]
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return UNIT_VALUE
        except IOError as e:
            raise RuntimeError_(f"写入文件 '{path}' 失败: {e}")

    def _builtin_file_exists(self, *args):
        path = args[0]
        return os.path.exists(path)

    def _builtin_list_dir(self, *args):
        path = args[0]
        try:
            return sorted(os.listdir(path))
        except OSError as e:
            raise RuntimeError_(f"列出目录 '{path}' 失败: {e}")

    # ----------------------------------------------------------
    # JSON 内置函数
    # ----------------------------------------------------------

    def _builtin_json_parse(self, *args):
        text = args[0]
        try:
            result = json.loads(text)
            return self._convert_json_to_nova(result)
        except json.JSONDecodeError as e:
            raise RuntimeError_(f"JSON 解析失败: {e}")

    def _convert_json_to_nova(self, val):
        """将 Python JSON 值转换为 Nova 运行时值"""
        if val is None:
            return NovaADTValue("Option", "None", [])
        if isinstance(val, bool):
            return val
        if isinstance(val, int):
            return val
        if isinstance(val, float):
            return val
        if isinstance(val, str):
            return val
        if isinstance(val, list):
            return [self._convert_json_to_nova(item) for item in val]
        if isinstance(val, dict):
            # JSON 对象转换为 NovaADTValue 或 Python dict
            # 使用 Python dict 来表示，键为 String，值为任意类型
            return {k: self._convert_json_to_nova(v) for k, v in val.items()}
        return val

    def _builtin_json_stringify(self, *args):
        val = args[0]
        try:
            return json.dumps(self._convert_nova_to_json(val))
        except (TypeError, ValueError) as e:
            raise RuntimeError_(f"JSON 序列化失败: {e}")

    def _convert_nova_to_json(self, val):
        """将 Nova 运行时值转换为 Python JSON 兼容值"""
        if val is UNIT_VALUE:
            return None
        if val is None:
            return None
        if isinstance(val, NovaADTValue):
            if val.variant_name == "None":
                return None
            if val.variant_name == "Some" and len(val.fields) == 1:
                return self._convert_nova_to_json(val.fields[0])
            if val.variant_name == "Ok" and len(val.fields) == 1:
                return self._convert_nova_to_json(val.fields[0])
            if val.variant_name == "Err":
                return None
            return {"_type": val.type_name, "_variant": val.variant_name,
                    "_fields": [self._convert_nova_to_json(f) for f in val.fields]}
        if isinstance(val, list):
            return [self._convert_nova_to_json(item) for item in val]
        if isinstance(val, tuple):
            return [self._convert_nova_to_json(item) for item in val]
        if isinstance(val, dict):
            return {str(k): self._convert_nova_to_json(v) for k, v in val.items()}
        return val

    # ----------------------------------------------------------
    # 数学内置函数
    # ----------------------------------------------------------

    def _to_float(self, val):
        """将值转换为 Float（支持 Int 输入）"""
        if isinstance(val, int) and not isinstance(val, bool):
            return float(val)
        return val

    def _builtin_abs(self, *args):
        return abs(self._to_float(args[0]))

    def _builtin_sqrt(self, *args):
        return math.sqrt(self._to_float(args[0]))

    def _builtin_pow(self, *args):
        return math.pow(self._to_float(args[0]), self._to_float(args[1]))

    def _builtin_log(self, *args):
        return math.log(self._to_float(args[0]))

    def _builtin_log10(self, *args):
        return math.log10(self._to_float(args[0]))

    def _builtin_exp(self, *args):
        return math.exp(self._to_float(args[0]))

    def _builtin_sin(self, *args):
        return math.sin(self._to_float(args[0]))

    def _builtin_cos(self, *args):
        return math.cos(self._to_float(args[0]))

    def _builtin_tan(self, *args):
        return math.tan(self._to_float(args[0]))

    def _builtin_floor(self, *args):
        return float(math.floor(self._to_float(args[0])))

    def _builtin_ceil(self, *args):
        return float(math.ceil(self._to_float(args[0])))

    def _builtin_round(self, *args):
        return float(round(self._to_float(args[0])))

    def _builtin_min(self, *args):
        return float(min(self._to_float(args[0]), self._to_float(args[1])))

    def _builtin_max(self, *args):
        return float(max(self._to_float(args[0]), self._to_float(args[1])))

    def _builtin_pi(self, *args):
        return math.pi

    # ----------------------------------------------------------
    # 辅助方法
    # ----------------------------------------------------------

    def _format_value(self, val) -> str:
        """将运行时值格式化为字符串"""
        if val is UNIT_VALUE:
            return "()"
        if val is None:
            return "null"
        if isinstance(val, bool):
            return "true" if val else "false"
        if isinstance(val, NovaADTValue):
            return repr(val)
        if isinstance(val, list):
            items = ", ".join(self._format_value(v) for v in val)
            return f"[{items}]"
        if isinstance(val, tuple):
            items = ", ".join(self._format_value(v) for v in val)
            return f"({items})"
        if isinstance(val, NovaClosure):
            return f"<fn {val.name}>"
        if isinstance(val, BuiltinFn):
            return f"<builtin {val.name}>"
        return str(val)

    def _call_fn(self, fn, args: List[Any]) -> Any:
        """调用函数（支持闭包和内置函数，支持部分应用/柯里化）"""
        if isinstance(fn, BuiltinFn):
            # 如果参数不足且函数支持部分应用，返回一个柯里化版本
            if fn.arity > 0 and len(args) < fn.arity:
                def curried(*more_args):
                    return fn.fn(*(args + list(more_args)))
                return BuiltinFn(fn.name, curried, fn.arity - len(args))
            return fn.fn(*args)

        if isinstance(fn, NovaClosure):
            if len(args) < len(fn.params):
                # 部分应用：返回捕获已提供参数的闭包
                captured_params = fn.params[:len(args)]
                remaining_params = fn.params[len(args):]

                # 创建捕获环境：在原始 env 基础上绑定已捕获的参数
                captured_env = fn.env.child()
                for param, arg in zip(captured_params, args):
                    captured_env.define(param.name, arg)

                return NovaClosure(
                    name=f"<partial {fn.name}>",
                    params=remaining_params,
                    body=fn.body,
                    env=captured_env,
                )
            if len(args) > len(fn.params):
                raise RuntimeError_(
                    f"函数 '{fn.name}' 期望 {len(fn.params)} 个参数，但传入了 {len(args)} 个"
                )
            child_env = fn.env.child()
            for param, arg in zip(fn.params, args):
                child_env.define(param.name, arg)

            old_env = self.env
            self.env = child_env
            self._call_depth += 1
            if self._call_depth > self.MAX_CALL_DEPTH:
                self._call_depth -= 1
                self.env = old_env
                raise RuntimeError_("栈溢出：调用深度超过限制")
            try:
                result = self.eval_expr(fn.body)
            except ReturnSignal as ret:
                result = ret.value
            except BreakSignal:
                raise RuntimeError_("break 不能出现在函数体内")
            except ContinueSignal:
                raise RuntimeError_("continue 不能出现在函数体内")
            finally:
                self._call_depth -= 1
                self.env = old_env
            return result

        raise RuntimeError_(f"无法调用非函数值: {fn}")

    def get_output(self) -> List[str]:
        """获取 print 输出"""
        return self._output

    def clear_output(self):
        """清空输出缓冲"""
        self._output.clear()

    # ----------------------------------------------------------
    # 程序求值
    # ----------------------------------------------------------

    def eval_program(self, program: Program):
        """求值整个程序（两遍扫描：先注册所有函数/类型，再求值绑定和表达式）

        第一遍：注册所有函数、ADT 构造器、类型别名
        第二遍：求值 let/mut 绑定的值和顶层表达式
        这样支持前向引用和相互递归
        """
        # 第一遍：收集所有函数和类型声明
        for decl in program.declarations:
            self._collect_decl(decl)

        # 第二遍：求值绑定值和顶层表达式
        for decl in program.declarations:
            self._eval_decl_body(decl)

        # 自动调用 main() 函数
        try:
            main_fn = self.env.lookup("main")
        except (NameError, RuntimeError_):
            pass  # 没有 main 函数时忽略
        else:
            if callable(main_fn) or isinstance(main_fn, (NovaClosure, BuiltinFn)):
                self._call_fn(main_fn, [])

    def _collect_decl(self, decl):
        """第一遍：注册函数和类型声明（不求值函数体）"""
        if isinstance(decl, FnDef):
            # 创建闭包（捕获当前环境，即顶层环境）
            closure = NovaClosure(
                name=decl.name,
                params=decl.params,
                body=decl.body,
                env=self.env,
            )
            self.env.define(decl.name, closure)

        elif isinstance(decl, TypeDef):
            # 注册 ADT 构造函数
            for variant in decl.variants:
                if variant.fields:
                    # 带字段的构造器 -> 函数
                    field_names = [f[0] for f in variant.fields]

                    def make_constructor(type_name, vname, fnames):
                        def constructor(*args):
                            return NovaADTValue(type_name, vname, list(args), fnames)
                        return constructor

                    ctor = BuiltinFn(
                        variant.name,
                        make_constructor(decl.name, variant.name, field_names),
                        len(variant.fields)
                    )
                else:
                    # 无字段构造器 -> 直接是值
                    ctor = NovaADTValue(decl.name, variant.name, [], [])

                self.env.define(variant.name, ctor)

        elif isinstance(decl, AliasDef):
            # 类型别名在运行时不产生值，跳过
            pass

        elif isinstance(decl, (ImportDecl, ExportDecl)):
            if isinstance(decl, ImportDecl):
                self._handle_import_decl(decl)
            elif isinstance(decl, ExportDecl):
                self._exported_names.add(decl.name)

        # let/mut 绑定和顶层表达式在第二遍处理
        else:
            pass

    def _eval_decl_body(self, decl):
        """第二遍：求值绑定值和顶层表达式"""
        if isinstance(decl, LetBinding):
            val = self.eval_expr(decl.value)
            self.env.define(decl.name, val, mutable=False)

        elif isinstance(decl, MutBinding):
            val = self.eval_expr(decl.value)
            self.env.define(decl.name, val, mutable=True)

        elif isinstance(decl, (FnDef, TypeDef, AliasDef)):
            pass  # 这些在第一遍已处理

        elif isinstance(decl, ImportDecl):
            pass  # 导入在第一遍已处理

        elif isinstance(decl, ExportDecl):
            pass  # 导出在第一遍已标记

        else:
            # 顶层表达式
            self.eval_expr(decl)

    def eval_decl(self, decl):
        """求值顶层声明"""
        if isinstance(decl, LetBinding):
            val = self.eval_expr(decl.value)
            self.env.define(decl.name, val, mutable=False)

        elif isinstance(decl, MutBinding):
            val = self.eval_expr(decl.value)
            self.env.define(decl.name, val, mutable=True)

        elif isinstance(decl, FnDef):
            # 创建闭包
            closure = NovaClosure(
                name=decl.name,
                params=decl.params,
                body=decl.body,
                env=self.env,
            )
            self.env.define(decl.name, closure)

        elif isinstance(decl, TypeDef):
            # 注册 ADT 构造函数
            for variant in decl.variants:
                if variant.fields:
                    # 带字段的构造器 -> 函数
                    field_names = [f[0] for f in variant.fields]

                    def make_constructor(type_name, vname, fnames):
                        def constructor(*args):
                            return NovaADTValue(type_name, vname, list(args), fnames)
                        return constructor

                    ctor = BuiltinFn(
                        variant.name,
                        make_constructor(decl.name, variant.name, field_names),
                        len(variant.fields)
                    )
                else:
                    # 无字段构造器 -> 直接是值
                    ctor = NovaADTValue(decl.name, variant.name, [])

                self.env.define(variant.name, ctor)

        elif isinstance(decl, AliasDef):
            # 类型别名在运行时不产生值，跳过
            pass

        elif isinstance(decl, (ImportDecl, ExportDecl)):
            if isinstance(decl, ImportDecl):
                self._handle_import_decl(decl)
            elif isinstance(decl, ExportDecl):
                self._exported_names.add(decl.name)

        else:
            # 顶层表达式
            self.eval_expr(decl)

    def _handle_import_decl(self, decl: ImportDecl):
        """处理导入声明（运行时级别）"""
        if self._module_manager is None:
            return  # 没有模块管理器时跳过

        module_path = decl.module_name

        # 解析并加载模块
        from nova.modules import ModuleResolver
        resolver = ModuleResolver(self._module_manager.search_paths, self._current_file)
        file_path = resolver.resolve(module_path)

        if not file_path:
            raise RuntimeError_(f"找不到模块: {module_path}")

        # 检查缓存
        if file_path in self._module_manager.modules:
            module_info = self._module_manager.modules[file_path]
        else:
            module_info = self._module_manager.load_module(
                module_path, self._current_file, check_types=self.check_types
            )

        if module_info is None:
            raise RuntimeError_(f"无法加载模块: {module_path}")

        # 将导出的绑定导入到当前环境
        for name in module_info.exported_names:
            try:
                value = module_info.eval_env.lookup(name)
                self.env.define(name, value, mutable=False)
            except (NameError, RuntimeError_):
                pass  # 忽略找不到的绑定

    @property
    def exported_names(self) -> set:
        """获取本模块导出的名称集合"""
        return self._exported_names

    # ----------------------------------------------------------
    # 表达式求值
    # ----------------------------------------------------------

    def eval_expr(self, expr) -> Any:
        """求值表达式并返回运行时值"""

        # --- 字面量 ---
        if isinstance(expr, IntLiteral):
            return expr.value

        elif isinstance(expr, FloatLiteral):
            return expr.value

        elif isinstance(expr, StringLiteral):
            return expr.value

        elif isinstance(expr, CharLiteral):
            return expr.value

        elif isinstance(expr, BoolLiteral):
            return expr.value

        elif isinstance(expr, UnitLiteral):
            return UNIT_VALUE

        # --- 标识符 ---
        elif isinstance(expr, Identifier):
            try:
                return self.env.lookup(expr.name)
            except (NameError, RuntimeError_):
                raise RuntimeError_(f"未定义的变量 '{expr.name}'")

        # --- 二元操作 ---
        elif isinstance(expr, BinaryOp):
            return self._eval_binary_op(expr)

        # --- 一元操作 ---
        elif isinstance(expr, UnaryOp):
            return self._eval_unary_op(expr)

        # --- 管道操作 ---
        elif isinstance(expr, PipeExpr):
            # expr |> f  等价于 f(expr)
            left_val = self.eval_expr(expr.left)
            right_val = self.eval_expr(expr.right)
            return self._call_fn(right_val, [left_val])

        # --- ? 错误传播 ---
        elif isinstance(expr, TryExpr):
            val = self.eval_expr(expr.expr)
            if isinstance(val, NovaADTValue):
                if val.variant_name in ("None", "Err"):
                    # 提前退出当前函数，将 Err/None 值传播上去
                    raise ReturnSignal(val)
                if val.variant_name in ("Some", "Ok"):
                    return val.fields[0]
                raise RuntimeError_(f"? 操作符只能在 Option 或 Result 类型上使用，得到 {val.type_name}")
            raise RuntimeError_(f"? 操作符只能在 Option 或 Result 类型上使用，得到 {type(val).__name__}")

        # --- 函数调用 ---
        elif isinstance(expr, FnCall):
            callee = self.eval_expr(expr.callee)
            args = [self.eval_expr(a) for a in expr.args]
            return self._call_fn(callee, args)

        # --- Lambda ---
        elif isinstance(expr, Lambda):
            return NovaClosure(
                name="<lambda>",
                params=expr.params,
                body=expr.body,
                env=self.env,
            )

        # --- if-then-else ---
        elif isinstance(expr, IfExpr):
            cond = self.eval_expr(expr.condition)
            if not isinstance(cond, bool):
                cond_ty = type(cond).__name__
                raise RuntimeError_(f"if 条件必须是 Bool 类型，得到 {cond_ty}")
            if cond:
                return self.eval_expr(expr.then_branch)
            elif expr.else_branch:
                return self.eval_expr(expr.else_branch)
            return UNIT_VALUE

        # --- match ---
        elif isinstance(expr, MatchExpr):
            return self._eval_match(expr)

        # --- 代码块 ---
        elif isinstance(expr, Block):
            child_env = self.env.child()
            old_env = self.env
            self.env = child_env
            for stmt in expr.statements:
                self.eval_expr(stmt)
            result = UNIT_VALUE
            if expr.tail_expression:
                result = self.eval_expr(expr.tail_expression)
            self.env = old_env
            return result

        # --- let 绑定（在代码块内） ---
        elif isinstance(expr, LetBinding):
            val = self.eval_expr(expr.value)
            self.env.define(expr.name, val, mutable=False)
            return UNIT_VALUE

        # --- mut 绑定（在代码块内） ---
        elif isinstance(expr, MutBinding):
            val = self.eval_expr(expr.value)
            self.env.define(expr.name, val, mutable=True)
            return UNIT_VALUE

        # --- 赋值 ---
        elif isinstance(expr, Assignment):
            val = self.eval_expr(expr.value)
            try:
                self.env.assign(expr.name, val)
            except RuntimeError_ as e:
                raise RuntimeError_(str(e))
            return UNIT_VALUE

        # --- 列表 ---
        elif isinstance(expr, ListExpr):
            return [self.eval_expr(e) for e in expr.elements]

        # --- 字典 ---
        elif isinstance(expr, MapExpr):
            return {self.eval_expr(k): self.eval_expr(v) for k, v in expr.pairs}

        # --- 列表推导式 ---
        elif isinstance(expr, ListComprehension):
            return self._eval_list_comprehension(expr)

        # --- for 循环 ---
        elif isinstance(expr, ForExpr):
            return self._eval_for_expr(expr)

        # --- while 循环 ---
        elif isinstance(expr, WhileExpr):
            return self._eval_while_expr(expr)

        # --- break ---
        elif isinstance(expr, BreakExpr):
            raise BreakSignal()

        # --- continue ---
        elif isinstance(expr, ContinueExpr):
            raise ContinueSignal()

        # --- 元组 ---
        elif isinstance(expr, TupleExpr):
            return tuple(self.eval_expr(e) for e in expr.elements)

        # --- 字段访问 ---
        elif isinstance(expr, FieldAccess):
            target = self.eval_expr(expr.target)
            if isinstance(target, tuple):
                try:
                    idx = int(expr.field)
                    return target[idx]
                except (ValueError, IndexError):
                    raise RuntimeError_(f"元组索引 '{expr.field}' 越界")
            elif isinstance(target, NovaADTValue):
                # 尝试索引访问
                try:
                    idx = int(expr.field)
                    if 0 <= idx < len(target.fields):
                        return target.fields[idx]
                    raise RuntimeError_(f"ADT 字段索引 {idx} 越界")
                except ValueError:
                    pass
                # 按名称访问
                field_name = expr.field
                for i, fname in enumerate(target.field_names):
                    if fname == field_name:
                        return target.fields[i]
                raise RuntimeError_(f"ADT 值没有字段 '{field_name}'")
            raise RuntimeError_(f"无法对值进行字段访问")

        # --- 索引访问 ---
        elif isinstance(expr, IndexExpr):
            target = self.eval_expr(expr.target)
            idx = self.eval_expr(expr.index)
            try:
                if isinstance(target, dict):
                    if idx not in target:
                        raise RuntimeError_(f"键不存在: {idx}")
                    return target[idx]
                else:
                    return target[idx]
            except IndexError:
                raise RuntimeError_(f"索引越界: {idx}")
            except TypeError:
                raise RuntimeError_(f"类型错误: 无法对 {type(target).__name__} 进行索引操作")

        else:
            raise RuntimeError_(f"未知的表达式类型: {type(expr).__name__}")

    def _eval_binary_op(self, expr: BinaryOp) -> Any:
        """求值二元操作"""
        # 短路求值
        if expr.op == "&&":
            left = self.eval_expr(expr.left)
            if not left:
                return left
            return self.eval_expr(expr.right)

        if expr.op == "||":
            left = self.eval_expr(expr.left)
            if left:
                return left
            return self.eval_expr(expr.right)

        left = self.eval_expr(expr.left)
        right = self.eval_expr(expr.right)

        if expr.op == "+":
            return left + right
        elif expr.op == "-":
            return left - right
        elif expr.op == "*":
            return left * right
        elif expr.op == "/":
            if isinstance(left, int) and isinstance(right, int):
                if right == 0:
                    raise RuntimeError_("除零错误")
                return left // right  # 整数除法
            return left / right
        elif expr.op == "%":
            return left % right
        elif expr.op == "++":
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            raise RuntimeError_("类型错误：操作符 '++' 只能用于 String 类型")
        elif expr.op == "==":
            # Nova 中 Bool 和 Int 是不同类型：bool 与非 bool 比较永远不相等
            if isinstance(left, bool) != isinstance(right, bool):
                return False
            return left == right
        elif expr.op == "!=":
            if isinstance(left, bool) != isinstance(right, bool):
                return True
            return left != right
        elif expr.op in ("<", ">", "<=", ">="):
            if isinstance(left, bool) != isinstance(right, bool):
                raise RuntimeError_("类型错误：Bool 类型只能与 Bool 类型进行比较")
            if expr.op == "<":
                return left < right
            elif expr.op == ">":
                return left > right
            elif expr.op == "<=":
                return left <= right
            elif expr.op == ">=":
                return left >= right

        raise RuntimeError_(f"未知的操作符 '{expr.op}'")

    def _eval_unary_op(self, expr: UnaryOp) -> Any:
        """求值一元操作"""
        operand = self.eval_expr(expr.operand)
        if expr.op == "-":
            return -operand
        elif expr.op == "!":
            if not isinstance(operand, bool):
                raise RuntimeError_(f"! 操作数必须是 Bool 类型，得到 {type(operand).__name__}")
            return not operand
        raise RuntimeError_(f"未知的一元操作符 '{expr.op}'")

    def _eval_for_expr(self, expr: ForExpr) -> Any:
        """求值 for 循环表达式，返回列表"""
        # 确定迭代器
        if isinstance(expr.iterable, tuple) and expr.iterable[0] == "range":
            # 范围循环: ("range", start, end, step)
            start = self.eval_expr(expr.iterable[1])
            end = self.eval_expr(expr.iterable[2])
            step = self.eval_expr(expr.iterable[3]) if expr.iterable[3] else 1
            if step > 0:
                items = list(range(start, end + 1, step))
            elif step < 0:
                items = list(range(start, end - 1, step))
            else:
                raise RuntimeError_("range 步长不能为 0")
        else:
            # 列表遍历
            items = self.eval_expr(expr.iterable)

        results = []
        for item in items:
            child_env = self.env.child()
            child_env.define(expr.var_name, item)
            old_env = self.env
            self.env = child_env
            try:
                result = self.eval_expr(expr.body)
                results.append(result)
            except BreakSignal:
                break
            except ContinueSignal:
                pass
            finally:
                self.env = old_env

        return results

    def _eval_while_expr(self, expr: WhileExpr) -> Any:
        """求值 while 循环表达式"""
        result = UNIT_VALUE
        while True:
            cond = self.eval_expr(expr.condition)
            if not isinstance(cond, bool):
                raise RuntimeError_(f"while 条件必须是 Bool 类型，得到 {type(cond).__name__}")
            if not cond:
                break
            try:
                result = self.eval_expr(expr.body)
            except BreakSignal:
                break
            except ContinueSignal:
                continue
        return result

    def _eval_list_comprehension(self, expr: ListComprehension) -> Any:
        """求值列表推导式"""
        # 确定迭代器
        if isinstance(expr.iterable, tuple) and expr.iterable[0] == "range":
            start = self.eval_expr(expr.iterable[1])
            end = self.eval_expr(expr.iterable[2])
            step = self.eval_expr(expr.iterable[3]) if expr.iterable[3] else 1
            if step > 0:
                items = list(range(start, end + 1, step))
            elif step < 0:
                items = list(range(start, end - 1, step))
            else:
                raise RuntimeError_("range 步长不能为 0")
        else:
            items = self.eval_expr(expr.iterable)

        results = []
        for item in items:
            child_env = self.env.child()
            child_env.define(expr.var_name, item)
            old_env = self.env
            self.env = child_env
            try:
                # 检查过滤条件
                if expr.filter_cond is not None:
                    if not self.eval_expr(expr.filter_cond):
                        continue
                results.append(self.eval_expr(expr.expr))
            finally:
                self.env = old_env

        return results

    def _eval_match(self, expr: MatchExpr) -> Any:
        """求值 match 表达式"""
        subject = self.eval_expr(expr.subject)

        for arm in expr.arms:
            bindings = {}
            if self._match_pattern(arm.pattern, subject, bindings):
                if arm.guard is not None:
                    child_env = self.env.child()
                    for name, val in bindings.items():
                        child_env.define(name, val)
                    old_env = self.env
                    self.env = child_env
                    try:
                        guard_val = self.eval_expr(arm.guard)
                    finally:
                        self.env = old_env
                    if not guard_val:
                        continue
                # 在新作用域中绑定模式变量并求值分支
                child_env = self.env.child()
                for name, val in bindings.items():
                    child_env.define(name, val)
                old_env = self.env
                self.env = child_env
                try:
                    result = self.eval_expr(arm.body)
                finally:
                    self.env = old_env
                return result

        raise RuntimeError_("模式匹配失败：没有匹配的分支（考虑添加 _ 通配符）")

    def _match_pattern(self, pattern, value, bindings: Dict[str, Any]) -> bool:
        """尝试匹配模式，成功则填充 bindings"""
        if isinstance(pattern, PatternWildcard):
            return True

        elif isinstance(pattern, PatternInt):
            return isinstance(value, int) and not isinstance(value, bool) and value == pattern.value

        elif isinstance(pattern, PatternFloat):
            return isinstance(value, float) and value == pattern.value

        elif isinstance(pattern, PatternString):
            return isinstance(value, str) and value == pattern.value

        elif isinstance(pattern, PatternBool):
            return isinstance(value, bool) and value == pattern.value

        elif isinstance(pattern, PatternChar):
            return isinstance(value, str) and len(value) == 1 and value == pattern.value

        elif isinstance(pattern, PatternIdentifier):
            bindings[pattern.name] = value
            return True

        elif isinstance(pattern, PatternConstructor):
            if not isinstance(value, NovaADTValue):
                return False
            if value.variant_name != pattern.name:
                return False
            if len(pattern.fields) != len(value.fields):
                return False
            for p, v in zip(pattern.fields, value.fields):
                if not self._match_pattern(p, v, bindings):
                    return False
            return True

        elif isinstance(pattern, PatternTuple):
            if not isinstance(value, tuple):
                return False
            if len(pattern.elements) != len(value):
                return False
            for p, v in zip(pattern.elements, value):
                if not self._match_pattern(p, v, bindings):
                    return False
            return True

        elif isinstance(pattern, PatternList):
            if not isinstance(value, list):
                return False
            if len(pattern.elements) != len(value):
                return False
            for p, v in zip(pattern.elements, value):
                if not self._match_pattern(p, v, bindings):
                    return False
            return True

        return False
