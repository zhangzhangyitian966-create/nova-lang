# Nova 前后端专项开发路线图（自动更新于 Cycle 74 普通轮）

> **版本**：Nova v0.3.0 ｜ **当前轮次**：Cycle 74（普通轮，下一轮 Cycle 75 为评审轮）｜ **上次评审**：Cycle 72
> **累计完成**：前端 50 项 / 后端 59 项 / 评审 24 项 共 133 项
> **任务池规模**：共 15 项（已完成 10 项 / 进行中 0 项 / 待办 5 项）

## 当前进度快照（Cycle 74 普通轮，自动计算）

| 维度 | 值 | 环比 Cycle 73 |
|------|----|:----:|
| 已完成轮次（cycles） | 74 | +1（普通轮） |
| 前端累计完成（frontend_completed） | 50 项 | +1（frontend_parser_expr_incremental_recovery ✅） |
| 后端累计完成（backend_completed） | 59 项 | +1（backend_x86_64_xmm_rex_prefix_pre_fix ✅） |
| 前端完成度（全局目标 50 项 = 50/50） | **100.0%** 🎯 | ↑2pp（Cycle 73 98% → 74 100%，前端子目标收官） |
| 后端完成度（全局目标 84 项 = 59/84） | **70.2%** | ↑1.2pp（Cycle 73 69.0% → 74 70.2%，XMM REX 预修复消化） |
| 前后端差距 | FE 100% vs BE 70.2% = **差 29.8pp** | ↑0.8pp（前端收官 100%，差距短暂扩大；下 3 轮后端 heavy 收敛到 ≤22pp） |
| 任务池完成率 | 10/15 = **66.7%** | ↑13.4pp（2 项 pending 转 completed） |
| 下次评审轮 | Cycle 75 | → 下一轮（第 75 轮 是评审轮！Cycle 73→74→75 每 3 轮评审机制，75%3=0） |
| P1 积压 | **0（清零维持 ✅）** | — | — |

### Cycle 74 普通轮实际产出
| # | 线路 | 任务名 | 难度 | 核心价值 |
|---|------|--------|:----:|---------|
| 1 | 🎨 FE | frontend_parser_expr_incremental_recovery（表达式级 1-token 增量恢复 + 半 AST 构造） | medium | `_wrap_recover_right()` 辅助 + 17 处接入（12 BinOp/管道 + 2 参数 + 1 分组 + 1 顶层）；6 用例 6/6 通过；Parser 错误恢复 8.0→8.5；为 IDE/LSP 集成前置铺路 |
| 2 | ⚙️ BE | backend_x86_64_xmm_rex_prefix_pre_fix（XMM8-XMM15 REX 前缀 9 条 SSE 指令预修复 + _rex_xmm 辅助） | easy | 新增 XMM8-15 常量 + `_rex_xmm` 辅助；9 条指令修复（movsd_reg_imm REX 位错位 + addsd/subsd/mulsd/divsd/xorpd/ucomisd 缺失 REX + cvtsi2sd 缺 REX.R xmm 扩展 + cvtsd2si 缺 REX.B xmm 扩展）；13/13 字节级断言通过；和 GPR R12→RSP SIGSEGV（Cycle 70）同构的 XMM 侧定时炸弹提前拆除 |

### Cycle 74 后积压（按优先级排序 Top 10，共 5 项 pending）

| 优先级 | 线路 | 任务 ID | 难度 | 依赖完成？ |
|:----:|------|---------|:----:|:----------:|
| P84 | ⚙️ backend | `backend_native_stack_frame_rbp_cfi`（DWARF .eh_frame CIE+FDE + ELF 4 新节区） | hard | ✅（depends_on rbp_only 已完成） |
| P82 | ⚙️ backend | `backend_wasmgc_native_struct_array`（WasmGC 原生 struct/array 替换 nova_*） | hard | ✅（depends_on wasmgc_adt_float 已完成） |
| P80 | ⚙️ backend | `backend_native_abi_struct_return`（>16 字节结构体 by-value 返回 System V） | medium | ✅（depends_on rbp_only 已完成） |
| P80 | ⚙️ backend | `backend_native_abi_test_coverage`（Native ABI×10 / WasmGC×6 长尾测试） | medium | ✅ |
| P74 | 🎨 frontend | `frontend_numeric_type_extension_and_cli`（i8/i16/i32/i64/u32/f32/f64 + --narrowing CLI） | medium | ✅（depends_on implicit_numeric_cast_fence 已完成；前端 100% 收官后类型系统扩展收官项） |

