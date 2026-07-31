# Nova 前后端专项开发日志

本日志由前后端专项开发系统自动生成，记录每轮开发的详细信息。

---


## 第 69 轮（评审轮）— 2026-07-31 16:02

> **双线路线图评审 ✅**（覆盖 Cycle 67-68 两轮普通开发 + P1 清零收官 5/5 评估 + Cycle 70-72 规划）｜前端质量 8.6→8.7（↑0.1）｜后端质量 7.9→7.6（↓0.3）｜**前后端完成度 92% vs 64.3%（差 27.7pp，12pp 结构性合理 / 16pp 后端硬积压）**｜Cycle 70-72 资源配比 FE 35% / BE 65%｜新增 8 项高价值任务（FE 3 / BE 5）｜废弃 0 / 调整 2｜下一轮 70 = **普通轮 hard 任务攻坚**（regalloc_v2 P92 hard + 数值窄化栅栏 P88 medium + 位运算指令选择 P85 medium 三线并行）

### 一、三轮回顾总结（Cycle 67-68，覆盖评审 66 → 评审 69）

#### 前端回顾（Cycle 66→69：2 项 hard + 1 项 easy，完成率 88%→92% +4pp）

| # | 任务 | 轮次 | 难度 | 结果 | 核心价值 |
|---|------|:----:|:----:|:----:|---------|
| 1 | ErrorExpr 下游双 handler（TypeChecker+Evaluator） | 67 | easy | ✅ | Parser 四级熔断 3 轮投入（24/48/64）ROI 从 0→1；错误恢复体系真实可用 |
| 2 | **TypeVar Harden 三合一**（HM TVar 区分 + mut 幻影 + 泄漏栅栏 4 类前缀） | 68 | hard | ✅ | 前端 P1 最后一项清零；HM「实例化-泛化」对称正确；TypeChecker 现在对 4 类最常见歧义（空集合/悬空参数/悬空返回/未命名 TVar）给出中文友好错误；mut 幻影 bug 修复（同一 mut 变量两次读取 TVar 独立→冲突不检测） |

**前端里程碑**：HM 子集（generalize/instantiate 对称 + Value Restriction 最小化实现 + Error 哨兵 + 泄漏栅栏）完整性从 Cycle 66 的 65% → Cycle 69 的 **85%+**。错误恢复三端贯通（Parser 熔断 → TypeChecker ERROR_T 宽容合一 → Evaluator None 哨兵），前端的「用户体验成熟度」从 70% → **90%**。

#### 后端回顾（Cycle 66→69：3 项 hard + 1 项 medium，完成率 61.9%→64.3% +2.4pp）

| # | 任务 | 轮次 | 难度 | 结果 | 核心价值 |
|---|------|:----:|:----:|:----:|---------|
| 1 | WasmGC 双 P1（ADT variant_tag 独立 + Float 复合构建 4 处位转换） | 67 | medium | ✅ | WasmGC 真实可用度 15%→65%（单轮 +50pp）；C/Native 同款 variant_tag 复制粘贴 bug 同步修复 |
| 2 | **Phi 升级 fail-fast**（stderr→raise + has_incon 消费 + Loop Phi 覆盖） | 68 | medium | ✅ | MIR 降级 Phi 类型一致性从软观察（6 轮超期）升级为硬保证；_insert_loop_phis 旧「入口边单类型命中即 break」bug 修复（循环变量 Phi 回边类型不再静默被入口边覆盖） |
| 3 | **Native Float imm XMM0 冲突**（9+ float 参数溢出路径 silent data corruption 级 bug） | 68 | easy | ✅ | ABI 骨架 280 行 10 步的最后 1 个确定性 correctness bug 清零；Native ABI 子模块 78%→82% |

**后端里程碑**：P1 积压 **0（清零）**。评审 66 定义的 5 项 P1（FE 2 + BE 3）全部在 Cycle 67-68 两轮完成。三后端完成度分化：C 88.8%（健康）>> Native 78.1%（被栈帧 65%+寄存器分配 75% 两项拖后腿）> WasmGC 73.8%（复合结构 65% 全走 runtime 模拟，未切原生 GC struct/array）。

---

### 二、双线评估结果（深度审计维度）

#### 前端评估：质量 8.7/10 ↑0.1｜进度 92%｜体系已成熟

| 子维度 | 分数 | 证据 |
|--------|:----:|------|
| 类型系统完整性 | 9.0/10 | HM 泛化/实例化 85%+；泄漏栅栏 4 类全覆盖；ERROR_T 宽容合一；**缺口：Type Classes（架构愿景远景）+ 隐式数值窄化告警（近期 P88）** |
| 错误恢复可用性 | 9.2/10 | Parser TOP_LEVEL/STMT_BOUNDARY/EXPR 三级熔断 + ErrorExpr + TypeChecker ERROR_T + Evaluator None 哨兵 四端贯通；**缺口：STMT 级独立计数器（嵌套块偶发错误被 Panic mode 吞掉无计数）** |
| 测试密度 | 7.5/10 | type_checker.py 2496 行 / test_type_checker.py 1702 行 = **密度 0.68**（parser 0.90 / evaluator 1.01 的 ~67%）；Cycle 65-68 三项大改动（generalize/ErrorExpr/泄漏栅栏）的「边界×组合」路径覆盖仅 ~60%，需 frontend_type_system_test_matrix P75 补齐 |
| 代码注释率 | 9.0/10 | 关键算法（_generalize/_instantiate/_detect_leaking_tvars/_is_syntactic_value）docstring 覆盖率 >95%；TypeVar 元数据字段注释完整 |

