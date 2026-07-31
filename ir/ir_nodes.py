"""
Nova IR 节点定义 - 三层中间表示（立即架构手术 A · 已完成）

立即架构手术 A（拆 ir/ir_nodes.py 上帝模块）最终形态：
  - ✅ A1：通用类型系统 → `ir/ir_types.py`
  - ✅ A2：按层拆分 → `ir/hir.py`（HIR 节点）、`ir/mir.py`（MIR 节点）、`ir/lir.py`（LIR 节点）
  - ✅ A3（本轮）：本文件瘦身，仅保留薄 re-export 兼容层

设计参考了 MLIR Dialect 思想，将 IR 分为三层，每层有明确职责：
- HIR: 保留大部分语法结构，经过语义分析（类型已确定，变量已解析）
- MIR: 控制流图 (CFG) + SSA (静态单赋值) 形式
- LIR: 接近机器码表示，寄存器分配、指令选择

所有外部 ``from nova.ir.ir_nodes import IRType`` 等导入继续工作。
新代码推荐直接从子模块导入：
  - 类型相关  → ``from nova.ir.ir_types import ...``
  - HIR 节点   → ``from nova.ir.hir import ...``
  - MIR 节点   → ``from nova.ir.mir import ...``
  - LIR 节点   → ``from nova.ir.lir import ...``
"""

from dataclasses import dataclass, field, replace  # noqa: F401（下游间接访问兼容）
from enum import Enum, auto  # noqa: F401（下游间接访问兼容）
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 通用类型系统（三层共享）—— A1 迁移到 ir/ir_types.py
# ============================================================

from .ir_types import (  # noqa: E402
    ADTType,
    BOOL_TYPE,
    BoxType,
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
# HIR (High-Level IR) 节点 —— A2/A3 迁移到 ir/hir.py
# ============================================================

from .hir import (  # noqa: E402
    # 顶层：模块 / 函数 / 类型定义
    HIRModule,
    HIRFunction,
    HIRTypeDef,
    HIRVariant,
    # 声明
    HIRDecl,
    HIRFnDecl,
    HIRLetDecl,
    HIRTypeDecl,
    HIRAliasDecl,
    HIRImportDecl,
    HIRExportDecl,
    # 表达式基类 + 字面量
    HIRExpr,
    HIRIntLiteral,
    HIRFloatLiteral,
    HIRStringLiteral,
    HIRBoolLiteral,
    HIRCharLiteral,
    HIRUnitLiteral,
    HIRIdentifier,
    # 运算 / 控制流
    HIRBinaryOp,
    HIRUnaryOp,
    HIRIfExpr,
    HIRMatchExpr,
    HIRMatchArm,
    # 模式（用于 match）
    HIRPattern,
    HIRIntPattern,
    HIRFloatPattern,
    HIRStringPattern,
    HIRBoolPattern,
    HIRCharPattern,
    HIRWildcardPattern,
    HIRBindPattern,
    HIRConstructorPattern,
    HIRRangePattern,
    HIRTuplePattern,
    HIRListPattern,
    # 其他表达式：Lambda/调用/管道/容器/字段/循环
    HIRLambda,
    HIRCallExpr,
    HIRPipeExpr,
    HIRListExpr,
    HIRTupleExpr,
    HIRMapExpr,
    HIRFieldExpr,
    HIRIndexExpr,
    HIRBlockExpr,
    HIRForExpr,
    HIRWhileExpr,
    HIRBreakExpr,
    HIRContinueExpr,
    HIRListComprehension,
    HIRADTConstructor,
    HIRUnwrapExpr,
    HIRAssignExpr,
    # 基础设施：Visitor/Rewriter + 数据驱动表/函数
    _HIR_CHILD_FIELDS,
    _iter_hir_children,
    HIRVisitor,
    HIRRewriter,
)

# ============================================================
# MIR (Mid-Level IR) 节点 - SSA + CFG —— A2/A3 迁移到 ir/mir.py
# ============================================================

from .mir import (  # noqa: E402
    # 顶层：模块 / 函数 / 基本块 / 全局
    MIRModule,
    MIRFunction,
    MIRBasicBlock,
    MIRGlobal,
    # 指令基类 + 子类
    MIRInstruction,
    MIRConst,
    MIRLoad,
    MIRStore,
    MIRBinOp,
    MIRUnaryOp,
    MIRCall,
    MIRClosureCreate,
    MIRListBuild,
    MIRListAppend,
    MIRTupleBuild,
    MIRMapBuild,
    MIRADTBuild,
    MIRFieldAccess,
    MIRIndexAccess,
    MIRPhi,
    # 终结指令
    MIRTerminator,
    MIRJump,
    MIRBranch,
    MIRReturn,
    MIRSwitch,
    MIRMatchJump,
    MIRPanic,
)

# ============================================================
# LIR (Low-Level IR) 节点 - 接近机器码 —— A2/A3 迁移到 ir/lir.py
# ============================================================

from .lir import (  # noqa: E402
    # 顶层：模块 / 函数 / 全局 / 数据段
    LIRModule,
    LIRFunction,
    LIRGlobal,
    LIRData,
    # 指令基类 + 子类
    LIRInstr,
    LIRLoadConst,
    LIRLoadGlobal,
    LIRStoreGlobal,
    LIRLoadReg,
    LIRStoreReg,
    LIRBinOp,
    LIRUnaryOp,
    LIRCall,
    LIRCallIndirect,
    LIRJump,
    LIRBranch,
    LIRSwitch,
    LIRReturn,
    LIRLabel,
    LIRIndex,
    LIRFieldAccess,
    LIRBuildList,
    LIRListAppend,
    LIRBuildMap,
    LIRBuildTuple,
    LIRBuildADT,
    LIRClosureCreate,
    LIRPanic,
)

# ============================================================
# 显式 re-export 清单（供 `from nova.ir.ir_nodes import *` 与 IDE 使用）
# ============================================================

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
    "BoxType",
    # --- 来自 hir.py 的 HIR 节点 ---
    # 顶层：模块 / 函数 / 类型定义
    "HIRModule",
    "HIRFunction",
    "HIRTypeDef",
    "HIRVariant",
    # 声明
    "HIRDecl",
    "HIRFnDecl",
    "HIRLetDecl",
    "HIRTypeDecl",
    "HIRAliasDecl",
    "HIRImportDecl",
    "HIRExportDecl",
    # 表达式基类 + 字面量
    "HIRExpr",
    "HIRIntLiteral",
    "HIRFloatLiteral",
    "HIRStringLiteral",
    "HIRBoolLiteral",
    "HIRCharLiteral",
    "HIRUnitLiteral",
    "HIRIdentifier",
    # 运算 / 控制流
    "HIRBinaryOp",
    "HIRUnaryOp",
    "HIRIfExpr",
    "HIRMatchExpr",
    "HIRMatchArm",
    # 模式
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
    # 其他表达式
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
    # 基础设施
    "_HIR_CHILD_FIELDS",
    "_iter_hir_children",
    "HIRVisitor",
    "HIRRewriter",
    # --- 来自 mir.py 的 MIR 节点 ---
    "MIRModule",
    "MIRFunction",
    "MIRBasicBlock",
    "MIRGlobal",
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
    "MIRTerminator",
    "MIRJump",
    "MIRBranch",
    "MIRReturn",
    "MIRSwitch",
    "MIRMatchJump",
    "MIRPanic",
    # --- 来自 lir.py 的 LIR 节点 ---
    "LIRModule",
    "LIRFunction",
    "LIRGlobal",
    "LIRData",
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
