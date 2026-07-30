# Nova 前后端专项开发路线图

**更新时间**: 2026-07-30
**上次评审**: 第 57 轮
**当前评审**: 第 60 轮
**当前轮次**: 第 61 轮
**下次评审**: 第 63 轮

本路线图由前后端专项开发系统维护，专注于前端类型系统和后端代码生成的核心功能开发。

## 进度概览

| 轨道 | 总数 | 已完成 | 待做 | 废弃 | 完成率 |
|------|------|--------|------|------|--------|
| 前端 | 44 | 41 | 3 | 3 | **93.2%**（第 61 轮 +1，测试盲区补齐完成） |
| 后端 | 72 | 48 | 9 | 10 | **66.7%**（第 61 轮 +1，P1-4 MIR Phi 一致性清零） |
| **总计** | **116** | **89** | **12** | **13** | **76.7%**（+1.7pp） |

## 前端开发线

**状态：维护模式（41/44 = 93.2%，code_audit_60 3 项清零 1/3）—— 下阶段主攻 ForExpr 静默降级 + parser 错误恢复扩展**

前端核心功能全部完成。第 61 轮完成 P2 级测试盲区补齐：type_checker.py 8/12 类核心错误零测试的场景全部补上（+15 用例，1099→1114 passed）。code_audit_60 3 项清零 1/3。

### 第 60 轮评审新增 3 个前端任务

| 任务 | 难度 | 优先级 | 严重度 | 状态 | 轮次计划 |
|------|------|--------|--------|------|----------|
| **补齐 type_checker 8 类核心测试盲区**（Let/Mut/函数返回/Lambda/For/赋值/推导式/注解语法 + ADT 构造器，~15 用例） | easy | **95** | P2 | ✅ **已完成（第 61 轮，+15 测试，0 回归）** | 第 61 轮 ✅ |
| **修复 ForExpr iterable 非 List 静默降级为 TypeVar**（类型系统漏洞） | easy | **88** | P1 | 待做 | **第 62 轮**（前端主攻，30min 小任务可与后端任务并行） |
| **parser 错误恢复计数器扩展**（BLOCK_MAX_ERRORS → TOP_LEVEL/STMT_LIST/EXPR 三级，6 个单测） | medium | 78 | P2 | 待做 | 第 63 轮 |

### 第 57 轮评审遗留 3 个前端任务进度

| 任务 | 难度 | 优先级 | 严重度 | 状态 | 轮次计划 |
|------|------|--------|--------|------|----------|
| 统一 type_checker 所有报错走 _error() 出口 + match 错误补 source_code（P2-1+P2-3 合并） | medium | 75 | P2 | ✅ 已完成（第 59 轮，使用率 100%） | 第 59 轮 |
| 补齐 test_type_checker.py 核心模块测试盲区（12 类场景，~15 个用例） | easy | 65→**95**↑ | P2 | ✅ **已完成（第 61 轮，+15 用例，0 回归）** | 第 61 轮 ✅ |
| Parser Map/Block 歧义探测静默吞错文档化 + 错误恢复单测补齐 | easy | 45 | P2 | ✅ 已完成（第 58 轮） | 第 58 轮 |

### code_audit_60 发现清单（前端 3 项，1/3 清零）

| 发现 | 位置 | 影响 | 严重度 | 状态 |
|------|------|------|--------|------|
| **ForExpr iterable 非 List 静默降级为 TypeVar（不抛类型错）** | type_checker.py L820-825 | `for x in "string"` / `for x in 42` 等语义错误代码类型检查静默通过，后续 x 类型使用全部污染为 TypeVar | **P1 前端正确性** | 🔴 待修复（第 62 轮，frontend_for_expr_non_list_fix, P88） |
| **type_checker 12 类核心错误中 8 类零测试** | test_type_checker.py 全文件 | Let/Mut 注解错、函数返回错、Lambda 多态推断、ForExpr 错、赋值错、ListComprehension 错、类型注解语法错、ADT 构造器字段错——均无回归测试 | P2 测试覆盖 | ✅ **已清零（第 61 轮，+15 用例覆盖 8 大类）** |
| **parser 错误恢复计数器 BLOCK_MAX_ERRORS 仅覆盖 _parse_block()** | parser.py 多处（L503 定义，仅 L564 使用） | 顶层声明/语句列表/表达式级的连续语法错误无熔断，产生雪崩式 10+ 条错误消息，IDE 体验差 | P2 可维护性 | 🔴 待修复（第 63 轮，frontend_parser_error_recovery_full, P78） |