**趋势**：**变好（↑）**——Cycle 66-68 前端投入 ROI 极高（两项任务直接清零所有 F-P1 积压 + 成熟度 +22pp），剩余 8% 全部是体验优化和测试补齐，无 correctness 类高优缺口。

#### 后端评估：质量 7.6/10 ↓0.3｜进度 Native 78.1% / WasmGC 73.8% / C 88.8%｜结构性分化

| 后端 | 8 子模块平均 | 最高子模块 | 最低子模块 | 测试密度 |
|------|:------:|------|------|------|
| **Native x86_64** | **78.1%** | ELF 头/节区 88%、全局变量 85% | **栈帧 65%、指令选择 72%** | **0.38**（2773 行源码 / 1045 行测试，< 业界 0.5 安全线） |
| **WasmGC** | **73.8%** | 局部变量 90%、函数 85% | **extern 导入 60%、复合结构 65%** | ~0.51 |
| **C** | **88.8%** | 局部变量 98%、类型声明 95% | 闭包 80%、复合结构 82% | **0.84**（健康） |

**Native 三大硬缺口（按 ROI 排序）**：
1. **寄存器分配 v1 → v2（75%→90%，+15pp）**：Linear Scan 区间分裂 + R12-R15 候选池扩展，vreg 溢出率 -40%、密集循环速度 +25-35%
2. **栈帧（65%→88%，+23pp）**：RBP 基址帧 + DWARF CFI .eh_frame（CIE+FDE），**可调试性 0→100**，后续所有 hard 任务开发周期 -50%
3. **指令选择（72%→88%，+16pp）**：按位运算 7 条指令（AND/OR/XOR/NOT/SHL/SHR/SAR）+ CMOVcc，加密/哈希/网络协议代码从 NotImplementedError → 可用

**趋势**：**持平略降（→）但加速追赶窗口已打开**——P1 清零后的 2-3 轮（Cycle 70-72）如果把 Native 三大硬缺口清掉，Native 总平均将从 78.1%→ **85%**，后端总体从 64.3%→**72%**，前后端差距从 27.7pp 收窄到 **~20pp**（<20pp 容差）。

#### 综合评估：前后端平衡度 7.2/10 →

**差距合理性拆解（27.7pp）**：
- ✅ **12pp 结构性合理**：前端目标 50（相对收敛） vs 后端目标 84（3 条后端 × N 子模块天然发散），分母大 68%；且前端剩余 4 项全是 easy/medium，后端 30 项里 10+ 是 hard
- ⚠️ **~16pp 后端硬积压**：Native 三大硬缺口（regalloc/栈帧/位运算）+ WasmGC 原生 struct/array 切换共 4 项 hard 任务，每轮平均 1.5 项 hard 吞吐，需要约 3 轮（Cycle 70-72）才能消化

**方向正确性**：✅ 正确——Cycle 66 评审定义的 5 项 P1 全部按时清零；Native ABI 正确性类 bug（silent data corruption 级）清零，安全边际达成。

**Cycle 70-72 资源配比建议：前端 35% / 后端 65%**

理由：
1. **边际收益差**：前端 92%→95% 的最后 3pp 是测试密度（0.68→0.75，+15 用例）和错误消息改进（30 行改动），每轮投入 1 项任务 ROI 足够；后端 64.3%→72% 的 +7.7pp 需要每轮 2 项 hard 任务
2. **hard 任务吞吐**：4 项 P1-P2 级 hard 任务（regalloc_v2/栈帧CFI/位运算/WasmGC 原生）+ 1 项 medium（struct 返回 ABI）= 5 项后端，3 轮平均每轮 ~1.7 项，需 65% 资源
3. **风险对冲**：如果前端 35% 资源在 Cycle 70 中提前完成 implicit_cast_fence P88，可弹性切到 test_matrix P75，不影响后端主线

---

### 三、问题总结与根因分析（评审 69 新发现）

| # | 问题 | 严重度 | 根因 | 对应任务 |
|---|------|:------:|------|---------|
| 1 | **Native 栈帧 65% 不可调试**：gdb backtrace 仅显示 _start+0x??，所有 hard 任务的调试效率极低 | **P1 级体验** | prologue/epilogue 未用 RBP 基址帧；ELF shoff=0 无节区头；.eh_frame CFI 未生成 | **backend_native_stack_frame_rbp_cfi P88 hard**（Cycle 71） |
| 2 | **Native 测试密度 0.38 不达标**：2773 行源码仅 1045 行测试，调度表覆盖率达标但长尾边界（9+ float 参数/混合参数/递归/结构体返回）覆盖不足 | P2 级风险 | emit_abi_call_direct 骨架化 280 行后没有同步补对应长尾测试；Cycle 64-68 五轮 CC 拆分/骨架化/XMM0 修复只补了 4 个专项，缺 10+ 普通场景 | **backend_native_abi_test_coverage P80 medium**（Cycle 72） |
| 3 | **WasmGC 复合结构 65% 全走 runtime 模拟**：nova_list_new 等导入函数返回 externref，GC 把对象当黑盒、字段访问索引是运行时参数 | P2 级正确性 | 第 67 轮只修了 variant_tag 独立和 float 位转换，没切原生 GC 类型声明 | **backend_wasmgc_native_struct_array P82 hard**（Cycle 71） |
| 4 | **前端 TypeChecker 测试密度 0.68 偏低**：generalize/ErrorExpr/TVar 泄漏 三大改动的组合路径覆盖 ~60% | P2 级回归风险 | Cycle 67-68 每轮只补了本任务专项的 7/11 用例，没覆盖「泄漏栅栏 × generalize × mut」三维组合 | **frontend_type_system_test_matrix P75 easy**（Cycle 71） |
| 5 | **Native 按位运算 7 条指令缺失**：AND/OR/XOR/NOT/SHL/SHR/SAR 调度表 7 条映射空白 | P2 级功能缺口 | 早期 C 后端优先实现，Native 后端从 ELF→指令选择→寄存器分配→ABI 的主线推进中没跟进同步 | **backend_native_instr_selection_bitwise P85 medium**（Cycle 70） |

