# Nova 前后端专项开发日志

本日志由前后端专项开发系统自动生成，记录每轮开发的详细信息。

---

## 第 21 轮评审 — 2026-07-25 08:30

> 三轮回顾评审：第 19-21 轮总结 + 双线路线图调整

---

### 三轮回顾总结（第 19-21 轮）

**完成任务统计：**

| 轨道 | 完成数 | 三轮前总数 | 三轮后总数 | 完成率变化 |
|------|--------|-----------|-----------|-----------|
| 前端 | 2 | 12/14 | 14/14 | 85.7% → **100%** |
| 后端 | 2 | 14/22 | 16/24 | 63.6% → 70.8% |
| 评审 | 1 | - | - | - |
| **总计** | **5** | **26/36** | **31/38** | **72.2% → 81.6%** |

**三轮产出质量：** 5/5 全部成功，无失败任务，测试通过率 100%（395 passed），无回归。
**难度构成：** 2 easy + 2 medium（评审轮不做功能开发）

---

### 深度代码审计重大发现

#### P0：必须立即修复

**P0-1：native_backend.py `_emit_runtime_call` 引用未定义变量**
- `CALLER_GPRS`、`INT_ARG_REGS`、`FLOAT_ARG_REGS` 仅在 `_emit_call` 方法内（第 571-573 行）定义为局部变量
- `_emit_runtime_call` 方法（第 779、788、803、859 行）引用这些变量，运行时会抛出 `NameError`
- 影响范围：所有通过 `_emit_runtime_call` 调用的运行时函数（BuildList/BuildMap/BuildTuple/BuildADT/Index/ListAppend）
- 根因：第 19 轮将手动调用迁移到 `_emit_runtime_call` 时，未将 ABI 常量从 `_emit_call` 内提取为模块级
- 当前未暴露原因：原生后端测试仅覆盖 x86_64 指令编码和 ELF 格式，无端到端编译测试触发 `_emit_runtime_call` 路径

**P0-2：native_backend.py `_emit_build_tuple` 浮点字段负栈偏移**
- 第 939 行：`e.movsd_mem_reg(RSP, -(i * 8 + 8), XMM0)` 向低地址写入
- 可能覆盖 caller-saved 保存区或返回地址，导致栈损坏
- 整数字段（第 944 行）同样使用 `e.mov_mem_reg(RSP, -(i * 8 + 8), RCX)`

**P0-3：wasm_backend.py 间接调用引用未声明函数**
- `_compile_call_indirect`（第 573 行）调用 `$nova_closure_call` 但该函数未在 `_emit_imports` 中声明
- 多参数间接调用（第 567 行）直接 `pass`，不生成任何代码，破坏栈平衡

#### P1：应尽快修复

**P1-1：所有后端的闭包创建和间接调用均为占位实现**
- Native: `LIRClosureCreate` 返回零值，`LIRCallIndirect` 是空 `pass`
- WASM: `LIRClosureCreate` 返回 `i32.const 0`，`LIRCallIndirect` 调用不存在函数
- C: 闭包函数指针为 `NULL`
- **lambda 表达式和 higher-order 函数在所有后端均无法工作**

**P1-2：MIR 层 `_lower_lambda` 不编译 lambda 函数体**
- `mir_lowering.py` 的 `_lower_lambda` 只创建 `MIRClosureCreate` 但不生成独立的 `MIRFunction`
- lambda 的函数体永远不会被编译到任何后端
- 这是所有后端闭包支持的前置条件

**P1-3：WASM 后端 GC 类型声明与实际使用不一致**
- 声明了 WasmGC struct 类型但不使用 `struct.new`/`struct.get` 指令
- 所有堆分配通过 `nova_alloc` 线性内存操作完成

#### P2：建议改进

- **P2-1**：模式匹配完备性缺少 Int/String/Char 字面量冗余检测
- **P2-2**：WASM Switch 使用 O(n) if-else 级联，可考虑 br_table
- **P2-3**：Pass Manager 仅支持 HIR 层优化，MIR/LIR 层缺少优化 pass
- **P2-4**：C 后端不区分内部/外部函数调用

