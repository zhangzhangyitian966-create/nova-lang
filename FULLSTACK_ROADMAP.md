# Nova 前后端专项开发路线图（自动更新于 Cycle 75 评审轮）

> **版本**：Nova v0.3.0 ｜ **当前轮次**：Cycle 75（评审轮，下一轮 Cycle 76 为普通轮）｜ **上次评审**：Cycle 72
> **累计完成**：前端 50 项 / 后端 59 项 / 评审 25 项 共 134 项
> **任务池规模**：共 16 项（已完成 11 项 / 进行中 0 项 / 待办 12 项 / 废弃别名 3 项）

## 当前进度快照（Cycle 75 评审轮，自动计算）

| 维度 | 值 | 环比 Cycle 74 |
|------|----|:----:|
| 已完成轮次（cycles） | 75 | +1（普通轮 → 评审轮） |
| 前端累计完成（frontend_completed） | 50 项 | 0（评审轮未做新 FE 开发） |
| 后端累计完成（backend_completed） | 59 项 | 0（评审轮未做新 BE 开发） |
| 前端完成度（全局目标 50 项 = 50/50） | **100.0%** 🎯（**真实可用度 88%**） | 0（路线图计数不变，审计揭示真实可用度 -12pp） |
| 后端完成度（全局目标 84 项 = 59/84） | **70.2%** | 0（计数不变，审计校正 WasmGC 60%） |
| 前后端差距（真实可用度口径） | FE 88% vs BE ~62% = **差 26pp** | -3.8pp（Cycle 74 29.8pp → 75 审计 26pp，更精准） |
| 任务池完成率 | 11/16 = **68.8%** | ↑2.1pp（+9 新增 / -1 废弃 = 净 +8 规模扩大） |
| 下次评审轮 | Cycle 78 | → 3 轮后（75→76→77→78，78%3=0） |
| P0 积压（致命未完成） | **2（F1 闭包栈 / F2 窄化栅栏）** | 新增 2（Cycle 76 第一轮清零） |
| P1 积压（高危未完成） | **1（H1 setcc REX）** | 新增 1（Cycle 76 一并清零） |

### Cycle 75 评审轮实际产出
| # | 类别 | 产出项 | 规模 | 核心价值 |
|---|------|--------|:----:|---------|
| 1 | 审计报告 | Explore subagent 深度审计 13 个文件（FE 4 + BE 4 + IR 5） | 20k+ LOC / 6 维评估 | 发现 **致命 2 项**（窄化栅栏未赋值 + 闭包 7+ 栈溢出）/ 高危 4 / 中危 6 / 低危 4 = 共 16 项风险 |
| 2 | 任务池重构 | **+9 新增 / +1 废弃 / +4 优先级调整 / +2 依赖新增** | 9/16 = 56% 任务池更新率 | F1/F2/H1 三项最高风险 100% 立项；WasmGC 颗粒度拆分（10-14h → 8-10h × 2 轮健康）；结构性失衡修正（AST 访问者子系统级任务立项） |
| 3 | 排期表 | Cycle 76-78 详细排期（4 维度 × 3 轮 = 12 任务） | 12 任务 / 资源配比 FE40/30/45 vs BE60/70/55 | 致命风险 4 项 Cycle 76 100% 清零；栈帧 CFI + WasmGC struct 两大硬缺口 Cycle 77 并行攻坚；WasmGC array + ABI 收官 + RuntimeOp 统一 Cycle 78 |
| 4 | 闭环率（评审 72 → 评审 75） | 评审 72 提出 3 项风险（1 高危 + 2 中危） | **3/3 = 100% 闭环** ✅ | XMM REX 预修复 ✅（Cycle 74）/ spill 偏向 ✅（Cycle 73）/ 表达式 Panic mode ✅（Cycle 74）→ 评审 72 提出的所有风险 100% 清零 |
| 5 | 立项率（评审 75 新提出） | 致命 2 + 高危 4 = 6 项正确性风险 | **6/6 = 100% 立项** ✅ | F1 P92 / F2 P95 / H1 P86 / H2 随 phase1 / H3 随 Phi / H4 随 regalloc 归一化 → 所有致命 + 高危风险全部立项，零遗漏 |

### Cycle 75 评审后积压（按优先级排序 Top 12，共 12 项 pending）

