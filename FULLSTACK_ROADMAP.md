# Nova 前后端专项开发路线图（Roadmap）

> 自动生成于 2026-07-31 16:02｜第 **69** 轮｜**评审轮**（Cycle 67-68 回顾 + Cycle 70-72 规划）｜P1 积压 0（清零维持）｜剩余活跃任务 **8** 项（FE 3 / BE 5，BE 中 4 项 hard / 1 项 medium）｜下一轮 **70 = 普通轮 hard 攻坚**（regalloc_v2 P92 hard + 数值窄化栅栏 P88 + 位运算指令选择 P85 三线并行）

---

## 总体进度概览

| 维度 | 目标 | 当前完成 | 进度条 | 完成率 | 较上轮（评审 66） |
|------|-----:|---------:|:-------|-------:|-------:|
| 前端（类型系统+解析器+语义分析） | 50 | 46 | ██████████████████████░░ | 92.0% | ↑2pp |
| 后端（Native x86_64 + WasmGC + C 统一） | 84 | 54 | ███████████████░░░░░░░░░ | 64.3% | ↑2.4pp |
| 任务池历史累计（已去重 completed_tasks） | — | 118 | — | — | +1 |
| 当前任务池（tasks 列表） | 10 | 1 completed / 8 pending / 0 failed / 1 deprecated alias | — | — | 新增 8 项高价值任务 |
| P1 积压（active） | ≤2 | **0（清零维持 ✅）** | — | — | 持续 |

---

## 本轮（Cycle 69 评审）里程碑

### ✅ 评审输出 5 项关键结论

| # | 结论 | 详情 |
|---|------|------|
| 1 | **前端质量 8.7/10（↑0.1）：体系成熟** | HM 泛化/实例化 85%+ 对称；ErrorExpr 三端贯通（Parser→TypeChecker ERROR_T→Evaluator None 哨兵）；TVar 泄漏栅栏 4 类前缀分发（空集合/悬空参数/悬空返回/未命名 TVar） |
| 2 | **后端质量 7.6/10（↓0.3）：结构性分化** | C 88.8% ✅ / Native 78.1%（栈帧 65% + 寄存器 75% 拖后腿） / WasmGC 73.8%（复合结构 65% 全走 runtime 模拟未切原生 GC struct） |
| 3 | **前后端 92% vs 64.3%：差 27.7pp，12pp 结构性合理 / 16pp 后端硬积压** | 前端目标 50 < 后端目标 84（68%）；Native 三大硬缺口（regalloc_v2 + 栈帧CFI + 位运算）+ WasmGC 原生 struct/array = 4 项 hard，需 3 轮消化 |
| 4 | **Cycle 70-72 资源配比 FE 35% / BE 65%** | 前端 92%→95% 每轮 1 任务足够（体验优化 + 测试补齐）；后端 64.3%→72% 每轮 2 项 hard 任务（4 项 hard + 2 项 medium = 6 项 / 3 轮 = 2 项/轮） |
| 5 | **新增 8 项高价值任务：FE 3 + BE 5** | FE：P88（隐式窄化栅栏）/ P78（ADT 字段建议）/ P75（测试矩阵 15 用例）；BE：P92（regalloc_v2）/ P88（栈帧CFI）/ P85（位运算 7 指令）/ P82（WasmGC 原生 struct）/ P80（struct 返回 ABI） |

### 🎯 Cycle 70-72 目标（评审 69→评审 72）

| 指标 | 评审 69（当前） | 评审 72（目标） | 变化 |
|------|----------------:|----------------:|:----:|
| 前端完成度 | 92.0% | 95.0% | +3pp |
| 后端完成度 | 64.3% | 72.0% | +7.7pp |
| Native 总平均 | 78.1% | 85.0% | +6.9pp |
| WasmGC 总平均 | 73.8% | 80.0% | +6.2pp |
| 前后端差距 | 27.7pp | ~20pp | -7.7pp（<20pp 容差） |
| 前端测试密度 | 0.68 | ≥0.75 | +0.07 |
| Native 测试密度 | 0.38 | ≥0.50 | +0.12 |

---

## 剩余活跃任务（按优先级降序，共 8 项）

### 🎨 前端剩余（3 项：1 medium + 2 easy）