### 审计发现清单（P2 已清零 3/3 —— 第 57 轮审计遗留）

| 发现 | 位置 | 影响 | 严重度 | 状态 |
|------|------|------|--------|------|
| type_checker.py 44 处裸 raise TypeCheckError 未走 _error() 统一出口 | type_checker.py L479-1898 多处 | 约 40% 报错路径无 source_code 和 `-->` 标记 | P2-1 | ✅ **已清零**（第 59 轮，使用率 100%） |
| match 错误手动传 line/col 但缺少 source_code（无 `-->` 标记） | type_checker.py L1477-1576 | match 不完备/冗余报错缺少源码上下文 | P2-3 | ✅ **已清零**（第 59 轮，合并入 P2-1 同一任务） |
| parser.py _parse_brace_primary 静默吞错缺少注释说明 | parser.py L1077 | Map/Block 歧义探测意图不明易被误改 | P2-2 | ✅ 已清零（第 58 轮） |

### 核心能力清单（全部已稳定）

- Hindley-Milner 类型推断（含 let-polymorphism）
- 泛型参数数量校验 + 参数化类型实例化
- 模式匹配完备性检查（ADT / Bool / Tuple / List / 嵌套子模式 / 无限域判定）
- 冗余分支检测（guard 通配符排除 / NaN 安全 / 字面量集合去重）
- Parser Panic Mode 错误恢复（声明边界 + 语句边界双同步点，BLOCK_MAX_ERRORS=3 防风暴）
- TypeCheckError 统一 _error() 出口（**100% 使用率**，44/44 已迁移，含 span→expr→属性三级回退）

## 后端开发线

### 紧急问题清零看板（P0/P1/P2，第 57 轮评审新发现 9 项，✅ 9/9 全部清零）

| 严重度 | 编号 | 问题 | 对应任务 | 优先级 | 预计轮次 | 状态 |
|--------|------|------|----------|--------|----------|------|
| **P0** | P0-1 | Native 完整 ELF 模式 external_calls 偏移 0 | backend_native_elf_external_calls | **99** | 第 58 轮 | ✅ **已清零**（第 58 轮） |
| P1 | P1-1 | Native XMM caller-saved 寄存器跨 call 未保存 | backend_native_xmm_caller_saved | 90 | 第 58 轮 | ✅ **已清零**（第 58 轮，含 x86_64 emitter SIB bug 修复） |
| P1 | P1-2 | Native ELF PT_LOAD p_offset/p_vaddr 对齐违规 | backend_native_ptload_align | 88 | 第 58 轮 | ✅ **已清零**（第 58 轮） |
| P1 | P1-3 | C 后端 nova_alloc/malloc NULL 未检查 | backend_c_alloc_null_check | 85 | 第 59 轮 | ✅ **已清零**（第 59 轮，同步修复 nova_panic 单参数调用 bug） |
| P1 | **P1-4** | **MIR Phi 节点类型取第一个源 SSA 不做一致性校验（正确性致命）** | **backend_mir_phi_type_consistency** | **98**↑ | **第 61 轮**（后端头号主攻） | ✅ **已清零（第 61 轮，9/9 里程碑达成）** |
| P1 | P1-5 | LIR terminator SSA 位置找不到时默认空字符串 | backend_lir_term_ssa_defensive | 78 | 第 59 轮 | ✅ **已清零**（第 59 轮，7 处全部替换为 _require_ssa_loc） |
| P2 | P2-1 | type_checker 44 处裸 raise 未走 _error() | frontend_typecheck_unify_error_exit | 75 | 第 59 轮 | ✅ **已清零**（第 59 轮，P2-3 合并清零） |
| P2 | P2-2 | Parser _parse_brace_primary 静默吞错无注释 | frontend_parser_brace_doc | 45 | 第 58 轮 | ✅ **已清零**（第 58 轮） |
| P2 | P2-3 | match 错误缺 source_code（无 `-->` 标记） | （合并入 P2-1） | — | 第 59 轮 | ✅ **已清零**（第 59 轮，合并入 P2-1） |

