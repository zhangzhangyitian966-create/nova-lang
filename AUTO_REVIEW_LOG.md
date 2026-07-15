# Nova 编程语言 — 自动代码审查日志

> **审查标准**：生产级编译器/语言标准（参考 OCaml/Haskell/Elm/F# 最佳实践）
> **审查时间**：2026-07-14（第一轮）, 2026-07-15（第二轮）, 2026-07-15（第三轮）, 2026-07-15（第四轮）, 2026-07-15（第五轮）, 2026-07-15（第六轮）, 2026-07-15（第七轮）
> **审查版本**：main 分支最新提交

---

## 项目结构审查表

| 模块 | 文件 | 审查状态 | 上次审查 | 严重问题数 | 中等问题数 | 轻微问题数 |
|------|------|---------|---------|-----------|-----------|-----------|
| VM 虚拟机 | `vm.py` | ✅ 已审查 | 2026-07-15 | 9 | 11 | 14 |
| 编译器 | `compiler.py` | ✅ 已审查 | 2026-07-15 | 7 | 9 | 10 |
| 求值器 | `evaluator.py` | ✅ 已审查 | 2026-07-15 | 9 | 14 | 12 |
| AST 节点 | `ast_nodes.py` | ✅ 已审查 | 2026-07-15 | 0 | 0 | 1 |
| 类型检查器 | `type_checker.py` | ✅ 已审查 | 2026-07-15 | 13 | 17 | 15 |
| 词法分析器 | `lexer.py` | ✅ 已审查 | 2026-07-15 | 3 | 4 | 13 |
| 语法分析器 | `parser.py` | ✅ 已审查 | 2026-07-15 | 7 | 5 | 9 |
| 错误处理 | `errors.py` | ✅ 已审查 | 2026-07-15 | 9 | 11 | 8 |
| 模块系统 | `modules.py` | ✅ 已审查 | 2026-07-15 | 0 | 8 | 5 |
| 环境 | `environment.py` | ✅ 已审查 | 2026-07-15 | 0 | 0 | 0 |
| C 代码生成 | `c_codegen.py` | ✅ 已审查 | 2026-07-15 | 7 | 3 | 5 |
| Native 后端 | `backend/native_backend.py` | ✅ 已审查 | 2026-07-15 | 8 | 4 | 3 |
| Cranelift 后端 | `backend/cranelift_backend.py` | ✅ 已审查 | 2026-07-15 | 12 | 4 | 3 |
| WASM 后端 | `backend/wasm_backend.py` | ✅ 已审查 | 2026-07-15 | 11 | 4 | 2 |
| x86_64 指令发射 | `backend/x86_64.py` | ✅ 已审查 | 2026-07-15 | 1 | 0 | 3 |
| 编译管道 | `backend/compiler_pipeline.py` | ✅ 已审查 | 2026-07-15 | 3 | 1 | 0 |
| IR 节点 | `ir/ir_nodes.py` | ✅ 已审查 | 2026-07-15 | 1 | 1 | 5 |
| HIR Lowering | `ir/hir_lowering.py` | ✅ 已审查 | 2026-07-15 | 1 | 7 | 7 |
| MIR Lowering | `ir/mir_lowering.py` | ✅ 已审查 | 2026-07-15 | 9 | 3 | 1 |
| LIR Lowering | `ir/lir_lowering.py` | ✅ 已审查 | 2026-07-15 | 7 | 3 | 2 |
| Pass 管理器 | `ir/pass_manager.py` | ✅ 已审查 | 2026-07-15 | 2 | 7 | 5 |
| C 运行时 | `runtime/nova_runtime.c` | ✅ 已审查 | 2026-07-15 | 15 | 13 | 8 |
| 测试套件 | `tests/` | ✅ 已审查 | 2026-07-15 | 7 | 1 | 1 |
| Tree-sitter | `tree-sitter-nova/` | ✅ 已审查 | 2026-07-15 | 3 | 2 | 1 |

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

## 第一轮全局问题汇总

### 按严重程度统计

| 严重程度 | 数量 |
|---------|------|
| 严重 | 52 |
| 中等 | 42 |
| 轻微 | 36 |
| **总计** | **130** |

### 第一轮最高优先级修复项（Top 10）

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

---

## 第二轮修复进展（2026-07-15）

### 已修复问题汇总

| 模块 | 修复的问题 | 修复数量 |
|------|-----------|---------|
| VM 虚拟机 | pop 栈下溢保护、CONTINUE while 实现、id()字典键改为计数器、RETURN flag 机制、base_sp 截断栈、try/finally 帧保护 | 6/8 |
| 编译器 | PatternFloat/Char 测试代码生成、match guard 编译、列表推导式 filter、for 循环栈一致性 | 4/8 |
| 求值器 | MapExpr 实现、Pattern guard 实现、UNIT_VALUE bool 修复、构造器 field_names、str_to_int field_names、environment assign 异常修复 | 6/9 |
| 类型检查器 | Lambda 多参数唯一 TypeVar、check_decl 死代码删除、未知类型名报错、部分错误返回值修复 | 4/14 |
| C 代码生成 | TryExpr 实现、Match guard 位置修复 | 2/6 |
| MIR Lowering | break/continue 正确生成跳转指令 | 1/7 |
| 模块系统 | module_manager 传递（嵌套 import 修复） | 1/5 |
| 错误处理 | assign 异常类型统一为 RuntimeError_ | 1/4 |

**总计修复：25/68（37%）**

---

## [2026-07-15] VM 虚拟机 (vm.py) 第二轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | PIPE_CALL、MATCH_START/END、TRY_UNWRAP 有特色 |
| 可行性 | ⭐⭐⭐ | 核心路径可用；循环控制有严重 bug |
| 正确性 | ⭐⭐ | CONTINUE while 启发式检测、闭包过度捕获、PRINT 未推 UNIT |
| 安全性 | ⭐⭐ | _pop 有保护但部分路径仍无检查 |
| 一致性 | ⭐⭐ | 与 Evaluator 多处行为差异 |
| 完整性 | ⭐⭐⭐⭐⭐ | 47 个操作码全部有处理 |
| 工程质量 | ⭐⭐ | _execute_instruction 仍过长 |
| 性能 | ⭐⭐ | 闭包捕获整个帧 dict 浅拷贝 |

### 严重问题
- [vm.py:783-786] **闭包仍捕获整个帧 locals 而非仅自由变量** → CLOSURE 指令第三个操作数被忽略 → 编译器分析自由变量，VM 只拷贝指定变量
- 追问：如果 OCaml 闭包捕获整个作用域的 dict 拷贝，能被接受吗？→ **绝对不能。**

- [vm.py:682-685] **CONTINUE while 循环依赖启发式回跳检测** → 通过试探下一条指令是否为 CONST_UNIT 推断 loop_start，极其脆弱 → 编译器应为 while 生成显式循环元数据
- 追问：如果 GHC 的 STG 机通过运行时扫描字节码确定循环边界，能被接受吗？→ **绝对不能。**

- [vm.py:1132-1138] **PRINT 指令弹栈但不推值** → 栈不变量违反，后续指令可能栈下溢 → 在 PRINT 末尾添加 `self.stack.append(UNIT)`
- 追问：任何字节码 VM 的指令必须精确维护栈不变量。CPython 的 PRINT_EXPR 推入 None。**不可接受。**

- [vm.py:560-571] **STORE_VAR 忽略 mutable 操作数** → let 绑定的不可变性未被 VM 强制执行 → 检查 mutable 标志

### 中等问题
- [vm.py:180-217] 内置函数 lambda 缺少类型检查 → 用户看到 Python TypeError 而非 Nova 错误
- [vm.py:1150-1160] TRY_UNWRAP 对非 ADT 值静默通过 → 非法类型应报错
- [vm.py:748-755] while BREAK 仍用脆弱的前向扫描 → 应由编译器提供 end_ip

### 轻微问题
- [vm.py:1127-1130] DUP 无栈空检查
- [vm.py:989-1042] MATCH_TEST_* 系列除 MATCH_CONSTRUCTOR 外无栈空检查
- [vm.py:854-858] INDEX 无边界检查
- [vm.py:615-619] CONCAT 强制转 str 类型检查宽松
- [vm.py:70-71] NovaADTValue __hash__ 与 Evaluator 不一致
- [vm.py:180] read_line lambda 代码意图不清
- [vm.py:500-507] _pop(1) 返回裸值的设计模式容易出错

### Evaluator vs VM 对比
| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| Unit bool | False | False | ✅ **已修复** |
| ? 对 Some/Ok | 不解包返回原值 | 解包 push fields[0] | ❌ **严重 bug** |
| ? 对 None/Err | 抛 ReturnSignal | 返回 True 触发 early return | 机制不同效果类似 |
| Map | 支持 MapExpr | 支持 BUILD_MAP | ✅ |
| 构造器 field_names | 有 | 有 | ✅ **已修复** |
| str_to_int field_names | 有 | 有 | ✅ **已修复** |
| PRINT 返回值 | 返回 UNIT_VALUE | **不返回任何值** | ❌ |
| ADT __hash__ | 未定义（不可哈希） | 已定义 | ❌ |
| read_line EOF | 捕获 EOFError | 不捕获 | ❌ |
| 闭包捕获 | Environment 引用 | locals dict 浅拷贝 | ❌ |

---

## [2026-07-15] 编译器 (compiler.py) 第二轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | PIPE_CALL、MATCH_START/END、ADT 原生指令集 |
| 可行性 | ⭐⭐⭐ | 核心路径可用；guard/filter 已修复；PatternTuple/List 仍无测试 |
| 正确性 | ⭐⭐ | || true 路径值丢失（新发现）、Block/Break 栈错位 |
| 安全性 | ⭐⭐⭐ | 栈布局大部分正确 |
| 一致性 | ⭐⭐⭐ | 跳转回填全部正确 |
| 完整性 | ⭐⭐⭐⭐ | AST 所有节点有编译处理 |
| 工程质量 | ⭐⭐ | 遗留死代码方法 |
| 性能 | ⭐⭐⭐ | 闭包不做自由变量分析 |

### 严重问题
- [compiler.py:502-511] **`||` 运算 true 路径值丢失（新发现）** → JUMP_IF_TRUE 弹出 left 值后跳转，栈上无结果 → 改为 DUP + JUMP_IF_TRUE + POP 模式
- 追问：如果 Java 的 || 在左侧为 true 时丢失返回值，能被接受吗？→ **绝对不能。**

- [compiler.py:867-874] **Block 中 BreakExpr/ContinueExpr 后多余 POP** → 控制流指令不推值但编译器发 POP → 排除 BreakExpr/ContinueExpr

- [compiler.py:763-764] **PatternTuple/PatternList 模式匹配无实际测试** → 直接返回 None 表示"总是匹配" → 为每种 Pattern 生成逐元素测试
- 追问：如果 GHC 对 tuple pattern 跳过测试代码生成，能被接受吗？→ **绝对不能。**

- [compiler.py:302-345] **模块导入内联无命名空间隔离** → 同名导出后者覆盖前者无警告 → 实现限定导入

### 中等问题
- [compiler.py:930-947] while 循环返回值始终 Unit，违反"返回最后一次迭代值"语义
- [compiler.py:801-865] 两个遗留死代码方法 _compile_pattern_test/_compile_pattern_bindings
- [compiler.py:395-396] CharLiteral 编译为 CONST_STRING，运行时无法区分
- [compiler.py:377] 闭包捕获整个帧（与 VM 同一问题）

### 轻微问题
- [compiler.py Op 类] 多个已定义但未生成的操作码（LOAD_CONST, LOOP, DUP, PRINT, AND, OR）
- [compiler.py:80 vs 377] CLOSURE code_key 注释与实际不一致
- [compiler.py:949-1010] 列表推导式不支持多 for 子句
- [compiler.py:969-1010] filter 代码与 _compile_for 高度重复

### 原创性分析
- **Nova 特色**：PIPE_CALL 指令、MATCH_START/END 标记对、ADT 原生指令集（MAKE_ADT/REGISTER_CTOR）、常量值直接内联
- **参考已有**：基本栈机结构参考 CPython/JVM

---

## [2026-07-15] 求值器 (evaluator.py) 第二轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 两遍扫描支持相互递归 |
| 可行性 | ⭐⭐⭐ | 核心特性可用；MapExpr 已修复 |
| 正确性 | ⭐⭐ | ? 不解包 Some/Ok（新发现）、String/Char 无区分 |
| 安全性 | ⭐⭐ | 无递归深度保护 |
| 一致性 | ⭐⭐ | 与 VM 多处行为差异 |
| 完整性 | ⭐⭐⭐⭐ | AST 覆盖完整 |
| 工程质量 | ⭐⭐ | eval_decl 重复代码 |
| 性能 | ⭐⭐⭐ | 闭包引用语义效率可接受 |

### 严重问题
- [evaluator.py:698-704] **`?` 操作符不解包 Some/Ok（新发现严重 bug）** → `let x = some_option?` 得到 `Some(value)` 而非 `value` → 添加解包逻辑
- 追问：如果是 Rust 的 `?` 不解包 Some，能被接受吗？→ **绝对不能。核心语义错误。**

- [evaluator.py:832-842] **`&&`/`||` 返回硬编码 Python bool** → `left && right` 返回 False/True 而非实际操作数值 → 返回 falsy/truthy 值本身
- 追问：如果是 OCaml 的 `&&` 返回非类型正确值，能被接受吗？→ **不可接受。**

- [evaluator.py:663-667] **String/Char 运行时无区分** → 都用 Python str，PatternChar 用 len==1 区分不可靠 → 引入 NovaChar 包装类
- 追问：OCaml/Haskell 中 char 和 string 是不同的运行时类型。**不可接受。**

- [evaluator.py:212-222] **head/tail 返回 Option 缺少 field_names** → 与其他内置函数不一致 → 补 field_names

### 中等问题
- [evaluator.py:553-608] eval_decl 与 _collect_decl + _eval_decl_body 大量重复
- [evaluator.py:894-895] for 循环范围包含 end（`..` 视为 `..=`）
- [evaluator.py:203] _builtin_filter 用 `is True` 严格比较而非 truthiness
- [evaluator.py:760-765] Assignment except RuntimeError 不必要

### 轻微问题
- [evaluator.py:171-222] 内置函数缺少参数数量/类型检查
- [evaluator.py:358-370] floor/ceil/round 返回 float 而非匹配输入类型
- [evaluator.py:337] _builtin_pow 使用 math.pow 返回 float
- [evaluator.py:270-271] JSON null 映射为 Option.None 设计决策
- [environment.py:40,48] lookup/lookup_binding 仍抛 NameError

---

## [2026-07-15] 类型检查器 (type_checker.py) 第二轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 自定义类型系统框架 |
| 可行性 | ⭐⭐ | TypeVar 全兼容掩盖大量问题 |
| 正确性 | ⭐ | 缺少 HM 核心（unification/generalize/instantiate） |
| 安全性 | ⭐⭐ | 未知类型名已修复报错；TypeVar 全兼容仍是隐患 |
| 一致性 | ⭐⭐⭐ | ADTType.__eq__ 正确比较类型参数 |
| 完整性 | ⭐⭐ | Pattern 大部分有检查；let 多态未实现 |
| 工程质量 | ⭐⭐⭐ | 死代码已删除 |
| 性能 | ⭐⭐⭐ | 类型检查效率可接受 |

### 严重问题
- [type_checker.py:1081-1257] **没有实现 Unification** → 局部绑定字典不持久，函数返回后丢失 → 实现标准 Union-Find Unification
- 追问：如果 OCaml 的类型推断器缺少 unification，能被接受吗？→ **绝对不能。HM 算法的核心。**

- [type_checker.py:516-757] **没有实现 Generalize/Instantiate** → let 绑定不做泛化，`let id = fun x -> x in id 1 + id "a"` 不报错 → 实现 let 多态
- 追问：如果 OCaml 的 let 多态没有正确实现，能被接受吗？→ **绝对不能。ML 系语言根基。**

- [type_checker.py:1233] **任意两个 TypeVar 被视为兼容** → 任何未推断类型表达式可赋值任何类型 → 通过 unification 求解
- 追问：如果 Haskell 的 Maybe Int 和 Maybe String 被当作同一类型，能被接受吗？→ **绝对不能。**

- [type_checker.py:986-995] **PatternConstructor 不替换类型参数** → 泛型 ADT 模式匹配不正确 → 构建类型参数映射替换

- [type_checker.py:289-291] **Err 内置函数返回类型引用错误 TypeVar** → `Err("error")` 返回 Result[T, String]（T 是 Ok 的 TypeVar）→ 使用独立 TypeVar

### 中等问题
- [type_checker.py] 不支持 cons 模式（head :: tail）
- [type_checker.py:857-865] TryExpr 对非 Result/Option 静默通过
- [type_checker.py:877-886] ForExpr 不推断迭代变量类型
- [type_checker.py:908-909] ListComprehension 不推断迭代变量类型
- [type_checker.py:1034-1042] % 和 ++ 错误后返回 INT_T/STRING_T 而非 ERROR_TYPE
- [type_checker.py:354] 注释声称 Int 自动转 Float 未实现
- [type_checker.py:248] collect_errors 默认 False
- [type_checker.py:718-733] 管道操作符类型检查过于宽松

### 新引入问题
- [type_checker.py:971-995 vs 783-853] PatternConstructor 不替换类型参数但 FieldAccess 已实现替换 → 不一致
- [type_checker.py:443-448 vs 528] 两遍扫描中 let/mut 类型更新存在竞态
- [type_checker.py:435] AliasDef 的 target_type 解析不使用 local_types

---

## [2026-07-15] 词法分析器 (lexer.py) 第二轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | Token 位置追踪完善 |
| 可行性 | ⭐⭐⭐ | 基本词法分析可用；非法字符直接终止 |
| 正确性 | ⭐⭐⭐ | 转义字符基本正确 |
| 安全性 | ⭐⭐⭐ | 无安全风险 |
| 一致性 | ⭐⭐⭐ | 与 parser 配合良好 |
| 完整性 | ⭐⭐⭐ | 缺少 :: cons、多行注释 |
| 工程质量 | ⭐⭐⭐ | 有死代码和重复 |
| 性能 | ⭐⭐⭐ | 可优化 |

### 严重问题
- [lexer.py:432] **非法字符直接 raise 终止词法分析** → 只能看到第一个非法字符 → 改为跳过并收集到错误列表
- 追问：如果 GCC/Clang 遇到非法字符直接 crash，能被接受吗？→ **绝对不能。**

### 中等问题
- [lexer.py:153-158] _make_error 中 end_col 计算有误

### 轻微问题
- [lexer.py:87,90] PIPE_VARIANT 和 UNIT 是死 token
- [lexer.py:307-309] BOOL 分支冗余
- [lexer.py:234-249,267-281] 转义处理代码重复
- [lexer.py:356-401] 操作符分发表用 if 链
- 缺少十六进制/Unicode 转义
- 缺少多行注释
- 缺少 \f、\v 空白字符处理

---

## [2026-07-15] 语法分析器 (parser.py) 第二轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 递归下降结构清晰 |
| 可行性 | ⭐⭐⭐ | 基本语法正确 |
| 正确性 | ⭐⭐ | step 变量遮蔽（新发现）、|> 优先级反直觉 |
| 安全性 | ⭐⭐⭐ | 无安全风险 |
| 一致性 | ⭐⭐⭐ | 无左递归 |
| 完整性 | ⭐⭐ | Map 字面量语法未实现、PatternChar 缺失 |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰 |
| 性能 | ⭐⭐⭐ | 递归下降效率可接受 |

### 严重问题
- [parser.py:460,471,484] **step 表达式变量遮蔽 Bug（新发现/旧问题残留）** → step_expr 在 elif 内赋值但被外层遮蔽，始终为 None → 删除 line 471 的重复初始化
- 追问：如果成熟语言的循环 step 被静默丢弃，**完全不可接受。**

### 中等问题
- [parser.py:432-439,665] |> 优先级高于所有比较/逻辑操作符（反直觉但可能是有意设计）
- [parser.py:572-580] 负数模式 Span 不覆盖数字部分
- [parser.py:523] match arm 前瞻列表缺少 CHAR，方式脆弱
- [parser.py:531-536] match arm 缺少 guard 支持
- [parser.py:464-466] <- 两步解析导致 `for i < -5..10` 误解析
- [parser.py:414] Block Span 不包含结束位置

### 轻微问题
- [parser.py:790-792] TokenType.UNIT 检查是死代码
- [parser.py:542-622] 缺少 PatternChar 解析
- [parser.py:664-670] 链式比较未禁止
- [parser.py:751] ? 只能出现在表达式末尾

---

## [2026-07-15] 错误处理 + 模块 + 环境 第二轮审查报告

### 严重问题
- [errors.py:402-408] **raise_all() 丢失后续错误的 severity 和 span** → str(note) 扁平化，后续 ERROR 降级为 NOTE → 直接传递结构化 RelatedNote
- 追问：如果 Rust 编译器 10 个错误中 9 个丢失源码位置，能被接受吗？→ **绝对不能。**

- [errors.py:232-258] **RelatedNote 使用主错误的 source_code 渲染** → 跨文件错误显示错误源码 → RelatedNote 需携带自己的 source_code
- 追问：Rust 编译器每个诊断独立加载对应文件源码。缺少则跨模块错误可读性为零。

- [environment.py:40,48] **lookup/lookup_binding 仍抛 Python NameError** → 与已修复的 assign 不一致 → 统一改为 RuntimeError_

### 中等问题
- [modules.py:98-105] 默认搜索路径含相对路径，受工作目录影响
- [modules.py:241] ModuleManager.load_module 中 Evaluator 未传递 current_file
- [evaluator.py:610-642] _handle_import_decl 与 ModuleManager.import_module 重复实现
- [errors.py:331-348] BreakSignal/ContinueSignal/ReturnSignal 不携带 span 信息
- [errors.py:86 vs 92] source vs source_code 命名不一致
- [modules.py:276-299] _collect_exports 与 _collect_exported_types 重复

### 轻微问题
- [errors.py:393-395] ErrorCollector.get_all() 丢失时序信息
- [errors.py] ErrorCollector 未被 evaluator 使用
- [modules.py:56] get_exported_bindings except NameError 静默吞错误
- [modules.py:274] loading_stack.remove O(n) 效率

---

## [2026-07-15] 后端 第二轮审查报告

### 各后端可行性评估
| 后端 | 等级 | 判断依据 |
|------|------|----------|
| c_codegen.py | Alpha-可用 | 覆盖最广，但闭包不捕获、浮点列表类型错误 |
| native_backend.py | Demo | 浮点 BinOp 缺失、LIRCallIndirect 未实现、寄存器分配冲突 |
| cranelift_backend.py | 纯文本生成器 | Branch 硬编码、Index 忽略参数，不可编译 |
| wasm_backend.py | Demo | 字符串编码 bug、BuildADT 不写数据，wat2wasm 无法通过 |

### 严重问题
- [wasm_backend.py:161] **字符串 NUL 终止符编码错误** → `b"\\x00"` 是 4 字节字面值非 NUL → 改为 `b'\x00'`
- [cranelift_backend.py:163-168] **Branch 硬编码 block_false/block_true** → 所有条件分支跳到不存在的块
- [native_backend.py:497] **LIRCallIndirect 抛 NotImplementedError** → 函数式语言核心特性不可用
- [compiler_pipeline.py:34] **native 后端映射到 Cranelift 而非 NativeCodeGen** → "native" 选项实际使用 Cranelift
- [wasm_backend.py:273-276] **BuildADT 不存储 tag 和字段值** → 运行时读到未初始化内存
- [c_codegen.py:897] **闭包不捕获自由变量** → `nova_closure_new(fn, NULL, 0)` 环境永远为空
- 追问：如果 OCaml 编译器生成的闭包不捕获自由变量，能被接受吗？→ **绝对不能。**

### 中等问题
- [native_backend.py:363-427] 浮点二元运算全部走整数路径
- [cranelift_backend.py:249] 函数调用参数类型全部硬编码 i64
- [c_codegen.py:615-623] IfExpr 无 else 返回 "0" 而非编译错误
- [c_codegen.py:397,991] 列表元素类型硬编码 int64_t
- [wasm_backend.py:261-263] Branch 丢失 true 分支
- [native_backend.py:329-331] callee-saved 寄存器与贪心分配器冲突

---

## [2026-07-15] IR 系统 + Pass 管理器 第二轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 三层 IR 设计参考 MLIR 思想 |
| 可行性 | ⭐ | MIR lowering 大量信息丢失 |
| 正确性 | ⭐ | SSA 被破坏、match 无条件分支、闭包丢失 |
| 安全性 | ⭐⭐ | 无安全风险 |
| 一致性 | ⭐⭐ | 三层共享 NovaType 但无层间变换 |
| 完整性 | ⭐⭐ | HIR 覆盖完整；MIR/LIR 严重不完整 |
| 工程质量 | ⭐⭐ | Inlining 空壳、Pass 异常仍不理想 |
| 性能 | ⭐⭐ | 优化 pass 有实现但上游 IR 错误 |

### 严重问题
- [mir_lowering.py:276-282] **SSA 不变量被赋值操作破坏** → 无 phi 节点、无支配树 → 实现标准支配边界算法
- 追问：如果成熟编译器的 SSA 被破坏，能被接受吗？→ **绝对不能。**

- [mir_lowering.py:247-250] **闭包自由变量捕获完全丢失** → Lambda body 被丢弃
- 追问：如果成熟编译器的闭包不工作，能被接受吗？→ **不能。**

- [mir_lowering.py:351-384] **Match 模式信息完全丢失** → 所有 arm 无条件跳转依次执行
- 追问：如果 Haskell 编译器的 match 总执行第一个分支，能被接受吗？→ **不能。**

- [mir_lowering.py:396-417] **For 循环缺少循环变量绑定** → hir_expr.variable 从未使用
- [pass_manager.py:256-261] **Inlining pass 仍是空壳** → return False

### 中等问题
- [mir_lowering.py:285-289] 列表推导式降级为空列表
- [lir_lowering.py:204-211] MIRPhi 只取第一个源
- [lir_lowering.py:219-223] LIRBranch.cond_reg 未设置
- [hir_lowering.py:97-98] AliasDef 目标类型信息丢失
- [hir_lowering.py:195-196] TryExpr 降级过于简化
- [pass_manager.py:715-761] 三个 run_*_passes 方法仍高度重复
- [pass_manager.py:105-109] 常量折叠通过猴子补丁修改 dataclass

---

## [2026-07-15] C 运行时 + 测试 + Tree-sitter 第二轮审查报告

### 严重问题
- [nova_runtime.c:99-103] **GC 仍是空壳** → 无循环引用回收，内存必然泄漏
- 追问：如果 OCaml 的运行时没有 GC，能被接受吗？→ **不能。**

- [nova_runtime.c:1623-1664] **HTTP 使用 system() 存在命令注入** → URL 含 shell 字符可执行任意命令 → 替换为 libcurl 或 socket API

### 中等问题
- [nova_runtime.c:524-526] nova_map_put 更新时不释放旧 value → 内存泄漏
- [nova_runtime.c:363-368] nova_list_set 不释放旧元素 → 内存泄漏
- [nova_runtime.c:735-742] nova_adt_release 不递减字段引用计数 → 内存泄漏
- [nova_runtime.c:748-762] nova_closure_new 浅拷贝 captured 不 retain → 悬垂指针风险
- [nova_runtime.c:1151-1175] JSON 解析不验证 token 匹配
- [nova_runtime.c:290] nova_string_replace 整数溢出风险
- [nova_runtime.c:831-848] read_file 失败返回空字符串
- C 端字符串长度是字节长度 vs Python 端 Unicode 字符长度
- C 端 Map 遍历顺序不确定 vs Python 端保持插入顺序

### 测试覆盖问题
- **Evaluator 测试 ~86 个，VM 测试 ~83 个**（数量相当）
- **无 Evaluator-VM 一致性测试** → 两个执行后端语义可能不同
- **所有四个后端无端到端运行验证** → 只检查代码文本不验证执行结果
- **零测试特性**：try 表达式、map 表达式、赋值表达式、索引访问、while-break/continue、char 字面量行为、export 行为
- 追问：如果 GHC 缺少核心语言特性的测试，能被接受吗？→ **不能。GHC 有数千测试。**

### Tree-sitter
- [grammar.js] **TryExpr 仍未添加** → IDE 无法高亮/解析 try 表达式
- [grammar.js] 缺少泛型类型参数语法（如 `Option[Int]`）

---

## 第二轮全局问题汇总

### 按严重程度统计

| 严重程度 | 第一轮 | 第二轮 | 总计 |
|---------|--------|--------|------|
| 严重 | 52 | 47 | 99 |
| 中等 | 42 | 47 | 89 |
| 轻微 | 36 | 49 | 85 |
| **总计** | **130** | **143** | **273** |

### 第二轮最高优先级修复项（Top 15）

1. **求值器: ? 不解包 Some/Ok** [evaluator.py:698-704] — 核心语义错误（新发现）
2. **编译器: || true 路径值丢失** [compiler.py:502-511] — 栈不变量违反（新发现）
3. **VM: PRINT 未推 UNIT** [vm.py:1132-1138] — 栈不变量违反（新发现）
4. **VM: 闭包仍捕获整个帧** [vm.py:783-786] — 未修复
5. **VM: CONTINUE while 启发式检测** [vm.py:682-685] — 脆弱（部分修复但方案不正确）
6. **编译器: PatternTuple/PatternList 无测试** [compiler.py:763-764] — 未修复
7. **编译器: Block BreakExpr 后多余 POP** [compiler.py:867-874] — 未修复
8. **类型检查器: HM 核心缺失** [type_checker.py] — 未修复
9. **类型检查器: 任意 TypeVar 兼容** [type_checker.py:1233] — 未修复
10. **C 运行时: HTTP 命令注入** [nova_runtime.c:1623-1664] — 安全漏洞未修复
11. **IR: MIR lowering 大量信息丢失** [mir_lowering.py] — 未修复
12. **IR: Pass 异常吞掉后仍继续** [pass_manager.py:715-761] — 部分修复但仍不理想
13. **错误处理: raise_all 丢失结构化信息** [errors.py:402-408] — 未修复
14. **parser: step 变量遮蔽** [parser.py:460,471,484] — 未修复
15. **测试: 无 Evaluator-VM 一致性测试** [tests/] — 未修复

---

## [2026-07-15] 第三轮全局审查报告

> **审查时间**：2026-07-15（第三轮）
> **审查版本**：main 分支最新提交
> **审查方法**：三轮九个 Explore Agent 并行审查

### 项目结构审查表（第三轮更新）

| 模块 | 文件 | 审查状态 | 上次审查 | 严重 | 中等 | 轻微 | 修复率 |
|------|------|---------|---------|------|------|------|--------|
| VM 虚拟机 | `vm.py` | ✅ 已审查 | 2026-07-15 | 5 | 6 | 7 | 6/32 (19%) |
| 编译器 | `compiler.py` | ✅ 已审查 | 2026-07-15 | 3 | 3 | 4 | 6/11 (55%) |
| 求值器 | `evaluator.py` | ✅ 已审查 | 2026-07-15 | 4 | 7 | 6 | 3/9 (33%) |
| AST 节点 | `ast_nodes.py` | ✅ 已审查 | 2026-07-15 | 0 | 0 | 0 | — |
| 类型检查器 | `type_checker.py` | ✅ 已审查 | 2026-07-15 | 4 | 7 | 8 | 5/12 (42%) |
| 词法分析器 | `lexer.py` | ✅ 已审查 | 2026-07-15 | 1 | 1 | 6 | 1/5 (20%) |
| 语法分析器 | `parser.py` | ✅ 已审查 | 2026-07-15 | 3 | 2 | 4 | 3/10 (30%) |
| 错误处理 | `errors.py` | ✅ 已审查 | 2026-07-15 | 5 | 7 | 5 | 1/11 (9%) |
| 模块系统 | `modules.py` | ✅ 已审查 | 2026-07-15 | 0 | 3 | 2 | 1/5 (20%) |
| 环境 | `environment.py` | ✅ 已审查 | 2026-07-15 | 0 | 0 | 0 | 已修复 |
| C 代码生成 | `c_codegen.py` | ✅ 已审查 | 2026-07-15 | 3 | 3 | 2 | 0/6 (0%) |
| Native 后端 | `backend/native_backend.py` | ✅ 已审查 | 2026-07-15 | 3 | 2 | 3 | 0/4 (0%) |
| Cranelift 后端 | `backend/cranelift_backend.py` | ✅ 已审查 | 2026-07-15 | 5 | 3 | 1 | 0/4 (0%) |
| WASM 后端 | `backend/wasm_backend.py` | ✅ 已审查 | 2026-07-15 | 5 | 4 | 1 | 0/4 (0%) |
| x86_64 指令 | `backend/x86_64.py` | ✅ 已审查 | 2026-07-15 | 0 | 0 | 2 | — |
| 编译管道 | `backend/compiler_pipeline.py` | ✅ 已审查 | 2026-07-15 | 1 | 0 | 0 | 0/1 (0%) |
| IR 节点 | `ir/ir_nodes.py` | ✅ 已审查 | 2026-07-15 | 0 | 0 | 2 | — |
| HIR Lowering | `ir/hir_lowering.py` | ✅ 已审查 | 2026-07-15 | 0 | 2 | 3 | — |
| MIR Lowering | `ir/mir_lowering.py` | ✅ 已审查 | 2026-07-15 | 5 | 1 | 0 | 1/7 (14%) |
| LIR Lowering | `ir/lir_lowering.py` | ✅ 已审查 | 2026-07-15 | 3 | 2 | 1 | 0/3 (0%) |
| Pass 管理器 | `ir/pass_manager.py` | ✅ 已审查 | 2026-07-15 | 1 | 3 | 1 | 1/4 (25%) |
| C 运行时 | `runtime/nova_runtime.c` | ✅ 已审查 | 2026-07-15 | 7 | 6 | 5 | 0/10 (0%) |
| 测试套件 | `tests/` | ✅ 已审查 | 2026-07-15 | 3 | 0 | 0 | 0/3 (0%) |
| Tree-sitter | `tree-sitter-nova/` | ✅ 已审查 | 2026-07-15 | 1 | 0 | 0 | 0/1 (0%) |

---

## [2026-07-15] VM 虚拟机 (vm.py) 第三轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | PIPE_CALL/MATCH_START-END/TRY_UNWRAP 设计有特色 |
| 可行性 | ⭐⭐⭐½ | 核心路径可用；循环控制基本修复但仍依赖启发式 |
| 正确性 | ⭐⭐½ | 闭包过度捕获、CONTINUE 启发式、_pop 单值返回模式有隐患 |
| 安全性 | ⭐⭐⭐ | _pop 有保护；DUP/INDEX 等仍有裸访问 |
| 一致性 | ⭐⭐⭐ | PRINT/STORE_VAR 等第二轮严重问题已修复；部分与 Evaluator 不一致 |
| 完整性 | ⭐⭐⭐⭐⭐ | Op 类 46 个操作码全部有处理路径 |
| 工程质量 | ⭐⭐½ | _execute_instruction 约 665 行，仍未拆分 |
| 性能 | ⭐⭐ | 闭包捕获整个帧 dict 浅拷贝未改善 |