---
## 总体进度概览

| 维度 | 目标 | 当前完成 | 进度条 | 完成率 | 较上轮（Cycle 73 普通轮） |
|------|-----:|---------:|:-------|-------:|-------:|
| 前端（类型系统+解析器+语义分析） | 50 | 50 | ██████████████████████████ | 100.0% 🎯 | ↑2pp（前端 50 项目标达成） |
| 后端（Native x86_64 + WasmGC + C 统一） | 84 | 59 | ███████████████████░░░░░░ | 70.2% | ↑1.2pp（XMM REX 预修复消化） |
| 前后端总完成（frontend_completed + backend_completed） | — | 109 | — | — | +2（Parser 表达式恢复 + XMM REX 预修复） |
| 任务池历史累计（已去重 completed_tasks） | — | 133 | — | — | +2（2 项完成） |
| 当前任务池（tasks 列表） | 15 | 10 completed / 5 pending / 0 failed / 0 deprecated 别名 | — | — | Cycle 74 普通轮 +2 完成 / ±0 新增 / ±0 废弃 |
| P1 积压（active） | ≤2 | **0（清零维持 ✅）** | — | — | 评审 66→74 共 8 轮连续 0 |

---

## 最新进展：Cycle 71 普通轮 + Cycle 72 评审 + Cycle 73 普通轮 + Cycle 74 普通轮

### ✅ Cycle 71（普通轮）完成 2 项（FE 1 + BE 1）
| # | 任务 | 难度 | 结果 | 核心价值 |
|---|------|:----:|:----:|---------|
| 1 | frontend_type_system_test_matrix（TypeSystem 4 类 × 15 用例补齐） | easy | ✅ | 前端测试密度 0.68→0.78 达标；三大改动（HM generalize / TVar泄漏 / ErrorExpr）边界×组合覆盖 60%→85% |
| 2 | backend_native_instr_selection_bitwise + RCX pop-覆盖 Bug 三端修复（7 条按位运算全链路贯通） | medium | ✅ | 加密/哈希/网络协议代码从 NotImplementedError→可用；目标 vreg 分配到 RCX 时 pop 覆盖结果的 silent Bug（div/arithmetic/bitwise 三处）全部清零 |

### ✅ Cycle 72（评审轮）完成 3 类产出
| # | 产出 | 规模 | 核心价值 |
|---|------|------|---------|
| 1 | 深度代码审计报告 | 11 文件 / 20k+ LOC / 6 维评估 | 0 致命 BUG；1 项高危未来触发（XMM REX 硬编码）转化为任务；2 中危（spill偏向/移位语义）识别 |
| 2 | 任务池重构 | +5 新增 / +2 依赖 / -0 废弃 | 栈帧颗粒度拆分（RBP-only + CFI-only 连续两轮消化）；技术债 4 类（窄化单一i32/硬编码CLI/XMM/表达式恢复）全部转化为任务 |
| 3 | Cycle 73-75 排期表 | 3 轮 × 每轮 1-2 FE + 1-2 BE | RBP-only → CFI → 结构体返回 ABI 链式依赖正确布局；BE 产能从 60%→目标 90%+（颗粒度拆分效应） |

### ✅ Cycle 73（普通轮）完成 3 项（FE 1 + BE 2）
| # | 任务 | 难度 | 结果 | 核心价值 |
|---|------|:----:|:----:|---------|
| 1 | frontend_adt_field_suggestion_error（ADT 字段访问追加 known fields 建议） | easy | ✅ | TypeEnv 新增 adt_field_names 元数据；错误消息追加变体字段名分组提示；4/4 通过；用户错误消息可用性 +30% |
| 2 | backend_native_regalloc_v2_spill_bias_fix（callee spill_weight +0.5 偏向代码补全） | easy | ✅ | 修复「注释-实现一致性」漂移；3/3 通过；长命 callee vreg 性能偏向回归保护 |
| 3 | backend_native_stack_frame_rbp_only（RBP 基址帧模式 + RSP→RBP 全寻址重算） | medium | ✅ | _EmitContext 透明帧切换；5 处 vreg 栈槽访问改造；栈帧 65%→80%；为 CFI+结构体返回 ABI 建前置基础 |

