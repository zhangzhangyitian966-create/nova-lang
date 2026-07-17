"""
Nova IR 节点定义 - 三层中间表示

HIR (High-Level IR): 接近源码语义，用于高级优化
MIR (Mid-Level IR):   SSA + CFG，用于经典优化
LIR (Low-Level IR):   接近机器码，用于代码生成

设计参考了 MLIR Dialect 思想，将 IR 分为三层，每层有明确职责：
- HIR: 保留大部分语法结构，经过语义分析（类型已确定，变量已解析）
- MIR: 控制流图 (CFG) + SSA (静态单赋值) 形式
- LIR: 接近机器码表示，寄存器分配、指令选择
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 通用类型系统（三层共享）
# ============================================================


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


@dataclass
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


# 常用类型快捷构造
INT_TYPE = NovaType(IRType.INT)
FLOAT_TYPE = NovaType(IRType.FLOAT)
STRING_TYPE = NovaType(IRType.STRING)
BOOL_TYPE = NovaType(IRType.BOOL)
CHAR_TYPE = NovaType(IRType.CHAR)
UNIT_TYPE = NovaType(IRType.UNIT)
NEVER_TYPE = NovaType(IRType.NEVER)


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


@dataclass
class HIRCallExpr(HIRExpr):
    """HIR 函数调用"""

    function: HIRExpr
    arguments: List[HIRExpr]
    ir_type: NovaType = field(default_factory=lambda: NovaType(IRType.TYPE_VAR))


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
    """MIR 指令基类"""

    result_type: NovaType = field(default_factory=lambda: NovaType(IRType.UNIT))
    result_name: str = ""  # SSA 名，由 lowering 分配


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
    """LIR 函数调用"""

    func_name: str = ""
    arg_count: int = 0


@dataclass
class LIRCallIndirect(LIRInstr):
    """LIR 间接调用"""

    pass


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

    type_tag: int = 0
    field_count: int = 0


@dataclass
class LIRPanic(LIRInstr):
    """LIR panic"""

    message: str = ""
