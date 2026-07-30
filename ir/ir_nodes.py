"""
Nova IR 节点定义 - 三层中间表示（立即架构手术 A · 拆分进行中）

HIR (High-Level IR): 接近源码语义，用于高级优化
MIR (Mid-Level IR):   SSA + CFG，用于经典优化
LIR (Low-Level IR):   接近机器码，用于代码生成

设计参考了 MLIR Dialect 思想，将 IR 分为三层，每层有明确职责：
- HIR: 保留大部分语法结构，经过语义分析（类型已确定，变量已解析）
- MIR: 控制流图 (CFG) + SSA (静态单赋值) 形式
- LIR: 接近机器码表示，寄存器分配、指令选择

模块拆分进度（ARCHITECTURE_VISION.md §2.1 立即架构手术 A）：
  - ✅ **A1（本轮）**：通用类型系统已移至 `ir/ir_types.py`（本文件保留 re-export 兼容层）
  - ⏳  A2：按 IR 层拆分 hir.py / mir.py / lir.py（下一轮）
  - ⏳  A3：两轮观察期后删除冗余定义，保留薄 re-export（A2 完成后两轮）

所有外部 ``from nova.ir.ir_nodes import IRType`` 等导入继续工作，
新代码建议直接从 ``nova.ir.ir_types`` 导入类型相关符号。
"""

from dataclasses import dataclass, field, replace
from enum import Enum, auto  # noqa: F401 （下游模块可能通过 ir_nodes 间接访问）
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 通用类型系统（三层共享）
# 立即架构手术 A1：定义已迁移至 ir/ir_types.py，本处为零破坏性兼容 re-export
# ============================================================

from .ir_types import (  # noqa: E402 （模块级 re-export 放在头部区域之后符合风格）
    ADTType,
    BOOL_TYPE,
    CHAR_TYPE,
    CLOSURE_TYPE,
    FLOAT_TYPE,
    FnType,
    INT_TYPE,
    IRType,
    ListType,
    MapType,
    NEVER_TYPE,
    NovaType,
    OptionType,
    ResultType,
    STRING_TYPE,
    TupleType,
    UNIT_TYPE,
)

# 显式 re-export 清单（供 `from nova.ir.ir_nodes import *` 与 IDE 静态分析使用）
__all__ = [
    # --- 来自 ir_types.py 的类型系统符号 ---
    "IRType",
    "NovaType",
    "INT_TYPE",
    "FLOAT_TYPE",
    "STRING_TYPE",
    "BOOL_TYPE",
    "CHAR_TYPE",
    "UNIT_TYPE",
    "NEVER_TYPE",
    "CLOSURE_TYPE",
    "ListType",
    "MapType",
    "TupleType",
    "FnType",
    "ADTType",
    "OptionType",
    "ResultType",
]

# ============================================================
# HIR (High-Level IR) 节点
# ============================================================


@dataclass
class HIRModule:
    """HIR 模块：顶层编译单元"""

    name: str
    declarations: List["HIRDecl"] = field(default_factory=list)
    type_defs: Dict[str, "HIRTypeDef"] = field(default_factory=dict)
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)


@dataclass
class HIRFunction:
    """HIR 函数定义"""

    name: str
    params: List[Tuple[str, NovaType]]  # [(name, type), ...]
    return_type: NovaType
    body: "HIRExpr"
    is_recursive: bool = False
    type_params: List[str] = field(default_factory=list)


@dataclass
class HIRTypeDef:
    """HIR ADT 类型定义"""

    name: str
    variants: List["HIRVariant"]
    type_params: List[str] = field(default_factory=list)


@dataclass
class HIRVariant:
    """HIR ADT 变体"""

    name: str
    fields: List[Tuple[str, NovaType]]  # [(name, type), ...]


# --- HIR 声明 ---


class HIRDecl:
    """HIR 声明基类"""

    pass


@dataclass
class HIRFnDecl(HIRDecl):
    """HIR 函数声明"""

    fn_def: HIRFunction


@dataclass
class HIRLetDecl(HIRDecl):
    """HIR let/mut 绑定声明"""

    name: str
    ir_type: NovaType
    value: "HIRExpr"
    is_mutable: bool = False


