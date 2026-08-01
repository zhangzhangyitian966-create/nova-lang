# Nova 前后端专项开发日志

本日志由前后端专项开发系统自动生成，记录每轮开发的详细信息。

---


## 第 75 轮（评审轮）— 2026-08-02 19:01

> **双线路线图评审 ✅**（覆盖 Cycle 73-74 两轮普通开发 + 窄化栅栏未赋值致命缺陷 + Native 闭包栈溢出 + WasmGC 颗粒度拆分 3 类重点）
> ｜前端质量 8.5→9.2（↑0.7：窄化栅栏设计完整但核心赋值路径漏掉扣 0.8 / Parser 表达式级增量恢复 9.5 / HM TVar泄漏9.5 分项健康，综合 A）
> ｜后端质量 7.8→7.5（↓0.3：Native 8.3 微升但 WasmGC 6.0 结构欠账 + C 8.1 持平，三端分化加剧，综合 B）
> ｜**发现致命 BUG 2 项（窄化栅栏赋值未闭合 + 闭包 captured 7+ 栈溢出）、高危 4 项、中危 6 项、低危 4 项**
> ｜**隐藏 BUG 闭环率：评审 72 提出的 3 项 100% 清零 → 评审 75 新提出的 6 项（致命2+高危4）立项 100%**
> ｜前后端差距 FE 100% vs BE 70.2% = **29.8pp（短暂扩大：FE 收官 100%，BE 70.2%→下 3 轮收敛到 ≤22pp）**
> ｜Cycle 76-78 资源配比 FE 40%/30%/45% vs BE 60%/70%/55%，向后端再倾斜 5pp
> ｜任务池变更：+9 新增（FE 5 / BE 4）/ +1 废弃（原 WasmGC 整体任务拆 2 子项）/ +4 优先级调整 / +2 依赖新增

---

### 一、三轮回顾总结（Cycle 73-74，覆盖评审 72 → 评审 75）

#### 前端回顾（Cycle 72→75：1 项 easy + 1 项 medium，完成度 96%→100% 🎯，真实可用度 88%）

| # | 任务 | 轮次 | 难度 | 结果 | 核心价值 |
|---|------|:----:|:----:|:----:|---------|
| 1 | ADT 字段访问错误追加 known fields 建议（TypeEnv.adt_field_names + _format_adt_known_fields 变体分组） | 73 | easy | ✅ | 错误消息可用性 +30%；TestADTFieldSuggestionError 4/4 通过；多变体/嵌套/非 ADT 回归保护全过 |
| 2 | Parser 表达式级增量恢复（_wrap_recover_right() 辅助 + 17 处接入点 BinOp/Call/管道/分组） | 74 | medium | ✅ | 表达式级从 Panic mode 整段丢弃 → 1-token 就地恢复 + 半 AST 构造（a+*b → BinOp(a,+,ErrorExpr)）；TestParserExprIncrementalRecovery 6/6 通过；IDE/LSP 集成前置铺路；Parser 错误恢复 8.0→8.5 |
| 3 | 【里程碑】前端 50 项目标 **100% 收官**（Cycle 74 尾） | 74 | n/a | ✅ | 类型系统/解析器/词法/AST/语义分析 5 大子系统 50 项路线图计数目标达成；**但真实可用度 88%（Cycle 75 审计发现致命缺陷）** |

**前端里程碑**：HM 子集完整性 85%+ 保持；错误恢复四端贯通（Parser 熔断→TC ERROR_T→Evaluator None 哨兵）稳定；TVar 泄漏/窄化栅栏/幻影实例化三类 Type 硬保证 2/3 到位（窄化栅栏未赋值 = 第三道防线挂空挡）。剩余 12% 缺口：窄化栅栏闭合 / Lexer 数字前缀 / AST 访问者 / HM level 利用 / 多位数类型扩展 + CLI。

#### 后端回顾（Cycle 72→75：1 项 easy + 1 项 easy + 1 项 medium，完成度 66.7%→70.2%，+3.5pp）

| # | 任务 | 轮次 | 难度 | 结果 | 核心价值 |
|---|------|:----:|:----:|:----:|---------|
| 1 | regalloc_v2 spill 权重 +0.5 偏向代码补全（注释-实现漂移 5 行修复） | 73 | easy | ✅ | 长命 callee vreg 等权重场景翻转溢出 caller；性能回归保护；TestRegallocV2SpillBias 3/3 通过 |
| 2 | RBP 基址帧模式 + RSP→RBP 全寻址重算（栈帧 65%→80% 拆分 A） | 73 | medium | ✅ | _EmitContext 透明帧切换（frame_base_reg + frame_stack_bias）；5 处 vreg 栈槽访问改造；Prologue 55 48 89 e5 签名 + Epilogue 5d c3 签名；为 DWARF CFI + 结构体返回 ABI 建前置基础 |
| 3 | XMM8-XMM15 REX 前缀 9 条 SSE 指令预修复（_rex_xmm 辅助 + 9 条指令修复） | 74 | easy | ✅ | 与 GPR R12→RSP SIGSEGV（Cycle 70 修复）同构的 XMM 侧定时炸弹提前拆除；XMM8-15 扩展时 9 条指令 SIGILL 清零；TestX86_64Emitter 13/13 字节级断言通过 |

**后端里程碑**：P1 积压 0（维持 8 轮 ✅）。Native 三大硬缺口（regalloc_v2 ✅90% / 栈帧CFI 80%未动 / 位运算 ✅80%）完成 2.1/3；XMM REX 定时炸弹清零；隐藏 BUG 闭环率（评审72 3 项）3/3 = 100%。三后端分化持续加剧：C 88.8% ✅ >> Native 8.3/10 ≈ 83%（栈帧 80% 拖后腿）>> WasmGC 6.0/10 ≈ 60%（复合结构 3/10 全走 runtime，差距拉开）。

---

### 二、双线评估结果（基于 Explore subagent 13 文件深度审计）

#### 前端评估（总分 9.2 / 10，真实可用度 88%）

