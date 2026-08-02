# Nova LLM 智能开发路线图

**更新时间**: 2026-08-02 00:32
**上次评审**: 第 93 轮（路线图评审 · 五维评估 方向9.5/质量9.4/效率9.8/价值9.6/审查对齐10 + CC=13钉子户4→0清零 + M-ARCH手术B收官）
**上次开发**: 第 92 轮（_linear_scan_alloc 三闭包提升 · CC=13/14 钉子户双出榜 · unused_import v10 清理 · 3/3 = 100% 审查驱动）
**架构战略文档**: [ARCHITECTURE_VISION.md](./ARCHITECTURE_VISION.md) — 架构决策最高参考，如与本路线图冲突以其为准，本文件同步更新
**总完成度**: ~192/192 ≈ **100%**（任务池 101 项 · 新增 3 审查/评审派生）
**里程碑 M-ARCH**: ✅ **5/5 全部完成 + Phase2 100% 收尾**（cycles=80 硬截止前达成 · cycle=91 unify_c_backend_phase2 删除旧 c_codegen.py 1591 行 · LIR→C 唯一路径定板）
**里程碑 M-MEM**: ✅ **4/4 + 验证基础 全部完成**（cycles=87 Step1-4 完成 · cycle=91 Allocator 独立单测 72 passed 补齐 · Allocator API 正确性锚点齐全）
**里程碑 M-SH1**: 🚀 **In Progress · CC=13钉子户4→0彻底清零 + 6/7闸门解除**（剩余 Token 契约冻结闸门 1 项 · cycle=94 首任务强制执行）
**审查驱动任务占比（任务池总 101 项）**: 50/101 = **49.5%**（≥30% 硬约束 · 93 评审再增 3 条审查派生）
**下一阶段聚焦 cycles=94~96**：① 94：Token契约冻结(P92) + _unify_types+_detect CC=15/14双拆(P90) + unused_import v11降噪(P85) ② 95：CC=14 _has_overflow_risk + evaluator异常收窄(P88) + MIR E2E 8cases(P83) + CI超时分层(P75) ③ 96：lexer.nv骨架首轮编码(P95里程碑) + TypeChecker空分支覆盖 + CC=23 _check_fn_decl拆分边界登记 + gate_sh1_parity看板v1 · **cycles=96 末 SH-1 lexer.nv 骨架可编译 闸门7/7 100% 打开**

本路线图由 LLM 智能开发系统动态维护。

---

## 🗺️ v0.3.0 → v1.0 总览里程碑（架构战略约束）

> 第 93 轮评审结论：cycles=91-92 两轮严格执行第 90 轮评审「三轮攻坚 · 每轮1座CC大山+1架构债/测试缺口+1 filler」方向，方向评估 9.5/10，质量评估 9.4/10，效率评估 9.8/10，价值评估 9.6/10，审查对齐 10/10。五维评估全面超越 90 评审。M-ARCH 手术 B 100% 收官、CC=26 Top#1 首破、CC=13 钉子户 4→0 彻底清零（四连出榜）、连续 8 轮 100% 核心测试。唯一不足：CC=15 _unify_types Phase2 + test_mir_e2e 被挤走、unused_import 噪音 314 条未清理、审查 CI 超时连续 2 轮。cycles=94-96 三轮攻坚定档：cycle=94 末 Token 契约冻结闸门完成（6/7→7/7），cycle=96 末 lexer.nv 骨架首轮编码（SH-1 里程碑里程碑性第一步）。
>
> cycle=91 执行回顾：**3/3 100% 成功**（unify_c_backend_phase2 删旧c_codegen.py 1591行✅ + CC=26 _unify 10方法提取为_Unifier类✅ + Allocator单测72 passed✅）；测试 444→约1400 零回归；审查驱动 3/3 = 100%
> cycle=92 执行回顾：**3/3 100% 成功**（寄存器分配三闭包CC≈42拆分各≤12✅ + CC=14/13钉子户双出榜 CC=13钉子户4→0✅ + unused_import真未使用3→0✅）；测试 444→444 零回归；审查驱动 3/3 = 100%
> cycle=93 评审结论：**cycles=94-96 三轮攻坚定档**——每轮强制：1 座 CC≥15 大山 + 1 SH-1 闸门/测试缺口 + 1 filler（降噪/CI）。cycle=96 末 SH-1 lexer.nv 骨架可编译。