@dataclass
class HIRTypeDecl(HIRDecl):
    """HIR 类型声明"""

    type_def: HIRTypeDef


@dataclass
class HIRAliasDecl(HIRDecl):
    """HIR 类型别名声明"""

    name: str
    target: NovaType


@dataclass
class HIRImportDecl(HIRDecl):
    """HIR 导入声明"""

    module: str


@dataclass
class HIRExportDecl(HIRDecl):
    """HIR 导出声明"""

    name: str


# --- HIR 表达式 ---


class HIRExpr:
    """HIR 表达式基类"""

    pass


@dataclass
class HIRIntLiteral(HIRExpr):
    """HIR 整数字面量"""

    value: int
    ir_type: NovaType = INT_TYPE


@dataclass
class HIRFloatLiteral(HIRExpr):
    """HIR 浮点数字面量"""

    value: float
    ir_type: NovaType = FLOAT_TYPE


@dataclass
class HIRStringLiteral(HIRExpr):
    """HIR 字符串字面量"""

    value: str
    ir_type: NovaType = STRING_TYPE


@dataclass
class HIRBoolLiteral(HIRExpr):
    """HIR 布尔字面量"""

    value: bool
    ir_type: NovaType = BOOL_TYPE


@dataclass
class HIRCharLiteral(HIRExpr):
    """HIR 字符字面量"""

    value: str
    ir_type: NovaType = CHAR_TYPE


@dataclass
class HIRUnitLiteral(HIRExpr):
    """HIR Unit 字面量"""

    ir_type: NovaType = UNIT_TYPE


@dataclass
class HIRIdentifier(HIRExpr):
    """HIR 标识符引用（变量/函数名）"""

    name: str
    ir_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))


@dataclass
class HIRBinaryOp(HIRExpr):
    """HIR 二元操作"""

    op: str  # +, -, *, /, %, ==, !=, <, >, <=, >=, &&, ||, ++, |>
    left: HIRExpr
    right: HIRExpr
    ir_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))


@dataclass
class HIRUnaryOp(HIRExpr):
    """HIR 一元操作"""

    op: str  # -, !
    operand: HIRExpr
    ir_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))


@dataclass
class HIRIfExpr(HIRExpr):
    """HIR if-then-else 表达式"""

    condition: HIRExpr
    consequence: HIRExpr
    alternative: Optional[HIRExpr] = None
    ir_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))


@dataclass
class HIRMatchExpr(HIRExpr):
    """HIR match 表达式"""

    value: HIRExpr
    arms: List["HIRMatchArm"]
    ir_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))


@dataclass
class HIRMatchArm:
    """HIR match 分支"""

    pattern: "HIRPattern"
    guard: Optional[HIRExpr] = None
    body: HIRExpr = field(default_factory=lambda: HIRUnitLiteral())


# --- HIR 模式 ---


class HIRPattern:
    """HIR 模式基类"""

    pass


@dataclass
class HIRIntPattern(HIRPattern):
    """HIR 整数模式"""

    value: int


@dataclass
class HIRFloatPattern(HIRPattern):
    """HIR 浮点数模式"""

    value: float


@dataclass
class HIRStringPattern(HIRPattern):
    """HIR 字符串模式"""

    value: str


@dataclass
class HIRBoolPattern(HIRPattern):
    """HIR 布尔模式"""

    value: bool


@dataclass
class HIRCharPattern(HIRPattern):
    """HIR 字符模式"""

    value: str


@dataclass
class HIRWildcardPattern(HIRPattern):
    """HIR 通配符模式 _"""

    pass


@dataclass
class HIRBindPattern(HIRPattern):
    """HIR 绑定模式 x"""

    name: str


@dataclass
class HIRConstructorPattern(HIRPattern):
    """HIR 构造器模式 Variant(fields...)"""

    type_name: str
    variant_name: str
    field_patterns: List[HIRPattern]


@dataclass
class HIRRangePattern(HIRPattern):
    """HIR 范围模式 low..high"""

    low: int
    high: int


@dataclass
class HIRTuplePattern(HIRPattern):
    """HIR 元组模式 (a, b)"""

    elements: List[HIRPattern]