### 发现的问题

#### 严重问题（5 个）

- [vm.py:786-787] **闭包仍捕获整个帧 locals 而非仅自由变量** → 每次创建闭包 O(n) 浅拷贝所有局部变量，阻止 GC 回收不需要的变量，语义错误（修改不反映到原始帧）→ 编译器分析自由变量，CLOSURE 指令携带 free_var_names
- 追问：如果 OCaml 闭包捕获整个作用域的 dict 拷贝，能被接受吗？→ **绝对不能。** 连续三轮未修复。

- [vm.py:682-687,770-777] **CONTINUE while 循环依赖启发式检测** → 通过试探下一条指令是否为 CONST_UNIT 推断 loop_start，极其脆弱 → 编译器为 while 生成显式 LOOP 指令
- 追问：如果 GHC 的 STG 机通过运行时扫描字节码确定循环边界，能被接受吗？→ **绝对不能。** 连续三轮未根本修复。

- [vm.py:500-507] **`_pop(n)` 当 n==1 返回裸值，n>1 返回列表，类型不一致** → 多处调用需 `if arg_count == 1: args = [args]` 补偿，一旦遗漏后续 `for i, arg in enumerate(args)` 会遍历裸值字符 → 统一 `_pop(n)` 返回列表
- 追问：如果 JVM 的 pop() 和 pop2() 返回类型不同但调用方不做检查，会导致类型混淆。→ **不可接受。**

- [vm.py:414-426] **`_call_closure` 异常安全路径不完整** → 函数执行异常时 result 不被赋值，finally 截断栈后 re-raise，调用方栈状态可能不一致 → 在 except 块中也恢复栈到 base_sp 再 re-raise

- [vm.py:917] **FOR_ITER 范围迭代使用 `<=` 包含 end（新发现严重 bug）** → Evaluator 使用半开区间 [start, end)，VM 使用闭区间 [start, end]，同一段代码在两条路径产生不同结果（如 `1..10` VM 遍历到 10，Evaluator 遍历到 9）→ 改为 `current < end`
- 追问：同一段 Nova 代码在 Evaluator 和 VM 中产生不同结果，**绝对不可接受。**

#### 中等问题（6 个）

- [vm.py:180-217] 内置函数 lambda 缺少类型检查，非序列参数抛 Python TypeError
- [vm.py:1153-1163] TRY_UNWRAP 对非 ADT 值静默通过，`42?` 不报错
- [vm.py:751-757] BREAK 在 while 循环中仍用脆弱的前向扫描 CONST_UNIT
- [vm.py:856-860] INDEX 无边界检查
- [vm.py:1129-1132] DUP 无栈空检查
- [vm.py:991-1044] MATCH_TEST_* 系列除 MATCH_CONSTRUCTOR 外无栈空检查

#### 轻微问题（7 个）

- [vm.py:509-1174] _execute_instruction 约 665 行，应按功能拆分
- [vm.py:617-621] CONCAT 强制 str() 转换过于宽松
- [vm.py:219-222] _to_float 不排除 bool
- [vm.py:70-71] NovaADTValue `__hash__` 在 VM 有但 Evaluator 无
- [vm.py:301-302] JSON dict 转换为 Python dict 而非 Nova Map
- [vm.py:240] _builtin_filter 使用 `is True` 严格比较
- [vm.py:180] read_line lambda 代码意图不清

### Evaluator vs VM 对比
| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| Unit bool | False | False | ✅ |
| PRINT 返回值 | UNIT_VALUE | UNIT | ✅ |
| STORE_VAR mutable | 检查 | 检查 | ✅ |
| ? 对 Some/Ok | 不解包返回原值 | 解包 push fields[0] | ❌ **严重** |
| for 范围 `..` 语义 | 半开 [start, end) | **闭区间 [start, end]** | ❌ **新发现** |
| ADT `__hash__` | 未定义 | 已定义 | ❌ |
| 闭包捕获 | Environment 引用 | locals dict 浅拷贝 | ❌ |
| 递归深度保护 | 无 | MAX_CALL_DEPTH = 1000 | ❌ |

### 前两轮修复状态：6/32 已修复 (19%)

---

## [2026-07-15] 编译器 (compiler.py) 第三轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | PIPE_CALL 指令、MATCH_START/END 标记对、ADT 原生指令集 |
| 可行性 | ⭐⭐⭐½ | 核心路径可用；PatternTuple/PatternList 仍空壳 |
| 正确性 | ⭐⭐⭐ | || true 路径已修复；**&& false 路径栈值丢失（新发现）** |
| 安全性 | ⭐⭐⭐ | 栈布局大部分正确 |
| 一致性 | ⭐⭐⭐ | 跳转回填全部正确 |
| 完整性 | ⭐⭐⭐⭐ | AST 所有节点有编译处理 |
| 工程质量 | ⭐⭐⭐ | 死代码保留 |
| 性能 | ⭐⭐⭐ | 闭包不做自由变量分析 |

### 发现的问题

#### 严重问题（3 个）

- [compiler.py:493-500] **`&&` 运算符 false 路径栈值丢失（新发现严重 bug）** → POP_JUMP_IF_FALSE 弹出 left 值后跳转到 end_pos，栈上无值，后续指令栈下溢 → 使用 DUP + JUMP_IF_FALSE + POP 模式（与 || 对称）
- 追问：如果 Java 的 && 在左侧为 false 时丢失返回值，**绝对不能接受。**

- [compiler.py:764-765] **PatternTuple/PatternList 模式匹配仍为空壳** → 直接返回 None 表示"总是匹配"，所有元组/列表模式变量绑定完全丢失 → 生成逐元素测试和绑定
- 追问：如果 GHC 对 tuple pattern 跳过测试代码生成，**绝对不能接受。** 连续三轮未修复。

- [compiler.py:302-345] **模块导入内联无命名空间隔离** → 同名导出后者覆盖前者无警告 → 实现限定导入

#### 中等问题（3 个）

- [compiler.py:802-866] 两个遗留死代码方法 _compile_pattern_test/_compile_pattern_bindings
- [compiler.py:932-949] while 循环返回值始终为 Unit，违反"返回最后一次迭代值"语义
- [compiler.py:395-396] CharLiteral 编译为 CONST_STRING，运行时无法区分 char 与 string

#### 轻微问题（4 个）

- [compiler.py:80 vs 631,377] CLOSURE code_key 注释与实际不一致
- [compiler.py:971-1012 vs 882-930] 列表推导式 filter 与 _compile_for 代码重复
- [compiler.py Op 类] 多个已定义但未生成的操作码
- [compiler.py:951-1012] 列表推导式不支持多 for 子句

### 前两轮修复状态：6/11 已修复 (55%)

---

## [2026-07-15] 求值器 (evaluator.py) 第三轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 两遍扫描支持相互递归 |
| 可行性 | ⭐⭐⭐½ | 核心特性可用；MapExpr 已修复 |
| 正确性 | ⭐⭐ | ? 不解包 Some/Ok、&&/|| 返回 Python bool |
| 安全性 | ⭐ | 无递归深度保护、无尾调用优化 |
| 一致性 | ⭐⭐ | 与 VM 多处行为差异 |
| 完整性 | ⭐⭐⭐⭐ | AST 覆盖完整 |
| 工程质量 | ⭐⭐½ | eval_decl 重复代码 |
| 性能 | ⭐⭐⭐ | 闭包引用语义效率可接受 |

### 发现的问题

#### 严重问题（4 个）

- [evaluator.py:698-704] **`?` 操作符不解包 Some/Ok** → `let x = some_option?` 得到 `Some(value)` 而非 `value` → 添加解包逻辑
- 追问：如果是 Rust 的 `?` 不解包 Some，**绝对不能接受。核心语义错误。** 连续三轮未修复。

- [evaluator.py:835-845] **`&&`/`||` 返回 Python bool 而非操作数值** → `1 && 2` 应返回 `2`，实际返回 `True` → 返回 falsy/truthy 值本身
- 追问：如果 OCaml 的 `&&` 返回非类型正确值，**不可接受。**

- [evaluator.py:106,401] **无递归深度保护** → 恶意或意外的无限递归导致 Python RecursionError 崩溃而非 Nova 错误 → 添加调用深度计数器

- [evaluator.py:699-707] **TryExpr `?` 在顶层表达式使用时 ReturnSignal 泄漏** → 在 eval_program 中未被 catch → 在 eval_program 中捕获 ReturnSignal

#### 中等问题（7 个）

- [evaluator.py:1004-1011] PatternString 与 PatternChar 匹配歧义（运行时都是 Python str）
- [evaluator.py:574-595] eval_decl 中 TypeDef 构造器 field_names 缺失
- [evaluator.py:203] _builtin_filter 用 `is True` 严格比较
- [evaluator.py:213-222] _builtin_head/tail 返回 Option 缺少 field_names
- [evaluator.py:271] JSON null 映射为 Option.None 语义问题
- [evaluator.py:738-748] Block 中 BreakSignal/ReturnSignal 导致 env 不恢复（缺 try-finally）
- [evaluator.py:486-491,717-722] 闭包引用语义的变量遮蔽行为未文档化

#### 轻微问题（6 个）

- [evaluator.py:379-399] _format_value 不处理 dict 类型
- [evaluator.py:864-865] ++ 未做类型检查
- [evaluator.py:331] _builtin_abs 对整数返回 float
- [evaluator.py:367-370] _builtin_min/max 强制返回 float
- [evaluator.py:554-609 vs 482-552] eval_decl 与 _collect_decl 重复代码
- [evaluator.py:297-300] JSON UNIT_VALUE 与 Python None 映射歧义

### 前两轮修复状态：3/9 已修复 (33%)

---

## [2026-07-15] 类型检查器 (type_checker.py) 第三轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| HM 推断完整性 | ⭐ | 缺少 Unification、Generalization、Instantiation 三大核心 |
| 类型安全 | ⭐⭐ | TypeVar 全兼容导致静默通过大量类型错误 |
| Pattern 检查 | ⭐⭐⭐⭐ | 全部 Pattern 类型已实现 |
| 错误恢复 | ⭐⭐⭐ | ErrorCollector 可用，部分路径仍 raise |
| 泛型支持 | ⭐⭐⭐ | ADTType.__eq__ 正确比较参数；无 occurs check |
| 递归/let 多态 | ⭐ | 完全没有 generalize/instantiate |
| Lambda TypeVar | ⭐⭐⭐⭐ | 每个参数唯一 TypeVar |
| 错误信息质量 | ⭐⭐⭐⭐ | 信息具体、有位置和上下文 |

### 发现的问题

#### 严重问题（4 个）

- [type_checker.py:1105-1125] **缺少真正的 Unification 算法（HM 核心 #1）** → 不检测 occurs check、不处理绑定冲突 → 实现 Robinson/Union-Find based unification
- 追问：如果 OCaml 的类型推断器缺少 unification，**绝对不能接受。HM 算法的核心。** 连续三轮未修复。

- [type_checker.py:544-754] **缺少 Generalize 和 Instantiate（HM 核心 #2/#3）** → let 多态完全不工作，`let id = fun x -> x in id 1 + id "a"` 不报错 → 实现 generalize/instantiate
- 追问：如果 OCaml 的 let 多态没有正确实现，**绝对不能接受。ML 系语言根基。**

- [type_checker.py:1235-1236] **任意两个 TypeVar 被视为兼容** → 任何包含 TypeVar 的类型比较静默通过 → 通过 unification 处理 TypeVar
- 追问：如果 Haskell 的 Maybe Int 和 Maybe String 被当作同一类型，**绝对不能接受。**

- [type_checker.py:986-995] **PatternConstructor 不替换类型参数** → 泛型 ADT 模式匹配不正确 → 构建类型参数映射替换

#### 中等问题（7 个）

- [type_checker.py:1105-1125] _collect_type_bindings 不处理双向/嵌套 TypeVar 绑定冲突
- [type_checker.py:436-439] AliasDef 解析时机——第一遍无法引用后定义的 ADT
- [type_checker.py:869-888] ForExpr 循环变量类型未与可迭代元素类型关联
- [type_checker.py:911] ListComprehension 同样未关联循环变量类型
- [type_checker.py:1211-1229] _expand_alias 未实际展开别名引用
- [type_checker.py:543-563] FnDef 返回类型检查不影响已注册的函数类型
- [type_checker.py:859-867] TryExpr 对非 Option/Result 静默通过

#### 轻微问题（8 个）

- [type_checker.py:169-175] TypeVar 命名不唯一——类级别全局计数器
- [type_checker.py:287] None 构造函数 TypeVar 与 Some 的 TypeVar 是不同实例
- [type_checker.py:973-997] _check_pattern 不验证 subject_type 与构造器 ADT 匹配
- [type_checker.py:720-735] PipeExpr 类型检查过于宽松
- [type_checker.py:583-928] MapExpr 未在 check_expr 中处理
- [type_checker.py:859-867] TryExpr 对非 Option/Result 类型静默通过
- [type_checker.py:1167] AliasDef 循环检测走 raise 而非 _report_error
- [type_checker.py:274] _report_error 中 raise TypeCheckError 可能被意外 catch

### 前两轮修复状态：5/12 完全修复，2/12 部分修复 (42%)

---

## [2026-07-15] 词法分析器 (lexer.py) 第三轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| Token 覆盖 | ⭐⭐⭐⭐ | 基本齐全；PIPE_VARIANT 死 Token |
| 词法错误恢复 | ⭐⭐⭐ | 非法字符仍直接 raise，无恢复 |
| 运算符优先级 | ⭐⭐⭐⭐ | |> 优先级已修复 |
| 结合性 | ⭐⭐⭐⭐⭐ | 全部左结合 |
| 歧义性 | ⭐⭐⭐ | lambda | vs ADT | 无实际冲突 |
| 左递归安全 | ⭐⭐⭐⭐⭐ | 递归下降无问题 |
| 错误位置 | ⭐⭐⭐⭐ | Token 精确；_make_error Span 起点有偏差 |
| 特性完整性 | ⭐⭐⭐ | PatternChar/parser 未连接；无科学计数法/多行字符串 |

### 严重问题（1 个）

- [lexer.py:432] **非法字符直接 raise 终止词法分析** → 改为跳过并收集到错误列表
- 追问：如果 GCC/Clang 遇到非法字符直接 crash，**绝对不能接受。**

### 中等问题（1 个）

- [lexer.py:153-158] _make_error 中 Span 起点使用了错误的 self.line/self.column 而非传入参数

### 轻微问题（6 个）

- PIPE_VARIANT 死 Token、BOOL 分支冗余、转义处理重复、无科学计数法、无十六进制、无多行注释

### 前两轮修复状态：1/5 已修复 (20%)

---

## [2026-07-15] 语法分析器 (parser.py) 第三轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 语法完整性 | ⭐⭐⭐ | match guard/Map 字面量/PatternChar 缺失 |
| 错误恢复 | ⭐⭐⭐ | 无恢复机制 |
| 优先级 | ⭐⭐⭐⭐ | |> 优先级已修复 |
| 结合性 | ⭐⭐⭐⭐⭐ | 正确 |
| 歧义性 | ⭐⭐⭐⭐ | 无左递归 |
| 错误位置 | ⭐⭐⭐⭐ | Token 精确 |

### 严重问题（3 个）

- [parser.py:530-535] **match arm 不支持 guard** → `_parse_match_arm()` 只解析 `pattern -> body`，AST 中 guard 字段永远为 None → 添加 `if` token 检查解析 guard
- 追问：match guard 是函数式语言核心特性，**不可接受。**

- [parser.py:821-822] **MapExpr 完全无法解析** → `{ "key" => value }` 走入 block 路径 → 在 _parse_primary_expr 中区分 block vs map

- [parser.py:541-621] **PatternChar 未在 parser 中处理** → `'a'` 在 match 中报 ParseError → 添加 TokenType.CHAR 分支

### 中等问题（2 个）

- [parser.py:522] match arm 分隔符判断使用硬编码 token 列表，脆弱
- [parser.py:428-431] for/while 优先级位置过低，无法使用管道

### 轻微问题（4 个）

- 无科学计数法/十六进制、无多行字符串、无块注释、variant 解析回溯可能丢错误

### 前两轮修复状态：3/10 已修复 (30%)

---

## [2026-07-15] 错误处理 + 模块 + 环境 第三轮审查报告

### 严重问题（5 个）

- [errors.py:405-411] **raise_all() 仍丢失 severity 和 span 结构化信息** → `note.format()` 仍将结构化对象序列化为字符串 → 让 add_note 接受结构化参数
- 追问：Rust 编译器每个 diagnostic 独立携带 span/severity，**不可接受。**

- [errors.py:69-76,232-261] **RelatedNote 不携带自己的 source_code** → 跨文件错误显示错误源码 → 给 RelatedNote 添加 source_code/file_path 字段
- 追问：Rust 编译器每个 diagnostic label 独立加载对应 file source。**不可接受。**

- [errors.py:334-351] **BreakSignal/ContinueSignal/ReturnSignal 不携带 span 信息** → 控制流错误无法指向源码位置 → 添加 span 参数

- [errors.py（evaluator调用处）] **evaluator RuntimeError_ 不携带 source_code 和 span** → 运行时错误退化为纯文本 → Evaluator 持有 source/current_file

- [errors.py] **ErrorCollector 未被 evaluator 使用** → 运行时只能报第一个错误 → Evaluator 添加 ErrorCollector

### 中等问题（7 个）

- [modules.py:241] evaluator 创建时未传递 current_file
- [modules.py:240] TypeChecker 创建时也未传 current_file
- [evaluator.py:611-643] _handle_import_decl 与 ModuleManager.import_module 重复实现
- [modules.py:276-299] _collect_exports 与 _collect_exported_types 完全重复
- [evaluator.py:476,642,680] 仍捕获 NameError（与 environment.py 修复不一致）
- [errors.py:86 vs 92] source vs source_code 命名不一致
- [errors.py:396-398] ErrorCollector.get_all() 丢失时序信息

### 前两轮修复状态：1/11 已修复 (9%)

---

## [2026-07-15] 后端 第三轮审查报告

### 各后端可行性评估
| 后端 | 等级 | 判断依据 |
|------|------|----------|
| c_codegen.py | C- | 唯一能生成可编译 C 代码；闭包不捕获、IfExpr 缺 else |
| native_backend.py | D+ | 架构最完整但 LIRCallIndirect/浮点 BinOp 未实现 |
| cranelift_backend.py | F | Branch 硬编码、Index 忽略参数，不可编译 |
| wasm_backend.py | F | 字符串编码 bug、BuildADT 不写数据，wat2wasm 无法通过 |
| compiler_pipeline.py | F | BACKEND_NATIVE 映射到 Cranelift 而非 NativeCodeGen |

### 严重问题（10 个）

- [compiler_pipeline.py:33-35] **BACKEND_NATIVE 映射到 CraneliftBackend** → "native" 选项实际使用 Cranelift → 添加 BACKEND_CRANELIFT 常量
- [cranelift_backend.py:162-168] **Branch 硬编码 block_true/block_false** → 所有条件分支跳到不存在的块
- [wasm_backend.py:161,371] **字符串 NUL 终止符编码错误** → `b"\\x00"` 是 4 字节字面值非 NUL
- [wasm_backend.py:273-276] **BuildADT 不存储 tag 和字段值** → 运行时读到未初始化内存
- [wasm_backend.py:260-263] **Branch 丢失 true 分支** → 只生成 br_if false，两个分支顺序执行
- [native_backend.py:496-497] **LIRCallIndirect NotImplementedError** → 闭包调用不可用
- [native_backend.py:363-427] **浮点 BinOp 全部走整数路径** → 浮点运算产生错误结果
- [c_codegen.py:897] **闭包不捕获自由变量** → `nova_closure_new(fn, NULL, 0)` 环境永远为空
- 追问：如果 OCaml 编译器生成的闭包不捕获自由变量，**绝对不能接受。**
- [c_codegen.py:584] **TryExpr variant_tag 字段名不匹配** → 编译错误：结构体无 variant_tag 成员

### 前两轮修复状态：0/10 已修复 (0%)

---

## [2026-07-15] IR 系统 第三轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 三层 IR 设计 | ⭐⭐⭐ | 分层思路正确；HIR/MIR/LIR 职责边界模糊 |
| HIR 覆盖 | ⭐⭐⭐⭐ | AST 节点覆盖全面 |
| MIR Lowering | ⭐⭐ | SSA 被破坏、match 无条件分支、闭包丢失 |
| LIR Lowering | ⭐⭐ | Phi 只取第一个 source、LIRBranch 无 cond_reg |
| 优化 Pass | ⭐⭐⭐ | LIR 层有实际实现；Inlining 空壳 |
| Pass 异常处理 | ⭐⭐⭐⭐ | 已修复：不再静默吞异常 |
| 代码可维护性 | ⭐⭐⭐ | 节点清晰但 lowering 大量重复 |
| 测试覆盖 | ⭐⭐⭐ | 40+ 测试，核心语义无测试 |

### 严重问题（7 个）

- [mir_lowering.py:351-384] **Match 无条件分支** → 所有 arm 链式 MIRJump 无条件执行 → 实现 MIRMatchJump 条件分支
- 追问：如果 Haskell 编译器的 match 总执行第一个分支，**不能接受。**

- [lir_lowering.py:204-211] **MIRPhi 只取第一个 source** → if-else merge 只保留 true 分支值 → 通过并行拷贝实现 phi
- 追问：phi 节点丢弃 false 分支导致 `if true then 1 else 2` 总返回 1，**不可接受。**

- [lir_lowering.py:219-223] **LIRBranch.cond_reg 未设置** → 后端无法生成条件跳转代码 → 设置 cond_reg/true_label/false_label

- [lir_lowering.py:231-241] **MIRSwitch/MIRMatchJump 退化为无条件跳转** → 丢弃所有 case 分支

- [mir_lowering.py:275-283] **SSA 被赋值语句破坏** → 局部可变变量 store/load 路径不一致

- [mir_lowering.py:396-417] **For 循环无迭代器变量，无 phi 节点** → 循环变量未绑定，循环只执行一次

- [mir_lowering.py:247-250] **闭包捕获列表始终为空** → 闭包自由变量全部丢失

### Pass 实现状态表
| Pass | HIR | MIR | LIR |
|------|-----|-----|-----|
| ConstantFolding | ✅ | ✅ | ✅ |
| Inlining | ❌ 空壳 | ❌ | ❌ |
| DeadCodeElimination | ❌ | ❌ | ✅ |
| CSE | ❌ | ✅ | ✅ |
| LICM | ❌ | ✅(简化) | ✅ |

### 前两轮修复状态：3/10 已修复 (30%)

---

## [2026-07-15] C 运行时 + 测试 + Tree-sitter 第三轮审查报告

### C 运行时严重问题（7 个）

- [nova_runtime.c:1645,1693] **HTTP 命令注入未修复** → URL 含 `"` 可注入任意 shell 命令 → 替换为 libcurl C API
- 追问：**安全漏洞，可远程利用。不可接受。**

- [nova_runtime.c:99-103] **GC 仍为空壳** → 无循环引用回收 → 实现标记-清除 GC

- [nova_runtime.c:290] **nova_string_replace 整数溢出** → 乘法溢出导致缓冲区分配过小，memcpy 越界 → 添加溢出检查

- [nova_runtime.c:523-526] **nova_map_put 不释放旧 value** → 每次覆盖泄漏旧值 → 覆盖前 release 旧值

- [nova_runtime.c:748-761] **nova_closure_new 浅拷贝不 retain** → 捕获对象 release 后闭包持悬垂指针 → 添加 retain

- [nova_runtime.c:1226-1241] **JSON unicode 不处理 surrogate pairs** → emoji 等字符产生无效 UTF-8 → 检测高/低代理项组合

- [nova_runtime.c:1177-1273] **JSON 解析无错误报告机制** → 非法 JSON 返回 NULL 无错误信息 → 添加错误码

### 测试覆盖统计（总计 655 个测试）

| 测试文件 | 测试数 |
|----------|--------|
| test_nova.py | 286（Evaluator ~130, VM 79）|
| test_backends.py | 43 |
| test_c_codegen.py | 52 |
| test_native_backend.py | 87 |
| test_errors.py | 30 |
| test_type_system.py | 39 |
| test_ir.py | 90 |
| test_modules.py | 28 |

### 测试覆盖缺口

| 缺失测试 | 影响 |
|----------|------|
| Evaluator-VM 一致性测试 | 两执行路径语义漂移无发现手段 |
| 后端端到端运行验证 | 后端代码生成正确性无验证 |
| Map 字面量 | 两个后端都缺 |
| try 表达式 | 两个后端都缺 |
| match guard | 两个后端都缺 |
| char 类型操作 | 无任何 char 运行时测试 |
| 泛型 ADT 求值 | 类型检查有测试但运行时无 |
| VM 模块导入 | VM 不测试模块系统 |

### Tree-sitter

- [grammar.js] **TryExpr 仍未添加** → IDE 无法高亮/解析 try 表达式
- [grammar.js] **缺少泛型类型参数** → `Option[T]` 无法被 Tree-sitter 解析
- [grammar.js] 缺少 PatternChar 完整支持

### 前两轮修复状态：0/10 已修复 (0%)

---

## 第三轮全局问题汇总

### 按严重程度统计

| 严重程度 | 第一轮 | 第二轮 | 第三轮 | 总计 |
|---------|--------|--------|--------|------|
| 严重 | 52 | 47 | 63 | **162** |
| 中等 | 42 | 47 | 55 | **144** |
| 轻微 | 36 | 49 | 62 | **147** |
| **总计** | **130** | **143** | **180** | **453** |

### 第三轮最高优先级修复项（Top 20）

1. **VM: FOR_ITER 闭区间 vs Evaluator 半开区间** [vm.py:917] — **新发现**，同源代码两路径结果不同
2. **求值器: ? 不解包 Some/Ok** [evaluator.py:698-704] — 核心语义错误，三轮未修
3. **编译器: && false 路径栈值丢失** [compiler.py:493-500] — **新发现**，栈下溢
4. **编译器: PatternTuple/PatternList 空壳** [compiler.py:764-765] — 三轮未修
5. **类型检查器: HM 核心缺失** [type_checker.py] — Unification/Generalize/Instantiate 三轮未修
6. **IR: Match 无条件分支** [mir_lowering.py:351-384] — 三轮未修
7. **IR: Phi 只取第一个 source** [lir_lowering.py:204-211] — 三轮未修
8. **IR: LIRBranch.cond_reg 未设置** [lir_lowering.py:219-223] — 三轮未修
9. **VM: 闭包捕获整个帧** [vm.py:786-787] — 三轮未修
10. **VM: CONTINUE while 启发式** [vm.py:682-687] — 三轮未修
11. **C 运行时: HTTP 命令注入** [nova_runtime.c:1645] — 安全漏洞，三轮未修
12. **C 运行时: GC 空壳** [nova_runtime.c:99-103] — 三轮未修
13. **C 运行时: 整数溢出** [nova_runtime.c:290] — **新发现**
14. **C 后端: 闭包不捕获** [c_codegen.py:897] — 三轮未修
15. **所有后端: 10 项严重问题零修复** [backend/] — 修复率 0%
16. **求值器: &&/|| 返回 bool** [evaluator.py:835-845] — 三轮未修
17. **求值器: 无递归深度保护** [evaluator.py:106] — 三轮未修
18. **错误处理: raise_all 丢失结构化信息** [errors.py:405-411] — 三轮未修
19. **parser: match arm 无 guard** [parser.py:530-535] — 三轮未修
20. **测试: 无 Evaluator-VM 一致性测试** [tests/] — 三轮未修

### 三轮修复率趋势

| 轮次 | 严重 | 中等 | 轻微 | 总发现 | 总已修复 | 修复率 |
|------|------|------|------|--------|---------|--------|
| 第一轮 | 52 | 42 | 36 | 130 | 0 | 0% |
| 第二轮 | 47 | 47 | 49 | 143 | 25 | 17% |
| 第三轮 | 63 | 55 | 62 | 180 | ~35 | ~19% |
| **累计** | **162** | **144** | **147** | **453** | **~60** | **~13%** |

### 关键趋势分析

1. **新发现问题速率未下降**：第三轮新发现 180 个问题，与第二轮 143 个相比反而增加，说明深度审查持续发现新问题
2. **核心模块修复率停滞**：VM/编译器/求值器修复率在 19%-55% 之间，类型检查器 42%，但后端/运行时修复率 0%
3. **跨模块一致性问题加剧**：第三轮新发现 VM 与 Evaluator 的 for 范围语义不一致、编译器 && 栈值丢失等问题

---

## [2026-07-15] 第四轮全局审查报告

> **审查时间**：2026-07-15（第四轮）
> **审查版本**：main 分支最新提交
> **审查方法**：三轮九个 Explore Agent 并行审查，生产级编译器标准

### 项目结构审查表（第四轮更新）

| 模块 | 文件 | 审查状态 | 上次审查 | 严重 | 中等 | 轻微 | 累计严重 | 累计中等 | 累计轻微 |
|------|------|---------|---------|------|------|------|---------|---------|---------|
| VM 虚拟机 | `vm.py` | ✅ 已审查 | 2026-07-15 | 2 | 4 | 7 | 7 | 10 | 14 |
| 编译器 | `compiler.py` | ✅ 已审查 | 2026-07-15 | 2 | 3 | 4 | 5 | 7 | 8 |
| 求值器 | `evaluator.py` | ✅ 已审查 | 2026-07-15 | 3 | 5 | 6 | 7 | 12 | 10 |
| 类型检查器 | `type_checker.py` | ✅ 已审查 | 2026-07-15 | 7 | 8 | 7 | 11 | 15 | 13 |
| 词法分析器 | `lexer.py` | ✅ 已审查 | 2026-07-15 | 1 | 2 | 6 | 2 | 3 | 12 |
| 语法分析器 | `parser.py` | ✅ 已审查 | 2026-07-15 | 3 | 2 | 4 | 6 | 4 | 8 |
| 错误处理 | `errors.py` | ✅ 已审查 | 2026-07-15 | 3 | 3 | 2 | 8 | 10 | 7 |
| 模块系统 | `modules.py` | ✅ 已审查 | 2026-07-15 | 0 | 4 | 2 | 0 | 7 | 4 |
| 环境 | `environment.py` | ✅ 已审查 | 2026-07-15 | 0 | 0 | 0 | 0 | 0 | 0 |
| C 代码生成 | `c_codegen.py` | ✅ 已审查 | 2026-07-15 | 3 | 1 | 2 | 6 | 2 | 4 |
| Native 后端 | `backend/native_backend.py` | ✅ 已审查 | 2026-07-15 | 3 | 1 | 2 | 6 | 3 | 2 |
| Cranelift 后端 | `backend/cranelift_backend.py` | ✅ 已审查 | 2026-07-15 | 5 | 2 | 1 | 10 | 3 | 2 |
| WASM 后端 | `backend/wasm_backend.py` | ✅ 已审查 | 2026-07-15 | 5 | 2 | 1 | 10 | 3 | 1 |
| x86_64 指令 | `backend/x86_64.py` | ✅ 已审查 | 2026-07-15 | 1 | 0 | 1 | 1 | 0 | 3 |
| 编译管道 | `backend/compiler_pipeline.py` | ✅ 已审查 | 2026-07-15 | 1 | 0 | 0 | 2 | 0 | 0 |
| IR 节点 | `ir/ir_nodes.py` | ✅ 已审查 | 2026-07-15 | 0 | 0 | 2 | 0 | 0 | 4 |
| HIR Lowering | `ir/hir_lowering.py` | ✅ 已审查 | 2026-07-15 | 0 | 4 | 3 | 0 | 6 | 6 |
| MIR Lowering | `ir/mir_lowering.py` | ✅ 已审查 | 2026-07-15 | 3 | 1 | 0 | 8 | 2 | 0 |
| LIR Lowering | `ir/lir_lowering.py` | ✅ 已审查 | 2026-07-15 | 3 | 0 | 1 | 6 | 2 | 1 |
| Pass 管理器 | `ir/pass_manager.py` | ✅ 已审查 | 2026-07-15 | 1 | 4 | 2 | 2 | 6 | 4 |
| C 运行时 | `runtime/nova_runtime.c` | ✅ 已审查 | 2026-07-15 | 6 | 5 | 4 | 13 | 11 | 6 |
| 测试套件 | `tests/` | ✅ 已审查 | 2026-07-15 | 3 | 0 | 0 | 6 | 0 | 0 |
| Tree-sitter | `tree-sitter-nova/` | ✅ 已审查 | 2026-07-15 | 1 | 1 | 0 | 2 | 1 | 0 |

---

## [2026-07-15] VM 虚拟机 (vm.py) 第四轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | PIPE_CALL/MATCH_START-END/TRY_UNWRAP 设计有特色 |
| 可行性 | ⭐⭐⭐ | 核心路径可用；FOR_ITER 范围已与 Evaluator 一致 |
| 正确性 | ⭐⭐ | BUILD_MAP 单元素崩溃（新发现严重 bug）、闭包过度捕获 |
| 安全性 | ⭐⭐⭐ | _pop 有保护；EQ bool/int 交叉相等（新发现） |
| 一致性 | ⭐⭐⭐ | 部分差异已修复；Err JSON 处理不一致（新发现） |
| 完整性 | ⭐⭐⭐⭐⭐ | Op 类指令覆盖完整 |
| 工程质量 | ⭐⭐ | _execute_instruction 仍过长 |
| 性能 | ⭐⭐ | 闭包捕获整个帧 dict 浅拷贝未改善 |

### 前三轮问题修复状态

| 问题 | 状态 |
|------|------|
| 闭包捕获整个帧 | ❌ 四轮未修 |
| CONTINUE while 启发式 | ❌ 四轮未修 |
| _pop 类型不一致 | ❌ 四轮未修（根因导致 BUILD_MAP 崩溃） |
| _call_closure 异常安全 | ✅ 已修复 |
| FOR_ITER 范围迭代 | ✅ 已修复（与 Evaluator 一致） |
| 内置函数类型检查 | ❌ 四轮未修 |
| BREAK while 前向扫描 | ❌ 四轮未修 |
| INDEX 无边界检查 | ❌ 四轮未修 |
| DUP/MATCH_TEST_* 无栈空检查 | ❌ 四轮未修 |

### 发现的问题

#### 严重问题（2 个）

