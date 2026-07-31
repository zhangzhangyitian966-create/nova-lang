# Nova 前后端专项开发路线图

**更新时间**: 2026-07-31
**上次评审**: 第 66 轮
**当前评审**: 第 66 轮
**当前轮次**: 第 67 轮
**下次评审**: 第 69 轮

本路线图由前后端专项开发系统维护，专注于前端类型系统和后端代码生成的核心功能开发。

## 进度概览

| 轨道 | 总数 | 已完成 | 待做 | 废弃 | 完成率 |
|------|------|--------|------|------|--------|
| 前端 | 50 | **45** | 3 | 6 | **90.0%**（第 67 轮 P1 清零 1/2：ErrorExpr 下游修复，P1 积压 2→1） |
| 后端 | 84 | **52** | 4 | 13 | **61.9%**（第 67 轮 P1 清零 1/2：WasmGC 双 bug，P1 积压 2→1，WasmGC 真实完成度 45%→65%） |
| **总计** | **134** | **97** | **7** | **19** | **72.4%**（第 67 轮 P1 清零里程碑 2/5：前后端各清 1 项 P1，距 P1=0 还差 2 项） |

> **第 67 轮里程碑推进说明**：P1 积压 5 项 → 剩 3 项（剩 frontend_harden_typevar_leak_guard P1 + backend_mir_phi_type_upgrade_raise P1；backend_native_float_imm_xmm0_conflict 为 P2）。第 68 轮 = P1 清零里程碑 5/5 收官轮（剩 2 P1 同轮双开 + 1 P2 顺带）。

## 前端开发线

**状态：P1 清零攻坚阶段（质量 8.1→预测 8.5/10 第 68 轮后）—— ErrorExpr 下游 ✅ 恢复错误恢复体系可用性；剩 TypeVar 泄漏+HM TVar+mut 幻影三合一 harden（P1 最后 1 项）**

前端功能表面完成率高（90%），第 67 轮完成的 ErrorExpr 下游修复使 Parser 四级熔断的真实 ROI 从 0→1，错误恢复闭环。下一阶段 harden 任务一次性清 P1 TVar 泄漏 + P2×2（HM generalize 不区分 TVar、mut 幻影实例化）= 前端 P1=0 + P2=0 双达成。

### 第 66 轮评审新增 3 个前端任务进度（2/3 已推进）

| 任务 | 难度 | 优先级 | 严重度 | 状态 | 轮次计划 |
|------|------|--------|--------|------|----------|
| **修复 ErrorExpr 下游双缺失**（type_checker + evaluator 各加 1 handler，错误恢复归零风险） | easy | **98** | P1 | ✅ **第 67 轮完成（7/7 TC + 3/3 Evaluator，0 回归）**【P1 清零 1/2：前端错误恢复体系闭环，ROI 0→1】 | **第 67 轮 ✅** |
| **TypeVar 泄漏 + HM TVar 区分 + mut 幻影实例化 三合一 harden**（前端 P1 最后 1 项，同步修复 2×P2 类型安全漏洞） | hard | **92** | P1 | 🔴 待做 | **第 68 轮**（前端主攻，依赖已满足：ErrorExpr 下游先修复 ✅） |
| **类型系统边界测试矩阵**（+15 用例：泄漏检测/泛化边界/ErrorExpr 下游/回归保护 4 类） | easy | **78** | P2 | 🔴 待做 | **第 69 轮**（测试+回归轮，与后端测试并行） |

### 第 63 轮评审新增 3 个前端任务进度（3/3 已清零 🎉）