@dataclass
class HIRListPattern(HIRPattern):
    """HIR 列表模式 [a, b, c]"""

    elements: List[HIRPattern]


# --- HIR 其他表达式 ---


@dataclass
class HIRLambda(HIRExpr):
    """HIR Lambda 表达式"""

    params: List[Tuple[str, NovaType]]  # [(name, type), ...]
    body: HIRExpr
    ir_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))
    return_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))


@dataclass
class HIRCallExpr(HIRExpr):
    """HIR 函数调用

    字段命名说明（跨 IR 层统一）:
    - function / callee: 被调用函数（callee 为统一命名别名）
    - arguments / args: 参数列表（args 为统一命名别名）
    """

    function: HIRExpr
    arguments: List[HIRExpr]
    ir_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))

    @property
    def callee(self) -> HIRExpr:
        """统一命名别名：被调用函数"""
        return self.function

    @callee.setter
    def callee(self, value: HIRExpr):
        self.function = value

    @property
    def args(self) -> List[HIRExpr]:
        """统一命名别名：参数列表"""
        return self.arguments

    @args.setter
    def args(self, value: List[HIRExpr]):
        self.arguments = value


@dataclass
class HIRPipeExpr(HIRExpr):
    """HIR 管道表达式"""

    stages: List[HIRExpr]  # 至少 2 个
    ir_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))


@dataclass
class HIRListExpr(HIRExpr):
    """HIR 列表表达式"""

    elements: List[HIRExpr]
    ir_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))


@dataclass
class HIRTupleExpr(HIRExpr):
    """HIR 元组表达式"""

    elements: List[HIRExpr]
    ir_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))


@dataclass
class HIRMapExpr(HIRExpr):
    """HIR Map 表达式"""

    entries: List[Tuple[HIRExpr, HIRExpr]]  # [(key_expr, value_expr), ...]
    ir_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))


@dataclass
class HIRFieldExpr(HIRExpr):
    """HIR 字段访问"""

    object: HIRExpr
    field_name: str
    ir_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))


@dataclass
class HIRIndexExpr(HIRExpr):
    """HIR 索引访问"""

    object: HIRExpr
    index: HIRExpr
    ir_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))


@dataclass
class HIRBlockExpr(HIRExpr):
    """HIR 代码块"""

    exprs: List[HIRExpr]
    ir_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))


@dataclass
class HIRForExpr(HIRExpr):
    """HIR for 循环"""

    variable: str
    iterable: HIRExpr
    body: HIRExpr
    step: Optional[HIRExpr] = None
    ir_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))


@dataclass
class HIRWhileExpr(HIRExpr):
    """HIR while 循环"""

    condition: HIRExpr
    body: HIRExpr
    ir_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))


@dataclass
class HIRBreakExpr(HIRExpr):
    """HIR break 表达式"""

    ir_type: NovaType = NEVER_TYPE


@dataclass
class HIRContinueExpr(HIRExpr):
    """HIR continue 表达式"""

    ir_type: NovaType = NEVER_TYPE


@dataclass
class HIRListComprehension(HIRExpr):
    """HIR 列表推导式"""

    result_expr: HIRExpr
    variable: str
    iterable: HIRExpr
    filter: Optional[HIRExpr] = None
    ir_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))


@dataclass
class HIRADTConstructor(HIRExpr):
    """HIR ADT 构造器调用"""

    type_name: str
    variant_name: str
    fields: List[HIRExpr]
    ir_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))


@dataclass
class HIRUnwrapExpr(HIRExpr):
    """HIR 解包操作（? 操作符）"""

    operand: HIRExpr
    ir_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))


@dataclass
class HIRAssignExpr(HIRExpr):
    """HIR 赋值表达式"""

    target: HIRExpr  # 通常是 HIRIdentifier
    value: HIRExpr
    ir_type: NovaType = UNIT_TYPE


# ============================================================
# HIR Visitor / Rewriter 基础设施
# ============================================================

