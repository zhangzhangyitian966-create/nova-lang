"""
Nova LIR (Low-Level IR) 节点定义

立即架构手术 A-2（拆分 ir_nodes.py 按层拆分）：
- 来源：ir/ir_nodes.py 行号 1078-1358（LIR 全部节点）
- 原文件兼容：ir_nodes.py 保留完整定义 + TODO(arch_split) 标记，3 轮观察期后删除（A3 阶段）
- 新代码建议：从 ``nova.ir.lir`` 导入 LIR 相关符号
- 向后兼容：``from nova.ir.ir_nodes import LIRModule`` 等旧导入继续工作

LIR 是 Nova 编译器的最底层中间表示，特点：
- 线性指令序列：不再有 SSA Phi 节点（Phi 已降级为 move/copy）
- 接近机器码：寄存器/栈分配已完成或半完成
- 指令选择友好：操作数是寄存器号/栈偏移/立即数
- 用于后端：Native x86_64、C 源码生成、WasmGC 三大后端统一输入
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# 共享类型系统
from .ir_types import (
    NovaType,
)


# ============================================================
# LIR 顶层：模块 / 函数 / 全局 / 数据段
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


# ============================================================
# LIR 指令
# ============================================================


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
    variant_tag: int = 0  # 变体在 ADT 内的索引（第 66 轮 P1 修复：与 type_tag 独立）
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


# ============================================================
# 公共 API 导出
# ============================================================

__all__ = [
    # --- 顶层：模块 / 函数 / 全局 / 数据段 ---
    "LIRModule",
    "LIRFunction",
    "LIRGlobal",
    "LIRData",
    # --- 指令基类 + 子类 ---
    "LIRInstr",
    "LIRLoadConst",
    "LIRLoadGlobal",
    "LIRStoreGlobal",
    "LIRLoadReg",
    "LIRStoreReg",
    "LIRBinOp",
    "LIRUnaryOp",
    "LIRCall",
    "LIRCallIndirect",
    "LIRJump",
    "LIRBranch",
    "LIRSwitch",
    "LIRReturn",
    "LIRLabel",
    "LIRIndex",
    "LIRFieldAccess",
    "LIRBuildList",
    "LIRListAppend",
    "LIRBuildMap",
    "LIRBuildTuple",
    "LIRBuildADT",
    "LIRClosureCreate",
    "LIRPanic",
]
