# Nova 编程语言 — 自动代码审查日志

> **审查标准**：生产级编译器/语言标准（参考 OCaml/Haskell/Elm/F# 最佳实践）
> **审查时间**：2026-07-14
> **审查版本**：main 分支最新提交

---

## 项目结构审查表

| 模块 | 文件 | 审查状态 | 上次审查 | 严重问题数 | 中等问题数 | 轻微问题数 |
|------|------|---------|---------|-----------|-----------|-----------|
| VM 虚拟机 | `vm.py` | ✅ 已审查 | 2026-07-14 | 6 | 5 | 5 |
| 编译器 | `compiler.py` | ✅ 已审查 | 2026-07-14 | 5 | 4 | 6 |
| 求值器 | `evaluator.py` | ✅ 已审查 | 2026-07-14 | 3 | 5 | 4 |
| AST 节点 | `ast_nodes.py` | ✅ 已审查 | 2026-07-14 | 0 | 0 | 1 |
| 类型检查器 | `type_checker.py` | ✅ 已审查 | 2026-07-14 | 6 | 5 | 4 |
| 词法分析器 | `lexer.py` | ✅ 已审查 | 2026-07-14 | 1 | 3 | 6 |
| 语法分析器 | `parser.py` | ✅ 已审查 | 2026-07-14 | 2 | 4 | 3 |
| 错误处理 | `errors.py` | ✅ 已审查 | 2026-07-14 | 0 | 1 | 2 |
| 模块系统 | `modules.py` | ✅ 已审查 | 2026-07-14 | 1 | 2 | 2 |
| 环境 | `environment.py` | ✅ 已审查 | 2026-07-14 | 1 | 0 | 0 |
| C 代码生成 | `c_codegen.py` | ✅ 已审查 | 2026-07-14 | 4 | 2 | 2 |
| Native 后端 | `backend/native_backend.py` | ✅ 已审查 | 2026-07-14 | 3 | 3 | 0 |
| Cranelift 后端 | `backend/cranelift_backend.py` | ✅ 已审查 | 2026-07-14 | 3 | 3 | 1 |
| WASM 后端 | `backend/wasm_backend.py` | ✅ 已审查 | 2026-07-14 | 4 | 1 | 1 |
| x86_64 指令发射 | `backend/x86_64.py` | ✅ 已审查 | 2026-07-14 | 0 | 1 | 0 |
| 编译管道 | `backend/compiler_pipeline.py` | ✅ 已审查 | 2026-07-14 | 0 | 0 | 2 |
| IR 节点 | `ir/ir_nodes.py` | ✅ 已审查 | 2026-07-14 | 0 | 1 | 2 |
| HIR Lowering | `ir/hir_lowering.py` | ✅ 已审查 | 2026-07-14 | 0 | 2 | 2 |
| MIR Lowering | `ir/mir_lowering.py` | ✅ 已审查 | 2026-07-14 | 4 | 3 | 1 |
| LIR Lowering | `ir/lir_lowering.py` | ✅ 已审查 | 2026-07-14 | 0 | 3 | 2 |
| Pass 管理器 | `ir/pass_manager.py` | ✅ 已审查 | 2026-07-14 | 2 | 2 | 1 |
| C 运行时 | `runtime/nova_runtime.c` | ✅ 已审查 | 2026-07-14 | 2 | 4 | 1 |
| 测试套件 | `tests/` | ✅ 已审查 | 2026-07-14 | 2 | 0 | 0 |
| Tree-sitter | `tree-sitter-nova/` | ✅ 已审查 | 2026-07-14 | 1 | 0 | 0 |

---

## 审查记录

---

## [2026-07-14] VM 虚拟机 (vm.py) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | MATCH_START/MATCH_END 标记、PIPE_CALL 指令有特色；但栈机设计基本标准 |
| 可行性 | ⭐⭐⭐ | 核心路径（函数调用、基本运算、模式匹配）可用；循环控制有严重 bug |
| 正确性 | ⭐⭐ | CONTINUE 空实现、闭包过度捕获、base_sp 错误、RETURN 语义错误 |
| 安全性 | ⭐⭐ | 无栈下溢保护、id() 做键不安全、迭代状态泄漏 |
| 一致性 | ⭐⭐⭐ | 与 Evaluator 存在 Unit bool 语义、str_to_int field_names 等差异 |
| 完整性 | ⭐⭐⭐⭐⭐ | 60 个操作码全部有处理路径 |
| 工程质量 | ⭐⭐ | _execute_instruction 600 行过长、重复代码 |
| 性能 | ⭐⭐ | 闭包捕获整个帧 dict 浅拷贝，高频创建闭包场景性能差 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [vm.py:550-837] **所有 pop 操作无栈下溢保护** → 约 35 条指令在 pop 前不检查栈是否为空，空栈时抛 Python IndexError 而非 Nova 错误 → 抽取 `_pop()` / `_pop_n(n)` 辅助方法，栈空时抛 RuntimeError_
- 追问：如果是 Haskell GHC 的 STG 机器栈管理有 bug，能被接受吗？→ **绝对不能。** 栈管理是 VM 最基本的正确性要求。