# HIR 节点子字段描述表（数据驱动，降低圈复杂度）
# 格式: { 节点类: [ 字段描述, ... ] }
# 字段描述类型:
#   "field_name"              - 单值子表达式
#   ("list", "field_name")    - 子表达式列表
#   ("optional", "field_name") - 可选子表达式
#   ("pair_list", "field_name") - (key_expr, val_expr) 元组列表
#   ("arm_list", "field_name")  - HIRMatchArm 列表（arm 有 guard 和 body 两个子表达式）
_HIR_CHILD_FIELDS = {
    # 叶子节点（无子表达式）
    HIRIntLiteral: [],
    HIRFloatLiteral: [],
    HIRStringLiteral: [],
    HIRBoolLiteral: [],
    HIRCharLiteral: [],
    HIRUnitLiteral: [],
    HIRIdentifier: [],
    HIRBreakExpr: [],
    HIRContinueExpr: [],
    # 一元子节点
    HIRUnaryOp: ["operand"],
    HIRFieldExpr: ["object"],
    HIRUnwrapExpr: ["operand"],
    # 二元子节点
    HIRBinaryOp: ["left", "right"],
    HIRAssignExpr: ["target", "value"],
    HIRIndexExpr: ["object", "index"],
    # 列表子节点
    HIRBlockExpr: [("list", "exprs")],
    HIRListExpr: [("list", "elements")],
    HIRTupleExpr: [("list", "elements")],
    HIRPipeExpr: [("list", "stages")],
    HIRADTConstructor: [("list", "fields")],
    # 键值对列表
    HIRMapExpr: [("pair_list", "entries")],
    # 可选子节点
    HIRIfExpr: ["condition", "consequence", ("optional", "alternative")],
    # 声明（非表达式但可被访问）
    HIRLetDecl: ["value"],
    # 函数调用
    HIRCallExpr: ["function", ("list", "arguments")],
    # Match（arm 列表特殊处理）
    HIRMatchExpr: ["value", ("arm_list", "arms")],
    # 循环
    HIRForExpr: ["iterable", "body", ("optional", "step")],
    HIRWhileExpr: ["condition", "body"],
    # Lambda
    HIRLambda: ["body"],
    # 列表推导式
    HIRListComprehension: ["result_expr", "iterable", ("optional", "filter")],
}


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


class HIRVisitor:
    """HIR 只读访问者基类

    遍历 HIR 表达式树，对每个节点调用对应的 visit_* 方法。
    默认实现递归访问所有子节点。
    子类只需重写感兴趣的节点类型的 visit_* 方法。

    使用方式：
        visitor = MyVisitor()
        visitor.visit(expr)
    """

    def visit(self, expr):
        """访问表达式，自动分派到对应的 visit_* 方法"""
        method_name = "visit_" + type(expr).__name__
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(expr)

    def generic_visit(self, expr):
        """默认访问：递归访问所有子表达式（数据驱动实现）"""
        for item in _iter_hir_children(expr):
            kind = item[0]
            if kind in ("single", "optional"):
                self.visit(item[2])
            elif kind == "list_item":
                self.visit(item[3])
            elif kind in ("pair_key", "pair_val", "arm_guard", "arm_body"):
                self.visit(item[3])