| 优先级 | 任务 | 难度 | 排期轮次 | 状态 |
|-------:|------|:----:|:--------:|:----:|
| 88 | **隐式数值窄化安全栅栏：_unify_types 位宽差异≥32 且无显式注解时告警 + TypeVar.overflow_risk 标记**（frontend_implicit_numeric_cast_fence） | medium | 70 | pending |
| 78 | **ADT 字段访问错误消息增强：type X has no field Y → known fields are [a,b,c]**（frontend_adt_field_suggestion_error） | easy | 71 | pending |
| 75 | **TypeVar 泄漏/泛化/ErrorExpr/泛化边界 4 类 × 15 用例补齐（前端测试密度 0.68→0.75）**（frontend_type_system_test_matrix） | easy | 71 | pending |

### ⚙️ 后端剩余（5 项：3 hard + 2 medium）

| 优先级 | 任务 | 难度 | 排期轮次 | 状态 |
|-------:|------|:----:|:--------:|:----:|
| 92 | **寄存器分配器 v2：Linear Scan 区间分裂 + spill 粒度细化 + R12-R15 callee-saved 溢出（Native 完成度最大单项瓶颈）**（backend_native_regalloc_linear_scan_v2） | hard | 70 | pending |
| 88 | **栈帧布局精确化：RBP 基址帧 + DWARF CFI .eh_frame 元数据（CIE + FDE 序列）+ ELF 节区头 .shstrtab/.eh_frame/.symtab/.strtab**（backend_native_stack_frame_rbp_cfi） | hard | 71 | pending |
| 85 | **指令选择补齐：按位运算 AND/OR/XOR/NOT/SHL/SHR/SAR + CMOVcc 分支less 条件移动**（backend_native_instr_selection_bitwise） | medium | 70 | pending |
| 82 | **WasmGC 升级：引入原生 (type $adt_X (struct ...)) + (type $list_T (array ...)) 声明替换 nova_* runtime 模拟**（backend_wasmgc_native_struct_array） | hard | 71 | pending |
| 80 | **ABI 调用补齐：大结构体 >16 字节 by-value 返回 System V AMD64 规范（RDI 指针返回约定）+ 同步补 Native ABI +10 场景 / WasmGC 6 场景长尾测试**（backend_native_abi_struct_return + backend_native_abi_test_coverage 打包） | medium | 72 | pending |

---

## Cycle 70-72 排期表（正式确认版）

| 轮次 | 类型 | 前端任务（35%） | 后端任务（65%） | 里程碑 |
|-----:|:----:|-----------------|-----------------|--------|
| **70** | 普通轮 | frontend_implicit_numeric_cast_fence P88 medium（隐式窄化栅栏 6 用例） | **backend_native_regalloc_linear_scan_v2 P92 hard**（寄存器分配 v2，区间分裂+R12-R15，8 用例）**+** backend_native_instr_selection_bitwise P85 medium（按位运算 7 指令 + CMOVcc，9 用例） | 寄存器分配 75%→90%；指令选择 72%→88%；Native 总平均 78.1%→81.5%；前端隐式窄化 silent bug 类清零 |
| **71** | 普通轮 | frontend_adt_field_suggestion_error P78 easy（ADT 字段 known fields，4 用例）**+** frontend_type_system_test_matrix P75 easy（测试矩阵 15 用例，密度 0.68→0.75） | **backend_native_stack_frame_rbp_cfi P88 hard**（RBP 基址帧 + DWARF CFI + ELF 节区头 4 节，5 用例）**+** **backend_wasmgc_native_struct_array P82 hard**（WasmGC 原生 struct/array，6 用例） | 栈帧 65%→88%；Native 总平均 81.5%→84%；WasmGC 复合结构 65%→90%，WasmGC 总平均 73.8%→80%；前端测试密度 ≥0.75；前端 92%→94% |
| **72** | 普通轮 | Cycle 70-71 遗留（如有）或 parser STMT 级独立计数器（可选 P72） | **backend_native_abi_struct_return P80 medium**（大结构体 >16 字节 by-value 返回 System V，5 用例）**+** backend_native_abi_test_coverage P80 medium（Native ABI +10 场景 / WasmGC 6 场景，16 用例合计） | ABI 82%→92%；Native 总平均 84%→85%；Native 测试密度 0.38→0.50 达标；后端总体 64.3%→72%；差距 27.7pp→~20pp（<20pp 容差） |
| **72** | **评审轮**（72 % 3 = 0） | — | — | 评审 Cycle 70-71-72 三轮开发 + 更新任务池 + 规划 Cycle 73-75 |