- [vm.py:717-728] **CONTINUE 在 while 循环中是空实现（no-op）** → `while cond { continue; body }` 中 continue 不跳回条件检查而是继续执行 body，完全违反 continue 语义 → 为 while 循环的 CONTINUE 记录循环条件检查位置（类似 for 循环的 loop_start）
- 追问：如果任何生产级语言的 continue 是空实现，能被接受吗？→ **绝对不能。** C/Java/Python/JavaScript/Rust 的 continue 空实现都会导致程序逻辑完全错误。

- [vm.py:736-738] **闭包捕获整个帧 locals 而非仅自由变量** → 每次创建闭包都 dict 浅拷贝所有局部变量，时间 O(n)，且阻止 GC 回收不需要的变量；可变共享对象违反不可变性原则 → 编译器分析自由变量，CLOSURE 指令携带自由变量名列表，VM 只拷贝指定变量
- 追问：如果 OCaml 的闭包捕获了整个作用域的 dict 拷贝，性能影响能被接受吗？→ **绝对不能。** 内存使用量可能增加 10-100 倍，GC 压力增大，完全抵消函数式语言性能优势。

- [vm.py:845,884] **`id()` 被用作字典键** → Python 的 id() 返回内存地址，对象被 GC 后地址可能被新对象重用；异常退出时字典条目不清理 → 改用编译器分配的唯一循环 ID 或嵌套深度计数器
- 追问：如果 Python 的 itertools 用 id() 做 key 且有内存泄漏，能被接受吗？→ **不能。** 这是潜在的内存安全和正确性问题。

- [vm.py:751-754] **RETURN 在 _execute_instruction 中弹栈但不终止执行** → 如果 RETURN 出现在顶层代码中，弹出一个值后执行继续到下一条指令，语义错误 → RETURN 应触发提前返回或至少正确终止当前执行流
- 追问：如果是 OCaml 的函数调用返回值丢失，能被接受吗？→ **不能。** 函数调用是语言执行核心，返回值丢失是根本性错误。

- [vm.py:392] **base_sp 计算错误且从不用于栈截断** → 参数已弹出后再减 len(args) 得到错误值；Frame.base_sp 从未被读取用于截断栈，函数返回后可能残留中间值 → 在 _call_closure 返回后用 base_sp 截断栈

#### 中等问题（影响特定场景）

- [vm.py:971-989] **模式匹配失败时无栈恢复机制** → 嵌套模式匹配失败时栈上可能残留已 push 的字段值，依赖编译器正确生成 fail_ip → 在 MATCH_START 时记录 match_base_sp，失败时恢复栈
- [vm.py:168-208] **内置函数几乎全部缺少类型检查** → str_len/list_length 等对非序列参数崩溃；sqrt/log 不验证值域 → 为每个内置函数添加参数类型验证
- [vm.py:709-715] **BREAK 在 while 循环中用脆弱的前向扫描** → 扫描到第一个 CONST_UNIT 就停止，CONST_UNIT 是常见指令，可能匹配到循环体内无关位置 → 使用编译器提供的 end_ip 操作数
- [vm.py:537] **mutable 参数未使用，不可变性未强制** → let 绑定的不可变性未被 VM 强制执行 → 检查 mutable 标志，拒绝修改不可变变量

#### 轻微问题（代码质量）

- [vm.py:655,669] JUMP_IF_FALSE 和 POP_JUMP_IF_FALSE 实现完全相同，可合并
- [vm.py:482-1079] _execute_instruction 方法近 600 行，应按功能拆分
- [vm.py:133,138] Frame.locals 命名不一致（locals_ vs locals）
- [vm.py:171] read_line lambda 中有死代码
- [vm.py:293] JSON dict 转换为 Python dict 而非 Nova Map

#### 原创性分析

- **Nova 特色**：PIPE_CALL 专用管道调用指令、MATCH_START/MATCH_END 显式标记、TRY_UNWRAP 统一处理 Option/Result、ADT 原生指令（MAKE_ADT/REGISTER_CTOR/MATCH_CONSTRUCTOR）
- **参考已有**：基本栈机设计参考 CPython/JVM；FOR_ITER + LOOP_END 双指令循环

#### Evaluator vs VM 对比
| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| Unit 值 bool 语义 | `object()` → `__bool__` = True | `UNIT_TYPE.__bool__` = False | ❌ **严重** |
| str_to_int 返回 | `NovaADTValue("Option","Some",[v])` 无 field_names | `NovaADTValue("Option","Some",[v],["value"])` 有 field_names | ❌ |
| 闭包捕获 | Environment 引用（引用语义） | locals dict 浅拷贝 | ❌ |
| 递归深度保护 | 无 | MAX_CALL_DEPTH = 1000 | ❌ |
| 基本算术 | 正确 | 正确 | ✅ |
| ADT 构造 | 正确 | 正确 | ✅ |
| 模式匹配 | 正确 | 正确 | ✅ |
| 管道操作 | 正确 | 正确 | ✅ |

---

