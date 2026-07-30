"""
Nova HIR (High-Level IR) 节点定义

立即架构手术 A-2（拆分 ir_nodes.py 按层拆分）：
- 来源：ir/ir_nodes.py 行号 78-817（HIR 全部节点 + 基础设施）
- 原文件兼容：ir_nodes.py 保留完整定义 + TODO(arch_split) 标记，3 轮观察期后删除（A3 阶段）
- 新代码建议：从 ``nova.ir.hir`` 导入 HIR 相关符号
- 向后兼容：``from nova.ir.ir_nodes import HIRModule`` 等旧导入继续工作

HIR 是 Nova 编译器的最上层中间表示，特点：
- 保留大部分源码语义结构（if/match/for/while/列表推导式 等）
- 经过语义分析：类型已推断、变量已解析、闭包捕获已确定
- 用于高级优化：常量折叠、死代码消除、函数内联等
"""

from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional, Tuple

# 共享类型系统（来自 A1 阶段抽取出的 ir_types.py）
from .ir_types import (
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

# ============================================================
# HIR 顶层：模块 / 函数 / 类型定义
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


# ============================================================
# HIR 声明
# ============================================================


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


# ============================================================
# HIR 表达式基类 + 字面量
# ============================================================


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


# ============================================================
# HIR 运算 + 控制流表达式
# ============================================================


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


# ============================================================
# HIR 模式（用于 match 表达式）
# ============================================================


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


# ============================================================
# HIR 其他表达式（Lambda/调用/管道/容器/字段/循环/赋值）
# ============================================================


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
# 公共 API 导出
# ============================================================

__all__ = [
    # --- 顶层模块/函数/类型定义 ---
    "HIRModule",
    "HIRFunction",
    "HIRTypeDef",
    "HIRVariant",
    # --- 声明 ---
    "HIRDecl",
    "HIRFnDecl",
    "HIRLetDecl",
    "HIRTypeDecl",
    "HIRAliasDecl",
    "HIRImportDecl",
    "HIRExportDecl",
    # --- 表达式基类 + 字面量 ---
    "HIRExpr",
    "HIRIntLiteral",
    "HIRFloatLiteral",
    "HIRStringLiteral",
    "HIRBoolLiteral",
    "HIRCharLiteral",
    "HIRUnitLiteral",
    "HIRIdentifier",
    # --- 运算 / 控制流 ---
    "HIRBinaryOp",
    "HIRUnaryOp",
    "HIRIfExpr",
    "HIRMatchExpr",
    "HIRMatchArm",
    # --- 模式 ---
    "HIRPattern",
    "HIRIntPattern",
    "HIRFloatPattern",
    "HIRStringPattern",
    "HIRBoolPattern",
    "HIRCharPattern",
    "HIRWildcardPattern",
    "HIRBindPattern",
    "HIRConstructorPattern",
    "HIRRangePattern",
    "HIRTuplePattern",
    "HIRListPattern",
    # --- 其他表达式（Lambda/调用/管道/容器/字段/循环）---
    "HIRLambda",
    "HIRCallExpr",
    "HIRPipeExpr",
    "HIRListExpr",
    "HIRTupleExpr",
    "HIRMapExpr",
    "HIRFieldExpr",
    "HIRIndexExpr",
    "HIRBlockExpr",
    "HIRForExpr",
    "HIRWhileExpr",
    "HIRBreakExpr",
    "HIRContinueExpr",
    "HIRListComprehension",
    "HIRADTConstructor",
    "HIRUnwrapExpr",
    "HIRAssignExpr",
    # --- 基础设施（Visitor/Rewriter + 辅助函数/表）---
    "_HIR_CHILD_FIELDS",
    "_iter_hir_children",
    "HIRVisitor",
    "HIRRewriter",
]
