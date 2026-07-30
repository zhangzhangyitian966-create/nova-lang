# Nova 前后端专项开发路线图

**更新时间**: 2026-07-30
**上次评审**: 第 60 轮
**当前评审**: 第 63 轮
**当前轮次**: 第 64 轮
**下次评审**: 第 66 轮

本路线图由前后端专项开发系统维护，专注于前端类型系统和后端代码生成的核心功能开发。

## 进度概览

| 轨道 | 总数 | 已完成 | 待做 | 废弃 | 完成率 |
|------|------|--------|------|------|--------|
| 前端 | 47 | 43 | 2 | 4 | **91.5%**（第 64 轮 parser 三级错误恢复清零） |
| 后端 | 78 | 50 | 6 | 11 | **64.1%**（第 64 轮 _allocate_registers CC=39 拆分清零） |
| **总计** | **125** | **93** | **8** | **15** | **74.4%**（第 64 轮普通开发，2/2 任务全部成功） |

> **评审轮校准说明**：第 63 轮评审新增 5 个高价值任务（前端 3：generalize/TypeVar 守卫/parser 错误恢复；后端 2：regalloc CC 拆分/emit_abi_call 骨架抽离/Phi 升级 raise/WasmGC 指令补齐 = 实际后端新增 4，废弃 backend_lir_phi_lowering_verify），分母从 116 调整为 125。

## 前端开发线

**状态：小步精修阶段（质量 8.6/10，↑0.4 vs 第 60 轮）—— 核心类型系统 + 错误恢复完整性是下阶段主题**

前端核心功能全部稳定。第 62 轮清零 ForExpr 非 List 迭代器静默降级漏洞（P1 前端正确性），_error() 统一出口使用率 100%（第 59 轮），模式完备性/冗余检查/字面量去重全部成熟。

### 第 63 轮评审新增 3 个前端任务（HM 完整性 + 错误恢复闭环 + TypeVar 泄漏守卫）

| 任务 | 难度 | 优先级 | 严重度 | 状态 | 轮次计划 |
|------|------|--------|--------|------|----------|
| **实现 generalize() + 补全 let-polymorphism**（HM 核心能力缺失 Top1，id/const/compose 等多态函数） | hard | **93** | P1 | 待做 | **第 65 轮**（前端主攻，HM 完整性 65%→85%） |
| **parser 错误恢复计数器扩展**（TOP_LEVEL/STMT_LIST/EXPR 三级 + 顶层熔断） | medium | **85** | P2 | ✅ **已完成（第 64 轮，6/6 专项测试通过，0 回归）** | **第 64 轮 ✅**（前端主攻，code_audit_60 前端 3/3 清零） |
| **TypeVar 泄漏守卫 + 递归 ADT Occur Check 豁免**（封堵后端未约束 TypeVar + 自定义链表/树 ADT 误杀） | medium | **80** | P2 | 待做 | **第 66 轮**（前端主攻） |

### 第 60 轮评审新增 3 个前端任务进度（3/3 已清零 🎉）

| 任务 | 难度 | 优先级 | 严重度 | 状态 | 轮次计划 |
|------|------|--------|--------|------|----------|
| **补齐 type_checker 8 类核心测试盲区**（Let/Mut/函数返回/Lambda/For/赋值/推导式/注解语法 + ADT 构造器，+15 用例） | easy | **95** | P2 | ✅ **已完成（第 61 轮，+15 测试，0 回归）** | 第 61 轮 ✅ |
| **修复 ForExpr iterable 非 List 静默降级为 TypeVar**（类型系统漏洞，for x in 42/"string"/true 三类场景） | easy | **88** | P1 | ✅ **已完成（第 62 轮，+3 测试净增 2，0 回归）** | 第 62 轮 ✅ |
| **parser 错误恢复计数器扩展**（BLOCK_MAX_ERRORS → TOP_LEVEL/STMT_LIST/EXPR 三级，6 个单测） | medium | 78→**85**↑ | P2 | ✅ **已完成（第 64 轮，+6 专项测试 6/6 通过，0 回归）** | **第 64 轮 ✅**（code_audit_60 前端 3 项 3/3 清零里程碑达成） |