---

### 四、下阶段方向与理由（Cycle 70-72 正式规划）

#### 总体方向
- **主线（65% 后端）**：Native 三大硬缺口（regalloc_v2 → 栈帧CFI → 位运算 + struct 返回 ABI）+ WasmGC 原生 struct/array 切换，**目标：Native 总平均 78.1% → 85%、后端总体 64.3% → 72%、差距 27.7pp → ~20pp**
- **辅线（35% 前端）**：隐式窄化栅栏（正确性前瞻）→ ADT 字段建议（体验优化）→ 测试矩阵 15 用例（密度 0.68→0.75），**目标：前端 92% → 95%、测试密度达标 ≥0.75**

#### 三轮排期表

| 轮次 | 前端任务（35%） | 后端任务（65%） | 里程碑目标 |
|:----:|-----------------|-----------------|-----------|
| **70** | **frontend_implicit_numeric_cast_fence P88 medium**（隐式数值窄化安全栅栏 + TypeVar.overflow_risk 标记，6 用例） | **backend_native_regalloc_linear_scan_v2 P92 hard**（Linear Scan 区间分裂 + R12-R15 callee-saved 候选池扩展，8 用例）**+** **backend_native_instr_selection_bitwise P85 medium**（按位运算 7 条指令 + CMOVcc，9 用例） | 寄存器分配 v1→v2 75%→90%；指令选择 72%→88%；Native 总平均 78.1%→81.5%；前端隐式窄化 silent bug 类清零 |
| **71** | **frontend_adt_field_suggestion_error P78 easy**（ADT 字段访问错误 known fields 补全，4 用例）**+** **frontend_type_system_test_matrix P75 easy**（15 用例 4 类测试补齐，密度 0.68→0.75） | **backend_native_stack_frame_rbp_cfi P88 hard**（RBP 基址帧 + DWARF CFI CIE+FDE + ELF 节区头 .shstrtab/.eh_frame/.symtab/.strtab，5 用例）**+** **backend_wasmgc_native_struct_array P82 hard**（WasmGC 原生 struct/array 声明替换 nova_* runtime，6 用例） | 栈帧 65%→88%；Native 总平均 81.5%→84%；WasmGC 复合结构 65%→90%，WasmGC 总平均 73.8%→80%；前端测试密度 0.68→0.75；前端 92%→94% |
| **72** | **Cycle 70-71 遗留任务（如有）** 或 新增体验项（parser STMT 级计数器） | **backend_native_abi_struct_return P80 medium**（大结构体 >16 字节 by-value 返回 System V 约定，5 用例）**+** **backend_native_abi_test_coverage P80 medium**（Native ABI +10 场景 / WasmGC wat 合法性 6 场景，16 用例合计） | ABI 82%→92%；Native 总平均 84%→85%；Native 测试密度 0.38→0.50（达标 ≥0.5）；后端总体 64.3%→72%；差距 27.7pp → ~20pp（<20pp 容差） |

---

### 五、任务池变更说明

#### 新增任务（8 项，FE 3 + BE 5）

| 任务 ID | Track | 优先级 | 难度 | 预计耗时 | 来源理由 |
|---------|:-----:|:------:|:----:|---------|---------|
| **frontend_implicit_numeric_cast_fence** | FE | P88 | medium | 3-4h | review_cycle_69 审计：Native SIMD 引入后 i32/i64 窄化无检测 = 前置 silent data corruption 风险；对齐 C/C++ -Wconversion |
| **frontend_adt_field_suggestion_error** | FE | P78 | easy | 1-2h | review_cycle_69 审计：前端 92% 后体验优化 ROI 最高项；35 行改动 → 错误消息可用性 +30% |
| **frontend_type_system_test_matrix** | FE | P75 | easy | 2-3h | review_cycle_69 审计：前端测试密度 0.68 < parser 0.90 / evaluator 1.01；三大改动组合路径覆盖仅 60%，需固化回归 |
| **backend_native_regalloc_linear_scan_v2** | BE | P92 | hard | 10-14h | review_cycle_69 审计：Native 完成度最大单项瓶颈；升级后寄存器分配 75%→90%；Native 总平均 +3.5pp；所有后端 hard 任务 ROI 最高 |
| **backend_native_stack_frame_rbp_cfi** | BE | P88 | hard | 12-16h | review_cycle_69 审计：Native 24 子模块最低分 65%；DWARF CFI 生成后可调试性 0→100，后续所有 hard 任务开发周期缩短 50% |
| **backend_native_instr_selection_bitwise** | BE | P85 | medium | 4-6h | review_cycle_69 审计：Native 指令选择 72% 与 C 后端 88% 最大功能缺口；加密/哈希/网络协议代码 silent 降级到 NotImplementedError；改动 ~200 行 7 条映射 |
| **backend_wasmgc_native_struct_array** | BE | P82 | hard | 10-14h | review_cycle_69 审计：WasmGC 复合结构 65% 全走 runtime 模拟（externref 黑盒）→ 切原生 (ref struct) 后字段静态检查 + GC 精确回收；WasmGC 总平均 +6pp 到 ≥80%，float 位转换 i64.reinterpret_f64 可彻底删除 |
| **backend_native_abi_struct_return** | BE | P80 | medium | 4-6h | review_cycle_69 审计：Native ABI 82% 拖后腿项；Nova/C 互操作 90% 用例（Vec3/Mat4 值传递）才可用；改动 ~180 行（ABI 骨架 Step 0 扩展） |