## [2026-07-14] 编译器 (compiler.py) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | PIPE_CALL 指令、MATCH_START/END 标记、ADT 原生指令 |
| 可行性 | ⭐⭐⭐ | 基本编译流程可用；模式匹配、列表推导式有严重 bug |
| 正确性 | ⭐⭐ | 多种 Pattern 缺少测试代码生成；guard 被忽略；filter 被丢弃 |
| 安全性 | ⭐⭐⭐ | 栈布局基本正确但 for 循环非空/空路径不一致 |
| 一致性 | ⭐⭐ | 编译器假设的栈布局与 VM 实际执行有偏差 |
| 完整性 | ⭐⭐⭐ | AST 大部分节点有编译处理；MapExpr 缺失 |
| 工程质量 | ⭐⭐ | 死代码（遗留方法）、重复代码 |
| 性能 | ⭐⭐⭐ | 闭包不做自由变量分析影响效率 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [compiler.py:748] **PatternFloat/PatternChar/PatternTuple/PatternList 缺少模式测试代码生成** → `_compile_pattern_test_with_fail` 只处理 PatternInt/Bool/String/Constructor/Wildcard/Identifier，其他 Pattern 类型直接返回"匹配成功" → 为每种 Pattern 类型添加测试指令生成
- 追问：如果 Haskell GHC 编译器跳过某些 Pattern 的测试代码生成，能被接受吗？→ **绝对不能。** 模式匹配是函数式语言核心特性。

- [compiler.py:662-706] **match arm 的 guard 守卫条件被完全忽略** → `_compile_match` 中没有任何检查 `arm.guard` 的代码 → 在模式匹配成功后添加 guard 条件编译，失败时跳转到下一个 arm

- [compiler.py:924-939] **列表推导式 filter_cond 被完全忽略** → `ListComprehension.filter_cond` 字段存在但在转换为 ForExpr 时被丢弃，过滤条件静默失效 → 在转换的 ForExpr body 中添加 if 条件检查

- [compiler.py:855-903] **for 循环非空/空路径栈状态不一致** → 非空循环结束后栈为 `[iterable, result_list]`，空循环结束后栈为 `[result_list]`，后续表达式得到错误值 → 确保非空循环路径也正确弹出 iterable

- [compiler.py:300-343] **模块导入内联无命名空间隔离** → 所有导出名称直接进入全局变量表，同名导出后者覆盖前者且无警告 → 实现模块命名空间前缀或限定导入

#### 中等问题（影响特定场景）

- [compiler.py:844-849] Block 中 BreakExpr/ContinueExpr 后多余的 POP 导致栈错位
- [compiler.py:905-922] while 循环未实现"返回最后一次迭代值"语义
- [compiler.py:786-840] 两个完整的遗留模式匹配方法（_compile_pattern_test, _compile_pattern_bindings）从未被调用
- [compiler.py:300-343] 无循环导入检测

#### 轻微问题（代码质量）

- [compiler.py:80 vs 375] CLOSURE 指令的 code_key 操作数定义但未使用
- [compiler.py:607-628] 闭包不做自由变量分析（功能正确但效率差）
- [compiler.py Op 类] 多个已定义但从未生成的操作码（LOAD_CONST, LOOP, DUP, PRINT, AND, OR）
- [ast_nodes.py 全文] 类型注解全为 Any
- [compiler.py:924-939] 列表推导式不支持多 for 子句
- 多处命名不一致、方法名过长

#### 原创性分析

- **Nova 特色**：PIPE_CALL 专用指令、MATCH_START/MATCH_END 配对标记（方便调试）、FOR_ITER + LOOP_END 双指令循环设计、ADT 原生指令集（MAKE_ADT/REGISTER_CTOR）、常量值直接内联（无需常量池）
- **参考已有**：基本栈机结构参考 CPython/JVM；跳转回填参考标准编译器教材

#### Evaluator vs VM 对比

同 VM 报告中的对比表。

---

## [2026-07-14] 求值器 (evaluator.py) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 两遍扫描支持相互递归；内置 Option/Result 类型 |
| 可行性 | ⭐⭐⭐ | 核心特性可用；MapExpr 缺失、guard 未实现 |
| 正确性 | ⭐⭐ | UNIT_VALUE bool 语义、guard 静默忽略 |
| 安全性 | ⭐⭐ | 无递归深度保护、String/Char 无运行时区分 |
| 一致性 | ⭐⭐ | 与 VM 在 Unit bool、str_to_int field_names 等方面不一致 |
| 完整性 | ⭐⭐⭐ | 大部分 AST 节点有处理；MapExpr 完全缺失 |
| 工程质量 | ⭐⭐ | eval_decl 重复代码、eval_expr 170 行 if-elif 链 |
| 性能 | ⭐⭐⭐ | 闭包引用语义效率可接受；缺少递归深度保护 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [evaluator.py:817] **MapExpr 完全缺失** → eval_expr 的 else 分支抛 RuntimeError，任何使用 map 字面量的程序崩溃 → 添加 MapExpr 处理分支
- 追问：如果是 OCaml/Haskell 的编译器，已定义的 AST 节点在解释器中完全没有处理能被接受吗？→ **不能。** 相当于前端识别了语法但后端无法执行。

- [evaluator.py:956-967] **Pattern guard 守卫条件未实现** → `_eval_match` 完全不检查 arm.guard，第一个匹配的模式分支总是被执行 → 在模式匹配成功后求值 guard，失败时 continue 到下一个分支
- 追问：如果是 Haskell 的 when guard 被静默忽略能被接受吗？→ **绝对不能。** Pattern guard 是语言规范的一部分，忽略会导致程序逻辑错误。