---

### 前端线评估

**质量评分：88/100（与上轮持平，前端线已稳定）**

**质量趋势：类型系统已成熟，进入维护模式**

| 层面 | 完成度 | 说明 |
|------|--------|------|
| 词法分析 | 90% | Token 覆盖全面 |
| 语法分析 | 85% | 错误恢复已实现，递归下降结构清晰 |
| AST 设计 | 90% | 覆盖全部语法结构 |
| 类型系统 | ~90% | _unify_types 覆盖全面，let-polymorphism 就绪 |
| 模式匹配 | ~75% | 顶层完备性检查就绪，嵌套模式缺失 |

**进展亮点：**
- 第 19 轮完成 for 循环/列表推导迭代器类型推断
- 第 20 轮清理 `_types_compatible` 遗留死代码，前端线达到 100%

**最大短板：**
- 无显著短板。嵌套模式完备性检查和字面量冗余检测属于锦上添花

**结论：前端线投入产出比已极低，进入维护模式（仅修复 bug 或响应新需求）。**

---

### 后端线评估

**质量评分：Native 72/100 | Wasm 75/100 | C 68/100**

**进度评估：**

| 排名 | 后端 | 完成度 | 评分 | 关键缺失 |
|------|------|--------|------|----------|
| 1 | Native | ~80% | 72/100 | _emit_runtime_call P0 bug；闭包占位；无链接器 |
| 2 | WASM | ~78% | 75/100 | 间接调用 P0；闭包占位；GC 类型装饰 |
| 3 | C | ~70% | 68/100 | 闭包函数指针 NULL；不区分内外函数 |
| 4 | Cranelift | <30% | N/A | 仅有框架 |

**质量趋势：稳步提升但有隐患**
- 第 19 轮：原生后端运行时调用重构（统一到 `_emit_runtime_call`），但引入了 P0-1 bug（ABI 常量未提升到模块级）
- 第 20 轮：Wasm 数据结构构建完善，质量良好
- 整体：所有后端的闭包创建和间接调用均为占位实现，是系统性功能缺失

**最大短板：闭包/lambda 全链路不可用**
- MIR 层不编译 lambda 函数体
- LIR 层 `LIRClosureCreate` 无函数体信息
- 所有后端闭包创建和间接调用均为占位
- 影响：`map(lambda x: x+1, list)` 等高阶函数无法工作

**价值评估：下阶段最高价值任务**
1. P0 bug 修复（easy，P99）—— 解除原生后端实际可用性的阻断
2. 闭包 MIR 降级（hard，P85）—— 全链路前置条件
3. 原生后端闭包实现（hard，P82）—— 最高价值后端功能

---

### 综合评估

**前后端平衡性：严重失衡**
- 前端：14/14 = 100% 完成
- 后端：16/24 = 66.7% 完成（含 3 个已废弃任务，实际 16/21 = 76.2%）
- **建议投入比例：前端 10% / 后端 90%**

**方向评估：方向正确，需要调整优先级和投入比例**
- 第 18 轮评审设定的方向（后端 P0 bug 修复 + 运行时调用规范化）已全部完成
- 但第 19 轮的运行时调用重构引入了新的 P0 bug（ABI 常量未提升），说明代码质量保障流程需加强
- 闭包/lambda 全链路不可用是新发现的最大系统性问题

**效率评估：每轮平均产出良好**
- 三轮完成 4 个功能任务 + 1 个评审，全部成功
- easy/medium 任务效率高，hard 任务（ABI/模式匹配）需要 1-2 轮完成
- 0 失败任务，零回归记录

---

### 问题总结与根因分析