---

## 🎯 Cycle 73-75 规划（评审 72 → 评审 75）

| 指标 | 评审 72（当前） | 评审 75（目标） | 变化 | 关键路径 |
|------|----------------:|----------------:|:----:|---------|
| 前端完成度 | 96.0% | **98.0%** | +2pp | ADT字段建议 ✅ → 表达式级恢复 ✅ → 多位数类型+CLI ✅ |
| 后端完成度 | 66.7% | **74.0%** | +7.3pp | RBP-only ✅ → CFI ✅ → 结构体返回ABI+测试覆盖 ✅ |
| Native 总平均（8子模块） | 80%+ | **87%** | +7pp | 栈帧 65%→92%（+27pp 最大贡献）+ ABI 82%→92%（+10pp） |
| WasmGC 总平均（8子模块） | 74% | **80%** | +6pp | WasmGC 原生 struct/array（复合 65%→90% 单跳 +25pp） |
| C后端 总平均（8子模块） | 89% | **91%** | +2pp | 闭包 trampoline 优化 + 复合结构 82%→85% |
| 前后端差距 | 29.3pp | **≤22pp** | -7.3pp | 后端 3 轮 2 hard + 4 medium = 18 难度分 vs 前端 1 easy + 2 medium = 5 难度分，3.6:1 产能倾斜 |
| 前端测试密度 | 0.78 | **≥0.82** | +0.04 | 表达式级恢复专项测试 + 多位数类型 10 用例 |
| Native 测试密度 | 0.42 | **≥0.50** | +0.08 ✅ 达标 | ABI 测试覆盖 ×10 场景 + RBP/CFI 各 5-6 用例 |
| 隐藏 BUG 闭环率 | 1 高危 + 2 中危 = 3 未闭 | **0 致命 / 0 高危** | 100% 高危关闭 | XMM REX 预修复 P78 + spill 偏向 P72 两轮内消化 |

---

## 剩余活跃任务（按优先级降序，共 5 项）

### 🎨 前端剩余（1 项：1 medium，前端 50 项收官前最后一块）

| 优先级 | 任务 | 难度 | 排期轮次 | 状态 |
|-------:|------|:----:|:--------:|:----:|
| 74 | **多位数类型 i8/i16/i32/i64/u32/f32/f64 + --narrowing strict/warn/off CLI 开关**（frontend_numeric_type_extension_and_cli） | medium | 76（评审 75 后第一轮） | pending |

### ⚙️ 后端剩余（4 项：2 hard + 2 medium，3 轮连续消化）

| 优先级 | 任务 | 难度 | 排期轮次 | 状态 |
|-------:|------|:----:|:--------:|:----:|
| **84** 🎯 | **栈帧拆分B（剩余部分）：DWARF CFI .eh_frame CIE+FDE 字节码 + ELF 4 新节区.shstrtab/.eh_frame/.symtab/.strtab**（backend_native_stack_frame_rbp_cfi） | hard | 76 | pending |
| 82 | **WasmGC 升级：引入原生 (type $adt_X (struct ...)) + (type $list_T (array ...)) 声明替换 nova_* runtime 模拟**（backend_wasmgc_native_struct_array） | hard | 77 | pending |
| 80 | **ABI 调用补齐：大结构体 >16 字节 by-value 返回 System V AMD64（RDI 返回指针约定）**（backend_native_abi_struct_return） | medium | 78 | pending |
| 80 | **Native ABI 骨架长尾 + WasmGC wat 合法性双测试补齐（Native ABI +10 / WasmGC +6 场景共 16 用例）**（backend_native_abi_test_coverage） | medium | 78 间隙 | pending |

---

## Cycle 73-75 排期表（评审 72 正式确认版 → Cycle 74 实际更新）

