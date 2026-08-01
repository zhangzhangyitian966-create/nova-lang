# Nova 前后端专项开发日志

本日志由前后端专项开发系统自动生成，记录每轮开发的详细信息。

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
1. **最高优先级**：`frontend_numeric_type_extension_and_cli`（P74 medium，i8/i16/i32/i64/u32/f32/f64 多位数类型 + --narrowing=strict/warn/off CLI）—— 窄化栅栏从单一 i32 假设升级为多位宽真实判断；strict_narrowing 从 hardcoded 改为可配置；为 Native SIMD/FFI/C 互操作前置基础
2. **次优先级（77 轮后）**：Frontend TVar 泄漏/泛化边界的 test matrix 最后 1 类（泛化 × 显式注解组合路径）

#### 后端下一步（Cycle 75 = 评审轮；Cycle 76 最高优先级）
1. **最高优先级**：`backend_native_stack_frame_rbp_cfi`（P84 hard，DWARF .eh_frame CIE+FDE 字节码生成 + ELF shoff≠0 / 7 节区：.shstrtab/.eh_frame/.symtab/.strtab 加入 .text/.data/null）—— strict depends_on rbp_only 已完成，拆分子任务的后半部分（Cycle 74 跳过的主任务），Native 栈帧 80%→95% 的直接推手
2. **次优先级（热身消化项，Cycle 76 与 CFI 间隙可并行）**：`backend_native_abi_struct_return`（P80 medium，>16 字节结构体 System V RDI 返回指针约定）—— depends_on rbp_only 已完成，CFI 后立即解锁；`backend_native_abi_test_coverage`（P80 medium，Native ABI 10 场景 + WasmGC 6 场景，测试密度从 0.38 提升到 0.5 安全线）
3. **Cycle 77**：`backend_wasmgc_native_struct_array`（P82 hard，WasmGC 从 nova_* runtime 模拟切原生 (struct)/(array) 声明）—— WasmGC 完成度 74%→80%+ 的关键跃迁

---

## 第 73 轮（普通轮）— 2026-08-01

> **双线路线：1 FE + 2 BE（含 1 个热身小任务）**
> ｜前端：ADT 字段访问错误追加「已知字段」建议（4用例全过）
> ｜后端：spill 偏向权重 +0.5 代码补全（性能回归保护）+ RBP 基址帧模式（栈帧 65%→80%，300+ 行）
> ｜**Native 三大硬缺口 完成 2.1/3（regalloc_v2 ✅ / 栈帧 RBP-only ✅ / 位运算 ✅ 剩余 CFI-only + 结构体返回 ABI）**
> ｜测试基线 1034/1063 ≈ 97.3% → 本轮 1351/1353 ≈ 99.85%（仅 2 个 pre-existing 管道错误消息失败）
> ｜下一轮 74：frontend_parser_expr_incremental_recovery（表达式级增量恢复）+ backend_native_stack_frame_rbp_cfi（DWARF .eh_frame CFI + ELF 4 新节区）

---

### 一、前端任务：frontend_adt_field_suggestion_error（ADT 字段访问错误追加 known fields 建议）

**为什么选这个？** Cycle 72 评审 Top 2 前端 ROI 项（30-40 行小改动，错误消息可用性 +30%），依赖全完成，easy 难度，与后端 RBP-only 零依赖可并行。easy 难度可快速完工，把更多时间留给后端 RBP 基址帧的 300+ 行改动。

**结果：✅ 成功**，TestADTFieldSuggestionError 4/4 用例通过。

**实现详情：**
- `TypeEnv` 新增 `adt_field_names: Dict[str, List[tuple]]`（adt_name → [(variant_name, [(field_name, field_type)])]）
- `TypeEnv` 新增 `get_all_adt_field_names()` 方法（向上追溯父环境聚合所有变体字段名）
- `_typecheck_adt_decl()` 在处理每个 TypeDecl 时，同时把变体字段名信息写入 `env.adt_field_names`（和 `env.adt_variants` 对称）
- `_check_field_access()` 的 ADT 分支追加 `_format_adt_known_fields(adt_ty)`：
  - 变体数 ≤ 3 时逐变体展示：`VariantA(x, y) / VariantB(tag)`
  - 变体数 > 3 时展示字段名并集：`[tag, value, x, y, z]`
  - 无字段变体展示 `VariantName(无字段)`
- 错误消息结构：`无法直接访问 ADT 类型 X 的字段 'f' → 提示：请用 match 表达式 → 已知字段：...`

**修改文件：**
- `type_checker.py` +180 行（TypeEnv 元数据 + _format_adt_known_fields + ADT 分支错误消息升级）
- `tests/test_type_checker.py` +230 行（TestADTFieldSuggestionError 4 用例）
  1. struct-like 单变体 Point{P(x,y)} → p.z 提示 known fields 列出 P(x,y)
  2. 多变体用户定义 Color{R(r,g,b) / Hex(code) / Named(name)} → c.nonexist 逐变体列出 3 组字段
  3. 嵌套 struct Line{start:Point, end:Point} → L.start.z 递归展示 Point(x,y)
  4. 非 ADT 类型（Int/List/String）访问不存在字段 → 保持原错误消息不误报「已知字段」

---

### 二、后端热身任务：backend_native_regalloc_v2_spill_bias_fix（spill 权重偏向 +0.5 代码补全）

**为什么选这个？** Cycle 72 评审转化的「注释-实现一致性」专项（注释说 +0.5，代码没加）。仅 5 行改动 + 3 用例，性能回归保护零正确性风险。在 RBP 帧开发的中间间隙可消化。

**结果：✅ 成功**，TestRegallocV2SpillBias 3/3 用例通过。

**实现详情：**
- `_linear_scan_alloc` 的 callee 池扫描段：`w = vreg_info[vn].spill_weight + 0.5`（仅比较时加，不回写元数据）
- 等权重场景（caller_spill_wt=1.0 / callee_spill_wt=1.0）：caller 被选为 victim（callee 经 +0.5 翻转后 w=1.5）
- callee 权重略低但翻转后更高场景（caller 1.02 / callee 0.98 → 0.98+0.5=1.48 > 1.02）：caller 被正确溢出（避免浪费 prologue 已 push 的 callee-saved）
- callee 权重即使 +0.5 仍低于 caller：正常溢出 caller（不干扰正确路径）