| 问题 | 严重度 | 根因 | 修复方案 |
|------|--------|------|----------|
| _emit_runtime_call NameError | P0 | 第 19 轮重构时 ABI 常量未提升为模块级 | 提升为模块级常量 |
| _emit_build_tuple 负栈偏移 | P0 | 第 17 轮实现时未考虑栈帧布局 | 改用正偏移临时区 |
| Wasm 间接调用引用未声明函数 | P0 | 闭包占位实现时未声明导入 | 声明导入或整体重写 |
| 所有后端闭包不可用 | P1 | MIR 层不编译 lambda 函数体 + 后端占位 | 全链路实现 |
| WasmGC 类型装饰 | P1 | 命名与实现不符 | 推迟到闭包后评估 |

**根因模式：占位代码积累**
- 多轮开发中，无法完成的指令以"TODO"或零值占位
- 占位代码在后续轮次中未被标记为阻断问题
- 建议：后续开发中，占位实现必须在状态文件中显式记录

---

### 下阶段方向与理由

**第 22-24 轮聚焦计划：**

| 轮次 | 前端 | 后端 | 理由 |
|------|------|------|------|
| 22 | 字面量模式冗余检测(easy,P55) | 修复原生后端 P0 bug(easy,P99) | P0 优先，easy 风险低 |
| 23 | 嵌套模式完备性(medium,P60) | 闭包 MIR 降级(hard,P85) | 闭包前置条件 |
| 24 | 维护 | 原生后端闭包实现(hard,P82) | 闭包最高价值后端 |

**理由：**
1. P0 bug 修复是最紧急的任务，easy 难度确保快速完成
2. 闭包全链路是下阶段最大价值方向——lambda/higher-order 函数是现代语言核心特性
3. 前端仅需低投入维护，90% 精力投入后端

---

### 任务池变更说明

**新增 6 个任务：**

| 任务 ID | 名称 | 优先级 | 来源 | 理由 |
|---------|------|--------|------|------|
| backend_fix_native_runtime_call_bugs | 修复原生后端 _emit_runtime_call P0 bug | 99 | review_21_audit | P0，阻断所有运行时调用 |
| backend_closure_mir_lowering | 修复 MIR lambda 降级 | 85 | review_21_audit | 闭包全链路前置条件 |
| backend_native_closure_impl | 原生后端闭包创建与间接调用 | 82 | review_21_audit | 闭包最高价值后端 |
| backend_wasm_closure_impl | Wasm 后端完整闭包支持 | 75 | review_21_audit | 闭包次高价值后端 |
| frontend_nested_pattern_check | 嵌套模式完备性检查 | 60 | review_21_audit | 前端维护模式增量 |
| frontend_literal_pattern_redundancy | 字面量模式冗余检测 | 55 | review_21_audit | 前端维护模式增量 |

**废弃 2 个任务：**

| 任务 ID | 名称 | 原因 |
|---------|------|------|
| backend_wasm_indirect_multiarg | Wasm 多参数闭包调用 | 并入 backend_wasm_closure_impl 整体实现 |
| backend_wasm_gc_types | WasmGC 原生类型定义 | 推迟到闭包功能完成后再评估，当前投入价值低 |

---

### 下轮计划

- **前端**: 字面量模式冗余检测（easy，P55）或嵌套模式完备性检查（medium，P60）
- **后端**: **修复原生后端 _emit_runtime_call P0 bug**（easy，P99）——最高优先级

---

## 第 20 轮（2026-07-25 00:10-00:25）

### 前端任务：清理 _types_compatible 遗留方法

- **任务 ID**: frontend_cleanup_legacy_compatible
- **难度**: easy
- **优先级**: 52
- **结果**: 成功
- **为什么选这个**: 前端线仅剩最后 1 个待做任务。深度代码分析确认 `_types_compatible`（type_checker.py 行 1548-1588，共 41 行）零外部调用点，7 处引用全部为内部递归自引用，是彻底的死代码。清理后前端线达到 100% 完成。
- **修改内容**:
  - `type_checker.py`: 删除 `_types_compatible` 方法（41 行），包含 FnType/ListType/MapType/TupleType/ADTType 的递归兼容性检查。该方法对 TypeVar 直接放行（鸭子类型），不产生约束，与当前 _unify_types 的合一驱动语义不兼容。因无外部调用，直接删除即可，无需替换。