### code_audit_63 深度审计发现（前端 3 项，0/3 已清零）

| 发现 | 位置 | 影响 | 严重度 | 状态 |
|------|------|------|--------|------|
| **HM generalize() 完全缺失，let-polymorphism 不完整** | type_checker.py _check_binding_decl L466 env.define 前未泛化 | `let id = fn(x){x}; id(1); id("s")` 第二次调用失败（id 被合一为 Int→Int），HM 完成度仅 ~65% | **P1 语言表达能力天花板** | 🔴 **待修复（第 65 轮，frontend_let_polymorphism_generalize, P93）** |
| **TypeVar 静默泄漏到后端（空 List/Map、无注解参数、列表推导）** | type_checker.py 多处（L709 空列表/L730 空 Map/L508 无注解参数/L1126 LC 循环变量） | 未约束 TypeVar 被 _unify_and_resolve 保留，后端三后端 fallback 策略不一致（C void*/Native int/Wasm i32），行为不可预测 | **P2 稳定性 + 跨后端一致性** | 🔴 **待修复（第 66 轮，frontend_typevar_leak_guard, P80）** |
| **递归 ADT 被 Occur Check 误杀** | type_checker.py _occur_check L1909-1931 + _from_ast_type ADT 变体字段 | `type List a = Nil \| Cons a (List a)` 的 Cons 字段 `List a` 与参数 `a` 合一时触发 occur check 返回 False，用户自定义链表/树 ADT 无法编译 | **P2 语言可用性** | 🔴 **待修复（第 66 轮，合并入 frontend_typevar_leak_guard 同一任务）** |

### code_audit_60 遗留（前端 3 项，3/3 已清零 🎉）

| 发现 | 位置 | 影响 | 严重度 | 状态 |
|------|------|------|--------|------|
| **ForExpr iterable 非 List 静默降级为 TypeVar（不抛类型错）** | type_checker.py L820-825 | `for x in "string"` / `for x in 42` 等语义错误代码类型检查静默通过，后续 x 类型使用全部污染为 TypeVar | **P1 前端正确性** | ✅ **已清零（第 62 轮，三类场景断言抛错，line/col/source_code 位置正确）** |
| **type_checker 12 类核心错误中 8 类零测试** | test_type_checker.py 全文件 | Let/Mut 注解错、函数返回错、Lambda 多态推断、ForExpr 错、赋值错、ListComprehension 错、类型注解语法错、ADT 构造器字段错——均无回归测试 | P2 测试覆盖 | ✅ **已清零（第 61 轮，+15 用例覆盖 8 大类）** |
| **parser 错误恢复计数器 BLOCK_MAX_ERRORS 仅覆盖 _parse_block()** | parser.py 多处（L503 定义，仅 L564 使用） | 顶层声明/语句列表/表达式级的连续语法错误无熔断，产生雪崩式 10+ 条错误消息，IDE 体验差 | P2 可维护性 | ✅ **已清零（第 64 轮，TOP_LEVEL=5/EXPR=3/BLOCK=3 三级熔断 +6 专项测试 6/6）** |

### 核心能力清单（全部已稳定 + HM generalize 待补）

- Hindley-Milner 类型推断（含 let-polymorphism 实例化端 ✅，**泛化端 generalize ❌ 待补**）
- 泛型参数数量校验 + 参数化类型实例化
- 模式匹配完备性检查（ADT / Bool / Tuple / List / 嵌套子模式 / 无限域判定）
- 冗余分支检测（guard 通配符排除 / NaN 安全 / 字面量集合去重）
- Parser Panic Mode 错误恢复（**TOP_LEVEL/STMT_LIST/EXPR/BLOCK 四级熔断** ✅，_TOP_LEVEL_MAX_ERRORS=5/_EXPR_MAX_NESTED_ERRORS=3/_BLOCK_MAX_ERRORS=3）
- TypeCheckError 统一 _error() 出口（**100% 使用率**，44/44 已迁移，含 span→expr→属性三级回退）
- Union-Find + 路径压缩 + Occur Check（递归 ADT 豁免待补）