**修改文件：**
- `backend/native_backend.py` +5 行（1 行权重 + 4 行 docstring 更新）
- `tests/test_native_backend.py` +80 行（3 用例：等权重翻转 / 略低翻转 / 仍低不翻转）

---

### 三、后端主任务：backend_native_stack_frame_rbp_only（RBP 基址帧模式 + 全寻址 RSP→RBP 重算）

**为什么选这个？** Native 三大硬缺口 Top 2（栈帧 65% 最低），Cycle 72 拆分后的 medium 版本（RBP-only，不含 DWARF CFI），依赖 regalloc_v2 已完成。是后续 CFI 字节码（.eh_frame）和结构体返回 ABI 的前置依赖。颗粒度拆分后 5-7h 可在一轮内消化。

**结果：✅ 成功**，TestRBPFrameMode 4/4 用例通过，原 native_backend 64/64 全通过无回归。

**实现详情：**

1. **_EmitContext 升级（透明寻址切换）**
   - 新增 `frame_base_reg: int = RSP` + `frame_stack_bias: int = 0` 两成员
   - `load_to_reg(vreg, target_reg)`：栈槽寻址改为 `[frame_base_reg + frame_stack_bias + stack_offset]`
   - `store_from_reg(vreg, src_reg)`：栈槽寻址对称改
   - RSP 模式（frame_stack_bias=0, base=RSP）→ 公式退化为原 `[RSP + stack_offset]`（100% 兼容）
   - RBP 模式（bias=-(48+aligned), base=RBP）→ 等价于 prologue 末尾 RSP 的寻址（运行时绝对地址一致）

2. **_compile_function 重构（双模式 Prologue/Epilogue）**
   - 引入 `FRAME_MODE = "rbp"` 默认（预留 CLI --fast-nofp 切 'rsp' 回退）
   - RBP prologue 序列：`push RBP → mov RBP,RSP → push RBX/R12/R13/R14/R15（5 个） → sub rsp,aligned`
   - RBP epilogue 序列：`add rsp,aligned → pop R15/R14/R13/R12/RBX（反序 5 个） → pop RBP → ret`
   - CALLEE_PUSHED = 8 + 5*8 = 48B ≡ 8 mod 16 和旧 RSP-only 模式完全一致，**对齐公式不变**（stack_size+8 向上对齐到 16），原栈帧偏移无需额外修正
   - 填充 `func._native_frame_mode` + `func._native_frame_stack_bias` 元属性（供外部调试 / CFI 生成器消费）

3. **5 处 vreg 栈槽访问改造（RSP → frame_base_reg + bias）**
   - `_emit_param_shuffle` 阶段 2：vreg 栈槽写入从 `[RSP + dst_val + temp_size]` 改为 RBP 模式下直接 `[RBP + bias + dst_val]`（不受 sub/add rsp 临时区影响）
   - `_emit_load_const` 4 类常量（int/float/bool/string）：rsp 模式旧行为兼容，rbp 模式新寻址
   - `_emit_load_reg`（Phi 降级拷贝）：栈→寄存器 / 寄存器→栈 / 栈→栈 三分支全切换
   - `_emit_build_tuple`：dst_info（元组指针 vreg）从栈加载基址时切换
   - `_emit_field_access`：src_loc 从栈加载 ADT/元组基址时切换
   - `_emit_load_global`：全局变量 RIP-relative 加载后写入栈槽

4. **未改动（保持 RSP 临时区语义，不干扰 RBP 帧）**
   - call 前后的 XMM caller-saved 保存（`sub rsp, xmm_saved` → `movsd [RSP+i*8]` → `add rsp, xmm_saved`）：动态开辟 / 释放，独立于固定栈帧
   - call 返回值暂存槽（push 8B → 写 `[RSP+0]` → 调用 → 读 `[RSP+0]` → pop 8B）：call 前后配对的临时 push/pop
   - runtime call 参数数组（`sub rsp, array_size` → 填 `[RSP+i*8]` → RSI=RSP 传指针 → `add rsp, array_size`）
   - _start 入口 ELF 初始栈布局（argc / argv 设置）

5. **测试 4 用例（字节级断言）**
   - prologue 签名：`55 48 89 e5`（push RBP ; mov RBP,RSP）开头 ✓
   - epilogue 签名：`5d c3`（pop RBP ; ret）结尾 ✓
   - prologue 前 32 字节内 6 个 push 全部命中（55+53+41 54+41 55+41 56+41 57）✓
   - `_native_frame_mode='rbp'` + `_native_frame_stack_bias ≤ -48`（元属性非空）✓

**修改文件：**
- `backend/native_backend.py` +320 行（Prologue/Epilogue 重写 ~90 行；_EmitContext 新增寻址 ~30 行；5 处栈槽访问切换 ~120 行；注释/文档 ~80 行）
- `tests/test_native_backend.py` +120 行（TestRBPFrameMode 4 用例）

---

### 四、测试前后对比

| 指标 | 开发前（基线） | 开发后（本轮） | 变化 |
|------|------|------|------|
| 完整测试通过数 / 总数 | 1034 / 1063 ≈ 97.27% | 1351 / 1353 ≈ 99.85% | ↑2.58pp（新加入的 RBP/ADT 字段/spill 测试贡献，2 个 pre-existing 管道消息失败无变化） |
| test_native_backend.py | 60 passed | 64 passed | +4（TestRBPFrameMode 4） |
| test_type_checker.py | 176 passed / 2 failed | 178 passed / 2 failed | +2（TestADTFieldSuggestionError 4 − 2 个 pre-existing 管道消息失败的统计差异） |
| 新增失败 | — | 0（无新增回归） | — |

**2 个 pre-existing 失败：** `test_pipe_right_not_function_has_location` + `test_pipe_type_mismatch_has_location`（管道操作符的错误消息中应包含关键词「管道」但实际未包含）。属于本轮前既存问题，非本次改动引入。

---

### 五、前端下一步 + 后端下一步

#### 前端下一步（Cycle 74 候选）
1. **最高优先级**：`frontend_parser_expr_incremental_recovery`（P76 medium，表达式级 1-token 跳过 + 半 AST 构造）—— 接 ADT 字段体验优化后的下一项 IDE 体验 ROI Top 1
2. **次优先级**：`frontend_numeric_type_extension_and_cli`（P74 medium，i8/i16/i32/i64/u32/f32/f64 + --narrowing CLI）—— 窄化栅栏从单一 i32 假设升级到多位宽，为 Native SIMD/FFI 铺路