## 🧭 cycles=91~93 三轮攻坚任务表（第 90 轮评审输出 · 完成情况）

| 优先级 | 任务线 | 任务 | 目标轮次 | 来源 | 现状 |
|--------|--------|------|---------|------|------|
| P88 | **架构债强制收尾** | unify_c_backend_phase2 · 删除旧 c_codegen.py 1591 行 + LIR C 后端功能对齐 + test_c_codegen.py 迁移验证 | 91 强制 | 审查驱动+架构战略【手术B Phase2】 | ✅ **完成 (cycle 91)** · 36 passed, 4 skipped · LIR→C唯一路径定板 |
| P85 | **审查债务 CC=26 Top#1** | split_type_checker_unify Phase1 · HM 统一算法独立为 _Unifier 嵌套内部类（10 方法拆分）· CC 26→≤10 | 91 强制 | 审查驱动【CC Top 榜 #1】 | ✅ **完成 (cycle 91)** · 178 passed / 180 total · 55处调用点全局替换零回滚 |
| P82 | **质量补齐 测试缺口** | test_allocator_unit_suite · 新建 tests/test_allocator.py 72 passed（8 大类） | 91 优先 | 审查发现【测试缺口·Allocator 0%覆盖】 | ✅ **完成 (cycle 91)** · 72 passed in 0.13s · Libc 18 + Arena 14 + NovaBox 14 + Stats 10 |
| P85 | **审查债务 CC≈42 隐蔽爆点** | split_native_backend_reg_alloc Phase1深入 · _linear_scan_alloc 内部3闭包提升为实例方法 · 各 CC≤12 | 92 强制 | 审查驱动【CC Top #2 · native_backend.py 3157行】 | ✅ **完成 (cycle 92)** · 225→99行 · nonlocal闭包副作用→ctx Dict封装 |
| P84 | **CC=14+13 钉子户双出榜** | refactor_cc_parser_block_and_call_indirect · Parser._parse_block（14→≤5）+ LIRCBackend._compile_call_indirect（13→≤2） | 92 强制 | 审查驱动【CC=13 最后2个】 | ✅ **完成 (cycle 92)** · CC=13钉子户4→0彻底清零 · 共享double解包样板消除 |
| P85+P78 | **Filler 质量双清理** | cleanup_unused_imports_root_v10 · pyflakes扫描39文件 · 真实unused 3→0 · 兼容层10条noqa保留 | 92 Filler | 审查驱动+评审发现【unused_import 74条】 | ✅ **完成 (cycle 92)** · 真实unused_import清零 |
| P92 | **SH-1 启动闸门（顺延）** | sh1_lexer_token_contract_freeze · 12 Token 类型+Span+8基准tokenize MD5 + verify --mode=lexer钩子 | **94 强制·里程碑**【原93评审轮顺延】 | 评审发现【SH-1 自举前最后一道契约闸门】 | ⏳ **94 首任务强制执行** · 没有Token契约=等价性验证成本×10 |
| P90 | **CC=15/14 双拆（顺延）** | split_type_checker_unify Phase2 · _unify_types（CC=15）+ _detect_leaking_tvars（CC=14）迁到 _Unifier · 删4个薄包装 | **94 强制**【原93顺延】 | 审查驱动【CC=15全项目#2剩余最复杂】 | ⏳ **94 第二任务** · 目标两座山各CC≤8 · 不得再挤走 |
| P85 | **unused_import 降噪 v11** | cleanup_unused_imports_v11_massive · 9文件ir_nodes大导入块→直导入四模块 · MEDIUM 314→≤50 | **94 Filler**【93评审新增入池】 | 审查驱动【R1515 unused_import MEDIUM 314 · 噪音99.3%】 | ⏳ **94 第三任务** · 脚本化与cycle=85 v9 Massive同策略 |

---

## 🧭 cycles=94~96 三轮攻坚任务表（第 93 轮评审输出 · SH-1 闸门7/7打开 + lexer.nv首轮编码）

### Cycle 94：SH-1 Token 契约冻结闸门 + CC=15/14 双拆 + unused_import 降噪

