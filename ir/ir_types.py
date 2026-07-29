"""Nova IR 共享类型模块（ARCHITECTURE_VISION.md §2.1 手术 A-1 产物）。

从 ir/ir_nodes.py 上帝模块中拆出的第一层：纯类型枚举 + 统一类型表示 +
常用类型构造器。三层 IR（HIR/MIR/LIR）共享这些定义。严禁依赖 HIR/MIR/LIR 节点。
"""

from dataclasses import dataclass, field, replace
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple
class IRType(Enum):
    """IR 类型种类枚举"""

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
    PTR = auto()  # LIR 层新增
class NovaType:
    """Nova 统一类型表示（三层 IR 共享）"""

    kind: IRType
    params: List["NovaType"] = field(default_factory=list)
    name: str = ""  # 用于 ADT、类型变量等

    def __eq__(self, other):
        if not isinstance(other, NovaType):
            return False
        return (
            self.kind == other.kind
            and self.params == other.params
            and self.name == other.name
        )

    def __hash__(self):
        return hash((self.kind, tuple(self.params), self.name))

    def __repr__(self):
        if self.kind == IRType.LIST and self.params:
            return f"List[{self.params[0]}]"
        if self.kind == IRType.MAP and len(self.params) >= 2:
            return f"Map[{self.params[0]}, {self.params[1]}]"
        if self.kind == IRType.FUNCTION and len(self.params) >= 1:
            ret = self.params[-1]
            args = ", ".join(str(p) for p in self.params[:-1])
            return f"({args}) -> {ret}"
        if self.kind == IRType.TUPLE:
            elems = ", ".join(str(p) for p in self.params)
            return f"({elems})"
        if self.kind == IRType.ADT and self.params:
            params = ", ".join(str(p) for p in self.params)
            return f"{self.name}[{params}]"
        if self.name:
            return self.name
        return self.kind.name
INT_TYPE = NovaType(IRType.INT)
FLOAT_TYPE = NovaType(IRType.FLOAT)
STRING_TYPE = NovaType(IRType.STRING)
BOOL_TYPE = NovaType(IRType.BOOL)
CHAR_TYPE = NovaType(IRType.CHAR)
UNIT_TYPE = NovaType(IRType.UNIT)
NEVER_TYPE = NovaType(IRType.NEVER)
CLOSURE_TYPE = NovaType(IRType.FUNCTION, name="Closure")
def ListType(elem: NovaType) -> NovaType:
    """构造列表类型 List[T]"""
    return NovaType(IRType.LIST, [elem])
def MapType(key: NovaType, val: NovaType) -> NovaType:
    """构造 Map 类型 Map[K, V]"""
    return NovaType(IRType.MAP, [key, val])
def TupleType(*elems: NovaType) -> NovaType:
    """构造元组类型 (T1, T2, ...)"""
    return NovaType(IRType.TUPLE, list(elems))
def FnType(*params_and_ret: NovaType) -> NovaType:
    """构造函数类型，最后一个参数为返回类型"""
    return NovaType(IRType.FUNCTION, list(params_and_ret))
def ADTType(name: str, *params: NovaType) -> NovaType:
    """构造 ADT 类型"""
    return NovaType(IRType.ADT, list(params), name)
def OptionType(elem: NovaType) -> NovaType:
    """构造 Option[T] 类型"""
    return ADTType("Option", elem)
def ResultType(ok: NovaType, err: NovaType) -> NovaType:
    """构造 Result[T, E] 类型"""
    return ADTType("Result", ok, err)
def _iter_hir_children(expr):
    """遍历 HIR 节点的所有子表达式（生成器）。

    用于 generic_visit/generic_rewrite 的数据驱动遍历。
    产生 (字段类型, 字段名, 值) 元组。
    """
    schema = _HIR_CHILD_FIELDS.get(type(expr))
    if schema is None:
        return
    for field_desc in schema:
        if isinstance(field_desc, tuple):
            kind, fname = field_desc
            if kind == "list":
                for i, child in enumerate(getattr(expr, fname)):
                    yield ("list_item", fname, i, child)
            elif kind == "optional":
                val = getattr(expr, fname)
                if val is not None:
                    yield ("optional", fname, val)
            elif kind == "pair_list":
                for i, (k, v) in enumerate(getattr(expr, fname)):
                    yield ("pair_key", fname, i, k)
                    yield ("pair_val", fname, i, v)
            elif kind == "arm_list":
                for i, arm in enumerate(getattr(expr, fname)):
                    if arm.guard is not None:
                        yield ("arm_guard", fname, i, arm.guard)
                    yield ("arm_body", fname, i, arm.body)
        else:
            yield ("single", field_desc, getattr(expr, field_desc))