**3 轮清零计划（第 58-60-61 轮）进度**：P0×1 + P1×5 + P2×3 = 9 项，✅ **9/9 全部清零**（第 58 轮 3/9、第 59 轮 5/9、第 61 轮 9/9 里程碑达成）。Nova 编译器后端正确性达到"工业级可用"基线。

### code_audit_60 新发现（后端 3 项，1/3 清零）

| 严重度 | 编号 | 问题 | 对应任务 | 优先级 | 预计轮次 | 状态 |
|--------|------|------|----------|--------|----------|------|
| **P1** | P1-4（审计升级） | MIR Phi 类型取第一个分支即 break，其余分支类型完全忽略 → Int/Float/String 混用产生灾难性错代码 | backend_mir_phi_type_consistency | **98**↑ | **第 61 轮** | ✅ **已清零（第 61 轮）** |
| P2 | 60-B2 | lir_lowering.py 32 处非 terminator 指令仍 `get(ssa, "")` 静默回退空字符串 → 无效操作数或非法 C 表达式 | backend_lir_nonterm_ssa_strict | 80 | **第 62 轮** | 🔴 待修复（稳定性） |
| P2 | 60-B3 | native_backend.py Top2 复杂度：_emit_runtime_call CC=25、_emit_call CC=21 → 4 条 call 路径 XMM 保存修改需同步（第 58 轮真实踩坑） | backend_native_emit_complexity_refactor | 85 | **第 63 轮** | 🔴 待修复（可维护性） |

### 高优先级任务（下 3 轮，按优先级排序 — 第 61 轮 2/2 完成 ✅）

| 状态 | 任务 | 严重度 | 难度 | 优先级 | 预计 | 轮次计划 |
|------|------|--------|------|--------|------|----------|
| ✅ **第 61 轮头号主攻（完成）** | **修复 MIR Phi 节点类型不做一致性校验（P1-4）** | P1 | medium | **98** | 3-5h | **第 61 轮 后端** ✅（9/9 清零里程碑） |
| ✅ **第 61 轮前端主攻（完成）** | **补齐 test_type_checker 8 类核心测试盲区（+15 用例）** | P2 | easy | **95** | 4-6h | **第 61 轮 前端** ✅（+15 测试，0 回归） |
| 🔴 **第 62 轮后端主攻** | **lir_lowering 32 处非 terminator get(ssa,"") 静默回退 → _require_ssa_loc** | P2 | medium | 80 | 2-4h | **第 62 轮 后端**（稳定性） |
| 🔴 **第 62 轮前端小修** | **ForExpr iterable 非 List 静默降级修复**（30min 级） | P1 前端 | easy | **88** | 30-60min | **第 62 轮 前端**（类型系统漏洞） |
| 🔴 **第 63 轮后端主攻** | **native_backend _emit_runtime_call CC=25 + _emit_call CC=21 子方法拆分** | P2 | hard | 85 | 1-2d | **第 63 轮 后端**（可维护性 Top1+Top2） |
| 🔴 **第 63 轮前端主攻** | **parser 错误恢复计数器扩展（TOP_LEVEL/STMT_LIST/EXPR 三级）** | P2 | medium | 78 | 2-3h | **第 63 轮 前端**（错误恢复完整性） |

### 已完成的 P0/P1 历史清零里程碑