class HIRRewriter:
    """HIR 变换式访问者基类

    遍历 HIR 表达式树并返回变换后的新树。
    默认实现递归重建所有子节点，保持结构不变。
    子类重写感兴趣的 rewrite_* 方法，返回新节点。

    返回约定：rewrite_* 方法返回 (new_expr, changed)
    - new_expr: 变换后的表达式
    - changed: bool，是否发生了变化

    使用方式：
        rewriter = MyRewriter()
        new_expr, changed = rewriter.rewrite(expr)
    """

    def rewrite(self, expr):
        """变换表达式，自动分派到对应的 rewrite_* 方法"""
        method_name = "rewrite_" + type(expr).__name__
        rewriter = getattr(self, method_name, self.generic_rewrite)
        return rewriter(expr)

    def _rewrite_list_field(self, expr, fname):
        """处理 list 类型字段：递归变换列表中每个子表达式

        Args:
            expr: 当前 HIR 节点
            fname: 列表字段名

        Returns:
            (new_list, changed) 元组；changed 为 False 时 new_list 为 None
        """
        old_list = getattr(expr, fname)
        new_list = []
        changed = False
        for child in old_list:
            new_child, child_changed = self.rewrite(child)
            new_list.append(new_child)
            changed |= child_changed
        return (new_list, True) if changed else (None, False)

    def _rewrite_optional_field(self, expr, fname):
        """处理 optional 类型字段：None 时跳过，非 None 时递归变换

        Args:
            expr: 当前 HIR 节点
            fname: 可选字段名

        Returns:
            (new_val, changed) 元组；changed 为 False 时 new_val 为 None
        """
        old_val = getattr(expr, fname)
        if old_val is None:
            return (None, False)
        new_val, changed = self.rewrite(old_val)
        return (new_val, True) if changed else (None, False)

    def _rewrite_pair_list_field(self, expr, fname):
        """处理 pair_list 类型字段：递归变换每对 (key, value) 的两端

        Args:
            expr: 当前 HIR 节点
            fname: 键值对列表字段名

        Returns:
            (new_pairs, changed) 元组；changed 为 False 时 new_pairs 为 None
        """
        old_pairs = getattr(expr, fname)
        new_pairs = []
        changed = False
        for k, v in old_pairs:
            new_k, k_changed = self.rewrite(k)
            new_v, v_changed = self.rewrite(v)
            new_pairs.append((new_k, new_v))
            changed |= k_changed or v_changed
        return (new_pairs, True) if changed else (None, False)

    def _rewrite_arm_list_field(self, expr, fname):
        """处理 arm_list 类型字段：递归变换每个 match arm 的 guard 和 body

        Args:
            expr: 当前 HIR 节点
            fname: arm 列表字段名

        Returns:
            (new_arms, changed) 元组；changed 为 False 时 new_arms 为 None
        """
        old_arms = getattr(expr, fname)
        new_arms = []
        changed = False
        for arm in old_arms:
            new_guard = arm.guard
            guard_changed = False
            if arm.guard is not None:
                new_guard, guard_changed = self.rewrite(arm.guard)
            new_body, body_changed = self.rewrite(arm.body)
            if guard_changed or body_changed:
                new_arms.append(replace(arm, guard=new_guard, body=new_body))
                changed = True
            else:
                new_arms.append(arm)
        return (new_arms, True) if changed else (None, False)

    # 字段类型 → handler 方法名的调度表
    _FIELD_REWRITERS = {
        "list": "_rewrite_list_field",
        "optional": "_rewrite_optional_field",
        "pair_list": "_rewrite_pair_list_field",
        "arm_list": "_rewrite_arm_list_field",
    }

    def generic_rewrite(self, expr):
        """默认变换：递归变换所有子节点，有变化则重建节点（数据驱动实现）

        使用 _HIR_CHILD_FIELDS 表驱动遍历 + _FIELD_REWRITERS 调度表分派，
        将 4 种字段类型的处理逻辑委托给独立的 _rewrite_*_field 方法，
        用 dataclasses.replace 重建节点。
        """
        schema = _HIR_CHILD_FIELDS.get(type(expr))
        if not schema:
            # 未知类型或叶子节点：直接返回
            return expr, False

        changed = False
        # 收集需要替换的字段: {field_name: new_value}
        replacements = {}

        for field_desc in schema:
            if isinstance(field_desc, tuple):
                kind, fname = field_desc
                handler_name = self._FIELD_REWRITERS.get(kind)
                if handler_name:
                    new_val, field_changed = getattr(self, handler_name)(expr, fname)
                    if field_changed:
                        replacements[fname] = new_val
                        changed = True
            else:
                # 单值子表达式
                old_val = getattr(expr, field_desc)
                new_val, field_changed = self.rewrite(old_val)
                if field_changed:
                    replacements[field_desc] = new_val
                    changed = True

        if not changed:
            return expr, False

        # 用 dataclasses.replace 重建节点
        new_expr = replace(expr, **replacements)
        return new_expr, True


# ============================================================
# MIR (Mid-Level IR) 节点 - SSA + CFG
# ============================================================