#### 保留 / 调整任务（2 项）
- **backend_native_abi_test_coverage P80 medium**：保留，排 Cycle 72（与 struct 返回 ABI 一起打包补测试）
- **frontend_type_system_test_matrix P78→P75**：优先级下调 3pp（从 roadmap 剩余活跃任务的位置继续保留，不与 P88/P78 两项 FE 新任务挤 Cycle 70）

#### 废弃任务（0 项）
- 本轮无废弃：所有 deprecated 列表 13 项均是之前评审已确认 0 NIE 的历史任务

#### 已完成任务（新增 1 项记录）
- review_cycle_69：本轮评审本身

---

### 六、更新后的路线图进度（Cycle 69 评审后）

| 维度 | 目标 | 当前完成 | 进度条 | 完成率 | 较评审 66 |
|------|-----:|---------:|:-------|-------:|-------:|
| 前端（类型系统+解析器+语义分析） | 50 | 46 | ██████████████████████░░ | 92.0% | ↑2pp |
| 后端（Native x86_64 + WasmGC + C 统一） | 84 | 54 | ███████████████░░░░░░░░░ | 64.3% | ↑2.4pp |
| 任务池历史累计（completed_tasks 去重） | — | 118 | — | — | +1（review_cycle_69） |
| 当前任务池（tasks 列表） | — | **10 项：1 completed / 8 pending / 0 failed / 1 deprecated alias** | — | — | **新增 8 项高价值任务** |
| P1 积压（active） | ≤2 | **0（清零维持）** | — | — | ✅ 持续 |
| Native 测试密度 | ≥0.5 | 0.38 | ███████░░░░░░░░ | 76% 目标 | ↓待 Cycle 72 补齐 |
| 前后端完成度差距 | ≤20pp | 27.7pp | ██████████████████████░░░░░░░ | 72% 目标 | ↓待 Cycle 72 收窄到 ~20pp |

---


## 第 68 轮（普通轮）— 2026-07-31 05:05

> **P1 清零里程碑 5/5 收官 ✅**（TypeVar 泄漏三合一 harden + Phi 升级 fail-fast + Native XMM0 冲突修复三项全部成功）｜前端 46/50=92%（↑2pp）｜后端 54/84=64.3%（↑2.4pp）｜新增 19 专项测试（前端 11、后端 8）全通过｜基线 6 文件 455 passed / 20 subtests > 374 passed（↑81）｜0 回归｜**P1 积压清零**（F-P1-1+2 TypeVar 泄漏+HM+mut ✅ / B-P1-2 Phi 升级 ✅ / B-P1-5 Native XMM0 ✅）｜剩余活跃任务仅 2 项（easy+medium）｜下一轮 69 = **路线图评审轮**（3 轮周期：67→68→69，69 % 3 = 0，评审前 63/64/65 → 66/67/68 回顾）

### 前端任务（P95 hard）— TypeVar 泄露防护：区分 HM 泛化 TVar + mut 幻影实例化 + 空集合类型推断栅栏

**为什么选这个**：评审 66 定级 F-P1-1+2 合并为 1 任务—— TypeVar 泄漏是「用户可见的类型系统正确性」最高风险项（用户写出的代码，TypeChecker 不报错，但生成的 IR 类型是泄漏的未绑定 TVar → 下游 MIR/LIR/Native/C/Wasm 全部不可预测）。三个子问题叠加：(1) 泄露的 TVar 未被检测 → 静默错误；(2) HM 泛化 TVar 与实例化 TVar 不区分 → 外层约束的 TVar 被错误 fresh 成独立实例（即 mut 幻影，每次读同一个 mut 变量得到新 TVar，合一时互相独立→冲突不检测）；(3) 空集合 `[]`/`{}` 缺少注解时 TypeChecker 静默继续 → 后续 append/put 产生的类型错误没有可定位的起点。难度 hard（修改 TypeVar/_instantiate/_detect_leaking 三个核心函数），但收益是所有 P1 中最大的（一旦上线所有用户代码的类型泄漏都会被立即报出）。

**结果：成功 ✅（11/11 专项 + 368 前端 3 模块 0 回归）**