- [evaluator.py:98] **UNIT_VALUE 的 `__bool__` 返回 True** → `if () { ... }` 在 evaluator 中执行 then 分支，在 VM 中跳过 then 分支 → 替换为 `__bool__` 返回 False 的类

#### 中等问题（影响特定场景）

- [evaluator.py:577] eval_decl 中构造器缺少 field_names 参数
- [evaluator.py:186] _builtin_str_to_int 返回 Option 缺少 field_names
- [environment.py:59] assign 对未定义变量抛 Python NameError 而非 RuntimeError_
- [evaluator.py:982-989] String/Char 运行时无类型区分（都用 Python str）
- [evaluator.py:396] 缺少递归深度保护（VM 有 MAX_CALL_DEPTH=1000）

#### 轻微问题（代码质量）

- [evaluator.py:548-603] eval_decl 是 _collect_decl + _eval_decl_body 的重复
- [evaluator.py:648-818] eval_expr 170 行 if-elif 链，应用分派表替代
- [evaluator.py:845] bool 在算术运算中的隐式转换
- [evaluator.py:265-266,294-295] JSON null 与 Option.None 的序列化歧义

#### 原创性分析

- **Nova 特色**：两遍扫描（_collect_decl + _eval_decl_body）自然支持相互递归；内置 Option/Result/Some/None/Ok/Err 作为一等类型
- **参考已有**：环境链设计标准；break/continue 用异常实现参考常见解释器模式

#### Evaluator vs VM 对比

同 VM 报告中的对比表。

---

## [2026-07-14] 类型检查器 (type_checker.py) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 自定义类型系统框架；ErrorCollector 机制 |
| 可行性 | ⭐⭐ | TypeVar 全兼容掩盖了大量问题；修复后会暴露更多 bug |
| 正确性 | ⭐ | 缺少 HM 核心（unification/generalize/instantiate） |
| 安全性 | ⭐ | 任意 TypeVar 兼容、未知类型名静默通过 |
| 一致性 | ⭐⭐ | ADTType.__eq__ 正确比较类型参数 |
| 完整性 | ⭐⭐ | Pattern 大部分有检查；let 多态未正确实现 |
| 工程质量 | ⭐⭐ | 330 行死代码（check_decl）、大量重复 |
| 性能 | ⭐⭐⭐ | 类型检查本身效率可接受 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [type_checker.py 全局] **没有实现 Unification（统一化）** → _types_compatible 只做兼容性检查不执行替换；TypeVar 永远不会被"求解"，绑定在局部字典中函数返回后丢失 → 实现 HM unification 算法
- 追问：如果 OCaml 的类型推断器缺少 unification，能被接受吗？→ **绝对不能。** 这是 HM 算法的核心组件。

- [type_checker.py 全局] **没有实现 Generalize/Instantiate（泛化/实例化）** → let 绑定的类型直接存入环境不做泛化；lambda 参数共享同一 TypeVar 名 → 实现 let 多态的 generalize/instantiate
- 追问：如果 OCaml 的 let 多态没有正确实现，能被接受吗？→ **绝对不能。** let 多态是 ML 系语言的核心特性。

- [type_checker.py:1318-1319] **任意两个 TypeVar 被视为兼容** → `_types_compatible` 中 `isinstance(a, TypeVar) or isinstance(b, TypeVar): return True`，任何未推断类型的表达式可赋值给任何类型 → 区分不同 TypeVar，通过 unification 求解

- [type_checker.py:754] **Lambda 多参数共享同一 TypeVar** → `TypeVar("lambda_param")` 硬编码名称，多参数 lambda 所有参数被强制为同一类型 → 每个参数使用唯一名称的 TypeVar

- [type_checker.py:576-660] **check_decl 是 330 行死代码** → 与 _collect_decl + _check_decl_body 功能完全重复，从未被调用 → 删除

- [type_checker.py:1256] **未知类型名静默创建 PrimType** → 拼写错误的类型名（如 `Intt`）不会报错 → 在 types 和 aliases 中未找到时报类型未定义错误

#### 中等问题（影响特定场景）

- [type_checker.py:1080-1081] PatternConstructor 不替换类型参数，泛型 ADT 模式匹配不正确
- [type_checker.py:1093-1098] 不支持 cons 模式（head :: tail），函数式语言核心功能缺失
- [type_checker.py:291] Err 内置函数返回类型引用了错误的 TypeVar
- [type_checker.py:1115,1121,1128] 二元操作错误后返回 INT_T/STRING_T 而非 ERROR_TYPE
- [type_checker.py:354] 注释声称 Int 自动转 Float 但未实现

#### 轻微问题（代码质量）

- [type_checker.py:248] collect_errors 默认 False，应默认开启
- [type_checker.py:967,995] ForExpr/ListComprehension 不推断迭代变量类型
- [type_checker.py:943-951] TryExpr 对非 Result/Option 静默通过
- 多处大量重复代码（三遍扫描相关方法）

---