## 后端开发线

**状态：结构性改造启动（质量 7.7→7.9/10，↑0.2）—— Native 技术债 Top1 清零，下一步 Top2（_emit_abi_call 骨架）**

### 紧急问题清零看板（P0/P1/P2，code_audit_57 9 项 + code_audit_60 6 项 = 15 项累计，14/15 已清零）

#### code_audit_57 9 项里程碑（✅ 9/9 全部清零于第 61 轮达成）

| 严重度 | 编号 | 问题 | 对应任务 | 优先级 | 清零轮次 | 状态 |
|--------|------|------|----------|--------|----------|------|
| **P0** | P0-1 | Native 完整 ELF 模式 external_calls 偏移 0 | backend_native_elf_external_calls | **99** | 第 58 轮 | ✅ **已清零** |
| P1 | P1-1 | Native XMM caller-saved 寄存器跨 call 未保存 | backend_native_xmm_caller_saved | 90 | 第 58 轮 | ✅ **已清零** |
| P1 | P1-2 | Native ELF PT_LOAD p_offset/p_vaddr 对齐违规 | backend_native_ptload_align | 88 | 第 58 轮 | ✅ **已清零** |
| P1 | P1-3 | C 后端 nova_alloc/malloc NULL 未检查 | backend_c_alloc_null_check | 85 | 第 59 轮 | ✅ **已清零** |
| P1 | **P1-4** | **MIR Phi 节点类型取第一个源 SSA 不做一致性校验（正确性致命）** | **backend_mir_phi_type_consistency** | **98**↑ | **第 61 轮** | ✅ **已清零（里程碑）** |
| P1 | P1-5 | LIR terminator SSA 位置找不到时默认空字符串 | backend_lir_term_ssa_defensive | 78 | 第 59 轮 | ✅ **已清零** |
| P2 | P2-1 | type_checker 44 处裸 raise 未走 _error() | frontend_typecheck_unify_error_exit | 75 | 第 59 轮 | ✅ **已清零** |
| P2 | P2-2 | Parser _parse_brace_primary 静默吞错无注释 | frontend_parser_brace_doc | 45 | 第 58 轮 | ✅ **已清零** |
| P2 | P2-3 | match 错误缺 source_code（无 `-->` 标记） | （合并入 P2-1） | — | 第 59 轮 | ✅ **已清零** |

#### code_audit_60 6 项进度（5/6 已清零，剩余 1 项待第 65 轮攻坚）

| 严重度 | 编号 | 问题 | 对应任务 | 优先级 | 计划轮次 | 状态 |
|--------|------|------|----------|--------|----------|------|
| P1 | P1-4（审计升级） | MIR Phi 类型取第一个分支即 break，其余分支类型完全忽略 | backend_mir_phi_type_consistency | **98**↑ | **第 61 轮** | ✅ **已清零** |
| P2 | 60-B2 | lir_lowering.py 32 处非 terminator 指令仍 `get(ssa, "")` 静默回退空字符串 | backend_lir_nonterm_ssa_strict | 80 | **第 62 轮** | ✅ **已清零** |
| P2 | 60-B3 | native_backend.py Top2 复杂度：_emit_runtime_call CC=25、_emit_call CC=21 → 4 条 call 路径需同步修改 | **backend_native_regalloc_cc_split ✅ + backend_native_emit_abi_call_refactor**（评审轮拆分为两阶段） | 85→**92/90**↑ | **第 64/65 轮**（拆分攻坚） | 🔵 **1/2 已完成**（regalloc CC=39 拆分第 64 轮✅，emit_abi_call 骨架第 65 轮待做） |
| 前端×2 | ForExpr 静默降级 + 测试盲区补齐 | （见前端线） | frontend_for_expr_non_list_fix + frontend_typecheck_test_coverage | 88/95 | 第 61/62 轮 | ✅ **2/2 已清零** |