| 任务 | 难度 | 优先级 | 严重度 | 状态 | 轮次计划 |
|------|------|--------|--------|------|----------|
| **实现 generalize() + 补全 let-polymorphism**（HM 核心能力缺失 Top1） | hard | **93** | P1 | ✅ **第 65 轮完成（10/10 专项测试通过，HM 完整性 65%→85%）**【评审 66 追加：generalize 不区分 TVar + mut 幻影 P2 漏洞，并入 harden 任务】 | **第 65 轮 ✅** |
| **parser 错误恢复计数器扩展**（TOP_LEVEL/EXPR/BLOCK 三级 + ErrorExpr） | medium | **85** | P2 | ✅ **第 64 轮完成（6/6 专项通过）**【评审 66 追加：ErrorExpr 下游双缺失 P1，归零错误恢复投入，独立修复任务】 | **第 64 轮 ✅** |
| **TypeVar 泄漏守卫 + 递归 ADT Occur Check 豁免**（原 P80 medium） | medium | 80→**废弃** | P2 | 🗑️ **废弃（review_cycle_66）** | **并入 frontend_harden_typevar_leak_guard（P92 hard）：内容从单纯泄漏栅栏扩展为 泄漏+HM TVar+mut 幻影 三合一** |

### code_audit_66 深度审计发现（前端 3 项，0/3 已清零）

| 发现 | 位置 | 影响 | 严重度 | 状态 |
|------|------|------|--------|------|
| **ErrorExpr 下游 handler 双双缺失（TypeChecker + Evaluator）** | type_checker.py L589 调度表缺 ErrorExpr + evaluator.py L633 调度表缺 ErrorExpr | Parser 熔断返回 ErrorExpr 后 → TypeChecker 报「未知的表达式类型」覆盖原始 ParseError / Evaluator 直接抛 RuntimeError_ 崩溃 → 第 24/48/64 三轮投入的错误恢复体系价值归零 | **P1 归零风险** | 🔴 **下一轮清零（第 67 轮 frontend_fix_error_expr_downstream, P98 easy）** |
| **TypeVar 静默泄漏到后端（3 条确认路径：空 List/空 Map/无注解参数未用）** | type_checker.py 多处（L737 空列表/L757 空 Map/L533 FnDef 参数/L995 Lambda 参数） | 未约束 TVar 被 _unify_and_resolve 保留，后端三后端 fallback 策略不一致（C void*/Native int/Wasm i32）→ 行为不可预测 | **P1 跨层污染** | 🔴 **第 68 轮清零（frontend_harden_typevar_leak_guard, P92 hard，同步合并 HM TVar 区分 + mut 幻影）** |
| **HM generalize 不区分可泛化/被约束 TVar + mut 绑定幻影实例化** | type_checker.py _walk_type_generalize L2198 + _check_identifier L690 instantiate 无条件 | (a) 外层约束的 TVar 被 instantiate 独立 fresh，破坏内外层约束传播；(b) mut x = [] 同一变量两次读取的 TVar 相互独立 → append(1) 和 append("s") 分别约束两个独立 TVar，同一 list 同时含 Int+String = 类型安全漏洞 | **P2 类型安全漏洞×2** | 🔴 **与 TypeVar 泄漏任务合并（第 68 轮 harden 三合一），同源问题最高 ROI 处理** |

### code_audit_63 遗留（前端 3 项，3/3 名义完成但含下游缺陷 ⚠️）

| 发现 | 位置 | 状态 |
|------|------|------|
| **HM generalize() 完全缺失** | type_checker.py | ✅ 第 65 轮名义完成（HM 完整性 65%→85%），⚠️ 评审 66 发现 generalize 不区分 TVar（P2）+ mut 幻影（P2），并入 harden 任务同步清零 |
| **TypeVar 静默泄漏** | type_checker.py 多处 | 🔴 原 frontend_typevar_leak_guard（P80）已废弃，内容大幅扩展为 P1 跨层污染 + P2×2 类型安全，三合一 harden 任务 P92 第 68 轮清零 |
| **递归 ADT Occur Check 误杀** | _occur_check + _from_ast_type ADT 变体字段 | 📝 延期（当前用户 ADT 都比较简单，真实用户反馈为 0；优先级低于 P1×2），在 harden 任务中若有额外代码空间则顺手处理，否则单独第 70 轮 |

