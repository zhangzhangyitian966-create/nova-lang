"""
Nova LIR → C 代码生成后端

将 LIR (Low-level Intermediate Representation) 编译为 C 源代码。
这是 C 后端接入统一 IR 管线的第一步，使 C 后端能够受益于 IR 层的所有优化 Pass。

当前实现阶段：阶段一（最小可用集合）
- 支持整数/浮点/布尔常量加载
- 支持二元/一元运算
- 支持控制流（label/goto/if-goto/return）
- 支持函数调用
- 支持寄存器/栈位之间的数据移动
"""

from ..ir.ir_nodes import (
    UNIT_TYPE,
    LIRBinOp,
    LIRBranch,
    LIRBuildADT,
    LIRBuildList,
    LIRBuildMap,
    LIRBuildTuple,
    LIRCall,
    LIRCallIndirect,
    LIRFieldAccess,
    LIRFunction,
    LIRIndex,
    LIRInstr,
    LIRJump,
    LIRLabel,
    LIRListAppend,
    LIRLoadConst,
    LIRLoadGlobal,
    LIRLoadReg,
    LIRModule,
    LIRPanic,
    LIRReturn,
    LIRStoreGlobal,
    LIRStoreReg,
    LIRSwitch,
    LIRUnaryOp,
)
from .common import mangle_builtin_name


