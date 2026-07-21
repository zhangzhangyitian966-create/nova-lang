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

from typing import Any, Dict, List

from .ast_nodes import (
    AliasDef,
    Assignment,
    BinaryOp,
    Block,
    BoolLiteral,
    BreakExpr,
    CharLiteral,
    ContinueExpr,
    FieldAccess,
    FloatLiteral,
    FnCall,
    FnDef,
    ForExpr,
    Identifier,
    IfExpr,
    IntLiteral,
    Lambda,
    LetBinding,
    ListComprehension,
    ListExpr,
    MapExpr,
    MatchExpr,
    MutBinding,
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

# ============================================================
# 指令定义
# ============================================================


class Op:
    """字节码操作码"""

    # 常量与加载
    CONST_INT = "CONST_INT"  # operands: (value,)
    CONST_FLOAT = "CONST_FLOAT"  # operands: (value,)
    CONST_STRING = "CONST_STRING"  # operands: (value,)
    CONST_BOOL = "CONST_BOOL"  # operands: (value,)
    CONST_UNIT = "CONST_UNIT"  # operands: ()
    LOAD_CONST = "LOAD_CONST"  # operands: (index,)
    LOAD_VAR = "LOAD_VAR"  # operands: (name,)
    STORE_VAR = "STORE_VAR"  # operands: (name, mutable)

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
    JUMP = "JUMP"  # operands: (target_ip,)
    JUMP_IF_FALSE = "JUMP_IF_FALSE"  # operands: (target_ip,)
    JUMP_IF_TRUE = "JUMP_IF_TRUE"  # operands: (target_ip,)
    POP_JUMP_IF_FALSE = "POP_JUMP_IF_FALSE"  # operands: (target_ip,)
    LOOP = "LOOP"  # operands: (loop_start_ip,) - 标记循环继续跳回
    LOOP_END = "LOOP_END"  # operands: (loop_start_ip,) - 循环结束/继续跳回
    BREAK = "BREAK"
    CONTINUE = "CONTINUE"

    # 函数
    CLOSURE = "CLOSURE"  # operands: (func_name, param_count, code_key)
    CALL = "CALL"  # operands: (arg_count,)
    RETURN = "RETURN"
    CALL_BUILTIN = "CALL_BUILTIN"  # operands: (name, arg_count)

    # 数据结构
    BUILD_LIST = "BUILD_LIST"  # operands: (count,)
    BUILD_TUPLE = "BUILD_TUPLE"  # operands: (count,)
    BUILD_MAP = "BUILD_MAP"  # operands: (count,)
    INDEX = "INDEX"
    FIELD_ACCESS = "FIELD_ACCESS"  # operands: (field_name,)
    BUILD_RANGE = "BUILD_RANGE"  # operands: () - 从栈上弹出 start, end, [step]
    FOR_ITER = "FOR_ITER"  # operands: (loop_start_ip,) - 迭代一步

    # 模式匹配
    MATCH_START = "MATCH_START"  # operands: (arm_count,)
    MATCH_TEST_INT = "MATCH_TEST_INT"  # operands: (value, fail_ip,)
    MATCH_TEST_BOOL = "MATCH_TEST_BOOL"  # operands: (value, fail_ip,)
    MATCH_TEST_STRING = "MATCH_TEST_STRING"  # operands: (value, fail_ip,)
    MATCH_BIND = "MATCH_BIND"  # operands: (name,)
    MATCH_WILDCARD = "MATCH_WILDCARD"
    MATCH_CONSTRUCTOR = "MATCH_CONSTRUCTOR"  # operands: (name, field_count, fail_ip,)
    MATCH_END = "MATCH_END"

    # 管道
    PIPE_CALL = "PIPE_CALL"  # operands: (arg_count,)

    # ADT
    MAKE_ADT = "MAKE_ADT"  # operands: (type_name, variant_name, field_count,)
    REGISTER_CTOR = (
        "REGISTER_CTOR"  # operands: (type_name, variant_name, field_count, name)
    )

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

    def __init__(
        self,
        name: str,
        param_count: int,
        code: List[Instruction],
        constants: List[Any],
        param_names: List[str] = None,
    ):
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
            self.code[pos] = Instruction(
                instr.opcode, instr.operands[0], instr.operands[1], fail_ip
            )
        elif len(instr.operands) == 2:
            self.code[pos] = Instruction(instr.opcode, instr.operands[0], fail_ip)


# ============================================================
# 编译器
# ============================================================


class BytecodeCompiler:
    """AST 到字节码的编译器"""

    def __init__(self):
        self.bytecode = Bytecode()
        self._builtin_names: set = set()
        self._init_builtin_names()

    def _init_builtin_names(self):
        """初始化内置函数名称集合"""
        self._builtin_names = {
            "print",
            "read_line",
            "int_to_str",
            "float_to_str",
            "str_to_int",
            "str_len",
            "list_length",
            "filter",
            "map",
            "sum",
            "head",
            "tail",
            "read_file",
            "write_file",
            "file_exists",
            "list_dir",
            "json_parse",
            "json_stringify",
            "abs",
            "sqrt",
            "pow",
            "log",
            "log10",
            "exp",
            "sin",
            "cos",
            "tan",
            "floor",
            "ceil",
            "round",
            "min",
            "max",
            "pi",
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
        if isinstance(decl, TypeDef):
            for variant in decl.variants:
                if variant.fields:
                    # 带字段的构造器 -> 注册构造函数
                    self.bytecode.emit_op(
                        Op.REGISTER_CTOR,
                        decl.name,
                        variant.name,
                        len(variant.fields),
                        variant.name,
                    )
                    self.bytecode.emit_op(Op.STORE_VAR, variant.name, False)
                else:
                    # 无字段构造器 -> 创建 ADT 值
                    self.bytecode.emit_op(Op.MAKE_ADT, decl.name, variant.name, 0)
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

        func_block = FunctionBlock(
            fn_name, param_count, fn_code, fn_consts, param_names
        )
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
                self.bytecode.emit_op(Op.MAKE_ADT, "Option", "None", 0)
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
            jump_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.POP_JUMP_IF_FALSE, 0)
            self._compile_expr(expr.right)
            end_pos = self.bytecode.current_pos()
            self.bytecode.patch_jump(jump_pos, end_pos)
            return

        if op == "||":
            self._compile_expr(expr.left)
            jump_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.JUMP_IF_TRUE, 0)
            # 如果 left 为 true，需要在栈上保留 true
            # JUMP_IF_TRUE 不弹出，所以跳到 end 即可
            self._compile_expr(expr.right)
            end_pos = self.bytecode.current_pos()
            self.bytecode.patch_jump(jump_pos, end_pos)
            return

        self._compile_expr(expr.left)
        self._compile_expr(expr.right)

        op_map = {
            "+": Op.ADD,
            "-": Op.SUB,
            "*": Op.MUL,
            "/": Op.DIV,
            "%": Op.MOD,
            "++": Op.CONCAT,
            "==": Op.EQ,
            "!=": Op.NEQ,
            "<": Op.LT,
            ">": Op.GT,
            "<=": Op.LTE,
            ">=": Op.GTE,
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
                    self.bytecode.emit_op(Op.MAKE_ADT, "Option", "Some", arg_count)
                elif name == "Ok":
                    self.bytecode.emit_op(Op.MAKE_ADT, "Result", "Ok", arg_count)
                elif name == "Err":
                    self.bytecode.emit_op(Op.MAKE_ADT, "Result", "Err", arg_count)
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
        func_block = FunctionBlock(
            lambda_name, param_count, fn_code, fn_consts, param_names
        )
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
        fail_patches = []  # [(patch_pos,)]
        # fail_patches[i] 是 arm i 的 MATCH_TEST_* 的失败跳转占位位置

        for i, arm in enumerate(expr.arms):
            # 模式测试：匹配失败时跳到下一个 arm 的测试开始
            # 记录当前指令位置
            fail_ip_pos = self._compile_pattern_test_with_fail(arm.pattern)

            # 匹配成功 -> subject 在栈上
            # 编译匹配体的绑定（从 subject 中提取值）
            self._compile_pattern_extract_and_bind(arm.pattern)

            # 编译匹配体
            self._compile_expr(arm.body)

            # 跳到 match 结束
            jump_end = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.JUMP, 0)
            jump_to_end_positions.append(jump_end)

            # 记录 fail 跳转位置（稍后回填）
            if fail_ip_pos is not None:
                fail_patches.append((fail_ip_pos, self.bytecode.current_pos()))

        # 回填所有失败跳转
        for patch_pos, target in fail_patches:
            self.bytecode.patch_match_fail(patch_pos, target)

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

        elif isinstance(pattern, PatternBool):
            fail_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.MATCH_TEST_BOOL, pattern.value, 0)
            return fail_pos

        elif isinstance(pattern, PatternString):
            fail_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(Op.MATCH_TEST_STRING, pattern.value, 0)
            return fail_pos

        elif isinstance(pattern, PatternIdentifier):
            return None  # 变量绑定总是匹配

        elif isinstance(pattern, PatternConstructor):
            fail_pos = self.bytecode.current_pos()
            self.bytecode.emit_op(
                Op.MATCH_CONSTRUCTOR, pattern.name, len(pattern.fields), 0
            )
            return fail_pos

        elif isinstance(pattern, (PatternTuple, PatternList)):
            return None  # 简化处理

        else:
            return None

    def _compile_pattern_extract_and_bind(self, pattern):
        """
        从 subject 中提取值并绑定到变量。
        subject 在栈顶。对于非构造器模式，弹出 subject。
        对于构造器模式，subject 已被 MATCH_CONSTRUCTOR 弹出并替换为字段。
        """
        if isinstance(pattern, PatternIdentifier):
            self.bytecode.emit_op(Op.MATCH_BIND, pattern.name)
        elif isinstance(pattern, PatternWildcard):
            self.bytecode.emit_op(Op.POP)  # 弹出 subject
        elif isinstance(pattern, PatternConstructor):
            # 字段已由 MATCH_CONSTRUCTOR 压栈（subject 已被弹出）
            for field_pattern in pattern.fields:
                self._compile_pattern_extract_and_bind(field_pattern)
        elif isinstance(
            pattern, (PatternInt, PatternFloat, PatternString, PatternBool, PatternChar)
        ):
            self.bytecode.emit_op(Op.POP)  # 弹出 subject
        elif isinstance(pattern, (PatternTuple, PatternList)):
            self.bytecode.emit_op(Op.POP)
        else:
            self.bytecode.emit_op(Op.POP)

    def _compile_block(self, expr: Block):
        """编译代码块"""
        for stmt in expr.statements:
            self._compile_expr(stmt)
        if expr.tail_expression:
            self._compile_expr(expr.tail_expression)
        else:
            self.bytecode.emit_op(Op.CONST_UNIT)

    def _compile_for(self, expr: ForExpr):
        """编译 for 循环"""
        # 确定迭代器
        if (
            isinstance(expr.iterable, tuple)
            and len(expr.iterable) >= 2
            and expr.iterable[0] == "range"
        ):
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

        # 绑定循环变量
        self.bytecode.emit_op(Op.STORE_VAR, expr.var_name, False)

        # 此时栈: [iterable, result_list]
        # 编译循环体
        self._compile_expr(expr.body)

        # 此时栈: [iterable, result_list, body_result]
        # LOOP_END: 弹出 body_result, result_list, iterable;
        #           追加 body_result 到 result_list;
        #           压入 [iterable, result_list]; 跳回 loop_start
        self.bytecode.emit_op(Op.LOOP_END, loop_start)

        # 回填 FOR_ITER 的 fail_ip
        end_pos = self.bytecode.current_pos()
        self.bytecode.patch_jump(loop_start, end_pos)

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
        if (
            isinstance(expr.iterable, tuple)
            and len(expr.iterable) >= 2
            and expr.iterable[0] == "range"
        ):
            start_expr = expr.iterable[1]
            end_expr = expr.iterable[2]
            step_expr = expr.iterable[3] if len(expr.iterable) > 3 else None
            iterable = ("range", start_expr, end_expr, step_expr)
        else:
            iterable = expr.iterable

        for_expr = ForExpr(
            var_name=expr.var_name,
            iterable=iterable,
            body=expr.expr,
        )
        self._compile_for(for_expr)


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
        lines.append(
            f"Function '{name}' (params={func.param_count}, names={func.param_names}):"
        )
        lines.append(f"  Constants: {func.constants}")
        for i, instr in enumerate(func.code):
            lines.append(f"  {i:4d}: {instr}")

    return "\n".join(lines)