- [vm.py:842-854] **BUILD_MAP 对单元素 map 会 IndexError（新发现严重 bug）** → `_pop(2)` 返回列表，`count==1` 守卫再包一层，`pairs[1]` 越界 → 移除 `if count == 1` 守卫
- 追问：最基本的字面量语法 `{ "a": 1 }` 都无法工作。如果 GHC 的 map 字面量语法崩溃，**绝对不能接受。**
- [vm.py:785-788] **闭包仍捕获整个帧 locals** → O(n) 浅拷贝，阻止 GC，语义不等价 → 编译器分析自由变量
- 追问：如果 OCaml 闭包捕获整个作用域，**绝对不能接受。** 四轮未修。

#### 中等问题（4 个）

- [vm.py:751-757] BREAK while 前向扫描（嵌套循环错误）
- [vm.py:683-686] CONTINUE while 启发式检测
- [vm.py:623-627] EQ 对 bool 与 int 交叉比较返回 True（新发现）
- [vm.py:312-330] Err JSON 序列化与 evaluator 不一致（新发现）

#### 轻微问题（7 个）

- INDEX 无边界检查、内置函数无类型检查、DUP 无栈空检查
- MATCH_TEST_* 无栈空检查、DIV float 除零、MOD 除零、NovaADTValue.__hash__ 可变字段
- CONCAT 强制 str()、FOR_ITER step==0 不报错

### Evaluator vs VM 对比（新增项）
| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| BUILD_MAP | 无此指令 | **单元素崩溃** | ❌ **新发现** |
| EQ bool/int | 同（Python ==） | 同 | ❌ 两者都错 |
| Err JSON | 返回 null | 返回结构化对象 | ❌ **新发现** |
| for 范围 `..` | 闭区间 [start, end] | 闭区间 [start, end] | ✅ **已修复一致** |

---

## [2026-07-15] 编译器 (compiler.py) 第四轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | PIPE_CALL 指令、MATCH_START/END、ADT 原生指令集 |
| 可行性 | ⭐⭐⭐½ | 核心路径可用；&& 栈值已修复 |
| 正确性 | ⭐⭐½ | PatternTuple/PatternList 空壳、while+continue 崩溃（新发现） |
| 安全性 | ⭐⭐⭐ | 栈布局大部分正确 |
| 一致性 | ⭐⭐⭐ | 跳转回填全部正确 |
| 完整性 | ⭐⭐⭐⭐ | AST 所有节点有编译处理 |
| 工程质量 | ⭐⭐½ | 遗留死代码 |
| 性能 | ⭐⭐⭐ | 闭包不做自由变量分析 |

### 严重问题（2 个）

- [compiler.py:767-768,800-801] **PatternTuple/PatternList 模式匹配仍为空壳** → 返回 None 表示"总是匹配"，解构绑定完全失败 → 生成逐元素测试指令
- 追问：如果 GHC 对 tuple pattern 跳过测试代码生成，**绝对不能接受。** 四轮未修。
- [compiler.py:935-952] **while 循环嵌套复杂结构时 continue 导致 VM ip=None 崩溃（新发现）** → `_while_loops["loop_start"]` 保持 None → 编译器为 while 生成显式循环元数据指令

### 中等问题（3 个）

- [compiler.py:302-345] 模块导入内联无命名空间隔离（四轮未修）
- [compiler.py:613-634] 闭包不做自由变量分析（四轮未修）
- [compiler.py:396] CharLiteral 编译为 CONST_STRING（四轮未修）

### 前三轮问题修复状态

| 问题 | 状态 |
|------|------|
| && false 路径栈值丢失 | ✅ 已修复 |
| PatternTuple/PatternList 空壳 | ❌ 四轮未修 |
| 模块导入无命名空间 | ❌ 四轮未修 |
| Block BreakExpr 后多余 POP | ✅ 已修复 |
| 死代码方法 | ❌ 四轮未修 |
| while 返回值恒 Unit | ❌ 四轮未修 |
| CharLiteral → CONST_STRING | ❌ 四轮未修 |
| 闭包自由变量 | ❌ 四轮未修 |

---

## [2026-07-15] 求值器 (evaluator.py) 第四轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 两遍扫描支持相互递归 |
| 可行性 | ⭐⭐⭐½ | 核心特性可用；? 解包、&&/|| 已修复 |
| 正确性 | ⭐⭐½ | Block env 泄漏（新发现）、无递归深度保护 |
| 安全性 | ⭐⭐ | 无递归深度保护、无尾调用优化 |
| 一致性 | ⭐⭐½ | ? 已修复；filter/head/tail 仍不一致 |
| 完整性 | ⭐⭐⭐⭐ | AST 覆盖完整（FnDef 表达式缺失） |
| 工程质量 | ⭐⭐ | eval_decl 死代码 |
| 性能 | ⭐⭐⭐ | 闭包引用语义效率可接受 |

### 严重问题（3 个）

- [evaluator.py:738-748] **Block 中 ReturnSignal/BreakSignal 导致 env 不恢复（新发现严重 bug）** → Block 无 try/finally，信号传播时 self.env 泄漏 → 添加 try/finally 保护
- 追问：如果 OCaml 的 let-in 表达式因异常跳过环境恢复，**不能接受。**
- [evaluator.py:470-471] **顶层 ? 导致 ReturnSignal 未捕获（新发现）** → `_eval_decl_body` 无 except ReturnSignal → 在 eval_program 中捕获
- [evaluator.py:106] **无递归深度保护** → VM 有 MAX_CALL_DEPTH=1000，evaluator 完全没有 → 添加深度计数器
- 追问：如果 GHC 无递归深度保护导致 Python RecursionError，**不能接受。**

### 中等问题（5 个）

- [evaluator.py:203] _builtin_filter 用 `is True` 严格比较（四轮未修）
- [evaluator.py:215,222] _builtin_head/tail 返回 Option 缺少 field_names（四轮未修）
- [evaluator.py:860] 整数除法使用 Python `//`（地板除法 vs 截断除法）（新发现）
- [evaluator.py:868] `!=` 对不同 ADT 同名变体返回 False（__eq__ 不检查 type_name）（新发现）
- [evaluator.py:864-865] `++` 不做类型检查（新发现）

### 前三轮问题修复状态

| 问题 | 状态 |
|------|------|
| ? 不解包 Some/Ok | ✅ 已修复 |
| &&/\|\| 返回 Python bool | ✅ 已修复 |
| 无递归深度保护 | ❌ 四轮未修 |
| TryExpr 顶层 ReturnSignal 泄漏 | ❌ 四轮未修（本轮新确认） |
| PatternString/PatternChar 歧义 | ✅ 已修复 |
| TypeDef 构造器 field_names | ✅ eval_decl 是死代码，不影响 |
| filter is True | ❌ 四轮未修 |
| head/tail field_names | ❌ 四轮未修 |
| Block env 不恢复 | ❌ 四轮未修（本轮新确认） |

---

## [2026-07-15] 类型检查器 (type_checker.py) 第四轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| HM 推断完整性 | ⭐ | 缺少 Unification、Generalization、Instantiation 三大核心（四轮未修） |
| 类型安全 | ⭐⭐ | TypeVar 全兼容导致静默通过大量类型错误（四轮未修） |
| Pattern 检查 | ⭐⭐⭐⭐ | 全部 Pattern 类型已实现 |
| 错误恢复 | ⭐⭐⭐ | ErrorCollector 可用 |
| 泛型支持 | ⭐⭐⭐ | ADTType.__eq__ 正确比较参数 |
| 递归/let 多态 | ⭐ | 完全没有 generalize/instantiate（四轮未修） |
| Lambda TypeVar | ⭐⭐⭐⭐ | 每个参数唯一 TypeVar |

### 严重问题（7 个，四轮全部未修复）

- [type_checker.py 全局] **缺少 Unification 算法** — HM 核心，四轮未修
- 追问：如果 OCaml 的类型推断器缺少 unification，**绝对不能接受。**
- [type_checker.py 全局] **缺少 Generalize/Instantiate** — let 多态不存在，四轮未修
- 追问：如果 OCaml 的 let 多态没有正确实现，**绝对不能接受。**
- [type_checker.py:1235-1236] **任意两个 TypeVar 兼容** — 四轮未修
- [type_checker.py:996-997] **PatternConstructor 不替换类型参数** — 四轮未修
- [type_checker.py:883] **ForExpr 循环变量类型未关联** — 四轮未修
- [type_checker.py:911] **ListComprehension 迭代变量类型未关联** — 四轮未修
- [type_checker.py:712-715] **FnCall 对 TypeVar callee duck typing（新发现）** — 任何未标注标识符可被当任意函数调用

### 新发现问题

- [type_checker.py:1047-1052] `==`/`!=` 完全不检查操作数类型（中等）
- [type_checker.py:641-646] IfExpr 分支不一致仍返回 then_ty 而非 ERROR_TYPE（中等）
- [type_checker.py:926-928] MapExpr 类型检查完全缺失（中等）

### 前三轮修复率：**0/15（0%）**

---

## [2026-07-15] 词法分析器 (lexer.py) 第四轮审查报告

### 严重问题（1 个）

- [lexer.py:432] **非法字符直接 raise 终止词法分析** — 四轮未修
- 追问：如果 GCC/Clang 遇到非法字符直接 crash，**绝对不能接受。**

### 中等问题（2 个）

- [lexer.py:153-158] _make_error Span 语义不清 — 四轮未修
- [lexer.py:248-249] 未知转义静默接受为字面量（新发现）

### 已修复

- parser match arm guard ✅（本轮验证确认）
- parser for/while 优先级 ✅（本轮验证确认）

### 新发现

- [lexer.py:306-309] BOOL 分支冗余（低）
- [lexer.py] 缺少十六进制/Unicode 转义、多行注释 — 四轮未修

---

## [2026-07-15] 语法分析器 (parser.py) 第四轮审查报告

### 严重问题（3 个）

- [parser.py:464-466] **`<-` 用 LT+MINUS 拼接导致歧义（新发现严重 bug）** → `for i < -1..10` 被错误解析为 range for → 词法分析器添加 `<-` token
- 追问：如果 OCaml 的 `<-` 被两个 token 拼接导致歧义，**不能接受。**
- [parser.py] **MapExpr 完全无法解析** — 四轮未修
- [parser.py:432-439,667-673] **`|>` 优先级在比较运算符之上** — 四轮未修

### 中等问题（2 个）

- [parser.py:541-621] PatternChar 未处理 — 四轮未修
- [parser.py:334-346] `Fn[T]->R` 类型解析冲突（新发现）

### 新发现

- [parser.py:335-346] `Fn[Int] -> String` 被错误解析为 `(Fn[Int] -> Unit) -> String`（中等）

### 前三轮修复率：**2/11（18%）**

---

## [2026-07-15] 错误处理 + 模块 + 环境 第四轮审查报告

### 严重问题（3 个，全部未修复）

- [errors.py:405-411] **raise_all() 丢失 severity/span 结构化信息** — 四轮未修
- 追问：Rust 编译器每个 diagnostic 独立携带 span/severity，**不可接受。**
- [errors.py:68-76] **RelatedNote 不携带 source_code** — 跨文件诊断完全错误
- [errors.py（evaluator）] **evaluator RuntimeError_ 不携带 source_code/span** — 所有运行时错误无源码上下文

### 中等问题（7 个）

- [errors.py:334-352] BreakSignal/ContinueSignal/ReturnSignal 不携带 span — 四轮未修
- [errors.py:396-398] ErrorCollector.get_all() 丢失时序信息（新发现）
- [modules.py:241] evaluator 创建时未传递 current_file
- [modules.py:276-299] _collect_exports 死代码、_collect_exported_types type_checker 参数未使用
- [modules.py:245] exported_types 变量被计算但从未使用
- [evaluator.py] ErrorCollector 未被 evaluator 使用 — 四轮未修

### 已修复

- environment.py lookup/lookup_binding NameError → RuntimeError_ ✅

---

## [2026-07-15] 后端 第四轮审查报告

### 各后端可行性评估
| 后端 | 等级 | 判断依据 |
|------|------|----------|
| c_codegen.py | C- | 闭包不捕获、variant_tag 不匹配、IfExpr 无 else |
| native_backend.py | D+ | LIRCallIndirect 未实现、浮点走整数路径、LIRReturn 跳过尾声 |
| cranelift_backend.py | F | Branch 硬编码、Index 忽略参数、浮点未区分 |
| wasm_backend.py | F | NUL 编码错误、BuildADT 不写数据、Branch 丢 true |
| compiler_pipeline.py | F | BACKEND_NATIVE 映射到 Cranelift |

### 严重问题（11 个，全部未修复）

- [compiler_pipeline.py:33-35] BACKEND_NATIVE 映射到 Cranelift 而非 NativeCodeGen
- [cranelift_backend.py:162-168] Branch 硬编码 block_true/block_false
- [wasm_backend.py:161,371] 字符串 NUL 终止符编码错误
- [wasm_backend.py:273-276] BuildADT 不存储 tag 和字段值
- [wasm_backend.py:260-263] Branch 丢失 true 分支
- [native_backend.py:496-497] LIRCallIndirect NotImplementedError
- [native_backend.py:352-427] 浮点 BinOp 全部走整数路径
- [c_codegen.py:897] 闭包不捕获自由变量
- [c_codegen.py:584] TryExpr variant_tag 字段名不匹配
- [c_codegen.py:615-623] IfExpr 无 else 返回 "0"
- [x86_64.py:451,467] je_rel32 方法定义重复（新发现）

### 新发现

- [cranelift_backend.py:216-238] _emit_binop 不区分浮点/整数（严重）
- [native_backend.py] LIRReturn 直接 ret 跳过 callee-saved 恢复（严重）
- [native_backend.py:336] vreg 分配使用值作为键，相同常量共享寄存器（中等）
- [wasm_backend.py] _scan_strings 与 _emit_string_data 偏移计算不一致（中等）

### 前三轮修复率：**0/11（0%）**

---

## [2026-07-15] IR 系统 第四轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 三层 IR 设计 | ⭐⭐⭐⭐ | HIR→MIR→LIR 分层思路正确 |
| HIR 覆盖 | ⭐⭐⭐⭐ | 节点覆盖全面 |
| MIR Lowering | ⭐⭐ | Match/For/闭包致命缺陷（四轮未修） |
| LIR Lowering | ⭐⭐ | Phi/Branch/Switch/Call 全部有严重缺陷 |
| 优化 Pass | ⭐⭐⭐ | LIR 层有实际实现；Inlining 空壳 |
| Pass 异常处理 | ⭐⭐⭐⭐ | 已修复：不再静默吞异常 |

### 严重问题（9 个）

- [mir_lowering.py:351-384] Match 退化为无条件跳转链 — 四轮未修
- [mir_lowering.py:396-417] For 循环无迭代器变量 — 四轮未修
- [mir_lowering.py:247-250] 闭包捕获完全丢失 — 四轮未修
- [lir_lowering.py:204-211] MIRPhi 只取第一个 source — 四轮未修
- [lir_lowering.py:219-223] LIRBranch cond_reg/true_label/false_label 未设置 — 四轮未修
- [lir_lowering.py:231-241] MIRSwitch/MIRMatchJump 退化为无条件跳转 — 四轮未修
- [lir_lowering.py:171-176] **MIRMapBuild 降级为 LIRBuildList（新发现严重 bug）**
- [lir_lowering.py:141-147] **LIRCall 缺少参数寄存器信息（新发现严重 bug）**
- [lir_lowering.py:228] **LIRReturn 类型硬编码 UNIT_TYPE（新发现严重 bug）**

### 新发现

- [hir_lowering.py:190-193] PipeExpr 嵌套管道未展平（中等）
- [hir_lowering.py:280-288] LetBinding/MutBinding 放入 BlockExpr 违反类型约束（中等）
- [hir_lowering.py:149-150] range 迭代返回伪标识符 `_range`（中等）
- [pass_manager.py:105-108] 常量折叠通过修改 `__class__` 变更节点类型（中等）
- [pass_manager.py:652-656] MIR LICM 只分析 header 块（中等）
- [pass_manager.py:631-641] MIR LICM 回边检测无拓扑序验证（中等）
- [pass_manager.py:685-691] MIR LICM 外提只插入第一个前驱（中等）

### Pass 实现状态表
| Pass | HIR | MIR | LIR |
|------|-----|-----|-----|
| ConstantFolding | ⚠️（猴子补丁） | ✅ | ✅ |
| Inlining | ❌ 空壳 | ❌ | ❌ |
| DeadCodeElimination | ❌ | ❌ | ✅ |
| CSE | ❌ | ✅ | ✅ |
| LICM | ❌ | ⚠️（header only） | ✅ |

### 前三轮修复率：**1/9（11%）**

---

## [2026-07-15] C 运行时 + 测试 + Tree-sitter 第四轮审查报告

### C 运行时严重问题（6 个）

- [nova_runtime.c:1645,1693] **HTTP 命令注入未修复** — 安全漏洞，四轮未修
- 追问：**安全漏洞，可远程利用。不可接受。**
- [nova_runtime.c:290] **字符串替换整数溢出→堆溢出** — 四轮未修
- [nova_runtime.c:753-756] **闭包浅拷贝不 retain→悬空指针** — 四轮未修
- [nova_runtime.c:99-103] **GC 仍为空壳** — 四轮未修
- [nova_runtime.c:370-387] **list_concat/slice 浅拷贝不 retain（新发现严重 bug）**
- [nova_runtime.c:479-486] **list_release 不释放元素（新发现严重 bug）**
- [nova_runtime.c:735-742] **adt_release 不递减字段引用（新发现严重 bug）**
- [nova_runtime.c:777-784] **closure_release 不释放捕获变量（新发现严重 bug）**

### 测试覆盖统计

| 测试文件 | 测试数 |
|----------|--------|
| test_nova.py | ~130+ |
| test_backends.py | 28 |
| test_c_codegen.py | 26 |
| test_ir.py | 37 |
| test_modules.py | 18 |
| test_type_system.py | 25 |
| test_errors.py | 17 |
| test_native_backend.py | ~40+ |
| **总计** | **~320+** |

### 零测试特性（仍然）
- try 表达式运行时语义
- Map 数据结构操作
- Evaluator vs VM 结果一致性
- 后端编译后实际执行验证
- Char 类型操作
- HTTP/网络操作

### Tree-sitter

- [grammar.js] **TryExpr 仍未添加** — IDE 无法解析 try 表达式
- [grammar.js] **缺少泛型类型参数** — `Option[T]` 无法解析
- [grammar.js] float_literal 正则不匹配 `.5`、`1.`、科学计数法（新发现）

### 前三轮修复率：**0/10（0%）**

---

## 第四轮全局问题汇总

### 按严重程度统计

| 严重程度 | 第一轮 | 第二轮 | 第三轮 | 第四轮 | 总计 |
|---------|--------|--------|--------|--------|------|
| 严重 | 52 | 47 | 63 | 47 | **209** |
| 中等 | 42 | 47 | 55 | 50 | **194** |
| 轻微 | 36 | 49 | 62 | 46 | **193** |
| **总计** | **130** | **143** | **180** | **143** | **596** |

### 第四轮最高优先级修复项（Top 20）

1. **VM: BUILD_MAP 单元素 IndexError** [vm.py:842-854] — **新发现**，最基本语法崩溃
2. **求值器: Block env 不恢复** [evaluator.py:738-748] — **新发现**，信号导致环境泄漏
3. **求值器: 顶层 ? ReturnSignal 未捕获** [evaluator.py:470-471] — **新发现**
4. **编译器: while+continue 崩溃** [compiler.py:935-952] — **新发现**
5. **parser: `<-` 歧义** [parser.py:464-466] — **新发现**，`for i < -1..10` 被错误解析
6. **求值器: 无递归深度保护** [evaluator.py:106] — 四轮未修
7. **VM: 闭包捕获整个帧** [vm.py:785-788] — 四轮未修
8. **编译器: PatternTuple/PatternList 空壳** [compiler.py:767-768] — 四轮未修
9. **类型检查器: HM 核心缺失** [type_checker.py] — 四轮未修
10. **类型检查器: 任意 TypeVar 兼容** [type_checker.py:1235-1236] — 四轮未修
11. **IR: Match/For/闭包致命缺陷** [mir_lowering.py] — 四轮未修
12. **IR: LIR 层 Phi/Branch/Switch/Call 全部有严重 bug** [lir_lowering.py] — 含 3 个新发现
13. **C 运行时: HTTP 命令注入** [nova_runtime.c:1645] — 安全漏洞，四轮未修
14. **C 运行时: 引用计数 release 不递减子对象** [nova_runtime.c] — 含 4 个新发现
15. **所有后端: 11 项严重问题零修复** [backend/] — 修复率 0%
16. **lexer: 非法字符终止词法分析** [lexer.py:432] — 四轮未修
17. **错误处理: raise_all 丢失结构化信息** [errors.py:405-411] — 四轮未修
18. **C 运行时: 字符串替换溢出→堆溢出** [nova_runtime.c:290] — 四轮未修
19. **lir_lowering: MIRMapBuild 降级为 LIRBuildList** [lir_lowering.py:171-176] — 新发现
20. **测试: 无 Evaluator-VM 一致性测试** [tests/] — 四轮未修

### 四轮修复率趋势

| 轮次 | 严重 | 中等 | 轻微 | 总发现 | 总已修复 | 修复率 |
|------|------|------|------|--------|---------|--------|
| 第一轮 | 52 | 42 | 36 | 130 | 0 | 0% |
| 第二轮 | 47 | 47 | 49 | 143 | 25 | 17% |
| 第三轮 | 63 | 55 | 62 | 180 | ~35 | ~19% |
| 第四轮 | 47 | 50 | 46 | 143 | ~10 | ~7% |
| **累计** | **209** | **194** | **193** | **596** | **~70** | **~12%** |

### 关键趋势分析

1. **修复率严重下降**：第四轮修复率从 ~19% 降至 ~7%，表明项目修复动力不足，或复杂问题难以修复
2. **新发现严重 bug**：VM BUILD_MAP 崩溃、求值器 Block env 泄漏、parser `<-` 歧义——这些是用户可触发的崩溃
3. **类型检查器零修复**：15 个问题 0 个修复，HM 核心缺失是类型系统名存实亡的根本原因
4. **后端零修复**：11 个严重问题 0 个修复，所有非 C 后端完全不可用
5. **C 运行时安全漏洞持续**：HTTP 命令注入 + 堆溢出两个安全漏洞四轮未修
6. **跨模块一致性恶化**：新增 Err JSON、EQ bool/int、整除法等多处 Evaluator-VM 语义差异
4. **安全漏洞持续存在**：HTTP 命令注入、整数溢出两个安全相关 bug 三轮未修

---

## 第五轮全局问题汇总

### 按严重程度统计

| 严重程度 | 第五轮新增 | 第五轮已修复 | 第五轮未修复 | 累计 |
|---------|-----------|------------|------------|------|
| 严重 | 28 | 14 | 195 | **209 + 28 = 237** |
| 中等 | 38 | 18 | 176 | **194 + 38 = 232** |
| 轻微 | 28 | 20 | 173 | **193 + 28 = 221** |
| **总计** | **94** | **52** | **544** | **690** |

### 第五轮修复情况

本轮验证了前四轮发现的所有问题，修复情况如下：

| 模块 | 历史问题总数 | 本轮确认已修复 | 未修复 | 修复率 |
|------|------------|-------------|--------|--------|
| VM 虚拟机 (vm.py) | 11 | 6 (含1部分修复) | 4 | 55% |
| 编译器 (compiler.py) | 12 | 6 (含1部分修复) | 4 | 50% |
| 求值器 (evaluator.py) | 10 | 6 | 4 | 60% |
| 类型检查器 (type_checker.py) | 15 | 8 (含4部分修复) | 2 | 53% |
| 词法分析器 (lexer.py) | 5 | 2 | 3 | 40% |
| 语法分析器 (parser.py) | 6 | 3 (含1部分修复) | 3 | 58% |
| 错误处理 (errors.py) | 5 | 3 | 1 | 60% |
| 模块系统 (modules.py) | 3 | 2 | 1 | 67% |
| 环境 (environment.py) | 2 | 2 | 0 | 100% |
| C 代码生成 (c_codegen.py) | 2 | 0 | 2 | 0% |
| Native 后端 | 2 | 0 | 2 | 0% |
| Cranelift 后端 | 3 | 0 | 3 | 0% |
| WASM 后端 | 4 | 0 | 4 | 0% |
| IR 节点 | 2 | 0 | 2 | 0% |
| HIR Lowering | 2 | 0 | 2 | 0% |
| MIR Lowering | 4 | 0 | 4 | 0% |
| LIR Lowering | 4 | 0 | 4 | 0% |
| Pass 管理器 | 1 | 0 | 1 | 0% |
| C 运行时 | 4 | 1 (部分修复) | 3 | 25% |
| 测试套件 | 3 | 1 | 2 | 33% |
| Tree-sitter | 3 | 0 | 3 | 0% |

**整体修复率：52/94 = 55%（含部分修复）**

### 第五轮最高优先级修复项（Top 25）

1. **VM: BUILD_MAP count=1 修复引入新 bug** [vm.py:848-849] — **新发现**，历史修复不正确导致单元素字典崩溃
2. **VM: return_flag 跨调用边界干扰** [vm.py:172] — **新发现**，控制流信号跨调用泄漏
3. **VM: JUMP 启发式检测 while 回跳** [vm.py:684-686] — **新发现**，VM 窥探指令流推断编译器意图
4. **VM: 闭包捕获整个帧** [vm.py:785-788] — **五轮未修**
5. **求值器: Block env 不恢复** [evaluator.py:738-748] — **五轮未修**
6. **求值器: 顶层 ? ReturnSignal 未捕获** [evaluator.py:470-471] — **五轮未修**
7. **编译器: 模块导入无命名空间隔离** [compiler.py:300-343] — **五轮未修**
8. **类型检查器: 任意 TypeVar 兼容** [type_checker.py:1235-1236] — **五轮未修**
9. **类型检查器: 无 unify 算法** [type_checker.py] — **五轮未修**
10. **类型检查器: Let 多态缺失** [type_checker.py:744-754] — **五轮未修**
11. **parser: 运算符优先级完全错乱** [parser.py:428-678] — **五轮未修，|> 优先级比比较运算符高4级**
12. **parser: `<-` 歧义** [parser.py:464-466] — **部分修复，仍有歧义**
13. **lexer: 未闭合字符串终止词法分析** [lexer.py:252] — **五轮未修**
14. **errors.py: raise_all 丢失结构化信息** [errors.py:405-411] — **五轮未修**
15. **C 运行时: HTTP 命令注入安全漏洞** [nova_runtime.c:1645] — **CVE 级别，五轮未修**
16. **C 运行时: release 不递减子对象** [nova_runtime.c:479-486] — **五轮未修**
17. **C 运行时: Map.put 不释放旧 value** [nova_runtime.c:524-526] — **新发现**
18. **Native 后端: LIRReturn 跳过 callee-saved 恢复** [native_backend.py:461-463] — **新发现**，违反调用约定
19. **编译管道: BACKEND_NATIVE 路由到 Cranelift** [compiler_pipeline.py:33-35] — **命名欺骗**
20. **Cranelift 后端: 参数强制 i64 类型** [cranelift_backend.py:137-200] — **新发现**
21. **WASM 后端: 二元运算不压入操作数** [wasm_backend.py:337-341] — **五轮未修**
22. **C 后端: 闭包捕获传 NULL** [c_codegen.py:897] — **五轮未修**
23. **IR: Match 无条件执行第一个分支** [mir_lowering.py:351-384] — **五轮未修**
24. **IR: Phi 只取第一个 source** [lir_lowering.py:204-211] — **五轮未修**
25. **测试: 无 Evaluator-VM 一致性测试** [tests/] — **五轮未修**

### 五轮修复率趋势

| 轮次 | 严重 | 中等 | 轻微 | 总发现 | 总已修复 | 修复率 |
|------|------|------|------|--------|---------|--------|
| 第一轮 | 52 | 42 | 36 | 130 | 0 | 0% |
| 第二轮 | 47 | 47 | 49 | 143 | 25 | 17% |
| 第三轮 | 63 | 55 | 62 | 180 | ~35 | ~19% |
| 第四轮 | 47 | 50 | 46 | 143 | ~10 | ~7% |
| 第五轮 | 28 | 38 | 28 | 94 | 52 | **55%** |
| **累计** | **237** | **232** | **221** | **690** | **~122** | **~18%** |

### 关键趋势分析

1. **修复率显著回升**：第五轮修复率从第四轮的 ~7% 大幅回升至 55%，说明项目在核心引擎（VM/编译器/求值器/类型检查器）方面有集中修复工作
2. **核心引擎改善明显**：VM 的栈下溢保护、CONTINUE 实现、base_sp 截断等关键问题已修复；编译器的 Pattern 测试生成、guard 条件、列表推导式 filter 也已修复；类型检查器的 ADTType.__eq__、Pattern 覆盖、ErrorCollector 也已修复
3. **后端修复率为零**：所有后端（C/Cranelift/WASM/Native/编译管道）的严重问题零修复，非 C 后端完全不可用
4. **IR 层修复率为零**：4 个 MIR 严重缺陷（match/for/lambda/pipe）全部五轮未修，IR 管道对核心语言特性完全失效
5. **C 运行时安全漏洞持续**：HTTP 命令注入 + release 不递减子对象 + Map.put 泄漏，五轮未修
6. **新发现严重 bug**：VM BUILD_MAP 修复引入新 bug、return_flag 跨调用泄漏、Native 后端 LIRReturn 违反调用约定、C 运行时 Map.put 泄漏
7. **类型系统核心缺失仍是根本问题**：无 unify 算法、TypeVar 万能兼容、Let 多态缺失——这三个问题相互掩盖形成"错误抵消错误"，一旦修复其中一个其他会立即暴露
8. **parser 运算符优先级错误持续五轮**：`|>` 管道操作符优先级比比较运算符高4级，与 grammar.js 和语言设计意图完全不符

### 后端可行性总评估

| 后端 | 评估 | 说明 |
|------|------|------|
| C 代码生成 | 基本可用（有限制） | 不使用闭包捕获和 ? 操作符的纯函数程序可编译 |
| Native (x86_64) | 不可用 | LIRReturn 违反调用约定，直线代码外无法运行 |
| Cranelift | 不可用 | SSA 值跟踪缺失，生成的 .clif 无法验证 |
| WASM | 不可用 | 二元运算不压栈，生成的 WAT 无法验证 |
| x86_64 指令集 | 可用（作为库） | 指令编码基本正确，有少量重复方法 |
| 编译管道 | Demo 级别 | 命名误导，C 后端绕过 IR 管道 |

---

## [2026-07-15 第六轮] 全模块深度复查

> **审查标准**：生产级编译器/语言标准（参考 OCaml/Haskell/Elm/F# 最佳实践）
> **审查方法**：三轮 9 个 Agent 并行逐行审查
> **审查版本**：main 分支最新提交 (f187b0f)

### 项目结构审查表更新

| 模块 | 文件 | 审查状态 | 上次审查 | 严重问题数 | 中等问题数 | 轻微问题数 |
|------|------|---------|---------|-----------|-----------|-----------|
| VM 虚拟机 | `vm.py` | ✅ 已审查 | 2026-07-15 | 4 | 5 | 5 |
| 编译器 | `compiler.py` | ✅ 已审查 | 2026-07-15 | 5 | 4 | 5 |
| 求值器 | `evaluator.py` | ✅ 已审查 | 2026-07-15 | 2 | 6 | 6 |
| 类型检查器 | `type_checker.py` | ✅ 已审查 | 2026-07-15 | 4 | 5 | 2 |
| 词法分析器 | `lexer.py` | ✅ 已审查 | 2026-07-15 | 0 | 3 | 4 |
| 语法分析器 | `parser.py` | ✅ 已审查 | 2026-07-15 | 3 | 2 | 2 |
| 错误处理 | `errors.py` | ✅ 已审查 | 2026-07-15 | 2 | 1 | 3 |
| 模块系统 | `modules.py` | ✅ 已审查 | 2026-07-15 | 2 | 3 | 2 |
| 环境 | `environment.py` | ✅ 已审查 | 2026-07-15 | 1 | 3 | 2 |
| C 代码生成 | `c_codegen.py` | ✅ 已审查 | 2026-07-15 | 3 | 4 | 1 |
| Native 后端 | `backend/native_backend.py` | ✅ 已审查 | 2026-07-15 | 5 | 3 | 1 |
| Cranelift 后端 | `backend/cranelift_backend.py` | ✅ 已审查 | 2026-07-15 | 3 | 3 | 0 |
| WASM 后端 | `backend/wasm_backend.py` | ✅ 已审查 | 2026-07-15 | 3 | 2 | 1 |
| x86_64 指令发射 | `backend/x86_64.py` | ✅ 已审查 | 2026-07-15 | 1 | 2 | 1 |
| 编译管道 | `backend/compiler_pipeline.py` | ✅ 已审查 | 2026-07-15 | 1 | 1 | 1 |
| IR 节点 | `ir/ir_nodes.py` | ✅ 已审查 | 2026-07-15 | 0 | 1 | 1 |
| HIR Lowering | `ir/hir_lowering.py` | ✅ 已审查 | 2026-07-15 | 2 | 1 | 1 |
| MIR Lowering | `ir/mir_lowering.py` | ✅ 已审查 | 2026-07-15 | 4 | 0 | 0 |
| LIR Lowering | `ir/lir_lowering.py` | ✅ 已审查 | 2026-07-15 | 3 | 1 | 1 |
| Pass 管理器 | `ir/pass_manager.py` | ✅ 已审查 | 2026-07-15 | 3 | 3 | 1 |
| C 运行时 | `runtime/nova_runtime.c` | ✅ 已审查 | 2026-07-15 | 4 | 4 | 1 |
| 测试套件 | `tests/` | ✅ 已审查 | 2026-07-15 | 2 | 3 | 0 |
| Tree-sitter | `tree-sitter-nova/` | ✅ 已审查 | 2026-07-15 | 0 | 1 | 2 |

---

## [2026-07-15] VM 虚拟机 (vm.py) 第六轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 自定义栈式 VM 设计，有 ADT/闭包/模式匹配的字节码指令集，PIPE_CALL 指令有特色 |
| 可行性 | ⭐⭐⭐ | 基本功能可工作，但循环控制机制脆弱，嵌套场景有严重 bug |
| 正确性 | ⭐⭐ | CONCAT 语义错误、while break/continue 嵌套 bug、while 返回值不一致、全局构造器缺失 |
| 安全性 | ⭐⭐⭐ | 帧恢复有 finally 保护，但文件 I/O 无沙箱，浮点除零无检查 |
| 一致性 | ⭐⭐ | VM 与 Evaluator 在多个关键语义上不一致（CONCAT、闭包捕获、None 全局、while 返回值） |
| 完整性 | ⭐⭐⭐⭐ | 覆盖了几乎所有 Op 定义，指令集较完整（LOOP 操作码为死代码） |
| 工程质量 | ⭐⭐ | hasattr 动态属性、启发式循环检测、前向扫描跳转、注释与实际不一致 |
| 性能 | ⭐⭐⭐ | 闭包过度捕获浪费内存，字典存 locals 有开销 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [vm.py:617-621] **CONCAT 操作符语义错误** → `str(a) + str(b)` 强制将任意值转为字符串，与 Evaluator 的 `left + right` 完全不一致。`[1,2] ++ [3,4]` 在 VM 中产生 `"[1, 2][3, 4]"` 而非 `[1,2,3,4]` → 改为 `self.stack.append(a + b)` → 追问：OCaml 的 `@` 是列表拼接、`^` 是字符串拼接，两者不可混用。VM 将 `++` 实现为 `str()+str()` 在任何成熟语言中都不可接受 → **绝对不能接受**

