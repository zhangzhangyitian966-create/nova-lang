# Nova 前后端专项开发路线图

**更新时间**: 2026-07-30
**上次评审**: 第 54 轮
**当前评审**: 第 57 轮
**当前轮次**: 第 59 轮
**下次评审**: 第 60 轮

本路线图由前后端专项开发系统维护，专注于前端类型系统和后端代码生成的核心功能开发。

## 进度概览

| 轨道 | 总数 | 已完成 | 待做 | 废弃 | 完成率 |
|------|------|--------|------|------|--------|
| 前端 | 42 | 40 | 2 | 1 | **95.2%** |
| 后端 | 68 | 47 | 13 | 8 | **69.1%** |
| **总计** | **110** | **87** | **15** | **9** | **79.1%** |

## 前端开发线

**状态：维护模式（40/42 = 95.2%，P2×3 已全部清零）**

前端核心功能全部完成。本轮（第 59 轮）完成 P2-1+P2-3 清零：type_checker.py 44 处裸 raise 全部迁移到 _error() 统一出口，match 错误补全 source_code；前端 P2×3 全部清零。

### 本轮新增（第 57 轮评审，共 3 个前端新任务）

| 任务 | 难度 | 优先级 | 严重度 | 状态 | 轮次计划 |
|------|------|--------|--------|------|----------|
| 统一 type_checker 所有报错走 _error() 出口 + match 错误补 source_code（P2-1+P2-3 合并） | medium | 75 | P2 | ✅ 已完成（第 59 轮） | 第 59 轮 |
| 补齐 test_type_checker.py 核心模块测试盲区（12 类场景，~15 个用例） | easy | 65 | P2 | 待做 | **第 60 轮**（评审轮剩余带宽） |
| Parser Map/Block 歧义探测静默吞错文档化 + 错误恢复单测补齐 | easy | 45 | P2 | ✅ 已完成（第 58 轮） | 第 58 轮 |

### 审计发现清单（P2 已清零 3/3）

| 发现 | 位置 | 影响 | 严重度 | 状态 |
|------|------|------|--------|------|
| type_checker.py 44 处裸 raise TypeCheckError 未走 _error() 统一出口 | type_checker.py L479-1898 多处 | 约 40% 报错路径无 source_code 和 `-->` 标记 | P2-1 | ✅ **已清零**（第 59 轮，frontend_typecheck_unify_error_exit, P75） |
| match 错误手动传 line/col 但缺少 source_code（无 `-->` 标记） | type_checker.py L1477-1576 | match 不完备/冗余报错缺少源码上下文 | P2-3 | ✅ **已清零**（第 59 轮，合并入 P2-1 同一任务） |
| parser.py _parse_brace_primary 静默吞错缺少注释说明 | parser.py L1077 | Map/Block 歧义探测意图不明易被误改 | P2-2 | ✅ 已清零（第 58 轮，frontend_parser_brace_doc, P45） |

### 核心能力清单（全部已稳定）

- Hindley-Milner 类型推断（含 let-polymorphism）
- 泛型参数数量校验 + 参数化类型实例化
- 模式匹配完备性检查（ADT / Bool / Tuple / List / 嵌套子模式 / 无限域判定）
- 冗余分支检测（guard 通配符排除 / NaN 安全 / 字面量集合去重）
- Parser Panic Mode 错误恢复（声明边界 + 语句边界双同步点，BLOCK_MAX_ERRORS=3 防风暴）
- TypeCheckError 统一 _error() 出口（100% 使用率，44/44 已迁移，含 span→expr→属性三级回退）

## 后端开发线

### 紧急问题清零看板（P0/P1/P2，第 57 轮评审新发现 9 项，已清零 7/9）