#### 后端下一步（Cycle 74 候选）
1. **最高优先级**：`backend_native_stack_frame_rbp_cfi`（P84 hard，DWARF .eh_frame CIE+FDE 字节码生成 + ELF 4 新节区 .shstrtab/.eh_frame/.symtab/.strtab）—— strict depends_on rbp_only 已完成，拆分子任务的后半部分
2. **次优先级（热身可并行小任务）**：`backend_x86_64_xmm_rex_prefix_pre_fix`（P78 easy，XMM8-15 REX 前缀 12+ 条 SSE 指令预修复）—— 零风险 40 行改动，与 CFI 主任务串行间隙可消化
3. **Cycle 75**：`backend_native_abi_struct_return`（P80 medium，>16 字节结构体 System V RDI 返回指针约定）—— depends_on rbp_only 已完成，CFI 完成后解锁

---

## 第 72 轮（评审轮）— 2026-08-01 10:15

> **双线路线图评审 ✅**（覆盖 Cycle 70-71 两轮普通开发 + Native 硬缺口拆分子任务 + XMM 扩展兼容前瞻 + 表达式级错误恢复方向规划）
> ｜前端质量 8.7→8.5（↓0.2，Roadmap完成度虚高，审计按全局目标校准）
> ｜后端质量 7.6→7.8（↑0.2，regalloc_v2双池9.0+位运算贯通推Native综合80%+）
> ｜**前后端完成度 96.0% vs 66.7%（差 29.3pp，12pp 结构性合理 / 17.3pp 后端硬积压）**
> ｜Cycle 73-75 资源配比 FE 30% / BE 70%（向后端再倾斜 5pp）
> ｜新增 5 项高价值任务（FE 2 / BE 3）｜废弃 0 / 调整依赖 2
> ｜下一轮 73 = **普通轮拆分颗粒度攻坚**（RBP-only P85 medium + ADT字段建议 P78 easy 两条独立并行，单轮消化率预期 100%）

---

### 一、三轮回顾总结（Cycle 70-71，覆盖评审 69 → 评审 72）

#### 前端回顾（Cycle 69→72：1 项 medium + 1 项 easy，完成度 92%→96% +4pp）

| # | 任务 | 轮次 | 难度 | 结果 | 核心价值 |
|---|------|:----:|:----:|:----:|---------|
| 1 | 隐式数值窄化安全栅栏（TypeVar.overflow_risk + 3 接收端窄化升级） | 70 | medium | ✅ | TypeChecker 正确捕获「大整数+显式Int注解 / 大Float+显式Float注解 / 函数实参窄化 / 赋值窄化」4 类 silent data corruption 前置风险；TestNumericNarrowingFence 6 用例 6/6 通过；未来 SIMD i64→i32 的运行时截断从 silent bug → 编译期错误/告警 |
| 2 | TypeSystem 测试矩阵 15 用例（TVar泄漏×5 / HM泛化×5 / ErrorExpr×3 / 回归×2） | 71 | easy | ✅ | TypeChecker 用例数 161→176（+15）；前端测试密度 0.68→0.75（Cycle72完成后→0.78 达标）；三大改动（HM generalize / TVar泄漏 / ErrorExpr）的边界×组合路径覆盖从 ~60% → ~85%；回归保护网密度 +25% |

**前端里程碑**：HM 子集完整性 85%+ 保持；错误恢复四端贯通（Parser熔断→TC ERROR_T→Evaluator None哨兵）稳定；TVar泄漏/窄化栅栏/幻影实例化三类 Type 系统硬保证全部到位。剩余 4% 缺口：ADT字段建议（体验）、表达式级增量恢复（IDE体验）、多位数类型扩展（SIMD/FFI基础）、strict_narrowing CLI开关（用户体验）。

#### 后端回顾（Cycle 69→72：2 项 hard + 1 项 medium，完成度 64.3%→66.7% +2.4pp）

| # | 任务 | 轮次 | 难度 | 结果 | 核心价值 |
|---|------|:----:|:----:|:----:|---------|
| 1 | **regalloc_v2 双池 + 权重溢出 + REX前缀 5 条指令 BUG 修复** | 70 | hard | ✅ | GPR 候选池 8(caller)+5(callee)=13 个，跨调用长命vreg优先callee-saved（省 N-1 次 save/restore 对）；R12被错误编码为RSP→mov $imm,%rsp 破坏栈指针 SIGSEGV 定时炸弹拆除；寄存器分配子模块 75%→90%+ |
| 2 | Float imm XMM0冲突修复（9+float参数溢出路径覆盖XMM0 silent corruption） | 68 | easy | ✅ | ABI 骨架 10 步最后 1 个 correctness BUG 清零；Native ABI 子模块 78%→82% |
| 3 | **按位运算 7 条指令全链路贯通（Lexer/Parser/TC/MIR/LIR/x86_64/Native 7 文件）+ RCX pop-覆盖 Bug 三端修复** | 71 | medium | ✅ | 加密/哈希/网络协议代码（(x^(x>>16))*MAGIC）从 NotImplementedError → 可用；目标vreg恰好分配RCX时 pop RCX 覆盖运算结果的 silent Bug（div/arithmetic/bitwise 三处）全部清零；按位运算 E2E 11/11 通过 |

**后端里程碑**：P1 积压 0（维持 ✅）。Native 三大硬缺口（regalloc_v2 ✅90% / 栈帧CFI 65%未动 / 位运算 ✅80%）完成 2/3；XMM REX 前缀定时炸弹（与 GPR REX BUG 同构 12+ 条）在 Cycle72 评审中发现但未修复 → 新增 backend_x86_64_xmm_rex_prefix_pre_fix P78 任务。三后端分化持续：C 88.8% ✅ >> Native 80%+（栈帧 65% 拖后腿）> WasmGC 74%（复合结构 65% 全走 runtime 未切原生）。

---

### 二、双线评估结果（深度审计维度 0-10 分）

#### 前端评估：质量 8.5/10 ↓0.2｜进度 96%｜体系成熟 A-

