"""
Nova MIR (Mid-Level IR) 节点定义

立即架构手术 A-2（拆分 ir_nodes.py 按层拆分）：
- 来源：ir/ir_nodes.py 行号 824-1072（MIR 全部节点）
- 原文件兼容：ir_nodes.py 保留完整定义 + TODO(arch_split) 标记，3 轮观察期后删除（A3 阶段）
- 新代码建议：从 ``nova.ir.mir`` 导入 MIR 相关符号
- 向后兼容：``from nova.ir.ir_nodes import MIRModule`` 等旧导入继续工作

MIR 是 Nova 编译器的中层中间表示，特点：
- SSA (Static Single Assignment) 形式：每个变量只赋值一次
- CFG (Control Flow Graph)：函数体由基本块 + 跳转组成
- 用于经典优化：公共子表达式消除 (CSE)、循环不变量外提 (LICM)、死代码消除 (DCE) 等
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# 共享类型系统
from .ir_types import (
    INT_TYPE,
    IRType,
    NovaType,
    UNIT_TYPE,
)

# MIRModule.type_defs 引用了 HIRTypeDef（跨层依赖）
# 注意：这里使用 TYPE_CHECKING 避免运行时循环导入问题，真正运行时 HIRTypeDef
# 已在 ir_nodes.py 或通过 hir.py 加载完成。下游通过 ir_nodes 导入时，
# Python 的模块加载顺序保证 hir 先于 mir 加载。
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .hir import HIRTypeDef


# ============================================================
# MIR 顶层：模块 / 函数 / 基本块 / 全局
# ============================================================


@dataclass
class MIRModule:
    """MIR 模块"""

    name: str
    functions: Dict[str, "MIRFunction"] = field(default_factory=dict)
    globals: Dict[str, "MIRGlobal"] = field(default_factory=dict)
    type_defs: Dict[str, "HIRTypeDef"] = field(default_factory=dict)


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


# ============================================================
# MIR 指令
# ============================================================


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


# ============================================================
# MIR 终结指令
# ============================================================


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
# 公共 API 导出
# ============================================================

__all__ = [
    # --- 顶层：模块 / 函数 / 基本块 / 全局 ---
    "MIRModule",
    "MIRFunction",
    "MIRBasicBlock",
    "MIRGlobal",
    # --- 指令基类 + 子类 ---
    "MIRInstruction",
    "MIRConst",
    "MIRLoad",
    "MIRStore",
    "MIRBinOp",
    "MIRUnaryOp",
    "MIRCall",
    "MIRClosureCreate",
    "MIRListBuild",
    "MIRListAppend",
    "MIRTupleBuild",
    "MIRMapBuild",
    "MIRADTBuild",
    "MIRFieldAccess",
    "MIRIndexAccess",
    "MIRPhi",
    # --- 终结指令 ---
    "MIRTerminator",
    "MIRJump",
    "MIRBranch",
    "MIRReturn",
    "MIRSwitch",
    "MIRMatchJump",
    "MIRPanic",
]