### code_audit_63 新发现（后端 3 项，1/3 已清零 —— 结构性改造启动）

| 严重度 | 编号 | 问题 | 对应任务 | 优先级 | 计划轮次 | 状态 |
|--------|------|------|----------|--------|----------|------|
| P2（可维护性 Top1） | 63-B1 | **_allocate_registers CC≈39（134 行 4 子阶段内聚，float/非 float 双路 8 份重复代码）** | **backend_native_regalloc_cc_split** | **92** | **第 64 轮（后端头号主攻）** | ✅ **已清零**（拆 3 子方法 + 1 流水线主方法，CC≤5 达成，53/53 native 测试通过） |
| P2（可维护性 Top2） | 63-B2 | **_emit_runtime_call CC≈31 + _emit_call CC≈24 两方法 70% 代码重复（10 步 ABI 流程几乎一致）** | **backend_native_emit_abi_call_refactor** | **90** | **第 65 轮（后端主攻）** | 🔴 待做（抽出 _emit_abi_call 通用骨架 + save_all_gprs/allow_imm 双 flag；depends_on regalloc 拆分已完成 ✅） |
| P1（正确性收尾） | 63-B3 | **_resolve_phi_type 仍在观察期 stderr 警告，未升级 raise MIRLoweringError（has_inconsistency 标志未消费）** | **backend_mir_phi_type_upgrade_raise** | **88** | **第 66 轮（后端主攻）** | 🔴 待做（已历 3 轮观察期 0 次警告，可安全升级） |

### 高优先级任务（下 2 轮 = 第 65-66 轮，按优先级排序 — 共 6 个任务 前端 2 + 后端 4）

| 状态 | 轮次 | 任务 | 严重度 | 难度 | 优先级 | 估算工作量 |
|------|------|------|--------|------|--------|------------|
| ✅ **第 64 轮完成** | **64** | **_allocate_registers CC=39 拆分 3 子方法（活跃分析/线性扫描+栈/caller-saved 标记 + 主方法流水线 CC≤5）** | P2 | hard | **92** | 1-2 天 |
| ✅ **第 64 轮完成** | **64** | **parser 错误恢复扩展 TOP_LEVEL/EXPR 两级 + BLOCK 复用（code_audit_60 前端 3/3 清零，+6 专项测试 6/6）** | P2 | medium | **85** | 2-3 小时 |
| 🔴 **第 65 轮后端主攻** | **65** | **抽离 _emit_abi_call 骨架消除 70% 重复（_emit_runtime_call/_emit_call/_emit_call_indirect 三调用点复用）** | P2 | hard | **90** | 1-2 天 |
| 🔴 **第 65 轮前端主攻** | **65** | **实现 generalize() + let-polymorphism（id/const/compose 等多态函数，HM 完成度 65%→85%）** | P1 | hard | **93** | 6-10 小时 |
| 🔴 **第 66 轮后端主攻** | **66** | **升级 _resolve_phi_type 从 stderr→raise MIRLoweringError（结束观察期，MIR 正确性强保证）** | P1 | medium | **88** | 2-4 小时 |
| 🔴 **第 66 轮后端次攻** | **66** | **WasmGC 后端补齐 LIRClosureCreate/LIRCallIndirect/LIRSwitch 3 个 NIE（4 后端断层从 48pp→≤30pp）** | P2 | medium | **75** | 4-6 小时 |
| 🔴 **第 66 轮前端主攻** | **66** | **TypeVar 泄漏守卫 + 递归 ADT Occur Check 豁免（封堵后端未约束 TypeVar + 自定义链表/树 ADT 误杀）** | P2 | medium | **80** | 3-5 小时 |
| 📝 废弃别名（向后兼容） | — | backend_native_emit_complexity_refactor（第 60 轮评审定义，实际功能与 backend_native_emit_abi_call_refactor 合并） | P2 | hard | 85 | — | **deprecated_alias**（不独立执行） |

### 已废弃/降级任务（本轮新增 1 个废弃 backend_lir_phi_lowering_verify）