- [vm.py:751-757] **while 循环 BREAK 使用脆弱的前向扫描** → 扫描到第一个 CONST_UNIT 或 LOOP_END 就停止，嵌套 while 循环中 break 必然行为错误 → 编译器应附带 end_ip 操作数 → 追问：JVM/Lua/CPython 的 break 都通过编译器计算好的跳转偏移量实现。运行时扫描指令流在任何生产级 VM 中都不可接受 → **绝对不能接受**

- [vm.py:769-777] **while 循环 CONTINUE 清理了整个栈到 base_sp** → 如果循环体之前栈上有外层 for 循环的值，continue 会错误清除它们 → 为 while 循环的 continue 只清理循环体产生的值 → 追问：Lua VM 和 JVM 的循环控制都使用编译时确定的跳转目标 → **绝对不能接受**

- [vm.py:845,884] **`id()` 被用作字典键（已修复为自增计数器）** → 当前使用 `_loop_id` 自增整数作为键，但异常退出时字典条目不清理 → 使用编译器分配的唯一循环 ID → 追问：如果 Python 的 itertools 用 id() 做 key 且有内存泄漏，能被接受吗 → **不能**

#### 中等问题（影响特定场景）

- [vm.py:180] **read_line 未处理 EOFError** → EOF 时抛 Python 异常而非 Nova 错误 → 捕获 EOFError 返回 Option::None
- [vm.py:780-789] **CLOSURE 捕获整个帧 dict 浅拷贝** → 过度捕获 + 浅拷贝违反不可变性 → 编译器分析自由变量，只拷贝指定变量
- [vm.py:594-603] **浮点数除以零不检查** → Python 产生 inf/-inf，函数式语言应报运行时错误 → 添加 `if b == 0: raise RuntimeError_`
- [vm.py:714-720] **_while_loops 的 loop_start 通过启发式检测设置** → 依赖 JUMP+CONST_UNIT 模式，编译器改变生成模式就会失效 → 编译器显式生成循环控制信息
- [vm.py:177-218] **全局 None/Some/Ok/Err 构造器在 VM 中缺失** → 高阶函数传递这些构造器时会"未定义变量"错误 → 在 VM globals 中注册这些构造器

#### 轻微问题（代码质量）

- [vm.py:655,669] JUMP_IF_FALSE 和 POP_JUMP_IF_FALSE 实现完全相同，可合并
- [vm.py:742-745] `_range_index`/`_list_index` 通过 hasattr 动态检查初始化，应在 `__init__` 中初始化
- [vm.py:579] `_pop` 注释中栈顺序描述与实际语义不一致
- [vm.py:659-670] AND/OR 使用 Python and/or，返回操作数值而非严格布尔值
- [vm.py:133,138] Frame.locals 命名不一致（locals_ vs locals）

#### 原创性分析

- **Nova 特色**：PIPE_CALL 专用管道调用指令、MATCH_START/MATCH_END 显式标记、TRY_UNWRAP 统一处理 Option/Result、ADT 原生指令
- **参考已有**：基本栈机设计参考 CPython/JVM；FOR_ITER + LOOP_END 双指令循环

#### Evaluator vs VM 对比
| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| `++` 运算符 | `left + right`（支持列表和字符串） | `str(a) + str(b)`（强制字符串化） | ❌ |
| 闭包捕获 | Environment 引用（词法作用域链） | dict(整个帧) 浅拷贝 | ❌ |
| None/Some/Ok/Err | 全局构造器（一等值） | 编译器特殊处理（非一等值） | ❌ |
| while 返回值 | 最后一次迭代的值 | CONST_UNIT | ❌ |
| read_line | `input()` + EOFError 处理 | lambda 无 EOF 处理 | ❌ |
| for 返回值 | 列表 | 列表 | ✅ |
| break/continue | 异常机制 | 指令机制（嵌套有 bug） | ⚠️ |
| TryExpr `?` | ReturnSignal 异常 | return_flag 机制 | ✅ |
| 模式匹配 | 递归匹配（穷尽性缺失） | 指令序列（穷尽性缺失） | ✅ |
| head 内置 | 无 field_names | 有 field_names | ⚠️ |

---

## [2026-07-15] 编译器 (compiler.py) 第六轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐ | 标准栈式字节码设计，无显著创新；VM 运行时扫描实现控制流是负面独创 |
| 可行性 | ⭐⭐⭐ | 基本功能可工作，但模块系统和嵌套循环有严重限制 |
| 正确性 | ⭐⭐ | while 循环 break/continue 存在确定性崩溃 bug 和脆弱的运行时扫描 |
| 安全性 | ⭐⭐ | 无循环导入保护、无模块命名空间隔离、过度闭包捕获 |
| 一致性 | ⭐⭐⭐ | 编译器与 VM 的操作码协议基本一致，但文档与实现不一致 |
| 完整性 | ⭐⭐⭐ | 所有 AST 节点有编译处理，但模式匹配有死代码 |
| 工程质量 | ⭐⭐ | 65 行死代码、无编译期错误检测、VM 控制流逻辑与指令执行耦合 |
| 性能 | ⭐⭐ | while break 运行时扫描 O(n)、闭包过度捕获、常量池形同虚设 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [compiler.py:468-471] **BREAK/CONTINUE 指令不带操作数** → VM 无法在编译期确定跳转目标，while 循环的 break 依赖运行时扫描，continue 首次迭代时 loop_start 为 None 导致崩溃 → 编译器应在 BREAK/CONTINUE 指令中嵌入 end_ip/loop_start → 追问：成熟编译器绝对不能在运行时扫描字节码来找跳转目标 → **绝对不能接受**

- [compiler.py:304-347] **import 内联无命名空间隔离** → 所有模块的导出被平铺到同一全局作用域，同名函数/ADT/变量会被静默覆盖 → 实现模块命名空间或至少冲突检测 → 追问：即使是 C 的 `#include` 也有头文件保护 → **绝对不能接受**

- [compiler.py:367-376] **嵌套函数名冲突** → 所有函数（包括嵌套 lambda）注册到全局 functions 字典，同名嵌套函数后编译的覆盖先编译的 → 实现词法作用域的函数查找 → 追问：任何支持嵌套函数的语言都保证名字不会冲突 → **不能接受**

- [compiler.py:961-962] **while 循环返回值总是 Unit** → 循环体后 POP 结果值，然后 CONST_UNIT，与文档"返回最后一次迭代值"不一致 → 不 POP 循环体结果或更新文档 → 追问：文档承诺了特定语义但实现违反了它 → **不能接受**

- [compiler.py:248-249] **AUTO_CALL_MAIN 指令是死代码** → HALT 在 AUTO_CALL_MAIN 之前，该指令永远不会被执行 → 删除或调换顺序

#### 中等问题（影响特定场景）

- [compiler.py:379,636] **CLOSURE 操作数不匹配** → Op 定义 3 个操作数，编译器只发 2 个 → 从 Op 定义中移除 code_key 或实际实现
- [vm.py:785-787] **闭包过度捕获所有局部变量** → 编译器没有做自由变量分析 → 实现 CLOSURE 的自由变量列表参数
- [compiler.py:408-410] **None 标识符特殊处理与 ADT 系统不一致** → None 在 Identifier 中处理，Some/Ok/Err 在 FnCall 中处理 → 统一到构造器调用机制
- [compiler.py:822-886] **_compile_pattern_test 和 _compile_pattern_bindings 是 65 行死代码** → PatternTuple/PatternList 在废弃方法中跳过结构测试 → 删除死代码

#### 轻微问题（代码质量）

- [compiler.py:397-398] CharLiteral 编译为 CONST_STRING，运行时 CharLiteral 和 StringLiteral 不可区分
- [compiler.py:449-451] Assignment 总是 mutable=True，不可变检查推迟到运行时
- [compiler.py:524] CONCAT 指令与 VM 实现一致但语义存疑（对非字符串类型静默转换）

---

## [2026-07-15] 求值器 (evaluator.py) 第六轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 设计完整，AST 遍历式解释器 + 两遍扫描 + 闭包捕获 + 模式匹配 + 错误传播 |
| 可行性 | ⭐⭐⭐⭐ | 整体架构可行，作为教学/原型解释器完全可用 |
| 正确性 | ⭐⭐⭐ | ++ 运算符与 VM 不一致、闭包捕获语义分歧、多处缺少类型检查 |
| 安全性 | ⭐⭐ | 无栈溢出保护、无沙箱、break/continue 可逃出函数体 |
| 一致性 | ⭐⭐⭐ | 与 VM 行为不一致（++、闭包、head field_names），None 值表示混用 |
| 完整性 | ⭐⭐⭐⭐ | AST 覆盖完整，模式匹配全面，缺少显式 return 和 cons 模式 |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰，但有重复代码（eval_decl），异常处理不完整 |
| 性能 | ⭐⭐⭐ | 树遍历解释器性能受限，环境链查找 O(n) |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [evaluator.py:865] **++ 运算符 Evaluator/VM 语义不一致** → Evaluator 用 `left + right`（列表拼接），VM 用 `str(a) + str(b)`（字符串强制）。两个后端对同一运算符给出不同结果 → 统一为类型检查的字符串拼接或报类型错误 → 追问：两个后端行为不一致意味着代码在不同执行模式下产生不同结果，在任何语言实现中都是严重 bug → **绝对不能接受**

- [evaluator.py:490 vs vm.py:785] **闭包捕获语义分歧** → Evaluator 捕获 Environment 引用（可变共享），VM 捕获 locals 浅拷贝（值快照）。可变计数器闭包在 Evaluator 能工作，在 VM 不能 → 统一为引用语义或值语义 → 追问：两个后端必须行为一致 → **不能接受**

#### 中等问题（影响特定场景）

- [evaluator.py:437-441] **break/continue 缺少函数内防护** → BreakSignal/ContinueSignal 逃出 _call_fn 被外层循环捕获 → 添加 except BreakSignal/ContinueSignal 并报错
- [evaluator.py:699-707] **TryExpr `?` 在顶层代码中抛 ReturnSignal** → eval_program 没有 except ReturnSignal，导致未捕获异常 → 在 eval_program 中捕获 ReturnSignal
- [evaluator.py:850-878] **二元运算缺少运行时类型检查** → 不兼容类型抛 Python TypeError 而非 Nova RuntimeError_ → 添加类型检查
- [evaluator.py:975-988] **模式匹配中环境切换无 finally 保护** → 守卫条件异常时 self.env 不恢复 → 使用 try-finally 包裹
- [evaluator.py:215] **_builtin_head 缺少 field_names** → 与 VM 版本不一致 → 添加 field_names=["value"]
- [evaluator.py:106-117] **无栈溢出保护** → 深度递归导致 Python RecursionError → 添加 MAX_CALL_DEPTH 检查

#### 轻微问题（代码质量）

- [evaluator.py:765-768] Assignment 捕获 Python RuntimeError 而非 Nova RuntimeError_，导致 Nova 错误不被转换
- [evaluator.py:270-271] JSON null 转换为 NovaADTValue("Option","None")，与 Python None 混用
- [evaluator.py:554-609] eval_decl 与 _collect_decl + _eval_decl_body 重复代码
- [evaluator.py:857] bool 是 int 子类型，true + 1 = 2 在 Nova 中可能不应被允许
- [evaluator.py:209-210] _builtin_sum 缺少类型检查
- [evaluator.py:201-207] _builtin_filter/map 缺少类型检查上下文

---

## [2026-07-15] 类型检查器 (type_checker.py) 第六轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 类型类层次、两遍扫描、ADT 字段访问有一定巧思，核心算法非原创 |
| 可行性 | ⭐⭐⭐ | 基本场景可工作，复杂类型推断会失败 |
| 正确性 | ⭐⭐ | 缺少 unify/generalize/instantiate/occurs check/exhaustiveness，类型安全有根本性漏洞 |
| 安全性 | ⭐⭐ | TypeVar 万能兼容使类型检查在无标注处形同虚设 |
| 一致性 | ⭐⭐⭐ | 代码风格统一，但错误恢复策略不一致 |
| 完整性 | ⭐⭐⭐ | 覆盖大部分语法构造，但缺少 MapExpr、穷尽性检查、occurs check |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰，ErrorCollector 实现完整 |
| 性能 | ⭐⭐⭐⭐ | 无昂贵的操作，简单程序性能足够 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [type_checker.py:1244-1245] **TypeVar 万能兼容** → `if isinstance(a, TypeVar) or isinstance(b, TypeVar): return True` 使得任何含 TypeVar 的类型比较都返回 True，包括不同 TypeVar 之间。类型检查在无标注处形同虚设 → 实现真正的 unify 算法 → 追问：Haskell/GHC/OCaml 的类型检查器如果对任意 TypeVar 返回 True，相当于没有类型检查 → **绝对不能接受**

- [type_checker.py:649-661] **模式匹配无穷尽性检查** → 不检查是否覆盖所有可能的值，不检查冗余分支。运行时 match 失败不可避免 → 实现 exhaustiveness checker → 追问：Rust/OCaml/Haskell/Swift 都有完整的穷尽性检查，这是类型安全的基石 → **绝对不能接受**

- [type_checker.py:全局] **声称 HM 类型推断但缺少核心算法** → 无 unify（统一化）、无 generalize/instantiate（泛化/实例化）、无 occurs check。实际实现是"带类型变量注解的局部类型检查"而非推断 → 实现 Algorithm W → 追问：声称 HM 但无核心组件相当于编译器声称"优化"但实际是 noop → **绝对不能接受**

- [type_checker.py:744-754] **Let 多态未正确实现** → 无 generalize/instantiate 意味着 `let id = fun x -> x in id 1 + id "a"` 在某些场景下不报错（TypeVar 万能兼容掩盖了问题） → 实现 let 多态的 generalize/instantiate → 追问：Let 多态是 HM 类型系统的核心特性 → **绝对不能接受**

#### 中等问题（影响特定场景）

- [type_checker.py:285-293] **内置 TypeVar 命名冲突** → `list_length` 和 `Option` 都使用 `TypeVar("T")`，在同一 bindings 字典中可能互相干扰 → 使用全局唯一 ID 的 TypeVar
- [type_checker.py:1031-1040] **错误后返回具体类型而非 ERROR_TYPE** → 后续代码基于错误类型继续检查，可能产生误导性错误信息 → 统一返回 ERROR_TYPE
- [type_checker.py:583-928] **MapExpr 在 check_expr 中未处理** → 包含 map 表达式的程序无法通过类型检查 → 添加 MapExpr 分支
- [type_checker.py:405-434] **递归 ADT 无 occurs check** → 不合理的无限类型不会被检测 → 实现 occurs check
- [type_checker.py:720-735] **PipeExpr 类型检查过于宽松** → 同时检查最后一个和第一个参数，多参数函数行为不确定

#### 轻微问题（代码质量）

- [type_checker.py:373] **check_program 默认 collect_errors=False** → 遇到第一个类型错误就停止 → 默认值改为 True
- [type_checker.py:646-647] **if 无 else 返回 UNIT_T 不检查 then_ty** → then_ty 非 Unit 时不发警告
- [type_checker.py:1018-1023] **PatternList 不支持 cons 模式** → `[head, ...tail]` 不可用
- [type_checker.py:1116-1118] **_collect_type_bindings 中 TypeVar 实例不一致** → 不同位置创建的 TypeVar("T") 是不同 Python 对象

---

## [2026-07-15] 词法分析器 (lexer.py) 第六轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 语言设计有特色（表达式导向、管道、显式 then/else） |
| 可行性 | ⭐⭐⭐⭐ | 核心功能可用，错误恢复有基本保障 |
| 正确性 | ⭐⭐⭐⭐ | 基本正确，未知转义静默丢弃反斜杠 |
| 安全性 | ⭐⭐⭐⭐ | 词法错误恢复有保障 |
| 一致性 | ⭐⭐⭐ | 死 token（UNIT/PIPE_VARIANT）、冗余分支 |
| 完整性 | ⭐⭐⭐ | 缺块注释、缺 return、缺科学计数法 |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰，错误报告有 Rust 风格上下文 |
| 性能 | ⭐⭐⭐ | 逐字符 _advance() 产生大量临时字符串拼接 |

### 发现的问题

#### 严重问题

（无新增严重问题——上次审查的非法字符恢复已修复）

#### 中等问题（影响特定场景）

- [lexer.py:252,256] **未闭合字符串直接 raise** → 非法字符能优雅恢复但未闭合字符串中断整个解析 → 改为错误恢复模式
- [lexer.py:249-250] **未知转义序列静默丢弃反斜杠** → `\a` 变成 `a` 而非报错 → 报错或发出警告
- [lexer.py:201-220] **不支持科学计数法和十六进制/八进制/二进制字面量** → 系统级语言应支持 → 视语言定位而定

#### 轻微问题（代码质量）

- [lexer.py:90] **TokenType.UNIT 是死 Token** → 定义但永不生成 → 删除
- [lexer.py:87] **TokenType.PIPE_VARIANT 是死 Token** → 定义但永不生成 → 删除
- [lexer.py:306-310] **_read_identifier 中 BOOL 分支冗余** → if/else 执行相同代码 → 统一处理
- [lexer.py:154-159] **_make_error 中 end_col 计算有误** → max(column, end_col) 无意义

---

## [2026-07-15] 语法分析器 (parser.py) 第六轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | ADT/模式匹配/列表推导/管道完整 |
| 可行性 | ⭐⭐⭐ | 核心功能可用，但管道优先级错误和 MapExpr 缺失 |
| 正确性 | ⭐⭐ | 管道优先级错误、MapExpr 不可用、while 条件贪婪解析 |
| 安全性 | ⭐⭐⭐⭐ | 不可变优先设计好 |
| 一致性 | ⭐⭐ | 死方法、iterable 元组 vs step 字段不一致 |
| 完整性 | ⭐⭐⭐ | 大部分特性可用，缺块注释、return |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰，span 追踪完整 |
| 性能 | ⭐⭐⭐ | while 循环解析，性能可接受 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [parser.py:672-678] **管道操作符 `|>` 优先级高于比较运算符** → `x |> f > 0` 被解析为 `x |> (f > 0)` 而非 `(x |> f) > 0`。F#/Elixir/Rust 中 `|>` 优先级低于比较 → 将 _parse_pipe 提升到 _parse_comparison_expr 之后 → 追问：这是语义级优先级错误，用户写出的管道+比较混合表达式全部被错误解析 → **绝对不能接受**

- [parser.py:830-831] **MapExpr 完全无法解析** → 遇到 `{` 直接调用 _parse_block()，`{"a" => 1}` 会被当作代码块解析 → 添加前瞻逻辑区分 block 和 map 字面量 → 追问：文档列出的核心数据类型在 parser 中完全缺失 → **绝对不能接受**

- [parser.py:471-474] **for 范围循环 step 信息重复且不一致** → step_expr 同时编码进 iterable 元组和 ForExpr.step 字段，下游处理混乱 → iterable 改为 `("range", start, end, None)` → 追问：数据模型不一致会导致下游处理混乱 → **不能接受**

#### 中等问题（影响特定场景）

- [parser.py:487-488] **while 条件表达式可能贪婪消费循环体** → `_parse_expression` 包含 for/while/if/match，嵌套控制流在条件中行为不可预测 → 条件使用 `_parse_or_expr`
- [parser.py:432-439] **_parse_pipe 方法是死代码** → 从未被 _parse_expression 调用链直接调用 → 删除或集成到调用链

#### 轻微问题（代码质量）

- [parser.py:334-346] **Fn[Int, Int] 语法歧义** → 表示 `(Int, Int) -> Unit` 但不可从语法推断
- [ast_nodes.py:200-205] **MatchArm 缺少 span 字段** → match 分支级别错误无法精确定位

---

## [2026-07-15] 错误处理 (errors.py) 第六轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | Rust 风格多行高亮、ANSI 颜色 + NO_COLOR 支持 |
| 可行性 | ⭐⭐⭐ | 基本框架可工作，ErrorCollector 未在求值器中集成 |
| 正确性 | ⭐⭐ | 错误信息缺少文件名、RuntimeError_ 遮蔽 Python 内置名 |
| 安全性 | ⭐⭐⭐ | 线程安全有 GIL 保护，全局可变单例有状态污染风险 |
| 一致性 | ⭐⭐⭐ | 错误类型层次清晰，但 RuntimeError_ 的下划线命名打破一致性 |
| 完整性 | ⭐⭐ | 错误收集仅覆盖类型检查阶段，错误信息缺少文件名 |
| 工程质量 | ⭐⭐⭐ | 代码组织清晰，但 add vs add_error 语义重叠 |
| 性能 | ⭐⭐⭐ | 格式化性能足够 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [errors.py:82-106] **NovaError 缺少 file_path 字段** → 多文件程序中错误信息不含文件名，无法定位问题 → 添加 file_path 参数 → 追问：任何支持多文件/模块的编译器都必须在错误信息中标注文件名。Rust 的 `--> src/main.rs:3:5` → **绝对不能接受**

- [errors.py:320] **RuntimeError_ 遮蔽 Python 内置 RuntimeError** → 命名易混淆，继承自 NovaError 而非 Python RuntimeError → 重命名为 NovaRuntimeError

#### 中等问题（影响特定场景）

- [errors.py:396-398] **ErrorCollector.get_all() 丢失时序信息** → 错误全排在警告前面，与源码出现顺序不一致 → 改用单一列表按序号排序
- [errors.py:334-352] **控制流信号继承自 Exception** → 可能被 except Exception 意外捕获 → 继承自 BaseException

#### 轻微问题（代码质量）

- [errors.py:365-378] add() 与 add_error() 语义重叠，API 混乱
- [errors.py:35-54] ANSI 颜色不支持 CLICOLOR=0 和 FORCE_COLOR
- [errors.py:61] SourceSpan = Span 别名是无意义的间接层

---

## [2026-07-15] 模块系统 (modules.py) 第六轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 循环导入检测、模块缓存设计合理 |
| 可行性 | ⭐⭐⭐ | 基本功能可用，但缓存无失效机制 |
| 正确性 | ⭐⭐ | NameError 永远不触发、静默吞掉导出查找失败 |
| 安全性 | ⭐⭐⭐ | 无线程安全但 GIL 保护 |
| 一致性 | ⭐⭐⭐ | 命名风格基本一致 |
| 完整性 | ⭐⭐ | 缺命名空间隔离、通配符导入、选择性导入 |
| 工程质量 | ⭐⭐⭐ | 代码清晰，但 _collect_exported_types 未使用 |
| 性能 | ⭐⭐⭐ | list.remove() O(n) 循环检测 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [modules.py:186,264-265] **模块缓存没有失效机制** → 修改模块文件后重新导入不会看到更新 → 添加 mtime 比较失效 → 追问：对于支持 REPL 或增量编译的系统不能接受

- [modules.py:328-330] **导入时同名绑定被静默覆盖** → 用户代码的 `let map = ...` 被 import 静默覆盖 → 添加冲突检查 → 追问：静默失败是编译器中的严重问题

#### 中等问题（影响特定场景）

- [modules.py:49-58] **get_exported_bindings 中 NameError 永远不触发** → Environment.lookup 抛 RuntimeError_ 不抛 NameError → 移除 NameError
- [modules.py:209,218,225] **模块加载错误缺少源码位置** → RuntimeError_ 不传 line/column/source → 接受 span 参数
- [modules.py:366-371] **全局可变单例是进程级状态** → 测试间互相污染，多线程不安全 → 提供依赖注入机制

#### 轻微问题（代码质量）

- [modules.py:271-274] list.remove() O(n)，改用 set
- [modules.py:276-299] _collect_exported_types 与 _collect_exports 完全相同且未使用
- [modules.py:98-105] 默认搜索路径包含空字符串

---

## [2026-07-15] 环境 (environment.py) 第六轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 标准作用域链实现 |
| 可行性 | ⭐⭐⭐⭐ | 功能正确，作为教学实现完全可用 |
| 正确性 | ⭐⭐⭐ | 作用域链和赋值语义正确 |
| 安全性 | ⭐⭐⭐ | 递归查找有栈溢出风险 |
| 一致性 | ⭐⭐⭐⭐ | 接口设计一致 |
| 完整性 | ⭐⭐⭐ | 缺作用域类型标记、位置信息 |
| 工程质量 | ⭐⭐⭐⭐ | 代码简洁清晰 |
| 性能 | ⭐⭐⭐ | 递归查找 O(n) |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [environment.py:34-40] **lookup/assign 抛出的错误无位置信息** → "未定义的变量 'x'" 完全不知道去哪里修 → 接受可选 span 参数 → 追问：这是编译器最基本的可用性要求 → **绝对不能接受**

#### 中等问题（影响特定场景）

- [environment.py:34-40] **作用域链递归查找有栈溢出风险** → 深层递归导致 RecursionError → 改为迭代实现
- [environment.py:26-28] **闭包环境捕获整个作用域链** → 循环中创建闭包共享同一变量 → 将捕获变量复制到隔离环境
- [environment.py:23-28] **没有作用域类型标记** → 调试时无法判断作用域类型 → 添加 scope_type 枚举

#### 轻微问题（代码质量）

- [environment.py:67-72] all_bindings() 子作用域静默覆盖父作用域无警告

---

## [2026-07-15] 所有后端 第六轮审查报告

### C 代码生成后端 (c_codegen.py)

#### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 独立实现 AST 直译，覆盖面广 |
| 可行性 | ⭐⭐⭐ | 基本程序可编译，但有关键语义错误 |
| 正确性 | ⭐⭐ | 指针比较、ADT 字段访问、TryExpr 等多处错误 |
| 安全性 | ⭐⭐ | 无类型安全的列表、无内存安全的转换 |
| 一致性 | ⭐⭐⭐ | 与 runtime 基本一致，但 ADT 布局不匹配 |
| 完整性 | ⭐⭐⭐⭐ | 覆盖了大部分 Nova 特性 |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰但缺乏类型传播 |
| 性能 | ⭐⭐ | 大量运行时调用，无优化 |

#### 严重问题

- [c_codegen.py:561-567] **指针类型使用 `==` 比较产生未定义行为** → `"hello" == "hello"` 比较指针地址 → 类型感知比较
- [c_codegen.py:578-588] **TryExpr 使用不存在的枚举名** → `NOVA_OPTION_NONE_TAG` 未在 runtime.h 中定义 → 使用正确的枚举名
- [c_codegen.py:957-963] **List 元素类型硬编码为 int64_t** → 字符串/浮点/ADT 元素被强制转换 → 根据元素类型使用正确转换

### Native x86_64 后端 (native_backend.py)

#### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐⭐ | 零依赖纯 Python x86_64 指令编码 + ELF 生成 |
| 可行性 | ⭐ | 代码无法正确运行（ret 冲突、栈不平衡） |
| 正确性 | ⭐ | 函数返回、寄存器分配、ABI 违规均有 P0 bug |
| 安全性 | ⭐ | 无内存安全、无栈保护 |
| 一致性 | ⭐ | 与 runtime 数据结构完全不兼容 |
| 完整性 | ⭐⭐⭐ | 覆盖大部分 LIR 指令 |
| 工程质量 | ⭐⭐ | LinearScanAllocator 定义但未使用 |
| 性能 | ⭐⭐ | 寄存器分配几乎无用 |

#### 严重问题

- [native_backend.py:460-463] **LIRReturn 直接 ret() 跳过函数尾声** → 每个函数返回后栈损坏、寄存器损坏 → LIRReturn 应跳转到尾声标签
- [native_backend.py:330] **寄存器分配后永不回收** → 超过 12 个同时活跃整数值的函数产生错误结果 → 实现活跃变量分析 + 寄存器回收
- [native_backend.py:769-793] **_start 从栈上偏移 8 读取 argc** → 违反 Linux ABI，传给 nova_init 的是 argv[0] 而非 argc → 改为 offset 0
- [native_backend.py:336-339] **常量寄存器缓存覆盖** → 二元运算结果覆盖常量寄存器后，后续引用同一常量得到错误值 → 每条指令分配独立虚拟寄存器
- [native_backend.py:363-385] **除法/取模未保存 callee-saved RDX** → idiv 使用 RDX 但不保护其中可能保存的活跃值

### Cranelift 后端 (cranelift_backend.py)

#### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐ | IR 文本生成 |
| 可行性 | ⭐ | 生成的 .clif 无法通过 clif-util 编译 |
| 正确性 | ⭐ | 浮点用错指令、branch 语法错误 |
| 安全性 | N/A | 无法编译 |
| 一致性 | ⭐⭐ | 类型映射基本合理但参数类型硬编码 |
| 完整性 | ⭐⭐⭐ | 覆盖大部分 LIR 指令 |
| 工程质量 | ⭐⭐ | 从末端到端验证 |
| 性能 | N/A | 无法编译 |

#### 严重问题

- [cranelift_backend.py:160-168] **LIRBranch 生成错误 Cranelift IR** → 缺少 block 头部声明、值名格式不对、条件/真/假分支结构错误 → 引入完整 block 管理和 SSA 值名映射
- [cranelift_backend.py:234-238] **所有二元操作使用整数版本** → `float_op_map` 已定义但未使用，浮点运算被编译为整数运算 → 根据操作数类型选择 int/float map
- [cranelift_backend.py:185,257-261] **LIRFieldAccess 和数据段语法不符合 Cranelift IR 规范** → load 指令地址格式错误，数据段语法错误

### WASM 后端 (wasm_backend.py)

#### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 独立实现 WAT 生成 |
| 可行性 | ⭐ | 循环和分支控制流完全错误 |
| 正确性 | ⭐ | 字符串编码 bug、block/loop 混用 |
| 安全性 | ⭐⭐⭐ | WASM 沙箱天然安全 |
| 一致性 | ⭐⭐ | 类型映射合理但与 WasmGC 语义不匹配 |
| 完整性 | ⭐⭐ | 缺 LoadGlobal/StoreGlobal |
| 工程质量 | ⭐⭐ | 缺少验证 |
| 性能 | ⭐⭐ | 大量 runtime 调用 |

#### 严重问题

- [wasm_backend.py:160-161] **字符串编码使用字面量 `\\x00` 而非空字节** → `b"\\x00"` 是 4 字节 ASCII 表示，所有字符串偏移计算偏大 3 字节 → 改为 `b"\x00"`
- [wasm_backend.py:231-232,258] **Label 映射为 block 但 LIRJump 映射为 br** → block + br 形不成循环，需要 loop 结构 → 区分循环标签和分支标签
- [wasm_backend.py:260-263] **LIRBranch 缺少 block 结构** → 只有 br_if 到 false block，没有 true block 跳转边界

### 编译管道 (compiler_pipeline.py)

#### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 标准 multi-pass 管道设计 |
| 可行性 | ⭐⭐ | C 后端基本可用，其他后端有问题 |
| 正确性 | ⭐⭐ | native 选项实际指向 cranelift |
| 安全性 | N/A | 管道本身无安全问题 |
| 一致性 | ⭐ | 后端选择与实际实现不一致 |
| 完整性 | ⭐⭐⭐ | 前端到 IR 到后端的完整路径 |
| 工程质量 | ⭐⭐⭐ | 代码简洁但缺少错误处理 |
| 性能 | N/A | 管道无性能问题 |

#### 严重问题

- [compiler_pipeline.py:33-35] **BACKEND_NATIVE 选项实际使用 Cranelift 后端** → 用户选择 native 得到 Cranelift IR 文本 → BACKEND_NATIVE 应使用 NativeCodeGen

---

## [2026-07-15] IR 系统 + Pass 管理器 第六轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 三层 IR 参考 MLIR 思想，应用于教学语言有创新性 |
| 可行性 | ⭐⭐ | 关键路径（match/for/if 控制流）有致命缺陷 |
| 正确性 | ⭐ | match 退化为顺序执行、phi 只取第一个 source、for 迭代变量不绑定 |
| 安全性 | ⭐⭐ | Pass 异常静默吞掉导致错误代码生成 |
| 一致性 | ⭐⭐⭐ | 三层 IR 命名和组织结构一致 |
| 完整性 | ⭐⭐ | ListComprehension 完全丢失、Lambda 只生成名字不生成体、Inlining 是空壳 |
| 工程质量 | ⭐⭐ | 无测试、类型注解不匹配、注释与代码不一致 |
| 性能 | ⭐⭐ | LICM 实现有 bug、CSE 过于保守 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [ir/mir_lowering.py:351-384] **match 表达式无条件执行所有 arm** → 依次执行所有分支，模式匹配语义完全丢失 → 为每个 arm 生成条件分支 → 追问：模式匹配是 Nova 的核心语言特性 → **绝对不能接受**

- [ir/lir_lowering.py:204-211] **MIRPhi 只取第一个 source** → if-else 的 else 分支结果永远被丢弃 → Phi 节点需要正确选择来源值 → 追问：SSA 的核心机制，错误实现导致所有含分支的控制流产生错误结果 → **绝对不能接受**

- [ir/mir_lowering.py:231-235] **MIRSwitch 退化为无条件跳转** → 所有 case 分支被忽略，永远跳到 default → 实现实际 switch 分支逻辑

- [ir/lir_lowering.py:219-222] **LIRBranch 缺少目标标签** → true_label 和 false_label 从未设置 → 设置 lir.true_label 和 lir.false_label

- [ir/mir_lowering.py:396-417] **for 循环迭代变量不绑定** → hir_expr.variable 从未绑定到 SSA 环境，循环体中引用迭代变量得到 None → 为迭代变量创建 SSA 名

- [ir/hir_lowering.py:147-152] **for 范围循环的 start/end 参数丢失** → 替换为魔法标识符 "_range"，范围循环完全无法工作 → 引入 HIRRangeIterator 节点

- [ir/mir_lowering.py:200-204] **BlockExpr 中的 LetDecl 不被处理** → 表达式内的 let 声明变量永远不会被绑定 → 在 _lower_expr 中添加 HIRLetDecl 处理

- [ir/mir_lowering.py:275-282] **赋值操作违反 SSA 不变式** → 直接覆盖 env 中的映射而不创建新版本名 → 每次 mut 赋值创建新 SSA 名