| 严重度 | 编号 | 问题 | 对应任务 | 优先级 | 预计轮次 | 状态 |
|--------|------|------|----------|--------|----------|------|
| **P0** | P0-1 | Native 完整 ELF 模式 external_calls 偏移 0 | backend_native_elf_external_calls | **99** | 第 58 轮 | ✅ **已清零**（第 58 轮） |
| P1 | P1-1 | Native XMM caller-saved 寄存器跨 call 未保存 | backend_native_xmm_caller_saved | 90 | 第 58 轮 | ✅ **已清零**（第 58 轮，含 x86_64 emitter SIB bug 修复） |
| P1 | P1-2 | Native ELF PT_LOAD p_offset/p_vaddr 对齐违规 | backend_native_ptload_align | 88 | 第 58 轮 | ✅ **已清零**（第 58 轮） |
| P1 | P1-3 | C 后端 nova_alloc/malloc NULL 未检查 | backend_c_alloc_null_check | 85 | 第 59 轮 | ✅ **已清零**（第 59 轮，同步修复 nova_panic 单参数调用 bug） |
| P1 | P1-4 | MIR Phi 节点类型取第一个源 SSA 不校验 | backend_mir_phi_type_consistency | 82 | **第 60 轮** | 待修复（评审轮） |
| P1 | P1-5 | LIR terminator SSA 位置找不到时默认空字符串 | backend_lir_term_ssa_defensive | 78 | 第 59 轮 | ✅ **已清零**（第 59 轮，7 处全部替换为 _require_ssa_loc） |
| P2 | P2-1 | type_checker 44 处裸 raise 未走 _error() | frontend_typecheck_unify_error_exit | 75 | 第 59 轮 | ✅ **已清零**（第 59 轮，P2-3 合并清零） |
| P2 | P2-2 | Parser _parse_brace_primary 静默吞错无注释 | frontend_parser_brace_doc | 45 | 第 58 轮 | ✅ **已清零**（第 58 轮） |
| P2 | P2-3 | match 错误缺 source_code（无 `-->` 标记） | （合并入 P2-1） | — | 第 59 轮 | ✅ **已清零**（第 59 轮，合并入 P2-1） |

**3 轮清零计划（第 58-60 轮）进度**：P0×1 + P1×5 + P2×3 = 9 项，已完成 7/9（P0 清零 + P1×4 清零 + P2×3 清零），剩余 1/9（P1-4：MIR Phi 类型一致性）。预计第 60 轮评审轮 9/9 全部清零。

### 高优先级任务（第 59 轮已完成 + 第 60 轮待做）

| 状态 | 任务 | 严重度 | 难度 | 优先级 | 预计 | 轮次计划 |
|------|------|--------|------|--------|------|----------|
| ✅ 完成 | **修复 Native 完整 ELF external_calls 偏移为 0（P0）** | P0 | hard | **99** | 1-2天 | 第 58 轮 |
| ✅ 完成 | 修复 Native 函数调用前 XMM caller-saved 未保存 + emitter SIB bug | P1 | hard | **90** | 3-5h | 第 58 轮 |
| ✅ 完成 | 修复 Native ELF 数据段 PT_LOAD 对齐违规 | P1 | easy | **88** | 30min | 第 58 轮 |
| ✅ 完成 | Parser Map/Block 歧义探测文档化 + 错误恢复单测（7 个用例） | P2 | easy | 45 | 1-2h | 第 58 轮 前端 |
| ✅ 完成 | **修复 C 后端 nova_alloc/malloc NULL 未检查**（含 nova_panic 3 参数签名修复） | P1 | medium | **85** | 2-3h | 第 59 轮 后端 |
| ✅ 完成 | **修复 LIR terminator SSA 位置默认空字符串**（7 处全部迁移到 _require_ssa_loc） | P1 | easy | **78** | 1h | 第 59 轮 后端 |
| ✅ 完成 | **统一 type_checker 所有报错走 _error()（44 处迁移）+ match 补 source** | P2 | medium | 75 | 4-6h | 第 59 轮 前端 |
| 待做 | 修复 MIR Phi 节点类型不做一致性校验 | P1 | medium | **82** | 3-5h | **第 60 轮**（评审轮后端） |
| 待做 | 补齐 test_type_checker.py 12 类核心场景测试盲区 | P2 | easy | 65 | 3-4h | **第 60 轮** 前端 |
| 待做 | 实现 Wasm 后端栈平衡验证器 | — | medium | 45 | 1-2天 | 第 60 轮后（评审轮带宽允许时） |
| 待做 | 验证 Phi 节点 LIR 降级正确性（菱形 CFG、并行拷贝语义） | — | medium | 42 | 3-5h | 第 60 轮后 |
| 待做 | 添加 Wasm 后端 WAT 缩进深度断言 | — | easy | 35 | 1h | 第 60 轮后 |

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

### 已废弃/降级任务

| 状态 | 任务 | 原因 |
|------|------|------|
| 废弃 | 收紧 TypeVar 兼容性判断（frontend_type_var_strict） | value restriction 长期项，前端进入维护模式 |
| 废弃 | 实现 Wasm 多参数闭包调用（backend_wasm_indirect_multiarg） | 并入 backend_wasm_closure_impl |
| 废弃 | 完善 WasmGC 原生类型定义（backend_wasm_gc_types） | 推迟到闭包后评估，闭包已完成无需再新增 |
| 废弃 | 统一 C 后端旧路径到 LIR 路径（backend_unify_c_codegen） | 降为维护模式，LIR 路径已覆盖 99% 场景 |
| 废弃 | backend_native_fn_ptr / backend_wasm_store_reg / backend_native_instr_selection / backend_c_todo_error | 分别并入后续任务或被更高优先级替代 |
| 废弃 | backend_native_runtime_link（旧 P70 hard，宽泛描述） | **第 57 轮评审废弃**——被更精确定位的 backend_native_elf_external_calls（P0 P99）替换，避免重复定义 |

