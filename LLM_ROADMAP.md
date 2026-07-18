# Nova LLM 智能开发路线图

**更新时间**: 2026-07-18 17:00:00
**上次评审**: 第 15 轮（路线图评审）

本路线图由 LLM 智能开发系统动态维护。

## 🏗️ 架构治理

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 |
|------|------|------|--------|------|------|
| ✅ | C 后端接入统一 IR 管线 | hard | 95 | 2-3 天 | - |
| ✅ | C 后端 LIR 代码生成基础框架 | medium | 92 | 1 天 | - |
| ⏳ | 统一 C 后端（LIR 路径功能对齐） | hard | 80 | 2-3 天 | fix_match_lowering, fix_mir_ssa, refactor_visitor_pattern |

## 🔧 IR 降级 / 正确性

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 |
|------|------|------|--------|------|------|
| ✅ | 修复 break/continue 控制流 | medium | 88 | 1-2 天 | - |
| ✅ | 修复列表推导式 MIR 降级 | medium | 85 | 1-2 天 | - |
| ✅ | 修复 LIR MapBuild 降级 bug | easy | 72 | 1 小时 | - |
| ✅ | 修复 Phi 节点 LIR 降级 | medium | 82 | 2-4 小时 | - |
| ✅ | 完善 MIR match 降级（真正的模式匹配） | medium | 92 | 4-6 小时 | - |
| ✅ | 修复 MIR 循环变量绑定 | medium | 90 | 2-4 小时 | - |
| ✅ | SSA 分支环境隔离 + 汇合点 Phi 插入 | medium | 88 | 4-6 小时 | fix_match_lowering, fix_mir_loop_vars |
| ✅ | 修复 while 循环 SSA Phi 插入 | medium | 90 | 4-6 小时 | fix_mir_ssa_branch_env |
| ✅ | 修复赋值表达式 SSA 语义 | medium | 88 | 3-5 小时 | fix_while_phi |
| ✅ | 修复 MIR SSA 构建正确性 | hard | 85 | 2-3 天 | fix_match_lowering, fix_mir_loop_vars |
| ✅ | 实现 MIR SSA 验证 Pass | medium | 86 | 4-6 小时 | fix_while_phi, fix_assign_ssa |
| ✅ | 修复 MIR/LIR 类型传递（消除 UNIT_TYPE 占位） | medium | 84 | 4-6 小时 | fix_mir_ssa |
| ✅ | for 循环 SSA 规范化（去除 hack 式替换） | medium | 76 | 3-5 小时 | fix_mir_ssa |
| ⏳ | 提取循环 SSA 通用方法（消除三重重复） | medium | 88 | 3-5 小时 | for_loop_ssa_normalize |
| ⏳ | 修复列表推导式 latch 块 SSA 替换不完整 | medium | 85 | 2-4 小时 | extract_loop_ssa |
| ⏳ | LIR switch/match 降级补全 | medium | 60 | 3-5 小时 | fix_mir_ssa |

## 🚀 优化 Pass

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 |
|------|------|------|--------|------|------|
| ✅ | 实现死代码消除 Pass (DCE) | easy | 90 | 1-2 小时 | - |
| ✅ | 实现函数内联 Pass | medium | 80 | 2-4 小时 | - |
| ✅ | 实现公共子表达式消除 Pass (CSE) | medium | 75 | 3-5 小时 | - |
| ⏳ | 实现循环不变量外提 Pass (LICM) | hard | 35 | 1-2 周 | fix_mir_ssa, cse_pass, mir_ssa_verifier, ssa_verifier_tests |

## ⚙️ 后端开发

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 |
|------|------|------|--------|------|------|
| ✅ | 补充 WasmGC StoreReg 实现 | easy | 65 | 1 小时 | - |
| ✅ | 修复 LIR C 后端条件分支 | easy | 72 | 30 分钟 | - |
| ⏳ | 修复 Wasm 后端 Label 实现 | medium | 62 | 3-5 小时 | fix_while_phi |
| ⏳ | 实现原生后端函数调用 ABI | hard | 25 | 3-5 天 | fix_mir_ssa |

## 🛠️ 工程质量

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 |
|------|------|------|--------|------|------|
| ✅ | 修复 Pass 管理器静默错误吞噬 | easy | 70 | 30 分钟 | - |
| ✅ | 消除 sys.path hack，标准化包结构 | medium | 88 | 1-2 天 | - |
| ✅ | 统一跨 IR 层字段命名 | medium | 80 | 1 天 | refactor_sys_path |
| ⏳ | 引入 IR Visitor 模式消除重复遍历 | medium | 82 | 6-8 小时 | unify_ir_naming, fix_constant_folding_class |
| ⏳ | 修复 ConstantFolding 的 __class__ 突变问题 | easy | 70 | 1-2 小时 | - |
| ⏳ | 统一后端类型/操作符映射表 | easy | 68 | 2-3 小时 | unify_ir_naming |

## 🧪 测试完善

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 |
|------|------|------|--------|------|------|
| ✅ | 修复原生后端测试导入 | easy | 85 | 30 分钟 | |
| ⏳ | 为 SSA 验证器编写完整测试 | easy | 78 | 2-3 小时 | mir_ssa_verifier, extract_loop_ssa |

---

**进度**: 23/37 (62%)
**已完成**: 23
**进行中**: 0
**待开发**: 13
**已废弃**: 1

> 注：第15轮路线图评审。新增 5 个任务（提取循环SSA通用方法、修复列表推导latch块SSA、修复ConstantFolding __class__突变、SSA验证器测试、统一后端映射表），调整 3 个任务优先级（Visitor模式 75→82、LIR switch/match 70→60、统一C后端 82→80）。下阶段（第16-18轮）聚焦：SSA加固→Visitor重构→后端整合。
