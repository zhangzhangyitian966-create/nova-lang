"""
Nova 编程语言 - 字节码编译器

将 AST 编译为字节码指令序列，供栈式虚拟机执行。

指令编码使用简单的 Python 对象列表，可读性好，支持 --dump-bytecode 打印。

编译流程：
1. 遍历 AST 节点
2. 为每个顶层声明生成字节码
3. 函数体编译为独立的字节码块（存储在 functions 字典中）
4. 字面量收集到常量池
5. 跳转偏移量在编译过程中通过占位符回填
"""

import sys
from typing import Dict, List, Optional, Any, Tuple

from nova.ast_nodes import (
    Program, Block,
    IntLiteral, FloatLiteral, StringLiteral, CharLiteral, BoolLiteral, UnitLiteral,
    Identifier, BinaryOp, UnaryOp, PipeExpr, TryExpr,
    Param, Lambda, FnDef, FnCall,
    LetBinding, MutBinding, Assignment,
    IfExpr, MatchArm, MatchExpr,
    ForExpr, WhileExpr, BreakExpr, ContinueExpr,
    ListExpr, ListComprehension, TupleExpr, MapExpr, FieldAccess,
    TypeDef, VariantDef, AliasDef,
    ImportDecl, ExportDecl,
    PatternWildcard, PatternInt, PatternFloat, PatternString,
    PatternBool, PatternChar, PatternIdentifier, PatternConstructor,
    PatternTuple, PatternList,
)


# ============================================================
# 指令定义
# ============================================================

class Op:
    """字节码操作码"""
    # 常量与加载
    CONST_INT = "CONST_INT"          # operands: (value,)
    CONST_FLOAT = "CONST_FLOAT"      # operands: (value,)
    CONST_STRING = "CONST_STRING"    # operands: (value,)
    CONST_BOOL = "CONST_BOOL"        # operands: (value,)
    CONST_UNIT = "CONST_UNIT"        # operands: ()
    LOAD_CONST = "LOAD_CONST"        # operands: (index,)
    LOAD_VAR = "LOAD_VAR"            # operands: (name,)
    STORE_VAR = "STORE_VAR"          # operands: (name, mutable)

    # 运算
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL"
    DIV = "DIV"
    MOD = "MOD"
    NEG = "NEG"
    CONCAT = "CONCAT"
    EQ = "EQ"
    NEQ = "NEQ"
    LT = "LT"
    GT = "GT"
    LTE = "LTE"
    GTE = "GTE"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"

    # 控制流
    JUMP = "JUMP"                    # operands: (target_ip,)
    JUMP_IF_FALSE = "JUMP_IF_FALSE"  # operands: (target_ip,)
    JUMP_IF_TRUE = "JUMP_IF_TRUE"    # operands: (target_ip,)
    POP_JUMP_IF_FALSE = "POP_JUMP_IF_FALSE"  # operands: (target_ip,)
    LOOP = "LOOP"                    # operands: (loop_start_ip,) - 标记循环继续跳回
    LOOP_END = "LOOP_END"            # operands: (loop_start_ip,) - 循环结束/继续跳回
    BREAK = "BREAK"
    CONTINUE = "CONTINUE"

    # 函数
    CLOSURE = "CLOSURE"              # operands: (func_name, param_count, code_key)
    CALL = "CALL"                    # operands: (arg_count,)
    RETURN = "RETURN"
    CALL_BUILTIN = "CALL_BUILTIN"    # operands: (name, arg_count)

    # 数据结构
    BUILD_LIST = "BUILD_LIST"        # operands: (count,)
    BUILD_TUPLE = "BUILD_TUPLE"      # operands: (count,)
    BUILD_MAP = "BUILD_MAP"          # operands: (count,)
    INDEX = "INDEX"
    FIELD_ACCESS = "FIELD_ACCESS"     # operands: (field_name,)
    BUILD_RANGE = "BUILD_RANGE"       # operands: () - 从栈上弹出 start, end, [step]
    FOR_ITER = "FOR_ITER"            # operands: (loop_start_ip,) - 迭代一步

    # 模式匹配
    MATCH_START = "MATCH_START"      # operands: (arm_count,)
    MATCH_TEST_INT = "MATCH_TEST_INT"    # operands: (value, fail_ip,)
    MATCH_TEST_FLOAT = "MATCH_TEST_FLOAT"    # operands: (value, fail_ip,)
    MATCH_TEST_BOOL = "MATCH_TEST_BOOL"  # operands: (value, fail_ip,)
    MATCH_TEST_STRING = "MATCH_TEST_STRING"  # operands: (value, fail_ip,)
    MATCH_TEST_CHAR = "MATCH_TEST_CHAR"  # operands: (value, fail_ip,)
    MATCH_BIND = "MATCH_BIND"        # operands: (name,)
    MATCH_WILDCARD = "MATCH_WILDCARD"
    MATCH_CONSTRUCTOR = "MATCH_CONSTRUCTOR"  # operands: (name, field_count, fail_ip,)
    MATCH_TEST_TUPLE = "MATCH_TEST_TUPLE"  # operands: (element_count, fail_ip,)
    MATCH_TEST_LIST = "MATCH_TEST_LIST"    # operands: (element_count, fail_ip,)
    MATCH_END = "MATCH_END"

    # 管道
    PIPE_CALL = "PIPE_CALL"          # operands: (arg_count,)

    # ADT
    MAKE_ADT = "MAKE_ADT"           # operands: (type_name, variant_name, field_count, field_names_tuple)
    REGISTER_CTOR = "REGISTER_CTOR"  # operands: (type_name, variant_name, field_count, name, field_names_tuple)

    # 其他
    POP = "POP"
    DUP = "DUP"
    PRINT = "PRINT"
    HALT = "HALT"
    TRY_UNWRAP = "TRY_UNWRAP"
    AUTO_CALL_MAIN = "AUTO_CALL_MAIN"  # 自动调用 main()