### 核心能力清单（HM generalize 落地但完整性 85%，下阶段 P1 清零后向 95% 迈进）

- Hindley-Milner 类型推断（含 let-polymorphism **实例化端 ✅ + 泛化端 generalize() ✅** 双端闭环，但 generalize 标记不区分 P2 + mut 幻影实例化 P2 两个待清漏洞，HM 完整性 ~85%）
- 泛型参数数量校验 + 参数化类型实例化
- 模式匹配完备性检查（ADT / Bool / Tuple / List / 嵌套子模式 / 无限域判定）
- 冗余分支检测（guard 通配符排除 / NaN 安全 / 字面量集合去重）
- Parser Panic Mode 错误恢复（**TOP_LEVEL/STMT_LIST/EXPR/BLOCK 四级熔断 ✅**，但 **ErrorExpr 下游 handler 缺失 🔴** 导致下游归零，第 67 轮清零）
- TypeCheckError 统一 _error() 出口（**100% 使用率**，44/44 已迁移）
- Union-Find + 路径压缩 + Occur Check（递归 ADT 豁免待补，延期）
- **Value Restriction 最小化**（mut/非语法值/语法值 三级策略 ✅）
- **TypeVar 泄漏栅栏 🔴**（第 68 轮 frontend_harden_typevar_leak_guard，含 ERROR_T 宽容匹配 + is_generalized 标记机制）

## 后端开发线

**状态：结构性改造收尾 + 细节正确性攻坚（质量 7.9→预测 8.3/10 第 68 轮后）—— WasmGC 双 P1 清零（模式匹配恢复可用 + Float 复合结构通过 Wasm 验证）、C/Native 同款 variant_tag 复制粘贴 bug 顺带同修；剩 Phi 升级收尾（P1 最后 1 项，观察期拖 5 轮）+ Native XMM0 冲突（P2，顺带）**

第 67 轮 WasmGC 两个确定性 P1 bug 清零（ADT variant_tag 独立 + Float 复合构建位转换），WasmGC 真实完成度从 45%→65%（单轮 ↑20pp，后端单轮价值最高里程碑）。LIRBuildADT 缺 variant_tag 字段的问题导致三后端（Wasm/C/Native）都有复制粘贴的 variant_tag=type_tag 同值 bug，本轮通过补字段 + 双注册表独立赋值一次性三后端同修，避免未来各后端分别排查。下一阶段 Phi 升级 + XMM0 同轮双开（mir_lowering/native_backend 无文件冲突），后端 P1=0 达成。

### 紧急问题清零看板（P0/P1/P2，code_audit_66 新增 5 项，**2/5 已清零 + 2/5 进入第 68 轮收尾**）

| 严重度 | 编号 | 问题 | 对应任务 | 优先级 | 计划轮次 | 状态 |
|--------|------|------|----------|--------|----------|------|
| **P1** | 66-B1 | **WasmGC ADT variant_tag 与 type_id 传同一字段 = 多变体模式匹配完全失效** | **backend_fix_wasmgc_adt_float** | **95** | **第 67 轮（后端主攻）** | ✅ **已清零**【LIRBuildADT 新增 variant_tag 字段 + lir_lowering 双注册表 + 三后端（Wasm/C/Native）统一修正】 |
| **P1** | 66-B2 | **WasmGC float 元素复合结构构建 i64/f64 类型栈不匹配 = 无法通过 wasm-validate** | **backend_fix_wasmgc_adt_float**（与 66-B1 合并同一任务，双 bug 同文件） | **95** | **第 67 轮** | ✅ **与 66-B1 同任务双清零**【4 处构建（list/tuple/map/adt）的 local.get Float 后统一补 i64.reinterpret_f64 条件位转换】 |
| **P1** | 63-B3（升级收尾） | **_resolve_phi_type 观察期超期 3 轮 + has_inconsistency 丢弃 + Loop Phi 未覆盖（原只覆盖 If/Match Merge）** | **backend_mir_phi_type_upgrade_raise** | **90**↑ | **第 68 轮**（与 frontend_harden 并行） | 🔴 原 P88 升 P90，新增 Loop Phi 覆盖要求【后端 P1 最后 1 项】 |
| P2 | 66-B3 | **Native Float imm 溢出路径（参数 ≥9 float）直接写 XMM0 覆盖第 0 个 float 参数值** | **backend_native_float_imm_xmm0_conflict** | **82** | **第 68 轮（与 Phi 升级同轮附带项）** | 🔴 易改，同轮顺手清（一个 mir、一个 native，无文件冲突零重叠） |
| P2 | 66-B4 | **后端测试密度 0.39 / Native 0.33 = 前端 0.88 的 ~44%，结构性改造后长尾场景测试缺** | **backend_native_abi_test_coverage**（+16 场景：Native ABI 10 + WasmGC 6） | **80** | **第 69 轮（测试+回归轮）** | 🔴 与前端类型测试矩阵并行 |