| 编号 | 问题 | 清零轮次 | 对应任务 |
|------|------|----------|----------|
| P0-1（最新） | Native 完整 ELF 模式 external_calls 偏移 0（独立二进制崩溃） | **第 58 轮** | backend_native_elf_external_calls |
| P0-回归 | 二元运算 RCX 临时寄存器覆盖活跃 vreg | 第 49 轮 | backend_native_regalloc_loop_regression |
| P0-新1 | 三后端未实现指令静默跳过/注释 | 第 40 轮 | backend_unified_silent_skip_fix |
| P0-B1 | native_backend 无链接器（ELF 不可执行） | 第 37 轮 | backend_native_linker_strategy |
| P0-2 | wasm_backend fn_ptr 传 NULL（闭包完全不可用） | 第 34 轮 | backend_wasm_fn_ptr |
| P0-1（旧） | native_backend fn_ptr 传 NULL | 第 31 轮 | backend_native_fn_ptr_tramp |
| P0-3 | lir_lowering 未处理 SSA callee（闭包调用错误编译） | 第 28 轮 | backend_lir_callee_ssa |
| P0-新2 | Cranelift 后端未实现指令降级为 TODO 注释 | 第 52 轮 | backend_cranelift_todo_fatal |
| P1-1（最新） | Native XMM caller-saved 寄存器跨 call 未保存 + x86_64 emitter RSP SIB bug | **第 58 轮** | backend_native_xmm_caller_saved |
| P1-2（最新） | Native ELF 数据段 PT_LOAD p_offset/p_vaddr 对齐违规 | **第 58 轮** | backend_native_ptload_align |
| P1-新1 | Native 后端缺失 LIRLoadGlobal/LIRStoreGlobal | 第 41 轮 | backend_native_global_var_support |
| P1-2（旧） | 浮点立即数 NotImplementedError | 第 38 轮 | backend_native_float_imm |
| P1-B2 | 寄存器分配器不感知调用点（低效） | 第 47 轮 | backend_native_regalloc_call_site |
| P1-B3 | 原生后端无端到端执行测试（正确性无验证） | 第 46 轮 | backend_native_elf_e2e_exec |
| P1-新2 | Native 后端浮点全局变量存储错误 | 第 53 轮 | backend_native_float_global_store |
| P1-新3 | C 后端闭包间接调用浮点返回丢失 + 内存泄漏 + bool cast | 第 55 轮 | backend_c_closure_double_return |
| P2-D | 闭包临时内存泄漏（C/Wasm） | 第 50 轮 | backend_closure_memory_leak_fix |
| P2-F | Native 独立 ELF 跳过外部函数重定位 | 第 46 轮 | backend_native_relocatable_elf_link_fix |
| P2-A | C 后端 trampoline double 返回值 UB | 第 35 轮 | backend_c_trampoline_double_fix |
| P2-新1 | Phi 拷贝源缺失静默跳过（潜在使用未初始化寄存器） | 第 56 轮 | backend_phi_copy_missing_error |
| P2-2（最新） | Parser _parse_brace_primary Map/Block 歧义探测静默吞错缺注释 | **第 58 轮** | frontend_parser_brace_doc |

### 已废弃/降级任务（本轮新增 2 个）

| 状态 | 任务 | 原因 |
|------|------|------|
| **🗑️ 本轮废弃** | **实现 Wasm 后端栈平衡验证器（backend_wasm_stack_balance, P45）** | code_audit_60 重新评估：Unit→空字符串映射经审计一致、dispatch loop return 策略一致、极端控制流无实际测试失败。Wasm 后端测试 58/58 全部通过，无真实栈不平衡 bug。优先级 45 低于后端 Top3 积压（P1-4 P98、32 处静默 P80、复杂度 P85）。**推迟到 WasmGC 实际使用时再引入**（ROI < 0）。 |
| **🗑️ 本轮废弃** | **添加 Wasm 后端 WAT 缩进深度断言（backend_wasm_wat_indent_verify, P35）** | code_audit_60 重新评估：label/branch/return/switch 四类块缩进配对经审计基本正确，缩进断言仅为风格约束不影响正确性。真实 Wasm 字节码生成正确性依赖 wasm-validate 而非缩进，WAT 缩进仅人读。优先级 35 为任务池最低。**直接废弃**，缩进问题作为 Code Review  checklist 项而非自动化测试任务。 |
| 废弃 | 收紧 TypeVar 兼容性判断（frontend_type_var_strict） | value restriction 长期项，前端进入维护模式 |
| 废弃 | 实现 Wasm 多参数闭包调用（backend_wasm_indirect_multiarg） | 并入 backend_wasm_closure_impl |
| 废弃 | 完善 WasmGC 原生类型定义（backend_wasm_gc_types） | 推迟到闭包后评估，闭包已完成无需再新增 |
| 废弃 | 统一 C 后端旧路径到 LIR 路径（backend_unify_c_codegen） | 降为维护模式，LIR 路径已覆盖 99% 场景 |
| 废弃 | backend_native_fn_ptr / backend_wasm_store_reg / backend_native_instr_selection / backend_c_todo_error | 分别并入后续任务或被更高优先级替代 |
| 废弃 | backend_native_runtime_link（旧 P70 hard，宽泛描述） | **第 57 轮评审废弃**——被更精确定位的 backend_native_elf_external_calls（P0 P99）替换，避免重复定义 |