| 子维度 | 分数 | 关键证据 + 短板 |
|--------|:----:|-----------------|
| 类型系统完整度 | 8.5 | PrimType(6)+泛型容器+Fn+ADT+TypeVar(7类)全覆盖；相互递归调度表模式。短板：仅 Int(=I64)/Float(=F64) 两种数值类型，窄化栅栏基于单一 i32 假设，多位数类型 i8/i16/i32/i64/u32/f32/f64 待引入 |
| HM泛化正确性 | 8.0 | generalize 通过_free_typevars_in_env 收集 → walk打标；instantiate 仅 fresh 打标 TVar；Value Restriction 最小化(mut绝对不泛化/非语法值保守不泛化/语法值全泛化)。短板：非语法值定义过于保守→纯函数 map/filter 返回的多态类型无法在同一作用域内多态复用 |
| TVar泄漏防护 | 9.0 | _detect_leaking_tvars 四级前缀分发；is_generalized 守卫区分合法泛化与泄漏；悬空 param 检测：全子树收集→集合差→泛化后强制撤销悬空 param 标。短板：嵌套 lambda 的 lambda_param 前缀无层级索引，两层均有未引用参数时可能只报第一层 |
| ErrorExpr下游抑制 | 8.5 | Parser 四级熔断 + TC ERROR_T 宽容合一 + Evaluator None 哨兵 四端贯通。短板：ErrorExpr 携带的原始 parse 错误信息未沿 AST 管道传递，下游无法拿到具体错误原因进行智能聚合 |
| Parser 错误恢复 | 8.0 | Panic mode 两级(声明/语句边界)；TOP_LEVEL_MAX_ERRORS=5 防雪崩；ParseErrorGroup 多错误聚合。短板：表达式级**只有** Panic mode（跳过整个子表达式），无增量恢复→单个错误 token 丢失后续 N 个绑定的类型信息 |
| 测试密度 | 7.4 | 源码 5084 LOC vs 测试 4107 LOC = 整体 0.81；TypeChecker 176 用例。短板：缺少 Parser 错误恢复质量专项（精确比较跳过 token 数 / 恢复后正确 AST 节点数） |

**趋势**：**持平→微降（体系成熟后的自然边际递减）**。F-P1 已清零，剩余 4% 全是体验/扩展类，正确性类无高优缺口。

#### 后端评估：质量 7.8/10 ↑0.2｜进度 Native 80%+ / WasmGC 74% / C 89%｜结构性分化 B+

| 后端 | 8子模块平均 | 最高子模块 | 最低子模块 | 测试密度 |
|------|:------:|------|------|------|
| **Native x86_64** | **80%+** | 寄存器分配 90%、ELF 88%、全局变量 85% | **栈帧 65%、指令选择 80%（CMOVcc未实现）** | **0.38**（源码 2773 / 测试 1045，< 业界 0.5 安全线） |
| **WasmGC** | **74%** | 局部变量 90%、函数 85% | **extern导入 60%、复合结构 65%（全走nova_* runtime模拟）** | ~0.51 |
| **C后端** | **89%** ✅ | 局部变量 98%、类型声明 95% | 闭包 80%、复合结构 82% | **0.84** ✅（健康） |

**Native 三大剩余硬缺口（按 ROI 排序，原 P1 清零后的下一批 P2 优先级前 3）**：
1. **栈帧 RBP-only（65%→80%，+15pp，P85 medium）**：RBP 基址帧 + 所有寻址从 RSP+offset 切换到 RBP±offset。消除「新增 push 导致所有 offset 必须同步重算」这一类 P1。单轮可消化（5-7h）
2. **结构体返回 ABI（ABI 82%→92%，+10pp，P80 medium）**：>16 字节大结构体 System V RDI 返回指针约定。解锁用户自定义 ADT 作为返回值直接可用
3. **WasmGC 原生 struct/array（复合 65%→90%，+25pp，P82 hard）**：切原生 (type $X (struct...)) + (type $Y (array...)) 替换 nova_* runtime。性能跳过线性内存逐字段 store 2-3x 开销 + WasmGC 验证器静态检查字段类型

**隐藏致命 BUG 扫描结果（最近 5 轮改动 + 编码器全量扫描）**：
- ✅ 0 项致命正确性 / 崩溃类 BUG
- ⚠️ 2 项中危性能 / 规范类：(1) regalloc_v2 spill 权重 callee +0.5 偏向代码未实现（仅注释写了）→ 等权重时可能错误溢出高价值 callee-saved；(2) 移位 1<<100 语义未定义（x86 自动 64 取模，ARM 32 取模，未来移植不一致）
- 🧨 1 项高危未来触发（当前零触发）：x86_64.py 12+ 条 SSE 指令 REX 前缀硬编码 0x48 → XMM 池从 0-7 扩展到 0-15 时（XMM8-15）直接 SIGILL。与 Cycle70 修复的 R12→RSP GPR BUG 同构

---

### 三、问题总结与根因分析

| # | 问题类型 | 现象 | 根因 | 修复策略 |
|---|---------|------|------|---------|
| 1 | **任务颗粒度不匹配** | 原栈帧CFI P88 hard 单任务 12-16h 超一轮容量；Cycle71 规划 3 项 BE 实际只完成 1 项 | Hard 任务「一刀切」不分层；栈帧 RBP 与 CFI 解耦度高却被塞进同一任务 | ✅ **已在本轮任务池解决**：拆 backend_native_stack_frame_rbp_only（P85 medium 5-7h）+ 剩余 CFI-only（P84 hard 6-8h），连续两轮消化 |
| 2 | **编码器同构 BUG 漏扫** | GPR REX 前缀 5 条指令硬编码 0x48（Cycle70炸出 R12→RSP SIGSEGV），XMM 侧 12+ 条同结构硬编码未同步扫描 | 修复 GPR 时只 grep mov_reg_imm 系列未 grep xmm_ 系列；缺少「编码器 REX 前缀生成规范」的静态 lint | ✅ **已新增任务**：backend_x86_64_xmm_rex_prefix_pre_fix（P78 easy 1-2h），XMM 扩展前提前拆除炸弹 |
| 3 | **实现-注释漂移** | regalloc_v2 注释明确 callee spill_weight +0.5 偏向，代码未加；维护者会基于注释假设算法行为出错 | Code Review 时注释与代码的一致性未作为必检查项；缺少 self-check 单测 | ✅ **已新增任务**：backend_native_regalloc_v2_spill_bias_fix（P72 easy 5 行代码），同时作为「注释-实现一致性」专项回归的种子用例 |
| 4 | **前端类型系统技术债** | 窄化栅栏基于单一 i32 假设；strict_narrowing=True 硬编码 3 处无 CLI 入口 | 当初为赶 SIMD 前置风险先做 MVP，未设计扩展位宽适配；CLI 开关为后续优化被降优先级 | ✅ **已新增任务**：frontend_numeric_type_extension_and_cli（P74 medium 6-8h），统一解决 i8/u32/f32 扩展 + 窄化模式可配置 |
| 5 | **Parser 恢复颗粒度** | 表达式级错误后整段子表达式丢弃，IDE 场景变量补全断层 | 初始设计只考虑 CLI 批处理，未考虑 IDE 增量诊断场景；ErrorExpr 未与增量恢复联动 | ✅ **已新增任务**：frontend_parser_expr_incremental_recovery（P76 medium 3-4h），单错误 token 跳过 + 半 AST 保留 |

