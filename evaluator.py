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

import json
import math
import os
from typing import Any, Callable, Dict, List

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
    PipeExpr,
    Program,
    StringLiteral,
    TryExpr,
    TupleExpr,
    TypeDef,
    UnaryOp,
    UnitLiteral,
    WhileExpr,
)
from .environment import Environment
from .errors import BreakSignal, ContinueSignal, RuntimeError_

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

    def __init__(self, type_name: str, variant_name: str, fields: List[Any]):
        self.type_name = type_name
        self.variant_name = variant_name
        self.fields = fields

    def __repr__(self):
        if self.fields:
            field_strs = ", ".join(repr(f) for f in self.fields)
            return f"{self.variant_name}({field_strs})"
        return self.variant_name

    def __eq__(self, other):
        return (
            isinstance(other, NovaADTValue)
            and self.variant_name == other.variant_name
            and self.fields == other.fields
        )


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
UNIT_VALUE = object()


class Evaluator:
    """Nova 解释器求值器"""

    def _setup_builtins(self):
        """注册内置函数"""
        self.env.define("print", BuiltinFn("print", self._builtin_print, 1))
        self.env.define("read_line", BuiltinFn("read_line", self._builtin_read_line, 0))
        self.env.define(
            "int_to_str", BuiltinFn("int_to_str", self._builtin_int_to_str, 1)
        )
        self.env.define(
            "float_to_str", BuiltinFn("float_to_str", self._builtin_float_to_str, 1)
        )
        self.env.define(
            "str_to_int", BuiltinFn("str_to_int", self._builtin_str_to_int, 1)
        )
        self.env.define("str_len", BuiltinFn("str_len", self._builtin_str_len, 1))
        self.env.define(
            "list_length", BuiltinFn("list_length", self._builtin_list_length, 1)
        )
        self.env.define("filter", BuiltinFn("filter", self._builtin_filter, 2))
        self.env.define("map", BuiltinFn("map", self._builtin_map, 2))
        self.env.define("sum", BuiltinFn("sum", self._builtin_sum, 1))
        self.env.define("head", BuiltinFn("head", self._builtin_head, 1))
        self.env.define("tail", BuiltinFn("tail", self._builtin_tail, 1))

        # ====== 文件 I/O ======
        self.env.define("read_file", BuiltinFn("read_file", self._builtin_read_file, 1))
        self.env.define(
            "write_file", BuiltinFn("write_file", self._builtin_write_file, 2)
        )
        self.env.define(
            "file_exists", BuiltinFn("file_exists", self._builtin_file_exists, 1)
        )
        self.env.define("list_dir", BuiltinFn("list_dir", self._builtin_list_dir, 1))

        # ====== JSON ======
        self.env.define(
            "json_parse", BuiltinFn("json_parse", self._builtin_json_parse, 1)
        )
        self.env.define(
            "json_stringify",
            BuiltinFn("json_stringify", self._builtin_json_stringify, 1),
        )

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
        self.env.define(
            "Some",
            BuiltinFn(
                "Some", lambda *args: NovaADTValue("Option", "Some", list(args)), 1
            ),
        )
        self.env.define("None", NovaADTValue("Option", "None", []))
        self.env.define(
            "Ok",
            BuiltinFn("Ok", lambda *args: NovaADTValue("Result", "Ok", list(args)), 1),
        )
        self.env.define(
            "Err",
            BuiltinFn(
                "Err", lambda *args: NovaADTValue("Result", "Err", list(args)), 1
            ),
        )

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
            return NovaADTValue("Option", "Some", [int(args[0])])
        except ValueError:
            return NovaADTValue("Option", "None", [])

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
            return NovaADTValue("Option", "Some", [lst[0]])
        return NovaADTValue("Option", "None", [])

    def _builtin_tail(self, *args):
        lst = args[0]
        if len(lst) > 0:
            return NovaADTValue("Option", "Some", [lst[1:]])
        return NovaADTValue("Option", "None", [])

    # ----------------------------------------------------------
    # 文件 I/O 内置函数
    # ----------------------------------------------------------

    def _builtin_read_file(self, *args):
        path = args[0]
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise RuntimeError_(f"文件 '{path}' 不存在")

    def _builtin_write_file(self, *args):
        path, content = args[0], args[1]
        try:
            with open(path, "w", encoding="utf-8") as f:
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
            return {
                "_type": val.type_name,
                "_variant": val.variant_name,
                "_fields": [self._convert_nova_to_json(f) for f in val.fields],
            }
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
                remaining_params = fn.params[len(args) :]
                captured = args

                def partially_applied(*more_args):
                    all_args = captured + list(more_args)
                    return self._call_fn(fn, all_args)

                return NovaClosure(
                    name=f"<partial {fn.name}>",
                    params=remaining_params,
                    body=fn.body,
                    env=fn.env,
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
            result = self.eval_expr(fn.body)
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
        """求值整个程序"""
        for decl in program.declarations:
            self.eval_decl(decl)

        # 自动调用 main() 函数
        try:
            main_fn = self.env.lookup("main")
            if callable(main_fn) or isinstance(main_fn, (NovaClosure, BuiltinFn)):
                self._call_fn(main_fn, [])
        # TODO: 审查此异常处理是否合理，避免静默吞噬异常
        except NameError:
            pass  # 没有 main 函数时忽略

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
                            return NovaADTValue(type_name, vname, list(args))

                        return constructor

                    ctor = BuiltinFn(
                        variant.name,
                        make_constructor(decl.name, variant.name, field_names),
                        len(variant.fields),
                    )
                else:
                    # 无字段构造器 -> 直接是值
                    ctor = NovaADTValue(decl.name, variant.name, [])

                self.env.define(variant.name, ctor)

        elif isinstance(decl, AliasDef):
            # 类型别名在运行时不产生值，跳过
            pass

        elif isinstance(decl, (ImportDecl, ExportDecl)):
            pass

        else:
            # 顶层表达式
            self.eval_expr(decl)

    # ----------------------------------------------------------
    # 表达式求值（调度表模式）
    # ----------------------------------------------------------

    def _build_expr_eval_dispatch_table(self) -> Dict[type, Callable]:
        """构建表达式求值调度表

        按 AST 节点类型映射到对应的求值方法，替代 if-isinstance 链。
        新增节点类型时只需在调度表中添加一条映射。
        """
        return {
            # --- 字面量 ---
            IntLiteral: self._eval_int_literal,
            FloatLiteral: self._eval_float_literal,
            StringLiteral: self._eval_string_literal,
            CharLiteral: self._eval_char_literal,
            BoolLiteral: self._eval_bool_literal,
            UnitLiteral: self._eval_unit_literal,
            # --- 标识符 ---
            Identifier: self._eval_identifier,
            # --- 运算 ---
            BinaryOp: self._eval_binary_op,
            UnaryOp: self._eval_unary_op,
            # --- 管道与错误传播 ---
            PipeExpr: self._eval_pipe_expr,
            TryExpr: self._eval_try_expr,
            # --- 函数 ---
            FnCall: self._eval_fn_call,
            Lambda: self._eval_lambda,
            # --- 控制流 ---
            IfExpr: self._eval_if_expr,
            MatchExpr: self._eval_match,
            # --- 块与绑定 ---
            Block: self._eval_block,
            LetBinding: self._eval_let_binding,
            MutBinding: self._eval_mut_binding,
            Assignment: self._eval_assignment,
            # --- 数据结构 ---
            ListExpr: self._eval_list_expr,
            ListComprehension: self._eval_list_comprehension,
            TupleExpr: self._eval_tuple_expr,
            FieldAccess: self._eval_field_access,
            # --- 循环 ---
            ForExpr: self._eval_for_expr,
            WhileExpr: self._eval_while_expr,
            BreakExpr: self._eval_break_expr,
            ContinueExpr: self._eval_continue_expr,
        }

    def eval_expr(self, expr) -> Any:
        """求值表达式并返回运行时值

        使用调度表模式分发到对应的求值方法，圈复杂度 O(1)。
        """
        handler = self._expr_dispatch.get(type(expr))
        if handler is not None:
            return handler(expr)
        raise RuntimeError_(f"未知的表达式类型: {type(expr).__name__}")

    # --- 字面量求值 ---

    def _eval_int_literal(self, expr: IntLiteral) -> Any:
        return expr.value

    def _eval_float_literal(self, expr: FloatLiteral) -> Any:
        return expr.value

    def _eval_string_literal(self, expr: StringLiteral) -> Any:
        return expr.value

    def _eval_char_literal(self, expr: CharLiteral) -> Any:
        return expr.value

    def _eval_bool_literal(self, expr: BoolLiteral) -> Any:
        return expr.value

    def _eval_unit_literal(self, expr: UnitLiteral) -> Any:
        return UNIT_VALUE

    # --- 标识符求值 ---

    def _eval_identifier(self, expr: Identifier) -> Any:
        try:
            return self.env.lookup(expr.name)
        except NameError:
            raise RuntimeError_(f"未定义的变量 '{expr.name}'")

    # --- 管道与错误传播 ---

    def _eval_pipe_expr(self, expr: PipeExpr) -> Any:
        """expr |> f  等价于 f(expr)"""
        left_val = self.eval_expr(expr.left)
        right_val = self.eval_expr(expr.right)
        return self._call_fn(right_val, [left_val])

    def _eval_try_expr(self, expr: TryExpr) -> Any:
        val = self.eval_expr(expr.expr)
        if isinstance(val, NovaADTValue):
            if val.variant_name in ("None", "Err"):
                # 简化：直接返回当前值（实际应提前返回）
                return val
        return val

    # --- 函数求值 ---

    def _eval_fn_call(self, expr: FnCall) -> Any:
        callee = self.eval_expr(expr.callee)
        args = [self.eval_expr(a) for a in expr.args]
        return self._call_fn(callee, args)

    def _eval_lambda(self, expr: Lambda) -> Any:
        return NovaClosure(
            name="<lambda>",
            params=expr.params,
            body=expr.body,
            env=self.env,
        )

    # --- 控制流求值 ---

    def _eval_if_expr(self, expr: IfExpr) -> Any:
        cond = self.eval_expr(expr.condition)
        if cond:
            return self.eval_expr(expr.then_branch)
        elif expr.else_branch:
            return self.eval_expr(expr.else_branch)
        return UNIT_VALUE

    # --- 块与绑定求值 ---

    def _eval_block(self, expr: Block) -> Any:
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

    def _eval_let_binding(self, expr: LetBinding) -> Any:
        val = self.eval_expr(expr.value)
        self.env.define(expr.name, val, mutable=False)
        return UNIT_VALUE

    def _eval_mut_binding(self, expr: MutBinding) -> Any:
        val = self.eval_expr(expr.value)
        self.env.define(expr.name, val, mutable=True)
        return UNIT_VALUE

    def _eval_assignment(self, expr: Assignment) -> Any:
        val = self.eval_expr(expr.value)
        try:
            self.env.assign(expr.name, val)
        except RuntimeError as e:
            raise RuntimeError_(str(e))
        return UNIT_VALUE

    # --- 数据结构求值 ---

    def _eval_list_expr(self, expr: ListExpr) -> Any:
        return [self.eval_expr(e) for e in expr.elements]

    def _eval_tuple_expr(self, expr: TupleExpr) -> Any:
        return tuple(self.eval_expr(e) for e in expr.elements)

    def _eval_field_access(self, expr: FieldAccess) -> Any:
        target = self.eval_expr(expr.target)
        if isinstance(target, tuple):
            try:
                idx = int(expr.field)
                return target[idx]
            except (ValueError, IndexError):
                raise RuntimeError_(f"元组索引 '{expr.field}' 越界")
        raise RuntimeError_(f"无法对值进行字段访问")

    # --- 循环求值 ---

    def _eval_break_expr(self, expr: BreakExpr) -> Any:
        raise BreakSignal()

    def _eval_continue_expr(self, expr: ContinueExpr) -> Any:
        raise ContinueSignal()

    def _eval_binary_op(self, expr: BinaryOp) -> Any:
        """求值二元操作"""
        # 短路求值
        if expr.op == "&&":
            left = self.eval_expr(expr.left)
            if not left:
                return False
            return self.eval_expr(expr.right)

        if expr.op == "||":
            left = self.eval_expr(expr.left)
            if left:
                return True
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
            return left + right  # 字符串拼接
        elif expr.op == "==":
            return left == right
        elif expr.op == "!=":
            return left != right
        elif expr.op == "<":
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
            items = list(range(start, end + 1, step))
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
            # TODO: 审查此异常处理是否合理，避免静默吞噬异常
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
            items = list(range(start, end + 1, step))
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
                # 在新作用域中绑定模式变量并求值分支
                child_env = self.env.child()
                for name, val in bindings.items():
                    child_env.define(name, val)
                old_env = self.env
                self.env = child_env
                result = self.eval_expr(arm.body)
                self.env = old_env
                return result

        raise RuntimeError_("模式匹配失败：没有匹配的分支（考虑添加 _ 通配符）")

    def _build_pattern_match_dispatch_table(self) -> Dict[type, Callable]:
        """构建模式匹配调度表

        按模式节点类型映射到对应的匹配方法，替代 if-isinstance 链。
        新增模式类型时只需在调度表中添加一条映射。
        """
        return {
            PatternWildcard: self._match_wildcard,
            PatternInt: self._match_int,
            PatternFloat: self._match_float,
            PatternString: self._match_string,
            PatternBool: self._match_bool,
            PatternChar: self._match_char,
            PatternIdentifier: self._match_identifier,
            PatternConstructor: self._match_constructor,
            PatternTuple: self._match_tuple,
            PatternList: self._match_list,
        }

    def __init__(self, check_types: bool = True):
        self.env = Environment()
        self.check_types = check_types
        self._output: List[str] = []  # 收集 print 输出
        self._expr_dispatch = self._build_expr_eval_dispatch_table()
        self._pattern_dispatch = self._build_pattern_match_dispatch_table()
        self._setup_builtins()

    def _match_pattern(self, pattern, value, bindings: Dict[str, Any]) -> bool:
        """尝试匹配模式，成功则填充 bindings

        使用调度表模式分发到对应的匹配方法，圈复杂度 O(1)。
        """
        handler = self._pattern_dispatch.get(type(pattern))
        if handler is not None:
            return handler(pattern, value, bindings)
        return False

    # --- 字面量模式匹配 ---

    def _match_wildcard(self, pattern, value, bindings: Dict[str, Any]) -> bool:
        """通配符 _ 匹配任何值"""
        return True

    def _match_int(self, pattern: PatternInt, value, bindings: Dict[str, Any]) -> bool:
        return isinstance(value, int) and value == pattern.value

    def _match_float(self, pattern: PatternFloat, value, bindings: Dict[str, Any]) -> bool:
        return isinstance(value, float) and value == pattern.value

    def _match_string(self, pattern: PatternString, value, bindings: Dict[str, Any]) -> bool:
        return isinstance(value, str) and value == pattern.value

    def _match_bool(self, pattern: PatternBool, value, bindings: Dict[str, Any]) -> bool:
        return isinstance(value, bool) and value == pattern.value

    def _match_char(self, pattern: PatternChar, value, bindings: Dict[str, Any]) -> bool:
        return isinstance(value, str) and len(value) == 1 and value == pattern.value

    def _match_identifier(self, pattern: PatternIdentifier, value, bindings: Dict[str, Any]) -> bool:
        """标识符模式绑定变量名到值"""
        bindings[pattern.name] = value
        return True

    # --- 复合模式匹配 ---

    def _match_constructor(self, pattern: PatternConstructor, value, bindings: Dict[str, Any]) -> bool:
        """ADT 构造器模式匹配，递归匹配字段"""
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

    def _match_tuple(self, pattern: PatternTuple, value, bindings: Dict[str, Any]) -> bool:
        """元组模式匹配，递归匹配元素"""
        if not isinstance(value, tuple):
            return False
        if len(pattern.elements) != len(value):
            return False
        for p, v in zip(pattern.elements, value):
            if not self._match_pattern(p, v, bindings):
                return False
        return True

    def _match_list(self, pattern: PatternList, value, bindings: Dict[str, Any]) -> bool:
        """列表模式匹配，递归匹配元素"""
        if not isinstance(value, list):
            return False
        if len(pattern.elements) != len(value):
            return False
        for p, v in zip(pattern.elements, value):
            if not self._match_pattern(p, v, bindings):
                return False
        return True