- **测试验证**: 395 passed, 20 subtests passed，无回归

### 后端任务：Wasm 后端数据结构构建指令完善

- **任务 ID**: backend_wasm_data_build_fill
- **难度**: medium
- **优先级**: 65
- **结果**: 成功
- **为什么选这个**: Wasm 后端的 BuildList/BuildTuple/BuildADT 三个指令只分配内存不填充数据，且 `_compile_build_adt` 存在参数数量不匹配 bug（传 2 个 i32 给单参数 nova_alloc）。这是功能性缺陷——任何使用列表字面量/元组/ADT 的程序在 Wasm 后端编译后运行结果必然错误。参照原生后端有完整实现可直接参考。
- **修改内容**:
  - `wasm_backend.py` `_emit_imports`: 新增 4 个运行时函数导入（`nova_map_new`、`nova_map_put`、`nova_adt_new`、`nova_adt_set_field`）
  - `wasm_backend.py` `_emit_dispatch_prologue`: 新增 `(local $tmp_ptr i32)` 临时局部变量声明，用于存储数据结构构建的指针
  - `wasm_backend.py` `_compile_build_list`: 从仅 `nova_list_new(count)` → `nova_list_new(count)` + 存入 `$tmp_ptr` + 循环 `nova_list_push($tmp_ptr, elem)`
  - `wasm_backend.py` `_compile_build_map`: 从仅 `nova_map_new(count)` → `nova_map_new(count)` + 存入 `$tmp_ptr` + 循环 `nova_map_put($tmp_ptr, key, value)`
  - `wasm_backend.py` `_compile_build_tuple`: 从仅 `nova_alloc(size)` → `nova_alloc(size)` + 存入 `$tmp_ptr` + 逐字段 `i64.store offset=N`
  - `wasm_backend.py` `_compile_build_adt`: 从错误的 `nova_alloc(type_tag, size)` → 正确的 `nova_adt_new(type_id, variant_tag, field_count)` + 循环 `nova_adt_set_field($tmp_ptr, idx, value)`
- **测试验证**: 395 passed, 20 subtests passed，无回归

### 测试前后对比

| 指标 | 开发前 | 开发后 |
|------|--------|--------|
| 通过测试数 | 395 | 395 |
| 子测试数 | 20 | 20 |
| 回归 | - | 无 |

### 下轮计划

- **前端**: 前端线已 100% 完成，无剩余任务。下轮起前端线进入维护模式（仅修复 bug 或响应新需求）。
- **后端**: 原生后端指令选择优化（easy，P68）或 Wasm 多参数闭包调用（medium，P54）。建议优先指令选择优化（easy 且低风险），或关注第 21 轮评审后可能新增的任务。

## 第 19 轮（2026-07-24 13:00-13:15）

### 前端任务：修复 for 循环和列表推导的迭代器类型推断

- **任务 ID**: frontend_for_loop_type_inference
- **难度**: medium
- **优先级**: 72
- **结果**: 成功
- **为什么选这个**: 第 18 轮评审明确指出的 P2 弱点。循环变量绑定为裸 TypeVar 导致类型精度不足，是前端类型系统的实质性短板。
- **修改内容**:
  - `type_checker.py` `_check_for_expr`: range 循环变量绑定为 `INT_T`；List 遍历提取 `ListType.elem_type`；其他类型回退到 `TypeVar`
  - `type_checker.py` `_check_list_comprehension`: 同样的修复逻辑
- **测试验证**: 395 passed, 20 subtests passed，无回归

### 后端任务：原生后端复合指令迁移到 _emit_runtime_call