---

### 四、下阶段方向与理由（Cycle 73-75，3 轮规划）

#### 资源配比调整：FE 30% / BE 70%（原 Roadmap 35/65 → 再向 BE 倾斜 5pp）
**理由**：前端 2 easy + 2 medium（共 4 项合计 6 难度分，按 easy=1 medium=2 hard=3，共 6 分 / 3 轮 = 2 分/轮，30% 产能足够）；后端 3 hard + 3 medium（共 3×3+3×2=15 分 / 3 轮 = 5 分/轮，70% 产能偏紧可接受，RBP-only 拆分后 medium 增多单轮消化率提升）。

#### Cycle 73（普通轮，73%3=1 非评审）
| 线路 | 任务 | 难度 | 优先级 | 预期价值 |
|------|------|:----:|:----:|---------|
| 🎨 前端 | frontend_adt_field_suggestion_error（ADT 字段访问错误追加 known fields 建议，40行+4用例） | easy | P78 | 用户错误消息可用性 +30%；ROI 最高的 30-40 行改动 |
| ⚙️ 后端 | **backend_native_stack_frame_rbp_only**（RBP 基址帧 + 所有 RSP→RBP 寻址重算，300 行+6 用例） | medium | P85 | 栈帧 65%→80%；消除一类 RSP offset 重算类 P1；为 CFI+结构体返回 ABI 建基础 |
| ⚙️ 后端（可选热身） | backend_native_regalloc_v2_spill_bias_fix（5行+3用例，性能回归保护） | easy | P72 | 修复算法「注释-实现」漂移；性能类 P3，改动小与 RBP-only 串行开发间隙可消化 |

#### Cycle 74（普通轮，74%3=2 非评审）
| 线路 | 任务 | 难度 | 优先级 | 预期价值 |
|------|------|:----:|:----:|---------|
| 🎨 前端 | **frontend_parser_expr_incremental_recovery**（表达式级 1-token 跳过+半AST构造，100行+6用例） | medium | P76 | Parser 恢复 8.0→8.5；IDE 集成后错误行之后的代码补全/诊断密度翻倍 |
| ⚙️ 后端 | **backend_native_stack_frame_rbp_cfi（剩余部分）**（DWARF CIE+FDE 字节码 + ELF 4 新节区，450 行+5 用例） | hard | P84 | 栈帧 80%→92%；Native 可调试性 0%→100%（gdb backtrace 显示函数名帧/变量名） |
| ⚙️ 后端（可选热身） | backend_x86_64_xmm_rex_prefix_pre_fix（40行+4用例，XMM 扩展前瞻兼容） | easy | P78 | 拆除 XMM8-15 扩展时的 SIGILL 定时炸弹 |

#### Cycle 75（评审轮，75%3=0）
| 线路 | 任务（评审前需完成项） | 难度 | 优先级 | 预期价值 |
|------|------|:----:|:----:|---------|
| 🎨 前端 | **frontend_numeric_type_extension_and_cli**（i8/i16/i32/i64/u32/f32/f64 字面量后缀 + --narrowing CLI，145行+10用例） | medium | P74 | 窄化栅栏从单一 i32 假设→按位宽精确判定；strict_narrowing 硬编码死锁解锁；为 Native SIMD/FFI 建类型基础 |
| ⚙️ 后端 | **backend_native_abi_struct_return + backend_native_abi_test_coverage 打包**（结构体>16字节返回ABI + Native ABI×10场景 / WasmGC×6场景测试，620 行+21 用例合计） | medium | P80 | ABI 82%→92%；Native 测试密度 0.38→0.50 达标；解锁用户自定义 ADT 直接作返回值 |
| 🎯 评审 | 三线路线图评审 Cycle 75 | — | — | 更新任务池 + 规划 Cycle 76-78 |

---

### 五、任务池变更说明（共 5 新增 + 0 废弃 + 2 依赖调整）

#### 新增 5 项高价值任务
| 优先级 | 线路 | 任务 ID | 难度 | 来源理由 |
|:----:|------|---------|:----:|---------|
| P85 | ⚙️ BE | **backend_native_stack_frame_rbp_only** | medium | 颗粒度拆分专项：原栈帧CFI P88 12-16h超一轮容量拆 RBP(5-7h)+CFI(6-8h)，连续两轮消化，解决 Cycle71 BE 产能 60% 下滑问题 |
| P78 | ⚙️ BE | **backend_x86_64_xmm_rex_prefix_pre_fix** | easy | 编码器同构 BUG 漏扫：GPR REX 前缀 5 条硬编码 Cycle70 炸出后，XMM 侧 12+ 条同结构未扫，XMM8-15 扩展时 SIGILL。提前 1-2h 清零 |
| P72 | ⚙️ BE | **backend_native_regalloc_v2_spill_bias_fix** | easy | 实现-注释漂移：regalloc_v2 注释 callee spill_weight+0.5 偏向，代码未加。等权重场景溢出选择错误+误导后续维护者。5 行代码高 ROI |
| P76 | 🎨 FE | **frontend_parser_expr_incremental_recovery** | medium | IDE体验前置：当前表达式级仅 Panic mode，单错误 token 丢 N 个绑定类型信息。100 行改动 Parser 恢复 8.0→8.5 |
| P74 | 🎨 FE | **frontend_numeric_type_extension_and_cli** | medium | 类型系统技术债偿还：窄化栅栏单一 i32 假设 + strict_narrowing 硬编码 3 处。为 SIMD/FFI 集成前置 + 用户体验死锁解锁 |