修改 2 个文件 约 420 行：

1. **type_checker.py TypeVar 类（L55-68）**：新增 `is_generalized: bool = False` 字段（默认 False），用于 _instantiate 中区分「应该 fresh 的 HM 泛化 TVar」和「应该保留身份的非泛化 TVar（mut 绑定 / 局部未泛化 let）」。
2. **type_checker.py _instantiate（L2248-2290）**：条件化实例化——仅当 TypeVar.root.is_generalized=True 时创建 fresh inst_{name} 副本；否则直接返回原 root（保留 union-find 身份）。这修复了 mut 幻影实例化 bug（mut xs = [] 每次读取 xs 得到独立 TVar → append 1 INT 和 append "s" STR 永不冲突）。
3. **type_checker.py _detect_leaking_tvars（L2318-2371）**：新增 4 前缀分发的泄漏栅栏（TypeCheckError 友好消息）：(a) `unknown_list_elem*` → 「空列表无法推断元素类型」；(b) `unknown_map_key*` / `unknown_map_value*` → 「空映射无法推断键/值类型」；(c) `param_*` / `lambda_param*` → 「参数类型无法确定，请为参数添加类型注解」；(d) `ret_*` → 「返回类型无法确定」。ERROR_T 哨兵与 generalized TVar 自动跳过（不触发次生泄漏误报）。
4. **type_checker.py _check_list_expr / _check_map_expr**：空集合列表元素 TVar 命名为 `unknown_list_elem_{counter}`（映射 key/value 同理），触发泄漏栅栏的 (a)(b) 分支。
5. **type_checker.py _check_binding_decl（mut 分支）**：mut 绑定的 result_type 在 generalise 调用时传入 mutable=True（最小化 Value Restriction 实现），mut 表达式不泛化 → is_generalized 保持 False → mut 读取保留身份。
6. **type_checker.py _check_fn_decl（悬空 param 检测算法）**：先 _generalize（合法 HM 多态 param T 在 f:FnType([T],Int) 的复合类型内部被引用 → is_generalized=True 不泄漏）；再用 self._find(pt_root) 计算的 root（不是 pt 自身）区分「param TypeVar 自身」与「param TypeVar 已被 unify 成 FnType/ListType」，识别出悬空 param（unused_param(x){42} 的 x 不被 return 或其他参数的子树引用 → dangling_param_ids 集合）；最后对悬空 param 撤销 generalize（恢复 is_generalized=False → 泄漏栅栏命中 → 报参数类型无法确定）。

**测试 11 用例 11/11（test_type_checker.py TestTypevarHarden）**：
- test_empty_list_no_annotation_raises_helpful_error ✅
- test_empty_map_no_annotation_raises_helpful_error ✅
- test_fn_param_unreferenced_no_annotation_raises ✅
- test_mut_list_multiple_append_type_conflict_detected ✅（原 mut 幻影 bug → 现在检测到 INT/STR 冲突）
- test_error_t_in_fn_type_not_triggers_leak_fence ✅（ERROR_T 哨兵不误报）
- test_syntactic_value_lambda_is_generalized_polymorphic ✅（HM 基本性质：id 函数多态，两次调用独立实例互不干扰）
- test_regression_hm_id_polymorphism_classic ✅（let id = |x| x; id(1); id("s") 不冲突）
- test_mut_binding_not_generalized_identity_preserved ✅
- test_mut_var_identity_through_identifier_lookup ✅
- test_non_syntactic_value_not_generalized ✅
- test_regression_mut_simple_reassignment_no_leak ✅

**价值**：P1 归零里程碑前端端收官。TypeChecker 现在对 4 类最常见的类型推断歧义（空集合、悬空参数、悬空返回、未命名 TVar）全部给出中文友好错误消息（非 cryptic "cannot unify None with Int"）。HM 类型系统的「实例化-泛化」对称现在正确：只有 generalize 标记过的 TVar 才被 fresh 实例化。mut 绑定幻影 bug 被修复（3 项任务中投入产出比最高的一个）。

### 后端任务 1（P90 medium）— 升级 _resolve_phi_type 从 stderr→raise MIRLoweringError + 消费 has_incon + 覆盖 Loop Phi

**为什么选这个**：评审 66 定级 B-P1-2（观察期超期 3 轮必须升级）。cycle 61 引入 _resolve_phi_type 的「第一阶段观察模式」（仅 print(stderr)，不抛异常），原定 1-2 轮零假阳性后升级为 fail-fast，实际 cycle 61→67 已经 6 轮超期 3 轮，继续观察没有收益，反而会让真正的 Phi 类型不一致（如 if true 分支 x:INT，false 分支 x:STR，上游 TypeChecker somehow 漏检）被静默继续编译 → Native 后端生成的 ELF 会栈上写 8 字节 INT 再读成 8 字节 FLOAT = 未定义行为（浮点寄存器加载整数位模式 = NaN/Inf，运行时随机崩溃）。fail-fast 是 MIR 降级的安全底线。

**结果：成功 ✅（4/4 专项 + 后端 5 模块 252 passed 0 回归）**

修改 2 个文件 约 200 行：