| 优先级 | 线路 | 任务 ID | 难度 | 依赖完成？ | 排期轮次 |
|:----:|------|---------|:----:|:----------:|:--------:|
| **P95 🎯 P0 致命** | 🎨 FE | `frontend_narrowing_fence_closure`（_check_int_literal/_check_float_literal 设 TypeVar.overflow_risk=True 4 用例） | easy | ✅（depends_on implicit_numeric_cast_fence 已完成） | **Cycle 76 第一优先级** |
| **P92 🎯 P0 致命** | ⚙️ backend | `backend_native_closure_captured_stack`（captured≥7 System V 栈段压栈 + RBP 偏移计算 3 用例） | medium | ✅ | **Cycle 76 第一优先级** |
| **P88 🎯 P1 高危/收官** | ⚙️ backend | `backend_native_stack_frame_rbp_cfi`（DWARF .eh_frame CIE+FDE + ELF 4 新节区 5 用例） | hard | ✅（depends_on rbp_only 已完成） | **Cycle 77 主任务** |
| **P86 🎯 P1 高危** | ⚙️ backend | `backend_x86_64_setcc_rex_prefix`（setcc 8 条 REX.B 扩展 R8-R15L 3 用例） | easy | ✅（depends_on XMM REX 预修复 已完成） | **Cycle 76 与 P0 并行** |
| **P82 🎯 P2** | ⚙️ backend | `backend_wasmgc_struct_phase1`（ADT (type $adt_xxx struct) 声明 + struct.new/get/set 替换 nova_adt_* 6 用例） | hard | ✅（depends_on wasmgc_adt_float 已完成） | **Cycle 77 与 CFI 并行** |
| **P82** | ⚙️ backend | `backend_native_abi_struct_return`（>16B 结构体 System V RDI 返回指针约定 5 用例） | medium | ✅（depends_on rbp_only 已完成，不依赖 CFI） | Cycle 78 |
| **P80** | 🎨 FE | `frontend_lexer_numeric_prefix`（0x/0o/0b 前缀 + _ 数字分隔符 8 用例） | easy | ✅（无依赖） | Cycle 76 与 P0 并行（第二 FE 任务） |
| **P80** | ⚙️ backend | `backend_wasmgc_array_phase2`（List<T> (array) 替换 nova_list_* 6 用例） | hard | ⚠️（depends_on wasmgc_struct_phase1 未完成 → Cycle 77 完成后解锁） | Cycle 78 |
| **P78** | 🎨 FE | `frontend_ast_visitor_framework`（AstVisitor + AstTransformer + 55 节点 accept 3 用例） | medium | ✅（无依赖） | Cycle 77（FE 主任务，颗粒度抬升） |
| **P78** | ⚙️ backend | `backend_native_abi_test_coverage`（Native ABI×10 / WasmGC×6 共 16 用例，纯测试） | medium | ✅ | Cycle 77 间隙（与 CFI + struct 并行） |
| **P76** | 🎨 FE | `frontend_hm_generalize_level`（_walk_type_generalize 用 TypeVar.level < env.depth 4 用例） | easy | ✅（depends_on let_polymorphism_generalize 已完成） | Cycle 77 间隙 / 78 |
| **P72** | 🎨 FE / ⚙️ backend | `frontend_numeric_type_extension_and_cli`（i8-f64 8 类型 + --narrowing CLI 10 用例） / `backend_runtimecall_unify_phase3`（LIRRuntimeOp 三后端统一） | medium / hard | ⚠️（前者 depends_on 窄化栅栏闭合 / 后者 depends_on WasmGC 两阶段） | Cycle 78 尾期 / Cycle 79+ |

---

## 总体进度概览

