"""
Nova 编程语言 - 栈式虚拟机

执行 BytecodeCompiler 编译生成的字节码指令序列。

VM 状态：
- stack: 操作数栈
- call_stack: 调用栈（帧包含局部变量、返回地址、基栈指针）
- globals: 全局变量
- constants: 常量池
- code: 字节码指令序列
- ip: 指令指针
- output: print 输出收集
- functions: 已编译函数的字节码块
"""

import math
import json
import os
from typing import Dict, List, Optional, Any, Callable

from nova.compiler import Bytecode, FunctionBlock, Instruction, Op
from nova.errors import RuntimeError_


# ============================================================
# 运行时值
# ============================================================

class UNIT_TYPE:
    """Unit 值单例标识"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "()"

    def __bool__(self):
        return False


UNIT = UNIT_TYPE()


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


class NovaClosure:
    """Nova 函数闭包值（VM 版）"""

    def __init__(self, func_name: str, param_count: int, captured_vars: Dict[str, Any]):
        self.func_name = func_name
        self.param_count = param_count
        self.captured_vars = captured_vars  # 闭包捕获的变量

    def __repr__(self):
        return f"<fn {self.func_name}>"


class NovaBuiltinFn:
    """内置函数（VM 版）"""

    def __init__(self, name: str, fn: Callable, arity: int = -1):
        self.name = name
        self.fn = fn
        self.arity = arity
        self._captured_args = []  # 用于部分应用

    def __repr__(self):
        return f"<builtin {self.name}>"


class NovaPartialBuiltin:
    """部分应用的内置函数"""

    def __init__(self, builtin: NovaBuiltinFn, captured_args: list):
        self.builtin = builtin
        self.captured_args = captured_args
        self.arity = builtin.arity - len(captured_args) if builtin.arity > 0 else -1

    def __repr__(self):
        return f"<partial_builtin {self.builtin.name}>"


class NovaConstructor:
    """ADT 构造函数（VM 版）"""

    def __init__(self, type_name: str, variant_name: str, field_count: int,
                 field_names: List[str] = None):
        self.type_name = type_name
        self.variant_name = variant_name
        self.field_count = field_count
        self.field_names = field_names or []

    def __repr__(self):
        return f"<ctor {self.variant_name}>"


# ============================================================
# 帧结构
# ============================================================

class Frame:
    """调用帧"""

    def __init__(self, return_ip: int, base_sp: int, code: List[Instruction],
                 constants: List[Any], locals_: Dict[str, Any], ip: int = 0):
        self.return_ip = return_ip
        self.base_sp = base_sp
        self.code = code
        self.constants = constants
        self.locals = locals_
        self.ip = ip


# ============================================================
# 虚拟机
# ============================================================

class NovaVM:
    """Nova 栈式虚拟机"""

    MAX_CALL_DEPTH = 1000  # 栈溢出保护

    def __init__(self, bytecode: Bytecode):
        self.bytecode = bytecode
        self.stack: List[Any] = []
        self.call_stack: List[Frame] = []
        self.globals: Dict[str, Any] = {}
        self.constants: List[Any] = bytecode.constants
        self.code: List[Instruction] = bytecode.code
        self.functions: Dict[str, FunctionBlock] = dict(bytecode.functions)
        self.ip = 0
        self.output: List[str] = []

        # 循环控制：用于 for 循环的迭代状态
        self._for_iters: List[Dict] = []

        # 循环控制：用于 while 循环的状态
        self._while_loops: List[Dict] = []

        # 循环控制：唯一循环 ID 计数器，替代 id() 作为迭代键
        self._loop_id = 0

        # RETURN 语义：标记提前返回
        self.return_flag = False

        # 初始化内置函数
        self._setup_builtins()

    def _setup_builtins(self):
        """注册内置函数到全局"""
        self.globals["print"] = NovaBuiltinFn("print", self._builtin_print, 1)
        self.globals["read_line"] = NovaBuiltinFn("read_line", lambda *a: input() if a == () else "", 0)
        self.globals["int_to_str"] = NovaBuiltinFn("int_to_str", lambda *a: str(a[0]), 1)
        self.globals["float_to_str"] = NovaBuiltinFn("float_to_str", lambda *a: str(a[0]), 1)
        self.globals["str_to_int"] = NovaBuiltinFn("str_to_int", self._builtin_str_to_int, 1)
        self.globals["str_len"] = NovaBuiltinFn("str_len", lambda *a: len(a[0]), 1)
        self.globals["list_length"] = NovaBuiltinFn("list_length", lambda *a: len(a[0]), 1)
        self.globals["filter"] = NovaBuiltinFn("filter", self._builtin_filter, 2)
        self.globals["map"] = NovaBuiltinFn("map", self._builtin_map, 2)
        self.globals["sum"] = NovaBuiltinFn("sum", lambda *a: sum(a[0]), 1)
        self.globals["head"] = NovaBuiltinFn("head", self._builtin_head, 1)
        self.globals["tail"] = NovaBuiltinFn("tail", self._builtin_tail, 1)

        # 文件 I/O
        self.globals["read_file"] = NovaBuiltinFn("read_file", self._builtin_read_file, 1)
        self.globals["write_file"] = NovaBuiltinFn("write_file", self._builtin_write_file, 2)
        self.globals["file_exists"] = NovaBuiltinFn("file_exists", lambda *a: os.path.exists(a[0]), 1)
        self.globals["list_dir"] = NovaBuiltinFn("list_dir", self._builtin_list_dir, 1)

        # JSON
        self.globals["json_parse"] = NovaBuiltinFn("json_parse", self._builtin_json_parse, 1)
        self.globals["json_stringify"] = NovaBuiltinFn("json_stringify", self._builtin_json_stringify, 1)

        # 数学函数
        self.globals["abs"] = NovaBuiltinFn("abs", lambda *a: abs(self._to_float(a[0])), 1)
        self.globals["sqrt"] = NovaBuiltinFn("sqrt", lambda *a: math.sqrt(self._to_float(a[0])), 1)
        self.globals["pow"] = NovaBuiltinFn("pow", lambda *a: math.pow(self._to_float(a[0]), self._to_float(a[1])), 2)
        self.globals["log"] = NovaBuiltinFn("log", lambda *a: math.log(self._to_float(a[0])), 1)
        self.globals["log10"] = NovaBuiltinFn("log10", lambda *a: math.log10(self._to_float(a[0])), 1)
        self.globals["exp"] = NovaBuiltinFn("exp", lambda *a: math.exp(self._to_float(a[0])), 1)
        self.globals["sin"] = NovaBuiltinFn("sin", lambda *a: math.sin(self._to_float(a[0])), 1)
        self.globals["cos"] = NovaBuiltinFn("cos", lambda *a: math.cos(self._to_float(a[0])), 1)
        self.globals["tan"] = NovaBuiltinFn("tan", lambda *a: math.tan(self._to_float(a[0])), 1)
        self.globals["floor"] = NovaBuiltinFn("floor", lambda *a: float(math.floor(self._to_float(a[0]))), 1)
        self.globals["ceil"] = NovaBuiltinFn("ceil", lambda *a: float(math.ceil(self._to_float(a[0]))), 1)
        self.globals["round"] = NovaBuiltinFn("round", lambda *a: float(round(self._to_float(a[0]))), 1)
        self.globals["min"] = NovaBuiltinFn("min", lambda *a: float(min(self._to_float(a[0]), self._to_float(a[1]))), 2)
        self.globals["max"] = NovaBuiltinFn("max", lambda *a: float(max(self._to_float(a[0]), self._to_float(a[1]))), 2)
        self.globals["pi"] = NovaBuiltinFn("pi", lambda *a: math.pi, 0)

    def _to_float(self, val):
        if isinstance(val, int) and not isinstance(val, bool):
            return float(val)
        return val

    # 内置函数实现

    def _builtin_print(self, *args):
        val = self._format_value(args[0])
        print(val)
        self.output.append(val)
        return UNIT

    def _builtin_str_to_int(self, *args):
        try:
            return NovaADTValue("Option", "Some", [int(args[0])], ["value"])
        except ValueError:
            return NovaADTValue("Option", "None", [], [])

    def _builtin_filter(self, *args):
        pred_fn, lst = args[0], args[1]
        return [item for item in lst if self._call_fn(pred_fn, [item]) is True]

    def _builtin_map(self, *args):
        map_fn, lst = args[0], args[1]
        return [self._call_fn(map_fn, [item]) for item in lst]

    def _builtin_head(self, *args):
        lst = args[0]
        if lst:
            return NovaADTValue("Option", "Some", [lst[0]], ["value"])
        return NovaADTValue("Option", "None", [], [])

    def _builtin_tail(self, *args):
        lst = args[0]
        if len(lst) > 0:
            return NovaADTValue("Option", "Some", [lst[1:]], ["value"])
        return NovaADTValue("Option", "None", [], [])

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
            return UNIT
        except IOError as e:
            raise RuntimeError_(f"写入文件 '{path}' 失败: {e}")

    def _builtin_list_dir(self, *args):
        path = args[0]
        try:
            return sorted(os.listdir(path))
        except OSError as e:
            raise RuntimeError_(f"列出目录 '{path}' 失败: {e}")

    def _builtin_json_parse(self, *args):
        text = args[0]
        try:
            result = json.loads(text)
            return self._convert_json_to_nova(result)
        except json.JSONDecodeError as e:
            raise RuntimeError_(f"JSON 解析失败: {e}")

    def _convert_json_to_nova(self, val):
        if val is None:
            return NovaADTValue("Option", "None", [], [])
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return val
        if isinstance(val, str):
            return val
        if isinstance(val, list):
            return [self._convert_json_to_nova(item) for item in val]
        if isinstance(val, dict):
            return {k: self._convert_json_to_nova(v) for k, v in val.items()}
        return val

    def _builtin_json_stringify(self, *args):
        val = args[0]
        try:
            return json.dumps(self._convert_nova_to_json(val))
        except (TypeError, ValueError) as e:
            raise RuntimeError_(f"JSON 序列化失败: {e}")

    def _convert_nova_to_json(self, val):
        if val is UNIT:
            return None
        if isinstance(val, NovaADTValue):
            if val.variant_name == "None":
                return None
            if val.variant_name == "Some" and len(val.fields) == 1:
                return self._convert_nova_to_json(val.fields[0])
            if val.variant_name == "Ok" and len(val.fields) == 1:
                return self._convert_nova_to_json(val.fields[0])
            return {"_type": val.type_name, "_variant": val.variant_name,
                    "_fields": [self._convert_nova_to_json(f) for f in val.fields]}
        if isinstance(val, list):
            return [self._convert_nova_to_json(item) for item in val]
        if isinstance(val, tuple):
            return [self._convert_nova_to_json(item) for item in val]
        if isinstance(val, dict):
            return {str(k): self._convert_nova_to_json(v) for k, v in val.items()}
        return val

    def _format_value(self, val) -> str:
        if val is UNIT:
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
        if isinstance(val, (NovaClosure, NovaBuiltinFn, NovaConstructor)):
            return repr(val)
        return str(val)

    # ----------------------------------------------------------
    # 函数调用
    # ----------------------------------------------------------

    def _call_fn(self, fn, args: List[Any]) -> Any:
        """调用函数（支持闭包、内置函数、构造函数，支持部分应用/柯里化）"""
        if isinstance(fn, NovaBuiltinFn):
            # 部分应用支持
            if fn.arity > 0 and len(args) < fn.arity:
                partial = NovaPartialBuiltin(fn, list(args))
                return partial
            return fn.fn(*args)

        if isinstance(fn, NovaPartialBuiltin):
            all_args = fn.captured_args + list(args)
            if fn.arity > 0 and len(all_args) < fn.builtin.arity:
                partial = NovaPartialBuiltin(fn.builtin, all_args)
                return partial
            return fn.builtin.fn(*all_args)

        if isinstance(fn, NovaConstructor):
            if len(args) != fn.field_count:
                raise RuntimeError_(
                    f"构造器 '{fn.variant_name}' 期望 {fn.field_count} 个参数，但传入了 {len(args)} 个"
                )
            return NovaADTValue(fn.type_name, fn.variant_name, list(args), fn.field_names)

        if isinstance(fn, NovaClosure):
            # 部分应用支持：参数不足时返回捕获已提供参数的闭包
            if len(args) < fn.param_count:
                captured = dict(fn.captured_vars)
                # 获取函数参数名用于绑定已捕获参数
                func_block = self.functions.get(fn.func_name)
                if func_block is None:
                    raise RuntimeError_(f"未找到函数 '{fn.func_name}'")
                # 已捕获的参数数量 = 总形参数 - 当前剩余参数
                total_params = len(func_block.param_names)
                already_bound = total_params - fn.param_count
                # 将新提供的参数绑定到捕获变量中
                for i, arg in enumerate(args):
                    param_idx = already_bound + i
                    if param_idx < total_params:
                        captured[func_block.param_names[param_idx]] = arg
                remaining_count = fn.param_count - len(args)
                return NovaClosure(
                    func_name=fn.func_name,
                    param_count=remaining_count,
                    captured_vars=captured,
                )
            return self._call_closure(fn, args)

        raise RuntimeError_(f"无法调用非函数值: {fn}")

    def _call_closure(self, closure: NovaClosure, args: List[Any]) -> Any:
        """调用闭包"""
        if len(self.call_stack) >= self.MAX_CALL_DEPTH:
            raise RuntimeError_("栈溢出：调用深度超过限制")

        func_block = self.functions.get(closure.func_name)
        if func_block is None:
            raise RuntimeError_(f"未找到函数 '{closure.func_name}'")

        # 参数数量校验
        if len(args) > closure.param_count:
            raise RuntimeError_(
                f"函数 '{closure.func_name}' 期望 {closure.param_count} 个参数，但传入了 {len(args)} 个"
            )

        # 合并捕获变量和参数
        locals_ = dict(closure.captured_vars)
        # 计算已绑定的参数数量（总参数 - 剩余参数）
        total_params = len(func_block.param_names)
        already_bound = total_params - closure.param_count
        for i, arg in enumerate(args):
            param_idx = already_bound + i
            locals_[func_block.param_names[param_idx]] = arg

        # 保存当前帧
        frame = Frame(
            return_ip=self.ip,
            base_sp=len(self.stack),  # 保存调用前的栈位置
            code=self.code,
            constants=self.constants,
            locals_=locals_,
            ip=self.ip,
        )
        self.call_stack.append(frame)

        # 切换到函数代码
        self.code = func_block.code
        self.constants = func_block.constants
        self.ip = 0

        self.return_flag = False
        try:
            # 执行函数
            result = self._execute_function()
        finally:
            # 恢复帧
            self.call_stack.pop()
            self.code = frame.code
            self.constants = frame.constants
            self.ip = frame.return_ip
            # 在函数返回后截断栈到调用前状态
            if len(self.stack) > frame.base_sp:
                del self.stack[frame.base_sp:]

        return result

    def _execute_function(self) -> Any:
        """执行当前代码直到 RETURN"""
        while self.ip < len(self.code) and not self.return_flag:
            instr = self.code[self.ip]
            opcode = instr.opcode

            if opcode == Op.RETURN:
                # Stack: [value] -> [] (within function execution)
                # Pop return value and return from function execution
                result = self.stack.pop() if self.stack else UNIT
                return result

            if self._execute_instruction(instr):
                # Early return triggered by TRY_UNWRAP
                return self.stack[-1] if self.stack else UNIT

        if self.return_flag:
            self.return_flag = False
            return self.stack.pop() if self.stack else UNIT

        return UNIT

    # ----------------------------------------------------------
    # 主执行循环
    # ----------------------------------------------------------

    def run(self):
        """执行主代码"""
        self._run_code(self.code, self.constants)
        # 自动调用 main
        self._auto_call_main()

    def _auto_call_main(self):
        """自动调用 main() 函数"""
        main_fn = self.globals.get("main")
        if main_fn is not None and isinstance(main_fn, (NovaClosure, NovaBuiltinFn)):
            self._call_fn(main_fn, [])

    def _run_code(self, code: List[Instruction], constants: List[Any]):
        """执行给定的代码序列"""
        saved_code = self.code
        saved_constants = self.constants
        saved_ip = self.ip

        self.code = code
        self.constants = constants
        self.ip = 0
        self.return_flag = False

        try:
            while self.ip < len(self.code) and not self.return_flag:
                instr = self.code[self.ip]
                opcode = instr.opcode

                if opcode == Op.HALT:
                    # Stack: unchanged
                    # Halt execution of current code sequence
                    break

                if opcode == Op.AUTO_CALL_MAIN:
                    # Stack: unchanged
                    # Marker for auto-calling main (handled in run()); stop execution
                    break

                if self._execute_instruction(instr):
                    # Early return triggered by TRY_UNWRAP in top-level code
                    break
        finally:
            self.code = saved_code
            self.constants = saved_constants
            self.ip = saved_ip
            self.return_flag = False

    def _pop(self, n=1):
        if len(self.stack) < n:
            raise RuntimeError_(f"VM stack underflow: need {n}, have {len(self.stack)}")
        if n == 0:
            return []
        return [self.stack.pop() for _ in range(n)][::-1]

    def _execute_instruction(self, instr: Instruction) -> bool:
        """执行单条指令，返回 True 表示需要提前返回"""
        opcode = instr.opcode
        self.ip += 1

        # === 常量与加载 ===
        if opcode == Op.CONST_INT:
            # Stack: [] -> [value]
            # Push integer constant onto stack
            self.stack.append(instr.operands[0])

        elif opcode == Op.CONST_FLOAT:
            # Stack: [] -> [value]
            # Push float constant onto stack
            self.stack.append(instr.operands[0])

        elif opcode == Op.CONST_STRING:
            # Stack: [] -> [value]
            # Push string constant onto stack
            self.stack.append(instr.operands[0])

        elif opcode == Op.CONST_BOOL:
            # Stack: [] -> [value]
            # Push boolean constant onto stack
            self.stack.append(instr.operands[0])

        elif opcode == Op.CONST_UNIT:
            # Stack: [] -> [()]
            # Push Unit value onto stack
            self.stack.append(UNIT)

        elif opcode == Op.LOAD_CONST:
            # Stack: [] -> [constant]
            # Load constant from constants pool by index
            idx = instr.operands[0]
            self.stack.append(self.constants[idx])

        elif opcode == Op.LOAD_VAR:
            # Stack: [] -> [value]
            # Load variable value onto stack (local first, then global)
            name = instr.operands[0]
            if self.call_stack:
                frame = self.call_stack[-1]
                if name in frame.locals:
                    self.stack.append(frame.locals[name])
                    return
            if name in self.globals:
                self.stack.append(self.globals[name])
            else:
                raise RuntimeError_(f"未定义的变量 '{name}'")

        elif opcode == Op.STORE_VAR:
            # Stack: [value] -> []
            # Pop value and store into variable (local first, then global)
            name = instr.operands[0]
            mutable = instr.operands[1]
            val = self._pop()[0]
            if self.call_stack:
                frame = self.call_stack[-1]
                if name in frame.locals:
                    if not mutable:
                        raise RuntimeError_(f"Cannot assign to immutable variable '{name}'")
                    frame.locals[name] = val
                    return
            self.globals[name] = val

        # === 运算 ===
        elif opcode == Op.ADD:
            # Stack: [a, b] -> [a+b]
            # Pop two values, add them, push result
            a, b = self._pop(2)
            if isinstance(a, bool) or isinstance(b, bool):
                raise RuntimeError_("算术运算 '+' 的操作数不能是 Bool 类型")
            self.stack.append(a + b)

        elif opcode == Op.SUB:
            # Stack: [a, b] -> [a-b]
            # Pop two values, subtract them, push result
            a, b = self._pop(2)
            if isinstance(a, bool) or isinstance(b, bool):
                raise RuntimeError_("算术运算 '-' 的操作数不能是 Bool 类型")
            self.stack.append(a - b)

        elif opcode == Op.MUL:
            # Stack: [a, b] -> [a*b]
            # Pop two values, multiply them, push result
            a, b = self._pop(2)
            if isinstance(a, bool) or isinstance(b, bool):
                raise RuntimeError_("算术运算 '*' 的操作数不能是 Bool 类型")
            self.stack.append(a * b)

        elif opcode == Op.DIV:
            # Stack: [a, b] -> [a/b]
            # Pop two values, divide them, push result
            a, b = self._pop(2)
            if isinstance(a, bool) or isinstance(b, bool):
                raise RuntimeError_("算术运算 '/' 的操作数不能是 Bool 类型")
            try:
                if isinstance(a, int) and isinstance(b, int):
                    self.stack.append(a // b)
                else:
                    self.stack.append(a / b)
            except ZeroDivisionError:
                raise RuntimeError_("除零错误")

        elif opcode == Op.MOD:
            # Stack: [a, b] -> [a%b]
            # Pop two values, compute modulo, push result
            a, b = self._pop(2)
            if isinstance(a, bool) or isinstance(b, bool):
                raise RuntimeError_("算术运算 '%' 的操作数不能是 Bool 类型")
            try:
                self.stack.append(a % b)
            except ZeroDivisionError:
                raise RuntimeError_("除零错误")

        elif opcode == Op.NEG:
            # Stack: [a] -> [-a]
            # Pop value, negate it, push result
            a = self._pop()[0]
            if isinstance(a, bool):
                raise RuntimeError_("算术运算 '-' 的操作数不能是 Bool 类型")
            self.stack.append(-a)

        elif opcode == Op.CONCAT:
            # Stack: [a, b] -> [a++b]
            # 仅允许 str 类型拼接
            a, b = self._pop(2)
            if isinstance(a, str) and isinstance(b, str):
                self.stack.append(a + b)
            else:
                raise RuntimeError_("类型错误：操作符 '++' 只能用于 String 类型")

        elif opcode == Op.EQ:
            # Stack: [a, b] -> [a==b]
            # Pop two values, compare equality, push boolean result
            # Nova 中 Bool 和 Int 是不同类型：bool 与非 bool 比较永远不相等
            a, b = self._pop(2)
            if isinstance(a, bool) != isinstance(b, bool):
                self.stack.append(False)
            else:
                self.stack.append(a == b)

        elif opcode == Op.NEQ:
            # Stack: [a, b] -> [a!=b]
            # Pop two values, compare inequality, push boolean result
            a, b = self._pop(2)
            if isinstance(a, bool) != isinstance(b, bool):
                self.stack.append(True)
            else:
                self.stack.append(a != b)

        elif opcode == Op.LT:
            # Stack: [a, b] -> [a<b]
            # Pop two values, compare less-than, push boolean result
            a, b = self._pop(2)
            if isinstance(a, bool) != isinstance(b, bool):
                raise RuntimeError_("类型错误：Bool 不能与非 Bool 类型进行比较")
            self.stack.append(a < b)

        elif opcode == Op.GT:
            # Stack: [a, b] -> [a>b]
            # Pop two values, compare greater-than, push boolean result
            a, b = self._pop(2)
            if isinstance(a, bool) != isinstance(b, bool):
                raise RuntimeError_("类型错误：Bool 不能与非 Bool 类型进行比较")
            self.stack.append(a > b)

        elif opcode == Op.LTE:
            # Stack: [a, b] -> [a<=b]
            # Pop two values, compare less-than-or-equal, push boolean result
            a, b = self._pop(2)
            if isinstance(a, bool) != isinstance(b, bool):
                raise RuntimeError_("类型错误：Bool 不能与非 Bool 类型进行比较")
            self.stack.append(a <= b)

        elif opcode == Op.GTE:
            # Stack: [a, b] -> [a>=b]
            # Pop two values, compare greater-than-or-equal, push boolean result
            a, b = self._pop(2)
            if isinstance(a, bool) != isinstance(b, bool):
                raise RuntimeError_("类型错误：Bool 不能与非 Bool 类型进行比较")
            self.stack.append(a >= b)

        elif opcode == Op.AND:
            # Stack: [a, b] -> [a and b]
            # Pop two boolean values, compute logical AND, push result
            # Note: short-circuit is handled by POP_JUMP_IF_FALSE in compilation
            a, b = self._pop(2)
            if not isinstance(a, bool) or not isinstance(b, bool):
                raise RuntimeError_("逻辑操作数必须是 Bool 类型")
            self.stack.append(a and b)

        elif opcode == Op.OR:
            # Stack: [a, b] -> [a or b]
            # Pop two boolean values, compute logical OR, push result
            a, b = self._pop(2)
            if not isinstance(a, bool) or not isinstance(b, bool):
                raise RuntimeError_("逻辑操作数必须是 Bool 类型")
            self.stack.append(a or b)

        elif opcode == Op.NOT:
            # Stack: [a] -> [not a]
            # Pop boolean value, compute logical NOT, push result
            a = self._pop()[0]
            if not isinstance(a, bool):
                raise RuntimeError_("逻辑操作数必须是 Bool 类型")
            self.stack.append(not a)

        # === 控制流 ===
        elif opcode == Op.JUMP:
            # Stack: unchanged
            # Unconditional jump to target_ip
            target = instr.operands[0]
            # 检测 while 循环回跳: JUMP 目标在前面，且下一条指令是 CONST_UNIT
            if target < self.ip and self.ip < len(self.code) and self.code[self.ip].opcode == Op.CONST_UNIT:
                if self._while_loops:
                    self._while_loops[-1]["loop_start"] = target
            self.ip = target

        elif opcode == Op.JUMP_IF_FALSE:
            # Stack: [cond] -> []
            # Pop condition; if false, jump to target_ip
            cond = self._pop()[0]
            if not isinstance(cond, bool):
                raise RuntimeError_("条件必须是 Bool 类型")
            if not cond:
                self.ip = instr.operands[0]

        elif opcode == Op.JUMP_IF_TRUE:
            # Stack: [cond] -> []
            # Pop condition; if true, jump to target_ip
            cond = self._pop()[0]
            if not isinstance(cond, bool):
                raise RuntimeError_("条件必须是 Bool 类型")
            if cond:
                self.ip = instr.operands[0]

        elif opcode == Op.POP_JUMP_IF_FALSE:
            # Stack: [cond] -> []
            # Pop condition; if false, jump to target_ip
            cond = self._pop()[0]
            if not isinstance(cond, bool):
                raise RuntimeError_("条件必须是 Bool 类型")
            if not cond:
                # 退出 while 循环，弹出循环信息
                if self._while_loops and self._while_loops[-1]["end_ip"] == instr.operands[0]:
                    self._while_loops.pop()
                self.ip = instr.operands[0]
            else:
                # 进入 while 循环体，记录循环信息（如果尚未记录）
                end_ip = instr.operands[0]
                if not (self._while_loops and self._while_loops[-1]["end_ip"] == end_ip):
                    self._while_loops.append({
                        "end_ip": end_ip,
                        "base_sp": len(self.stack),
                        "loop_start": None,
                    })

        elif opcode == Op.LOOP_END:
            # Stack: [iterable, result_list, body_result] -> [iterable, result_list]
            # Pop body_result, append it to result_list, push iterable and updated result_list,
            # then jump back to loop_start for next iteration
            loop_start = instr.operands[0]
            iterable, result_list, body_result = self._pop(3)
            result_list.append(body_result)
            self.stack.append(iterable)
            self.stack.append(result_list)
            self.ip = loop_start

        elif opcode == Op.BREAK:
            # Stack: [*] -> [result_list or unit]
            # Break out of current loop
            if instr.operands:
                # while 循环中的 BREAK：操作数为 end_pos
                # 清理循环体栈上残留的中间值，并弹出 _while_loops 条目
                if self._while_loops:
                    loop_info = self._while_loops.pop()
                    base_sp = loop_info["base_sp"]
                    if base_sp < len(self.stack):
                        del self.stack[base_sp:]
                self.ip = instr.operands[0]
            elif self._for_iters:
                loop_info = self._for_iters.pop()
                end_ip = loop_info["end_ip"]
                base_sp = loop_info["base_sp"]
                iter_type = loop_info.get("iter_type")
                iter_key = loop_info.get("iter_key")
                if iter_type == "range" and hasattr(self, '_range_index'):
                    self._range_index.pop(iter_key, None)
                elif iter_type == "list" and hasattr(self, '_list_index'):
                    self._list_index.pop(iter_key, None)
                result_list = self.stack[base_sp + 1]
                del self.stack[base_sp:]
                self.stack.append(result_list)
                self.ip = end_ip
            else:
                # while loop break fallback (无操作数的旧代码路径)：前向扫描
                while self.ip < len(self.code):
                    next_instr = self.code[self.ip]
                    if next_instr.opcode in (Op.LOOP_END, Op.CONST_UNIT):
                        self.ip += 1
                        break
                    self.ip += 1

        elif opcode == Op.CONTINUE:
            # Stack: [iterable, result_list, ...body_values] -> [iterable, result_list]
            # Continue to next iteration: clean body values and jump back to loop start
            if self._for_iters:
                loop_info = self._for_iters[-1]
                base_sp = loop_info["base_sp"]
                loop_start = loop_info["loop_start"]
                del self.stack[base_sp + 2:]
                self.ip = loop_start
            else:
                # while loop continue: clean stack and jump back to condition check
                if self._while_loops:
                    loop_info = self._while_loops[-1]
                    base_sp = loop_info["base_sp"]
                    # 优先使用编译器提供的操作数（loop_start），解决首次迭代 loop_start 为 None 的崩溃
                    if instr.operands:
                        loop_start = instr.operands[0]
                    else:
                        loop_start = loop_info["loop_start"]
                    # 清理栈上循环体产生的值
                    if base_sp < len(self.stack):
                        del self.stack[base_sp:]
                    self.ip = loop_start

        # === 函数 ===
        elif opcode == Op.CLOSURE:
            # Stack: [] -> [closure]
            # Create a closure capturing current frame locals, push it onto stack
            func_name = instr.operands[0]
            param_count = instr.operands[1]
            captured = {}
            if self.call_stack:
                captured = dict(self.call_stack[-1].locals)
            closure = NovaClosure(func_name, param_count, captured)
            self.stack.append(closure)

        elif opcode == Op.CALL:
            # Stack: [fn, arg1, ..., argN] -> [result]
            # Pop function and arguments, call function, push result
            arg_count = instr.operands[0]
            args = self._pop(arg_count)
            fn = self._pop()[0]
            result = self._call_fn(fn, args)
            self.stack.append(result)

        elif opcode == Op.RETURN:
            # Stack: [value] -> [value]
            # Save return value back to stack and set return_flag to signal early exit
            result = self.stack.pop() if self.stack else UNIT
            self.stack.append(result)
            self.return_flag = True

        elif opcode == Op.CALL_BUILTIN:
            # Stack: [arg1, ..., argN] -> [result]
            # Pop arguments, call builtin function, push result
            name = instr.operands[0]
            arg_count = instr.operands[1]
            args = self._pop(arg_count)
            builtin = self.globals.get(name)
            if builtin is None:
                raise RuntimeError_(f"未找到内置函数 '{name}'")
            result = self._call_fn(builtin, args)
            self.stack.append(result)

        # === 数据结构 ===
        elif opcode == Op.BUILD_LIST:
            # Stack: [elem1, ..., elemN] -> [list]
            # Pop N elements, build list, push it
            count = instr.operands[0]
            elements = self._pop(count)
            self.stack.append(elements)

        elif opcode == Op.BUILD_TUPLE:
            # Stack: [elem1, ..., elemN] -> [tuple]
            # Pop N elements, build tuple, push it
            count = instr.operands[0]
            elements = self._pop(count)
            self.stack.append(tuple(elements))

        elif opcode == Op.BUILD_MAP:
            # Stack: [key1, val1, ..., keyN, valN] -> [map]
            # Pop N key-value pairs, build map, push it
            count = instr.operands[0]
            result = {}
            pairs = self._pop(count * 2)
            for i in range(0, len(pairs), 2):
                key = pairs[i]
                val = pairs[i + 1]
                result[key] = val
            self.stack.append(result)

        elif opcode == Op.INDEX:
            # Stack: [obj, index] -> [obj[index]]
            # Pop object and index, push indexed value
            obj, index = self._pop(2)
            try:
                self.stack.append(obj[index])
            except IndexError:
                raise RuntimeError_("索引越界")
            except KeyError:
                raise RuntimeError_(f"键不存在: {index}")
            except TypeError as e:
                raise RuntimeError_(f"索引操作类型错误: {e}")

        elif opcode == Op.FIELD_ACCESS:
            # Stack: [obj] -> [obj.field]
            # Pop object, push field value (by index or name)
            field = instr.operands[0]
            obj = self._pop()[0]
            if isinstance(obj, tuple):
                self.stack.append(obj[int(field)])
            elif isinstance(obj, NovaADTValue):
                try:
                    idx = int(field)
                    self.stack.append(obj.fields[idx])
                except ValueError:
                    found = False
                    for i, fname in enumerate(obj.field_names):
                        if fname == field:
                            self.stack.append(obj.fields[i])
                            found = True
                            break
                    if not found:
                        raise RuntimeError_(f"ADT 值没有字段 '{field}'")
            else:
                raise RuntimeError_(f"无法对值进行字段访问 '{field}'")

        elif opcode == Op.BUILD_RANGE:
            # Stack: [start, end, step] -> [range_tuple]
            # Pop start, end, step, build range tuple ("range", start, end, step)
            start, end, step = self._pop(3)
            self.stack.append(("range", start, end, step))

        elif opcode == Op.FOR_ITER:
            # Stack: [iterable, result_list] -> [iterable, result_list, current] (has next)
            #                           -> [result_list] (exhausted)
            # Iterate one step; if exhausted, jump to fail_ip leaving result_list on stack
            fail_ip = instr.operands[0]
            iter_val, result_list = self._pop(2)

            if isinstance(iter_val, tuple) and iter_val[0] == "range":
                # 范围迭代
                if not hasattr(self, '_range_index'):
                    self._range_index = {}

                # 复用已有循环 ID 或分配新的
                if self._for_iters and self._for_iters[-1].get("loop_start") == self.ip - 1:
                    key = self._for_iters[-1]["iter_key"]
                    is_first = False
                else:
                    key = self._loop_id
                    self._loop_id += 1
                    is_first = True
                    self._range_index[key] = iter_val[1]  # start

                current = self._range_index[key]
                end = iter_val[2]
                step = iter_val[3]

                if (step > 0 and current <= end) or (step < 0 and current >= end):
                    self._range_index[key] = current + step
                    # 栈: [iterable, result_list, current_element]
                    self.stack.append(iter_val)
                    self.stack.append(result_list)
                    self.stack.append(current)
                    # 第一次迭代：注册循环状态
                    if is_first:
                        # base_sp: 循环状态之前的栈深度（iterable 和 result_list 下面）
                        base_sp = len(self.stack) - 3
                        self._for_iters.append({
                            "end_ip": fail_ip,
                            "loop_start": self.ip - 1,  # FOR_ITER 指令位置
                            "base_sp": base_sp,
                            "iter_type": "range",
                            "iter_key": key,
                        })
                else:
                    del self._range_index[key]
                    # 迭代结束，只保留结果列表
                    if self._for_iters:
                        self._for_iters.pop()
                    self.stack.append(result_list)
                    self.ip = fail_ip
                    return
            elif isinstance(iter_val, list):
                # 列表迭代
                if not hasattr(self, '_list_index'):
                    self._list_index = {}

                # 复用已有循环 ID 或分配新的
                if self._for_iters and self._for_iters[-1].get("loop_start") == self.ip - 1:
                    key = self._for_iters[-1]["iter_key"]
                    is_first = False
                else:
                    key = self._loop_id
                    self._loop_id += 1
                    is_first = True
                    self._list_index[key] = 0

                idx = self._list_index[key]
                if idx < len(iter_val):
                    self._list_index[key] = idx + 1
                    # 栈: [iterable, result_list, current_element]
                    self.stack.append(iter_val)
                    self.stack.append(result_list)
                    self.stack.append(iter_val[idx])
                    # 第一次迭代：注册循环状态
                    if is_first:
                        base_sp = len(self.stack) - 3
                        self._for_iters.append({
                            "end_ip": fail_ip,
                            "loop_start": self.ip - 1,
                            "base_sp": base_sp,
                            "iter_type": "list",
                            "iter_key": key,
                        })
                else:
                    del self._list_index[key]
                    # 迭代结束，只保留结果列表
                    if self._for_iters:
                        self._for_iters.pop()
                    self.stack.append(result_list)
                    self.ip = fail_ip
                    return
            else:
                raise RuntimeError_(f"无法迭代的值: {type(iter_val)}")

        # === 模式匹配 ===
        elif opcode == Op.MATCH_START:
            # Stack: unchanged
            # Marker for match expression start
            pass

        elif opcode == Op.MATCH_TEST_INT:
            # Stack: [subject] -> [] (match success) or [subject] (match fail)
            # Peek subject; if int and equals test_val, pop it; else jump to fail_ip
            test_val = instr.operands[0]
            fail_ip = instr.operands[1]
            if not self.stack:
                raise RuntimeError_("VM stack underflow: MATCH_TEST_INT")
            subject = self.stack[-1]
            if isinstance(subject, int) and not isinstance(subject, bool) and subject == test_val:
                self._pop()
            else:
                self.ip = fail_ip

        elif opcode == Op.MATCH_TEST_BOOL:
            # Stack: [subject] -> [] (match success) or [subject] (match fail)
            # Peek subject; if bool and equals test_val, pop it; else jump to fail_ip
            test_val = instr.operands[0]
            fail_ip = instr.operands[1]
            if not self.stack:
                raise RuntimeError_("VM stack underflow: MATCH_TEST_BOOL")
            subject = self.stack[-1]
            if isinstance(subject, bool) and subject == test_val:
                self._pop()
            else:
                self.ip = fail_ip

        elif opcode == Op.MATCH_TEST_STRING:
            # Stack: [subject] -> [] (match success) or [subject] (match fail)
            # Peek subject; if string and equals test_val, pop it; else jump to fail_ip
            test_val = instr.operands[0]
            fail_ip = instr.operands[1]
            if not self.stack:
                raise RuntimeError_("VM stack underflow: MATCH_TEST_STRING")
            subject = self.stack[-1]
            if isinstance(subject, str) and subject == test_val:
                self._pop()
            else:
                self.ip = fail_ip

        elif opcode == Op.MATCH_TEST_FLOAT:
            # Stack: [subject] -> [] (match success) or [subject] (match fail)
            # Peek subject; if float and equals test_val, pop it; else jump to fail_ip
            test_val = instr.operands[0]
            fail_ip = instr.operands[1]
            if not self.stack:
                raise RuntimeError_("VM stack underflow: MATCH_TEST_FLOAT")
            subject = self.stack[-1]
            if isinstance(subject, float) and subject == test_val:
                self._pop()
            else:
                self.ip = fail_ip

        elif opcode == Op.MATCH_TEST_CHAR:
            # Stack: [subject] -> [] (match success) or [subject] (match fail)
            # Peek subject; if string (char) and equals test_val, pop it; else jump to fail_ip
            test_val = instr.operands[0]
            fail_ip = instr.operands[1]
            if not self.stack:
                raise RuntimeError_("VM stack underflow: MATCH_TEST_CHAR")
            subject = self.stack[-1]
            if isinstance(subject, str) and len(subject) == 1 and subject == test_val:
                self._pop()
            else:
                self.ip = fail_ip

        elif opcode == Op.MATCH_WILDCARD:
            # Stack: [subject] -> []
            # Always matches; pop subject from stack
            self._pop()

        elif opcode == Op.MATCH_BIND:
            # Stack: [val] -> []
            # Pop value and bind it to variable name in current scope
            name = instr.operands[0]
            val = self._pop()[0]
            if self.call_stack:
                self.call_stack[-1].locals[name] = val
            else:
                self.globals[name] = val

        elif opcode == Op.MATCH_CONSTRUCTOR:
            # Stack: [subject] -> [field1, ..., fieldN] (match success)
            #      or [subject] (match fail)
            # Peek subject; if ADT with matching constructor and field count,
            # pop subject and push fields; else jump to fail_ip
            ctor_name = instr.operands[0]
            field_count = instr.operands[1]
            fail_ip = instr.operands[2]
            if not self.stack:
                raise RuntimeError_("VM 错误: MATCH_CONSTRUCTOR 需要栈顶有匹配对象")
            subject = self.stack[-1]
            if (isinstance(subject, NovaADTValue) and
                    subject.variant_name == ctor_name and
                    len(subject.fields) == field_count):
                self._pop()
                for field_val in reversed(subject.fields):
                    self.stack.append(field_val)
            else:
                self.ip = fail_ip

        elif opcode == Op.MATCH_TEST_TUPLE:
            # Stack: [subject] -> [elem1, ..., elemN] (match success)
            #      or [subject] (match fail)
            # Peek subject; if tuple with matching length, pop subject and push elements; else jump to fail_ip
            elem_count = instr.operands[0]
            fail_ip = instr.operands[1]
            if not self.stack:
                raise RuntimeError_("VM stack underflow: MATCH_TEST_TUPLE")
            subject = self.stack[-1]
            if isinstance(subject, tuple) and len(subject) == elem_count:
                self._pop()
                for elem in reversed(subject):
                    self.stack.append(elem)
            else:
                self.ip = fail_ip

        elif opcode == Op.MATCH_TEST_LIST:
            # Stack: [subject] -> [elem1, ..., elemN] (match success)
            #      or [subject] (match fail)
            # Peek subject; if list with matching length, pop subject and push elements; else jump to fail_ip
            elem_count = instr.operands[0]
            fail_ip = instr.operands[1]
            if not self.stack:
                raise RuntimeError_("VM stack underflow: MATCH_TEST_LIST")
            subject = self.stack[-1]
            if isinstance(subject, list) and len(subject) == elem_count:
                self._pop()
                for elem in reversed(subject):
                    self.stack.append(elem)
            else:
                self.ip = fail_ip

        elif opcode == Op.MATCH_END:
            # Stack: unchanged
            # Marker for match expression end
            pass

        # === 管道 ===
        elif opcode == Op.PIPE_CALL:
            # Stack: [..., pipe_value, extra_arg1, ..., extra_argN, fn] -> [..., result]
            # Pop fn, extra args, and pipe value; call fn with extra_args + [pipe_value]
            extra_arg_count = instr.operands[0]
            fn = self._pop()[0]
            extra_args = self._pop(extra_arg_count)
            pipe_value = self._pop()[0]
            args = extra_args + [pipe_value]
            result = self._call_fn(fn, args)
            self.stack.append(result)

        # === ADT ===
        elif opcode == Op.MAKE_ADT:
            # Stack: [field1, ..., fieldN] -> [adt_value]
            # Pop N field values, construct ADT value, push it
            type_name = instr.operands[0]
            variant_name = instr.operands[1]
            field_count = instr.operands[2]
            field_names = list(instr.operands[3]) if len(instr.operands) > 3 else []
            fields = self._pop(field_count)
            self.stack.append(NovaADTValue(type_name, variant_name, fields, field_names))

        elif opcode == Op.REGISTER_CTOR:
            # Stack: [] -> [constructor]
            # Create and push an ADT constructor value
            type_name = instr.operands[0]
            variant_name = instr.operands[1]
            field_count = instr.operands[2]
            name = instr.operands[3]
            field_names = list(instr.operands[4]) if len(instr.operands) > 4 else []
            self.stack.append(NovaConstructor(type_name, variant_name, field_count, field_names))

        # === 其他 ===
        elif opcode == Op.POP:
            # Stack: [value] -> []
            # Pop and discard top of stack
            self._pop()

        elif opcode == Op.DUP:
            # Stack: [value] -> [value, value]
            # Duplicate top of stack
            if not self.stack:
                raise RuntimeError_("VM stack underflow: DUP")
            self.stack.append(self.stack[-1])

        elif opcode == Op.PRINT:
            # Stack: [value] -> [()]
            # Pop value, format and print it, push Unit
            val = self._pop()[0]
            formatted = self._format_value(val)
            print(formatted)
            self.output.append(formatted)
            self.stack.append(UNIT)

        elif opcode == Op.HALT:
            # Stack: unchanged
            # Halt execution
            pass

        elif opcode == Op.AUTO_CALL_MAIN:
            # Stack: unchanged
            # Marker for auto-calling main (handled in run())
            pass

        elif opcode == Op.TRY_UNWRAP:
            # Stack: [val] -> [val] or early return
            # If Some/Ok, unwrap (pop and push inner value)
            # If None/Err, trigger early return with the error value
            if not self.stack:
                raise RuntimeError_("VM stack underflow: TRY_UNWRAP")
            val = self.stack[-1]
            if isinstance(val, NovaADTValue):
                if val.type_name not in ("Option", "Result"):
                    raise RuntimeError_(f"? 操作符只能在 Option 或 Result 类型上使用，得到 {val.type_name}")
                if val.variant_name in ("None", "Err"):
                    return True
                elif val.variant_name in ("Some", "Ok"):
                    self._pop()
                    self.stack.append(val.fields[0])
                else:
                    raise RuntimeError_(f"? 操作符只能在 Option 或 Result 类型上使用，得到 {val.type_name}")
            else:
                raise RuntimeError_(f"? 操作符只能在 Option 或 Result 类型上使用，得到 {type(val).__name__}")
            return False

        elif opcode == Op.LOOP:
            # Stack: unchanged
            # Unconditional jump back to loop_start
            loop_start = instr.operands[0]
            self.ip = loop_start

        else:
            raise RuntimeError_(f"VM 错误: 未知的指令 '{opcode}'")

        return False

    # ----------------------------------------------------------
    # 公共接口
    # ----------------------------------------------------------

    def get_output(self) -> List[str]:
        """获取 print 输出"""
        return self.output

    def get_global(self, name: str) -> Any:
        """获取全局变量值"""
        return self.globals.get(name)