@dataclass
class MIRModule:
    """MIR 模块"""

    name: str
    functions: Dict[str, "MIRFunction"] = field(default_factory=dict)
    globals: Dict[str, "MIRGlobal"] = field(default_factory=dict)
    type_defs: Dict[str, HIRTypeDef] = field(default_factory=dict)


@dataclass
class MIRFunction:
    """MIR 函数（SSA + CFG 形式）"""

    name: str
    params: List[Tuple[str, NovaType, str]]  # [(name, type, ssa_name), ...]
    return_type: NovaType
    basic_blocks: List["MIRBasicBlock"] = field(default_factory=list)
    entry_block: str = "bb0"


@dataclass
class MIRBasicBlock:
    """MIR 基本块"""

    label: str  # "bb0", "bb1", ...
    instructions: List["MIRInstruction"] = field(default_factory=list)
    terminator: Optional["MIRTerminator"] = None


@dataclass
class MIRGlobal:
    """MIR 全局变量"""

    name: str
    ir_type: NovaType
    init_value: Optional["MIRInstruction"] = None
    is_mutable: bool = False


# --- MIR 指令 ---


@dataclass
class MIRInstruction:
    """MIR 指令基类

    字段命名说明（跨 IR 层统一）:
    - result_type / ir_type: 指令结果类型（ir_type 为统一命名别名）
    - result_name: SSA 结果名
    """

    result_type: NovaType = field(default_factory=lambda: NovaType(IRType.UNIT))
    result_name: str = ""  # SSA 名，由 lowering 分配

    @property
    def ir_type(self) -> NovaType:
        """统一命名别名：指令结果类型"""
        return self.result_type

    @ir_type.setter
    def ir_type(self, value: NovaType):
        self.result_type = value


@dataclass
class MIRConst(MIRInstruction):
    """MIR 常量"""

    value: Any = None
    const_type: str = ""  # "int", "float", "string", "bool", "unit"


@dataclass
class MIRLoad(MIRInstruction):
    """MIR 加载变量"""

    name: str = ""  # 变量名（从全局或闭包捕获）


@dataclass
class MIRStore(MIRInstruction):
    """MIR 存储变量"""

    name: str = ""  # 变量名
    value: str = ""  # SSA 名


@dataclass
class MIRBinOp(MIRInstruction):
    """MIR 二元操作"""

    op: str = ""
    left: str = ""  # SSA 名
    right: str = ""  # SSA 名


@dataclass
class MIRUnaryOp(MIRInstruction):
    """MIR 一元操作"""

    op: str = ""
    operand: str = ""  # SSA 名


@dataclass
class MIRCall(MIRInstruction):
    """MIR 函数调用"""

    callee: str = ""  # 函数名或 SSA 名
    args: List[str] = field(default_factory=list)  # SSA 名列表


@dataclass
class MIRClosureCreate(MIRInstruction):
    """MIR 闭包创建"""

    fn_name: str = ""
    captures: List[str] = field(default_factory=list)  # 被捕获的 SSA 名列表


@dataclass
class MIRListBuild(MIRInstruction):
    """MIR 列表构建"""

    elements: List[str] = field(default_factory=list)  # SSA 名列表
    elem_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))


@dataclass
class MIRListAppend(MIRInstruction):
    """MIR 列表追加元素（返回新的列表）"""

    list_ssa: str = ""  # 目标列表 SSA 名
    element_ssa: str = ""  # 待追加元素 SSA 名


@dataclass
class MIRTupleBuild(MIRInstruction):
    """MIR 元组构建"""

    elements: List[str] = field(default_factory=list)


@dataclass
class MIRMapBuild(MIRInstruction):
    """MIR Map 构建"""

    entries: List[Tuple[str, str]] = field(
        default_factory=list
    )  # [(key_ssa, val_ssa), ...]


@dataclass
class MIRADTBuild(MIRInstruction):
    """MIR ADT 构建"""

    type_name: str = ""
    variant_name: str = ""
    fields: List[str] = field(default_factory=list)  # SSA 名列表


@dataclass
class MIRFieldAccess(MIRInstruction):
    """MIR 字段访问"""

    object: str = ""  # SSA 名
    field_name: str = ""
    field_index: int = 0