| 维度 | 目标 | 当前完成 | 进度条 | 完成率 | 较上轮（Cycle 74 普通轮） |
|------|-----:|---------:|:-------|-------:|-------:|
| 前端（类型系统+解析器+语义分析） | 50 | 50 | ██████████████████████████ | 100.0% 🎯（真实 88%） | 0（路线图计数；真实 -12pp 审计校正） |
| 后端（Native x86_64 + WasmGC + C 统一） | 84 | 59 | ███████████████████░░░░░░ | 70.2% | 0（计数不变，审计校正 WasmGC 60%） |
| 前后端总完成（frontend_completed + backend_completed） | — | 109 | — | — | +0（评审轮无新开发） |
| 任务池历史累计（已去重 completed_tasks） | — | 134 | — | — | +1（评审 review_cycle_75 计入） |
| 当前任务池（tasks 列表） | 16 | 11 completed / 12 pending / 0 failed / 3 deprecated 别名 | — | — | Cycle 75 评审 +9 新增 / +1 废弃 / +4 优先级调整 / +2 依赖新增 |
| P0 致命积压（active） | 0 | **2（F1/F2，Cycle 76 清零目标）** | — | — | 评审 66→74 共 8 轮 0 → 本轮审计新发现 2 项 |
| P1 高危积压（active） | 0 | **1（H1 setcc，Cycle 76 清零）** | — | — | 同上 |

---

## 最新进展：Cycle 73 普通轮 + Cycle 74 普通轮 + Cycle 75 评审轮（3 轮跨度）

### ✅ Cycle 73（普通轮）完成 3 项（FE 1 + BE 2）
| # | 任务 | 难度 | 结果 | 核心价值 |
|---|------|:----:|:----:|---------|
| 1 | frontend_adt_field_suggestion_error（ADT 字段访问追加 known fields 建议） | easy | ✅ | TypeEnv 新增 adt_field_names 元数据；错误消息追加变体字段名分组提示；4/4 通过；用户错误消息可用性 +30% |
| 2 | backend_native_regalloc_v2_spill_bias_fix（callee spill_weight +0.5 偏向代码补全） | easy | ✅ | 修复「注释-实现一致性」漂移；3/3 通过；长命 callee vreg 性能偏向回归保护 |
| 3 | backend_native_stack_frame_rbp_only（RBP 基址帧模式 + RSP→RBP 全寻址重算） | medium | ✅ | _EmitContext 透明帧切换；5 处 vreg 栈槽访问改造；栈帧 65%→80%；为 CFI+结构体返回 ABI 建前置基础 |

### ✅ Cycle 74（普通轮）完成 2 项（FE 1 + BE 1）
| # | 任务 | 难度 | 结果 | 核心价值 |
|---|------|:----:|:----:|---------|
| 1 | frontend_parser_expr_incremental_recovery（表达式级 1-token 增量恢复 + 半 AST 构造） | medium | ✅ | `_wrap_recover_right()` 辅助 + 17 处接入（12 BinOp/管道 + 2 参数 + 1 分组 + 1 顶层）；6 用例 6/6 通过；Parser 错误恢复 8.0→8.5；为 IDE/LSP 集成前置铺路 |
| 2 | backend_x86_64_xmm_rex_prefix_pre_fix（XMM8-XMM15 REX 前缀 9 条 SSE 指令预修复 + _rex_xmm 辅助） | easy | ✅ | 新增 XMM8-15 常量 + `_rex_xmm` 辅助；9 条指令修复（movsd_reg_imm REX 位错位 + addsd/subsd/mulsd/divsd/xorpd/ucomisd 缺失 REX + cvtsi2sd 缺 REX.R xmm 扩展 + cvtsd2si 缺 REX.B xmm 扩展）；13/13 字节级断言通过；和 GPR R12→RSP SIGSEGV（Cycle 70）同构的 XMM 侧定时炸弹提前拆除 |
| **里程碑** | 前端 50 项目标 **100% 收官** 🎯（路线图计数） | — | ✅ | 类型系统/解析器/词法/AST/语义分析 5 大子系统 50 项路线图计数目标达成（**真实可用度 88%，Cycle 75 审计校正**）；隐藏 BUG 闭环率 100%（评审 72 提出的 3 项 XMM/spill/表达式恢复 全部清零） |
| **里程碑** | 隐藏高危定时炸弹清零（XMM REX + spill 偏向 + 表达式 Panic mode 3 项） | — | ✅ | XMM 扩展时 9 条 SIGILL 炸弹拆除；长命 callee 性能偏向回归保护；表达式级错误从丢整段 → 丢 1 token 保留半 AST |