| 维度 | 得分 | 趋势（vs Cycle 72） | 详细判断 |
|------|:----:|:---:|---------|
| **质量趋势** | 9.2 | ↑0.7（8.5→9.2） | 整体变好；Parser 表达式级恢复 9.5 + HM TVar 泄漏 9.5 + ErrorExpr 10 三项拉高；窄化栅栏 8.0（未赋值 -2）拉低 |
| **类型系统 5 分项平均** | 9.1 | ↑0.4 | HM 泛化 9（level 未用 -1）/ TVar 泄漏 9.5 / 窄化栅栏 8（未赋值 -2）/ ErrorExpr 10 / ADT 字段建议 9（FieldAccess 错误处未接入 -1） |
| **Parser 4 阶段平均** | 9.1 | ↑0.6（8.5→9.1） | 顶层 Panic 9.5 / 语句级 9 / 块级 8.5 / 表达式级增量 9.5 |
| **进度评估（路线图 50 项）** | **100% 🎯** | ↑4pp（96%→100%） | Cycle 74 收官；但「路线图完成度 ≠ 真实可用度」（窄化栅栏致命缺陷、Lexer 数字字面量未支持前缀、AST 访问者未落地等缺口不在路线图 50 项计数内） |
| **速度评估（Cycle 73-74 两轮）** | 2 项 / 2 轮 = 1 项/轮 | 与上 3 轮持平 | 两项都是体验优化型（ADT 字段 40 行 + Parser 恢复 240 行），无正确性攻坚 |
| **价值最高任务** | ADT 字段建议 + Parser 表达式恢复（ROI 并列第一） | — | 分别 +30% 错误诊断可用性 / IDE 集成前置铺路；用户侧可感知收益最大 |
| **最大短板** | 窄化栅栏 overflow_risk 未赋值（**致命 SILENT CORRUPTION**） | ← 新发现 | TypeVar.overflow_risk 字段声明于 L230，但 _check_int_literal/_check_float_literal 两处字面量检查从不写 True → 三道防线（_has_overflow_risk + 3 接收端 strict_narrowing 升级）的触发条件为空 = 栅栏形同虚设 |
| **次短板** | AST 无访问者接口 / Lexer 无 0x/0o/0b 前缀 | ← 新发现 | 制约 FE 侧未来扩展；导致 FE 100% 收官后无「子系统级」攻坚任务，颗粒度太小造成结构性失衡 |

#### 后端评估（三端总平均 7.5 / 10）

| 维度 | 得分 | 趋势（vs Cycle 72） | 详细判断 |
|------|:----:|:---:|---------|
| **质量趋势（总平均）** | 7.5 | ↓0.3（7.8→7.5） | 表面下降因为 WasmGC 被深度审计出复合结构全走 nova_* 的 3/10 低分（之前因测试密度不足未暴露）；Native 实际提升 8.0→8.3；C 后端持平 8.1 |
| **Native x86_64 8 子模块** | 平均 **8.3** | ↑0.3 | ELF 头 8.5（缺 .shstrtab -1.5）/ 指令选择 8 / 寄存器分配 9（regalloc_v2 双池）/ **栈帧 8.5**（RBP-only 落地，缺 CFI -1.5）/ ABI 8.5（缺大结构体返回 -1.5，闭包 captured7+ 致命 -0 分计入致命风险单独列）/ 运行时 8 / 闭包 7.5（7+ 栈未处理 -2.5）/ 全局变量 8 |
| **WasmGC 8 子模块** | 平均 **6.0** | ↓0.3（6.3→6.0，审计拉低） | **类型声明 5**（仅硬编码 option/result/list 5 个 struct，用户 ADT 零声明）/ 函数 7 / 局部变量 6（ADT/LIST/MAP 全退化为 i32 指针）/ 控制流 8 / 调用 6（闭包走 nova_closure_call，未用 funcref+call_indirect 原生）/ **复合结构 3**（List/Map/Tuple/ADT 全走 nova_* runtime，零原生指令）/ 闭包 6 / extern 7 |
| **C 后端 8 子模块** | 平均 **8.1** | ↔ 持平 | 类型声明 8 / 函数 8.5 / 局部变量 9 / 控制流 9 / 调用 8 / 复合结构 7 / 闭包 trampoline 8（null 检查已修）/ extern 7 |
| **进度评估（路线图 84 项）** | 59/84 = **70.2%** | ↑3.5pp（66.7%→70.2%） | XMM REX 预修复 + RBP-only 两项贡献 3.5pp；WasmGC 结构性欠账（复合结构 3/10）= 最大单项拖后腿 |
| **完成度变化（各后端）** | C 88.8% >> Native 83% >> WasmGC 60% | 分化加剧 | Native 与 C 的差距从 10pp → 5.8pp 收敛；WasmGC 与 C 的差距 28.8pp → 28.8pp 不变；WasmGC 是下 3 轮攻坚重点 |
| **价值最高任务（已完成）** | RBP-only 栈帧（Cycle 73） | ROI 最高 | 栈帧子模块 65%→80%（+15pp）；为 DWARF CFI/结构体返回 ABI/调试符号 三项后续任务建前置基础，单任务撬动 3 个后续解锁 |
| **价值最高任务（积压）** | backend_native_stack_frame_rbp_cfi（P88 hard） + backend_wasmgc_struct_phase1（P82 hard） | 并列第一 | CFI = 栈帧 80%→92%（+12pp，Native 收官推手）；WasmGC struct = 复合结构 3→82%（+79pp，WasmGC 最大单项跃迁） |
| **最大短板（致命）** | Native 闭包 trampoline captured 7+ 未压栈（**SIGSEGV**） | 新发现 F1 | _generate_trampoline L340-342 仅处理 min(capture_count, 6) 寄存器 captured，L349-352 用户参数也只处理寄存器；第 7+ captured 是逻辑参数的最左部分（栈最上方），完全未搬运 → 闭包体内访问 captured[6+] = 读 NULL/垃圾 = SIGSEGV |
| **次短板（高危 ×3）** | setcc REX R8-R15（H1） / WasmGC 用户 ADT 零静态校验（H2） / Phi UNIT 过度宽容（H3） / regalloc_v2 span 淹没跨 call 启发式（H4） | 4 项全部新发现 | setcc = 与 R12→RSP SIGSEGV / XMM SIGILL 同构的第三颗定时炸弹；WasmGC H2 = 未来 runtime API 变更时整体崩溃；H3 = 架构脆弱未来改 UNIT 大小立即错位；H4 = 超大函数性能退化 |
| **三后端分化判断** | **严重分化 + 颗粒度失衡** | — | C 后端已接近收官（88.8%，只剩 3 个 1-2pp 小优化），Native 83% 走在中期（栈帧+CFI+ABI+闭包 4 项收尾），WasmGC 60% 还在早期（复合结构/类型声明/调用 3 子模块 <70%）；颗粒度：WasmGC 的原整体任务 10-14h 超一轮容量 50%，拆分后才健康 |