## [2026-07-14] 词法分析器 (lexer.py) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | Token 位置追踪完善（行+列+跨度） |
| 可行性 | ⭐⭐⭐ | 基本词法分析可用；非法字符直接终止 |
| 正确性 | ⭐⭐⭐ | 转义字符基本正确；_make_error Span 有 bug |
| 安全性 | ⭐⭐⭐ | 无安全风险 |
| 一致性 | ⭐⭐⭐ | 与 parser 配合良好 |
| 完整性 | ⭐⭐⭐ | 缺少 :: cons 操作符、多行注释 |
| 工程质量 | ⭐⭐⭐ | 代码清晰；有死代码和重复 |
| 性能 | ⭐⭐⭐ | 操作符分发可用 Trie 优化 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [lexer.py:432] **非法字符直接 raise 终止词法分析** → 一个文件中两处非法字符只能看到第一个 → 改为跳过非法字符并收集到错误列表
- 追问：如果 GCC/Clang 遇到非法字符直接 crash，能被接受吗？→ **绝对不能。** 生产编译器应报告错误并继续解析。

#### 中等问题（影响特定场景）

- [lexer.py:153-158] `_make_error` 中 `end_col = self.column - 1` 计算有误
- [lexer.py:87] `PIPE_VARIANT` 定义了但从未被 lexer 生成（死 token）
- [lexer.py:19-91] 缺少 `::` cons 操作符 Token

#### 轻微问题（代码质量）

- [lexer.py:307-309] _read_identifier 中 BOOL 分支冗余
- [lexer.py:267-281] 字符和字符串的转义处理代码重复
- [lexer.py:90] UNIT token 在 lexer 中是死代码
- 缺少十六进制/Unicode 转义
- 操作符分发表效率可优化
- 缺少多行注释支持

---

## [2026-07-14] 语法分析器 (parser.py) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 递归下降结构清晰；管道操作符支持 |
| 可行性 | ⭐⭐⭐ | 基本语法正确；`|>` 优先级错误、step 被丢弃 |
| 正确性 | ⭐⭐ | `|>` 优先级严重错误；step 静默丢弃 |
| 安全性 | ⭐⭐⭐ | 无安全风险 |
| 一致性 | ⭐⭐⭐ | 无左递归；悬挂 else 不存在 |
| 完整性 | ⭐⭐ | Map 字面量语法未实现；`?` 只能出现在表达式末尾 |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰 |
| 性能 | ⭐⭐⭐ | 递归下降效率可接受 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [parser.py:432] **`|>` 管道操作符优先级错误** → 当前优先级最低（低于 `||`），`x |> f == y` 被解析为 `x |> (f == y)` → 将 _parse_pipe 移到 _parse_comparison_expr 之后、_parse_cons_expr 之前
- 追问：如果 OCaml 的管道操作符优先级错误，能被接受吗？→ **不能。** 几乎所有使用管道的场景都会产生类型错误。

- [parser.py:482-483] **`step` 表达式被静默丢弃** → `for i <- 1..10 step 2 { ... }` 中 step_expr 被解析但传入 ForExpr 时 `step=None` → 修正为 `step=step_expr`
- 追问：如果是 OCaml/Haskell 静默丢弃用户代码，能被接受吗？→ **绝对不能。**

#### 中等问题（影响特定场景）

- [parser.py:663-669] 链式比较 `a < b > c` 未被禁止，产生错误语义
- [parser.py:750-752] `?` 操作符只能出现在表达式末尾，不支持 `f(x)?.field`
- [parser.py] Map 字面量语法未实现（AST 有 MapExpr 但 parser 不生成）
- [parser.py:236] type 定义中变体分隔允许无 `|` 的换行分隔，对某些 token 类型可能出错

#### 轻微问题（代码质量）

- [parser.py:708-718] 负数字面量被解析为 UnaryOp(-, IntLiteral) 而非规范化
- 缺少字符串插值支持
- 缺少 `module` 关键字
- Block Span 不包含结束位置

---

## [2026-07-14] 错误处理 (errors.py) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | Rust 风格多行高亮、ANSI 颜色、批量错误收集 |
| 可行性 | ⭐⭐⭐⭐ | 错误格式化系统完整可用 |
| 正确性 | ⭐⭐⭐⭐ | 错误信息质量高 |
| 安全性 | ⭐⭐⭐ | 无安全风险 |
| 一致性 | ⭐⭐⭐ | Severity.WARNING 定义但未使用 |
| 完整性 | ⭐⭐⭐ | 大部分错误类型有覆盖 |
| 工程质量 | ⭐⭐⭐⭐ | 代码清晰 |
| 性能 | ⭐⭐⭐ | 无性能问题 |

### 发现的问题

#### 中等问题

- [errors.py:24-28] `Severity.WARNING` 定义了但未被实际使用
- [errors.py:402-408] `raise_all()` 将后续错误作为 note 附加，丢失 severity/span 信息

#### 轻微问题

- [errors.py:92,86] source_code vs source 命名不一致
- RuntimeError_ vs Python RuntimeError 混用

---

## [2026-07-14] 模块系统 (modules.py) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | ModuleResolver 路径解析设计合理 |
| 可行性 | ⭐⭐ | 嵌套 import 不工作 |
| 正确性 | ⭐⭐ | 模块加载时未传递 module_manager |
| 安全性 | ⭐⭐⭐ | 无安全风险 |
| 一致性 | ⭐⭐ | 导入逻辑在两处独立实现 |
| 完整性 | ⭐⭐⭐ | 基本功能可用 |
| 工程质量 | ⭐⭐⭐ | 有重复代码 |
| 性能 | ⭐⭐⭐ | 模块缓存机制正确 |