### 历史已完成（47/72 = 65.3%，后端部分）

| 排名 | 任务组 | 代表任务 | 完成轮次 |
|------|--------|----------|----------|
| 1 | 寄存器分配体系 | 线性扫描寄存器分配器 / 调用点活跃切口 / 循环回归修复 | 43 / 47 / 48 |
| 2 | 原生后端 ELF 工具链 | 两阶段标签回填 / gcc 链接方案 / 可重定位 ELF / 端到端执行 | 19 / 37 / 45 / 46 |
| 3 | System V ABI 调用约定 | 栈帧管理 / ABI 调用约定 / 外部运行时复合指令 | 27 / 29 / 31 |
| 4 | 三后端闭包全栈支持 | MIR Lambda 降级 / LIR SSA callee / C/Wasm/Native 三后端实现 | 28 / 42 / 45 / 32 / 34 |
| 5 | 浮点立即数 & 全局存储 | 浮点立即数加载 / 浮点返回值处理 / 浮点全局存储（P1-新2） | 38 / 44 / 53 |
| 6 | C 后端健壮性 | trampoline double UB 修复 / 闭包双精度返回丢失清零（P1-新3）+ malloc NULL 检查（P1-3） | 35 / 55 / 59 |
| 7 | Phi & 控制流降级 | Phi 边缘块 / MatchJump 后继不全 / 并行拷贝语义防御 / terminator SSA 防御（P1-5） | 19 / 23 / 56 / 59 |
| 8 | Cranelift 安全基线 | 未知指令从 TODO 注释改为 NotImplementedError（P0-新2 清零） | 52 |
| 9 | Native 外部运行时 | 运行时调用重构 / bug 修复 / 闭包内存泄漏清零 + external_calls 静态 stub（P0-1） | 34 / 40 / 50 / 58 |
| 10 | 三后端静默跳过统一 | C/Wasm/Cranelift 三后端未知指令从静默改为异常 | 40 |

## 各后端完成度排名（第 58 轮三连修复后 → 第 60 轮评审微调）

| 排名 | 后端 | 完成度 | 变化 | 关键缺失（按严重度排序） |
|------|------|--------|------|--------------------------|
| 1 | **C 后端** | **~90%** | ↑5pp（P1-3 malloc NULL + nova_panic 签名修复） | 边界类型映射子串误判（低优，~3%）、MIR Phi 类型一致性影响 C 后端（P1-4 通用 MIR 层缺陷，非 C 后端独有） |
| 2 | **原生后端** | **~85%** | 持平（第 58 轮 ↑15pp 后稳定） | P1-4 通用 MIR Phi 缺陷、闭包场景 caller-saved 全保存优化（低优）、_emit_runtime_call/_emit_call 高 CC 可维护性债、复杂结构体字段对齐（低优） |
| 3 | **WasmGC 后端** | **~78%** | 持平 | MIR Phi 类型一致性影响（P1-4 通用层）、端到端验证缺失（无 wasmtime 实际跑 Nova 程序的 e2e 测试）、栈平衡/缩进断言经本轮评估 ROI<0 已废弃 |
| 4 | **Cranelift 后端** | **~35%** | 持平 | 大量指令未实现（安全基线已达标：未知指令抛 NotImplementedError 不静默）；弃用路线不变（v0.5.0 移除） |

### 原生后端完成度说明（稳定 ~85%，第 58 轮三连修复后）

第 57 轮审计后三大阻塞问题（P0×1 + P1×2）在第 58 轮一轮内全部清零，效果持续：