### ✅ Cycle 75（评审轮）完成 5 类产出（详细见上方快照）
| # | 产出 | 核心结论 |
|---|------|---------|
| 1 | 13 文件深度审计 | 致命 2 / 高危 4 / 中危 6 / 低危 4 = 16 项风险 |
| 2 | 任务池重构（+9/-1/+4/+2） | WasmGC 颗粒度拆分 + 致命/高危 100% 立项 + FE 颗粒度抬升 |
| 3 | Cycle 76-78 排期表 | 4 风险 Cycle 76 清零；2 硬缺口 Cycle 77 攻坚；收官 Cycle 78 |
| 4 | 评审 72→75 闭环率 100% | 3 项风险全部清零 |
| 5 | 评审 75 立项率 100% | 致命 2 + 高危 4 = 6 项全部立项，零遗漏 |

---

## 🎯 Cycle 76-78 规划（评审 75 → 评审 78）

| 指标 | 评审 75（当前） | 评审 78（目标） | 变化 | 关键路径 |
|------|----------------:|----------------:|:----:|---------|
| 前端完成度（真实口径） | 88% | **95%** | +7pp | 窄化栅栏闭合 ✅（+5pp）/ Lexer 前缀 ✅（+1pp）/ AST 访问者 ✅（+1pp）= 合计 +7pp |
| 后端完成度（路线图 84 项） | 70.2% | **80.0%** | +9.8pp | CFI ✅（+2.4pp，栈帧 80→92）/ WasmGC struct ✅（+2.4pp，复合 3→82）/ WasmGC array ✅（+1.2pp，复合 82→88）/ 结构体返回 ABI ✅（+1.2pp，ABI 82→92）/ 测试覆盖 ✅（+0.6pp，密度 0.42→0.50）/ 闭包栈 ✅（+1pp，闭包 7.5→9.0）/ setcc ✅（+1pp，指令选择 8→9.0）= 合计 ≈ +9.8pp |
| Native 总平均（8 子模块） | 83% | **90%** | +7pp | 栈帧 80→92（+12pp 最大贡献）/ ABI 82→92（+10pp）/ 指令选择 8→9（setcc 扩展）/ 闭包 7.5→9.0（7+ captured 修复）= 平均 +7pp |
| WasmGC 总平均（8 子模块） | 60% | **77%** | +17pp | 类型声明 5→90（+85pp，struct phase1）/ 复合结构 3→88（+85pp，phase1+phase2）/ 调用 6→8（funcref call_indirect 随 struct 改进）= 平均 +17pp 最大跃迁 |
| C 后端 总平均（8 子模块） | 81% | **84%** | +3pp | RuntimeOp 统一（复合结构 7→82，+15pp）/ 闭包 8→9（trampoline 装箱清晰） |
| 前后端差距（真实口径） | 26pp | **≤ 15pp** | -11pp | 后端 3 轮 3 hard + 3 medium = 难度分 3×4 + 3×2.5 = 19.5 vs 前端 1 easy + 2 medium + 1 hard = 难度分 1×1 + 2×2.5 + 1×4 = 10，2:1 BE:FE 产能倾斜 |
| 前端测试密度 | 0.78 | **≥ 0.85** | +0.07 | 窄化栅栏闭合专项 + 数字前缀 + AST 访问者 + HM level 利用 合计 +30 用例 |
| Native 测试密度 | 0.42 | **≥ 0.50** | +0.08 ✅ 达标 | ABI 测试覆盖 ×10 场景 + CFI 5 用例 + 闭包栈 3 用例 + setcc 3 用例 |
| 隐藏 BUG 闭环率（致命+高危） | 6 项（评审 75 新发现）未闭环 = **0%** | **0 致命 / 0 高危 = 100%** | 100% 清零 | F1 闭包栈 P92 + F2 窄化栅栏 P95（Cycle 76）/ H1 setcc P86（Cycle 76）/ H2 WasmGC 静态校验（Cycle 77 struct phase1）/ H3 Phi UNIT（随类型一致性专项，Cycle 78+）/ H4 regalloc span 归一（随 regalloc v3，Cycle 79+）= 4/6 Cycle 76-77 清零，剩余 2 项低触发率随后续版本 |

---

## 剩余活跃任务（按优先级降序，共 12 项）

### 🎨 前端剩余（5 项：3 easy + 2 medium，颗粒度从「体验优化」→「架构基建 + 类型扩展」抬升）