---

## 三后端完成度明细（8 子模块 × 3 后端 = 24 项，审计分数）

### Native x86_64（总平均 **78.1%**，目标：Cycle 72 → 85%）

| 子模块 | 当前 | 目标 72 | 对应任务 |
|--------|:----:|:-------:|---------|
| ELF 头/节区 | 88% | 92% | backend_native_stack_frame_rbp_cfi（.shstrtab/.symtab/.strtab/.eh_frame 4 节区补齐） |
| 指令选择 | 72% | 88% | backend_native_instr_selection_bitwise（AND/OR/XOR/NOT/SHL/SHR/SAR + CMOVcc） |
| 寄存器分配 | 75% | 90% | backend_native_regalloc_linear_scan_v2（区间分裂 + R12-R15 候选池） |
| 栈帧 | 65% | 88% | backend_native_stack_frame_rbp_cfi（RBP 基址帧 + DWARF CFI CIE+FDE） |
| ABI 调用 | 82% | 92% | backend_native_abi_struct_return（>16 字节 by-value 返回 System V 约定） |
| 运行时调用 | 80% | 83% | 待后续 extern "C" setjmp/longjmp 集成 |
| 闭包 | 78% | 80% | 待后续 runtime allocator GC 标记集成 |
| 全局变量 | 85% | 87% | 待后续 TLS 线程局部存储 |

### WasmGC（总平均 **73.8%**，目标：Cycle 72 → 80%）

| 子模块 | 当前 | 目标 72 | 对应任务 |
|--------|:----:|:-------:|---------|
| 类型声明 | 70% | 90% | backend_wasmgc_native_struct_array（(type $X (struct ...)) / (type $Y (array ...))） |
| 函数 | 85% | 88% | 待后续 tail call 优化 |
| 局部变量 | 90% | 92% | 小改动即可 |
| 控制流 if/loop/block | 70% | 75% | 待后续 br_table switch 跳转 |
| 调用（含 call_indirect） | 80% | 82% | 小改动即可 |
| 复合结构 list/tuple/map/adt | 65% | 90% | backend_wasmgc_native_struct_array（array.new_default / struct.new + array.get/set / struct.get） |
| 闭包 | 70% | 72% | 待后续 GC 根 tracing |
| extern 导入 | 60% | 62% | 待后续用户自定义 extern 导入机制 |

### C 后端（总平均 **88.8%**，健康 ✅）

| 子模块 | 当前 | 目标 72 |
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

| 指标 | 当前值 | 目标 | 状态 | 备注 |
|------|-------:|-----:|:----:|------|
| 基线测试通过率（11 文件 830 项） | 830 / 830 = 100% | ≥100%（无回归） | ✅ 绿 | Exit 0，所有子文件 individually passed |
| 新增代码注释率（关键函数） | >85% | ≥60% | ✅ 绿 | _generalize/_instantiate/_detect_leaking_tvars docstring 覆盖 >95% |
| 单任务失败后回滚率 | 100%（最近 10 任务 0 失败） | 100% | ✅ 绿 | P1 清零 5/5 全部一次成功 |
| P1 积压数 | **0** | ≤2 | ✅ 绿 | 评审 66→69 维持 0，Cycle 70-72 规划新增 0 项 P1 |
| Native ABI correctness 级 bug | 0（最近 1 项 XMM0 冲突 Cycle 68 清零） | ≤1/轮 | ✅ 绿 | emit_abi_call_direct 10 步骨架 correctness 类全部清零 |
| 前端测试密度（type_checker.py） | 0.68（源码 2496 / 测试 1702） | ≥0.75 | ⚠️ 黄 | 目标：frontend_type_system_test_matrix P75 上线后 0.75 |
| Native 后端测试密度 | 0.38（源码 2773 / 测试 1045） | ≥0.50 | ⚠️ 黄 | 目标：backend_native_abi_test_coverage P80 上线后 0.50 |
| 前后端完成度差距 | 27.7pp | ≤20pp | ⚠️ 黄 | 目标：Cycle 72 收窄到 ~20pp（<20pp 容差） |