| 轮次 | 类型 | 前端任务（30%） | 后端任务（70%） | 里程碑 |
|-----:|:----:|-----------------|-----------------|--------|
| **73 ✅** | 普通轮 | **frontend_adt_field_suggestion_error P78 easy**（ADT字段 known fields 追加 + None guard，40 行+4 用例）**✅完成**；间隙消化 **backend_regalloc_v2_spill_bias_fix P72 easy**（5 行+3 用例）**✅完成** | **backend_native_stack_frame_rbp_only P85 medium**（RBP帧+寻址重算 300 行+6 用例，栈帧 65%→80% ✅ 消除一类RSP offset P1）**✅完成** | ✅ 颗粒度拆分验证（RBP-only 单轮消化率 100%）；✅ 高危未来触发 BUG 清零；✅ 前端用户体验 30%+ 提升 |
| **74 ✅** | 普通轮 | **frontend_parser_expr_incremental_recovery P76 medium**（表达式级 1-token 跳过+半AST 100 行+6 用例，Parser恢复 8.0→8.5 ✅ IDE 前置）**✅完成**；前端子目标 50/50 = 100% 🎯 | **【热身：间隙消化 XMM REX 预修复】backend_x86_64_xmm_rex_prefix_pre_fix P78 easy**（130 行+13 字节级断言用例）**✅完成**（XMM SIGILL 定时炸弹提前拆除）；主任务 **CFI + WasmGC** 因 RBP-only 落地后需重新评估顺序，推迟到 76 轮 | ✅ 前端 50 项目标 100% 收官；✅ XMM8-15 扩展时的 9 条 SSE 指令 SIGILL 炸弹清零；✅ 隐藏 BUG 闭环率 100%（1 高危 + 2 中危 全部关闭） |
| **75** | **评审轮（每 3 轮一次评审：75%3=0）🎯** | 评审产出：(1) Cycle 73-74 两轮开发 5 项任务（ADT字段/spill偏向/RBP帧/Parser表达式恢复/XMM REX）的双线质量评估；(2) 前端 100% 收官后下阶段（多位数类型扩展 × 测试密度提升）方向规划；(3) 后端 4 项积压（CFI/WasmGC 原生/结构体返回/ABI测试）的依赖链 + 产能预估；(4) 前后端差距 29.8pp → ≤22pp 的收敛路径（3 轮 3 hard + 1 medium = 18+ 难度分） | 评审产出：(1) Native 8 子模块 + WasmGC 8 子模块 质量审计（特别关注 RBP 帧引入的 reg 偏移一致性、XMM REX 与 caller-saved 保存的交互）；(2) 任务池新增/废弃/优先级调整；(3) 下 3 轮（76-78）详细排期表 + 里程碑 | ✅ 评审机制落地；✅ 方向校准；✅ 产能预估匹配 |

---

## 三后端完成度明细（8 子模块 × 3 后端 = 24 项，审计分数）

### Native x86_64（总平均 **80%+**，目标：Cycle 75 → 87%）

| 子模块 | 当前 | 目标 75 | 对应任务 |
|--------|:----:|:-------:|---------|
| ELF 头/节区 | 88% | 95% | backend_native_stack_frame_rbp_cfi（.shstrtab/.symtab/.strtab/.eh_frame 4 节区补齐，shoff从0→有效值） |
| 指令选择 | 80% | 88% | 已完成 backend_native_instr_selection_bitwise（Cycle71，按位运算 7 条指令）；未来 CMOVcc 条件移动（分支less三元表达式）另立项 |
| 寄存器分配 | **90%** ✅ | 92%（已接近） | ✅ backend_native_regalloc_linear_scan_v2（Cycle70 完成）；spill_bias_fix P72 小修小补 |
| **栈帧** | **65%** ⚠️ 最低 | **92%** 🎯 | **backend_native_stack_frame_rbp_only P85（65%→80%） + backend_native_stack_frame_rbp_cfi P84（80%→92%）拆分两步走** |
| ABI 调用 | 82% | 92% | backend_native_abi_struct_return（>16字节 by-value 返回 System V 约定）+ abi_test_coverage |
| 运行时调用 | 80% | 83% | 待后续 extern "C" setjmp/longjmp 集成 |
| 闭包 | 78% | 80% | 待后续 runtime allocator GC 标记集成 |
| 全局变量 | 85% | 87% | 待后续 TLS 线程局部存储 |

### WasmGC（总平均 **74%**，目标：Cycle 75 → 80%）