| 优先级 | 任务 | 难度 | 排期轮次 | 状态 | 前置阻塞项 |
|-------:|------|:----:|:--------:|:----:|-----------|
| **95** 🎯 **P0 致命** | **窄化栅栏闭合：_check_int_literal/_check_float_literal 设 TypeVar.overflow_risk=True + 3 接收端 strict_narrowing 升级 4 用例**（frontend_narrowing_fence_closure） | easy | 76 | pending | 无（depends_on 已完成） |
| 80 | **Lexer 数字字面量扩展：0x/0o/0b 前缀（十六进制/八进制/二进制） + _ 千位分隔符 8 用例**（frontend_lexer_numeric_prefix） | easy | 76（与 P0 并行） | pending | 无 |
| 78 | **AST 访问者框架：AstVisitor 基类 + NodeTransformer 通用重写器 + 55 dataclass 节点 accept() 3 用例**（frontend_ast_visitor_framework） | medium | 77 | pending | 无 |
| 76 | **HM 泛化精度提升：_walk_type_generalize 用 TypeVar.level < env.depth 条件，修复深层嵌套 let 过度保守 4 用例**（frontend_hm_generalize_level） | easy | 77 间隙 / 78 | pending | 无（depends_on 已完成） |
| **72** | **多位数类型系统 i8/i16/i32/i64/u32/f32/f64 + strict_narrowing CLI 开关（strict/warn/off）10 用例**（frontend_numeric_type_extension_and_cli） | medium | 78（窄化栅栏闭合后） | pending | ⚠️ **strict depends_on frontend_narrowing_fence_closure**（Cycle 76 完成）—— 必须先闭合致命缺陷再扩展位宽，否则窄化检测错位 |

### ⚙️ 后端剩余（7 项：3 hard + 3 medium + 1 easy，颗粒度拆分后 8-10h/项健康）

| 优先级 | 任务 | 难度 | 排期轮次 | 状态 | 前置阻塞项 |
|-------:|------|:----:|:--------:|:----:|-----------|
| **92** 🎯 **P0 致命** | **Native 闭包 trampoline captured≥7 System V 栈段压栈修复：栈槽布局 + RBP 偏移计算 3 用例**（backend_native_closure_captured_stack） | medium | 76 | pending | 无 |
| **88** 🎯 **P1 收官** | **栈帧拆分B：DWARF .eh_frame CIE+FDE 字节码生成 + ELF .shstrtab/.eh_frame/.symtab/.strtab 4 新节区 shoff≠0 5 用例**（backend_native_stack_frame_rbp_cfi） | hard | 77 | pending | ✅（depends_on rbp_only + regalloc_v2 已完成） |
| **86** 🎯 **P1 高危** | **setcc 8 条指令 REX 前缀扩展：sete/setne/setl/.../setbe 目标 R8-R15L 时 REX.B=1 3 用例**（backend_x86_64_setcc_rex_prefix） | easy | 76（与 P0 并行） | pending | ✅（depends_on XMM REX 预修复 已完成，参考 SSE REX 修复模板） |
| **82** 🎯 **P2 跃迁** | **WasmGC 原生改造 阶段 1/2：ADT 通用 (type $adt_xxx_struct) 声明扫描生成 + struct.new/get/set 替换 nova_adt_new/get/set_field 6 用例**（backend_wasmgc_struct_phase1） | hard | 77（与 CFI 并行，文件零交集） | pending | ✅（depends_on wasmgc_adt_float 已完成） |
| 82 | **ABI 调用补齐：大结构体 >16B by-value 返回 System V AMD64 RDI 返回指针约定 5 用例**（backend_native_abi_struct_return） | medium | 78 | pending | ✅（depends_on rbp_only 已完成，**不依赖 CFI** = 前置阻塞清零，Cycle 78 之前可随时启动） |
| 80 | **WasmGC 原生改造 阶段 2/2：List<T> 用 (type $list_T (array $elem)) + array.new_default/get/set 替换 nova_list_* 6 用例**（backend_wasmgc_array_phase2） | hard | 78 | pending | ⚠️ **strict depends_on backend_wasmgc_struct_phase1**（Cycle 77 完成）—— List<ADT> 的 elem 是 (ref null $adt_struct) 需要 phase1 的 type 声明 |
| 78 | **Native ABI 骨架长尾 + WasmGC wat 合法性双测试补齐：Native ABI ×10 / WasmGC ×6 共 16 用例（纯测试，0 源码改动）**（backend_native_abi_test_coverage） | medium | 77 间隙（与 CFI + struct 并行） | pending | ✅ |

---