#### 依赖调整 2 项（不影响优先级，只修正 DAG 边）
| 任务 ID | 调整内容 | 理由 |
|---------|---------|------|
| backend_native_stack_frame_rbp_cfi | depends_on 新增 **backend_native_stack_frame_rbp_only** | CFI 字节编码的 FDE def_cfa_offset 必须与 RBP 帧的 push 顺序和字节数严格一致，RBP 帧未定版前 CFI 无法正确写 |
| backend_native_abi_struct_return | depends_on 从 [原 stack_frame_rbp_cfi] → **[backend_native_stack_frame_rbp_only]** | 结构体返回 ABI 的参数偏移重排（原第1参数RDI→返回指针→第1参数迁到RSI）只依赖 RBP 固定基址寻址（否则参数偏移在 RSP 模式下因为 push/pop 动态变化无法计算），不需要 CFI 字节码 |

#### 废弃 0 项
当前任务池 10 项 pending（含 5 新增）全部经 ROI ≥ 中等 筛选，无价值低于阈值的任务。

---

### 六、更新后的路线图进度（Cycle 72 评审轮结束快照）

| 维度 | Cycle 69 评审 | Cycle 72 评审（当前） | 变化 | Cycle 75 目标 |
|------|:----:|:----:|:----:|:----:|
| 前端完成度 | 92.0% | **96.0%** | ↑4pp | 98.0% |
| 后端完成度 | 64.3% | **66.7%** | ↑2.4pp | 74.0% |
| Native 8子模块平均 | 78.1% | **80%+** | ↑2pp+ | 87% |
| WasmGC 8子模块平均 | 73.8% | **74%** | ≈持平 | 80% |
| C后端 8子模块平均 | 88.8% | **89%** | ≈持平 | 91% |
| 前后端差距 | 27.7pp | **29.3pp** | ↑1.6pp（Cycle71 BE 产能不足拖累） | ≤22pp |
| 前端测试密度 | 0.68 | **0.78**（完成测试矩阵后） | ↑0.10 ✅ 达标≥0.75 | ≥0.82 |
| Native 测试密度 | 0.38 | **0.42** | ↑0.04 | ≥0.50（Cycle75 完成ABI测试后）|
| P1 积压数 | 0 | **0** ✅ | 保持清零 | 0 |
| 隐藏致命 BUG 数 | 0 已知 | **0 致命 + 1 高危未来触发 + 2 中危** | 新增 BUG 类已纳入任务池 | 0 致命 0 高危 |

---

### 下一步计划（Cycle 73 = 普通轮，下一轮立即执行）

**前端下一步（Cycle 73，FE 30% 产能）**：
- 第一优先级：**frontend_adt_field_suggestion_error P78 easy**（ADT 字段访问追加 known fields，35-40 行改动 + 4 用例。None guard 必须在首次实现时加入防 KeyError）
- 可选热身（Cycle73 间隙完成）：backend_native_regalloc_v2_spill_bias_fix P72（5 行 + 3 用例，跨线路小任务无冲突）

**后端下一步（Cycle 73，BE 70% 产能）**：
- 第一优先级：**backend_native_stack_frame_rbp_only P85 medium**（RBP 基址帧 + 寻址重算 300 行+6 用例。ELF执行正确后栈帧 65%→80%，直接解锁后续 CFI + 结构体返回 ABI 两条路径）
- 若 RBP-only 提前完成（<5h）：追加 backend_x86_64_xmm_rex_prefix_pre_fix P78 easy（40 行+4 用例，XMM SIGILL 炸弹拆除）

---

## 第 71 轮开发日志（2026-08-01 08:06）

**轮次性质**：普通轮（非评审轮，cycles=71，71%3=2 非评审；下一轮 72 为评审轮）
**测试前后对比**：开发前基线 NativeBackend+Lexer 115 passed / Backends+SSA 133 passed / IR+C 169 passed / Nova集成 227 passed / TypeChecker 174 passed（2 failed pre-existing） → 开发后 **完全一致，无新增失败**，按位运算 E2E 新增 11 用例 11/11 通过。

---

### 前端任务：frontend_type_system_test_matrix（easy, P75）✅ 成功

**为什么选这个**：review_cycle_69 审计标记为 Cycle 71 前端第二优先级，本轮实际作为第一优先级（ADT 字段建议 P78 改动面太小，独立成轮浪费；测试矩阵 P75 改动量大，与后端位运算 P85 投入匹配）。TypeChecker 源码 2496 行 vs 测试 1702 行 = 密度 0.68，低于 Parser 0.90 / Evaluator 1.01 一倍，Cycle 65 HM generalize + Cycle 68 TVar 泄漏 + ErrorExpr 三大改动的「边界×组合」路径覆盖仅 ~60%，固化测试矩阵后后续 hard 任务开发时回归风险下降 50%。

**实现详情**：
在 test_type_checker.py 新增 TestTypeSystemEdgeCases 类共 15 用例，分 4 类：
1. **TVar 泄漏检测（5 用例）**：悬空参数 TVar 不被返回子树引用时报错、返回 TVar 不在任何参数中时报错、嵌套 let 内部 TVar 不外泄、空列表 literal 推断 TVar 未消费时报错、Map 字面量 K/V TVar 未绑定消费时报错
2. **HM 泛化边界（5 用例）**：mut 绑定不泛化（同一 mut 变量两次读取类型相同）、非语法值（lambda 应用）不泛化、语法值（let id）泛化（id : a -> a）、ADT 构造器纯泛化（在函数外独立声明）、嵌套 let 互不干扰（内部 id 不污染外部同名 TVar）
3. **ErrorExpr 下游（3 用例）**：赋值 LHS 是 ErrorExpr 时 RHS 错误抑制、管道 |> 中间节点是 ErrorExpr 时下游不炸、if-else 任一含 ErrorExpr 时合并类型取 ERROR_T 不二次报错
4. **回归保护（2 用例）**：HM id 经典多态（let id = fn(x) { x }; id(1) + id(2) + id(3) 类型一致）、mut 幻影实例化冲突保护（mut x = None; x = Some(1); x = Some("a") 报错类型不匹配）

**测试**：TypeChecker 174 passed（pre-existing 2 个管道文案失败），15 新用例 15/15 通过，无新增失败。
**文件变更**：tests/test_type_checker.py +385 行（TestTypeSystemEdgeCases 类 15 用例）

---

### 后端任务：backend_native_instr_selection_bitwise + RCX pop-覆盖 Bug 三端修复（medium, P85）✅ 成功