### 发现的问题

#### 严重问题

- [modules.py:240-241] **模块加载时未传递 module_manager** → 被导入模块内的嵌套 import 无法工作 → 传递 module_manager 参数

#### 中等问题

- [modules.py:127] 相对路径只搜索 search_paths[0]，设计脆弱
- [modules.py:98-102] 默认搜索路径含相对路径，受工作目录影响

#### 轻微问题

- [modules.py:276-299] _collect_exports 与 _collect_exported_types 逻辑重复
- [modules.py:305-339] 模块导入逻辑与 evaluator.py:608-637 重复实现

---

## [2026-07-14] 环境 (environment.py) 审查报告

### 发现的问题

#### 严重问题

- [environment.py:53,59] **assign 对未定义变量和不可变变量抛 Python 原生异常** → NameError 和 RuntimeError 不是 RuntimeError_ 子类，evaluator 的 except RuntimeError 无法捕获 → 改为抛 RuntimeError_

#### Evaluator vs VM 对比

无新增对比项（见 VM 报告）。

---

## [2026-07-14] C 代码生成 (c_codegen.py) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 直接从 AST 生成 C，设计直接 |
| 可行性 | ⭐⭐ | 最接近可用的后端；闭包和 TryExpr 有严重缺陷 |
| 正确性 | ⭐⭐ | 闭包不捕获变量、guard 位置错误、TryExpr 被忽略 |
| 安全性 | ⭐⭐ | 列表元素类型硬编码 int64_t |
| 一致性 | ⭐⭐ | 与 Evaluator/VM 语义差异大 |
| 完整性 | ⭐⭐⭐ | 大部分 AST 节点有处理 |
| 工程质量 | ⭐⭐ | 重复的 for 循环编译代码 |
| 性能 | ⭐⭐⭐ | 依赖外部 C 编译器 |

### 发现的问题

#### 严重问题

- [c_codegen.py:880] **闭包不捕获自由变量** → `nova_closure_new(fn, NULL, 0)` 环境永远为空 → 实现自由变量分析和捕获
- 追问：如果 OCaml 编译器生成的闭包不捕获自由变量，能被接受吗？→ **绝对不能。**

- [c_codegen.py:524-525] **TryExpr（? 操作符）被完全忽略** → 只编译内部表达式，Option/Result 错误传播丢失 → 实现错误传播代码生成

- [c_codegen.py:634-640] **Match guard 条件位置错误** → guard 检查在绑定执行之后，语义错误 → 将 guard 移到绑定之前

- [c_codegen.py:603-611] **IfExpr 缺少 else 分支时丢失返回值** → 返回空字符串导致无效 C 代码 → 返回默认值（如 UNIT）

#### 中等问题

- [c_codegen.py:397,974,1050] 列表元素类型硬编码为 int64_t
- [c_codegen.py:356-404 vs 1024-1071] for 循环编译代码重复

#### 轻微问题

- [c_codegen.py:646-705] PatternChar 未处理
- [c_codegen.py:534] 未处理表达式静默生成 C 注释

---

## [2026-07-14] Native 后端 (backend/native_backend.py) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐ | 标准 x86_64 代码生成 |
| 可行性 | ⭐ | 未接入编译管道；缺少关键指令 |
| 正确性 | ⭐ | Branch/Index/CallIndirect/FieldAccess 缺失或不正确 |
| 安全性 | ⭐⭐ | Panic 无错误信息 |
| 一致性 | ⭐ | 与 Nova 语义差异大 |
| 完整性 | ⭐ | 大量 NotImplementedError |
| 工程质量 | ⭐⭐ | LinearScanAllocator 未使用、SimpleNativeCompiler 是测试桩 |
| 性能 | ⭐⭐ | 无寄存器分配（用贪心分配） |

### 发现的问题

#### 严重问题

- [native_backend.py:489] **LIRCallIndirect（闭包调用）抛 NotImplementedError** → 函数式语言核心特性不可用
- [native_backend.py:497] **LIRFieldAccess（ADT 字段访问）抛 NotImplementedError** → ADT 模式匹配不可用
- [native_backend.py:410-415] **&&/|| 使用位运算（非短路求值）** → `and_reg_reg`/`or_reg_reg` 是位运算不是逻辑运算
- 追问：如果 OCaml 把 &&/|| 编译为非短路位运算，能被接受吗？→ **不能。**

#### 中等问题

- [native_backend.py:352-419] 浮点二元运算和浮点比较未实现
- [native_backend.py:35-82] LinearScanAllocator 实现了但从未使用
- [native_backend.py:729-751] _compile_counted_loop 是空壳方法

---

## [2026-07-14] Cranelift 后端 (backend/cranelift_backend.py) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐ | 标准 Cranelift IR 生成 |
| 可行性 | ⭐ | 生成的 CLIF IR 有严重错误，无法编译 |
| 正确性 | ⭐ | Branch 硬编码、Index 忽略操作数、类型硬编码 |
| 安全性 | ⭐⭐ | LIRStoreReg 静默忽略 |
| 一致性 | ⭐ | 与 Nova 语义差异大 |
| 完整性 | ⭐⭐ | LoadGlobal/StoreGlobal/StoreReg 有缺陷 |
| 工程质量 | ⭐⭐ | 多处静默忽略 |
| 性能 | ⭐⭐ | BinOp 不区分整数/浮点 |