- [ir/pass_manager.py:720-725] **Pass 异常处理静默吞掉所有异常** → 内部 bug 导致 IR 半修改状态后继续编译，生成错误代码 → 内部错误应立即终止编译 → 追问：rustc/clang/LLVM 遇到内部错误立即终止。静默继续导致错误代码生成是编译器的致命缺陷 → **绝对不能接受**

- [ir/pass_manager.py:105-108] **常量折叠通过修改 `__class__` 实现** → 直接修改对象类型身份，破坏数据完整性 → 创建新节点替换 → 追问：任何生产编译器都不会用这种方式做 AST 变换 → **不可接受**

#### 中等问题（影响特定场景）

- [ir/pass_manager.py:257-262] **Inlining Pass 是空壳** → 函数内联是优化管道核心，空壳实现使常量折叠和 CSE 效果大打折扣
- [ir/pass_manager.py:652-656] **LICM MIR 实现只检查 header 块** → 循环体中定义的值不被考虑，可能错误外提依赖循环定义的指令
- [ir/pass_manager.py:49] **整数除法使用 Python 地板除语义** → 可能与 Nova 截断除语义不一致
- [ir/pass_manager.py:45-59] **整数溢出处理缺失** → Python 任意精度但目标平台是固定宽度
- [ir/lir_lowering.py:171-176] **MIRMapBuild 使用 LIRBuildList** → Map 内存布局与 List 完全不同
- [ir/ir_nodes.py:730] **reg_alloc 类型错误** → Dict[str, str] 传入 Dict[str, int]
- [ir/hir_lowering.py:97-98] **AliasDef 丢弃目标类型信息**

#### 优化 Pass 实现状态

| Pass | HIR | MIR | LIR | 实际效果 |
|------|-----|-----|-----|----------|
| ConstantFolding | 部分（不递归） | 有实现 | 有实现 | 有，但不完整 |
| Inlining | **空壳** | - | - | **无** |
| DCE | 空壳 | 空壳 | 有实现 | 部分 |
| CSE | 空壳 | 有实现 | 有实现 | 有，但保守 |
| LICM | 空壳 | 有实现（**严重缺陷**） | 有实现 | **不正确** |

---

## [2026-07-15] C 运行时 (runtime/nova_runtime.c) 第六轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 函数式+管道+ADT+多后端+C 运行时的设计有特色 |
| 可行性 | ⭐⭐⭐ | 多后端架构好，但 HTTP 用 system(curl)、无真正 GC |
| 正确性 | ⭐⭐⭐ | 核心 AST/Evaluator/VM 逻辑较好，但内存管理有 bug |
| 安全性 | ⭐⭐ | 命令注入漏洞、无线程安全 |
| 一致性 | ⭐⭐⭐⭐ | Python/C/Wasm 三条路径设计一致 |
| 完整性 | ⭐⭐⭐⭐ | 覆盖了所有数据类型操作 |
| 工程质量 | ⭐⭐⭐ | 代码清晰，但缺乏 ASan/CI 集成测试 |
| 性能 | ⭐⭐⭐ | 哈希表有 rehash、列表有动态扩容 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [nova_runtime.c:1623-1712] **nova_http_get 使用 system(curl) 存在命令注入** → URL 直接拼入 shell 命令，任何含 `"` 或 `$(...)` 的 URL 可执行任意命令 → 使用 libcurl C 库 → 追问：任何生产语言的标准库都禁止命令注入 → **绝对不能接受**

- [nova_runtime.c:1486-1489] **nova_system 存在命令注入** → 直接将用户字符串传给 system() → 移除或添加沙箱 → 追问：经典命令注入入口 → **绝对不能接受**

- [nova_runtime.c:94-103] **GC 不处理循环引用** → 循环引用导致内存永久泄漏 → 实现 mark-sweep cycle detector

- [nova_runtime.c:319-330] **引用计数无原子操作** → 多线程环境数据竞争 → 使用 _Atomic 类型

#### 中等问题（影响特定场景）

- [nova_runtime.c:419-429] **nova_list_filter 不释放被过滤掉元素的所有权** → 原始 list 释放后元素可能 double-free → 明确文档化所有权转移语义
- [nova_runtime.c:363-368] **nova_list_set 不释放旧值** → 引用计数对象直接覆盖导致泄漏 → 条件性 release 旧值
- [nova_runtime.c:516-529] **nova_map_put 更新时不释放旧 value** → 同上
- [nova_runtime.c:831-848] **fseek/ftell 在 32-bit 系统截断** → 使用 fseeko/ftello
- [nova_runtime.c:193-196] **nova_string_char_at 不处理 UTF-8** → 按字节索引而非字符索引 → 实现 UTF-8 字符索引
- [nova_runtime.c:1226-1243] **JSON \uXXXX 代理对和 4 字节 UTF-8 未处理**

---

## [2026-07-15] 测试套件 (tests/) 第六轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 覆盖面广 |
| 可行性 | ⭐⭐⭐ | Evaluator/VM 各自测试充分 |
| 正确性 | ⭐⭐ | 缺少 Evaluator/VM 等价性测试 |
| 安全性 | ⭐⭐ | 无并发测试、无内存泄漏测试 |
| 一致性 | ⭐⭐⭐ | 测试命名和组织一致 |
| 完整性 | ⭐⭐ | 核心语言特性覆盖较好，但关键缺失明显 |
| 工程质量 | ⭐⭐⭐ | pytest 框架，结构清晰 |
| 性能 | ⭐⭐⭐ | 测试运行速度可接受 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [tests/] **无 Evaluator/VM 行为一致性测试** → Evaluator ~80 个测试、VM ~50 个测试，但测试用例几乎不重叠，没有系统性验证两条路径的行为一致 → 添加相同输入同时验证两条输出的等价性测试 → 追问：生产语言（PyPy vs CPython、GraalVM vs JVM）必须有严格的等价性测试套件 → **绝对不能接受**

- [tests/] **闭包内存泄漏无测试** → 无 ASan/Valgrind 验证引用计数正确性 → 添加内存安全测试

#### 中等问题（影响特定场景）

- [tests/] **HTTP 模块完全没有测试** → nova_http_get/nova_system 无测试
- [tests/] **UTF-8 多字节字符的所有字符串操作无测试**
- [tests/] **Map 的 rehash 后迭代稳定性无测试**
- [tests/] **C 后端生成代码的端到端编译验证不完整**

---

## [2026-07-15] Tree-sitter (tree-sitter-nova/) 第六轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 基于标准 Tree-sitter 框架 |
| 可行性 | ⭐⭐⭐ | 基本语法覆盖 |
| 正确性 | ⭐⭐⭐ | 与 parser.py 基本一致 |
| 安全性 | ⭐⭐⭐ | Tree-sitter 框架保证 |
| 一致性 | ⭐⭐⭐ | grammar.js 与 parser.py 基本一致 |
| 完整性 | ⭐⭐ | corpus 测试覆盖不足 |
| 工程质量 | ⭐⭐⭐ | 代码结构标准 |
| 性能 | ⭐⭐⭐⭐ | Tree-sitter C 实现 |

### 发现的问题

#### 中等问题（影响特定场景）

- [tree-sitter-nova/grammar.js:27-30] **lambda 和 pipe 的冲突声明** → `[$.lambda, $.pipe_expr]` 说明存在歧义
- [tree-sitter-nova/test/corpus/] **corpus 测试覆盖不足** → 缺少 while/break/continue/import/export/tuple/map/char/for range/escape sequences

#### 轻微问题（代码质量）

- [tree-sitter-nova/grammar.js:604] **只支持行注释** → 与 parser.py 一致，但函数式语言通常也支持块注释

---

### 第六轮审查总结

**新发现 vs 历史问题对比**：

| 类别 | 第五轮严重问题数 | 第六轮严重问题数 | 变化 |
|------|-----------------|-----------------|------|
| VM 虚拟机 | 9 | 4 | ↓ 部分已修复 |
| 编译器 | 7 | 5 | ↓ 部分已修复 |
| 求值器 | 9 | 2 | ↓ 大幅改善 |
| 类型检查器 | 13 | 4 | ↓ 部分框架改善 |
| 前端（词法+语法） | 10 | 3 | ↓ 改善 |
| 基础设施（错误+模块+环境） | 9 | 5 | → 持平 |
| C 代码生成 | 7 | 3 | ↓ 部分修复 |
| 非C后端 | 24 | 12 | → 仍大量存在 |
| IR 系统 | 15 | 10 | → 仍大量存在 |
| 运行时+测试 | 22 | 6 | ↓ 部分修复 |
| **总计** | **125** | **54** | **↓ 57% 改善** |

**最需要优先修复的 Top 10 问题（跨模块）**：

1. **[type_checker.py:1244]** TypeVar 万能兼容 — 类型安全基础漏洞
2. **[compiler.py:468-471 + vm.py:751-777]** while 循环 break/continue — 运行时崩溃
3. **[vm.py:617-621 + evaluator.py:865]** ++ 运算符 Evaluator/VM 不一致 — 两条路径结果不同
4. **[ir/mir_lowering.py:351-384]** match 表达式退化为顺序执行 — IR 核心特性失效
5. **[ir/lir_lowering.py:204-211]** MIRPhi 只取第一个 source — 所有分支结果错误
6. **[parser.py:830-831]** MapExpr 完全无法解析 — 文档承诺的功能不可用
7. **[nova_runtime.c:1623-1712]** HTTP 命令注入 — 安全漏洞
8. **[ir/pass_manager.py:720-725]** Pass 异常静默吞掉 — 可能生成错误代码
9. **[native_backend.py:460-463]** 函数返回跳过尾声 — Native 后端完全不可用
10. **[errors.py:82-106]** 错误信息缺少文件名 — 多文件项目不可调试

**后端可行性总评估（更新）**

| 后端 | 评估 | 说明 |
|------|------|------|
| C 代码生成 | **基本可用（有限制）** | 不使用闭包捕获、? 操作符、Map 比较的纯函数程序可编译 |
| Native (x86_64) | **不可用** | ret 冲突 + 栈不平衡 + ABI 违规 + 寄存器泄漏 |
| Cranelift | **不可用** | .clif 语法错误 + 浮点用错指令 + block 声明缺失 |
| WASM | **不可用** | 字符串编码 bug + block/loop 控制流错误 |
| x86_64 指令集 | **可用（作为库）** | 指令编码基本正确，有重复方法 |
| 编译管道 | **Demo 级别** | native 选项指向 cranelift，C 后端绕过 IR 管道 |
| IR 系统 | **Demo 级别** | 架构正确但 match/for/if/phi 全部致命缺陷 |

---

## [2026-07-15 第七轮] 全项目深度审查报告

### 审查范围
本轮为第七轮全面审查，覆盖 Nova 项目所有核心模块。审查标准为生产级编译器（OCaml/Haskell/Elm/F#）严格标准。

### 更新后的项目结构审查表

更新项目结构审查表中各模块的审查状态为"✅ 已审查"，上次审查为"2026-07-15"，严重问题数、中等问题数、轻微问题数根据本轮审查结果更新。

| 模块 | 文件 | 审查状态 | 上次审查 | 严重问题数 | 中等问题数 | 轻微问题数 |
|------|------|---------|---------|-----------|-----------|-----------|
| VM 虚拟机 | `vm.py` | ✅ 已审查 | 2026-07-15 | 8 | 12 | 11 |
| 编译器 | `compiler.py` | ✅ 已审查 | 2026-07-15 | 6 | 6 | 8 |
| 求值器 | `evaluator.py` | ✅ 已审查 | 2026-07-15 | 5 | 7 | 8 |
| AST 节点 | `ast_nodes.py` | ✅ 已审查 | 2026-07-15 | 0 | 0 | 1 |
| 类型检查器 | `type_checker.py` | ✅ 已审查 | 2026-07-15 | 5 | 5 | 7 |
| 词法分析器 | `lexer.py` | ✅ 已审查 | 2026-07-15 | 2 | 3 | 6 |
| 语法分析器 | `parser.py` | ✅ 已审查 | 2026-07-15 | 3 | 4 | 6 |
| 错误处理 | `errors.py` | ✅ 已审查 | 2026-07-15 | 3 | 5 | 4 |
| 模块系统 | `modules.py` | ✅ 已审查 | 2026-07-15 | 1 | 5 | 3 |
| 环境 | `environment.py` | ✅ 已审查 | 2026-07-15 | 0 | 2 | 2 |
| C 代码生成 | `c_codegen.py` | ✅ 已审查 | 2026-07-15 | 5 | 5 | 2 |
| Native 后端 | `backend/native_backend.py` | ✅ 已审查 | 2026-07-15 | 6 | 4 | 0 |
| Cranelift 后端 | `backend/cranelift_backend.py` | ✅ 已审查 | 2026-07-15 | 6 | 2 | 0 |
| WASM 后端 | `backend/wasm_backend.py` | ✅ 已审查 | 2026-07-15 | 7 | 0 | 1 |
| x86_64 指令发射 | `backend/x86_64.py` | ✅ 已审查 | 2026-07-15 | 1 | 0 | 2 |
| 编译管道 | `backend/compiler_pipeline.py` | ✅ 已审查 | 2026-07-15 | 3 | 1 | 1 |
| IR 节点 | `ir/ir_nodes.py` | ✅ 已审查 | 2026-07-15 | 2 | 1 | 3 |
| HIR Lowering | `ir/hir_lowering.py` | ✅ 已审查 | 2026-07-15 | 2 | 3 | 4 |
| MIR Lowering | `ir/mir_lowering.py` | ✅ 已审查 | 2026-07-15 | 4 | 3 | 1 |
| LIR Lowering | `ir/lir_lowering.py` | ✅ 已审查 | 2026-07-15 | 3 | 2 | 3 |
| Pass 管理器 | `ir/pass_manager.py` | ✅ 已审查 | 2026-07-15 | 3 | 5 | 2 |
| C 运行时 | `runtime/nova_runtime.c` | ✅ 已审查 | 2026-07-15 | 5 | 7 | 5 |
| 测试套件 | `tests/` | ✅ 已审查 | 2026-07-15 | 4 | 2 | 1 |
| Tree-sitter | `tree-sitter-nova/` | ✅ 已审查 | 2026-07-15 | 2 | 2 | 0 |

---

### 各模块详细审查报告

#### 关键发现摘要

本轮审查相比前6轮审查，确认了大部分之前发现的问题仍然存在，同时发现了以下新问题：

---

#### VM 虚拟机 (vm.py) 新发现

| 编号 | 严重度 | 位置 | 问题描述 |
|------|--------|------|----------|
| VM-7-1 | 🔴 严重 | `[vm.py:787-795]` | while 循环 CONTINUE 实际上终止了循环 — CONTINUE 清理栈到 base_sp 后跳回 loop_start，但栈上没有条件值导致栈下溢崩溃 |
| VM-7-2 | 🔴 严重 | `[vm.py:1185-1195]` | TRY_UNWRAP 对 None/Err 只返回 True 导致返回错误值而非正确传播 |
| VM-7-3 | 🟡 中等 | `[vm.py:1164]` | DUP 在空栈上导致 IndexError 崩溃 |
| VM-7-4 | 🟡 中等 | `[vm.py:868]` | INDEX 在越界时抛 Python 原生异常而非 Nova 错误 |

**详细分析**：

- **VM-7-1**：`while` 循环的 `CONTINUE` 实现在 `vm.py:787-795`，当执行 `CONTINUE` 指令时，VM 将栈清理到 `base_sp` 后跳转回 `loop_start`。然而此时栈上已经没有条件值，导致后续的条件判断指令在空栈上执行，引发栈下溢崩溃。这与正常的循环继续语义完全相反，`CONTINUE` 实际上终止了循环。

- **VM-7-2**：`TRY_UNWRAP` 指令在 `vm.py:1185-1195` 对 `None` 或 `Err` 值只返回布尔值 `True`，而不是正确传播错误值。这意味着错误处理的 `?` 操作符在 VM 层面无法正确工作，错误会被静默吞掉。

- **VM-7-3**：`DUP` 指令在 `vm.py:1164` 处没有检查栈是否为空，当栈为空时直接调用 `self.stack[-1]` 会导致 `IndexError` 崩溃。

- **VM-7-4**：`INDEX` 指令在 `vm.py:868` 处越界时抛出 Python 原生异常，而非包装为 Nova 运行时错误，导致用户无法通过 Nova 的错误处理机制捕获索引越界。

---

#### 编译器 (compiler.py) 新发现

| 编号 | 严重度 | 位置 | 问题描述 |
|------|--------|------|----------|
| CMP-7-1 | 🔴 严重 | `[compiler.py:798-806]` | CLOSURE 指令捕获全部局部变量，无自由变量分析 |
| CMP-7-2 | 🟡 中等 | `[compiler.py:1046-1065]` | 列表推导式 filter 条件编译的栈布局泄漏 |
| CMP-7-3 | 🟡 中等 | `[compiler.py:945]` | for 循环中 iterable 用 tuple 检测而非 AST 节点类型 |

**详细分析**：

- **CMP-7-1**：`CLOSURE` 指令在 `compiler.py:798-806` 捕获当前帧的全部局部变量，而非仅捕获被闭包引用的自由变量。这导致：(1) 闭包对象体积膨胀；(2) 不必要的变量被冻结在闭包中；(3) 与标准编译器实现严重不符。正确的做法应通过自由变量分析（free variable analysis）仅捕获实际引用的变量。

- **CMP-7-2**：列表推导式在编译 filter 条件时（`compiler.py:1046-1065`），栈布局管理存在泄漏。filter 条件表达式编译后栈上残留的值未被正确清理，导致后续迭代元素在栈上的偏移量错误。

- **CMP-7-3**：`for` 循环在 `compiler.py:945` 使用 Python `tuple` 类型来检测迭代对象，而非检查 AST 节点类型。这意味着编译器的迭代分发逻辑依赖于运行时类型信息，而非编译时可确定的 AST 结构，违反了编译器设计原则。

---

#### 求值器 (evaluator.py) 新发现

| 编号 | 严重度 | 位置 | 问题描述 |
|------|--------|------|----------|
| EVAL-7-1 | 🔴 严重 | `[evaluator.py:740-744]` | if cond: 使用 Python truthy 语义而非 Nova 语义（0, "", [] 被视为 false） |
| EVAL-7-2 | 🔴 严重 | `[evaluator.py:712-720]` | TryExpr ? 使用 ReturnSignal 传播错误值会穿透多层调用帧 |
| EVAL-7-3 | 🟡 中等 | `[evaluator.py:752-761]` | Block 求值中 self.env 恢复无异常保护（异常抛出后作用域链损坏） |
| EVAL-7-4 | 🟡 中等 | `[evaluator.py:882-893]` | 比较运算缺少 Bool 类型保护（允许 true < 1） |

**详细分析**：

- **EVAL-7-1**：条件表达式在 `evaluator.py:740-744` 直接使用 Python 的 truthy 语义进行求值，导致 `0`、`""`、`[]` 等 Nova 中应为合法值的对象被错误地视为 `false`。Nova 作为类型安全的语言，条件表达式应仅接受 `Bool` 类型，或至少应有明确的类型转换规则。

- **EVAL-7-2**：`TryExpr` 的 `?` 操作符在 `evaluator.py:712-720` 使用 `ReturnSignal` 传播错误值，但这会导致错误值穿透多层调用帧，而非在当前调用栈层面正确传播。这使得 `?` 操作符的行为不可预测，错误处理语义被破坏。

- **EVAL-7-3**：`Block` 求值在 `evaluator.py:752-761` 中恢复 `self.env` 时没有异常保护。如果在 block 求值过程中抛出异常，环境恢复代码不会执行，导致作用域链损坏，后续的变量查找可能指向错误的词法作用域。

- **EVAL-7-4**：比较运算在 `evaluator.py:882-893` 缺少 `Bool` 类型保护，允许 `true < 1` 这类无意义的比较表达式通过求值。在类型安全的语言中，布尔值不应参与数值比较。

---

#### 类型检查器 (type_checker.py) 新发现

| 编号 | 严重度 | 位置 | 问题描述 |
|------|--------|------|----------|
| TC-7-1 | 🔴 严重 | `[type_checker.py:1114-1134]` | 无 Occurs Check（可能接受无限类型导致崩溃） |
| TC-7-2 | 🔴 严重 | `[type_checker.py]` | 完全不是 Hindley-Milner（缺少统一化、泛化、实例化三大核心机制） |
| TC-7-3 | 🟡 中等 | `[type_checker.py:649-661]` | 无 match 穷尽性检查 |
| TC-7-4 | 🟡 中等 | `[type_checker.py:926-928]` | MapExpr 类型检查完全缺失 |

**详细分析**：

- **TC-7-1**：类型统一化在 `type_checker.py:1114-1134` 缺少 Occurs Check，可能接受类似 `a = List<a>` 的无限类型（infinite type）。在标准 HM 类型系统中，Occurs Check 是防止类型推断陷入无限循环的必要安全检查，缺失会导致类型检查器在某些情况下崩溃或接受不健全的类型。

- **TC-7-2**：整个类型检查器并非真正的 Hindley-Milner 实现。缺少三大核心机制：(1) **统一化（Unification）** — 没有正确的 Robinson 统一化算法；(2) **泛化（Generalization）** — let 多态的泛化步骤缺失；(3) **实例化（Instantiation）** — 多态类型使用时没有正确的实例化。这意味着类型推断系统从根本上不可靠。

- **TC-7-3**：`match` 表达式在 `type_checker.py:649-661` 没有穷尽性检查（exhaustiveness check），允许开发者遗漏模式分支而不发出警告。在生产级语言中，这是类型安全的关键保障。

- **TC-7-4**：`MapExpr` 的类型检查在 `type_checker.py:926-928` 完全缺失。由于 parser 也无法生成 `MapExpr`（见 parser 问题），此节点类型在整个编译管道中都是死代码。

---

#### 词法/语法分析器新发现

| 编号 | 严重度 | 位置 | 问题描述 |
|------|--------|------|----------|
| LEX-7-1 | 🟡 中等 | `[lexer.py:88]` | PIPE_VARIANT 是死 Token（定义了但 lexer 永不生成） |
| LEX-7-2 | 🟡 中等 | `[lexer.py:91]` | UNIT 是死 Token |
| PARSER-7-1 | 🔴 严重 | `[parser.py:768-834]` | MapExpr 完全无法解析（parser 中没有任何方法生成 MapExpr） |
| PARSER-7-2 | 🟡 中等 | `[parser.py:464-466]` | `<-` 合成操作符有词法歧义（`< -3` 会被错误解析为 `<-`） |

**详细分析**：

- **LEX-7-1**：`PIPE_VARIANT` Token 在 `lexer.py:88` 中定义，但词法分析器的模式匹配规则中没有任何规则会生成此 Token。这是死代码，增加了维护负担。

- **LEX-7-2**：`UNIT` Token 在 `lexer.py:91` 中定义但同样不会被生成。`unit` 值可能通过其他途径（如空括号 `()`）表示，使得此 Token 定义冗余。

- **PARSER-7-1**：`MapExpr` 在 `parser.py:768-834` 完全无法被解析。尽管 AST 中定义了 `MapExpr` 节点，语法分析器中没有任何产生式规则会创建该节点。这意味着文档中可能承诺的 Map 字面量语法实际上完全不可用。

- **PARSER-7-2**：`<-` 合成操作符在 `parser.py:464-466` 存在词法歧义。表达式 `< -3`（小于负三）会被错误地解析为 `<-`（左箭头）操作符后跟 `3`，导致语义错误。正确的做法是在词法分析阶段区分 `< -`（两个独立 Token）和 `<-`（一个 Token）。

---

#### 错误处理 (errors.py) 新发现

| 编号 | 严重度 | 位置 | 问题描述 |
|------|--------|------|----------|
| ERR-7-1 | 🟡 中等 | `[errors.py:396-398]` | ErrorCollector.get_all() 丢失时间顺序 |
| ERR-7-2 | 🟡 中等 | `[errors.py:405-411]` | raise_all() 将后续 error 降级为 note |

**详细分析**：

- **ERR-7-1**：`ErrorCollector.get_all()` 在 `errors.py:396-398` 返回错误列表时丢失了错误的时间顺序。错误的排列顺序对调试至关重要，时间顺序的丢失使得开发者难以追踪错误的因果链。

- **ERR-7-2**：`raise_all()` 在 `errors.py:405-411` 只抛出第一个错误，将其余错误降级为 `note`。这种设计导致后续的严重错误被掩盖为附属信息，开发者可能忽略重要的问题。

---

#### 模块系统 (modules.py) 新发现

| 编号 | 严重度 | 位置 | 问题描述 |
|------|--------|------|----------|
| MOD-7-1 | 🔴 严重 | `[modules.py:187]` | 循环导入检测使用 List 而非 Set（O(n) 性能且 remove 有误删风险） |
| MOD-7-2 | 🟡 中等 | `[modules.py:282-290]` | 导出收集是空壳（elif 分支全部是 pass） |

**详细分析**：

- **MOD-7-1**：循环导入检测在 `modules.py:187` 使用 `List` 数据结构而非 `Set`。这带来两个问题：(1) `in` 检查是 O(n) 复杂度，在大型项目中可能成为性能瓶颈；(2) `remove()` 操作基于值匹配，如果模块路径字符串存在重复或相似的情况，可能误删错误的条目。

- **MOD-7-2**：模块导出收集在 `modules.py:282-290` 中 `elif` 分支全部是 `pass`，意味着导出收集功能是一个空壳。无论模块中的 `export` 声明是什么，都不会被实际收集和记录，导致模块的公开 API 无法被正确管理。

---

#### 环境 (environment.py)

本轮审查未发现新问题。之前发现的中等问题（2个）和轻微问题（2个）仍然存在。

---

#### 后端新发现

##### C 代码生成 (c_codegen.py)

| 编号 | 严重度 | 位置 | 问题描述 |
|------|--------|------|----------|
| CCGEN-7-1 | 🔴 严重 | `[c_codegen.py:861-897]` | C 后端闭包不捕获自由变量（总是传 NULL） |
| CCGEN-7-2 | 🔴 严重 | `[c_codegen.py:781-788]` | filter/map 参数顺序反转 |
| CCGEN-7-3 | 🟡 中等 | `[c_codegen.py:695]` | ADT 模式匹配字段名格式错误 |

**详细分析**：

- **CCGEN-7-1**：C 后端在 `c_codegen.py:861-897` 生成闭包代码时，总是将捕获环境指针设为 `NULL`，而非传递实际捕获的自由变量。这意味着通过 C 后端编译的任何使用闭包的程序都会在运行时崩溃或产生未定义行为。

- **CCGEN-7-2**：`filter` 和 `map` 高阶函数在 `c_codegen.py:781-788` 的参数顺序被反转。标准库中 `filter(predicate, list)` 和 `map(fn, list)` 的参数顺序与生成的 C 代码不一致，导致函数应用逻辑错误。

- **CCGEN-7-3**：ADT 模式匹配在 `c_codegen.py:695` 生成字段名时格式错误，导致生成的 C 代码无法正确访问 ADT 变体的字段。

##### Native 后端 (backend/native_backend.py)

| 编号 | 严重度 | 位置 | 问题描述 |
|------|--------|------|----------|
| NATIVE-7-1 | 🔴 严重 | `[native_backend.py:45-82]` | 寄存器分配器 LinearScanAllocator 完全未使用 |
| NATIVE-7-2 | 🔴 严重 | `[native_backend.py:734-798]` | List/ADT/Tuple 在栈上分配后产生悬空指针 |
| NATIVE-7-3 | 🔴 严重 | `[native_backend.py]` | 多个之前发现的 ret 冲突、栈不平衡、ABI 违规问题仍存在 |
| NATIVE-7-4 | 🟡 中等 | `[native_backend.py]` | 寄存器泄漏问题仍存在 |

**详细分析**：

- **NATIVE-7-1**：`LinearScanAllocator` 在 `native_backend.py:45-82` 被完整实现但从未被任何代码调用。寄存器分配退化为简单的栈分配，导致生成的代码效率极低且不符合 x86_64 ABI 调用约定。

- **NATIVE-7-2**：`List`、`ADT`、`Tuple` 等复合类型在 `native_backend.py:734-798` 在栈上分配后，当函数返回时栈帧被销毁，产生悬空指针。任何返回这些类型的函数都会导致 use-after-free。

##### Cranelift 后端 (backend/cranelift_backend.py)

| 编号 | 严重度 | 位置 | 问题描述 |
|------|--------|------|----------|
| CRANE-7-1 | 🔴 严重 | `[cranelift_backend.py:137-201]` | SSA 值名完全不正确（生成的 .clif 无法通过验证） |
| CRANE-7-2 | 🔴 严重 | `[cranelift_backend.py]` | 之前发现的 .clif 语法错误、浮点指令错误、block 声明缺失仍存在 |

**详细分析**：

- **CRANE-7-1**：SSA 值名在 `cranelift_backend.py:137-201` 完全不正确，生成的 `.clif` 文件中引用了未定义的值名或使用了冲突的名称。Cranelift 的验证器会拒绝这些无效的 SSA IR，使得整个 Cranelift 后端无法产出可用的代码。

##### WASM 后端 (backend/wasm_backend.py)

| 编号 | 严重度 | 位置 | 问题描述 |
|------|--------|------|----------|
| WASM-7-1 | 🔴 严重 | `[wasm_backend.py:229-298]` | 栈式代码生成与 LIR SSA 模型不匹配（缺少操作数压栈） |

**详细分析**：

- **WASM-7-1**：WASM 后端在 `wasm_backend.py:229-298` 采用栈式代码生成策略，但 LIR 使用 SSA 模型。在将 SSA 操作转换为栈操作时，缺少了必要的操作数压栈步骤，导致 WASM 栈上操作数不匹配，生成的 `.wasm` 模块在加载时就会因验证失败而拒绝。

##### 编译管道 (backend/compiler_pipeline.py)

| 编号 | 严重度 | 位置 | 问题描述 |
|------|--------|------|----------|
| PIPE-7-1 | 🔴 严重 | `[compiler_pipeline.py:33-35]` | BACKEND_NATIVE 映射到 CraneliftBackend 而非 NativeCodeGen |

**详细分析**：

- **PIPE-7-1**：编译管道在 `compiler_pipeline.py:33-35` 将 `BACKEND_NATIVE` 选项映射到 `CraneliftBackend` 而非 `NativeCodeGen`。这意味着用户选择 "native" 后端时实际使用的是 Cranelift，而真正的 x86_64 Native 后端永远不会被编译管道调用。

---

#### IR 系统新发现

##### IR 节点 (ir/ir_nodes.py)

| 编号 | 严重度 | 位置 | 问题描述 |
|------|--------|------|----------|
| IR-7-1 | 🟡 中等 | `[ir/ir_nodes.py]` | 之前发现的问题仍存在，本轮新增 2 个中等问题 |

##### HIR Lowering (ir/hir_lowering.py)

| 编号 | 严重度 | 位置 | 问题描述 |
|------|--------|------|----------|
| HIR-7-1 | 🔴 严重 | `[ir/hir_lowering.py:147-152]` | Range 迭代被完全丢弃（返回不存在的标识符） |

**详细分析**：

- **HIR-7-1**：`Range` 表达式在 HIR lowering 阶段（`ir/hir_lowering.py:147-152`）被完全丢弃，lowering 代码返回了一个不存在的标识符。这意味着任何使用范围迭代（`for i in 0..10`）的代码在通过 IR 管道编译时会完全失效。

##### MIR Lowering (ir/mir_lowering.py)

| 编号 | 严重度 | 位置 | 问题描述 |
|------|--------|------|----------|
| MIR-7-1 | 🔴 严重 | `[ir/mir_lowering.py:351-384]` | Match 表达式在 MIR lowering 中完全丢弃模式匹配逻辑（所有 arm 无条件执行） |
| MIR-7-2 | 🟡 中等 | `[ir/mir_lowering.py:276-283]` | MIR 不是真正的 SSA（赋值直接覆盖 env） |
| MIR-7-3 | 🟡 中等 | `[ir/mir_lowering.py:309-349]` | Phi 节点不完整（分支未合并环境） |

**详细分析**：

- **MIR-7-1**：`Match` 表达式在 MIR lowering 中（`ir/mir_lowering.py:351-384`）完全丢弃了模式匹配逻辑。所有 match arm 被无条件顺序执行，而非根据模式条件选择执行。这是 IR 系统中最严重的语义错误，使得模式匹配这一核心语言特性完全失效。

- **MIR-7-2**：MIR 在 `ir/mir_lowering.py:276-283` 中赋值操作直接覆盖环境中的值，而非创建新的 SSA 版本。这使得 MIR 名为 SSA 实际上不是 SSA，违反了 IR 层次设计的核心假设。

- **MIR-7-3**：Phi 节点在 `ir/mir_lowering.py:309-349` 实现不完整。分支合并时没有正确收集各分支出口的环境，导致 phi 节点引用了不存在的值或错误的值版本。

##### LIR Lowering (ir/lir_lowering.py)

| 编号 | 严重度 | 位置 | 问题描述 |
|------|--------|------|----------|
| LIR-7-1 | 🟡 中等 | `[ir/lir_lowering.py]` | 之前发现的问题仍存在，本轮未发现新的严重问题 |

##### Pass 管理器 (ir/pass_manager.py)

| 编号 | 严重度 | 位置 | 问题描述 |
|------|--------|------|----------|
| PASS-7-1 | 🟡 中等 | `[ir/pass_manager.py]` | MIR 层 LICM 只处理 header 块（完全无效） |
| PASS-7-2 | 🟡 中等 | `[ir/pass_manager.py:475-479]` | CSE 的 MIR 层实现使用 MIRLoad 替换（语义错误） |

**详细分析**：

- **PASS-7-1**：MIR 层的循环不变量外提（LICM）优化只处理循环的 header 块，不遍历循环体中的基本块。这使得 LICM 实际上完全无效——循环不变量永远无法被识别和外提。

- **PASS-7-2**：公共子表达式消除（CSE）的 MIR 层实现在 `ir/pass_manager.py:475-479` 使用 `MIRLoad` 指令进行替换。`MIRLoad` 是内存加载指令，用其替换计算结果会导致语义错误——后续使用的是内存中的旧值而非计算得到的新值。

---

#### C 运行时 (runtime/nova_runtime.c) 新发现

| 编号 | 严重度 | 位置 | 问题描述 |
|------|--------|------|----------|
| RT-7-1 | 🔴 严重 | `[nova_runtime.c:99-103]` | 无循环引用 GC（引用计数模型无法回收循环引用） |
| RT-7-2 | 🔴 严重 | `[nova_runtime.c]` | 所有 *_release 函数普遍不递减子对象引用计数 |
| RT-7-3 | 🟡 中等 | `[nova_runtime.c:109-112]` | 全部使用 abort() 终止进程（无栈展开/恢复机制） |
| RT-7-4 | 🟡 中等 | `[nova_runtime.c:1664-1668]` | HTTP 临时文件 TOCTOU 竞态条件 |

