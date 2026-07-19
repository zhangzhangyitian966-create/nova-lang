"""
后端公共模块 - 共享的映射表和工具函数

所有后端共享的配置和工具：
- 内置函数名映射（Nova 函数名 → 运行时函数名）
- 通用类型分类工具
"""

from typing import Dict

# ============================================================
# 内置函数名映射表
# Nova 源码中的函数名 → 运行时 C 函数名
# 所有后端共享此映射，确保命名一致
# ============================================================

BUILTIN_FUNCTION_MAP: Dict[str, str] = {
    # 输出
    "print": "nova_print",
    "println": "nova_println",
    # 字符串转换
    "int_to_str": "nova_int_to_str",
    "float_to_str": "nova_float_to_str",
    "str_to_int": "nova_str_to_int",
    "str_len": "nova_string_length",
    "string_split": "nova_string_split",
    "string_concat": "nova_string_concat",
    # 数学函数
    "sqrt": "nova_sqrt",
    "pow": "nova_pow",
    "sin": "nova_sin",
    "cos": "nova_cos",
    "tan": "nova_tan",
    "log": "nova_log",
    "log10": "nova_log10",
    "exp": "nova_exp",
    "floor": "nova_floor",
    "ceil": "nova_ceil",
    "round": "nova_round",
    "abs": "nova_abs",
    "min": "nova_min",
    "max": "nova_max",
    "pi": "nova_pi",
    # 列表函数
    "filter": "nova_list_filter",
    "map": "nova_list_map",
    "sum": "nova_list_sum",
    "head": "nova_list_head",
    "tail": "nova_list_tail",
    "list_length": "nova_list_length",
    # JSON
    "json_parse": "nova_json_parse",
    "json_stringify": "nova_json_stringify",
    # 文件 IO
    "read_line": "nova_read_line",
    "read_file": "nova_read_file",
    "write_file": "nova_write_file",
    "file_exists": "nova_file_exists",
    # 内存管理
    "alloc": "nova_alloc",
    "free": "nova_free",
    # 运行时控制
    "panic": "nova_panic",
    "init": "nova_init",
    "cleanup": "nova_cleanup",
    # 列表操作
    "list_new": "nova_list_new",
    "list_push": "nova_list_push",
    "list_get": "nova_list_get",
    # 映射操作
    "map_new": "nova_map_new",
    # ADT 操作
    "adt_new": "nova_adt_new",
}


def mangle_builtin_name(name: str) -> str:
    """
    将 Nova 内置函数名转换为运行时函数名。

    如果是已知的内置函数，返回映射后的名字；
    否则添加 nova_fn_ 前缀（用户函数命名空间前缀，避免与 C 关键字冲突。
    """
    if name in BUILTIN_FUNCTION_MAP:
        return BUILTIN_FUNCTION_MAP[name]
    return f"nova_fn_{name}"


def is_builtin_function(name: str) -> bool:
    """判断函数名是否为内置函数"""
    return name in BUILTIN_FUNCTION_MAP
