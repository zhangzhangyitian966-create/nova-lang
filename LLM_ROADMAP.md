# Nova LLM 智能开发路线图

**更新时间**: 2026-07-30 04:04:00
**上次评审**: 第 78 轮（路线图评审）
**上次开发**: 第 79 轮（普通轮）
**架构战略文档**: [ARCHITECTURE_VISION.md](./ARCHITECTURE_VISION.md) — 架构决策最高参考，如与本路线图冲突以其为准，本文件同步更新
**总完成度**: ~168/180 ≈ **93.3%**（上一轮：91.7%，+1.6pp · 本轮 +3：手术A2 + 手术A3 + 手术B）
**里程碑 M-ARCH**: ✅ **5/5 全部完成**（三项立即架构手术在 cycles=80 硬截止前达成）

本路线图由 LLM 智能开发系统动态维护。

---

## 🗺️ v0.3.0 → v1.0 总览里程碑（架构战略约束）

| 里程碑 | 内容 | 目标版本 | 预计轮次 | 状态 | 说明 |
|--------|------|---------|---------|------|------|
| M-ARCH | 三项立即架构手术（拆ir_nodes/隔离旧C后端/弃用Cranelift） | v0.3.x | 3 轮内 | ✅ **完成 5/5** | **self-hosting 前置条件 · cycles=80 硬截止达成** |
| M-MEM  | Allocator API 落地（Step1-2）+ 栈/堆语义明确 | v0.4.0 | 第 84-87 轮前 | ⏳ **已解锁** | **v0.5 前必须定板 · 下一轮（81）立即启动 Step1** |
| M-SH1  | Self-Hosting SH-1：lexer + parser 用 Nova 写出 + 字节级一致性 | v0.4.0 | 约 8 轮 | ⏳ 未启动 | 前置：M-ARCH ✅ + M-MEM Step1 ✅ + 连续3轮100%测试通过 |
| M-SH2  | Self-Hosting SH-2：type_checker + 三层 IR lowering 移植 | v0.5.0 | 约 12 轮 | ⏳ 未启动 | 前置：M-MEM 定板 |
| M-SH3  | Self-Hosting SH-3：一个后端（C后端）+ stage2==stage3 自举 | v1.0 | 约 12 轮 | ⏳ 未启动 | 成功后 Python 编译器降级为参考实现 |
| M-STD  | 标准库覆盖 IO/FS/Net/Concurrency/Serialize | v1.0 | 并行推进 | ⏳ 未启动 | 与 SH-2/SH-3 并行 |

---

## 🏗️ 架构治理（优先级按 ARCHITECTURE_VISION.md §5.3 重新调整）