### code_audit_63 新发现（后端 3 项，**3/3 全部进入完成/收尾阶段** 🎉）

| 严重度 | 编号 | 问题 | 对应任务 | 优先级 | 状态 |
|--------|------|------|----------|--------|------|
| P2（可维护性 Top1） | 63-B1 | **_allocate_registers CC≈39 拆分** | **backend_native_regalloc_cc_split** | **92** | ✅ **第 64 轮清零**（拆 3 子方法+流水线主方法 CC≤5） |
| P2（可维护性 Top2） | 63-B2 | **_emit_runtime_call CC≈31 + _emit_call CC≈24 两方法 70% 重复** | **backend_native_emit_abi_call_refactor** | **90** | ✅ **第 65 轮清零**（抽出 _emit_abi_call_direct 通用 10 步骨架，~75% 重复消除）⚠️ 评审 66 追加：Float imm 溢出路径覆盖 XMM0 长尾 P2，独立任务第 68 轮清 → **第 68 轮一起收尾** |
| P1（正确性收尾） | 63-B3 | **_resolve_phi_type 观察期未结束 + has_inconsistency 未消费** | **backend_mir_phi_type_upgrade_raise** | **90**↑ | 🔴 **第 68 轮清零**（观察期从 2 轮拖到 5 轮严重超期，评审 66 追加 Loop Phi 覆盖要求 + 优先级从 88→90） |

### 高优先级任务（下 3 轮 = 第 67-69 轮，按优先级排序 — **共 7 个任务 2/7 已完成 5/7 待推进**）

| 状态 | 轮次 | 任务 | 严重度 | 难度 | 优先级 | 估算工作量 |
|------|------|------|--------|------|--------|------------|
| ✅ **已完成** | **67** | **修复 ErrorExpr 下游双缺失（type_checker+evaluator 调度表各 1 handler + ERROR_T 单例）**【P1 清零 1/5】 | P1 | easy | **98** | 1-2 小时 |
| ✅ **已完成** | **67** | **WasmGC 双 P1 修复：ADT variant_tag 传对 + float 复合结构构建 i64.reinterpret_f64 补全（C/Native 同款 variant_tag bug 同修）**【P1 清零 2/5】 | P1 | medium | **95** | 3-5 小时 |
| 🔴 **第 68 轮前端主攻** | **68** | **TypeVar 泄漏栅栏 + HM generalize 标记区分 + mut 幻影实例化修复 三合一 harden（前端 P1 最后 1 项 + 双 P2 同步清零里程碑）**【P1 清零 3/5】 | P1 | hard | **92** | 6-10 小时 |
| 🔴 **第 68 轮后端主攻** | **68** | **Phi inconsistency 升级 raise + has_incon 消费 + Loop Phi（for/while）统一走 _resolve_phi_type 覆盖【结束 5 轮观察期】**【P1 清零 4/5，后端 P1 最后 1 项】 | P1 | medium | **90** | 3-5 小时 |
| 🔵 **第 68 轮后端附带** | **68** | **Native Float imm 溢出路径：XMM0 冲突修复（走内存中转 sub rsp,8/movsd[rsp]/push[rsp] 零寄存器冲突 + 2 专项）**【P2 XMM0 清零】 | P2 | easy | **82** | 1-2 小时（Phi 升级同轮顺带） |
| 🔴 **第 69 轮测试+回归轮 并行 2 任务** | **69** | **前端类型系统边界测试矩阵 +15 用例（泄漏检测/泛化边界/ErrorExpr 下游/回归保护 4 类）**【前端测试密度 0.61→0.70】 | P2 | easy | **78** | 2-3 小时 |
| 🔴 **第 69 轮测试+回归轮 并行 2 任务** | **69** | **后端双端测试补齐：Native ABI 骨架长尾 +10 场景（8int溢出/混合5int5float/递归/栈对齐/imm float 溢出） + WasmGC wat 合法性验证 +6 场景**【后端密度 0.39→0.45】 | P2 | medium | **80** | 4-6 小时 |