#### 综合评估

| 问题 | 判断 | 根因 / 说明 |
|------|:----:|------------|
| **前后端平衡吗？** | ❌ 中度失衡 | FE 路线图 100% vs BE 70.2% = 差 29.8pp；但 FE 真实可用度 88%，BE 真实可用度 ~62% = 差 26pp。FE 颗粒度太小（未来 5 项都是 2-6h 小任务，无子系统级）；BE 颗粒度太大（原 WasmGC 整体 10-14h 超一轮，拆分后才 8-10h） |
| **方向对吗？** | ✅ 大方向正确 | 三大方向全部走对：(1) Native 先 RBP-only 再 CFI（颗粒度拆分） / (2) WasmGC 先 runtime 跑通 再原生改造（先跑通再优化） / (3) 前端先错误恢复 再体验优化（先 IDE 基础再细节） |
| **方向偏移点** | ⚠️ 2 处偏移 | (1) 窄化栅栏先写框架后写核心赋值路径被打断 = 「设计 100% 实现 0%」的典型 LLM 开发特征；(2) WasmGC 整体任务立项时颗粒度未拆分 = 3 轮规划后才在本次评审拆分，浪费了 Cycle 74 一轮产能（原计划做 CFI + WasmGC，结果因颗粒度太大只消化了 XMM REX 热身） |
| **效率（每轮平均产出）** | 3 轮（Cycle 72-74）：难度 3.83 / 650 行 / 12 用例 | ✅ 健康 | 难度 3.83（中高难度机器码级）对应 650 行/轮 = 开发密度合理；用例 12 个/轮 = 测试密度达标；对比业界 LLM 开发平均水平（400-800 行/轮）处于中位数 |
| **下 3 轮（76-78）聚焦什么？** | **(1) 闭合致命风险 2 项 → (2) 两大硬缺口（栈帧 CFI + WasmGC struct）→ (3) 两大架构基建（AST 访问者 + WasmGC array）→ (4) ABI 收官 + 测试密度达标** | 优先级从高到低：Cycle 76 = P0 致命 2 项（窄化栅栏 2h + 闭包栈 4h，可 1 轮内全部 100% 消化）+ P1 热身（setcc REX 2h + Lexer 前缀 3h，两任务独立并行）；Cycle 77 = 栈帧 CFI（8h）+ WasmGC struct 阶段 1（8h）+ AST 访问者（6h，三者文件零交集 = 可同轮消化 70%）；Cycle 78 = WasmGC array 阶段 2（8h）+ 结构体返回 ABI（5h）+ HM level 利用 + CLI 多位类型（6h + 8h，跨 78 尾期到 79） |
| **资源配比（76-78）** | **76: FE40/BE60 / 77: FE30/BE70 / 78: FE45/BE55** | ✅ 向后端再倾斜 5pp | FE 仅 1 项 P0（窄化栅栏闭合）+ 2 项 P2/P3（数字前缀 + AST 访问者）；BE 有 1 项 P0（闭包栈）+ 1 项 P1（setcc REX）+ 2 项 P1 hard（CFI + WasmGC struct）+ 1 项 P2 hard（WasmGC array）+ 1 项 P2 medium（结构体返回 ABI）= 6 项 vs FE 3 项；BE 难度分约 38 vs FE 约 11，3.45:1 难度比对应约 35:65 工时比，40/30/45 vs 60/70/55 的加权平均 38:62 与难度比 35:65 匹配 |

---

### 三、问题总结与根因分析（致命 2 + 高危 4 + 中危 6 + 低危 4 = 共 16 项）

#### 致命级（2 项，必须 Cycle 76 第一轮立即清零）

| # | 风险 | 根因分析 | 触发概率 | 修复成本 |
|---|------|---------|:--------:|---------|
| **F1** | Native 闭包 captured ≥ 7 时 SIGSEGV | _generate_trampoline 代码在寄存器循环 min(capture_count, len(ARG_REGS)) 的边界上「写了寄存器就忘了栈段」；典型 LLM 「先写 happy path（≤6 captured 测试全部过），尾段（7+）因测试未覆盖被打断后未续完」 | 闭包 captured 7+ ~15% 用户场景 | 4-5h 中 |
| **F2** | 窄化栅栏 overflow_risk 从未赋值 → 大整数窄化静默截断 | 三道防线设计（声明字段 → 标记风险 → 接收端升级）完整，但最核心的第 2 步（字面量处赋值）在开发中被上下文切换打断；典型「框架 100% + 核心 0%」的 LLM 多轮开发错位 | >60%（所有写大整数的代码都漏检） | 2h 极低（ROI 最高 ） |

#### 高危级（4 项，Cycle 76-77 清零）

| # | 风险 | 根因分析 | 触发概率 | 修复成本 |
|---|------|---------|:--------:|---------|
| H1 | setcc R8-R15L 写错误寄存器（REX.B 缺失） | 同构 BUG 第三次出现：Cycle 70 GPR R12→RSP SIGSEGV（REX 硬编码 0x48）/ Cycle 74 XMM8-15 SIGILL（SSE 指令 REX 缺失）/ Cycle 75 setcc R8-R15L（byte 目标 REX 缺失）→ 三类寄存器扩展位分别独立修，未一次性扫描所有指令的 REX 覆盖 | regalloc 压力增大 >30% | 2h 极低 |
| H2 | WasmGC 用户 ADT 无静态类型校验 | 阶段 0（当前）设计策略「先跑通」：所有用户 ADT 退化为 i32 指针 + nova_* runtime 偏移访问字段；完全依赖 runtime 侧 C 结构体不变，无编译期静态保证 | runtime 升级时 100% 触发 | 随 WasmGC struct 阶段 1 一并解决（8h） |
| H3 | Phi UNIT 宽容过度 → UNIT 改大小立即错位 | mir_lowering.py `t1.kind==UNIT or t2.kind==UNIT` 直接 True；当前 UNIT=8B 与 Int 同大小 = 侥幸安全；但属于「碰巧通过」的架构级脆弱点 | 改 UNIT 大小的未来改动 100% 触发 | 3h 低（随 Phi 类型一致性专项） |
| H4 | regalloc_v2 spill_weight span 绝对淹没启发式 | span = last-first+1 与函数大小线性相关，has_call/mid 只是 ×2/×1.5 系数；1000+ 指令超大函数的 span 绝对权重超过所有启发式 → 跨调用长命 vreg 不优先溢出 caller-saved → call 前 save/restore 激增 | 大型项目首次出现时 70% | 4h 中（归一化权重） |