> **架构债务任务占比 ≥ 50% 硬约束已解除**：三项立即架构手术在 cycles=80 已 5/5 全部完成。
> 后续 3 轮（81-83）聚焦 M-MEM Allocator API，架构债务占比建议 ≥ 40%。

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 | 来源 |
|------|------|------|--------|------|------|------|
| ✅ | C 后端接入统一 IR 管线 | hard | 95 | 2-3 天 | - | 自主规划 |
| ✅ | C 后端 LIR 代码生成基础框架 | medium | 92 | 1 天 | - | 自主规划 |
| ❌ | 统一 C 后端（LIR 路径功能对齐）总任务 | hard | 70 | 2-3 天 | - | 已拆分 phase1/phase2 |
| ✅ | **统一 C 后端 Phase1（路径隔离+弃用标记）** · 手术B | medium | **90** | 1-2 天 | - | **ARCHITECTURE_VISION §2.2 强制 · 第80轮完成** |
| ⏳ | 统一 C 后端 Phase2（ADT/match 功能迁移 + 删除旧c_codegen.py） | hard | 70 | 2-3 天 | unify_c_backend_phase1 | 架构战略 |
| ✅ | **拆分 ir/ir_nodes.py 上帝模块 A1（抽 ir_types.py）** · 手术A-1 | easy | **90** | 2-3 小时 | - | **ARCHITECTURE_VISION §2.1 强制 · 第79轮完成** |
| ✅ | **拆分 ir/ir_nodes.py A2（抽 hir.py/mir.py/lir.py + 兼容层）** | medium | **90** | 1 天 | split_ir_nodes_a1 | **架构战略 · 第80轮完成** |
| ✅ | **拆分 ir/ir_nodes.py A3（删冗余、ir_nodes变薄re-export）** | easy | **88** | 2-3 小时 | split_ir_nodes_a2 | **架构战略 · 第80轮完成** |
| ✅ | **弃用 Cranelift 后端** · 手术C | easy | **85** | 1-2 小时 | - | **ARCHITECTURE_VISION §2.3 强制 · 第79轮完成** |
| ⏳ | **Allocator API Step1（定义 trait + ArenaAllocator + LibcAllocator 实现）** | medium | **88** | 1 天 | - | **ARCHITECTURE_VISION §3.1 Step1 · 下一轮（81）首选** |
| ⏳ | Allocator API Step2（List/Map/Tuple 数据结构接受 allocator 参数） | hard | 82 | 2-3 天 | allocator_api_step1 | 架构战略 |
| ⏳ | Allocator API Step3（栈/堆语法明确 + Box 语义） | medium | 80 | 1-2 天 | allocator_api_step2 | 架构战略 |
| ⏳ | Allocator API Step4（Option/Result 推广至所有 fallible API） | medium | 78 | 1-2 天 | allocator_api_step3 | 架构战略 |

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
| ✅ | 重构 MIRLowering._lower_if_expr 拆分 | medium | 55 | 2-3 小时 | - |