@dataclass
class MIRIndexAccess(MIRInstruction):
    """MIR 索引访问"""

    object: str = ""
    index: str = ""


@dataclass
class MIRPhi(MIRInstruction):
    """MIR SSA phi 节点"""

    sources: List[Tuple[str, str]] = field(
        default_factory=list
    )  # [(block_label, ssa_name), ...]


# --- MIR 终结指令 ---


class MIRTerminator:
    """MIR 终结指令基类"""

    pass


@dataclass
class MIRJump(MIRTerminator):
    """MIR 无条件跳转"""

    target: str = ""  # 基本块标签


@dataclass
class MIRBranch(MIRTerminator):
    """MIR 条件分支"""

    condition: str = ""  # SSA 名
    true_target: str = ""
    false_target: str = ""


@dataclass
class MIRReturn(MIRTerminator):
    """MIR 返回"""

    value: Optional[str] = None  # SSA 名，None 表示 Unit


@dataclass
class MIRSwitch(MIRTerminator):
    """MIR switch 跳转"""

    value: str = ""  # SSA 名
    cases: List[Tuple[Any, str]] = field(
        default_factory=list
    )  # [(value, target_block), ...]
    default_target: str = ""


@dataclass
class MIRMatchJump(MIRTerminator):
    """MIR match 跳转"""

    value: str = ""
    variant_tests: List[Tuple[str, List[str], str]] = field(
        default_factory=list
    )  # [(variant_name, fields, target_block), ...]
    default_target: str = ""


@dataclass
class MIRPanic(MIRTerminator):
    """MIR panic/abort"""

    message: str = ""


# ============================================================
# LIR (Low-Level IR) 节点 - 接近机器码
# ============================================================


@dataclass
class LIRModule:
    """LIR 模块"""

    name: str
    functions: Dict[str, "LIRFunction"] = field(default_factory=dict)
    globals: List["LIRGlobal"] = field(default_factory=list)
    data_section: List["LIRData"] = field(default_factory=list)


@dataclass
class LIRFunction:
    """LIR 函数"""

    name: str
    params: List[Tuple[str, NovaType]]  # [(reg/stack_offset, type), ...]
    return_type: NovaType
    body: List["LIRInstr"] = field(default_factory=list)  # 线性指令序列
    stack_size: int = 0  # 栈帧大小
    reg_alloc: Dict[str, int] = field(default_factory=dict)  # SSA -> 寄存器/栈位


@dataclass
class LIRGlobal:
    """LIR 全局变量"""

    name: str
    ir_type: NovaType
    data: Optional["LIRData"] = None


@dataclass
class LIRData:
    """LIR 数据段"""

    name: str
    value: bytes = b""  # 原始数据


# --- LIR 指令 ---


@dataclass
class LIRInstr:
    """LIR 指令基类，带寄存器/栈分配信息"""

    src_locs: List[Tuple[str, NovaType]] = field(
        default_factory=list
    )  # [(reg/stack, type), ...]
    dst_loc: Optional[Tuple[str, NovaType]] = None  # (reg/stack, type)
    src_locs_imm: List[Any] = field(default_factory=list)  # 立即数


@dataclass
class LIRLoadConst(LIRInstr):
    """LIR 加载常量"""

    value: Any = None
    const_type: str = ""


@dataclass
class LIRLoadGlobal(LIRInstr):
    """LIR 加载全局变量"""

    global_name: str = ""


@dataclass
class LIRStoreGlobal(LIRInstr):
    """LIR 存储全局变量"""

    global_name: str = ""


@dataclass
class LIRLoadReg(LIRInstr):
    """LIR 寄存器间传送"""

    pass


@dataclass
class LIRStoreReg(LIRInstr):
    """LIR 存储到寄存器/栈"""

    pass


@dataclass
class LIRBinOp(LIRInstr):
    """LIR 二元操作"""

    op: str = ""


@dataclass
class LIRUnaryOp(LIRInstr):
    """LIR 一元操作"""

    op: str = ""


