"""
Nova IR 通用类型系统（立即架构手术 A-1 · 拆分 ir_nodes.py）

本模块提供 Nova 编译器三层 IR（HIR → MIR → LIR）共享的统一类型表示，
由 ir/ir_nodes.py（原上帝模块）拆分而来。

拆分背景（2026-07-29 ARCHITECTURE_VISION.md §2.1「立即架构手术 A」）：
  原 ir/ir_nodes.py 累计 1413 行、112 个类，是 Nova 最大的单体模块，
  连续 10+ 轮审查报告 MEDIUM 级 `class_too_large` 钉子户。
  为确保 self-hosting 移植（SH-1/2/3）的可维护性，采用三步零破坏性迁移：

  - **A1（本轮）**：抽 `ir_types.py` — 类型枚举 / 统一类型表示 / 常量 / 工厂
  - **A2**：抽 `hir.py / mir.py / lir.py` — 按 IR 层拆分节点 + 兼容 re-export
  - **A3**：两轮观察期后删除 ir_nodes.py 中的冗余定义，仅保留薄 re-export 层

所有符号在 `ir/ir_nodes.py` 中均有同名 re-export，外部代码**无需任何修改**。
新代码推荐直接使用 `from nova.ir.ir_types import ...`。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    # 防止循环导入 — 类型表示不直接依赖节点定义
    pass


# ============================================================
# IR 类型种类枚举
# ============================================================


class IRType(Enum):
    """IR 类型种类枚举（三层 IR 共享）

    所有 Nova 值在 IR 层最终都归约到其中一种 kind；参数化类型
    （List / Map / Tuple / Function / ADT）通过 :class:`NovaType.params`
    表达子类型，通过 :class:`NovaType.name` 表达 ADT/类型变量名。

    成员说明：

    * **标量**：``INT`` / ``FLOAT`` / ``BOOL`` / ``CHAR`` / ``UNIT`` / ``NEVER``
    * **容器**：``LIST`` / ``MAP`` / ``TUPLE``
    * **函数/代数**：``FUNCTION`` / ``ADT`` / ``TYPE_VAR``
    * **LIR 层扩展**：``PTR``（低级指针，不暴露给前端语义）
    """

    INT = auto()
    FLOAT = auto()
    STRING = auto()
    BOOL = auto()
    CHAR = auto()
    UNIT = auto()
    NEVER = auto()
    LIST = auto()
    MAP = auto()
    TUPLE = auto()
    FUNCTION = auto()
    ADT = auto()
    TYPE_VAR = auto()
    # --- M-MEM Step3 新增：Box<T> 堆分配唯一所有权指针（前端可见） ---
    BOX = auto()
    # --- LIR 层新增（前端不可见，指针大小统一按 64-bit 处理） ---
    PTR = auto()


# ============================================================
# 统一类型表示 NovaType
# ============================================================


@dataclass(frozen=False)
class NovaType:
    """Nova 统一类型表示（三层 IR 共享）

    设计上是一个带参数的有根树形结构：
      - ``kind``   根种类（:class:`IRType` 枚举值）
      - ``params`` 子类型列表（参数化类型的"泛型参数"）
      - ``name``   附加字符串语义（ADT 名 / 类型变量名 / 具名元组字段等）

    三个字段都参与 :meth:`__eq__` 与 :meth:`__hash__`，可安全用作
    字典键、放入集合（类型查表、单态化缓存、特化索引等）。

    常用构造请优先使用下方的工厂函数：
    :func:`list_type` / :func:`map_type` / :func:`tuple_type` /
    :func:`fn_type` / :func:`adt_type` / :func:`option_type` / :func:`result_type`。
    （旧 :func:`ListType` 等 PascalCase 名保留为向后兼容别名。）
    """

    kind: IRType
    params: List["NovaType"] = field(default_factory=list)
    name: str = ""

    # ------------------------------------------------------------------
    # 等价 & 哈希（数据类默认生成，但显式写出以锁定语义）
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NovaType):
            return False
        return (
            self.kind == other.kind
            and self.params == other.params
            and self.name == other.name
        )

    def __hash__(self) -> int:
        # list → tuple 后再哈希，使得 NovaType 天然可哈希
        return hash((self.kind, tuple(self.params), self.name))

    # ------------------------------------------------------------------
    # 人类可读显示（错误信息、调试输出、REPL）
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        kind = self.kind

        # Box[Elem]  — M-MEM Step3 堆分配唯一所有权
        if kind == IRType.BOX and self.params:
            return f"Box[{self.params[0]}]"

        # List[Elem]
        if kind == IRType.LIST and self.params:
            return f"List[{self.params[0]}]"

        # Map[Key, Val]
        if kind == IRType.MAP and len(self.params) >= 2:
            return f"Map[{self.params[0]}, {self.params[1]}]"

        # (Arg1, Arg2, ...) -> Ret
        if kind == IRType.FUNCTION and self.params:
            ret = self.params[-1]
            args = ", ".join(str(p) for p in self.params[:-1])
            return f"({args}) -> {ret}"

        # (T1, T2, ...)
        if kind == IRType.TUPLE:
            elems = ", ".join(str(p) for p in self.params)
            return f"({elems})"

        # ADTName[P1, P2, ...]
        if kind == IRType.ADT and self.params:
            params = ", ".join(str(p) for p in self.params)
            return f"{self.name}[{params}]"

        # 具名类型（ADT 无参 / 类型变量 / 别名 target）
        if self.name:
            return self.name

        # Fallback：枚举名（INT / FLOAT / ...）
        return kind.name


# ============================================================
# 常用类型单例（零参类型，共享实例降低内存占用）
# ============================================================

#: 64-bit 有符号整数（Nova 默认整型）
INT_TYPE: NovaType = NovaType(IRType.INT)
#: 64-bit IEEE 754 双精度浮点
FLOAT_TYPE: NovaType = NovaType(IRType.FLOAT)
#: UTF-8 字节串（Nova 字符串内部表示）
STRING_TYPE: NovaType = NovaType(IRType.STRING)
#: 1-byte 布尔值（0 = False, 非 0 = True）
BOOL_TYPE: NovaType = NovaType(IRType.BOOL)
#: Unicode 码点（U+0000 ~ U+10FFFF）
CHAR_TYPE: NovaType = NovaType(IRType.CHAR)
#: 零元组 / 空类型（相当于 Rust 的 () / Haskell 的 ()）
UNIT_TYPE: NovaType = NovaType(IRType.UNIT)
#: 发散类型（panic / 死代码 / 无限循环）
NEVER_TYPE: NovaType = NovaType(IRType.NEVER)
#: 闭包捕获环境 + 代码指针的内部类型表示
CLOSURE_TYPE: NovaType = NovaType(IRType.FUNCTION, name="Closure")


# ============================================================
# 参数化类型工厂函数（PEP8 snake_case 规范名）
#
# 命名说明（Cycle-1513 审查门禁 gate_naming_violation 修复）：
#   原 8 个工厂函数使用 PascalCase（ListType/MapType/...），违反 PEP8
#   函数命名规范。现统一改为 snake_case 规范名，旧名保留为薄别名
#   以保证 100% 向后兼容（外部调用方无需改动）。
# ============================================================


def list_type(elem: NovaType) -> NovaType:
    """构造列表类型 ``List[elem]``

    >>> list_type(INT_TYPE)
    List[INT]
    """
    return NovaType(IRType.LIST, [elem])


def map_type(key: NovaType, val: NovaType) -> NovaType:
    """构造关联数组类型 ``Map[key, val]``

    >>> map_type(STRING_TYPE, INT_TYPE)
    Map[STRING, INT]
    """
    return NovaType(IRType.MAP, [key, val])


def tuple_type(*elems: NovaType) -> NovaType:
    """构造元组类型 ``(T1, T2, ...)``

    零参数时返回 :data:`UNIT_TYPE`；单参数仍会包装成 1-Tuple。
    """
    return NovaType(IRType.TUPLE, list(elems))


def fn_type(*params_and_ret: NovaType) -> NovaType:
    """构造函数类型，**最后一个参数为返回类型**

    >>> fn_type(INT_TYPE, INT_TYPE, BOOL_TYPE)
    (INT, INT) -> BOOL
    """
    return NovaType(IRType.FUNCTION, list(params_and_ret))


def adt_type(name: str, *params: NovaType) -> NovaType:
    """构造 ADT（代数数据类型）类型

    >>> adt_type("Option", INT_TYPE)
    Option[INT]
    >>> adt_type("Bool")
    Bool
    """
    return NovaType(IRType.ADT, list(params), name)


def option_type(elem: NovaType) -> NovaType:
    """``Option[T]`` = 可能不存在的值（前端标准库 ADT 糖）"""
    return adt_type("Option", elem)


def result_type(ok: NovaType, err: NovaType) -> NovaType:
    """``Result[T, E]`` = 可能失败的计算（前端标准库 ADT 糖）"""
    return adt_type("Result", ok, err)


def box_type(inner: NovaType) -> NovaType:
    """``Box[T]`` = 堆分配唯一所有权指针（M-MEM Step3 核心类型）

    语义（对齐 ARCHITECTURE_VISION.md §3.1「栈/堆语义明确」）：
      - 值语义：``Box[T]`` 表示 *拥有* 一个堆上的 ``T`` 值
      - 唯一所有权：任何时刻同一 Box 只有一个活跃引用
      - 显式析构：Box 离开作用域时自动 drop（不依赖 GC）
      - 传递：移动语义（Copy 语义需显式 ``clone_box``）

    >>> box_type(INT_TYPE)
    Box[INT]
    >>> list_type(box_type(adt_type("Node")))
    List[Box[Node]]
    """
    return NovaType(IRType.BOX, [inner])


# ------------------------------------------------------------------
# 向后兼容：保留 PascalCase 薄别名（100% 零破坏性迁移）
# ------------------------------------------------------------------
# 任何外部代码 `from nova.ir.ir_types import ListType` 仍可正常工作。
# 新代码请优先使用 snake_case 规范名。

ListType = list_type   #: 向后兼容别名 → :func:`list_type`
MapType = map_type     #: 向后兼容别名 → :func:`map_type`
TupleType = tuple_type #: 向后兼容别名 → :func:`tuple_type`
FnType = fn_type       #: 向后兼容别名 → :func:`fn_type`
ADTType = adt_type     #: 向后兼容别名 → :func:`adt_type`
OptionType = option_type #: 向后兼容别名 → :func:`option_type`
ResultType = result_type #: 向后兼容别名 → :func:`result_type`
BoxType = box_type     #: 向后兼容别名 → :func:`box_type`


# ============================================================
# 公开 API（配合 from nova.ir.ir_types import * 使用）
# ============================================================

__all__ = [
    # --- 核心类型 ---
    "IRType",
    "NovaType",
    # --- 单例 ---
    "INT_TYPE",
    "FLOAT_TYPE",
    "STRING_TYPE",
    "BOOL_TYPE",
    "CHAR_TYPE",
    "UNIT_TYPE",
    "NEVER_TYPE",
    "CLOSURE_TYPE",
    # --- 工厂函数（PEP8 snake_case 规范名，推荐使用）---
    "list_type",
    "map_type",
    "tuple_type",
    "fn_type",
    "adt_type",
    "option_type",
    "result_type",
    "box_type",
    # --- 工厂函数（向后兼容 PascalCase 别名）---
    "ListType",
    "MapType",
    "TupleType",
    "FnType",
    "ADTType",
    "OptionType",
    "ResultType",
    "BoxType",
]