### 发现的问题

#### 严重问题

- [cranelift_backend.py:163-168] **Branch 硬编码 block_false/block_true** → 所有条件分支跳到同一个不存在的块
- [cranelift_backend.py:188] **Index 忽略源操作数** → 硬编码 `v0 + 0`，任何数组索引读到错误地址
- [cranelift_backend.py:249-250] **函数调用参数类型全部硬编码为 i64** → 类型不匹配导致 Cranelift 编译失败
- 追问：如果 OCaml 的 native 编译器生成的代码不正确，能被接受吗？→ **绝对不能。**

#### 中等问题

- [cranelift_backend.py:199-200] LIRStoreReg 静默忽略（pass）
- [cranelift_backend.py:144] LIRLoadGlobal 结果未绑定到变量名
- [cranelift_backend.py:234] BinOp 不区分整数/浮点

#### 轻微问题

- [cranelift_backend.py:234] 浮点操作使用整数操作映射

---

## [2026-07-14] WASM 后端 (backend/wasm_backend.py) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐ | 标准 WASM 代码生成 |
| 可行性 | ⭐ | 多处致命错误，wat2wasm 无法编译通过 |
| 正确性 | ⭐ | Branch 丢失、Index 无地址、字符串编码错误 |
| 安全性 | ⭐⭐ | BuildADT 不存储字段 |
| 一致性 | ⭐ | 与 Nova 语义差异大 |
| 完整性 | ⭐ | LoadGlobal/StoreGlobal/CallIndirect 缺失 |
| 工程质量 | ⭐⭐ | 代码结构清晰但实现不完整 |
| 性能 | ⭐⭐ | i32.eqz 用于 i64 上下文 |

### 发现的问题

#### 严重问题

- [wasm_backend.py:261-263] **Branch 丢失 true 分支** → 只有 `br_if $block_false`，true 分支永远不跳转
- [wasm_backend.py:285-286] **Index 忽略索引参数** → 无地址计算，直接从栈顶加载
- [wasm_backend.py:161,371] **字符串 NUL 终止符编码错误** → `b"\\x00"` 是 6 字节字面值不是 NUL 字节
- [wasm_backend.py:273-276] **BuildADT 不存储 tag 和字段值** → 只分配内存但不写入

#### 中等问题

- [wasm_backend.py:205-227] 函数末尾缺少自动补全 return
- [wasm_backend.py:229-298] LIRCallIndirect 完全缺失

#### 轻微问题

- [wasm_backend.py:249] `!` 操作使用 i32.eqz 但上下文是 i64

---

## [2026-07-14] IR 系统 (ir/) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 三层 IR 设计（HIR→MIR→LIR）参考 MLIR 思想 |
| 可行性 | ⭐ | MIR lowering 大量信息丢失 |
| 正确性 | ⭐ | SSA 破坏、match 无条件分支、break/continue panic |
| 安全性 | ⭐⭐ | 无安全风险 |
| 一致性 | ⭐⭐ | 三层共享 NovaType 但无层间类型变换 |
| 完整性 | ⭐⭐ | HIR 覆盖完整；MIR/LIR 严重不完整 |
| 工程质量 | ⭐⭐ | Inlining 空壳、Pass 异常静默吞掉 |
| 性能 | ⭐⭐ | 优化 pass 大部分有实现但 MIR lowering 错误导致无意义 |

### 发现的问题

#### 严重问题

- [mir_lowering.py:267-275] **SSA 不变量被赋值操作破坏** → `self.env[name] = val_ssa` 直接覆盖，没有 phi 节点
- 追问：如果成熟编译器的 SSA 被破坏，能被接受吗？→ **绝对不能。** 所有依赖 SSA 的优化都会产生错误结果。

- [mir_lowering.py:46-83] **缺少真正的 SSA 构建过程** → 没有构建 dominance tree、放置 phi 节点

- [pass_manager.py:256-261] **Inlining pass 是空壳** → 只返回 False，注册在默认管道中但永远不做任何事

- [pass_manager.py:720-721,733-734,748-749] **Pass 异常被静默吞掉** → 三个 `run_*_passes` 方法都是 `except Exception: pass`
- 追问：如果 LLVM 的 opt 工具静默吞掉所有 pass 异常，能被接受吗？→ **绝对不能。** 用户以为编译成功但生成的二进制可能语义错误。

- [mir_lowering.py:245-248] **闭包自由变量捕获完全丢失** → Lambda 参数和函数体被丢弃，变为无名标签
- 追问：如果成熟编译器的闭包不工作，能被接受吗？→ **不能。** 闭包是函数式语言核心特性。

- [mir_lowering.py:343-376] **Match 模式信息完全丢失** → 所有 arm 通过无条件跳转依次连接，无条件执行所有分支
- 追问：如果 Haskell 编译器的 match 总执行第一个分支，能被接受吗？→ **不能。**

- [mir_lowering.py:259-265] **break/continue 被降级为 panic** → 运行时崩溃而非跳转到循环边界

#### 中等问题