class Instruction:
    """字节码指令"""

    def __init__(self, opcode: str, *operands):
        self.opcode = opcode
        self.operands = operands

    def __repr__(self):
        if self.operands:
            ops = ", ".join(repr(o) for o in self.operands)
            return f"{self.opcode} {ops}"
        return self.opcode

    def __eq__(self, other):
        if isinstance(other, Instruction):
            return self.opcode == other.opcode and self.operands == other.operands
        return NotImplemented


# ============================================================
# 编译结果
# ============================================================

class FunctionBlock:
    """函数字节码块"""

    def __init__(self, name: str, param_count: int, code: List[Instruction],
                 constants: List[Any], param_names: List[str] = None):
        self.name = name
        self.param_count = param_count
        self.code = code
        self.constants = constants
        self.param_names = param_names or []


class Bytecode:
    """编译产物：包含指令序列、常量池、函数块"""

    def __init__(self):
        self.code: List[Instruction] = []
        self.constants: List[Any] = []
        self.functions: Dict[str, FunctionBlock] = {}

    def add_const(self, value) -> int:
        """添加常量到常量池，返回索引"""
        # 去重检查
        try:
            idx = self.constants.index(value)
            return idx
        except (ValueError, TypeError):
            idx = len(self.constants)
            self.constants.append(value)
            return idx

    def emit(self, instruction: Instruction):
        """追加一条指令"""
        self.code.append(instruction)

    def emit_op(self, opcode: str, *operands):
        """追加一条指令（便捷方法）"""
        self.code.append(Instruction(opcode, *operands))

    def current_pos(self) -> int:
        """当前指令位置"""
        return len(self.code)

    def patch_jump(self, pos: int, target_ip: int):
        """回填跳转目标"""
        instr = self.code[pos]
        self.code[pos] = Instruction(instr.opcode, target_ip)

    def patch_match_fail(self, pos: int, fail_ip: int):
        """回填 match 模式测试的失败跳转（保留前两个操作数）"""
        instr = self.code[pos]
        # 格式: MATCH_TEST_* (value, fail_ip_placeholder) 或
        #        MATCH_CONSTRUCTOR (name, field_count, fail_ip_placeholder)
        if len(instr.operands) == 3:
            self.code[pos] = Instruction(instr.opcode, instr.operands[0], instr.operands[1], fail_ip)
        elif len(instr.operands) == 2:
            self.code[pos] = Instruction(instr.opcode, instr.operands[0], fail_ip)


# ============================================================
# 编译器
# ============================================================