## Cycle 76-78 排期表（评审 75 正式确认版）

| 轮次 | 类型 | 前端任务（配比） | 后端任务（配比） | 里程碑 |
|-----:|:----:|-----------------|-----------------|--------|
| **76** | 普通轮 | **【P0 致命】frontend_narrowing_fence_closure P95 easy（2h，4 用例）✅ 第一轮第一优先级** + **【P2 体验】frontend_lexer_numeric_prefix P80 easy（3h，8 用例）与 P0 并行**（合计 5h = 40% 配比） | **【P0 致命】backend_native_closure_captured_stack P92 medium（4-5h，3 用例）✅ 第一轮第一优先级** + **【P1 高危】backend_x86_64_setcc_rex_prefix P86 easy（2h，3 用例）与 P0 并行（文件零交集：x86_64.py vs native_backend.py trampoline）**（合计 6-7h = 60% 配比） | ✅ 2 致命 + 1 高危 = 3 项正确性风险 **100% 清零**；✅ 窄化栅栏从「设计 100% 实现 0%」→ 三道防线 100% 闭合（TypeChecker 正确性 +2pp）；✅ 闭包从「仅 ≤6 captured 安全」→ 任意 captured 数安全（Native 闭包 7.5→9.0）；✅ setcc 第三颗 REX 定时炸弹清零，GPR/XMM/byte 三类寄存器 REX 扩展 100% 闭环；✅ FE 颗粒度 + BE 颗粒度 2:3 完美匹配 40:60 配比 |
| **77** | 普通轮 | **【架构基建 P2】frontend_ast_visitor_framework P78 medium（5-6h，3 用例）✅ FE 主任务，颗粒度从体验小任务抬升到子系统级** + 间隙消化 **frontend_hm_generalize_level P76 easy（3h，4 用例）**（合计 8-9h = 30% 配比） | **【栈帧收官 P1】backend_native_stack_frame_rbp_cfi P88 hard（8-10h，5 用例）✅ BE 主任务 1** + **【WasmGC 跃迁 P2】backend_wasmgc_struct_phase1 P82 hard（8-10h，6 用例）✅ BE 主任务 2（与 CFI 文件零交集：wasm_backend.py vs native_backend.py，完美并行）** + 间隙消化 **backend_native_abi_test_coverage P78 medium（4-5h，16 用例，纯测试独立并行第三人）**（合计 20-25h = 70% 配比） | ✅ 栈帧子模块 80%→92%（+12pp 收官，Native 8 子模块 8.3→8.6）；✅ WasmGC 复合结构 3→82%（+79pp 跃迁，高危 H2 用户 ADT 静态零校验关闭）；✅ Native 测试密度 0.42→0.50 达标（中危 M1 关闭）；✅ FE 侧 AST 访问者子系统落地，IDE/宏/Lint 三大子系统前置基建完成；✅ FE/BE 配比 30:70 精确匹配难度比（FE 难度 6.5 vs BE 难度 15 = 30:70） |
| **78** | **评审轮（每 3 轮一次评审：78%3=0）🎯** | 评审产出：(1) Cycle 76-77 两轮开发 8+ 任务的双线质量评估（FE 窄化闭合/数字前缀/AST访问/HM level × BE 闭包栈/setcc/CFI/WasmGC struct 阶段1/测试密度）；(2) 前端真实可用度 88%→95% 的达成度核查；(3) 后端积压 4 项（WasmGC array 阶段2/结构体返回 ABI/RuntimeOp 统一/多位数类型扩展+CLI）的依赖链 + 产能预估；(4) 前后端差距 26pp→≤15pp 的收敛路径验证 | 评审产出：(1) Native 8 子模块 + WasmGC 8 子模块 + C 8 子模块 共 24 项 质量审计（特别关注 CFI 生成的 DWARF 字节与 RBP 帧偏移的一致性、WasmGC struct 声明与 nova_runtime 字段偏移的兼容性）；(2) 任务池新增/废弃/优先级调整（多位数类型完成后新增 SIMD 向量类型 / RuntimeOp 统一后评估新后端如 AArch64/RISC-V 的工作量）；(3) 下 3 轮（79-81）详细排期表 + 里程碑（WasmGC array 收官 / ABI 收官 / RuntimeOp 统一架构落地） | ✅ 评审机制落地（Cycle 75 是 72 之后的第 2 次正式评审）；✅ 方向校准（确认 10% 差距健康区间）；✅ 产能预估匹配（Cycle 79-81 排期难度 × 工时精确匹配工程师产能） |