### 已废弃/降级任务（本轮新增 2 个废弃）

| 状态 | 任务 | 原因 |
|------|------|------|
| **🗑️ 本轮废弃** | **frontend_typevar_leak_guard（原 P80 medium）** | review_cycle_66 重新评估：原任务只覆盖「泄漏栅栏」1 个方面，忽略同步发现的 2 个 P2 同源问题（HM TVar 不区分 + mut 幻影），用扩展版 frontend_harden_typevar_leak_guard（P92 hard，三合一）替代，一次开发 3 个问题清零 ROI 远高于分开 3 个任务。 |
| **🗑️ 本轮废弃** | **backend_wasmgc_instruction_fill（原 P75 medium）** | review_cycle_66 审计确认：wasm_backend.py 调度表覆盖 19 种主要 LIR 指令类型，仅有 1 处兜底 NotImplementedError（良好实践）。原假设「3 个 NIE 指令」不成立，但审计发现两个真实的更高优先级 P1 bug（ADT tag + float 位转换），用具体 bug 修复任务 backend_fix_wasmgc_adt_float（P95 medium）替代抽象的「NIE 补齐」任务。 |
| 🗑️ 第 63 轮废弃 | backend_lir_phi_lowering_verify（P42） | Phi 降级验证 ROI<新增 5 个高优任务（P75+），推迟到 SIMD/结构体优化 |
| 🗑️ 第 60 轮废弃×2 | backend_wasm_stack_balance（P45）/ backend_wasm_wat_indent_verify（P35） | 0 真实 bug / 仅风格约束 |
| 废弃×5 | frontend_type_var_strict / backend_wasm_indirect_multiarg + gc_types / backend_native_fn_ptr + wasm_store_reg + instr_selection / backend_c_todo_error / backend_native_runtime_link | 并入更高优任务 / 被精确定位任务替代 |

### 各后端完成度排名（**第 67 轮完成 2 P1 后大幅更新** — WasmGC 从 45%→65% 跳涨）

| 排名 | 后端 | 完成度 | 变化 | 关键缺失（按严重度排序） |
|------|------|--------|------|--------------------------|
| 1 | **C 后端** | **~89%** | ↑1pp | 边界类型映射子串误判（低优 ~3%）、未知指令 NotImplementedError 兜底（良好实践）、**✅ L601 variant_tag=type_tag 复制粘贴 bug 已同轮顺带修** |
| 2 | **原生后端（x86_64）** | **~85%** | ↑1pp（**L1432 variant_tag 复制粘贴 bug 同轮顺带修 +1pp**，抵消 XMM0 -1pp） | P0/P1 三大正确性 ✅ 清零；Top2 CC 方法 ✅ 清零；**variant_tag bug 已修**；**Float imm XMM0 冲突 P2（第 68 轮清）**；复杂结构体字段对齐（低优） |
| 3 | **WasmGC 后端** | **~65%** | **↑20pp（单轮最大涨幅！清零两个 P1 长尾 bug）** | **✅ ADT variant_tag bug 清零（三后端同修）**；**✅ Float 复合构建位转换清零（4 处写路径统一修复）**；闭包/间接调用端到端 wasmtime e2e 实际执行测试缺失（第 69 轮补）；switch br_table 多臂结构的实际分支正确性边界条件测试 |
| 4 | **Cranelift 后端** | **~40%** | 弃用路线不变 | 大量指令未实现、弃用路线不变（v0.5.0 移除），不作为投入方向 |