class LIRCBackend:
    """LIR → C 代码生成器

    将 LIR 模块编译为 C 源代码。
    虚拟寄存器直接映射为 C 局部变量，由 C 编译器负责寄存器分配和优化。
    控制流使用 C 的 goto + label 实现。
    """

    def __init__(self):
        self._output = []
        self._indent_level = 0
        self._string_literals = []  # 收集字符串常量
        self._string_counter = 0
        self._tmp_counter_value = 0  # 临时变量计数器

    def compile(self, lir_module: LIRModule) -> str:
        """编译 LIR 模块为 C 源代码字符串"""
        self._output = []
        self._indent_level = 0
        self._string_literals = []
        self._string_counter = 0
        self._tmp_counter_value = 0

        # 1. 输出头文件
        self._emit_header()

        # 2. 收集字符串常量（先扫描所有函数）
        self._collect_string_literals(lir_module)

        # 3. 输出字符串常量声明
        self._emit_string_literals()

        # 4. 输出全局变量声明
        self._emit_globals(lir_module)

        # 5. 输出函数前向声明
        self._emit_fn_declarations(lir_module)

        # 6. 输出函数定义
        for name, fn in lir_module.functions.items():
            self._compile_function(fn)

        # 7. 输出 main 函数
        self._emit_main(lir_module)

        return "\n".join(self._output)

    # ------------------------------------------------------------------
    # 头部与全局
    # ------------------------------------------------------------------

    def _emit_header(self):
        """输出头文件包含"""
        self._emit('#include "nova_runtime.h"')
        self._emit("#include <stdio.h>")
        self._emit("#include <stdlib.h>")
        self._emit("#include <string.h>")
        self._emit("#include <stdbool.h>")
        self._emit("#include <stdint.h>")
        self._emit("")

    def _collect_string_literals(self, lir_module: LIRModule):
        """收集所有字符串常量"""
        for name, fn in lir_module.functions.items():
            for instr in fn.body:
                if isinstance(instr, LIRLoadConst):
                    if instr.const_type == "string" and instr.value is not None:
                        if instr.value not in self._string_literals:
                            self._string_literals.append(instr.value)

    def _emit_string_literals(self):
        """输出字符串常量的静态数组声明"""
        if not self._string_literals:
            return
        for i, s in enumerate(self._string_literals):
            escaped = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            self._emit(f'static const char nova_str_{i}[] = "{escaped}";')
        self._emit("")

    def _get_string_label(self, value: str) -> str:
        """获取字符串常量的标签名"""
        if value in self._string_literals:
            idx = self._string_literals.index(value)
            return f"nova_str_{idx}"
        # 不在预收集列表中（理论上不应该发生）
        idx = len(self._string_literals)
        self._string_literals.append(value)
        return f"nova_str_{idx}"

    def _emit_globals(self, lir_module: LIRModule):
        """输出全局变量声明"""
        if not lir_module.globals:
            return
        for g in lir_module.globals:
            c_type = self._nova_type_to_c(g.ir_type)
            self._emit(f"{c_type} {g.name};")
        self._emit("")

    def _emit_fn_declarations(self, lir_module: LIRModule):
        """输出函数前向声明"""
        for name, fn in lir_module.functions.items():
            ret_type = self._nova_type_to_c(fn.return_type)
            params = self._gen_params_str(fn)
            c_name = self._mangle_fn_name(name)
            self._emit(f"{ret_type} {c_name}({params});")
        self._emit("")

    def _emit_main(self, lir_module: LIRModule):
        """输出 main 函数"""
        self._emit("int main(int argc, char** argv) {")
        self._indent_level += 1
        self._emit("nova_init();")

        # 如果有 main 函数则调用
        if "main" in lir_module.functions:
            main_fn = lir_module.functions["main"]
            c_name = self._mangle_fn_name("main")
            if main_fn.return_type == UNIT_TYPE:
                self._emit(f"{c_name}();")
            else:
                self._emit(f"{c_name}();")

        self._emit("nova_cleanup();")
        self._emit("return 0;")
        self._indent_level -= 1
        self._emit("}")
        self._emit("")

    # ------------------------------------------------------------------
    # 函数编译
    # ------------------------------------------------------------------

    def _compile_function(self, fn: LIRFunction):
        """编译单个函数"""
        ret_type = self._nova_type_to_c(fn.return_type)
        c_name = self._mangle_fn_name(fn.name)
        params = self._gen_params_str(fn)

        self._emit(f"{ret_type} {c_name}({params}) {{")
        self._indent_level += 1

        # 收集所有用到的虚拟寄存器（位置）并声明变量
        locs = self._collect_locations(fn)
        for loc_name, loc_type in locs.items():
            # 跳过参数（已在参数列表中声明）
            param_names = [p[0] for p in fn.params]
            if loc_name in param_names:
                continue
            c_type = self._nova_type_to_c(loc_type)
            var_name = self._loc_var_name(loc_name)
            self._emit(f"{c_type} {var_name};")

        if locs:
            self._emit("")

        # 编译函数体指令
        for instr in fn.body:
            self._compile_instr(instr, fn)

        self._indent_level -= 1
        self._emit("}")
        self._emit("")

    def _collect_locations(self, fn: LIRFunction) -> dict:
        """收集函数中所有用到的位置（虚拟寄存器）及其类型"""
        locs = {}
        # 参数
        for name, ty in fn.params:
            locs[name] = ty

        for instr in fn.body:
            # 源位置
            if instr.src_locs:
                for loc_name, loc_type in instr.src_locs:
                    if loc_name and loc_name not in locs:
                        locs[loc_name] = loc_type
            # 目标位置
            if instr.dst_loc:
                loc_name, loc_type = instr.dst_loc
                if loc_name and loc_name not in locs:
                    locs[loc_name] = loc_type
        return locs

    def _gen_params_str(self, fn: LIRFunction) -> str:
        """生成参数列表字符串"""
        if not fn.params:
            return "void"
        parts = []
        for name, ty in fn.params:
            c_type = self._nova_type_to_c(ty)
            var_name = self._loc_var_name(name)
            parts.append(f"{c_type} {var_name}")
        return ", ".join(parts)

    # ------------------------------------------------------------------
    # 指令编译
    # ------------------------------------------------------------------

    def _compile_instr(self, instr: LIRInstr, fn: LIRFunction):
        """编译单条 LIR 指令"""

        # 标签（不缩进）
        if isinstance(instr, LIRLabel):
            self._indent_level -= 1
            self._emit(f"{instr.name}:;")
            self._indent_level += 1
            return

        dst = self._dst_var_name(instr) if instr.dst_loc else None

        # 常量加载
        if isinstance(instr, LIRLoadConst):
            self._compile_load_const(instr, dst)
            return

        # 寄存器/栈位传送
        if isinstance(instr, LIRLoadReg):
            if instr.src_locs and dst:
                src = self._loc_var_name(instr.src_locs[0][0])
                self._emit(f"{dst} = {src};")
            return

        if isinstance(instr, LIRStoreReg):
            if instr.src_locs and dst:
                src = self._loc_var_name(instr.src_locs[0][0])
                self._emit(f"{dst} = {src};")
            return

        # 全局变量加载/存储
        if isinstance(instr, LIRLoadGlobal):
            if dst:
                self._emit(f"{dst} = {instr.global_name};")
            return

        if isinstance(instr, LIRStoreGlobal):
            if instr.src_locs:
                src = self._loc_var_name(instr.src_locs[0][0])
                self._emit(f"{instr.global_name} = {src};")
            return

        # 二元运算
        if isinstance(instr, LIRBinOp):
            self._compile_binop(instr, dst)
            return

        # 一元运算
        if isinstance(instr, LIRUnaryOp):
            if instr.src_locs and dst:
                src = self._loc_var_name(instr.src_locs[0][0])
                op = self._map_unary_op(instr.op)
                self._emit(f"{dst} = {op}{src};")
            return

        # 函数调用
        if isinstance(instr, LIRCall):
            self._compile_call(instr, dst)
            return

        # 间接调用（闭包/函数指针）
        if isinstance(instr, LIRCallIndirect):
            self._compile_call_indirect(instr, dst)
            return

        # 控制流
        if isinstance(instr, LIRJump):
            self._emit(f"goto {instr.target};")
            return

        if isinstance(instr, LIRBranch):
            self._compile_branch(instr)
            return

        if isinstance(instr, LIRSwitch):
            self._compile_switch(instr)
            return

        if isinstance(instr, LIRReturn):
            if instr.src_locs:
                src = self._loc_var_name(instr.src_locs[0][0])
                self._emit(f"return {src};")
            else:
                self._emit("return;")
            return

        # 列表构建
        if isinstance(instr, LIRBuildList):
            if dst:
                self._emit(f"{dst} = nova_list_new({instr.count});")
            return

        if isinstance(instr, LIRListAppend):
            if instr.src_locs and len(instr.src_locs) >= 2:
                lst = self._loc_var_name(instr.src_locs[0][0])
                elem = self._loc_var_name(instr.src_locs[1][0])
                self._emit(f"nova_list_push({lst}, {elem});")
            return

        # 元组构建
        if isinstance(instr, LIRBuildTuple):
            if dst:
                size = instr.count * 8
                self._emit(f"{dst} = (NovaValue*)nova_alloc({size});")
            return

        # Map 构建
        if isinstance(instr, LIRBuildMap):
            if dst:
                self._emit(f"{dst} = nova_map_new({instr.entry_count});")
            return

        # ADT 构建
        if isinstance(instr, LIRBuildADT):
            if dst:
                tag = instr.type_tag
                fields_size = instr.field_count * 8 + 8
                self._emit(f"{dst} = nova_adt_new({tag}, {fields_size});")
            return

        # 字段访问
        if isinstance(instr, LIRFieldAccess):
            if instr.src_locs and dst:
                src = self._loc_var_name(instr.src_locs[0][0])
                # offset 是字段索引，每个字段 8 字节（NovaValue 大小）
                byte_offset = instr.offset * 8
                self._emit(f"{dst} = *(NovaValue*)((char*){src} + {byte_offset});")
            return

        # 索引访问
        if isinstance(instr, LIRIndex):
            if instr.src_locs and len(instr.src_locs) >= 2 and dst:
                lst = self._loc_var_name(instr.src_locs[0][0])
                idx = self._loc_var_name(instr.src_locs[1][0])
                self._emit(f"{dst} = nova_list_get({lst}, {idx});")
            return

        # Panic
        if isinstance(instr, LIRPanic):
            msg = instr.message or "panic"
            self._emit(f'nova_panic("{msg}");')
            return

        # 未知指令：输出注释，不中断编译
        self._emit(
            f"/* TODO: LIR instruction {type(instr).__name__} not implemented */"
        )

    def _compile_load_const(self, instr: LIRLoadConst, dst: str):
        """编译常量加载指令"""
        if not dst:
            return

        ctype = instr.const_type
        val = instr.value

        if ctype == "int":
            self._emit(f"{dst} = (int64_t){val};")
        elif ctype == "float":
            self._emit(f"{dst} = (double){val};")
        elif ctype == "bool":
            bool_val = "true" if val else "false"
            self._emit(f"{dst} = {bool_val};")
        elif ctype == "string":
            label = self._get_string_label(val if val else "")
            self._emit(f"{dst} = (NovaString*)nova_string_new((char*){label});")
        elif ctype == "unit":
            self._emit(f"{dst} = 0;")
        elif ctype == "closure":
            # 闭包常量：简化处理，先置空
            self._emit(f"{dst} = NULL;")
        else:
            self._emit(f"{dst} = 0; /* unknown const type: {ctype} */")

    def _compile_binop(self, instr: LIRBinOp, dst: str):
        """编译二元运算"""
        if not instr.src_locs or len(instr.src_locs) < 2 or not dst:
            return

        left = self._loc_var_name(instr.src_locs[0][0])
        right = self._loc_var_name(instr.src_locs[1][0])
        op = instr.op

        # 字符串拼接特殊处理
        if op == "++":
            self._emit(f"{dst} = nova_string_concat({left}, {right});")
            return

        # 普通运算
        c_op = self._map_binop(op)
        self._emit(f"{dst} = {left} {c_op} {right};")

    def _compile_branch(self, instr: LIRBranch):
        """编译条件跳转

        LIR 语义：条件为真走 true_target，条件为假走 false_target。
        生成显式双向跳转，不依赖 fall-through，确保非顺序 CFG 也正确。
        """
        if not instr.src_locs:
            return

        cond = self._loc_var_name(instr.src_locs[0][0])
        false_target = instr.false_target or "block_false"
        true_target = instr.true_target or "block_true"

        # 显式双向跳转：条件为真跳 true_target，否则跳 false_target
        # 不依赖 fall-through 假设，确保任意基本块顺序下都正确
        self._emit(f"if ({cond}) goto {true_target};")
        self._emit(f"goto {false_target};")

    def _compile_switch(self, instr: LIRSwitch):
        """编译 switch 多分支跳转

        策略：
        - 整型 case 且数量 >= 3：使用 C switch 语句（跳转表优化）
        - 其他情况（字符串、布尔、浮点等）：使用 if-else if 级联
        """
        if not instr.src_locs or not instr.cases:
            # 没有值或没有 case，直接跳 default
            if instr.default_target:
                self._emit(f"goto {instr.default_target};")
            return

        cond_val = self._loc_var_name(instr.src_locs[0][0])

        # 判断是否所有 case 都是整型（可使用 switch）
        all_int_cases = all(
            isinstance(v, int) and not isinstance(v, bool)
            for v, _ in instr.cases
        )

        if all_int_cases and len(instr.cases) >= 3:
            # 整型 case 较多：使用 C switch 语句
            self._emit(f"switch ((int64_t){cond_val}) {{")
            self._indent_level += 1
            for case_val, target in instr.cases:
                self._emit(f"case {case_val}: goto {target};")
            if instr.default_target:
                self._emit(f"default: goto {instr.default_target};")
            self._indent_level -= 1
            self._emit("}")
        else:
            # 使用 if-else if 级联
            for i, (case_val, target) in enumerate(instr.cases):
                if isinstance(case_val, str):
                    # 字符串比较
                    self._emit(
                        f'if (nova_str_eq({cond_val}, "{case_val}")) goto {target};'
                    )
                elif isinstance(case_val, bool):
                    # 布尔比较
                    self._emit(
                        f"if ({cond_val} == {'1' if case_val else '0'}) goto {target};"
                    )
                else:
                    # 数值比较（int, float 等）
                    self._emit(f"if ({cond_val} == {case_val}) goto {target};")

            # default 分支
            if instr.default_target:
                self._emit(f"goto {instr.default_target};")

    def _compile_call(self, instr: LIRCall, dst: str):
        """编译函数调用"""
        c_name = self._mangle_fn_name(instr.func_name)
        args = []

        if instr.src_locs:
            for i in range(min(instr.arg_count, len(instr.src_locs))):
                args.append(self._loc_var_name(instr.src_locs[i][0]))

        args_str = ", ".join(args)

        if dst:
            self._emit(f"{dst} = {c_name}({args_str});")
        else:
            self._emit(f"{c_name}({args_str});")

    def _compile_call_indirect(self, instr: LIRCallIndirect, dst: str):
        """编译间接调用（闭包/函数指针调用）

        使用 nova_closure_call 运行时函数，将参数打包为 void* 数组。
        第一个 src_loc 是闭包对象，后续是参数。
        """
        if not instr.src_locs or len(instr.src_locs) < 1:
            return

        closure = self._loc_var_name(instr.src_locs[0][0])
        arg_count = instr.arg_count

        # 构建参数数组
        args_array = f"nova_args_{self._tmp_counter()}"
        self._emit(f"void* {args_array}[{max(arg_count, 1)}];")

        for i in range(arg_count):
            if i + 1 < len(instr.src_locs):
                arg_var = self._loc_var_name(instr.src_locs[i + 1][0])
                self._emit(f"{args_array}[{i}] = (void*){arg_var};")

        if dst:
            self._emit(
                f"{dst} = (NovaValue*)nova_closure_call((NovaClosure*){closure}, "
                f"{args_array}, {arg_count});"
            )
        else:
            self._emit(
                f"nova_closure_call((NovaClosure*){closure}, "
                f"{args_array}, {arg_count});"
            )

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _tmp_counter(self) -> int:
        """生成唯一的临时变量序号"""
        self._tmp_counter_value += 1
        return self._tmp_counter_value

    def _emit(self, line: str):
        """输出一行代码"""
        indent = "    " * self._indent_level
        self._output.append(f"{indent}{line}")

    def _loc_var_name(self, loc: str) -> str:
        """虚拟寄存器名 → C 变量名"""
        # 直接使用位置名作为变量名
        return loc

    def _dst_var_name(self, instr: LIRInstr) -> str:
        """获取指令目标位置的 C 变量名"""
        if instr.dst_loc:
            return self._loc_var_name(instr.dst_loc[0])
        return ""

    def _nova_type_to_c(self, ty) -> str:
        """Nova 类型 → C 类型字符串"""
        if ty is None:
            return "int64_t"

        type_name = getattr(ty, "name", None) or str(ty)

        if type_name == "Int" or "Int" in str(ty):
            return "int64_t"
        if type_name == "Float" or "Float" in str(ty):
            return "double"
        if type_name == "Bool" or "Bool" in str(ty):
            return "bool"
        if type_name == "String" or "String" in str(ty):
            return "NovaString*"
        if type_name == "Unit" or "Unit" in str(ty):
            return "void"
        if "List" in str(ty) or "List" in type_name:
            return "NovaList*"
        if "Map" in str(ty) or "Map" in type_name:
            return "NovaMap*"
        if "->" in str(ty) or "Fn" in str(ty) or "Closure" in str(ty):
            return "NovaClosure*"
        # 默认：使用不透明指针
        return "NovaValue*"

    def _mangle_fn_name(self, name: str) -> str:
        """函数名修饰（内置函数使用共享映射表，用户函数加 nova_fn_ 前缀）"""
        return mangle_builtin_name(name)

    def _map_binop(self, op: str) -> str:
        """二元运算符映射"""
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
        return op_map.get(op, op)

    def _map_unary_op(self, op: str) -> str:
        """一元运算符映射"""
        op_map = {
            "-": "-",
            "!": "!",
        }
        return op_map.get(op, op)