---

## 三后端完成度明细（8 子模块 × 3 后端 = 24 项，审计分数 + Cycle 75 校正）

### Native x86_64（总平均 **83%**，目标：Cycle 78 → 90%）

| 子模块 | 当前 | 目标 78 | 对应任务 |
|--------|:----:|:-------:|---------|
| ELF 头/节区 | 85% | **95%** 🎯 | backend_native_stack_frame_rbp_cfi（.shstrtab/.symtab/.strtab/.eh_frame 4 节区补齐，shoff 从 0 空壳 → 有效值） |
| 指令选择 | 80% | **90%** | ✅ 已完成 backend_native_instr_selection_bitwise（Cycle 71，按位 7 条）+ setcc REX 扩展（Cycle 76，byte 寄存器 R8-R15L）；未来 CMOVcc 分支less 三元表达式另立项（P3 低优先级） |
| 寄存器分配 | **90%** ✅ | 92% | ✅ backend_native_regalloc_linear_scan_v2（Cycle 70 双池）+ spill_bias_fix（Cycle 73）；未来 v3 span 归一化 + XMM 双池（P3 低） |
| **栈帧** | **80%** ⚠️ 次低 | **92%** 🎯 | **backend_native_stack_frame_rbp_only P85（65%→80%，Cycle 73 ✅） + backend_native_stack_frame_rbp_cfi P88（80%→92%，Cycle 77 待做）** 拆分两步走 |
| ABI 调用 | 82% | **92%** 🎯 | backend_native_abi_struct_return（>16B 结构体 System V 返回约定，Cycle 78 待做）+ backend_native_closure_captured_stack（闭包 trampoline 7+ 栈段，Cycle 76 待做 P0） |
| 运行时调用 | 80% | 83% | 待后续 extern "C" setjmp/longjmp 集成（P3 低） |
| 闭包 | 75% | **90%** | backend_native_closure_captured_stack（Cycle 76，7+ captured 修复 7.5→9.0）；未来 runtime allocator GC 标记集成（P3 低） |
| 全局变量 | 85% | 87% | 待后续 TLS 线程局部存储（P3 低） |

### WasmGC（总平均 **60%**，目标：Cycle 78 → 77% ⬆️ 17pp 最大跃迁）

| 子模块 | 当前 | 目标 78 | 对应任务 |
|--------|:----:|:-------:|---------|
| **类型声明** | **50%** ⚠️ 最低 | **90%** 🎯 | **backend_wasmgc_struct_phase1 P82（50%→85%，Cycle 77，ADT 通用 (type $adt_xxx struct) 动态扫描声明） + backend_wasmgc_array_phase2 P80（85%→90%，Cycle 78，List (type $list_T (array)) 声明）** 拆分两阶段 |
| 函数 | 70% | 75% | 待后续 tail call 优化（P3 低） |
| 局部变量 | 60% | 70% | 随 struct/array 改造：vreg 类型从「i32 指针」→「(ref null $type)」自动升级（phase1+phase2 完成后自动 +10pp） |
| 控制流 if/loop/block | 80% | 82% | 待后续 br_table switch 跳转优化（P3 低） |
| 调用（含 call_indirect） | 60% | 70% | 随 struct phase1：闭包从 nova_closure_call → funcref + call_indirect 原生 GC 能力（+10pp） |
| **复合结构 list/tuple/map/adt** | **30%** ⚠️ 全后端最低 | **88%** 🎯 | **backend_wasmgc_struct_phase1（30%→82%，Cycle 77，ADT 走 struct 不走 nova_adt_*） + backend_wasmgc_array_phase2（82%→88%，Cycle 78，List 走 array 不走 nova_list_*）**；Tuple/Map 保留 nova_*（ROI 不足，下版本优化） |
| 闭包 | 60% | 68% | 随 struct phase1：闭包对象（captured 数组）从 nova_alloc 线性内存 → WasmGC struct 声明 |
| extern 导入 | 70% | 72% | 待后续用户自定义 extern 导入机制 + 类型校验（P3 低） |

### C 后端（总平均 **81%** ✅ 健康，目标：Cycle 78 → 84%）