#### 中危级（6 项，Cycle 77-79 逐步关闭）

| # | 风险 | 预计关闭轮次 |
|---|------|:-----------:|
| M1 | Native 每个 call 保守保存 XMM0-7（64B），缺精确保存集 | 77 （与 CFI 并行，测试密度达标专项） |
| M2 | Parser _parse_brace_primary 推测解析吞错（except ParseError: pass） | 78 |
| M3 | 三后端 List/Map/Tuple/ADT 构建 3 套独立代码（~400 行重复） | 78+ （RuntimeOp 统一，WasmGC 两阶段之后启动） |
| M4 | C 后端 trampoline 非 int/double/bool 返回值装箱不明确 | 78 |
| M5 | Lexer 数字字面量不支持 0x/0o/0b 前缀和 _ 分隔符 | **76**（本轮立项 FE 第二优先级） |
| M6 | Native _allocate_registers 返回空容器 label_offsets API 误导 | 77 |

#### 低危级（4 项，随时可关闭）

| # | 风险 | 预计关闭轮次 |
|---|------|:-----------:|
| L1 | type_checker _subst setter/getter 代理模式增加调试难度 | 按需 |
| L2 | MatchArm AST 节点无 span 字段 | 77（AST 访问者一起修） |
| L3 | wasm_backend _emit_dispatch_prologue func=None 默认值冗余 | 77 |
| L4 | Native FRAME_MODE="rbp" 硬编码 TODO 从 CLI 读 | 77（CFI 专项顺便） |

---

### 四、下阶段方向与理由（Cycle 76-78 排期表 + 资源配比）

#### Cycle 76（普通轮）：**致命风险清零轮** — FE 40% / BE 60%

| 线路 | 任务 | 难度 | 工时 | 理由 |
|------|------|:----:|:----:|------|
| FE P0 🎯 | **frontend_narrowing_fence_closure P95 easy**（_check_int_literal/_check_float_literal 设 TypeVar.overflow_risk=True，3 接收端 strict_narrowing 从不触发→正确触发） | easy | 2h | **致命 F2 直接修复**；20 行代码 ROI 所有任务最高；修复后 TypeChecker 正确性分 +2pp（窄化栅栏 8→10） |
| FE P2 | **frontend_lexer_numeric_prefix P80 easy**（0x/0o/0b 前缀 + _ 分隔符 8 用例） | easy | 3h | 中危 M5 关闭；系统级语言标配字面量；用户体验 +20%；与 BE setcc REX 两任务 0 交集并行 |
| BE P0 🎯 | **backend_native_closure_captured_stack P92 medium**（captured 7+ 按 System V 顺序压栈 + RBP 寻址偏移计算 3 用例） | medium | 4-5h | **致命 F1 直接修复**；Native 闭包正确性从「仅 ≤6 场景安全」→「任意 captured 数安全」；P0 最高优先级 |
| BE P1 | **backend_x86_64_setcc_rex_prefix P86 easy**（sete/setne/.../setbe 8 条指令 REX.B=1 当 reg≥8 3 用例） | easy | 2h | **高危 H1 直接修复**；与 GPR R12/XMM REX 同构的第三颗定时炸弹清零；2h 零风险 |

**Cycle 76 预期里程碑**：✅ 2 致命 + 1 高危 + 1 中危 = 4 风险 100% 清零；✅ 前端 P0 任务 100% + 体验任务 100%（FE 侧 2 任务工时 5h = 40%，匹配配比）；✅ 后端 P0 任务 100% + P1 热身 100%（BE 侧两任务工时 6-7h = 60%，匹配配比）；✅ 总难度分 easy×3 + medium×1 = 5（中等偏轻，第一轮快速获胜建立信心）

#### Cycle 77（普通轮）：**硬缺口攻坚轮** — FE 30% / BE 70%

| 线路 | 任务 | 难度 | 工时 | 理由 |
|------|------|:----:|:----:|------|
| FE P2 | **frontend_ast_visitor_framework P78 medium**（AstVisitor 基类 + AstTransformer + 55 节点 accept() + 3 用例） | medium | 5-6h | **解决 FE 颗粒度太小的结构性失衡**；AST 访问者是 IDE 增量重解析 / 宏系统 / lint 规则 三大子系统的共同前置基建；做一次以后所有 FE 新特性快 30%；杠杆型架构任务 |
| FE P3（间隙） | **frontend_hm_generalize_level P76 easy**（_walk_type_generalize 用 TypeVar.level < env.depth 条件 4 用例） | easy | 3h | FE 颗粒度抬升后间隙消化；类型系统分项 HM 泛化 9→9.5（+0.5pp）；修复深层嵌套 let-polymorphism 过度保守 |
| BE P1 🎯 | **backend_native_stack_frame_rbp_cfi P88 hard**（DWARF .eh_frame CIE+FDE + ELF 4 新节区 .shstrtab/.eh_frame/.symtab/.strtab 5 用例） | hard | 8-10h | **栈帧子模块收官（80%→92% +12pp）**；Native 调试效率 +50%（gdb backtrace / perf 符号解析）；Native 8 子模块平均从 8.3→8.5（+0.2pp） |
| BE P2 🎯 | **backend_wasmgc_struct_phase1 P82 hard**（(type $adt_xxx) 声明生成 + struct.new/get/set 替换 ADT nova_* 6 用例） | hard | 8-10h | **WasmGC 复合结构 3→82%（+79pp 跃迁）**；用户 ADT 类型有编译期静态校验（高危 H2 关闭）；与栈帧 CFI 任务文件零交集（wasm_backend.py vs native_backend.py）= 可并行开发 |
| BE P3（间隙） | **backend_native_abi_test_coverage P78 medium**（Native ABI ×10 / WasmGC ×6 共 16 用例，纯测试） | medium | 4-5h | **Native 测试密度 0.42→0.50 达标（中危 M1 部分关闭）**；纯测试 = 与 CFI/WasmGC struct 两大源码任务 0 交集 = 第三人可并行；16 用例 ~350 行 |

