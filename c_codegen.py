"""
Nova 编程语言 - C 代码生成器

将 Nova AST 编译为 C 源代码，然后通过系统的 C 编译器（gcc/clang/MSVC）
生成原生二进制文件。

架构：
  Nova 源码 → Lexer → Parser → Type Checker → CCodeGen → C 源码 → gcc/clang/MSVC → 原生二进制
"""

from typing import Dict, List, Optional, Set, Tuple

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
    Param,
    PatternBool,
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

# ============================================================
# C 关键字集合
# ============================================================

C_KEYWORDS: Set[str] = {
    "auto",
    "break",
    "case",
    "char",
    "const",
    "continue",
    "default",
    "do",
    "double",
    "else",
    "enum",
    "extern",
    "float",
    "for",
    "goto",
    "if",
    "inline",
    "int",
    "long",
    "register",
    "restrict",
    "return",
    "short",
    "signed",
    "sizeof",
    "static",
    "struct",
    "switch",
    "typedef",
    "union",
    "unsigned",
    "void",
    "volatile",
    "while",
    "_Alignas",
    "_Alignof",
    "_Atomic",
    "_Bool",
    "_Complex",
    "_Generic",
    "_Imaginary",
    "_Noreturn",
    "_Static_assert",
    "_Thread_local",
    # C 标准库宏/类型名
    "NULL",
    "true",
    "false",
    "bool",
    "int64_t",
    "uint64_t",
    "size_t",
    "ptrdiff_t",
    "intptr_t",
    "uintptr_t",
    "stdin",
    "stdout",
    "stderr",
    "EOF",
    "FILE",
    "main",
    "printf",
    "fprintf",
    "sprintf",
    "snprintf",
    "malloc",
    "calloc",
    "realloc",
    "free",
    "memcpy",
    "memmove",
    "memset",
    "memcmp",
    "strcmp",
    "strcpy",
    "strncpy",
    "strlen",
    "strcat",
    "strncat",
    "exit",
    "abort",
    "assert",
    "nova_string_new",
    "nova_string_concat",
    "nova_string_free",
    "nova_list_new",
    "nova_list_push",
    "nova_list_free",
    "nova_list_get",
    "nova_list_length",
    "nova_list_filter",
    "nova_list_map",
    "nova_map_new",
    "nova_map_free",
    "nova_map_get",
    "nova_map_set",
    "nova_closure_new",
    "nova_closure_call",
    "nova_adt_new",
    "nova_adt_free",
    "nova_adt_variant",
    "nova_adt_get_field",
    "nova_init",
    "nova_cleanup",
    "NovaString",
    "NovaList",
    "NovaMap",
    "NovaClosure",
    "NovaADT",
}


# ============================================================
# C 代码生成器
# ============================================================