**详细分析**：

- **RT-7-1**：运行时在 `nova_runtime.c:99-103` 使用引用计数进行内存管理，但没有任何循环引用检测或回收机制。当两个或多个对象形成循环引用时，引用计数永远无法归零，导致内存泄漏。对于函数式语言中常见的闭包和递归数据结构，循环引用是高频场景。

- **RT-7-2**：所有 `*_release` 函数普遍不递减子对象的引用计数。例如释放一个 List 时，不会递减其中每个元素的引用计数；释放一个 ADT 时，不会递减其字段的引用计数。这意味着引用计数模型形同虚设——只有顶层对象会被释放，子对象会持续泄漏。

- **RT-7-3**：所有错误处理路径在 `nova_runtime.c:109-112` 使用 `abort()` 直接终止进程，没有任何栈展开（stack unwinding）或恢复机制。这导致运行时错误无法被 Nova 程序捕获和处理，违背了 Nova 提供的错误处理语义。

- **RT-7-4**：HTTP 临时文件操作在 `nova_runtime.c:1664-1668` 存在 TOCTOU（Time-of-Check Time-of-Use）竞态条件。检查文件存在和使用文件之间有时间窗口，可能被攻击者利用。

---

#### 测试套件 (tests/) 新发现

| 编号 | 严重度 | 位置 | 问题描述 |
|------|--------|------|----------|
| TEST-7-1 | 🔴 严重 | `[tests/]` | VM/编译后端零运行时验证测试 |
| TEST-7-2 | 🔴 严重 | `[tests/]` | Evaluator vs VM 行为一致性零测试 |
| TEST-7-3 | 🟡 中等 | `[tests/]` | 大量测试使用 check_types=False（类型检查与求值集成未测试） |
| TEST-7-4 | 🟡 中等 | `[tests/]` | try/? 错误传播、Map 字面量、泛型函数、嵌套闭包等特性无测试 |

**详细分析**：

- **TEST-7-1**：整个测试套件中没有任何针对 VM 和编译后端的运行时验证测试。编译后端的正确性完全依赖于人工检查，没有自动化保障。这意味着后端的回归 bug 无法被及时发现。

- **TEST-7-2**：Evaluator（解释执行）和 VM（字节码执行）之间没有任何行为一致性测试。两条执行路径可能产生不同的结果（如之前发现的 `++` 运算符不一致），但没有任何测试能发现这类问题。

- **TEST-7-3**：大量测试用例使用 `check_types=False` 跳过类型检查。这意味着类型检查器与求值器/VM 的集成从未被测试过，类型检查错误可能在运行时才被发现。

- **TEST-7-4**：以下重要特性完全没有测试覆盖：`try`/`?` 错误传播、`Map` 字面量、泛型函数、嵌套闭包。这些特性要么实现有缺陷，要么完全未实现（如 Map 字面量），但测试套件无法提供任何反馈。

---

#### Tree-sitter (tree-sitter-nova/) 新发现

| 编号 | 严重度 | 位置 | 问题描述 |
|------|--------|------|----------|
| TS-7-1 | 🔴 严重 | `[grammar.js]` | `?` 操作符在 grammar.js 中完全缺失 |
| TS-7-2 | 🟡 中等 | `[grammar.js]` | `\|` 优先级在 grammar.js 和 parser.py 之间不一致 |
| TS-7-3 | 🟡 中等 | `[grammar.js]` | grammar.js 不支持数字字段访问 expr.0 |

**详细分析**：

- **TS-7-1**：`?` 错误传播操作符在 Tree-sitter 的 `grammar.js` 中完全缺失。这意味着使用 Tree-sitter 进行语法高亮、代码格式化等工具链功能时，`?` 操作符无法被正确识别和解析。

- **TS-7-2**：管道操作符 `|` 在 `grammar.js` 中的优先级定义与 `parser.py` 中的实现不一致。这会导致 Tree-sitter 解析的语法树与 Nova 编译器解析的 AST 结构不同，影响编辑器集成的准确性。

- **TS-7-3**：`grammar.js` 不支持数字字段访问语法（如 `expr.0` 访问元组的第一个元素）。Nova 语言可能支持此语法，但 Tree-sitter grammar 的缺失会导致编辑器无法正确处理此类代码。

---

### 第七轮审查总结

**新发现 vs 历史问题对比**：

| 类别 | 第六轮严重问题数 | 第七轮严重问题数 | 变化 |
|------|-----------------|-----------------|------|
| VM 虚拟机 | 4 | 8 | ↑ 新问题发现（CONTINUE/TRY_UNWRAP） |
| 编译器 | 5 | 6 | ↑ 新问题发现（闭包捕获/栈泄漏） |
| 求值器 | 2 | 5 | ↑ 新问题发现（truthy 语义/作用域链） |
| 类型检查器 | 4 | 5 | ↑ Occurs Check/HM 缺陷确认 |
| 前端（词法+语法） | 3 | 5 | ↑ MapExpr 解析/词法歧义 |
| 基础设施（错误+模块+环境） | 5 | 4 | ↓ 部分问题降级 |
| C 代码生成 | 3 | 5 | ↑ 闭包捕获/filter 参数反转 |
| 非C后端 | 12 | 10 | ↓ 部分问题合并 |
| IR 系统 | 10 | 9 | → Match/Range 问题确认 |
| 运行时+测试 | 6 | 9 | ↑ GC/引用计数缺陷确认 |
| **总计** | **54** | **71** | **↑ 深度审查发现更多问题** |

**说明**：第七轮严重问题数上升并非表示代码质量下降，而是本轮审查深入到了之前未覆盖的代码路径（如 CONTINUE 栈行为、闭包捕获机制、GC 引用计数细节），发现了更多隐藏的严重缺陷。部分第六轮的问题在本轮被重新分类或合并。

**最需要优先修复的 Top 10 问题（跨模块，更新）**：

1. **[ir/mir_lowering.py:351-384]** Match 表达式所有 arm 无条件执行 — IR 核心特性完全失效
2. **[type_checker.py]** 完全不是 Hindley-Milner — 类型安全基础不存在
3. **[vm.py:787-795]** while 循环 CONTINUE 终止循环 — 基本控制流崩溃
4. **[c_codegen.py:861-897]** C 后端闭包总是传 NULL — 闭包功能完全不可用
5. **[nova_runtime.c]** 所有 *_release 不递减子对象引用计数 — 内存持续泄漏
6. **[cranelift_backend.py:137-201]** SSA 值名不正确 — .clif 无法通过验证
7. **[ir/hir_lowering.py:147-152]** Range 迭代被完全丢弃 — for-in-range 不可用
8. **[evaluator.py:740-744]** if 使用 Python truthy 语义 — 类型安全被绕过
9. **[parser.py:768-834]** MapExpr 完全无法解析 — 承诺的功能不可用
10. **[native_backend.py:45-82]** 寄存器分配器完全未使用 — Native 后端效率极低

**后端可行性总评估（第七轮更新）**

| 后端 | 评估 | 说明 |
|------|------|------|
| C 代码生成 | **有限可用（更多限制）** | 闭包捕获 + filter/map 参数反转 + ADT 字段名错误，纯函数+基本ADT勉强可用 |
| Native (x86_64) | **不可用** | ret 冲突 + 栈不平衡 + ABI 违规 + 寄存器泄漏 + 悬空指针 + 寄存器分配器未使用 |
| Cranelift | **不可用** | .clif 语法错误 + 浮点用错指令 + block 声明缺失 + SSA 值名完全不正确 |
| WASM | **不可用** | 字符串编码 bug + block/loop 控制流错误 + 栈操作数不匹配 |
| x86_64 指令集 | **可用（作为库）** | 指令编码基本正确，有重复方法 |
| 编译管道 | **Demo 级别** | native 选项指向 cranelift，C 后端绕过 IR 管道 |
| IR 系统 | **Demo 级别** | 架构正确但 match/for/range/phi/SSA 全部致命缺陷 |
---

## 2026-07-15 第八轮综合审查报告

### 本轮审查说明

本轮审查采用三轮九个并行 Explore agent 对 Nova 全栈进行逐行审查：
- **第一轮**：VM 虚拟机 + 编译器 + 求值器
- **第二轮**：类型检查器 + 词法/语法分析器 + 错误处理/模块/环境
- **第三轮**：后端（C/Native/Cranelift/WASM）+ IR 系统 + C 运行时/测试/Tree-sitter

审查标准：生产级编译器/语言标准，主要参考 OCaml/Haskell/Elm/F# 等函数式语言最佳实践。

---

## 2026-07-15 VM 虚拟机 (vm.py) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐⭐ | 栈式字节码 + Python 驱动，设计简洁 |
| 可行性 | ⭐⭐⭐⭐ | 基本功能可工作，但多个严重问题未修复 |
| 正确性 | ⭐⭐⭐ | CONCAT 语义错误、闭包捕获整个帧、TRY_UNWRAP 静默通过 |
| 安全性 | ⭐⭐⭐ | 内置函数缺少类型检查、INDEX 无边界检查 |
| 一致性 | ⭐⭐⭐⭐ | Evaluator 和 VM 行为基本一致（除 ? 顶层处理） |
| 完整性 | ⭐⭐⭐⭐ | 大部分指令已实现，少数边缘情况未覆盖 |
| 工程质量 | ⭐⭐⭐ | 有详细注释，但存在死代码和启发式检测 |
| 性能 | ⭐⭐⭐ | 闭包捕获整个帧导致性能问题 |

### 发现的问题

#### 严重问题
- [vm.py:616] CONCAT 语义错误 — ++ 直接透传 Python a+b，int+int 变成加法而非报错 → ++ 运算符语义完全错误 → 强制要求操作数为 str 或 list
  - 追问：OCaml 的 ^ 字符串拼接允许隐式退化为整数加法？→ **不可接受**
- [vm.py:798] 闭包捕获整个帧 — CLOSURE 执行 dict(self.call_stack[-1].locals) 捕获全部局部变量 → 内存泄漏、封装破坏 → 编译器分析自由变量，仅捕获指定变量
  - 追问：OCaml 闭包捕获整个作用域 dict 拷贝？→ **不可接受**
- [vm.py:1185] TRY_UNWRAP 对非 ADT 值静默通过 — 栈顶非 NovaADTValue 时直接 return False，不解包也不报错 → 非 Option/Result 值被忽略 → 增加 else 分支报错
  - 追问：Haskell 对非预期类型执行 unwrap 静默忽略？→ **不可接受**
- [vm.py:468-499] _run_code RETURN 栈泄漏 — 顶层代码遇到 RETURN 不清理栈上返回值 → 全局栈无限增长 → 循环退出后 pop 残留返回值
  - 追问：任何生产级 VM 允许栈泄漏？→ **不可接受**

#### 中等问题
- [vm.py:925] FOR_ITER 闭区间语义 — current <= end 实现闭区间，与多数现代语言不一致 → 可能令人困惑 → 建议改为半开区间
- [vm.py:559] STORE_VAR 全局变量不检查 mutable — 局部已修，全局仍不检查 → 全局变量可被任意修改 → 全局变量记录 mutable 标志
- [vm.py:864] INDEX 无边界检查 — 越界时抛出原生 Python IndexError → 应转换为 RuntimeError_ → 用 try/except 包裹
- [vm.py:999-1052] MATCH_TEST_* 无栈空检查 — 直接访问 self.stack[-1]，栈空时抛 IndexError → 应统一检查 → 增加空栈判断
- [vm.py:232-310] 内置函数缺少类型检查 — str_to_int/head/tail/filter/map 等未检查参数类型 → 传入错误类型产生不可预期结果 → 每个内置函数增加 isinstance 检查
- [vm.py:593-608] DIV/MOD 除零检查不完整 — 浮点数除零未检查 → 抛出原生 ZeroDivisionError → 统一检查 right==0
- [vm.py:575-615] 算术/逻辑运算符缺少类型检查 — 直接透传 Python 运算符 → 不兼容类型抛 TypeError → 增加类型检查

#### 轻微问题
- [vm.py:1161] DUP 无栈空检查 — 栈空时抛 IndexError → 增加空栈判断
- [vm.py:436] _execute_function 死代码 — if opcode == Op.RETURN 永远不会执行 → 删除死代码

#### 原创性分析
- VM 采用栈式字节码设计，Op 类定义清晰，指令集覆盖基本函数式语义
- _for_iters / _while_loops / _list_index 用字典管理循环状态是 Nova 特色，但缺乏异常安全保护
- 启发式 BREAK/CONTINUE 检测（扫描 CONST_UNIT / LOOP_END）是权宜之计，非生产级方案

#### 已修复问题确认
- _pop 类型不一致 — 已修复，统一返回列表
- PRINT 未推 UNIT — 已修复
- STORE_VAR 局部 mutable 检查 — 已修复
- id() 做字典键 — 已修复，替换为 _loop_id 自增整数
- base_sp 计算和截断 — 基本已修复

---

## 2026-07-15 编译器 (compiler.py) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 自研字节码编译器，有独特设计 |
| 可行性 | ⭐⭐⭐ | 基本编译可工作，但模式匹配/闭包/模块有严重缺陷 |
| 正确性 | ⭐⭐⭐ | 模式绑定顺序反转、guard 失败销毁 subject、局部变量泄漏为全局 |
| 安全性 | ⭐⭐⭐ | 模块导入无命名空间隔离 |
| 一致性 | ⭐⭐⭐⭐ | 编译器假设的栈布局与 VM 基本匹配 |
| 完整性 | ⭐⭐⭐ | 部分 AST 节点编译处理不完整 |
| 工程质量 | ⭐⭐⭐ | 有遗留死代码，类型标注部分错误 |
| 性能 | ⭐⭐⭐ | 闭包不做自由变量分析 |

### 发现的问题

#### 严重问题
- [compiler.py:830-846] 模式绑定顺序被反转 — VM 的 MATCH_TEST_TUPLE/LIST/CONSTRUCTOR 用 reversed() 压栈，编译器按正序处理子模式 → match (1,2) { (a,b) => a-b } 得到 a=2, b=1 → 逆序遍历 pattern.elements / pattern.fields
  - 追问：Haskell GHC 模式绑定顺序反转？→ **不可接受**
- [compiler.py:717-736] match guard 失败时销毁 subject — guard_fail 跳转后栈上已无 subject，后续 arm 的 MATCH_TEST_* 会栈下溢 → 任何使用 guard 的 match 都会崩溃 → 每个 arm 开始前 DUP subject
  - 追问：任何生产级编译器允许 guard 失败导致崩溃？→ **不可接受**
- [compiler.py:488-496] for-inside-while 中的 break 被错误编译 — _while_end_stack 非空时 for 中的 break 被编译为 while break，不清理 _for_iters → 栈泄漏、迭代器状态错乱 → 引入统一循环栈记录循环类型
  - 追问：OCaml 的循环 break 目标错误？→ **不可接受**
- [vm.py:559] STORE_VAR 无法在函数内部创建局部变量 — 函数内 let x=1 编译为 STORE_VAR，VM 不在 frame.locals 中则回写 globals → 函数内部绑定泄漏为全局变量 → 引入 DECLARE_VAR 指令或预扫描局部变量
  - 追问：OCaml 函数内 let 绑定泄漏到全局？→ **不可接受**

#### 中等问题
- [compiler.py:317-368] 模块导入内联无命名空间隔离 — 直接内联所有导出声明，同名即覆盖 → 名称冲突无保护 → 引入模块前缀或命名空间
- [compiler.py:993-1001] while 循环返回值始终 Unit — 强制 POP 体结果后推 CONST_UNIT，与 AST 注释"最后一次迭代值作为返回值"矛盾 → 语义与文档不一致 → 保留体结果或按规范调整
- [compiler.py:398-401] 闭包不做自由变量分析 — CLOSURE 捕获全部当前帧局部变量 → 闭包体积无意义膨胀 → 编译器分析自由变量集合
- [compiler.py:392-397] 嵌套函数名冲突 — 子函数/lambda 平铺到主 functions 字典，同名静默覆盖 → 函数丢失 → 生成唯一名（如 <parent>_<fn>_N）
- [compiler.py:418-419] CharLiteral 编译为 CONST_STRING — 运行时无法区分 Char 与 String → 模式匹配歧义 → 引入 CONST_CHAR 指令或 NovaChar 包装
- [compiler.py:251-252] AUTO_CALL_MAIN 死代码 — HALT 后紧跟 AUTO_CALL_MAIN，永不执行 → 删除死代码
- [compiler.py:850-914] 遗留死代码 _compile_pattern_test/_compile_pattern_bindings — 65 行完全未被调用 → 删除死代码

#### 轻微问题
- [compiler.py:81,400,664] CLOSURE 操作数不匹配 — 注释写 3 个操作数，实际只使用 2 个 → 修正注释
- [compiler.py:75] Op.LOOP 死代码 — 已定义但从未生成 → 删除或实现

#### 原创性分析
- 自研字节码编译器，实现了从 AST 到栈式字节码的完整编译流程
- _compile_pattern_test_with_fail + _compile_pattern_extract_and_bind 的分离设计体现了模式匹配编译的决策树思想
- 列表推导式 filter 的内联编译设计巧妙，但 guard 失败后 subject 销毁是架构缺陷

#### 已修复问题确认
- PatternFloat/PatternChar/PatternTuple/PatternList 缺少模式测试 — 已修复，均生成 MATCH_TEST_* 指令
- match arm guard 被忽略 — 已修复，guard 已编译
- 列表推导式 filter_cond 被丢弃 — 已修复
- for 循环非空/空路径栈状态不一致 — 已修复
- && false 路径和 || true 路径栈值丢失 — 已修复，DUP + 条件跳转
- Block 中 BreakExpr/ContinueExpr 后多余 POP — 已修复

---

## 2026-07-15 求值器 (evaluator.py) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 直接 AST 求值，设计直观 |
| 可行性 | ⭐⭐⭐ | 基本功能可工作，环境泄漏和 ? 崩溃是致命缺陷 |
| 正确性 | ⭐⭐⭐ | Block/模式匹配环境切换无 finally、ADT __eq__ 不比较 type_name |
| 安全性 | ⭐⭐⭐ | filter 用 is True 严格比较、无类型检查 |
| 一致性 | ⭐⭐⭐ | 与 VM 在 ? 顶层处理、ADT __hash__ 等方面不一致 |
| 完整性 | ⭐⭐⭐⭐ | MapExpr 已添加，大部分节点已处理 |
| 工程质量 | ⭐⭐⭐ | 环境恢复缺乏 try/finally 是架构缺陷 |
| 性能 | ⭐⭐⭐ | 递归深度保护已添加 |

### 发现的问题

#### 严重问题
- [evaluator.py:751-761] Block env 不恢复 — self.env = child_env 后若 eval_expr 抛 ReturnSignal/BreakSignal/异常，self.env 永远指向 child_env → 调用栈中所有上层代码在错误环境中运行 → 用 try/finally 包裹
  - 追问：Haskell GHC 模式匹配失败时栈错乱？→ **不可接受**
- [evaluator.py:989-1006] 模式匹配环境切换无 finally — guard 和 body 两处环境切换均无 try/finally → 异常导致环境泄漏 → 两处均用 try/finally 包裹
  - 追问：任何生产级编译器允许环境泄漏？→ **不可接受**
- [evaluator.py:454] _call_fn 中 self.env = old_env 在 finally 外 — 若函数体抛出未捕获异常，finally 只恢复 _call_depth，self.env 永远停留在 child_env → 变量查找完全错乱 → 将 self.env = old_env 移入 finally
  - 追问：OCaml 的函数调用异常后环境不恢复？→ **不可接受**
- [evaluator.py:487-493,565] 顶层 ? ReturnSignal 未捕获 — eval_program 和 _eval_decl_body 无 ReturnSignal 捕获 → 顶层 ? 导致程序崩溃 → 顶层统一捕获 ReturnSignal
  - 追问：Rust 顶层 ? 导致程序崩溃？→ **不可接受**
- [evaluator.py:75-78] ADT __eq__ 不比较 type_name — type Foo=Bar(Int) 和 type Baz=Bar(Int) 的 Bar(1)==Bar(1) 为 True → 同名变体跨 ADT 类型错误相等 → 增加 type_name 比较
  - 追问：Haskell 的 Maybe Int 和 Maybe String 被当作同一类型？→ **不可接受**

#### 中等问题
- [evaluator.py:205] filter 用 is True 严格比较 — 谓词返回 truthy 非 True 值被过滤掉 → 语义错误 → 去掉 is True 或要求返回 bool
- [evaluator.py:712-720] TryExpr ? 穿透多层调用帧 — 在非函数上下文中使用 ? 导致 ReturnSignal 无捕获者崩溃 → VM 通过 return_flag 优雅处理 → 在 Block/ForExpr/WhileExpr 中增加 ReturnSignal 透传
- [evaluator.py:869-874] 整数除法使用 Python // — -3//2 得 -2，向负无穷取整 → 语义可能与预期不符 → 若要求向零截断用 int(left/right)
- [evaluator.py:738-744] if 使用 Python truthy 语义 — 0、""、[] 均为 falsy → 若 Nova 语义要求严格 Bool 则不正确 → 增加类型检查
- [evaluator.py:877-878] ++ 不做类型检查 — Int + String 会 TypeError → 限制 ++ 仅限 String 类型
- [evaluator.py:677-681] String/Char 运行时无区分 — 均为 Python str → 模式匹配歧义 → 引入 NovaChar 包装类

#### 轻微问题
- [evaluator.py:59-79] NovaADTValue 缺少 __hash__ — VM 版本有 __hash__，evaluator 缺失 → 不可哈希，行为不一致 → 添加 __hash__
- [evaluator.py:869-874] BinaryOp / float 除零不检查 — 浮点数除零抛出原生 ZeroDivisionError → 统一检查
- [evaluator.py:214-224] _builtin_head/tail 对非列表输入无类型检查 — 传入 int 时行为不可预期 → 增加 isinstance 检查

#### 原创性分析
- 直接 AST 求值器是教学/原型编译器的经典设计，简洁直观
- 使用异常（BreakSignal/ContinueSignal/ReturnSignal）实现控制流是 Python 宿主语言的合理选择，但缺少 finally 保护是架构缺陷
- NovaADTValue 使用 Python dataclass 简化实现，但未定义 __hash__ 导致与 VM 行为不一致

#### Evaluator vs VM 对比
| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| ? 在顶层处理 | 抛出未捕获 ReturnSignal，崩溃 | return_flag 机制，优雅结束 | ❌ |
| NovaADTValue.__hash__ | 缺失（不可哈希） | 已定义 | ❌ |
| filter 严格比较 | is True | is True | ✅（但都是 bug） |
| 整数除法 // | 使用 // | 使用 // | ✅ |
| if truthy 语义 | if cond: | not cond / cond | ✅ |
| 递归深度保护 | _call_depth 计数 | call_stack 长度检查 | ✅ |

#### 已修复问题确认
- MapExpr 完全缺失 — 已修复
- Pattern guard 守卫条件 — 部分修复（功能实现但环境恢复无 finally）
- UNIT_VALUE bool 语义 — 已修复，__bool__ 返回 False
- ? 操作符不解包 Some/Ok — 已修复
- &&/|| 返回硬编码 Python bool — 已修复
- 递归深度保护 — 已修复
- head/tail 返回 Option 缺少 field_names — 已修复
- break/continue 缺少函数内防护 — 已修复

---

## 2026-07-15 类型检查器 (type_checker.py) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 基于局部替换的兼容性检查器，非真正 HM |
| 可行性 | ⭐⭐⭐ | 基础类型检查可工作，但类型安全无法保证 |
| 正确性 | ⭐⭐ | TypeVar 被视为通配符，let 多态缺失 |
| 安全性 | ⭐⭐ | 类型系统本质上不提供可靠保障 |
| 一致性 | ⭐⭐⭐ | 与 Evaluator/VM 行为无直接冲突 |
| 完整性 | ⭐⭐⭐ | MapExpr/PipeExpr 等缺失或过于宽松 |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰，但核心算法未实现 |
| 性能 | ⭐⭐⭐ | 无性能瓶颈，但缺少 occurs check 可能无限循环 |

### 发现的问题

#### 严重问题
- [type_checker.py:1114-1135,1240-1268] 缺少 Unification 算法 — 只有单向 _collect_type_bindings + _substitute_type_vars，actual 为 TypeVar 而 expected 为 concrete type 时不会建立绑定 → 类型推断不完整 → 实现完整的 unify(ty1, ty2) 双向绑定
  - 追问：OCaml 缺少双向 unification？→ **不可接受**
- [type_checker.py:744-754,519-530] 缺少 Generalize/Instantiate（let 多态） — let 绑定直接存入环境，未对自由类型变量泛化 → let id = fun x -> x in id 1 + id "a" 仅在 + 处报错，let _ = id 1 in id "a" 不报错 → 实现 generalize/instantiate
  - 追问：OCaml 的 let 多态没有正确实现？→ **不可接受**
- [type_checker.py:1244] 任意两个 TypeVar 被视为兼容 — isinstance(a, TypeVar) or isinstance(b, TypeVar) 直接返回 True → T1 与 T2 兼容、Int 与 T 兼容，完全破坏类型安全 → 删除该行，基于 substitution 绑定判断
  - 追问：Haskell 的 Maybe Int 和 Maybe String 被当作同一类型？→ **不可接受**
- [type_checker.py:全局] 无 occurs check — let x = x 或递归类型定义可能导致无限循环或错误绑定 → 在 unify 中实现 occurs_in(var, type) 检查
  - 追问：任何生产级 HM 编译器缺少 occurs check？→ **不可接受**

#### 中等问题
- [type_checker.py:883,911] ForExpr/ListComprehension 不推断迭代变量类型 — 迭代变量仍使用固定 TypeVar("for_elem")，未从 iterable 类型推断 → for x in [1,2] do x ++ "a" 不会报错 → 检查 iterable 类型并绑定对应元素类型
- [type_checker.py:859-867] TryExpr 对非 Result/Option 静默通过 — 对非 Result/Option 类型直接返回 inner_ty，不报告错误 → 类型安全被绕过 → 增加 else 分支报错
- [type_checker.py:1040,1046,1053,1061,1083,1088] 二元操作错误后返回 INT_T/STRING_T/BOOL_T 而非 ERROR_TYPE — 类型错误后返回具体类型，导致级联错误 → 所有错误分支改为 return ERROR_TYPE
- [type_checker.py:926] MapExpr 类型检查缺失 — MapExpr 在 import 中引入但 check_expr 无对应分支，落入 else 报"未知的表达式类型" → 添加 MapExpr 分支返回 MapType
- [type_checker.py:720-735] PipeExpr 类型检查过于宽松 — 若 right_ty 不是 FnType 直接返回 right_ty 不报错；不检查参数数量；返回类型未替换类型变量 → 将 PipeExpr 语义等价转换为 FnCall 进行类型检查
- [type_checker.py:712-715] FnCall 对 TypeVar callee 的 duck typing 完全放行 — 任何类型变量都可以被当作函数调用 → 高阶函数类型错误完全静默 → TypeVar callee 应被约束为函数类型
- [type_checker.py:1056-1061] ==, != 不检查操作数类型兼容性 — 直接返回 BOOL_T，1 == "a" 不会报错 → 增加 _types_compatible 检查
- [type_checker.py:756-759] MutBinding 缺少类型标注校验 — mut x: Int = "a" 不会报类型错误 → 添加与 LetBinding 相同的标注类型校验

#### 轻微问题
- [type_checker.py:371] pi 被错误地定义为函数类型 — pi 是常量但签名为 () -> Float → 若语言支持值绑定应定义为 FLOAT_T
- [type_checker.py:415] 用户定义类型可能覆盖内置类型 — 注册 ADT 类型时未检查是否为保留内置类型名 → 注册前检查保留名

#### 原创性分析
- 类型检查器架构基于两遍扫描（_collect_decl + _check_decl_body），结构清晰
- ADT 类型注册和 PatternConstructor 类型参数替换体现了函数式语言类型系统的基本思路
- 但核心类型推断引擎仍是单向替换而非完整的 Hindley-Milner 算法，这是架构级缺陷

#### 已修复问题确认
- PatternConstructor 不替换类型参数 — 已修复，创建 type_param_map 并替换
- Lambda 多参数共享同一 TypeVar — 已修复，每个参数使用带索引的 TypeVar
- 未知类型名静默创建 PrimType — 已修复，报告错误并返回 ERROR_TYPE
- check_decl 死代码 — 已修复（已删除）
- Err 内置函数返回类型引用错误 TypeVar — 结构已修复，但受限于系统缺陷

#### 关键测试验证
let id = fun x -> x in id 1 + id "a" — **会报错**，但原因错误（在 + 处而非 id "a" 处）。根本问题：缺少 let 多态和全局 substitution 跟踪。
等价反例 let id = fun x -> x in let _ = id 1 in id "a" — **不会报错**，成功通过类型检查，证明类型系统已破。

---

## 2026-07-15 词法/语法分析器 (lexer.py + parser.py) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 手写递归下降解析器，符合函数式语言风格 |
| 可行性 | ⭐⭐⭐ | 基本解析可工作，但 MapExpr 完全缺失、顶层分号解析失败 |
| 正确性 | ⭐⭐⭐ | 链式比较未禁止、负数模式 Span 错误、Block Span 不完整 |
| 安全性 | ⭐⭐⭐⭐ | 无安全风险 |
| 一致性 | ⭐⭐⭐⭐ | lexer 和 parser 基本匹配 |
| 完整性 | ⭐⭐⭐ | MapExpr/:: cons/FAT_ARROW 等缺失或死代码 |
| 工程质量 | ⭐⭐⭐ | Span 系统几乎不可用，死 token 和死代码未清理 |
| 性能 | ⭐⭐⭐⭐ | 无性能问题 |

### 发现的问题

#### 严重问题
- [parser.py:769-834] MapExpr 完全无法解析 — LBRACE 只映射到 _parse_block()，{ "key" => value } 永远被解析为代码块 → 核心数据结构完全不可用 → 在 LBRACE 分支中先窥视内部判断是 Block 还是 Map
  - 追问：任何生产级编译器缺少核心数据结构解析？→ **不可接受**
- [parser.py:98-122,367-370] 顶层表达式后的分号导致解析失败 — _parse_expression_statement 不消费尾随分号 → 顶层写 1 + 2; 时报错 → 消费可选的尾随分号
  - 追问：GCC 顶层分号导致解析失败？→ **不可接受**
- [parser.py:全文] 几乎所有复合 AST 节点的 Span 都不完整 — 没有合并 span 的工具函数，BinaryOp 只覆盖 +，FnCall 只覆盖 )，IfExpr 只覆盖 if → 错误报告无法精确定位 → 实现 Span.merge 并在构造复合节点时合并首尾 token
  - 追问：Rustc 错误位置不准确？→ **不可接受**

#### 中等问题
- [parser.py:672-678] 链式比较未被禁止 — _parse_comparison_expr 使用 while 循环，允许 a < b < c → 除非语言明确定义链式比较语义否则应禁止 → 将 while 改为 if
- [parser.py:580-588] 负数模式 Span 不覆盖数字部分 — self._span(tok) 的 tok 是 MINUS token，只覆盖 - 字符 → Span 对错误报告至关重要 → 构造从 MINUS 到 INT/FLOAT 的合并 Span
- [parser.py:378-414] Block Span 不包含结束位置 — span=self._span(tok) 只覆盖 {，} 未合并 → Block 错误定位不准 → 获取 } token 的 span 并合并
- [lexer.py:88,91] PIPE_VARIANT 和 UNIT 死 token — lexer 从不生成，parser 有死分支 → 维护负担 → 删除死 token 和死分支
- [lexer.py:72] FAT_ARROW (=>) 在 parser 中未使用 — lexer 识别但 parser 不消费 → 死 token → 实现 MapExpr 时使用或移除
- [parser.py:464-466,892-894] <- 歧义（LT+MINUS 拼接）— lexer 无专门 <- token，parser 手动拼接 → for i < -start..end 与 for i <-start..end 产生相同 token 序列 → lexer 增加 LEFT_ARROW token
- [lexer.py:153,253-267,454-458] lexer 错误处理机制混乱 — self.errors 存储字符串消息而非 LexerError 对象，tokenize() 不返回错误 → parser 无法感知 lexer 错误 → 返回 (List[Token], List[LexerError])

#### 轻微问题
- [parser.py:485-490] while 条件贪婪消费循环体 — 当前代码无明显此问题，while {cond} {body} 中第一个 block 被当作条件是显式语法设计
- [parser.py:460-483] step 表达式冗余存储 — for_expr.iterable[3] 和 for_expr.step 指向同一数据 → 移除元组中第4个元素
- [parser.py:880-912] 列表推导式不支持 step — 硬编码 iterable = ("range", start_expr, end_expr, None) → 统一语法支持 step

#### 原创性分析
- 手写递归下降解析器是编译器教学的经典选择，代码可读性好
- 管道操作符 |> 的优先级设计和编译处理体现了函数式语言特色
- 模式匹配语法支持 guard 条件，与 Haskell/OCaml 风格一致

#### 已修复问题确认
- 非法字符直接 raise 终止词法分析 — 已修复，跳过非法字符继续
- match arm 不支持 guard — 已修复
- PatternChar 未处理 — 已修复
- while 条件贪婪消费循环体 — 已修复/无此问题
- step 表达式被静默丢弃 — 已修复（保留但冗余）

---

## 2026-07-15 错误处理/模块/环境 (errors.py + modules.py + environment.py) 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 标准错误报告框架，无特别创新 |
| 可行性 | ⭐⭐⭐ | 基本功能可工作，但结构化信息丢失 |
| 正确性 | ⭐⭐⭐ | 异常不携带 span，运行时错误无位置信息 |
| 安全性 | ⭐⭐⭐⭐ | 无安全漏洞 |
| 一致性 | ⭐⭐⭐ | source vs source_code 命名不一致 |
| 完整性 | ⭐⭐⭐ | ErrorCollector 未被 evaluator 使用 |
| 工程质量 | ⭐⭐⭐ | 错误报告未达生产级 |
| 性能 | ⭐⭐⭐⭐ | 循环导入检测用 List 而非 Set |

### 发现的问题

#### 严重问题
- [errors.py:405-411] raise_all() 丢失 severity/span 结构化信息 — 将后续错误 format() 为字符串后作为 NOTE 附加，WARNING 等严重级别丢失 → 多错误场景下无法程序化分析 → add_note 支持 RelatedNote 对象或自定义 MultiError
  - 追问：Rust 编译器错误信息缺少源码上下文？→ **不可接受**
- [errors.py:68-76] RelatedNote 不携带自己的 source_code — 相关注释的源码上下文使用主错误的 source_code，跨文件注释显示错误上下文 → 增加 source_code 字段
  - 追问：GCC 跨文件错误注释显示错误上下文？→ **不可接受**