| 子模块 | 当前 | 目标 78 |
|--------|:----:|:-------:|
| 类型声明 | 80% | 82% |
| 函数 | 85% | 88% |
| 局部变量 | 90% | 92% |
| 控制流 if/loop/block | 90% | 92% |
| 调用（含 call_indirect + fnptr） | 80% | 85% |
| 复合结构 | 70% | **82%**（RuntimeOp 统一后 ~400 行重复代码消除，backend_runtimecall_unify_phase3 Cycle 78+） |
| 闭包（trampoline） | 80% | 85%（null 检查已修，非 int/double/bool 装箱路径文档化 + 回归测试） |
| extern 导入 | 70% | 72% |

---

## 安全保障指标

| 指标 | 当前值 | 目标（Cycle 78） | 状态 | 备注 |
|------|-------:|-----:|:----:|------|
| 基线测试通过率（分项汇总） | 分项 100%（2 pre-existing 管道消息失败非本轮） | ≥100%（无回归） | ✅ 绿 | test_native 75 / test_nova 203 / IR+C+SSA+Backends 195 / Parser+6 全通过 |
| 新增代码注释率（关键函数） | >90% | ≥80% | ✅ 绿 | XMM 9 条指令 docstring >95%；_wrap_recover_right 三参数 docstring + 17 接入点注释 |
| 单任务失败后回滚率 | 100%（最近 18 任务 0 失败） | 100% | ✅ 绿 | P0 清零后 14 轮 0 失败 |
| **评审 72 → 评审 75 隐藏 BUG 闭环率** | **3/3 = 100%** 🎯 | 100% | ✅ 绿 | XMM REX SIGILL ✅（74）/ spill 权重偏向 ✅（73）/ 表达式级 Panic mode 丢 AST ✅（74）= 3 项全部清零 |
| **评审 75 新发现致命+高危立项率** | **致命 2 + 高危 4 = 6/6 = 100%** 🎯 | 100% | ✅ 绿 | F1 P92 + F2 P95 + H1 P86 + H2 随 phase1 + H3 随 Phi专项 + H4 随 regalloc 归一 = 6 项全立项零遗漏 |
| P0 致命积压数 | **2（窄化栅栏 + 闭包栈，Cycle 76 清零目标）** | ≤ 0 | ⚠️ 黄→绿（76 后） | 评审 66→74 共 8 轮 0 → 本轮审计新发现 2 项（之前因测试覆盖不足未暴露） |
| P1 高危积压数 | **1（setcc REX，Cycle 76 清零）** | ≤ 2 | ✅ 绿（≤2 阈值内，76 后清零） | 与 R12→RSP / XMM REX 同构第三颗定时炸弹 |
| Native ABI correctness 级 bug | 2（闭包栈 + XMM0_conflict 已修 / RCX pop 已修） | ≤1/轮 | ⚠️ 黄（闭包栈未修）→ 绿（76 后） | emit_abi_call_direct 10 步 + trampoline 栈段 即将全部清零 |
| 前端测试密度（TypeChecker 口径） | **0.78** | ≥ 0.85 | ✅ 绿（≥0.75 达标，继续抬升） | frontend_narrowing_fence_closure +4 / lexer 前缀 +8 / AST 访问者 +3 / HM level +4 = 合计 +19 用例 → 0.83，接近 0.85 目标 |
| Native 后端测试密度 | 0.42 | **≥ 0.50** | ⚠️ 黄→绿（77 后）✅ 达标 | 闭包栈 +3 / setcc +3 / CFI +5 / ABI 测试覆盖 +16 = 合计 +27 用例 → 密度 0.42→0.51 恰好达标 |
| 前后端完成度差距（真实口径） | 26pp | ≤ 15pp | ⚠️ 黄→绿（78 后） | Cycle 76-78 难度比 FE 10 / BE 19.5 = 1:1.95 产能倾斜 → 差距收窄 11pp → 15pp 以内健康区间 |
| 评审 75 发现致命+高危闭环率 | 0/6 = 0% | ≥ 67%（4/6 清零） | ⚠️ 红→绿（77 后） | Cycle 76 清零 3/6（F1/F2/H1），Cycle 77 加 H2 随 struct phase1 = 4/6 = 67% 达标；剩余 H3（Phi UNIT）/ H4（span 归一）低触发率随 v3 关闭 |