- [mir_lowering.py:277-281] 列表推导式被降级为空列表常量
- [mir_lowering.py:388-403] For 循环缺少循环变量绑定
- [lir_lowering.py:204-211] MIRPhi 在 LIR lowering 中只取第一个源
- [hir_lowering.py:97-98] AliasDef 的目标类型信息丢失
- [hir_lowering.py:195-196] TryExpr 降级过于简化
- [pass_manager.py:104-107] 常量折叠通过猴子补丁修改 dataclass

#### 轻微问题

- [ir/__init__.py] 几乎为空，无公共 API 导出
- [lir_lowering.py:219-223] LIRBranch.cond_reg 未设置
- [ir_nodes.py:807-811] LIRCallIndirect 定义了但从未使用
- [pass_manager.py:713-753] 三个 run_*_passes 方法高度重复
- [hir_lowering.py:290-291] 未知 AST 节点静默替换为 UnitLiteral

---

## [2026-07-14] C 运行时 (runtime/nova_runtime.c) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 完整的数据结构实现（String/List/Map/ADT/Closure） |
| 可行性 | ⭐⭐ | 数据结构实现完整但 GC 空壳、内存安全有严重问题 |
| 正确性 | ⭐⭐ | 内存泄漏、use-after-free、命令注入 |
| 安全性 | ⭐ | 多处内存安全漏洞 |
| 一致性 | ⭐⭐⭐ | 与 Python 端数据结构基本一致 |
| 完整性 | ⭐⭐⭐ | HTTP/JSON/String/Map/List/ADT/Closure 都有实现 |
| 工程质量 | ⭐⭐ | 错误处理不完善 |
| 性能 | ⭐⭐ | 引用计数但实现不完整 |

### 发现的问题

#### 严重问题

- [nova_runtime.c:99-103] **GC 是空壳** → `nova_gc_collect()` 只返回差值，没有实际回收逻辑
- 追问：如果 OCaml 的运行时没有 GC，能被接受吗？→ **不能。** 内存必然泄漏。

- [nova_runtime.c:1623-1650] **HTTP 实现使用 system() 存在命令注入** → URL 含 `"` 字符可注入 shell 命令 → 替换为 libcurl 或 POSIX socket API

#### 中等问题

- [nova_runtime.c:479-486,735-741] release 不递减子对象引用计数
- [nova_runtime.c:525-526] nova_map_put 更新时不释放旧 value
- [nova_runtime.c:752-755] nova_closure_new 浅拷贝 captured 不 retain
- [nova_runtime.c:62-67] OOM 时直接 abort 无清理
- [nova_runtime.c:1151-1175] JSON 解析不验证 token 匹配
- [nova_runtime.c:290] nova_string_replace 整数溢出风险

#### 轻微问题

- [nova_runtime.c:833-834] read_file 失败返回空字符串，无法区分错误类型

---

## [2026-07-14] 测试套件 (tests/) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 覆盖度 | ⭐⭐⭐ | Evaluator 约 200+ 测试、VM 约 70+ 测试；但缺少多项核心特性测试 |
| 一致性 | ⭐ | 无 Evaluator-VM 一致性测试 |
| 端到端 | ⭐ | 所有后端测试只检查代码生成不验证运行结果 |
| 质量量 | ⭐⭐⭐ | 测试代码质量可接受 |

### 发现的问题

#### 严重问题

- [tests/ 全局] **所有四个后端无端到端运行验证** → C/WASM/x86_64/Cranelift 后端只检查生成代码字符串，不编译运行 → 添加端到端测试
- 追问：如果 GHC 缺少核心语言特性的测试，能被接受吗？→ **不能。** 不验证运行结果是严重缺陷。

- [tests/ 全局] **无 Evaluator-VM 一致性测试** → 两个执行路径独立测试，无交叉验证 → 添加参数化测试验证同一源码在两条路径的输出一致

---

## [2026-07-14] Tree-sitter (tree-sitter-nova/) 审查报告

### 发现的问题

#### 严重问题

- [grammar.js] **TryExpr 在 AST 中定义但 grammar.js 不支持** → IDE 高亮不处理 try/catch，Tree-sitter 查询无法匹配 → 在 grammar.js 添加 try_expr 规则

---

## 全局问题汇总

### 按严重程度统计

| 严重程度 | 数量 |
|---------|------|
| 严重 | 52 |
| 中等 | 42 |
| 轻微 | 36 |
| **总计** | **130** |

### 最高优先级修复项（Top 10）

1. **VM: CONTINUE 在 while 中空实现** [vm.py:717-728] — 语义完全错误
2. **编译器: guard/filter 被忽略** [compiler.py:662-706, 924-939] — 用户代码被静默丢弃
3. **求值器: guard 未实现** [evaluator.py:956-967] — 同上
4. **VM: 所有 pop 无栈下溢保护** [vm.py 全文] — 安全基础缺失
5. **VM: 闭包捕获整个帧** [vm.py:736-738] — 性能和语义问题
6. **类型检查器: HM 核心缺失** [type_checker.py 全局] — 类型系统名存实亡
7. **类型检查器: 任意 TypeVar 兼容** [type_checker.py:1318-1319] — 类型安全形同虚设
8. **IR: Pass 异常静默吞掉** [pass_manager.py:720-721] — 隐藏编译错误
9. **IR: MIR lowering 大量信息丢失** [mir_lowering.py] — 后端全部不可用
10. **C 运行时: HTTP 命令注入** [nova_runtime.c:1623-1650] — 安全漏洞