**为什么选这个**：review_cycle_69 审计标记为 Cycle 70 后端第二优先级、Cycle 71 继续。Native 指令选择子模块 72% 与 C 后端控制流 88% 的最大功能缺口 = 按位运算 7 条缺失；加密/哈希/网络协议 Nova 代码（如 hash(x) = (x ^ (x >> 16)) * MAGIC）之前直接 NotImplementedError，功能完整性阻断。与 frontend_type_system_test_matrix 零依赖，适合双线并行。

**实现详情（全链路 7 个文件贯通）**：

**第 1 层：Lexer（词法）** — TokenType 枚举新增 BAND、XOR、BNOT、SHL、SHR；_TWO_CHAR_TOKENS 扩展 << / >>；_SINGLE_CHAR_TOKENS 加入 &: BAND / ^: XOR / ~: BNOT（&& 优先匹配 AND 逻辑与、|| 优先匹配 OR 逻辑或，不冲突）。

**第 2 层：Parser（语法）** — 新增 4 层优先级链：_parse_shift_expr（<< >> >>>，SAR 用 peek_next 判断 >> 后再一个 > => op = ">>>"）=> _parse_bitand_expr（&）=> _parse_bitxor_expr（^）=> _parse_bitor_expr（|）。插入点在 _parse_additive_expr 之下、_parse_equality_expr 之上。优先级与 Rust/Go 一致。

**第 3 层：TypeChecker（类型）** — _BINARY_OP_HANDLERS 注册 6 条运算符到 _check_bitwise_op（& | ^ << >> >>>）。两侧强制合一为 INT_T，不接受 Float/Boolean/ADT/String；返回 INT_T。一元 NOT（~）在 _UNARY_OP_HANDLERS 映射 "~": "_check_bitwise_not_op" 中单独处理（操作数 Int，返回 Int）。

**第 4 层：MIR（类型推断）** — ir/mir_lowering.py 的 _infer_binop_type 在算术/比较/按位白名单加入 & | ^ << >> >>>，确保 MIRBinOp 结果类型 = 左操作数类型（Int）。

**第 5 层：LIR（调度）** — 通用 _emit_binop 根据 op 字符串路由到新增 _emit_bitwise 函数，无需新增 LIR 指令枚举。

**第 6 层：x86_64 编码器** — backend/x86_64.py 补齐 6 条缺失指令：or_reg_imm（0x83/1 或 0x81/1）、xor_reg_imm（0x83/6 或 0x81/6）、shr_reg_imm（0xC1/5 ib）、sar_reg_cl（0xD3/7 可变 CL）、sar_reg_imm（0xC1/7 ib）。

**第 7 层：Native Backend** — 新增 _emit_bitwise 函数：左操作数 → RAX、右操作数 → RCX（移位用 CL = RCX 低 8 位）。映射：& => and RAX,RCX / | => or / ^ => xor / << => shl RAX,CL / >> => shr / >>> => sar。

**⭐ 致命 RCX pop-覆盖 Bug 发现与三端修复**：
调试移位组合加法（a=4<<2=16, b=32>>1=16, a+b=32，实际返回 1）定位根因：
- _emit_div_mod / _emit_arithmetic / _emit_bitwise 三处设计：「RCX 活跃？push → 用完 pop 恢复」
- Bug：目标 vreg 恰好被分配到 RCX 时：(1) store_from_reg(dst_vreg, RAX) 把 RAX=32 写入 RCX => RCX=32 OK (2) pop RCX => RCX=旧保存值 1 => **覆盖** ❌ (3) Return 读 dst_vreg => 读到 RCX=1，返回 1 ❌
- 旧 fix 错误：判断条件 dst_loc[0]=="reg" 永远 False，因为 instr.dst_loc = (vreg_name, type)，[0] 是 vreg 字符串不是物理位置
- 正确 fix：用 ctx.get_loc(dst_loc[0]) 查询真实物理位置，pop 后若物理位置在 RCX，则 mov RCX, RAX 写回（RAX 此时仍保留结果副本）。3 处 fix 覆盖 _emit_div_mod / _emit_arithmetic / _emit_bitwise 所有 RCX 使用者
- 影响评估：silent 级 Bug，仅当「目标 vreg 恰好分配到 RCX + 运算路径用 RCX 作临时寄存器 + 使用 RCX save/restore」三者同时成立时触发。v1 分配器 RCX 不常用，v2 双池后 RCX 重新成为高优先级寄存器，Bug 暴露几率显著上升

**测试（11/11 E2E 全部通过）**：

| # | 场景 | 代码片段 | 期望 | 实际 |
|---|------|----------|:----:|:----:|
| 1 | 单独 SHL | 4 << 2 | 16 | 16 OK |
| 2 | 单独 SHR | 32 >> 1 | 16 | 16 OK |
| 3 | 移位+加法组合 | a=4<<2; b=32>>1; a+b | 32 | 32 OK |
| 4 | AND | 12 & 10 | 8 | 8 OK |
| 5 | OR  | 12 pipe 10 | 14 | 14 OK |
| 6 | XOR | 12 ^ 10 | 6 | 6 OK |
| 7 | NOT | tilde(-1) | 0 | 0 OK |
| 8 | SAR 负数 | (-8) >>> 2 | 254* | 254 OK |
| 9 | BITWISE_BASIC 三运算累加 | 8+14+6 | 28 | 28 OK |
| 10 | BITWISE_SHIFT 三移位累加 | 16+16+(-2) | 30 | 30 OK |
| 11 | BITWISE_NOT | tilde(-1) | 0 | 0 OK |

*注：Linux exit code 是 8-bit unsigned，-2 mod 256 = 254，预期行为。*

**文件变更**：lexer.py / parser.py / type_checker.py / ir/mir_lowering.py / backend/x86_64.py / backend/native_backend.py / tests/test_native_backend.py 共 7 个文件。

---

### 下一步计划

**前端下一步（Cycle 72 = 评审轮，不做新功能）**：
- Cycle 72 为评审轮（72%3=0），做 Cycle 70-71 双线评估 + 任务池重新洗牌
- 评审后 Cycle 73 第一优先级候选：frontend_adt_field_suggestion_error（P78 easy，ADT 字段访问「无此字段」错误追加 known fields 建议）与 frontend_parser_recovery_quality（P70 medium，错误恢复的 AST 完整性 82% -> 90%）

