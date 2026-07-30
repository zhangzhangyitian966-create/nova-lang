"""Nova IR 层 - 三层中间表示（HIR → MIR → LIR）

立即架构手术 A 进度（拆 ir/ir_nodes.py 上帝模块）：

- ✅ **A1**：通用类型系统已独立为 :mod:`~.ir_types`
- ⏳  **A2**：HIR / MIR / LIR 节点按层拆分（下一轮）
- ⏳  **A3**：两轮观察期后 :mod:`~.ir_nodes` 变薄为 re-export

下游代码无需任何修改：所有 100+ 处对 ``nova.ir.ir_nodes`` 的导入
（IRType / NovaType / 各层节点等）通过兼容 re-export 层继续工作。

新代码推荐导入路径：
  - 类型相关 → ``from nova.ir.ir_types import ...``
  - HIR 节点   → ``from nova.ir.ir_nodes import HIR...``（A2 后独立）
  - MIR 节点   → ``from nova.ir.ir_nodes import MIR...``（A2 后独立）
  - LIR 节点   → ``from nova.ir.ir_nodes import LIR...``（A2 后独立）
  - 优化 Pass  → ``from nova.ir.pass_manager import ...``
  - IR 降级    → ``from nova.ir.hir_lowering import HIRLowering`` 等
"""

# 兼容 re-export：保持 `from nova.ir import IRType` 等旧用法可用
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

__all__ = [
    # --- 类型系统（来自 ir_types）---
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
    # --- 子模块 ---
    "ir_types",
    "ir_nodes",
    "hir_lowering",
    "mir_lowering",
    "lir_lowering",
    "pass_manager",
    "cfg_utils",
]