### 历史已完成（41/68 = 60.3%，后端部分）

| 排名 | 任务组 | 代表任务 | 完成轮次 |
|------|--------|----------|----------|
| 1 | 寄存器分配体系 | 线性扫描寄存器分配器 / 调用点活跃切口 / 循环回归修复 | 43 / 47 / 48 |
| 2 | 原生后端 ELF 工具链 | 两阶段标签回填 / gcc 链接方案 / 可重定位 ELF / 端到端执行 | 19 / 37 / 45 / 46 |
| 3 | System V ABI 调用约定 | 栈帧管理 / ABI 调用约定 / 外部运行时复合指令 | 27 / 29 / 31 |
| 4 | 三后端闭包全栈支持 | MIR Lambda 降级 / LIR SSA callee / C/Wasm/Native 三后端实现 | 28 / 42 / 45 / 32 / 34 |
| 5 | 浮点立即数 & 全局存储 | 浮点立即数加载 / 浮点返回值处理 / 浮点全局存储（P1-新2） | 38 / 44 / 53 |
| 6 | C 后端健壮性 | trampoline double UB 修复 / 闭包双精度返回丢失清零（P1-新3） | 35 / 55 |
| 7 | Phi & 控制流降级 | Phi 边缘块 / MatchJump 后继不全 / 并行拷贝语义防御 | 19 / 23 / 56 |
| 8 | Cranelift 安全基线 | 未知指令从 TODO 注释改为 NotImplementedError（P0-新2 清零） | 52 |
| 9 | Native 外部运行时 | 运行时调用重构 / bug 修复 / 闭包内存泄漏清零 | 34 / 40 / 50 |
| 10 | 三后端静默跳过统一 | C/Wasm/Cranelift 三后端未知指令从静默改为异常 | 40 |

## 各后端完成度排名（第 58 轮三连修复后）

| 排名 | 后端 | 完成度 | 变化 | 关键缺失 |
|------|------|--------|------|----------|
| 1 | **C 后端** | **~85%** | 持平（第 57 轮 ↓3pp 后稳定） | nova_alloc NULL 未检查（P1-3，第 59 轮修复）、边界类型映射子串误判（低优） |
| 2 | **原生后端** | **~85%** | ↑**15pp**（第 58 轮三连修复） | 闭包场景 caller-saved 全保存优化（低优）、复杂结构体字段对齐（低优） |
| 3 | **WasmGC 后端** | **~78%** | 持平 | 栈平衡极端控制流验证、WAT 缩进断言、端到端验证缺失 |
| 4 | **Cranelift 后端** | **~35%** | 持平 | 大量指令未实现（安全基线已达标：未知指令抛 NotImplementedError 不静默） |

### 原生后端完成度回升说明（~70% → ~85%，第 58 轮）

第 57 轮审计后三大阻塞问题（P0×1 + P1×2）在本轮一轮内全部清零，效果显著：

1. ✅ **P0-1 external_calls 偏移为 0 → 清零**：_generate_elf 新增第 5.55 节，在 code 段末尾追加 11 类 x86_64 汇编 stub（noop/nova_alloc 用 brk 系统调用/nova_panic 用 write+exit/nova_list_new/Map/ADT/assert），回填所有 external_calls 的 call rel32。静态 ELF 独立运行不再 SIGSEGV。
2. ✅ **P1-1 XMM caller-saved + emitter SIB bug → 清零**：定义 CALLER_XMMS=[XMM0..XMM7]，4 条 call 路径（_emit_call/_emit_runtime_call/_emit_closure_create/_emit_call_indirect）均在 GPR 保存后分配 64 字节 XMM 区 movsd 存/取。同步修复 x86_64 emitter movsd_mem_reg/movsd_reg_mem RSP 基址缺少 SIB 字节的底层 bug（原编码 `[rax+rax*1-0xe]` → 段错误）。
3. ✅ **P1-2 PT_LOAD 对齐违规 → 清零**：code 段末尾用 0x90 NOP 填充到页对齐，data_offset 本身对齐，p_vaddr = base_addr+data_offset，实现 p_offset%4096 = p_vaddr%4096 = 0。hardening 内核/QEMU user 模式加载不再返回 EINVAL。

**Native 后端可用性评估**：.o + gcc 链接模式（主要测试路径）继续稳定；独立静态 ELF 模式从"完全不可用"提升至"基础程序可运行"（nova_init/nova_alloc/nova_panic 均有 stub 实现，List/Map/ADT 基础操作可用）。完成度从 ~70% 回升至 ~85%，与 C 后端并列第 1。