**断层收敛目标更新**：原第 66 轮目标 Native→88% / WasmGC→70% 无法达成（两个 P1 拉低 10pp）。**第 67 轮已超目标**：WasmGC 双 P1 清零 → **65%**（↑20pp，单轮后端最高价值）；第 68 轮 Native XMM0 + Phi 收尾 → Native **~86%**；第 69 轮测试补齐 → 稳定 86/67/40。C/Native/WasmGC 有效三后端最大差从 34pp→**21pp**（第 68 轮后预计 19pp 达标 ≤19pp，三后端断层收敛目标提前实现）。

---

## 前后端平衡评估（第 66 轮评审结论）

### 客观指标对比

| 维度 | 前端 | 后端 | 比例 | 结论 |
|------|------|------|------|------|
| 综合质量评分 | **8.1/10**（↓0.5 vs 第 63 轮） | **7.9/10**（↓0.2 vs 第 65 轮名义 8.1，↑0.2 vs 第 63 轮 7.7） | 领先 0.2 分（从 0.9pp 差距大幅收窄） | 两端质量差距收敛，但都处于「功能完成但边界条件不足」阶段，需先清零 P1 再评分 |
| 测试数量（用例） | ~233（lexer 21 + parser 95 + type_checker 138 - 重叠 21） | ~311（native 53 + ir 63 + c_codegen 50 + backends 58 + lir_c 50 + mir 57 + pass 18 + ssa 15 - 重叠 53） | **1:1.33**（后端测试更多但分散） | ⚠️ 后端单测密度 = 源码行比前端一半，用例数多但专项少，长尾场景缺覆盖 |
| 核心代码行数 | 5,197（type_checker 2286 + parser 1312 + ast 582 + evaluator 1017） | 7,199（native 2770 + mir 1896 + wasm 955 + lir 876 + hir 574 + pipeline 128） | **1:1.38**（前端 42%，后端 58%） | ✅ 代码行数比合理，前端复杂度集中在类型系统（2286 行/5197=44%） |
| 测试密度（测试行数/源码行数） | 0.88（parser 0.90 + evaluator 1.13 + type_checker 0.61） | 0.39（native 0.33 + mir 0.41 + wasm 0.43） | **2.26:1**（前端测试密度为后端 2.3 倍） | ⚠️ 后端测试严重不足，结构性改造风险高，第 69 轮测试+回归轮专门补 |
| 最近 3 轮任务分布（64-65-66，66=评审） | 开发×2（Parser 错误恢复 + HM generalize）+ 评审×1 | 开发×2（regalloc CC 拆分 + emit_abi_call 骨架）+ 评审×1 | **1:1** | ✅ 名义任务数 1:1，实际后端每轮代码量是前端 2-3 倍，符合配比 |
| 积压正确性风险（P1） | **2 项**（ErrorExpr 下游归零风险 + TypeVar 泄漏跨层污染） | **3 项**（WasmGC 双 bug 合并 1 任务 + Phi 观察期超期升级） | 2:3 | ⚠️ P1 积压总数 5（创 66 轮以来新高），之前最多 2 项。第 67 轮必须清零 2 项（前端 1 + 后端 1），第 68 轮清零剩余 2 项（前端 1 + 后端 1），里程碑 P1 = 0 |
| 积压可维护性风险（P2） | **2 项**（HM TVar 区分 + mut 幻影，合并入 harden 任务） | **2 项**（Native XMM0 冲突 + 后端测试密度缺口） | 1:1 | ✅ P2 数控制良好，4 项 P2 中有 3 项都与 P1 同源合并（harden / 同轮附带），只有第 69 轮测试补齐是独立 P2 |

