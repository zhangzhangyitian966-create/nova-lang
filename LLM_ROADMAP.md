# Nova LLM 智能开发路线图

**更新时间**: 2026-07-16 14:30:00
**上次评审**: 第 9 轮（路线图评审）

本路线图由 LLM 智能开发系统动态维护。

## 🏗️ 架构治理

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 |
|------|------|------|--------|------|------|
| ✅ | C 后端接入统一 IR 管线 | hard | 95 | 2-3 天 | - |
| ✅ | C 后端 LIR 代码生成基础框架 | medium | 92 | 1 天 | - |
| ⏳ | 统一 C 后端（LIR 路径功能对齐） | hard | 78 | 2-3 天 | fix_match_lowering, fix_mir_ssa |

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
| ⏳ | 修复赋值表达式 SSA 语义 | medium | 88 | 3-5 小时 | fix_while_phi |
| ⏳ | 修复 MIR SSA 构建正确性（循环 Phi + 完整 SSA） | hard | 85 | 2-3 天 | fix_mir_ssa_branch_env |
| ✅ | 实现 MIR SSA 验证 Pass | medium | 86 | 4-6 小时 | fix_while_phi, fix_assign_ssa |

## 🚀 优化 Pass

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 |
|------|------|------|--------|------|------|
| ✅ | 实现死代码消除 Pass (DCE) | easy | 90 | 1-2 小时 | - |
| ✅ | 实现函数内联 Pass | medium | 80 | 2-4 小时 | - |
| ✅ | 实现公共子表达式消除 Pass (CSE) | medium | 75 | 3-5 小时 | - |
| ⏳ | 实现循环不变量外提 Pass (LICM) | hard | 35 | 1-2 周 | fix_mir_ssa, cse_pass, mir_ssa_verifier |

## ⚙️ 后端开发

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 |
|------|------|------|--------|------|------|
| ✅ | 补充 WasmGC StoreReg 实现 | easy | 65 | 1 小时 | - |
| ⏳ | 修复 LIR C 后端条件分支 | easy | 72 | 30 分钟 | - |
| ⏳ | 修复 Wasm 后端 Label 实现 | medium | 65 | 3-5 小时 | fix_while_phi |
| ⏳ | 实现原生后端函数调用 ABI | hard | 40 | 3-5 天 | fix_mir_ssa |

## 🛠️ 工程质量

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 |
|------|------|------|--------|------|------|
| ✅ | 修复 Pass 管理器静默错误吞噬 | easy | 70 | 30 分钟 | - |
| ⏳ | 消除 sys.path hack，标准化包结构 | medium | 85 | 1-2 天 | - |
| ⏳ | 统一跨 IR 层字段命名 | medium | 80 | 1 天 | refactor_sys_path |
| ⏳ | 引入 IR Visitor 模式消除重复遍历 | medium | 75 | 6-8 小时 | unify_ir_naming |

## 🧪 测试完善

| 状态 | 任务 | 难度 | 优先级 | 预计 |
|------|------|------|--------|------|
| ✅ | 修复原生后端测试导入 | easy | 85 | 30 分钟 |

---

**进度**: 16/27 (59%)
**已完成**: 16
**进行中**: 0
**待开发**: 11

> 注：第9轮评审后任务池从 25 个扩展到 27 个（新增 3 个高价值任务：while 循环 Phi、赋值 SSA 化、C 后端条件分支修复）。第10轮完成 2 个 SSA 相关任务（while 循环 Phi + SSA 验证器），进度从 52% 提升到 59%。