| 状态 | 任务 | 原因 |
|------|------|------|
| **🗑️ 本轮废弃** | **backend_lir_phi_lowering_verify（Phi 降级验证菱形 CFG/并行拷贝/回边，P42）** | review_cycle_63 重新评估：MIR Phi 类型一致性已在 P1-4 修复后具备强保证；并行拷贝语义已在第 56 轮 backend_phi_copy_missing_error 做防御性兜底；当前 1116 全量测试 0 Phi 降级相关失败。优先级 42 < 新增 5 个高优任务（P75+），ROI 不足。**推迟到 SIMD/复杂结构体优化时再引入**。 |
| 🗑️ 第 60 轮废弃 | backend_wasm_stack_balance（Wasm 栈平衡验证器，P45） | 审计确认 58/58 Wasm 测试全过，无真实栈不平衡 bug，ROI<0 |
| 🗑️ 第 60 轮废弃 | backend_wasm_wat_indent_verify（WAT 缩进断言，P35） | 缩进仅为风格约束，不影响字节码正确性，真实依赖 wasm-validate |
| 废弃 | frontend_type_var_strict（收紧 TypeVar 兼容性） | value restriction 长期项，并入 frontend_let_polymorphism_generalize 时再考虑 |
| 废弃 | backend_wasm_indirect_multiarg / backend_wasm_gc_types / backend_unify_c_codegen | 分别并入更高优任务或降为维护模式（C 后端 LIR 路径已覆盖 99% 场景） |
| 废弃 | backend_native_fn_ptr / backend_wasm_store_reg / backend_native_instr_selection / backend_c_todo_error | 分别并入后续任务或被更高优先级替代 |
| 废弃 | backend_native_runtime_link（旧 P70 hard，宽泛描述） | **第 57 轮评审废弃**——被更精确定位的 backend_native_elf_external_calls（P0 P99）替换 |

### 各后端完成度排名更新（code_audit_63 深度审计后 — Native CC 债修正了完成度水分）

| 排名 | 后端 | 完成度 | 变化 | 关键缺失（按严重度排序） |
|------|------|--------|------|--------------------------|
| 1 | **C 后端** | **~88%** | ↑2pp（malloc NULL + nova_panic 签名修复 + Phi 一致性 MIR 层受益） | 边界类型映射子串误判（低优 ~3%）、未知指令抛 NotImplementedError 但安全基线已达标 |
| 2 | **原生后端（x86_64）** | **~82%** | ↓3pp（CC 债审计确认：_allocate_registers CC=39/_emit_runtime_call CC=31/_emit_call CC=24，可维护性拉低实际可用度） | ✅ P0-1/P1×2 三大正确性已清零；**Top 缺失 = 三大高 CC 方法可维护性**；寄存器分配溢出策略保守；复杂结构体字段对齐（低优） |
| 3 | **WasmGC 后端** | **~55%** | ↓5pp（审计确认 LIRClosureCreate/LIRCallIndirect/LIRSwitch 3 条指令为 NotImplementedError，闭包/间接调用/match 多臂场景会崩溃） | LIRClosureCreate / LIRCallIndirect / LIRSwitch 3 个 NIE（本轮新增任务 P75 补齐）；端到端 wasmtime 实际跑 Nova 程序 e2e 测试缺失 |
| 4 | **Cranelift 后端** | **~40%** | ↑5pp（安全基线已达标，未知指令抛 NIE，_compile_store_reg 虽 pass 但其他骨架式生成具备基础能力） | 大量指令未实现、弃用路线不变（v0.5.0 移除），不作为投入方向 |

**断层收敛目标**：第 66 轮后 Native→88%、WasmGC→70%、Cranelift→40%，4 后端最大差从 48pp→≤48pp（Cranelift 拖尾），有效可用三后端（C/Native/WasmGC）最大差 33pp→≤18pp。

---

## 前后端平衡评估（第 63 轮评审结论）

### 客观指标对比

