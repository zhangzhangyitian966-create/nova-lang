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

import json
import math
import os
from typing import Any, Callable, Dict, List

from .compiler import Bytecode, FunctionBlock, Instruction, Op
from .errors import RuntimeError_

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

    def __hash__(self):
        return hash((self.variant_name, tuple(self.fields)))


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

    def __init__(self, type_name: str, variant_name: str, field_count: int):
        self.type_name = type_name
        self.variant_name = variant_name
        self.field_count = field_count

    def __repr__(self):
        return f"<ctor {self.variant_name}>"


# ============================================================
# 帧结构
# ============================================================


class Frame:
    """调用帧"""

    def __init__(
        self,
        return_ip: int,
        base_sp: int,
        code: List[Instruction],
        constants: List[Any],
        locals_: Dict[str, Any],
        ip: int = 0,
    ):
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

        # 初始化内置函数
        self._setup_builtins()

    def _setup_builtins(self):
        """注册内置函数到全局"""
        self.globals["print"] = NovaBuiltinFn("print", self._builtin_print, 1)
        self.globals["read_line"] = NovaBuiltinFn(
            "read_line", lambda *a: input() if a == () else "", 0
        )
        self.globals["int_to_str"] = NovaBuiltinFn(
            "int_to_str", lambda *a: str(a[0]), 1
        )
        self.globals["float_to_str"] = NovaBuiltinFn(
            "float_to_str", lambda *a: str(a[0]), 1
        )
        self.globals["str_to_int"] = NovaBuiltinFn(
            "str_to_int", self._builtin_str_to_int, 1
        )
        self.globals["str_len"] = NovaBuiltinFn("str_len", lambda *a: len(a[0]), 1)
        self.globals["list_length"] = NovaBuiltinFn(
            "list_length", lambda *a: len(a[0]), 1
        )
        self.globals["filter"] = NovaBuiltinFn("filter", self._builtin_filter, 2)
        self.globals["map"] = NovaBuiltinFn("map", self._builtin_map, 2)
        self.globals["sum"] = NovaBuiltinFn("sum", lambda *a: sum(a[0]), 1)
        self.globals["head"] = NovaBuiltinFn("head", self._builtin_head, 1)
        self.globals["tail"] = NovaBuiltinFn("tail", self._builtin_tail, 1)

        # 文件 I/O
        self.globals["read_file"] = NovaBuiltinFn(
            "read_file", self._builtin_read_file, 1
        )
        self.globals["write_file"] = NovaBuiltinFn(
            "write_file", self._builtin_write_file, 2
        )
        self.globals["file_exists"] = NovaBuiltinFn(
            "file_exists", lambda *a: os.path.exists(a[0]), 1
        )
        self.globals["list_dir"] = NovaBuiltinFn("list_dir", self._builtin_list_dir, 1)

        # JSON
        self.globals["json_parse"] = NovaBuiltinFn(
            "json_parse", self._builtin_json_parse, 1
        )
        self.globals["json_stringify"] = NovaBuiltinFn(
            "json_stringify", self._builtin_json_stringify, 1
        )

        # 数学函数
        self.globals["abs"] = NovaBuiltinFn(
            "abs", lambda *a: abs(self._to_float(a[0])), 1
        )
        self.globals["sqrt"] = NovaBuiltinFn(
            "sqrt", lambda *a: math.sqrt(self._to_float(a[0])), 1
        )
        self.globals["pow"] = NovaBuiltinFn(
            "pow", lambda *a: math.pow(self._to_float(a[0]), self._to_float(a[1])), 2
        )
        self.globals["log"] = NovaBuiltinFn(
            "log", lambda *a: math.log(self._to_float(a[0])), 1
        )
        self.globals["log10"] = NovaBuiltinFn(
            "log10", lambda *a: math.log10(self._to_float(a[0])), 1
        )
        self.globals["exp"] = NovaBuiltinFn(
            "exp", lambda *a: math.exp(self._to_float(a[0])), 1
        )
        self.globals["sin"] = NovaBuiltinFn(
            "sin", lambda *a: math.sin(self._to_float(a[0])), 1
        )
        self.globals["cos"] = NovaBuiltinFn(
            "cos", lambda *a: math.cos(self._to_float(a[0])), 1
        )
        self.globals["tan"] = NovaBuiltinFn(
            "tan", lambda *a: math.tan(self._to_float(a[0])), 1
        )
        self.globals["floor"] = NovaBuiltinFn(
            "floor", lambda *a: float(math.floor(self._to_float(a[0]))), 1
        )
        self.globals["ceil"] = NovaBuiltinFn(
            "ceil", lambda *a: float(math.ceil(self._to_float(a[0]))), 1
        )
        self.globals["round"] = NovaBuiltinFn(
            "round", lambda *a: float(round(self._to_float(a[0]))), 1
        )
        self.globals["min"] = NovaBuiltinFn(
            "min", lambda *a: float(min(self._to_float(a[0]), self._to_float(a[1]))), 2
        )
        self.globals["max"] = NovaBuiltinFn(
            "max", lambda *a: float(max(self._to_float(a[0]), self._to_float(a[1]))), 2
        )
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
            return NovaADTValue("Option", "Some", [int(args[0])])
        except ValueError:
            return NovaADTValue("Option", "None", [])

    def _builtin_filter(self, *args):
        pred_fn, lst = args[0], args[1]
        return [item for item in lst if self._call_fn(pred_fn, [item]) is True]

    def _builtin_map(self, *args):
        map_fn, lst = args[0], args[1]
        return [self._call_fn(map_fn, [item]) for item in lst]

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
            return NovaADTValue("Option", "None", [])
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
            return NovaADTValue(fn.type_name, fn.variant_name, list(args))

        if isinstance(fn, NovaClosure):
            return self._call_closure(fn, args)

        raise RuntimeError_(f"无法调用非函数值: {fn}")

    def _call_closure(self, closure: NovaClosure, args: List[Any]) -> Any:
        """调用闭包"""
        if len(self.call_stack) >= self.MAX_CALL_DEPTH:
            raise RuntimeError_("栈溢出：调用深度超过限制")

        func_block = self.functions.get(closure.func_name)
        if func_block is None:
            raise RuntimeError_(f"未找到函数 '{closure.func_name}'")

        # 合并捕获变量和参数
        locals_ = dict(closure.captured_vars)
        for i, arg in enumerate(args):
            if i < len(func_block.param_names):
                locals_[func_block.param_names[i]] = arg

        # 保存当前帧
        frame = Frame(
            return_ip=self.ip,
            base_sp=len(self.stack) - len(args),  # 保存调用前的栈位置
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

        # 执行函数
        result = self._execute_function()

        # 恢复帧
        self.call_stack.pop()
        self.code = frame.code
        self.constants = frame.constants
        self.ip = frame.return_ip

        return result

    def _execute_function(self) -> Any:
        """执行当前代码直到 RETURN"""
        while self.ip < len(self.code):
            instr = self.code[self.ip]
            opcode = instr.opcode

            if opcode == Op.RETURN:
                # 返回栈顶值
                result = self.stack.pop() if self.stack else UNIT
                return result

            self._execute_instruction(instr)

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

        while self.ip < len(self.code):
            instr = self.code[self.ip]
            opcode = instr.opcode

            if opcode == Op.HALT:
                break

            if opcode == Op.AUTO_CALL_MAIN:
                # 自动调用 main 在 run() 中单独处理
                break

            self._execute_instruction(instr)

        self.code = saved_code
        self.constants = saved_constants
        self.ip = saved_ip

    def _execute_instruction(self, instr: Instruction):
        """执行单条指令"""
        opcode = instr.opcode
        self.ip += 1

        # === 常量与加载 ===
        if opcode == Op.CONST_INT:
            self.stack.append(instr.operands[0])

        elif opcode == Op.CONST_FLOAT:
            self.stack.append(instr.operands[0])

        elif opcode == Op.CONST_STRING:
            self.stack.append(instr.operands[0])

        elif opcode == Op.CONST_BOOL:
            self.stack.append(instr.operands[0])

        elif opcode == Op.CONST_UNIT:
            self.stack.append(UNIT)

        elif opcode == Op.LOAD_CONST:
            idx = instr.operands[0]
            self.stack.append(self.constants[idx])

        elif opcode == Op.LOAD_VAR:
            name = instr.operands[0]
            # 在帧局部变量中查找
            if self.call_stack:
                frame = self.call_stack[-1]
                if name in frame.locals:
                    self.stack.append(frame.locals[name])
                    return
            # 在全局变量中查找
            if name in self.globals:
                self.stack.append(self.globals[name])
            else:
                raise RuntimeError_(f"未定义的变量 '{name}'")

        elif opcode == Op.STORE_VAR:
            name = instr.operands[0]
            mutable = instr.operands[1]
            val = self.stack.pop()
            # 优先存储在当前帧的局部变量中
            if self.call_stack:
                frame = self.call_stack[-1]
                if name in frame.locals:
                    frame.locals[name] = val
                    return
            # 存储到全局
            self.globals[name] = val

        # === 运算 ===
        elif opcode == Op.ADD:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a + b)

        elif opcode == Op.SUB:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a - b)

        elif opcode == Op.MUL:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a * b)

        elif opcode == Op.DIV:
            b, a = self.stack.pop(), self.stack.pop()
            if isinstance(a, int) and isinstance(b, int):
                if b == 0:
                    raise RuntimeError_("除零错误")
                self.stack.append(a // b)
            else:
                self.stack.append(a / b)

        elif opcode == Op.MOD:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a % b)

        elif opcode == Op.NEG:
            a = self.stack.pop()
            self.stack.append(-a)

        elif opcode == Op.CONCAT:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(str(a) + str(b))

        elif opcode == Op.EQ:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a == b)

        elif opcode == Op.NEQ:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a != b)

        elif opcode == Op.LT:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a < b)

        elif opcode == Op.GT:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a > b)

        elif opcode == Op.LTE:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a <= b)

        elif opcode == Op.GTE:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a >= b)

        elif opcode == Op.AND:
            # 在 && 编译中，POP_JUMP_IF_FALSE 已经处理了短路
            # 这里只处理两边的求值结果
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a and b)

        elif opcode == Op.OR:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a or b)

        elif opcode == Op.NOT:
            a = self.stack.pop()
            self.stack.append(not a)

        # === 控制流 ===
        elif opcode == Op.JUMP:
            self.ip = instr.operands[0]

        elif opcode == Op.JUMP_IF_FALSE:
            cond = self.stack.pop()
            if not cond:
                self.ip = instr.operands[0]

        elif opcode == Op.JUMP_IF_TRUE:
            cond = self.stack.pop()
            if cond:
                self.ip = instr.operands[0]

        elif opcode == Op.POP_JUMP_IF_FALSE:
            cond = self.stack.pop()
            if not cond:
                self.ip = instr.operands[0]

        elif opcode == Op.LOOP_END:
            loop_start = instr.operands[0]
            # 栈: [iterable, result_list, body_result]
            body_result = self.stack.pop()
            result_list = self.stack.pop()
            iterable = self.stack.pop()
            result_list.append(body_result)
            self.stack.append(iterable)
            self.stack.append(result_list)
            self.ip = loop_start

        elif opcode == Op.BREAK:
            # 跳出循环 - 需要清理栈并跳到循环结束
            # 在 for 循环中弹出 (iter, index, result_list)
            if self._for_iters:
                self._for_iters.pop()
                # 弹出 for 循环状态
                if len(self.stack) >= 3:
                    self.stack.pop()  # body_result
                    result_list = self.stack.pop()  # result_list
                    self.stack.pop()  # index (for range)
                    self.stack.pop()  # iter (for range)
                    self.stack.append(result_list)
            else:
                # while 循环中的 break
                pass
            # 跳到当前 for_iter 的 end 位置
            if self._for_iters:
                self.ip = self._for_iters[-1].get("end_ip", self.ip)
            else:
                # 找到下一个 LOOP_END 的位置
                while self.ip < len(self.code):
                    next_instr = self.code[self.ip]
                    if next_instr.opcode in (Op.LOOP_END, Op.CONST_UNIT):
                        self.ip += 1
                        break
                    self.ip += 1

        elif opcode == Op.CONTINUE:
            if self._for_iters:
                self.ip = self._for_iters[-1]["loop_start"]
            else:
                # while 循环中的 continue - 跳回循环开始
                # 查找最近的 POP_JUMP_IF_FALSE 之前的 JUMP 位置
                pass

        # === 函数 ===
        elif opcode == Op.CLOSURE:
            func_name = instr.operands[0]
            param_count = instr.operands[1]
            # 捕获当前帧的局部变量
            captured = {}
            if self.call_stack:
                captured = dict(self.call_stack[-1].locals)
            closure = NovaClosure(func_name, param_count, captured)
            self.stack.append(closure)

        elif opcode == Op.CALL:
            arg_count = instr.operands[0]
            args = [self.stack.pop() for _ in range(arg_count)][::-1]
            fn = self.stack.pop()
            result = self._call_fn(fn, args)
            self.stack.append(result)

        elif opcode == Op.RETURN:
            result = self.stack.pop() if self.stack else UNIT
            # 由 _execute_function 处理返回

        elif opcode == Op.CALL_BUILTIN:
            name = instr.operands[0]
            arg_count = instr.operands[1]
            args = [self.stack.pop() for _ in range(arg_count)][::-1]
            builtin = self.globals.get(name)
            if builtin is None:
                raise RuntimeError_(f"未找到内置函数 '{name}'")
            result = self._call_fn(builtin, args)
            self.stack.append(result)

        # === 数据结构 ===
        elif opcode == Op.BUILD_LIST:
            count = instr.operands[0]
            elements = [self.stack.pop() for _ in range(count)][::-1]
            self.stack.append(elements)

        elif opcode == Op.BUILD_TUPLE:
            count = instr.operands[0]
            elements = [self.stack.pop() for _ in range(count)][::-1]
            self.stack.append(tuple(elements))

        elif opcode == Op.BUILD_MAP:
            count = instr.operands[0]
            result = {}
            for _ in range(count):
                val = self.stack.pop()
                key = self.stack.pop()
                result[key] = val
            self.stack.append(result)

        elif opcode == Op.INDEX:
            index = self.stack.pop()
            obj = self.stack.pop()
            self.stack.append(obj[index])

        elif opcode == Op.FIELD_ACCESS:
            field = instr.operands[0]
            obj = self.stack.pop()
            if isinstance(obj, tuple):
                self.stack.append(obj[int(field)])
            elif isinstance(obj, NovaADTValue):
                self.stack.append(obj.fields[int(field)])
            else:
                raise RuntimeError_(f"无法对值进行字段访问 '{field}'")

        elif opcode == Op.BUILD_RANGE:
            step = self.stack.pop()
            end = self.stack.pop()
            start = self.stack.pop()
            # 返回范围信息: (type, start, end, step)
            self.stack.append(("range", start, end, step))

        elif opcode == Op.FOR_ITER:
            fail_ip = instr.operands[0]
            # 栈: [iterable, result_list]
            result_list = self.stack.pop()
            iter_val = self.stack.pop()

            if isinstance(iter_val, tuple) and iter_val[0] == "range":
                # 范围迭代
                if not hasattr(self, "_range_index"):
                    self._range_index = {}

                key = id(iter_val)
                if key not in self._range_index:
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
                else:
                    del self._range_index[key]
                    # 迭代结束，只保留结果列表
                    self.stack.append(result_list)
                    self.ip = fail_ip
                    return
            elif isinstance(iter_val, list):
                # 列表迭代
                if not hasattr(self, "_list_index"):
                    self._list_index = {}

                key = id(iter_val)
                if key not in self._list_index:
                    self._list_index[key] = 0

                idx = self._list_index[key]
                if idx < len(iter_val):
                    self._list_index[key] = idx + 1
                    # 栈: [iterable, result_list, current_element]
                    self.stack.append(iter_val)
                    self.stack.append(result_list)
                    self.stack.append(iter_val[idx])
                else:
                    del self._list_index[key]
                    # 迭代结束，只保留结果列表
                    self.stack.append(result_list)
                    self.ip = fail_ip
                    return
            else:
                raise RuntimeError_(f"无法迭代的值: {type(iter_val)}")

        # === 模式匹配 ===
        elif opcode == Op.MATCH_START:
            pass

        elif opcode == Op.MATCH_TEST_INT:
            test_val = instr.operands[0]
            fail_ip = instr.operands[1]
            subject = self.stack[-1]  # peek
            if (
                isinstance(subject, int)
                and not isinstance(subject, bool)
                and subject == test_val
            ):
                pass  # 匹配成功，subject 仍在栈上
            else:
                self.ip = fail_ip  # 跳到下一个 arm（subject 仍保留）

        elif opcode == Op.MATCH_TEST_BOOL:
            test_val = instr.operands[0]
            fail_ip = instr.operands[1]
            subject = self.stack[-1]
            if isinstance(subject, bool) and subject == test_val:
                pass
            else:
                self.ip = fail_ip

        elif opcode == Op.MATCH_TEST_STRING:
            test_val = instr.operands[0]
            fail_ip = instr.operands[1]
            subject = self.stack[-1]
            if isinstance(subject, str) and subject == test_val:
                pass
            else:
                self.ip = fail_ip

        elif opcode == Op.MATCH_WILDCARD:
            pass  # subject 仍在栈上

        elif opcode == Op.MATCH_BIND:
            name = instr.operands[0]
            val = self.stack.pop()
            if self.call_stack:
                self.call_stack[-1].locals[name] = val
            else:
                self.globals[name] = val

        elif opcode == Op.MATCH_CONSTRUCTOR:
            ctor_name = instr.operands[0]
            field_count = instr.operands[1]
            fail_ip = instr.operands[2]
            subject = self.stack.pop()
            if (
                isinstance(subject, NovaADTValue)
                and subject.variant_name == ctor_name
                and len(subject.fields) == field_count
            ):
                # 匹配成功：弹出 subject，将字段压栈
                for field_val in reversed(subject.fields):
                    self.stack.append(field_val)
            else:
                self.ip = fail_ip

        elif opcode == Op.MATCH_END:
            pass

        # === 管道 ===
        elif opcode == Op.PIPE_CALL:
            extra_arg_count = instr.operands[0]
            # 栈: [..., pipe_value, extra_arg1, ..., extra_argN, fn]
            fn = self.stack.pop()
            extra_args = [self.stack.pop() for _ in range(extra_arg_count)][::-1]
            pipe_value = self.stack.pop()
            # 管道值作为最后一个参数（Nova 约定: filter(f, list)）
            args = extra_args + [pipe_value]
            result = self._call_fn(fn, args)
            self.stack.append(result)

        # === ADT ===
        elif opcode == Op.MAKE_ADT:
            type_name = instr.operands[0]
            variant_name = instr.operands[1]
            field_count = instr.operands[2]
            fields = [self.stack.pop() for _ in range(field_count)][::-1]
            self.stack.append(NovaADTValue(type_name, variant_name, fields))

        elif opcode == Op.REGISTER_CTOR:
            type_name = instr.operands[0]
            variant_name = instr.operands[1]
            field_count = instr.operands[2]
            name = instr.operands[3]
            self.stack.append(NovaConstructor(type_name, variant_name, field_count))

        # === 其他 ===
        elif opcode == Op.POP:
            self.stack.pop()

        elif opcode == Op.DUP:
            self.stack.append(self.stack[-1])

        elif opcode == Op.PRINT:
            val = self.stack.pop()
            formatted = self._format_value(val)
            print(formatted)
            self.output.append(formatted)

        elif opcode == Op.HALT:
            pass

        elif opcode == Op.AUTO_CALL_MAIN:
            pass

        elif opcode == Op.TRY_UNWRAP:
            val = self.stack[-1]
            if isinstance(val, NovaADTValue) and val.variant_name in ("None", "Err"):
                pass  # 保持当前值（错误传播）
            # 否则保持值不变

        elif opcode == Op.LOOP:
            loop_start = instr.operands[0]
            self.ip = loop_start

        else:
            raise RuntimeError_(f"VM 错误: 未知的指令 '{opcode}'")

    # ----------------------------------------------------------
    # 公共接口
    # ----------------------------------------------------------

    def get_output(self) -> List[str]:
        """获取 print 输出"""
        return self.output

    def get_global(self, name: str) -> Any:
        """获取全局变量值"""
        return self.globals.get(name)