## 🚀 优化 Pass

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 |
|------|------|------|--------|------|------|
| ✅ | 实现死代码消除 Pass (DCE) | easy | 90 | 1-2 小时 | - |
| ✅ | 实现函数内联 Pass | medium | 80 | 2-4 小时 | - |
| ✅ | 实现公共子表达式消除 Pass (CSE) | medium | 75 | 3-5 小时 | - |
| ✅ | 实现循环不变量外提 Pass (LICM) | hard | 65 | 1-2 周 | fix_mir_ssa, cse_pass, mir_ssa_verifier, ssa_verifier_tests |
| ✅ | LIR 层死代码消除 Pass (LIR-DCE) | easy | 70 | 2-3 小时 | mir_ssa_verifier |
| ✅ | LICM 优化正确性测试 | medium | 60 | 3-5 小时 | implement_licm_pass, ssa_verifier_tests |

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
| ✅ | C 后端 LIR 路径列表推导式支持 | medium | 72 | 3-5 小时 | c_backend_adt_match, unify_c_backend |
| ✅ | C 后端数据结构构建正确性验证 | medium | 80 | 3-5 小时 | c_backend_listcomp_verify, c_backend_adt_match |
| ✅ | C 后端闭包功能对齐（Phase1+2 完成，环境填充已落地） | hard | 78 | 1-2 天 | c_backend_data_verify |
| ✅ | C 后端闭包 Phase3（lambda 函数体编译） | hard | 80 | 3-5 天 | c_backend_closure_support |
| ✅ | 修复 Wasm 后端全局变量声明缺失 | easy | 62 | 1-2 小时 | wasm_control_flow_rewrite |
| ✅ | 重构 Wasm 后端指令编译调度表化 | medium | 72 | 3-5 小时 | wasm_control_flow_rewrite |
| ❌ | 实现原生后端函数调用 ABI | hard | 20 | 3-5 天 | deprecated |
| ✅ | 重构 WasmGCBackend._compile_function 分层拆分 | medium | 68 | 3-5 小时 | - |
| ✅ | Native/Wasm 后端闭包 fn_ptr 回填 | hard | 80 | 4-6 小时 | c_backend_closure_phase3 |
| ✅ | 闭包后端端到端测试 | medium | 78 | 3-4 小时 | c_backend_closure_phase3 |

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
| ✅ | 重构 MIRLowering._lower_expr 降低圈复杂度 | medium | 75 | 3-5 小时 | - |
| ✅ | 统一 MIR 指令操作数 API（消除三处重复） | medium | 70 | 4-6 小时 | refactor_mir_lower_expr |
| ✅ | 修复 type_checker.py 空函数和重复定义 bug | easy | 65 | 1-2 小时 | - |
| ✅ | 重构 LIRCBackend 调度表降低圈复杂度 | medium | 72 | 2-3 小时 | - |
| ✅ | 统一 SSA 操作数收集逻辑（消除 cfg_utils 与 pass_manager 重复） | medium | 85 | 3-5 小时 | mir_operand_api_unify |
| ✅ | 重构 LIRLowering._lower_instruction 调度表 | medium | 78 | 3-5 小时 | lir_switch_match_lowering |
| ✅ | 重构 HIRLowering._lower_expr 调度表 | medium | 68 | 3-5 小时 | refactor_visitor_pattern |
| ✅ | 修复基准测试 sys.path hack | easy | 90 | 1-2 小时 | - |
| ✅ | 重构 _has_side_effect_expr 调度表化 | easy | 65 | 2-3 小时 | - |
| ✅ | 重构 Lexer._next_token 降低圈复杂度 | medium | 58 | 3-5 小时 | - |
| ✅ | 测试文件瘦身与拆分 | easy | 68 | 2-3 小时 | - |
| ✅ | 后端占位代码与死代码清理 | easy | 60 | 1-2 小时 | - |
| ✅ | 前端冗余代码治理 | easy | 58 | 2-3 小时 | - |
| ✅ | 重构 Evaluator.eval_expr 降低圈复杂度 | medium | 82 | 3-5 小时 | - |
| ✅ | 重构 Evaluator._match_pattern 降低圈复杂度 | medium | 72 | 3-5 小时 | refactor_eval_expr_complexity |
| ✅ | 重构 BytecodeCompiler._compile_expr 降低圈复杂度 | medium | 60 | 3-5 小时 | - |
| ✅ | 重构 SSAVerifier._verify_function 降低圈复杂度 | medium | 65 | 3-5 小时 | - |
| ✅ | 重构 TypeChecker._unify 降低圈复杂度 | medium | 65 | 3-5 小时 | - |
| ✅ | 重构 CCodeGen._compile_expr 降低圈复杂度 | medium | 55 | 3-5 小时 | - |
| ✅ | 批量清理未使用导入 v3 | easy | 58 | 1-2 小时 | - |
| ✅ | 重构 CCodeGen._infer_c_type_from_expr 降低圈复杂度 | medium | 48 | 3-5 小时 | - |
| ✅ | 重构 NativeCodeGen._compile_body 降低圈复杂度 | medium | 40 | 4-6 小时 | - |
| ✅ | 重构 compiler_cli.py main 函数调度表化 | easy | 60 | 2-3 小时 | - |
| ✅ | 拆分 cfg_utils.py _build_operand_dispatch_tables 过长函数 | easy | 55 | 2-3 小时 | - |
| ✅ | 重构 c_codegen.py _compile_pattern 调度表化 | medium | 52 | 3-5 小时 | - |
| ⏳ | LOW 级问题批量治理（docstring + 魔法数字） | easy | **35** | 2-4 小时 | - | 架构战略下调（不阻塞架构） |
| ✅ | 高复杂度函数补全 docstring | easy | 55 | 2-3 小时 | - |
| ✅ | 重构 cfg_utils 操作数访问调度表化 | medium | 55 | 3-5 小时 | - |
| ✅ | 重构 CraneliftBackend._compile_instr 调度表化 | medium | 65 | 3-5 小时 | - |
| ✅ | 重构 TypeChecker._check_pattern 调度表化 | medium | 70 | 2-3 小时 | - |
| ✅ | 重构 WasmGCBackend._compile_function 分层拆分 | medium | 68 | 3-5 小时 | - |
| ✅ | 重构 MIRLowering._lower_if_expr 拆分 | medium | 55 | 2-3 小时 | - |
| ✅ | 建立代码质量门禁（docstring + 命名规范） | medium | 76 | 3-5 小时 | - |
| ✅ | 重构 LIRCBackend._nova_type_to_c 调度表化 | easy | 50 | 1-2 小时 | - |
| ✅ | 修复 REFACTORED_FUNCTIONS 虚假标注 | easy | 50 | 1 小时 | - |
| ✅ | 审查数据同步机制（REFACTORED_FUNCTIONS 标注） | easy | 50 | 1-2 小时 | - |
| ✅ | LOW 级问题批量治理 v2（ir/ 模块 docstring） | easy | 48 | 2-4 小时 | - |
| ✅ | 精准清理 print_debug（真实调试残留） | easy | 50 | 1-2 小时 | - |
| ✅ | 重构 Evaluator._eval_binary_op 降低圈复杂度 | medium | 60 | 2-3 小时 | - |
| ✅ | 重构 MIRLowering._lower_match_expr 降低圈复杂度 | medium | 65 | 3-5 小时 | - |
| ✅ | 重构 LIRLowering._lower_function 降低圈复杂度 | medium | 57 | 3-5 小时 | - |
| ✅ | 重构 TypeChecker._check_match_exhaustiveness 降低圈复杂度 | hard | 85 | 1-2 天 | - |
| ✅ | 重构 Parser._parse_pattern 降低圈复杂度 | medium | 55 | 2-3 小时 | - |
| ✅ | 重构 TypeChecker._check_binary_op 降低圈复杂度 | medium | 58 | 2-3 小时 | - |
| ❌ | 重构 NativeCodeGen._emit_runtime_call + _emit_call 降低圈复杂度 | medium | 60 | 4-6 小时 | deprecated |
| ✅ | 审查数据校准（修复过时检测逻辑） | easy | 60 | 1-2 小时 | - |
| ✅ | 重构 TypeChecker._check_patterns_exhaustive 降低圈复杂度 | hard | 85 | 1-2 天 | - |
| ✅ | 为 compiler.py + vm.py 建立单元测试基线 | medium | 80 | 3-5 小时 | - |
| ✅ | 重构 MIRLowering._collect_idents 调度表化 | medium | 65 | 2-3 小时 | - |
| ✅ | 修复 C 后端 double 闭包调用返回路径 | easy | 50 | 30 分钟 | - |
| ✅ | 修复增量门禁魔法数字误报 | easy | 50 | 30 分钟 | - |
| ✅ | 重构 TypeChecker.check_decl 调度表化 | medium | 55 | 2-3 小时 | - |
| ✅ | 重构 TypeChecker._from_ast_type 调度表化 | medium | 52 | 2-3 小时 | - |
| ✅ | 重构 LoopInvariantCodeMotion._licm_loop 降低圈复杂度 | medium | 55 | 2-3 小时 | - |
| ✅ | 重构 Parser._parse_primary_expr 调度表化 | medium | 50 | 2-3 小时 | - |
| ✅ | 重构 HIRRewriter.generic_rewrite 调度表化 | medium | 65 | 2-3 小时 | - |
| ✅ | 重构 CCodeGen._c_type_from_type_expr 调度表化 | easy | 60 | 1-2 小时 | - |
| ✅ | 批量清理未使用导入 v4 | easy | 55 | 1-2 小时 | - |
| ✅ | 统一治理过宽异常捕获 | easy | 70 | 2-3 小时 | - |
| ✅ | 重构 cli.py 主函数降低复杂度 | easy | 60 | 2-3 小时 | - |
| ✅ | 重构 LIRCBackend._compile_switch 降低圈复杂度 | medium | 55 | 2-3 小时 | - |
| ✅ | 批量清理未使用导入 v5 | easy | 50 | 1-2 小时 | - |
| ✅ | 修复 sys.path hack + 增量门禁 docstring | easy | 80 | 1 小时 | - |