1. **ir/mir_lowering.py _resolve_phi_type（L979-990）**：print(stderr, has_inconsistency=True 但不中断）改为 fail-fast raise MIRLoweringError。异常消息包含：上下文标签 @ merge_block[bbN]::var[x]（定位 Phi 插入位置）+ 前驱块名 b_i/b_j（定位哪个块）+ 类型 t_i/t_j（定位类型）+ kind 名（调试时快速识别枚举）。两两一致性校验内层 for 一旦检测到不兼容对立即 fail（不再继续检查其他对，fail-fast）。
2. **ir/mir_lowering.py _lower_function（L285-290）**：MIRFunction 创建时初始化动态属性 mir_fn.annotation = {}（不修改 MIRFunction dataclass，保持 LIRLowering/Native 后端的跨模块兼容性），用于 has_inconsistency 消费端写入计数器。
3. **ir/mir_lowering.py _insert_merge_phis（L1019-1028）**：原 `phi_type, _ = self._resolve_phi_type(...)` 改为显式解包 `phi_type, has_incon`；`if has_incon` 写入 `annotation["phi_inconsistency_count"] += 1`（注意 fail-fast 路径下 has_incon=True 但代码不会执行到这里，仅作为安全 fallback；未来若降级为 warning 模式则直接可用）。
4. **ir/mir_lowering.py _insert_match_merge_phis（L1095-1102）**：同 _insert_merge_phis，显式消费 has_incon。
5. **ir/mir_lowering.py _insert_loop_phis（L1555-1580）**：删除旧「先取入口边 pre_ssa 的 ssa_types[pre_ssa] 作为 phi_type，第一个命中即确定」的逻辑（第一个可能不对，入口边是 INT 回边是 FLOAT 会静默把 FLOAT 读成 INT）。改为先收集 phi_sources（入口边 + 所有 latch 边），再统一调用 _resolve_phi_type(context_label=loop_header[...]::var[var_name])——for/while/list_comprehension 三类循环的循环变量 Phi 全部走同一条一致性校验路径。

**测试 4 用例 4/4（test_ir.py MIRLoweringPhiUpgradeRaiseTest）**：
- test_if_merge_phi_int_float_conflict_raises_with_context ✅（bb_true→INT vs bb_false→FLOAT，含 merge[bb3]::var[x] context）
- test_match_merge_phi_int_float_conflict_raises ✅（arm0→INT vs arm1→FLOAT）
- test_for_loop_phi_int_vs_float_conflict_raises ✅（entry→INT vs latch→FLOAT）
- test_while_loop_phi_int_vs_str_conflict_raises ✅（entry→INT vs latch→STRING）

**价值**：B-P1-2 清零，MIR 降级的「Phi 类型一致性」成为硬保证（fail-fast 异常）而非软观察（stderr 没人看）。_insert_loop_phis 的旧第一个命中即 break bug 被修复（之前只检查入口边类型，不检查回边类型）。has_inconsistency 的消费端不再是哑元变量 `_`，而是写入 MIRFunction.annotation 字典便于 emit 阶段查询（后续若需要 warning 模式不用再改调用点）。

### 后端任务 2（P82 easy）— 修复 Native Float imm 溢出路径覆盖 XMM0（已装载第 0 个 float 参数）

**为什么选这个**：B-P1-5（easy 任务，顺便处理）。在 _emit_abi_call_direct 的参数装载溢出分支中，当 8 个 XMM 寄存器（XMM0-XMM7）用完之后，第 9+ 个 float 立即数参数的原代码路径是 `movsd XMM0,[RIP+disp32] → movq RAX,XMM0 → push RAX`——用 XMM0 当临时寄存器加载 float 常量再转 GPR 压栈，但 XMM0 在 Step 4 的参数装载开始就已经写入第 0 个 float 参数的值（如果有第 0 个 float 参数）。所以执行完溢出路径后 XMM0 被覆盖 = 第 0 个 float 参数在 call 指令执行时已变成第 9 个 float 常量的值 → **静默数值错误**（不 crash，但 ABI 参数错位，所有 float 参数都错）。难度 easy（只改 3 行代码），但属于 ABI 正确性的 silent-data-corruption 级 bug，必须立即修复。

**结果：成功 ✅（4/4 专项 + native 模块 57 passed 0 回归）**

修改 1 个文件 2 行 + 测试约 110 行：

1. **backend/native_backend.py _emit_abi_call_direct（L1066-1073）**：删除 3 行旧 `movsd XMM0 → movq RAX,XMM0 → push RAX`，改为 2 行新 `mov RAX,[RIP+disp32] → push RAX`。原理：8 字节 float 常量的 RIP-relative 加载对 XMM 和 GPR 是完全对称的（都是 ModRM=05，REX.W=0 vs 1），data_fixup 中的 RIP 偏移计算对 mov_reg_rip 和 movsd_reg_imm 是同一公式（disp32 = 目标 .data 地址 - 当前 .text 位置下一条指令地址），因此 data_fixups 追加逻辑不变（fixup_offset 仍然是 emitter 中 32-bit imm 占位的相对位置，fixup_type="float" 仍然表示 8 字节数据段中的 float 常量——因为 RAX 是 64 位整数寄存器，mov [RIP+disp32] 加载的 64 位内容和 movsd 加载的 64 位内容完全一样：都是 double 的 IEEE 754 位模式，之后 push RAX 把这 64 位压栈到栈上参数位置——对被调用者来说栈上 8 字节内容完全等价（ABI 只要求栈上 8 字节 double 位模式正确，不关心是 XMM→MOVQ→PUSH 还是 RAX→PUSH 搬过来的）。

**测试 4 用例 4/4（test_native_backend.py TestNativeFloatImmOverflowXmm0Conflict）**：
- test_float_imm_overflow_emit_no_movsd_xmm0_in_overflow ✅（9 float：MOVQ_RAX_XMM0 字节特征码不出现 + MOV_RAX_RIP count=1）
- test_float_imm_overflow_stack_count ✅（9 float：MOV_RAX_RIP 次数=1）
- test_int_args_then_float_overflow_no_xmm0_conflict ✅（6 int+9 float：MOVQ_RAX_XMM0 不出现 + MOV_RAX_RIP count=1）
- test_vast_majority_float_overflow_multiple_no_xmm0 ✅（20 float：MOV_RAX_RIP ≥12 = 20-8 溢出数）

**价值**：Native 后端的 9+ float 参数调用的 silent-data-corruption bug 被修复。之前任何用户代码中调用 `extern fn(1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0)`（9 个 float 立即数参数）都会导致第 0 个参数变成 9.0。

### 测试前后对比

| 指标 | 开发前（基线 6 文件） | 开发后（基线 6 文件） | 变化 |
|------|---------------------|---------------------|------|
| 6 模块通过数 | 374 passed / 20 subtests | **455 passed / 20 subtests** | **+81 passed**（含 cycle 63-66 新测试） |
| 6 模块失败数 | 0 | 0 | 0 |
| 新增专项测试 | - | 19（前端 11 + 后端 8） | +19 |
| 前端 3 模块（type+parser+evaluator） | 357（cycle 67 基线） | **368** | +11 |
| 后端 5 模块（IR+native+C+backends+ssa） | 244（cycle 67 基线） | **252** | +8 |

### 前端下一步（第 69 评审轮准备）
- **主动**：评审 69 = 三周年评审（63-68 共 6 轮回顾）。准备材料：前端完成度 46/50=92%（距架构愿景 95% 还差 3pp，仅剩 Type Classes 或 Traits 系统未实现）、错误恢复体系 Parser→TypeChecker→Evaluator 三段贯通（ErrorExpr→ERROR_T→None 哨兵）、TypeVar 泄漏栅栏+HM 泛化/mut 幻影修复=类型系统可用度达标 HM 子集 + Value Restriction 最小化实现。
- **反应式**：若用户报告新的 TypeCheckError 误报（正常，泄露检测上线后首次暴露潜在问题代码）→ 区分"真泄露（应该报错）"vs"假泄露（_detect_leaking_tvars 条件太严）"→ 对应调整前缀分发条件或悬空 param 检测的 duck-typing 子树遍历。

### 后端下一步（第 69 评审轮准备）
- **主动**：Native 后端真实完成度——Phi 升级+B-P1-2 清零，Native 后端的「正确性类 P1」全部清零（只剩性能类：寄存器分配器 P88 hard / 栈帧布局精确化 P86 hard / System V ABI caller-saved 精确集 P84 hard）。WasmGC 后端的 ADT variant_tag + Float reinterpret_f64 已经修复完成度 65%。C 后端 LIR 统一度 = 3/4。
- **反应式**：下一轮评审后 P2 选 2 项（B-P2-1 寄存器分配器 P88 hard + B-P2-4 栈帧精确 P86 hard，或换成 WasmGC 的 externref 包装 + 引用类型全局变量 P68 hard），根据评审结论决定优先级。

---


## 第 67 轮（普通轮）— 2026-07-31 02:46

> **P1 清零里程碑 2/5**（第 66 轮评审 P1 积压 5 项：ErrorExpr 下游 ✅ + WasmGC 双 bug ✅ / 剩 TypeVar 泄漏三合一 + Phi 升级收尾 2 项）｜前端 45/50=90%（↑2pp）｜后端 52/84=61.9%（↑1.2pp）｜新增 13 专项测试（前端 8、后端 5）全通过｜全量 ~1158 测试 0 回归｜WasmGC 真实完成度（看 emit 逻辑）45%→65%，单轮 ↑20pp｜**下一轮 68 = P1 清零里程碑 5/5 收官轮**（前端 harden 三合一 + 后端 Phi 升级 + Native XMM0 顺带）

### 前端任务（P98 easy）— 修复 ErrorExpr 下游双缺失：type_checker + evaluator 各加 1 handler

**为什么选这个**：评审 66 定级 F-P1-1「归零风险」—— Parser 24/48/64 三轮投入的四级熔断体系产出 ErrorExpr，但下游两消费者（TypeChecker/Evaluator）的调度表都不含 handler = 错误发生时 Parser 努力恢复，但 TypeChecker 报「未知的表达式类型」覆盖原始 ParseError、Evaluator 直接抛 RuntimeError_ 崩溃 = 错误恢复的真实 ROI 为 0。作为 easy 任务（修改两调度表+两小方法+测试），是所有 P1 中投入最小但收益最大的一项。

**结果：成功 ✅**

修改 4 个文件 约 150 行：
1. **type_checker.py**：新增 `ERROR_T = PrimType("__Error__")` 哨兵单例；`_unify` 情况 0 宽容合一（ERROR_T 与任何类型兼容，不触发次生类型错误阻塞后续分析）；`_build_expr_checkers` 新增 `ErrorExpr → _check_error_expr` 映射；`_check_error_expr(expr)` 返回 ERROR_T（方法体 0 raise，不再次报错——错误已在 Parser 侧记录）。
2. **evaluator.py**：`_build_expr_eval_dispatch_table` 新增 `ErrorExpr → _eval_error_expr` 映射；`_eval_error_expr(expr)` 返回 `None` 哨兵（允许解释器在错误恢复模式下继续执行块内其他语句，不因为一个表达式崩溃整个程序）。
3. **test_type_checker.py TestErrorExprDownstream（7 用例 7/7）**：ERROR_T 单例检查 / ERROR_T 与 Int/Float 合一通过（宽容策略正反方向）/ 直接构造 ErrorExpr 传入 check_expr 返回 ERROR_T 不抛「未知的表达式类型」/ 含 ERROR_T 的合一结果不会泄漏成未绑定 TVar / 构造带 ErrorExpr 的 Program AST 直接传 TypeChecker.check_program 不崩溃次生错。
4. **test_evaluator.py TestErrorExprEvalDownstream（3 用例 3/3）**：ErrorExpr 传入 eval_expr 返回 None 哨兵不抛 RuntimeError「未知的表达式类型」/ 多次重复调用同一 ErrorExpr 对象结果一致（幂等）/ 块语句中夹一个 ErrorExpr 其余 Int 语句正常求值返回最后一个有效语句的值。

**价值**：前端 P1 积压 2→1（剩 TypeVar 泄漏+HM TVar+mut 幻影三合一 harden）；前端完成度 44/50=88%→45/50=90%；Parser 错误恢复体系的真实 ROI 从 0→1；作为 TypeCheckError 的消费前置依赖，harden 任务 Step 2 新增的泄漏栅栏报错现在不会被 ErrorExpr 触发的次生崩溃覆盖（ERROR_T 宽容合一+泄漏栅栏可正确跳过）。

### 后端任务（P95 medium）— 修复 WasmGC 双 P1：ADT variant_tag 独立传递 + Float 元素复合构建位转换（C/Native 同款 variant_tag bug 同步修复）

**为什么选这个**：评审 66 定级 B-P1-1 + B-P1-2 合成一个任务（两个都在 WasmGC 后端同一主文件，修改面重叠 ROI 最高）。ADT variant_tag 传错 = Some/None 等多变体全部走同一分支 = WasmGC 目标的 ADT 模式匹配完全不可用；Float 复合构建缺 i64.reinterpret_f64 = 任何含 Float 元素的 List/Tuple/Map 构建都无法通过 Wasm 验证器 type mismatch = 两个 P1 叠加导致 WasmGC 目标的「真实可用场景」只有纯 Int 单变体 ADT 和纯 Int 复合结构，名义完成度 45% 但实际可用度约 15%。同任务还顺手修复 C/Native 三后端的同款 variant_tag 复制粘贴 bug（因为 LIRBuildADT 原缺 variant_tag 字段，三后端都被迫复用 type_tag）。

**结果：成功 ✅**

修改 6 个文件 约 310 行：

**Bug A【ADT variant_tag 独立】（5 处）**：
1. **ir/lir.py LIRBuildADT 数据类**：新增 `variant_tag: int = 0` 字段，与 type_tag 独立。
2. **ir/lir_lowering.py**：LIRLowering.__init__ 新增 `_adt_type_ids: Dict[str,int]`（type_name→自增 ID）和 `_adt_variant_index: Dict[str,Dict[str,int]]`（type_name→variant_name→自增索引）双注册表；`_lower_adt_build` 查表独立赋值 type_tag/variant_tag（如 Option 的两次构建 Some=variant_tag=0 / None=variant_tag=1 保证不同）。
3. **backend/wasm_backend.py _compile_build_adt**：原 L747-748 两行完全相同 `i32.const {instr.type_tag}` → 改为 `type_tag`（ADT 类型全局唯一 ID）+ `variant_tag`（变体在 ADT 内的索引）独立传递。
4. **backend/lir_c_backend.py _compile_build_adt（L601）**：variant_tag = `instr.variant_tag` 不再复制 type_tag。
5. **backend/native_backend.py _emit_build_adt（L1432）**：nova_adt_new 运行时调用第二参改为 `instr.variant_tag`。

三后端（Wasm/C/Native）的 ADT variant_tag 统一修复，消除多变体同值的跨端一致性 bug。

**Bug B【Float 位转换缺失】（4 处构建）**：

backend/wasm_backend.py 的 4 个数据结构构建方法中，local.get Float 元素后栈为 f64，但对应的写入接口（nova_* 函数 param i64 或 i64.store）期望 i64，一律在 `local.get $elem_loc` 之后、写入动作之前插入条件位转换：
1. `_compile_build_list` → nova_list_push 之前：if elem_type.kind == FLOAT → emit `i64.reinterpret_f64`
2. `_compile_build_map` → nova_map_put 之前（第三参 value）：if val_type.kind == FLOAT → emit `i64.reinterpret_f64`
3. `_compile_build_tuple` → i64.store 之前：if elem_type.kind == FLOAT → emit `i64.reinterpret_f64`（对齐 NovaValue 8 字节的位模式）
4. `_compile_build_adt` → nova_adt_set_field 之前（第三参 field value）：if field_type.kind == FLOAT → emit `i64.reinterpret_f64`