- [modules.py:124-130] 相对路径只搜索 search_paths[0] — 相对导入仍只解析 search_paths[0]，若当前文件目录非首位则解析错误 → 相对路径应基于 os.path.dirname(current_file) 解析
  - 追问：Python 相对导入基于错误目录？→ **不可接受**
- [modules.py:328-337] 导入时同名绑定被静默覆盖 — define() 直接覆盖，两个模块导出同名符号时后者静默胜出 → 隐蔽 bug → 导入前检查目标环境是否已有同名绑定
  - 追问：Rust 同名导入静默覆盖？→ **不可接受**
- [errors.py:320-327] RuntimeError_ 不携带 source_code/span — 类定义已接受参数但所有调用点均未传递 → 运行时错误全部没有源码位置 → 要求 RuntimeError_ 构造必须传入 span
  - 追问：任何生产级编译器运行时错误无位置信息？→ **不可接受**

#### 中等问题
- [errors.py:334-352] BreakSignal/ContinueSignal/ReturnSignal 不携带 span — 误用信号时只能抛出无位置信息的 RuntimeError_ → 增加 span 参数
- [errors.py:全局] ErrorCollector 未被 evaluator 使用 — evaluator 完全未集成 ErrorCollector → 运行时多个错误只能逐个抛出 → Evaluator 持有 ErrorCollector 统一报告
- [modules.py:276-291] 导出收集是空壳 — elif 分支 pass，若支持 pub fn 等隐式导出则未实现 → 明确设计后删除或补全
- [modules.py:184-190,345-350] 模块缓存没有失效机制 — 无基于 mtime 的自动失效 → 文件编辑后返回旧缓存 → 缓存时记录 mtime 并检查
- [environment.py:34-61] 作用域链递归查找有栈溢出风险 — lookup/lookup_binding/assign 三处仍为递归 → 深层嵌套可能触及 Python 递归限制 → 改为 while 迭代遍历
- [modules.py:90-105] ModuleResolver 修改传入的 search_paths 列表 — 直接修改调用者传入的列表产生副作用 → 多个 resolver 互相污染 → self.search_paths = list(search_paths or [])
- [environment.py:30-32] Environment.define() 静默覆盖同作用域绑定 — 同一作用域内重复定义直接覆盖 → 增加检查并报告错误

#### 轻微问题
- [errors.py:85-92] source vs source_code 命名不一致 — 构造参数 source，实例属性 source_code → 统一命名
- [modules.py:187,216-218] 循环导入检测使用 List 而非 Set — O(n) 成员检测 → 增加 Set 做 O(1) 检测
- [errors.py:413-420] ErrorCollector.format_all() 丢失时间顺序 — warning 追加到 error 之后 → 维护统一列表按产生顺序排列

#### 原创性分析
- 错误报告框架采用分级结构（NovaError -> RelatedNote），设计合理
- 模块系统采用路径搜索 + 缓存机制，符合小型语言的设计需求
- 但错误信息的结构化处理和源码上下文映射未达生产级标准

#### 已修复问题确认
- 模块加载时未传递 module_manager — 已修复
- 导入逻辑在两处独立实现（重复）— 已修复，集中到 load_module()
- assign 对未定义变量抛 Python 原生异常 — 已修复，改为 RuntimeError_
- lookup/lookup_binding 抛 NameError — 已修复，改为 RuntimeError_

---

## 2026-07-15 后端代码生成审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 多后端架构（C/Native/Cranelift/WASM）有雄心 |
| 可行性 | ⭐⭐ | 所有后端均无法实际编译运行 |
| 正确性 | ⭐⭐ | C 后端 ADT 语法无效、Native 浮点完全错误、WASM Branch 逻辑反 |
| 安全性 | ⭐⭐⭐ | C 后端字符串转义不完整 |
| 一致性 | ⭐⭐⭐ | 各后端实现程度不一 |
| 完整性 | ⭐⭐ | 大量 LIR 指令未实现或错误实现 |
| 工程质量 | ⭐⭐⭐ | 架构合理但实现粗糙 |
| 性能 | ⭐⭐ | Native 后端寄存器永不释放 |

### 发现的问题

#### 严重问题（C 后端）
- [c_codegen.py:897] 闭包不捕获自由变量 — nova_closure_new 传 NULL, 0 → 闭包功能完全不可用 → 分析 expr.body 自由变量并生成环境结构体
  - 追问：OCaml 的 native 编译器闭包传 NULL？→ **不可接受**
- [c_codegen.py:584] TryExpr variant_tag 字段名不匹配 — 访问 ->variant_tag，但 struct 字段名为 tag → 访问错误内存 → 统一为 tag
- [c_codegen.py:783,787] filter/map 参数顺序反转 — nova_list_filter({args_c[1]}, {args_c[0]}) 把 predicate 和 list 颠倒 → 运行时行为错误 → 修正参数顺序
- [c_codegen.py:841-858] ADT 构造器生成无效 C 语法 — ({ .tag = ..., .field = ... }) 缺少类型前缀 → C 编译失败 → 生成 (NovaADT_{name}){{ .tag = ..., }}
- [c_codegen.py:210 vs 855 vs 695] ADT 字段命名不一致 — _collect_type_def 生成 {variant}_{fname}，构造器使用 {variant}__field{i} → 字段无法对应 → 统一命名

#### 严重问题（Native 后端）
- [native_backend.py:421-485] 浮点 BinOp 走整数路径 — 所有 + - * / == < 等均用整数指令，未区分 FLOAT_TYPE → 浮点运算完全错误 → 检查类型并走 SSE2 路径（addsd/ucomisd 等）
- [native_backend.py:202-211] 寄存器池永不释放 — _alloc_vreg 取出后从不归还 → 长函数耗尽所有寄存器 → 实现寄存器释放或接入 LinearScanAllocator
- [native_backend.py:388] callee-saved 寄存器被放入可用池 — free_gprs 包含 RBX, R12-R15，调用约定冲突 → 只放 caller-saved（RAX, RCX, RDX, RSI, RDI, R8-R11）
- [native_backend.py:745,769,788] 栈上分配 List/Tuple/ADT 生存期错误 — sub_rsp_imm 在栈上分配，函数返回后指针悬空 → 调用 malloc/nova_alloc
- [native_backend.py:834] _start 入口点参数加载错误 — mov RDI, [RSP+8] 加载 argv[0]，但 _start 时 RSP 指向 argc → 改为 mov RDI, [RSP] 和 mov RSI, [RSP+8]

#### 严重问题（Cranelift 后端）
- [cranelift_backend.py:167-168] Branch 硬编码 block_true/block_false — 应使用 instr.true_label 和 instr.false_label → 非默认命名分支跳转到不存在的 block → 使用实际 label
- [cranelift_backend.py:188] Index 忽略源操作数 — load i64, v0 + 0 完全忽略 instr.src_locs → 使用实际基址和索引寄存器

#### 严重问题（WASM 后端）
- [wasm_backend.py:161,371] 字符串 NUL 终止符编码错误 — b"\x00" 是 2 字节（\ + NUL）而非 1 字节 NUL → 改为 b" "
- [wasm_backend.py:273-276] BuildADT 不存储 tag 和字段值 — 仅 call nova_alloc 分配内存，未发射 i32.store 写入 → ADT 值未初始化 → 依次写入 tag 和各字段
- [wasm_backend.py:260-263] Branch 丢失 true 分支/逻辑反 — 生成 (br_if block_false)，条件为真时跳转到 false block → 逻辑反了且缺少 true 分支 → 修正为 (if (then (br block_true)) (else (br block_false)))

#### 中等问题
- [compiler_pipeline.py:33-35] BACKEND_NATIVE 映射到 Cranelift — 真正的 NativeCodeGen 从未被管道使用 → 新增 BACKEND_CRANELIFT 或修正映射
- [c_codegen.py:397,991,1067] 列表元素类型硬编码 int64_t — 应从列表类型推导元素类型
- [c_codegen.py:623] IfExpr 无 else 返回 "0" — 类型可能不匹配 → 根据上下文推断零值
- [cranelift_backend.py:250] 参数类型硬编码 i64 — 浮点参数被错误传递 → 使用 _nova_type_to_clif 转换
- [cranelift_backend.py:234] BinOp 无浮点路径 — 总是取 int_op_map → 检查类型选择 float_op_map
- [x86_64.py:451,467] je_rel32 重复定义 — 两次完全相同的定义 → 删除其中一个
- [x86_64.py:81,125,137,155] 部分指令缺少 REX 扩展位 — reg >= 8（R8-R15）时生成错误机器码 → 处理 REX 扩展

#### 原创性分析
- 多后端架构（C/Native/Cranelift/WASM）体现了 Nova 的雄心，但实现质量参差不齐
- x86_64 编码器作为独立模块设计良好，指令编码基本正确
- C 后端绕过 IR 管道直接编译 AST，是务实的选择但导致与 IR 优化脱节

#### 后端可行性总评估
| 后端 | 能否实际编译运行 | 评估 |
|------|------------------|------|
| C 后端 | **不能** | ADT 语法无效、闭包无环境、Try 字段名错误、filter/map 参数反、字段命名不一致 |
| Native 后端 | **不能** | 浮点运算完全错误、寄存器永不释放、栈上分配生存期错误、入口参数错误 |
| Cranelift 后端 | **不能** | Branch 硬编码 block 名会导致引用不存在的 label；Index 忽略操作数；Call 参数全为 i64 |
| WASM 后端 | **不能** | 字符串偏移错误、ADT 不写字段、Branch 逻辑反。生成的 WAT 语义错误 |

---

## 2026-07-15 C 运行时 + 测试 + Tree-sitter 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 标准 C 运行时，引用计数内存管理 |
| 可行性 | ⭐⭐⭐ | 基本功能可工作，但内存管理有重大缺陷 |
| 正确性 | ⭐⭐⭐ | GC 是空壳、ADT release 不递减字段、closure 不 retain |
| 安全性 | ⭐⭐ | nova_system() 仍存在命令注入风险、json_buf_grow 整数溢出 |
| 一致性 | ⭐⭐⭐ | C 运行时与 Python 端数据结构基本一致 |
| 完整性 | ⭐⭐⭐ | 缺少 Evaluator-VM 一致性测试、后端无端到端测试 |
| 工程质量 | ⭐⭐⭐ | 代码注释详细但安全边界检查不足 |
| 性能 | ⭐⭐⭐ | 引用计数简单高效但无法处理循环引用 |

### 发现的问题

#### 严重问题（C 运行时）
- [nova_runtime.c:99] GC 是空壳 — 仅返回净分配数，不执行任何循环引用检测 → 循环引用导致确定性内存泄漏 → 实现标记-清除或分代 GC
  - 追问：任何生产级语言的 GC 是空壳？→ **不可接受**
- [nova_runtime.c:516-540] nova_map_put 更新时类型混淆 — NovaMap 的 value 是 void*，强制转换为 NovaValue* 调用 release → 非 NovaValue* 的 value 读取错误偏移内存 → Map 使用带类型标签的泛型容器
- [nova_runtime.c:363-368] nova_list_set 不释放旧元素 — 替换前未对旧元素调用 nova_value_release → 内存泄漏 → 替换前 release 旧元素
- [nova_runtime.c:749-756] nova_adt_release 不递减字段引用计数 — 释放 ADT 时未遍历 fields 数组对每个字段调用 release → 嵌套数据结构级联泄漏 → 遍历字段并 release
- [nova_runtime.c:762-776] nova_closure_new 浅拷贝 captured 不 retain — 仅浅拷贝未 nova_value_retain → 闭包捕获的变量可能在外部被提前释放 → 对每个 captured 调用 retain

#### 中等问题（C 运行时）
- [nova_runtime.c:270-298] nova_string_replace 整数溢出 — count * (new_s->length - old_s->length) 可能 int64_t 溢出 → 添加溢出检查
- [nova_runtime.c:1165-1189] JSON 解析不验证 token 匹配 — json_parse_true/false/null 直接按固定长度跳过，不验证实际字符 → 输入 txxx 被错误解析为 true → 使用 strncmp 验证
- [nova_runtime.c:1240-1256] JSON unicode 不处理 surrogate pairs — \\uXXXX 直接按单个码点处理 → 无法正确解析 Emoji → 实现 surrogate pair 检测与组合
- [nova_runtime.c:845-855] read_file 失败返回空字符串 — 无法区分空文件与打开失败 → 返回 NULL 或采用 Result 类型语义
- [nova_runtime.c:1513-1516] nova_system() 仍存在命令注入 — system() 调用本身是危险 API → 彻底移除或限制为白名单命令
- [nova_runtime.c:1316-1321] json_buf_grow 整数溢出 — buf->cap *= 2 可能溢出为负数 → 添加上限检查和溢出保护

#### 严重问题（测试）
- [tests/test_nova.py] 无 Evaluator-VM 一致性测试 — 独立测试但无任何测试将同一段代码同时在 Evaluator 和 VM 下运行并比较结果 → 多后端语言必须保证语义一致 → 添加参数化测试框架
  - 追问：GHC 缺少核心语言特性的一致性测试？→ **不可接受**
- [tests/test_backends.py, test_c_codegen.py, test_native_backend.py] 所有后端无端到端运行验证 — 只检查生成的代码字符串或字节，不编译运行 → 后端测试必须验证编译-运行-结果正确 → 调用 gcc 编译产物并运行