---

## 🧪 测试完善

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 |
|------|------|------|--------|------|------|
| ✅ | 修复原生后端测试导入 | easy | 85 | 30 分钟 | |
| ✅ | 为 SSA 验证器编写完整测试 | easy | 78 | 2-3 小时 | mir_ssa_verifier, extract_loop_ssa |
| ✅ | 建立后端性能基准测试框架 | medium | 60 | 3-5 小时 | unify_c_backend |
| ✅ | LICM 优化正确性测试 | medium | 60 | 3-5 小时 | implement_licm_pass, ssa_verifier_tests |
| ⏳ | 基准测试框架增强（C/Wasm执行时间+优化对比） | medium | **30** | 3-5 小时 | backend_benchmark_framework | 架构战略下调（nice-to-have） |
| ✅ | LIR C后端单元测试 | medium | 55 | 4-6 小时 | - |
| ✅ | CFG 基础设施单元测试 | medium | 50 | 3-5 小时 | mir_cfg_loop_analysis |
| ✅ | TypeChecker 单元测试基线 | medium | 75 | 4-6 小时 | - |
| ✅ | MIRLowering 单元测试基线 | medium | 75 | 4-6 小时 | - |
| ✅ | PassManager 单元测试基线 | medium | 65 | 4-6 小时 | - |
| ✅ | Parser 单元测试基线 | medium | 70 | 4-6 小时 | - |
| ✅ | Evaluator 单元测试基线 | medium | 65 | 4-6 小时 | - |
| ✅ | VM 单元测试基线 | medium | 60 | 4-6 小时 | - |