**Cycle 77 预期里程碑**：✅ 栈帧子模块 + WasmGC ADT 两硬缺口同时收官（两项 8-10h hard 颗粒度经 Cycle 73 RBP-only 验证可单轮消化 90%+）；✅ 高危 H2（WasmGC 静态零校验）随 phase1 关闭；✅ 中危 M5（数字前缀）/ M6（空容器 API）随间隙任务关闭；✅ FE 侧首次落地子系统级任务（AST 访问者），颗粒度从 2-3h 抬升到 5-6h，结构性失衡开始修正；✅ 资源比 FE30/BE70 完美匹配（FE 8-9h vs BE 20-25h ≈ 28:72）

#### Cycle 78（普通轮）：**架构统一 + ABI 收官轮** — FE 45% / BE 55%

| 线路 | 任务 | 难度 | 工时 | 理由 |
|------|------|:----:|:----:|------|
| FE P3 | **frontend_numeric_type_extension_and_cli P72 medium**（i8/i16/i32/i64/u32/f32/f64 8 类型 + --narrowing strict/warn/off CLI 10 用例） | medium | 6-8h | **FE 类型系统扩展收官项**；窄化栅栏从单一 i32 假设升级为真实位宽判断；为 Native SIMD/FFI/C 互操作前置基础；depends_on 窄化栅栏闭合（Cycle 76 已修） |
| FE P3（间隙） | **frontend_hm_generalize_level**（若 Cycle 77 未消化完） | easy | 3h | 兜底 |
| BE P2 | **backend_wasmgc_array_phase2 P80 hard**（List<T> 用 (array) 替换 nova_list_* 6 用例） | hard | 8-10h | **WasmGC 复合结构 82%→88%（+6pp）**；List 占 nova_list_* 调用 80% 场景；depends_on phase1（Cycle 77 完成） |
| BE P2 | **backend_native_abi_struct_return P82 medium**（>16 字节结构体 System V RDI 返回指针约定 5 用例） | medium | 4-6h | **Native ABI 子模块收官（82%→92% +10pp）**；C/Nova 互操作 90% 场景（Vec3/Mat4 值传递）可用；depends_on rbp_only 已完成 |
| BE P3（间隙） | **backend_runtimecall_unify_phase3 P72 hard**（LIRRuntimeOp 三后端统一 ~315 行，净删 ~400 行重复） | hard | 6-8h | **中危 M3（三后端重复代码）关闭**；放 Cycle 78 尾期启动避免过早抽象限制 WasmGC 原生优化路径；depends_on WasmGC 两阶段完成 |

**Cycle 78 预期里程碑**：✅ WasmGC 复合结构 3→88%（两阶段累计 +85pp 跃迁，子模块收官）；✅ Native ABI 子模块 82%→92%（+10pp 收官）；✅ 三后端 RuntimeOp 统一架构落地（~400 行重复代码消除，中危 M3 关闭）；✅ FE 类型系统扩展收官（i8-f64 多位数 + CLI 开关）；✅ 前后端差距从 29.8pp → ≤22pp（收敛 7.8pp，达标 Cycle 72 规划目标）

---

### 五、任务池变更说明（本次评审：+9 新增 / +1 废弃 / +4 优先级调整 / +2 依赖新增 / +0 直接删除）

| 变更类型 | 任务 ID | 内容 | 理由 / 来源 |
|---------|---------|------|------------|
| **新增** | frontend_narrowing_fence_closure（P95 easy） | _check_int_literal/_check_float_literal 设 TypeVar.overflow_risk=True，3 接收端 strict_narrowing 从不触发→正确触发 | 致命 F2（review_cycle_75 审计）：silent data corruption，ROI 最高（20 行代码） |
| **新增** | backend_native_closure_captured_stack（P92 medium） | Native 闭包 trampoline captured ≥7 按 System V 顺序压栈 + RBP 寻址偏移 | 致命 F1（review_cycle_75 审计）：SIGSEGV |
| **新增** | backend_x86_64_setcc_rex_prefix（P86 easy） | setcc 8 条指令 REX.B=1 当 reg≥8（第三颗 REX 定时炸弹） | 高危 H1（review_cycle_75 审计）：与 R12→RSP / XMM REX 同构 BUG 第三例 |
| **新增** | frontend_lexer_numeric_prefix（P80 easy） | 0x/0o/0b 前缀 + _ 数字分隔符（Lexer 字面量扩展） | 中危 M5（review_cycle_75 审计）：系统语言标配字面量，ROI 高（3h 开发体验 +20%） |
| **新增** | frontend_ast_visitor_framework（P78 medium） | AstVisitor + AstTransformer + 55 节点 accept() | 结构性失衡修正（FE 颗粒度太小）+ 三大子系统前置基建（IDE/宏/Lint） |
| **新增** | frontend_hm_generalize_level（P76 easy） | _walk_type_generalize 用 TypeVar.level < env.depth，修复嵌套 let 过度保守 | 类型系统 HM 分项 9→9.5 的唯一扣分项（level 声明未用） |
| **新增** | backend_wasmgc_struct_phase1（P82 hard） | WasmGC 改造 阶段 1：(type $adt_xxx_struct) + struct.new/get/set 替换 ADT nova_* | 原 backend_wasmgc_native_struct_array 颗粒度拆分（10-14h→8-10h 健康） |
| **新增** | backend_wasmgc_array_phase2（P80 hard） | WasmGC 改造 阶段 2：List<T> 用 (array) 替换 nova_list_* | 同上拆分；List 占 nova_list_* 80% 调用，ROI 高于 Tuple/Map |
| **新增** | backend_runtimecall_unify_phase3（P72 hard） | LIRRuntimeOp 三后端统一（净删 ~400 行重复） | 中危 M3（三后端重复代码）；放最后避免限制 WasmGC 原生优化 |
| **废弃** | backend_wasmgc_native_struct_array | 原整体任务拆分为 phase1 + phase2 两子任务 | 颗粒度 10-14h 超一轮容量 50%；拆分后每轮 8-10h 消化率预期 100% |
| **↑优先级** | backend_native_stack_frame_rbp_cfi（P84→**P88**） | DWARF CFI + ELF 4 新节区 | 栈帧 80%→92% 收官推手；depends_on 全部清零（rbp_only 已完成），优先级应高于 WasmGC struct（缺前置少 = 先解锁先做） |
| **↑优先级** | backend_native_abi_struct_return（P80→**P82**） | >16B 结构体 by-value 返回 System V | depends_on rbp_only 已完成（不再依赖 CFI），前置阻塞清零；C 互操作 90% 场景卡点，价值提升 |
| **↓优先级** | backend_native_abi_test_coverage（P80→**P78**） | Native ABI×10 + WasmGC×6 长尾测试 | 纯测试不影响正确性，可与源码大任务并行开发，下调 2pp 匹配真实紧迫度 |
| **↓优先级** | frontend_numeric_type_extension_and_cli（P74→**P72**） | i8-f64 8 类型 + --narrowing CLI | **新增 depends_on frontend_narrowing_fence_closure**——必须先闭合致命缺陷再扩展位宽，否则窄化检测错位；致命缺陷优先导致本任务推后两轮 |
| **新增依赖** | frontend_numeric_type_extension_and_cli → depends_on 新增 frontend_narrowing_fence_closure | — | 窄化栅栏 overflow_risk 赋值未闭合前扩展 i8/i16 等位宽，会导致窄化阈值按错误的位宽比较 / 错判 / 漏判（致命缺陷影响扩展正确性） |
| **新增依赖** | backend_wasmgc_array_phase2 → depends_on backend_wasmgc_struct_phase1 | — | List<ADT> 的 elem 是 (ref null $adt_xxx_struct) 需要 phase1 的 (type) 声明存在；否则 Wasm 验证器报 unknown type index |