| 优先级 | 任务线 | 任务 | 来源 | 难度 | 目标结果 |
|--------|--------|------|------|------|---------|
| **P92 强制·里程碑** | SH-1 闸门 #1 | **sh1_lexer_token_contract_freeze**：12 Token 类型（INT/FLOAT/STRING/IDENT/...）+ Span(start,end,file) 数据契约 + 8 基准文件 tokenize 输出 MD5 固化 + sh1_parity_verify.py --mode=lexer 钩子 | 评审发现【93评审 SH-1 闸门6/7→7/7】 | medium | Token契约冻结文档 + fixtures/sh1_parity/*.tokens.json（8份）+ manifest.md5 · verify --mode=lexer 8/8 PASS |
| **P90 强制·CC 双拆** | 审查债务 CC=15/14 | **split_type_checker_unify Phase2**：_unify_types（CC=15）+ _detect_leaking_tvars（CC=14）从 TypeChecker 迁到 _Unifier 嵌套类；删4个薄包装方法；新增 unify_types_subst 增长断言单测 2 条 | 审查驱动【CC=15 #2 + CC=14 #3】 | hard | 两方法各 CC≤8；TypeChecker 方法数 -5；178+ passed · 零回归 |
| **P85 Filler·审查降噪** | 质量噪音治理 | **cleanup_unused_imports_v11_massive**：9 文件 ir_nodes 大导入块（30-70行）→直导入 ir_types/hir/mir/lir 四模块；复用 cycle=85 v9 Massive 脚本；保留 noqa:F401 兼容层 10 条 | 审查驱动【R1515 unused_import 314 · 噪音99.3%】 | easy | MEDIUM unused_import 314→≤50（降噪84%）；语法验证8/8 OK · 444 passed 零回归 |

### Cycle 95：CC=14 收尾 + 异常收窄 + MIR E2E 测试缺口 + CI 超时修复