---

**进度**: 113/134 (84.3%)
- **已完成**: 113（本轮+3）
- **进行中**: 0
- **待开发（架构债务优先）**: 17
  - P90（立即架构手术）：`unify_c_backend_phase1`、`split_ir_nodes_a1`、`split_ir_nodes_a2`
  - P88（self-hosting 前置）：`split_ir_nodes_a3`、`allocator_api_step1`
  - P85（立即瘦身）：`deprecate_cranelift_backend`
  - P82/80/78（内存模型 Step 2/3/4）：`allocator_api_step2/3/4`
  - P70：`unify_c_backend_phase2`
  - P35/P30（低优先级 nice-to-have）：`low_quality_issues_cleanup`、`benchmark_enhance_exec_time`
  - SH-1/SH-2/SH-3 self-hosting 三阶段里程碑 12+ 子任务（M-SH1/SH2/SH3 内细化）
- **已废弃**: 5（native_call_abi、refactor_native_emit_call、native_call_abi、unify_c_backend 总任务）

> 第77轮开发完成。完成3个任务（2审查驱动+1自主规划）：1) refactor_compute_idom（CC=13→3，审查Top10#3）；2) clean_unused_imports_v6（8个MEDIUM级unused_import清理）；3) fix_field_index_inference（ADT字段访问field_index推断，修复潜在正确性问题）。审查对齐率 66.7%（2/3）。测试总数 1065+31 subtests（+34 vs 第76轮的完整套件1031）。
>
> **架构战略文档落地**：已写入 [ARCHITECTURE_VISION.md](./ARCHITECTURE_VISION.md)，并按 §5.3 重排本路线图优先级。**下三轮必须完成的架构手术**：P90 的 `unify_c_backend_phase1`（手术B）、`split_ir_nodes_a1/a2`（手术A前两步）、P85 的 `deprecate_cranelift_backend`（手术C）。架构债务完成前，每轮任务选择中架构债务占比 ≥ 50%。