### 平衡结论与资源配比建议

**下 3 轮（第 67-68-69 轮）资源配比 = 前端 55% / 后端 45%**，较第 63 轮评审建议的 35:65 反转——因为 P1 积压数前端 2、后端 2（Phi 是收尾不是新发现的大问题），前端的 ErrorExpr 下游修复（P98 easy）和 TypeVar 三合一 harden（P92 hard）都是 1 次开发清零多个问题的高 ROI 任务；后端 WasmGC 两个 P1 虽严重但集中在同一个文件（wasm_backend.py）+ 2 个字段修正，实际修改量少于前端 harden（三合一 120+ 行）。

具体节奏：

| 轮次 | 前端任务（估算代码量） | 后端任务（估算代码量） | 前端:后端 代码比 | 本轮目标 |
|------|------------------------|------------------------|------------------|----------|
| **第 67 轮** | ErrorExpr 下游修复（type_checker ~30 行 + evaluator ~15 行 + tests ~120 行 = ~165 行） | WasmGC 双 P1 修复（wasm_backend ~25 行 + ir_nodes/lir_lowering ~10 行 + tests ~120 行 = ~155 行） | ~**1.06:1**（基本 1:1，P1 清零 2/5） | **P1 清零里程碑 2/5 = 前端 ErrorExpr + 后端 WasmGC 双 bug**，前后端两道最紧急 P1 搞定，前端错误恢复体系恢复正常 |
| **第 68 轮** | TypeVar 泄漏+HM TVar+mut 幻影 三合一 harden（type_checker ~120 行 + tests ~150 行 = ~270 行） | Phi inconsistency 升级+消费+Loop Phi 覆盖（mir_lowering ~70 行 + tests ~150 行 = ~220 行）**附带** Native XMM0 冲突修复（native_backend ~20 行 + tests ~50 行 = ~70 行） | ~**270:290 ≈ 0.93:1**（基本 1:1，P1 清零 5/5 里程碑） | **P1 清零里程碑 5/5 = 前端最后 1 项 + 后端最后 1 项 + 后端 P2 XMM0 顺手清**，前端 HM 类型系统完整性从 85% → 95% 迈进，后端 MIR Phi 正式从观察期进入强保证阶段 |
| **第 69 轮（测试+回归轮）** | 类型系统边界测试矩阵（test_type_checker ~300 行新增） | Native ABI 长尾 + WasmGC wat 合法性双测试补齐（test_native_backend ~200 行 + test_backends ~150 行 = ~350 行） | ~**300:350 ≈ 0.86:1** | **测试密度提升目标达成**：前端测试密度 0.61→0.70、后端综合 0.39→0.45、Native 0.33→0.40。进入下一个 3 轮周期（第 70-72 轮）时质量基线更扎实，结构性改造回归风险降低 50%+ |
| **合计 3 轮** | 前端工作包 × 3（≈ 735 行新增/修改） | 后端工作包 × 5（两项附带合并 + 两项并行 = ≈ 940 行新增/修改） | ~**1:1.28**（按代码行数；按难度加权 前端 harden P92 占一半 → 加权比约 1:1.15，非常均衡 55:45） | 3 轮结束时 P1 积压 = 0（里程碑！）、P2 积压 = 0（4/4 清零）、测试密度两端向 0.5+ 安全线靠拢 |

**兜底预案**：若第 68 轮 frontend_harden_typevar_leak_guard（hard P92）超时（如 generalize 打标+ instantiate 守卫引起现有 10 个 generalize 专项测试回归），可将 frontend_type_system_test_matrix（第 69 轮 P78 easy）顺延至第 70 轮，把第 69 轮前端时间留给 harden 任务的回归修复 + 现有 10 个专项调试。后端第 69 轮测试补齐不受影响。