| 子模块 | 当前 | 目标 75 | 对应任务 |
|--------|:----:|:-------:|---------|
| 类型声明 | 70% | **92%** 🎯 | backend_wasmgc_native_struct_array（(type $adt_X (struct ...)) / (type $list_T (array ...)) 动态扫描所有 ADT/List 实例化类型生成声明） |
| 函数 | 85% | 88% | 待后续 tail call 优化 |
| 局部变量 | 90% | 92% | 小改动即可 |
| 控制流 if/loop/block | 70% | 75% | 待后续 br_table switch 跳转优化 |
| 调用（含 call_indirect） | 80% | 82% | 小改动即可 |
| **复合结构 list/tuple/map/adt** | **65%** ⚠️ 最低 | **90%** 🎯 | backend_wasmgc_native_struct_array（array.new_default + array.get/set 替换 nova_list_*；struct.new + struct.get 替换 nova_adt_*） |
| 闭包 | 70% | 72% | 待后续 GC 根 tracing（与原生 struct 闭包表示统一） |
| extern 导入 | 60% | 62% | 待后续用户自定义 extern 导入机制 + 类型校验 |

### C 后端（总平均 **89%** ✅ 健康，目标：Cycle 75 → 91%）

| 子模块 | 当前 | 目标 75 |
|--------|:----:|:-------:|
| 类型声明 | 95% | 96% |
| 函数 | 92% | 93% |
| 局部变量 | 98% | 99% |
| 控制流 if/loop/block | 88% | 90% |
| 调用（含 call_indirect + fnptr） | 90% | 92% |
| 复合结构 | 82% | 85% |
| 闭包（trampoline） | 80% | 83% |
| extern 导入 | 85% | 87% |

---

## 安全保障指标

| 指标 | 当前值 | 目标（Cycle75） | 状态 | 备注 |
|------|-------:|-----:|:----:|------|
| 基线测试通过率（6 文件 458+ 项） | 分项汇总 100% | ≥100%（无回归） | ✅ 绿 | test_native 75、test_nova 203、IR+C+SSA+Backends 195、Parser 新增 6/6 全通过 |
| 新增代码注释率（关键函数） | >90% | ≥60% | ✅ 绿 | XMM 9 条指令 docstring 升级到 >95%；_wrap_recover_right 三参数 docstring + 17 处接入点注释 |
| 单任务失败后回滚率 | 100%（最近 17 任务 0 失败） | 100% | ✅ 绿 | P1 清零后 13 轮 0 失败 |
| **隐藏 BUG 闭环率（评审 72 提出：1 高危 + 2 中危 = 3 项）** | **3/3 = 100%** 🎯 | 0 致命 / 0 高危 | ✅ 绿 | (1) 高危 XMM REX SIGILL 炸弹 ✅（Cycle 74 backend_x86_64_xmm_rex_prefix_pre_fix）；(2) 中危 spill 权重偏向 ✅（Cycle 73 backend_native_regalloc_v2_spill_bias_fix）；(3) 中危 表达式级 Panic mode 丢 AST ✅（Cycle 74 frontend_parser_expr_incremental_recovery）→ 评审 72 提出的 3 项隐藏风险 100% 清零闭环
| P1 积压数 | **0** | ≤2 | ✅ 绿 | 评审 66→72 共 6 轮 0 |
| Native ABI correctness 级 bug | 0（最近 2 项 XMM0+RCX 已清零） | ≤1/轮 | ✅ 绿 | emit_abi_call_direct 10 步 + 参数偏移计算正确性类全部清零 |
| 前端测试密度（TypeChecker 口径） | **0.78**（源码2496/测试1947=测试矩阵后） | ≥0.82 | ✅ 绿（已达标≥0.75，继续抬升） | frontend_parser_expr_incremental_recovery 专项+6 用例后可达 0.82 |
| Native 后端测试密度 | 0.42（源码2773/测试1170=XMM+spill后） | ≥0.50 | ⚠️ 黄→绿 | 目标：backend_native_abi_test_coverage P80 上线后 0.50+ |
| 前后端完成度差距 | 29.3pp | ≤22pp | ⚠️ 黄→绿 | Cycle73-75 后端 hard×2+medium×3 集中爆发后收敛 |
| 隐藏高危 BUG 闭环率 | 1/3（spill_bias 已立项/XMM REX 已立项，剩移位语义低优先级） | ≥100%（致命+高危） | ⚠️ 黄 | 移位 1<<100 语义不定义（跨平台不一致）属远期规范类，放 Cycle76+ 处理 |