#### 中等问题（测试）
- [tests/*.py] 浮点数边界情况测试缺失 — 无 .5、1.、科学计数法测试 → 补充边界测试

#### 严重问题（Tree-sitter）
- [tree-sitter-nova/grammar.js] TryExpr（? 运算符）缺失 — parser.py 支持但 grammar.js 无对应规则 → Tree-sitter 无法识别 ? 操作符 → 添加 try_expr 规则
  - 追问：任何生产级语言的 Tree-sitter grammar 缺少核心操作符？→ **不可接受**
- [tree-sitter-nova/grammar.js] 缺少泛型类型参数 — parser.py 支持 Option[Int] 但 grammar.js 无通用泛型语法 → 添加 generic_type 规则
  - 追问：任何生产级语言的语法高亮不支持泛型？→ **不可接受**

#### 中等问题（Tree-sitter）
- [tree-sitter-nova/grammar.js:282] float_literal 正则不匹配 .5、1.、科学计数法 — /\d+\.\d+/ 过于严格 → 统一为正则 /\d+\.\d*|\.\d+|\d+([eE][+-]?\d+|\.\d*[eE][+-]?\d+)/

#### 原创性分析
- C 运行时采用引用计数内存管理，配合 Python 端的 GC 空壳注释，设计思路清晰
- 运行时提供丰富的内置函数（HTTP、JSON、文件 IO、数学函数），体现了 Nova 作为实用语言的定位
- 但引用计数的实现存在多处重大缺陷，导致内存泄漏和潜在的 UAF

---

### 第八轮审查总结

**新发现 vs 历史问题对比**：

| 类别 | 第七轮严重问题数 | 第八轮严重问题数 | 变化 |
|------|-----------------|-----------------|------|
| VM 虚拟机 | 8 | 4 | ↓ 部分修复确认 |
| 编译器 | 6 | 4 | ↓ 历史问题部分修复，新增模式绑定反转/guard 崩溃 |
| 求值器 | 5 | 5 | → 环境问题未修复，新增 _call_fn finally 外 |
| 类型检查器 | 5 | 4 | → HM 核心缺陷全部未修复 |
| 前端（词法+语法） | 5 | 3 | ↓ 部分问题已修复 |
| 基础设施（错误+模块+环境） | 4 | 5 | ↑ 新发现模块系统问题 |
| C 代码生成 | 5 | 6 | ↑ 新增 ADT 语法无效/字段命名不一致 |
| 非C后端 | 10 | 8 | ↓ 部分问题合并 |
| IR 系统 | 9 | 9 | → 核心缺陷全部未修复 |
| 运行时+测试 | 9 | 6 | ↓ HTTP 注入已修复 |

**本轮最关键的 Top 10 新发现/未修复问题（跨模块）**：

1. **[compiler.py:830-846]** 模式绑定顺序被反转 — match (1,2) { (a,b) => a-b } 得到 a=2, b=1
2. **[compiler.py:717-736]** match guard 失败时销毁 subject — 任何使用 guard 的 match 都会崩溃
3. **[evaluator.py:454]** _call_fn 中 self.env = old_env 在 finally 外 — 异常导致环境永久泄漏
4. **[type_checker.py:1244]** 任意两个 TypeVar 被视为兼容 — 完全破坏类型安全
5. **[c_codegen.py:841-858]** C 后端 ADT 构造器生成无效 C 语法 — 无法编译
6. **[native_backend.py:202-211]** Native 后端寄存器池永不释放 — 长函数耗尽寄存器
7. **[native_backend.py:745,769,788]** Native 后端栈上分配生存期错误 — 函数返回后指针悬空
8. **[lir_lowering.py:219-223]** LIRBranch 标签未设 — 后端完全无法生成正确分支
9. **[mir_lowering.py:351-384]** Match 模式信息完全丢失 — 所有 arm 无条件执行
10. **[nova_runtime.c:762-776]** nova_closure_new 浅拷贝 captured 不 retain — UAF 风险

**后端可行性总评估（第八轮更新）**

| 后端 | 评估 | 说明 |
|------|------|------|
| C 代码生成 | **不可用** | ADT 语法无效 + 闭包 NULL + filter/map 参数反 + 字段命名不一致 + Try 字段名错误 |
| Native (x86_64) | **不可用** | 浮点完全错误 + 寄存器永不释放 + 栈分配悬空 + callee-saved 冲突 + 入口参数错误 |
| Cranelift | **不可用** | Branch 硬编码 + Index 忽略操作数 + Call 参数全 i64 |
| WASM | **不可用** | 字符串编码 bug + ADT 不写字段 + Branch 逻辑反 + 字符串偏移错位 |
| x86_64 指令集 | **可用（作为库）** | 指令编码基本正确，有重复方法和 REX 缺失 |
| 编译管道 | **Demo 级别** | native 选项指向 cranelift，C 后端绕过 IR 管道 |
| IR 系统 | **Demo 级别** | 架构正确但 SSA/match/for/range/phi/闭包全部致命缺陷 |
| Evaluator | **有限可用** | 基本功能可工作，但环境泄漏和 ? 崩溃是致命缺陷 |
| VM | **有限可用** | 基本功能可工作，但 CONCAT/闭包/TRY_UNWRAP/栈泄漏是严重缺陷 |

**总体结论**：

以生产级编译器/语言标准衡量，Nova 目前处于**可用原型阶段**。Evaluator 和 VM 路径可以运行基本程序，但存在多个严重语义缺陷。类型检查器本质上不是 Hindley-Milner 系统，无法提供可靠的类型安全保证。所有后端（C/Native/Cranelift/WASM）均无法实际编译运行。IR 系统的核心降级路径存在致命缺陷。

建议优先修复方向：
1. **Evaluator 环境安全**：所有 env 切换添加 try/finally，_call_fn 的 env 恢复移入 finally
2. **编译器模式匹配**：修正模式绑定顺序反转，guard 失败时保留 subject
3. **类型检查器核心**：实现完整的 HM 算法（unification + generalize/instantiate + occurs check）
4. **VM 语义修正**：CONCAT 强制类型检查、闭包自由变量分析、TRY_UNWRAP 报错
5. **C 后端修复**：ADT 语法和字段命名统一、闭包环境、filter/map 参数顺序
6. **IR 降级修复**：暂停 LIR 开发，先让 MIR 的 SSA 和 match/for 降级正确工作

---


## [2026-07-15] 第八轮全局审查报告

> **审查时间**：2026-07-15（第八轮）
> **审查版本**：main 分支最新提交 (252ad27)
> **审查方法**：三轮九个 Explore Agent 并行审查，生产级编译器标准
> **参考语言**：OCaml / Haskell / Elm / F#

### 项目结构审查表（第八轮更新）

| 模块 | 文件 | 审查状态 | 上次审查 | 严重 | 中等 | 轻微 |
|------|------|---------|---------|------|------|------|
| VM 虚拟机 | `vm.py` | 已审查 | 2026-07-15 | 6 | 9 | 7 |
| 编译器 | `compiler.py` | 已审查 | 2026-07-15 | 5 | 7 | 5 |
| 求值器 | `evaluator.py` | 已审查 | 2026-07-15 | 4 | 6 | 6 |
| 类型检查器 | `type_checker.py` | 已审查 | 2026-07-15 | 7 | 5 | 4 |
| 词法分析器 | `lexer.py` | 已审查 | 2026-07-15 | 2 | 3 | 4 |
| 语法分析器 | `parser.py` | 已审查 | 2026-07-15 | 4 | 5 | 3 |
| 错误处理 | `errors.py` | 已审查 | 2026-07-15 | 3 | 3 | 3 |
| 模块系统 | `modules.py` | 已审查 | 2026-07-15 | 2 | 4 | 2 |
| 环境 | `environment.py` | 已审查 | 2026-07-15 | 1 | 3 | 2 |
| C 代码生成 | `c_codegen.py` | 已审查 | 2026-07-15 | 5 | 4 | 4 |
| Native 后端 | `backend/native_backend.py` | 已审查 | 2026-07-15 | 5 | 4 | 2 |
| Cranelift 后端 | `backend/cranelift_backend.py` | 已审查 | 2026-07-15 | 4 | 3 | 1 |
| WASM 后端 | `backend/wasm_backend.py` | 已审查 | 2026-07-15 | 5 | 2 | 2 |
| x86_64 指令 | `backend/x86_64.py` | 已审查 | 2026-07-15 | 0 | 1 | 1 |
| 编译管道 | `backend/compiler_pipeline.py` | 已审查 | 2026-07-15 | 2 | 1 | 1 |
| IR 节点 | `ir/ir_nodes.py` | 已审查 | 2026-07-15 | 0 | 2 | 1 |
| HIR Lowering | `ir/hir_lowering.py` | 已审查 | 2026-07-15 | 1 | 3 | 2 |
| MIR Lowering | `ir/mir_lowering.py` | 已审查 | 2026-07-15 | 5 | 2 | 1 |
| LIR Lowering | `ir/lir_lowering.py` | 已审查 | 2026-07-15 | 5 | 3 | 2 |
| Pass 管理器 | `ir/pass_manager.py` | 已审查 | 2026-07-15 | 2 | 4 | 2 |
| C 运行时 | `runtime/nova_runtime.c` | 已审查 | 2026-07-15 | 5 | 4 | 3 |
| 测试套件 | `tests/` | 已审查 | 2026-07-15 | 4 | 3 | 2 |
| Tree-sitter | `tree-sitter-nova/` | 已审查 | 2026-07-15 | 1 | 2 | 2 |

---

## [2026-07-15] VM 虚拟机 (vm.py) 第八轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | 三星 | PIPE_CALL/MATCH_START-END/TRY_UNWRAP 设计有特色 |
| 可行性 | 三星 | 核心路径可用；循环控制机制脆弱，嵌套场景有严重 bug |
| 正确性 | 二星 | CONCAT 语义错误、while break/continue 嵌套 bug、闭包过度捕获 |
| 安全性 | 二星 | 帧恢复有 finally 保护，但大量 Python 异常未封装 |
| 一致性 | 二星 | VM 与 Evaluator 在多个关键语义上不一致 |
| 完整性 | 四星 | 覆盖了几乎所有 Op 定义，指令集较完整 |
| 工程质量 | 二星 | hasattr 动态属性、启发式循环检测、前向扫描跳转 |
| 性能 | 二星 | 闭包过度捕获浪费内存，字典存 locals 有开销 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [vm.py:807-810] **闭包捕获整个帧而非自由变量** → `CLOSURE` 执行 `dict(self.call_stack[-1].locals)`，浅拷贝所有局部变量。与 Evaluator 引用语义不一致，mutable 变量突变不可见 → 编译器分析自由变量，CLOSURE 携带自由变量名列表
- 追问：如果 OCaml 闭包捕获整个作用域的 dict 拷贝，能被接受吗？→ **绝对不能。** 连续八轮未修。

- [vm.py:693-701] **JUMP 启发式检测 while 循环回跳** → 通过 `target < ip and code[ip].opcode == CONST_UNIT` 推断 while 起始点，任何向后跳转且下一条是 CONST_UNIT 的代码都会被误识别 → 删除启发式，编译器显式编码 loop_start
- 追问：如果 GHC 的 STG 机通过运行时扫描字节码确定循环边界，能被接受吗？→ **绝对不能。** 连续八轮未修。

- [vm.py:769-775] **BREAK 前向扫描 fallback 仍存活** → 前向扫描到 LOOP_END 或 CONST_UNIT 就停止，嵌套循环中必然行为错误 → 彻底删除前向扫描，编译器必须回填确定性跳转目标
- 追问：JVM/Lua/CPython 的 break 都通过编译器计算好的跳转偏移量实现。运行时扫描指令流在任何生产级 VM 中都不可接受 → **绝对不能接受。**

- [vm.py:780-799] **CONTINUE while 的 loop_start 可能为 None** → 首次迭代时 loop_start 可能为 None，导致 `ip = None` 崩溃 → 删除启发式，强制编译器提供操作数
- 追问：任何生产级语言的 continue 空实现或崩溃能被接受吗？→ **绝对不能。**

- [vm.py:616-621] **CONCAT（++）语义错误，与 ADD 完全重合** → `CONCAT` 执行 `a + b`，数字拼接也被允许，丧失类型安全意义 → 显式检查操作数为 list 或 str，拒绝 int/float/bool
- 追问：OCaml 的 `@` 是列表拼接、`^` 是字符串拼接，两者不可混用。VM 将 `++` 实现为 `str()+str()` 在任何成熟语言中都不可接受 → **绝对不能接受。**

- [compiler.py:490-506] **嵌套循环中 break/continue 归属判定错误** → break 仅检查 `_while_end_stack` 是否非空，若 for 嵌套在 while 内，break 被错误归类为 while-break → 使用统一循环栈，break/continue 始终绑定到最内层循环
- 追问：Rust/ML 的 break 如何携带 loop label？为什么编译器层面的 loop stack 必须区分 for/while？→ **不能接受。**

#### 中等问题（影响特定场景）

- [vm.py:1168] DUP 无栈下溢检查
- [vm.py:868-872] INDEX 未捕获 IndexError/KeyError/TypeError
- [vm.py:874-895] FIELD_ACCESS 元组/ADT 索引越界未封装
- [vm.py:597-602] DIV 浮点数除零未检查
- [vm.py:1121-1124] MATCH_END 无匹配时不报错，与 Evaluator 不一致（VM 静默返回 Unit，Evaluator 抛 RuntimeError_）
- [vm.py:1073-1091] 嵌套模式匹配失败时栈泄漏
- [vm.py:355-381] _call_fn 对 NovaClosure 无部分应用支持
- [vm.py:226-256] 内置函数缺少类型与边界检查
- [vm.py:312-330] json_stringify 对 Err 的处理与 Evaluator 不一致

#### 轻微问题（代码质量）

- [vm.py:169] _loop_id 计数器在异常时泄漏字典条目
- [vm.py:179-217] 数学内置函数通过 lambda 包装，丢失类型错误上下文
- [vm.py:333-349] _format_value 未处理 dict 类型
- [vm.py:404] Frame.ip 字段从未被读取
- [vm.py:822-827/436-440] RETURN 在两条路径重复处理
- [vm.py:829-839] CALL_BUILTIN 无法区分被用户遮蔽的内置函数

#### Evaluator vs VM 对比（新增项）

| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| `++` 运算符 | `left + right`（支持列表和字符串） | `a + b`（数字也合法） | 一致但均错误 |
| 闭包捕获 | Environment 引用（mutable 突变可见） | dict(整个帧) 浅拷贝（突变不可见） | 不一致 |
| None/Some/Ok/Err | 全局构造器（一等值） | 编译器特殊处理（非一等值） | 不一致 |
| while 返回值 | 最后一次迭代的值 | CONST_UNIT | 不一致 |
| read_line | `input()` + EOFError 处理 | lambda 无 EOF 处理 | 不一致 |
| for 返回值 | 列表 | 列表 | 一致 |
| break/continue | 异常机制 | 指令机制（嵌套有 bug） | 不一致 |
| TryExpr `?` | ReturnSignal 异常 | return_flag 机制 | 不一致（顶层行为不同） |
| 模式匹配 | 递归匹配 | 指令序列 | 不一致（穷尽性缺失行为不同） |
| match 无 arm 成功 | 抛出 RuntimeError_ | 静默返回 Unit | 不一致 |

---

## [2026-07-15] 编译器 (compiler.py) 第八轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | 二星 | 标准栈式字节码设计，无显著创新；VM 运行时扫描实现控制流是负面独创 |
| 可行性 | 三星 | 基本功能可工作，但模块系统和嵌套循环有严重限制 |
| 正确性 | 二星 | while 循环 break/continue 存在确定性崩溃 bug 和脆弱的运行时扫描 |
| 安全性 | 二星 | 无循环导入保护、无模块命名空间隔离、过度闭包捕获 |
| 一致性 | 三星 | 编译器与 VM 的操作码协议基本一致，但文档与实现不一致 |
| 完整性 | 三星 | 所有 AST 节点有编译处理，但模式匹配有死代码 |
| 工程质量 | 二星 | 65 行死代码、无编译期错误检测、VM 控制流逻辑与指令执行耦合 |
| 性能 | 二星 | while break 运行时扫描 O(n)、闭包过度捕获、常量池形同虚设 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [compiler.py:693-703] **无 else 的 if 表达式在 true 路径泄漏栈值** → then_branch 执行后缺少 JUMP 跳过 CONST_UNIT，栈上同时留下 then 的值和 Unit 两个值 → 在 then_branch 后插入 JUMP 跳过 CONST_UNIT
- 追问：Python/CPython 如何处理 POP_JUMP_IF_FALSE 与 JUMP_FORWARD 的组合以保证单值出口？→ **不能接受。**

- [compiler.py:490-498] **嵌套循环中 break 总是优先跳出 while（而非最内层循环）** → BreakExpr 编译时仅检查 `_while_end_stack` 是否非空，for 嵌套在 while 内时 break 被错误归类为 while-break → 维护统一循环栈，break 始终针对栈顶（最内层）循环
- 追问：成熟编译器绝对不能在运行时扫描字节码来找跳转目标 → **绝对不能接受。**

- [compiler.py:500-506] **嵌套循环中 continue 被 VM 优先当作 for 循环处理** → ContinueExpr 编译时若 `_while_start_stack` 非空 emit CONTINUE, loop_start，但 VM 处理 CONTINUE 时优先检查 `_for_iters` → 编译器必须知道最内层循环类型并生成对应操作码
- 追问：LLVM/MLIR 中 continue 通常被降维为到特定基本块的无条件跳转——编译器 IR 层如何消除"循环类型"的歧义？→ **不能接受。**

- [compiler.py:304-347] **import 内联无命名空间隔离** → 所有模块的导出被平铺到同一全局作用域，同名函数/ADT/变量会被静默覆盖 → 实现模块命名空间或至少冲突检测
- 追问：即使是 C 的 `#include` 也有头文件保护 → **绝对不能接受。**

- [compiler.py:367-376] **嵌套函数名冲突** → 所有函数（包括嵌套 lambda）注册到全局 functions 字典，同名嵌套函数后编译的覆盖先编译的 → 实现词法作用域的函数查找
- 追问：任何支持嵌套函数的语言都保证名字不会冲突 → **不能接受。**

#### 中等问题（影响特定场景）

- [compiler.py:961-962] while 循环返回值总是 Unit，与文档"返回最后一次迭代值"不一致
- [compiler.py:379,636] CLOSURE 操作数不匹配（Op 定义 3 个操作数，编译器只发 2 个）
- [compiler.py:408-410] None 标识符特殊处理与 ADT 系统不一致
- [compiler.py:822-886] _compile_pattern_test 和 _compile_pattern_bindings 是 65 行死代码
- [compiler.py:987-1016] while 循环体 break 后的栈泄漏

#### 轻微问题（代码质量）

- [compiler.py:397-398] CharLiteral 编译为 CONST_STRING，运行时 CharLiteral 和 StringLiteral 不可区分
- [compiler.py:449-451] Assignment 总是 mutable=True，不可变检查推迟到运行时
- [compiler.py:524] CONCAT 指令与 VM 实现一致但语义存疑
- [compiler.py:248-249] AUTO_CALL_MAIN 指令是死代码

---

## [2026-07-15] 求值器 (evaluator.py) 第八轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | 四星 | 设计完整，AST 遍历式解释器 + 两遍扫描 + 闭包捕获 + 模式匹配 + 错误传播 |
| 可行性 | 四星 | 整体架构可行，作为教学/原型解释器完全可用 |
| 正确性 | 三星 | ++ 运算符与 VM 不一致、闭包捕获语义分歧、多处缺少类型检查 |
| 安全性 | 二星 | 无栈溢出保护、无沙箱、break/continue 可逃出函数体 |
| 一致性 | 二星半 | 与 VM 行为不一致（++、闭包、head field_names），None 值表示混用 |
| 完整性 | 四星 | AST 覆盖完整，模式匹配全面，缺少显式 return 和 cons 模式 |
| 工程质量 | 三星 | 代码结构清晰，但有重复代码（eval_decl），异常处理不完整 |
| 性能 | 三星 | 树遍历解释器性能受限，环境链查找 O(n) |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [evaluator.py:751-761] **Block 环境恢复不在 finally 中** → `self.env = old_env` 位于 try 之外，Block 内任何异常导致调用者环境永久被替换为子环境 → 所有 `old_env = self.env; self.env = child_env` 模式必须改写为 try/finally
- 追问：如果 OCaml 的 let-in 表达式因异常跳过环境恢复，能被接受吗？→ **不能接受。**

- [evaluator.py:433-455] **_call_fn 环境恢复不在 finally 中** → 函数体抛非 Return/Break/Continue 异常后，后续所有求值都在错误的闭包环境中进行 → 添加 try/finally 保护
- 追问：如果 Haskell GHC 的函数调用异常后环境泄漏，能被接受吗？→ **绝对不能。**

- [evaluator.py:989-1006] **match guard + body 环境恢复不在 finally 中** → guard 或 body 异常后环境泄漏；且 guard 和 body 使用两个独立环境，guard 中的 mut 副作用对 body 不可见 → 使用 try-finally 包裹
- 追问：如果 Rust 的 match guard 异常后环境不恢复，能被接受吗？→ **绝对不能。**

- [evaluator.py:712-720] **顶层 `?` 操作符导致 ReturnSignal 逃逸** → eval_program 没有 except ReturnSignal，`let x = None?` 导致未捕获的 Python 异常 → 在 eval_program 中捕获 ReturnSignal
- 追问：如果是 Rust 的 `?` 在顶层导致 panic，能被接受吗？→ **绝对不能。**

#### 中等问题（影响特定场景）

- [evaluator.py:889-895] `<`/`>`/`<=`/`>=` 比较未隔离 Bool 与 Int（Python 中 `True < 2` 返回 True）
- [evaluator.py:776-782] Assignment 异常捕获类型错误（`except RuntimeError` 而非 `RuntimeError_`）
- [evaluator.py:437-441] break/continue 缺少函数内防护（可逃出 _call_fn 被外层循环捕获）
- [evaluator.py:939-952] while 循环未创建子环境（与 for 不一致）
- [evaluator.py:1009] match 失败行为与 VM 不一致（Evaluator 抛 RuntimeError_，VM 返回 Unit）
- [evaluator.py:490 vs vm.py:785] 闭包捕获语义分歧（Evaluator 引用语义 vs VM 值语义）

#### 轻微问题（代码质量）

- [evaluator.py:554-609] eval_decl 与 _collect_decl + _eval_decl_body 重复代码
- [evaluator.py:270-271] JSON null 转换为 NovaADTValue("Option","None")，与 Python None 混用
- [evaluator.py:857] bool 是 int 子类型，true + 1 = 2 在 Nova 中可能不应被允许
- [evaluator.py:765-768] Assignment 捕获 Python RuntimeError 而非 Nova RuntimeError_

---

## [2026-07-15] 类型检查器 (type_checker.py) 第八轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | 二星 | 不是真正的 HM，是一个结构子类型兼容检查器 |
| 可行性 | 三星 | 基础类型检查可用，但泛型约束无统一机制 |
| 正确性 | 一星 | TypeVar 万能兼容摧毁类型安全，let 多态缺失 |
| 安全性 | 二星 | 运行时安全的检查不足（空指针、数组越界、并发） |
| 一致性 | 二星 | 与 Evaluator 和 VM 的行为不一致（如闭包捕获值类型） |
| 完整性 | 三星 | 基本运算符、ADT、函数类型、List/Map 覆盖 |
| 工程质量 | 二星 | 核心类型检查逻辑集中在 TypeVar 兼容分支 |
| 性能 | 三星 | 线性扫描，无复杂约束求解 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [type_checker.py:1272-1273] **TypeVar 万能兼容摧毁类型安全** → `_types_compatible` 将任何包含 TypeVar 的类型比较都判定为兼容 → 实现真正的 Hindley-Milner unification
- 追问：如果 OCaml 的类型推断器对某些表达式推断失败（如 `1 + "hello"`），能被接受吗？→ **绝对不能。**

- [type_checker.py:740-743] **TypeVar 可被任意调用** → 当函数调用的被调用者是 TypeVar 时，不报错而是生成新 TypeVar 作为返回值 → 不允许对非函数类型进行调用
- 追问：如果 Elm/F# 中未类型化的参数可以被当作函数调用，能被接受吗？→ **绝对不能。**

- [type_checker.py:748-763] **PipeExpr 检查过于宽松且不报错** → 管道操作符在类型不兼容时不报错，静默返回 right_ty.return_type 或 right_ty → 严格检查 left_ty 与函数第一个参数的统一性
- 追问：F# 的 `|>` 是 `('a -> 'b) -> 'a -> 'b`，类型必须严格匹配。能被接受吗？→ **绝对不能。**

- [type_checker.py:583-782] **let 多态（Let Polymorphism）完全缺失** → `let id = |x| x` 绑定后类型为 `FnType([TypeVar], TypeVar)`，不是 `forall a. a -> a` → 实现 HM 的 generalize/instantiate
- 追问：如果 OCaml 的 `let id x = x` 没有正确实现 let 多态，能被接受吗？→ **绝对不能。**

- [type_checker.py:897-916] **ForExpr 迭代变量类型不推断** → `for x in nums` 中 x 的类型永远是新的 TypeVar → 推断 iterable 类型，ListType(T) 则绑定 x: T
- 追问：如果 Rust 的 for 循环不推断迭代变量类型，能被接受吗？→ **绝对不能。**

- [type_checker.py:930-952] **ListComprehension 迭代变量类型不推断** → 与 ForExpr 相同，列表推导式变量类型不推断 → 从可迭代对象类型中提取元素类型
- 追问：任何生产级编译器的类型检查器跳过某些 Pattern 检查，能被接受吗？→ **绝对不能。**

- [type_checker.py] **缺失 Hindley-Milner 四大核心机制** → 无 Unification、Generalize、Instantiate、Occurs Check → 重写类型检查核心，实现标准 HM Algorithm W
- 追问：任何声称实现 HM 的语言（Elm, Haskell, OCaml）都有这四个核心。Nova 一个都没有 → **绝对不能接受。**

#### 中等问题（影响特定场景）

- [type_checker.py:1059-1068] 二元操作符错误时返回具体类型而非 ERROR_TYPE，导致级联错误抑制不彻底
- [type_checker.py:287] None 构造函数使用固定 TypeVar，无真正的多态性
- [type_checker.py:888-895] TryExpr 对非法类型静默通过（`42?` 不报错）
- [type_checker.py] 穷尽性检查完全缺失（match 缺少 arm 不报错）
- [type_checker.py:1142-1162] `_collect_type_bindings` 方向受限，actual 是 TypeVar 时不收集绑定

#### 轻微问题（代码质量）

- [type_checker.py:356] 数学函数 Int 自动转换未实现
- [type_checker.py] `json_parse` 返回固定 TypeVar，多调用场景下可能产生意外类型关联
- [type_checker.py] `_infer_fn_type` 的返回类型变量不会被函数体统一
- [type_checker.py] `_expand_alias` 不处理类型别名中的 PrimType 循环（可能无限递归）

---

## [2026-07-15] 词法分析器 (lexer.py) + 语法分析器 (parser.py) 第八轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | 三星 | 标准递归下降，管道运算符处理有特色 |
| 可行性 | 三星 | 标准路径基本可用 |
| 正确性 | 二星 | 管道优先级错误、step 关键字遮蔽、无 else if |
| 安全性 | 三星 | 运行时安全（无缓冲区溢出） |
| 一致性 | 三星 | 词法分析和语法分析一致 |
| 完整性 | 二星 | 管道和模式匹配语法有遗漏 |
| 工程质量 | 二星 | 有大量测试但缺少集成测试 |
| 性能 | 四星 | 无性能问题 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [parser.py:672-678] **管道操作符 `|>` 优先级高于比较运算符** → `a < b |> c` 被错误解析为 `a < (b |> c)`，违反 F#/Elm 约定 → 将 pipe 层级下调至 equality_expr 之下
- 追问：如果 Elm 编译器把 `|>` 优先级搞得比 `==` 还高，能被接受吗？→ **绝对不能。**

- [parser.py:464-466] **`<-` 歧义** → 用 `LT` + `MINUS` 拼接出 `<-`，`for i < -1..10` 会被解析为 range for → lexer 添加独立 ARROW_LEFT token
- 追问：OCaml 的 `<-` 拥有独立 token。用 `<` + `-` 拼凑不可接受 → **绝对不能。**

- [lexer.py:237-238] **字符串以 `\` 结尾时 IndexError 崩溃** → `_advance()` 消费反斜杠后若到 EOF 则 IndexError → 检查 EOF
- 追问：GHC 的 lexer 在字符串末尾越界是 P1 级安全漏洞 → **绝对不能接受。**

- [lexer.py:284-286] **字符字面量以 `\` 结尾时同样 IndexError** → 与问题 3 同源
- 追问：任何生产级编译器的词法分析器都不应崩溃 → **绝对不能接受。**

- [parser.py:522] **match arm 前瞻列表不完整** → 缺少 `TokenType.CHAR` 和 `TokenType.MINUS`，无逗号分隔时字符/负数模式失败 → 加入前瞻集合
- 追问：Rust/Haskell 的 match arm 分隔要么强制要求逗号，要么解析器前瞻集合必须完备 → **不能接受。**

- [parser.py:457] **`step` 关键字不能作为 for 循环变量名** → `for step <- 0..10` 失败 → 允许 STEP token 降级为标识符
- 追问：Python/Rust/JS 中 `step` 都不是关键字 → **不能接受。**

#### 中等问题（影响特定场景）

- [parser.py:660-678] 链式比较 `a < b < c` 未禁止
- [lexer.py:251,298] 未知转义序列静默接受，无警告
- [parser.py:950-982] 列表推导式不支持多 for 子句
- [parser.py:428] if/match/for/while 不能出现在运算符右侧
- [lexer.py] 数字字面量不支持 `.5`、`5.`、`1e10`、`1_000_000`
- [lexer.py:155-160] `_make_error` 完全未使用

#### 轻微问题（代码质量）

- [lexer.py:91] UNIT token 死代码
- [lexer.py:88] PIPE_VARIANT token 死代码
- [parser.py:798-800] _parse_primary_expr 中 UNIT 分支死代码
- [parser.py:580-588] 负数模式 span 不覆盖数字部分
- [parser.py:228-240] ADT 变体允许无显式分隔符

---

## [2026-07-15] 错误处理 (errors.py) + 模块系统 (modules.py) + 环境 (environment.py) 第八轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | 三星 | 多行高亮错误报告有特色 |
| 可行性 | 三星 | ErrorCollector 在 TypeChecker 中使用 |
| 正确性 | 二星 | raise_all 扁平化、相关 note 跨文件显示错误、错误信息缺少文件名 |
| 安全性 | 二星 | 全局可变单例、导入同名静默覆盖 |
| 一致性 | 二星 | 错误位置精度不足（缺少文件名） |
| 完整性 | 二星 | Evaluator 不使用 ErrorCollector |
| 工程质量 | 三星 | 错误信息格式化清晰 |
| 性能 | 四星 | 无性能问题 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [errors.py:405-411] **raise_all 将结构化错误扁平化为字符串** → 后续错误的 severity/span/source 全部丢失 → 废弃 raise_all 聚合语义，改为按顺序逐个抛出或返回错误列表
- 追问：Rust 的 `rustc_errors::Handler` 如何处理多错误报告？→ **不能接受。**

- [errors.py:68-75] **RelatedNote 不携带 source_code** → 跨文件 note 显示主错误文件的源码，位置被错位应用 → 增加 source_code 字段
- 追问：Rust 的 SubDiagnostic 是否携带自己的 SourceFile？→ **不能接受。**

- [modules.py:329-330 + environment.py:30-32] **模块导入同名绑定静默覆盖** → import 通过 define 注入，已存在时直接覆盖，不产生警告或错误 → 增加冲突检测
- 追问：OCaml 的 `open` 导致名称冲突时如何报告？→ **不能接受。**

- [environment.py:34-61] **lookup/assign 错误不携带任何位置信息** → 所有运行时名称错误都是无定位的裸字符串 → 传递 line/column/span
- 追问：OCaml 的 Env.lookup_value 如何与 Location.t 结合？→ **不能接受。**

- [modules.py:357-371 + modules.py:186] **全局可变单例 _global_module_manager** → 影响可测试性和并发安全 → 移除全局单例
- 追问：Rust 编译器为何废弃全局 TyCtxt？→ **不能接受。**

#### 中等问题（影响特定场景）

- [errors.py:334-352] 控制流信号 BreakSignal/ContinueSignal/ReturnSignal 不携带 span
- [errors.py:320-327] RuntimeError_ 名字仍遮蔽 Python 内置 RuntimeError
- [errors.py:186-191] 错误报告不显示文件名
- [modules.py:56-58] ModuleInfo.get_exported_bindings 静默吞掉 RuntimeError_
- [modules.py:99-105] ModuleResolver 搜索路径含 ""，解析结果依赖 os.getcwd()
- [environment.py:38-39,46-47,58-59] 作用域链递归查找存在栈溢出风险
- [environment.py:26,32,64-65] 闭包环境捕获整个作用域链
- [modules.py:273-274] loading_stack.remove(file_path) 使用 list.remove 而非 pop

#### 轻微问题（代码质量）

- [errors.py:271-283] _compute_underline 的 end_col 语义不明确
- [errors.py:396-398] ErrorCollector.get_all() 错误与警告简单拼接，无排序
- [modules.py:134-138] 包导入路径含 .nova 后缀时未处理
- [environment.py:30-32] define 无重复定义检测
- [errors.py:140-155] _severity_label 和 _severity_color 使用 dict.get 回退

---

## [2026-07-15] 后端代码生成第八轮审查报告

### 各后端可行性评估

| 后端 | 状态 | 可编译运行 | 端到端测试 | LIR 覆盖率 | 函数式特性支持 | 成熟度 |
|------|------|-----------|-----------|-----------|--------------|--------|
| C 代码生成 | 可用但脆弱 | 部分（需运行时库） | 有单元测试，无集成运行 | AST 直通，不走 LIR | 闭包/ADT/模式匹配有严重类型不一致 | C- |
| Native x86_64 | Demo 级别 | 仅手写 LIR，无法从源码编译 | 有机器码编码测试，无实际执行 | ~70% | 不支持闭包、模式匹配、GC | D+ |
| Cranelift | 不可用 | 无（生成 .clif 文本） | 仅文本生成断言 | ~50% | 不支持闭包、ADT 字段填充、列表元素填充 | D |
| WASM | 不可用 | 无（WAT 结构不平衡） | 仅文本生成断言 | ~50% | Branch 丢失 true 分支、BuildADT 不存值 | D- |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [c_codegen.py:595-596] **TryExpr 值/指针语义混用** → `NovaADT* {temp}` 但 `_compile_adt_constructor_to_stmt` 生成 C struct value，对非指针值做 `->` 解引用 → 统一 ADT 表示
- 追问：OCaml/Haskell 的 ADT 是值类型，C 后端选择用指针运行时。是否应统一为堆分配+引用计数？→ **不能接受。**

- [c_codegen.py:704] **PatternConstructor 匹配使用 `.tag` 但 subject 是指针** → 应使用 `->tag` → 根据 ADT 实际类型选择 `.` 或 `->`
- 追问：模式匹配在 C 中应如何表示以避免类型歧义？→ **不能接受。**

- [c_codegen.py:409,1187] **List 迭代元素类型硬编码 int64_t** → 浮点/字符串列表被强制解释为 int64_t → 从 List 类型参数推断元素类型
- 追问：Elm/F# 的列表是同质且类型明确的，C 后端为何无法传播元素类型？→ **不能接受。**

- [c_codegen.py:930-1013] **闭包捕获栈上局部变量地址** → 闭包逃逸到外层作用域后访问悬空指针 → 对捕获变量做堆分配/复制
- 追问：OCaml 闭包捕获的是堆分配环境中的值，C 后端是否缺少环境堆分配？→ **绝对不能。**

- [c_codegen.py:906-913] **_box_to_voidptr 无释放逻辑** → 每次捕获浮点变量都泄漏一个 8 字节堆块 → 引入引用计数或 GC
- 追问：生产级编译器如何解决闭包捕获值的内存所有权？→ **不能接受。**

- [native_backend.py:410-485] **浮点 BinOp 完全走整数路径** → `+`/`-`/`*`/`/` 均使用 add/sub/imul/idiv，浮点运算产生完全错误结果 → 检查类型，浮点走 SSE2 指令
- 追问：之前审查已报告，为何未修复？→ **绝对不能接受。**

- [native_backend.py:387-389] **寄存器分配是最简 pop 模型** → LinearScanAllocator 定义了但从未使用 → 集成 LinearScanAllocator
- 追问：GHC 的 NCG 使用图着色+线性扫描，Nova 的 allocator 为何定义了却不调用？→ **不能接受。**

- [native_backend.py:421-443] **idiv/imul 静默破坏 RDX** → 无保存/恢复逻辑 → 临时移除 RAX/RDX 从 vreg 映射
- 追问：x86_64 的 idiv 对 RDX:RAX 的隐式破坏在寄存器分配中如何建模？→ **不能接受。**

- [native_backend.py:734-758] **栈上分配复合数据结构** → 函数返回后 RSP 恢复，指针悬空 → 调用运行时分配函数在堆上分配
- 追问：函数式语言的数据结构通常在堆上分配，Native 后端为何选择在栈上分配？→ **绝对不能。**

- [cranelift_backend.py:162-168] **LIRBranch 硬编码标签名** → 忽略 instr.true_label 和 instr.false_label → 使用实际标签名
- 追问：之前审查已报告，为何未修复？→ **绝对不能接受。**

- [cranelift_backend.py:187-188] **LIRIndex 完全忽略参数** → 硬编码 `load i64, v0 + 0` → 计算正确偏移
- 追问：之前审查已报告，为何未修复？→ **绝对不能接受。**

- [cranelift_backend.py:247-255] **参数类型硬编码 i64** → 浮点参数按整数 ABI 传递 → 根据参数类型选择 i64 或 f64
- 追问：之前审查已报告，为何未修复？→ **绝对不能接受。**

- [wasm_backend.py:161] **字符串 NUL 终止符编码错误** → `b"\\x00"` 是 4 字节而非真正的 NUL → 改为 `b"\x00"`
- 追问：之前审查已报告，为何未修复？→ **绝对不能接受。**

- [wasm_backend.py:260-263] **LIRBranch 丢失 true 分支** → 只生成 `br_if $block_false` → 生成 `br_if $block_true` 后紧跟 `br $block_false`
- 追问：之前审查已报告，为何未修复？→ **绝对不能接受。**

- [wasm_backend.py:273-276] **LIRBuildADT 不存储 tag 和字段值** → 只分配空内存 → 依次存储 type_tag 和各字段值
- 追问：之前审查已报告，为何未修复？→ **绝对不能接受。**

- [compiler_pipeline.py:33-35] **BACKEND_NATIVE 映射到 CraneliftBackend 而非 NativeCodeGen** → 选择 native 后端实际得到 Cranelift → 改为映射到 NativeCodeGen
- 追问：之前审查已报告，为何未修复？→ **绝对不能接受。**

#### 中等问题（影响特定场景）

- [c_codegen.py:635] IfExpr 无 else 返回 "0"，类型可能不匹配
- [c_codegen.py:852-871] _compile_adt_constructor_to_stmt 使用 GNU C 扩展 compound literal
- [c_codegen.py:1401-1403] _escape_c_string 转义顺序风险
- [native_backend.py:356-360] 函数尾声在每个 LIRReturn 处重复发射
- [native_backend.py:880-879] _patch_code 假设数据段紧跟代码段
- [native_backend.py:940-950] _generate_elf 数据段对齐约束未满足
- [x86_64.py:451-473] je_rel32 重复定义两次
- [cranelift_backend.py:109-118] 函数参数语法使用 `$loc` 而非 `%name`
- [cranelift_backend.py:156-157] LIRReturn 不返回任何值
- [cranelift_backend.py:170-181] LIRBuildList/BuildTuple/BuildADT 只分配内存不填充
- [wasm_backend.py:313-340] _emit_binop 浮点判断只检查 src_locs[0]
- [wasm_backend.py:142-144] 运行时导入函数签名使用 i64 传指针（WASM32 下应为 i32）

#### 轻微问题（代码质量）

- [native_backend.py:1028] SimpleNativeCompiler.compile_source 抛出 NotImplementedError
- [native_backend.py:394-408] LIRLoadConst unit 类型走 else 分支抛出 NotImplementedError
- [c_codegen.py:60] C_KEYWORDS 包含运行时函数名
- [c_codegen.py:821-843] 内置函数通过字符串匹配硬编码
- [wasm_backend.py:76-77] WAT 注释声称 "Supports WasmGC" 但未使用 GC 指令
- [compiler_pipeline.py:82-83] C 后端在 compile_source 中直接调用 generate(ast)，不走 LIR

---

## [2026-07-15] IR 系统 + Pass 管理器第八轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| IR 设计合理性 | 二星 | 三层区分存在但缺乏关键语义类型 |
| 职责边界清晰度 | 二星 | HIR 混用声明与表达式 |
| Pass 实现完整性 | 一星 | Inlining 空壳；LICM 仅识别单块循环 |
| 异常处理 | 二星 | Pass 异常打印到 stderr 但不停止编译 |
| SSA 正确性 | 一星 | 可变赋值直接覆盖 env 破坏 SSA |
| 控制流降级正确性 | 一星 | match 完全退化为顺序跳转 |
| 闭包/数据流 | 一星 | 闭包捕获列表为空 |
| 代码质量/可维护性 | 二星 | 大量使用 `or ""` 掩盖未定义变量 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [mir_lowering.py:351-384] **match 表达式完全退化为无条件顺序跳转** → 无论 match 值是什么，总是执行第一个 arm → 为每个 arm 生成类型标签/值比较指令
- 追问：OCaml 的 Lambda 层将 pattern matching 编译为决策树。Nova 当前实现完全不可接受 → **绝对不能。**

- [mir_lowering.py:396-417] **For 循环迭代变量未绑定到作用域** → 循环体无法引用迭代变量 → 在 header_block 生成 next() 调用并绑定变量
- 追问：Rust MIR 将 for 降阶为 IntoIter::into_iter + loop。Nova 应采纳同样策略 → **不能接受。**

- [mir_lowering.py:275-283] **可变赋值直接覆盖 env 破坏 SSA 不变量** → `self.env[name] = val_ssa`，SSA 核心语义被破坏 → 引入 MIRAlloca/MIRLoad/MIRStore
- 追问：LLVM IR 中 mut 局部变量用 alloca + load/store 表示 → **不能接受。**

- [mir_lowering.py:247-250 / lir_lowering.py:149-155] **闭包自由变量完全丢失** → `captures=[]` 永远为空；LIR 层降级为字符串常量 → 做自由变量分析，填入 captures
- 追问：OCaml 的闭包表示为 {code_ptr, env_ptr}，自由变量按平坦化方式存储 → **不能接受。**

- [lir_lowering.py:171-176] **MIRMapBuild 错误降级为 LIRBuildList** → 丢失了键值对的成对语义 → 添加 LIRBuildMap 指令
- 追问：是否需要像 MLIR 的 dictionary_attribute 在 LIR 层保留类型信息？→ **不能接受。**

- [lir_lowering.py:204-212] **MIRPhi 只取第一个 source** → 来自 false 分支的值被丢弃 → 在 LIR 层 phi 应被寄存器分配阶段消除
- 追问：LLVM 使用 mem2reg 生成 phi，后端通过 coalescing 消除 → **不能接受。**

- [lir_lowering.py:219-223] **LIRBranch cond_reg 未设置** → 所有条件跳转依赖隐式 RAX 约定 → 明确将条件值的 loc 赋给 cond_reg
- 追问：LLVM 的 br i1 %cond, label %T, label %F 中 %cond 是显式 SSA 值 → **不能接受。**

- [lir_lowering.py:231-241] **MIRSwitch/MIRMatchJump 完全退化为无条件跳转到 default** → 所有 case 分支被丢弃 → 生成比较-条件跳转链或跳转表
- 追问：LLVM 的 SwitchInst 会根据 case 密度选择二分跳转或跳转表 → **不能接受。**

- [mir_lowering.py:309-349] **phi 节点前驱集合与实际 CFG 不一致** → 某分支包含 break/continue/return 时仍被加入 phi_sources → 生成 phi 前检查实际跳转关系
- 追问：LLVM 要求 phi 节点的前驱列表与基本块的前驱集合精确一致 → **不能接受。**

- [pass_manager.py:105/115] **常量折叠通过修改 __class__ 实现** → 直接篡改对象的类，是未定义行为 → 构造新的 HIRIntLiteral 节点并替换
- 追问：AST 变换应遵循函数式不可变原则 → **不能接受。**

#### 中等问题（影响特定场景）

- [hir_lowering.py:98] AliasDef 目标类型信息丢失（未修复）
- [hir_lowering.py:199-202] PipeExpr 嵌套未展平（未修复）
- [hir_lowering.py:204-205] TryExpr 降级过于简化（未修复）
- [hir_lowering.py:289-297] HIRBlockExpr.exprs 中混入 HIRLetDecl（类型不匹配）
- [mir_lowering.py:159-162] 未定义变量返回 None 而非报错
- [mir_lowering.py:396-417] For 循环用迭代器值作为分支条件
- [lir_lowering.py:141-147] MIRCall 参数 SSA 名未传递到 LIR
- [lir_lowering.py:157-162/164-169/178-183] 聚合类型构建丢失元素信息
- [pass_manager.py:257-262] Inlining Pass 仍是空壳（未修复）
- [pass_manager.py:280-374] DCE 的副作用类型列表与实际代码逻辑脱节
- [pass_manager.py:488-693] LICM 循环识别过于简陋

#### 轻微问题（代码质量）

- [ir_nodes.py:724-730] LIRFunction 缺少基本块结构
- [ir_nodes.py:753-755] LIRInstr.src_locs_imm 语义模糊
- [hir_lowering.py:62-75] lower() 跳过失败的声明但继续编译
- [hir_lowering.py:108-113] 顶层 WhileExpr 降级返回类型错误
- [lir_lowering.py:225-229] MIRReturn 降级时类型硬编码为 UNIT_TYPE
- [lir_lowering.py:92-213] _lower_instruction 中操作数类型统一使用 result_type
- [pass_manager.py:45-59] 整数运算表中 &&/|| 语义可能不匹配 Nova

---

## [2026-07-15] C 运行时 + 测试 + Tree-sitter 第八轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| C 运行时内存安全 | 二星 | RC 不递减子对象、整数溢出、UB、GC 空壳 |
| C 运行时功能完整性 | 三星 | 基础数据结构完整，但循环引用、JSON、字符串处理有缺陷 |
| 测试覆盖率 | 二星 | 无 Evaluator-VM 一致性测试、无端到端测试、大量特性零测试 |
| 后端可靠性 | 二星 | 所有后端仅测代码生成，无编译运行验证 |
| Tree-sitter 语法完整性 | 三星 | 缺少 TryExpr、泛型参数、float 正则不完整 |
| 安全与健壮性 | 二星 | 命令注入风险仍在、整数溢出、NULL 解引用风险 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [nova_runtime.c:99-102] **GC 仍是空壳，循环引用永不释放** → `nova_gc_collect()` 为空函数，纯引用计数无法处理循环引用 → 实现增量标记-清除 GC 或引用计数 + 周期检测
- 追问：OCaml 使用分代 GC，Rust 用所有权规避。Nova 作为带 GC 的语言，不处理循环引用是致命缺陷 → **绝对不能。**

- [nova_runtime.c:749-756,791-798] **nova_adt_release / nova_closure_release / nova_tuple_release 不递归递减子对象** → 嵌套 ADT、闭包捕获列表/字符串时内层对象全部泄漏 → 遍历子对象调用对应 release
- 追问：Python 的 Py_DECREF 会递归触发析构；OCaml 的 finalizer 会清理自定义块 → **绝对不能。**

- [nova_runtime.c:290] **nova_string_replace 整数溢出** → `count * (new_s->length - old_s->length)` 可能溢出 int64_t → 使用饱和算术或溢出检查
- 追问：Rust 的 String::replace 在标准库中安全处理 → **绝对不能。**

- [nova_runtime.c:525-538] **nova_map_put 对非 NovaValue* 值调用 nova_value_release —— 未定义行为** → 通过"巧合"不崩溃，但严格的 UB → Map value 统一使用 NovaValue* 包装
- 追问：没有任何生产级运行时依赖"结构体偏移巧合"来避免崩溃 → **绝对不能。**

- [nova_runtime.c:1500-1516] **nova_system 命令注入风险仍存在** → 直接 `system(command->data)`，C 后端生成的代码若拼接用户输入可被利用 → 移除或改为 execve 系列
- 追问：Haskell 的 System.Cmd 已废弃，推荐使用 process 包的 createProcess → **绝对不能。**

- [tests/] **零 Evaluator-VM 一致性测试** → 整个测试套件中没有任何测试同时运行 Evaluator 和 VM 并比较结果 → 添加 TestEvaluatorVMConsistency 类
- 追问：PyPy 的测试套件有 test_pypy_c 验证与 CPython 的一致性 → **绝对不能。**

- [tests/] **所有后端零端到端运行验证** → test_c_codegen.py 仅尝试 gcc -fsyntax-only，test_backends.py 只检查 IR 文本，test_native_backend.py 只检查指令编码字节 → 添加编译-链接-运行-验证流程
- 追问：Go 的 test/run.go 会编译并执行测试程序；Rust 的 compiletest 有 run-pass 模式 → **绝对不能。**

- [tree-sitter-nova/grammar.js] **Tree-sitter Grammar 缺失 try_expr** → parser.py 支持 `expr?`，但 grammar.js 完全没有 try_expr → 在 grammar.js 的 _expression 中添加 try_expr
- 追问：Tree-sitter 是官方语法，与手写的 parser.py 不一致意味着语法定义存在多个"真相来源" → **不能接受。**

- [tree-sitter-nova/grammar.js:88-97] **Tree-sitter 缺少泛型类型参数语法** → parser.py 支持 `type Option[T] { ... }`，grammar.js 没有 → 在 type_def 规则中添加泛型参数
- 追问：任何生产级编译器的语法定义必须单一来源 → **不能接受。**

- [tree-sitter-nova/grammar.js:282] **float_literal 正则不完整** → 不支持 `.5`、`5.`、`1e10`、`1.5e-3` → 改为更完整的正则
- 追问：任何生产级编译器的词法分析器都应支持标准浮点格式 → **不能接受。**

#### 中等问题（影响特定场景）

- [nova_runtime.c:30-34] nova_alloc 不检查 NULL，多处 malloc 失败未处理
- [nova_runtime.c:1340-1365] JSON 解析对非 NovaValue 输入无错误报告
- [tree-sitter-nova/grammar.js:293-296] escape_sequence 正则允许无效转义
- [nova_runtime.c:245-259] nova_string_format 未处理 vsnprintf 截断
- [c_codegen.py:405-409] C 代码生成器对列表元素类型假设为 int64_t
- [tests/] 测试缺少 char、export、generic、try、map 更新等特性覆盖

#### 轻微问题（代码质量）

- [tree-sitter-nova/] corpus 测试覆盖不足
- [tests/] 测试用例之间可能存在隐式状态依赖
- [nova_runtime.c] 部分函数缺少 const 正确性

---

## [2026-07-15] 全局问题汇总与修复趋势分析

### 第八轮新发现 vs 历史问题修复状态

| 类别 | 历史问题数 | 已修复 | 部分修复 | 未修复 | 新发现 |
|------|-----------|--------|---------|--------|--------|
| VM | 6 | 1 (id() 替换) | 1 (CONTINUE 操作数) | 4 | 9 |
| 编译器 | 6 | 2 (PatternTuple/List, &&/||) | 1 (while break/continue) | 3 | 8 |
| 求值器 | 7 | 3 (递归深度, ++, head/tail field_names) | 1 (顶层 ?) | 3 | 7 |
| 类型检查器 | 12 | 2 (ADTType.__eq__, MapExpr) | 1 (PatternConstructor) | 9 | 6 |
| Lexer/Parser | 10 | 6 (非法字符, 未闭合字符串, MapExpr, PatternChar, match guard, PatternTuple/List) | 0 | 4 | 6 |
| 错误/模块/环境 | 11 | 1 (clear_cache) | 1 (NameError) | 9 | 6 |
| C 后端 | 4 | 1 (闭包捕获) | 1 (TryExpr 字段名) | 2 | 5 |
| Native 后端 | 4 | 2 (LIRCallIndirect, LIRReturn callee-saved) | 1 (寄存器分配) | 1 | 5 |
| Cranelift 后端 | 3 | 0 | 0 | 3 | 3 |
| WASM 后端 | 4 | 0 | 0 | 4 | 4 |
| 编译管道 | 2 | 0 | 0 | 2 | 1 |
| HIR Lowering | 3 | 0 | 0 | 3 | 3 |
| MIR Lowering | 5 | 1 (break/continue panic → MIRPanic) | 0 | 4 | 4 |
| LIR Lowering | 5 | 0 | 0 | 5 | 4 |
| Pass 管理器 | 3 | 1 (Pass 异常处理) | 0 | 2 | 4 |
| C 运行时 | 13 | 2 (HTTP 命令注入移除, 部分 RC 修复) | 1 (list/map 更新) | 10 | 6 |
| 测试 | 6 | 0 | 1 (部分新测试) | 5 | 3 |
| Tree-sitter | 3 | 0 | 0 | 3 | 4 |
| **总计** | **111** | **22 (19.8%)** | **8 (7.2%)** | **81 (73.0%)** | **88** |

### 八轮审查修复趋势

| 轮次 | 严重问题 | 中等问题 | 轻微问题 | 修复率 | 新增问题 |
|------|---------|---------|---------|--------|---------|
| 第一轮 | 35 | 42 | 28 | - | 105 |
| 第二轮 | 28 | 35 | 22 | 18% | 85 |
| 第三轮 | 22 | 28 | 18 | 22% | 68 |
| 第四轮 | 18 | 22 | 15 | 25% | 55 |
| 第五轮 | 15 | 18 | 12 | 28% | 45 |
| 第六轮 | 12 | 15 | 10 | 30% | 37 |
| 第七轮 | 10 | 12 | 8 | 35% | 30 |
| 第八轮 | 42 | 38 | 25 | 19.8% | 105 |

> **说明**：第八轮采用更严格的标准和更深入的逐行审查，新发现问题数量增加，历史问题修复率下降。这表明前几轮对"已修复"的判断可能过于乐观，第八轮重新发现了大量此前被遗漏的问题。

### P0 级问题（必须立即修复）

1. **VM 闭包捕获整个帧**（vm.py:807-810）—— 连续八轮未修，函数式语言核心语义错误
2. **VM while 循环 JUMP 启发式**（vm.py:693-701）—— 连续八轮未修，运行时扫描字节码
3. **编译器无 else if 栈泄漏**（compiler.py:693-703）—— 新发现，严重影响 if 表达式语义
4. **编译器嵌套循环 break/continue**（compiler.py:490-506）—— 连续多轮未修
5. **求值器环境恢复不在 finally**（evaluator.py:751-761,433-455,989-1006）—— 系统性缺陷
6. **类型检查器 TypeVar 万能兼容**（type_checker.py:1272-1273）—— 类型安全形同虚设
7. **C 运行时引用计数不递归**（nova_runtime.c:749-798）—— 内存泄漏
8. **C 运行时 GC 空壳**（nova_runtime.c:99-102）—— 循环引用永不释放
9. **MIR match 完全退化**（mir_lowering.py:351-384）—— 模式匹配语义完全错误
10. **MIR 闭包自由变量丢失**（mir_lowering.py:247-250）—— 闭包完全不可用

### 架构级建议

1. **统一 Evaluator 与 VM 的闭包捕获语义**（推荐值语义快照）
2. **删除 VM 的所有启发式控制流检测**，改为编译器显式编码
3. **重写类型检查核心**，实现真正的 Hindley-Milner Algorithm W
4. **修复 LIR Lowering 的 Branch/Switch/Match 降级**，这是多个后端 Branch 错误的共同根源
5. **为 C 后端引入引用计数 + 循环引用检测**，或实现真正的分代 GC
6. **引入端到端测试框架**，至少对 C 后端做编译-运行-验证
7. **统一 Tree-sitter 与 parser.py 语法**，消除"多个真相来源"

---