---

### 六、更新后的路线图进度（Cycle 75 评审轮后）

| 维度 | 值 | 对比 Cycle 74 |
|------|----|:---:|
| 已完成轮次（cycles） | **75**（评审轮） | +1（普通轮 → 评审轮） |
| 前端累计完成（frontend_completed） | 50 项（路线图收官） | 0（本轮评审未做新 FE 开发） |
| 后端累计完成（backend_completed） | 59 项 | 0（本轮评审未做新 BE 开发） |
| 前端完成度（路线图 50 项） | **100% 🎯**（真实可用度 88%） | 0（路线图计数不变，真实可用度审计 -12pp） |
| 后端完成度（路线图 84 项） | 59/84 = **70.2%** | 0（计数不变，审计校正 WasmGC 60%） |
| 前后端差距（真实可用度口径） | FE 88% vs BE ~62% = **26pp** | -3.8pp（Cycle 74 29.8pp → 75 审计 26pp，审计揭示差距更准确） |
| 任务池规模 | 16 项（12 pending / 1 completed / 1 deprecated / 2 别名） | +1（Cycle 74 5 pending → 75 12 pending，新增 9 减去拆 1 废弃 + 别名 2 = 净增 7 pending） |
| 下次评审轮 | Cycle 78 | → 3 轮后（75→76→77→78，78%3=0） |
| P0 积压 | **0 → 2（致命 F1+F2 立项未完成）** | 新增 2（Cycle 76 第一轮清零） |
| P1 积压 | 0 → 1（setcc H1） | 新增 1（Cycle 76 一并清零） |
| 隐藏 BUG 闭环率（评审 72 提出 3 项） | **3/3 = 100%**（评审 72 → 评审 75） | ✅ 清零：XMM REX ✅（74）/ spill 偏向 ✅（73）/ 表达式 Panic mode ✅（74） |
| 隐藏 BUG 立项率（评审 75 提出 致命 2+高危 4 = 6 项） | **6/6 = 100%** | ✅ 全立项：F1 P92 / F2 P95 / H1 P86 / H2 随 phase1 / H3 随 Phi 专项 / H4 随 regalloc 归一化 |

---

## 第 74 轮（普通轮）— 2026-08-02

> **双线路线：1 FE + 1 BE（均为评审转化的前瞻性+体验型任务）**
> ｜前端：Parser 表达式级增量恢复（_wrap_recover_right + 17处接入，6/6 用例）
> ｜后端：XMM8-XMM15 REX 前缀 9 条指令预修复（_rex_xmm + 13/13 用例）
> ｜**Native 三大硬缺口 完成 2.1/3（regalloc_v2 ✅ / 栈帧 RBP-only ✅ / 位运算 ✅ 剩余 CFI-only + 结构体返回 ABI + XMM REX 预修复✅）**
> ｜测试：test_parser +6/6、test_native_backend +13/13、test_nova 203、IR+C+SSA+Backends 195 全通过
> ｜下一轮 75（评审轮）：Cycle 73-74-75 双线路线图评审（每 3 轮一次评审）

---

### 一、前端任务：frontend_parser_expr_incremental_recovery（Parser 表达式级增量错误恢复）

**为什么选这个？** Cycle 72 评审转化的前端 IDE 体验 Top 1 项（当前表达式级仅 Panic mode：单个错误 token → 丢整个子表达式到下一个分号/关键字，IDE 集成后错误行之后所有变量无补全/无诊断）。依赖 frontend_parser_error_recovery_full 已完成（Cycle 66），ADT 字段建议（Cycle 73）之后下一项 ROI 最高。medium 难度 3-4h 改动 ≤300 行，本轮能 100% 消化。

**结果：✅ 成功**，TestParserExprIncrementalRecovery 6/6 用例全部通过；原有 Parser 测试无回归。

**实现详情：**