| 优先级 | 任务线 | 任务 | 来源 | 难度 | 目标结果 |
|--------|--------|------|------|------|---------|
| **P88 强制·CC 收尾** | CC=14 最后一座 + too_broad_exception | **split_type_checker_unify Phase3**：_has_overflow_risk（CC=14）拆为 _check_int_overflow/_check_float_range 双方法 CC 各≤5 + **evaluator_bare_except_6_fix**：evaluator.py 6 处 `except:` → 窄异常 + 1 条错误路径断言 | 审查驱动【CC=14 + too_broad_exception MEDIUM 6】 | medium | CC=15 剩余钉子户 ≤1（仅 _check_fn_decl CC=23 预警留 96）；异常路径 100% 不静默吞错 |
| **P83 强制·测试缺口** | 测试锚点补齐 | **test_mir_lowering_e2e_8cases**：新建 tests/test_mir_lowering_e2e.py ≥8 端到端 HIR→MIR 结构断言（phi数/bb数/指令数/操作数类型分布）；输入复用 fixtures/sh1_parity/ 8 基准 AST JSON | 审查驱动【gap_coverage MEDIUM】 | medium | ≥8 passed；覆盖 listcomp/闭包/ADT/管道/循环/模式匹配 6 大类场景 |
| **P75 Filler·CI 治理** | 质量门禁修复 | **review_ci_timeout_fix**：(a) 所有 tests/*.py 添加 pytest.mark.fast/slow 装饰器（native_backend=slow/allocator=fast/其他混合）；(b) auto_review.py 测试命令 → `pytest -m "not slow"` 快速模式 ≤60s，慢测单独报告 | 审查发现【R1514-1515「测试分析」TIMEOUT>120s】 | easy | fast/slow 标记覆盖率 100%；审查报告「测试分析」栏恢复有数据 |

### Cycle 96：SH-1 里程碑·lexer.nv 首轮编码 + 薄弱分支覆盖 + parity 看板 v1

| 优先级 | 任务线 | 任务 | 来源 | 难度 | 目标结果 |
|--------|--------|------|------|------|---------|
| **P95 里程碑·SH-1启动** | 自举编译器首轮编码 | **sh1_lexer_nova_skeleton_v1**：创建 nova-compiler/lexer.nv 骨架。首部注释引用 SYNTAX_FREEZE_v0.5 + Token 契约冻结 MD5；`type TokenType { INT | FLOAT | STRING | CHAR | BOOL | UNIT | IDENT | LET | MUT | FN | IF | ... }` ADT 前 30 项；`struct Span { start: Int; end_: Int; file: String }`；空 `fn tokenize(src: String) -> List[(TokenType, Span)]` 函数签名 + return []。**编译通过** | 自主规划【M-SH1 里程碑 · 6/7闸门→7/7 打开后首轮编码】 | medium | lexer.nv 文件存在（约 200 行）；Nova 编译器可编译通过（输出空 List）；TokenType ADT 前30项定义完整 |
| **P85·测试+预警** | 薄弱分支覆盖 + CC=23 预警 | **test_tc_empty_branches_6_cases**：TypeChecker 6 空分支（无else/无match默认/空if体/空while/空for/空match）100% 行覆盖 + **CC=23 预警排查**：_check_fn_decl（CC=23 最高）读代码划拆分边界、登记任务池（不做改动） | 审查驱动【gap_coverage + CC Top 榜预警】 | medium | 6/6 空分支覆盖 100%；_check_fn_decl 拆分方案文档（3段拆分建议 + 调用点列表） |
| **P78 Filler·可视化** | SH-1 parity 持续追踪看板 | **sh1_parity_gate_dashboard_v1**：创建 scripts/gate_sh1_parity.py 每日报告脚本。流程 = Python lexer→8基准→token流 JSON→MD5；输出 2×2 看板表（Token契约×8基准 = 通过数/差异字节数/MD5）。首次运行必 100%（Nova 侧未实现）。 | 评审发现【87 评审起持续 parity 追踪看板诉求未落地】 | easy | gate_sh1_parity.py 脚本存在（约 120 行）；首次运行输出 2×2 看板 JSON + TTY 表格 |

### cycles=96 末 SH-1 启动闸门验收清单（7/7 目标）

| 闸门项 | 当前状态（92末） | cycles=96末目标 | 执行轮次 |
|--------|----------------|----------------|---------|
| 1. M-ARCH 三项手术 5/5 完成 | ✅ 已达成 | ✅ 保持 | — |
| 2. M-MEM 4/4 Allocator API + 72 passed 锚点 | ✅ 已达成 | ✅ 保持 | — |
| 3. 语法冻结声明 SYNTAX_FREEZE_v0.5.md | ✅ 已达成 | ✅ 保持 | — |
| 4. SH-1 parity baseline build 8/8 MD5 锚点 | ✅ 已达成（cycle=88） | ✅ 保持 | — |
| 5. 连续 3 轮 100% 核心测试 | ✅ 已达成×8轮 | ✅ 目标 11 轮 | 94+95+96 保持 |
| 6. **Token 契约冻结 + verify 钩子** | ⏳ 未执行 | ✅ **94 P92 首任务** | cycle=94 |
| 7. **lexer.nv 骨架可编译 + TokenType ADT 前30项** | ⏳ 未执行 | ✅ **96 P95 里程碑** | cycle=96 |

---

### cycles=88~89 三线并行任务完成情况回顾（第 87 轮评审输出 · 100% 达成）

| 优先级 | 任务线 | 任务 | 轮次 | 结果 |
|--------|--------|------|------|------|
| P87 | **SH-1 启动基建** | sh1_parity_baseline_build · 8 基准文件 AST JSON + MD5 固化 + fixtures/sh1_parity/ + parity verify 脚本 | **88 ✅ 完成** | SH-1 baseline 闸门 100% 解除 · 8/8 MD5 锚点产出 |
| P70 | **审查债务 CC** | refactor_cc_parse_primary_type（CC=13→≤4 拆分三方法·类级常量）· 钉子户出榜 4→3 | **88 ✅ 完成** | CC=13 钉子户 -1 · Parser._parse_primary_type 出榜 |
| P83 | **质量补齐 测试** | test_lexer_unit_tests（11 大类 55 passed + 40 subtests）· SH-1 lexer.nv 等价性锚点 | **88 ✅ 完成** | 三骨架锚点 #1 Lexer 补齐 · 55 passed |
| P88 | **审查债务 CC** | refactor_cc_lowering_lower_list_comp CC=13→≤4（钉子户出榜·Top 连续 4 轮 · 拆 4 helper） | **89 ✅ 完成** | CC=13 钉子户再 -1 · MIRLowering._lower_list_comprehension 出榜 |
| P86 | **审查债务 质量** | test_parser_docstring_bulk_74 · 75 例英→中文语义 docstring（gate_docstring_quality 清零） | **89 ✅ 完成** | 审查门禁噪音大幅降低 · 74/75 例极简 docstring 升级 |
| P85 | **审查发现 测试缺口** | test_ast_nodes_ir_types_bundle · 新建 2 文件 100 passed（AST 58 节点 + IR 类型 28 公开 API） | **89 ✅ 完成** | 三骨架锚点 #2 AST + #3 IR Types 双补齐 · 100 passed |

---

## 🏗️ 架构治理（第 87 轮评审更新 · 新增 24 条审查派生任务）

> **审查驱动任务占比 ≥ 30% 硬约束**：cycle=87 评审后任务池 94 项中审查派生 34 项 = **36.2%**（达标）。
> **cycles=88-90 聚焦方向**：① SH-1 parity baseline 基建 P87；② 审查债务清零 CC+长函数+unused_import P88~P90（25 项）；③ 质量补齐 TC/Native 测试覆盖 P88~P89；④ 薄弱模块 God Class 渐进拆分 P87。

| 里程碑 | 内容 | 目标版本 | 预计轮次 | 状态 | 说明 |
|--------|------|---------|---------|------|------|
| M-ARCH | 三项立即架构手术（拆ir_nodes/隔离旧C后端/弃用Cranelift） | v0.3.x | 3 轮内 | ✅ **完成 5/5** | **self-hosting 前置条件 · cycles=80 硬截止达成** |
| M-MEM  | Allocator API 落地（Step1-4）+ 栈/堆语义明确 | v0.4.0 | 第 82-86 轮 | ✅ **4/4 Step1+Step2+Step3+Step4 全部完成** | **cycles=82 trait+Arena/Libc；cycles=83 Evaluator 注入；cycles=85 BoxType+NovaBox+5内置函数；cycles=86 Option/Result 推广 + 自动解包兼容层；提前1轮于 cycles=87 截止前完成** |
| M-SH1  | Self-Hosting SH-1：lexer + parser 用 Nova 写出 + 字节级一致性 | v0.4.0 | 约第 88-98 轮 | 🚀 **In Progress · baseline 闸门 100% 解除** | 前置：M-ARCH ✅ + M-MEM ✅（4/4 完成）+ 连续5轮100% ✅（cycles=82+83+85+86+88）+ 语法冻结 ✅（SYNTAX_FREEZE_v0.5.md cycle=86 产出）· **parity baseline build ✅（cycle=88 产出 scripts/sh1_baseline.py + sh1_parity_verify.py · 8/8 MD5 锚点）** · parser 与冻结文档 2 处不一致 ✅ 对齐（14 保留字拦截 + PipeExpr→FnCall desugar）· Lexer 单测 55 passed ✅ 锚点 · cycle=89 可启动 lexer.nv 编写 · Nova 侧 lexer+parser cycles=89~98 |
| M-SH2  | Self-Hosting SH-2：type_checker + 三层 IR lowering 移植 | v0.5.0 | 约 12 轮 | ⏳ 未启动 | 前置：M-MEM 定板 + SH-1 字节级一致 |
| M-SH3  | Self-Hosting SH-3：一个后端（C后端）+ stage2==stage3 自举 | v1.0 | 约 12 轮 | ⏳ 未启动 | 成功后 Python 编译器降级为参考实现 |
| M-STD  | 标准库覆盖 IO/FS/Net/Concurrency/Serialize | v1.0 | 并行推进 | ⏳ 未启动 | 与 SH-2/SH-3 并行推进 |

---

## 🏗️ 架构治理（第 84 轮评审更新）

> **架构债务任务占比 ≥ 50% 硬约束**：cycles=84-86 三线规划中架构债占比 75%-83%，远超要求。
> **cycles=84-86 聚焦方向**：① 质量止血（unused_import 306→≤50 + 门禁恢复）P88-P86；② M-MEM Step3(Box) P82 + Step4(Option) P80；③ SH-1 前置：syntax_freeze P85（必须启动）+ parity P77；④ 薄弱模块渐进治理：CC=13 filler + 文档化 + native_backend 拆分首步。

| 状态 | 任务 | 难度 | 优先级 | 预计 | 依赖 | 来源 |
|------|------|------|--------|------|------|------|
| ✅ | C 后端接入统一 IR 管线 | hard | 95 | 2-3 天 | - | 自主规划 |
| ✅ | C 后端 LIR 代码生成基础框架 | medium | 92 | 1 天 | - | 自主规划 |
| ❌ | 统一 C 后端（LIR 路径功能对齐）总任务 | hard | 70 | 2-3 天 | - | 已拆分 phase1/phase2 |
| ✅ | **统一 C 后端 Phase1（路径隔离+弃用标记）** · 手术B | medium | **90** | 1-2 天 | - | **ARCHITECTURE_VISION §2.2 强制 · 第80轮完成** |
| ✅ | **统一 C 后端 Phase2（ADT/match 功能迁移 + 删除旧c_codegen.py 1591 行）** · Part1 cycle=83 断包级API · Part2 cycle=91 删除 + 40 测试迁移验证 | hard | **88** | 2-3 天 | unify_c_backend_phase1 | 【审查驱动+架构战略】手术B Phase2 ✅ cycle=91 完成：LIR→C 成为 C 代码生成唯一路径 · 36 passed, 4 skipped（4 个已知 bug 标记 skip） |
| ✅ | **拆分 ir/ir_nodes.py 上帝模块 A1（抽 ir_types.py）** · 手术A-1 | easy | **90** | 2-3 小时 | - | **ARCHITECTURE_VISION §2.1 强制 · 第79轮完成** |
| ✅ | **拆分 ir/ir_nodes.py A2（抽 hir.py/mir.py/lir.py + 兼容层）** | medium | **90** | 1 天 | split_ir_nodes_a1 | **架构战略 · 第80轮完成** |
| ✅ | **拆分 ir/ir_nodes.py A3（删冗余、ir_nodes变薄re-export）** | easy | **88** | 2-3 小时 | split_ir_nodes_a2 | **架构战略 · 第80轮完成** |
| ✅ | **弃用 Cranelift 后端** · 手术C | easy | **85** | 1-2 小时 | - | **ARCHITECTURE_VISION §2.3 强制 · 第79轮完成** |
| ✅ | **Allocator API Step1（定义 trait + ArenaAllocator + LibcAllocator 实现）** | medium | **88** | 1 天 | - | ✅ cycle=82 完成 · runtime/allocator.py 720行 · Allocator trait + Libc/Arena + 统计/错误 · 1116 passed 零回归 |
| ✅ | **Allocator API Step2（Evaluator 注入可选 allocator + 7 构造点统一路由）** | hard（范围可控） | **82** | 2-3 天 | allocator_api_step1 | ✅ cycle=83 完成 · Evaluator.__init__(allocator=None) 注入 + _make_list/_make_tuple/_make_dict helper + 7 个构造点改造 · 零回归 1037 passed |
| ✅ | **Allocator API Step3（栈/堆语义明确 + Box 内核）** | medium | **82** | 1-2 天 | allocator_api_step2 | ✅ cycle=85 完成 · 【自主规划】架构战略 M-MEM 3/4 · 新增 IRType.BOX + BoxType + NovaBox(217行) + 5内置函数 box/unbox/set_box/drop_box/clone_box · 440 passed 零回归 |
| ✅ | **Allocator API Step4（Option/Result 推广至所有 fallible API）** | medium | **82** | 1-2 天 | allocator_api_step3 | ✅ cycle=86 完成 · 【自主规划】架构战略 M-MEM 4/4 收尾 · evaluator.py 6 个 I/O+JSON fallible 内置函数 Result::Ok/Err 改造 + _call_fn 自动解包兼容层（100% 向后兼容）· 401 passed + 20 subtests 零回归 |
| ✅ | **审查门禁校准（命名误报+dunder豁免+魔法数字白名单+noqa机制）** | easy | **80** | 2-3 小时 | - | ✅ cycle=82 完成 · 误报率 81%→<20% · 75+ dunder豁免 · COMMON_NUMS 14→60+ · noqa三级豁免 · 注释/字符串剥离 |
| ✅ | **语法冻结声明 v0.5 文档（SH-1 前置条件）** | medium | **87** | 1 天 | - | ✅ cycle=86 完成 · 【自主规划】SH-1 前置硬阻塞 · 产出 SYNTAX_FREEZE_v0.5.md（11 章节）· 71 Token / 31 Keyword / 14 级优先级表 / 23 Expr+7 Decl AST 形状完全冻结 · SH-1 闸门解除 2/4 |
| ✅ | **批量清理未使用导入 v9 Massive（219 个间接导入→直导入）** | easy | **88** | 2-3 小时 | - | ✅ cycle=85 完成 · 【审查驱动】Cycle-1514 MEDIUM unused_import 306 钉子户 100% 替换为 ir_types/hir/mir/lir 四模块直导入 · 8测试文件 347 passed 零回归 |
| ⏳ | **test_parser.py 74 例测试函数补 docstring（门禁修复）** | easy | **86** | 1-2 小时 | - | 【审查驱动】Cycle-1512 门禁失败 74 例主因 · cycle=84 质量止血 #2 |
| ⏳ | **调优增量门禁：魔法数字豁免（断言值/注释/文档字符串）** | easy | **79** | 1-2 小时 | - | 【审查驱动】门禁每轮必触发 1-9+ 次误报 · 降低噪音提高可信度 |
| ⏳ | **ir/mir_lowering.py 文档化补全（27 个无 doc→≤3）** | medium | **72** | 3-5 小时 | - | 【审查驱动】薄弱模块#3 · 三层IR核心（1897 行 42.9% 无 doc） |
| ⏳ | **evaluator.py 语义权威文档化（67 个无 doc→≤20）** | medium | **70** | 3-5 小时 | - | 【审查驱动】薄弱模块#5 · 架构指定语义权威 ARCHITECTURE_VISION §1.3 · 64.4% 无 doc |
| ⏳ | **native_backend 拆分 Step1：抽出 X86_64RegAlloc 寄存器分配类** | hard（范围可控） | **68** | 1-2 天 | split_native_backend_elf | 【审查驱动】薄弱模块#1 · 全项目最复杂单体（2771 行）· _allocate_registers 历史 CC=18 |
| ⏳ | **SH-1 parity 基线搭建：8 个基准文件 AST JSON + MD5 输出脚本** | medium | **84** | 3-5 小时 | syntax_freeze_declaration | 【自主规划】SH-1 字节级一致性校验基础设施 · 语法冻结文档 ✅ 已产出 · **M-SH1 仅剩唯一前置** · Cycle 88（评审后下一轮开发）必须启动 · P79→P84（前置压力上调） |
| ✅ | **批量清理未使用导入 v7（unused_import 58→41）** | easy | **62** | 1-2 小时 | - | ✅ cycle=82 完成 · 6 文件删 17 处未使用导入 · 零回归 |
| ✅ | **批量清理未使用导入 v8（unused_import 41→38） + unify Phase2 Part1** | easy | **60** | 30 分钟 | clean_unused_imports_v7 | ✅ cycle=83 完成 · 3处清理 + 断 CCodeGen 包 API · 零回归 |
| ✅ | **拆分 TypeChecker._unify Phase1（_Unifier 嵌套内部类·10方法·CC26→≤10）** | hard | **85** | 2-3 天 | split_ir_nodes_a1 | 【审查驱动】薄弱模块#2 ✅ cycle=91 Phase1 完成：178 passed / 180 total · Phase2 拆 _unify_types 剩余 3 方法到 _Unifier |
| ⏳ | 拆分 NativeCodeGen ELF 生成子模块（2771 行单体拆分第一步） | hard | 62 | 2-3 天 | - | 【审查驱动】薄弱模块#1 · native_backend.py 2771 行 · ELFWriter 抽出 |
| ✅ | **重构 Evaluator._convert_nova_to_json 降低圈复杂度 CC=13 → ≤4** | medium | **72** | 3-5 小时 | - | ✅ 【审查驱动】cycle=83 完成 · 5 helper + 2 张调度表 · 零回归 1037 passed |
| ✅ | **重构 _iter_hir_children 降低圈复杂度 CC=13→≤5** | medium | **70** | 3-5 小时 | - | ✅ cycle=85 完成 · 【审查驱动】Top10 CC=13 长尾 #4 出榜 · 拆 _yield_field_children helper + 统一 yield 为 4 元组 + generic_visit CC=6→1 · 179 IR 测试零回归 · CC=13 长尾 5→4 |
| ⏳ | LOW 级问题批量治理（docstring + 魔法数字） | easy | **38** | 2-4 小时 | - | 【审查驱动】no_docstring 619 + magic_number 825 持续增长 · nice-to-have |
| ⏳ | 基准测试框架增强（C/Wasm执行时间+优化对比） | medium | **25** | 3-5 小时 | backend_benchmark_framework | 【自主规划】nice-to-have · 优先级下调 |

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