| 维度 | 前端 | 后端 | 比例 | 结论 |
|------|------|------|------|------|
| 综合质量评分 | **8.6/10**（↑0.4 vs 第 60 轮） | **7.7/10**（↑0.7 vs 第 60 轮） | 领先 0.9 分 | 后端增速更快但差距仍大（结构性改造差距） |
| 测试数量（用例） | ~221（lexer 21 + parser 89 + type_checker 111） | ~224（native 53 + ir 63 + c_codegen 50 + backends 58） | **1:1.01** | ✅ 测试数量均衡 |
| 核心代码行数 | 4,352（lexer 415 + parser 1263 + type_checker 2109 + ast 565） | 8,898（native 2708 + wasm 955 + c_backend 1036 + mir 1786 + lir 851 + pass 1562） | **1:2.04** | ⚠️ 后端代码量 2×，后端单测密度为前端一半，代码维护压力更大 |
| 最近 3 轮任务分布（60-61-62） | 评审×1 + 开发×2 = 2 开发任务（测试盲区+ForExpr） | 评审×1 + 开发×2 = 2 开发任务（MIR Phi + 32 处 SSA） | **1:1**（符合第 60 轮评审 1:2 建议的后端倾斜 — 实际 1:1 但后端任务代码量是前端 2-3 倍） | ✅ 实际工作量后端略多，节奏合理 |
| 积压正确性风险（P0/P1） | 1 项（HM generalize P1 语言能力） | 1 项（Phi 升级 raise P1 正确性收尾） | 1:1 | ✅ 两端 P1 积压已几乎持平（前端是能力级 P1，后端是收尾级 P1） |
| 积压可维护性风险（P2） | 2 项（parser 错误恢复扩展 P85 + TypeVar 泄漏 P80） | 4 项（regalloc CC 拆分 P92 + emit_abi_call 骨架 P90 + WasmGC 3 NIE 补齐 P75 + 1 废弃） | 1:2 | ⚠️ 后端 P2 积压 2×，技术债堆积更重 |

### 平衡结论与资源配比建议

**下 3 轮（第 64-65-66 轮）资源配比 = 前端 35% / 后端 65%**，较第 60 轮评审建议的 1:2（≈33%:67%）基本一致，前端略增加 2pp（因 generalize P1 hard 任务需投入）。具体节奏：

| 轮次 | 前端任务（估算代码量） | 后端任务（估算代码量） | 前端:后端 代码比 |
|------|------------------------|------------------------|------------------|
| **第 64 轮** | parser 错误恢复 TOP_LEVEL/STMT_LIST/EXPR 三级扩展（~150-200 行 parser.py + ~150 行测试） | **_allocate_registers CC=39 拆分 4 子方法**（~350-450 行 native_backend.py + ~150 行测试） | ~**1:2**（后端代码量 2×，符合配比） |
| **第 65 轮** | **实现 generalize() + let-polymorphism（HM 完整性 ~150-200 行 type_checker.py + ~200 行测试）** | **抽离 _emit_abi_call 通用骨架（~400 行 native_backend.py + ~100 行测试）** | ~**1:1.5**（前端 hard 任务量提升） |
| **第 66 轮** | TypeVar 泄漏守卫 + 递归 ADT Occur Check 豁免（~80-120 行 type_checker.py + ~150 行测试） | **Phi 升级 raise MIRLoweringError（~50 行 mir_lowering.py + ~150 行测试） + WasmGC 3 NIE 补齐（~250 行 wasm_backend.py + ~180 行测试）** | ~**1:2.5**（后端双任务并行，65% 配比达成） |
| **合计 3 轮** | 前端工作包 × 3（≈1,380 行新增/修改） | 后端工作包 × 4（≈2,030 行新增/修改） | ~**1:1.47**（按代码行数；按难度加权后约 1:1.8，符合 35:65 配比） |

**注**：若某轮后端 hard 任务（regalloc 拆分 / emit_abi_call 骨架）超时，可将前端次优任务（TypeVar 泄漏守卫）顺延至第 67 轮，保证 native_backend 结构性改造按期完成 — 这是后续所有 Native 后端优化/新指令的前置条件。