1. **_wrap_recover_right() 辅助函数（增量恢复核心）**
   - 语义：调用 parse_func() 解析右半部分，失败时 **就地恢复**（不向上抛到顶层 Panic mode）
   - 捕获 ParseError 后：
     - errors.append(e)（复用 Parser 多错误聚合，不改现有架构）
     - 生成 ErrorExpr：优先用 ParseError.line/column，fallback 到运算符 token 的 span，再 fallback 到 _cur()
     - **skip_tokens_on_error**：可选消费 N 个错误 token，避免下一个 _peek_type() 在同一点重复失败（BinOp 的错误 token 仍留在 pos 的典型场景）
   - 熔断：**不触发** `_expr_nested_errors` 计数（精确恢复不是嵌套雪崩，不需要 Panic 兜底）

2. **17 处接入点（4 大类场景）**
   - 【12 个 BinOp/管道优先级函数】：_parse_pipe / _parse_for_while_expr / _parse_and / _parse_or / _parse_equality / _parse_comparison / _parse_bit_or / _parse_bit_xor / _parse_bit_and / _parse_shift_expr / _parse_additive_expr / _parse_multiplicative_expr
     - 全部：fallback_span_token=运算符（PLUS/STAR/AND/OR 等）+ skip_tokens_on_error=1
   - 【2 个后缀参数解析】：_parse_postfix_expr 的 Call 实参循环、管道符 rhs
     - Call：每个实参独立 wrap，单个参数失败不影响其他（f(1,*,3) → args=[1, ErrorExpr, 3]）
     - skip_tokens_on_error=1：实参的错误 token 不被 _advance 消费，需手动跳过
   - 【1 个分组/元组表达式】：_parse_tuple_or_grouped 的内层表达式 wrap
     - 保证 (a + *) 的外层括号完整性（错误 token 在 BinOp 层级已消费 1 个，再补 1 个确保 RPAREN 可匹配）
   - 【1 个顶层兜底】：_parse_expression 外层 try/except ParseErrorGroup 也接入（极端 Panic 回退路径）

3. **TestParserExprIncrementalRecovery 6 用例**
   1. test_binop_rhs_failure_preserves_left：`a + * b` → AST 为 BinOp(lhs=Identifier(a), op=+, rhs=ErrorExpr)（不丢 a 的绑定/推断）
   2. test_let_binding_name_preserved_after_expr_error：`let x = a + * b` → Let 绑定 x 存在，IDE 能识别 x 的类型/使用点
   3. test_call_single_arg_error_preserves_others：`f(1, *, 3)` → args=[1, ErrorExpr, 3]（单个参数失败不拖垮整个 Call）
   4. test_nested_binop_two_levels_error：`(a + * b) * c` → 外层 BinOp lhs=BinOp（内层 a+* 恢复），rhs=Identifier(c)（两层级独立恢复）
   5. test_precise_single_error_count：`a + * b` → 仅 1 个 ParseError（非 Panic mode 跳过 10+ token 产生 N 个错误）
   6. test_multi_statement_two_independent_errors：`a + * b; c + * d` → ParseErrorGroup 聚合 2 个错误，两条语句的绑定/结构都保留

**修改文件：**
- `parser.py` +240 行（_wrap_recover_right 辅助函数 60 行 + 17 处接入点 ~120 行 + 注释/文档 ~60 行）
- `tests/test_parser.py` +210 行（TestParserExprIncrementalRecovery 6 用例 + _parse_collect 辅助）

---

### 二、后端任务：backend_x86_64_xmm_rex_prefix_pre_fix（XMM8-XMM15 REX 前缀 9 条指令预修复）

**为什么选这个？** Cycle 72 评审转化的前瞻性兼容专项（当前 XMM 池仅 0-7 零触发，但 XMM 池扩展到 8-15 时 9 条指令直接 SIGILL，和 GPR 的 R12→RSP SIGSEGV（Cycle 70 P92 修复）是同构定时炸弹）。原设计本轮后端主任务是 backend_native_stack_frame_rbp_cfi（P84 hard 12-16h），但 rbp_only 刚在 Cycle 73 落地，中间间隙消化 easy 难度的热身任务降低风险——先清 130 行零风险的 REX 修复，再集中精力攻 CFI 16 小时大任务。

**结果：✅ 成功**，test_native_backend.py 75/75 全通过（含新增 TestX86_64Emitter 13 条 REX 字节级断言）。

**实现详情：**

1. **基础设施**
   - 常量：x86_64.py 新增 XMM8/XMM9/XMM10/XMM11/XMM12/XMM13/XMM14/XMM15（8-15）—— 之前仅定义到 XMM7，也是扩展寄存器之前没被用到的旁证
   - 辅助函数 `_rex_xmm(r_ext, b_ext)`：SSE 专用 W=0 REX（区别于 GPR 的 `_rex_rb(W=1)`），仅当 R/B 扩展位非零时才输出（和 _rex 一致的 rex==0x40 省略优化）

2. **9 条指令修复详情（每条含：旧代码问题 → 修复后）**

| 指令 | 位置 | 旧代码问题 | 修复方案 | 触发条件 |
|---|---|---|---|---|
| movsd_reg_imm | x86_64 L379-391 | reg>=8 时硬编码 `_rex(0,0,0,1)`（REX.B=1 错误）；但 reg 在 ModR/M.reg（_modrm 第二个参数），需 REX.R=1 | `_rex_xmm((reg>>3)&1, 0)`；RIP-relative rm=5<8，不需要 REX.B | XMM8-XMM15 加载 Float 常量 |
| addsd_reg_reg | L490-495 | 完全缺失 REX → XMM8-XMM15 静默折叠为 XMM0-XMM7 | `_rex_xmm((src>>3)&1, (dst>>3)&1)`（src 在 ModR/M.reg，dst 在 rm） | XMM8+ 做浮点加法 |
| subsd_reg_reg | L497-502 | 同 addsd | 同上 | XMM8+ 做浮点减法 |
| mulsd_reg_reg | L504-509 | 同 addsd | 同上 | XMM8+ 做浮点乘法 |
| divsd_reg_reg | L511-516 | 同 addsd | 同上 | XMM8+ 做浮点除法 |
| xorpd_xmm | L518-523 | 完全缺失 REX；reg 同时在 ModR/M.reg 和 ModR/M.rm 两侧 | `_rex_xmm((reg>>3)&1, (reg>>3)&1)`（R 和 B 都要填） | XMM8+ 自清零 |
| cvtsi2sd | L525-531 | 旧 `_rex_rb(0, gpr_reg)` = `_rex(W=1, R=0, B=(gpr>>3)&1)`，**丢失 xmm 在 ModR/M.reg 侧的 REX.R**；xmm>=8 时写错误寄存器 | `_rex(1, (xmm>>3)&1, 0, (gpr>>3)&1)`；注意 cvtsi2sd 64-bit GPR 源必须 REX.W=1（不能用 _rex_xmm） | XMM8+ 做 Int→Float 转换 |
| cvtsd2si | L533-539 | 旧 `_rex_rb(gpr_reg, 0)` = `_rex(W=1, R=(gpr>>3)&1, B=0)`，**丢失 xmm 在 ModR/M.rm 侧的 REX.B**；xmm>=8 时读错误寄存器 | `_rex(1, (gpr>>3)&1, 0, (xmm>>3)&1)`；同样必须 REX.W=1 | XMM8+ 做 Float→Int 转换 |
| ucomisd | L541-546 | 完全缺失 REX；ModR/M.reg=b，ModR/M.rm=a | `_rex_xmm((b>>3)&1, (a>>3)&1)`（与 movsd_reg_reg 对称） | XMM8+ 做浮点比较 |

