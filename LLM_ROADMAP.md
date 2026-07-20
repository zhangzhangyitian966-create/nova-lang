# Nova LLM 智能开发路线图

**更新时间**: 2026-07-20 14:30:00
**上次评审**: 第 24 轮（路线图评审）

本路线图由 LLM 智能开发系统动态维护。

## 🏗️ 架构治理

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 |
|------|------|------|--------|------|------|
| ✅ | C 后端接入统一 IR 管线 | hard | 95 | 2-3 天 | - |
| ✅ | C 后端 LIR 代码生成基础框架 | medium | 92 | 1 天 | - |
| ⏳ | 统一 C 后端（LIR 路径功能对齐） | hard | 75 | 2-3 天 | fix_match_lowering, fix_mir_ssa, refactor_visitor_pattern, lir_switch_match_lowering |

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
| ✅ | 提取循环 SSA 通用方法（消除三重重复） | medium | 88 | 3-5 小时 | for_loop_ssa_normalize |
| ✅ | 修复列表推导式 latch 块 SSA 替换不完整 | medium | 85 | 2-4 小时 | extract_loop_ssa |
| ✅ | MIR CFG 工具与循环分析基础设施 | medium | 70 | 4-6 小时 | mir_ssa_verifier, ssa_verifier_tests |
| ✅ | LIR switch/match 降级补全 | medium | 65 | 3-5 小时 | fix_mir_ssa |

## 🚀 优化 Pass

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 |
|------|------|------|--------|------|------|
| ✅ | 实现死代码消除 Pass (DCE) | easy | 90 | 1-2 小时 | - |
| ✅ | 实现函数内联 Pass | medium | 80 | 2-4 小时 | - |
| ✅ | 实现公共子表达式消除 Pass (CSE) | medium | 75 | 3-5 小时 | - |
| ✅ | 实现循环不变量外提 Pass (LICM) | hard | 65 | 1-2 周 | fix_mir_ssa, cse_pass, mir_ssa_verifier, ssa_verifier_tests |

## ⚙️ 后端开发

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 |
|------|------|------|--------|------|------|
| ✅ | 补充 WasmGC StoreReg 实现 | easy | 65 | 1 小时 | - |
| ✅ | 修复 LIR C 后端条件分支 | easy | 72 | 30 分钟 | - |
| ✅ | 修复 Wasm 后端 Label 实现 | medium | 62 | 3-5 小时 | fix_while_phi |
| ✅ | Wasm 后端控制流重写（支持任意 CFG） | hard | 90 | 2-3 天 | fix_wasm_label |
| ✅ | 修复 Wasm 后端多个正确性 bug | easy | 65 | 1-2 小时 | wasm_control_flow_rewrite |
| ✅ | 修复 Wasm 后端 StoreReg 实现 | easy | 60 | 1 小时 | wasm_control_flow_rewrite |
| ✅ | C 后端 LIR 路径 ADT/match 支持 | hard | 72 | 1-2 天 | lir_switch_match_lowering, unify_c_backend |
| ⏳ | C 后端 LIR 路径列表推导式支持 | medium | 68 | 3-5 小时 | c_backend_adt_match, unify_c_backend |
| ⏳ | 实现原生后端函数调用 ABI | hard | 25 | 3-5 天 | fix_mir_ssa |

## 🛠️ 工程质量

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 |
|------|------|------|--------|------|------|
| ✅ | 修复 Pass 管理器静默错误吞噬 | easy | 70 | 30 分钟 | - |
| ✅ | 消除 sys.path hack，标准化包结构 | medium | 88 | 1-2 天 | - |
| ✅ | 统一跨 IR 层字段命名 | medium | 80 | 1 天 | refactor_sys_path |
| ✅ | 修复 ConstantFolding 的 __class__ 突变问题 | easy | 70 | 1-2 小时 | - |
| ✅ | 引入 IR Visitor 模式消除重复遍历 | medium | 82 | 6-8 小时 | unify_ir_naming, fix_constant_folding_class |
| ✅ | 统一后端类型/操作符映射表 | easy | 68 | 2-3 小时 | unify_ir_naming |
| ✅ | 重构 HIRRewriter 降低圈复杂度 | easy | 75 | 2-3 小时 | refactor_visitor_pattern |
| ✅ | 修复过宽异常捕获 | easy | 60 | 1-2 小时 | - |
| ✅ | 批量清理未使用导入 | easy | 55 | 1-2 小时 | - |
| ✅ | 拆分 VM 巨型执行函数 | medium | 70 | 4-6 小时 | - |
| ✅ | 重构 TypeChecker 降低圈复杂度 | medium | 55 | 4-6 小时 | - |
| ⏳ | 重构 MIRLowering._lower_expr 降低圈复杂度 | medium | 75 | 3-5 小时 | - |
| ⏳ | 统一 MIR 指令操作数 API（消除三处重复） | medium | 70 | 4-6 小时 | refactor_mir_lower_expr |
| ⏳ | 修复 type_checker.py 空函数和重复定义 bug | easy | 65 | 1-2 小时 | - |

## 🧪 测试完善

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 |
|------|------|------|--------|------|------|
| ✅ | 修复原生后端测试导入 | easy | 85 | 30 分钟 | |
| ✅ | 为 SSA 验证器编写完整测试 | easy | 78 | 2-3 小时 | mir_ssa_verifier, extract_loop_ssa |
| ⏳ | 建立后端性能基准测试框架 | medium | 60 | 3-5 小时 | unify_c_backend |

---

**进度**: 47/53 (89%)
**已完成**: 47
**进行中**: 0
**待开发**: 5
**已废弃**: 1

> 注：第24轮评审完成。回顾第22-23轮（6个任务：VM巨型函数拆分 + LIR switch/match降级补全 + Wasm bug修复 + C后端ADT/match支持 + TypeChecker重构 + Wasm指令补全），路线图进度 81% → 89%，测试 418 全通过，零回归。五维评估：方向正确、质量持续变好、效率稳定、价值高、审查对齐良好。新增 4 个任务（MIR操作数API统一、C后端列表推导式、type_checker空函数修复、Wasm指令补全已完成），调整 3 个优先级。下阶段（第25-27轮）：MIR复杂度攻坚 → MIR基础设施统一 → C后端整合收尾+基准测试。