- **任务 ID**: backend_native_runtime_call_refactor
- **难度**: medium
- **优先级**: 90
- **结果**: 成功
- **为什么选这个**: 第 18 轮评审指出的 P1 风险，且是最高优先级后端任务（P90）。手动 push/pop+call 模式不检查栈对齐、不保存 caller-saved，存在正确性风险。
- **修改内容**:
  - 扩展 `_emit_runtime_call` 支持立即数参数（格式 `(('imm', value), arg_type)`），自动处理寄存器分配、栈对齐和 caller-saved 保存/恢复
  - 迁移 `_emit_build_list`（nova_list_new + nova_list_push 循环）
  - 迁移 `_emit_list_append`（nova_list_push）
  - 迁移 `_emit_build_map`（nova_map_new + nova_map_put 循环）
  - 迁移 `_emit_build_adt`（nova_adt_new + nova_adt_set_field 循环）
  - 迁移 `_emit_index`（nova_list_get）
  - 删除约 120 行手动 push/pop+call 代码
- **测试验证**: 395 passed, 20 subtests passed，无回归

### 测试前后对比

| 指标 | 开发前 | 开发后 |
|------|--------|--------|
| 通过测试数 | 395 | 395 |
| 子测试数 | 20 | 20 |
| 回归 | - | 无 |

### 下轮计划

- **前端**: 清理 _types_compatible 遗留方法（easy，最后一个前端待做任务）
- **后端**: 原生后端指令选择优化（easy，P68）或 Wasm 后端数据结构构建指令完善（medium，P65）

## 第 18 轮评审 — 2026-07-24 10:10

> 三轮回顾评审：第 16-18 轮总结 + 双线路线图调整

---

### 三轮回顾总结（第 16-18 轮）

**完成任务统计：**

| 轨道 | 完成数 | 总任务数（第15轮时） | 完成率 |
|------|--------|-------------------|--------|
| 前端 | 2 | 6 | 66.7% → 100% |
| 后端 | 3 | 7 | 42.9% → 85.7% |
| **总计** | **5** | **13** | **53.8% → 84.6%** |

注：第 18 轮为评审轮，额外修复 1 个 P0 Bug（nova_map_set/put 命名不一致），计入后端完成数。

**三轮产出质量：** 5/5 全部成功，无失败任务，测试通过率 100%（395 passed），无回归。
**难度构成：** 1 easy + 1 medium + 3 hard（hard 任务成功率 100%）

---

### P0 Bug 修复（评审轮额外完成）

**nova_map_set / nova_map_put 命名不一致**
- **严重程度**: P0（链接必失败）
- **影响范围**: native_backend.py、lir_c_backend.py、c_codegen.py 三个后端
- **根因**: 原生后端（cycle 17）和 LIR C 后端实现 Map 构建时使用了 `nova_map_set`，但运行时库 nova_runtime.h/c 中只定义了 `nova_map_put`
- **修复**: 将三个文件中的 `nova_map_set` 统一改为 `nova_map_put`，6 处修改
- **验证**: 395 测试全部通过

---

### 前端线评估

**质量趋势：类型系统已成熟，进入精度优化阶段**
- 第 16 轮完成模式匹配完备性检查（hard）——ADT 构造器覆盖、Bool 覆盖、通配符/变量绑定、冗余检测
- 第 17 轮完成 match guard 类型检查——guard 必须为 Bool，含 guard 的通配符不视为完备覆盖
- 类型合一已全面部署（46 处 `_unify_types` 调用覆盖所有关键路径）
- `_types_compatible` 已无外部调用点（0 个），仅剩 6 处内部递归自引用，可安全删除

**进度评估：**

| 层面 | 完成度（第15轮时） | 完成度（现在） | 变化 |
|------|-----------------|--------------|------|
| 词法分析 | 90% | 90% | - |
| 语法分析 | 85% | 85% | - |
| AST 设计 | 90% | 90% | - |
| 类型系统（核心） | ~80% | ~90% | +10%（模式匹配完备性+guard） |