@dataclass
class LIRCall(LIRInstr):
    """LIR 函数调用

    字段命名说明（跨 IR 层统一）:
    - func_name / callee: 被调用函数名（callee 为统一命名别名）
    - arg_count / args: 参数数量（args 为统一命名别名，返回 arg_locs 长度）
    - arg_locs: 参数位置列表（每个参数的寄存器/栈位置 + 类型）
    - caller_saved_to_preserve: 调用点需要保存的 caller-saved 寄存器列表
      （由寄存器分配器根据活跃区间分析填充，替代保守的全部保存）
    """

    func_name: str = ""
    arg_count: int = 0
    arg_locs: List[Tuple[str, NovaType]] = field(
        default_factory=list
    )  # [(reg/stack, type), ...]
    caller_saved_to_preserve: List[int] = field(default_factory=list)

    @property
    def callee(self) -> str:
        """统一命名别名：被调用函数名"""
        return self.func_name

    @callee.setter
    def callee(self, value: str):
        self.func_name = value

    @property
    def args(self) -> List[Tuple[str, NovaType]]:
        """统一命名别名：参数位置列表"""
        return self.arg_locs

    @args.setter
    def args(self, value: List[Tuple[str, NovaType]]):
        self.arg_locs = value
        self.arg_count = len(value)


@dataclass
class LIRCallIndirect(LIRInstr):
    """LIR 间接调用（闭包调用/函数指针调用）

    通过闭包或函数指针调用函数，参数在 src_locs 中，
    第一个 src_loc 是闭包/函数指针对象，后续是参数。
    """

    arg_count: int = 0
    arg_locs: List[Tuple[str, NovaType]] = field(
        default_factory=list
    )  # [(reg/stack, type), ...]
    caller_saved_to_preserve: List[int] = field(default_factory=list)

    @property
    def args(self) -> List[Tuple[str, NovaType]]:
        """统一命名别名：参数位置列表"""
        return self.arg_locs

    @args.setter
    def args(self, value: List[Tuple[str, NovaType]]):
        self.arg_locs = value
        self.arg_count = len(value)


@dataclass
class LIRJump(LIRInstr):
    """LIR 无条件跳转"""

    target: str = ""


@dataclass
class LIRBranch(LIRInstr):
    """LIR 条件跳转"""

    true_target: str = ""
    false_target: str = ""


@dataclass
class LIRSwitch(LIRInstr):
    """LIR switch 多分支跳转

    将值与多个 case 比较，匹配成功跳转到对应目标块，
    都不匹配则跳转到 default_target。
    后端可以选择实现为 if-else 级联或跳转表。
    """

    cases: List[Tuple[Any, str]] = field(
        default_factory=list
    )  # [(value, target_block), ...]
    default_target: str = ""


@dataclass
class LIRReturn(LIRInstr):
    """LIR 返回"""

    pass


@dataclass
class LIRLabel(LIRInstr):
    """LIR 标签"""

    name: str = ""


@dataclass
class LIRIndex(LIRInstr):
    """LIR 索引操作"""

    pass


@dataclass
class LIRFieldAccess(LIRInstr):
    """LIR 字段访问"""

    offset: int = 0


@dataclass
class LIRBuildList(LIRInstr):
    """LIR 构建列表"""

    count: int = 0


@dataclass
class LIRListAppend(LIRInstr):
    """LIR 列表追加元素"""

    pass


@dataclass
class LIRBuildMap(LIRInstr):
    """LIR 构建映射（Map）"""

    entry_count: int = 0


@dataclass
class LIRBuildTuple(LIRInstr):
    """LIR 构建元组"""

    count: int = 0


@dataclass
class LIRBuildADT(LIRInstr):
    """LIR 构建 ADT"""

    type_name: str = ""
    variant_name: str = ""
    type_tag: int = 0
    field_count: int = 0


@dataclass
class LIRClosureCreate(LIRInstr):
    """LIR 闭包创建

    创建一个闭包对象，包含函数指针和捕获的环境变量。
    fn_name 指向被捕获的函数名（在 LIRModule 中作为独立函数存在）。
    capture_locs 是被捕获变量的位置列表（寄存器/栈槽）。
    """

    fn_name: str = ""
    capture_count: int = 0


@dataclass
class LIRPanic(LIRInstr):
    """LIR panic"""

    message: str = ""