class BytecodeCompiler:
    """AST 到字节码的编译器"""

    def __init__(self, module_manager=None, current_file: str = None):
        self.bytecode = Bytecode()
        self._builtin_names: set = set()
        self._init_builtin_names()
        # ADT 构造器注册表: {variant_name: (type_name, field_count)}
        # 用于在模式匹配中区分零字段构造器与变量绑定
        self._adt_constructors: Dict[str, Tuple[str, int]] = {}
        self._init_builtin_adt_constructors()
        self._module_manager = module_manager  # ModuleManager 实例
        self._current_file = current_file      # 当前文件路径

    def _init_builtin_adt_constructors(self):
        """初始化内置 ADT 构造器"""
        self._adt_constructors["None"] = ("Option", 0)
        self._adt_constructors["Some"] = ("Option", 1)
        self._adt_constructors["Ok"] = ("Result", 1)
        self._adt_constructors["Err"] = ("Result", 1)

    def _init_builtin_names(self):
        """初始化内置函数名称集合"""
        self._builtin_names = {
            "print", "read_line", "int_to_str", "float_to_str", "str_to_int",
            "str_len", "list_length", "filter", "map", "sum", "head", "tail",
            "read_file", "write_file", "file_exists", "list_dir",
            "json_parse", "json_stringify",
            "abs", "sqrt", "pow", "log", "log10", "exp",
            "sin", "cos", "tan", "floor", "ceil", "round",
            "min", "max", "pi",
        }

    def compile(self, program: Program) -> Bytecode:
        """编译整个程序"""
        for decl in program.declarations:
            self._compile_decl(decl)

        self.bytecode.emit_op(Op.HALT)
        self.bytecode.emit_op(Op.AUTO_CALL_MAIN)
        return self.bytecode

    # ----------------------------------------------------------
    # 声明编译
    # ----------------------------------------------------------

    def _compile_decl(self, decl):
        """编译顶层声明"""
        if isinstance(decl, ImportDecl):
            # 内联导入的模块声明
            self._compile_import(decl)
            return

        if isinstance(decl, ExportDecl):
            # 导出声明：编译器不需要做额外工作（内联时名称已在作用域中）
            return

        if isinstance(decl, TypeDef):
            for variant in decl.variants:
                field_count = len(variant.fields)
                field_names = tuple(f[0] for f in variant.fields)
                # 注册构造器到编译器的 ADT 构造器表（用于模式匹配识别）
                self._adt_constructors[variant.name] = (decl.name, field_count)
                if variant.fields:
                    # 带字段的构造器 -> 注册构造函数
                    self.bytecode.emit_op(
                        Op.REGISTER_CTOR,
                        decl.name, variant.name, field_count, variant.name, field_names
                    )
                    self.bytecode.emit_op(Op.STORE_VAR, variant.name, False)
                else:
                    # 无字段构造器 -> 创建 ADT 值
                    self.bytecode.emit_op(Op.MAKE_ADT, decl.name, variant.name, 0, field_names)
                    self.bytecode.emit_op(Op.STORE_VAR, variant.name, False)

        elif isinstance(decl, AliasDef):
            pass

        elif isinstance(decl, FnDef):
            self._compile_fn_def(decl)

        elif isinstance(decl, LetBinding):
            self._compile_expr(decl.value)
            self.bytecode.emit_op(Op.STORE_VAR, decl.name, False)

        elif isinstance(decl, MutBinding):
            self._compile_expr(decl.value)
            self.bytecode.emit_op(Op.STORE_VAR, decl.name, True)

        else:
            # 顶层表达式
            self._compile_expr(decl)
            self.bytecode.emit_op(Op.POP)

    def _get_decl_name(self, decl):
        """获取声明的名称，用于冲突检测。

        支持从 FnDef、LetBinding、MutBinding、TypeDef、AliasDef 等声明中提取名称。
        对于不含名称的声明（如顶层表达式），返回 None。
        """
        if isinstance(decl, (FnDef, LetBinding, MutBinding, TypeDef, AliasDef)):
            return decl.name
        return None

    def _compile_import(self, decl: ImportDecl):
        """编译导入声明（内联方式）

        加载导入的模块，将其导出的声明内联到当前字节码中。
        """
        if self._module_manager is None:
            return

        module_path = decl.module_name

        from nova.modules import ModuleResolver
        resolver = ModuleResolver(self._module_manager.search_paths, self._current_file)
        file_path = resolver.resolve(module_path)

        if not file_path:
            raise RuntimeError(f"编译器错误: 找不到模块 '{module_path}'")

        # 加载模块
        if file_path in self._module_manager.modules:
            module_info = self._module_manager.modules[file_path]
        else:
            module_info = self._module_manager.load_module(
                module_path, self._current_file, check_types=False
            )

        if module_info is None:
            raise RuntimeError(f"编译器错误: 无法加载模块 '{module_path}'")

        # 内联导出的声明到当前字节码
        for imp_decl in module_info.program.declarations:
            # 跳过导入模块中的导入和导出声明
            if isinstance(imp_decl, (ImportDecl, ExportDecl)):
                continue
            # 跳过未导出的声明
            if isinstance(imp_decl, FnDef) and imp_decl.name not in module_info.exported_names:
                continue
            if isinstance(imp_decl, (LetBinding, MutBinding)) and imp_decl.name not in module_info.exported_names:
                continue
            if isinstance(imp_decl, TypeDef) and imp_decl.name not in module_info.exported_names:
                continue
            if isinstance(imp_decl, AliasDef) and imp_decl.name not in module_info.exported_names:
                continue
            # 检测同名冲突：如果声明名称已存在于当前编译上下文中，发出警告
            decl_name = self._get_decl_name(imp_decl)
            if decl_name is not None:
                if decl_name in self.bytecode.functions or decl_name in self._builtin_names:
                    print(
                        f"warning: import '{decl_name}' shadows existing binding",
                        file=sys.stderr,
                    )
            # 内联编译
            self._compile_decl(imp_decl)

    def _compile_fn_def(self, decl: FnDef):
        """编译函数定义"""
        param_count = len(decl.params)
        fn_name = decl.name
        param_names = [p.name for p in decl.params]

        # 编译函数体为独立的字节码块
        old_bytecode = self.bytecode
        fn_bytecode = Bytecode()
        self.bytecode = fn_bytecode

        # 编译函数体
        self._compile_expr(decl.body)
        self.bytecode.emit_op(Op.RETURN)

        fn_code = fn_bytecode.code
        fn_consts = fn_bytecode.constants
        # 收集函数内嵌定义的所有子函数/lambdas
        fn_sub_functions = dict(fn_bytecode.functions)

        self.bytecode = old_bytecode

        func_block = FunctionBlock(fn_name, param_count, fn_code, fn_consts, param_names)
        self.bytecode.functions[fn_name] = func_block

        # 将子函数/lambdas 也注册到主 bytecode 的 functions 中
        for sub_name, sub_block in fn_sub_functions.items():
            self.bytecode.functions[sub_name] = sub_block

        # 在主代码中创建闭包
        self.bytecode.emit_op(Op.CLOSURE, fn_name, param_count)
        self.bytecode.emit_op(Op.STORE_VAR, fn_name, False)

    # ----------------------------------------------------------
    # 表达式编译
    # ----------------------------------------------------------

    def _compile_expr(self, expr):
        """编译表达式"""
        if isinstance(expr, IntLiteral):
            self.bytecode.emit_op(Op.CONST_INT, expr.value)

        elif isinstance(expr, FloatLiteral):
            self.bytecode.emit_op(Op.CONST_FLOAT, expr.value)

        elif isinstance(expr, StringLiteral):
            self.bytecode.emit_op(Op.CONST_STRING, expr.value)

        elif isinstance(expr, CharLiteral):
            self.bytecode.emit_op(Op.CONST_STRING, expr.value)

        elif isinstance(expr, BoolLiteral):
            self.bytecode.emit_op(Op.CONST_BOOL, expr.value)

        elif isinstance(expr, UnitLiteral):
            self.bytecode.emit_op(Op.CONST_UNIT)

        elif isinstance(expr, Identifier):
            name = expr.name
            if name == "None":
                self.bytecode.emit_op(Op.MAKE_ADT, "Option", "None", 0, ())
            else:
                self.bytecode.emit_op(Op.LOAD_VAR, name)

        elif isinstance(expr, BinaryOp):
            self._compile_binary_op(expr)

        elif isinstance(expr, UnaryOp):
            self._compile_unary_op(expr)

        elif isinstance(expr, PipeExpr):
            self._compile_pipe(expr)

        elif isinstance(expr, TryExpr):
            self._compile_expr(expr.expr)
            self.bytecode.emit_op(Op.TRY_UNWRAP)

        elif isinstance(expr, FnCall):
            self._compile_fn_call(expr)

        elif isinstance(expr, Lambda):
            self._compile_lambda(expr)

        elif isinstance(expr, IfExpr):
            self._compile_if(expr)

        elif isinstance(expr, MatchExpr):
            self._compile_match(expr)

        elif isinstance(expr, Block):
            self._compile_block(expr)

        elif isinstance(expr, LetBinding):
            self._compile_expr(expr.value)
            self.bytecode.emit_op(Op.STORE_VAR, expr.name, False)

        elif isinstance(expr, MutBinding):
            self._compile_expr(expr.value)
            self.bytecode.emit_op(Op.STORE_VAR, expr.name, True)

        elif isinstance(expr, Assignment):
            self._compile_expr(expr.value)
            self.bytecode.emit_op(Op.STORE_VAR, expr.name, True)

        elif isinstance(expr, ListExpr):
            for elem in expr.elements:
                self._compile_expr(elem)
            self.bytecode.emit_op(Op.BUILD_LIST, len(expr.elements))

        elif isinstance(expr, ListComprehension):
            self._compile_list_comprehension(expr)

        elif isinstance(expr, ForExpr):
            self._compile_for(expr)

        elif isinstance(expr, WhileExpr):
            self._compile_while(expr)

        elif isinstance(expr, BreakExpr):
            self.bytecode.emit_op(Op.BREAK)

        elif isinstance(expr, ContinueExpr):
            self.bytecode.emit_op(Op.CONTINUE)

        elif isinstance(expr, TupleExpr):
            for elem in expr.elements:
                self._compile_expr(elem)
            self.bytecode.emit_op(Op.BUILD_TUPLE, len(expr.elements))

        elif isinstance(expr, MapExpr):
            for key_expr, val_expr in expr.pairs:
                self._compile_expr(key_expr)
                self._compile_expr(val_expr)
            self.bytecode.emit_op(Op.BUILD_MAP, len(expr.pairs))

        elif isinstance(expr, FieldAccess):
            self._compile_expr(expr.target)
            self.bytecode.emit_op(Op.FIELD_ACCESS, expr.field)

        else:
            raise RuntimeError(f"编译器错误: 未知的表达式类型 {type(expr).__name__}")

    def _compile_binary_op(self, expr: BinaryOp):
        """编译二元操作"""
        op = expr.op

        if op == "&&":
            self._compile_expr(expr.left)
            self.bytecode.emit_op(Op.DUP)
            jump_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.POP_JUMP_IF_FALSE, 0)
            # true 路径：left 为 true，弹出 dup 的值，计算 right
            self.bytecode.emit_op(Op.POP)
            self._compile_expr(expr.right)
            end_pos = self.bytecode.current_pos()
            self.bytecode.patch_jump(jump_pos, end_pos)
            return

        if op == "||":
            self._compile_expr(expr.left)
            self.bytecode.emit_op(Op.DUP)
            jump_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.JUMP_IF_TRUE, 0)
            # false 路径：left 为 false，弹出 dup 的值，计算 right
            self.bytecode.emit_op(Op.POP)
            self._compile_expr(expr.right)
            end_pos = self.bytecode.current_pos()
            self.bytecode.patch_jump(jump_pos, end_pos)
            return

        self._compile_expr(expr.left)
        self._compile_expr(expr.right)

        op_map = {
            "+": Op.ADD, "-": Op.SUB, "*": Op.MUL, "/": Op.DIV, "%": Op.MOD,
            "++": Op.CONCAT,
            "==": Op.EQ, "!=": Op.NEQ,
            "<": Op.LT, ">": Op.GT, "<=": Op.LTE, ">=": Op.GTE,
        }
        if op in op_map:
            self.bytecode.emit_op(op_map[op])
        else:
            raise RuntimeError(f"编译器错误: 未知的二元操作符 '{op}'")

    def _compile_unary_op(self, expr: UnaryOp):
        """编译一元操作"""
        self._compile_expr(expr.operand)
        if expr.op == "-":
            self.bytecode.emit_op(Op.NEG)
        elif expr.op == "!":
            self.bytecode.emit_op(Op.NOT)
        else:
            raise RuntimeError(f"编译器错误: 未知的一元操作符 '{expr.op}'")

    def _compile_pipe(self, expr: PipeExpr):
        """编译管道操作 expr |> f"""
        # 编译左侧（被管道的值）
        self._compile_expr(expr.left)

        # 编译右侧
        # 如果右侧是函数调用 f(args)，需要编译 args，加载 f，然后用 PIPE_CALL
        if isinstance(expr.right, FnCall):
            fn_call = expr.right
            # 编译 f 的参数
            for arg in fn_call.args:
                self._compile_expr(arg)

            # 加载 f
            if isinstance(fn_call.callee, Identifier):
                name = fn_call.callee.name
                if name in self._builtin_names:
                    self.bytecode.emit_op(Op.LOAD_VAR, name)
                else:
                    self.bytecode.emit_op(Op.LOAD_VAR, name)
            else:
                self._compile_expr(fn_call.callee)

            # PIPE_CALL: pipe_value + fn_call 的参数
            extra_arg_count = len(fn_call.args)
            self.bytecode.emit_op(Op.PIPE_CALL, extra_arg_count)
        else:
            # 右侧不是函数调用，直接加载并调用
            self._compile_expr(expr.right)
            self.bytecode.emit_op(Op.PIPE_CALL, 0)

    def _compile_fn_call(self, expr: FnCall):
        """编译函数调用"""
        # 先编译 callee，再编译参数（栈: [fn, arg1, arg2, ...]）
        callee_on_stack = False

        if isinstance(expr.callee, Identifier):
            name = expr.callee.name
            if name in self._builtin_names:
                # 内置函数：先编译参数，再 CALL_BUILTIN
                for arg in expr.args:
                    self._compile_expr(arg)
                arg_count = len(expr.args)
                self.bytecode.emit_op(Op.CALL_BUILTIN, name, arg_count)
                return
            elif name in ("Some", "Ok", "Err"):
                # ADT 构造器：先编译参数
                for arg in expr.args:
                    self._compile_expr(arg)
                arg_count = len(expr.args)
                if name == "Some":
                    self.bytecode.emit_op(Op.MAKE_ADT, "Option", "Some", arg_count, ("value",))
                elif name == "Ok":
                    self.bytecode.emit_op(Op.MAKE_ADT, "Result", "Ok", arg_count, ("value",))
                elif name == "Err":
                    self.bytecode.emit_op(Op.MAKE_ADT, "Result", "Err", arg_count, ("error",))
                return
            else:
                self.bytecode.emit_op(Op.LOAD_VAR, name)
                callee_on_stack = True
        else:
            self._compile_expr(expr.callee)
            callee_on_stack = True

        # 编译参数
        for arg in expr.args:
            self._compile_expr(arg)

        arg_count = len(expr.args)
        if callee_on_stack:
            self.bytecode.emit_op(Op.CALL, arg_count)

    def _compile_lambda(self, expr: Lambda):
        """编译 lambda 为独立的字节码块"""
        param_count = len(expr.params)
        param_names = [p.name for p in expr.params]

        old_bytecode = self.bytecode
        fn_bytecode = Bytecode()
        self.bytecode = fn_bytecode

        self._compile_expr(expr.body)
        self.bytecode.emit_op(Op.RETURN)

        fn_code = fn_bytecode.code
        fn_consts = fn_bytecode.constants

        self.bytecode = old_bytecode

        lambda_name = f"<lambda_{len(self.bytecode.functions)}_{id(fn_code)}>"
        func_block = FunctionBlock(lambda_name, param_count, fn_code, fn_consts, param_names)
        self.bytecode.functions[lambda_name] = func_block

        self.bytecode.emit_op(Op.CLOSURE, lambda_name, param_count)

    def _compile_if(self, expr: IfExpr):
        """编译 if-then-else"""
        self._compile_expr(expr.condition)

        if expr.else_branch:
            jump_to_else = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.JUMP_IF_FALSE, 0)

            self._compile_expr(expr.then_branch)

            jump_to_end = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.JUMP, 0)

            else_pos = self.bytecode.current_pos()
            self.bytecode.patch_jump(jump_to_else, else_pos)

            self._compile_expr(expr.else_branch)

            end_pos = self.bytecode.current_pos()
            self.bytecode.patch_jump(jump_to_end, end_pos)
        else:
            jump_to_end = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.JUMP_IF_FALSE, 0)

            self._compile_expr(expr.then_branch)

            end_pos = self.bytecode.current_pos()
            self.bytecode.patch_jump(jump_to_end, end_pos)

            # 无 else 时，false 路径推入 Unit
            self.bytecode.emit_op(Op.CONST_UNIT)

    def _compile_match(self, expr: MatchExpr):
        """编译模式匹配"""
        # 编译 subject（留在栈顶）
        self._compile_expr(expr.subject)

        arm_count = len(expr.arms)
        self.bytecode.emit_op(Op.MATCH_START, arm_count)

        jump_to_end_positions = []

        for i, arm in enumerate(expr.arms):
            # 模式测试：匹配失败时跳到下一个 arm 的测试开始
            # 记录当前指令位置
            fail_ip_pos = self._compile_pattern_test_with_fail(arm.pattern)

            # 匹配成功 -> subject 在栈上
            # 编译匹配体的绑定（从 subject 中提取值）
            self._compile_pattern_extract_and_bind(arm.pattern)

            # 编译 guard 条件（如果有）
            if arm.guard is not None:
                self._compile_expr(arm.guard)
                guard_fail_pos = self.bytecode.current_pos()
                self.bytecode.emit_op(Op.JUMP_IF_FALSE, 0)

            # 编译匹配体
            self._compile_expr(arm.body)

            # 跳到 match 结束
            jump_end = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.JUMP, 0)
            jump_to_end_positions.append(jump_end)

            # 回填模式测试和 guard 的失败跳转到下一个 arm 的开始
            next_arm_start = self.bytecode.current_pos()
            if fail_ip_pos is not None:
                self.bytecode.patch_match_fail(fail_ip_pos, next_arm_start)
            if arm.guard is not None:
                self.bytecode.patch_jump(guard_fail_pos, next_arm_start)

        # 所有 arm 都匹配失败
        self.bytecode.emit_op(Op.POP)  # 弹出 subject
        self.bytecode.emit_op(Op.CONST_UNIT)  # 默认值
        self.bytecode.emit_op(Op.MATCH_END)

        end_pos = self.bytecode.current_pos()
        for jpos in jump_to_end_positions:
            self.bytecode.patch_jump(jpos, end_pos)

    def _compile_pattern_test_with_fail(self, pattern):
        """
        编译模式测试。匹配失败时跳到下一个 arm。
        返回 fail_ip 的占位位置，或 None（如果总是匹配）。
        subject 在栈顶，匹配成功时保留在栈上。
        """
        if isinstance(pattern, PatternWildcard):
            return None  # 总是匹配

        elif isinstance(pattern, PatternInt):
            fail_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.MATCH_TEST_INT, pattern.value, 0)
            return fail_pos

        elif isinstance(pattern, PatternFloat):
            fail_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.MATCH_TEST_FLOAT, pattern.value, 0)
            return fail_pos

        elif isinstance(pattern, PatternBool):
            fail_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.MATCH_TEST_BOOL, pattern.value, 0)
            return fail_pos

        elif isinstance(pattern, PatternString):
            fail_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.MATCH_TEST_STRING, pattern.value, 0)
            return fail_pos

        elif isinstance(pattern, PatternChar):
            fail_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.MATCH_TEST_CHAR, pattern.value, 0)
            return fail_pos

        elif isinstance(pattern, PatternIdentifier):
            # 检查是否是已知的零字段 ADT 构造器（如 None, Red 等）
            if pattern.name in self._adt_constructors:
                type_name, field_count = self._adt_constructors[pattern.name]
                if field_count == 0:
                    # 零字段构造器：作为构造器模式编译
                    fail_pos = self.bytecode.current_pos()
                    self.bytecode.emit_op(Op.MATCH_CONSTRUCTOR, pattern.name, 0, 0)
                    return fail_pos
            return None  # 变量绑定总是匹配

        elif isinstance(pattern, PatternConstructor):
            fail_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.MATCH_CONSTRUCTOR, pattern.name, len(pattern.fields), 0)
            return fail_pos

        elif isinstance(pattern, PatternTuple):
            fail_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.MATCH_TEST_TUPLE, len(pattern.elements), 0)
            return fail_pos

        elif isinstance(pattern, PatternList):
            fail_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.MATCH_TEST_LIST, len(pattern.elements), 0)
            return fail_pos

        else:
            return None

    def _compile_pattern_extract_and_bind(self, pattern):
        """
        从 subject 中提取值并绑定到变量。
        约定：所有 MATCH_TEST_* 操作码在匹配成功时已弹出 subject。
        对于构造器模式，subject 已被 MATCH_CONSTRUCTOR 弹出并替换为字段。
        对于没有测试操作码的模式（通配符、元组、列表等），在此处弹出。
        """
        if isinstance(pattern, PatternIdentifier):
            # 检查是否是已知的零字段 ADT 构造器
            if pattern.name in self._adt_constructors:
                _type_name, field_count = self._adt_constructors[pattern.name]
                if field_count == 0:
                    # 零字段构造器：MATCH_CONSTRUCTOR 已经弹出 subject 且没有字段
                    # 不需要做任何额外操作（栈上没有剩余值）
                    return
            self.bytecode.emit_op(Op.MATCH_BIND, pattern.name)
        elif isinstance(pattern, PatternWildcard):
            # 注意：通配符模式没有测试操作码，所以需要在这里弹出 subject
            self.bytecode.emit_op(Op.POP)  # 弹出 subject
        elif isinstance(pattern, PatternConstructor):
            # 字段已由 MATCH_CONSTRUCTOR 压栈（subject 已被弹出）
            for field_pattern in pattern.fields:
                self._compile_pattern_extract_and_bind(field_pattern)
        elif isinstance(pattern, (PatternInt, PatternFloat, PatternString,
                                  PatternBool, PatternChar)):
            # MATCH_TEST_* 已经弹出了 subject，不需要再弹
            pass
        elif isinstance(pattern, PatternTuple):
            # MATCH_TEST_TUPLE 已弹出 subject 并将各元素压栈（reversed）
            # 递归处理每个元素子模式
            for elem_pattern in pattern.elements:
                self._compile_pattern_extract_and_bind(elem_pattern)
        elif isinstance(pattern, PatternList):
            # MATCH_TEST_LIST 已弹出 subject 并将各元素压栈（reversed）
            # 递归处理每个元素子模式
            for elem_pattern in pattern.elements:
                self._compile_pattern_extract_and_bind(elem_pattern)
        else:
            self.bytecode.emit_op(Op.POP)

    def _compile_pattern_test(self, pattern):
        """编译模式测试指令，失败时跳转到 fail_ip"""
        if isinstance(pattern, PatternWildcard):
            self.bytecode.emit_op(Op.MATCH_WILDCARD)
            return

        elif isinstance(pattern, PatternInt):
            fail_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.MATCH_TEST_INT, pattern.value, 0)
            return fail_pos

        elif isinstance(pattern, PatternFloat):
            fail_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.MATCH_TEST_FLOAT, pattern.value, 0)
            return fail_pos

        elif isinstance(pattern, PatternBool):
            fail_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.MATCH_TEST_BOOL, pattern.value, 0)
            return fail_pos

        elif isinstance(pattern, PatternString):
            fail_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.MATCH_TEST_STRING, pattern.value, 0)
            return fail_pos

        elif isinstance(pattern, PatternChar):
            fail_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.MATCH_TEST_CHAR, pattern.value, 0)
            return fail_pos

        elif isinstance(pattern, PatternIdentifier):
            self.bytecode.emit_op(Op.MATCH_WILDCARD)
            return None

        elif isinstance(pattern, PatternConstructor):
            fail_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.MATCH_CONSTRUCTOR, pattern.name, len(pattern.fields), 0)
            return fail_pos

        elif isinstance(pattern, PatternTuple):
            self.bytecode.emit_op(Op.MATCH_WILDCARD)
            return None

        elif isinstance(pattern, PatternList):
            self.bytecode.emit_op(Op.MATCH_WILDCARD)
            return None

        else:
            self.bytecode.emit_op(Op.MATCH_WILDCARD)
            return None

    def _compile_pattern_bindings(self, pattern, has_subject_on_stack=True):
        """编译模式变量绑定"""
        if isinstance(pattern, PatternIdentifier):
            self.bytecode.emit_op(Op.MATCH_BIND, pattern.name)
        elif isinstance(pattern, PatternConstructor):
            for field_pattern in pattern.fields:
                self._compile_pattern_bindings(field_pattern, has_subject_on_stack=False)
        elif isinstance(pattern, PatternTuple):
            for elem_pattern in pattern.elements:
                self._compile_pattern_bindings(elem_pattern, has_subject_on_stack=False)
        elif isinstance(pattern, PatternList):
            for elem_pattern in pattern.elements:
                self._compile_pattern_bindings(elem_pattern, has_subject_on_stack=False)

    def _compile_block(self, expr: Block):
        """编译代码块"""
        for stmt in expr.statements:
            self._compile_expr(stmt)
            # 对于会留下值的语句（非绑定/赋值类），弹出结果
            # LetBinding / MutBinding / Assignment 已通过 STORE_VAR 弹出值，无需额外 POP
            # BreakExpr / ContinueExpr 不推值到栈上，无需 POP
            if not isinstance(stmt, (LetBinding, MutBinding, Assignment, BreakExpr, ContinueExpr)):
                self.bytecode.emit_op(Op.POP)
        if expr.tail_expression:
            self._compile_expr(expr.tail_expression)
        else:
            self.bytecode.emit_op(Op.CONST_UNIT)

    def _compile_for(self, expr: ForExpr):
        """编译 for 循环

        栈布局（非空循环）：
            FOR_ITER 前: [iterable, result_list]
            FOR_ITER 后: [iterable, result_list, current]
            STORE_VAR 后: [iterable, result_list]
            body 后:      [iterable, result_list, body_result]
            LOOP_END 后:  [iterable, result_list]

        空循环处理：
            FOR_ITER 发现无可迭代元素时，直接跳转到 loop_end 之后，
            此时栈上仅剩 [result_list]，LOOP_END 不会执行。
        """
        # 确定迭代器
        if isinstance(expr.iterable, tuple) and len(expr.iterable) >= 2 and expr.iterable[0] == "range":
            self._compile_expr(expr.iterable[1])  # start
            self._compile_expr(expr.iterable[2])  # end
            if len(expr.iterable) > 3 and expr.iterable[3] is not None:
                self._compile_expr(expr.iterable[3])
            else:
                self.bytecode.emit_op(Op.CONST_INT, 1)
            self.bytecode.emit_op(Op.BUILD_RANGE)
        else:
            self._compile_expr(expr.iterable)

        # 初始化结果列表
        self.bytecode.emit_op(Op.BUILD_LIST, 0)

        # loop_start: FOR_ITER
        loop_start = self.bytecode.current_pos()
        self.bytecode.emit_op(Op.FOR_ITER, 0)  # fail_ip 占位

        # 绑定循环变量（循环变量需要可变以支持每次迭代更新）
        self.bytecode.emit_op(Op.STORE_VAR, expr.var_name, True)

        # 此时栈: [iterable, result_list]
        # 编译循环体（block 保证栈顶有值）
        self._compile_expr(expr.body)

        # 此时栈: [iterable, result_list, body_result]
        # LOOP_END: 弹出 body_result, result_list, iterable;
        #           追加 body_result 到 result_list;
        #           压入 [iterable, result_list]; 跳回 loop_start
        self.bytecode.emit_op(Op.LOOP_END, loop_start)

        # 回填 FOR_ITER 的 fail_ip：空循环直接跳过 LOOP_END
        after_loop = self.bytecode.current_pos()
        self.bytecode.patch_jump(loop_start, after_loop)

    def _compile_while(self, expr: WhileExpr):
        """编译 while 循环"""
        loop_start = self.bytecode.current_pos()

        self._compile_expr(expr.condition)

        jump_to_end = self.bytecode.current_pos()
        self.bytecode.emit_op(Op.POP_JUMP_IF_FALSE, 0)

        self._compile_expr(expr.body)
        self.bytecode.emit_op(Op.POP)  # 弹出体结果

        self.bytecode.emit_op(Op.JUMP, loop_start)

        end_pos = self.bytecode.current_pos()
        self.bytecode.patch_jump(jump_to_end, end_pos)

        self.bytecode.emit_op(Op.CONST_UNIT)

    def _compile_list_comprehension(self, expr: ListComprehension):
        """编译列表推导式"""
        if isinstance(expr.iterable, tuple) and len(expr.iterable) >= 2 and expr.iterable[0] == "range":
            start_expr = expr.iterable[1]
            end_expr = expr.iterable[2]
            step_expr = expr.iterable[3] if len(expr.iterable) > 3 else None
            iterable = ("range", start_expr, end_expr, step_expr)
        else:
            iterable = expr.iterable

        if expr.filter_cond is None:
            # 无过滤条件：直接委托给 _compile_for
            for_expr = ForExpr(
                var_name=expr.var_name,
                iterable=iterable,
                body=expr.expr,
            )
            self._compile_for(for_expr)
            return

        # 有过滤条件：内联编译，filter 为 false 时跳过 LOOP_END 追加
        # 编译迭代器
        if isinstance(iterable, tuple) and iterable[0] == "range":
            self._compile_expr(iterable[1])  # start
            self._compile_expr(iterable[2])  # end
            if len(iterable) > 3 and iterable[3] is not None:
                self._compile_expr(iterable[3])
            else:
                self.bytecode.emit_op(Op.CONST_INT, 1)
            self.bytecode.emit_op(Op.BUILD_RANGE)
        else:
            self._compile_expr(iterable)

        # 初始化结果列表
        self.bytecode.emit_op(Op.BUILD_LIST, 0)

        # loop_start: FOR_ITER
        loop_start = self.bytecode.current_pos()
        self.bytecode.emit_op(Op.FOR_ITER, 0)  # fail_ip 占位

        # 绑定循环变量（循环变量需要可变以支持每次迭代更新）
        self.bytecode.emit_op(Op.STORE_VAR, expr.var_name, True)

        # 编译过滤条件
        self._compile_expr(expr.filter_cond)
        filter_fail = self.bytecode.current_pos()
        self.bytecode.emit_op(Op.POP_JUMP_IF_FALSE, 0)  # 过滤失败则跳过追加

        # 编译映射表达式
        self._compile_expr(expr.expr)

        # LOOP_END: 追加结果到列表，跳回 loop_start
        self.bytecode.emit_op(Op.LOOP_END, loop_start)

        # 过滤失败目标：跳回 loop_start（跳过追加）
        after_filter = self.bytecode.current_pos()
        self.bytecode.patch_jump(filter_fail, after_filter)
        self.bytecode.emit_op(Op.JUMP, loop_start)

        # 回填 FOR_ITER 的 fail_ip：空循环直接跳过
        after_loop = self.bytecode.current_pos()
        self.bytecode.patch_jump(loop_start, after_loop)


# ============================================================
# 字节码打印（调试用）
# ============================================================

def dump_bytecode(bytecode: Bytecode) -> str:
    """将字节码格式化为可读字符串"""
    lines = []
    lines.append("=== Nova Bytecode ===")
    lines.append(f"Constants ({len(bytecode.constants)}): {bytecode.constants}")
    lines.append(f"Functions: {list(bytecode.functions.keys())}")
    lines.append("")

    lines.append("Main code:")
    for i, instr in enumerate(bytecode.code):
        lines.append(f"  {i:4d}: {instr}")

    for name, func in bytecode.functions.items():
        lines.append("")
        lines.append(f"Function '{name}' (params={func.param_count}, names={func.param_names}):")
        lines.append(f"  Constants: {func.constants}")
        for i, instr in enumerate(func.code):
            lines.append(f"  {i:4d}: {instr}")

    return "\n".join(lines)