class CCodeGen:
    """将 Nova AST 编译为 C 源代码"""

    def __init__(self):
        self.output_lines: List[str] = []
        self.indent_level: int = 0
        self.temp_counter: int = 0
        self.global_vars: List[str] = []
        self.functions: List[str] = []
        self.forward_decls: List[str] = []
        self.type_defs: List[str] = []
        self.current_context: str = "global"  # global / function / block
        self.adt_info: Dict[str, List[Tuple[str, List[str]]]] = (
            {}
        )  # adt_name -> [(variant_name, [field_names])]
        self.adt_field_types: Dict[str, Dict[str, List[str]]] = (
            {}
        )  # adt_name -> {variant_name -> [field_type_strings]}
        self._main_fn_name: Optional[str] = None

    # ----------------------------------------------------------
    # 公开接口
    # ----------------------------------------------------------

    def generate(self, program: Program) -> str:
        """生成完整的 C 源代码"""
        # 重置状态
        self.output_lines = []
        self.indent_level = 0
        self.temp_counter = 0
        self.global_vars = []
        self.functions = []
        self.forward_decls = []
        self.type_defs = []
        self.adt_info = {}
        self.adt_field_types = {}
        self._main_fn_name = None

        # 第一遍：收集类型定义和前向声明
        for decl in program.declarations:
            self._collect_decl_info(decl)

        # 第二遍：生成代码
        self._emit_header()

        # 类型定义
        for line in self.type_defs:
            self._emit(line)
        if self.type_defs:
            self._emit("")

        # 前向声明
        for line in self.forward_decls:
            self._emit(line)
        if self.forward_decls:
            self._emit("")

        # 全局变量
        for line in self.global_vars:
            self._emit(line)
        if self.global_vars:
            self._emit("")

        # 函数定义
        for line in self.functions:
            self._emit(line)
        if self.functions:
            self._emit("")

        # main 函数
        self._gen_main_function(program)

        return "\n".join(self.output_lines) + "\n"

    # ----------------------------------------------------------
    # 头部和 main 生成
    # ----------------------------------------------------------

    def _emit_header(self):
        """输出 #include 和运行时头文件"""
        self._emit('#include "nova_runtime.h"')
        self._emit("#include <stdio.h>")
        self._emit("#include <stdlib.h>")
        self._emit("#include <stdint.h>")
        self._emit("#include <stdbool.h>")
        self._emit("")

    def _gen_main_function(self, program: Program):
        """生成 C main 函数"""
        self._emit("int main(int argc, char** argv) {")
        self.indent_level += 1

        self._emit("nova_init();")

        # 生成顶层声明的代码（在 main 中执行）
        for decl in program.declarations:
            if isinstance(decl, (ImportDecl, ExportDecl, TypeDef, AliasDef, FnDef)):
                continue
            self._compile_decl_in_main(decl)

        # 如果有 main 函数则调用
        if self._main_fn_name:
            self._emit(f"{self._mangle_fn_name(self._main_fn_name)}();")

        self._emit("nova_cleanup();")
        self._emit("return 0;")
        self.indent_level -= 1
        self._emit("}")

    # ----------------------------------------------------------
    # 第一遍：收集信息
    # ----------------------------------------------------------

    def _collect_decl_info(self, decl):
        """第一遍收集类型信息、前向声明、全局变量和函数"""
        if isinstance(decl, TypeDef):
            self._collect_type_def(decl)
        elif isinstance(decl, AliasDef):
            pass  # C 中使用 typedef
        elif isinstance(decl, FnDef):
            self._collect_fn_def(decl)
        elif isinstance(decl, LetBinding):
            c_name = self._mangle_name(decl.name)
            c_type = self._infer_c_type_from_expr(decl.value)
            self.global_vars.append(f"{c_type} {c_name};")
        elif isinstance(decl, MutBinding):
            c_name = self._mangle_name(decl.name)
            c_type = self._infer_c_type_from_expr(decl.value)
            self.global_vars.append(f"{c_type} {c_name};")
        elif isinstance(decl, (ImportDecl, ExportDecl)):
            pass

    def _collect_type_def(self, typedef: TypeDef):
        """收集 ADT 类型定义，生成 C 结构体和枚举"""
        name = typedef.name
        variants = typedef.variants
        self.adt_info[name] = [(v.name, [f[0] for f in v.fields]) for v in variants]

        # 生成枚举标识变体
        enum_values = ", ".join(f"NOVA_ADT_{name}_{v.name}" for v in variants)
        self.type_defs.append(f"enum NovaADT_{name}_Tag {{ {enum_values} }};")
        self.type_defs.append(f"typedef enum NovaADT_{name}_Tag NovaADT_{name}_Tag;")

        # 生成包含所有字段的最大联合体结构体
        all_fields = []
        for v in variants:
            for fname, ftype in v.fields:
                all_fields.append((f"{v.name}_{fname}", ftype))

        # 记录字段类型信息
        self.adt_field_types[name] = {}
        for v in variants:
            c_field_types = []
            for fname, ftype in v.fields:
                c_field_types.append(self._c_type_from_type_expr(ftype))
            self.adt_field_types[name][v.name] = c_field_types

        if all_fields:
            struct_fields = ["    NovaADT_%s_Tag tag;" % name]
            for field_cname, ftype in all_fields:
                c_ftype = self._c_type_from_type_expr(ftype)
                struct_fields.append(f"    {c_ftype} {field_cname};")
            struct_body = "\n".join(struct_fields)
            self.type_defs.append(
                f"typedef struct {{\n{struct_body}\n}} NovaADT_{name};"
            )
        else:
            # 无字段的枚举，仅用 tag
            self.type_defs.append(
                f"typedef struct {{ NovaADT_{name}_Tag tag; }} NovaADT_{name};"
            )

    def _collect_fn_def(self, fndef: FnDef):
        """收集函数定义信息"""
        c_name = self._mangle_fn_name(fndef.name)

        # 判断返回类型
        if fndef.name == "main":
            self._main_fn_name = fndef.name

        ret_type = "void"
        if fndef.return_type:
            ret_type = self._c_type_from_type_expr(fndef.return_type)
        else:
            ret_type = "void"

        params_str = self._gen_fn_params(fndef.params)
        self.forward_decls.append(f"{ret_type} {c_name}({params_str});")

        # 生成函数体
        self.functions.append(self._gen_fn_definition(fndef, c_name, ret_type))

    # ----------------------------------------------------------
    # 函数生成
    # ----------------------------------------------------------

    def _gen_fn_definition(self, fndef: FnDef, c_name: str, ret_type: str) -> str:
        """生成完整的 C 函数定义"""
        old_context = self.current_context
        self.current_context = "function"

        params_str = self._gen_fn_params(fndef.params)
        lines = [f"{ret_type} {c_name}({params_str}) {{"]
        self.indent_level = 1

        # 编译函数体
        body_code = self._compile_expr(fndef.body)

        # 如果函数返回非 void，需要 return
        if ret_type != "void" and isinstance(fndef.body, Block):
            # 检查 body 是否以 tail expression 结尾
            lines.append(self._indent_str(body_code))
            # 添加 return 尾表达式
            if fndef.body.tail_expression:
                tail_c = self._compile_expr(fndef.body.tail_expression)
                lines.append(self._indent_str(f"return {tail_c};"))
        elif ret_type != "void":
            lines.append(self._indent_str(f"return {body_code};"))
        else:
            # void 函数
            if isinstance(fndef.body, Block):
                lines.append(self._indent_str(body_code))
                if fndef.body.tail_expression:
                    tail_c = self._compile_expr(fndef.body.tail_expression)
                    lines.append(self._indent_str(f"{tail_c};"))
            else:
                lines.append(self._indent_str(f"{body_code};"))

        lines.append("}")

        self.indent_level = 0
        self.current_context = old_context
        return "\n".join(lines)

    def _gen_fn_params(self, params: List[Param]) -> str:
        """生成 C 函数参数列表"""
        if not params:
            return "void"
        parts = []
        for p in params:
            c_type = "int64_t"  # 默认类型
            if p.type_annotation:
                c_type = self._c_type_from_type_expr(p.type_annotation)
            c_name = self._mangle_name(p.name)
            parts.append(f"{c_type} {c_name}")
        return ", ".join(parts)

    # ----------------------------------------------------------
    # 顶层声明编译（在 main 函数中）
    # ----------------------------------------------------------

    def _compile_decl_in_main(self, decl):
        """在 main 函数中编译顶层声明"""
        if isinstance(decl, LetBinding):
            c_name = self._mangle_name(decl.name)
            value_c = self._compile_expr(decl.value)
            self._emit(f"{c_name} = {value_c};")
        elif isinstance(decl, MutBinding):
            c_name = self._mangle_name(decl.name)
            value_c = self._compile_expr(decl.value)
            self._emit(f"{c_name} = {value_c};")
        elif isinstance(decl, ForExpr):
            self._compile_for_expr_main(decl)
        elif isinstance(decl, WhileExpr):
            cond_c = self._compile_expr(decl.condition)
            self._emit(f"while ({cond_c}) {{")
            self.indent_level += 1
            body_c = self._compile_expr(decl.body)
            if isinstance(decl.body, Block):
                self._emit(body_c)
            else:
                self._emit(f"{body_c};")
            self.indent_level -= 1
            self._emit("}")
        else:
            # 顶层表达式
            expr_c = self._compile_expr(decl)
            self._emit(f"{expr_c};")

    def _compile_for_expr_main(self, for_expr: ForExpr):
        """在 main 中编译顶层 for 循环"""
        var_name = self._mangle_name(for_expr.var_name)
        iterable = for_expr.iterable

        if isinstance(iterable, tuple) and iterable[0] == "range":
            # for i <- start..end
            start_c = self._compile_expr(iterable[1])
            end_c = self._compile_expr(iterable[2])
            step_c = self._compile_expr(iterable[3]) if iterable[3] else "1"

            i_var = self._new_temp()
            self._emit(
                f"for (int64_t {i_var} = {start_c}; {i_var} < {end_c}; {i_var} += {step_c}) {{"
            )
            self.indent_level += 1
            self._emit(f"int64_t {var_name} = {i_var};")
            body_c = self._compile_expr(for_expr.body)
            if isinstance(for_expr.body, Block):
                self._emit(body_c)
            else:
                self._emit(f"{body_c};")
            self.indent_level -= 1
            self._emit("}")
        else:
            # for x in list
            list_c = self._compile_expr(iterable)
            list_var = self._new_temp()
            self._emit(f"NovaList* {list_var} = {list_c};")
            idx_var = self._new_temp()
            len_var = self._new_temp()
            self._emit(f"int64_t {len_var} = nova_list_length({list_var});")
            self._emit(
                f"for (int64_t {idx_var} = 0; {idx_var} < {len_var}; {idx_var}++) {{"
            )
            self.indent_level += 1
            # 默认元素类型为 int64_t
            self._emit(
                f"int64_t {var_name} = (int64_t)(intptr_t)nova_list_get({list_var}, {idx_var});"
            )
            body_c = self._compile_expr(for_expr.body)
            if isinstance(for_expr.body, Block):
                self._emit(body_c)
            else:
                self._emit(f"{body_c};")
            self.indent_level -= 1
            self._emit("}")

    # ----------------------------------------------------------
    # 声明编译
    # ----------------------------------------------------------

    def _compile_decl(self, decl) -> str:
        """编译顶层声明为 C 代码片段"""
        if isinstance(decl, LetBinding):
            c_name = self._mangle_name(decl.name)
            value_c = self._compile_expr(decl.value)
            return f"{c_name} = {value_c};"
        elif isinstance(decl, MutBinding):
            c_name = self._mangle_name(decl.name)
            value_c = self._compile_expr(decl.value)
            return f"{c_name} = {value_c};"
        elif isinstance(decl, Assignment):
            c_name = self._mangle_name(decl.name)
            value_c = self._compile_expr(decl.value)
            return f"{c_name} = {value_c};"
        else:
            return self._compile_expr(decl)

    # ----------------------------------------------------------
    # 表达式编译
    # ----------------------------------------------------------

    def _compile_expr(self, expr) -> str:
        """编译表达式，返回 C 表达式字符串"""

        if isinstance(expr, IntLiteral):
            return f"((int64_t){expr.value})"

        elif isinstance(expr, FloatLiteral):
            return f"((double){repr(expr.value)})"

        elif isinstance(expr, StringLiteral):
            escaped = self._escape_c_string(expr.value)
            return f'nova_string_new("{escaped}")'

        elif isinstance(expr, CharLiteral):
            escaped = self._escape_c_char(expr.value)
            return f"'{escaped}'"

        elif isinstance(expr, BoolLiteral):
            return "true" if expr.value else "false"

        elif isinstance(expr, UnitLiteral):
            return "((void)0)"

        elif isinstance(expr, Identifier):
            return self._mangle_name(expr.name)

        elif isinstance(expr, BinaryOp):
            return self._compile_binary_op(expr)

        elif isinstance(expr, UnaryOp):
            return self._compile_unary_op(expr)

        elif isinstance(expr, IfExpr):
            return self._compile_if_expr(expr)

        elif isinstance(expr, MatchExpr):
            return self._compile_match_expr(expr)

        elif isinstance(expr, FnCall):
            return self._compile_fn_call(expr)

        elif isinstance(expr, Lambda):
            return self._compile_lambda(expr)

        elif isinstance(expr, PipeExpr):
            return self._compile_pipe_expr(expr)

        elif isinstance(expr, LetBinding):
            return self._compile_let_binding_expr(expr)

        elif isinstance(expr, MutBinding):
            return self._compile_mut_binding_expr(expr)

        elif isinstance(expr, Assignment):
            c_name = self._mangle_name(expr.name)
            value_c = self._compile_expr(expr.value)
            return f"({c_name} = {value_c})"

        elif isinstance(expr, Block):
            return self._compile_block(expr)

        elif isinstance(expr, ListExpr):
            return self._compile_list_expr(expr)

        elif isinstance(expr, ListComprehension):
            return self._compile_list_comprehension(expr)

        elif isinstance(expr, TupleExpr):
            return self._compile_tuple_expr(expr)

        elif isinstance(expr, MapExpr):
            return self._compile_map_expr(expr)

        elif isinstance(expr, FieldAccess):
            return self._compile_field_access(expr)

        elif isinstance(expr, ForExpr):
            return self._compile_for_expr(expr)

        elif isinstance(expr, WhileExpr):
            return self._compile_while_expr(expr)

        elif isinstance(expr, BreakExpr):
            return "break"

        elif isinstance(expr, ContinueExpr):
            return "continue"

        elif isinstance(expr, TryExpr):
            return self._compile_expr(expr.expr)

        elif isinstance(expr, (ImportDecl, ExportDecl)):
            return ""

        elif isinstance(expr, TypeDef):
            return ""

        elif isinstance(expr, AliasDef):
            return ""

        elif isinstance(expr, FnDef):
            # 嵌套函数定义——生成闭包
            return self._compile_nested_fn_def(expr)

        else:
            return f"/* unhandled: {type(expr).__name__} */"

    # ----------------------------------------------------------
    # 字面量和基本表达式
    # ----------------------------------------------------------

    def _compile_binary_op(self, expr: BinaryOp) -> str:
        """编译二元操作"""
        left_c = self._compile_expr(expr.left)
        right_c = self._compile_expr(expr.right)

        if expr.op == "++":
            # 字符串拼接
            return f"nova_string_concat({left_c}, {right_c})"

        # 普通二元操作符
        op_map = {
            "+": "+",
            "-": "-",
            "*": "*",
            "/": "/",
            "%": "%",
            "==": "==",
            "!=": "!=",
            "<": "<",
            ">": ">",
            "<=": "<=",
            ">=": ">=",
            "&&": "&&",
            "||": "||",
        }
        c_op = op_map.get(expr.op, expr.op)
        return f"({left_c} {c_op} {right_c})"

    def _compile_unary_op(self, expr: UnaryOp) -> str:
        """编译一元操作"""
        operand_c = self._compile_expr(expr.operand)
        if expr.op == "-":
            return f"(-{operand_c})"
        elif expr.op == "!":
            return f"(!{operand_c})"
        return f"({expr.op}{operand_c})"

    def _compile_if_expr(self, expr: IfExpr) -> str:
        """编译 if-then-else 表达式"""
        cond_c = self._compile_expr(expr.condition)

        if expr.else_branch is not None:
            then_c = self._compile_expr(expr.then_branch)
            else_c = self._compile_expr(expr.else_branch)
            # 使用三元运算符
            return f"({cond_c} ? {then_c} : {else_c})"
        else:
            # 无 else 分支：生成 if 语句块字符串
            then_c = self._compile_expr(expr.then_branch)
            lines = []
            lines.append(f"if ({cond_c}) {{")
            lines.append(f"    {then_c};")
            lines.append(f"}}")
            return "\n".join(lines)

    def _compile_match_expr(self, expr: MatchExpr) -> str:
        """编译 match 表达式为 if-else 链"""
        subject_c = self._compile_expr(expr.subject)
        subject_tmp = self._new_temp()

        lines = []
        lines.append(f"{{")
        lines.append(
            f"    {self._infer_c_type_from_expr(expr.subject)} {subject_tmp} = {subject_c};"
        )

        for i, arm in enumerate(expr.arms):
            pattern_c, bindings = self._compile_pattern(arm.pattern, subject_tmp, expr)

            # 生成条件
            lines.append(f"    {'if' if i == 0 else '} else if'} ({pattern_c}) {{")

            # 绑定变量
            for bind_name, bind_expr in bindings:
                c_name = self._mangle_name(bind_name)
                lines.append(
                    f"        {self._infer_c_type_from_expr(expr.subject)} {c_name} = {bind_expr};"
                )

            # 分支体
            body_c = self._compile_expr(arm.body)
            if arm.guard:
                guard_c = self._compile_expr(arm.guard)
                lines.append(f"        if ({guard_c}) {{ {body_c}; }}")
            else:
                lines.append(f"        {body_c};")

            lines.append(f"    }}")

        lines.append(f"}}")

        return "\n".join(lines)

    def _compile_pattern(
        self, pattern, subject_var: str, match_expr: MatchExpr
    ) -> Tuple[str, List[Tuple[str, str]]]:
        """编译模式，返回 (条件字符串, 绑定列表 [(name, c_expr)])"""
        bindings = []

        if isinstance(pattern, PatternWildcard):
            return ("1", bindings)  # 总是匹配

        elif isinstance(pattern, PatternInt):
            return (f"{subject_var} == ((int64_t){pattern.value})", bindings)

        elif isinstance(pattern, PatternFloat):
            return (f"{subject_var} == ((double){repr(pattern.value)})", bindings)

        elif isinstance(pattern, PatternString):
            escaped = self._escape_c_string(pattern.value)
            return (
                f'nova_string_eq({subject_var}, nova_string_new("{escaped}"))',
                bindings,
            )

        elif isinstance(pattern, PatternBool):
            return (
                f"{subject_var} == ({'true' if pattern.value else 'false'})",
                bindings,
            )

        elif isinstance(pattern, PatternIdentifier):
            # 变量绑定模式
            bindings.append((pattern.name, subject_var))
            return ("1", bindings)

        elif isinstance(pattern, PatternConstructor):
            # ADT 构造器模式
            conds = []
            # 判断 tag
            conds.append(
                f"{subject_var}.tag == NOVA_ADT_{self._find_adt_name(pattern.name)}_{pattern.name}"
            )
            # 绑定字段
            for i, field_pat in enumerate(pattern.fields):
                field_accessor = f"{subject_var}.{pattern.name}__field{i}"
                field_conds, field_bindings = self._compile_pattern(
                    field_pat, field_accessor, match_expr
                )
                conds.append(field_conds)
                bindings.extend(field_bindings)

            return (" && ".join(conds), bindings)

        elif isinstance(pattern, PatternTuple):
            conditions = []
            for i, elem_pat in enumerate(pattern.elements):
                elem_accessor = f"nova_tuple_get({subject_var}, {i})"
                elem_conds, elem_bindings = self._compile_pattern(
                    elem_pat, elem_accessor, match_expr
                )
                conditions.append(elem_conds)
                bindings.extend(elem_bindings)
            return (" && ".join(conditions) if conditions else "1", bindings)

        elif isinstance(pattern, PatternList):
            conditions = []
            conditions.append(
                f"nova_list_length({subject_var}) == {len(pattern.elements)}"
            )
            for i, elem_pat in enumerate(pattern.elements):
                elem_accessor = f"nova_list_get({subject_var}, {i})"
                elem_conds, elem_bindings = self._compile_pattern(
                    elem_pat, elem_accessor, match_expr
                )
                conditions.append(elem_conds)
                bindings.extend(elem_bindings)
            return (" && ".join(conditions), bindings)

        else:
            return ("1", bindings)

    def _find_adt_name(self, constructor_name: str) -> str:
        """根据构造器名称查找对应的 ADT 名称"""
        for adt_name, variants in self.adt_info.items():
            for vname, _ in variants:
                if vname == constructor_name:
                    return adt_name
        return "Unknown"

    def _compile_fn_call(self, expr: FnCall) -> str:
        """编译函数调用"""
        # 检查是否是 ADT 构造器调用
        if isinstance(expr.callee, Identifier):
            callee_name = expr.callee.name
            # 检查是否是 ADT 构造器
            adt_name = self._find_adt_name(callee_name)
            if adt_name != "Unknown" and callee_name in [
                v[0] for v in self.adt_info.get(adt_name, [])
            ]:
                return self._compile_adt_constructor(adt_name, callee_name, expr.args)

            # 内置函数特殊处理
            if callee_name == "print":
                if expr.args:
                    arg_c = self._compile_expr(expr.args[0])
                    return f"nova_print({arg_c})"
                return "((void)0)"

            if callee_name == "println":
                if expr.args:
                    arg_c = self._compile_expr(expr.args[0])
                    return f"nova_println({arg_c})"
                return 'nova_print(nova_string_new("\\n"))'

            if callee_name == "int_to_str":
                arg_c = self._compile_expr(expr.args[0])
                return f"nova_int_to_string({arg_c})"

            if callee_name == "float_to_str":
                arg_c = self._compile_expr(expr.args[0])
                return f"nova_float_to_string({arg_c})"

            if callee_name == "str_len":
                arg_c = self._compile_expr(expr.args[0])
                return f"nova_string_length({arg_c})"

            if callee_name == "list_length":
                arg_c = self._compile_expr(expr.args[0])
                return f"nova_list_length({arg_c})"

            if callee_name == "filter":
                if len(expr.args) == 2:
                    fn_arg = self._compile_expr(expr.args[0])
                    list_arg = self._compile_expr(expr.args[1])
                    return f"nova_list_filter({list_arg}, {fn_arg})"

            if callee_name == "map":
                if len(expr.args) == 2:
                    fn_arg = self._compile_expr(expr.args[0])
                    list_arg = self._compile_expr(expr.args[1])
                    return f"nova_list_map({list_arg}, {fn_arg})"

            if callee_name == "sum":
                arg_c = self._compile_expr(expr.args[0])
                return f"nova_list_sum({arg_c})"

            if callee_name == "head":
                arg_c = self._compile_expr(expr.args[0])
                return f"nova_list_head({arg_c})"

            if callee_name == "tail":
                arg_c = self._compile_expr(expr.args[0])
                return f"nova_list_tail({arg_c})"

            if callee_name == "read_line":
                return "nova_read_line()"

            if callee_name == "str_to_int":
                arg_c = self._compile_expr(expr.args[0])
                return f"nova_str_to_int({arg_c})"

            # 数学内置函数
            math_builtins = {
                "abs": "nova_abs",
                "sqrt": "nova_sqrt",
                "pow": "nova_pow",
                "log": "nova_log",
                "log10": "nova_log10",
                "exp": "nova_exp",
                "sin": "nova_sin",
                "cos": "nova_cos",
                "tan": "nova_tan",
                "floor": "nova_floor",
                "ceil": "nova_ceil",
                "round": "nova_round",
                "min": "nova_min",
                "max": "nova_max",
            }
            if callee_name in math_builtins:
                args_c = ", ".join(self._compile_expr(a) for a in expr.args)
                return f"{math_builtins[callee_name]}({args_c})"

            if callee_name == "pi":
                return "nova_pi()"

            # I/O 内置函数
            io_builtins = {
                "read_file": "nova_read_file",
                "write_file": "nova_write_file",
                "file_exists": "nova_file_exists",
                "list_dir": "nova_list_dir",
                "json_parse": "nova_json_parse",
                "json_stringify": "nova_json_stringify",
            }
            if callee_name in io_builtins:
                args_c = ", ".join(self._compile_expr(a) for a in expr.args)
                return f"{io_builtins[callee_name]}({args_c})"

        # 普通函数调用
        callee_c = self._compile_expr(expr.callee)
        args_c = ", ".join(self._compile_expr(a) for a in expr.args)

        # 如果 callee 是变量（可能是闭包），使用 nova_closure_call
        if isinstance(expr.callee, Identifier):
            # 使用函数名转换（nova_fn_ 前缀）
            c_name = self._mangle_fn_name(expr.callee.name)
            return f"{c_name}({args_c})"

        return f"{callee_c}({args_c})"

    def _compile_adt_constructor(
        self, adt_name: str, variant_name: str, args: list
    ) -> str:
        """编译 ADT 构造器调用"""
        # 构造器查找对应字段信息
        variants_info = self.adt_info.get(adt_name, [])
        field_info = None
        for vname, fnames in variants_info:
            if vname == variant_name:
                field_info = fnames
                break

        lines = [f"({{"]
        lines.append(f"    .tag = NOVA_ADT_{adt_name}_{variant_name},")

        if field_info and args:
            field_types = self.adt_field_types.get(adt_name, {}).get(variant_name, [])
            for i, arg in enumerate(args):
                arg_c = self._compile_expr(arg)
                field_cname = f"{variant_name}__field{i}"
                lines.append(f"    .{field_cname} = {arg_c},")

        lines.append(f"}})")
        return "\n".join(lines)

    def _compile_lambda(self, expr: Lambda) -> str:
        """编译 Lambda 为闭包创建"""
        # 生成闭包结构
        lines = ["nova_closure_new("]
        lines.append("    /* capture_count */ 0,")

        # 生成 lambda 函数体为独立的 C 函数
        lambda_fn_name = self._new_temp()
        self.indent_level = 0
        ret_type = "int64_t"
        if expr.return_type:
            ret_type = self._c_type_from_type_expr(expr.return_type)

        params_str = "void* _nova_closure_env"
        if expr.params:
            param_parts = [
                f"{self._c_type_from_type_expr(p.type_annotation) if p.type_annotation else 'int64_t'} {self._mangle_name(p.name)}"
                for p in expr.params
            ]
            params_str = "void* _nova_closure_env, " + ", ".join(param_parts)

        self.functions.append(
            f"/* lambda */ {ret_type} nova_lambda_{lambda_fn_name}({params_str});"
        )
        lines.append(f"    nova_lambda_{lambda_fn_name},")
        lines.append(f"    NULL /* env */")
        lines.append(f")")

        # 生成实际的 lambda 函数
        body_c = self._compile_expr(expr.body)
        fn_lines = [f"{ret_type} nova_lambda_{lambda_fn_name}({params_str}) {{"]
        fn_lines.append(f"    (void)_nova_closure_env;")
        if isinstance(expr.body, Block):
            fn_lines.append(self._indent_str(body_c))
            if expr.body.tail_expression:
                tail_c = self._compile_expr(expr.body.tail_expression)
                fn_lines.append(f"    return {tail_c};")
        else:
            fn_lines.append(f"    return {body_c};")
        fn_lines.append(f"}}")
        self.functions.append("\n".join(fn_lines))

        return "\n".join(lines)

    def _compile_nested_fn_def(self, fndef: FnDef) -> str:
        """编译嵌套函数定义为闭包"""
        return self._compile_lambda(
            Lambda(
                params=fndef.params,
                return_type=fndef.return_type,
                body=fndef.body,
            )
        )

    def _compile_pipe_expr(self, expr: PipeExpr) -> str:
        """编译管道表达式：left |> right → right(left)"""
        left_c = self._compile_expr(expr.left)

        if isinstance(expr.right, FnCall):
            callee = expr.right.callee
            args = [expr.left] + expr.right.args
            new_call = FnCall(callee=callee, args=args, span=expr.right.span)
            return self._compile_fn_call(new_call)
        elif isinstance(expr.right, Identifier):
            # 直接函数引用
            return f"{self._mangle_name(expr.right.name)}({left_c})"
        else:
            # 右侧是 lambda 或其他表达式
            right_c = self._compile_expr(expr.right)
            return f"nova_closure_call({right_c}, {left_c})"

    def _compile_let_binding_expr(self, expr: LetBinding) -> str:
        """编译块内的 let 绑定"""
        c_name = self._mangle_name(expr.name)
        value_c = self._compile_expr(expr.value)
        lines = []
        # 推断 C 类型
        c_type = self._infer_c_type_from_expr(expr.value)
        lines.append(f"{c_type} {c_name} = {value_c};")
        return "\n".join(lines)

    def _compile_mut_binding_expr(self, expr: MutBinding) -> str:
        """编译块内的 mut 绑定"""
        c_name = self._mangle_name(expr.name)
        value_c = self._compile_expr(expr.value)
        c_type = self._infer_c_type_from_expr(expr.value)
        return f"{c_type} {c_name} = {value_c};"

    def _compile_block(self, block: Block) -> str:
        """编译代码块"""
        lines = ["{"]
        old_indent = self.indent_level
        self.indent_level = 1

        for stmt in block.statements:
            stmt_c = self._compile_expr(stmt)
            lines.append(self._indent_str(stmt_c))

        if block.tail_expression:
            tail_c = self._compile_expr(block.tail_expression)
            lines.append(self._indent_str(f"/* tail: */ {tail_c};"))

        self.indent_level = old_indent
        lines.append("}")
        return "\n".join(lines)

    def _compile_list_expr(self, expr: ListExpr) -> str:
        """编译列表表达式"""
        tmp = self._new_temp()
        lines = [f"{{"]
        lines.append(f"    NovaList* {tmp} = nova_list_new();")
        for elem in expr.elements:
            elem_c = self._compile_expr(elem)
            lines.append(f"    nova_list_push({tmp}, (void*)(intptr_t){elem_c});")
        lines.append(f"    {tmp}")
        lines.append(f"}}")
        return "\n".join(lines)

    def _compile_list_comprehension(self, expr: ListComprehension) -> str:
        """编译列表推导式"""
        result_var = self._new_temp()
        var_name = self._mangle_name(expr.var_name)
        iterable = expr.iterable

        lines = [f"{{"]
        lines.append(f"    NovaList* {result_var} = nova_list_new();")

        if isinstance(iterable, tuple) and iterable[0] == "range":
            # 范围推导式
            start_c = self._compile_expr(iterable[1])
            end_c = self._compile_expr(iterable[2])
            idx_var = self._new_temp()
            lines.append(
                f"    for (int64_t {idx_var} = {start_c}; {idx_var} < {end_c}; {idx_var}++) {{"
            )
            lines.append(f"        int64_t {var_name} = {idx_var};")

            # 可选过滤条件
            if expr.filter_cond:
                filter_c = self._compile_expr(expr.filter_cond)
                lines.append(f"        if ({filter_c}) {{")

            elem_c = self._compile_expr(expr.expr)
            lines.append(
                f"            nova_list_push({result_var}, (void*)(intptr_t){elem_c});"
            )

            if expr.filter_cond:
                lines.append(f"        }}")

            lines.append(f"    }}")
        else:
            # 列表遍历推导式
            list_c = self._compile_expr(iterable)
            list_var = self._new_temp()
            idx_var = self._new_temp()
            lines.append(f"    NovaList* {list_var} = {list_c};")
            lines.append(
                f"    int64_t {self._new_temp()} = nova_list_length({list_var});"
            )
            lines.append(
                f"    for (int64_t {idx_var} = 0; {idx_var} < nova_list_length({list_var}); {idx_var}++) {{"
            )
            lines.append(
                f"        int64_t {var_name} = (int64_t)(intptr_t)nova_list_get({list_var}, {idx_var});"
            )

            if expr.filter_cond:
                filter_c = self._compile_expr(expr.filter_cond)
                lines.append(f"        if ({filter_c}) {{")

            elem_c = self._compile_expr(expr.expr)
            lines.append(
                f"            nova_list_push({result_var}, (void*)(intptr_t){elem_c});"
            )

            if expr.filter_cond:
                lines.append(f"        }}")

            lines.append(f"    }}")

        lines.append(f"    {result_var}")
        lines.append(f"}}")
        return "\n".join(lines)

    def _compile_tuple_expr(self, expr: TupleExpr) -> str:
        """编译元组表达式"""
        # 元组在 C 中使用索引字段的结构体
        elem_count = len(expr.elements)
        tmp = self._new_temp()
        lines = [f"{{"]

        # 使用 void* 数组表示元组
        lines.append(f"    void* {tmp}[{elem_count}];")
        for i, elem in enumerate(expr.elements):
            elem_c = self._compile_expr(elem)
            lines.append(f"    {tmp}[{i}] = (void*)(intptr_t){elem_c};")

        # 返回一个标记为元组的指针（简化实现）
        lines.append(f"    nova_tuple_new({tmp}, {elem_count})")
        lines.append(f"}}")
        return "\n".join(lines)

    def _compile_map_expr(self, expr: MapExpr) -> str:
        """编译 Map 表达式"""
        tmp = self._new_temp()
        lines = [f"{{"]
        lines.append(f"    NovaMap* {tmp} = nova_map_new();")
        for key_expr, val_expr in expr.pairs:
            key_c = self._compile_expr(key_expr)
            val_c = self._compile_expr(val_expr)
            lines.append(
                f"    nova_map_set({tmp}, (void*)(intptr_t){key_c}, (void*)(intptr_t){val_c});"
            )
        lines.append(f"    {tmp}")
        lines.append(f"}}")
        return "\n".join(lines)

    def _compile_field_access(self, expr: FieldAccess) -> str:
        """编译字段访问"""
        target_c = self._compile_expr(expr.target)
        try:
            idx = int(expr.field)
            return f"nova_tuple_get({target_c}, {idx})"
        except ValueError:
            # 结构体字段访问
            return f"{target_c}.{expr.field}"

    def _compile_for_expr(self, expr: ForExpr) -> str:
        """编译 for 循环表达式（返回列表）"""
        result_var = self._new_temp()
        var_name = self._mangle_name(expr.var_name)
        iterable = expr.iterable

        lines = [f"{{"]
        lines.append(f"    NovaList* {result_var} = nova_list_new();")

        if isinstance(iterable, tuple) and iterable[0] == "range":
            start_c = self._compile_expr(iterable[1])
            end_c = self._compile_expr(iterable[2])
            step_c = self._compile_expr(iterable[3]) if iterable[3] else "1"
            idx_var = self._new_temp()
            lines.append(
                f"    for (int64_t {idx_var} = {start_c}; {idx_var} < {end_c}; {idx_var} += {step_c}) {{"
            )
            lines.append(f"        int64_t {var_name} = {idx_var};")
        else:
            list_c = self._compile_expr(iterable)
            list_var = self._new_temp()
            idx_var = self._new_temp()
            lines.append(f"    NovaList* {list_var} = {list_c};")
            lines.append(
                f"    for (int64_t {idx_var} = 0; {idx_var} < nova_list_length({list_var}); {idx_var}++) {{"
            )
            lines.append(
                f"        int64_t {var_name} = (int64_t)(intptr_t)nova_list_get({list_var}, {idx_var});"
            )

        body_c = self._compile_expr(expr.body)
        lines.append(
            f"        nova_list_push({result_var}, (void*)(intptr_t){body_c});"
        )
        lines.append(f"    }}")
        lines.append(f"    {result_var}")
        lines.append(f"}}")
        return "\n".join(lines)

    def _compile_while_expr(self, expr: WhileExpr) -> str:
        """编译 while 循环"""
        cond_c = self._compile_expr(expr.condition)
        lines = [f"{{"]
        lines.append(f"    while ({cond_c}) {{")
        body_c = self._compile_expr(expr.body)
        if isinstance(expr.body, Block):
            for body_line in body_c.split("\n"):
                lines.append(f"    {body_line}")
        else:
            lines.append(f"        {body_c};")
        lines.append(f"    }}")
        lines.append(f"}}")
        return "\n".join(lines)

    # ----------------------------------------------------------
    # 类型转换
    # ----------------------------------------------------------

    def _c_type_from_type_expr(self, type_node) -> str:
        """将 AST 类型表达式转换为 C 类型字符串"""
        if type_node is None:
            return "int64_t"

        if isinstance(type_node, TypeInt):
            return "int64_t"
        elif isinstance(type_node, TypeFloat):
            return "double"
        elif isinstance(type_node, TypeString):
            return "NovaString*"
        elif isinstance(type_node, TypeBool):
            return "bool"
        elif isinstance(type_node, TypeChar):
            return "char"
        elif isinstance(type_node, TypeUnit):
            return "void"
        elif isinstance(type_node, TypeIdentifier):
            name = type_node.name
            # 检查是否是已知 ADT
            if name in self.adt_info:
                return f"NovaADT_{name}"
            return "int64_t"  # 默认
        elif isinstance(type_node, TypeGeneric):
            base = type_node.base
            if base == "List":
                return "NovaList*"
            elif base == "Map":
                return "NovaMap*"
            elif base in ("Option", "Result"):
                return "NovaADT*"
            elif base in self.adt_info:
                return f"NovaADT_{base}"
            return "NovaADT*"
        elif isinstance(type_node, TypeTuple):
            return "NovaTuple*"
        elif isinstance(type_node, TypeFn):
            return "NovaClosure*"
        return "int64_t"

    def _infer_c_type_from_expr(self, expr) -> str:
        """从表达式推断 C 类型"""
        if isinstance(expr, IntLiteral):
            return "int64_t"
        elif isinstance(expr, FloatLiteral):
            return "double"
        elif isinstance(expr, StringLiteral):
            return "NovaString*"
        elif isinstance(expr, CharLiteral):
            return "char"
        elif isinstance(expr, BoolLiteral):
            return "bool"
        elif isinstance(expr, UnitLiteral):
            return "void"
        elif isinstance(expr, ListExpr):
            return "NovaList*"
        elif isinstance(expr, ListComprehension):
            return "NovaList*"
        elif isinstance(expr, TupleExpr):
            return "NovaTuple*"
        elif isinstance(expr, MapExpr):
            return "NovaMap*"
        elif isinstance(expr, Lambda):
            return "NovaClosure*"
        elif isinstance(expr, Identifier):
            return "int64_t"  # 默认
        elif isinstance(expr, BinaryOp):
            if expr.op == "++":
                return "NovaString*"
            if expr.op in ("==", "!=", "<", ">", "<=", ">=", "&&", "||"):
                return "bool"
            if isinstance(expr.left, FloatLiteral) or isinstance(
                expr.right, FloatLiteral
            ):
                return "double"
            return "int64_t"
        elif isinstance(expr, UnaryOp):
            if expr.op == "!":
                return "bool"
            return "int64_t"
        elif isinstance(expr, IfExpr):
            if expr.then_branch and expr.else_branch:
                return self._infer_c_type_from_expr(expr.then_branch)
            return "void"
        elif isinstance(expr, FnCall):
            if isinstance(expr.callee, Identifier):
                name = expr.callee.name
                if name in ("print", "println"):
                    return "void"
                if name == "int_to_str":
                    return "NovaString*"
                if name == "str_len":
                    return "int64_t"
                if name == "list_length":
                    return "int64_t"
                if name == "read_line":
                    return "NovaString*"
                # 检查 ADT 构造器
                adt_name = self._find_adt_name(name)
                if adt_name != "Unknown":
                    return f"NovaADT_{adt_name}"
            return "int64_t"
        elif isinstance(expr, Block):
            if expr.tail_expression:
                return self._infer_c_type_from_expr(expr.tail_expression)
            return "void"
        elif isinstance(expr, MatchExpr):
            if expr.arms:
                return self._infer_c_type_from_expr(expr.arms[0].body)
            return "void"
        elif isinstance(expr, PipeExpr):
            return self._infer_c_type_from_expr(expr.right)
        elif isinstance(expr, ForExpr):
            return "NovaList*"
        elif isinstance(expr, WhileExpr):
            return self._infer_c_type_from_expr(expr.body)
        elif isinstance(expr, LetBinding):
            return self._infer_c_type_from_expr(expr.value)
        elif isinstance(expr, MutBinding):
            return self._infer_c_type_from_expr(expr.value)
        elif isinstance(expr, Assignment):
            return "void"
        elif isinstance(expr, TryExpr):
            return self._infer_c_type_from_expr(expr.expr)
        return "int64_t"  # 默认

    # ----------------------------------------------------------
    # 名称处理
    # ----------------------------------------------------------

    def _mangle_name(self, name: str) -> str:
        """将 Nova 名称转换为合法的 C 标识符"""
        if name in C_KEYWORDS:
            return f"nova_{name}"
        # 替换非字母数字下划线字符
        safe = []
        for ch in name:
            if ch.isalnum() or ch == "_":
                safe.append(ch)
            else:
                safe.append(f"_0x{ord(ch):02x}_")
        result = "".join(safe)
        # 确保不以数字开头
        if result and result[0].isdigit():
            result = "nova_" + result
        return result or "nova_anon"

    def _mangle_fn_name(self, name: str) -> str:
        """将 Nova 函数名转换为 C 函数名（添加 nova_fn_ 前缀）"""
        # nova_fn_ 前缀已经避免了与 C 关键字冲突，所以直接安全化名称即可
        safe = []
        for ch in name:
            if ch.isalnum() or ch == "_":
                safe.append(ch)
            else:
                safe.append(f"_0x{ord(ch):02x}_")
        result = "".join(safe)
        # 确保不以数字开头
        if result and result[0].isdigit():
            result = "x_" + result
        return f"nova_fn_{result}" if result else "nova_fn_anon"

    # ----------------------------------------------------------
    # 字符串转义
    # ----------------------------------------------------------

    def _escape_c_string(self, s: str) -> str:
        """转义 C 字符串字面量中的特殊字符"""
        return (
            s.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\t", "\\t")
            .replace("\r", "\\r")
            .replace("\0", "\\0")
        )

    def _escape_c_char(self, s: str) -> str:
        """转义 C 字符字面量"""
        if s == "\n":
            return "\\n"
        elif s == "\t":
            return "\\t"
        elif s == "\r":
            return "\\r"
        elif s == "\0":
            return "\\0"
        elif s == "'":
            return "\\'"
        elif s == "\\":
            return "\\\\"
        return s

    # ----------------------------------------------------------
    # 辅助方法
    # ----------------------------------------------------------

    def _new_temp(self) -> str:
        """生成新的临时变量名"""
        name = f"nova_tmp_{self.temp_counter}"
        self.temp_counter += 1
        return name

    def _emit(self, line: str):
        """输出一行 C 代码"""
        self.output_lines.append(self._indent_str(line))

    def _indent_str(self, line: str) -> str:
        """为行添加缩进（仅在非空行时）"""
        if not line:
            return line
        return "    " * self.indent_level + line

    # ----------------------------------------------------------
    # 公共工具方法
    # ----------------------------------------------------------

    @staticmethod
    def is_c_keyword(name: str) -> bool:
        """检查名称是否是 C 关键字"""
        return name in C_KEYWORDS