1. ✅ **P0-1 external_calls 偏移为 0 → 清零**：_generate_elf 新增第 5.55 节，在 code 段末尾追加 11 类 x86_64 汇编 stub（noop/nova_alloc 用 brk 系统调用/nova_panic 用 write+exit/nova_list_new/Map/ADT/assert），回填所有 external_calls 的 call rel32。静态 ELF 独立运行不再 SIGSEGV。
2. ✅ **P1-1 XMM caller-saved + emitter SIB bug → 清零**：定义 CALLER_XMMS=[XMM0..XMM7]，4 条 call 路径（_emit_call/_emit_runtime_call/_emit_closure_create/_emit_call_indirect）均在 GPR 保存后分配 64 字节 XMM 区 movsd 存/取。同步修复 x86_64 emitter movsd_mem_reg/movsd_reg_mem RSP 基址缺少 SIB 字节的底层 bug。
3. ✅ **P1-2 PT_LOAD 对齐违规 → 清零**：code 段末尾用 0x90 NOP 填充到页对齐，data_offset 本身对齐，p_vaddr = base_addr+data_offset，实现 p_offset%4096 = p_vaddr%4096 = 0。

**下阶段 Native 后端优先级排序**：(1) 通用 MIR 层 P1-4 修复（先修复正确性，native 后端自动受益）→ (2) lir_lowering 32 处静默回退（稳定性，native 后端同样受益）→ (3) native_backend 自身 Top2 复杂度重构（可维护性）。正确路线：先修 MIR/LIR 通用层缺陷，再优化 native 后端自身。

---

## 前后端平衡评估（第 60 轮评审结论）

### 客观指标对比

| 维度 | 前端 | 后端 | 比例 | 结论 |
|------|------|------|------|------|
| 测试数量（用例） | ~221（lexer 21 + parser 89 + type_checker 111） | ~224（native 53 + ir 63 + c_codegen 50 + backends 58） | **1:1.01** | ✅ 测试数量均衡 |
| 核心代码行数 | 4,352（lexer 415 + parser 1263 + type_checker 2109 + ast 565） | 8,898（native 2708 + wasm 955 + c_backend 1036 + mir 1786 + lir 851 + pass 1562） | **1:2.04** | ⚠️ 后端代码量 2×，后端单测密度仅为前端一半 |
| 最近 3 轮任务分布（57/58/59） | 3 个（3:1 倾斜前端） | 1 个（高复杂度 backend_native_closure_e2e_test） | 3:1 | ⚠️ 后端硬骨头（P1-4、复杂度重构、32 处静默）连续 3 轮推迟未动 |
| 积压正确性风险 | 1 项（ForExpr 静默降级 P1 前端） | 2 项（MIR Phi P1-4 正确性致命 + 32 处静默稳定性） | 1:2 | ⚠️ 后端积压 2 倍 |

### 平衡结论

**下 3 轮（第 61-62-63 轮）建议比例 = 前端:后端 = 1:2**，具体节奏：

| 轮次 | 前端任务（估算代码量） | 后端任务（估算代码量） |
|------|------------------------|------------------------|
| **第 61 轮** | 测试盲区补齐前 4 类（Let/Mut/函数返回/Lambda，~8 用例，+300 行测试） | **P1-4 MIR Phi 类型一致性修复**（+80-120 行修复 + ~10 个类型冲突测试） |
| **第 62 轮** | 测试盲区补齐后 4 类（For/赋值/推导式/注解语法 + ADT 构造器，~7 用例，+200 行） **+** ForExpr 静默降级修复（+30-50 行，30min） | lir_lowering 32 处非 terminator 静默回退替换（+100-150 行防御 + ~5 个单测） |
| **第 63 轮** | parser 错误恢复计数器扩展（TOP_LEVEL/STMT_LIST/EXPR，+100-150 行 + 6 个单测） | native_backend _emit_runtime_call CC=25 + _emit_call CC=21 拆分子方法（+400-500 行重构，零回归） |
| **合计 3 轮** | 前端工作包 × 4（~680 行新增/修改） | 后端工作包 × 3（~750 行新增/修改） | ~**1:1.1**（实际工作量均衡，因后端任务复杂度更高；若某轮后端任务超时可推迟前端 parser 修复到第 64 轮） |