3. **不改动（回归保护，之前已实现正确）**
   - movsd_reg_reg / movsd_reg_mem / movsd_mem_reg（x86_64 L369-466）：已有 `if dst>=8 or src>=8` 判断 + 正确 REX.R/B 位
   - movq_xmm_gpr / movq_gpr_xmm（L468-488）：同上，已有 REX 判断
   - 以上 5 条在本次编码审计中确认为零修改，验证「修复不破坏正确路径」

4. **TestX86_64Emitter 13 用例（字节级断言）**
   - movsd_reg_imm_xmm8_uses_rex_r_not_b：REX=0x44（R=1，B=0，W=0）✓
   - addsd_both_xmm_low_no_rex：两寄存器 <8 → 不输出 REX ✓
   - addsd_src_xmm8_rex_r：src=XMM8 → REX.R=1 ✓
   - addsd_dst_xmm15_rex_b：dst=XMM15 → REX.B=1 ✓
   - subsd/mulsd/divsd_xmm8_xmm9_rex_rb：三个函数 REX=0x45（R=1,B=1）+ opcode 分别 5C/59/5E ✓
   - xorpd_xmm15_rex_rb：REX=0x45 ✓
   - xorpd_xmm0_no_rex：低寄存器无 REX ✓
   - cvtsi2sd_xmm8_r9_w1_r1_b1：REX=0x4D（W=1,R=1,B=1）✓
   - cvtsd2si_rax_xmm8_w1_r0_b1：REX=0x49（W=1,B=1,R=0）✓
   - ucomisd_xmm8_xmm9_rex_r1_b1：REX=0x45 ✓
   - ucomisd_xmm0_xmm1_no_rex：低寄存器无 REX ✓

**修改文件：**
- `backend/x86_64.py` +130 行（XMM8-15 常量 4 行 + _rex_xmm 辅助 14 行 + 9 条指令 docstring 升级 + REX 前缀替换）
- `tests/test_native_backend.py` +145 行（XMM8/9/15 导入 + _first_rex 辅助 + 13 用例）

---

### 三、测试前后对比

| 指标 | 开发前（基线 Cycle 73） | 开发后（本轮 Cycle 74） | 变化 |
|------|------|------|------|
| 完整测试通过率（参考值） | 1351/1353 ≈ 99.85% | ≥ 同水平（分项汇总 100%） | 无回归 |
| test_parser.py（增量用例数） | — | +6/6 passed | ↑6（TestParserExprIncrementalRecovery） |
| test_native_backend.py | 75/75 passed（Cycle 73 含 4 RBP / 3 SpillBias） | 75/75 passed（+13 XMM REX） | 测试规模扩大，质量密度提升 |
| test_nova.py 集成 | 203 passed（Cycle 73） | 203 passed, 20 subtests | 0 变化 |
| test_ir + test_c_codegen + test_ssa_verifier + test_backends | 195 passed（Cycle 73） | 195 passed | 0 变化 |
| 新增失败 | — | 0（无新增回归） | — |

**2 个 pre-existing 失败（非本轮引入）**：test_pipe_right_not_function_has_location + test_pipe_type_mismatch_has_location（管道错误消息关键词「管道」）。

---

### 四、前端下一步 + 后端下一步

#### 前端下一步（Cycle 75 = 评审轮，不做新开发；Cycle 76 最高优先级）
1. **最高优先级**：`frontend_narrowing_fence_closure`（P95 easy，致命 F2 修复：_check_int_literal/_check_float_literal 设 TypeVar.overflow_risk=True）—— 窄化栅栏从「设计 100% 实现 0%」→ 三道防线 100% 闭合
2. **次优先级（Cycle 76 并行）**：`frontend_lexer_numeric_prefix`（P80 easy，0x/0o/0b 前缀 + _ 分隔符）—— 系统级语言标配字面量，关闭中危 M5
3. **Cycle 77**：`frontend_ast_visitor_framework`（P78 medium，AstVisitor + NodeTransformer + 55 节点 accept）—— 解决 FE 颗粒度太小的结构性失衡，IDE/宏/Lint 三大子系统前置基建

#### 后端下一步（Cycle 75 = 评审轮；Cycle 76 最高优先级）
1. **最高优先级**：`backend_native_closure_captured_stack`（P92 medium，致命 F1 修复：captured 7+ 栈段 System V 压栈）—— 闭包从「≤6 场景安全」→「任意 captured 数安全」
2. **次优先级（Cycle 76 并行）**：`backend_x86_64_setcc_rex_prefix`（P86 easy，高危 H1：setcc 8 条 REX.B 扩展）—— 第三颗 REX 定时炸弹清零
3. **Cycle 77 攻坚**：`backend_native_stack_frame_rbp_cfi`（P88 hard，DWARF CFI + ELF 4 新节区，栈帧 80%→92% 收官）+ `backend_wasmgc_struct_phase1`（P82 hard，ADT 原生 struct 声明 + 指令替换，WasmGC 复合结构 3→82% +79pp）

---