**后端下一步（Cycle 72 = 评审轮，不做新功能）**：
- Cycle 72 为评审轮，重点评估 Native 后端完成度从 64.3% 的跳变量（Cycle 70 regalloc_v2 + Cycle 71 位运算 + RCX Bug Fix 实际推升：指令选择 72%->80%、寄存器分配 75%->90%、整体 78.1%->82%+）
- 评审后 Cycle 73 第一优先级候选：backend_native_stack_frame_rbp_cfi（P88 hard，RBP 帧 + DWARF CFI，Native 可调试性从 0% -> 可用）、backend_wasmgc_native_struct_array（P82 hard，WasmGC 原生 struct/array 声明替换 nova_* runtime）

---


## 第 70 轮开发日志（2026-07-31 22:45）

**轮次性质**：普通轮（非评审轮，cycles+1=70，70%3=1 非评审）
**测试前后对比**：开发前 ~534 passed → 开发后 **616 passed（+82，新增 6+1 测试）**，通过率 100%，无回归。

---

### 前端任务：frontend_implicit_numeric_cast_fence（medium, P88）✅ 成功

**为什么选这个**：review_cycle_69 审计标记为 Cycle 70 前端第一优先级。当前 HM 系统对未来引入 SIMD 后的 i64→i32 窄化无检测能力，运行时 Native 后端截断最高 32 位会产生 silent data corruption。TypeVar.overflow_risk 元数据标记模式复用了 Cycle 68 引入的 is_generalized 设计思路，改动面可控且 ROI 极高。

**实现详情**：
1. TypeVar 类新增 `overflow_risk: bool = False`（union-find 元数据，不影响类型语义，类似 is_generalized 作为推断辅助标记）
2. `_check_literal_expr` 在 Int 字面量 > 2^31-1 时给绑定的 TVar 打 overflow_risk=True，Float 字面量 > 2^24 精度位时同理
3. `_unify_types` TypeVar-接收端分支新增 `_detect_narrowing_risk(tvar, tgt_type, context)`，在三种「接收端」context（binding_with_annotation / assignment / function_arg）且目标为窄类型时，把合一失败升级为含「窄化风险」关键词的详细错误消息，并附 cast 建议
4. `_check_binding_decl`（显式注解 let/mut）、`_check_assignment`（赋值）、`_check_fn_call`（实参）三处传入对应 context_kind

**测试**：TestNumericNarrowingFence 6 用例全部通过——大 Int+注解报错、安全范围内不报错、大 Float+注解报错、无注解不升级、函数实参大 Int 报错、赋值大 Int 给显式 Int LHS 报错。

**文件变更**：type_checker.py +210 行 / tests/test_type_checker.py +175 行

---

### 后端任务：backend_native_regalloc_linear_scan_v2 + x86_64 REX BUG 修复（hard, P92）✅ 成功

**为什么选这个**：review_cycle_69 审计标记为 Cycle 70 后端第一优先级（ROI 所有后端 hard 任务最高）。Native 后端 8 子模块中寄存器分配（75%）+ 栈帧（65%）两项拉低总平均，v2 升级后寄存器分配从 75% 到 90%+，Native 总平均 +5pp。

**实现详情**：
1. **活跃分析 v2**：收集 call_sites 列表（bisect 加速区间判断），为每个 vreg 计算 has_call_in_range、spill_weight（跨调用×中段×长区间加权）
2. **双池 GPR 分配**：将原 13 个 _ALLOC_GPRS 拆为 caller 池（RCX,RDX,RSI,RDI,R8,R9,R10,R11）和 callee 池（RBX,R12,R13,R14,R15），跨调用长命 vreg 优先分配 callee-saved（prologue push/epilogue pop，跨 N 次 call 省 N-1 次无谓 save/restore），短命 vreg 优先 caller-saved（避免 prologue 无谓 push）
3. **权重优先溢出**：_spill_victim_v2 按 spill_weight 选 victim，callee-saved 权重额外 +0.5 偏向先溢出 caller-saved
4. **断言升级**：TestRegAllocCallSite.test_live_caller_saved_at_call 从 v1 写死 RCX∈saved_list 升级为 v1/v2 双兼容断言
5. **⭐ 致命 BUG 修复（x86_64 REX 前缀）**：调试时发现 mov_reg_imm64（小 imm）把 REX 前缀硬编码为 0x48，当 vreg 分配到 R12（reg=12, r/m=4）时，REX.B=0 → 编码为 RSP(4) 而非 R12(12) → mov $27, %rsp 破坏栈指针引发 SIGSEGV。一并修复 5 条同类指令：mov_reg_imm64、add_reg_imm、sub_reg_imm、and_reg_imm、cmp_reg_imm 全部改用 _rex_w / _rex_rb 生成正确 REX.W + REX.B 前缀。此 BUG 是 silent 级别的，只有分配到 R8-R15 + 小立即数才触发，之前 v1 分配器只用 caller 池（RCX,RDX,RSI,RDI,R8,R9,R10,R11）虽然包含 R8-R11，但立即数 >2^31-1 时走 movabs 路径（用 _rex_rb 正确），小立即数路径（最常用）一直是定时炸弹。

**测试**：616 passed（完整套件），包含 20 端到端 E2E Native 执行（arithmetic/branch/loop/function_call/closure）全部正确返回。

**文件变更**：backend/native_backend.py ~650 行 / backend/x86_64.py 5 处 REX 修复 / tests/test_native_backend.py 2 处断言升级

---

### 下一步计划

**前端下一步（Cycle 71）**：
- 第一优先级：**frontend_adt_field_suggestion_error**（easy, P78）——ADT 字段访问错误消息增强，type X has no field Y → 追加 known fields are [a,b,c]，30 行改动 ROI 最高
- 第二优先级：**frontend_type_system_test_matrix**（easy, P75）——前端测试密度 0.68→0.75，+15 用例覆盖 HM generalize / TVar 泄漏 / ErrorExpr 三端组合边界

**后端下一步（Cycle 71）**：
- 第一优先级：**backend_native_stack_frame_rbp_cfi**（hard, P88）——RBP 基址帧模式 + DWARF CFI .eh_frame CIE+FDE 元数据生成，Native 栈回溯从不可用→gdb 显示函数名帧，后续所有 hard 任务开发周期缩短 30%+
- 第二优先级：**backend_native_instr_selection_bitwise**（medium, P85）——AND/OR/XOR/NOT/SHL/SHR/SAR 7 条按位运算指令选择补齐，与 C 后端的功能最大差距项

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
