

> **审查标准**：生产级编译器/语言标准（参考 OCaml/Haskell/Elm/F# 最佳实践）
> **审查时间**：2026-07-14（第一轮）, 2026-07-15（第二轮~第十一轮）, 2026-07-15（第十二轮）, 2026-07-15（第十三轮）, 2026-07-15（第十四轮）, 2026-07-15（第十五轮）, 2026-07-15（第十六轮）, 2026-07-15（第十七轮）, 2026-07-15（第十八轮）, 2026-07-15（第十九轮）
> **审查版本**：main 分支最新提交

---

## 项目结构审查表

| 模块 | 文件 | 审查状态 | 上次审查 | 严重问题数 | 中等问题数 | 轻微问题数 |
|------|------|---------|---------|-----------|-----------|-----------|
| VM 虚拟机 | `vm.py` | ✅ 已审查 | 2026-07-15(第十九轮) | 26 | 30 | 21 |
| 编译器 | `compiler.py` | ✅ 已审查 | 2026-07-15(第十九轮) | 17 | 25 | 24 |
| 求值器 | `evaluator.py` | ✅ 已审查 | 2026-07-15(第十九轮) | 15 | 22 | 24 |
| AST 节点 | `ast_nodes.py` | ✅ 已审查 | 2026-07-15(第九轮) | 0 | 0 | 0 |
| 类型检查器 | `type_checker.py` | ✅ 已审查 | 2026-07-15(第十九轮) | 22 | 25 | 22 |
| 词法分析器 | `lexer.py` | ✅ 已审查 | 2026-07-15(第十九轮) | 8 | 24 | 24 |
| 语法分析器 | `parser.py` | ✅ 已审查 | 2026-07-15(第十九轮) | 16 | 28 | 24 |
| 错误处理 | `errors.py` | ✅ 已审查 | 2026-07-15(第十九轮) | 8 | 15 | 16 |
| 模块系统 | `modules.py` | ✅ 已审查 | 2026-07-15(第十九轮) | 13 | 17 | 16 |
| 环境 | `environment.py` | ✅ 已审查 | 2026-07-15(第十九轮) | 5 | 10 | 12 |
| C 代码生成 | `c_codegen.py` | ✅ 已审查 | 2026-07-15(第十九轮) | 9 | 18 | 16 |
| Native 后端 | `backend/native_backend.py` | ✅ 已审查 | 2026-07-15(第十九轮) | 12 | 15 | 9 |
| Cranelift 后端 | `backend/cranelift_backend.py` | ✅ 已审查 | 2026-07-15(第十九轮) | 13 | 11 | 6 |
| WASM 后端 | `backend/wasm_backend.py` | ✅ 已审查 | 2026-07-15(第十九轮) | 10 | 9 | 8 |
| x86_64 指令发射 | `backend/x86_64.py` | ✅ 已审查 | 2026-07-15(第十九轮) | 4 | 5 | 5 |
| 编译管道 | `backend/compiler_pipeline.py` | ✅ 已审查 | 2026-07-15(第十九轮) | 7 | 5 | 5 |
| IR 节点 | `ir/ir_nodes.py` | ✅ 已审查 | 2026-07-15(第十九轮) | 0 | 5 | 10 |
| HIR Lowering | `ir/hir_lowering.py` | ✅ 已审查 | 2026-07-15(第十九轮) | 6 | 10 | 12 |
| MIR Lowering | `ir/mir_lowering.py` | ✅ 已审查 | 2026-07-15(第十九轮) | 14 | 14 | 10 |
| LIR Lowering | `ir/lir_lowering.py` | ✅ 已审查 | 2026-07-15(第十九轮) | 13 | 13 | 10 |
| Pass 管理器 | `ir/pass_manager.py` | ✅ 已审查 | 2026-07-15(第十九轮) | 7 | 12 | 12 |
| C 运行时 | `runtime/nova_runtime.c` | ✅ 已审查 | 2026-07-15(第十九轮) | 19 | 20 | 14 |
| 测试套件 | `tests/` | ✅ 已审查 | 2026-07-15(第十九轮) | 5 | 14 | 11 |
| Tree-sitter | `tree-sitter-nova/` | ✅ 已审查 | 2026-07-15(第十九轮) | 7 | 11 | 8 |

---

## 审查记录

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


## [2026-07-15] 第九轮全局审查报告

### 第九轮新发现 vs 历史问题修复状态

| 类别 | 历史问题数 | 已修复 | 部分修复 | 未修复 | 新发现 |
|------|-----------|--------|---------|--------|--------|
| VM | 10 | 1 (id()替换) | 1 (CONTINUE操作数) | 8 | 10 |
| 编译器 | 13 | 2 (PatternTuple/List, &&/\|\|) | 1 (while break/continue) | 10 | 13 |
| 求值器 | 15 | 3 (递归深度, ++, head/tail) | 1 (顶层?) | 11 | 18 |
| 类型检查器 | 20 | 3 (ADTType.__eq__, MapExpr, ErrorCollector) | 1 (PatternConstructor) | 16 | 15 |
| Lexer/Parser | 17 | 6 (非法字符, 未闭合字符串, MapExpr, PatternChar, match guard, PatternTuple/List) | 0 | 11 | 22 |
| 错误/模块/环境 | 22 | 1 (clear_cache) | 1 (NameError) | 20 | 15 |
| C 后端 | 11 | 1 (闭包捕获) | 1 (TryExpr字段名) | 9 | 10 |
| Native 后端 | 12 | 2 (LIRCallIndirect, LIRReturn callee-saved) | 1 (寄存器分配) | 9 | 12 |
| Cranelift 后端 | 15 | 0 | 0 | 15 | 12 |
| WASM 后端 | 15 | 0 | 0 | 15 | 11 |
| 编译管道 | 5 | 0 | 0 | 5 | 4 |
| HIR Lowering | 7 | 0 | 0 | 7 | 5 |
| MIR Lowering | 14 | 1 (break/continue) | 0 | 13 | 8 |
| LIR Lowering | 14 | 0 | 0 | 14 | 8 |
| Pass 管理器 | 10 | 1 (Pass异常处理) | 0 | 9 | 5 |
| C 运行时 | 19 | 2 (HTTP注入, 部分RC) | 1 (list/map更新) | 16 | 13 |
| 测试 | 13 | 0 | 1 (部分新测试) | 12 | 13 |
| Tree-sitter | 6 | 0 | 0 | 6 | 8 |
| **总计** | **258** | **22 (8.5%)** | **8 (3.1%)** | **206 (79.8%)** | **192** |

> 第九轮采用更深入逐行审查，新发现问题数量增加。修复率从 19.8% 下降到 8.5%，说明前几轮"已修复"判断过于乐观。**核心架构级问题（闭包捕获、VM 启发式控制流、类型推断非 HM、IR 降级退化）连续九轮未修复。**

---

## [2026-07-15] VM 虚拟机 (vm.py) 第九轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 栈式 VM 设计标准；while 循环启发式检测有创意但属反面教材 |
| 可行性 | ⭐⭐ | 简单程序可运行，但闭包捕获、循环控制、短路求值等核心功能有根本性缺陷 |
| 正确性 | ⭐ | 10+ 个 P0 级 bug：闭包过度捕获、CONTINUE 首次崩溃、AND/OR 非短路、STORE_VAR 静默创建全局 |
| 安全性 | ⭐ | 无输入验证、任意文件 I/O、无沙箱、栈操作无边界检查 |
| 一致性 | ⭐⭐ | 与 Evaluator 在 json_stringify、__hash__、短路求值、STORE_VAR、闭包捕获等方面存在严重行为差异 |
| 完整性 | ⭐⭐⭐⭐ | 全部 64 个操作码已实现，所有内置函数已注册 |
| 工程质量 | ⭐ | 启发式控制流、运行时状态猜测、三重指令处理、hasattr 动态属性、无不变量保护 |
| 性能 | ⭐⭐ | 无优化、dict 全帧拷贝、线性扫描、每条指令 if-elif 链（无跳转表） |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [vm.py:1165-1168] **DUP 指令无栈下溢检查** → 空栈时抛 Python IndexError 而非 Nova RuntimeError_ → 添加 `if not self.stack: raise RuntimeError_("VM stack underflow")`
- 追问：如果是 Haskell GHC 的 STG 机器栈管理有 bug，能被接受吗？→ **绝对不能**

- [vm.py:1008,1019,1030,1041,1052,1099,1113] **7 个模式匹配指令对空栈无保护** → 使用 `stack[-1]` 无检查，空栈时抛 Python IndexError → 所有 MATCH_TEST_* 指令添加空栈检查
- 追问：如果是 GHC 模式匹配失败时栈错乱，能被接受吗？→ **绝对不能**

- [vm.py:802-811] **CLOSURE 捕获整个帧的所有局部变量** → `dict(self.call_stack[-1].locals)` 浅拷贝全部 locals，时间 O(n)，阻止 GC，语义错误 → 编译器分析自由变量，CLOSURE 只捕获指定变量
- 追问：如果 OCaml 的闭包捕获了整个作用域的 dict 拷贝，性能影响能被接受吗？→ **绝对不能**（连续九轮未修）

- [vm.py:788-799] **CONTINUE 在 while 循环中 loop_start 可能为 None** → 虽有 `instr.operands` 优先逻辑，但当编译器未提供操作数且 `loop_info["loop_start"]` 为 None 时，`self.ip = None` 导致 TypeError → 添加防御性检查
- 追问：如果任何生产级语言的 continue 空实现/崩溃，能被接受吗？→ **绝对不能**

- [vm.py:698-702] **JUMP 启发式检测 while 循环** → VM 在运行时通过"JUMP 目标在前方 + 下一条指令是 CONST_UNIT"的启发式判断 while 循环回跳 → 编译器应显式编码循环起始位置
- 追问：如果生产编译器用运行时启发式检测控制流，能被接受吗？→ **绝对不能**（连续九轮未修）

- [vm.py:809] **闭包使用 `dict()` 浅拷贝共享可变引用** → list/dict 值被闭包和帧共享，修改互相影响 → 使用不可变数据结构或深拷贝

- [vm.py:1189-1199] **TRY_UNWRAP 对非 ADT 值静默通过** → 栈顶是 `42`（普通 int）时，TRY_UNWRAP 不 pop 也不 push → 添加对非 ADT 值的处理或文档说明

- [vm.py:163-169,916-922,960-966] **循环迭代器状态跨函数共享** → `_for_iters`、`_while_loops` 是 VM 实例级共享状态，函数 A 调用函数 B 时混合循环状态 → 将循环状态放入 Frame 中
- 追问：如果 GHC 的循环状态不隔离，能被接受吗？→ **绝对不能**

- [vm.py:674-685] **AND/OR 非短路求值** → 编译器已对两侧求值后才执行 AND/OR，不存在短路语义，与 Evaluator 短路求值不一致 → 编译器应生成条件跳转指令
- 追问：如果 Haskell 的 `&&` 不短路，能被接受吗？→ **绝对不能**

- [vm.py:571-572] **STORE_VAR 对未定义变量静默创建全局** → `self.globals[name] = val` 不检查变量是否已定义，拼写错误会静默创建新全局 → 未定义时应抛 RuntimeError_

#### 中等问题（影响特定场景）

- [vm.py:436-440,482-490,822-827] HALT/AUTO_CALL_MAIN/RETURN 三重处理导致语义歧义
- [vm.py:868-872] INDEX 指令无类型检查和边界检查
- [vm.py:575-608] 运算指令无操作数类型检查
- [vm.py:418-426] base_sp 截断栈时不清理循环状态
- [vm.py:748-753] while BREAK 不清理 `_while_loops`
- [vm.py:737-746 vs evaluator.py:939-952] for 返回列表、while 返回 UNIT 语义不一致
- [vm.py:769-775] BREAK 无操作数时的前向扫描回退逻辑
- [vm.py:74-83,802-811] NovaClosure 存储函数名而非字节码引用
- [vm.py:181-217] 所有 lambda 内置函数无参数类型检查
- [vm.py:258-280] 文件 I/O 内置函数无沙箱限制

#### 轻微问题（代码质量）

- [vm.py:412-413] `hasattr(self, '_range_index')` 运行时属性检查
- [vm.py:180] read_line 不处理 EOFError
- [vm.py:188] sum 对空列表行为
- [vm.py:195,275-280] file_exists/list_dir 无路径类型检查

#### Evaluator vs VM 对比
| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| 闭包捕获 | 引用整个 Environment（链式查找） | dict(frame.locals) 浅拷贝整个帧 | ❌ 语义不同 |
| 短路求值 (AND/OR) | AST 层面短路 | 两侧均已求值 | ❌ |
| NovaADTValue.__hash__ | 缺失 | 有 (vm.py:70-71) | ❌ |
| json_stringify(Err) | 返回 None | 返回 JSON 对象 | ❌ |
| STORE_VAR 未定义变量 | 抛 RuntimeError_ | 静默创建全局 | ❌ |
| 布尔比较 | 允许 true < 1 | 报错 | ❌ |
| for 循环返回值 | 结果列表 | 结果列表 | ✅ |
| read_line EOF | 捕获返回 "" | 不捕获，Python EOFError 向上传播 | ❌ |

---

## [2026-07-15] 编译器 (compiler.py) 第九轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | MATCH_START/MATCH_END 框架、LOOP_END 复合指令、FOR_ITER/LOOP_END 分工设计有特色 |
| 可行性 | ⭐⭐⭐⭐ | 可完整编译所有 AST 节点并生成可执行字节码 |
| 正确性 | ⭐⭐ | 嵌套模式匹配解构错误、嵌套循环 break/continue 作用域混淆、HALT/AUTO_CALL_MAIN 顺序错误 |
| 安全性 | ⭐⭐⭐ | 模块冲突检测不完整、无类型保证穷尽的 match 默认 Unit |
| 一致性 | ⭐⭐⭐ | CLOSURE 操作数声明与使用不一致、存在死代码、CharLiteral 编译为 String |
| 完整性 | ⭐⭐⭐⭐ | AST 覆盖完整、模式匹配节点全覆盖、所有跳转正确回填 |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰；约 50 行死代码、缺少自由变量分析、注释与实现不一致 |
| 性能 | ⭐⭐ | 闭包捕获全部局部变量、不可达代码生成 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [compiler.py:253-254] **HALT 在 AUTO_CALL_MAIN 之前，后者不可达** → VM 碰到 HALT 就停止，AUTO_CALL_MAIN 永远不执行 → AUTO_CALL_MAIN 在前，HALT 在后
- 追问：如果 GHC 生成不可达的死代码指令，能被接受吗？→ **绝对不能**

- [compiler.py:490-498] **嵌套 for-in-while 中 BREAK 作用域混淆** → while 嵌套 for 时，for 中 BREAK 误用 `_while_end_stack` 被当作 while 的 BREAK → 引入统一循环上下文栈
- 追问：如果 GHC 对嵌套循环的 break 作用域有 bug，能被接受吗？→ **绝对不能**

- [compiler.py:844-853] **嵌套 PatternTuple/PatternList 解构绑定错误** → `_compile_pattern_extract_and_bind` 对嵌套元组不生成解构指令，嵌套模式绑定整个元组到第一个变量 → 生成解构操作码或修改 VM 递归处理
- 追问：如果 GHC 的模式匹配编译不处理嵌套模式，能被接受吗？→ **绝对不能**

- [compiler.py:650-671] **无自由变量分析，闭包捕获全部 locals** → 编译器不做自由变量分析，每次创建闭包都复制整个局部环境 → 编译器应分析自由变量，CLOSURE 携带自由变量列表
- 追问：如果 OCaml 闭包转换不分析自由变量，能被接受吗？→ **绝对不能**

#### 中等问题（影响特定场景）

- [compiler.py:987-1016] while 中 BREAK 跳转到 CONST_UNIT 之前，栈可能不平衡
- [compiler.py:81] CLOSURE 操作数声明（3个）与使用（2个）不一致
- [compiler.py:857-907] 约 50 行完全不可达的死代码（`_compile_pattern_test` 和 `_compile_pattern_bindings`）
- [compiler.py:420-421] CharLiteral 编译为 CONST_STRING，类型信息丢失
- [compiler.py:604-607] PIPE_CALL 0 时栈布局需 VM 验证

#### 轻微问题（代码质量）

- [compiler.py:268-270] ExportDecl 被完全忽略
- [compiler.py:361-368] 模块导入冲突检测不检查 let/mut 绑定
- [compiler.py:745-748] match 全失败静默返回 Unit 而非报错
- [compiler.py:987-1016] while 返回值与规范不一致

#### 原创性分析

- **Nova 特色**：MATCH_START/MATCH_END 框架、LOOP_END 复合指令（弹出+追加+跳回三合一）、FOR_ITER/LOOP_END 职责分离、REGISTER_CTOR 将 ADT 构造器统一为可调用函数
- **参考已有**：基本栈式 VM 编译器设计

---

## [2026-07-15] 求值器 (evaluator.py) 第九轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 闭包引用捕获+作用域链设计有特色，两遍扫描支持前向引用 |
| 可行性 | ⭐⭐⭐⭐ | 整体架构可行，但系统性异常安全问题需要全面修复 |
| 正确性 | ⭐⭐ | 4 个严重 bug（作用域泄漏、TryExpr 崩溃、异常类型错误、ADT 不可哈希） |
| 安全性 | ⭐⭐ | Block/match/函数调用的作用域泄漏是系统性安全缺陷 |
| 一致性 | ⭐⭐⭐ | 与 VM 有多处行为差异（布尔比较、闭包捕获、json_parse） |
| 完整性 | ⭐⭐⭐⭐ | AST 覆盖完整，所有模式类型均支持，内置函数丰富 |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰，但 eval_decl 重复、缺乏异常安全的 try/finally |
| 性能 | ⭐⭐⭐ | ++ 运算符 O(n) 拼接、递归 AST 遍历 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [evaluator.py:751-761] **Block 表达式异常不安全，作用域泄漏** → `self.env = old_env` 不在 finally 中，异常时环境永久破坏 → 所有环境切换必须用 try/finally
- 追问：如果 OCaml 运行时异常后作用域泄漏，能被接受吗？→ **绝对不能**

- [evaluator.py:988-1007] **match 守卫和分支体异常不安全** → 环境切换不在 finally 中 → 添加 try/finally

- [evaluator.py:437-455] **_call_fn 环境恢复不在 finally 中** → finally 只恢复 _call_depth，RuntimeError_ 传播时 self.env 不恢复 → 将 `self.env = old_env` 放入 finally

- [evaluator.py:712-720] **TryExpr(?) 在非函数上下文崩溃** → 抛 ReturnSignal 但无对应 except 捕获 → 在 eval_program 中处理顶层 ReturnSignal

#### 中等问题（影响特定场景）

- [evaluator.py:778-781] Assignment 捕获错误的异常类型（Python RuntimeError 而非 RuntimeError_）
- [evaluator.py:567-608] eval_decl 重复代码且与 _collect_decl 不一致
- [evaluator.py:59-78] NovaADTValue 缺少 __hash__ 方法
- [evaluator.py:439-443] 递归深度限制不防护 AST 遍历递归
- [evaluator.py:877-878] ++ 运算符 O(n) 字符串拼接
- [evaluator.py:214-224] head/tail None variant field_names=["value"] 错误

#### 轻微问题（代码质量）

- [evaluator.py:1022-1029] PatternString/PatternChar 匹配歧义
- [evaluator.py:972-976] list comprehension 中 continue + finally 可读性差
- [evaluator.py:939-952] while + break 返回值语义
- [evaluator.py:270-273] json None field_names 不一致

#### Evaluator vs VM 对比
| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| Block 异常安全 | 无 finally，作用域泄漏 | VM 用栈，无此问题 | N/A |
| TryExpr 非函数上下文 | 崩溃（ReturnSignal 未捕获） | 通过 _execute_instruction 返回 True 工作 | ❌ |
| Assignment 异常类型 | 捕获 Python RuntimeError（无效） | 直接赋值到 locals/globals | ❌ |
| NovaADTValue.__hash__ | 缺失 | 有 | ❌ |
| 闭包捕获 | 引用整个 Environment | dict(frame.locals) 浅拷贝整个帧 | ❌ |
| head/tail None | field_names=["value"]（错误） | field_names=["value"]（错误） | ❌（共同 bug） |

---

## [2026-07-15] 类型检查器 (type_checker.py) 第九轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 两遍扫描+ErrorCollector+部分应用支持有设计思考 |
| 可行性 | ⭐⭐ | 有标注函数类型检查基本可用；无标注函数的类型推断因 TypeVar 万能兼容几乎不可用 |
| 正确性 | ⭐⭐ | TypeVar 万能兼容导致类型安全形同虚设；let 多态缺失；occurs check 缺失 |
| 安全性 | ⭐ | TypeVar 万能兼容意味着任何表达式都可被赋予任何类型 |
| 一致性 | ⭐⭐⭐ | 类型表示层一致；TypeVar "万能" 语义与 "类型变量" 名称矛盾 |
| 完整性 | ⭐⭐⭐ | Pattern 检查完整；类型标注覆盖全面；缺 exhaustiveness checking |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰；check_expr 方法过长 |
| 性能 | ⭐⭐⭐⭐ | O(n) 遍历，无复杂约束求解 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [type_checker.py:1272-1273] **TypeVar 万能兼容 — 类型安全形同虚设** → `if isinstance(a, TypeVar) or isinstance(b, TypeVar): return True` 使任何 TypeVar 与任何类型兼容 → 实现真正的 unification 算法
- 追问：如果 OCaml 的类型推断器对某些表达式推断失败，能被接受吗？→ **绝对不能。** 这等于废除了整个类型系统（连续九轮未修）

- [type_checker.py:772-782] **未实现 let 多态（无泛化/实例化）** → `let id = fun x -> x in id 1 + id "a"` 静默通过 → 实现 generalize/instantiate
- 追问：如果 OCaml 的 let 多态没有正确实现，能被接受吗？→ **绝对不能**

- [type_checker.py:1142-1162] **类型推断无 Occurs Check** → 递归类型导致无限替换 → 添加 occurs check

- [type_checker.py:287] **None 构造函数的 TypeVar 未绑定** → Some 和 None 各自使用独立 TypeVar("opt_t")，Option[String] == Option[Int] 因 TypeVar 万能兼容偶然通过 → 实现 Scheme + instantiate

- [type_checker.py:740-743] **泛型函数的 TypeVar callee 允许任意调用** → 未类型化函数可被以任意参数调用 → 应将 TypeVar 约束为 FnType

- [type_checker.py:677-689] **模式匹配穷尽性检查完全缺失** → 不检查是否所有变体被覆盖 → 实现 exhaustiveness checking
- 追问：如果 GHC 不做模式匹配穷尽性检查，能被接受吗？→ **不能**

- [type_checker.py:1084-1089] **== / != 不做类型检查** → `42 == "hello"` 静默通过 → 检查操作数类型兼容性

- [type_checker.py:1064-1068] **运算符错误后返回 INT_T 而非 ERROR_TYPE** → 掩盖后续类型错误 → 改为返回 ERROR_TYPE

#### 中等问题（影响特定场景）

- [type_checker.py:722-739] FnCall 的 _collect_type_bindings 是 unification 的劣质替代
- [type_checker.py:748-763] PipeExpr 管道运算符类型检查使用 `or` 逻辑过于宽松
- [type_checker.py:911] ForExpr 循环变量类型是孤立的 TypeVar
- [type_checker.py:939] ListComprehension 循环变量类型是孤立的 TypeVar
- [type_checker.py:604-609] Identifier 查找返回未约束 TypeVar，多次使用无法实例化
- [type_checker.py:288-293] Ok/Err 的 TypeVar 实例不共享
- [type_checker.py:905-907] ForExpr 对非列表迭代器不检查类型

#### 原创性分析

- **Nova 特色**：两遍扫描策略（先收集声明再检查函数体）、ErrorCollector 设计
- **参考已有**：类型表示层（ADTType, FnType, TypeVar 等）参考 OCaml/Elm 类型系统设计
- **已修复确认**：ADTType.__eq__ 已正确比较类型参数（L1）；Pattern 全 10 种类型已实现（L2）；ErrorCollector 已真正实现（L3）

---

## [2026-07-15] 词法分析器 (lexer.py) + 语法分析器 (parser.py) 第九轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 表达式导向设计、`{}` 歧义解决方案有创意 |
| 可行性 | ⭐⭐⭐ | 核心功能可用；`\|>` 优先级与 grammar.js 不一致 |
| 正确性 | ⭐⭐ | 管道优先级错误、转义序列后 EOF 崩溃、`<-` 与 `< -` 歧义 |
| 安全性 | ⭐⭐⭐ | 错误恢复基本完善，但 IndexError 崩溃 |
| 一致性 | ⭐⭐⭐ | 死 Token、BOOL 冗余分支、parser 与 grammar.js 优先级不一致 |
| 完整性 | ⭐⭐⭐⭐ | 模式匹配语法完整，缺少 or-pattern、spread 模式、多行注释 |
| 工程质量 | ⭐⭐⭐ | 递归下降结构清晰、结合性全部正确、无左递归 |
| 性能 | ⭐⭐⭐⭐ | O(n) 线性扫描；_is_map_literal 最坏 O(n) 前瞻 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [parser.py:428-678] **`\|>` 优先级与 grammar.js 完全不一致** → parser.py 中 `|>` 在比较和 `++` 之间，grammar.js 中 `|>` 是最低优先级运算符 → 将 `_parse_pipe` 提升到 `_parse_for_while_expr` 和 `_parse_if_expr` 之间
- 追问：如果 GCC 的运算符优先级与官方规范不一致，能被接受吗？→ **绝对不能**（连续九轮未修）

#### 中等问题（影响特定场景）

- [lexer.py:236-251] `_read_string` 未处理文件末尾的转义序列（IndexError）
- [lexer.py:284-298] `_read_char` 同样未处理文件末尾的转义序列
- [parser.py:464-466] `<-` 与 `< -` 歧义（for x < -5 被错误解析为范围循环）
- [parser.py:335-346] `Fn[...]` 类型语法缺少返回类型
- [parser.py:460-474] for 循环 step 被重复存储
- [lexer.py:88,91] PIPE_VARIANT 和 UNIT 是死 Token
- [lexer.py:155-160] `_make_error` 从未被调用（死代码）
- [parser.py:838-878] `_is_map_literal` 每次遇到 `{` 都 O(n) 前瞻扫描

#### 轻微问题（代码质量）

- [lexer.py:328-331] `_read_identifier` 中 BOOL 分支冗余
- [parser.py:950-982] 列表推导式范围变体缺少 step 支持
- lexer.py/parser.py 无块注释 `/* ... */` 支持

---

## [2026-07-15] 错误处理 (errors.py) + 模块系统 (modules.py) + 环境 (environment.py) 第九轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 错误格式化借鉴 Rust 风格，控制流信号有独立设计 |
| 可行性 | ⭐⭐⭐⭐ | 整体可工作，但路径安全、环境递归深度需修复 |
| 正确性 | ⭐⭐⭐ | NameError 死代码路径、静默吞错误、loading_stack 用 list.remove |
| 安全性 | ⭐⭐ | 缺少路径遍历防护（符号链接）、任意文件读取 |
| 一致性 | ⭐⭐⭐ | IR 错误类型脱离体系、部分环境方法用 NameError 部分用 RuntimeError_ |
| 完整性 | ⭐⭐⭐ | 有基本错误分类但缺 NameError/ImportError/Error Code |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰但存在冗余（空分支、重复方法） |
| 性能 | ⭐⭐⭐⭐ | 环境查找 O(d)，模块缓存合理 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [errors.py:82-106] **缺少独立的 NameError 类型** → "未定义变量"和"除零错误"是同一 RuntimeError_ → 新增 UndefinedNameError 子类
- 追问：如果 Rust 编译器的错误信息缺少源码上下文，能被接受吗？→ **绝对不能**

- [modules.py:107-140] **缺少路径规范化（path traversal）防护** → 未用 `os.path.realpath()` 处理符号链接 → 所有路径用 `os.path.realpath()` 解析

- [modules.py:56-57] **导出查找失败静默吞掉** → `except (NameError, RuntimeError_): pass` 隐藏模块导出错误 → 至少记录警告

#### 中等问题（影响特定场景）

- [errors.py:159] `source_code.split('\n')` 未处理 CRLF 混合格式
- [errors.py:265-283] 多行高亮下划线缺少 `|` 标记
- [errors.py:134-136] 无源码上下文时的降级格式太简陋
- [errors.py:290-327] 缺少 ImportError/ModuleError 类型和错误码
- [errors.py:405-411] `raise_all()` 将后续错误作为 note 附加，丢失独立诊断
- [modules.py:84-105] search_paths 硬编码且无验证
- [modules.py:118-121] 绝对路径导入无安全校验
- [modules.py:187] loading_stack 使用 file_path 字符串比较（符号链接问题）
- [modules.py:271-274] 循环导入时用 `list.remove()` 而非 `list.pop()`
- [modules.py:276-291] `_collect_exports` 大量空分支
- [modules.py:293-299] `_collect_exported_types` 与 `_collect_exports` 完全重复
- [environment.py:40] `RuntimeError_` 未携带源码位置
- [environment.py:50-61] `assign` 递归实现可能触发 Python RecursionError

---

## [2026-07-15] 所有后端第九轮审查报告

### LIR 指令覆盖对比表

| LIR 指令 | Native | Cranelift | Wasm | C 后端 |
|----------|:------:|:---------:|:----:|:------:|
| LIRLoadConst | ✅ | ✅ | ✅ | N/A |
| LIRLoadGlobal | ✅ | ✅ | ❌ | N/A |
| LIRStoreGlobal | ✅ | ❌ | ❌ | N/A |
| LIRLoadReg | ✅ | ✅ | ✅ | N/A |
| LIRStoreReg | ✅ | ⚠️空操作 | ⚠️空操作 | N/A |
| LIRBinOp | ✅ | ✅ | ✅ | N/A |
| LIRUnaryOp | ✅ | ✅ | ✅ | N/A |
| LIRCall | ✅ | ✅ | ⚠️不传参 | N/A |
| LIRCallIndirect | ✅ | ❌ | ❌ | N/A |
| LIRJump | ✅ | ✅ | ✅ | N/A |
| LIRBranch | ✅ | ⚠️语义错 | ⚠️语义错 | N/A |
| LIRReturn | ✅ | ✅ | ✅ | N/A |
| LIRLabel | ✅ | ✅ | ⚠️无end | N/A |
| LIRIndex | ✅ | ⚠️硬编码v0 | ⚠️语义错 | N/A |
| LIRFieldAccess | ✅ | ✅ | ⚠️语义错 | N/A |
| LIRBuildList | ✅ | ✅ | ✅ | N/A |
| LIRBuildTuple | ✅ | ✅ | ✅ | N/A |
| LIRBuildADT | ✅ | ✅ | ⚠️语义错 | N/A |
| LIRPanic | ✅ | ✅ | ✅ | N/A |

### 各后端评分

| 后端 | 综合评分 | 可生成可执行文件 | 能运行简单程序 |
|------|---------|:---:|:---:|
| Native (x86_64) | ⭐⭐ (1.4/5) | ❌ 必崩 | ❌ |
| Cranelift | ⭐⭐ (1.5/5) | ❌ 无编译工具 | ❌ |
| WasmGC | ⭐ (1.3/5) | ❌ WAT 不合法 | ❌ |
| C | ⭐⭐⭐ (2.8/5) | ⚠️ 需 runtime | ⚠️ 需手动链接 |

### 发现的问题

#### 严重问题（阻碍正常使用）

**Native 后端**：
- [native_backend.py:340-389] 寄存器分配器（LinearScanAllocator）定义但从未调用，贪心分配有根本缺陷
- [native_backend.py:410-485] 浮点二元操作使用整数指令
- [native_backend.py:734-798] 栈分配的数据在函数返回后无效（悬垂指针）
- [native_backend.py:383-389] 循环中寄存器不回收，后续迭代全错
- [native_backend.py:340,522] double epilogue 导致返回路径错误

**Cranelift 后端**：
- [cranelift_backend.py:274-276] 调用不存在的 `clif-util compile` 工具
- [cranelift_backend.py:162-168] LIRBranch 生成的 Cranelift IR 语义错误
- [cranelift_backend.py:234] LIRBinOp 不区分整数/浮点操作

**Wasm 后端**：
- [wasm_backend.py:229-297] 栈机语义完全错误——不操作值栈
- [wasm_backend.py:231-232] LIRLabel 生成的 block 缺少 end
- [wasm_backend.py:273-276] LIRBuildADT 不写入字段值
- [wasm_backend.py:279-282] 字段访问类型大小不匹配

**C 后端**：
- [c_codegen.py:321,1082-1083] 列表/Map 元素强制 (void*)(intptr_t) 转换，只能存整数
- [compiler_pipeline.py:33-35] BACKEND_NATIVE 选择 Cranelift 而非 Native 后端

#### 追问
- 如果是 OCaml 的 native 编译器生成的代码不正确，能被接受吗？→ **绝对不能**

---

## [2026-07-15] IR 系统 + Pass 管理器第九轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 三层 IR 设计 | ⭐⭐⭐ | 三层分离理念正确，但 MIR 未形成真正 SSA，LIR 信息丢失严重 |
| AST-HIR 完整性 | ⭐⭐⭐ | 主要节点覆盖，但 PatternConstructor.type_name 丢失 |
| HIR-MIR 正确性 | ⭐ | Match 退化为跳转链、Lambda 丢失全部信息 |
| MIR-LIR 正确性 | ⭐⭐ | Switch/MatchJump/Branch 三个终结符全部退化 |
| 优化 Pass 质量 | ⭐⭐ | 常量折叠基本可用；Inlining 空壳 |
| Pass 异常处理 | ⭐ | 异常被 catch 后继续执行后续 pass |
| 代码工程质量 | ⭐⭐ | `__class__` 修改类型、大量 `or ""` None 隐式处理 |
| 总体可用性 | ⭐⭐ | 不含 match/lambda/闭包的简单算术程序可工作 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [mir_lowering.py:351-384] **MIR Match 降级完全退化为无条件跳转链** → 无论 scrutinee 是什么值，永远执行第一个 arm → 实现真正的 match 分支逻辑
- 追问：如果 GHC 的 STG→Cmm 将 match 退化为无条件跳转，能被接受吗？→ **绝对不能**

- [lir_lowering.py:231-235] **MIRSwitch 降级完全丢失所有 case 分支** → 只保留 default_target 的无条件跳转 → 实现 case 分支选择

- [lir_lowering.py:219-223] **MIRBranch 降级丢失 true/false target** → LIRBranch.true_label 和 false_label 从未赋值 → 赋值目标标签

- [mir_lowering.py:247-250] **Lambda 降级丢弃闭包体和自由变量** → 参数列表、函数体、捕获的自由变量全部被丢弃 → 完整实现 lambda 降级

- [mir_lowering.py:285-289] **ListComprehension 降级为空列表常量** → 结果永远返回 `[]` → 实现循环+过滤+映射逻辑

- [lir_lowering.py:237-241] **MIRMatchJump 降级完全丢失匹配逻辑** → variant_tests 被忽略 → 实现构造器匹配

- [pass_manager.py:720-726,736-741,750-756] **Pass 异常被静默吞掉后继续执行** → 损坏的 IR 上运行后续 pass 可能产生更多错误 → fail-fast：异常立即终止
- 追问：如果 LLVM 的 opt 工具静默吞掉所有 pass 异常，能被接受吗？→ **绝对不能**

#### 中等问题（影响特定场景）

- [lir_lowering.py:204-211] MIRPhi 降级只取第一个 source
- [mir_lowering.py:231-237] HIRFieldAccess 降级 field_index 始终为 0
- [lir_lowering.py:172-176] MIRMapBuild 降级为 LIRBuildList
- [lir_lowering.py:149-155] MIRClosureCreate 降级为字符串常量
- [pass_manager.py:262] Inlining pass 是空壳（return False）
- [pass_manager.py:266-293] DCE 在 HIR/MIR 层直接 return False
- [hir_lowering.py:328-330] PatternConstructor 降级时 type_name 丢失为空字符串
- [hir_lowering.py:205] TryExpr 降级为 HIRUnwrapExpr 丢失 early return 语义

---

## [2026-07-15] C 运行时 + 测试 + Tree-sitter 第九轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 内存安全 | ⭐ | GC 空壳，引用计数不递归，循环引用必然泄漏 |
| API 设计 | ⭐⭐ | 接口声明完整但行为语义不清晰 |
| 测试覆盖 | ⭐⭐ | Evaluator:VM 约 7:1，无跨后端一致性测试 |
| 测试质量 | ⭐⭐⭐ | 断言充分但存在死代码残留，边界条件覆盖不足 |
| Tree-sitter 一致性 | ⭐⭐⭐ | 基本运算符优先级一致，但缺少 while/break/continue/try/? 支持 |
| 代码质量 | ⭐⭐⭐ | 可读性好，注释充分 |
| 错误处理 | ⭐⭐⭐⭐ | panic/assert 宏设计合理 |
| 架构设计 | ⭐⭐⭐ | 头文件结构清晰，但 GC 抽象层次混乱 |

### C 运行时发现的问题

#### 严重问题（阻碍正常使用）

- [nova_runtime.c:99-103] **nova_gc_collect() 是空壳函数** → 不执行任何回收，循环引用永久泄漏 → 实现真正的 GC 或移除 API 声明
- 追问：如果 GHC 声明有 GC 但实际从不运行，能被接受吗？→ **绝对不能**（连续九轮未修）

- [nova_runtime.c:749-756] **nova_adt_release() 不递归释放字段** → ADT 中的 NovaString/NovaList/NovaADT 堆对象全部泄漏 → 递归 release

- [nova_runtime.c:479-486] **nova_list_release() 不递归释放元素** → 列表元素引用计数永不递减 → 递归 release 或文档明确声明

- [nova_runtime.c:370-388] **nova_list_concat() 浅拷贝元素不 retain** → 原列表释放后新列表的元素指针悬挂 → 拼接时 retain 所有元素

### 测试发现的问题

#### 严重问题（阻碍正常使用）

- **无 Evaluator 与 VM 行为一致性对比测试** → 两条执行路径对同一程序可能产生不同结果但无任何测试验证 → 选取代表性程序同时用两条路径运行并断言结果相同
- 追问：如果 GHC 缺少核心语言特性的测试，能被接受吗？→ **绝对不能**

- **无 mut 变量的 reassignment 测试** → test_mut_binding 只检查初始值，不检查后续赋值
- **无 C 运行时与 Python 端行为一致性测试**

#### 中等问题

- 无嵌套 ADT + match 求值器测试
- 无 Map 字面量和 Map 操作测试
- 无 Result unwrap-on-err 的 panic 测试
- 无泛型函数测试
- 无浮点除法测试

### Tree-sitter 发现的问题

#### 严重问题

- [grammar.js] **不支持 while 和 break/continue** → parser.py 支持但 Tree-sitter 不支持 → 添加 while_expr 规则

#### 中等问题

- [grammar.js] 不支持 try/throw 表达式
- [grammar.js] 不支持 `?` 操作符
- [grammar.js] `|>` 优先级与 parser.py 基本一致但与 if 控制流交互可能不同

---

## [2026-07-15] 第九轮 P0 级问题更新

| # | 问题 | 模块 | 状态 |
|---|------|------|------|
| 1 | CLOSURE 捕获整个帧 | vm.py, compiler.py | 连续九轮未修 |
| 2 | TypeVar 万能兼容 | type_checker.py | 连续九轮未修 |
| 3 | let 多态未实现 | type_checker.py | 连续九轮未修 |
| 4 | VM while 启发式检测 | vm.py | 连续九轮未修 |
| 5 | `|>` 优先级不一致 | parser.py vs grammar.js | 连续九轮未修 |
| 6 | C 运行时 GC 空壳 | nova_runtime.c | 连续九轮未修 |
| 7 | C 运行时引用计数不递归 | nova_runtime.c | 连续九轮未修 |
| 8 | MIR match 完全退化 | mir_lowering.py | 连续九轮未修 |
| 9 | LIR Branch/Switch/Match 退化 | lir_lowering.py | 连续九轮未修 |
| 10 | Evaluator 作用域泄漏（系统性） | evaluator.py | 新确认 |
| 11 | AND/OR 非短路求值 | vm.py, compiler.py | 新发现 |
| 12 | STORE_VAR 静默创建全局 | vm.py | 新发现 |
| 13 | 嵌套 PatternTuple/PatternList 解构错误 | compiler.py | 新发现 |
| 14 | Native 后端寄存器分配从未调用 | native_backend.py | 新发现 |
| 15 | Native 后端悬垂指针 | native_backend.py | 新发现 |
| 16 | Lambda 闭包自由变量丢失 | mir_lowering.py | 新发现 |
| 17 | Pass 异常静默吞掉 | pass_manager.py | 新发现（部分修复） |
| 18 | 所有后端无端到端测试 | tests/ | 连续九轮未修 |

### 第九轮架构级建议

1. **重写类型检查核心**：实现真正的 Hindley-Milner Algorithm W（unification + occurs check + generalize/instantiate）。这是类型系统的基础，所有其他类型问题都源于此。
2. **统一闭包语义**：Evaluator 用引用捕获（环境链），VM 用值快照（dict 拷贝）。必须选择一种并统一。推荐值语义快照 + 仅捕获自由变量。
3. **删除 VM 所有启发式控制流**：while 循环检测、CONTINUE 起始位置、BREAK 目标扫描——全部改为编译器显式编码。
4. **修复 IR 降级链**：MIR match/lambda/list-comp 的退化是所有后端（除 C 外）不可用的根源。
5. **实现真正的 GC 或明确标注"无 GC"**：当前 nova_gc_collect API 是欺骗性的。
6. **引入端到端测试**：Evaluator-VM 一致性测试、C 后端编译-运行-验证。
7. **统一 Tree-sitter 与 parser.py 语法**：补全 while/break/continue/try/?/throw。

---

## [2026-07-15 第十轮] VM 虚拟机审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 结构化 MATCH_START/MATCH_END 指令对设计独特；PIPE_CALL 统一管道调用优雅 |
| 可行性 | ⭐⭐⭐ | 主执行路径可用，但循环控制和闭包有根本性问题 |
| 正确性 | ⭐⭐ | 6个高危bug，CLOSURE/STORE_VAR/CONTINUE/BREAK全有问题 |
| 安全性 | ⭐⭐ | 栈下溢检查缺失，内置函数无类型/边界检查 |
| 一致性 | ⭐⭐ | 与Evaluator闭包语义根本不同，整数除法语义与OCaml不一致 |
| 完整性 | ⭐⭐⭐⭐ | 47个操作码全部处理，无缺失 |
| 工程质量 | ⭐⭐ | RETURN重复处理，死代码，启发式控制流 |
| 性能 | ⭐⭐ | 全量帧捕获、递归栈无TCO |

### 指令集完整性
Op 类定义 47 个操作码，`_execute_instruction` 全部处理，**无缺失**。

### 发现的问题

#### 严重问题（阻碍正常使用）

- [vm.py:812] **CLOSURE 捕获整个帧而非自由变量** → 闭包捕获所有 locals 的浅拷贝，语义错误、内存浪费、可变对象别名问题 → 实现自由变量分析，CLOSURE 指令携带捕获列表
- 追问：如果 OCaml 的闭包捕获整个作用域的 dict 拷贝，性能影响能被接受吗？→ **绝对不能**，OCaml 精确计算自由变量
- [vm.py:702] **while 循环使用启发式检测** → `target < self.ip && next == CONST_UNIT` 判断 while 回跳，非平凡代码会误判 → 编译器显式编码 loop_start 到 CONTINUE 指令操作数
- 追问：如果 Haskell GHC 的 STG 机器用启发式检测控制流，能被接受吗？→ **绝对不能**
- [vm.py:573] **STORE_VAR 静默创建全局变量** → 变量名拼写错误时不报错，直接创建新全局变量，违反函数式"无隐式状态"原则 → 检查 `name in self.globals` 且是 mutable，否则报"未定义变量"
- 追问：如果 OCaml 未绑定变量被静默创建为全局，能被接受吗？→ **绝对不能**
- [vm.py:791-802] **CONTINUE 在 while 中 loop_start 可能为 None** → 如果启发式检测未触发，loop_start 为 None，`self.ip = None` 导致崩溃 → 始终从操作数获取 loop_start，删除启发式
- [vm.py:772-778] **BREAK fallback 前向扫描** → 线性扫描后续指令直到 LOOP_END 或 CONST_UNIT，语义完全错误 → BREAK 操作数应直接编码跳转目标

#### 中等问题（影响特定场景）

- [vm.py:677-688] **AND/OR 非短路求值** → 两侧值已被求值压栈，`side_effect() && other()` 会导致副作用被错误执行 → 编译器用 POP_JUMP_IF_FALSE 实现短路，删除 AND/OR 操作码（死代码）
- [vm.py:755-756] **BREAK 在 while 循环中不清理栈** → 跳转前栈上有 body 返回值残留，后续代码读取错误值 → 跳转前清理到 base_sp
- [vm.py:871-875] **INDEX 无边界检查** → 越界索引产生 Python IndexError 而非 Nova RuntimeError_ → 添加边界检查
- [vm.py:1197-1198] **TRY_UNWRAP 传播到执行循环而非函数边界** → 与 Evaluator 传播到函数调用者的语义不一致 → 在函数内使用 return_flag，在顶层使用 error
- [vm.py:916-926,959-970] **异常退出时 _range_index/_list_index 字典条目可能泄漏** → BREAK 异常退出时迭代索引可能不清理 → 用 try/finally 保护
- [vm.py:1011,1022,1033,1044,1055,1102,1116] **MATCH_TEST_* 指令无栈空检查** → 栈为空时 peek 产生 Python IndexError → 添加栈空检查
- [vm.py:437+825] **RETURN 重复处理** → _execute_function 和 _execute_instruction 都有 RETURN 处理，控制流分支不重叠但代码冗余 → 统一为单一处理路径

#### 轻微问题（代码质量）

- [vm.py:601] **整数除法使用 Python `//`（地板除）** → `-7 // 2 = -4` 而非 OCaml 的 `-3`（截断除法）→ 使用 `int(a/b)` 或 `math.trunc(a/b)`
- [vm.py:204-217] **内置函数无参数/类型检查** → `sqrt("hello")` 产生 Python TypeError 而非 Nova 错误 → 添加类型和参数检查
- [vm.py:1171] **DUP 无栈空检查** → 栈为空时 IndexError → 添加检查
- [vm.py:916,959] **_range_index/_list_index 未在 __init__ 中初始化** → 使用 hasattr 动态创建 → 在 __init__ 中初始化

#### 原创性分析
- **独特**：MATCH_START/MATCH_END 结构化指令对、PIPE_CALL 统一管道调用约定、DUP+延迟 POP 的 match arm 模式
- **常规**：栈式字节码架构、常量池+跳转回填、帧式函数调用

#### Evaluator vs VM 对比
| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| 闭包捕获语义 | 引用语义（共享 Environment） | 值语义（dict 浅拷贝） | ❌ |
| 闭包捕获范围 | 全量（环境链） | 全量（locals 字典） | ✅（但机制不同） |
| 作用域链深度 | 任意深度 | 两层（locals + globals） | ❌ |
| ? 非 Option/Result | 静默返回原值 | 报错 | ❌ |
| Bool 与非 Bool 比较 | 允许 | 报类型错误 | ❌ |
| AND/OR 短路 | 正确短路（evaluator.py:848-858） | 非短路（但编译器可能不生成这些指令） | ⚠️ |
| for 返回值 | 结果列表 | 结果列表 | ✅ |
| while 返回值 | 最后一次迭代结果 | 最后一次迭代结果 | ✅ |
| 管道操作符 | f(pipe_value) | f(extra_args, pipe_value) | ✅ |
| 模式匹配 | 递归匹配，支持所有类型 | 字节码跳转，支持所有类型 | ✅ |
| 守卫条件 | 支持 | 支持 | ✅ |
| break/continue | 异常实现 | 字节码跳转 | ✅ |
| 整数除法 | // 地板除 | // 地板除 | ✅（但非 OCaml 语义） |
| 部分应用 | 委托式 | 独立 PartialBuiltin | ✅ |

---

## [2026-07-15 第十轮] 编译器审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | PIPE_CALL 管道统一调用、MATCH_START/END 结构化指令对 |
| 可行性 | ⭐⭐⭐ | 主路径可用，嵌套模式匹配和 while 循环有严重 bug |
| 正确性 | ⭐⭐ | 嵌套 PatternTuple/PatternList 不生成测试指令（P0） |
| 安全性 | ⭐⭐⭐ | import 冲突仅 warning |
| 一致性 | ⭐⭐⭐ | 栈布局基本与 VM 一致，BREAK 有栈泄漏 |
| 完整性 | ⭐⭐⭐⭐ | AST 节点全覆盖，所有 TypeExpr 正确擦除 |
| 工程质量 | ⭐⭐ | 死代码（旧版模式方法）、HALT/AUTO_CALL_MAIN 顺序可疑 |
| 性能 | ⭐⭐ | 无 TCO、无自由变量分析导致闭包全量捕获 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [compiler.py:865-878] **嵌套 PatternTuple/PatternList 不生成测试指令** → `match x { (1, 2) -> ... }` 只检查元组长度不检查元素值 → 重构为统一的 `_compile_full_pattern(pattern, fail_label)` 方法，递归生成测试和绑定
- 追问：如果 Haskell GHC 编译器跳过某些 Pattern 的测试代码生成，能被接受吗？→ **绝对不能**，这是 release blocker

#### 中等问题（影响特定场景）

- [compiler.py:402,671] **CLOSURE 指令操作数与定义注释不匹配** → 注释声明 3 个操作数（含 code_key），实际只用 2 个；同名函数跨模块冲突风险 → 更新注释或添加 code_key
- [compiler.py:319-370] **import 内联名称冲突检测不完整** → 只检查 functions 和 _builtin_names，不检查全局变量；冲突时仅 warning → 添加全局变量检查，冲突改为 error
- [compiler.py:494] **while 循环 BREAK 栈布局不一致** → BREAK 跳过 body POP，栈上残留返回值 → VM BREAK 处理中添加 base_sp 栈清理
- [compiler.py:805-813] **自由变量分析完全缺失** → VM 捕获整个帧而非自由变量 → 实现自由变量分析

#### 轻微问题（代码质量）

- [compiler.py:882-946] **`_compile_pattern_test` 和 `_compile_pattern_bindings` 是死代码** → 无任何调用者 → 删除
- [compiler.py:384,659] **无尾调用优化** → 深度递归栈溢出 → 长期实现 TCO
- [compiler.py:253-254] **HALT 在 AUTO_CALL_MAIN 之前** → 如果 VM 顺序执行，AUTO_CALL_MAIN 永远不执行 → 确认 VM 启动逻辑或交换顺序

#### 原创性分析
- **独特**：PIPE_CALL 统一管道调用（编译器重排参数 + VM 统一处理）、MATCH_START/END 结构化指令对、DUP+延迟 POP 的 match arm 模式
- **常规**：栈式字节码、跳转回填、常量池

---

## [2026-07-15 第十轮] 求值器审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 作用域链设计清晰，BreakSignal/ContinueSignal 异常机制干净 |
| 可行性 | ⭐⭐⭐⭐ | AST 节点全覆盖，主执行路径稳定 |
| 正确性 | ⭐⭐⭐ | 闭包引用语义与 VM 值语义不一致（P0），? 操作符行为差异 |
| 安全性 | ⭐⭐⭐ | 环境链正确隔离，嵌套循环 break/continue 正确 |
| 一致性 | ⭐⭐ | 闭包语义根本差异，? 非 Option/Result 行为不一致 |
| 完整性 | ⭐⭐⭐⭐ | 所有 AST 节点和 Pattern 类型全覆盖，守卫条件正确 |
| 工程质量 | ⭐⭐⭐⭐ | 代码清晰，try/finally 环境恢复模式一致 |
| 性能 | ⭐⭐ | 环境链查找递归实现，部分应用委托式调用有额外开销 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [evaluator.py:498-504,729-735] **闭包引用语义 vs VM 值语义** → Evaluator 捕获 Environment 引用（修改 mut 变量影响外部），VM 捕获 dict 浅拷贝 → 统一为值语义快照 + 仅捕获自由变量
- 追问：如果 OCaml 的解释器和字节码编译器对闭包行为不一致，能被接受吗？→ **绝对不能**，相当于 GCC 和 Clang 对同一 C 代码产生不同行为

#### 中等问题（影响特定场景）

- [evaluator.py:712-720] **`?` 对非 Option/Result 值静默返回** → VM 会报错，Evaluator 不报错 → 添加类型检查
- [evaluator.py:717] **`?` 在顶层代码中抛出未捕获的 ReturnSignal** → VM 也有此问题 → 添加顶层错误处理

#### 轻微问题（代码质量）

- [evaluator.py:890-897] **`< > <= >=` 缺少 Bool 类型检查** → `true < 1` 不报错（Python 语义） → 添加 Bool 类型检查
- [evaluator.py:778-781] **捕获 Python RuntimeError 的死代码** → Environment.assign 只抛 RuntimeError_ → 删除无用 try/except
- [evaluator.py:870-873] **整数除法使用 Python `//`（地板除）** → 与 VM 一致但非 OCaml 语义 → 使用截断除法

---

## [2026-07-15 第十轮] 类型检查器审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐ | 标准类型检查器设计，无独特创新 |
| 可行性 | ⭐ | 类型推断几乎不可用，TypeVar 兜底导致大部分类型检查失效 |
| 正确性 | ⭐ | 无真正 unification、无 let 多态、无 occurs check |
| 安全性 | ⭐ | TypeVar 万能兼容使类型系统形同虚设 |
| 一致性 | ⭐⭐ | 类型标注解析完整，ADT 类型参数比较正确 |
| 完整性 | ⭐⭐ | Pattern 类型检查完整，类型标注覆盖所有语法 |
| 工程质量 | ⭐⭐ | 代码可读，但核心算法缺失 |
| 性能 | ⭐⭐ | 线性搜索构造器、非 HM 算法 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [type_checker.py:1287-1288] **`_types_compatible` TypeVar 万能兼容** → `isinstance(a, TypeVar) or isinstance(b, TypeVar): return True` 导致所有含 TypeVar 的类型检查完全失效 → 实现 unification，TypeVar 通过绑定到具体类型来检查兼容性
- 追问：如果 Haskell 的 Maybe Int 和 Maybe String 被当作同一类型，能被接受吗？→ **绝对不能**
- [type_checker.py:779-789] **无 generalize/instantiate（let 多态缺失）** → `let id = fun x -> x in id 1 + id "a"` 不报错，泛型函数无法在不同调用点使用不同类型 → 实现 HM Algorithm W 的 generalize 和 instantiate
- 追问：如果 OCaml 的 let 多态没有正确实现，能被接受吗？→ **绝对不能**，这是 HM 类型系统的核心
- [type_checker.py:1157-1177] **无 occurs check** → `T = List[T]` 无限类型不被检测 → 在类型绑定中添加 occurs check
- [type_checker.py:1157-1177] **无真正 unification** → `_collect_type_bindings` 只是单向绑定收集，不处理冲突 → 实现标准 unification 算法

#### 中等问题（影响特定场景）

- [type_checker.py:740-750] **FnCall TypeVar 分支绕过 `_collect_errors`** → 非 collect 模式下错误被静默吞掉 → 统一使用 _report_error
- [type_checker.py:1218-1219] **循环别名检测被两遍扫描绕过** → `alias A = B; alias B = A` 不触发报错，产生错误类型 → 统一遍扫描或两遍都检测
- [type_checker.py:1135-1155] **`_substitute_type_vars` 不处理链式替换** → T1→T2, T2→Int 时 T1 仍为 T2 → 实现完整替换闭包
- [type_checker.py:922,950] **for 循环/列表推导元素类型为 TypeVar 兜底** → 循环体内元素类型检查被绕过 → 在循环体上下文中绑定具体元素类型

#### 轻微问题（代码质量）

- [type_checker.py:766-767] **PipeExpr 过于宽松** → 同时检查最后一个参数和第一个参数，任一匹配即通过 → 只检查最后一个参数
- [type_checker.py:1012-1021] **PatternConstructor 可能匹配错误 ADT** → 多 ADT 同名构造器用线性搜索，可能匹配到错误 ADT → 使用 (type_name, variant_name) 二元组查找

---

## [2026-07-15 第十轮] 词法/语法分析器审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 递归下降 + while 循环消除左递归是标准做法 |
| 可行性 | ⭐⭐⭐⭐ | 主解析路径稳定，悬挂 else 通过 `then` 关键字消除 |
| 正确性 | ⭐⭐ | **P0：`|>` 优先级严重错误** |
| 安全性 | ⭐⭐⭐ | 词法错误恢复合理（跳过非法字符继续分析） |
| 一致性 | ⭐⭐ | 与 grammar.js 有多处不一致（优先级、guard 位置、泛型） |
| 完整性 | ⭐⭐⭐ | 基本覆盖所有语法，缺多行注释/十六进制/科学计数法 |
| 工程质量 | ⭐⭐⭐ | 代码清晰，Span 追踪基本正确 |
| 性能 | ⭐⭐⭐⭐ | 递归下降 O(n) 解析 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [parser.py:672-678] **`|>` 管道操作符优先级严重错误** → `_parse_pipe` 被嵌套在 `_parse_comparison_expr` 下面，导致 `|>` 优先级高于比较运算符。`a |> f > b` 被解析为 `a |> (f > b)` 而非 `(a |> f) > b` → 将 `_parse_pipe` 调用移到 `_parse_or_expr` 中
- 追问：如果 GCC 的运算符优先级表错误，能被接受吗？→ **绝对不能**
- [parser.py:530-539 vs grammar.js:398-403] **match_arm guard 位置与 grammar.js 不一致** → parser.py 中 guard 在 `->` 前（`pattern if guard -> body`），grammar.js 中在 `->` 后（`pattern -> body if guard`）→ 统一为一种语法

#### 中等问题（影响特定场景）

- [lexer.py:155-160] **`_make_error` 是死代码** → 词法错误直接 append 字符串到 errors 列表，无 Span 信息 → 使用 _make_error 或创建 LexerError 对象
- [lexer.py:88] **`PIPE_VARIANT` Token 类型从未被生成** → 死代码 → 删除
- [lexer.py:252-258,262-267] **未闭合字符串/字符返回下一个 Token 而非错误占位** → Token 流中丢失错误位置 → 插入 ERROR Token 占位

#### 轻微问题（代码质量/功能缺失）

- [lexer.py:全文] **不支持多行注释 `/* */`** → 与 grammar.js 一致但生产级编译器应有
- [lexer.py:全文] **不支持十六进制 `0x...` 和科学计数法 `1.5e10`**
- [lexer.py:250-251] **未知转义序列静默保留不报 warning**
- [parser.py:221-228] **泛型 type 参数与 grammar.js 不一致** → grammar.js 不支持泛型参数
- [parser.py:189] **fn body 允许表达式，grammar.js 只允许 block**

---

## [2026-07-15 第十轮] 错误处理 + 模块 + 环境审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | Rust 风格错误格式化（ANSI + 上下文高亮）是好的设计参考 |
| 可行性 | ⭐⭐⭐ | 错误系统框架完整，ErrorCollector 可用 |
| 正确性 | ⭐⭐⭐ | 环境链实现正确，模块循环导入检测基本可用 |
| 安全性 | ⭐ | **模块系统存在路径遍历安全漏洞** |
| 一致性 | ⭐⭐ | 控制流信号放在 errors.py 违反单一职责 |
| 完整性 | ⭐⭐ | 缺少 ModuleError/ResolutionError 类型 |
| 工程质量 | ⭐⭐⭐ | 代码可读性好，但 Tab 处理和文件名缺失 |
| 性能 | ⭐⭐⭐ | 环境链递归查找在深层嵌套时可能栈溢出 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [modules.py:117-121,124-129] **路径遍历安全漏洞** → 绝对路径无限制（可 `import "/etc/passwd"`），相对路径 `..` 可遍历到任意目录 → 增加"允许的根目录"白名单
- 追问：如果 Rust 的模块系统允许导入任意系统文件，能被接受吗？→ **绝对不能**

#### 中等问题（影响特定场景）

- [errors.py:85-96] **NovaError 缺少 file_path 字段** → 错误信息无法显示文件名，用户无法区分同名文件 → 添加 file_path 参数
- [errors.py:186] **位置格式不符合编译器惯例** → `--> 第3行，第5列` 而非 `--> filename:3:5` → 改为机器可解析格式
- [errors.py:265-283] **Tab 字符导致下划线偏移** → `_compute_underline` 中空格数与实际显示位置不一致 → Tab 展开为空格后计算
- [modules.py:187,216-218] **循环导入检测用 List + `in`（O(n)）且路径未规范化** → 符号链接绕过检测 → 改用 Set + realpath
- [modules.py:293-299] **`_collect_exported_types` 与 `_collect_exports` 完全重复** → 代码冗余 → 删除，复用 _collect_exports
- [modules.py:276-291] **导出机制无时序保证** → export 在定义前时，运行时 lookup 可能失败 → 确认 eval_program 是否两遍扫描

#### 轻微问题（代码质量）

- [errors.py:330-351] **BreakSignal/ContinueSignal/ReturnSignal 放在 errors.py** → 不是错误类型，违反单一职责 → 移至 signals.py
- [errors.py:396-398] **ErrorCollector.get_all() 丢失时间顺序** → errors 排在 warnings 前，但实际交替出现 → 按添加顺序存储
- [errors.py:全文件] **无致命错误提前终止机制** → 缺少 Severity.FATAL → 增加 is_fatal 标志
- [environment.py:34-40,50-61] **lookup/assign 递归实现** → 深层嵌套可能 Python RecursionError → 改为循环实现
- [environment.py:40] **错误信息缺少源码位置** → "未定义变量"无行号列号 → 接受可选 span 参数
- [environment.py:全文件] **无 __slots__ 优化** → 每个绑定创建 BindingInfo 对象开销大 → 添加 __slots__

---

## [2026-07-15 第十轮] 所有后端审查报告

### 各后端 LIR 指令覆盖对比表

| LIR 指令 | Native | Cranelift | Wasm | C 后端 |
|----------|:------:|:---------:|:----:|:------:|
| LIRLoadConst | ✅ | ✅ | ✅ | N/A |
| LIRLoadGlobal | ✅ | ✅(part) | ❌ | N/A |
| LIRStoreGlobal | ✅ | ❌ | ❌ | N/A |
| LIRLoadReg | ✅ | ✅ | ✅ | N/A |
| LIRStoreReg | ✅ | ⚠️skip | ⚠️skip | N/A |
| LIRBinOp | ✅ | ⚠️int only | ✅ | N/A |
| LIRUnaryOp | ✅ | ✅ | ✅ | N/A |
| LIRCall | ✅ | ⚠️i64 args | ✅ | N/A |
| LIRCallIndirect | ✅ | ❌ | ❌ | N/A |
| LIRJump | ✅ | ✅ | ✅ | N/A |
| LIRBranch | ✅ | ⚠️hardcoded | ⚠️reversed | N/A |
| LIRReturn | ✅ | ✅ | ✅ | N/A |
| LIRLabel | ✅ | ⚠️no end | ⚠️no end | N/A |
| LIRIndex | ✅ | ⚠️hardcoded v0 | ⚠️no addr | N/A |
| LIRFieldAccess | ✅ | ✅ | ⚠️no base | N/A |
| LIRBuildList | ✅ | ⚠️no elems | ⚠️no elems | N/A |
| LIRBuildTuple | ✅ | ✅ | ✅ | N/A |
| LIRBuildADT | ✅ | ⚠️no fields | ⚠️no fields | N/A |
| LIRPanic | ✅ | ✅ | ✅ | N/A |

### 各后端综合评分

| 后端 | 指令覆盖 | 代码正确性 | 可行性 | Nova 语义对应 | 总分 |
|------|---------|-----------|--------|-------------|------|
| Native (x86_64) | 19/19 | 2/10 | Demo | 1/10 | ⭐⭐ (3/10) |
| Cranelift | 15/19 | 0/10 | 不可用 | 0/10 | ⭐ (1/10) |
| WasmGC | 17/19 | 1/10 | 不可用 | 1/10 | ⭐ (1.5/10) |
| C | AST 全覆盖 | 6/10 | 基本可用 | 6/10 | ⭐⭐⭐ (6/10) |

### 发现的问题

#### 严重问题（阻碍正常使用）

**Native 后端**（全部未修复）：
- [native_backend.py:202-211] 寄存器分配器定义但从未调用，使用简陋的 `_alloc_vreg` 贪婪策略
- [native_backend.py:410-485] 浮点二元操作使用整数指令
- [native_backend.py:734-798] 栈分配数据在函数返回后失效（悬垂指针）
- [native_backend.py:340,522] double epilogue 导致返回路径错误

**Cranelift 后端**（全部未修复）：
- [cranelift_backend.py:274-275] 调用不存在的 `clif-util compile` 工具
- [cranelift_backend.py:163-168] LIRBranch 硬编码 `block_false/block_true`
- [cranelift_backend.py:234] 不区分整数/浮点运算

**Wasm 后端**（全部未修复）：
- [wasm_backend.py:231-232] LIRLabel 生成的 block 缺少 end → WAT 语法错误
- [wasm_backend.py:273-276] LIRBuildADT 不写入字段值
- [wasm_backend.py:279-282] FieldAccess 栈不平衡（缺少 base 地址）
- [wasm_backend.py:161] NUL 终止符编码错误（`b"\\x00"` vs `b"\x00"`）

**C 后端**：
- [c_codegen.py:1082,1111等] 列表/Map 元素 `(void*)(intptr_t)` 强转只能存整数
- [c_codegen.py:590-600] Try 表达式使用不存在的 `variant_tag` 字段
- [c_codegen.py:707] 构造器模式字段名生成错误（`__field0` vs 实际字段名）

**Compiler Pipeline**：
- [compiler_pipeline.py:33-35] BACKEND_NATIVE 选择 Cranelift 而非 Native 后端（未修复）

- 追问：如果是 OCaml 的 native 编译器生成的代码不正确，能被接受吗？→ **绝对不能**

---

## [2026-07-15 第十轮] IR 系统 + Pass 管理器审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 三层 IR 设计 | ⭐⭐⭐ | 分层理念正确，但 MIR/LIR 降级语义丢失严重 |
| HIR 完整性 | ⭐⭐⭐ | 主要节点覆盖，PatternConstructor type_name 丢失 |
| MIR 正确性 | ⭐ | match 退化为跳转链、Lambda 丢失全部信息、Pipe 语义错误 |
| LIR 正确性 | ⭐ | Branch/Switch/MatchJump 三个终结符全部退化 |
| 优化 Pass 质量 | ⭐⭐ | 常量折叠基本可用；Inlining 空壳 |
| Pass 异常处理 | ⭐⭐⭐ | 已修复（不再静默吞掉，有 stderr 输出） |
| 代码工程质量 | ⭐⭐ | __class__ 类型魔改、or "" None 隐式处理 |

### Pass 实现状态表

| Pass | HIR | MIR | LIR | 评级 |
|------|-----|-----|-----|------|
| ConstantFolding | ✅ 有实现 | ✅ 有实现 | ✅ 有实现 | B+（HIR 层用 __class__ 魔改） |
| Inlining | **空壳** | N/A | N/A | **F（return False）** |
| DeadCodeElimination | **return False** | **return False** | ✅ 有实现 | C（仅 LIR 层） |
| CommonSubexprElimination | N/A | ✅ 有实现 | ✅ 有实现 | B（基本块内 CSE） |
| LoopInvariantCodeMotion | N/A | ✅ 有实现 | ✅ 有实现 | B-（MIR 回边检测错误） |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [mir_lowering.py:351-384] **MIR match 退化为无条件跳转链** → 所有 arm 串行执行（未修复） → 实现真正的 match 分支逻辑
- 追问：如果 GHC 的 STG→Cmm 将 match 退化为无条件跳转，能被接受吗？→ **绝对不能**
- [mir_lowering.py:247-250] **Lambda 丢弃闭包体和自由变量** → 闭包在 MIR 层变成名字标签，无法执行（未修复）
- [mir_lowering.py:285-289] **ListComprehension 降级为空列表常量** → 结果永远返回 `[]`（未修复）
- [lir_lowering.py:219-223] **LIRBranch 丢失 true/false target** → 条件分支变成无跳转目标的指令（未修复）
- [lir_lowering.py:231-235] **MIRSwitch 丢失所有 case 分支** → 只保留 default_target（未修复）
- [lir_lowering.py:237-241] **MIRMatchJump 丢失匹配逻辑** → variant_tests 被忽略（未修复）

#### 中等问题（影响特定场景）

- [mir_lowering.py:386-394] **Pipe 降级语义错误** → 前一步结果作为 callee 而非参数 → 修正为 `g(f(x))` 语义
- [lir_lowering.py:204-211] **Phi 节点只取第一个来源** → false 分支的值被忽略
- [lir_lowering.py:171-176] **MIRMapBuild 误用 LIRBuildList** → Map 被降级为 List
- [pass_manager.py:636] **LICM 回边检测不正确** → 前向跳转也被识别为回边
- [pass_manager.py:105-108] **常量折叠用 `__class__` 魔改类型** → 绕过 dataclass 构造 → 创建新节点替换

#### 轻微问题

- [hir_lowering.py:330] PatternConstructor type_name 丢失为空字符串（未修复）
- [hir_lowering.py:205] TryExpr 降级为 UnwrapExpr 丢失错误传播语义
- [lir_lowering.py:88] stack_size 计算粗糙（每个 SSA 值假设 8 字节）
- [ir_nodes.py:730] LIRFunction.reg_alloc 类型注解与实际值不匹配

---

## [2026-07-15 第十轮] C 运行时 + 测试 + Tree-sitter 审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 内存安全 | ⭐ | GC 空壳，引用计数不递归，循环引用必然泄漏 |
| API 设计 | ⭐⭐ | 接口声明完整但行为语义不清晰 |
| 测试覆盖 | ⭐⭐ | Evaluator:VM 约 207:81，无跨路径一致性测试 |
| 测试质量 | ⭐⭐⭐ | 断言充分但边界条件覆盖不足 |
| Tree-sitter 一致性 | ⭐⭐⭐ | while/break/continue 已修复，但 guard 位置和 `?` 不一致 |
| 代码质量 | ⭐⭐⭐ | 可读性好，注释充分 |

### 测试统计

| 文件 | 测试数量 |
|------|---------|
| test_nova.py | 288 |
| test_ir.py | 90 |
| test_native_backend.py | 88 |
| test_c_codegen.py | 52 |
| test_backends.py | 43 |
| test_type_system.py | 39 |
| test_modules.py | 28 |
| test_errors.py | 36 |
| **总计** | **664** |

Evaluator 测试约 207 个，VM 测试约 81 个（约 7:2.5）。

### 发现的问题

#### 严重问题（阻碍正常使用）

- [nova_runtime.c:99-103] **nova_gc_collect() 仍是空壳** → 不执行任何回收（连续十轮未修） → 实现真正的 GC 或移除 API 声明
- 追问：如果 GHC 声明有 GC 但实际从不运行，能被接受吗？→ **绝对不能**
- [nova_runtime.c:749-756] **nova_adt_release() 不递归释放字段** → ADT 中的堆对象全部泄漏（未修复） → 递归 release
- [nova_runtime.c:479-486] **nova_list_release() 不递归释放元素** → 列表元素引用计数永不递减（未修复） → 递归 release
- [nova_runtime.c:370-388] **nova_list_concat() 浅拷贝不 retain** → 原列表释放后新列表元素指针悬挂（未修复） → 拼接时 retain
- **无 Evaluator/VM 行为一致性测试** → 两条执行路径可能产生不同结果但无验证（连续十轮未修）
- 追问：如果 GHC 缺少核心语言特性的测试，能被接受吗？→ **绝对不能**

#### 中等问题

- **完全缺失测试的特性**：`?` 操作符语义、Map 字面量操作、match guard、字符串操作（split/trim/upper/lower）、char 字面量求值、负整数模式、C 运行时内存管理
- **无端到端测试** → 无"Nova 源码→编译→执行→验证输出"的完整流程
- [nova_runtime.c:791-798] **nova_closure_release() 不递归释放捕获变量**
- [nova_runtime.h] **缺少 NovaTuple 结构体** → C 运行时无法处理 tuple
- [grammar.js] **不支持 `?`（TryExpr）** → 与 parser.py 不一致
- [grammar.js:398-403 vs parser.py:530-539] **match_arm guard 位置不一致** → parser.py 在 `->` 前，grammar.js 在 `->` 后

#### 轻微问题

- [nova_runtime.c:109-119] nova_panic 直接 abort() 不做清理
- [nova_runtime.c:651-668] nova_map_release 释放 key 但不释放 value

### Tree-sitter 已修复问题

- grammar.js 现已支持 while_expr（第 428 行）、break_expr（第 441 行）、continue_expr（第 443 行）

---

## [2026-07-15] 第十轮 P0 级问题完整更新

| # | 问题 | 模块 | 状态 |
|---|------|------|------|
| 1 | CLOSURE 捕获整个帧 | vm.py, compiler.py | 连续十轮未修 |
| 2 | TypeVar 万能兼容 | type_checker.py | 连续十轮未修 |
| 3 | let 多态未实现 | type_checker.py | 连续十轮未修 |
| 4 | VM while 启发式检测 | vm.py | 连续十轮未修 |
| 5 | `\|>` 优先级不一致（parser.py 位置错误） | parser.py vs grammar.js | 连续十轮未修，本轮确认更严重：parser.py 中 \|> 在比较运算符下面 |
| 6 | C 运行时 GC 空壳 | nova_runtime.c | 连续十轮未修 |
| 7 | C 运行时引用计数不递归 | nova_runtime.c | 连续十轮未修 |
| 8 | MIR match 完全退化 | mir_lowering.py | 连续十轮未修 |
| 9 | LIR Branch/Switch/Match 退化 | lir_lowering.py | 连续十轮未修 |
| 10 | Evaluator 作用域泄漏（系统性） | evaluator.py | 连续十轮未修 |
| 11 | AND/OR 非短路求值 | vm.py, compiler.py | 连续十轮未修 |
| 12 | STORE_VAR 静默创建全局 | vm.py | 连续十轮未修 |
| 13 | 嵌套 PatternTuple/PatternList 解构错误 | compiler.py | 连续十轮未修 |
| 14 | Native 后端寄存器分配从未调用 | native_backend.py | 连续十轮未修 |
| 15 | Native 后端悬垂指针 | native_backend.py | 连续十轮未修 |
| 16 | Lambda 闭包自由变量丢失 | mir_lowering.py | 连续十轮未修 |
| 17 | Pass 异常静默吞掉 | pass_manager.py | **本轮确认已修复**（现打印 stderr + 收集 errors） |
| 18 | 所有后端无端到端测试 | tests/ | 连续十轮未修 |
| 19 | 闭包语义 Evaluator vs VM 根本不一致 | evaluator.py vs vm.py | 持续性问题（引用 vs 值） |
| 20 | 嵌套模式匹配不生成子模式测试 | compiler.py | 连续十轮未修 |
| 21 | 模块系统路径遍历安全漏洞 | modules.py | **新发现** |
| 22 | ListComprehension 降级为空列表 | mir_lowering.py | 连续十轮未修 |
| 23 | Pipe MIR 降级语义错误 | mir_lowering.py | **新发现** |
| 24 | 无 occurs check | type_checker.py | **新发现** |
| 25 | 无真正 unification | type_checker.py | **新发现** |
| 26 | match guard 位置 parser.py vs grammar.js 不一致 | parser.py, grammar.js | **新确认** |
| 27 | grammar.js 不支持 `?` | grammar.js | **新发现** |

### 第十轮新发现的架构级建议

1. **重写类型检查核心**（重复建议，优先级最高）：实现真正的 Hindley-Milner Algorithm W（unification + occurs check + generalize/instantiate）。这是类型系统的基础，所有其他类型问题都源于此。
2. **统一闭包语义**（重复建议）：Evaluator 用引用捕获，VM 用值快照。必须选择一种并统一。推荐值语义快照 + 仅捕获自由变量。
3. **修复 `|>` 优先级**：将 `_parse_pipe` 从 `_parse_comparison_expr` 移到 `_parse_or_expr` 中，使管道操作符优先级低于所有二元运算符。
4. **修复编译器嵌套模式匹配**：重构为统一的 `_compile_full_pattern(pattern, fail_label)` 方法。
5. **删除 VM 所有启发式控制流**：while 循环检测、CONTINUE 起始位置、BREAK 目标扫描——全部改为编译器显式编码。
6. **修复 IR 降级链**：MIR match/lambda/list-comp/pipe 的退化是所有后端不可用的根源。
7. **修复模块安全**：添加路径白名单，规范化所有路径。
8. **实现真正的 GC 或明确标注"无 GC"**。
9. **引入端到端测试**：Evaluator-VM 一致性测试、C 后端编译-运行-验证。

---

## [2026-07-15] 第十一轮全面代码审查报告

> **审查方法**：3 轮 × 3 并行 = 9 个 Explore 子代理，逐行审查全部源文件
> **审查标准**：生产级编译器/语言标准（参考 OCaml/Haskell/Elm/F# 最佳实践）

---

### 第十一轮 P0 级问题完整追踪

| # | 问题 | 模块 | 状态 |
|---|------|------|------|
| 1 | CLOSURE 捕获整个帧 | vm.py, compiler.py | 连续十一轮未修 |
| 2 | TypeVar 万能兼容（_types_compatible） | type_checker.py | 连续十一轮未修（新增：第1287行 TypeVar 短路） |
| 3 | let 多态未实现 | type_checker.py | 连续十一轮未修 |
| 4 | 无 occurs check / 无真正 unification | type_checker.py | 连续十一轮未修 |
| 5 | `\|>` 优先级 parser.py vs grammar.js 矛盾 | parser.py, grammar.js | 连续十一轮未修 |
| 6 | C 运行时 GC 空壳 | nova_runtime.c | 连续十一轮未修 |
| 7 | C 运行时引用计数不递归 | nova_runtime.c | **已修复**（nova_value_release 现在递归） |
| 8 | MIR match 完全退化 | mir_lowering.py | 连续十一轮未修 |
| 9 | LIR Branch/Switch/Match 退化 | lir_lowering.py | 连续十一轮未修 |
| 10 | Evaluator 闭包引用捕获 vs VM 值快照 | evaluator.py vs vm.py | 连续十一轮未修 |
| 11 | AND/OR 非短路（VM 层） | vm.py | 连续十一轮未修（编译器已实现短路，但 VM AND/OR 指令仍非短路） |
| 12 | STORE_VAR 静默创建全局 | vm.py | 连续十一轮未修 |
| 13 | 嵌套 PatternTuple/PatternList 子模式测试缺失 | compiler.py | 连续十一轮未修 |
| 14 | Native 后端寄存器分配从未调用 | native_backend.py | 连续十一轮未修 |
| 15 | Native 后端操作数传播完全失效 | native_backend.py | **新发现**（vregs 键名与 LIR src_locs 不匹配） |
| 16 | Lambda 闭包自由变量丢失 | mir_lowering.py | 连续十一轮未修 |
| 17 | Pass 异常静默吞掉 | pass_manager.py | **已修复**（现打印 stderr + 收集 errors） |
| 18 | 所有后端无端到端测试 | tests/ | 连续十一轮未修 |
| 19 | 闭包语义 Evaluator vs VM 根本不一致 | evaluator.py vs vm.py | 持续性问题（引用 vs 值） |
| 20 | 嵌套模式匹配不生成子模式测试 | compiler.py | 连续十一轮未修 |
| 21 | 模块系统路径遍历安全漏洞 | modules.py | 连续十一轮未修 |
| 22 | ListComprehension 降级为空列表 | mir_lowering.py | 连续十一轮未修 |
| 23 | Pipe MIR 降级对未绑定函数名生成空 callee | mir_lowering.py | 连续十一轮未修 |
| 24 | Cranelift 后端 SSA 值不传播 | cranelift_backend.py | **新发现**（生成的 .clif 变量全部未定义） |
| 25 | WASM 后端 Block/Label/Jump 语义完全错误 | wasm_backend.py | **新发现**（block 不闭合、br 不能前向跳转） |
| 26 | match guard 位置 parser.py vs grammar.js 不一致 | parser.py, grammar.js | 连续十一轮未修 |
| 27 | grammar.js 不支持 `?` | grammar.js | 连续十一轮未修 |
| 28 | LIR Phi 只取第一个 source | lir_lowering.py | **新发现** |
| 29 | parser.py 缺少索引表达式 `expr[idx]` | parser.py | **新发现** |
| 30 | C 运行时 HTTP GET 临时文件 TOCTOU 竞态 | nova_runtime.c | **新发现** |
| 31 | FnCall 中 error_collector 绕过 _report_error | type_checker.py | **新发现** |
| 32 | Inlining pass 完全空壳 | pass_manager.py | **新发现** |

---

## [2026-07-15] VM 虚拟机 (vm.py) 审查报告（第十一轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | PIPE_CALL 专用指令、MATCH_TEST_* 系列有特色 |
| 可行性 | ⭐⭐⭐ | 核心路径可用；闭包全量捕获影响表达力 |
| 正确性 | ⭐⭐ | 闭包全量捕获、STORE_VAR 全局泄漏、MATCH_BIND 无作用域 |
| 安全性 | ⭐⭐⭐ | 栈下溢保护基本到位（_pop 已修复），id() 已修复为 _loop_id |
| 一致性 | ⭐⭐ | 与 Evaluator 在闭包语义、作用域、STORE_VAR 等存在差异 |
| 完整性 | ⭐⭐⭐⭐⭐ | 47 个操作码全部有处理路径 |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰，但 _execute_instruction 仍过长 |
| 性能 | ⭐⭐⭐ | 闭包全量复制、dict 管理循环状态有开销 |

### 发现的问题

#### 严重问题（阻碍正常使用）
- [vm.py:812] **CLOSURE 捕获整个帧 locals 而非仅自由变量** → 每次创建闭包 dict 浅拷贝所有局部变量，时间 O(n)，且阻止 GC 回收不需要的变量 → 编译器分析自由变量，CLOSURE 指令携带自由变量名列表
- 追问：如果 OCaml 的闭包捕获了整个作用域的 dict 拷贝，性能影响能被接受吗？→ **绝对不能。** 内存使用量可能增加 10-100 倍。
- [vm.py:573] **STORE_VAR 在函数体内对未定义变量静默创建全局** → 函数内拼写错误的赋值会静默创建全局变量，违背"变量必须先声明"原则 → 添加严格模式或编译期检查
- 追问：如果 OCaml 中未声明变量可以赋值，能被接受吗？→ **绝对不能。**

#### 中等问题（影响特定场景）
- [vm.py:1082-1084] MATCH_BIND 在非函数上下文静默创建全局变量 → 与 Evaluator 子环境行为不一致
- [vm.py:1112] MATCH_TEST_TUPLE 无栈空检查 → 空栈时 Python IndexError 而非 Nova RuntimeError
- [vm.py:1126] MATCH_TEST_LIST 无栈空检查 → 同上
- [vm.py:1208] TRY_UNWRAP 无栈空检查 → 同上
- [vm.py:682,688] AND/OR 指令非短路（依赖编译器生成 POP_JUMP_IF_FALSE 序列）→ 如果编译器某些路径生成 AND/OR 指令则丢失短路
- [vm.py:379-380] VM 闭包不支持部分应用 → 与 Evaluator 行为不一致

#### 轻微问题（代码质量）
- [vm.py:677-688] AND/OR 的 Python `and`/`or` 语义与 Nova 语义不同（Python 返回操作数，不是 bool）
- [vm.py:797-798] CONTINUE while 首次迭代时 loop_start 可能为 None
- [vm.py:926,970] 异常退出时 _range_index/_list_index 条目泄漏（内存泄漏，不影响正确性）

### 已修复的历史问题（本轮确认）
- ✅ 栈下溢保护 `_pop()` 统一方法已实现
- ✅ `id()` 字典键已改为 `_loop_id` 计数器
- ✅ RETURN 语义已修复（return_flag 正确终止执行流）
- ✅ base_sp 栈截断已实现
- ✅ CONTINUE while 循环已实现（不再空操作）
- ✅ BREAK while 循环已使用操作数直接跳转

#### Evaluator vs VM 对比
| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| 闭包捕获 | 环境引用（引用语义） | 值快照（值语义） | ❌ 不一致 |
| 作用域隔离 | Block/For/Match 子环境 | 扁平帧 locals | ❌ 不一致 |
| STORE_VAR 未定义变量 | 报错 | 静默创建全局 | ❌ 不一致 |
| AND/OR 短路 | 运行时短路 | 编译时短路 | ⚠️ 条件一致 |
| TRY_UNWRAP 传播 | ReturnSignal 异常 | return True + stack[-1] | ✅ 语义等价 |
| for 循环返回值 | list | list（LOOP_END 收集） | ✅ 一致 |
| while 循环返回值 | 最后迭代值 / UNIT | UNIT | ⚠️ 可能不一致 |
| 部分应用 | NovaClosure 部分 | 仅 NovaPartialBuiltin | ❌ 不一致 |
| 调用深度限制 | 1000 | 1000 | ✅ 一致 |

---

## [2026-07-15] 编译器 (compiler.py) 审查报告（第十一轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | PIPE_CALL 专用指令和 MATCH_TEST_* 系列有特色 |
| 可行性 | ⭐⭐⭐⭐ | 编译器-VM 协作清晰，能正确执行大部分程序 |
| 正确性 | ⭐⭐⭐ | 嵌套模式匹配是严重 bug；闭包全量捕获；STORE_VAR 静默全局 |
| 安全性 | ⭐⭐⭐ | 栈溢出保护有，但无运行时类型安全检查 |
| 一致性 | ⭐⭐⭐⭐ | 栈布局编译器与 VM 基本一致；短路求值正确 |
| 完整性 | ⭐⭐⭐⭐ | AST 覆盖完整；所有指令有 VM 处理 |
| 工程质量 | ⭐⭐⭐ | 存在死代码（旧方法、AND/OR 指令）、无意义 if/else |
| 性能 | ⭐⭐⭐ | 闭包全量复制、循环状态用 dict |

### 发现的问题

#### 严重问题
- [compiler.py:869-878] **嵌套模式匹配不生成子模式测试** → `match x { (1, "hello") -> ... }` 只测试元组长度，不测试内部值 → `_compile_pattern_extract_and_bind` 应对每个子模式调用 `_compile_pattern_test_with_fail`
- 追问：如果 Haskell GHC 编译器跳过嵌套 Pattern 的测试代码生成，能被接受吗？→ **绝对不能。**

#### 中等问题
- [compiler.py:361-369] Import 内联冲突检测只检查 `bytecode.functions`，不检查 globals/let/mut，检测到冲突仅 warning 仍静默覆盖
- [compiler.py:402] 闭包 CLOSURE 指令不含捕获列表，由 VM 在运行时全量捕获

#### 轻微问题
- [compiler.py:882-946] 旧版 `_compile_pattern_test` 和 `_compile_pattern_bindings` 是死代码
- [compiler.py:420-421] CharLiteral 编译为 CONST_STRING，'a' 和 "a" 运行时无法区分
- [compiler.py:592-598] PIPE 操作数路径两个分支代码完全相同
- [compiler.py:66-67] Op.AND / Op.OR 指令是死代码（编译器从不生成）

### 已修复的历史问题（本轮确认）
- ✅ AST 覆盖完整 — 全部节点有编译处理
- ✅ 跳转回填无遗漏
- ✅ AND/OR 短路实现正确（DUP + POP_JUMP_IF_FALSE）
- ✅ CLOSURE 参数与 VM 一致
- ✅ 管道操作符优先级有明确位置

---

## [2026-07-15] 求值器 (evaluator.py) 审查报告（第十一轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐⭐ | 完整的函数式语言解释器，支持闭包/ADT/模式匹配/管道/柯里化 |
| 可行性 | ⭐⭐⭐⭐ | 核心功能完整可用 |
| 正确性 | ⭐⭐⭐ | 闭包语义与 VM 根本不一致，IfExpr 作用域泄漏，顶层 TryExpr 崩溃 |
| 安全性 | ⭐⭐⭐⭐ | 递归深度保护到位，但比较运算类型安全缺失 |
| 一致性 | ⭐⭐ | 与 VM 在闭包、作用域、TRY_UNWRAP、比较运算等多处不一致 |
| 完整性 | ⭐⭐⭐⭐⭐ | AST 覆盖 100%，模式匹配覆盖所有类型+嵌套+守卫 |
| 工程质量 | ⭐⭐⭐ | eval_decl 重复代码、self.env 切换模式脆弱 |
| 性能 | ⭐⭐⭐ | Python 解释器性能受限 |

### 发现的问题

#### 严重问题
- [evaluator.py:46-53] **闭包引用捕获 vs VM 值快照不一致** → 同一程序在 Evaluator 和 VM 下产生不同结果 → 必须统一为一种语义
- 追问：如果 GHC 的两个执行后端语义不一致，能被接受吗？→ **绝对不能。**

#### 中等问题
- [evaluator.py:741-747] IfExpr 不创建子作用域，then 分支中的 let 泄漏到外部 → 与 Rust/ML 行为不同
- [evaluator.py:715-723] TryExpr 在顶层使用导致未捕获的 ReturnSignal 异常崩溃
- [evaluator.py:723] TryExpr 对非 ADT 值不过错（直接返回），与 VM 行为不同
- [evaluator.py:893-900] 比较运算 `<`/`>`/`<=`/`>=` 不检查 Bool 类型安全（Python 的 bool 是 int 子类）
- [evaluator.py:944-957] While 循环体不创建子作用域

#### 轻微问题
- [evaluator.py:570-625] eval_decl 与 eval_program 接口重复
- [evaluator.py:808-813] break/continue 在非循环中的错误检测依赖 _call_fn 二次捕获
- [evaluator.py:1032] PatternString 与 PatternChar 对单字符都有歧义匹配

---

## [2026-07-15] 类型检查器 (type_checker.py) 审查报告（第十一轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐ | 类型表示是标准的，TypeVar 绑定收集是简化创新但不够完备 |
| 可行性 | ⭐⭐⭐ | 能处理基本场景，但不支持核心 HM 特性 |
| 正确性 | ⭐⭐ | ADTType.__eq__ 已修复，但 TypeVar 万能兼容、无 let 多态 |
| 安全性 | ⭐⭐ | TypeVar 逃逸、名称碰撞、_types_compatible 短路严重削弱类型安全 |
| 一致性 | ⭐⭐⭐ | 两遍扫描设计合理，但 FnCall 错误报告绕过 _report_error |
| 完整性 | ⭐⭐⭐ | 覆盖所有 AST 节点和模式类型，但缺 generalize/instantiate |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰，但类型系统架构有根本缺陷 |
| 性能 | ⭐⭐⭐⭐ | 无 union-find 反而使单次检查更快 |

### 发现的问题

#### 严重问题
- [type_checker.py:1287-1288] **_types_compatible 对 TypeVar 短路** → `if isinstance(a, TypeVar) or isinstance(b, TypeVar): return True` 使任何包含 TypeVar 的类型比较都返回 True，破坏类型安全
- [type_checker.py] **let 多态完全未实现** → `let id = fun x -> x in (id 1, id "a")` 被静默接受 → 实现 generalize/instantiate
- 追问：如果 OCaml 的 let 多态没有正确实现，能被接受吗？→ **绝对不能。** 这是 HM 系统的核心。
- [type_checker.py] **无真正 unification / 无 occurs check** → 不是 Algorithm W，只是模式匹配+变量替换

#### 中等问题
- [type_checker.py:744] FnCall 中 error_collector.add() 绕过 _report_error，当 collect_errors=False 时错误不会被抛出
- [type_checker.py:292-293] Err 构造器类型签名有独立的 TypeVar（err_ok_t 未与 Ok 共享）
- [type_checker.py:922] for 循环迭代变量类型为固定 TypeVar("for_elem")，不从迭代器推断
- [type_checker.py:950] 列表推导式元素类型同样未推断
- [type_checker.py:766-768] PipeExpr 类型检查过于宽松（只要与第一个或最后一个参数兼容就通过）

#### 轻微问题
- [type_checker.py:169-174] TypeVar 手动指定名字时不保证唯一性
- [type_checker.py:1015-1021] PatternConstructor 使用线性搜索查找构造器
- [type_checker.py:287] 内置 Option 构造器 None 共享 TypeVar 实例（设计选择，非 bug）

### 已修复的历史问题
- ✅ ADTType.__eq__ 比较类型参数（Option[Int] != Option[String]）
- ✅ ErrorCollector 完整实现
- ✅ Pattern 类型检查覆盖所有类型

---

## [2026-07-15] 词法分析器 (lexer.py) 审查报告（第十一轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 标准 lexer 设计，无特殊创新 |
| 可行性 | ⭐⭐⭐⭐⭐ | 功能完整，词法错误恢复机制完善 |
| 正确性 | ⭐⭐⭐⭐ | 关键字/标识符/数值/字符串解析正确 |
| 安全性 | ⭐⭐⭐⭐ | 错误后能继续分析，不会崩溃 |
| 一致性 | ⭐⭐⭐ | 错误处理方式不统一（print+append vs LexerError 类） |
| 完整性 | ⭐⭐⭐⭐ | 覆盖绝大部分语法元素 |
| 工程质量 | ⭐⭐⭐ | 有死 Token 和未使用方法 |
| 性能 | ⭐⭐⭐⭐ | O(n) tokenizer 合理 |

### 发现的问题
- [lexer.py:155-160] `_make_error` 方法定义但从未使用（死代码）
- [lexer.py:240-251] 缺少 `\0`, `\x`, `\u` unicode 转义支持
- [lexer.py:88] PIPE_VARIANT Token 死代码，从未被 lexer 产出
- [lexer.py:91] UNIT Token 死代码，parser 从 LPAREN+RPAREN 推导

---

## [2026-07-15] 语法分析器 (parser.py) 审查报告（第十一轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 表达式导向、ADT、管道、错误传播 `?` 有个性 |
| 可行性 | ⭐⭐⭐ | 核心语法可行，但 pipe 优先级矛盾和索引缺失影响可用性 |
| 正确性 | ⭐⭐ | 3 个严重问题 |
| 安全性 | ⭐⭐⭐⭐ | 词法错误恢复完善，不会崩溃 |
| 一致性 | ⭐⭐ | parser 与 tree-sitter grammar.js 存在多处不一致 |
| 完整性 | ⭐⭐⭐ | 缺少索引表达式、块注释、unicode 转义 |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰，有 span 追踪 |
| 性能 | ⭐⭐⭐ | `_is_map_literal` 有 O(n) 前瞻 |

### 发现的问题

#### 严重问题
- [parser.py:672-678] **\|>` 优先级高于比较运算符，与 grammar.js 矛盾** → parser 中 \|> 在 comparison 之下，grammar.js 中 \|> 最低（PREC.PIPE=2）→ `1 + 2 |> f` 两种解析不同
- 追问：如果 GCC/Clang 的 parser 和 tree-sitter grammar 对同一代码产生不同 AST，能被接受吗？→ **绝对不能。**
- [parser.py:530-539] **match guard 位置与 grammar.js 不一致** → parser: `pat if guard -> body`，grammar.js: `pat -> body if guard`
- [parser.py:733-763] **缺少索引表达式 `expr[idx]` 的解析** → `_parse_postfix_expr` 只处理函数调用和字段访问

#### 中等问题
- [parser.py:344] `Fn[T1, T2]` 返回类型硬编码为 Unit
- [parser.py:464-466] `<-` 由 LT+MINUS 组合，允许 `< -`（带空格）通过

#### 轻微问题
- [parser.py:580-588] 负数模式错误消息不够具体
- [parser.py:680-687] `_parse_cons_expr` 名称误导（实际解析 `++` 字符串拼接）

---

## [2026-07-15] 错误处理 (errors.py) 审查报告（第十一轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | Rust 风格多行高亮、RelatedNote、ANSI + NO_COLOR |
| 可行性 | ⭐⭐⭐⭐ | TypeChecker 已集成 ErrorCollector |
| 正确性 | ⭐⭐⭐ | 缺文件名、控制流信号无 span、get_all() 时序丢失 |
| 安全性 | ⭐⭐⭐⭐ | 无安全敏感操作 |
| 一致性 | ⭐⭐⭐ | RuntimeError_ 命名不一致，RelatedNote 上下文窗口不一致 |
| 完整性 | ⭐⭐⭐ | 缺文件名、缺 Evaluator 集成 |
| 工程质量 | ⭐⭐⭐⭐ | 代码结构清晰，docstring 完整 |
| 性能 | ⭐⭐⭐⭐⭐ | 无性能瓶颈 |

### 发现的问题
- [errors.py:396-398] `get_all()` 丢失时序信息（errors 排在 warnings 前面）
- [errors.py:334-352] BreakSignal/ContinueSignal/ReturnSignal 不携带 span 信息
- [errors.py:186-190] 缺少文件名输出（只有行号，无 `src/main.nova:1:5` 格式）
- [errors.py] ErrorCollector 未集成到 Evaluator
- [errors.py:405-411] `raise_all()` 将富格式子错误降级为纯文本
- [errors.py:244] RelatedNote 上下文窗口不一致（1行 vs 主错误2行）

---

## [2026-07-15] 模块系统 (modules.py) 审查报告（第十一轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 标准 module resolver 模式 |
| 可行性 | ⭐⭐⭐⭐ | 基本模块加载、缓存、循环检测均可工作 |
| 正确性 | ⭐⭐⭐ | 路径遍历漏洞、API 契约违反 |
| 安全性 | ⭐ | 路径遍历漏洞允许读取任意文件 |
| 一致性 | ⭐⭐⭐ | 重复代码、死代码 |
| 完整性 | ⭐⭐⭐ | 缺路径白名单、缺导入冲突检测 |
| 工程质量 | ⭐⭐⭐ | 文档完整但实现与文档不符 |
| 性能 | ⭐⭐⭐⭐ | 模块数量通常很小 |

### 发现的问题
- [modules.py:107-140] **路径遍历安全漏洞** → 可通过 `import "/etc/passwd"` 或 `import "../../.ssh/id_rsa"` 读取任意文件 → 添加路径白名单和 realpath 验证
- 追问：如果 Rust 的 cargo 允许任意文件读取，能被接受吗？→ **绝对不能。这是 CVE 级别漏洞。**
- [modules.py:328-330] 导入同名绑定被静默覆盖，无冲突检查
- [modules.py:191-209] `load_module` 文档标注返回 Optional[ModuleInfo] 但实际 raise RuntimeError_
- [modules.py:276-299] `_collect_exports` 和 `_collect_exported_types` 完全重复
- [modules.py:159-174] `resolve_package_path` 死代码
- [modules.py:358-364] 标准库搜索路径依赖工作目录（相对路径不可靠）

### 已修复的历史问题
- ✅ 循环导入检测正确（loading_stack 机制）

---

## [2026-07-15] 环境 (environment.py) 审查报告（第十一轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐ | 标准作用域链模式 |
| 可行性 | ⭐⭐⭐⭐⭐ | 简洁、正确、可直接使用 |
| 正确性 | ⭐⭐⭐⭐⭐ | 作用域链、变量查找、可变性检查均正确 |
| 安全性 | ⭐⭐⭐⭐ | 无安全敏感操作 |
| 一致性 | ⭐⭐⭐⭐⭐ | 命名一致，风格统一 |
| 完整性 | ⭐⭐⭐⭐ | 核心功能完整 |
| 工程质量 | ⭐⭐⭐⭐ | 简洁清晰 |
| 性能 | ⭐⭐⭐⭐⭐ | Dict O(1) 查找，作用域链深度通常 <20 |

### 发现的问题
- [environment.py:26-27] 闭包生命周期依赖 Python GC，无显式管理（文档说明即可）
- [environment.py:67-72] `all_bindings()` 返回扁平 dict 丢失作用域层级（调试辅助，可接受）
- [environment.py] 缺少 `__contains__` / `__getitem__` Python 协议

---

## [2026-07-15] C 代码生成 (c_codegen.py) 审查报告（第十一轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | AST 到 C 的转换是经典实现，闭包捕获分析有深度 |
| 可行性 | ⭐⭐⭐⭐ | 唯一真正可端到端使用的后端 |
| 正确性 | ⭐⭐⭐ | Try 表达式字段名错误、for 循环元素类型硬编码 int64_t |
| 安全性 | ⭐⭐⭐ | 闭包浮点数堆泄漏、列表元素类型假设 |
| 一致性 | ⭐⭐⭐⭐ | 与 Nova 语义基本对应 |
| 完整性 | ⭐⭐⭐⭐⭐ | 覆盖所有 AST 节点 |
| 工程质量 | ⭐⭐⭐⭐ | 两遍编译设计合理 |
| 性能 | ⭐⭐⭐ | 依赖 C 编译器优化 |

### 发现的问题
- [c_codegen.py:596] Try 表达式使用 `variant_tag` 但 ADT 结构体字段名为 `tag` → 生成的 C 代码编译失败
- [c_codegen.py:409] for 循环元素类型硬编码为 `int64_t` → 对浮点/字符串列表截断或指针错误
- [c_codegen.py:906-913] 闭包捕获浮点数的装箱内存泄漏
- [c_codegen.py:548-561] 使用 GNU 语句表达式 `({ ... })`，MSVC 不支持
- [c_codegen.py:1302] `_infer_c_type_from_expr` 对 Identifier 默认返回 `int64_t`

---

## [2026-07-15] Native 后端 (native_backend.py) 审查报告（第十一轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐⭐ | 从零手写 x86_64 机器码发射器和 ELF 生成器 |
| 可行性 | ⭐ | 生成的 ELF 无法实际运行 |
| 正确性 | ⭐ | 操作数传播完全失效，寄存器分配从未调用 |
| 安全性 | ⭐ | 悬垂指针、无边界检查 |
| 一致性 | ⭐⭐ | 与 Nova 语义差距大 |
| 完整性 | ⭐⭐⭐ | 浮点运算未实现 |
| 工程质量 | ⭐⭐⭐ | 工程量巨大但核心机制不工作 |
| 性能 | N/A | 不工作 |

### 发现的问题（7 个严重问题）
- [native_backend.py:45-82] LinearScanAllocator 类存在但从未被调用（死代码）
- [native_backend.py] vregs 字典键名与 LIR src_locs 不匹配 → BinOp 几乎永远找不到操作数寄存器
- [native_backend.py] 运行时函数（nova_init 等）未在 ELF 中链接 → 调用必然 segfault
- [native_backend.py] RBX 被 _compile_store_global 用作临时地址寄存器 → 覆盖 callee-saved 值
- [native_backend.py] 双重 epilogue（LIRReturn + 函数末尾）→ 栈不平衡
- [native_backend.py] 栈对齐可能被破坏（sub_rsp 不保证 16 字节对齐）
- [native_backend.py] 浮点 BinOp 完全缺失

---

## [2026-07-15] Cranelift 后端 (cranelift_backend.py) 审查报告（第十一轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐ | 纯文本模板拼接 |
| 可行性 | ⭐ | 生成的 .clif 无法被 Cranelift 编译 |
| 正确性 | ⭐ | SSA 值完全不传播、Branch 硬编码标签 |
| 安全性 | N/A | 代码无法编译 |
| 一致性 | ⭐⭐ | 基本类型映射正确 |
| 完整性 | ⭐⭐⭐ | 缺 StoreGlobal/CallIndirect |
| 工程质量 | ⭐⭐ | 代码量少但核心问题致命 |
| 性能 | N/A | 不工作 |

### 发现的问题（7 个严重问题）
- [cranelift_backend.py] SSA 值完全不传播 → 每条指令引用未定义变量名
- [cranelift_backend.py:167-168] Branch 硬编码 block_true/block_false
- [cranelift_backend.py:157] Return 不返回值
- [cranelift_backend.py] Float BinOp 不区分整数/浮点
- [cranelift_backend.py:257-261] 数据段格式不符合 Cranelift IR 规范
- [cranelift_backend.py] Call 不传递参数（SSA 名未定义）
- [cranelift_backend.py] compile_to_object fallback 不调用 C 编译器

---

## [2026-07-15] WASM 后端 (wasm_backend.py) 审查报告（第十一轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | WasmGC struct 定义有想法 |
| 可行性 | ⭐ | 生成的 WAT 不合法 |
| 正确性 | ⭐ | Block/Label/Jump 语义完全错误 |
| 安全性 | N/A | 代码无法编译 |
| 一致性 | ⭐ | 与 Nova 语义差距大 |
| 完整性 | ⭐⭐ | 缺 LoadGlobal/StoreGlobal |
| 工程质量 | ⭐⭐ | 设计方向正确但实现失败 |
| 性能 | N/A | 不工作 |

### 发现的问题（10 个严重问题）
- [wasm_backend.py:230-231] Block/Label 语义完全错误（block 不闭合）
- [wasm_backend.py:258] Jump 语义错误（WASM br 不能前向跳转到 loop 外）
- [wasm_backend.py:261-263] Branch 只生成 br_if 到 false，不生成 true 分支
- [wasm_backend.py:161] 字符串编码 bug（`b"\\x00"` 是 4 字符不是空字节）
- [wasm_backend.py:249] UnaryOp ! 使用 i32.eqz 但 Nova 整数是 i64
- [wasm_backend.py:279-282] FieldAccess 缺少基址操作数
- [wasm_backend.py:284-285] Index 完全错误（只有 load，无基址和索引计算）
- [wasm_backend.py] 内存导入与数据段冲突
- [wasm_backend.py:274-276] BuildADT tag 值被丢弃
- [wasm_backend.py:173-174] 多个 data 段可能重叠

---

## [2026-07-15] x86_64 指令发射器 (x86_64.py) 审查报告（第十一轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐⭐ | 纯 Python x86_64 指令编码器 |
| 可行性 | ⭐⭐⭐⭐ | 作为独立库测试充分 |
| 正确性 | ⭐⭐⭐⭐ | 大部分指令编码正确 |
| 安全性 | ⭐⭐⭐⭐ | 测试覆盖好 |
| 一致性 | N/A | 基础设施库 |
| 完整性 | ⭐⭐⭐⭐ | 覆盖算术/位运算/比较/浮点(SSE2)/跳转/调用/栈操作 |
| 工程质量 | ⭐⭐⭐⭐ | 代码清晰 |
| 性能 | ⭐⭐⭐⭐ | N/A |

### 发现的问题
- [x86_64.py:451-473] `je_rel32` 定义了两次（第二个覆盖第一个）
- [x86_64.py:375-386] `mov_mem_imm64` 实际只能存 32 位立即数（C7 opcode）
- [x86_64.py:125-128] `mov_reg_imm32` 对 R8-R15 缺少 REX.B 前缀

---

## [2026-07-15] 编译管道 (compiler_pipeline.py) 审查报告（第十一轮）

### 发现的问题
- [compiler_pipeline.py:33-35] BACKEND_NATIVE 常量选择 Cranelift 而非 NativeCodeGen（命名误导）
- [compiler_pipeline.py] 错误处理缺失（前端错误直接崩溃）

---

## [2026-07-15] IR 系统 (ir/) 审查报告（第十一轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 三层 IR 参考 MLIR Dialect 思想 |
| 可行性 | ⭐⭐⭐ | 架构合理可扩展，但 MIR/LIR 降级不可行 |
| 正确性 | ⭐ | 6 个严重语义 bug |
| 安全性 | ⭐⭐⭐ | pass 异常处理已修复 |
| 一致性 | ⭐⭐ | 层间命名不一致，Map→List 语义混淆 |
| 完整性 | ⭐⭐ | HIR 完整，MIR/LIR 严重不完整；Inlining 空壳 |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰但有 monkey-patching |
| 性能 | ⭐⭐⭐ | 常量折叠/CSE/DCE/LICM 有实际实现 |

### 严重问题
- [mir_lowering.py:351-384] **MIR match 完全退化** → 模式被忽略，只执行第一分支
- [mir_lowering.py:285-289] **ListComprehension 降级为空列表**
- [mir_lowering.py:247-250] **Lambda 闭包自由变量丢失**
- [lir_lowering.py:219-223] **LIRBranch 缺少 true_label/false_label**
- [lir_lowering.py:231-235] MIRSwitch 退化为无条件跳转
- [lir_lowering.py:237-241] MIRMatchJump 退化为无条件跳转

### 中等问题
- [lir_lowering.py:204-211] MIRPhi 只取第一个 source
- [lir_lowering.py:149-155] Closure 降级为字符串常量
- [lir_lowering.py:171-176] Map 降级为 List
- [mir_lowering.py:386-394] Pipe 对未绑定函数名生成空 callee
- [mir_lowering.py:299-305] Unwrap 降级为 field access，无错误传播
- [mir_lowering.py:396-417] for 循环无迭代器调用、无变量绑定
- [pass_manager.py:257-262] Inlining 完全空壳
- [pass_manager.py:596-608] LICM 外提到 header 之后而非之前

---

## [2026-07-15] C 运行时 (nova_runtime.c) 审查报告（第十一轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | FNV-1a 哈希、链地址法 map |
| 可行性 | ⭐⭐⭐ | 基本功能可用，但 GC 缺失限制长期可行性 |
| 正确性 | ⭐⭐ | 列表 concat/slice 不 retain 元素、map_remove 不释放 value |
| 安全性 | ⭐⭐ | 临时文件 TOCTOU、ref_count 下溢无保护、realloc 失败丢指针 |
| 一致性 | ⭐⭐⭐ | 与 Python 端基本一致但命名不完全对应 |
| 完整性 | ⭐⭐⭐ | 缺 GC、缺安全测试 |
| 工程质量 | ⭐⭐⭐ | 注释充分但有结构性内存管理缺陷 |
| 性能 | ⭐⭐⭐ | 动态数组有 amortized 扩容 |

### 发现的问题
- [nova_runtime.c:99-103] GC 空壳 → `nova_gc_collect()` 只返回净分配计数
- [nova_runtime.c:371-387] `nova_list_concat` 不 retain 元素 → 原列表释放后悬垂指针
- [nova_runtime.c:1664] HTTP GET 临时文件使用 PID 拼接 → TOCTOU 竞态条件
- [nova_runtime.c:79] `nova_realloc` 失败返回 NULL 时原指针丢失
- [nova_runtime.c:325-329] `nova_string_release` ref_count 下溢无保护
- [nova_runtime.c:597-613] `nova_map_remove` 不释放 value

---

## [2026-07-15] 测试套件 (tests/) 审查报告（第十一轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 测试覆盖范围广 |
| 可行性 | ⭐⭐⭐ | 单元测试充分，但缺端到端测试 |
| 正确性 | ⭐⭐⭐ | 部分 TestLoops 测试在 main guard 之后不会执行 |
| 安全性 | N/A | N/A |
| 一致性 | ⭐⭐ | 无 Evaluator-VM 一致性测试 |
| 完整性 | ⭐⭐ | 缺 GC 测试、缺端到端测试、缺边界条件测试 |
| 工程质量 | ⭐⭐⭐ | 测试组织良好 |
| 性能 | N/A | N/A |

### 发现的问题
- [test_nova.py:1014-1079] TestLoops 类在 `if __name__` 之后 → 这些测试永远不会被执行
- **无 Evaluator vs VM 一致性测试** → 无法验证两条路径的行为一致性
- **无端到端测试** → 无编译+运行+验证输出的测试
- 缺少 GC 测试、JSON 边界测试、大整数溢出测试

---

## [2026-07-15] Tree-sitter (grammar.js) 审查报告（第十一轮）

### 发现的问题
- [grammar.js] **\|>` 优先级与 parser.py 矛盾** → grammar.js PIPE=2 最低，parser.py 在 comparison 之上
- [grammar.js:398-403] **match guard 位置与 parser.py 不一致** → grammar.js: `pat -> body if guard`，parser: `pat if guard -> body`

---

## 第十一轮新发现汇总

### 本轮确认已修复的问题（4 项）
1. ✅ VM 栈下溢保护 `_pop()` 统一方法
2. ✅ VM `id()` 字典键改为 `_loop_id`
3. ✅ VM RETURN 语义修复
4. ✅ VM base_sp 栈截断实现
5. ✅ VM CONTINUE while 循环实现
6. ✅ 编译器 AND/OR 短路实现
7. ✅ C 运行时引用计数递归释放
8. ✅ Pass 异常不再静默吞掉

### 本轮新增严重问题（8 项）
1. Native 后端操作数传播完全失效（vregs 键名不匹配）
2. Cranelift 后端 SSA 值完全不传播
3. WASM 后端 Block/Label/Jump 语义完全错误
4. LIR Phi 只取第一个 source
5. parser.py 缺少索引表达式
6. C 运行时 HTTP GET TOCTOU 竞态
7. FnCall error_collector 绕过 _report_error
8. Inlining pass 完全空壳

### 第十一轮架构级建议（优先级排序）

1. **重写类型检查核心**（最高优先级）：实现真正的 HM Algorithm W（unification + occurs check + generalize/instantiate）。修复 _types_compatible TypeVar 短路。
2. **统一闭包语义**：Evaluator 和 VM 必须使用相同语义。推荐值语义快照 + 仅捕获自由变量。
3. **修复 `|>` 优先级**：将 `_parse_pipe` 移到 `_parse_or_expr` 中。
4. **修复编译器嵌套模式匹配**：子模式必须生成测试指令。
5. **修复 IR 降级链**：MIR match/lambda/list-comp/pipe 是所有后端不可用的根源。LIR Branch 必须有目标标签。
6. **修复模块安全**：添加路径白名单，规范化所有路径。
7. **添加索引表达式解析**：parser.py `_parse_postfix_expr` 需要处理 `LBRACKET`。
8. **统一 match guard 位置**：parser 与 grammar.js 必须一致。
9. **Native/Cranelift/WASM 后端需要根本性重写**，当前生成的代码无法工作。
10. **引入端到端测试**：Evaluator-VM 一致性测试、C 后端编译-运行-验证。

---

## [2026-07-15] 第十二轮全面代码审查报告

> **审查方法**：三轮九个并行 Explore Agent，每轮 3 个 Agent
> **审查标准**：生产级编译器（OCaml/Haskell/GHC/LLVM 级别），不因为是学习项目而降低标准

---

## [2026-07-15] VM 虚拟机 (vm.py) 第十二轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | PIPE_CALL/MATCH_START_END 有特色；基本栈机设计标准 |
| 可行性 | ⭐⭐⭐⭐ | 核心路径可用；循环控制 bug 已修复 |
| 正确性 | ⭐⭐⭐ | 栈下溢保护已添加，闭包过度捕获仍存，迭代状态泄漏 |
| 安全性 | ⭐⭐⭐ | id() 已替换，但 ADT hash/eq 不一致，INDEX 无边界检查 |
| 一致性 | ⭐⭐⭐ | 与 Evaluator 仍有闭包捕获、内置函数集合等差异 |
| 完整性 | ⭐⭐⭐⭐⭐ | 52 个操作码全部有处理路径 |
| 工程质量 | ⭐⭐⭐ | _pop 辅助方法改善了栈安全，但 600 行方法仍需拆分 |
| 性能 | ⭐⭐ | 闭包捕获整个帧 dict 浅拷贝，高频创建闭包场景性能差 |

### 第十一轮问题修复状态

| 问题 | 状态 |
|------|------|
| pop 操作无栈下溢保护 | ✅ 已修复（_pop 辅助方法） |
| CONTINUE 在 while 中空实现 | ✅ 已修复（loop_start 跳转） |
| id() 用作字典键 | ✅ 已修复（自增计数器） |
| RETURN 顶层语义错误 | ✅ 已修复（return_flag） |
| base_sp 不用于栈截断 | ✅ 已修复（del self.stack[frame.base_sp:]） |
| 模式匹配失败栈恢复 | ✅ 已修复（fail_ip 跳转） |
| BREAK 前向扫描 | ✅ 已修复（操作数跳转） |
| 闭包捕获整个帧 | ❌ 仍未修复 |
| 内置函数类型检查 | ⚠️ 部分修复 |
| JUMP_IF_FALSE 重复 | ⚠️ 设计差异可接受 |

### 发现的问题

#### 严重问题（3）

- [vm.py:810-812] **闭包仍捕获整个帧 locals dict 浅拷贝** → 语义错误+性能灾难，每个闭包拷贝所有局部变量 → 编译器分析自由变量，CLOSURE 指令携带自由变量列表
- 追问：OCaml 闭包捕获整个作用域 dict 拷贝能被接受吗？→ **绝对不能**

- [vm.py:915-996] **迭代状态字典在异常退出时不被清理** → for 循环中 RuntimeError_ 抛出时 _range_index/_list_index 键永久残留 → 用 try/finally 包装或关联 Frame 对象
- 追问：Python itertools 内存泄漏能被接受吗？→ **不能**

- [vm.py:178-218] **VM 未注册 Some/None/Ok/Err 全局构造函数** → Evaluator 有注册但 VM 没有，VM 执行的 Option/Result 代码报"未定义变量" → 在 _setup_builtins() 中添加

#### 中等问题（8）

- [vm.py:181] read_line lambda 参数安全 bug（静默丢弃多余参数）
- [vm.py:204-218] 数学函数缺少类型/边界检查，Python 原生错误泄露
- [vm.py:795-802] CONTINUE fallback 中 loop_start 可能为 None
- [vm.py:772-778] BREAK 旧代码路径死代码仍残留
- [vm.py:871-875] INDEX 指令无边界检查和类型检查
- [vm.py:630-634] EQ 指令对含列表字段的 ADT 的 hash/eq 不一致
- [vm.py:358-370] 部分应用逻辑参数溢出风险
- [vm.py:379-380] 错误路径下栈一致性风险

#### 轻微问题（5）

- [vm.py:859-869] BUILD_MAP 不可哈希键泄露 TypeError
- [vm.py:617-624] CONCAT 不支持 List 的 ++ 拼接（需确认语言规范）
- [vm.py:336-337] _format_value 对 None 的处理掩盖问题
- [vm.py:1198-1206] HALT/AUTO_CALL_MAIN 在 _execute_instruction 中空操作
- [vm.py] 栈无上限（正常编译器产出不会无限压栈）

---

## [2026-07-15] 编译器 (compiler.py) 第十二轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | PIPE_CALL/MATCH_START_END/ADT 原生指令/FOR_ITER+LOOP_END |
| 可行性 | ⭐⭐⭐ | 模式匹配和 guard 已修复，但 while break 栈泄漏 |
| 正确性 | ⭐⭐⭐ | Pattern 测试代码生成已补全，guard 已实现，但 while/break 仍有严重 bug |
| 安全性 | ⭐⭐⭐ | 栈布局基本正确，while break 是例外 |
| 一致性 | ⭐⭐⭐ | for 循环已修复，while 循环仍有问题 |
| 完整性 | ⭐⭐⭐⭐ | AST 覆盖完整，MapExpr 已实现 |
| 工程质量 | ⭐⭐ | 仍有死代码、未使用操作码 |
| 性能 | ⭐⭐⭐ | 闭包不做自由变量分析影响效率 |

### 第十一轮问题修复状态

| 问题 | 状态 |
|------|------|
| Pattern 测试代码生成缺失 | ✅ 已修复 |
| guard 守卫条件被忽略 | ✅ 已修复 |
| 列表推导式 filter 被忽略 | ✅ 已修复 |
| for 循环栈状态不一致 | ✅ 已修复 |
| Block 中多余 POP | ✅ 已修复 |
| 模块导入无命名空间隔离 | ⚠️ 部分修复（加了警告） |
| while 循环不返回值 | ❌ 仍未修复 |
| 遗留死方法 | ❌ 仍未修复 |
| CLOSURE code_key 未使用 | ❌ 仍未修复 |
| 闭包不做自由变量分析 | ❌ 仍未修复 |

### 发现的问题

#### 严重问题（3）

- [compiler.py:1036-1044] **while 循环 break 栈泄漏** → break 跳过 POP 直接到 CONST_UNIT，栈上残留体结果 → 在 break 跳转目标前插入清理
- 追问：Rust 的 loop break 栈不变量破坏能被接受吗？→ **绝对不能**

- [compiler.py:1037,1044] **while 循环永远返回 Unit，与 AST 文档矛盾** → AST 文档声明"返回最后一次迭代值"但编译器固定 POP+CONST_UNIT → 要么实现语义，要么更新文档
- 追问：Scala 的 while 返回 Unit 但 Rust 的 loop 可返回值。文档与实现矛盾在任何编译器中不可接受。

- [compiler.py:421] **CharLiteral 编译为 CONST_STRING，运行时无法区分 String 和 Char** → PatternString("a") 匹配字符 'a'（违反类型安全）→ 引入 CONST_CHAR 操作码
- 追问：Haskell Char 和 String 完全不同类型，运行时混淆不可接受。

#### 中等问题（6）

- [compiler.py:891-955] 两个遗留死方法仍未删除
- [compiler.py:81,402,671] CLOSURE code_key 参数未使用
- [compiler.py:650-671] 闭包不做自由变量分析
- [compiler.py:48,75,90] LOOP/LOAD_CONST/INDEX 操作码从未生成
- [compiler.py:319-370] 模块导入仍无命名空间隔离
- [compiler.py:815-823] PatternIdentifier 与 ADT 构造器名冲突

#### 轻微问题（3）

- [compiler.py:856] 注释与实际行为不一致
- [compiler.py:1041-1044] break 不支持携带值
- [compiler.py:1106-1109] 列表推导过滤跳转可优化

---

## [2026-07-15] 求值器 (evaluator.py) 第十二轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 两遍扫描支持相互递归，内置 Option/Result 类型 |
| 可行性 | ⭐⭐⭐⭐ | 核心特性可用，MapExpr 和 guard 已修复 |
| 正确性 | ⭐⭐⭐ | UNIT_VALUE bool 已修复，但部分应用完全损坏 |
| 安全性 | ⭐⭐⭐ | 递归深度保护已有，但 String/Char 仍无区分 |
| 一致性 | ⭐⭐⭐ | 与 VM 差异减少但闭包捕获语义差异仍存 |
| 完整性 | ⭐⭐⭐⭐⭐ | 所有 AST 节点均有 eval 处理 |
| 工程质量 | ⭐⭐⭐ | eval_decl 重复代码仍存 |
| 性能 | ⭐⭐⭐ | 闭包引用语义效率可接受 |

### 第十一轮问题修复状态

| 问题 | 状态 |
|------|------|
| MapExpr 缺失 | ✅ 已修复 |
| guard 未实现 | ✅ 已修复 |
| UNIT_VALUE bool | ✅ 已修复 |
| 构造器 field_names | ✅ 已修复 |
| str_to_int field_names | ✅ 已修复 |
| assign NameError | ✅ 已修复 |
| String/Char 无区分 | ❌ 仍未修复 |

### 发现的问题

#### 严重问题（1）

- [evaluator.py:416-431] **闭包部分应用完全损坏** → partially_applied 函数定义但从未调用，返回的 NovaClosure 的 body 引用全部参数但 params 只有剩余参数 → 将已捕获参数绑定到中间环境
- 追问：OCaml 部分应用损坏，零容忍级别 bug。

#### 中等问题（4）

- [evaluator.py:680-684] String/Char 运行时无类型区分（历史遗留）
- [evaluator.py 多处] 运行时错误无源码位置信息
- [evaluator.py:336,372,375] abs/min/max 对 Int 输入返回 Float
- [evaluator.py:876] 整数除法使用 Python 地板除法（向负无穷取整）

#### 轻微问题（5）

- [evaluator.py:502-508] 闭包引用语义依赖但无注释说明
- [evaluator.py:570-625] eval_decl 与 _collect_decl 大量重复
- [evaluator.py:221,227] head/tail None field_names 与 VM 不一致
- [evaluator.py:384-404] _format_value 缺少 dict 格式化
- [evaluator.py:492,658,696] 冗余 NameError 捕获

---

## [2026-07-15] 类型检查器 (type_checker.py) 第十二轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | ADT 类型参数比较已修复 |
| 可行性 | ⭐⭐ | let 多态缺失、无 occurs check，泛型 ADT 基本不可用 |
| 正确性 | ⭐⭐ | 泛型构造函数未 fresh 实例化，for 循环变量类型不推导 |
| 安全性 | ⭐⭐ | _types_compatible 对 TypeVar 过于宽松 |
| 一致性 | ⭐⭐⭐ | ErrorCollector 已实现，注释与实现有不一致 |
| 完整性 | ⭐⭐⭐ | 所有 Pattern 类型检查完整，类型标注全部支持 |
| 工程质量 | ⭐⭐⭐ | TypeVar 命名不一致但功能正确 |
| 性能 | ⭐⭐⭐ | 单遍检查，无性能问题 |

### 第十一轮问题修复状态

| 问题 | 状态 |
|------|------|
| ADTType.__eq__ 不比较类型参数 | ✅ 已修复 |
| ErrorCollector 实现 | ✅ 已修复 |
| let 多态 | ❌ 仍未修复 |

### 发现的问题

#### 严重问题（3）

- [type_checker.py:779-789] **let 多态完全未实现** → 无 TypeScheme、无 free_type_vars、无 generalize → 引入 TypeScheme + fresh 实例化
- 追问：OCaml 缺少 let 多态连标准库都检查不了。

- [type_checker.py:1157-1177] **无 occurs check，统一化不完整** → 递归定义导致 TypeVar 无限循环 → 实现标准 unify + occurs check
- 追问：Haskell/OCaml 的 occurs check 是类型推断器最基本的安全保障。

- [type_checker.py:429-434] **泛型 ADT 构造函数未 fresh 实例化** → Box(1) 和 Box("hi") 共享同一个 TypeVar("T")，无法共存 → 每次 lookup 构造函数时 fresh 实例化
- 追问：Haskell 的 Maybe Int 和 Maybe String 可以共存，当前行为不可接受。

#### 中等问题（7）

- [type_checker.py:1070-1079] Int/Float 混合运算不支持，注释不一致
- [type_checker.py:1287-1288] _types_compatible 对 TypeVar 过于宽松
- [type_checker.py:917-922] for 循环变量类型未从可迭代对象推导
- [type_checker.py:949-950] 列表推导变量类型未推导
- [type_checker.py:755-770] PipeExpr 类型检查"第一个或最后一个参数"
- [type_checker.py:287] None 无参构造器 TypeVar 共享
- [type_checker.py:1107,1110] || 错误消息写死为 &&

#### 轻微问题（4）

- [type_checker.py:1095-1101] ==/!= 不检查操作数类型一致
- [type_checker.py:285-350] TypeVar 命名不一致
- [type_checker.py:1263-1281] 别名展开不完整
- [type_checker.py] 缺少类型推导上下文传递

---

## [2026-07-15] 词法分析器 (lexer.py) 第十二轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 标准 lexer 设计 |
| 可行性 | ⭐⭐⭐ | 基本功能可用，转义序列末尾崩溃 |
| 正确性 | ⭐⭐⭐ | 非法字符/未闭合字符串处理正确，末尾反斜杠 IndexErro |
| 安全性 | ⭐⭐ | 源码末尾转义序列导致 IndexError 崩溃 |
| 一致性 | ⭐⭐⭐ | Token 生成与 parser 预期基本一致 |
| 完整性 | ⭐⭐⭐⭐ | 所有语法元素有 Token |
| 工程质量 | ⭐⭐⭐ | 有死代码（_make_error、PIPE_VARIANT、UNIT） |
| 性能 | ⭐⭐⭐⭐ | 单遍扫描，性能好 |

### 发现的问题

#### 严重问题（1）

- [lexer.py:238,286] **字符串/字符末尾反斜杠导致 IndexError** → _advance() 在源码末尾无边界检查 → 在 esc = self._advance() 前检查 pos < len(source)

#### 中等问题（1）

- [lexer.py:155-160] _make_error 是死代码

#### 轻微问题（4）

- [lexer.py:250-251] 未识别转义序列静默保留
- [lexer.py:88] PIPE_VARIANT 是死 Token
- [lexer.py:91] UNIT Token 是死 Token
- [lexer.py:236-251,284-298] 转义处理逻辑重复

---

## [2026-07-15] 语法分析器 (parser.py) 第十二轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 标准递归下降 |
| 可行性 | ⭐⭐ | |> 优先级错误，for/while 不能在运算符右侧 |
| 正确性 | ⭐⭐ | 管道优先级高于比较运算违反所有函数式语言惯例 |
| 安全性 | ⭐⭐⭐ | 悬挂 else 已通过关键字解决 |
| 一致性 | ⭐⭐ | |> 优先级与 Elixir/F#/OCaml 不一致 |
| 完整性 | ⭐⭐⭐⭐ | 全部语法元素有处理 |
| 工程质量 | ⭐⭐⭐ | 前瞻扫描 map/block 歧义 |
| 性能 | ⭐⭐⭐ | _is_map_literal 前瞻 O(n^2) |

### 发现的问题

#### 严重问题（2）

- [parser.py:672-678] **管道操作符 |> 优先级高于比较运算符** → `x |> f > 2` 被解析为 `x |> (f > 2)` → 将 _parse_pipe() 移到 _parse_or_expr() 之前
- 追问：Elixir/F#/OCaml 的 |> 优先级低于比较运算符。优先级错误改变程序语义。

- [parser.py:464-466] **<- 拆为两个 Token 导致 `for i < -1..10` 错误解析** → `<-` 不是单一 Token，`for i < -1` 被误识别为范围语法 → 引入专门的 ARROW_LEFT Token

#### 中等问题（3）

- [parser.py:441-448] for/while 不能出现在运算符右侧
- [parser.py:386-388] 赋值检测 token 前瞻脆弱
- [parser.py:503-504] else-if 链产生深度嵌套 AST

#### 轻微问题（3）

- [parser.py:838-878] _is_map_literal 前瞻扫描 O(n^2)
- [parser.py:252-268] _parse_variant_def 回退解析副作用风险
- [parser.py:798-800] UNIT Token 死分支

---

## [2026-07-15] 错误处理 (errors.py) + 模块系统 (modules.py) + 环境 (environment.py) 第十二轮审查报告

### errors.py 评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 工程质量 | ⭐⭐⭐⭐ | Rust 风格多行高亮已实现 |

### modules.py 评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 可行性 | ⭐⭐⭐⭐ | 循环导入检测完整正确 |
| 完整性 | ⭐⭐⭐ | 路径解析覆盖三种情况 |

### environment.py 评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 正确性 | ⭐⭐⭐ | 作用域链正确，但闭包生命周期无管理 |
| 安全性 | ⭐⭐ | 运行时错误缺少源码位置 |

### 发现的问题

#### 严重问题（1）

- [environment.py:50-61] **运行时错误缺少源码位置** → RuntimeError_ 构造不传递 span/line/column → 所有 RuntimeError_ 接受可选位置参数
- 追问：Rust panic 总是包含文件名和行号。

#### 中等问题（8）

- [errors.py:177-179] 多行错误上下文只显示前后各 1 行，无省略指示
- [errors.py:340-344] raise_all 将后续错误扁平化为纯文本
- [errors.py:93] highlight_span 与 span 双轨状态
- [modules.py:357-364] stdlib 搜索路径依赖 cwd 而非安装目录
- [modules.py:366] 全局可变 ModuleManager 单例影响测试隔离
- [modules.py:276-291] _collect_exports 与 _collect_exported_types 代码重复
- [environment.py:26-28] 闭包捕获导致整个作用域链无法释放
- [environment.py] 缺乏 scope push/pop 协议，TypeEnv 和 Environment 重复实现

#### 轻微问题（6）

- [errors.py:48] NO_COLOR 检查不完全符合规范
- [errors.py:253-254] Span end_line None 比较隐患
- [errors.py:340-344] ContinueSignal 继承 Exception 而非 BaseException
- [modules.py:84] search_paths 类型标注
- [environment.py:67-72] all_bindings 静默覆盖
- [environment.py:26-28] 无变量析构机制

---

## [2026-07-15] 所有后端 第十二轮审查报告

### 可行性总结

| 后端 | 评估 | 说明 |
|------|------|------|
| Native (x86_64) | **Demo 级别** | 寄存器分配失效、浮点缺失、栈泄漏、_start 错误 |
| Cranelift | **Demo 级别** | 类型错误、分支标签硬编码、返回值丢失 |
| WASM | **Demo 级别** | block 无 end、分支反转、调用无参数、偏移错误 |
| x86_64 发射器 | **基本可用** | 指令编码正确有测试 |
| 编译管道 | **框架可用** | C 路径端到端可工作 |
| C 代码生成 | **最接近可用** | TryExpr 无法编译 |

### 严重问题汇总（26 个，全部未修复）

**Native 后端（7）**: 寄存器分配含 RAX/RSP、浮点 BinOp 缺失、重复 epilogue、返回值未传播、BinOp 破坏性写回、栈上 List/Tuple/ADT 无对齐无释放、_start argc 偏移

**Cranelift 后端（7）**: LIRBranch 标签硬编码、LIRStoreReg 静默忽略、BinOp 不区分 int/float、LIRCall 参数全 i64、LIRReturn 丢弃返回值、LIRLoadGlobal 未建立映射、LIRBuildTuple/ADT 不填充字段

**WASM 后端（10）**: LIRLabel 无 end、LIRJump 与 block 不匹配、LIRBranch 逻辑反转、LIRIndex block 嵌套问题、字符串偏移不一致、LIRCall 忽略参数、module 结构错误、一元取反分支缺失、运行时导入不匹配、固定 100 页内存

**C 代码生成（2）**: TryExpr 使用未定义 tag 常量、TryExpr 类型与结构体名不匹配

---

## [2026-07-15] IR 系统 (ir/) 第十二轮审查报告

### 三层 IR 设计评价
HIR→MIR→LIR 设计合理，与 LLVM/GCC/MLIR 层次一致。架构无严重问题，实现层面有大量缺陷。

### Pass 实现状态

| Pass | HIR | MIR | LIR | 状态 |
|------|-----|-----|-----|------|
| 常量折叠 | 部分（__class__ 变形） | 有实现 | 有实现 | ⚠️ 有缺陷 |
| 内联 | 空壳 | N/A | N/A | ❌ 未实现 |
| 死代码消除 | 空壳 | 空壳 | 有实现 | ⚠️ 部分实现 |
| CSE | N/A | 有实现 | 有实现 | ✅ 可用 |
| LICM | N/A | 有缺陷 | 有实现 | ⚠️ 有缺陷 |

### 严重问题（5）

- [pass_manager.py:105-108] **`__class__` 变形实现节点类型替换** → 不调用 __init__，对象可能不一致 → 创建全新实例替换
- [pass_manager.py:720-726] **Pass 异常被捕获后继续执行** → LLVM 的 opt 绝不会静默吞异常 → pass 失败应终止编译
- 追问：LLVM opt 静默吞 pass 异常能被接受吗？→ **绝对不能**

- [mir_lowering.py:351-384] **match 表达式无条件跳转第一个分支** → 所有分支都是无条件跳转，后续 arm 永远不可达 → 生成条件分支
- [mir_lowering.py:285-289] **ListComprehension 降级为空列表** → 总是产生空列表 → 实现迭代器协议
- [lir_lowering.py:141-147] **LIRCall 丢失所有参数寄存器位置** → 后端无法知道参数放在哪个寄存器 → 添加 arg_locs 字段
- [lir_lowering.py:219-223] **LIRBranch 丢失 true_label/false_label** → 条件分支永远不知道跳到哪里 → 设置分支目标

---

## [2026-07-15] C 运行时 (nova_runtime.c) 第十二轮审查报告

### 严重问题（3，全部未修复）

- [nova_runtime.c:99-103] **引用计数不处理循环引用** → 互相引用对象永久泄漏 → 引入标记-清除或弱引用
- [nova_runtime.c:193-196] **UTF-8 按字节索引而非字符索引** → 多字节字符（中文）返回错误字节 → 实现 UTF-8 解码
- [nova_runtime.c:536-538] **Map put 对非 NovaValue* 的 value 调用 release** → 未定义行为 → 改为模板/回调模式

### 中等问题（5）

- 列表/Map 派生操作不递增元素引用计数
- nova_list_contains/index_of 使用指针比较
- JSON \u 转义不处理代理对
- nova_init 不接受 argc/argv
- nova_pow 参数名遮蔽 math.h exp

---

## [2026-07-15] 测试套件 (tests/) 第十二轮审查报告

### 严重问题（2，全部未修复）

- **VM/后端路径零执行验证测试** → 编译器可能生成语义错误的代码 → 添加端到端执行测试
- 追问：GHC 缺少 ghc --make + 执行测试能被接受吗？→ **不能**

- **Evaluator 与 C 后端行为一致性完全无验证** → 两条执行路径可能产生不同结果 → 选取代表性程序双路径验证

### 中等问题（2）

- 大量核心语言特性缺少 Evaluator 测试（mut 赋值、Map、Char、? 操作符、match guard、while break/continue、嵌套构造器模式）
- test_nova.py 中 TestLoops 位于 `if __name__` 之后

---

## [2026-07-15] Tree-sitter (grammar.js) 第十二轮审查报告

### 严重问题（1）

- [grammar.js] **缺少 `?` 操作符** → IDE 无法正确解析 `expr?` 语法 → 添加 try_expr 规则

### 中等问题（3）

- escape_sequence 过于宽松
- map_expr 与 block_expr 的 `{}` 歧义未在 conflicts 中声明
- char_literal 的转义正则可能有问题

---

## 第十二轮全局总结

### 问题统计

| 类别 | 严重 | 中等 | 轻微 | 总计 |
|------|------|------|------|------|
| VM | 3 | 8 | 5 | 16 |
| 编译器 | 3 | 6 | 3 | 12 |
| 求值器 | 1 | 4 | 5 | 10 |
| 类型检查器 | 3 | 7 | 4 | 14 |
| 词法分析器 | 1 | 1 | 4 | 6 |
| 语法分析器 | 2 | 3 | 3 | 8 |
| 错误处理+模块+环境 | 1 | 8 | 6 | 15 |
| 后端（Native+Cranelift+WASM+C+管道） | 26 | 5 | 0 | 31 |
| IR 系统 | 5 | 10 | 5 | 20 |
| C 运行时 | 3 | 5 | 4 | 12 |
| 测试套件 | 2 | 2 | 1 | 5 |
| Tree-sitter | 1 | 3 | 2 | 6 |
| **总计** | **51** | **62** | **42** | **155** |

### 与第十一轮对比

| 指标 | 第十一轮 | 第十二轮 | 变化 |
|------|---------|---------|------|
| 严重问题总数 | 46 | 51 | +5 |
| 核心引擎（VM+编译器+求值器）严重问题 | 6 | 7 | +1（新增闭包部分应用损坏） |
| 类型系统严重问题 | 3 | 3 | 持平 |
| 前端（lexer+parser）严重问题 | 3 | 3 | 持平 |
| 后端严重问题 | 26 | 26 | 持平（全部未修复） |
| IR 严重问题 | 7 | 5 | -2（重新分类） |
| 已修复的历史问题 | - | ~20 | 多项历史问题已修复 |

### 最高优先级修复建议（P0）

1. **evaluator.py:416-431** — 修复闭包部分应用（核心语言特性损坏）
2. **type_checker.py** — 实现 let 多态 + occurs check + 泛型 fresh 实例化
3. **vm.py:810-812** — 闭包只捕获自由变量
4. **compiler.py:1036-1044** — while break 栈泄漏
5. **parser.py:672-678** — `|>` 优先级修正
6. **lexer.py:238** — 末尾反斜杠 IndexError

### 原创性亮点

- PIPE_CALL 专用管道调用指令（VM/编译器联合设计）
- MATCH_START/MATCH_END 显式标记（方便调试）
- ADT 原生指令集（MAKE_ADT/REGISTER_CTOR/MATCH_CONSTRUCTOR）
- FOR_ITER + LOOP_END 双指令循环设计
- Rust 风格错误信息（多行高亮、ANSI 颜色、批量收集）
- 三层 IR 架构（HIR→MIR→LIR）

---

## [2026-07-15] VM 虚拟机 (vm.py) 审查报告（第十三轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 为函数式语言定制的栈式 VM，PIPE_CALL、MATCH_*、TRY_UNWRAP 等指令有语言特色 |
| 可行性 | ⭐⭐⭐⭐ | 核心路径（函数调用、基本运算、模式匹配、for 循环）可运行 |
| 正确性 | ⭐⭐ | MOD 除零、while BREAK 栈泄漏、异常不安全、RETURN 语义冗余等严重问题仍未修复 |
| 安全性 | ⭐⭐⭐ | `id()` 做键已修复，但 Python 内部异常大量泄漏、全局 mutable 不保护 |
| 一致性 | ⭐⭐⭐ | 与 Evaluator 在全局 mutable、参数过多、read_line EOF、TryExpr 非 ADT 等方面仍不一致 |
| 完整性 | ⭐⭐⭐⭐⭐ | 全部 64 个操作码均有处理路径 |
| 工程质量 | ⭐⭐⭐ | 结构清晰，但存在死字段、脆弱启发式、重复代码 |
| 性能 | ⭐⭐ | 闭包全帧捕获 O(n)、纯 Python 解释执行性能上限低 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [vm.py:605-609] **MOD 取模除零保护完全缺失** → 当 `b` 为 0 时抛出 Python 原生 `ZeroDivisionError`，而非 Nova 的 `RuntimeError_`；与 DIV 指令（已检查整数除零）形成不一致 → 添加与 DIV 类似的除零检查，整数和浮点均需覆盖
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **结论：绝对不能。** 生产级运行时对整数/浮点除零必须给出明确定义的语言级错误。

- [vm.py:751-756] **while 循环 BREAK 不清理栈** → BREAK 带操作数时仅设置 ip，完全不清理循环体在栈上残留的中间值；与 for 循环 BREAK（正确使用 base_sp 截断栈）行为严重不一致；while CONTINUE 反而正确清理了栈，形成内部不一致 → 使用 `_while_loops[-1]["base_sp"]` 截断栈，并弹出 `_while_loops` 栈顶
  - 追问：如果是任何生产级语言的 VM，这个 bug 能被接受吗？→ **结论：绝对不能。** 栈深度一致性是 VM 正确性的根基。

- [vm.py:469-500] **`_run_code` 无 try/finally 异常安全保护** → 状态恢复代码不在 finally 块中，如果执行过程中抛出异常，VM 全局状态将被破坏；与 `_call_closure`（已有 try/finally）形成不一致 → 将状态恢复代码放入 finally 块
  - 追问：如果是 OCaml/Haskell 的运行时，这个 bug 能被接受吗？→ **结论：绝对不能。** 异常安全是生产运行时的底线。

- [vm.py:805-814] **闭包捕获整个帧 locals 而非仅自由变量** → 每次创建闭包都 O(n) 拷贝整个 locals dict 浅拷贝，时间 O(n)，阻止 GC 回收未被闭包使用的大对象；浅拷贝意味着可变对象在闭包内外共享，违反不可变性预期 → 编译器做自由变量分析，CLOSURE 指令携带自由变量名列表，VM 只拷贝指定变量
  - 追问：如果 OCaml 的闭包捕获了整个作用域的 dict 拷贝，性能影响能被接受吗？→ **结论：绝对不能。** 函数式语言中闭包创建是高频操作，全帧拷贝会让性能降低 10-100 倍。

- [vm.py:871-875] **INDEX 指令异常未包装** → 直接执行 `obj[index]`，`IndexError`、`KeyError`、`TypeError` 等 Python 原生异常直接泄漏；用户无法通过 Nova 的错误处理机制捕获这些错误 → 用 try/except 包装，将 Python 异常转换为 `RuntimeError_`
  - 追问：如果是 Haskell GHC，数组越界泄漏宿主语言异常能被接受吗？→ **结论：不能。** 运行时必须将所有操作错误转换为语言级异常。

- [vm.py:825-830 + 437-449] **RETURN 语义实现冗余且混乱** → 存在两套并行处理路径：`_execute_function` 前置检查 RETURN 弹栈直接返回，`_execute_instruction` 中 RETURN 弹栈后又压回原值设置 return_flag；两套路径行为不同 → 统一为单一 RETURN 处理路径，保留 return_flag 方案（与 TRY_UNWRAP 统一），移除前置检查
  - 追问：如果是 OCaml 的字节码解释器，同一条指令有两套不同实现路径能被接受吗？→ **结论：不能。** 关键指令的实现必须单一、清晰，冗余路径是 bug 的温床。

- [vm.py:181] **read_line 内置函数无 EOFError 处理且含死代码** → 未捕获 EOFError，遇到 EOF 时程序崩溃；`if a == ()` 检查是死代码 → 改为正规方法实现，添加 EOFError 捕获返回空字符串
  - 追问：如果是 Python 标准库的 input() 在 EOF 时不处理异常，能被接受吗？→ **结论：不能。** I/O 操作的边界情况必须正确处理。

#### 中等问题（影响特定场景）

- [vm.py:560-573] **STORE_VAR 对全局变量不检查 mutable** → 全局 let 绑定可以被随意修改，破坏不可变性保证
- [vm.py:394-397] **闭包调用参数过多时静默忽略** → 多余参数被静默丢弃，无任何错误提示
- [vm.py:697-705] **JUMP 的 while 回跳检测过于脆弱** → 通过启发式判断，可能误匹配
- [vm.py:771-778] **BREAK 回退路径使用前向扫描** → 扫描到 LOOP_END 或 CONST_UNIT 就停止，非常脆弱
- [vm.py:597-603] **浮点除法除零未检查** → `5.0 / 0.0` 返回 inf 而非报错
- [vm.py:164-167] **循环状态在异常时泄漏** → 循环体抛出异常时，循环状态不清理
- [vm.py:259-265] **read_file 仅捕获 FileNotFoundError** → 其他错误泄漏为 Python 原生异常
- [vm.py:164-165] **`_for_iters` 与 `_while_loops` 并存，循环管理混乱** → 两套独立栈增加状态一致性维护成本
- [vm.py:94,100-109] **NovaPartialBuiltin 部分应用机制不完整** → 部分应用类缺少 `__eq__`、`__hash__` 等方法

#### 轻微问题（代码质量）

- [vm.py:507] `_pop` 方法使用 `[::-1]` 反转列表，效率低
- [vm.py:1045-1056] MATCH_TEST_FLOAT 直接浮点相等比较，NaN 比较行为需注释说明
- [vm.py:1198-1201] Op.HALT 在 `_execute_instruction` 和 `_run_code` 中重复处理
- [vm.py:1001-1004, 1138-1141] MATCH_START / MATCH_END 是空操作
- [vm.py:433] `_execute_function` 循环条件包含 `not self.return_flag` 冗余
- [vm.py:173] `return_flag` 作为实例变量在调用间传递，设计脆弱

#### 原创性分析

**Nova VM 的创新点：** TRY_UNWRAP 指令统一处理 Option/Result 错误传播；PIPE_CALL 专用管道调用指令；MATCH_* 12 条模式匹配专用指令；ADT 原生支持（MAKE_ADT、REGISTER_CTOR）；FOR_ITER + LOOP_END 双指令循环。

**参考已有设计：** 基本栈机架构参考 CPython/JVM/Lua；闭包实现属于入门级方案。

#### Evaluator vs VM 对比
| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| Unit bool 语义 | `__bool__` = False | `__bool__` = False | ✅ 一致 |
| TryExpr 非 ADT 值 | 静默穿透，直接返回 | 抛 RuntimeError_ | ❌ VM 更严格 |
| `if` 条件非 Bool | 接受（Python truthiness） | 接受（JUMP_IF_FALSE 用 truthiness） | ⚠️ 两者都有问题 |
| 全局 mutable 检查 | Environment.assign 沿链检查 | 全局直接赋值，不检查 | ❌ VM 更松 |
| 参数过多 | 抛 RuntimeError_ | 静默忽略 | ❌ VM 更危险 |
| read_line EOF | 捕获 EOFError 返回 "" | 未捕获，可能崩溃 | ❌ VM 不安全 |
| 闭包实现 | Environment 引用链 | captured_vars 字典副本 | 实现不同，语义基本一致 |
| 整数除法 | `//` 向下取整 | `//` 向下取整 | ✅ 一致 |
| 递归深度保护 | MAX_CALL_DEPTH=1000 | MAX_CALL_DEPTH=1000 | ✅ 一致 |
| 管道操作 | 正确 | 正确 | ✅ 一致 |


---

## [2026-07-15] 编译器 (compiler.py) 审查报告（第十三轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | PIPE_CALL 专用指令、MATCH_TEST_* 系列模式匹配指令集、ADT 原生字节码有特色 |
| 可行性 | ⭐⭐⭐ | 核心路径可运行；嵌套模式匹配失败栈错位、嵌套 lambda 丢失、导入污染等会导致错误 |
| 正确性 | ⭐⭐ | 嵌套模式失败栈残留、lambda 子函数丢失、while break 栈不清理、导入构造器污染 |
| 安全性 | ⭐⭐ | 栈下溢无编译期校验、导入路径遍历风险、静默失败返回 Unit |
| 一致性 | ⭐⭐⭐ | 基本栈布局大体对齐；但嵌套模式失败路径、while break 路径与正常路径栈不一致 |
| 完整性 | ⭐⭐⭐⭐ | AST 节点 100% 有编译处理路径；死代码方法残留 |
| 工程质量 | ⭐⭐⭐ | 结构清晰；但有 60+ 行死代码、类型注解错误、重复模式 |
| 性能 | ⭐⭐⭐ | 闭包全量捕获、无尾调用优化、常量池去重用 O(n) 查找 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [compiler.py:751-766] **嵌套模式匹配失败时栈残留未清理** → 模式测试失败时统一跳转到 fail_cleanup_pos，仅一条 POP 清理 DUP 副本；但嵌套模式测试成功时已将 subject 分解为多个字段压栈，子模式测试失败时栈上残留 N 个已分解字段值 → 在 MATCH_START 记录 base_sp，失败时截断栈到 base_sp
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **结论：绝对不能。** 模式匹配是函数式语言的核心特性，嵌套模式失败时栈错位会导致完全错误的程序行为。

- [compiler.py:650-671] **Lambda 嵌套子函数丢失** → `_compile_lambda` 只提取了 lambda 自身的 code 和 constants，未将 `fn_bytecode.functions` 中的嵌套子函数/lambda 回写到外层；而 `_compile_fn_def` 中有对应处理 → 参照 `_compile_fn_def` 添加子函数提取循环
  - 追问：如果是 GHC/OCaml 丢失嵌套 lambda，能被接受吗？→ **结论：绝对不能。** 高阶函数和闭包是函数式语言的基石。

- [compiler.py:272-288, 348-370] **导入模块 ADT 构造器污染当前模块模式匹配** → 导入模块的 TypeDef 内联编译时，variant 名注册到当前编译器的 `_adt_constructors` 全局表中；违反模块隔离原则 → 为每个模块维护独立的 ADT 构造器表，或导入时添加模块前缀
  - 追问：如果是 Rust/Haskell/OCaml，这个 bug 能被接受吗？→ **结论：绝对不能。** 模式匹配的作用域规则是类型系统安全性的根基。

- [compiler.py:491-495 + vm.py:751-756] **while 循环 BREAK 不清理栈** → BREAK 直接跳转到 end_pos（CONST_UNIT 位置），不清理循环体栈上的中间值；与 for 循环行为不一致 → 在 while 循环入口记录 base_sp，BREAK 时截断栈到 base_sp 再压入 Unit
  - 追问：如果是 C/Java/Rust 的 while-break 不清理栈，能被接受吗？→ **结论：不能。** 虽然多数场景因语句级 POP 掩盖了问题，但这是潜在的栈泄漏和正确性隐患。

#### 中等问题（影响特定场景）

- [compiler.py:771-774] match 全失败路径静默返回 Unit，无任何警告或错误
- [compiler.py:397-399] 顶层函数的嵌套子函数全局平铺导致同名覆盖
- [compiler.py:490-506] while/for 嵌套 break/continue 归属判定脆弱
- [compiler.py:1044] while 循环不返回最后一次迭代值，与注释语义不符
- [compiler.py:81] CLOSURE 指令操作数定义与实际不符（code_key 未使用）

#### 轻微问题（代码质量）

- [compiler.py:891-955] `_compile_pattern_test` 和 `_compile_pattern_bindings` 两个死代码方法
- [compiler.py:592-598] PIPE 右侧 Identifier 加载存在无意义分支（两个分支代码完全相同）
- [compiler.py:225] `_while_end_stack` 类型注解错误
- [compiler.py:253-254] AUTO_CALL_MAIN 与 HALT 语义冗余
- [compiler.py:168-177] 常量池去重用 O(n) 查找（list.index）
- [compiler.py:420-421] CharLiteral 编译为 CONST_STRING 无类型区分
- [compiler.py:753-755] match arm 中 POP DUP 副本与 _compile_pattern_test_with_fail 的 POP 重复

#### 原创性分析

1. **PIPE_CALL 专用管道调用指令** — 将管道值作为最后一个参数传递
2. **MATCH_TEST_* 系列专用模式匹配指令** — 为每种字面量类型提供测试+跳转指令，元组/列表/构造器测试成功时自动分解字段压栈
3. **MATCH_START / MATCH_END 配对标记** — 显式标记模式匹配块
4. **ADT 原生指令集** — MAKE_ADT / REGISTER_CTOR / MATCH_CONSTRUCTOR
5. **TRY_UNWRAP 统一 Option/Result 错误传播**
6. **常量值直接内联指令操作数** — 减少常量池查表

---

## [2026-07-15] 求值器 (evaluator.py) 审查报告（第十三轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 两遍扫描支持相互递归、词法闭包引用语义、内置 Option/Result 类型 |
| 可行性 | ⭐⭐⭐⭐ | 核心特性全部可用；边缘场景有类型错误裸抛问题 |
| 正确性 | ⭐⭐⭐ | 核心语义正确；但 TryExpr 非 ADT 静默穿透、`if` 条件接受非 Bool 值 |
| 安全性 | ⭐⭐⭐ | 有递归深度保护；但多处裸 Python 异常、Map 键不可哈希崩溃 |
| 一致性 | ⭐⭐⭐ | 与 VM 存在 TryExpr 严格度、错误包装、`field_names` 一致性等差异 |
| 完整性 | ⭐⭐⭐⭐ | AST 节点覆盖率高；缺少 IndexExpr（AST 也无） |
| 工程质量 | ⭐⭐⭐ | 结构清晰，但 `eval_decl` 死代码重复、错误包装不统一 |
| 性能 | ⭐⭐⭐⭐ | 闭包引用语义（Environment 链）比 VM 的 dict 拷贝更高效；无尾递归优化 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [evaluator.py:741-747] **`if` 条件接受非 Bool 值，违反强类型语义** → `if` 表达式直接使用 Python truthiness 判断条件，任何值都可以作为条件；破坏了 Nova 声称的强类型语义 → 在 `_eval_if` 中添加类型检查，条件必须是 bool 类型
  - 追问：如果是 OCaml/Haskell 的编译器，`if 42 { ... }` 能通过运行时检查吗？→ **结论：绝对不能。** 强类型函数式语言的 `if` 条件必须是 Bool 类型。

- [evaluator.py:715-723] **TryExpr 对非 ADT 值静默穿透，类型约束完全失效** → `?` 操作符仅在值是 NovaADTValue 且 variant 为 None/Err/Some/Ok 时才有特殊行为；对于所有其他值直接原样返回 → 若值不是 NovaADTValue 或 variant 不是 None/Err/Some/Ok，抛出 RuntimeError_
  - 追问：如果是 Rust 的 `?` 操作符可以作用于非 Result/Option 类型，能被接受吗？→ **结论：绝对不能。** `?` 操作符的语义就是错误传播，必须严格限定在 Option/Result 类型上。

#### 中等问题（影响特定场景）

- [evaluator.py:866-867] 二元运算对类型不匹配抛出裸 Python TypeError
- [evaluator.py:792-793] MapExpr 键不可哈希时抛出裸 Python TypeError
- [evaluator.py:820-843] 字段访问对非 tuple/ADT 值错误信息过于笼统
- [evaluator.py:168 vs 221 vs 276] None 变体的 field_names 不一致
- [evaluator.py:912-913] 一元运算符 `!` 对非 Bool 值也能工作
- [evaluator.py:872-876] 整数除法 `//` 向下取整语义未明确
- [evaluator.py:570-625] `eval_decl` 方法是死代码，与两遍扫描逻辑重复
- [evaluator.py:997-1018] match guard 求值时创建了两次 child_env

#### 轻微问题（代码质量）

- [evaluator.py:81-82] `NovaADTValue.__hash__` 对含不可哈希字段的值可能崩溃
- [evaluator.py:302-305] UNIT_VALUE 和 None 在 JSON 序列化中都映射为 null
- [evaluator.py:496] `eval_program` 调用 main 未处理返回值
- [evaluator.py:658-659] 模块导入时绑定缺失静默忽略
- [evaluator.py:931-943] for 循环每次迭代都创建新的 child_env
- [evaluator.py:780-784] Assignment 错误捕获冗余包装
- [evaluator.py:358-365] `_convert_json_to_nova` 中 JSON 对象转换为 Nova Map 时键类型未验证
- [evaluator.py:850-856] 元组相等比较直接用 Python `==`，未考虑嵌套 ADT 值

#### 原创性分析

**Nova 特色设计：** 两遍扫描 + 词法闭包（支持相互递归）；Environment 链实现闭包（引用语义）；`?` 操作符统一 Option/Result 错误传播；BreakSignal/ContinueSignal 异常机制；ADT 构造器作为一等值。

**参考已有：** 基本的 AST walker 解释器模式是教科书标准；环境链作用域是经典的词法作用域实现。


---

## [2026-07-15] 类型检查器 (type_checker.py) 审查报告（第十三轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 基于 Python 实现的简化类型系统，有 ADT、模式匹配等现代语言特性 |
| 可行性 | ⭐⭐⭐ | 基本类型检查可用，但核心推断能力弱 |
| 正确性 | ⭐⭐ | let 多态缺失、守卫未检查、`==` 不检查类型、TypeVar 与任意类型兼容 |
| 安全性 | ⭐⭐ | 类型系统无法有效防止类型错误，本质上是 gradual typing |
| 一致性 | ⭐⭐⭐ | 多数特性实现风格一致，但错误处理和管道操作有不一致之处 |
| 完整性 | ⭐⭐ | 基础类型覆盖较全，但核心的 HM 推断、递归类型、多态等关键特性缺失 |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰，命名规范，但缺少注释、无统一的算法设计文档 |
| 性能 | ⭐⭐⭐ | 代码量小，无明显性能瓶颈 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [type_checker.py:779-789] **Let 多态完全未实现 — HM 类型系统的核心缺陷** → LetBinding 直接将推断出的类型赋值给变量名，没有泛化（generalization）步骤；`let id = fun x -> x in id 1 + id "a"` 会报错 → 实现完整的 HM 类型推断算法 W，包括 generalize 和 instantiate
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **结论：绝对不能。** Let 多态是 HM 类型系统的基石。

- [type_checker.py:969-977] **Match 守卫条件完全未做类型检查** → `check_match_arm` 方法中完全没有对 `arm.guard` 进行类型检查；守卫中的表达式可以是任意类型，守卫中引用的模式绑定变量不会被正确引入环境 → 在 check_match_arm 中添加守卫类型检查，守卫必须返回 Bool 类型
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **结论：绝对不能。** 守卫都是严格类型检查的，必须返回 Bool。

- [type_checker.py:1287-1288] **类型变量与任意类型兼容 — 本质上不是 HM 推断** → `_types_compatible` 中只要任意一方是 TypeVar 就返回 True；TypeVar 在这里的作用不是"待推断的类型变量"，而是"动态类型" → 实现真正的合一（unification）算法，TypeVar 通过 union-find 维护绑定关系
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **结论：绝对不能。** 这相当于把类型系统降级为了带部分静态检查的动态类型。

- [type_checker.py:740-750] **FnCall 中 TypeVar 被调用时绕过错误报告机制** → 被调用者类型为 TypeVar 时，直接调用 `self.error_collector.add()` 而不是 `_report_error()`；在非 collect_errors 模式下错误不会抛出 → 统一使用 `_report_error` 方法
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **结论：不能。** 错误报告机制的一致性是编译器工程的基本要求。

- [type_checker.py:1095-1101] **`==` 和 `!=` 操作符不检查操作数类型兼容性** → 只对 `< > <= >=` 做了数值类型检查，`==` 和 `!=` 直接返回 BOOL_T；`42 == "hello"` 等完全不同类型的比较不会被捕获 → 对 `==` 和 `!=` 添加类型兼容性检查
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **结论：绝对不能。** 相等比较的类型安全是静态类型系统最基本的保障之一。

- [type_checker.py:612-613, 630-632] **空列表/空 Map 共享同名 TypeVar，导致错误的类型合一** → 空列表使用固定名字 `"unknown_list_elem"` 的 TypeVar；所有空列表共享同一个元素类型变量 → 使用计数器生成唯一的 TypeVar 名称
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **结论：不能。** 每个独立的空列表应有自己的类型变量。

#### 中等问题（影响特定场景）

- [type_checker.py:916-927] For 循环变量类型与迭代器类型不关联
- [type_checker.py:941-963] ListComprehension 有同样的问题
- [type_checker.py:755-770] 管道操作符类型检查语义混乱且不做类型变量替换
- [type_checker.py:1157-1177] 缺少 occurs check（出现检查）
- [type_checker.py:1218-1221] 类型别名循环检测不可靠
- [type_checker.py:1159-1161] `_collect_type_bindings` 对冲突绑定不报错
- [type_checker.py:935-939] Break/Continue 在循环外使用不检测
- [type_checker.py:820-890] 递归 ADT 类型检查在无标注场景下可能失效

#### 轻微问题（代码质量）

- [type_checker.py:169] TypeVar 计数器是类级别全局状态
- [type_checker.py:1104-1112] `_check_binary_op` 中逻辑操作的错误消息硬编码
- [type_checker.py:1229-1237] `_from_ast_type` 中错误返回后仍继续构造类型
- [type_checker.py:279-293] 内置函数的类型变量命名不统一
- [type_checker.py:1263-1281] `_expand_alias` 函数不处理 TypeVar 中的别名
- [type_checker.py:113] 模式匹配不检查穷尽性
- [type_checker.py:71] 缺少模块级文档字符串

#### 原创性分析

1. **两阶段检查架构**：先收集声明签名，再检查函数体，支持前向引用和相互递归
2. **ADT 字段访问的"所有变体共有字段"检查**：支持对 ADT 按字段名或索引访问
3. **管道操作符的双参数检查**：同时尝试匹配第一个和最后一个参数
4. **简化的类型推断**：用"类型变量 + 函数调用处收集绑定 + 替换"替代完整的 HM 合一算法

---

## [2026-07-15] 词法/语法分析器 (lexer.py + parser.py) 审查报告（第十三轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 递归下降 + 表达式导向是标准做法；管道操作符、ADT 模式匹配有函数式语言特色 |
| 可行性 | ⭐⭐⭐ | 核心路径可用；但索引访问缺失、`<-` 歧义、优先级不一致影响可用性 |
| 正确性 | ⭐⭐ | `|>` 优先级与 grammar.js 矛盾、`++` 优先级不一致、`<-` LT+MINUS 拼接歧义 |
| 安全性 | ⭐⭐⭐⭐ | 无内存安全问题（Python）；错误抛出机制基本健全 |
| 一致性 | ⭐⭐ | 与 grammar.js 多处不一致 |
| 完整性 | ⭐⭐⭐ | 索引访问缺失、多行注释不支持、转义序列不完整 |
| 工程质量 | ⭐⭐⭐ | 结构清晰但有死代码 |
| 性能 | ⭐⭐⭐⭐ | 线性扫描，递归下降效率可接受 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [parser.py:672-678, 432-439] **`|>` 管道操作符优先级与 grammar.js 严重不一致** → parser.py 中 `|>` 优先级高于比较运算符，grammar.js 中 PIPE 是最低优先级 → 将 `_parse_pipe` 提升到表达式解析最外层，使 `|>` 成为最低优先级二元运算符
  - 追问：如果 GCC 的运算符优先级表与官方规范完全相反，这个 bug 能被接受吗？→ **结论：绝对不能接受。** 运算符优先级是语言规范的核心契约。

- [parser.py:680-687] **`++` 字符串拼接运算符优先级与 grammar.js 不一致** → parser.py 中 `++` 优先级高于 `+`/`-`，grammar.js 中 CONCAT 低于 ADD → 同步两边优先级表
  - 追问：如果 Clang 的字符串拼接优先级与语言规范不一致，能被接受吗？→ **结论：不能接受。** 前端解析与官方语法定义矛盾会导致用户困惑。

- [parser.py:464-466, 962-964] **`<-` 用 LT+MINUS 拼接导致歧义** → `<-` 并非独立 token，而是通过先匹配 `<` 再 `_expect(MINUS)` 拼接实现 → 在 lexer 中添加 LEFT_ARROW token（`<-`）
  - 追问：如果 GCC 的 `->` 成员访问用 `-` + `>` 拼接实现，能被接受吗？→ **结论：绝对不能接受。** 多字符运算符必须作为独立 token 处理。

- [parser.py:733-763] **索引访问 `expr[index]` 完全未实现** → `_parse_postfix_expr` 中完全没有处理 LBRACKET；list[0]、arr[i] 等所有索引操作都无法解析 → 在 `_parse_postfix_expr` 的 while 循环中添加 LBRACKET 分支，同步添加 IndexExpr 类
  - 追问：如果 Rust 编译器不支持 `vec[i]` 索引语法，能被接受吗？→ **结论：不能接受。** 索引访问是数组/列表/Map 类型的基本操作语法。

- [parser.py:758-761] **`?` 操作符放在 postfix 循环之外，链式调用错误** → `foo?()` 无法正确解析；`opt?.field` 被解析为 `(opt.field)?` → 将 `?` 处理移入 while 循环内部，与函数调用、字段访问同级别
  - 追问：如果 Rust 的 `?` 运算符后面不能跟方法调用，能被接受吗？→ **结论：不能接受。** `?` 作为后缀运算符应与其他后缀操作同级别。

- [lexer.py:252-258] **未闭合字符串/字符错误恢复时丢失错误位置信息** → 直接跳过错误 token，Token 流中没有 ERROR token 占位；错误仅存储在 self.errors 列表（字符串）中 → 生成 ERROR token 插入 token 流，携带错误位置信息
  - 追问：如果 GCC 遇到词法错误时静默跳过且不记录错误位置，能被接受吗？→ **结论：绝对不能接受。** 错误恢复是编译器前端的基本功能。

#### 中等问题（影响特定场景）

- [lexer.py:88] PIPE_VARIANT Token 定义但从不生成
- [lexer.py:91, parser.py:798-800] UNIT Token 定义但从不生成
- [lexer.py:155-160] `_make_error` 方法是死代码
- [parser.py:534-536] match guard 位置与 grammar.js 不一致
- [parser.py:960-968] 列表推导式 range 形式不支持 step
- [lexer.py:240-251, 287-298] 字符串/字符转义序列不完整
- [lexer.py:186-200] 不支持多行注释 `/* */`
- [lexer.py:202-221] 数字字面量限制（不支持科学计数法、十六进制等）
- [parser.py:386-391] block 中赋值检测仅支持简单标识符
- [parser.py:294-308] 元组类型 `(A, B) -> C` 的歧义

#### 轻微问题（代码质量）

- [lexer.py:107 vs ast_nodes.py:22] Token.end_col 与 Span.end_column 命名不一致
- [parser.py:36] Parser 不消费 Lexer 的 errors
- [parser.py:402-411] block 中缺少分号的连续表达式被默许
- [parser.py:580-588] 负数模式的 Span 未覆盖数字部分
- [parser.py:133-136] `export` 语法限制过严（只能导出标识符）
- [parser.py:859-877] `is_map_literal` 向前扫描可能跨越不匹配的括号
- [lexer.py:172-175] 关键字列表与 TokenType 枚举分离，容易不同步

#### 原创性分析

**Nova 特色设计：** 表达式导向的 for/while；`|>` 管道操作符；`?` 错误传播操作符；`then` 关键字消除悬挂 else；ADT + 模式匹配；列表推导式。

**参考已有：** 递归下降解析（教科书标准）；优先级爬升（通过函数调用层级隐式实现）；Token 设计参考常见语言。


---

## [2026-07-15] 错误处理 + 模块系统 + 环境 (errors.py + modules.py + environment.py) 审查报告（第十三轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 错误报告借鉴 Rust 风格，模块系统和环境是经典实现 |
| 可行性 | ⭐⭐⭐ | 基本功能可用，但存在多处关键缺陷 |
| 正确性 | ⭐⭐⭐ | 作用域链基本正确，但模块路径遍历、循环导入、错误收集均有问题 |
| 安全性 | ⭐⭐ | **路径遍历攻击完全无防护**，模块系统可读取任意文件 |
| 一致性 | ⭐⭐⭐ | 错误信息格式基本统一，但 Lexer 错误处理方式与其他阶段不一致 |
| 完整性 | ⭐⭐⭐ | 功能覆盖面较广但深度不足 |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰、注释充分，但缺少防御性编程 |
| 性能 | ⭐⭐⭐⭐ | 基本操作均为 O(1) 或 O(n)，无明显性能瓶颈 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [modules.py:107-140] **模块系统路径遍历漏洞 — 无任何防护** → `resolve()` 方法对传入的 module_path 完全不做安全校验；相对路径 `../` 可以无限制向上导航，绝对路径可以指向系统任意文件 → 添加沙箱根目录限制，所有解析出的路径必须位于允许的搜索路径内
  - 追问：如果是 Rust 编译器的模块系统允许路径遍历读取任意文件，能被接受吗？→ **结论：绝对不能。** 这是安全漏洞级别问题。

- [modules.py:211-218] **循环导入检测存在竞态 — 缓存检查早于栈检查** → 模块在完全加载前就可以被部分使用；eval_program 执行过程中，另一个 import 尝试导入该模块会因缓存未命中而再次加载 → 在开始加载时就创建"正在加载中"的占位符加入缓存
  - 追问：如果是 Python 的 import 系统循环导入检测不可靠，能被接受吗？→ **结论：不能。** 生产级语言应该提供更清晰的诊断和更可靠的检测。

- [errors.py:358-426] **ErrorCollector 与异常机制不兼容 — 实际无法批量收集** → Lexer 不使用 ErrorCollector；Parser 不支持收集模式；TypeChecker 有部分支持但有直接 raise 绕过收集机制的路径 → Lexer 错误改用 LexerError 对象；Parser 实现错误恢复机制；TypeChecker 所有错误通过 _report_error 发出
  - 追问：如果是 Rust 编译器只能报告类型错误遇到第一个语法错误就崩了，能被接受吗？→ **结论：绝对不能。** 生产级编译器的标志是"一次编译报告所有错误"。

- [environment.py:50-61] **闭包环境生命周期管理缺失** → 没有任何生命周期管理机制（无引用计数、无 GC 根标记、无闭包环境的特殊处理）；如果函数返回后环境被销毁，闭包会悬空引用 → 闭包创建时捕获其定义时的整个环境链；使用共享引用存储可变变量
  - 追问：如果是 Scheme 的闭包捕获后外层环境被销毁，能被接受吗？→ **结论：绝对不能。** 闭包延长捕获变量的生命周期是函数式语言的基本语义。

- [errors.py:157-263] **错误信息缺少文件名 — 只有行号列号** → 格式化错误时只显示行号列号，不显示文件名；多文件项目中无法定位到具体文件 → 给 NovaError 添加 file_path 字段
  - 追问：如果是 Rust 编译器的错误信息缺少文件名，能被接受吗？→ **结论：不能。** 文件名+行号+列号是最基本的定位信息。

#### 中等问题（影响特定场景）

- [modules.py:328-337] 导入命名冲突无处理机制，静默覆盖
- [modules.py:126-128] 相对路径解析依赖 search_paths[0] — 脆弱的隐式约定
- [errors.py:265-283] 错误下划线计算在多行场景下偏移错误
- [modules.py:49-58] ModuleInfo.get_exported_bindings 静默吞掉错误
- [modules.py:330] 所有导入的绑定都被设为不可变 — 语义正确但缺少提示
- [lexer.py:255,264,278] Lexer 错误存储为字符串而非 LexerError 对象
- [environment.py:40,48,61] 环境查找失败抛出 RuntimeError_ — 类型不一致

#### 轻微问题（代码质量）

- [errors.py:320] RuntimeError_ 命名带下划线后缀
- [errors.py:61] SourceSpan 别名无意义
- [errors.py:93, 172-174] highlight_span 旧格式兼容增加复杂度
- [modules.py:276-299] _collect_exported_types 与 _collect_exports 逻辑重复
- [environment.py:67-72] all_bindings 方法名称有歧义
- [errors.py 各处] 错误消息中文化但代码是英文，国际化策略不明确
- [modules.py:188-189] type_checkers 和 evaluators 字典可能冗余

#### 原创性分析

**错误系统（errors.py）：** 借鉴 Rust 编译器的错误报告风格——severity 分级、related note/help、源码上下文高亮、ANSI 颜色；ErrorCollector 的收集模式和立即抛出模式切换有一定实用价值。

**模块系统（modules.py）：** 经典的模块系统设计——解析器+管理器分离、缓存、加载栈检测循环，类似于 Python 的 importlib 机制。

**环境系统（environment.py）：** 经典的词法作用域链实现，与大多数解释器教材中的实现一致。

---

## [2026-07-15] 所有后端审查报告（第十三轮）

### 总体评分
| 维度 | native_backend | cranelift_backend | wasm_backend | x86_64 | c_codegen |
|------|---------------|-------------------|--------------|--------|-----------|
| 原创性 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 可行性 | ⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 正确性 | ⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 安全性 | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| 一致性 | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 完整性 | ⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 工程质量 | ⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 性能 | ⭐ | N/A | N/A | ⭐⭐⭐ | N/A |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [native_backend.py:734-798] **栈上分配的 ADT/List/Tuple 返回后为悬空指针** → _compile_build_list、_compile_build_tuple、_compile_build_adt 均在当前函数栈帧上分配空间构建数据结构；函数返回后栈帧销毁，返回的指针指向已回收的栈空间 → 调用运行时的 malloc/nova_alloc 在堆上分配空间
  - 追问：如果是 OCaml 的 native 编译器生成的代码不正确，能被接受吗？→ **结论：绝对不能。** 值逃逸函数作用域时仍使用栈分配是不可接受的编译器 bug。

- [native_backend.py:202-211] **寄存器分配器永不释放寄存器** → _alloc_vreg 从空闲列表弹出寄存器分配给虚拟寄存器，但从未将寄存器归还；LinearScanAllocator 类完整实现但完全未被使用 → 正确使用 LinearScanAllocator 进行全局寄存器分配
  - 追问：如果是 OCaml 的 native 编译器寄存器分配不正确，能被接受吗？→ **结论：不能。** 寄存器分配器是正确性的基础保障。

- [native_backend.py:340-381] **函数入口不设置参数寄存器** → 函数序言仅保存 callee-saved 寄存器和分配栈帧，但从未将函数参数从 ABI 寄存器移动到虚拟寄存器映射中 → 在函数序言后、函数体前，遍历 func.params，将每个参数从对应的 ABI 寄存器移动到分配的虚拟寄存器中
  - 追问：如果是 OCaml 的 native 编译器函数参数加载错误，能被接受吗？→ **结论：不能。** 函数参数传递是 ABI 兼容性的核心。

- [native_backend.py:673-720] **`_compile_index` 破坏基址寄存器** → 索引操作使用 add_reg_reg 将偏移量直接加到 base_reg 上，原地修改了基址寄存器的值 → 使用 lea 指令计算有效地址到目标寄存器
  - 追问：如果是任何生产级编译器的索引操作破坏基址寄存器，能被接受吗？→ **结论：不能。** 这是基础的代码生成正确性问题。

- [c_codegen.py:199-237] **ADT 结构体与运行时 NovaADT 不兼容** → c_codegen 生成的 ADT 结构体使用扁平结构体，而运行时定义的 NovaADT 使用 tag + fields 指针数组；两者内存布局完全不同 → 统一使用运行时的 NovaADT 结构体和 API
  - 追问：如果是 OCaml 的 C FFI 与运行时内存布局不兼容，能被接受吗？→ **结论：绝对不能。** 内存布局不兼容会导致所有跨模块 ADT 传递失败。

- [cranelift_backend.py:137-201] **基本是空壳，生成的 CLIF 无法编译** → SSA 值管理混乱，基本块结构缺失，函数参数未使用 → 重写整个 Cranelift 后端
  - 追问：如果是 OCaml 的 native 后端生成的代码无法通过验证器，能被接受吗？→ **结论：不能。** 后端至少要能生成可通过验证的中间表示。

- [wasm_backend.py:229-297] **操作数栈管理完全缺失** → WebAssembly 是基于栈的虚拟机，但 WasmGC 后端完全没有跟踪操作数栈状态；LIRStoreReg 是空实现 → 实现操作数栈模拟器
  - 追问：如果是任何 WebAssembly 编译器生成的代码通不过验证器，能被接受吗？→ **结论：不能。** 栈不平衡的 Wasm 代码会被验证器直接拒绝。

- [compiler_pipeline.py:33-35] **BACKEND_NATIVE 实际使用 CraneliftBackend** → 当 target == BACKEND_NATIVE 时，代码创建的是 CraneliftBackend 实例，而不是 NativeCodeGen → 将 NativeCodeGen 接入编译管道，或修改常量名
  - 追问：如果是 GCC 的 -O2 优化选项实际执行的是 -O0，能被接受吗？→ **结论：绝对不能。** 编译目标选项与实际行为不一致是严重的诚信问题。

- [c_codegen.py:590-600] **TryExpr 使用错误的字段名 `variant_tag`** → 引用 `{temp}->variant_tag`，但 c_codegen 自身生成的 ADT 结构体字段名是 `tag` → 统一字段命名

#### 中等问题（影响特定场景）

- [native_backend.py:518-522] 返回值未显式移动到 RAX
- [native_backend.py:233-240] `_compile_branch` 中条件寄存器来源不可靠
- [native_backend.py:444-467] 浮点比较运算未实现
- [x86_64.py:81-93] `mov_reg_imm64` 大负数处理错误（注释声称零扩展，实际是符号扩展）
- [wasm_backend.py:230-232] LIRLabel 编译为 block 而非 loop/block 标签
- [wasm_backend.py:161] 字符串编码中 `\x00` 是字面量而非 null 字节
- [cranelift_backend.py:216-238] 浮点比较未使用 float_op_map
- [cranelift_backend.py:204] `iconst` 指令名错误（应为 i64const）
- [c_codegen.py:850-871] ADT 构造器使用 GNU C 复合字面量扩展
- [c_codegen.py:1301-1302] `_infer_c_type_from_expr` 对 Identifier 默认返回 int64_t

#### 轻微问题（代码质量）

- [native_backend.py:35-82] LinearScanAllocator 定义了但从未使用
- [native_backend.py:804-826] `_compile_counted_loop` 是空方法
- [x86_64.py:275-287] `movsd_reg_imm` 方法名误导
- [wasm_backend.py:43] 类名叫 WasmGCBackend 但几乎没用到 WasmGC
- [cranelift_backend.py:288-292] `compile_to_object` 的 fallback 名不副实
- [c_codegen.py:35-60] C_KEYWORDS 集合包含大量非关键字
- 所有后端：缺少端到端执行测试

#### 原创性分析

**x86_64 编码器 + native_backend：高原创性** — 从零实现了完整的 x86_64 指令编码器（ModR/M、REX 前缀、SIB 寻址等），以及 ELF 可执行文件生成器。不依赖任何外部汇编器或编译器，直接输出机器码字节。

**三层 IR 设计：中等原创性** — 参考了 MLIR 的 Dialect 思想，但实现较为轻量化。

**c_codegen：低原创性** — C 代码生成是最常见的 transpiler 方案。


---

## [2026-07-15] IR 系统 + Pass 管理器 (ir/) 审查报告（第十三轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 架构设计 | ⭐⭐⭐ | 三层 IR 概念清晰，但分层职责模糊，MIR 未真正实现 SSA |
| 降级完整性 | ⭐⭐ | 多处降级为退化实现：match 完全退化、ListComprehension 降为空列表 |
| 模式匹配 | ⭐ | MIR match 完全退化为顺序跳转，LIR 进一步退化为无条件跳转 |
| 循环语义 | ⭐⭐ | while 循环结构正确，但 for 循环的迭代语义完全丢失 |
| 闭包支持 | ⭐ | Lambda 降级仅创建占位字符串，自由变量完全丢失 |
| Pass 实现 | ⭐⭐ | 常量折叠三层均有实现；Inlining 完全空壳；DCE/CSE 在 LIR 层有实现 |
| 代码质量 | ⭐⭐ | 大量 `__class__` 动态修改类、`del` 属性、异常处理粗糙 |
| 性能 | ⭐⭐⭐ | 代码量小无明显性能瓶颈，但优化 pass 效果有限 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [mir_lowering.py:351-384] **MIR match 表达式完全退化 — 所有分支被无条件执行** → 所有 arm 通过 MIRJump 无条件依次跳转到每个 arm 块，没有任何条件判断或值比较；第一个 arm 永远被执行 → 对字面量模式生成比较+条件分支链；对构造器模式生成 variant tag 比较+字段解构
  - 追问：如果 LLVM 的 switch 指令退化为无条件跳转，能被接受吗？→ **结论：绝对不能。** 模式匹配是函数式语言的核心控制流结构。

- [mir_lowering.py:285-289] **ListComprehension 降级为常量空列表 — 语义完全丢失** → HIRListComprehension 被直接降级为一个值为 `[]` 的 MIRConst，完全忽略了所有语义信息 → 应降级为循环 + 列表追加操作的等价 MIR 序列
  - 追问：如果是任何生产级编译器的列表推导式返回空列表，能被接受吗？→ **结论：绝对不能。** 这是静默的语义错误。

- [mir_lowering.py:247-250] **Lambda 闭包自由变量完全丢失** → HIRLambda 降级仅创建 MIRClosureCreate，captures 列表为空；Lambda 的 body 和 params 完全被丢弃 → 实现闭包转换（closure conversion）
  - 追问：如果是 OCaml 的闭包丢失了所有捕获变量，能被接受吗？→ **结论：绝对不能。** 闭包是函数式语言的基石。

- [pass_manager.py:720-725, 738-741, 754-757] **Pass 管理器静默吞掉所有异常 — 优化失败不可感知** → 三个方法都用 try/except Exception 捕获所有异常，仅记录到 self.errors 并打印到 stderr，然后继续执行下一个 pass → 默认行为：pass 异常应向上传播，终止编译
  - 追问：如果 LLVM 的 opt 工具静默吞掉所有 pass 异常，能被接受吗？→ **结论：绝对不能。** 静默吞异常意味着生成的代码可能是错误的，而用户毫不知情。

- [lir_lowering.py:231-241] **MIRSwitch / MIRMatchJump 在 LIR 层退化为无条件跳转** → MIRSwitch 降级为跳转到 default 分支的无条件跳转，完全忽略所有 case → MIRSwitch 应降级为比较+条件跳转序列或跳转表
  - 追问：如果是任何编译器的 switch 语句退化为无条件跳转，能被接受吗？→ **结论：绝对不能。** 这是控制流的根本性错误。

- [lir_lowering.py:219-223] **LIRBranch 缺少 true/false 标签赋值** → MIRBranch 降级为 LIRBranch 时，只设置了 src_locs，但完全没有设置 true_label 和 false_label 字段 → 添加 true_label 和 false_label 的设置
  - 追问：如果是任何编译器的条件跳转没有目标地址，能被接受吗？→ **结论：绝对不能。** 控制流指令没有目标地址等于生成无效代码。

- [mir_lowering.py:396-417] **For 循环迭代语义完全丢失 — 直接用 iterable 当布尔条件** → for 循环降级时直接将 iter_ssa 作为 MIRBranch 的条件；没有迭代器创建、没有 next() 调用、没有元素绑定到循环变量 → 生成迭代器创建代码，在 header 块中调用 next 并检查终止
  - 追问：如果是 Python 的 for 循环直接把列表当条件判断，能被接受吗？→ **结论：绝对不能。** 这意味着 for 循环要么死循环要么不执行。

- [pass_manager.py:257-262] **Inlining 是完全的空壳** → Inlining.run() 直接 return False，没有任何内联逻辑；但它被加入了默认优化管道 → 要么实现基本的内联，要么从默认管道中移除
  - 追问：如果 GCC 的 -O3 选项包含一个空的优化 pass，能被接受吗？→ **结论：不能。** 空壳 pass 不仅浪费编译时间，还会误导用户。

#### 中等问题（影响特定场景）

- [pass_manager.py:105-108, 115-118] HIR 常量折叠使用 `__class__` 动态修改 + `del` 属性 — 极度危险
- [mir_lowering.py:275-283] MIR 不是真正的 SSA 形式 — 变量既可以是 SSA 寄存器又可以是内存位置
- [lir_lowering.py:204-211] LIR Phi 节点降级只取第一个 source — 语义错误
- [pass_manager.py:652-691] LICM MIR 层实现只看 header 块 — 外提位置错误
- [pass_manager.py:346] LIR DCE 不考虑 LIRBinOp 等指令的副作用判断不一致
- [pass_manager.py:596-608] LIR 层的 LICM 外提到 header 之后 — 位置错误
- [lir_lowering.py:225-229] MIRReturn 的值在 LIR 中类型硬编码为 UNIT_TYPE
- [lir_lowering.py:114-119] MIRStore 在 LIR 中降级为 LIRStoreGlobal — 语义改变
- [hir_lowering.py:328-330] HIR 模式中构造器模式的 type_name 为空
- [lir_lowering.py:171-176] LIRMapBuild 降级为 LIRBuildList — 类型信息丢失

#### 轻微问题（代码质量）

- [pass_manager.py:458-485] MIR 层 CSE 只在基本块内做，不考虑跨块公共子表达式
- [hir_lowering.py:115-118] HIR Lowering 顶层声明的 else 分支吞掉未知声明类型
- [pass_manager.py:28-29] Pass 基类的 run 方法抛出 NotImplementedError，但子类不调用 super
- [mir_lowering.py:307] `_lower_expr` 默认返回 None 而非抛出错误
- [lir_lowering.py:88] LIRFunction 的 stack_size 计算过于简化（所有虚拟寄存器都占 8 字节）
- [ir_nodes.py:821-825] LIRBranch 的 cond_reg 字段与 src_locs 冗余
- [pass_manager.py:549] 循环 LICM 中 back_edge_end 初始值不合理
- [pass_manager.py:715, 731, 747] Pass 管理器的 max_iterations 默认值 10 可能不够

#### 原创性分析

**架构设计的原创性：** 三层 IR（HIR→MIR→LIR）的设计借鉴了 MLIR Dialect 和 Rust 编译器的分层思想，并非原创。但将其用 Python 实现并精简到单文件每一层，有一定的工程简洁性考量。

**节点定义的原创性：** 节点类型命名和组织方式参考了 MLIR 和 Rust MIR 的常见做法；三层共享类型系统的设计有一定特色。

**Pass 实现的原创性：** 常量折叠、DCE、CSE、LICM 都是标准优化，算法逻辑是通用的；LICM 的 "back-edge 识别 + 循环不变判断" 框架是教科书式的，但实现有缺陷。

---

## [2026-07-15] C 运行时 + 测试套件 + Tree-sitter 审查报告（第十三轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| C 运行时内存安全性 | ⭐⭐ | 引用计数无下溢保护、map/list 元素不释放、循环引用完全不处理 |
| 测试覆盖完整性 | ⭐⭐⭐ | Evaluator 测试 ~65 个，VM 测试 ~90+ 个，但缺少一致性测试和端到端测试 |
| Tree-sitter 语法一致性 | ⭐⭐ | 优先级顺序与 parser.py 不一致，缺少泛型类型参数语法 |
| 代码质量与可维护性 | ⭐⭐⭐ | 代码结构清晰、命名规范，但 C 运行时注释与实际行为不符 |
| 架构设计 | ⭐⭐⭐⭐ | 多后端架构设计良好 |
| 安全性 | ⭐⭐ | HTTP 临时文件 TOCTOU 未修，路径遍历漏洞存在 |
| 性能优化 | ⭐⭐⭐ | GC 空壳影响长期运行性能，闭包 O(n) 拷贝 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [nova_runtime.c:323-330, 479-486, 651-668, 749-756, 791-798, 1468-1494] **引用计数完全没有下溢保护，可导致 double-free** → 所有 `*_release` 函数都使用 `ref_count--` 后判断 `<= 0` 的模式，但完全没有检查递减前是否已经为 0 或负数 → 在递减前检查 `ref_count > 0`，或使用断言
  - 追问：如果是 C++ shared_ptr 多次释放，能被接受吗？→ **结论：绝对不能。** 这是引用计数运行时最基础的安全防线。

- [nova_runtime.c:597-614] **`nova_map_remove` 不释放 value，导致内存泄漏** → 只释放了 entry 的 key 和 entry 本身，但完全没有释放 entry->value → 在释放 entry 前释放 value
  - 追问：如果是 Python dict 的 del 不释放 value，能被接受吗？→ **结论：不能。** 这是教科书级的内存泄漏 bug。

- [nova_runtime.c:651-668] **`nova_map_release` 不释放 entry 的 value，整体释放路径泄漏所有 value** → 释放整个 map 时，遍历所有 bucket 释放 entry 的 key 和 entry 结构体，但完全没有释放每个 entry 的 value → 在释放循环中添加 value 释放
  - 追问：如果是 Rust 的 HashMap drop 时不释放 value，能被接受吗？→ **结论：绝对不能。** 容器析构函数必须释放所有持有的资源。

- [nova_runtime.c:479-486] **`nova_list_release` 不释放列表元素，列表析构时所有元素泄漏** → 只释放了 `items` 数组本身，但数组中每个元素都没有被释放 → 假设元素都是 NovaValue* 并调用 nova_value_release
  - 追问：如果是 C++ vector 的析构函数不调用元素的析构函数，能被接受吗？→ **结论：绝对不能。** 容器释放时不释放其内容，等于整个容器内存管理完全失效。

- [nova_runtime.c:99-103] **GC 完全不处理循环引用，`nova_gc_collect` 只是返回分配计数** → nova_gc_collect 不做任何实际的垃圾回收，只是返回净分配数；函数名具有严重误导性 → 要么实现真正的循环引用检测，要么将函数重命名并明确说明
  - 追问：如果是 Java 的 GC 什么都不回收，能被接受吗？→ **结论：不能。** 一个名为 gc_collect 的函数什么都不回收，是 API 设计层面的严重问题。

- [nova_runtime.c:79-87] **`nova_realloc` 不更新 g_free_count 和 g_alloc_count，导致分配统计错误** → realloc 分配新内存时，旧内存被释放、新内存被分配，但计数完全没有反映这一变化 → 在 nova_realloc 中正确更新计数
  - 追问：如果是任何语言的分配器统计功能不准确，能被接受吗？→ **结论：不能。** 分配器的统计功能必须准确。

- [nova_runtime.c:525-538] **`nova_map_put` 中 value 释放使用类型强转，对非 NovaValue* value 是未定义行为** → 将 entry->value（类型为 void*）强制转换为 NovaValue* 并调用 nova_value_release → Map API 应该明确 value 的生命周期管理方式，增加 value_free_fn 回调参数

- [grammar.js:88-97] **Tree-sitter 语法缺少泛型类型参数，与 parser.py 不一致** → parser.py 支持 type Option[T] 这样的泛型 ADT 定义，但 tree-sitter 语法完全没有类型参数部分 → 添加可选的类型参数列表
  - 追问：如果是成熟语言的语法定义缺少泛型支持，能被接受吗？→ **结论：不能。** 泛型是现代语言的核心特性。

- [grammar.js:612-624 vs parser.py:428-725] **Tree-sitter 运算符优先级与 parser.py 不一致** → 管道操作符 `|>` 的优先级、字符串拼接 `++` 的优先级等都不一致 → 使 tree-sitter 的优先级与 parser.py 完全一致
  - 追问：如果是成熟语言的两个解析器优先级不一致，能被接受吗？→ **结论：绝对不能。** 运算符优先级是语言语法的核心规范。

- [全部测试文件] **测试套件缺少 Evaluator 与 VM 的行为一致性测试** → 没有任何测试对同一段代码同时运行 Evaluator 和 VM 并比较输出结果 → 添加 TestEvaluatorVmConsistency 测试类
  - 追问：如果是 CPython 和 PyPy 没有一致性测试，能被接受吗？→ **结论：不能。** 拥有多个执行路径的语言都有大量的一致性测试。

- [test_c_codegen.py, test_native_backend.py, test_backends.py] **C 后端 / Native 后端没有端到端执行测试** → test_c_codegen.py 的 gcc 语法检查测试不做任何断言；test_native_backend.py 全部是单元测试 → 添加 C 后端和 Native 后端端到端测试
  - 追问：如果是 GCC 没有端到端执行测试，能被接受吗？→ **结论：绝对不能。** 编译器后端没有端到端执行测试，等于后端的正确性完全没有保证。

#### 中等问题（影响特定场景）

- [nova_runtime.c:749-756] `nova_adt_release` 不释放 fields 数组中的元素
- [nova_runtime.c:791-798] `nova_closure_release` 不释放 captured 数组中的元素
- [nova_runtime.c:363-368] `nova_list_set` 不释放旧值
- [nova_runtime.c:150-166] `nova_string_concat` 对 NULL 参数处理不一致
- [nova_runtime.c:1700-1703, 1770-1772] `nova_http_get` 和 `nova_http_post` 不解析响应头，status_code 始终是 200
- [grammar.js] Tree-sitter 语法缺少 range 运算符 `..` 的独立定义
- [tree-sitter-nova/test/corpus/] Tree-sitter 测试覆盖范围有限

#### 轻微问题（代码质量）

- [nova_runtime.c:336-337] `nova_list_new` 中最小容量策略应注释说明
- [nova_runtime.c:135-148] `nova_string_new_len` 中 str 为 NULL 时的处理逻辑可以更清晰
- [nova_runtime.c:39-40] 全局变量 `g_argc` 和 `g_argv` 从未被设置
- [nova_runtime.c:1518-1521] `nova_exit` 的返回值永远不会执行到（死代码）
- [grammar.js:434-439] Tree-sitter 语法中 block_expr 的分号尾表达式语法奇怪
- [grammar.js:92-95] variant_def 的语法中变体之间用 `|` 分隔，但 parser.py 支持省略 `|`
- [test_c_codegen.py:146-171] `test_generate_valid_c` 测试不做任何断言

#### 原创性分析

1. **表达式导向的语法设计**：将 let/fn/type/if/match/for/while 全部作为表达式处理
2. **多层 IR 架构**：HIR → MIR → LIR 的三层 IR 设计，配合 PassManager 优化管道
3. **多后端并行**：同时维护 Evaluator、Bytecode VM、C 后端、Native（x86_64）后端、Cranelift 后端、WasmGC 后端
4. **Tree-sitter 语法支持**：为语言提供 tree-sitter 语法定义

C 运行时的内存管理设计是完全照搬基础引用计数模式，没有创新性改进。整体来看，Nova 的架构设计有广度，但深度（尤其是运行时内存管理的正确性）不足。

---

## 第十三轮架构级建议（优先级排序）

1. **立即修复 C 运行时 ref_count 下溢保护**（崩溃级安全漏洞）
2. **立即修复 nova_map_release / nova_list_release 释放元素**（大规模内存泄漏）
3. **立即修复模块系统路径遍历漏洞**（安全漏洞）
4. **立即统一 `|>` 优先级和 `++` 优先级**（parser.py、grammar.js、文档三方同步）
5. **高优先级：重写类型检查核心**（实现真正的 HM Algorithm W）
6. **高优先级：修复 IR 降级链**（MIR match/lambda/list-comp/for 是所有后端不可用的根源）
7. **高优先级：VM 异常安全**（_run_code/_execute_function 添加 try/finally）
8. **高优先级：修复 VM while BREAK 栈清理和 MOD 除零**
9. **中优先级：修复编译器嵌套模式匹配失败栈恢复**
10. **中优先级：统一闭包语义**（Evaluator 和 VM 使用相同语义，仅捕获自由变量）
11. **中优先级：修复 while BREAK 栈清理**
12. **中优先级：添加 Evaluator-VM 一致性测试和 C/Native 后端端到端测试**
13. **中优先级：修复错误信息缺少文件名**
14. **长期：Native/Cranelift/WASM 后端根本性重写**，当前生成的代码无法工作
15. **长期：实现真正的 GC 或循环引用检测**（函数式语言中闭包和递归数据结构是高频场景）

## [2026-07-15] VM 虚拟机 (vm.py) 审查报告（第十四轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | MATCH_* 系列指令、PIPE_CALL、TRY_UNWRAP 有特色 |
| 可行性 | ⭐⭐⭐ | 核心路径可用；闭包、循环、参数校验有严重缺陷 |
| 正确性 | ⭐⭐ | 缺少部分应用、参数过多静默丢弃、全局可变不检查 |
| 安全性 | ⭐⭐ | 异常退出状态泄漏、BREAK 回退扫描极脆弱 |
| 一致性 | ⭐⭐ | 与 Evaluator 至少 6 处行为差异 |
| 完整性 | ⭐⭐⭐⭐⭐ | 64 个操作码全部有处理路径 |
| 工程质量 | ⭐⭐ | 双栈循环系统设计脆弱、冗余代码多 |
| 性能 | ⭐⭐ | 闭包浅拷贝整个帧、内存浪费严重 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [vm.py:395-397] **闭包调用缺少参数数量校验——参数过多静默丢弃** → 传入参数多于形参时，多余参数被静默丢弃，调用方错误无法及时发现 → 在 `_call_closure` 开头添加参数数量检查，过多时抛出 RuntimeError_
  - 追问：如果是 OCaml/Haskell 的编译器，参数数量不匹配能被接受吗？→ **结论：绝对不能。** 即使是解释器也必须在运行时报错。

- [vm.py:379-429] **闭包缺少部分应用（柯里化）支持** → Evaluator 支持参数不足时返回部分应用闭包，VM 直接调用 `_call_closure` 创建不完整的 locals，导致高阶函数编程范式不可用 → 在 `_call_fn` 的 NovaClosure 分支中添加部分应用逻辑
  - 追问：如果是 OCaml 的编译器，柯里化失效能被接受吗？→ **结论：绝对不能。** 柯里化是函数式语言的核心特性。

- [vm.py:575] **STORE_VAR 全局变量不检查 mutability** → 局部变量检查 mutable 标志，但全局变量直接赋值完全忽略 mutable 标志，破坏不可变性保证 → 全局变量需要追踪 mutability 信息，赋值时检查
  - 追问：如果是 Haskell 的编译器，不可变变量可以被修改能被接受吗？→ **结论：不能。** 不可变性是函数式语言的基石。

- [vm.py:795-802] **BREAK 指令的回退扫描路径存在灾难性错误** → 当 BREAK 既无操作数也不在 `_for_iters` 中时，执行前向扫描寻找 LOOP_END 或 CONST_UNIT，可能匹配到内层循环或无关位置，且完全不清理栈 → 删除该回退路径，改为直接抛出 RuntimeError_
  - 追问：如果是任何成熟编译器的 VM，用启发式扫描确定 break 目标能被接受吗？→ **结论：不能接受。** 这是定时炸弹。

- [vm.py:834-837] **CLOSURE 浅拷贝 locals 与闭包可变变量交互问题** → 闭包捕获的是 locals 字典的浅拷贝，mutable 变量修改在闭包间不共享，与 Evaluator 的 Environment 链语义不一致 → 使用可变容器包装 mutable 变量，或使用引用对象使闭包间共享可变状态
  - 追问：如果是任何函数式语言的闭包语义不一致，能被接受吗？→ **结论：不可接受。** 闭包语义是语言的核心。

- [vm.py:834-837] **CLOSURE 捕获整个帧而非自由变量，嵌套闭包丢失外层环境** → 仅浅拷贝当前帧 locals，不包含父环境链，深层嵌套闭包无法访问外层函数的变量 → 编译器分析自由变量并传递给 CLOSURE 指令；或用链式环境模型
  - 追问：如果是 OCaml 的编译器，嵌套闭包丢失外层环境能被接受吗？→ **结论：不可接受。** 闭包的词法作用域必须完整保留。

#### 中等问题（影响特定场景）

- [vm.py:963] **FOR_ITER range step=0 应报错而非静默返回空列表** → step == 0 时两个条件都为 false，立即终止迭代但不报错 → 添加 step == 0 检查，抛出 RuntimeError_
- [vm.py:946-947, 990-991] **异常退出时 `_range_index` / `_list_index` 字典泄漏** → for 循环因异常中断时，迭代索引条目永远不清理，长时间运行导致内存泄漏 → 在 `__init__` 中初始化为空字典，用 try/finally 清理
- [vm.py:495-497, 1246-1247] **TRY_UNWRAP 顶层行为不一致** → 顶层 TRY_UNWRAP 失败时静默终止，无明确语义 → 顶层失败时应抛出 RuntimeError_ 或有明确定义的行为
- [vm.py:578-621] **ADD/SUB/MUL/NEG 缺少类型检查** → 算术运算直接委托给 Python 运算符，字符串、列表等非数值类型也能"相加"，绕过类型系统 → 添加类型检查，仅允许 int/float
- [vm.py:883-893] **BUILD_MAP 键可为任意不可哈希类型，抛裸 Python TypeError** → 用 try/except 捕获 TypeError，转换为 RuntimeError_
- [vm.py:913-914] **FIELD_ACCESS 对 tuple 不做边界检查** → 越界时抛 Python IndexError，未转换为 Nova 错误 → 添加边界检查或 try/except
- [vm.py:1153-1167] **MATCH_TEST_LIST 仅支持精确长度匹配，不支持 cons/rest 模式** → 列表模式只能匹配固定长度，无法匹配 `head :: tail` 这样的分解模式 → 新增指令或修改语义支持 rest 模式

#### 轻微问题（代码质量）

- [vm.py:504-509] `_pop(0)` 冗余检查顺序，n==0 应放在前面
- [vm.py:1032-1035, 1169-1172] MATCH_START 和 MATCH_END 完全是 no-op
- [vm.py:946-947] `hasattr(self, '_range_index')` 模式不规范，应在 `__init__` 中初始化
- [vm.py:972, 1012] FOR_ITER 中 `base_sp = len(self.stack) - 3` 过于脆弱
- [vm.py:348] `_format_value` 遗漏 `NovaPartialBuiltin` 类型分类
- [vm.py:437-441 vs 849-854] RETURN 指令在两处重复处理
- [vm.py:1216-1218] DUP 指令自己做栈下溢检查，未复用 `_pop` 机制
- [vm.py:302-303] `_convert_json_to_nova` dict 键不进行类型转换

#### 原创性分析

**Nova 特色设计：**
1. **MATCH_* 系列专用指令**：将模式匹配下沉到 VM 层，简化编译器
2. **PIPE_CALL 专用管道调用指令**：减少一次栈操作
3. **TRY_UNWRAP 提前返回机制**：用 return_flag 实现 Rust 风格的 `?` 操作符
4. **FOR_ITER + LOOP_END 双指令循环**：LOOP_END 同时承担结果收集和循环回跳

**参考已有方案：**
- 基本栈机设计参考 CPython/JVM
- 双栈循环系统（_for_iters + _while_loops）设计独特但脆弱

#### Evaluator vs VM 对比
| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| 闭包部分应用 | 支持，参数不足返回部分闭包 | 不支持，静默创建不完整 locals | ❌ 严重 |
| 闭包参数过多 | 抛出 RuntimeError_ | 静默丢弃多余参数 | ❌ 严重 |
| 全局变量 mutability | Environment.assign 检查 mutable | 直接赋值，忽略 mutable 标志 | ❌ 严重 |
| 闭包环境模型 | 链式 Environment（含父环境） | 浅拷贝当前帧 locals | ❌ 严重 |
| 可变变量闭包共享 | 共享（同一 Environment） | 不共享（字典浅拷贝） | ❌ 严重 |
| range 负步长语义 | `range(start, end+1, step)` | `current >= end` | ❓ 待验证 |
| `?` 顶层传播 | ReturnSignal 抛出到顶层 | 静默终止，无明确语义 | ❌ 中等 |
| 算术运算类型检查 | 无（Python 原生行为） | 无（Python 原生行为） | ✅ 共有缺陷 |

---

## [2026-07-15] 编译器 (compiler.py) 审查报告（第十四轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | PIPE_CALL 指令、MATCH_START/END 标记、ADT 原生指令 |
| 可行性 | ⭐⭐⭐ | 基本编译流程可用；构造器字段模式、嵌套模式有严重 bug |
| 正确性 | ⭐⭐ | 构造器字段模式未测试；嵌套模式失败栈失衡；for-in-while break 错误 |
| 安全性 | ⭐⭐⭐ | 栈布局基本正确但嵌套模式失败路径不一致 |
| 一致性 | ⭐⭐ | 编译器假设的栈布局与 VM 实际执行在嵌套模式下有偏差 |
| 完整性 | ⭐⭐⭐⭐ | AST 大部分节点有编译处理；CharLiteral 用错类型 |
| 工程质量 | ⭐⭐ | 死代码残留、命名不一致、硬编码多 |
| 性能 | ⭐⭐⭐ | 闭包不做自由变量分析影响效率 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [compiler.py:836-839] **构造器模式的字段子模式从未被测试** → `PatternConstructor` 分支仅发出 `MATCH_CONSTRUCTOR` 测试构造器名称和字段数量，没有递归测试字段子模式，导致 `Some(0)` 错误匹配 `Some(42)` → 添加递归测试字段子模式的代码
  - 追问：如果是 Haskell GHC 编译器跳过构造器字段模式测试，能被接受吗？→ **结论：绝对不能。** 模式匹配是函数式语言的核心特性。

- [compiler.py:762-777, 841-857] **嵌套模式匹配失败路径栈失衡** → PatternTuple/PatternList 递归测试子模式时，外层已将 subject 分解为多个元素压栈，失败清理只执行一次 POP，残留分解元素导致后续所有计算栈失衡 → 失败时正确回滚栈到 DUP 之前的状态，跟踪当前栈深度偏移量
  - 追问：如果是 OCaml 的字节码编译器，嵌套模式匹配失败时栈错乱能被接受吗？→ **结论：绝对不能。** 每个执行路径的栈深度必须一致是栈式 VM 的基本要求。

- [compiler.py:490-506] **for 循环嵌套在 while 循环中时，break/continue 指向错误的循环** → BreakExpr/ContinueExpr 仅检查 `_while_end_stack` 是否非空来判断是否在 while 中，for-in-while 时 break 被编译为 while break 而非 for break → 引入统一的循环栈数据结构，break/continue 始终作用于栈顶最内层循环
  - 追问：如果是任何成熟编译器，break 不跳出最内层循环能被接受吗？→ **结论：不能。** 这是结构化编程的基本约定。

#### 中等问题（影响特定场景）

- [compiler.py:402, 682] **闭包无自由变量分析，捕获全部局部变量** → CLOSURE 只携带 func_name 和 param_count，VM 端复制全部 locals，内存浪费且语义与引用捕获预期不符 → 实现自由变量分析，将自由变量列表作为 CLOSURE 操作数
- [compiler.py:362-368] **导入名称冲突检测不完整** → 仅检查函数字典和内置函数名，不检查已有的 let 绑定、mut 绑定、零字段构造器等 → 维护统一的全局符号表，导入时统一检查冲突
- [compiler.py:420-421] **CharLiteral 编译为 CONST_STRING 导致类型混淆** → 字符和字符串在运行时使用相同表示（单字符字符串），MATCH_TEST_CHAR 仅检查长度，运行时无法区分 → 使用 CONST_CHAR 操作码或 NovaChar 包装类型
- [compiler.py:597-602] **管道编译中内置函数的 if/else 分支完全相同** → 代码误导性强，维护者可能以为有特殊处理 → 删除冗余 if 判断

#### 轻微问题（代码质量）

- [compiler.py:902-967] 两套死代码模式编译方法（`_compile_pattern_test` + `_compile_pattern_bindings`）
- [compiler.py:81] CLOSURE 操作码注释与实际不符（声称 3 个操作数实际 2 个）
- [compiler.py:431-432] None 标识符硬编码而非查表，与模式匹配不一致
- [compiler.py:277-288] 内联导入中构造器注册与全局变量存储的顺序依赖，设计脆弱
- [compiler.py:1047-1048] while 循环 BREAK 栈清理与 POP 双重机制增加维护复杂度
- [compiler.py:1048] while 循环体末尾显式 POP 与 VM 端 base_sp 截断的双重机制

#### 原创性分析

**栈式字节码设计的独特之处：**
1. **MATCH_* 系列指令**：将模式匹配编译为专用测试指令而非通用比较+跳转序列，简化编译器但增加 VM 复杂度
2. **FOR_ITER + LOOP_END 配对**：LOOP_END 同时承担结果收集和循环回跳
3. **PIPE_CALL 指令**：专用管道调用指令减少栈操作
4. **TRY_UNWRAP 提前返回**：利用 VM 的 return_flag 机制实现 `?` 操作符

---

## [2026-07-15] 求值器 (evaluator.py) 审查报告（第十四轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 两遍扫描支持相互递归；Environment 链闭包引用语义 |
| 可行性 | ⭐⭐⭐ | 核心路径可用；部分应用、Block 异常安全有严重缺陷 |
| 正确性 | ⭐⭐ | NovaClosure 部分应用完全失效；Block 异常时环境泄漏；`&&`/`||` 无类型检查 |
| 安全性 | ⭐⭐ | 多处裸 Python 异常；环境泄漏可能导致难以调试的错误 |
| 一致性 | ⭐⭐⭐ | 与 VM 在 abs 返回类型、`&&`/`||` 严格度、部分应用行为上存在差异 |
| 完整性 | ⭐⭐⭐⭐ | AST 覆盖较完整；缺少高级模式（cons 模式、as-pattern） |
| 工程质量 | ⭐⭐ | 环境管理不一致；死代码残留；重复代码多 |
| 性能 | ⭐⭐⭐⭐ | 闭包引用语义效率高于 VM；但 for 循环每次迭代创建 child_env 有开销 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [evaluator.py:416-431] **NovaClosure 部分应用完全失效——捕获参数从未进入作用域** → `partially_applied` 函数被定义但从未被使用，返回的 NovaClosure 直接使用原始 fn.body 和 fn.env，已捕获的参数完全不在作用域中 → 将已捕获参数预先定义到闭包环境中，返回包含这些绑定的 child_env
  - 追问：如果是 OCaml 的解释器，部分应用返回的闭包中捕获变量不在作用域里，能被接受吗？→ **结论：绝对不能。** 柯里化是 ML 家族语言的基础语义。

- [evaluator.py:757-767] **Block 求值无 try/finally——异常发生时环境泄漏** → block 内语句抛异常时，`self.env = old_env` 永远不执行，求值器环境指针永久指向废弃的 child_env，后续操作行为不可预测 → 用 try/finally 包裹 block 求值，确保环境恢复
  - 追问：如果是 Haskell 的 `do` 块在异常时不恢复词法作用域，能被接受吗？→ **结论：绝对不能。** 环境管理是解释器的核心基础设施。

- [evaluator.py:870-880] **`&&` / `||` 短路操作不检查左操作数类型** → 左操作数直接用 Python truthiness 判断，与 if/while 的严格类型检查不一致，违反强类型语义 → 在短路判断前添加类型检查，验证操作数为 Bool 类型
  - 追问：如果是 OCaml 的 `&&` 接受整数并使用 truthiness，能被接受吗？→ **结论：绝对不能。** 强类型语言中逻辑运算符的操作数必须是 bool 类型。

- [evaluator.py:335-336] **`_builtin_abs` 对整数输入也返回浮点数** → `abs` 总是先调用 `_to_float()` 将输入转为浮点数，Int 输入也返回 Float，改变了值的类型 → 保持输入类型不变，Int 输入返回 Int
  - 追问：如果是 Haskell 的 `abs` 将 Int 变成 Float，能被接受吗？→ **结论：绝对不能。** `abs` 应该保持输入类型不变。

- [evaluator.py:985-1011] **列表推导式不处理 BreakSignal/ContinueSignal——信号泄漏 + filter_cond 无类型检查** → 推导式循环体只有 finally 恢复 env，没有捕获 BreakSignal/ContinueSignal；filter_cond 求值结果用 Python truthiness 判断，不验证 Bool 类型 → 显式捕获循环控制信号并转换为 RuntimeError_；验证 filter_cond 结果为 Bool
  - 追问：如果 Python 的列表推导式中 break 会静默跳过，能被接受吗？→ **结论：不能。** 语法和语义的边界应该清晰。

#### 中等问题（影响特定场景）

- [evaluator.py:940-945] for 循环范围的 start/end/step 不做类型验证，非 int 时抛裸 Python TypeError
- [evaluator.py:823-846] FieldAccess 错误消息不包含实际类型名称，调试困难
- [evaluator.py:849-862] IndexExpr 对所有支持 `[]` 的 Python 类型都生效，String 索引语义不明确
- [evaluator.py:795-796] MapExpr 键不可哈希时抛出裸 Python TypeError
- [evaluator.py:885-924] 二元运算类型不匹配抛出裸 Python TypeError，未包装为 RuntimeError_
- [evaluator.py:217-227] `_builtin_head` / `_builtin_tail` 对非列表参数崩溃，抛原生错误

#### 轻微问题（代码质量）

- [evaluator.py:784-787] Assignment 不必要的 RuntimeError_ 重新包装，丢失元数据
- [evaluator.py:1020-1041] `_eval_match` 中守卫求值创建了两次 child_env，可优化
- [evaluator.py:570-625] `eval_decl` 方法是死代码，与两遍扫描逻辑重复
- [evaluator.py:304-305] `_convert_nova_to_json` 中冗余的 `val is None` 检查

#### 原创性分析

**Nova 特色：**
1. 两遍扫描 + 词法闭包：第一遍注册所有函数签名，第二遍求值体，使相互递归自然成立
2. `?` 操作符统一 Option/Result 错误传播：通过 ReturnSignal 异常机制实现提前返回
3. ADT 构造器一等值：无参数构造器是值，有参数构造器是函数

#### 与 VM 的差异对比表
| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| 部分应用（NovaClosure） | 完全失效（捕获变量不在作用域） | 未实现 | ❌ 两边都有 bug |
| Block 异常安全 | 无 try/finally，环境泄漏 | 栈式结构天然安全 | ❌ |
| `&&`/`||` 类型检查 | 左操作数不检查 | AND/OR 指令也不检查 | ✅ 一致但都有问题 |
| `abs` 返回类型 | Int 输入也返回 Float | 同样返回 Float | ✅ 一致但都有问题 |
| 闭包环境模型 | 链式 Environment（引用语义） | 浅拷贝当前帧（值语义） | ❌ |
| 全局可变性检查 | Environment.assign 检查 | 不检查 | ❌ |
| 参数过多处理 | 抛出 RuntimeError_ | 静默丢弃 | ❌ |

---

## [2026-07-15] 类型检查器 (type_checker.py) 审查报告（第十四轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 类型推断算法正确性 | ⭐⭐ | 非真正 HM 推断，无合一，TypeVar 过于宽松，let 多态完全缺失 |
| 泛型支持完备性 | ⭐⭐⭐ | ADTType.__eq__ 正确比较类型参数，但实例化无 occurs check |
| 模式匹配类型检查 | ⭐⭐⭐ | 基本模式检查存在，但无穷尽性检查、无冗余分支检测、无 guard 类型检查 |
| 错误恢复能力 | ⭐⭐ | ErrorCollector 存在但大量路径直接 raise，错误恢复不彻底 |
| 类型标注支持 | ⭐⭐⭐ | 基本类型语法支持，但 TypeVar 在类型标注中无语法支持 |
| 递归类型处理 | ⭐ | 无 occurs check，递归 ADT 类型检查可能导致无限循环 |
| let 多态 | ⭐ | 完全缺失，let 绑定的类型不被泛化 |
| 代码质量与可维护性 | ⭐⭐⭐ | 结构清晰，但缺少算法文档，类型变量命名混乱 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [type_checker.py:1318-1319] **`_types_compatible` 中 TypeVar 过于宽松——类型系统基本失效** → 任何一方是 TypeVar 就返回 True，类型变量可以与任何类型兼容，这不是 HM 推断而是"带类型提示的 duck typing" → 实现真正的合一(unification)算法，用 union-find 结构管理类型变量等价类
  - 追问：如果是 OCaml 的类型检查器，类型变量与任何类型都兼容能被接受吗？→ **结论：绝对不能。** 这等于没有类型系统。

- [type_checker.py:1188-1208] **`_collect_type_bindings` 缺少一致性检查——同一变量可绑定到不同类型** → 当同一个 TypeVar 在不同位置出现时，如果两次实际类型不同，第一次会绑定，第二次被静默忽略 → 当 TypeVar 已绑定时，检查新绑定与旧绑定是否一致，不一致时报错
  - 追问：如果是 Haskell 的类型检查器，不检查同一类型变量的多次绑定一致性，能被接受吗？→ **结论：绝对不能。** 这是参数化多态的基础。

- [type_checker.py:1190-1192] **`_collect_type_bindings` 中 actual 为 TypeVar 时不做任何处理** → 当 expected 是具体类型而 actual 是 TypeVar 时，完全跳过，类型变量绑定完全丢失 → 实现双向类型检查或合一算法，使类型信息可以双向流动
  - 追问：如果是 SML 的类型检查器，只能从参数向函数传递类型信息而不能反向，能被接受吗？→ **结论：不能。** 合一算法的核心就是双向的类型等式求解。

- [type_checker.py（全局缺失）] **无 occurs check——递归类型可无限展开** → 整个类型检查器没有 occurs check，合一过程中可能创建无限递归类型 → 实现合一算法时必须加入 occurs check；对于递归 ADT，使用 μ 类型或基于名称的递归类型表示
  - 追问：如果是 OCaml 的类型检查器，没有 occurs check 导致 `let rec f x = f x` 产生无限类型，能被接受吗？→ **结论：绝对不能。** Occurs check 是 HM 类型系统的安全基石。

- [type_checker.py:279-293] **内置 ADT 构造函数使用相同 TypeVar 实例——所有调用共享类型变量** → `Some` 的类型签名使用同一个 `t_opt` TypeVar 对象，每次调用不生成新鲜实例，高阶函数场景类型变量会混淆 → 实现类型方案(Forall)概念，每次引用多态值时生成新鲜的类型变量实例
  - 追问：如果是 Haskell 的类型检查器，多态函数每次调用不生成新鲜类型变量，能被接受吗？→ **结论：绝对不能。** 这是参数化多态的基本实现机制。

- [type_checker.py:1000-1008] **Match guard 完全没有类型检查** → `check_match_arm` 完全不检查 arm.guard 的类型，guard 可以是非 Bool 类型 → 在 `_check_pattern` 之后、`check_expr(arm.body)` 之前，检查 arm.guard 的类型为 Bool
  - 追问：如果是 Rust 的 match guard 不做类型检查，能被接受吗？→ **结论：绝对不能。** Guard 是 match 表达式的关键组成部分。

#### 中等问题（影响特定场景）

- [type_checker.py:1294-1312] `_expand_alias` 不处理 TypeIdentifier，实际是死代码
- [type_checker.py:677-689] 模式匹配无穷尽性检查，漏掉 None 分支不警告
- [type_checker.py:677-689] 模式匹配无冗余分支检测，不可达分支不警告
- [type_checker.py:740-750] FnCall 中 TypeVar 类型的 callee 走 duck typing 路径，静默跳过类型检查
- [type_checker.py:939-958] ForExpr 循环变量类型与迭代器类型完全脱节，for 循环实际上无类型检查
- [type_checker.py:755-770] PipeExpr 类型检查逻辑混乱，同时检查第一个和最后一个参数，语义模糊
- [type_checker.py:1248-1252] 类型别名循环检测仅检测直接循环，不检测间接循环；别名不支持前向引用
- [type_checker.py:791-794] 局部 MutBinding 不检查类型标注，与顶层不一致

#### 轻微问题（代码质量）

- TypeVar 命名混乱，缺乏统一命名规范
- `_types_compatible` 与 `__eq__` 功能重叠且语义不一致
- 导入模块时名称冲突处理不一致，取决于声明顺序
- `ListExpr` 空列表的类型变量名 `"unknown_list_elem"` 有误导性
- 二元操作的错误报告不一致，`||` 报错时硬编码为 `'&&'`
- ADT 构造函数的类型参数在第一遍就固定了，失去多态性

#### 原创性分析

**原创性：低** — 代码声称实现了 Hindley-Milner 类型推断，但实际上只是带类型变量占位符的类型检查器。缺少 HM 系统的关键组件：合一算法、类型方案、let 多态、occurs check、穷尽性检查。

**值得肯定的设计：**
- ADTType 的 `__eq__` 和 `__hash__` 正确实现了类型参数比较
- 两遍扫描支持相互递归
- ErrorType 单例模式用于错误恢复

---

## [2026-07-15] 词法/语法分析器 (lexer.py + parser.py) 审查报告（第十四轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| Token 覆盖度 | ⭐⭐⭐ | 基础语法元素覆盖尚可，但缺少块注释、科学计数法、十六进制字面量 |
| 词法错误恢复 | ⭐⭐ | 有基本跳过机制，但使用递归而非迭代，存在栈溢出风险 |
| 运算符优先级 | ⭐⭐ | 管道 `|>` 优先级反常地高于算术运算符；`++` 优先级高于 `+` 不寻常 |
| 结合性正确性 | ⭐⭐⭐ | 比较运算符左结合（应非结合）；一元运算符右结合正确 |
| 语法歧义处理 | ⭐⭐⭐⭐ | `then` 关键字避免悬挂 else；map/block 歧义用无限前瞻解决 |
| 左递归处理 | ⭐⭐⭐⭐ | 递归下降+优先级爬升正确处理左结合运算符 |
| 错误位置精度 | ⭐⭐⭐⭐ | 行号列号基本准确，Span 机制完善 |
| 错误恢复能力 | ⭐⭐ | 解析器遇错即抛异常，无任何 panic mode 恢复 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [parser.py:672-678] **比较运算符左结合导致语义错误** → `a < b < c` 被解析为 `(a < b) < c`，即将布尔值与 c 比较，几乎肯定不是用户预期 → 改为非结合（遇到第二个比较运算符时抛错），或实现 Python 风格的链式比较
  - 追问：如果是 GCC/Clang，比较运算符左结合能被接受吗？→ **结论：绝对不能。** 所有主流语言的比较运算符都是非结合的。

- [parser.py:660-666] **相等运算符左结合导致同类问题** → `a == b == c` 被解析为 `(a == b) == c`，比较布尔值与 c → 同比较运算符，改为非结合或链式比较
  - 追问：在任何成熟语言的前端中，这都是不可接受的 bug。→ **结论：不能接受。**

- [parser.py:432-439] **管道 `|>` 优先级反常地高于算术运算符** → `a + b |> f` 被解析为 `a + (b |> f)`，与 Elixir/F#/Elm 等所有主流管道语言的直觉相反 → 将管道操作符移到比较运算符之下（更低优先级）
  - 追问：如果是 Elixir/F# 的管道操作符优先级高于算术，能被接受吗？→ **结论：不能接受。** 当前优先级设计与所有主流管道语言相悖。

- [parser.py:733-769] **`?` 错误传播操作符不在后缀循环内，链式调用失效** → `f(x)?` 正确，但 `expr?.field`、`expr?[idx]`、`f()?.g()` 等链式调用完全失效 → 将 `?` 的解析移入 `_parse_postfix_expr` 的 while 循环内
  - 追问：如果是 Rust，`expr?.method()` 不是合法语法能被接受吗？→ **结论：生产级不可接受。** 严重限制了 `?` 的使用场景。

- [parser.py:474, 974] **for 循环 iterable 字段类型混用——字符串元组混入 AST** → ForExpr.iterable 可能是 AST 节点或 `("range", start, end, step)` 元组，下游消费者必须用 isinstance + 字符串比较判断 → 创建 RangeExpr AST 节点，或使用单独的字段表示
  - 追问：GCC/Clang/任何成熟编译器的 AST 中会出现裸字符串元组吗？→ **结论：绝对不会。** 这是架构级别的设计缺陷。

#### 中等问题（影响特定场景）

- [lexer.py:258, 267, 281, 308, 458] 词法错误恢复使用递归，大量非法字符可能导致栈溢出
- [lexer.py:250-251, 297-298] 未知转义序列静默通过，无任何警告
- [lexer.py:88] PIPE_VARIANT token 类型永不产生——死代码
- [lexer.py:91, 368-372] UNIT token 类型永不产生，primary 中的 UNIT 分支是死代码
- [parser.py:522] match 分支延续检测遗漏负数模式和字符模式
- [parser.py:844-884] `_is_map_literal` 无限制前瞻，O(n²) 复杂度
- [parser.py:386-391] 块内赋值仅支持标识符，不支持字段和索引赋值
- [lexer.py:155-160] `_make_error` 的 end_col 计算逻辑错误

#### 轻微问题（代码质量）

- 缺少块注释 `/* */` 支持
- 数字字面量不支持十六进制、八进制、二进制
- 数字字面量不支持科学计数法
- 数字字面量不支持下划线分隔符
- 不支持前导小数点的浮点数 `.5`
- 缺少 `\0`（空字符）转义
- 不支持 Unicode 转义序列 `\u{...}`
- 标识符字符集使用 `isalnum()` 过于宽泛
- 空白字符处理不完整（缺少换页符、垂直制表符等）
- 无 BOM 处理
- 解析器完全没有错误恢复机制
- `<-` 不是独立 token，由 LT + MINUS 拼凑
- `step` 字段与 `iterable` 元组中的 step 冗余

#### 原创性分析

**独特设计：**
1. 管道操作符高优先级设计——独此一家，可能是实验性设计但更可能是实现错误
2. `then` 关键字消除悬挂 else——函数式语言常见做法，设计合理
3. Map 字面量与代码块共用 `{}` 语法，用 `=>` 区分——类似 Ruby，但通过全扫描前瞻实现

---

## [2026-07-15] 错误处理 + 模块系统 + 环境 审查报告（第十四轮）

### 总体评分
| 维度 | errors.py | modules.py | environment.py | 说明 |
|------|-----------|------------|----------------|------|
| 正确性 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | errors 缺少错误码/文件路径；modules 有路径遍历和缓存一致性问题 |
| 健壮性 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | 错误恢复不完整；模块加载异常时状态清理有隐患 |
| 可诊断性 | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | 无错误码、无文件名、无错误文档链接 |
| 安全性 | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐ | 模块路径无沙箱限制，路径遍历攻击面大 |
| 性能 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | loading_stack O(n) 查找；env 查找是 O(depth) 链遍历 |
| 可维护性 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | errors 有命名不一致；modules 重复代码多 |
| 完整性 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | errors 缺错误码体系；modules 缺命名空间/重导出 |
| 互操作性 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | 错误无机器可读格式；模块无版本化接口 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [errors.py:82-327] **错误系统完全没有错误码体系** → 所有错误只有消息字符串，没有机器可读的错误标识，IDE/工具链无法做错误分类、搜索、文档关联 → 实现 ErrorCode 枚举体系，每个 NovaError 携带唯一错误码
  - 追问：如果 Rust 编译器没有错误码，`rustc --explain E0308`、`#[deny(warnings)]` 这些能实现吗？→ **结论：完全不能。** 错误码是生产级编译器的基础设施。

- [errors.py:157-263] **错误输出不含文件名，多文件项目无法定位** → `_format_with_context` 只输出行号列号，从未输出文件名，模块系统启用后错误来源完全模糊 → NovaError 类增加 file_path 字段，错误输出格式包含完整路径
  - 追问：OCaml 的模块系统中，如果编译器报 "Unbound value x" 却不说是哪个 `.ml` 文件里的，能接受吗？→ **结论：完全不能。这是编译器的基本要求。**

- [modules.py:107-157] **路径遍历安全漏洞——无模块路径沙箱限制** → 恶意 `.nova` 文件可以通过 `import "../../../etc/passwd"` 或绝对路径读取系统任意文件 → 实现 `_is_path_safe()` 校验，确保解析后的路径在允许的目录内
  - 追问：Node.js 的 `require()`、Python 的 `import` 允许从模块系统任意读取系统文件吗？→ **结论：不能。** 没有路径沙箱，语言无法安全运行第三方代码。

- [modules.py:228-274] **循环导入检测在异常时栈不回滚的隐患 + evaluator 重复实现导入逻辑** → evaluator 中 `_handle_import_decl` 自己做了一套导入逻辑，与 modules.py 的 `import_module` 分叉，且 evaluator 路径导入的模块没有类型信息 → evaluator 应直接调用 `self._module_manager.import_module()`，删除重复实现
  - 追问：Rust 的 rustc 里，AST lowering 和 codegen 各自实现一套模块解析吗？→ **结论：不会。模块解析是单一职责的阶段。**

- [modules.py:293-299] **`_collect_exported_types` 三重死代码** → 函数名和参数暗示会从 type_checker 收集类型信息，但完全没用到 type_checker 参数，返回值也从未被使用 → 删除该函数和无用赋值

#### 中等问题（影响特定场景）

- [errors.py:365-370] ErrorCollector.add 将 NOTE/HELP 错误误归入 errors 列表，has_errors() 会误报
- [errors.py:249] RelatedNote 使用主错误的 max_line_num_width，行号范围不同时对齐错位
- [errors.py: lexer.py:153] Lexer 存储错误为字符串而非 NovaError 对象，丢失结构化信息
- [modules.py:124-130] 相对路径解析依赖 search_paths[0]，设计脆弱，隐式假设第一个是当前目录
- [environment.py:30-32] define 静默覆盖同作用域已有绑定，无重定义检测，mutable 可被意外改变
- [environment.py:34-48] 环境链查找递归实现，极深嵌套可能导致 Python 递归栈溢出

#### 轻微问题（代码质量）

- [errors.py:86 vs 92] `source` 参数名与 `source_code` 属性名不一致
- [errors.py:281] `_compute_underline` 多行尾行下划线计算边界情况
- [errors.py:413-420] `format_all()` 不区分错误和警告的输出顺序语义
- [modules.py:56] `get_exported_bindings` 静默吞掉 NameError
- [modules.py:358-364] 全局模块管理器搜索路径包含相对路径，受 CWD 影响
- [environment.py:67-73] `all_bindings()` 不返回可变性信息
- [environment.py] 缺少 `is_defined_here` 方法

#### 原创性分析

**errors.py：** 借鉴 Rust 输出格式（源码上下文、ANSI 颜色、严重程度标签），但实现深度不足（无错误码、无文件名、无 JSON 输出）。ErrorCollector 设计思路有原创性但实现质量不足。

**modules.py：** 标准设计（路径解析、模块缓存、循环导入检测），但完成度低（无命名空间、无重导出、无别名导入、无选择性导入）。两套导入逻辑分叉是架构级债务。

**environment.py：** 教科书级词法作用域链实现（SICP 标准模式），73 行代码量说明极简正确但远非生产级。

---

## [2026-07-15] 所有后端审查报告（第十四轮）

### 总体评分
| 维度 | native_backend | cranelift_backend | wasm_backend | x86_64 | compiler_pipeline | c_codegen |
|------|---------------|-------------------|--------------|--------|-------------------|-----------|
| 指令覆盖率 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 代码正确性 | ⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| 端到端可用性 | ⭐ | ⭐ | ⭐ | N/A | ⭐⭐ | ⭐⭐⭐ |
| 寄存器分配/栈管理 | ⭐ | N/A | N/A | N/A | N/A | N/A |
| 调用约定一致性 | ⭐⭐ | ⭐⭐ | ⭐⭐ | N/A | N/A | ⭐⭐⭐ |
| 异常/边界安全 | ⭐ | ⭐ | ⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐ |
| 测试充分性 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| 架构设计合理性 | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [native_backend.py:430-443] **除法/取模运算破坏 ABI 调用约定** → `idiv` 指令隐式使用 RDX:RAX 作为被除数，当前代码在除法前没有保存/恢复 RDX，如果 RDX 中有活跃变量会被破坏 → 在调用 idiv 前，如果 RDX 中有活跃值先溢出到栈；或寄存器分配阶段预留 RAX/RDX
  - 追问：如果是 GCC/LLVM 的后端，隐式寄存器使用不被寄存器分配器建模能被接受吗？→ **结论：不能。** 这是后端最基本的正确性问题。

- [native_backend.py:388-389, 45-82] **寄存器分配器完全未使用，一次性分配 14 个后静默失败** → LinearScanAllocator 类定义了但从未使用，`_alloc_vreg` 只是顺序从 free_gprs 取寄存器，用完不回收，超过 14 个后变量分配为 None → 实现真正的活跃区间分析，接入 LinearScanAllocator，实现 spill/reload 机制
  - 追问：GCC/LLVM 中没有正确的寄存器分配能被接受吗？→ **结论：完全不能。** 没有正确的寄存器分配就不是真正的后端。

- [native_backend.py:734-798] **数据结构构建在栈上分配，返回后失效** → `_compile_build_list`、`_compile_build_tuple`、`_compile_build_adt` 都在当前函数栈帧上分配空间构建数据结构，函数返回后栈帧回收，指针变成悬垂指针 → 调用 `nova_alloc` 在堆上分配，或使用 sret 调用约定
  - 追问：GCC/LLVM 中返回值指向栈内存能被接受吗？→ **结论：不能。** 这是最基本的内存生命周期问题。

- [cranelift_backend.py:162-168] **条件分支硬编码错误的标签名** → `LIRBranch` 处理使用硬编码的 `block_false` 和 `block_true`，而不是 instr.false_label 和 instr.true_label，所有多分支函数的控制流完全错误 → 使用 instr.true_label 和 instr.false_label
  - 追问：GCC/LLVM 中条件分支跳转到固定标签能被接受吗？→ **结论：绝对不能。** 这是最基本的控制流正确性问题。

- [wasm_backend.py:230-232] **标签实现为 block，破坏控制流语义** → LIRLabel 被编译为 Wasm 的 block 结构，但 Wasm 的 block 不是标签，br 指令只能跳出不能跳入，循环等向后跳转完全失效 → 实现 relooper 算法，或至少正确区分 loop 和 block
  - 追问：GCC/LLVM 中 Wasm 后端的 CFG-to-structured-control-flow 是核心算法吗？→ **结论：是的。** 没有正确的控制流结构化，Wasm 后端就是不可用的。

- [c_codegen.py:590-600] **? 操作符的 return 语句类型不匹配 + 字段名不一致** → Option/Result 为 None/Err 时直接 return {temp}，如果函数返回类型不是 NovaADT* 就会类型不匹配；且使用 `variant_tag` 字段但定义的是 `tag` → 统一字段名，添加正确的函数返回类型检查
  - 追问：GCC/LLVM 中类型不匹配能通过编译吗？→ **结论：不能。** 类型不匹配是编译期就能发现的错误。

- [x86_64.py:451-473] **je_rel32 重复定义** → 同一方法在文件中定义了两次，暗示缺乏代码审查和测试覆盖 → 删除重复定义

#### 中等问题（影响特定场景）

- [native_backend.py:242-273] 函数调用参数传递忽略溢出情况，第 7 个参数（索引 6）既不放入寄存器也不压栈
- [native_backend.py:834] _start 入口读取 argc 方式错误，偏移应为 0 而非 8
- [native_backend.py:860-879] RIP-relative 重定位计算错误，基于文件偏移而非虚拟地址
- [native_backend.py:536-538] Panic 实现不完整，直接 exit(1) 无错误信息无栈展开
- [native_backend.py:468-481] 逻辑运算使用位运算代替，缺少短路语义
- [wasm_backend.py:161] 字符串编码中的转义错误，`b"\\x00"` 是字面量而非 NUL 字节
- [wasm_backend.py:260-263] 条件分支只使用 br_if false，缺少 true 路径跳转
- [cranelift_backend.py:204] iconst 指令名错误，应为类型化指令（如 i64.const）
- [c_codegen.py:1152-1159] 字段访问歧义处理不当，指针类型应该用 `->` 而非 `.`
- [compiler_pipeline.py:80-84] C 后端绕过 IR 管道，直接从 AST 生成代码，无法受益于 IR 优化

#### 轻微问题（代码质量）

- [x86_64.py:82-93] mov_reg_imm64 优化路径对负数小立即数可以更紧凑
- [x86_64.py:507-541] setcc 和 movzx 指令缺少 REX 前缀处理（R8-R15 扩展寄存器）
- [cranelift_backend.py:211] 字符串常量生成临时变量名冲突风险
- [wasm_backend.py:369-374] _get_string_offset 与 _scan_strings 重复逻辑，动态添加的字符串无数据存储
- [c_codegen.py:1042] let 绑定的 result_expr 为空字符串，表达式上下文中可能产生语法错误
- [c_codegen.py:690] 字符串模式比较每次都创建新字符串但不释放，造成内存泄漏
- [native_backend.py:722-728] 字段访问破坏 base_reg，原地修改基址寄存器

#### 原创性分析

**x86_64 编码器：高原创性** — 从零实现完整的 x86_64 指令编码器（ModR/M、REX 前缀、SIB 寻址等），以及 ELF 可执行文件生成器。不依赖任何外部汇编器，直接输出机器码字节。

**三层 IR 设计：中等原创性** — 参考 MLIR Dialect 思想，但实现深度较浅。

**整体评价：** 后端的广度（多个后端）大于深度（每个后端的完整性）。从学术/学习角度有价值，但离生产可用还有很大距离。目前只有 C 后端有潜力实际运行简单程序，其余三个后端都是 demo 级别。

---

## [2026-07-15] IR 系统 + Pass 管理器 (ir/) 审查报告（第十四轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 三层 IR 架构设计 | ⭐⭐⭐ | 分层思路正确，但层间抽象泄漏严重，类型系统不完整 |
| SSA 形式正确性 | ⭐ | 共享 env 字典导致 SSA 构造根本性错误，Phi 节点使用不正确 |
| 类型系统一致性 | ⭐⭐⭐⭐ | 类型在各层传递但缺乏精度（无位宽/大小信息） |
| Pass 优化实现完整性 | ⭐⭐ | Inlining 空壳，MIR LICM 基本不可用，多处优化算法有缺陷 |
| 异常处理鲁棒性 | ⭐⭐ | PassManager 静默吞掉所有异常，IR 可能处于不一致状态 |
| 边界情况处理 | ⭐⭐ | for 循环变量未绑定、Switch 信息丢失、Phi 只取首个源等多处边界崩坏 |
| 代码可维护性 | ⭐⭐⭐ | dataclass + __class__ 动态修改、层间直接引用 HIR 类型 |
| 可验证性/可调试性 | ⭐ | 完全没有 IR Verifier，无法保证 IR 合法性 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [mir_lowering.py:51, 90, 103, 160-162, 278] **SSA 构造根本性错误：共享 env 字典导致控制流污染** → 使用单个 self.env 字典跨所有基本块共享，真分支对变量的赋值会污染假分支，合并后不需要 Phi 节点，整个 SSA 形式是假的 → 每个基本块维护独立的环境映射，在控制流合并点对所有被修改的变量插入 Phi 节点
  - 追问：LLVM/MLIR 能接受 SSA 构造根本性错误吗？→ **结论：绝对不能。** SSA 是 MIR 层的核心承诺，不成立则整个优化基础设施失效。

- [mir_lowering.py:396-417] **for 循环变量从未绑定到环境中 + 迭代逻辑完全缺失** → `hir_expr.variable` 从未被加入 self.env，循环体中对循环变量的引用返回 None，操作数为空字符串；迭代逻辑也完全缺失 → 在 header 块中添加获取下一个元素的指令，将元素值绑定到循环变量的 SSA 名
  - 追问：LLVM/MLIR 中 for 循环降低根本没有实现能被接受吗？→ **结论：不能。** 这是功能完全缺失。

- [pass_manager.py:105-108, 115-118] **HIR 常量折叠使用 `__class__` 动态修改 dataclass** → 在 dataclass 实例上修改 __class__ 是极其危险的操作，字段布局不匹配、哈希表行为异常、类型检查失效 → 不要就地修改对象，改为创建新节点并返回，调用者用新节点替换
  - 追问：LLVM/MLIR 中会用 __class__ 突变来修改 IR 节点吗？→ **结论：绝对不能。** 所有 IR 节点都是堆分配并通过指针引用，从不使用类型突变。

- [lir_lowering.py:204-211] **LIR Phi 节点降低只取第一个源，完全错误** → Phi 节点的核心语义是"根据来自哪个前驱块选择对应的值"，当前实现直接取 sources[0]，忽略所有其他前驱的值 → 采用经典的 Phi 消除算法，在每个前驱块末尾插入 copy 指令
  - 追问：LLVM/MLIR 中 Phi 节点只取第一个源能被接受吗？→ **结论：不能。** 这是编译器正确性的核心问题。

- [pass_manager.py:720-725, 736-741, 752-757] **PassManager 静默吞掉所有异常** → 三个 pass 运行器都捕获所有异常，打印错误后继续执行，IR 可能处于不一致状态，编译继续进行最终可能生成错误代码 → 对致命错误立即终止编译管道，保存完整 traceback，添加 IR verifier 检查
  - 追问：LLVM 中 pass 失败后静默继续能被接受吗？→ **结论：不能。** 静默失败比崩溃更危险。

- [lir_lowering.py:231-241] **Switch 和 MatchJump 降低为普通 Jump，所有分支信息丢失** → MIRSwitch 的所有 case 和 MIRMatchJump 的所有 variant 测试在 LIR 层完全丢失，只剩跳转到 default 目标 → LIR 层需要支持条件跳转表或多分支比较序列

#### 中等问题（影响特定场景）

- [mir_lowering.py:368-372] Match 表达式 Phi 源收集方式错误，取最后一条指令的 result_name 而非 arm 结果
- [lir_lowering.py:141-147] LIR 函数调用参数完全丢失，LIRCall 只有 func_name 和 arg_count，没有实际参数位置
- [lir_lowering.py:107-119] MIRLoad/MIRStore 一律按全局变量降低，局部变量被当作全局存储
- [pass_manager.py:616-693] MIR LICM 实现完全不可用，只看 header 块、只找 header 中的指令、外提位置错误
- [pass_manager.py:688] MIR LICM 可能破坏 SSA 支配关系，外提指令的操作数可能未定义
- [hir_lowering.py:292-300] HIRBlockExpr 中包含 HIRLetDecl 但 MIR 降低不处理，块内局部变量被静默丢弃
- [pass_manager.py:91-121] HIR 常量折叠不处理一元操作，-5、!true 等永远不会被折叠
- [pass_manager.py:346] DCE 不将 LIRBinOp 视为无副作用指令，优化遗漏
- [pass_manager.py:336-342] DCE 不可达代码检测只覆盖 LIRJump，LIRReturn/LIRPanic 之后的死代码不删除

#### 轻微问题（代码质量）

- [ir_nodes.py:524] MIRModule.type_defs 直接引用 HIR 类型，破坏层间抽象
- 完全没有 IR Verifier，无法验证 SSA 支配性、基本块终结指令、类型一致性等
- [ir_nodes.py:23-38] 类型系统缺乏位宽和大小信息，LIR 层无法正确分配内存和寄存器
- [pass_manager.py:49] 整数除法使用 Python 地板除法语义，与 C/Rust 的向零舍入不同
- [pass_manager.py:91-121] HIR 常量折叠不递归遍历所有表达式类型，if/match/call 中的子表达式不折叠
- [ir_nodes.py:640-644] MIRFieldAccess.field_name 和 field_index 冗余且可能不一致
- [pass_manager.py:547-612] LIR LICM 不考虑嵌套循环，内层不变量不能外提到外层
- [pass_manager.py:423-431] CSE 引入额外寄存器拷贝而非直接复用结果

#### 原创性分析

**三层 IR 设计的"薄冰"现象：** 每一层都只是"看起来像"成熟的 IR，实际上关键功能都缺失。HIR 类型大多是 TYPE_VAR；MIR 声称是 SSA+CFG 但 SSA 是假的；LIR 声称接近机器码但没有寄存器分配、没有指令选择。

**Pass 实现的"演示级"vs"生产级"差距：** ConstantFolding 是所有 pass 中最完整的，但即使它也有严重问题。其他 pass 情况更糟：Inlining 完全空壳，DCE 漏了 BinOp，CSE 只做基本块内的，LICM 几乎是伪代码。

---

## [2026-07-15] C 运行时 + 测试套件 + Tree-sitter 审查报告（第十四轮）

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 内存安全 | ⭐⭐⭐⭐ | 引用计数模型无循环回收，map remove 泄漏 value，realloc 不计入 free |
| GC 完整性 | ⭐ | 纯引用计数，无循环引用检测，nova_gc_collect 仅返回统计差值 |
| 并发安全 | ⭐ | 全局变量无任何同步原语，完全非线程安全 |
| 测试覆盖度 | ⭐⭐⭐ | 测试文件数量可观，但存在大量盲区（Unicode、fuzz、一致性测试等） |
| 语法一致性 | ⭐⭐ | Tree-sitter 与 parser.py 存在多处语法不一致 |
| 边界情况处理 | ⭐⭐⭐ | 部分边界有处理，但 JSON 解析、字符串操作仍有隐患 |
| 错误处理健壮性 | ⭐⭐⭐ | 部分操作静默失败（文件读写返回空字符串），缺少传播机制 |
| 代码可维护性 | ⭐⭐⭐⭐ | 结构清晰、命名规范，但部分函数过长，注释质量参差不齐 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [nova_runtime.c:597-614] **Map remove 操作泄漏 value 内存** → `nova_map_remove` 只释放 key 和 entry 结构体，没有释放 value 的引用计数，每次 remove 都会泄漏一个 NovaValue 及其子对象 → 在 `nova_free(entry)` 之前，根据 value 类型调用对应的 release 函数
  - 追问：CPython 的 `PyDict_DelItem` 会正确递减 value 的引用计数吗？→ **结论：是的。** 这个 bug 在 CPython 中绝对不能接受。

- [nova_runtime.c:99-103] **纯引用计数无法处理循环引用，nova_gc_collect 名不副实** → `nova_gc_collect` 只是返回统计差值，根本没有执行任何垃圾回收，所有循环引用（自引用列表、Map→ADT→Map、闭包自引用）都会永久泄漏 → 实现标记-清扫式循环检测器，或文档明确说明不支持循环引用
  - 追问：CPython 有专门的循环垃圾回收器，OCaml 用分代标记清扫。纯引用计数 + 无循环回收的方案，在任何成熟语言运行时中能被接受吗？→ **结论：不可接受。**

- [nova_runtime.c:39-43] **全局状态完全非线程安全** → 所有全局计数器和状态变量都没有任何同步保护（无 mutex、无 atomic、无 thread-local），多线程环境下会产生数据竞争 → 使用 `_Atomic int64_t` 保护计数器，或将运行时状态封装到 NovaRuntime* 结构体中
  - 追问：CPython 有 GIL，OCaml runtime 有域锁。完全无锁的全局状态在多线程运行时中能被接受吗？→ **结论：不可接受。**

- [nova_runtime.c:79-87] **nova_realloc 不更新 g_free_count，内存统计失真** → realloc 完全不更新 g_alloc_count 和 g_free_count，nova_gc_collect() 返回的净分配数严重失真 → 正确更新计数：新分配增加 alloc_count，旧内存释放增加 free_count
  - 追问：CPython 的 PYMALLOC_DEBUG 统计是精确的。运行时统计数据不可靠在生产环境中能被接受吗？→ **结论：不可接受。**

- [nova_runtime.c:1206-1224, 1240-1256] **JSON `\uXXXX` 解码堆缓冲区溢出（安全漏洞）** → 预计算 decoded_len 时假设每个 `\uXXXX` 只产生 1 字节，但实际上 U+0080-U+07FF 需要 2 字节、U+0800-U+FFFF 需要 3 字节，预分配缓冲区只有实际需要的 1/2 到 1/3 大小 → 修正预计算逻辑，根据码点范围计算正确的字节数，或采用动态扩容策略
  - 追问：这是一个可被利用的安全漏洞。在 CPython 或任何生产级 JSON 解析器中，这种级别的缓冲区溢出是 P0 级别的 bug 吗？→ **结论：是的，绝对不可接受。**

- [tree-sitter-nova/grammar.js:398-403] **Tree-sitter match arm guard 顺序与 parser.py 不一致** → Tree-sitter 中是 `pattern -> body if condition`，parser.py 中是 `pattern if condition -> body`，两者语法不一致 → 统一语法，以 parser.py 的实际行为为准
  - 追问：成熟语言的语法定义是唯一真相来源。Tree-sitter 语法与官方 parser 不一致在生产级语言中能被接受吗？→ **结论：不能接受。**

- [nova_runtime.c:525-538] **nova_map_put 对非 NovaValue* value 的错误类型转换，破坏 NovaString capacity 字段** → 将 entry->value 强制转换为 NovaValue* 并调用 nova_value_release，对 NovaString* 会把 capacity 字段当作 ref_count 递减，逐渐破坏 capacity 值 → 让 NovaMap 的 value 统一为 NovaValue* 类型，或提供 nova_map_put_with_dtor 让调用方传入释放函数

#### 中等问题（影响特定场景）

- [nova_runtime.c:845-862] nova_read_file 缓冲区溢出风险，依赖 nova_string_new_len 的内部实现细节
- [nova_runtime.c:1240-1256] JSON `\u` 转义不处理代理对（surrogate pairs），补充平面字符解析错误
- [nova_runtime.c:1074-1078, 1156-1160] JSON 解析器不对无效输入报错，采取静默忽略策略
- [nova_runtime.c:205-211] nova_string_find 空字符串和 NULL 参数返回值语义不一致
- [nova_runtime.c:1664-1708] HTTP 临时文件使用 PID 命名存在竞态和符号链接攻击风险
- [nova_runtime.c:1702] HTTP 响应 status_code 硬编码为 200，实际未读取 curl 的 -w 输出
- 缺少 Evaluator 与 VM 的一致性测试，两条执行路径可能产生分歧
- [tree-sitter-nova/grammar.js:612-624] Tree-sitter 运算符优先级与 parser.py 不一致
- 缺少 Unicode / UTF-8 字符串操作测试，nova_string_length 返回字节数而非字符数
- [nova_runtime.c:959] nova_abs_int 对 INT64_MIN 未定义行为（有符号整数溢出）

#### 轻微问题（代码质量）

- [nova_runtime.c:226-240] nova_string_split 末尾空字符串行为，循环条件可读性差
- Tree-sitter 语法缺少 map_expr 实际使用验证，6 个测试语料库中完全没有 map 字面量
- Tree-sitter 语法缺少负数模式匹配测试
- C 运行时测试中大量内存泄漏，测试结尾不验证净分配数为 0
- 缺少 fuzz 测试（parser、JSON、lexer）
- 缺少边界值测试（INT64_MIN/MAX、空字符串、空列表等极值）
- 缺少并发安全测试
- 缺少属性测试（QuickCheck 风格）

#### 原创性分析

**Map value 类型双关的潜伏问题：** 这是之前审查可能遗漏的深层问题。nova_map_put 中的注释声称"碰巧不崩溃"，但实际上会逐渐修改 NovaString 的 capacity 字段，是一个潜伏的数据损坏 bug。

**JSON 解码堆溢出漏洞：** 预计算长度严重不足是典型的安全漏洞，在第十四轮深度审查中才被发现，说明前几轮审查主要关注功能正确性，未深入安全层面。

---

## 第十四轮架构级建议（优先级排序）

1. **立即修复 JSON `\uXXXX` 解码堆缓冲区溢出**（P0 安全漏洞，可被利用）
2. **立即修复类型检查器 TypeVar 过于宽松问题**（类型系统基本失效，等于没有类型检查）
3. **立即修复 MIR SSA 构造根本性错误**（整个 IR 优化管道建立在假 SSA 之上）
4. **立即修复闭包部分应用完全失效**（Evaluator 中柯里化核心功能不可用）
5. **立即修复路径遍历安全漏洞**（模块系统无沙箱限制）
6. **高优先级：修复 VM 闭包参数过多静默丢弃 + 全局可变不检查**
7. **高优先级：修复编译器构造器字段模式未测试 + 嵌套模式失败栈失衡**
8. **高优先级：修复 Parser 比较/相等运算符左结合 + 管道优先级错误**
9. **高优先级：修复 Map remove 泄漏 value + nova_realloc 统计错误**
10. **高优先级：修复错误系统无错误码 + 无文件名**
11. **中优先级：统一 `?` 操作符语法（移入后缀循环）**
12. **中优先级：添加 Evaluator-VM 一致性测试**
13. **中优先级：修复 Block 求值异常安全（try/finally）**
14. **中优先级：修复 Tree-sitter 与 parser.py 语法不一致**
15. **中优先级：修复 native 后端寄存器分配 + 栈上返回值问题**
16. **长期：重写类型检查核心，实现真正的 HM Algorithm W**
17. **长期：重写 IR 降级链，实现真正的 SSA + Phi 消除**
18. **长期：实现真正的 GC 或循环引用检测**


---

## [2026-07-15] 第十五轮审查总览

**审查方式**：三轮 9 个 Explore Agent 并行深度审查
**审查范围**：全部 24 个模块
**新增问题**：约 150+ 个（含严重 25+、中等 45+、轻微 60+）
**核心发现**：多后端一致性缺失、IR 降级链语义错误、类型系统 TypeVar 过于宽松

---

## [2026-07-15] VM 虚拟机 (vm.py) 第十五轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | MATCH_* 系列指令、PIPE_CALL、TRY_UNWRAP 提前返回机制有特色 |
| 可行性 | ⭐⭐⭐ | 核心路径可用；while-in-for CONTINUE 错误、全局可变不检查等严重缺陷仍存 |
| 正确性 | ⭐⭐ | 嵌套循环 CONTINUE 指向错误循环、闭包语义与 Evaluator 多处不一致 |
| 安全性 | ⭐⭐⭐ | 栈下溢保护到位；异常退出状态泄漏、BUILD_MAP 裸异常仍存 |
| 一致性 | ⭐⭐ | 与 Evaluator 至少 7 处行为差异，闭包语义根本不同 |
| 完整性 | ⭐⭐⭐⭐⭐ | 64 个操作码全部有处理路径，无缺失 |
| 工程质量 | ⭐⭐ | 双栈循环系统设计脆弱、重复代码多、hasattr 模式不规范 |
| 性能 | ⭐⭐ | 闭包捕获整个帧 dict 浅拷贝，高频创建闭包场景性能差 |

### 已修复的历史问题（本轮确认）

| 问题 | 状态 | 验证行号 |
|------|------|---------|
| 栈下溢保护 _pop() 统一方法 | ✅ 已修复 | vm.py:534-539 |
| id() 字典键改为 _loop_id 计数器 | ✅ 已修复 | vm.py:170, 984-985, 1028-1029 |
| RETURN 语义（return_flag 正确终止） | ✅ 已修复 | vm.py:477-479, 879-884 |
| base_sp 栈截断 | ✅ 已修复 | vm.py:456-457 |
| CONTINUE while 循环实现 | ✅ 基本修复 | vm.py:843-856 |
| BREAK while 循环使用操作数 | ✅ 基本修复 | vm.py:802-810 |
| 闭包部分应用（柯里化） | ✅ 已修复 | vm.py:379-401 |
| 闭包参数过多校验 | ✅ 已修复 | vm.py:415-418 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [vm.py:834-856] **while-in-for 嵌套时 CONTINUE 指向错误的循环** → `CONTINUE` 无条件优先检查 `_for_iters`，当 while 嵌套在 for 内时，while 体内的 continue 会错误地继续外层 for 循环，违反结构化编程约定 → 使用统一的循环栈（单一列表）替代双栈设计，每个循环条目包含 loop_type、end_ip、loop_start 等，BREAK/CONTINUE 始终作用于栈顶
  - 追问：如果是任何成熟编译器的 VM，continue 不继续最内层循环能被接受吗？→ **结论：绝对不能。** 这是结构化编程的基石性错误。

- [vm.py:799-832] **BREAK 指令的回退扫描路径是定时炸弹** → 当 BREAK 既无操作数也不在 for/while 上下文中时，前向扫描寻找 LOOP_END 或 CONST_UNIT，可能匹配到内层循环、无关位置，且完全不清理栈 → 删除回退路径，直接抛 RuntimeError_("break 不在循环中")
  - 追问：如果是 OCaml 的字节码解释器，用启发式扫描确定 break 目标能被接受吗？→ **结论：绝对不能。** 这是定时炸弹级别的设计。

- [vm.py:592-605] **STORE_VAR 全局变量完全忽略 mutability** → 对局部变量检查 mutable 标志，但对全局变量直接赋值，不可变的全局变量可被随意修改 → 为 globals 引入可变性跟踪，STORE_VAR 在赋值前检查
  - 追问：如果是 Haskell 的编译器，不可变的顶级绑定可以被修改能被接受吗？→ **结论：绝对不能。** 不可变性是函数式语言的基石。

- [vm.py:859-868] **CLOSURE 捕获整个帧 locals 而非自由变量** → 每次创建闭包都 dict 浅拷贝所有局部变量，时间 O(n)，空间 O(n)，且阻止 GC 回收不需要的变量 → 编译器分析自由变量，CLOSURE 指令携带自由变量名列表，VM 只拷贝指定变量
  - 追问：如果 OCaml 的闭包捕获了整个作用域的 dict 拷贝，性能影响能被接受吗？→ **结论：绝对不能。** 内存使用量可能增加 10-100 倍。

- [vm.py:859-868] **闭包可变变量不共享——值语义 vs 引用语义** → 由于是字典浅拷贝，两个闭包捕获的同一个 mutable 变量各自维护独立副本，与 Evaluator 的引用语义不一致 → 引入 MutableCell 包装类，mutable 变量存储为 cell 引用，CLOSURE 拷贝 cell 引用
  - 追问：如果任何函数式语言的闭包对可变变量使用值语义而非引用语义，能被接受吗？→ **结论：不可接受。** 闭包的词法作用域和共享语义是语言的核心。

- [vm.py:825-832] **BREAK 无操作数且无 for/while 上下文时栈完全不清理** → 回退扫描路径只调整 ip，不做任何栈清理，栈上可能残留中间值 → 删除此路径（同问题 2），改为报错

- [vm.py:1269-1283] **TRY_UNWRAP 顶层失败时静默终止，语义不明确** → 顶层代码中 `?` 失败时静默退出，没有错误提示，用户不知道发生了什么 → 顶层 TRY_UNWRAP 失败时应抛出 RuntimeError_ 并打印错误信息

#### 中等问题（影响特定场景）

- [vm.py:993] **FOR_ITER range step=0 静默产生空列表** → step=0 时两个条件都不满足，直接返回空列表；Python range() 和 Evaluator 都会抛异常 → 检查 step == 0，抛出 RuntimeError_("range 步长不能为 0")

- [vm.py:976-977, 1020-1021] **异常退出时循环状态字典泄漏** → for 循环因异常中断时，_range_index/_list_index 条目不清理，_for_iters 也不弹出 → 用 try/finally 或在异常传播时清理循环状态

- [vm.py:608-651] **算术运算缺少类型检查** → ADD、SUB、MUL、NEG 直接使用 Python 运算符，不检查操作数类型，字符串、布尔值可参与运算 → 添加类型检查，仅允许 int/float 操作数（排除 bool）

- [vm.py:913-923] **BUILD_MAP 键不可哈希时抛裸 Python TypeError** → 第 922 行直接赋值，key 不可哈希时抛 Python 原生 TypeError → 用 try/except 捕获并转换为 RuntimeError_

- [vm.py:943-944] **FIELD_ACCESS 对 tuple 不做边界检查** → 直接索引 tuple，越界时抛 Python IndexError → 添加边界检查或用 try/except 捕获

- [vm.py:1147-1165] **MATCH_CONSTRUCTOR 字段按逆序压栈** → 第 1162 行 reversed(subject.fields) 将字段逆序压栈，可能与编译器约定不一致 → 与编译器确认字段压栈顺序约定，确保一致

- [vm.py:1067-1197] **模式匹配失败路径栈深度不一致** → 不同分支失败时栈深度不同，完全依赖编译器生成正确清理代码 → 在 MATCH_START 记录栈底，失败路径统一回滚

- [vm.py:348] **_format_value 遗漏 NovaPartialBuiltin 类型** → isinstance 检查中未包含 NovaPartialBuiltin → 添加该类型

- [vm.py:467-471] **_execute_function 中 RETURN 用裸 pop() 而非 _pop()** → 与整体风格不一致，可能漏掉边界情况统一处理 → 统一使用 _pop()

#### 轻微问题（代码质量）

- [vm.py:534-539] _pop(0) 冗余检查顺序，n==0 检查应在开头
- [vm.py:976-977, 1020-1021] hasattr 模式不规范，应在 __init__ 中初始化
- [vm.py:1062-1065, 1199-1202] MATCH_START 和 MATCH_END 完全是 no-op
- [vm.py:1243-1248] DUP 指令自己做栈下溢检查，未复用 _pop() 机制
- [vm.py:181] read_line lambda 写法令人困惑，应直接写 lambda: input()
- [vm.py:437, 879-884] RETURN 指令在两处重复处理
- [vm.py:817-820] BREAK 清理迭代索引时用 hasattr 检查
- [vm.py:1002, 1042] FOR_ITER 中 base_sp = len(self.stack) - 3 硬编码脆弱

#### 原创性分析

**Nova VM 的特色设计：**
1. MATCH_* 系列专用指令——模式匹配下沉到 VM 层，简化编译器但增加 VM 复杂度
2. PIPE_CALL 专用管道调用指令——减少一次栈操作
3. TRY_UNWRAP 提前返回机制——利用 return_flag 实现 Rust 风格的 ? 操作符
4. FOR_ITER + LOOP_END 双指令循环——职责分离清晰

**已有方案的参考：**
- 基本栈机设计参考 CPython/JVM/Lua VM
- 闭包+帧的设计是标准做法
- 双栈循环系统设计独特但脆弱

#### Evaluator vs VM 对比
| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| 闭包捕获语义 | Environment 引用链（引用语义） | dict 浅拷贝（值语义） | ❌ 严重 |
| 闭包可变变量共享 | 共享（同一 Environment） | 不共享（独立拷贝） | ❌ 严重 |
| 全局变量 mutability | Environment.assign 检查 mutable | 直接赋值，忽略 mutable | ❌ 严重 |
| while-in-for CONTINUE | 继续最内层 while | 错误地继续外层 for | ❌ 严重 |
| range step=0 | Python ValueError 冒泡 | 静默返回空列表 | ❌ 中等 |
| ? 顶层传播 | ReturnSignal 冒泡（未被捕获） | 静默终止，无错误信息 | ❌ 中等 |
| 模式匹配失败 | 报错（无通配符时） | 继续执行（栈可能失衡） | ❌ 中等 |
| 基本算术 | 正确 | 正确 | ✅ |
| ADT 构造 | 正确 | 正确 | ✅ |
| 管道操作 | 正确 | 正确 | ✅ |
| 调用深度限制 | 1000 | 1000 | ✅ |


---

## [2026-07-15] 编译器 (compiler.py) 第十五轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | PIPE_CALL 指令、MATCH_START/END 标记、ADT 原生指令 |
| 可行性 | ⭐⭐⭐ | 基本编译流程可用；复合模式匹配、作用域泄漏有严重 bug |
| 正确性 | ⭐⭐ | 复合模式字面量+绑定混合时栈错位、match 变量作用域泄漏 |
| 安全性 | ⭐⭐⭐ | 栈布局基本正确但模式匹配存在严重栈错位 bug |
| 一致性 | ⭐⭐ | 编译器假设的栈布局与 VM 实际执行有偏差 |
| 完整性 | ⭐⭐⭐ | AST 大部分节点有编译处理；FnDef 作为表达式缺失 |
| 工程质量 | ⭐⭐ | 死代码、重复代码、操作数定义不一致 |
| 性能 | ⭐⭐⭐ | 闭包不做自由变量分析影响效率 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [compiler.py:791-864] **复合模式匹配中字面量+绑定混合时栈错位** → 对于元组/列表/构造器等复合模式，当子模式混合了字面量测试模式和恒匹配模式（变量/通配符）时，测试阶段的栈布局会发生错位，导致后续子模式测试到错误的值。例如 `(a, 42)` 匹配 `(10, 42)` 会失败，因为第一个子模式 `a` 不 POP，第二个子模式测试到错误的字段 → 将测试与绑定合并为单遍编译，或为恒匹配模式插入 POP 保证栈对齐
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **结论：绝对不能接受。** 模式匹配是函数式语言核心特性，属于 P0 级缺陷。

- [compiler.py:881] **模式匹配绑定变量作用域泄漏到外层** → MATCH_BIND 直接写入当前帧 locals，match 结束后从不清理，arm 中绑定的变量泄漏到 match 之后的作用域 → 在 MATCH_END 之前恢复进入 match 前的局部变量环境快照，或引入作用域栈
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **结论：绝对不能接受。** 模式匹配绑定严格限定在 arm 作用域内，是词法作用域的基本要求。

- [vm.py:864-866] **闭包全量捕获当前帧所有局部变量** → CLOSURE 捕获全部局部变量，编译器未做自由变量分析，内存浪费且闭包语义不精确 → 实现自由变量分析，将自由变量列表作为 CLOSURE 操作数
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **结论：不能接受。** 生产级编译器必须做精确的自由变量分析。

- [compiler.py:420-421] **CharLiteral 编译为 CONST_STRING 丢失类型信息** → 字符在运行时与字符串无区别，类型系统的 Char 类型无运行时表示支撑 → 增加 CONST_CHAR 操作码，或通过类型系统保证不混用

#### 中等问题（影响特定场景）

- [compiler.py:81] CLOSURE 操作数定义与实际发射不匹配（code_key 未使用）
- [compiler.py:48,168-177] LOAD_CONST 和常量池完全未使用（死代码）
- [compiler.py:906-970] _compile_pattern_test 和 _compile_pattern_bindings 是死代码（从未调用）
- [compiler.py:93] FOR_ITER 操作数注释错误（写 loop_start_ip 实际是 fail_ip）
- [compiler.py:362-368] 导入名称冲突检测不完整（不检测 let/mut 绑定和 ADT 构造器）
- [compiler.py:409-529] FnDef 不能作为 Block 内部语句（不支持嵌套函数定义）

#### 轻微问题（代码质量）

- [compiler.py:75] LOOP 操作码定义但编译器未使用
- [compiler.py:599-602] 管道编译中 builtin 检查的 if-else 分支完全相同
- [compiler.py:986-1034] ForExpr.step 字段从未被编译器使用（用 tuple hack）
- [compiler.py:329-331] 每次 import 都新建 ModuleResolver
- [compiler.py:172] add_const 去重用 list.index() O(n)
- [compiler.py:534-536] match guard 位置与 grammar.js 不一致

#### 原创性分析

**Nova 特色：**
1. MATCH_TEST_* 系列指令的"成功则弹出、失败则跳转"语义——设计巧妙但引入了栈错位问题
2. TRY_UNWRAP 的早期返回机制——VM 级别支持简化编译器
3. FOR_ITER + LOOP_END 的 for 循环抽象——将迭代管理和结果收集解耦
4. PIPE_CALL 专用指令——语义清晰，为未来优化留空间

**参考已有：** 基本栈机结构参考 CPython/JVM；跳转回填参考标准编译器教材

---

## [2026-07-15] 求值器 (evaluator.py) 第十五轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 两遍扫描支持相互递归；内置 Option/Result 类型 |
| 可行性 | ⭐⭐⭐ | 核心特性可用；负步长 range、TryExpr 类型安全有严重 bug |
| 正确性 | ⭐⭐ | 负步长 range 错误、TryExpr 类型漏洞、短路运算符无类型检查 |
| 安全性 | ⭐⭐ | 大量操作依赖 Python 隐式类型转换，浮点除零泄漏原生异常 |
| 一致性 | ⭐⭐ | 与 VM 在闭包语义、Unit bool、可变变量共享等方面不一致 |
| 完整性 | ⭐⭐⭐ | 大部分 AST 节点有处理；Range tuple hack 污染 AST |
| 工程质量 | ⭐⭐ | eval_decl 重复代码、eval_expr 长 if-elif 链 |
| 性能 | ⭐⭐⭐ | 闭包引用语义效率可接受；缺少递归深度保护 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [evaluator.py:946] **负步长 range 循环计算错误** → `range(start, end + 1, step)` 对负步长错误，`end + 1` 只对正步长正确，对负步长应使用 `end - 1` → `stop = end + 1 if step > 0 else end - 1`
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **不能**。范围迭代是基础特性，反向迭代不工作属于核心语义缺陷。

- [evaluator.py:718-724] **TryExpr 对非 ADT 值静默放行，违反类型安全** → `?` 运算符仅对 NovaADTValue 做判断，非 ADT 值直接原样返回，`42?`、`"hello"?` 都会静默通过 → 添加类型检查，非 ADT 值抛 RuntimeError_
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **绝对不能**。`?` 运算符的全部意义就在于类型安全的错误传播。

- [evaluator.py:721] **TryExpr 在顶层使用会导致未捕获 ReturnSignal 崩溃** → `?` 通过抛出 ReturnSignal 实现错误传播，但 ReturnSignal 只在 _call_fn 中被捕获，顶层使用会以 Python traceback 崩溃 → 在 eval_program 顶层捕获 ReturnSignal 并转换为合适的运行时错误
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **不能**。顶层错误传播应当有明确定义的语义。

- [evaluator.py:871-881] **短路运算符 && / || 不检查操作数类型** → 使用 Python 的 `if not left:` 做真值判断，不验证操作数是 Bool 类型，`0 && true` 返回 0 → 添加类型检查，与 if 表达式保持一致
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **绝对不能**。强类型语言的逻辑运算符必须严格限定在 Bool 类型。

- [evaluator.py:897] **浮点除零未捕获，导致 Python 原生异常泄漏** → 整数除法有除零检查但浮点没有，`1.0 / 0.0` 触发 Python ZeroDivisionError → 用 try/except 包装或提前检查
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **不能**。所有运行时错误都必须被捕获并包装为语言自身的错误类型。

- [evaluator.py:930-931] **一元 `-` 运算符不检查数值类型** → 直接应用 Python `-` 运算符，`-"hello"` 触发 Python TypeError → 添加数值类型检查
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **不能**。所有运算符都必须有明确的类型签名和类型检查。

- [evaluator.py:941] **Range 使用 tuple 混入 AST，破坏类型一致性** → ForExpr.iterable 实际运行时可能是 Python tuple `("range", start, end, step)`，AST 中混入了非 AST 节点的数据结构 → 定义 RangeExpr AST 节点替代 tuple hack
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **绝对不能**。AST 必须是封闭的代数数据类型，用无类型 tuple 混入 AST 等于放弃了类型安全。

#### 中等问题（影响特定场景）

- [evaluator.py:785-788] 赋值错误重新包装 RuntimeError_ 丢失元数据（span、line、column）
- [evaluator.py:986-1012] 列表推导式不处理 break/continue（信号泄漏）
- [evaluator.py:1021-1043] match 守卫与分支使用两个独立子环境（守卫变量不可见）
- [evaluator.py:336] _builtin_abs 将整数输入转换为浮点输出（改变输入类型）
- [evaluator.py:384-404] _format_value 不处理 dict/Map 类型
- [evaluator.py:342] _builtin_pow 始终返回 float
- [evaluator.py:1047-1101] 模式匹配缺少线性检查（重复变量绑定不报错）
- [evaluator.py:1006] 列表推导式过滤条件不检查 Bool 类型
- [evaluator.py:1071-1081] 构造器模式匹配不校验 type_name
- [evaluator.py:953-965] _eval_for_expr 每次迭代创建新环境未复用

#### 轻微问题（代码质量）

- UNIT_VALUE 与 VM 的 UNIT 命名不一致
- _UnitValue 类未使用单例模式
- 错误消息中英文混用
- ForExpr.step 字段在 AST 中定义但 evaluator 不使用
- eval_decl 方法与 _eval_decl_body 大量重复
- FieldAccess 元组索引的 ValueError 被静默忽略
- MapExpr 键值对求值顺序依赖 Python dict 推导式

#### 原创性分析

**深层架构问题：**
1. AST 类型污染——用 tuple 表示 range 表达式是最严重的架构问题
2. 异常驱动控制流的脆弱性——break/continue/return 全部基于 Python 异常
3. 环境链 vs 显式闭包捕获的设计分歧——与 VM 实现根本不同

**零覆盖率的功能区域：** TryExpr、PatternList、守卫条件、MapExpr、CharLiteral、负步长 range、闭包可变变量捕获

#### Evaluator vs VM 对比
| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| 负步长 range 循环 | 返回空列表（bug） | 正确返回 | ❌ Evaluator Bug |
| ? 非 ADT 值 | 静默返回原值 | 抛出 RuntimeError_ | ❌ Evaluator Bug |
| ? 顶层使用 | ReturnSignal 泄漏崩溃 | 提前退出循环 | ❌ Evaluator Bug |
| &&/|| 类型检查 | 不检查，接受任意类型 | 严格检查 Bool | ❌ Evaluator Bug |
| 闭包可变变量捕获 | 引用语义，正确共享 | 值语义，不共享 | ❌ VM Bug |
| 浮点除零错误 | 泄漏 Python 异常 | 捕获并包装 | ❌ Evaluator Bug |
| 全局变量 mutability | 检查 mutable | 忽略 mutable | ❌ VM Bug |


---

## [2026-07-15] 类型检查器 (type_checker.py) 第十五轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 类型推断算法正确性 | ⭐⭐ | 非真正 HM 推断，无合一(unification)，TypeVar 过于宽松 |
| 泛型支持完备性 | ⭐⭐⭐ | ADTType.__eq__ 正确比较类型参数，但无类型方案、无 fresh 实例化 |
| 模式匹配类型检查 | ⭐⭐⭐ | 基本模式存在，但无 guard 检查、无穷尽性检查、无冗余分支检测 |
| 错误恢复能力 | ⭐⭐ | ErrorCollector 已实现但有路径绕过，级联错误掩盖 |
| 类型标注支持 | ⭐⭐⭐ | 基本类型语法全部支持，但 TypeVar 无语法支持 |
| 递归类型处理 | ⭐ | 无 occurs check，递归 ADT 无标注时可能失效 |
| let 多态 | ⭐ | 完全缺失，无 TypeScheme/generalize/instantiate |
| 工程质量 | ⭐⭐ | 代码结构清晰，但核心算法缺失 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [type_checker.py:1318-1319] **_types_compatible 中 TypeVar 过于宽松——类型系统基本失效** → 任何一方是 TypeVar 就返回 True，类型变量不是"待推断的类型"而是"任何类型都兼容"的通配符，整个类型系统的静态保证基本失效 → 实现真正的合一(unification)算法，使用 union-find 结构管理类型变量等价类
  - 追问：如果是 OCaml/Haskell 的编译器，类型变量与任何类型都兼容能被接受吗？→ **结论：绝对不能。** 这等于没有类型系统。

- [type_checker.py:1190-1192] **_collect_type_bindings 缺少一致性检查——同一变量可绑定到不同类型** → 同一个 TypeVar 在不同位置实际类型不同时，第一次绑定生效，第二次被静默忽略，泛型函数调用类型不一致不会被检测 → 当 TypeVar 已在 bindings 中时，检查新 actual 与旧绑定是否一致，不一致时报类型错误
  - 追问：如果是 Haskell 的类型检查器，不检查同一类型变量的多次绑定一致性，能被接受吗？→ **结论：绝对不能。** 这是参数化多态的基础。

- [type_checker.py:1188-1208] **_collect_type_bindings 中 actual 为 TypeVar 时完全不处理** → 类型信息只能从实参流向形参，不能反向流动，高阶函数场景下类型推断完全失效 → 实现双向类型检查或完整的合一算法

- [type_checker.py（全局缺失）] **全局缺失 occurs check——递归类型可无限展开** → 整个类型检查器没有出现检查，`let rec f x = f x` 不会被拒绝，可能产生无限类型 → 实现合一算法时加入 occurs check；对于递归 ADT 使用基于名称的递归类型表示
  - 追问：如果是 OCaml 的类型检查器，没有 occurs check 导致无限类型，能被接受吗？→ **结论：绝对不能。** Occurs check 是 HM 类型系统的安全基石。

- [type_checker.py:285-293] **内置 ADT 构造函数使用相同 TypeVar 实例——所有调用共享类型变量** → Some、None、Ok、Err 的类型签名使用同一个 TypeVar 对象，每次调用不生成新鲜实例，所有泛型构造函数实际上是单态的 → 实现类型方案(TypeScheme)概念，每次引用多态值时生成新鲜的类型变量实例
  - 追问：如果是 Haskell 的类型检查器，多态函数每次调用不生成新鲜类型变量，能被接受吗？→ **结论：绝对不能。** 这是参数化多态的基本实现机制。

- [type_checker.py:520-530, 779-789] **Let 多态完全未实现——HM 类型系统的核心缺陷** → LetBinding 直接将推断出的类型赋值给变量名，没有泛化步骤，`let id = fun x -> x in id 1 + id "a"` 会报错 → 实现完整的 HM 类型推断算法 W，包括 TypeScheme、generalize、instantiate
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **结论：绝对不能。** Let 多态是 HM 类型系统的基石。

- [type_checker.py:1000-1008] **Match guard 完全没有类型检查** → check_match_arm 完全不检查 arm.guard，守卫表达式可以是任何类型 → 在模式匹配成功后检查 guard 类型为 Bool
  - 追问：如果是 Rust 的 match guard 不做类型检查，能被接受吗？→ **结论：绝对不能。** Guard 是 match 表达式的关键组成部分。

- [type_checker.py:1126-1132] **== 和 != 操作符完全不检查操作数类型兼容性** → 只有 < > <= >= 做了数值类型检查，== 和 != 直接返回 BOOL_T，`42 == "hello"` 不会被捕获 → 对 == 和 != 添加类型兼容性检查
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **结论：绝对不能。** 相等比较的类型安全是静态类型系统最基本的保障。

- [type_checker.py:613, 631-632] **空列表/空 Map 共享固定名字的 TypeVar，导致错误的类型关联** → 所有空列表共享名为 "unknown_list_elem" 的同一个 TypeVar，两个不相关的空列表会被认为有相同的元素类型 → 使用计数器生成唯一的 TypeVar 名称
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **结论：不能。** 每个独立的空列表应有自己的多态类型变量。

- [type_checker.py:740-750] **FnCall 中 TypeVar callee 绕过错误报告机制** → 被调用者类型为 TypeVar 时，直接调用 error_collector.add() 而非 _report_error()，在非 collect_errors 模式下错误被静默吞掉 → 统一使用 _report_error 方法

#### 中等问题（影响特定场景）

- [type_checker.py:939-958] ForExpr 循环变量类型与迭代器类型完全脱节
- [type_checker.py:972-994] ListComprehension 有同样的循环变量类型问题
- [type_checker.py:755-770] PipeExpr 类型检查逻辑混乱且不做类型变量替换
- [type_checker.py:1138, 1141] 逻辑操作 || 的错误消息硬编码为 &&
- [type_checker.py:791-794] 局部 MutBinding 不检查类型标注
- [type_checker.py:1248-1252] 类型别名循环检测仅检测直接循环
- [type_checker.py:1294-1312] _expand_alias 不处理 TypeVar，实际是死代码
- [type_checker.py:677-689] 模式匹配无穷尽性检查缺失
- [type_checker.py:677-689] 模式匹配无冗余分支检测
- [type_checker.py:350] json_parse 返回类型为 TypeVar，绕过类型检查

#### 轻微问题（代码质量）

- TypeVar 命名混乱，缺乏统一规范
- _types_compatible 与 __eq__ 功能重叠且语义不一致
- 导入模块时名称冲突处理不一致
- ADT 变体字段名元组结构不直观
- check_program 中 _user_defined_names 初始化不总是有值
- PatternList 不支持 cons 模式（head :: tail）

#### 原创性分析

**原创性：低** — 代码声称实现了 Hindley-Milner 类型推断，但实际上只是"带类型变量占位符的类型检查器"。缺少 HM 系统的所有关键组件：合一算法、类型方案、let 多态、occurs check、算法 W。当前实现本质是带类型标注的、部分类型推断的渐进式类型检查器。

**值得肯定的设计：**
1. ADTType 的 __eq__ 和 __hash__ 正确实现了类型参数比较
2. 两遍扫描架构支持前向引用和相互递归
3. ErrorType 单例模式用于错误恢复
4. ADT 字段访问的"所有变体共有字段"检查是有意思的设计

---

## [2026-07-15] 词法/语法分析器 (lexer.py + parser.py) 第十五轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| Token 覆盖 | ⭐⭐⭐ | 基本 token 齐全，但存在死 token、`<-` 无独立 token |
| 词法错误恢复 | ⭐⭐ | 未闭合字符串/非法字符用递归恢复，有栈溢出风险 |
| 运算符优先级 | ⭐⭐ | 与 grammar.js 严重不一致，`|>` 优先级偏差 4 级 |
| 结合性 | ⭐⭐⭐ | 大部分左结合正确，但赋值无右结合 |
| 歧义性 | ⭐⭐⭐ | 无悬挂 else 问题，但 `{` 的 map/block 区分策略脆弱 |
| 左递归 | ⭐⭐⭐⭐ | 递归下降采用优先级分层，无左递归问题 |
| 错误位置 | ⭐⭐ | _make_error span 计算错误，多处 span 起点不准确 |
| 工程质量 | ⭐⭐ | 死代码多、硬编码多、代码模式脆弱 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [lexer.py:258,267,281,308,458] **错误恢复使用递归调用 _next_token()，可能导致栈溢出** → 未闭合字符串、非法字符等错误恢复通过递归调用实现，大量连续非法字符可导致 Python 递归深度超限崩溃，是 DoS 漏洞 → 将递归调用改为循环，在 _next_token 中使用 while True 循环
  - 追问：如果是 GCC 或 Clang 的编译器，这个 bug 能被接受吗？→ **绝对不能接受。** GCC 使用循环跳过非法字符，绝不会递归调用词法器主循环。

- [parser.py:672-678] **`|>` 管道操作符优先级与 grammar.js 规范严重不一致** → parser.py 中 `|>` 优先级比规范高 4 个等级，`x |> f == y` 解析为 `x |> (f == y)` 而非 `(x |> f) == y` → 将 _parse_pipe 移到优先级最低层，与 grammar.js 的 PREC.PIPE=2 对齐
  - 追问：如果是 GCC 或 Clang 的编译器，这个 bug 能被接受吗？→ **绝对不能接受。** 运算符优先级是语言规范的核心契约。

- [parser.py:680-687] **`++` 字符串拼接优先级位置错误** → CONCAT 优先级应低于加减但实际高于加减，与 grammar.js 不一致 → 调整优先级链，使 _parse_additive_expr 调用 _parse_cons_expr

- [parser.py:464-466, 970-972] **`<-` 不是独立 token，解析方式脆弱且错误** → `<-` 通过 LT + MINUS 拼接，允许空白分隔，错误消息不准确 → 在 lexer 中添加 LEFT_ARROW token 类型，parser 直接匹配
  - 追问：如果是 GCC 或 Clang 的编译器，这个 bug 能被接受吗？→ **不能接受。** 多字符操作符必须作为单个 token 识别。

- [lexer.py:155-160] **_make_error 方法的 span 计算完全错误** → end_col 使用 self.column - 1，但当前列可能已推进很远，max(column, end_col) 无意义 → 为每种错误场景正确计算 span
  - 追问：如果是 GCC 或 Clang 的编译器，这个 bug 能被接受吗？→ **不能接受。** 错误位置准确性是编译器最基本的用户体验要求。

- [parser.py:844-884] **_is_map_literal 前瞻扫描策略在语法错误时误导** → 通过扫描匹配的 `}` 内是否有 `=>` 判断是 map 还是 block，语法错误时会误判 → 采用上下文驱动策略，或在 _parse_map_expr 失败时回退尝试 _parse_block
  - 追问：如果是 GCC 或 Clang 的编译器，这个 bug 能被接受吗？→ **不能接受。** GCC 处理 C++ 的 `{` 歧义使用上下文相关解析。

- [parser.py:733-769] **`?` 操作符位置错误：后缀循环外才处理** → `expr?.field` 无法正确解析，`.field` 被"剩下"导致意外解析错误 → 将 `?` 放入后缀循环中（与函数调用、字段访问同级）

- [parser.py:522] **match arm 起始 token 列表漏掉 CHAR 和 MINUS** → 无逗号分隔的 match arm 中，字符模式和负数模式会导致解析失败 → 将 TokenType.CHAR 和 TokenType.MINUS 添加到 while 条件列表中

- [parser.py:476-483] **iterable 类型不一致（表达式 vs 元组）** → ForExpr.iterable 对 in 形式是表达式节点，对 <- 形式是 tuple ("range", ...)，破坏 AST 类型一致性 → 创建 RangeExpr AST 节点

- [parser.py:522] **match arm 继续条件过长且脆弱** → 硬编码所有可能作为 pattern 开头的 token 类型，容易漏掉新的 pattern 类型 → 提取 _is_pattern_start() 辅助函数共享使用

#### 中等问题（影响特定场景）

- [lexer.py:88] PIPE_VARIANT 是死 Token，永不生成
- [lexer.py:91] UNIT Token 是死 Token
- [lexer.py:202-221] 数字字面量不支持科学计数法、十六进制、八进制、二进制
- [lexer.py:208] 数字字面量不支持下划线分隔符
- [lexer.py:186-200] 不支持块注释 /* ... */
- [lexer.py:250-251] 字符串转义遇到未知转义序列时静默忽略
- [parser.py:215-242] type 定义中变体的 `|` 分隔符可选，导致语法歧义
- [parser.py:334-346] Fn[Int, String] 类型语法没有返回类型位置
- [parser.py:386-391] 块内赋值的判断无法处理字段/索引赋值
- [parser.py:378-414] 块解析中语句分隔逻辑混乱
- [parser.py:534-536] match guard 位置与 grammar.js 不一致

#### 轻微问题（代码质量）

- [lexer.py:87] UNDERSCORE token 注释不准确
- [parser.py:11] from typing import Any 未使用
- [parser.py:436] tok = self.tokens[self.pos - 1] 模式重复
- [lexer.py:13] Span 导入在函数内部，风格不统一
- [parser.py:81] _span 方法名与属性命名冲突风险
- [parser.py:545-630] _parse_pattern 方法过长（85 行）
- [lexer.py:109-110] Token.__repr__ 输出中文"行/列"
- [parser.py:748-754] 元组索引用 FieldAccess 表示不清晰

#### 原创性分析

**核心问题：** 优先级表与规范存在系统性偏差，不是简单漏了一级而是整个优先级层级结构都需要重构。`<-` 操作符的系统性缺失是词法分析器偷懒、语法分析器买单的反模式。错误恢复的递归反模式是系统性设计缺陷。

**`{` 的 map/block 歧义是设计层面的问题**——选择用"扫描整个 block 看有没有 =>"来解决，效率低且不准确。更好的做法是从语法层面消除歧义。


---

## [2026-07-15] 错误处理 + 模块系统 + 环境 (errors.py + modules.py + environment.py) 第十五轮审查报告

### 总体评分
| 维度 | errors.py | modules.py | environment.py |
|------|-----------|------------|----------------|
| 正确性 | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| 健壮性（边界处理） | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| 错误信息质量 | ⭐⭐⭐ | ⭐ | ⭐ |
| 模块系统完整性 | — | ⭐⭐ | — |
| 作用域/闭包正确性 | — | — | ⭐⭐ |
| 代码可维护性 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| 测试覆盖 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [errors.py:165] **_format_with_context 中 end_col 默认值错误导致下划线长度总是 1** → 当没有 span 也没有 highlight_span 时，end_col = self.column + 1，下划线只有 1 个字符宽，无法准确标示错误范围 → 对于单点错误至少用 3-5 个 ^ 标示，或高亮整个 token
  - 追问：如果 Rust 编译器的错误信息缺少源码上下文，能被接受吗？→ **结论：不能接受。** rustc 的错误信息以精确的源码高亮著称。

- [errors.py:277-281] **_compute_underline 多行首行下划线偏移错误、末行完全错位** → 末行下划线没有前导空格，^ 直接从行首开始，与实际错误位置对不齐；末行 end_col - 1 少算了一列 → 修正多行下划线的起始偏移和长度计算

- [modules.py:271-274] **循环导入检测使用 list.remove() + 异常安全路径，存在竞态和性能问题** → 用列表进行循环检测，O(n) 查找和删除；检测发生在文件读取之后，浪费 I/O → 使用 Set 进行 O(1) 检测，保留列表用于错误消息；将循环检测移到文件读取之前

- [modules.py:53-57] **ModuleInfo.get_exported_bindings 静默吞掉所有异常** → 导出的名称在求值环境中找不到时被静默忽略，export foo 但 foo 从未定义也不会报错 → 导出名称时验证其是否存在于环境中，不存在则发出警告或错误

- [environment.py:50-61] **Environment.assign 允许在父作用域修改变量，破坏闭包封装** → assign 沿着作用域链向上查找并修改父作用域变量，没有函数作用域边界标记，无法区分 nonlocal 和 global → 在 Environment 中添加 is_function_scope 标记，assign 只在当前函数作用域及更内层查找

- [modules.py:328-337] **模块导入命名空间污染** → import 会将模块所有导出名称直接注入当前作用域，无命名空间前缀、无选择性导入，同名导出后者覆盖前者无警告 → 实现命名空间导入和选择性导入

#### 中等问题（影响特定场景）

- [errors.py:186-191] 位置信息格式不符合行业标准（用中文而非 file:line:col）
- [errors.py:365-370] ErrorCollector.add 的分类逻辑不完整（NOTE/HELP 被当错误）
- [errors.py:405-411] ErrorCollector.raise_all 将后续错误格式化为 note 丢失结构化信息
- [modules.py:124-130] ModuleResolver 相对路径解析依赖 search_paths[0] 作为当前目录
- [modules.py:98-105] 默认搜索路径包含相对路径，行为依赖工作目录
- [modules.py:243-249] load_module 中导出收集在类型检查之前进行
- [environment.py:40] Environment.lookup 抛出 RuntimeError_ 但没有位置信息
- [environment.py:67-73] all_bindings 子作用域覆盖父作用域有性能问题
- [errors.py:320] RuntimeError_ 命名不一致且与 Python 内置冲突风险

#### 轻微问题（代码质量）

- [errors.py:47] ANSI.enabled 方法名是动词但返回布尔值
- [errors.py:61] SourceSpan = Span 别名多余
- [errors.py:68-75] RelatedNote 同时有 line/column 和 span 两套位置系统
- [modules.py:276-299] _collect_exports 和 _collect_exported_types 逻辑几乎重复
- [modules.py:305-339] import_module 既有副作用又有返回值，API 设计不清晰
- [environment.py:63-65] child() 方法名可改为 new_scope() 更直观
- [environment.py:17-20] BindingInfo 的 name 字段冗余
- [errors.py:334-351] BreakSignal/ContinueSignal/ReturnSignal 放在 errors.py 不合适
- [errors.py:413-420] format_all 错误和警告分开遍历，顺序与源码不一致

#### 原创性分析

**错误格式化系统：** 试图模仿 Rust 编译器的错误输出风格，但实现深度不足——有源码上下文但精度不够，有 ANSI 颜色但色阶单一，有相关注释但无错误码，无建议修复。

**模块系统：** 实现了基本的导入导出和循环检测，但缺少现代语言模块系统的核心特性——无命名空间、无选择性导入、无重命名、无重新导出。当前更像是 Python 2 的 from module import * 模式。

**环境/作用域：** 教科书式的作用域链实现，但对于支持闭包的语言过于简单——没有函数作用域标记，没有环境快照机制，没有作用域类型区分。

---

## [2026-07-15] 所有后端 (backend/ + c_codegen.py) 第十五轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 指令覆盖完整性 | ⭐⭐⭐ | Native 声称全覆盖但质量存疑；Cranelift/Wasm 缺 3-4 条指令 |
| 生成代码正确性 | ⭐ | 存在大量正确性 bug，多数后端生成的代码无法正确运行 |
| 端到端测试覆盖 | ⭐⭐ | 有指令编码级单元测试，但无运行时验证 |
| 寄存器分配质量 | ⭐ | Native 后端的寄存器分配是装饰性的，用完后静默跳过 |
| ABI 合规性 | ⭐⭐ | System V 参数传递有雏形但参数未正确加载 |
| 架构设计合理性 | ⭐⭐ | 三层 IR 架构思路清晰，但管道实现不一致 |
| 代码可维护性 | ⭐⭐ | 可读性尚可，但大量硬编码、重复逻辑和半成品 |
| 综合评级 | ⭐⭐ | 原型级别，远未达到生产可用 |

### 各后端单独评估

| 后端 | LIR 覆盖 | 可行性 | 核心问题 |
|------|---------|--------|---------|
| Native（自研 x86_64） | 19/19 | Demo 级别 | 寄存器分配假、除法破坏 RDX、索引破坏基址、参数未加载、返回值无保证 |
| Cranelift | 16/19 | 纯文本生成器 | 浮点操作误用整型指令、分支标签硬编码、LIRIndex 完全错误 |
| WasmGC | 15/19 | Demo 级别 | Label 用 block 实现语义错误、字符串 NUL 终止符是字面量 |
| C CodeGen | 不适用（绕开 IR） | 相对最成熟 | 类型推断默认 int64_t、match guard 有未初始化风险 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [native_backend.py:202-211] **寄存器分配器静默失败，导致指令不被发射** → 虚拟寄存器超过可用物理寄存器时，vregs[name] = None，后续指令静默跳过，生成的代码行为完全不可预测 → 要么真正实现带 spill 的寄存器分配，要么在寄存器耗尽时显式报错
  - 追问：如果 OCaml 的 native 编译器生成的代码不正确，能被接受吗？→ **结论：绝对不能。** 编译器的核心职责是生成正确的代码，静默生成错误代码是最严重的缺陷。

- [native_backend.py:430-443] **除法/取模操作静默破坏 RDX 寄存器** → idiv 同时破坏 RAX 和 RDX，代码只保存/恢复了 RAX，完全没考虑 RDX 是否被其他值占用 → 在 idiv 前检查 RDX 是否活跃，若是则先 push 到栈上

- [native_backend.py:715] **LIRIndex 破坏基址寄存器** → add_reg_reg(base_reg, RCX) 直接修改基址寄存器，多次索引的基址会错 → 使用 SIB 寻址，或先 mov 到临时寄存器

- [native_backend.py:340-381] **函数参数从未被加载到虚拟寄存器** → System V ABI 的参数在 RDI/RSI 等寄存器中，但代码从未映射到虚拟寄存器名 → 在函数体编译前遍历 func.params，映射到对应的 ABI 参数寄存器

- [native_backend.py:518-522] **返回值位置无任何保证** → 注释声称返回值在 RAX/XMM0，但没有代码保证这一点，结果被分配到其他寄存器时返回错误值 → LIRReturn 根据返回类型将值移动到 RAX/XMM0

- [compiler_pipeline.py:33-35] **Native 后端在编译管道中根本未被使用** → BACKEND_NATIVE 对应的是 CraneliftBackend，而不是 NativeCodeGen → 新增 BACKEND_CRANELIFT 常量，将 BACKEND_NATIVE 指向 NativeCodeGen

- [cranelift_backend.py:234-238] **Cranelift 后端浮点操作使用整型指令** → _emit_binop 完全不区分整型和浮点，浮点加法也生成 iadd → 根据类型信息选择 int_op_map 或 float_op_map

- [wasm_backend.py:230-232] **Wasm 后端 Label 用 block 实现，控制流语义错误** → Wasm block 不支持任意 goto，br 只能跳出，循环无法工作 → 使用 loop + block 组合，或将 LIR 的 CFG 重新结构化

- [compiler_pipeline.py:81-84] **C 后端绕过所有 IR 层，管道设计不一致** → C 后端直接从 AST 生成代码，完全跳过三层 IR 和所有优化 pass → C 后端应从 LIR 生成代码，保持管道一致性

#### 中等问题（影响特定场景）

- [wasm_backend.py:161] 字符串 NUL 终止符是字面量 \x00 而非字节（b"\\x00" vs b"\x00"）
- [cranelift_backend.py:162-168] 分支标签硬编码为 block_true/block_false
- [cranelift_backend.py:187-188] LIRIndex 总是从 v0+0 加载
- [native_backend.py:834] _start 入口加载了错误的 argc（偏移 8 而非 0）
- [c_codegen.py:655-669] match guard 不成立时 tmp 未初始化
- [c_codegen.py:1301-1302] Identifier 类型推断默认 int64_t
- [wasm_backend.py:273-276] LIRBuildADT 只分配不写内容
- [native_backend.py:745] 栈上分配的结构可能被覆盖（与 stack_size 不同步）
- [compiler_pipeline.py:90-107] compile_to_ir_text 跳过类型检查

#### 轻微问题（代码质量）

- LinearScanAllocator 类定义了但从未被使用
- x86_64.py:467-473 je_rel32 方法定义了两次
- 字符串常量生成 symbol_value @str_v0，但符号未定义
- ADT 构造器使用 GNU C 语句表达式，非标准扩展
- FLOAT_NEG 用 0.0 - x 实现，效率低且有语义差异
- 函数调用参数硬编码为 i64 类型，浮点参数应为 f64

#### 原创性分析

**有原创价值的部分：**
1. 三层 IR 架构，参考 MLIR Dialect 思想，分层清晰
2. 零依赖 x86_64 编码器，纯 Python 手写从 REX 前缀到 ModR/M 到 SIB
3. 零依赖 ELF 生成器，直接构造 ELF64 header
4. 线性扫描寄存器分配器（虽然没被用上）


---

## [2026-07-15] IR 系统 + Pass 管理器 (ir/) 第十五轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 三层IR设计合理性 | ⭐⭐⭐ | 分层理念正确，但边界模糊，HIR混入声明，LIR过于抽象 |
| 优化Pass完整性 | ⭐⭐ | 常量折叠相对完整，CSE有限，DCE极弱，LICM逻辑错误，内联空壳 |
| Pass管理器健壮性 | ⭐ | 全局吞异常是致命设计缺陷，严重程度最高 |
| Lowering正确性 | ⭐⭐ | 简单表达式正确，控制流/模式匹配/phi节点严重错误 |
| 类型安全 | ⭐⭐ | dataclass设计良好，但HIRBlockExpr类型违规 |
| 代码可维护性 | ⭐⭐⭐ | 结构清晰命名规范，但大量stub和部分实现造成误导 |
| 测试覆盖 | ⭐⭐ | 有测试但多为"不抛异常即可"级别，未验证语义正确性 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [pass_manager.py:720-725, 736-741, 752-757] **Pass 管理器静默吞掉所有 Pass 异常** → 三个 run_*_passes 方法均用 try/except Exception 捕获所有 pass 异常，仅打印到 stderr 后继续执行，IR 可能处于部分修改的不一致状态 → 区分致命错误和可恢复错误，pass 失败默认为致命错误，立即中止编译
  - 追问：如果 LLVM 的 opt 工具静默吞掉所有 pass 异常，能被接受吗？→ **结论：绝对不能接受。** 优化器的正确性是编译器最基本的承诺。

- [pass_manager.py:596-608] **LICM LIR 层"外提"指令实际仍在循环内** → LICM 将可外提指令插入到 header_idx + 1，但循环体的定义就是 loop_start = header_idx + 1，指令仍在每次迭代中执行 → 外提位置应为 header_idx（插入到循环头标签之前），修复测试用例
  - 追问：如果 LLVM 的 LICM pass 实际上没有把指令移到循环外，能被接受吗？→ **结论：绝对不能。** 这是 pass 名实不符的欺诈性 bug。

- [lir_lowering.py:204-211] **MIR Phi 节点在 LIR lowering 中被错误实现** → SSA Phi 节点被降级为简单的寄存器复制，仅取第一个源操作数，所有控制流合并点的语义完全错误 → Phi 节点不能在 LIR 中被降级，应在每个前驱块末尾插入 copy 指令，或保留 phi 节点由寄存器分配器处理
  - 追问：如果 LLVM 的 SSA 构造器把 phi 节点变成只取第一个源，能被接受吗？→ **结论：绝对不能。** Phi 节点是 SSA 形式的核心，此 bug 导致整个 MIR→LIR 降级对含控制流的代码都是错误的。

- [pass_manager.py:105-108, 115-118] **HIR 常量折叠使用 __class__ 篡改对象类型** → 通过直接修改 expr.__class__ 将 HIRBinaryOp 原地变为 HIRIntLiteral，同时用 del 删除旧字段，这是 Python 中极度危险的反模式 → 创建新的 HIRIntLiteral/HIRFloatLiteral 对象返回，而非原地修改

- [lir_lowering.py:219-223] **LIR Branch 未设置 true/false 目标标签** → MIRBranch 降级为 LIRBranch 时，true_label 和 false_label 字段从未被赋值，所有条件跳转都没有目标地址 → 正确设置两个标签字段

- [mir_lowering.py:351-384] **MIR Match 降级无实际匹配逻辑，直接顺序执行所有分支** → 为每个 arm 创建基本块，但用无条件跳转串联所有 arm 块，没有任何模式比较和条件分派 → 为每个 arm 生成模式比较代码，使用 MIRBranch 实现比较成功则执行 arm 体，失败则跳到下一个 arm

- [lir_lowering.py:231-241] **MIRSwitch 和 MIRMatchJump 降级为无条件跳转** → 都被降级为跳转到 default 目标的无条件 LIRJump，所有 case 信息完全丢失 → 在 LIR 中增加 LIRSwitch 指令，或展开为比较+分支序列

#### 中等问题（影响特定场景）

- [hir_lowering.py:292-300] HIRBlockExpr 类型违规 - HIRLetDecl 混入 expr 列表
- [mir_lowering.py:404-406] MIR For 循环降级 - iterable 直接当布尔条件用
- [pass_manager.py:346] DCE pass 极弱 - LIRBinOp 未被视为无副作用
- [pass_manager.py:91-121] HIR 常量折叠仅处理 BinaryOp，不递归进入其他表达式
- [pass_manager.py:474-480] MIR CSE 使用 MIRLoad 替代重复计算，语义错误
- [pass_manager.py:630-641] MIR LICM 回边检测逻辑错误（无支配关系判断）
- [pass_manager.py:652-656] MIR LICM 仅收集 header 块的定义作为循环内定义
- [mir_lowering.py:299-305] HIR UnwrapExpr 降级为普通字段访问，丢失早返回语义
- [hir_lowering.py:332-333] HIRConstructorPattern 的 type_name 为空字符串
- [mir_lowering.py:285-289] 列表推导式降级为空列表常量

#### 轻微问题（代码质量）

- Inlining pass 完全是空壳（return False）
- HIR AliasDecl 丢失目标类型信息（TYPE_VAR）
- Lambda 降级为无体闭包占位符
- MIRMapBuild 降级为 LIRBuildList
- LIR Return 值的类型硬编码为 UNIT_TYPE
- HIR 标识符未找到时静默返回 None
- MIRFieldAccess 的 field_index 从未设置
- _SIDE_EFFECT_TYPES 定义但从未使用
- LIR stack_size 简单按 loc_counter * 8 估算
- MIR lowering 的 ForExpr step 字段未使用

#### 原创性分析

**设计亮点：**
1. 三层 IR 架构借鉴 MLIR 思想，方向正确
2. Pass 管理器支持不动点迭代（max_iterations + changed 检测）
3. 类型系统设计统一（NovaType 三层共享）
4. LIR 指令的 src_locs/dst_loc 设计将寄存器分配和指令语义分离

**不足与差距：**
1. 实现深度严重不足，大量核心功能是 stub
2. 测试偏"存在性验证"，不验证语义正确性
3. 降级过程中信息大量丢失
4. 错误处理哲学错误——静默降级而非明确报错

---

## [2026-07-15] 运行时 + 测试 + Tree-sitter 第十五轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| C 运行时内存安全 | ⭐⭐ | 引用计数不处理循环引用，Map value 释放存在类型混淆 |
| 运行时数据结构正确性 | ⭐⭐⭐ | 基础功能可用，但嵌套容器释放存在严重漏洞 |
| 测试覆盖率（Evaluator） | ⭐⭐⭐ | ~80 个 Evaluator 测试，缺少错误路径和高级特性 |
| 测试覆盖率（VM） | ⭐⭐⭐⭐ | ~93 个 VM 测试，覆盖主要特性 |
| 两条路径行为一致性验证 | ⭐ | 几乎没有测试同时验证 Evaluator 和 VM 的输出一致性 |
| Tree-sitter 语法一致性 | ⭐⭐⭐ | 运算符优先级与 Python parser 不一致 |
| 测试完整性 | ⭐⭐ | 泛型函数、模块系统类型检查、网络 HTTP 等缺乏测试 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [nova_runtime.c:99-103] **GC 完全不处理循环引用** → nova_gc_collect() 仅返回净分配数，无任何 GC 逻辑，闭包自引用、ADT 自引用、循环数据结构都会永久泄漏 → 实现 tracing GC（标记-清扫）或至少提供循环引用检测
  - 追问：如果 GHC 缺少核心语言特性的测试，能被接受吗？→ **结论：不能。** 但对于 GC 来说，不处理循环引用对函数式语言是严重缺陷。

- [nova_runtime.c:536-538] **nova_map_put 更新 value 时存在类型混淆释放** → 用 nova_value_release 释放任意 void* value，对 NovaList/NovaADT 等不同类型，ref_count 偏移量对应的字段值可能恰好为 1，导致误释放 → NovaMap 增加 value_type 标签，或统一所有 heap 对象的头部布局

- [nova_runtime.c:479-486, 651-668, 749-756] **嵌套容器释放不递归，导致内存泄漏** → nova_list_release 只释放 items 数组不释放元素，nova_map_release 只释放 key 不释放 value，nova_adt_release 只释放 fields 数组不释放字段内容 → 为每个容器类型增加 element_free_fn 回调，或在统一类型系统下递归调用 release

- [test_nova.py 全文] **两条执行路径（Evaluator vs VM）无一致性测试** → 没有任何测试对同一程序同时运行 Evaluator 和 VM 并比较输出，多后端一致性无保障 → 建立"黄金测试"框架，同一组测试用例同时运行两个后端，断言输出一致
  - 追问：如果 GHC 缺少核心语言特性的跨后端一致性测试，能被接受吗？→ **结论：绝对不能。** 生产级编译器必须有跨后端回归测试套件。

#### 中等问题（影响特定场景）

- [grammar.js:612-624 vs parser.py] Tree-sitter 与 Python parser 运算符优先级不一致（Pipe 优先级错位）
- [nova_runtime.c:403-442] nova_list_map/filter/reduce 的函数指针类型不安全
- [nova_runtime.c:1212-1224] JSON 解析器的 \uXXXX 转义解码长度计算不准确
- [nova_runtime.c:1700-1703] nova_http_get/post 中 HTTP 状态码硬编码为 200
- [nova_runtime.c:959] nova_abs_int 在 INT64_MIN 时溢出
- [test_type_system.py 全文] 泛型函数缺乏测试（只有泛型 ADT 测试）

#### 轻微问题（代码质量）

- Tree-sitter grammar 缺少 step 关键字显式声明
- Tree-sitter corpus 测试极少（仅 6 个文件）
- nova_string_new_len 容量计算可能浪费空间
- nova_realloc 不更新 g_alloc_count/g_free_count
- nova_read_file 不处理空文件的微小浪费
- test_runtime.c 中 Map value 测试掩盖了类型混淆 bug
- 测试中大量使用 check_types=False
- 缺少 fuzz 测试、边界值测试、属性测试

#### 测试覆盖率详细分析

**未被测试覆盖的高风险特性：**
- 泛型函数（核心特性，高风险）
- 模式匹配 guard 子句（高风险）
- Map 字面量 {key => value}（高风险）
- 列表模式匹配（中风险）
- 字符类型及操作（中风险）
- HTTP 网络操作（安全敏感，高风险）
- 系统命令执行（安全敏感，高风险）
- 日期时间操作（中风险）
- 目录操作（中风险）

#### 原创性分析

**C 运行时：** 引用计数 + 手动内存管理是经典设计，FNV-1a 哈希、动态数组扩容等都是标准做法。JSON 解析器是常见的递归下降实现。整体属于工程实现而非原创设计。

**Tree-sitter grammar：** 结构参考了 tree-sitter-javascript/rust 的模式，Pipe 运算符的加入是函数式语言常见特性。语法设计上无明显原创性。

**测试组织：** 按分层测试是编译器项目的标准实践，但缺少跨后端一致性测试是重大质量缺口。

---

## 第十五轮架构级建议（优先级排序）

1. **立即修复 Pass 管理器静默吞异常**（P0 安全漏洞——优化器静默失败可能生成错误代码）
2. **立即修复类型检查器 TypeVar 过于宽松问题**（类型系统基本失效，等于没有类型检查）
3. **立即修复 MIR Phi 节点 LIR 降级错误**（整个 IR 优化管道建立在假 SSA 之上）
4. **立即修复 while-in-for 嵌套 CONTINUE 指向错误循环**（结构化编程基石性错误）
5. **立即修复复合模式匹配字面量+绑定混合时栈错位**（函数式语言核心特性的 P0 缺陷）
6. **高优先级：修复 VM 全局变量 mutability 不检查**
7. **高优先级：修复 Evaluator 负步长 range + TryExpr 类型漏洞**
8. **高优先级：修复 Parser 管道优先级错误 + `<-` 非独立 token**
9. **高优先级：修复嵌套容器释放不递归 + Map value 类型混淆**
10. **高优先级：添加 Evaluator-VM 一致性测试框架**
11. **中优先级：统一 `?` 操作符语法（移入后缀循环）**
12. **中优先级：修复 Tree-sitter 与 parser.py 语法不一致**
13. **中优先级：修复 native 后端寄存器分配静默失败**
14. **中优先级：修复错误系统位置信息格式不标准**
15. **长期：重写类型检查核心，实现真正的 HM Algorithm W**
16. **长期：重写 IR 降级链，实现真正的 SSA + Phi 消除**
17. **长期：实现真正的 GC 或循环引用检测**
18. **长期：建立模块命名空间系统，摆脱 from module import * 模式**


---

## [2026-07-15] 第十六轮全面代码审查报告

> **审查方法**：3 轮 × 3 并行 = 9 个 Explore 子代理，逐行审查全部源文件
> **审查标准**：生产级编译器/语言标准（参考 OCaml/Haskell/Elm/F# 最佳实践）
> **审查轮次**：第十六轮

---

### 第十六轮 P0 级问题完整追踪

| # | 问题 | 模块 | 状态 |
|---|------|------|------|
| 1 | CLOSURE 捕获整个帧 | vm.py, compiler.py | 连续十六轮未修 |
| 2 | TypeVar 万能兼容（_types_compatible） | type_checker.py | 连续十六轮未修 |
| 3 | let 多态未实现 | type_checker.py | 连续十六轮未修 |
| 4 | 无 occurs check / 无真正 unification | type_checker.py | 连续十六轮未修 |
| 5 | `\|>` 优先级 parser.py vs grammar.js 矛盾 | parser.py, grammar.js | 连续十六轮未修 |
| 6 | C 运行时 GC 空壳 | nova_runtime.c | 连续十六轮未修 |
| 7 | MIR match 完全退化 | mir_lowering.py | 连续十六轮未修 |
| 8 | LIR Branch/Switch/Match 退化 | lir_lowering.py | 连续十六轮未修 |
| 9 | Evaluator 闭包引用捕获 vs VM 值快照 | evaluator.py vs vm.py | 连续十六轮未修 |
| 10 | STORE_VAR 静默创建全局 | vm.py | 连续十六轮未修 |
| 11 | 嵌套 PatternTuple/PatternList 子模式测试缺失 | compiler.py | 连续十六轮未修 |
| 12 | Native 后端寄存器分配从未调用 | native_backend.py | 连续十六轮未修 |
| 13 | Lambda 闭包自由变量丢失 | mir_lowering.py | 连续十六轮未修 |
| 14 | 所有后端无端到端测试 | tests/ | 连续十六轮未修 |
| 15 | 闭包语义 Evaluator vs VM 根本不一致 | evaluator.py vs vm.py | 持续性问题 |
| 16 | 模块系统路径遍历安全漏洞 | modules.py | 连续十六轮未修 |
| 17 | ListComprehension 降级为空列表 | mir_lowering.py | 连续十六轮未修 |
| 18 | Pipe MIR 降级对未绑定函数名生成空 callee | mir_lowering.py | 连续十六轮未修 |
| 19 | Cranelift 后端 SSA 值不传播 | cranelift_backend.py | 连续十六轮未修 |
| 20 | WASM 后端 Block/Label/Jump 语义完全错误 | wasm_backend.py | 连续十六轮未修 |
| 21 | match guard 位置 parser.py vs grammar.js 不一致 | parser.py, grammar.js | 连续十六轮未修 |
| 22 | grammar.js 不支持 `?` | grammar.js | 连续十六轮未修 |
| 23 | LIR Phi 只取第一个 source | lir_lowering.py | 连续十六轮未修 |
| 24 | C 运行时引用计数不递归（list/map/ADT/closure） | nova_runtime.c | 连续十六轮未修 |
| 25 | 算术运算 bool/int 不分 | vm.py, evaluator.py | **本轮新确认** |
| 26 | MATCH_BIND 作用域污染（失败分支绑定残留） | vm.py | **本轮新确认** |
| 27 | TRY_UNWRAP 仅检查 variant_name 不检查 type_name | vm.py, evaluator.py | **本轮新确认** |
| 28 | BREAK 前向扫描脆弱设计 | vm.py | **本轮新确认** |
| 29 | while 循环 CONTINUE 依赖 JUMP 启发式检测 | vm.py | **本轮新确认** |
| 30 | 错误信息缺少文件名 | errors.py | **本轮新确认** |
| 31 | caret 下划线 off-by-one 错误 | errors.py | **本轮新确认** |
| 32 | AST 节点 span 信息不完整（仅起始位置） | parser.py | **本轮新确认** |
| 33 | Parser 完全无语法错误恢复 | parser.py | **本轮新确认** |

---

## [2026-07-15] VM 虚拟机 (vm.py) 第十六轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | PIPE_CALL 专用指令、MATCH_TEST_* 系列有特色 |
| 可行性 | ⭐⭐⭐ | 核心路径可用；闭包全量捕获、STORE_VAR 全局泄漏影响表达力 |
| 正确性 | ⭐⭐ | 闭包全量捕获、STORE_VAR 全局泄漏、bool/int 不分、MATCH_BIND 作用域污染 |
| 安全性 | ⭐⭐⭐ | 栈下溢保护已到位（_pop），但 BUILD_MAP/FIELD_ACCESS 等仍有原生错误 |
| 一致性 | ⭐⭐ | 与 Evaluator 在闭包语义、作用域、STORE_VAR、range步长等存在差异 |
| 完整性 | ⭐⭐⭐⭐⭐ | 64 个操作码全部有处理路径，无遗漏 |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰，但 _execute_instruction 仍过长（~750行） |
| 性能 | ⭐⭐⭐ | 闭包全量复制、dict 管理循环状态有开销 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [vm.py:859-868] **CLOSURE 捕获整个帧 locals 而非仅自由变量** → 每次创建闭包 dict 浅拷贝所有局部变量，时间 O(n)，阻止 GC 回收不需要的大对象，可变对象在闭包间共享违反不可变性预期 → 编译器分析自由变量，CLOSURE 指令携带变量名列表，VM 仅拷贝指定变量
  - 追问：如果 OCaml 的闭包捕获了整个作用域的 dict 拷贝，性能影响能被接受吗？→ **结论：绝对不能。** 内存使用可膨胀 10-100 倍，是函数式语言实现的核心正确性+性能问题。
  - 历史状态：第 1 轮即发现，经 16 轮仍未修复。

- [vm.py:592-605] **STORE_VAR 在函数体内对未定义变量静默创建全局** → 函数内打错变量名会静默创建/修改全局变量，违背静态作用域原则，与 Evaluator 的 Environment.assign() 语义不一致 → 在函数帧中，STORE_VAR 仅应修改已存在的局部变量；若变量不存在，应报错而非泄漏到全局
  - 追问：如果 OCaml 中未声明变量可以赋值，能被接受吗？→ **结论：绝对不能。**

- [vm.py:608-651] **算术运算不区分 bool 和 int** → Python 的 bool 是 int 子类，True + 1 = 2、False * 5 = 0 会静默通过，而比较运算明确区分了 bool 和非 bool，造成算术运算和比较运算的类型检查标准不一致 → 所有算术运算前检查 isinstance(val, bool)，若为 bool 则抛类型错误
  - 追问：如果 Haskell 的 True + 1 能编译通过还返回 2，能被接受吗？→ **结论：绝对不能。** 类型系统的基本意义就是防止这种隐式转换。

- [vm.py:1137-1145] **MATCH_BIND 失败分支的绑定残留于当前帧** → MATCH_BIND 直接写入 frame.locals，无回滚机制；模式匹配 arm1 部分匹配成功后子模式失败，跳转到 arm2 时，arm1 的绑定仍在局部变量表中，可能误读到前一个 arm 的绑定值 → MATCH_START 时保存当前局部变量快照，MATCH_END 或失败跳转时恢复到快照状态
  - 追问：如果 Haskell 的 case 表达式中，失败分支的变量绑定会泄漏到下一个分支，能被接受吗？→ **结论：绝对不能。** 模式匹配的作用域隔离是基本语义保证。

- [vm.py:1269-1283] **TRY_UNWRAP 仅检查 variant_name 不检查 type_name** → 任何 ADT 只要变体名是 "Some"/"None"/"Ok"/"Err" 就会被当作 Option/Result 处理，自定义 type Foo = Some(Int) | Bar(String) 的 Some(42) 会被错误解包 → 同时检查 val.type_name in ("Option", "Result")
  - 追问：如果 Rust 的 ? 运算符对任何叫 Some 的枚举都起作用，能被接受吗？→ **结论：不能。** 类型安全是 Result/Option 模式的核心价值。

- [vm.py:825-832] **BREAK 无操作数时的前向扫描脆弱且错误** → 向前扫描直到遇到 LOOP_END 或 CONST_UNIT 就停止，CONST_UNIT 极其常见，扫描极可能匹配到循环体内无关位置 → 删除前向扫描 fallback，BREAK 无操作数且不在循环中时直接报错
  - 追问：如果 CPython 的 BREAK 指令找不到循环结尾就瞎跳一个最近的常量，能被接受吗？→ **结论：绝对不能。** 这是定时炸弹级别的设计。

- [vm.py:743-746] **while 循环 CONTINUE 依赖 JUMP 指令启发式检测** → 用"JUMP 向前跳 + 下一条指令是 CONST_UNIT"来判断是否是 while 循环的回跳，极度脆弱，任何前向 JUMP 后恰好有 CONST_UNIT 的情况都会误触发 → 删除 JUMP 中的 while 循环检测逻辑，完全依赖编译器提供的显式操作数
  - 追问：如果 JVM 的 GOTO 指令靠猜测下一条指令来维护循环状态，能被接受吗？→ **结论：绝对不能。** VM 执行应完全基于指令语义，而非启发式猜测。

- [vm.py:913-923] **BUILD_MAP 非哈希键抛 Python 错误而非 Nova 错误** → 传入 list 等不可哈希类型作为键时，抛出 Python 原生 TypeError 而非 RuntimeError_，错误信息和类型都不符合 Nova 语言的错误规范 → 用 try/except 包装键赋值，转换为 RuntimeError_

- [vm.py:943-944] **FIELD_ACCESS 元组索引越界/非整数时崩溃** → 元组索引越界 → Python IndexError，field 不是数字字符串 → Python ValueError；对比 INDEX 指令有完整的 try/except 错误处理，FIELD_ACCESS 明显遗漏 → 添加 try/except 捕获 IndexError/ValueError，转换为 RuntimeError_

- [vm.py:358-363] **内置函数无超额参数检查** → 所有 arity > 0 的内置函数都可以传入任意多的参数，多余参数被 Python *args 静默忽略，例如 print(1, 2, 3) 只打印 1 → 添加 if fn.arity > 0 and len(args) > fn.arity 检查
  - 追问：如果 Haskell 的内置函数传多了参数不报错而是静默丢弃，能被接受吗？→ **结论：不能。** 参数数量不匹配是基本的调用约定错误。

- [vm.py:993] **FOR_ITER range 步长为 0 时与 Evaluator 语义不一致** → VM 中 step == 0 时直接退出（返回空列表），而 Evaluator 报错 "range 步长不能为 0" → VM 应在 step == 0 时抛错，与 Evaluator 对齐

- [vm.py:163-170] **迭代状态异常退出时 _for_iters/_while_loops 不清理** → for 循环体中发生 RuntimeError_ 异常时，_for_iters 栈顶条目、_range_index/_list_index 对应条目不会被清理，异常被外部捕获后继续使用 VM 时循环状态被污染 → FOR_ITER 注册的循环状态应与当前帧关联，帧弹出时清理
  - 追问：如果 JVM 异常退出后局部变量表不清理，导致下次方法调用看到旧值，能被接受吗？→ **结论：不能。** 这是基本的执行隔离要求。

- [vm.py:572-576] **LOAD_CONST 无边界检查** → 索引越界时抛 Python IndexError 而非 Nova 运行时错误 → 添加边界检查

#### 中等问题（影响特定场景）

- [vm.py:467-471] **RETURN 在 _execute_function 和 _execute_instruction 中重复处理** → 两套逻辑一套死码一套活码，维护成本高
- [vm.py:134,140,436] **Frame.ip 死字段** → 设置但从未读取
- [vm.py:713-728] **AND/OR 操作码死代码** → 编译器用 DUP + JUMP 实现短路，从不生成 AND/OR 操作码；VM 中的实现是非短路版本，若未来被误启用会导致严重语义错误
- [vm.py:239-257] **内置函数缺少类型检查** → filter/map/head/tail/str_len/list_length 等无参数类型校验
- [vm.py:653-660] **CONCAT 仅支持字符串，不支持列表拼接**
- [vm.py:974-1059] **FOR_ITER 仅支持 range 和 list，不支持 string/tuple 迭代**
- [vm.py:541-1294] **_execute_instruction 方法过长（约 750 行 if-elif 链）** → 可读性差、维护成本高
- [vm.py:181] **read_line 与 Evaluator 不一致，无 EOF 处理** → VM 用 lambda 带死代码，input() 遇 EOF 抛 EOFError 未被捕获
- [vm.py:1062-1065,1199-1202] **MATCH_START/MATCH_END 是空操作** → 标记指令无实际功能
- [vm.py:204-218] **数学函数非数值参数抛 Python 错误** → 应转换为 Nova RuntimeError_
- [vm.py:220-223] **_to_float 命名误导** → 实际是 int_to_float，非通用转换
- [vm.py:100-109] **NovaPartialBuiltin 与 BuiltinFn 部分应用不一致** → 两套部分应用机制，代码重复

#### 轻微问题（代码质量）

- [vm.py:30-46] **UNIT 单例类与 Evaluator 不同（UNIT_TYPE vs _UnitValue）**
- [vm.py:65-69] **NovaADTValue.__eq__ 不比较 field_names**
- [vm.py:330] **json_stringify dict 键强制转 str**
- [vm.py:632] **DIV 整数除法用 floor 除法，负数行为与 C 风格不同** → 需明确文档化
- [vm.py:1285-1289] **LOOP 指令功能与 JUMP 完全相同**
- [vm.py:156,178-218] **globals 字典包含内置函数，与用户定义的全局变量混在一起**

#### 原创性分析

**Nova 特色**：
1. PIPE_CALL 专用管道指令——为管道操作定制的指令，管道值作为最后一个参数传入函数
2. MATCH_START/MATCH_END 标记指令——为模式匹配提供显式边界标记（当前是空操作，但设计意图好）
3. TRY_UNWRAP 统一 Option/Result 解包——用单条指令同时处理 Option 和 Result 的 ? 运算符语义
4. ADT 原生指令集——MAKE_ADT/REGISTER_CTOR/MATCH_CONSTRUCTOR 将代数数据类型操作内建为 VM 原语
5. FOR_ITER + LOOP_END 双指令循环——迭代器状态在 VM 内部维护

**参考已有**：基本栈机架构参考 CPython/JVM，闭包+调用帧模型是标准函数式语言实现方式。

#### Evaluator vs VM 对比表
| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| 闭包捕获机制 | Environment 引用链（引用语义） | dict 浅拷贝（值语义） | ❌ 不一致 |
| 闭包捕获范围 | 整个环境链（所有父作用域） | 仅当前帧 locals | ❌ 不一致 |
| 递归深度保护 | _call_depth + MAX_CALL_DEPTH | call_stack 长度检查 | ✅ 一致 |
| read_line EOF 处理 | 有 try/except EOFError → "" | 无处理 → 抛 Python 错误 | ❌ 不一致 |
| range 步长为 0 | 报错 "步长不能为 0" | 静默返回空列表 | ❌ 不一致 |
| 赋值语义 | 沿作用域链向上找可变绑定 | 仅当前帧或直接写全局 | ❌ 不一致（严重） |
| 模式匹配作用域 | 每个 arm 新 child_env，失败不污染 | 失败分支 bindings 残留 | ❌ 不一致（严重） |
| bool 参与算术运算 | 未检查（True+1=2） | 未检查（True+1=2） | ✅ 都错 |
| TRY_UNWRAP 类型检查 | 仅 variant_name | 仅 variant_name | ✅ 都错 |
| for 循环可迭代类型 | 依赖 items = eval(iterable) | 仅 range 和 list | ❌ 不一致 |
| 基本算术运算 | 正确 | 正确 | ✅ 一致 |
| ADT 构造/解构 | 正确 | 正确 | ✅ 一致 |
| 管道操作 | 正确（最后参数） | 正确（最后参数） | ✅ 一致 |
| Unit 值 bool 语义 | __bool__ = False | __bool__ = False | ✅ 已修复 |


---

## [2026-07-15] 编译器 (compiler.py) 第十六轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | PIPE_CALL 专用指令、MATCH_START/END 标记、ADT 原生指令 |
| 可行性 | ⭐⭐⭐⭐ | 编译器-VM 协作清晰，能正确执行大部分程序 |
| 正确性 | ⭐⭐⭐ | 嵌套模式匹配是严重 bug；闭包全量捕获；Import 冲突检测不全 |
| 安全性 | ⭐⭐⭐ | 栈溢出保护有，但无运行时类型安全检查 |
| 一致性 | ⭐⭐⭐⭐ | 栈布局编译器与 VM 基本一致；短路求值正确 |
| 完整性 | ⭐⭐⭐⭐ | AST 覆盖完整；所有指令有 VM 处理 |
| 工程质量 | ⭐⭐⭐ | 存在死代码（旧方法、AND/OR 指令）、无意义 if/else |
| 性能 | ⭐⭐⭐ | 闭包全量复制、循环状态用 dict |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [compiler.py:836-861] **嵌套构造器/元组/列表模式的子模式测试栈错位** → _compile_pattern_test_with_fail 处理多元素模式时，按正序递归处理子模式，但 VM 压栈顺序是 reversed 的，导致子模式测试的是错位的元素 → 递归处理子模式时按 reversed 顺序遍历，与 VM 压栈顺序一致
  - 追问：如果 Haskell GHC 编译器跳过嵌套 Pattern 的测试代码生成，能被接受吗？→ **结论：绝对不能。** 模式匹配是函数式语言核心特性，嵌套模式错位是 P0 级缺陷。

- [compiler.py:866-904] **模式匹配 extract_and_bind 同样存在子模式顺序错位** → 与上面同源，按正序递归处理子模式，但 VM 压栈顺序是 reversed 的，导致绑定到错误的值 → 子模式递归以 reversed 顺序遍历
  - 追问：如果 OCaml 的模式匹配变量绑定错位，能被接受吗？→ **结论：绝对不能。** 这是模式匹配的基本正确性问题。

- [compiler.py:402,682] **闭包全量捕获当前帧所有局部变量** → CLOSURE 指令不含捕获列表，由 VM 在运行时全量捕获；空间浪费严重，意外保留引用，语义不精确 → 编译器实现自由变量分析，通过 CLOSURE 指令传递精确的捕获列表
  - 追问：如果 OCaml 的闭包捕获了整个作用域的所有变量，能被接受吗？→ **结论：不能。** 闭包转换是编译流程核心 pass，精确计算自由变量是基本要求。

- [compiler.py:362-368] **Import 内联的名称冲突检测不完整** → 只检查 functions 和 _builtin_names，不检查已编译的 LetBinding/MutBinding 和 ADT 构造器；导入的模块可以静默覆盖当前模块中已有的 let/mut 绑定 → 维护统一的"已定义名称"集合，import 内联时检查所有声明类型的名称冲突
  - 追问：生产级编译器的模块系统名称冲突检测如此不完整，能被接受吗？→ **结论：不能。** OCaml 的模块系统会对所有名称做冲突检查。

- [compiler.py:1017,1034] **FOR_ITER 回填方式错误——使用 patch_jump 回填单操作数** → patch_jump 将整条指令替换为单操作数指令，与 FOR_ITER 语义完全不同（FOR_ITER 是"迭代一步，耗尽则跳"），当前能工作只是因为 FOR_ITER 恰好只有一个操作数 → 增加专用的 patch_for_iter_fail 方法
  - 追问：成熟编译器中这种"碰巧能用"的设计能被接受吗？→ **结论：不能。** 指令回填必须按指令类型精确处理，不能依赖操作数数量巧合。

- [compiler.py:770-777] **_compile_match 中 fail_cleanup_pos 的计算依赖 next_arm_start** → 变量名与其值的语义不一致，代码结构让人困惑，容易引入 bug → 拆分变量，用 fail_cleanup_pos 和 next_arm_pos 两个独立变量

#### 中等问题（影响特定场景）

- [compiler.py:906-970] **_compile_pattern_test 和 _compile_pattern_bindings 是死代码** → 从未被调用，增加维护成本
- [compiler.py:420-421] **CharLiteral 编译为 CONST_STRING** → 运行时无法区分单字符字符串和 char 值
- [compiler.py:535-557] **BinaryOp 中 &&/|| 栈注释与实际行为有微妙差异** → false 分支栈上保留的是 left 值而不是"结果值"
- [compiler.py:597-602] **管道表达式中 builtin 与普通函数的处理完全相同** → 两个分支代码完全一样，失去了 CALL_BUILTIN 的优化机会
- [compiler.py:431-434] **Identifier("None") 特殊处理会与变量名冲突** → None 被硬编码为 ADT 构造器，用户无法定义名为 None 的变量
- [compiler.py:491-495] **while 循环的 BREAK 操作数使用 patch_jump** → 与 FOR_ITER 同样的"巧合能工作"问题
- [compiler.py:1020,1108] **for 循环中循环变量被标记为 mutable** → 函数式语言中 for 循环的每次迭代应当创建新的绑定，而非修改同一个可变变量
- [compiler.py:304-307] **顶层表达式声明会 POP 掉值** → 没有 main 函数的脚本，最后一个表达式的值被丢弃，与大多数脚本语言直觉不符

#### 轻微问题（代码质量）

- [compiler.py:168-177] **add_const 使用 list.index() 做去重，时间复杂度 O(n)**
- [compiler.py:48] **LOAD_CONST 操作码定义了但从未使用**
- [compiler.py:66-67] **Op.AND / Op.OR 指令是死代码**
- [compiler.py:882-946] **旧版模式匹配方法从未被调用**
- [compiler.py:924-939] **列表推导式 filter_cond 被完全忽略** → 历史问题，已确认 16 轮未修
- [compiler.py:80 vs 375] **CLOSURE 指令的 code_key 操作数定义但未使用**
- [compiler.py:607-608] **pipe_call 的栈布局与注释不一致**
- [compiler.py:844-849] **Block 中 BreakExpr/ContinueExpr 后多余的 POP 导致栈错位** → 历史问题

#### 原创性分析

**Nova 特色**：
1. MATCH_* 系列指令的"测试即弹出"设计——将模式匹配的"测试"和"解构"合并到一条指令中
2. FOR_ITER + LOOP_END 的循环抽象——将 for 循环的迭代控制和结果收集封装为两条指令
3. TRY_UNWRAP 的早期返回机制——`?` 操作符直接通过 VM 层面的早期返回实现
4. PIPE_CALL 指令——将管道操作直接编码为字节码指令
5. 全量捕获闭包——简单但低效，在现代函数式语言编译器中很少见

**参考已有**：基本栈机结构参考 CPython/JVM；跳转回填参考标准编译器教材。

---

## [2026-07-15] 求值器 (evaluator.py) 第十六轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐⭐ | 完整的函数式语言解释器，支持闭包/ADT/模式匹配/管道/柯里化 |
| 可行性 | ⭐⭐⭐⭐ | 核心功能完整可用 |
| 正确性 | ⭐⭐⭐ | 闭包语义与 VM 根本不一致，短路运算无类型检查，算术运算无类型检查 |
| 安全性 | ⭐⭐⭐⭐ | 递归深度保护到位，但算术运算类型安全缺失 |
| 一致性 | ⭐⭐ | 与 VM 在闭包、作用域、STORE_VAR、比较运算等多处不一致 |
| 完整性 | ⭐⭐⭐⭐⭐ | AST 覆盖 100%，模式匹配覆盖所有类型+嵌套+守卫 |
| 工程质量 | ⭐⭐⭐ | eval_decl 重复代码、self.env 切换模式脆弱 |
| 性能 | ⭐⭐⭐ | Python 解释器性能受限 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [evaluator.py:49,735-740,502-508] **闭包引用捕获 vs VM 值快照不一致** → Evaluator 的 NovaClosure 捕获 Environment 对象引用（引用语义），VM 的 NovaClosure.captured_vars 是 dict 值快照（值语义）；同一程序在 Evaluator 和 VM 下行为不一致 → 统一闭包模型，要么都用引用语义（实现 upvalue 机制），要么都用值快照
  - 追问：如果 GHC 的两个执行后端语义不一致，能被接受吗？→ **结论：绝对不能。** 闭包语义是函数式语言的核心，属于 P0 级缺陷。

- [evaluator.py:872-882] **短路逻辑运算 &&/|| 不做类型检查** → 直接用 if not left: 判断，没有检查 left 是否为 bool 类型；Python 中 0、""、[]、None 都是 falsy，会被当作 false 处理 → 在短路求值前添加 isinstance(left, bool) 检查，与 if/while 保持一致
  - 追问：如果是成熟语言的解释器，逻辑运算符不检查类型能被接受吗？→ **结论：不能。** ML 家族语言的逻辑运算符严格要求 Bool 类型。

- [evaluator.py:887-900] **算术运算完全无类型检查** → +、-、*、/、% 等直接委托给 Python 运算符，没有类型检查；True + 1 → 2，"hello" * 3 → "hellohellohello" → 对所有算术运算符添加类型检查，确保操作数类型匹配
  - 追问：如果 OCaml 的解释器允许 True + 1 还返回 2，能被接受吗？→ **结论：绝对不能。** 类型安全的基本防线。

- [evaluator.py:716-725] **TryExpr (? 操作符) 在非函数上下文中使用会用 ReturnSignal 炸出顶层** → TryExpr 抛出 ReturnSignal(val)，依赖 _call_fn 捕获；但如果 ? 出现在顶层代码或循环体内但不在函数中，ReturnSignal 不会被捕获，直接导致程序崩溃 → 在 eval_program 或 eval_expr 顶层入口处捕获 ReturnSignal，给出明确的错误信息

- [evaluator.py:942,995] **ForExpr 和 ListComprehension 中 iterable 用 tuple hack 表示范围** → expr.iterable 应该是 AST 节点，但范围形式被构造成 tuple ("range", start, end, step) 而非 proper AST 节点，破坏了类型安全性和可维护性 → 定义 proper 的 AST 节点（如 RangeExpr）来表示范围

- [evaluator.py:975-990] **while 循环体不创建子作用域，变量泄漏到外部** → 直接在当前环境中求值循环体 body，没有创建子作用域；body 中的 let/mut 可能泄漏到外部 → 无论 body 是否为 Block，循环结构本身应保证一致的作用域语义

#### 中等问题（影响特定场景）

- [evaluator.py:571-626] **eval_decl 与 _collect_decl + _eval_decl_body 代码重复**
- [evaluator.py:208] **_builtin_filter 用 is True 严格判断谓词返回值** → 谓词返回非布尔值时静默当作 false 过滤掉，而不是报错
- [evaluator.py:851-864] **IndexExpr 对字符串索引行为不一致** → Python 字符串索引返回长度为 1 的字符串，而 Nova 应该有 Char 类型
- [evaluator.py:833-847] **FieldAccess 对 ADT 值同时支持索引访问和名称访问，优先级不清** → 先尝试 int(expr.field) 做索引访问，失败则按名称访问，字段名叫 "0" 时永远无法通过名称访问
- [evaluator.py:797-798] **MapExpr 的键直接用 Python 值作 dict key，不支持不可哈希类型**
- [evaluator.py:443-447] **递归深度检查只在 _call_fn 中，非函数递归无保护**
- [evaluator.py:287-290] **JSON 对象转换为 Python dict，但键类型是 Python 字符串而非 Nova String 值**
- [evaluator.py:337-338] **BreakSignal 携带 value 但 Evaluator 未使用**

#### 轻微问题（代码质量）

- [evaluator.py:106] **UNIT_VALUE 与 VM 的 UNIT 命名不一致**
- [evaluator.py:59-82] **NovaADTValue 在 evaluator 和 vm 中重复定义**
- [evaluator.py:671-867] **eval_expr 是超长 if-elif 链，无结构化分发**
- [evaluator.py:384-404] **_format_value 对 dict 类型无格式化处理**
- [evaluator.py:219-227] **_builtin_head/_builtin_tail 中 None variant 的 field_names 不一致**
- [evaluator.py:214-215] **_builtin_sum 对空列表返回 0（int），但列表元素可能是 float**
- [evaluator.py:335-378] **数学内置函数返回 float 即使输入是 int**
- [evaluator.py:684-685] **CharLiteral 求值为 Python str，与 String 类型无法区分**

#### 原创性分析

**亮点**：
1. 两遍扫描的程序求值——正确支持了前向引用和相互递归的函数定义
2. 模式匹配实现完整——支持所有 10 种 Pattern 类型，嵌套模式递归匹配正确，守卫条件有独立作用域
3. 部分应用/柯里化——_call_fn 中对参数不足的情况正确返回新闭包
4. 比较运算类型安全——==/!= 对 bool 和非 bool 做了隔离，</> 等对跨类型比较抛错

**不足**：类型安全不彻底（算术运算完全依赖 Python）、闭包语义与 VM 不一致、AST 设计不纯。


---

## [2026-07-15] 类型检查器 (type_checker.py) 第十六轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 类型系统正确性 | ⭐⭐ | TypeVar 万能兼容导致核心 soundness 崩坏，无真正 unification |
| 类型推断能力 | ⭐⭐ | 非 Algorithm W，是"带通配符的类型检查"，推断能力极弱 |
| 模式匹配检查 | ⭐⭐⭐ | 所有 Pattern 类型有覆盖，但构造器模式缺少主题类型校验 |
| 错误恢复能力 | ⭐⭐⭐ | ErrorCollector 框架存在，但部分路径绕过 |
| 泛型支持 | ⭐⭐⭐ | ADT 类型参数比较正确，但函数级泛型依赖 TypeVar 通配符机制 |
| 递归类型处理 | ⭐⭐ | 无专门处理，靠结构比较侥幸工作 |
| 代码质量与架构 | ⭐⭐⭐ | 结构清晰，两遍扫描设计合理，但核心算法有根本缺陷 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [type_checker.py:1325] **TypeVar 万能兼容——类型系统 soundness 核心崩坏** → `if isinstance(a, TypeVar) or isinstance(b, TypeVar): return True` 使任何包含 TypeVar 的类型比较都返回 True；未标注类型的函数参数可以接受任意类型的实参，类型检查形同虚设 → 实现真正的合一算法，用 union-find 管理类型变量等价类
  - 追问：如果是 OCaml/Haskell/GHC 的类型检查器，这个 bug 能被接受吗？→ **结论：绝对不能。** 这相当于把类型系统降级为"有标注才检查，没标注就全放过"的可选类型系统。

- [type_checker.py:1195-1215] **无真正的合一（Unification）算法** → _collect_type_bindings 是单向模式匹配（actual → expected），不是双向合一；无法处理两侧都是 TypeVar 的情况，也无法处理 actual 含 TypeVar 但 expected 是具体类型的情况 → 实现基于 union-find 的高效合一算法，支持 occurs check、递归类型检测
  - 追问：成熟语言的类型检查器能没有真正的合一算法吗？→ **结论：不能。** 合一（unification）是 HM 类型推断的基石。

- [type_checker.py:779-789] **无 let 多态（Let-Polymorphism）** → let 绑定直接将推断类型存入环境，没有泛化（generalization）步骤；let id = fun x -> x in id 1 + id "a" 之所以能通过，是因为 TypeVar 是万能兼容的，而非 id 被泛化为 forall a. a -> a → 引入类型方案（type scheme）概念 Forall [vars] ty，let 绑定时泛化自由变量，使用时实例化新鲜副本
  - 追问：没有 let 多态能叫 HM 类型系统吗？→ **结论：不能。** let-polymorphism 是 Hindley-Milner 的定义性特征之一。

- [type_checker.py 全文] **无 Occurs Check — 潜在无限类型风险** → 整个文件无 occurs check 实现；虽然当前由于 TypeVar 是通配符不会产生无限类型，但一旦修复合一算法，缺少 occurs check 会导致类型检查器可能因用户输入而挂起或崩溃 → 在合一算法中添加 occurs check，检测类型变量是否出现在待合一的类型中
  - 追问：生产级类型检查器能没有 occurs check 吗？→ **结论：绝对不能。** 这是 Robinson 合一算法的标准组成部分。

- [type_checker.py:543-563] **函数返回类型推断后不更新环境** → _check_decl_body 中检查 FnDef 函数体后，仅在有 return_type 标注时报错比较，但从不更新环境中函数的返回类型；所有未标注返回类型的函数，其返回值在类型系统中等同于 dyn → 函数体检查完成后，用推断出的 body_type 与函数签名中的返回类型进行合一

- [type_checker.py:740-750] **函数调用 TypeVar 类型值直接放行的 duck typing** → 当被调用者类型是 TypeVar 时，直接允许调用，不做任何检查，返回一个新的 TypeVar；完全破坏了类型安全 → 如果 callee 类型是 TypeVar 且无法确定是函数类型，报告类型错误并返回 ERROR_TYPE
  - 追问：生产级静态类型系统能允许对未知类型的值随意调用吗？→ **结论：不能。**

- [type_checker.py:1043-1076] **PatternConstructor 不校验主题类型是否为对应 ADT** → 在 _check_pattern 中，PatternInt/PatternFloat 等都检查了主题类型兼容，但 PatternConstructor 完全没有检查主题类型是否是对应的 ADT；对一个 Int 类型的值做 match x { Some(y) -> ... } 不会报错 → 在 PatternConstructor 分支开头，验证 subject_type 是对应 ADT 类型

- [type_checker.py:953,981] **for 循环/列表推导的循环变量是万能 TypeVar** → 循环变量的类型被设为 TypeVar，而不是从可迭代对象推断；for x in [1, 2, 3] { x ++ "hello" } 会通过类型检查 → 从 iterable 类型（ListType 的 elem_type，或 range 情况的 INT_T）推断循环变量类型

#### 中等问题（影响特定场景）

- [type_checker.py:755-770] **PipeExpr 类型检查完全是启发式的** → 既不绑定也不校验，只要一个兼容就通过
- [type_checker.py:791-794] **MutBinding 表达式内不检查类型注解** → LetBinding 有类型注解检查，但 MutBinding 没有
- [type_checker.py:744-749] **TypeVar 函数调用错误绕过 _report_error** → 直接调用 error_collector.add() 而非 _report_error()，行为不一致
- [type_checker.py:350] **json_parse 返回 TypeVar——本质上是动态类型逃逸口**
- [type_checker.py:613,631-632] **空列表/空 Map 的元素类型是 TypeVar 通配符**
- [type_checker.py:925-937] **TryExpr（? 操作符）不校验上下文类型**
- [type_checker.py:445-450] **顶层 let/mut 绑定两遍扫描的类型占位问题**
- [type_checker.py:677-689] **MatchExpr 无穷尽性检查**
- [type_checker.py 全文] **无冗余/不可达模式检查**
- [type_checker.py:1101-1110] **二元操作符不支持隐式 Int→Float 转换**

#### 轻微问题（代码质量）

- [type_checker.py:169-174] **TypeVar._counter 是全局类变量，跨实例共享**
- [type_checker.py:1144-1149] **逻辑操作符错误消息硬编码为 '&&'**
- [type_checker.py:1301-1319] **_expand_alias 不展开别名内部的 TypeIdentifier 引用**
- [type_checker.py:431] **ADT 构造函数字段名在比较时被忽略**
- [type_checker.py:891-892] **FieldAccess 对非元组/ADT 类型不检查是否有 TypeVar**

#### 原创性分析

**架构设计（有一定思考）**：两遍扫描支持前向引用和相互递归，ErrorType 单例模式，TypeEnv 父子环境链，ADT 变体信息与类型参数分离存储。

**核心算法（无原创性，且有根本缺陷）**：声称实现"简化的 Hindley-Milner"，但缺少 HM 的三大支柱：合一（unification）、泛化（generalization）、实例化（instantiation）。TypeVar 被当作万能通配符使用，这不是"简化"而是"错误"。

**历史问题修复评估**：
- ✅ ADTType.__eq__ 比较类型参数：已修复
- ❌ TypeVar 万能兼容：仍然存在
- ❌ let 多态未实现：仍然存在
- ❌ 无真正 unification：仍然存在
- ❌ 无 occurs check：仍然存在

---

## [2026-07-15] 词法/语法分析器 (lexer.py + parser.py) 第十六轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| Token 覆盖完整性 | ⭐⭐⭐⭐ | 基本覆盖所有语法元素，但有死代码 token |
| 词法错误恢复 | ⭐⭐⭐ | 有基本恢复，但错误非结构化，且不影响解析流程 |
| 语法错误恢复 | ⭐ | 完全没有错误恢复，遇错即停 |
| 运算符优先级正确性 | ⭐⭐ | 管道操作符优先级与 grammar.js 严重不一致 |
| 结合性正确性 | ⭐⭐⭐⭐ | 大部分运算符结合性正确 |
| 语法歧义处理 | ⭐⭐⭐ | if-then-else 无悬挂歧义，但 match 分支隐式分隔有风险 |
| 错误位置准确性 | ⭐ | 绝大多数 AST 节点 span 仅含起始 token，非完整范围 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [parser.py:672-678] **管道操作符优先级严重错误** → _parse_comparison_expr 调用 _parse_pipe 获取操作数，意味着管道操作符优先级高于比较操作符；与 grammar.js 定义完全矛盾，与函数式语言的常规直觉相悖 → 调整优先级链，将 _parse_pipe 放在 _parse_or_expr 之下（最低优先级之一）
  - 追问：如果是 GCC/Clang 的前端，运算符优先级不一致的 bug 能被接受吗？→ **结论：绝对不能。** 优先级错误会导致用户代码被静默地错误解析，是编译器前端最严重的错误类别之一。

- [parser.py:534-536] vs [grammar.js:402] **match arm guard 位置语法不一致** → parser.py: pattern if cond -> body（guard 在 -> 之前）；grammar.js: pattern -> body if cond（guard 在 -> 之后）；两种语法完全不兼容 → 明确规范，统一两者。建议 guard 在 -> 之前（parser.py 的方式）
  - 追问：如果是 GCC/Clang 的前端，语法定义不一致能被接受吗？→ **结论：绝对不能。** 语法定义的不一致意味着语言规范本身不明确。

- [parser.py 全局] **AST 节点位置信息严重不完整** → 几乎所有 AST 节点的 span 都只包含起始关键字或操作符的位置，而非整个表达式/语句的完整范围；FnCall 的 span 只是右括号位置，BinaryOp 的 span 只是操作符位置 → 为每个 AST 节点计算完整的 span，从第一个 token 的起始位置到最后一个 token 的结束位置
  - 追问：如果是 GCC/Clang 的前端，AST 节点位置信息不准确能被接受吗？→ **结论：绝对不能。** 位置信息不准确会严重影响诊断质量，是生产级编译器的硬性要求。

- [parser.py 全局] **Parser 完全没有语法错误恢复** → 解析器遇到第一个语法错误就抛出 ParseError 并终止，没有任何错误恢复机制 → 实现基本的 panic mode 错误恢复，在同步 token（如 ;、}、换行后的关键字）处重新同步解析流程
  - 追问：如果是 GCC/Clang 的前端，完全没有错误恢复能被接受吗？→ **结论：不能。** 现代编译器前端的基本要求就是"遇错不止"。

- [lexer.py:254-267,454-458] **词法错误不影响解析流程** → 词法错误只存储在 self.errors 中并打印到 stderr，但解析器从不检查 lexer 是否有错误，直接继续解析；错误是字符串而非结构化对象 → 使用 ErrorCollector 统一收集词法错误，错误应为 LexerError 对象而非字符串

- [grammar.js:466-470] vs [parser.py:386-391] **赋值表达式设计不一致** → grammar.js 中 assignment_expr 是一个表达式，优先级最低；parser.py 中赋值只在 _parse_block 中通过前瞻检测特殊处理，不是真正的表达式 → 明确设计决策，统一两者

#### 中等问题（影响特定场景）

- [lexer.py:91, parser.py:804-806] **UNIT token 是死代码**
- [lexer.py:88] **PIPE_VARIANT token 是死代码**
- [lexer.py:13,155-160] **_make_error 方法和 LexerError import 是死代码**
- [parser.py:764-767] **? 操作符不支持链式** → 在 postfix 循环之外单独处理一次
- [parser.py:464-466] **<- 左箭头没有专用 token** → LT + MINUS 手动组合
- [lexer.py, grammar.js] **缺少块注释支持** → 无 /* */
- [lexer.py:202-221] **数字字面量功能不足** → 缺科学计数法、十六进制、八进制、二进制、数字分隔符
- [lexer.py:240-251] **字符串转义序列不完整** → 缺 \0、\xNN、\u{NNNN}、无效转义错误处理
- [parser.py:522] **match 分支隐式分隔可能导致错误恢复差**
- [parser.py:463,474] **ForExpr.iterable 类型不一致** → 有时是表达式，有时是 tuple

#### 轻微问题（代码质量）

- [lexer.py:168-173] **_peek_ahead 参数命名误导**
- [parser.py:252-273] **_parse_variant_def 中使用位置回溯**
- [parser.py:844-884] **_is_map_literal 前瞻扫描的健壮性**
- [lexer.py:284-298] **缺少字符字面量的 Unicode 转义支持**
- [parser.py:57-62] **_advance 在 EOF 的静默处理**
- [parser.py:367-370] **_parse_expression_statement 是多余包装**

#### parser.py vs grammar.js 对比表
| 特性 | parser.py | grammar.js | 一致？ |
|------|-----------|------------|--------|
| 管道优先级 | 高于比较（第8级） | 最低之一（第2级） | ❌ 严重不一致 |
| match guard 位置 | pat if cond -> body（-> 前） | pat -> body if cond（-> 后） | ❌ 严重不一致 |
| 赋值表达式 | 仅在 block 中特殊处理 | 是最低优先级表达式 | ❌ 不一致 |
| 泛型类型参数 | 支持 type Option[T] { ... } | 不支持 | ❌ 不一致 |
| <- token | LT + MINUS 组合 | 单个 token <- | ❌ 不一致 |
| match 分支分隔 | 逗号或隐式换行 | 逗号分隔 | ⚠️ 部分不一致 |
| ADT 变体分隔 | \| 或换行 | \| 分隔 | ⚠️ 部分不一致 |
| 管道结合性 | 左结合 | 左结合 | ✅ 一致 |
| 算术优先级 | 正确 | 正确 | ✅ 一致 |
| 索引表达式 | 支持（后缀循环中） | 支持（PREC.CALL） | ✅ 一致 |
| 函数调用 | 支持（后缀循环中） | 支持（PREC.CALL） | ✅ 一致 |
| if-then-else | if c then t else e | if c then t else e | ✅ 一致 |
| Lambda 语法 | \|params\| body | \|params\| body | ✅ 一致 |
| ? 操作符 | 支持 | 不支持 | ❌ 不一致 |


---

## [2026-07-15] 错误处理 + 模块系统 + 环境 第十六轮审查报告

### 总体评分

#### errors.py
| 维度 | 评分 | 说明 |
|------|------|------|
| 错误格式化质量 | ⭐⭐⭐ | 有基本的上下文显示，但缺少文件名、错误码，caret 有 off-by-one 问题 |
| 源码上下文完整性 | ⭐⭐ | 仅显示前后各1行，无文件名 |
| 错误分类完整性 | ⭐⭐⭐ | 4大类（词法/语法/类型/运行时），但缺少细分错误码 |
| 错误恢复能力 | ⭐⭐ | ErrorCollector 存在但集成度低 |
| ANSI 颜色支持 | ⭐⭐⭐ | 支持 NO_COLOR，但不支持 CLICOLOR/CLICOLOR_FORCE 标准 |
| 可维护性 | ⭐⭐⭐ | 结构清晰但有冗余 |
| 生产就绪度 | ⭐⭐ | 缺少错误码系统、文件名、行号列号一致性校验 |

#### modules.py
| 维度 | 评分 | 说明 |
|------|------|------|
| 路径解析完整性 | ⭐⭐⭐ | 支持绝对/相对/包导入，但相对路径基准逻辑有歧义 |
| 循环导入检测 | ⭐⭐ | 基于加载栈检测，但无部分加载状态 |
| 路径遍历安全 | ⭐ | **严重安全漏洞**：无沙箱限制，可直接读取任意文件 |
| 缓存机制正确性 | ⭐⭐⭐ | 基本缓存可用，但缓存键仅用 file_path |
| export 语义正确性 | ⭐⭐ | 仅收集 ExportDecl 的 name 字符串，不校验导出名称是否真实存在 |
| 可维护性 | ⭐⭐⭐ | 结构清晰，但全局单例模式有状态污染风险 |
| 生产就绪度 | ⭐⭐ | 缺少命名空间导入、重导出、选择性导入等关键特性 |

#### environment.py
| 维度 | 评分 | 说明 |
|------|------|------|
| 作用域链正确性 | ⭐⭐⭐⭐ | 基本实现正确，查找逻辑清晰 |
| 闭包环境生命周期 | ⭐⭐ | 闭包持有完整环境引用（含父链），存在内存泄漏风险 |
| 不可变性区分 | ⭐⭐⭐ | mutable/immutable 区分正确，但 assign 错误信息不够精确 |
| 环境快照/恢复 | ⭐ | **完全缺失**，无快照、无事务回滚能力 |
| Evaluator/VM 一致性 | ⭐ | **严重不一致**：Evaluator 用 Environment 作用域链，VM 用扁平 locals + captured_vars 字典 |
| 可维护性 | ⭐⭐⭐⭐ | 代码简洁，职责单一 |
| 生产就绪度 | ⭐⭐ | 缺少阴影检测、作用域调试信息 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [modules.py:118-121] **路径遍历安全漏洞——任意文件读取** → ModuleResolver.resolve() 对绝对路径直接返回，对相对路径仅做 os.path.abspath 拼接，完全没有沙箱边界检查；攻击者可以通过 import "../../../etc/passwd" 读取系统任意文件 → 实现 _is_within_allowed_paths() 沙箱检查
  - 追问：如果 Rust 编译器允许 mod "../../etc/passwd" 读取任意系统文件，能被接受吗？→ **结论：绝对不能。** 这是 P0 级安全漏洞。

- [environment.py:23-73] vs [vm.py:75-84,405-420] **Evaluator 与 VM 的环境语义严重不一致** → Evaluator 使用 Environment 链式作用域实现闭包（引用语义），VM 的 NovaClosure 使用扁平字典 captured_vars（值拷贝语义）；同一程序在 Evaluator 和 VM 中运行结果可能不同 → 统一闭包模型
  - 追问：Rust 编译器的 MIR 和代码生成后端必须保证语义一致吗？→ **结论：是的，必须一致。** 同一程序在不同后端运行结果不同是 P0 级正确性缺陷。

- [errors.py:186-191] **错误信息缺少文件名——无法定位错误源** → _format_with_context() 方法的位置信息只有行号和列号，完全没有文件名；在多文件项目中，用户看到错误却不知道是哪个文件的错误 → NovaError 增加 file_path 字段，位置格式改为 文件名:行号:列号
  - 追问：Rust 编译器错误信息如果没有文件名，能被接受吗？→ **结论：绝对不能。** 这是 P0 级可用性缺陷。

- [errors.py:271-274] **caret 下划线计算有 off-by-one 错误** → _compute_underline 方法中 end_col - start_col 少一个字符，在排他模型下少一个字符 → 明确 Span 的 end_column 是排他还是包含，并修正计算

- [modules.py:216-218,228,273-274] **循环导入检测过于脆弱** → 基于 loading_stack，但模块加载失败时 finally 块从栈中移除，modules 中没有缓存半成品；没有"部分加载"状态 → 引入"加载中"状态（LOADING/LOADED/FAILED）

- [modules.py:276-291] **导出收集不校验名称是否存在** → _collect_exports() 只是简单收集 ExportDecl 的 name 字段，完全不检查这个名称是否真的在模块中定义了 → 导出收集后，校验每个导出名称是否存在于类型环境和求值环境中

#### 中等问题（影响特定场景）

- [errors.py:47-48] **ANSI 颜色检测不遵循通用标准** → 只检查 NO_COLOR 和 isatty()，缺少 CLICOLOR/CLICOLOR_FORCE/FORCE_COLOR/TERM=dumb 支持
- [errors.py:405-411] **ErrorCollector.raise_all 滥用 note 机制** → 将后续错误作为第一个错误的"注释"，每个错误都是独立的，应该分别报告
- [modules.py:98-105] **默认搜索路径包含相对路径且顺序有歧义** → 空字符串 "" 作为搜索路径含义模糊
- [modules.py:328-330] **导入的绑定一律设为 immutable——语义是否正确？** → 需明确文档化并在类型检查中一致处理
- [environment.py:34-48] **lookup 与 lookup_binding 重复代码** → 违反 DRY 原则
- [environment.py:50-61] **assign 错误信息无法区分"未定义"还是"不可变"**
- [errors.py:249] **相关注释的源码上下文与主错误共享行号宽度** → note 行号远大于主错误时显示会错位
- [modules.py:293-299] **_collect_exported_types 与 _collect_exports 重复，且返回值未使用**

#### 轻微问题（代码质量）

- [errors.py:61] **SourceSpan = Span 无意义别名**
- [errors.py:93] **highlight_span 旧格式兼容造成冗余**
- [errors.py:124-128] **__str__ 和 format() 重复**
- [modules.py:29] **RuntimeError_ 命名不一致**
- [modules.py:366] **全局模块管理器单例**
- [modules.py:56-57] **get_exported_bindings 静默跳过未定义名称**
- [environment.py:67-73] **all_bindings 递归效率低**
- [environment.py 全文] **缺少 has / is_defined 方法**
- [errors.py:179] **ctx_end 计算 off-by-one 疑虑**

#### 原创性分析

**errors.py**：中等原创性（⭐⭐⭐）。Rust 风格的错误格式是借鉴，但多行 span 的下划线计算在 Python 实现中不多见。

**modules.py**：低原创性（⭐⭐）。模块解析器是教科书式实现，与 Python importlib、Node.js require 思路类似。

**environment.py**：低原创性（⭐⭐）。链式作用域环境是解释器实现的标准做法，与 SICP 中的环境模型完全一致。


---

## [2026-07-15] 所有后端 第十六轮审查报告

### 总体评分
| 维度 | Native后端 | Cranelift后端 | Wasm后端 | x86_64编码器 | 编译管道 |
|------|:----------:|:-------------:|:--------:|:------------:|:--------:|
| 指令覆盖 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| 生成代码正确性 | ⭐ | ⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ |
| 可行性(生产可用) | ⭐ | ⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ |
| 与Nova语义对应 | ⭐⭐ | ⭐ | ⭐ | N/A | ⭐⭐ |
| 寄存器分配 | ⭐ | N/A | N/A | N/A | N/A |
| 指令编码正确性 | N/A | N/A | N/A | ⭐⭐⭐ | N/A |
| 编译管道连接 | ⭐ | ⭐⭐ | ⭐⭐ | N/A | ⭐⭐ |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [native_backend.py:45-82] **Native 后端寄存器分配器 LinearScanAllocator 完全未使用** → 完整实现了线性扫描算法，但在整个代码库中从未被调用；实际代码生成使用 _alloc_vreg，只从 free_gprs/free_xmms 列表中弹出寄存器，永远不回收，分配完 12 个 GPR 和 8 个 XMM 后所有后续分配返回 None → 在 _compile_function 入口处调用 LinearScanAllocator
  - 追问：如果是 OCaml 的 native 编译器，寄存器分配器从未调用能被接受吗？→ **结论：绝对不能。**

- [native_backend.py:410-485] **Native 后端 BinOp 结果目标 dst_loc 完全被忽略** → LIRBinOp 的结果总是写入 left_reg（第一个操作数寄存器），dst_loc 字段从未被读取；导致操作数被覆盖，后续指令读取错误的值 → 编译完 BinOp 后，如果 dst_loc 存在且目标寄存器与 left_reg 不同，发射 mov 指令将结果移到目标位置
  - 追问：OCaml native 编译器会允许算术运算结果不写入目标位置吗？→ **结论：不会。** 这是最基本的 SSA 语义正确性要求。

- [native_backend.py:412-419] **Native 后端 src_locs 操作数静默回退到错误寄存器** → 当 vregs.get() 返回 None 时（寄存器耗尽或操作数未注册），代码静默回退到 RAX/RCX；操作数实际上是 RAX/RCX 中碰巧存在的任何值 → 寄存器未找到时应抛出明确错误，或正确实现 spilling

- [native_backend.py:734-798] **BuildList/BuildTuple/BuildADT 栈分配未被追踪，导致返回时栈损坏** → 直接调用 e.sub_rsp_imm() 在栈上分配空间，但这些分配不计入 func.stack_size；函数尾声只 add rsp, func.stack_size，不会恢复这些额外的栈分配 → 在构建操作后恢复栈指针，或在计算 func.stack_size 时包含所有构建操作的栈需求

- [cranelift_backend.py:137-200] **Cranelift 后端 SSA 值传播完全失效** → 每条指令都生成新的临时变量名 v{counter}，但后续指令的操作数直接使用 LIR 的 src_locs 位置名（如 "r0"、"const_42"），这些名字在 Cranelift IR 中不存在；生成的 .clif 文件无法被解析 → 建立 LIR 位置名 → Cranelift SSA 名的映射表

- [cranelift_backend.py:162-168] **Cranelift 后端分支使用硬编码标签名** → LIRBranch 编译时总是跳转到 block_false 和 block_true，而不是 instr.true_label 和 instr.false_label → 使用 instr.true_label 和 instr.false_label

- [cranelift_backend.py:156-157] **Cranelift 后端 Return 不返回值** → LIRReturn 只发射 return，没有返回值；函数返回值丢失 → 返回值应从 src_locs 或最后一个 SSA 值中获取

- [cranelift_backend.py:216-238] **Cranelift 后端浮点运算使用整数操作码** → _emit_binop 总是使用 int_op_map，即使操作数是浮点类型；浮点加/减/乘/除会生成整数 iadd/isub/imul/sdiv 指令 → 根据操作数类型选择 float_op_map 或 int_op_map

- [wasm_backend.py:230-264] **Wasm 后端 Block/Label/Jump 语义完全错误** → LIRLabel 被编译为 (block $block_name ...)，打开新 block 但从未关闭；LIRJump 被编译为 (br $block_target)，在 Wasm 中 br 是向外跳出块，不是向前跳转到标签 → 需要重新设计：将 LIR 的 CFG 转换为 Wasm 的 block/loop/if 结构
  - 追问：如果是生产级编译器后端，生成的目标代码语法都无效能被接受吗？→ **结论：绝对不能。**

- [compiler_pipeline.py:33-35] **编译管道 BACKEND_NATIVE 实际使用 CraneliftBackend** → 当 target == BACKEND_NATIVE 时，实际实例化的是 CraneliftBackend，而不是 NativeCodeGen；真正的自研 native 后端完全游离于管道之外 → 要么接入 NativeCodeGen，要么重命名常量为 BACKEND_CRANELIFT

- [compiler_pipeline.py:80-84] **编译管道 C 后端绕过整个 IR 管道** → C 后端直接接收 AST 调用 self.backend.generate(ast)，绕过了 HIR→MIR→LIR 的整个降级管道 → 统一编译管道，所有后端都从 LIR 开始

#### 中等问题（影响特定场景）

- [x86_64.py:375-386] **mov_mem_imm64 只写入 32 位立即数** → 函数名声称写入 64 位，但实际只调用 emit_uint32(imm)
- [x86_64.py:451-457,467-473] **je_rel32 重复定义** → 第二个定义覆盖第一个
- [x86_64.py:507-547] **setcc/movzx 缺少 REX 前缀** → R8-R15 寄存器无法正确访问低 8 位
- [native_backend.py:248-264] **函数调用时若 src_reg 为 None，参数被静默跳过**
- [cranelift_backend.py:210-211] **字符串常量引用但数据段未定义**
- [wasm_backend.py:296-297] **LIRStoreReg 是空操作**
- [wasm_backend.py:161] **字符串 null 字节编码错误** → b"\\x00" 是 4 个字面量字符
- [wasm_backend.py:153-163,368-374] **字符串表逻辑重复**
- [c_codegen.py:590-600] **C 代码生成 TryExpr 返回类型不匹配**

#### 轻微问题（代码质量）

- [x86_64.py:68-71] **_rex 方法在 rex == 0x40 时跳过发射**
- [native_backend.py:202-211] **_alloc_vreg 使用 f"const_{instr.value}" 等作为 key**
- [wasm_backend.py:79] **模块名硬编码为 $nova**
- [cranelift_backend.py:116-118] **函数前缀硬编码为 %nova_**
- [native_backend.py:804-826] **_compile_counted_loop 是空方法**
- [compiler_pipeline.py:88-107] **compile_to_ir_text 不运行 TypeChecker**

#### 指令覆盖对比表
| LIR 指令 | Native后端 | Cranelift后端 | Wasm后端 |
|----------|:----------:|:-------------:|:--------:|
| LIRLoadConst (int/float/bool/string) | ✅/✅/✅/⚠️ | ✅/✅/✅/⚠️ | ✅/✅/✅/⚠️ |
| LIRBinOp (算术 +-* /%) | ✅ | ⚠️（仅整数） | ⚠️ |
| LIRBinOp (比较 == != < > <= >=) | ✅ | ⚠️（仅整数） | ⚠️ |
| LIRBinOp (逻辑 && \|\|) | ✅ | ❌ | ❌ |
| LIRCall (直接) | ✅ | ✅ | ✅ |
| LIRJump | ✅ | ✅ | ❌（语义错误） |
| LIRBranch | ✅ | ❌（硬编码标签） | ❌（语义错误） |
| LIRReturn | ✅ | ❌（无返回值） | ⚠️ |
| LIRBuildList/Tuple/ADT | ✅ | ✅ | ✅ |
| LIRPanic | ✅ | ✅ | ✅ |

#### 原创性分析

- **x86_64 指令编码器**：自研实现，从零编码 ModR/M、REX 前缀、SSE 指令等，是项目中技术含量最高、最原创的部分
- **ELF 生成器**：自研实现，直接构建 ELF64 header + program headers，属于基础系统编程
- **LinearScanAllocator**：经典线性扫描算法的标准实现，非原创但正确实现了算法（可惜未被使用）
- **三层 IR 设计**：借鉴 MLIR Dialect 思想，属于业界标准做法

---

## [2026-07-15] IR 系统 + Pass 管理器 第十六轮审查报告

### 总体评分
| 维度 | ir_nodes.py | hir_lowering.py | mir_lowering.py | lir_lowering.py | pass_manager.py |
|------|-------------|-----------------|-----------------|-----------------|-----------------|
| 设计合理性 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| 正确性 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐ |
| 完整性 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| 健壮性 | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐ |
| 可维护性 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 文档质量 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [mir_lowering.py:351-384] **MIR Match 表达式完全退化——所有分支只有第一个被执行** → _lower_match_expr 将 match 完全降级为错误的控制流；计算了 value_ssa 但从未用于分支判断；所有 arm 通过 MIRJump 无条件依次连接，形成线性链；第一个 arm 执行后直接跳转到 merge_block → 正确的 match 降级应当对每个 arm 生成模式匹配代码（比较、守卫检查），条件满足则进入 arm body
  - 追问：如果 LLVM 的 switch 指令降级后只执行第一个 case，能被接受吗？→ **结论：绝对不能。** 这是编译器正确性的致命缺陷。

- [lir_lowering.py:204-211] **LIR Phi 节点只取第一个 source——SSA 语义彻底破坏** → Phi 节点的核心语义是"根据前驱基本块选择对应的值"，但这里直接丢弃了除第一个以外的所有 source；所有涉及控制流汇合点（if-else、match、循环）的变量值都是错误的 → 在 LIR 层正确实现 Phi 节点语义，或在每个前驱块末尾插入 copy 指令
  - 追问：如果 LLVM 的 Phi 节点只取第一个 source，能被接受吗？→ **结论：绝对不能。** SSA 形式名存实亡。

- [mir_lowering.py:285-289] **ListComprehension 降级为空列表** → 列表推导式直接返回空列表常量，完全丢弃了映射表达式、迭代变量、可迭代对象和过滤条件 → 正确实现列表推导式的 MIR 降级

- [mir_lowering.py:247-250] **Lambda 闭包自由变量完全丢失 + 函数体丢失** → captures 字段从未被填充；Lambda 的参数和 body 完全丢失；fn_name 是无意义的占位字符串，没有对应的 MIRFunction → 正确实现 Lambda 表达式的 MIR 降级，包括捕获变量和函数体

- [mir_lowering.py:386-394] **Pipe MIR 降级对未绑定函数名生成空 callee** → 管道的 stage 如果是命名函数，_lower_expr(HIRIdentifier("foo")) 因 foo 不在 self.env 中而返回 None，导致 callee = "" → 正确区分命名函数和 SSA 值，复用 HIRCallExpr 的处理逻辑

- [lir_lowering.py:219-223] **LIR Branch 丢失 true/false 目标标签** → LIRBranch 有 true_label 和 false_label 字段，但降级时完全没有设置；条件分支指令不知道跳转到哪里 → 正确设置 true_label 和 false_label

- [lir_lowering.py:231-241] **MIRSwitch 和 MIRMatchJump 降级为无判断的 LIRJump** → Switch 和 MatchJump 完全退化为无条件跳转到 default 目标，所有分支信息被丢弃 → 正确降级为多个条件分支或 switch 跳转表

- [pass_manager.py:256-261] **Inlining pass 完全空壳** → 内联优化完全没有实现，直接 return False；但它被加入了默认优化管道，每次迭代都被调用一次，白白浪费性能
  - 追问：如果 LLVM 的 opt 工具中有一个完全空壳的优化 pass，能被接受吗？→ **结论：不能。** 宣称有优化但实际无，具有欺骗性。

- [pass_manager.py:104-107,114-117] **HIR 常量折叠使用 __class__ 突变——极端脆弱** → 直接修改对象的 __class__ 并手动删除属性，这是极其危险的 Python 反模式；dataclass 生成的 __dataclass_fields__ 不会更新，isinstance 检查可能行为异常 → 使用新对象替换旧对象，或使用 visitor 模式

#### 中等问题（影响特定场景）

- [pass_manager.py:713-744] **Pass 管理器无异常处理** → 虽然不是"静默吞掉"，但异常发生时没有上下文信息（哪个 pass、在哪个函数中失败），调试困难
- [pass_manager.py:345] **DCE 不删除 LIRBinOp 死代码** → LIRBinOp 不在无副作用列表中
- [hir_lowering.py:292-300] **HIRBlockExpr 混合声明和表达式——类型不一致**
- [mir_lowering.py:159-162] **HIR 标识符未找到时静默返回 None**
- [pass_manager.py:474-478] **MIR CSE 用 MIRLoad 替换但语义错误**
- [mir_lowering.py:396-417] **For 循环迭代变量未绑定到环境**
- [lir_lowering.py:141-147] **LIRCall 不传递参数位置**
- [lir_lowering.py:157-183] **LIRBuildList/BuildTuple/BuildADT 不包含元素位置**
- [hir_lowering.py:97-98] **AliasDef 降级丢失目标类型**
- [hir_lowering.py:331-333] **PatternConstructor 降级丢失 type_name**

#### 各 Pass 实现状态表
| Pass 名称 | HIR 层 | MIR 层 | LIR 层 | 完整度 | 备注 |
|-----------|--------|--------|--------|--------|------|
| ConstantFolding | ⚠️ 部分实现 | ✅ 基本实现 | ✅ 基本实现 | 60% | HIR 层用 __class__ 突变反模式 |
| Inlining | ❌ 空壳 | N/A | N/A | 0% | 直接 return False |
| DeadCodeElimination | ❌ 空壳 | ❌ 空壳 | ✅ 基本实现 | 30% | LIR 层遗漏 LIRBinOp |
| CommonSubexprElimination | N/A | ⚠️ 有缺陷 | ✅ 基本实现 | 50% | MIR 层用 MIRLoad 替代语义错误 |
| LoopInvariantCodeMotion | N/A | ⚠️ 有缺陷 | ⚠️ 有缺陷 | 40% | MIR 层不识别条件分支循环 |

#### 原创性分析

**三层 IR 设计（HIR→MIR→LIR）**：借鉴 MLIR Dialect 和 Rust 编译器（HIR→MIR→LLVM IR）的分层思想，属于现代编译器的标准做法，不算原创但方向正确。

**Pass 管理器**：固定点迭代 + 分层 pass 的设计是标准做法，与 LLVM PassManager 的简化版思路一致。

**整体评价**：架构方向正确（三层 IR + SSA + CFG + 优化 pass 管道），但实现质量参差不齐——上层（HIR）相对完整，下层（MIR/LIR）有大量占位和退化实现。代码更像是一个"架构原型"而非生产级编译器。


---

## [2026-07-15] C 运行时 + 测试 + Tree-sitter 第十六轮审查报告

### 总体评分
| 维度 | C运行时 | 测试套件 | Tree-sitter语法 |
|------|---------|---------|----------------|
| 功能完整性 | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 内存安全 | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 错误处理 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 测试覆盖 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| 一致性 | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| 可维护性 | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 生产就绪度 | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [nova_runtime.c:99-103] **GC 空壳实现：仅有引用计数，无循环引用回收** → nova_gc_collect() 仅返回净分配数，不做任何实际回收；任何循环引用结构（如闭包捕获自身、ADT 自引用）都将永远无法释放 → 实现标记-清除 GC 或至少提供循环引用检测机制
  - 追问：如果 GHC 缺少核心语言特性（循环引用 GC）的测试，能被接受吗？→ **结论：绝对不能。** 对于以闭包和 ADT 为核心特性的函数式语言，这是不可接受的。

- [nova_runtime.c:597-614] **nova_map_remove 不释放 value 引用——内存泄漏** → 从 map 中删除 entry 时，仅释放 key 和 entry 结构体，value 的引用计数从未递减 → 在 nova_free(entry) 前添加 nova_value_release((NovaValue*)entry->value)

- [nova_runtime.c:651-668] **nova_map_release 不释放 entries 的 value——大规模内存泄漏** → 释放整个 map 时，只释放 key 和 entry 结构体，所有 value 的引用计数都未递减 → 遍历释放每个 entry 前，释放其 value 的引用计数

- [nova_runtime.c:479-486] **nova_list_release 不释放元素——内存泄漏** → 释放 list 时仅 nova_free(l->items) 释放指针数组，但每个元素的引用计数从未递减 → 遍历列表元素，根据元素类型调用对应 release 函数

- [nova_runtime.c:749-756] **nova_adt_release 不释放字段——内存泄漏** → 释放 ADT 时仅 nova_free(a->fields) 释放字段指针数组，但字段值（如果是堆分配对象）的引用计数从未递减 → 遍历 fields 数组，递减每个字段的引用计数

- [nova_runtime.c:791-798] **nova_closure_release 不释放捕获变量——内存泄漏** → 释放闭包时仅 nova_free(c->captured) 释放捕获数组，但捕获的堆分配对象引用计数未递减 → 遍历 captured 数组释放每个值

- [nova_runtime.c:536-538] **nova_map_put 类型双关——将非 NovaValue* 强制转换并调用 nova_value_release** → 当 map 的 value 不是 NovaValue* 类型时，通过 nova_value_release 读取 ref_count 偏移处的内存是未定义行为 → 引入统一的 value 标签类型，或在 map 中存储类型信息
  - 追问：如果是 C 标准库，这种类型双关导致的未定义行为能被接受吗？→ **结论：不能。** 这是严重的类型安全违规。

- [nova_runtime.c:1700-1708,1770-1778] **HTTP GET/POST 状态码恒为 200** → curl -w "%{http_code}" 输出被发送到 stdout 但从未被读取解析，代码直接硬编码 200；所有 HTTP 响应（包括 404、500、403 等）都被报告为 status_code = 200 → 使用 curl 的 -o body -w "%{http_code}" 并将状态码输出到单独文件

- [nova_runtime.c:1664-1669,1723-1731] **HTTP 临时文件 TOCTOU 竞态条件** → 使用可预测的文件名 /tmp/nova_http_<pid>.tmp；攻击者可预先创建符号链接指向敏感文件 → 使用 mkstemp() 生成不可预测的临时文件名

- [test_nova.py 全文] **无 Evaluator 与 VM 行为一致性测试** → Evaluator 和 Bytecode VM 是两条独立的执行路径，但没有任何测试验证同一程序在两条路径下产生相同结果 → 建立"黄金测试"框架，同一组测试用例同时运行两个后端，断言输出一致
  - 追问：如果 GHC 缺少核心语言特性的跨后端一致性测试，能被接受吗？→ **结论：绝对不能。** 生产级编译器必须有跨后端回归测试套件。

- [test_c_codegen.py:146-171] **C 后端无端到端编译+执行测试** → test_generate_valid_c 只是尝试用 gcc 检查语法（且不强制通过），从未实际编译运行并验证输出 → 添加端到端测试：编译 Nova 源码 → 生成 C → 编译为可执行文件 → 运行并验证输出

#### 中等问题（影响特定场景）

- [grammar.js 全文] **Tree-sitter 缺少 ? (try) 操作符** → parser.py 支持 TryExpr，但 grammar.js 中完全没有 try 表达式规则
- [grammar.js:88-97] **Tree-sitter 缺少泛型类型参数定义** → parser.py 支持 type Option[T] { ... } 泛型参数，但 grammar.js 的 type_def 规则没有 [T, ...] 泛型参数部分
- [nova_runtime.c:205-211] **nova_string_find 空 substr 返回 0（不符合常规语义）**
- [nova_runtime.c:1165-1188] **JSON 解析器不验证 true/false/null 拼写** → 直接 p->pos += 4/5/4，不检查实际字符
- [nova_runtime.c:959] **nova_abs_int 对 INT64_MIN 溢出** → -INT64_MIN 在补码表示中无法用 int64_t 表示，导致未定义行为
- [runtime/test_runtime.c] **C 运行时测试不集成到主测试套件** → 417 行的 C 测试文件与 Python 测试套件完全独立
- [test_type_system.py:242-254] **部分测试为"不崩溃"测试** → test_circular_alias_detected 只断言 assert True，验证"至少不崩溃"
- [nova_runtime.c:79-87] **nova_realloc 不更新分配计数** → g_alloc_count 和 g_free_count 在 realloc 时不更新
- [nova_runtime.c:39-43] **全局状态无线程安全保护** → g_alloc_count、g_free_count、g_argc、g_argv 均为全局变量，无任何锁保护
- [nova_runtime.c:827-843] **nova_read_line 固定 4096 字节缓冲区——长行截断**

#### 轻微问题（代码质量）

- [nova_runtime.c:138] **nova_string_new_len 最小容量 16** → 对于小字符串浪费内存
- [nova_runtime.c:337] **nova_list_new 最小容量 4** → 空列表也分配 4 个槽
- [nova_runtime.c:1518-1521] **nova_exit 返回值永远不会执行** → 死代码
- [nova_runtime.c:1712] **HTTP POST 的 headers 参数未使用** → (void)headers; 占位
- [nova_runtime.c:193-196] **nova_string_char_at 返回字节而非字符** → 对 UTF-8 字符串可能返回不完整的多字节字符
- [测试文件] **测试文件使用 unittest 和 pytest 混合** → 风格不统一
- [tree-sitter-nova/test/corpus] **Tree-sitter corpus 测试极少（仅 6 个文件）**
- [nova_runtime.c:1316-1321] **json_buf_grow 增长策略可能多次 realloc**

#### 测试覆盖统计表
| 测试文件 | 行数 | 测试函数数 | 主要覆盖领域 |
|---------|------|-----------|-------------|
| test_nova.py | ~2973 | ~312 | Lexer, Parser, TypeChecker, Evaluator, ADT, Pipe, Builtins, Loops, JSON, Math, BytecodeVM |
| test_type_system.py | ~425 | ~43 | 泛型ADT、内置泛型、类型参数数量、类型别名 |
| test_modules.py | ~825 | ~28 | 模块解析、导入导出、循环导入、标准库 |
| test_errors.py | ~357 | ~36 | SourceSpan、ErrorCollector、ANSI颜色、多行高亮 |
| test_ir.py | ~1354 | ~93 | IR类型、HIR/MIR/LIR降级、Pass管理器、优化Pass |
| test_c_codegen.py | ~441 | ~52 | C代码生成、名称修饰、表达式 |
| test_backends.py | ~517 | ~43 | Cranelift后端、WasmGC后端、编译管道 |
| test_native_backend.py | ~1500 | ~88 | x86_64指令编码、线性扫描分配器、原生代码生成 |
| **合计** | **~8392** | **~695** | |

#### 执行路径测试分布
| 执行路径 | 测试数量 | 占比 |
|---------|---------|------|
| Evaluator（解释器） | ~85 | ~12% |
| Bytecode VM | ~93 | ~13% |
| Evaluator + VM 一致性测试 | **0** | **0%** |
| C 后端端到端（编译+运行） | **0** | **0%** |
| 原生后端端到端（编译+运行） | **0** | **0%** |
| IR / Pass 优化 | ~93 | ~13% |
| 词法/语法/类型检查 | ~100 | ~14% |
| 其他 | ~324 | ~48% |

#### 原创性分析

**C 运行时**：整体架构（引用计数 + FNV-1a 哈希 + 递归下降 JSON 解析）是标准且成熟的设计，非原创但实现完整。

**测试套件**：测试组织合理，覆盖了多层。VM 测试（93个）数量可观，但整体缺乏跨层一致性测试和端到端集成测试。

**Tree-sitter 语法**：结构清晰，规则命名规范。但缺少 ? 操作符和泛型类型参数两个重要特性，与 parser.py 存在不一致。

---

## 第十六轮架构级建议（优先级排序）

### 🔴 P0 级（立即修复，安全/正确性基石）

1. **修复类型检查器 TypeVar 万能兼容问题** → 类型系统基本失效，等于没有类型检查
2. **修复模块系统路径遍历安全漏洞** → P0 安全漏洞，可读取系统任意文件
3. **修复 MIR Match 完全退化问题** → 整个 IR 优化管道的 match 控制流完全错误
4. **修复 LIR Phi 节点只取第一个 source** → SSA 语义彻底破坏，所有控制流汇合点值错误
5. **修复嵌套模式匹配子模式顺序错位** → 函数式语言核心特性的 P0 缺陷
6. **修复 CLOSURE 全量捕获（自由变量分析）** → 函数式语言核心语义的性能+正确性问题

### 🟠 P1 级（高优先级，影响功能正确性）

7. **修复 STORE_VAR 全局泄漏** → 违反静态作用域原则
8. **修复算术运算 bool/int 不分** → 类型安全的基本防线
9. **修复 MATCH_BIND 作用域污染** → 模式匹配的基本语义保证
10. **修复管道操作符优先级错误** → 函数式语言核心运算符的解析错误
11. **修复 TRY_UNWRAP 类型检查过松** → Option/Result 类型安全的核心价值
12. **添加 Evaluator-VM 一致性测试框架** → 多后端语言的基本质量要求
13. **修复错误信息缺少文件名** → 多文件项目调试几乎不可用
14. **修复 AST 节点 span 信息不完整** → 错误报告和 IDE 功能的基础
15. **修复 C 运行时嵌套容器释放不递归** → 大规模内存泄漏

### 🟡 P2 级（中优先级，影响质量/可维护性）

16. **统一闭包语义（引用 vs 值快照）** → 语言规范级别的分歧
17. **修复 match guard 位置不一致（parser vs grammar.js）**
18. **实现真正的 HM 类型推断（unification + let-polymorphism）**
19. **修复 while 循环 CONTINUE 依赖启发式检测**
20. **修复 BREAK 前向扫描脆弱设计**
21. **接入 Native 后端到编译管道**
22. **修复 Cranelift 后端 SSA 值传播**
23. **重写 Wasm 后端控制流翻译**
24. **实现 Parser 语法错误恢复**
25. **添加 C 后端端到端测试**

### 🟢 长期规划

26. **实现真正的 GC（标记-清除或分代 GC）**
27. **重写 IR 降级链，实现真正的 SSA + Phi 消除**
28. **建立模块命名空间系统，摆脱 import * 模式**
29. **实现 Tree-sitter 语法与 parser.py 的完全对齐**
30. **添加 fuzz 测试、属性测试、边界值测试**



---

## [2026-07-15] 第十七轮审查报告 — 核心执行引擎（VM/编译器/求值器）

---

## [2026-07-15] VM 虚拟机 (vm.py) 第十七轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 模式匹配字节码、FOR_ITER 栈式迭代、TRY_UNWRAP 指令有特色 |
| 可行性 | ⭐⭐⭐ | 核心路径可用；多处结构性问题，难以扩展到生产级 |
| 正确性 | ⭐⭐ | STORE_VAR 语义错误、块级作用域缺失、构造器不支持柯里化 |
| 安全性 | ⭐⭐ | 迭代器字典异常路径泄漏、read_line 无 EOF 保护、全局变量可任意创建 |
| 一致性 | ⭐⭐ | 与 Evaluator 存在作用域、Assignment 语义、构造器柯里化等多处差异 |
| 完整性 | ⭐⭐⭐⭐ | 64 条指令全部实现，覆盖常量/运算/控制流/函数/数据结构/模式匹配/ADT |
| 工程质量 | ⭐⭐⭐ | 代码可读但结构混乱，循环状态管理脆弱，重复代码多 |
| 性能 | ⭐⭐⭐ | 纯 Python 解释型 VM 性能天然受限，无指令派发优化 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [vm.py:592-605] **STORE_VAR 语义错误——赋值可任意创建全局变量** → 变量不存在于 locals 时直接写入 `self.globals[name] = val`，拼写错误的变量名会静默创建新全局变量而非报错；与 evaluator 的 `env.assign()`（找不到则抛 RuntimeError_）行为严重不一致 → 区分 LET_BINDING（创建新绑定）和 ASSIGN（赋值给已有绑定）两条指令，ASSIGN 在找不到变量时应抛出错误
  - 追问：如果 Python 中函数内赋值会静默创建全局变量（Python 2 的反模式），能被接受吗？→ **结论：绝对不能。** 这是作用域模型的根本性错误。

- [vm.py 全文] **块级作用域完全缺失** → 所有变量（for 循环变量、match 绑定、let 绑定）都直接写入 frame.locals 或 globals，块结束时不清理；for 循环变量循环结束后仍然存在，match 绑定泄漏到外层作用域 → 实现作用域栈或帧内作用域层级
  - 追问：如果 JavaScript 没有块级作用域（ES5 时代的 var），能算现代语言吗？→ **结论：不能。** 词法作用域是函数式语言的基础。

- [vm.py:871-880] **CLOSURE 捕获整个帧 locals 而非仅自由变量** → 每次创建闭包都 `dict(self.call_stack[-1].locals)` 浅拷贝所有局部变量，时间 O(n)、空间 O(n)，阻止 GC 回收不需要的大对象；与函数式语言标准语义不符 → 编译器实现自由变量分析，CLOSURE 指令携带捕获变量名列表
  - 追问：如果 OCaml 的闭包捕获了整个作用域的 dict 拷贝，性能影响能被接受吗？→ **结论：绝对不能。**

- [vm.py:372-377] **NovaConstructor 不支持部分应用/柯里化** → 构造器是独立类型，参数数量不匹配时直接报错；高阶函数中 `map(Some, [1,2,3])` 会失败；与 evaluator 中构造器包装为 BuiltinFn 支持柯里化不一致 → 将 NovaConstructor 改为通过 NovaClosure 或 BuiltinFn 机制支持部分应用
  - 追问：如果 Haskell 的数据构造器不能被部分应用，能被接受吗？→ **结论：绝对不能。** 一等构造器 + 柯里化是函数式语言的核心特性。

- [vm.py:988-1071] **迭代器索引字典异常退出时泄漏** → `_range_index` 和 `_list_index` 是 VM 实例级字典，正常退出（迭代完毕、BREAK）时清理，但 TRY_UNWRAP 提前返回、RuntimeError 异常、RETURN 提前返回时不清理；长时间运行会累积泄漏 → 用 try/finally 或上下文管理器确保清理

- [vm.py:755-758] **while 循环检测基于脆弱的启发式规则** → 通过"向后跳 + 下一条指令是 CONST_UNIT"的启发式推断来设置 loop_start，依赖代码生成的特定模式；嵌套循环或非 while 向后跳转可能错误修改循环状态 → 编译器通过操作数显式传递循环元数据

- [vm.py:525-527, 1291-1292] **TRY_UNWRAP 顶层语义与 evaluator 不一致** → 顶层代码中 `?` 失败时静默停止执行，错误值留在栈上但不报告；evaluator 中顶层 `?` 会向上传播 ReturnSignal 导致崩溃（至少用户能看到错误） → 顶层 TRY_UNWRAP 失败时应抛出明确的运行时错误

- [vm.py:467-471 vs 891-896] **RETURN 指令重复实现且语义不一致** → `_execute_function` 中 pop 值返回（栈变化 [value]→[]），`_execute_instruction` 中 pop 再 push + set return_flag（栈不变）；函数执行时前者优先，后者是死代码；顶层执行时后者生效 → 统一 RETURN 实现，消除死代码

#### 中等问题（影响特定场景）

- [vm.py:837-844] **BREAK 的前向扫描回退路径仍然存在** → for 循环 BREAK 在 `_for_iters` 为空时回退到前向扫描模式，扫描到 LOOP_END 或 CONST_UNIT 就停止，非常脆弱 → 删除回退路径，确保所有 BREAK 都有明确的操作数

- [vm.py:817-818] **_while_loops 条目 BREAK 时弹出但不验证对应关系** → 直接弹出栈顶元素，不验证是否与 BREAK 目标匹配；编译器一个 bug 就可能导致 VM 状态损坏 → 添加断言或验证逻辑

- [vm.py:181] **内置函数 read_line 没有 EOF 保护** → 直接调用 `input()`，遇到 EOF 时抛出 EOFError 导致 VM 崩溃；evaluator 有 try/except 捕获并返回空字符串 → 添加 try/except 捕获 EOFError

- [vm.py:241] **filter 内置函数使用 `is True` 严格判断** → 谓词必须返回精确的 `True` 单例，truthy 的非 Bool 值会静默过滤掉所有元素 → 检查谓词返回值类型，必须是 Bool 否则报错

- [vm.py:247-257] **_builtin_head/tail 不做类型检查** → 直接使用 `lst[0]` 和 `lst[1:]`，传入字符串、tuple 等可索引类型会产生意外行为 → 添加类型检查

- [vm.py:925-935] **BUILD_MAP 键可以是不可哈希类型** → 直接用 Python dict 存储，list 等不可哈希键会抛出 Python 原生 TypeError 而非 Nova 的 RuntimeError_ → 捕获 TypeError 并转为友好的 RuntimeError_

- [vm.py:1149-1157] **MATCH_BIND 绑定的变量在 match 结束后不清理** → 模式匹配中绑定的变量直接写入 frame.locals，match 结束后仍然存在；同一个函数中多个 match 绑定名冲突时会互相覆盖 → 实现块级作用域（见严重问题）

- [vm.py:336-337] **_format_value 中 Python None 显示为 "null"** → 如果 Python None 意外流入 Nova 运行时值，print 会显示 "null" 而非报错 → 遇到 Python None 时抛出断言错误

- [vm.py:608-614] **ADD 操作对字符串/列表也有效，类型检查宽松** → 虽然类型检查器应该只生成 CONCAT 用于字符串，但 ADD 允许任何支持 `+` 的类型，编译器意外使用 ADD 时 VM 会静默接受 → 收紧 ADD 的类型检查，仅允许数值类型

#### 轻微问题（代码质量）

- [vm.py:534-539] `_pop(0)` 先检查栈深度再返回空列表，可将 n==0 检查提前
- [vm.py:1258-1260] DUP 指令手动检查栈深度而非使用统一的 `_pop` 方法
- [vm.py:1290, 1297] TRY_UNWRAP 错误消息重复 type_name，应更精确区分两种错误情况
- [vm.py:42-43] UNIT_TYPE.__bool__ 返回 False 但语义不明，类型系统应要求条件必须是 Bool
- [vm.py:327-328] _convert_nova_to_json 中 tuple 转 list，反序列化时不会变回 tuple
- [vm.py:71-72] NovaADTValue.__hash__ 依赖 fields 的可哈希性，包含 list 时会抛 TypeError
- [vm.py:1074-1077, 1211-1214] MATCH_START 和 MATCH_END 是空操作，消耗指令周期
- [vm.py:196] file_exists 内置函数用 lambda 定义，其他用方法，风格不一致

#### 原创性分析

- **Nova 特色**：模式匹配专用字节码指令（MATCH_TEST_*、MATCH_CONSTRUCTOR 等）、FOR_ITER 栈式迭代设计、TRY_UNWRAP 作为独立指令实现错误传播、while 循环运行时检测的"VM 自适应"思路
- **参考已有**：基本栈机结构参考 CPython/JVM；FOR_ITER + LOOP_END 双指令循环类似 CPython；闭包实现参考 Lua upvalue 思路（但实现质量低）

#### Evaluator vs VM 对比
| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| 作用域模型 | 嵌套环境链，块级作用域 | 只有 frame.locals + globals 两层，无块级作用域 | ❌ |
| Assignment 语义 | 找不到变量时报错 | 找不到变量时创建全局变量 | ❌ |
| 构造器部分应用 | 通过 BuiltinFn 柯里化支持 | NovaConstructor 不支持，参数不匹配直接报错 | ❌ |
| match 失败处理 | 抛出 RuntimeError_ | 静默返回 UNIT | ❌ |
| match 绑定作用域 | 分支内有效，退出自动清理 | 写入 frame.locals，永久保留 | ❌ |
| read_line EOF | 捕获 EOFError 返回空串 | 直接调用 input()，EOF 时崩溃 | ❌ |
| 顶层 ? 失败 | ReturnSignal 向上传播（崩溃） | 静默停止执行 | ❌ |
| 闭包捕获 | 捕获整个环境链（引用） | 浅拷贝当前帧 locals（值拷贝） | ⚠️ 机制不同 |
| 整数除法 | `//` 地板除法 | `//` 地板除法 | ✅ |
| 递归深度保护 | MAX_CALL_DEPTH = 1000 | MAX_CALL_DEPTH = 1000 | ✅ |
| for 循环返回列表 | 返回结果列表 | 返回结果列表 | ✅ |
| JSON 转换 | 相同逻辑 | 相同逻辑 | ✅ |

---

## [2026-07-15] 编译器 (compiler.py) 第十七轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | PIPE_CALL 专用指令、MATCH_START/END 标记、ADT 原生指令集、常量直接内联 |
| 可行性 | ⭐⭐⭐⭐ | 核心路径可用；相比首轮大幅改进 |
| 正确性 | ⭐⭐ | 嵌套模式匹配栈破坏、闭包全量捕获、TypeDef.type_params 忽略 |
| 安全性 | ⭐⭐⭐ | 栈布局大部分路径正确；但嵌套模式匹配失败路径有栈下溢风险 |
| 一致性 | ⭐⭐⭐ | 跳转回填全部正确；指令定义与生成存在多处不一致 |
| 完整性 | ⭐⭐⭐⭐ | AST 节点基本全覆盖 |
| 工程质量 | ⭐⭐ | 大量死代码、重复代码、未使用操作码定义 |
| 性能 | ⭐⭐ | 闭包全量捕获 dict 浅拷贝；常量未入池导致代码膨胀 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [compiler.py:764-777] **嵌套模式匹配失败时栈破坏** → PatternTuple/PatternList/PatternConstructor 的子元素模式匹配失败时，栈上残留已被外层 deconstruct 压入的未测试元素值，仅用一条 POP 清理远远不够；下一个 arm 的 DUP 会在错误的栈位置上操作，导致后续所有行为未定义 → 每个失败点应回填到各自专属的清理代码路径，按当时栈深度生成对应数量的 POP；或在 MATCH_START 记录栈基址，失败时由 VM 统一恢复栈
  - 追问：如果 OCaml 的模式匹配编译器在嵌套模式失败时不恢复栈，能被接受吗？→ **结论：绝对不能。** 模式匹配是函数式语言的核心控制流。

- [compiler.py:402, 682] **闭包捕获整个帧 locals 而非仅自由变量** → CLOSURE 指令发射时不分析自由变量，VM 端 `dict(self.call_stack[-1].locals)` 全量浅拷贝；Op 类定义 CLOSURE 有 3 个操作数但实际只发射 2 个，第三个本应用于传递自由变量列表，完全未使用 → 编译器实现自由变量分析，CLOSURE 指令携带捕获变量名列表
  - 追问：同前 16 轮结论 —— 函数式语言中全量捕获是不可接受的性能缺陷。

- [compiler.py:319-370] **模块导入无命名空间隔离** → 所有导入模块的导出名称直接进入全局变量表，同名导出后者静默覆盖前者；`_get_decl_name` 只检查 functions 字典，不检查已有的全局变量绑定 → 实现限定导入或命名空间前缀

#### 中等问题（影响特定场景）

- [compiler.py:272-288] **TypeDef.type_params 完全被忽略** → 泛型 ADT 定义的类型参数在编译时完全丢失，REGISTER_CTOR 和 MAKE_ADT 都不携带 type_params 信息 → 在 REGISTER_CTOR/MAKE_ADT 中携带类型参数信息
- [compiler.py:906-970] **两套完整的模式匹配方法为死代码** → `_compile_pattern_test` 和 `_compile_pattern_bindings` 约 65 行死代码，从未被调用 → 删除死代码
- [compiler.py:81 vs 402,682] **CLOSURE 操作码定义与实际使用不一致** → 定义 3 操作数，实际只发射 2 个 → 要么实现自由变量列表作为第三操作数，要么修改注释
- [compiler.py:48,75,119] **多个操作码定义但从未生成** → LOAD_CONST、LOOP、PRINT、AND、OR 均为死定义 → 清理未使用的操作码定义
- [compiler.py:420-421] **CharLiteral 编译为 CONST_STRING 无类型区分** → Char 和 String 在运行时完全相同，单字符字符串与 char 无法区分 → 用单独的 NovaChar 类或添加 CONST_CHAR 操作码
- [compiler.py:1104-1128] **列表推导式 filter 路径中 FOR_ITER 的 _for_iters 状态问题** → filter 失败跳回 FOR_ITER 时，VM 的 `self.ip - 1` 启发式判断可能错误地认为是首次迭代，导致迭代状态重置 → 让 FOR_ITER 的 fail_ip 自身作为 key 标识循环

#### 轻微问题（代码质量）

- [compiler.py:597-602] 管道编译中内置函数判断冗余，两个分支都执行相同的 LOAD_VAR
- [compiler.py] 常量池机制形同虚设，add_const 和 LOAD_CONST 从未使用
- [compiler.py] FunctionBlock.constants 从未填充
- [compiler.py:463] ForExpr.step 字段未使用，编译器通过 iterable tuple 处理步长
- [compiler.py:268-270] ExportDecl 编译器直接忽略，应在模块层面统一处理
- [compiler.py] ImportDecl 只支持模块名，不支持选择性导入

#### 原创性分析

**独特设计亮点**：
1. PIPE_CALL 专用指令——将管道值作为最后一个参数传入，栈机上精巧的设计
2. MATCH_START/MATCH_END 标记指令——为调试器和 profiler 提供明确边界
3. ADT 原生指令集——三条指令形成完整的 ADT 构造-解构闭环
4. 常量直接内联——简化编译流程，牺牲空间换取简单性
5. TRY_UNWRAP 指令——Rust 风格错误处理在栈式字节码中的直接映射

**参考借鉴**：栈机整体结构参考 CPython/JVM；跳转回填参考标准教材；FOR_ITER+LOOP_END 类似 CPython

---

## [2026-07-15] 求值器 (evaluator.py) 第十七轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 经典 AST 遍历解释器，闭包环境引用、模式匹配递归实现，无特别新颖设计 |
| 可行性 | ⭐⭐⭐⭐ | 核心功能基本可用，能运行大部分 Nova 程序 |
| 正确性 | ⭐⭐⭐ | None 单例歧义、break/continue 异常可能被误捕获、列表推导式控制流泄漏 |
| 安全性 | ⭐⭐ | 文件 I/O 无路径限制（路径穿越风险）、递归深度保护不完整 |
| 一致性 | ⭐⭐⭐ | 与 VM 在闭包语义、Unit 单例、构造器柯里化等方面不一致 |
| 完整性 | ⭐⭐⭐⭐ | 大部分 AST 节点已覆盖 |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰，但存在大量重复（两遍扫描与单遍求值逻辑重复） |
| 性能 | ⭐⭐⭐ | 直接 AST 遍历性能尚可，无尾调用优化 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [evaluator.py:14, 101-106, 168] **None 与 UNIT_VALUE 的 Python None 歧义：运行时值表示混乱** → 文档注释声称 `None -> Nova Unit / None variant`，但实际 UNIT_VALUE 是 `_UnitValue` 单例，None 变体是 NovaADTValue；`_format_value` 处理 `val is None` 返回 "null"，但正常流程中 Nova 的 None 变体是 NovaADTValue——如果任何代码路径意外产生 Python None，会静默地被当作 "null" 打印 → 彻底禁止 Python None 出现在 Nova 运行时值中，_format_value 遇到 Python None 时抛出断言错误
  - 追问：如果一种语言的运行时同时存在两种"空"表示且可以静默转换，类型系统还有意义吗？→ **结论：没有。** 这是类型系统的根本漏洞。

- [evaluator.py:334-344, 816, 820] **BreakSignal/ContinueSignal 继承自 Exception，可能被 try/except Exception 误捕获** → 如果任何内置函数或用户代码中有 `except Exception`，break/continue 信号会被静默吞掉，循环无法正常退出；虽然当前纯 Nova 代码不会出现，但未来扩展 try-catch 时是定时炸弹 → 使用 BaseException 作为控制流异常基类（类似 Python 的 GeneratorExit），或用哨兵值+返回码实现
  - 追问：Python 自身用 PEP 479 防止 StopIteration 意外传播，Nova 没有类似防护能被接受吗？→ **结论：不能。**

- [evaluator.py:233-259] **文件 I/O 内置函数无路径沙箱限制** → read_file、write_file、file_exists、list_dir 直接使用用户提供的路径，无任何路径限制；支持相对路径和绝对路径，可以读取系统任意文件（如 /etc/passwd） → 添加可选的工作目录限制，规范化路径并检查是否在允许范围内
  - 追问：Deno 默认禁用文件系统访问需要显式权限，Nova 作为新语言不考虑能力安全模型吗？→ **结论：应该考虑。**

- [evaluator.py:1016-1047] **列表推导式中 break/continue 会泄漏到外层循环** → `_eval_list_comprehension` 没有捕获 BreakSignal 和 ContinueSignal；如果列表推导式 body 或 filter_cond 中包含 break/continue，信号会直接泄漏到外层循环 → 添加 BreakSignal/ContinueSignal 捕获，或在语法检查阶段禁止
  - 追问：如果 Python 的列表推导式中 break 会泄漏到外层循环，能被接受吗？→ **结论：不能。**

- [evaluator.py:799-800] **MapExpr 键使用 Python 默认哈希，ADT 值作为键可能行为异常** → 直接用 Python dict 实现，Nova List 作为键会抛 TypeError（不可哈希），且错误是 Python 原生 TypeError 而非 Nova 运行时错误 → 在 MapExpr 求值时检查键的可哈希性，提供友好的错误消息

- [evaluator.py:716-727] **TryExpr 的 ? 操作符用 ReturnSignal 传播，但顶层使用时无捕获** → ? 操作符出现在顶层代码（不在任何函数内）时，ReturnSignal 向上传播到 eval_program 没有被捕获，导致程序崩溃而非友好错误 → 在 eval_program 和顶层求值入口处捕获 ReturnSignal，给出明确错误消息

- [evaluator.py:1056-1078] **模式匹配守卫条件中变量绑定的作用域与分支体不一致** → 守卫在独立的 child_env 中求值，求值后环境被恢复；分支体又在另一个 child_env 中求值；守卫中 mut 变量的赋值修改不会传播到分支体 → 明确守卫语义，或共享环境，或禁止守卫中的赋值

- [evaluator.py:406-461] **递归深度保护不完整：内置函数回调用户代码计数不一致** → `_call_fn` 只在 NovaClosure 分支增加 _call_depth，BuiltinFn 分支不增加；但内置函数 filter/map 回调用户函数时通过 _call_fn 进入会计数，深度计数与 VM 的 call_stack 长度语义不同 → 统一深度计数机制

#### 中等问题（影响特定场景）

- [evaluator.py:499-626] eval_decl 与两遍扫描逻辑大量重复，代码重复率超 80%
- [evaluator.py 各处 RuntimeError_] 运行时错误普遍缺少位置信息（span）
- [evaluator.py:49-53, environment.py:50-61] 闭包是引用语义但与 VM 的值语义不一致
- [evaluator.py:208] _builtin_filter 用 `is True` 判断谓词结果过于严格，与 if 表达式类型检查不一致
- [evaluator.py:966-976] ForExpr.iterable 使用 tuple hack 表示 range，而非专用 AST 节点
- [evaluator.py:101-106] UNIT_VALUE 不是标准单例模式（无 __new__ 保护），对比 VM 的 UNIT_TYPE 实现
- [evaluator.py:786-792] Assignment 节点缺少对索引/字段赋值的支持
- [evaluator.py:221, 227] head/tail 空列表返回的 None 变体 field_names 不一致（有的 ["value"]，有的 []）

#### 轻微问题（代码质量）

- [evaluator.py:104] _UnitValue.__bool__ 返回 False 的语义不明确
- [evaluator.py:410-413] BuiltinFn 部分应用的 curried 函数不检查剩余参数数量
- [evaluator.py:194-198] _builtin_str_to_int 对空白字符串的处理（Python int 会 strip 空白）
- [evaluator.py:214-215] _builtin_sum 不检查元素类型，类型错误时抛 Python 原生 TypeError
- [evaluator.py:313-314] _convert_nova_to_json 中 Err 变体静默转为 null，丢失错误信息
- [evaluator.py:923-926] ++ 只支持 String 拼接，不支持 List 拼接
- [evaluator.py:1040-1042] 列表推导式 filter_cond 不检查 Bool 类型，与 if/while 不一致
- [evaluator.py:1099-1100] PatternChar 匹配不区分 Char 和 String，单字符 String 也能匹配 Char 模式
- [evaluator.py:765-766] Block 中语句的返回值被丢弃但可能有副作用，纯表达式的值被静默丢弃
- [evaluator.py:538-542, 618-622] ImportDecl 在两遍扫描中都处理，可能有循环导入问题

#### 原创性分析

Nova 求值器属于经典的直接 AST 遍历解释器，可追溯到 Lisp 的 eval/apply 模型。具体来说：

1. **环境模型**：链式环境（parent 指针）实现词法作用域，最经典的实现方式
2. **闭包实现**：闭包 = 代码 + 环境引用，标准的词法闭包实现
3. **模式匹配**：递归下降的模式匹配器，最直接的实现方式，无编译优化
4. **控制流**：用异常实现 break/continue/return，解释器中的常见技巧
5. **? 操作符**：用 ReturnSignal 传播 Option/Result 的错误值，类似 Rust 的 ? 操作符语义

**结论**：实现方式是教科书级别的，没有明显的原创性贡献。作为参考实现是合格的。

---

## [2026-07-15] 第十七轮审查报告 — 类型系统 + 前端

---

## [2026-07-15] 类型检查器 (type_checker.py) 第十七轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 类型推断算法 | ⭐ | 非真正 HM，TypeVar 是通配符，无约束传播 |
| 泛型/ADT 类型比较 | ⭐⭐⭐⭐ | __eq__ 正确比较类型参数，但 _types_compatible 中 TypeVar 破坏正确性 |
| Pattern 类型检查 | ⭐⭐⭐ | 所有 Pattern 有基本检查，但缺少守卫类型检查和穷尽性检查 |
| 错误恢复 | ⭐⭐⭐ | ErrorCollector 存在但有 bug，收集模式下基本可用 |
| 类型标注支持 | ⭐⭐⭐⭐ | 支持基本/泛型/函数/元组/ADT/别名，类型参数数量检查到位 |
| 递归 ADT | ⭐⭐⭐ | 结构上支持递归 ADT 定义，但无真正推断时递归函数类型推断失效 |
| Let 多态 | ⭐ | 完全缺失，无 generalization/instantiation，TypeVar 意外产生"伪多态" |
| 类型统一 (Unification) | ⭐ | 无真正的 unification，只有单向绑定收集和通配符式兼容检查 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [type_checker.py:1353-1354] **TypeVar 被当作万能通配符，类型系统本质不可靠** → 任何包含 TypeVar 的类型都被判定为与任何类型兼容；`fun x -> x + 1` 中 x 的类型是 TypeVar，x + 1 通过检查，但 x 未被约束为 Int；调用该函数时传入 String 也会通过类型检查 → 实现真正的 unification 算法，TypeVar 需要被具体类型替换（绑定），而不是永远匹配一切
  - 追问：如果 OCaml 的类型检查器允许 `fun x -> x + 1` 接受字符串参数，能被接受吗？→ **结论：绝对不能。** 这是类型系统的根本正确性问题。

- [type_checker.py:1223-1243] **无真正的 Unification 算法** → 只有单向绑定（从实际类型到期望类型的 TypeVar），没有双向统一；没有 occurs check；没有 variable-variable 统一；没有约束传播 → 实现完整的 Robinson unification 或基于 union-find 的高效 unification
  - 追问：如果 Haskell 的类型检查器没有 unification，能被接受吗？→ **结论：不能。** Unification 是 HM 类型推断的核心算法。

- [type_checker.py:779-789, 520-530] **Let 多态完全缺失** → 没有 generalization（将自由类型变量提升为 forall 量化），没有 instantiation（使用 let 绑定时生成新鲜实例）；当前表现出的"多态"是假的（因为 TypeVar 从不被约束） → 实现 type scheme（forall a. type）表示，let 绑定后 generalization，使用时 instantiation
  - 追问：如果 OCaml 没有正确实现 let 多态，能被接受吗？→ **结论：不能。** Let 多态是 Damas-Milner 类型系统的核心。

- [type_checker.py:740-750] **FnCall 中 TypeVar 被调用者绕过错误报告机制** → 在非收集模式下，错误被静默添加到收集器但从不抛出；返回新的 TypeVar 而不是 ERROR_TYPE，导致后续级联错误 → 统一使用 _report_error，返回 ERROR_TYPE

- [type_checker.py:691-707] **Lambda 的返回类型标注从未被检查** → Lambda AST 节点有 return_type 字段，但类型检查器完全忽略它 → 在 Lambda 检查中，将推断的 body 类型与 return_type 标注进行比较

- [type_checker.py:1014-1022] **MatchArm 的守卫条件从未被类型检查** → `match x { pat when cond -> body }` 中的 cond 守卫表达式完全不检查类型 → 在 check_match_arm 中检查 arm.guard，要求其类型为 Bool

- [type_checker.py:791-794] **表达式级 MutBinding 跳过类型标注检查** → 对比 LetBinding 有完整的类型标注检查，MutBinding 完全忽略 expr.type_annotation → 增加与 LetBinding 相同的类型标注检查逻辑

- [type_checker.py:755-770] **PipeExpr 类型检查是启发式的，不绑定类型变量** → 同时检查第一个参数和最后一个参数，只要其中一个兼容就通过；完全不调用 _collect_type_bindings，泛型函数的类型变量不被管道参数约束 → 明确定义管道语义，使用与 FnCall 相同的类型绑定和替换逻辑

- [type_checker.py:1311-1318] **TypeGeneric 未知类型名不报错** → TypeIdentifier 对未知类型名报错，但 TypeGeneric 对未知类型名静默通过；`let x: FooBar[Int] = ...` 不报错 → 当 adt_params is None 时报错

- [type_checker.py:543-563] **递归函数无类型标注时类型完全不受约束** → 无标注的递归函数在第一遍注册为全 TypeVar 类型，第二遍检查时由于 TypeVar 匹配一切，函数体中的任何用法都不会约束参数或返回类型 → 这是类型系统根本问题的一部分，需要真正的 unification

- [type_checker.py 全文] **无 Occurs Check，可构造无限类型** → 虽然当前 TypeVar 匹配一切的模式使得无限类型不直接导致问题，但一旦实现正确的 unification，缺少 occurs check 会导致 a = a -> Int 这样的无限类型被接受 → 在 unification 中实现 occurs check
  - 追问：如果 Haskell 接受 `a = a -> a` 这样的无限类型，能被接受吗？→ **结论：不能。** 简单类型 lambda 演算中不允许无限类型。

- [type_checker.py:242-254] **循环别名检测失效** → `alias A = B; alias B = A` 这样的循环别名不会被检测到 → 两遍处理别名：第一遍收集所有别名名称，第二遍解析并检测循环

#### 中等问题（影响特定场景）

- [type_checker.py:677-689] 无 Pattern 穷尽性检查——缺少分支不会报错
- [type_checker.py:677-689] 无冗余 Pattern 检测——永远不会被匹配到的分支不会警告
- [type_checker.py:953-954, 989-990] ForExpr/ListComprehension 对元组迭代的处理错误——只取第一个元素的类型
- [type_checker.py:356-357] 内置数学函数的 Int→Float 自动转换与类型签名矛盾——注释说自动转换但类型签名是 Float→Float
- [type_checker.py:167-185] TypeVar 按名称相等，名称冲突会导致错误绑定——不同作用域中同名 TypeVar 被视为同一个
- [type_checker.py:415, 1288-1291] 裸 ADT 名称（无类型参数）解析为带自由 TypeVar 的类型
- [type_checker.py:1058-1066] PatternConstructor 查找构造器效率低且可能不一致
- [type_checker.py:350] json_parse 的类型签名有效关闭了 JSON 值的类型检查——返回 TypeVar("json_value")，等于 any
- [type_checker.py:1329-1347] _expand_alias 不处理 TypeVar，代码结构不一致
- [type_checker.py:1162-1166] 比较操作符 (< > <= >=) 仅支持数值类型，String/Char 不可比较

#### 轻微问题（代码质量）

- [type_checker.py:253] ErrorCollector 总是被创建，即使在非收集模式
- [type_checker.py:1357-1376] _types_compatible 重复了 __eq__ 的逻辑
- [type_checker.py:4] 文档声称 HM 但实际差距很大——"简化的 Hindley-Milner" 有误导性
- [type_checker.py:169] TypeVar 计数器是全局类变量，多个 TypeChecker 实例共享
- [type_checker.py 全文] 无类型方案 (Type Scheme) 表示
- [type_checker.py:735-739] 部分应用返回类型不检查可行性
- [type_checker.py:820-890] ADT 字段访问是 product-like 语义（非标准）
- [type_checker.py:973-977] Break/Continue 返回 Unit 而非 Bottom 类型
- [type_checker.py:928-932] TryExpr 硬编码 Option/Result 名称，不支持用户自定义 error monad

#### 原创性分析

Nova 的类型检查器在设计上参考了 Hindley-Milner 的术语（TypeVar、泛型、ADT），但没有实现其核心算法（unification、let-polymorphism、generalization/instantiation）。这是一个"注解优先"的类型检查器：有标注的路径工作良好，无标注的路径不可靠。

**与成熟语言的对比**：
- 最接近的类比是早期 C 语言（K&R C）的隐式 int 规则
- 不像 OCaml/Haskell（真正的 HM）
- 不像 TypeScript（有 structural typing 和 any 类型，但 any 是显式的）

---

## [2026-07-15] 词法/语法分析器 (lexer.py + parser.py) 第十七轮审查报告

### 总体评分

#### Lexer (lexer.py)
| 维度 | 评分 | 说明 |
|------|------|------|
| Token 覆盖完整性 | ⭐⭐⭐⭐ | 基本覆盖所有语法元素，但 UNIT、PIPE_VARIANT 为死 Token |
| 词法错误恢复 | ⭐⭐⭐ | 有基本恢复，但错误为字符串而非结构化对象 |
| 位置信息准确性 | ⭐⭐⭐ | 行号/列号基本正确，但转义字符的 end_col 有偏差 |
| 运算符 Token 覆盖 | ⭐⭐⭐⭐ | 主要运算符均有对应 Token，缺少 <- 专用 Token |
| 字符串处理完整性 | ⭐⭐ | 缺少多行字符串、原始字符串、Unicode 转义 |
| 数字字面量完整性 | ⭐⭐ | 缺科学计数法、十六进制/八进制/二进制、数字分隔符 |
| 注释处理完整性 | ⭐⭐ | 仅支持单行注释，无块注释 |
| 生产就绪度 | ⭐⭐⭐ | 核心路径可用，但边缘场景覆盖不足 |

#### Parser (parser.py)
| 维度 | 评分 | 说明 |
|------|------|------|
| 运算符优先级正确性 | ⭐⭐ | 管道操作符优先级严重错误，与 grammar.js 矛盾 |
| 结合性正确性 | ⭐⭐⭐⭐ | 大部分运算符左结合正确；一元运算符右结合正确 |
| 语法歧义处理 | ⭐⭐⭐ | if-then-else 无悬挂歧义，但 match 分支隐式分隔有风险 |
| 左递归处理 | ⭐⭐⭐⭐⭐ | 递归下降通过优先级分层正确消除左递归 |
| 错误位置准确性 | ⭐ | 绝大多数 AST 节点 span 仅含起始 token，非完整范围 |
| 错误恢复能力 | ⭐ | 完全没有错误恢复，遇错即停 |
| AST 生成完整性 | ⭐⭐⭐⭐ | 大部分语法结构有对应 AST 节点 |
| 生产就绪度 | ⭐⭐ | 核心功能可用，但缺少错误恢复、位置信息不完整 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [parser.py:672-678] **管道操作符优先级严重错误（确认未修复）** → `_parse_comparison_expr` 调用 `_parse_pipe` 获取操作数，意味着管道操作符优先级高于比较操作符；与函数式语言常规（Elixir/OCaml/F# 中管道通常是最低优先级之一）以及 grammar.js（PREC.PIPE = 2）完全矛盾 → 调整优先级链，将 `_parse_pipe` 放在 `_parse_or_expr` 之下
  - 追问：如果 GCC/Clang 的运算符优先级表与语言规范矛盾，能被接受吗？→ **结论：绝对不能。** 优先级错误是编译器前端最严重的错误类别之一。

- [parser.py:764-767] **`?` 操作符不在后缀循环内——链式错误传播完全失效** → `?` 被放在后缀循环之外处理，`expr?.field`、`expr?[index]`、`expr?(args)` 等常见链式错误传播用法无法工作；在支持 `?` 的生产级语言（Rust、Swift、Kotlin）中，`?` 是后缀操作符，与字段访问/函数调用同优先级 → 将 `?` 的处理移入 `_parse_postfix_expr` 的 while 循环内
  - 追问：如果 Rust 的 `?` 运算符不能链式调用（`expr?.method()`），能被接受吗？→ **结论：不能。** 这是错误传播操作符的核心用法模式。

- [parser.py 全局] **AST 节点位置信息严重不完整（确认未修复）** → 几乎所有 AST 节点的 span 都只包含起始关键字或操作符的位置，而非整个表达式的完整范围；导致错误报告、IDE 功能（悬停、高亮）都无法正常工作 → 为每个 AST 节点计算完整的 span，从第一个 token 的起始到最后一个 token 的结束
  - 追问：如果 GCC/Clang 的 AST 节点只有起始位置没有结束位置，能被接受吗？→ **结论：绝对不能。** 位置信息是生产级编译器诊断质量的基础。

- [parser.py 全局] **Parser 完全没有语法错误恢复（确认未修复）** → 解析器遇到第一个语法错误就抛出 ParseError 并终止，用户只能看到一个错误；开发体验极差 → 实现基本的 panic mode 错误恢复，在同步 token（;、}、换行后的关键字）处重新同步
  - 追问：如果 GCC 遇到第一个语法错误就停止编译，能被接受吗？→ **结论：不能。** 现代编译器前端的基本要求就是"遇错不止"。

- [lexer.py:254-267, 454-458] **词法错误不影响解析流程且非结构化（确认未修复）** → 词法错误只存储在 self.errors 列表中并打印到 stderr，但解析器从不检查 lexer 是否有错误；错误是字符串而非结构化对象 → 使用 ErrorCollector 统一收集词法错误，解析器开始前应检查

- [parser.py:534-536] vs [grammar.js:402] **match arm guard 语法位置不一致（确认未修复）** → parser.py 中 guard 在 `->` 之前（Rust 风格），grammar.js 中 guard 在 `->` 之后（Swift 风格）；两种语法完全不兼容 → 明确规范并统一两者，建议 guard 在 `->` 之前

- [parser.py:464-466, 968-970] **`<-` 左箭头无专用 token——LT + MINUS 手动组合脆弱且错误** → `<-` 不是专用 token，而是通过 LT + MINUS 两个 token 手动组合；`x < -y` 可能被误解析为 `x <- y`；错误消息不准确 → 在 lexer 中添加 LEFT_ARROW token
  - 追问：如果 Haskell 的 `<-` 是由两个 token 手动组合的，能被接受吗？→ **结论：不能。** 多字符运算符应该在词法层面识别。

#### 中等问题（影响特定场景）

- [lexer.py:202-221] 数字字面量不支持前导小数点 `.5` 和尾随小数点 `5.`
- [lexer.py:202-221] 数字字面量无前导零处理——`0755` 是十进制还是八进制不明确
- [parser.py:384-414] Block 中隐式语句分隔对换行敏感——同一行是减法，换一行成两个语句
- [parser.py:522] match 分支隐式分隔——漏写逗号时错误消息可能误导
- [parser.py:844-884] _is_map_literal 前瞻扫描的 O(n²) 性能风险——嵌套很深时每层都扫描到匹配的 }
- [lexer.py:252-258] 未闭合字符串的错误恢复使用递归，大量非法输入时可能栈溢出
- [parser.py:252-273] VariantDef 字段解析使用位置回溯——类型表达式可能消耗多个 token
- [lexer.py:340-458] 非法字符的错误恢复使用递归而非循环
- [lexer.py:91] UNIT token 是死代码
- [lexer.py:88] PIPE_VARIANT token 是死代码
- [lexer.py:13, 155-160] _make_error 方法和 LexerError import 是死代码
- [parser.py:463, 474] ForExpr.iterable 类型不一致（元组 vs 表达式）

#### 轻微问题（代码质量）

- [lexer.py:168-173] `_peek_ahead` 参数命名误导——offset=1 是下一个字符
- [parser.py:57-62] `_advance` 在 EOF 时静默不推进
- [parser.py:367-370] `_parse_expression_statement` 是多余包装
- [parser.py:360, 629, 841] 错误处理中重复的 Span 构造代码，未复用 _span 方法
- [lexer.py:329-331] BOOL token 的 if 判断多余，两个 return 逻辑完全相同

#### 原创性分析

**词法分析器**：低原创性（⭐⭐）。标准的递归式词法分析器设计，与大多数教学级语言的 lexer 实现一致。

**语法分析器**：中等原创性（⭐⭐⭐）。递归下降解析器是标准做法，但 Nova 的优先级分层设计清晰，表达式导向的语言特性实现得比较完整。特色：map 字面量与 block 的区分通过前瞻扫描实现、管道操作符作为独立 AST 节点、`?` 操作符的 TryExpr 节点。

#### 运算符优先级表（parser.py 实际实现）

优先级从低到高：
| 优先级 | 运算符/结构 | 结合性 | 解析函数 |
|--------|------------|--------|----------|
| 1（最低） | for / while | N/A | _parse_for_while_expr |
| 2 | if-then-else | N/A | _parse_if_expr |
| 3 | match | N/A | _parse_match_expr |
| 4 | \|\| (OR) | 左 | _parse_or_expr |
| 5 | && (AND) | 左 | _parse_and_expr |
| 6 | ==, != | 左 | _parse_equality_expr |
| 7 | <, >, <=, >= | 左 | _parse_comparison_expr |
| 8 | \|> (PIPE) | 左 | _parse_pipe |
| 9 | ++ (CONCAT) | 左 | _parse_cons_expr |
| 10 | +, - | 左 | _parse_additive_expr |
| 11 | *, /, % | 左 | _parse_multiplicative_expr |
| 12 | -, ! (一元) | 右 | _parse_unary_expr |
| 13（最高） | 函数调用、字段访问、索引 | 左 | _parse_postfix_expr |
| N/A | ? (try) | N/A | _parse_postfix_expr（循环外） |

---

## [2026-07-15] 错误处理 + 模块系统 + 环境 第十七轮审查报告

### 总体评分
| 维度 | 错误处理 (errors.py) | 模块系统 (modules.py) | 环境 (environment.py) |
|------|---------------------|----------------------|---------------------|
| 正确性 | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| 完整性 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 安全性 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| 一致性 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| 可维护性 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 错误恢复能力 | ⭐⭐⭐ | ⭐⭐ | N/A |
| 生产就绪度 | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| 测试覆盖 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [errors.py:159, 179] **源码行索引边界错误导致上下文显示不准确** → `_format_with_context()` 中 `ctx_end = min(len(lines), end_line + 1)` 混用 1-based 和 0-based 索引，存在 off-by-one 风险；错误行后可能多显示一行 → 修正索引计算
  - 追问：如果 GCC 打印错误上下文时多显示或漏显示一行源码，能被接受吗？→ **结论：绝对不能。** 编译器的错误信息必须精确。

- [modules.py:240-241] **加载子模块时未传递 current_file，嵌套相对导入完全失效** → `module_manager=self` 已传递，但 `current_file=file_path` 仍然缺失；当模块 A 相对导入模块 B，模块 B 又相对导入模块 C 时，模块 B 的 current_file 为 None，相对路径解析失败 → 传递 current_file=file_path
  - 追问：如果 Python 的 import 系统中被导入的模块无法再相对导入其他模块，能被接受吗？→ **结论：绝对不能。** 这是模块系统的基本功能。

- [modules.py:124-130] **无路径遍历防护，存在目录穿越安全漏洞** → 相对路径导入直接使用 `os.path.join(current_dir, module_path)` 后接 `os.path.abspath()`，没有检查确保最终路径不超出允许的目录范围；恶意模块可通过 `../../etc/passwd` 读取系统任意文件 → 解析后应检查最终路径是否在允许的搜索路径内
  - 追问：如果 Deno 允许 import 路径通过 `../` 穿越到任意系统目录，能被接受吗？→ **结论：绝对不能。** 这是沙箱安全的基础。

- [environment.py:36-40] **lookup 不返回绑定的可变性信息，调用方无法区分** → lookup 只返回值，不返回 BindingInfo；调用方如果需要知道绑定是否可变，必须调用 lookup_binding；但很多地方直接用 lookup 获取值后原地修改（如列表 append），完全绕过 mutability 保护 → 统一使用 lookup_binding，或使不可变绑定的值真正不可变
  - 追问：如果 Haskell 的 let 绑定可以通过获取引用后原地修改数据结构，能被接受吗？→ **结论：不能。** 函数式语言的不可变性应该是深度的。

#### 中等问题（影响特定场景）

- [errors.py:281] 多行下划线最后一行计算错误——少了一个字符
- [errors.py:253-261] RelatedNote 下划线宽度计算不一致——没有 max(1, ...) 保护
- [modules.py:244-245] 导出收集在类型检查/求值之前执行，导致导出不存在的名称
- [modules.py:98-105] 默认搜索路径使用相对路径，受工作目录影响
- [modules.py:305-339] 导入逻辑在三处独立实现（ModuleManager + Evaluator + TypeChecker），严重重复
- [modules.py:245] _collect_exported_types 返回值从未被使用
- [environment.py:67-72] all_bindings() 子作用域遮蔽父作用域的逻辑正确但缺少测试
- [environment.py:42-48] lookup_binding 与 lookup 代码重复

#### 轻微问题（代码质量）

- [errors.py:93] highlight_span 语义混乱，注释说是旧格式兼容但仍在使用
- [errors.py:407-411] raise_all() 信息丢失严重——将后续错误作为纯文本 note 添加
- [errors.py:365-370] add() 方法对 WARNING 之外的 severity 处理不当——NOTE/HELP 被当作 error
- [errors.py:133-137] 无源码时的格式降级粗糙，缺少错误码体系
- [modules.py:126-127] 相对路径硬编码使用 search_paths[0]，应使用显式的 base_dir 参数
- [modules.py:358-364] 全局模块管理器默认搜索路径不一致——绝对路径 vs 相对路径
- [environment.py:30-32] define 允许重复定义同名变量而无警告
- [environment.py:26] parent 类型注解使用字符串前向引用
- [environment.py:17-20] BindingInfo.name 冗余——字典 key 已经是 name

#### 原创性分析

**错误处理系统**：Rust 风格错误格式化（源码上下文 + 箭头指示 + ANSI 颜色），是对 Rustc 的直接借鉴，实现质量中等偏上。

**模块系统**：ModuleResolver + ModuleManager 分离是标准设计；加载栈循环检测是经典 DFS 方法。原创性低。

**环境系统**：作用域链 + 父指针是经典的词法作用域实现，和 Lua、JavaScript 思路一致。三个文件中环境模块的代码质量最高，bug 最少。

---

## [2026-07-15] 第十七轮审查报告 — 后端 + IR + 运行时测试

---

## [2026-07-15] 所有后端 第十七轮审查报告

### 总体评分
| 后端 | 指令覆盖 | 代码正确性 | 可行性 | 语义对应 | 测试覆盖 | 综合评分 |
|------|---------|-----------|--------|---------|---------|---------|
| Native (自研x86_64) | 65% | 35% | Demo级 | 40% | 45% | ⭐⭐ |
| Cranelift | 55% | 15% | 不可用 | 20% | 20% | ⭐ |
| WasmGC | 50% | 10% | 不可用 | 15% | 25% | ⭐ |
| C代码生成 | 85% | 60% | 基本可用 | 65% | 55% | ⭐⭐⭐ |
| x86_64编码器 | 80% | 70% | 基本可用 | N/A | 60% | ⭐⭐⭐ |
| 编译管道 | 40% | 30% | 部分可用 | N/A | 35% | ⭐⭐ |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [native_backend.py:264] **Native 后端函数调用 ABI 第 7 个参数丢失** → 当函数调用有 7 个及以上整型参数时，第 7 个参数（索引 6）既不放入寄存器也不压栈，直接丢失；`int_idx > 6` 应为 `int_idx >= 6`
  - 追问：如果 GCC 的函数调用约定中第 7 个参数凭空消失了，能被接受吗？→ **结论：绝对不能。**

- [native_backend.py:791-845] **BuildList/BuildTuple/BuildADT 栈分配后不恢复，导致栈不平衡** → 每次构建都执行 `sub rsp, total_size`，但从未恢复 RSP；函数尾声只恢复 func.stack_size 对应的栈空间，导致 RSP 不正确，ret 会跳到错误地址 → 在 prologue 中预分配所有复合类型的空间，或每次构建后恢复 RSP
  - 追问：一个每次函数调用都会栈溢出的编译器，能算"可用"吗？→ **结论：不能。**

- [native_backend.py:781-845] **复合类型构建在栈上，返回后产生悬空指针** → List/Tuple/ADT 全部在当前函数栈帧上分配；一旦函数返回，这些内存就失效了；任何返回复合类型的函数都会产生 use-after-free → 需要堆分配（调用 malloc 或 Nova 运行时分配器）
  - 追问：OCaml 的 native 后端如果让所有 list/tuple 都是栈上悬空指针，能发布吗？→ **结论：绝对不能。**

- [native_backend.py:565-569] **LIRReturn 不将返回值移到 RAX/XMM0** → 返回值约定假设结果"刚好在 RAX 中"，但寄存器分配是自由分配的；如果最后一个操作的目标不是 RAX/XMM0，返回值就是错的 → LIRReturn 应检查 src_locs 并将值移动到正确的返回寄存器

- [native_backend.py:670-675] **StoreGlobal 硬编码使用 RBX 作为临时寄存器，可能破坏已有值** → 直接使用 RBX 保存地址，但 RBX 可能已被分配给某个 vreg；会静默破坏该 vreg 的值 → 从 free_gprs 中分配临时寄存器
  - 追问：在用户不知情的情况下偷偷覆盖寄存器，编译器和破坏者有什么区别？→ **结论：没有区别。**

- [cranelift_backend.py:162-168] **Cranelift 后端分支标签硬编码为 block_true/block_false** → 所有条件分支都跳转到固定标签，完全忽略 instr.true_label 和 instr.false_label；控制流完全错误 → 使用 instr.true_label 和 instr.false_label

- [cranelift_backend.py:216-238] **Cranelift 后端浮点运算使用整数操作码** → float_op_map 定义了但从未使用；_emit_binop 始终使用 int_op_map；浮点加减乘除会生成整数操作码 → 根据操作数类型选择 int_op_map 或 float_op_map

- [cranelift_backend.py:137-256] **Cranelift 后端 SSA 值名与 LIR 虚拟寄存器名不对应** → 常量加载生成 v0, v1 等新名字，但 BinOp/Call 等指令直接使用 LIR 虚拟寄存器名（如 "const_10"）；Cranelift 验证器会因引用未定义值而拒绝 → 建立 vreg_name -> clif_value 的映射表

- [cranelift_backend.py:156-157] **Cranelift 后端 return 不返回值** → LIRReturn 只生成 return 不带值；非 void 函数的返回值从未传递 → 从 instr.src_locs 获取返回值 SSA 名

- [wasm_backend.py:230-232, 257-263] **Wasm 后端 Label/Jump 语义完全错误（block vs label 混淆）** → LIRLabel 被编译为开一个 block，LIRJump 被编译为 br；但 Wasm 的 br 是跳出命名 block 不是跳到 block 开头；没有对应的 end 关闭 block；无法表达向后跳转（循环根本不可能） → 完全重写控制流生成，使用 loop + block 结构
  - 追问：如果 Wasm 的 block 语义理解反了（br 是跳出不是跳入），生成的代码能有任何一条正确路径吗？→ **结论：不能。**

- [wasm_backend.py:161] **Wasm 后端字符串偏移计算错误（null 终止符多算了 3 字节）** → `b"\\x00"` 是 4 个字节而非 1 个 null 字节；导致字符串偏移计算偏大，数据段中字符串实际位置与偏移不匹配 → 将 `b"\\x00"` 改为 `b"\x00"`

- [compiler_pipeline.py:33-35] **编译管道 BACKEND_NATIVE 映射到 Cranelift 而非 NativeCodeGen** → 用户选择 "native" 目标时，实际使用的是 CraneliftBackend；自研 x86_64 后端完全游离在管道之外 → 增加 BACKEND_NATIVE_X86 选项或修正映射

- [compiler_pipeline.py:80-84] **编译管道 C 后端绕过整个 IR 管道** → C 后端直接使用 AST，跳过 HIR→MIR→LIR 以及所有优化 pass；优化对 C 后端无效；架构不一致 → 统一编译管道，所有后端都从 LIR 开始

- [c_codegen.py:214, 707, 867] **C 代码生成 ADT 字段命名不一致** → 结构体定义中字段名是 `{variant_name}_{field_name}`，模式匹配中访问是 `{pattern.name}__field{i}`，构造器中赋值是 `{variant_name}__field{i}`；不匹配会导致 C 编译错误 → 统一字段命名方案

- [c_codegen.py:590-600] **C 代码生成 TryExpr 返回类型不匹配** → 生成 `return {temp};`，其中 temp 是 NovaADT*；但包含 try 表达式的函数可能返回任何类型（int, float, string 等）；直接返回 NovaADT* 与函数返回类型不匹配 → 根据函数返回类型正确处理 return

#### 中等问题（影响特定场景）

- [x86_64.py:451-457, 467-473] je_rel32 重复定义——第二个定义覆盖第一个
- [x86_64.py:375-386] mov_mem_imm64 名不副实——只写 32 位立即数
- [x86_64.py:507-547] setcc/movzx 不支持扩展寄存器（R8-R15）
- [native_backend.py:35-82] LinearScanAllocator 完全未使用——实际使用简单的 free list 分配
- [native_backend.py:701-714] LIRStoreReg 是空操作（只更新 vreg 映射）
- [native_backend.py:416-505] BinOp 浮点操作完全缺失——走整数路径
- [native_backend.py:346-366] 函数参数未从参数寄存器移到 vregs
- [cranelift_backend.py:203-206] iconst/f64.const 缺少类型后缀或格式不正确
- [cranelift_backend.py:116, 248] 函数名用 % 前缀，但调用用 $ 前缀
- [wasm_backend.py:296-297] StoreReg 是空操作
- [wasm_backend.py:187-188] LIRIndex 硬编码从 v0+0 加载
- [c_codegen.py:1301-1302] _infer_c_type_from_expr 对标识符默认返回 int64_t
- [c_codegen.py:955] Lambda 捕获所有可见变量而非仅自由变量
- [c_codegen.py:1055-1059] Assignment 不检查变量是否存在

#### 轻微问题（代码质量）

- [x86_64.py:83] mov_reg_imm64 对负数处理不当，只检查非负数范围
- [native_backend.py:542-549] FLOAT_NEG 使用 xorpd+subsd 而非直接翻转符号位
- [native_backend.py:851-873] _compile_counted_loop 是空方法
- [cranelift_backend.py:170-180] BuildList/Tuple/ADT 调用不存在的运行时函数
- [wasm_backend.py:90-100] 硬编码的 ADT 类型（Option/Result）不通用
- [c_codegen.py:52-60] C_KEYWORDS 包含非关键字的运行时函数名
- [compiler_pipeline.py:88-107] compile_to_ir_text 不做类型检查

#### 原创性分析

| 组件 | 原创性 | 说明 |
|------|--------|------|
| x86_64 编码器 | ⭐⭐⭐⭐ | 从零手写 x86_64 指令编码，涵盖 REX 前缀、ModR/M、SIB 等 |
| Native 后端 | ⭐⭐⭐ | 自研 ELF 生成 + 代码生成框架有原创性，但寄存器分配质量低 |
| Cranelift 后端 | ⭐ | 标准的 IR-to-IR 翻译模式，逻辑错误多 |
| Wasm 后端 | ⭐ | 标准的 WAT 生成，控制流理解有误 |
| C 代码生成 | ⭐⭐ | 典型的 source-to-source 翻译 |
| 编译管道 | ⭐⭐ | 三层 IR 架构有 MLIR 影子，但各层实现质量不均 |

---

## [2026-07-15] IR 系统 + Pass 管理器 第十七轮审查报告

### 总体评分
| 文件 | 设计合理性 | 实现正确性 | 完整性 | 代码质量 | 综合评分 |
|------|-----------|-----------|--------|---------|---------|
| ir_nodes.py | 7/10 | 8/10 | 6/10 | 7/10 | 7.0/10 |
| hir_lowering.py | 6/10 | 5/10 | 7/10 | 5/10 | 5.8/10 |
| mir_lowering.py | 5/10 | 2/10 | 3/10 | 4/10 | 3.5/10 |
| lir_lowering.py | 4/10 | 1/10 | 3/10 | 3/10 | 2.8/10 |
| pass_manager.py | 6/10 | 5/10 | 4/10 | 5/10 | 5.0/10 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [mir_lowering.py:351-384] **Match 表达式降级完全丢失条件分支语义** → _lower_match_expr 计算了 value_ssa 但从未用于分支判断；所有 arm 块被顺序跳转执行（每个 arm 以 MIRJump 跳到下一个 arm），等同于所有分支体依次执行；Match 表达式完全失效 → 根据模式类型生成条件分支链或跳转表
  - 追问：如果 LLVM 的 switch 降级后只执行第一个 case，能被接受吗？→ **结论：绝对不能。** 这是编译器正确性的致命缺陷。

- [lir_lowering.py:204-211] **Phi 节点只取第一个 source——SSA 语义完全破坏** → MIRPhi 降级时只取 instr.sources[0]，忽略其他所有前驱块的值；所有控制流合并（if-else、循环、match）的结果都只会取第一条路径的值 → 正确实现 Phi 节点语义，或在每个前驱块末尾插入 copy 指令
  - 追问：如果 LLVM 的 Phi 节点只取第一个 source，能被接受吗？→ **结论：绝对不能。** SSA 形式名存实亡。

- [lir_lowering.py:231-241] **Switch/MatchJump 降级为无条件跳转** → MIRSwitch 和 MIRMatchJump 都被降级为 LIRJump(target=default_target)；所有 case/variant 分支信息完全丢失，程序总是走默认分支 → 实现真正的 LIR 层 switch 指令，或展开为比较+分支链

- [mir_lowering.py:396-417] **For 循环降级未实现迭代语义** → 直接将 iter_ssa 作为条件分支的判断值；没有迭代器推进、没有元素绑定到循环变量、没有终止条件判断；for 循环等同于"如果 iterable 为真则执行一次 body" → 调用迭代器协议（iter() → next() → 判断 None/Some）

- [mir_lowering.py:285-289] **ListComprehension 降级为空列表常量** → HIRListComprehension 被降级为值为 [] 的 MIRConst，完全忽略了 result_expr、variable、iterable、filter；列表推导式永远产生空列表 → 展开为 for 循环 + 列表追加操作

- [mir_lowering.py:247-250] **Lambda/闭包降级仅生成占位符** → 仅创建 MIRClosureCreate，fn_name 是无意义的占位符，lambda 的 body 从未被降级为 MIR 函数，捕获变量列表为空 → 分析自由变量作为 captures，将 lambda body 降级为独立的 MIR 函数

- [hir_lowering.py:292-300] **HIRLetDecl 与 HIRBlockExpr 类型不匹配** → LetBinding 被降级为 HIRBlockExpr([HIRLetDecl(...)])，但 HIRBlockExpr.exprs 类型是 List[HIRExpr]，而 HIRLetDecl 继承自 HIRDecl 而非 HIRExpr → 区分声明和表达式的上下文，用 List[Union[HIRDecl, HIRExpr]]

- [lir_lowering.py:219-223] **Branch 指令的 true/false 标签从未设置** → MIRBranch 降级到 LIRBranch 时，只设置了 src_locs，但 true_label 和 false_label 字段完全为空；条件分支不知道跳去哪里 → 设置 lir.true_label = term.true_target 和 lir.false_label = term.false_target

- [lir_lowering.py:141-147] **Call 指令参数位置完全丢失** → MIRCall.args 在降级到 LIR 时完全被忽略，只保留了 arg_count；被调用函数无法获取任何参数值 → 将参数 SSA 映射到的寄存器/栈位置存入 LIRCall 的 src_locs

- [lir_lowering.py:157-183] **BuildList/BuildTuple/BuildADT 元素位置完全丢失** → MIRListBuild.elements、MIRTupleBuild.elements、MIRADTBuild.fields 在降级时全部被丢弃，只保留了 count → 将元素对应的寄存器位置存入 src_locs

#### 中等问题（影响特定场景）

- [pass_manager.py:104-107, 114-117] HIR 常量折叠使用 __class__ 赋值——极端危险的 Python 反模式
- [pass_manager.py:522-611] LICM 索引失效 bug——多循环场景下修改 body 后后续循环的索引全部失效
- [mir_lowering.py:386-394] Pipe 表达式降级与 Call 降级不一致——标识符阶段行为不同
- [mir_lowering.py:159-162] 未定义标识符静默返回 None——没有错误报告
- [hir_lowering.py:97-98] AliasDecl 目标类型未降级——别名指向的实际类型完全丢失
- [hir_lowering.py:331-333] ConstructorPattern 的 type_name 为空——下游无法确定变体属于哪个类型
- [pass_manager.py:615-692] MIR LICM 只看 header 块——不遍历整个循环体
- [pass_manager.py:280-283] DCE 副作用分类不一致——_SIDE_EFFECT_TYPES 定义了但从未被使用
- [lir_lowering.py:227-229] Return 值类型恒为 UNIT_TYPE——而不是函数的实际返回类型
- [hir_lowering.py:108-113] ForExpr/WhileExpr 顶层声明返回类型错误

#### 轻微问题（代码质量）

- [lir_lowering.py:53-56, 88] LIR 层无实际寄存器分配——只是递增的虚拟寄存器名
- [pass_manager.py:441-453] CSE 未处理交换律操作——(+, a, b) 和 (+, b, a) 被视为不同表达式
- [pass_manager.py:695-744] Pass 管理器无验证机制——错误的优化结果可能流入下一阶段
- [pass_manager.py:90-120] HIR 常量折叠不递归遍历所有子表达式
- [pass_manager.py:256-261] Inlining pass 是空壳——直接 return False 但被加入默认管道
- [pass_manager.py:288-291] HIR/MIR DCE 是空壳——只有 LIR 层有实现
- [pass_manager.py:407-439] CSE 不考虑副作用干扰——遇到内存写入或函数调用时应清除缓存
- [mir_lowering.py:368-372] Match phi sources 取最后一条指令而非结果
- [mir_lowering.py:326-337] If 表达式无 else 时 phi 只有一个 source
- [lir_lowering.py:171-176] LIRMapBuild 降级为 LIRBuildList——类型和语义都不对
- [lir_lowering.py:149-155] 闭包创建降级为字符串常量——完全是占位符

#### 各 Pass 实现状态表
| Pass 名称 | HIR 层 | MIR 层 | LIR 层 | 完整度 |
|-----------|--------|--------|--------|--------|
| ConstantFolding | ⚠️ 部分实现（__class__ 黑科技） | ⚠️ 部分实现 | ✅ 基本实现 | 60% |
| Inlining | ❌ 空壳 | N/A | N/A | 0% |
| DeadCodeElimination | ❌ 空壳 | ❌ 空壳 | ✅ 基本实现 | 30% |
| CommonSubexprElimination | N/A | ⚠️ 有缺陷 | ✅ 基本实现 | 50% |
| LoopInvariantCodeMotion | N/A | ⚠️ 有缺陷 | ⚠️ 有缺陷 | 40% |

---

## [2026-07-15] C 运行时 + 测试 + Tree-sitter 第十七轮审查报告

### 总体评分
| 维度 | C 运行时 | 测试套件 | Tree-sitter 语法 |
|------|----------|----------|------------------|
| 内存安全 | 38/100 | — | — |
| 类型安全 | 45/100 | — | — |
| 功能正确性 | 52/100 | — | — |
| 测试覆盖广度 | — | 62/100 | — |
| 测试质量深度 | — | 55/100 | — |
| 语法完整性 | — | — | 68/100 |
| 与 parser.py 一致性 | — | — | 45/100 |
| 综合评分 | 45/100 | 58/100 | 56/100 |

### 发现的问题

#### 严重问题（阻碍正常使用）

**C 运行时**：

- [nova_runtime.c:597-614] **nova_map_remove 不释放 value，内存泄漏** → 每次 map 删除操作泄漏一个 value；对于 NovaValue* 值，ref_count 永不递减 → 释放 entry 前调用 nova_value_release((NovaValue*)entry->value)
  - 追问：Rust 的 HashMap remove 会 drop 值。如果 GHC 的 Map.delete 不释放 thunk，能接受吗？

- [nova_runtime.c:651-668] **nova_map_release 不释放 entry 的 value，批量内存泄漏** → 整个 map 销毁时所有 value 全部泄漏；最严重的内存泄漏路径 → 遍历所有 entry，释放每个 value

- [nova_runtime.c:479-486] **nova_list_release 不释放元素，内存泄漏** → 所有列表元素永不释放；JSON 解析、列表推导式产生的列表全部泄漏 → 释放 items 数组前遍历释放每个元素

- [nova_runtime.c:749-756] **nova_adt_release 不释放字段值，内存泄漏** → 所有 ADT 变体的字段值永不释放；Option、Result、用户自定义 ADT 全部泄漏 → 遍历 fields 数组释放每个字段值

- [nova_runtime.c:791-798] **nova_closure_release 不释放捕获变量，内存泄漏** → 闭包捕获的所有变量永不释放；高阶函数、柯里化产生的闭包全部泄漏 → 遍历 captured 数组释放每个变量

- [nova_runtime.c:1701-1702, 1770-1771] **HTTP 状态码硬编码为 200，curl -w 完全被忽略** → 所有 HTTP 请求的响应状态码永远是 200；404、500、403 等错误完全无法检测 → 使用管道或第二个临时文件捕获 curl 的 -w 输出，解析真实状态码
  - 追问：如果 Python 的 requests 库永远返回 200 状态码，能投入生产吗？→ **结论：绝对不能。** 比没有 HTTP 支持更危险。

- [nova_runtime.c:536-538] **nova_map_put 中 void* 强转 NovaValue*，类型双关** → 依赖 NovaString 的 capacity 字段恰好位于 NovaValue.ref_count 的偏移位置且值 >= 16 来避免崩溃；属于未定义行为，一旦结构体布局变化立即内存损坏 → 统一使用 NovaValue* 作为 value 类型，或在 Map 结构中存储析构函数指针
  - 追问：GHC 的 RTS 中会允许 void* 强转后依赖内存布局巧合吗？→ **结论：绝对不能。**

- [nova_runtime.c:88-94] **GC 仅引用计数，无循环检测，循环引用永久泄漏** → 任何循环引用的数据结构都会永久泄漏；对于函数式语言，闭包与环境的循环、ADT 的自引用都是常见模式 → 实现标记-清除或引用计数+备份 tracing GC
  - 追问：纯引用计数的函数式语言运行时能叫生产级吗？→ **结论：不能。**

- [nova_runtime.c:577-594] **nova_map_get 不 retain 返回的 value，所有权语义混乱** → 返回的 value 指针不 retain；调用方持有指针期间如果 map 被释放或 key 被删除，会产生悬垂指针

**测试套件**：

- [test_nova.py 全文] **无 VM 与 Evaluator 行为一致性测试** → 0 个测试同时在两条执行路径上运行相同代码并比较结果；VM 和 Evaluator 可能对同一程序产生不同结果但完全无法发现 → 建立参数化测试框架
  - 追问：GHC 的解释器和编译后端有 100% 的一致性测试。两条路径结果可能不同但不验证，能发布吗？→ **结论：绝对不能。**

- [tree-sitter-nova/ 全文] **Tree-sitter 语法零测试** → 无 corpus 目录测试，无语法正确性验证；语法修改可能引入回归但完全无法检测 → 建立 tree-sitter 标准 corpus 测试

**Tree-sitter 语法**：

- [grammar.js:125-131] vs [parser.py:534-536] **match arm guard 位置与 parser.py 完全相反** → parser.py 中 guard 在 `->` 之前（Rust 风格），Tree-sitter 中 guard 在 `->` 之后（Swift 风格）；所有带 guard 的 match arm 在 Tree-sitter 中解析错误 → 将 Tree-sitter 的 guard 移到 `->` 之前

- [grammar.js:612-622] vs [parser.py:672-678] **管道运算符优先级与 parser.py 完全颠倒** → parser.py 中 pipe 优先级高于比较运算符；Tree-sitter 中 pipe 优先级低于 OR/AND/比较/相等；优先级关系完全颠倒 → 调整 Tree-sitter 优先级，将 PIPE 放在 COMPARISON 和 CONCAT 之间

#### 中等问题（影响特定场景）

**C 运行时**：
- nova_string_concat 双 NULL 分支引用计数多 1
- 函数指针从 void* 强转，不可移植（Harvard 架构）
- nova_read_file 使用 fseek/ftell 获取大小，二进制文件不保证（理论问题）
- fork + curl 实现 HTTP，资源消耗大且不可靠
- nova_http_post 的 Content-Type 硬编码为 application/json
- nova_string_split 末尾空字段行为未文档化

**测试套件**：
- 无边界值测试（大数、空值、极值）
- 负面测试覆盖率不足（运行时错误路径）
- 无端到端集成测试（编译→执行→验证输出）
- 并发/多线程测试为零

**Tree-sitter 语法**：
- 缺少 `?` 错误传播操作符（try 表达式）
- 缺少独立的 range 表达式（`..`）
- 列表推导式语法需确认是否完整

#### 轻微问题（代码质量）

- 临时文件命名不使用 mkstemp，有安全风险
- 测试命名风格不一致
- test_nova.py 一个文件 334 个测试，应拆分
- Tree-sitter 无语法错误恢复（error recovery）规则
- 缺少注释支持的显式 extras 规则

#### 测试覆盖统计表
| 测试文件 | 测试数量 | 主要覆盖领域 |
|----------|----------|-------------|
| test_nova.py | 334 | lexer、parser、typecheck、evaluator、ADT、pipe、builtins、loops、I/O、VM |
| test_type_system.py | 55 | 泛型 ADT、类型别名、类型推断、类型错误 |
| test_errors.py | 36 | 错误格式化、错误收集、错误恢复 |
| test_modules.py | 28 | 模块导入导出、循环依赖检测、命名空间 |
| test_ir.py | 93 | HIR/MIR/LIR lowering、pass manager、优化 pass |
| test_c_codegen.py | 52 | C 代码生成、类型映射、运行时集成 |
| test_backends.py | 43 | Cranelift、WasmGC、编译器管线 |
| test_native_backend.py | 99 | x86_64 发射、寄存器分配、原生代码生成 |
| **总计** | **740** | |

---

## 第十七轮架构级建议（优先级排序）

### 🔴 P0 级（立即修复，安全/正确性基石）

1. **修复类型检查器 TypeVar 万能兼容问题** → 类型系统基本失效，等于没有类型检查
2. **修复 STORE_VAR 语义错误（作用域模型）** → 违反静态作用域原则，赋值静默创建全局变量
3. **修复模块系统路径遍历安全漏洞** → P0 安全漏洞，可读取系统任意文件
4. **修复 MIR Match 完全退化问题** → 整个 IR 优化管道的 match 控制流完全错误
5. **修复 LIR Phi 节点只取第一个 source** → SSA 语义彻底破坏，所有控制流汇合点值错误
6. **修复嵌套模式匹配栈破坏** → 函数式语言核心特性的 P0 缺陷
7. **修复 CLOSURE 全量捕获（自由变量分析）** → 函数式语言核心语义的性能+正确性问题
8. **修复 C 运行时嵌套容器释放不递归** → 大规模内存泄漏，列表/Map/ADT/闭包全部只释放外壳

### 🟠 P1 级（高优先级，影响功能正确性）

9. **实现真正的 HM 类型推断（unification + let-polymorphism）** → 类型系统的架构级重构
10. **修复块级作用域缺失问题** → VM 中 for/match/if 的变量泄漏
11. **修复 NovaConstructor 不支持柯里化** → 函数式语言一等构造器的基本要求
12. **修复管道操作符优先级错误** → 函数式语言核心运算符的解析错误
13. **修复 `?` 操作符不在后缀循环内** → 错误传播操作符核心用法失效
14. **修复 AST 节点 span 信息不完整** → 错误报告和 IDE 功能的基础
15. **添加 Evaluator-VM 一致性测试框架** → 多后端语言的基本质量要求
16. **修复错误信息缺少文件名** → 多文件项目调试几乎不可用
17. **修复嵌套相对导入 current_file 缺失** → 模块系统的核心功能缺陷
18. **修复 HTTP 状态码硬编码 200** → 比没有 HTTP 支持更危险的误导性功能
19. **修复 Tree-sitter 与 parser.py 语法不一致** → guard 位置 + pipe 优先级两处严重不一致

### 🟡 P2 级（中优先级，影响质量/可维护性）

20. **统一闭包语义（引用 vs 值快照）** → 语言规范级别的分歧
21. **修复 while 循环 CONTINUE 依赖启发式检测**
22. **修复 BREAK 前向扫描脆弱设计**
23. **接入 Native 后端到编译管道**
24. **修复 Cranelift 后端 SSA 值传播**
25. **重写 Wasm 后端控制流翻译**
26. **实现 Parser 语法错误恢复**
27. **添加 C 后端端到端测试**
28. **修复迭代器字典异常路径泄漏**
29. **修复词法错误非结构化问题**
30. **实现模式匹配穷尽性检查**

### 🟢 长期规划

31. **实现真正的 GC（标记-清除或分代 GC）**
32. **重写 IR 降级链，实现真正的 SSA + Phi 消除**
33. **建立模块命名空间系统，摆脱 import * 模式**
34. **实现 Tree-sitter 语法与 parser.py 的完全对齐**
35. **添加 fuzz 测试、属性测试、边界值测试**
36. **实现 LSP 语言服务器支持**


---

## [2026-07-15] 第十八轮全面代码审查报告

> **审查轮次**：第18轮
> **审查标准**：生产级编译器/语言标准（参考 OCaml/Haskell/Elm/F# 最佳实践）
> **审查范围**：全部 9 个模块（VM、编译器、求值器、类型检查器、词法/语法、错误处理+模块+环境、后端、IR、运行时+测试+Tree-sitter）

---

## [2026-07-15] VM 虚拟机 (vm.py) 第十八轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | 模式匹配字节码、FOR_ITER 栈式迭代、TRY_UNWRAP 指令有特色 |
| 可行性 | ⭐⭐⭐ | 核心路径可用；多处结构性问题 |
| 正确性 | ⭐⭐ | 嵌套模式匹配栈泄漏、FOR_ITER BREAK off-by-one、RETURN 语义不一致 |
| 安全性 | ⭐⭐ | 循环状态异常泄漏、函数调用不保存循环状态 |
| 一致性 | ⭐⭐ | 与 Evaluator 在闭包语义、作用域、构造器柯里化等方面差异显著 |
| 完整性 | ⭐⭐⭐⭐ | 64 条指令全部实现 |
| 工程质量 | ⭐⭐⭐ | 代码可读但结构混乱，循环状态管理脆弱 |
| 性能 | ⭐⭐⭐ | 纯 Python 解释型 VM，无指令派发优化 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [vm.py:1159-1209] **嵌套模式匹配（构造器/元组/列表）失败路径栈泄漏** → 嵌套子模式测试失败时，栈上残留已解构的中间值；虽然 MATCH_TEST_* 失败时不 pop，但外层解构已替换栈顶，fail_cleanup 的单次 POP 不足以恢复 → 在 MATCH_START 记录 match_base_sp，失败时由 VM 统一恢复栈
  - 追问：如果 OCaml 的模式匹配编译器在嵌套模式失败时不恢复栈，能被接受吗？→ **结论：绝对不能。** 模式匹配是函数式语言的核心控制流。

- [vm.py:833] **FOR_ITER BREAK 的 result_list 索引 off-by-one** → `result_list = self.stack[base_sp + 1]` 应为 base_sp + 2；FOR_ITER 首次迭代时栈为 `[..., iterable, result_list, current]`，base_sp = len(stack) - 3，base_sp+1 是 iterable，base_sp+2 才是 result_list → 修正索引为 base_sp + 2
  - 追问：如果 for 循环 break 后返回值是迭代器本身而非结果列表，能被接受吗？→ **结论：绝对不能。** 这是 for 表达式返回值语义的根本错误。

- [vm.py:1291-1292] **TRY_UNWRAP None/Err 路径栈顶值未清理，顶层代码栈泄漏** → TRY_UNWRAP 遇到 None/Err 时返回 True（提前返回信号）但不弹出栈顶值；函数中由 _call_closure 截断栈没问题，但顶层代码中 break 后栈上残留 None/Err 值 → 顶层 TRY_UNWRAP 失败时应弹出值或在 break 前清理

- [vm.py:430-457] **函数调用时 _for_iters/_while_loops 不保存/恢复，异常退出后循环状态混乱** → `_call_closure` 的 finally 只恢复 code/constants/ip/call_stack，不清理循环状态；函数体内的循环因异常退出时，_for_iters 和 _while_loops 中残留条目，调用方继续执行另一个循环时状态错乱 → 函数调用前保存循环状态，返回后恢复

- [vm.py:467-471 vs 891-896] **RETURN 指令两处处理语义不一致，存在逻辑冗余和潜在风险** → `_execute_function` 中 pop 值并 return，`_execute_instruction` 中 pop 再 push + set return_flag；函数执行时前者优先，后者是死代码；顶层执行时后者生效但语义不同 → 统一 RETURN 实现，消除死代码

- [vm.py:755-758] **while 循环启发式检测（JUMP + CONST_UNIT）脆弱且不可靠** → 通过"向后跳 + 下一条指令是 CONST_UNIT"的启发式推断 loop_start，依赖代码生成的特定模式；嵌套循环或非 while 向后跳转可能错误修改循环状态 → 编译器通过操作数显式传递循环元数据

#### 中等问题（影响特定场景）

- [vm.py:925-935] BUILD_MAP 不检查 key 可哈希性 → list 等不可哈希键会抛出 Python 原生 TypeError
- [vm.py:657-663] NEG 只检查 Bool，未检查其他非数值类型 → 字符串、列表等取反会抛 Python 错误
- [vm.py:572-576] LOAD_CONST 无边界检查 → 索引越界时抛 IndexError
- [vm.py:986-1005] FOR_ITER range 迭代的 start/end/step 无类型检查 → 非数值类型会导致 Python 原生错误
- [vm.py:986-1069] 异常路径下 _for_iters/_range_index/_list_index 泄漏 → 异常退出时不清理循环状态
- [vm.py:898-908] CALL_BUILTIN 参数过多时抛出 Python 原生错误而非 RuntimeError_
- [vm.py:220-223] 内置函数 _to_float 不做类型检查 → 字符串等传入会抛 Python 错误
- [vm.py:1020] for 循环变量无独立作用域，闭包捕获语义与 evaluator 不一致 → 经典闭包变量捕获问题

#### 轻微问题（代码质量）

- [vm.py:30-43] UNIT_TYPE 单例与 evaluator 的 None 表示不一致
- [vm.py:1255-1260] DUP 手动栈检查与 _pop 风格不一致
- [vm.py:1084-1142] MATCH_TEST_* 系列手动栈检查，错误信息格式不统一
- [vm.py:1262-1269] PRINT 指令与 print 内置函数功能重复
- [vm.py:1302-1306] LOOP 指令是死代码，编译器不使用
- [vm.py:495-497] _auto_call_main 不识别 NovaPartialBuiltin 和 NovaConstructor
- [vm.py:988, 1032] _range_index/_list_index 惰性初始化是反模式

#### 原创性分析

- **Nova 特色**：模式匹配专用字节码指令集、FOR_ITER + LOOP_END 栈式迭代设计、TRY_UNWRAP 独立指令实现错误传播、BREAK/CONTINUE 通过操作数有无区分循环类型的约定
- **参考已有**：基本栈机结构参考 CPython/JVM；闭包实现参考 Lua upvalue 思路（但实现质量低）；循环控制参考 CPython 的迭代器协议

#### Evaluator vs VM 对比（本轮新发现）
| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| Unit 值表示 | _UnitValue 普通类单例 | UNIT_TYPE __new__ 真正单例 | ⚠️ 机制不同 |
| 构造器函数表示 | BuiltinFn（支持柯里化） | NovaConstructor（不支持部分应用） | ❌ |
| 内置函数部分应用类型 | BuiltinFn | NovaPartialBuiltin（独立类型） | ❌ |
| for 循环变量作用域 | 每次迭代新环境，闭包捕获不同值 | 同一帧 locals，闭包共享变量 | ❌ |
| 块级作用域 | 每个 Block 创建子环境 | 无块级作用域概念 | ❌ |
| 闭包捕获机制 | Environment 引用（引用语义） | captured_vars 字典拷贝（值语义） | ❌ |
| 递归深度保护 | 仅 NovaClosure 递增 | 与 call_stack 绑定 | ⚠️ 机制不同 |

---

## [2026-07-15] 编译器 (compiler.py) 第十八轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | PIPE_CALL 专用指令、MATCH_START/END 标记、ADT 原生指令集 |
| 可行性 | ⭐⭐⭐⭐ | 核心路径可用；相比首轮大幅改进 |
| 正确性 | ⭐⭐ | 嵌套模式匹配栈破坏、闭包全量捕获、变体名泄漏 |
| 安全性 | ⭐⭐⭐ | 栈布局大部分路径正确；嵌套模式失败路径有栈下溢风险 |
| 一致性 | ⭐⭐⭐ | 跳转回填全部正确；指令定义与生成存在多处不一致 |
| 完整性 | ⭐⭐⭐⭐ | AST 节点基本全覆盖 |
| 工程质量 | ⭐⭐ | 大量死代码、重复代码、未使用操作码定义 |
| 性能 | ⭐⭐ | 闭包全量捕获 dict 浅拷贝；常量未入池导致代码膨胀 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [compiler.py:836-861] **嵌套模式匹配失败时栈不平衡（栈破坏）** → PatternConstructor/PatternTuple/PatternList 的子元素模式匹配失败时，栈上残留已被外层 deconstruct 压入的未测试元素值，fail_cleanup 只 POP 一次远远不够 → 每个失败点应回填到各自专属的清理代码路径，或在 MATCH_START 记录栈基址由 VM 统一恢复
  - 追问：如果 OCaml 的模式匹配编译器在嵌套模式失败时不恢复栈，能被接受吗？→ **结论：绝对不能。** 模式匹配是函数式语言的核心控制流。

- [compiler.py:402, 682] **闭包捕获整个帧 locals 而非仅自由变量** → CLOSURE 指令发射时不分析自由变量，VM 端全量浅拷贝；Op 类定义 CLOSURE 有 3 个操作数但实际只发射 2 个，第三个本应用于传递自由变量列表 → 编译器实现自由变量分析，CLOSURE 指令携带捕获变量名列表

- [compiler.py:357-358 vs 272-288] **导入模块的 TypeDef 泄漏所有变体名到当前作用域** → 只检查 TypeDef 的名称是否导出，但一旦类型被导出，其所有变体都会被注册到 _adt_constructors 并通过 STORE_VAR 进入全局命名空间；导出 Color 会导致 Red/Green/Blue 全部泄漏 → 实现命名空间隔离或变体名前缀

- [compiler.py:825-834] **有字段构造器的 PatternIdentifier 被当作变量绑定** → 对于有字段的构造器（如 Some），如果用户写 `match expr { Some -> ... }`（不带括号），编译器当作普通变量绑定而非构造器模式；用户可能期望 Some 是构造器模式（零参数形式） → 明确语法规范，或将所有构造器名都识别为模式

- [compiler.py:805-808 vs vm.py:1118-1129] **MATCH_TEST_FLOAT 使用精确相等比较，语义危险** → 浮点数精确相等比较是生产级语言的大忌；`0.1 + 0.2` 匹配 `0.3` 会失败 → 禁止浮点字面量模式或添加 epsilon 比较

- [compiler.py:420-421] **CharLiteral 编译为 CONST_STRING，字符与字符串边界完全模糊** → Char 类型在运行时就是长度为1的字符串；类型检查器的 Char 类型是"凭空"的，运行时无独立表示 → 用单独的 NovaChar 类或添加 CONST_CHAR 操作码

#### 中等问题（影响特定场景）

- [compiler.py:906-971] _compile_pattern_test 和 _compile_pattern_bindings 是死代码（约65行）
- [compiler.py:597-602] 管道操作中内置函数走 LOAD_VAR 路径，与直接 CALL_BUILTIN 效率不一致
- [compiler.py:337-370] 多次 import 同一模块会重复编译声明
- [compiler.py:496-506] for 循环中的 BREAK/CONTINUE 依赖 VM 隐式状态，编译器无校验
- [compiler.py:225-227, 1047-1049] while 循环的 _while_start_stack 和 _while_end_stack 假设一一对应
- [compiler.py:628-639] MAKE_ADT 的 field_count 取实际参数数量，不校验构造器定义
- [compiler.py:513-517 vs vm.py:925-935] BUILD_MAP 的键值对顺序依赖 _pop 反转语义，脆弱易错
- [compiler.py:81] CLOSURE 操作码注释的操作数与实际不符

#### 轻微问题（代码质量）

- [compiler.py:75] LOOP 指令定义但编译器从未使用
- [compiler.py:48] LOAD_CONST 定义但编译器从未使用，常量池形同虚设
- [compiler.py:972-980] 块中 BreakExpr/ContinueExpr 后的死代码仍被编译
- [compiler.py:168-177] Bytecode.add_const 的去重使用 list.index，O(n) 复杂度
- [compiler.py:617, 642, 652] _compile_fn_call 中 callee_on_stack 变量多余
- [compiler.py:599-602] pipe 中内置函数的 if/else 分支完全相同

#### 原创性分析

**独特设计亮点**：
1. MATCH_* 系列指令的"成功时 pop、失败时保留"语义——简化嵌套模式编译
2. FOR_ITER + LOOP_END 配对的 for 循环模型——迭代管理与结果收集分离
3. PIPE_CALL 专用指令——语言级管道操作的直接映射
4. TRY_UNWRAP 的"提前返回信号"机制——通过返回 bool 嵌入执行循环
5. MATCH_CONSTRUCTOR 成功时解构压栈——嵌套模式递归编译无需额外解构指令

**总体原创性：中等偏上**。核心是经典栈式 VM 设计，但模式匹配指令集和 for 循环模型有一定特色。

---

## [2026-07-15] 求值器 (evaluator.py) 第十八轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 经典 AST 遍历解释器，无特别新颖设计 |
| 可行性 | ⭐⭐⭐⭐ | 核心功能基本可用，能运行大部分 Nova 程序 |
| 正确性 | ⭐⭐⭐ | Block 异常安全漏洞、与 VM 闭包语义分歧等实质问题 |
| 安全性 | ⭐⭐ | 文件 I/O 无路径限制、递归深度保护不完整 |
| 一致性 | ⭐⭐ | 与 VM 在闭包语义、Unit 单例、构造器柯里化等方面不一致 |
| 完整性 | ⭐⭐⭐⭐ | 大部分 AST 节点已覆盖 |
| 工程质量 | ⭐⭐⭐ | 代码结构清晰，但存在大量重复 |
| 性能 | ⭐⭐⭐ | 直接 AST 遍历性能尚可，无尾调用优化 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [evaluator.py:761-771] **Block 求值无异常安全保证，环境泄漏** → `self.env` 被切换为 child_env，但整个过程没有 try/finally 保护；块内语句抛出任何异常（BreakSignal、ContinueSignal、RuntimeError_、ReturnSignal）时，self.env 将停留在 child_env 上，不会恢复到 old_env → 添加 try/finally 确保环境恢复
  - 追问：如果 JavaScript 的 with 语句在异常时不恢复作用域，能被接受吗？→ **结论：绝对不能。** 词法作用域是语言的基础，异常时作用域泄漏是根本性错误。

- [evaluator.py:408-414] **内置函数部分应用绕过调用深度检查** → BuiltinFn 的部分应用返回新的 BuiltinFn(curried 闭包)，curried 内部直接调用 `fn.fn(*(args + list(more_args)))`，不经过 _call_fn；递归深度计数器 _call_depth 不会递增，BreakSignal/ContinueSignal 不会被拦截 → 将部分应用的再调用也纳入 _call_fn 主入口

- [evaluator.py:718-727] **TryExpr `?` 对非 Option/Result 的 ADT 检查重复且逻辑冗余** → 第719行已检查 type_name 必须是 Option 或 Result，第726行的 raise 永远不可达；如果构造出畸形 ADT 值，错误消息会误导 → 移除死代码，优化错误消息

#### 中等问题（影响特定场景）

- [evaluator.py:384-404] _format_value 对 dict/Map 类型无特殊处理，使用 Python 默认格式
- [evaluator.py:862] IndexExpr 对字符串索引返回字符串而非字符，与 Char 类型语义不一致
- [evaluator.py:800] MapExpr 键求值顺序无保证且重复键静默覆盖
- [evaluator.py:200-204] str_len 和 list_length 函数名不对称且无类型检查
- [evaluator.py:214-215] _builtin_sum 无类型检查，布尔值会被当作 int 求和
- [evaluator.py:1056-1078] 守卫条件的求值环境与 body 环境是兄弟关系，有冗余开销

#### 轻微问题（代码质量）

- [evaluator.py:571-626] eval_decl 与两遍扫描代码大量重复（重复率超 80%）
- [evaluator.py:530 vs 610] TypeDef 构造器注册中，无字段构造器的 field_names 在两处不一致
- [evaluator.py:335-336] _builtin_abs 总是返回 float，丢失整数类型信息
- [evaluator.py:101-104] _UnitValue 没有 __eq__ 方法，依赖默认身份比较
- [evaluator.py:182-186 vs vm.py:181] read_line 在 evaluator 和 VM 中行为有细微差异
- [evaluator.py:220-227] _builtin_tail 空列表的 field_names 与全局 None 单例不一致

#### 原创性分析

Nova 求值器属于经典的直接 AST 遍历解释器，可追溯到 Lisp 的 eval/apply 模型。特色在于：
1. **两遍扫描**：支持前向引用和互递归函数，这在解释器中不太常见
2. **Environment 链式作用域**：经典但实现质量不错
3. **? 操作符的 ReturnSignal 传播**：Rust 风格错误处理在解释器中的直接映射

**原创性评分：中等偏低**。实现方式是教科书级别的，没有明显的原创性贡献。作为参考实现是合格的。

#### Evaluator vs VM 对比（本轮新发现）
| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| Unit 值表示 | _UnitValue 普通类单例 | UNIT_TYPE __new__ 真正单例 | ⚠️ 机制不同 |
| 构造器函数表示 | BuiltinFn（支持柯里化） | NovaConstructor（不支持部分应用） | ❌ |
| 内置函数部分应用类型 | BuiltinFn | NovaPartialBuiltin（独立类型） | ❌ |
| for 循环变量闭包捕获 | 每次迭代不同绑定 | 同一变量共享 | ❌ |
| 块级作用域 | 每个 Block 子环境 | 无块级作用域 | ❌ |
| 闭包捕获语义 | Environment 引用（引用语义） | dict 拷贝（值语义） | ❌ |
| read_line 多余参数 | 抛 Python TypeError | 静默返回空字符串 | ❌ |
| 递归深度保护 | 仅 NovaClosure 递增 | 与 call_stack 绑定 | ⚠️ 机制不同 |

---

## [2026-07-15] 类型检查器 (type_checker.py) 第十八轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 类型推断算法 | ⭐ | 非真正 HM，TypeVar 是通配符，无约束传播；推断结果不写回环境 |
| 泛型/ADT 类型比较 | ⭐⭐⭐⭐ | __eq__ 正确比较类型参数，但 _types_compatible 中 TypeVar 破坏正确性 |
| Pattern 类型检查 | ⭐⭐⭐ | 所有 Pattern 有基本检查，但缺少穷尽性和守卫检查 |
| 错误恢复 | ⭐⭐⭐ | ErrorCollector 存在但有 bug，收集模式下基本可用 |
| 类型标注支持 | ⭐⭐⭐⭐ | 支持基本/泛型/函数/元组/ADT/别名 |
| 递归 ADT | ⭐⭐⭐ | 结构上支持递归 ADT 定义，但递归函数推断失效 |
| Let 多态 | ⭐ | 完全缺失，无 generalization/instantiation |
| 类型统一 | ⭐ | 无真正的 unification，只有单向绑定 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [type_checker.py:1349-1377] **_types_compatible 缺少 TupleType 递归兼容检查** → 对 FnType、ListType、MapType、ADTType 都有递归兼容检查，但完全遗漏了 TupleType；含 TypeVar 的元组类型在 if 分支统一、列表元素统一等场景会产生误报 → 添加 TupleType 的递归兼容检查
  - 追问：如果 OCaml 的类型检查器对元组类型不做兼容检查，能被接受吗？→ **结论：绝对不能。** 元组是基础类型，类型系统必须完整覆盖。

- [type_checker.py:796-807] **Assignment 完全不检查目标是否为可变绑定** → 赋值操作只检查目标是否存在、类型是否兼容，从不检查目标是 let（不可变）还是 mut（可变）；可以对不可变的 let 绑定赋值而不报错 → 在 Assignment 检查中验证绑定的可变性
  - 追问：如果 Haskell 中可以对 let 绑定重新赋值，能叫函数式语言吗？→ **结论：绝对不能。** 不可变性是函数式语言的核心原则。

- [type_checker.py:276-282] **内置 Option/Result 未注册到 env.types，裸类型名无法识别** → _setup_builtins 中注册了 adt_variants、adt_type_params 和构造函数，但从未将 "Option"/"Result" 本身加入 env.types；类型标注中写 `Option`（不带类型参数）时报 "未知类型名" → 将内置类型名注册到 env.types

- [type_checker.py:941-947, 981-984] **ForExpr/ListComprehension 的 range 形式完全不检查 start/end/step 类型** → start_ty、end_ty、step 的计算结果直接被丢弃，从不验证它们是 Int 类型；`for i <- "a".."z" step true` 不产生类型错误 → 添加 Int 类型验证

- [type_checker.py:543-563] **两阶段检查中，函数的推断返回类型从未写回环境** → 第一遍用 TypeVar 占位注册函数类型，第二遍检查了函数体并得到 body_type，但从未用推断出的 body_type 更新环境中注册的函数类型；所有无返回类型标注的函数始终返回 TypeVar（万能兼容） → 第二遍检查后更新环境中的函数类型
  - 追问：如果 OCaml 的类型推断器推断了函数类型但不记录，能被接受吗？→ **结论：绝对不能。** 推断结果不持久化等于没有推断。

#### 中等问题（影响特定场景）

- [type_checker.py:928-932] TryExpr 仅按名字匹配 Option/Result，用户自定义同名类型会误触发
- [type_checker.py:759-770] PipeExpr 右侧非函数类型时完全静默，不报错
- [type_checker.py:677-689] Match 穷尽性检查完全缺失
- [type_checker.py:1060-1066] 构造器在表达式和模式中使用不同的查找路径，结果可能不一致
- [type_checker.py:953-954, 989-990] ForExpr/ListComprehension 迭代元组时取第一个元素类型不合理
- [type_checker.py:1225-1227] _collect_type_bindings 无类型变量冲突检测，"先到先得"
- [type_checker.py:1353-1354] TypeVar 被当作万能通配符，类型系统本质不可靠（已知问题但需强调）

#### 轻微问题（代码质量）

- [type_checker.py:613, 631-632] 空列表/空 Map 的 TypeVar 名使用硬编码字符串
- [type_checker.py:812-819] FieldAccess 元组非数字字段名时报"索引越界"，错误消息误导
- [type_checker.py:973-977] BreakExpr/ContinueExpr 不在循环中时不报错
- [type_checker.py:1162-1166] 比较运算符不支持 String 和 Char
- [type_checker.py:689] Match 零分支时返回 UNIT_T 而非报错
- [type_checker.py:1296-1318] TypeGeneric 参数数量错误时静默截断/填充

#### 原创性分析

这个类型检查器不是 Hindley-Milner，甚至不是约束生成+求解的两阶段方法。它本质上是一个**带有 TypeVar 逃逸口的符号执行器**——遍历 AST 计算类型，遇到未知就塞一个 TypeVar，而 TypeVar 在 _types_compatible 中是万能通行证。

**与成熟语言的对比**：
- 最接近的类比是早期 C 语言（K&R C）的隐式 int 规则
- 不像 OCaml/Haskell（真正的 HM）
- 不像 TypeScript（有 structural typing 和 any 类型，但 any 是显式的）

---

## [2026-07-15] 词法/语法分析器 (lexer.py + parser.py) 第十八轮审查报告

### 总体评分

#### Lexer (lexer.py)
| 维度 | 评分 | 说明 |
|------|------|------|
| Token 覆盖完整性 | ⭐⭐⭐⭐ | 基本覆盖主要语法元素；缺少科学计数法、多进制数字、数字分隔符、块注释 |
| 词法错误恢复 | ⭐⭐⭐ | 能跳过非法字符，但错误非结构化、_make_error 死代码 |
| 位置信息准确性 | ⭐⭐ | _make_error 的 end_col 恒等于 start_col，跨度信息无效 |
| 字符串处理完整性 | ⭐⭐ | 缺少多行字符串、原始字符串、Unicode 转义 |
| 数字字面量完整性 | ⭐⭐ | 缺科学计数法、十六进制/八进制/二进制、数字分隔符 |
| 注释处理完整性 | ⭐⭐ | 仅支持单行注释，无块注释 |
| 生产就绪度 | ⭐⭐⭐ | 核心路径可用，边缘场景覆盖不足 |
| 代码质量 | ⭐⭐⭐ | 结构清晰但有死代码和重复 |

#### Parser (parser.py)
| 维度 | 评分 | 说明 |
|------|------|------|
| 运算符优先级正确性 | ⭐⭐ | 管道优先级设计存疑；? 不在后缀循环内；比较/相等性应为无结合性 |
| 结合性正确性 | ⭐⭐⭐⭐ | 大部分运算符左结合正确；一元运算符右结合正确 |
| 语法歧义处理 | ⭐⭐⭐ | 悬挂 else 已通过 then 关键字解决；map/block 消歧依赖前瞻扫描 |
| 左递归处理 | ⭐⭐⭐⭐⭐ | 递归下降 + 优先级分层正确消除左递归 |
| 错误位置准确性 | ⭐⭐ | 绝大多数 AST 节点 span 仅含起始 token |
| 错误恢复能力 | ⭐ | 完全没有错误恢复，遇错即停 |
| AST 生成完整性 | ⭐⭐⭐⭐ | 大部分语法结构有对应 AST 节点 |
| 生产就绪度 | ⭐⭐ | 核心功能可用，缺少错误恢复、位置信息不完整 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [lexer.py:155-160] **_make_error 方法中的 end_col 计算永远等于 start_col-1，导致跨度错误** → `end_col = self.column - 1` 与 `column == self.column` 结合，`max(column, end_col) = column`，跨度恒为单字符；多字符错误（如未闭合字符串）跨度完全不准确 → 修正 end_col 计算
  - 追问：如果 GCC 的词法错误跨度只有 1 个字符（即使是整行错误），能被接受吗？→ **结论：不能。** 错误位置精度直接影响诊断质量。

- [parser.py:764-767] **`?` 操作符不在后缀循环内——链式错误传播完全失效** → `?` 被放在后缀循环之外处理，`expr?.field`、`expr?[index]`、`expr?(args)` 等常见链式错误传播用法无法工作；Rust/Swift/Kotlin 中 `?` 是后缀操作符，与字段访问/函数调用同优先级 → 将 `?` 的处理移入 `_parse_postfix_expr` 的 while 循环内
  - 追问：如果 Rust 的 `?` 运算符不能链式调用（`expr?.method()`），能被接受吗？→ **结论：不能。** 这是错误传播操作符的核心用法模式。

- [parser.py:672-678] **管道操作符优先级严重错误（确认未修复）** → `_parse_comparison_expr` 调用 `_parse_pipe` 获取操作数，管道优先级高于比较操作符；与函数式语言常规（Elixir/OCaml/F# 中管道通常是最低优先级之一）以及 grammar.js（PREC.PIPE = 2）完全矛盾 → 调整优先级链，将 `_parse_pipe` 放在 `_parse_or_expr` 之下
  - 追问：如果 GCC/Clang 的运算符优先级表与语言规范矛盾，能被接受吗？→ **结论：绝对不能。** 优先级错误是编译器前端最严重的错误类别之一。

- [parser.py:464-466, 968-970] **`<-` 左箭头无专用 token——LT + MINUS 手动组合脆弱且错误** → `<-` 不是专用 token，而是通过 LT + MINUS 两个 token 手动组合；`x < -y` 可能被误解析为 `x <- y`；错误消息不准确 → 在 lexer 中添加 LEFT_ARROW token
  - 追问：如果 Haskell 的 `<-` 是由两个 token 手动组合的，能被接受吗？→ **结论：不能。** 多字符运算符应该在词法层面识别。

- [parser.py:386-391] **块中赋值语句检测仅检查 IDENT + ASSIGN，无法处理复合赋值目标** → 只能检测简单的 `ident = expr` 形式；索引赋值 `arr[0] = 5`、字段赋值 `obj.field = 10` 会被当作表达式语句解析 → 扩展赋值检测或重新设计语句/表达式消歧策略

- [parser.py:522] **match arm 起始 token 列表缺少 CHAR 和 MINUS（负数模式）** → while 条件列出的 pattern 起始 token 不完整；字符字面量和负数开头的 match arm 不会被识别为新 arm → 补充完整的 pattern 起始 token 列表

#### 中等问题（影响特定场景）

- [lexer.py:202-221] 数字字面量不支持科学计数法（`1e10`, `3.14e-2`）
- [lexer.py:208-216] 数字字面量不支持数字分隔符（`1_000_000`）
- [lexer.py:202-221] 数字字面量不支持不同进制（二进制 `0b`、八进制 `0o`、十六进制 `0x`）
- [lexer.py:240-251] 字符串转义序列不支持 `\0`、`\xHH`、`\u{...}`
- [parser.py:844-884] _is_map_literal 前瞻扫描可能在错误代码中超长距离扫描（O(n)）
- [lexer.py:69, 88] PIPE 和 PIPE_VARIANT 是同一字符的两种语义，但 token 类型只有 PIPE，PIPE_VARIANT 是死代码
- [lexer.py:91, 368-372] UNIT token 类型存在但词法分析器从不产生
- [parser.py:672-677] 比较操作符用 while 循环实现左结合，应为无结合性（non-associative）
- [parser.py:642-650] 相等性操作符同样应为无结合性，链式比较会产生意外 AST

#### 轻微问题（代码质量）

- [parser.py:57-62] _advance 在到达 EOF 时仍然返回最后一个 token，无明确错误指示
- [lexer.py:256, 265, 279, 306, 457] 词法错误使用 print() 直接输出到 stderr，破坏错误收集器统一管理
- [lexer.py:155-160] _make_error 方法从未被使用（死代码）
- [parser.py:530-539] _parse_match_arm 不返回 span 信息，MatchArm 无 span
- [lexer.py:109-110] Token.__repr__ 不显示 end_line/end_col
- [parser.py:367-370] _parse_expression_statement 是多余包装
- [lexer.py:186-200] _skip_whitespace_and_comments 不处理块注释

#### 原创性分析

**词法分析器**：低原创性（⭐⭐）。标准的递归式词法分析器设计。

**语法分析器**：中等原创性（⭐⭐⭐）。递归下降解析器是标准做法，但 Nova 的优先级分层设计清晰，表达式导向的语言特性实现得比较完整。特色：map 字面量与 block 的区分通过前瞻扫描实现、管道操作符作为独立 AST 节点、`?` 操作符的 TryExpr 节点。

#### 运算符优先级表（实际实现）
| 优先级 | 运算符/结构 | 结合性 | 解析函数 |
|--------|------------|--------|----------|
| 1（最低） | for / while | N/A | _parse_for_while_expr |
| 2 | if-then-else | N/A | _parse_if_expr |
| 3 | match | N/A | _parse_match_expr |
| 4 | \|\| (OR) | 左 | _parse_or_expr |
| 5 | && (AND) | 左 | _parse_and_expr |
| 6 | ==, != | 左（应为无） | _parse_equality_expr |
| 7 | <, >, <=, >= | 左（应为无） | _parse_comparison_expr |
| 8 | \|> (PIPE) | 左 | _parse_pipe |
| 9 | ++ (CONCAT) | 左 | _parse_cons_expr |
| 10 | +, - | 左 | _parse_additive_expr |
| 11 | *, /, % | 左 | _parse_multiplicative_expr |
| 12 | -, !（一元） | 右 | _parse_unary_expr |
| 13 | f(), .field, [index] | 左 | _parse_postfix_expr |
| 14 | ? (try) | N/A | _parse_postfix_expr（循环外）|
| 15（最高） | 字面量, 标识符, (), [], {}, \|\| | N/A | _parse_primary_expr |

---

## [2026-07-15] 错误处理 + 模块系统 + 环境 第十八轮审查报告

### 总体评分
| 维度 | 错误处理 (errors.py) | 模块系统 (modules.py) | 环境 (environment.py) |
|------|---------------------|----------------------|---------------------|
| 正确性 | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| 完整性 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 安全性 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| 一致性 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| 可维护性 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 错误恢复能力 | ⭐⭐⭐ | ⭐⭐ | N/A |
| 生产就绪度 | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| 测试覆盖 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [errors.py:167-171] **span.end_column 未做 None 校验，可能导致 None 赋值给 end_col** → 只检查了 `self.span.end_line is not None`，直接使用 `self.span.end_column`；如果 span 有 end_line 但 end_column 为 None，后续位置文本格式化和下划线计算会崩溃（TypeError） → 添加 end_column 的 None 校验
  - 追问：如果 Rust 编译器的 span 信息不完整时会崩溃，能被接受吗？→ **结论：不能。** 错误格式化是编译器的门面，自身不能崩溃。

- [errors.py:102-104] **highlight_span 仅在单行时设置，多行 span 丢失高亮信息** → 只有当 `span.line == span.end_line` 时才设置 `self.highlight_span`；多行错误的后备路径完全失效 → 为多行错误也设置 highlight_span 或移除后备路径

- [modules.py:244-245, 655-660] **导出名称不验证存在性，导入绑定静默失败** → _collect_exports 在类型检查之前执行，导出了不存在的名称也不会被发现；evaluator 的导入用 try/except 包裹 lookup，不存在就静默跳过；两边都静默失败意味着变量不存在但无任何错误提示 → 在类型检查阶段验证导出名称的存在性，导入失败时报明确错误
  - 追问：如果 Python 的 import 导入不存在的名称时静默失败而不报错，能被接受吗？→ **结论：绝对不能。** 导入失败是最基本的错误类型。

- [modules.py:124-130] **无路径遍历防护，存在目录穿越安全漏洞** → 相对路径导入直接使用 os.path.join 后接 abspath，没有检查确保最终路径不超出允许的目录范围；恶意模块可通过 `../../etc/passwd` 读取系统任意文件 → 解析后检查最终路径是否在允许的搜索路径内
  - 追问：如果 Deno 允许 import 路径通过 `../` 穿越到任意系统目录，能被接受吗？→ **结论：绝对不能。** 这是沙箱安全的基础。

- [environment.py:34-40 + modules.py:330] **lookup 不返回可变性信息，导入的 mut 变量丢失可变性** → Environment.lookup 只返回值，不返回可变性；模块导入硬编码 mutable=False；如果模块导出了 mut 变量，导入方会得到不可变的副本，赋值失败且错误信息误导 → 统一使用 lookup_binding，导入时保留可变性信息

#### 中等问题（影响特定场景）

- [errors.py:179] ctx_end 使用 end_line + 1 导致多显示一行上下文（off-by-one）
- [errors.py:244] note_start 使用 `note_idx - 0`，代码冗余且上下文显示不对称
- [errors.py:409-410] raise_all 将后续错误转为字符串 note，丢失结构化信息（span、severity）
- [modules.py:124-130] 相对路径导入依赖 search_paths[0] 为 current_dir，脆弱且可能失效
- [modules.py:293-299] _collect_exported_types 完全忽略 type_checker 参数
- [modules.py:358-363] 全局默认搜索路径与 ModuleResolver 默认路径不一致
- [environment.py:67-73] all_bindings 方法只返回值，不返回可变性和绑定来源层级

#### 轻微问题（代码质量）

- [errors.py:93] highlight_span 字段命名不一致（元组 vs Span 对象）
- [errors.py:216-229] 相关注释的颜色/标签逻辑重复
- [errors.py:260] note 下划线单字符 `^`，与主错误高亮不一致
- [modules.py:98-105] 默认搜索路径包含 `""`，语义模糊
- [modules.py:159-174] resolve_package_path 与 resolve 逻辑重复
- [environment.py:14-20] BindingInfo.name 字段冗余（字典 key 已经是 name）

#### 原创性分析

**错误处理系统**：Rust 风格错误格式化（源码上下文 + 箭头指示 + ANSI 颜色），是对 Rustc 的直接借鉴，实现质量中等偏上。

**模块系统**：ModuleResolver + ModuleManager 分离是标准设计；加载栈循环检测是经典 DFS 方法。原创性低。

**环境系统**：作用域链 + 父指针是经典的词法作用域实现，和 Lua、JavaScript 思路一致。三个文件中环境模块的代码质量最高，bug 最少。

---

## [2026-07-15] 所有后端 第十八轮审查报告

### 总体评分
| 后端 | 指令覆盖 | 代码正确性 | 可行性 | Nova 语义对应 | 综合评分 |
|------|---------|-----------|--------|--------------|---------|
| Native (自研x86_64) | 65% | 40% | 30% | 35% | ⭐⭐ |
| Cranelift | 55% | 25% | 15% | 30% | ⭐ |
| WasmGC | 50% | 20% | 10% | 25% | ⭐ |
| C 代码生成 | 80% | 65% | 75% | 70% | ⭐⭐⭐ |
| x86_64 编码器 | 80% | 70% | 75% | N/A | ⭐⭐⭐ |
| 编译管道 | — | 40% | 50% | — | ⭐⭐ |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [native_backend.py:416-505] **Native 后端浮点 BinOp 完全缺失——所有浮点算术/比较都生成整数指令** → `_compile_body` 中 `LIRBinOp` 的处理完全没有浮点分支，所有操作无条件使用整数指令；任何浮点运算程序都会产生完全错误的结果 → 根据操作数类型选择整数或浮点指令集
  - 追问：如果 GCC 的浮点运算全部生成整数指令，能被接受吗？→ **结论：绝对不能。** 这是后端最基本的正确性要求。

- [x86_64.py:375-386] **`mov_mem_imm64` 实际只写入 32 位立即数** → 函数名和文档声称写入 imm64，但实际只调用 `emit_uint32(imm)`；x86-64 的 `mov r/m64, imm32` 是符号扩展，大于 2^31-1 的值会静默截断 → 实现真正的 64 位立即数写入或重命名函数

- [cranelift_backend.py:156-157] **Cranelift 后端 LIRReturn 不返回值** → `_emit("return")` 不带返回值；所有非 void 函数的返回值都会丢失 → 从 instr.src_locs 获取返回值 SSA 名

- [cranelift_backend.py:162-168] **Cranelift 后端分支标签硬编码为 block_true/block_false** → 所有条件分支都跳转到固定标签，完全忽略 instr.true_label 和 instr.false_label；多个分支会生成重复标签名 → 使用 instr.true_label 和 instr.false_label

- [wasm_backend.py:230-232] **Wasm 后端 LIRLabel 被错误实现为 block 而非结构化控制流** → 每个 LIRLabel 都生成 `(block $block_xxx` 并增加缩进，但从未关闭这些 block；生成的 WAT 有未闭合的括号，完全无法解析 → 完全重写控制流生成，使用 loop + block 结构
  - 追问：如果一个后端生成的代码连语法都不正确，能叫"后端"吗？→ **结论：不能。** 至少应该能通过语法验证。

- [wasm_backend.py:260-263] **Wasm 后端 LIRBranch 引用不存在的 $block_false 标签** → `(br_if $block_false)` 硬编码了标签名，但该标签从未被定义；与第5条叠加，Wasm 控制流完全不可用 → 正确实现条件分支的结构化控制流

- [compiler_pipeline.py:33-35] **编译管道 BACKEND_NATIVE 映射到 Cranelift 而非 NativeCodeGen** → 用户请求原生后端时，实际得到的是 Cranelift 文本生成；名称与实际行为严重不符 → 修正映射或增加 BACKEND_NATIVE_X86 选项

- [compiler_pipeline.py:80-84] **C 后端绕过整个 IR 管道** → C 后端的 compile_source 在走完 HIR→MIR→LIR 全部降级后，完全忽略 LIR，直接调用 `self.backend.generate(ast)`；所有 IR 优化对 C 后端完全无效 → 统一编译管道，所有后端都从 LIR 开始

#### 中等问题（影响特定场景）

- [native_backend.py:645-654] _compile_load_global 不弹出已分配的寄存器，导致后续分配可能重用同一寄存器
- [native_backend.py:670-675] StoreGlobal 硬编码 RBX 作为临时寄存器，源值恰好分配在 RBX 时数据损坏
- [native_backend.py:762] _compile_index 破坏基址寄存器（直接 add_reg_reg），后续使用该指针得到错误地址
- [native_backend.py:792, 816, 835] BuildList/BuildTuple/BuildADT 的栈分配不计入 stack_size，函数尾声不恢复，栈不平衡
- [x86_64.py:451-473] je_rel32 重复定义（第二个覆盖第一个）
- [cranelift_backend.py:216-238] LIRBinOp 总是使用整数操作码，从不使用浮点操作码
- [cranelift_backend.py:109-112] 函数参数类型映射错误，参数名与 SSA 值不对应
- [wasm_backend.py:161] 字符串偏移计算使用 `b"\\x00"`（4字节字面量）而非 null 终止符
- [c_codegen.py:590-600] TryExpr 返回类型不匹配，直接返回 NovaADT* 与函数返回类型可能不兼容
- [c_codegen.py:853-871] ADT 构造器使用 GNU 语句表达式 + 指定初始化器，不可移植

#### 轻微问题（代码质量）

- [native_backend.py:35-82] LinearScanAllocator 定义但从未使用（死代码）
- [native_backend.py:851-873] _compile_counted_loop 是空方法
- [x86_64.py:275-288] movsd_reg_imm 命名误导（实际是 RIP-relative 内存加载）
- [cranelift_backend.py:257-261] _emit_data 每次都输出 section .rodata
- [wasm_backend.py:2-3] WasmGC 名称误导，实际未使用 GC 提案的 struct/ref 类型
- [c_codegen.py:1152-1159] ADT 字段访问与结构体定义不一致（命名字段 vs __field{i}）
- [c_codegen.py:1301-1302] _infer_c_type_from_expr 中 Identifier 默认为 int64_t
- [compiler_pipeline.py:88-107] compile_to_ir_text 不进行类型检查

#### 原创性分析

| 组件 | 原创性 | 说明 |
|------|--------|------|
| x86_64 编码器 | ⭐⭐⭐⭐ | 从零手写 x86_64 指令编码，涵盖 REX 前缀、ModR/M、SIB 等 |
| Native 后端 | ⭐⭐⭐ | 自研 ELF 生成 + 代码生成框架有原创性，但寄存器分配质量低 |
| Cranelift 后端 | ⭐ | 标准的 IR-to-IR 翻译模式，逻辑错误多 |
| Wasm 后端 | ⭐ | 标准的 WAT 生成，控制流理解有误 |
| C 代码生成 | ⭐⭐ | 典型的 source-to-source 翻译 |
| 编译管道 | ⭐⭐ | 三层 IR 架构有 MLIR 影子，但各层实现质量不均 |

---

## [2026-07-15] IR 系统 + Pass 管理器 第十八轮审查报告

### 总体评分
| 文件 | 设计合理性 | 实现正确性 | 完整性 | 代码质量 | 综合评分 |
|------|-----------|-----------|--------|---------|---------|
| ir_nodes.py | 7/10 | 8/10 | 6/10 | 7/10 | ⭐⭐⭐⭐ |
| hir_lowering.py | 6/10 | 3/10 | 7/10 | 5/10 | ⭐⭐ |
| mir_lowering.py | 5/10 | 2/10 | 3/10 | 4/10 | ⭐ |
| lir_lowering.py | 4/10 | 1/10 | 3/10 | 3/10 | ⭐ |
| pass_manager.py | 6/10 | 5/10 | 4/10 | 5/10 | ⭐⭐ |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [mir_lowering.py:109-110] **函数出口缺少 Return 终结指令** → 仅在 entry block 无 terminator 时才添加 MIRReturn；只要函数体包含任何控制流（if/match/for/while），merge/exit block 就没有终结指令；函数控制流"掉出"最后一个块，属于 malformed IR → 确保每个函数的最后一个块都有 Return 终结指令
  - 追问：如果 LLVM 的函数没有 return 终结指令，验证器能通过吗？→ **结论：绝对不能。** CFG 完整性是 SSA IR 的基本不变量。

- [lir_lowering.py:219-223] **LIR 条件分支目标标签完全丢失** → `_lower_terminator` 处理 MIRBranch 时，只设置了 src_locs，从未设置 lir.true_label 和 lir.false_label；所有条件分支在 LIR 层都是"无目的跳转" → 设置正确的目标标签
  - 追问：如果连最基本的 if-else 控制流在 LIR 层都是断裂的，IR 层有意义吗？→ **结论：没有。** 这是比"Switch 降级错误"更基础的致命 bug。

- [pass_manager.py:604-607] **LICM 外提指令仍在循环体内** → 被外提的指令被插入到 `header_idx + 1` 位置，而 loop_start = header_idx + 1 正是循环体的起始位置；外提的指令仍然每次迭代都会执行，LICM 完全没有起到外提作用 → 插入到 header 标签之前（pre-header 位置）
  - 追问：如果 LLVM 的 LICM 把指令"外提"到循环体第一行，能叫 LICM 吗？→ **结论：不能。** 这是优化 pass 的根本方向性错误。

- [mir_lowering.py:276-283] **MIR 变量赋值破坏 SSA 形式——无 Phi 插入** → HIRAssignExpr 直接更新 `self.env[name] = val_ssa` 并发出 MIRStore；当一个变量在不同控制流路径被赋值时，必须在合并点插入 Phi 节点，当前实现完全没有这个机制 → 实现完整的 SSA 构造（变量重命名 + Phi 插入）

- [hir_lowering.py:97-98] **HIR AliasDecl 完全丢失目标类型** → 类型别名的目标类型被直接丢弃，永远是 TYPE_VAR；下游的类型检查和代码生成都无法知道别名指向什么类型 → 正确降级别名的目标类型

- [hir_lowering.py:293-300 + mir_lowering.py:200-204] **HIRBlockExpr 混入 HIRLetDecl——类型违反** → LetBinding 在表达式上下文中被降级为 `HIRBlockExpr([HIRLetDecl(...)])`，但 HIRLetDecl 继承自 HIRDecl 而非 HIRExpr；块内的 let 绑定完全不生效，变量不会被加入环境 → 修正类型设计或实现正确的表达式级声明降级

- [hir_lowering.py:111-113] **HIRWhileExpr 作为顶层声明返回非 Decl 类型** → `_lower_decl` 返回 HIRWhileExpr（继承自 HIRExpr），与返回类型 HIRDecl 不匹配；后续遍历 declarations 时期望 HIRDecl 子类会出错 → 正确处理顶层的表达式声明

- [mir_lowering.py:232-237] **MIRFieldAccess 的 field_index 几乎总是 0** → 只有 HIRUnwrapExpr 的降级设置了 field_index = 0；所有普通字段访问的 field_index 都是默认值 0；所有字段访问都偏移为 0，全部读取第一个字段 → 正确计算字段索引

#### 中等问题（影响特定场景）

- [mir_lowering.py:396-417] For 循环变量从未绑定到环境，循环体无法访问迭代变量
- [mir_lowering.py:406] For 循环将 iterable 直接当布尔条件，语义完全错误
- [lir_lowering.py:227-228] LIR Return 值类型硬编码为 UNIT_TYPE，类型信息丢失
- [lir_lowering.py:171-176] MIRMapBuild 降级为 LIRBuildList，键值对结构完全丢失
- [lir_lowering.py:114-119] MIRStore 全部降级为全局存储，局部变量被错误地当作全局变量
- [lir_lowering.py:157-183] LIRBuildList/Tuple/ADT 丢失元素数据（src_locs 为空）
- [lir_lowering.py:141-147] MIRCall 参数未传递到 LIR（参数寄存器列表丢失）
- [hir_lowering.py:333] HIR ConstructorPattern 的 type_name 永远为空字符串
- [pass_manager.py:104-107] HIR 常量折叠使用 __class__ 赋值（非常脆弱的 Python 黑魔法）
- [pass_manager.py:474-479] MIR CSE 用 MIRLoad 替代 SSA 复用，语义错误

#### 轻微问题（代码质量）

- [pass_manager.py:90-120] HIR 常量折叠只递归 BinaryOp，不深入其他表达式
- [pass_manager.py:345] LIR DCE 的 side_effect_free_types 列表不全
- [pass_manager.py:280-283] DCE 的 _SIDE_EFFECT_TYPES 常量从未使用（死代码）
- [pass_manager.py:534-539] LIR LICM 只识别 LIRJump 回边，忽略 LIRBranch
- [pass_manager.py:636-640] MIR LICM 回边检测对 MIRBranch 几乎是空实现
- [pass_manager.py:651-655] MIR LICM 只收集 header 块的 SSA 定义（注释明确说"简化"）
- [ir_nodes.py:542] MIRBasicBlock.terminator 是 Optional 但 SSA 要求必须有
- [lir_lowering.py:88] LIR stack_size 假设所有值 8 字节，浪费空间且不一致

#### 各 Pass 实现状态表
| Pass 名称 | 层级 | 状态 | 主要问题 |
|-----------|------|------|----------|
| ConstantFolding | HIR | ⚠️ 部分可用 | 仅折叠顶层 HIRBinaryOp，不递归深入 |
| Inlining | HIR | ❌ 空壳 | 直接 return False |
| ConstantFolding | MIR | ✅ 基本可用 | 块内整型/浮点二元运算折叠正确 |
| CommonSubexprElimination | MIR | ⚠️ 有缺陷 | 用 MIRLoad 替代 SSA 复用，语义错误 |
| LoopInvariantCodeMotion | MIR | ❌ 基本无效 | 回边检测空实现 + 只看 header 块 |
| ConstantFolding | LIR | ✅ 基本可用 | 块内常量折叠正确，支持链式 |
| DeadCodeElimination | LIR | ⚠️ 部分可用 | 无副作用指令列表不全 |
| CommonSubexprElimination | LIR | ✅ 基本可用 | 块内 CSE 正确 |
| LoopInvariantCodeMotion | LIR | ❌ 外提错误 | 插入到循环体起始位置，仍在循环内 |

#### 原创性分析

三层 IR 设计（HIR→MIR→LIR）在概念上参考了 MLIR Dialect 思想，但实际每一层之间没有清晰的语义鸿沟。核心矛盾：三层设计增加了复杂度，但每层的抽象能力没有拉开差距。

**Pass 生态的"纸面繁荣"**：从 default_optimization_pipeline 看有 9 个 Pass，但实际有效实现的仅 3-4 个，且都是最简单的块内优化。跨块优化、过程间优化、循环优化全部失效或缺失。

---

## [2026-07-15] C 运行时 + 测试 + Tree-sitter 第十八轮审查报告

### 总体评分
| 维度 | C 运行时 | 测试套件 | Tree-sitter 语法 |
|------|----------|----------|------------------|
| 内存安全 | 3/10 | — | — |
| 类型安全 | 4/10 | — | — |
| 功能正确性 | 5/10 | — | — |
| 测试覆盖广度 | — | 6/10 | — |
| 测试质量深度 | — | 5/10 | — |
| 语法完整性 | — | — | 6/10 |
| 与 parser.py 一致性 | — | — | 4/10 |
| 综合评分 | 4/10 | 5.5/10 | 4.5/10 |

### 发现的问题

#### 严重问题（阻碍正常使用）

**C 运行时**：

- [nova_runtime.c:1218] **JSON `\u` 转义解码缓冲区分配不足导致堆溢出** → `decoded_len` 计算中 `\u` 只计为 1 字节，但 UTF-8 编码 BMP 字符需要 1-3 字节；`\u4e2d`（中文字符）decoded_len 只增加 1 但实际写入 3 字节 → 堆缓冲区溢出，可导致内存破坏
  - 追问：如果 Python 的 json.loads 有堆溢出漏洞，能发布吗？→ **结论：绝对不能。** 这是可利用的安全漏洞。

- [nova_runtime.c:607-608] **nova_map_remove 不释放 value，内存泄漏** → 只释放了 key 和 entry 结构体，entry->value 从未被释放；与 nova_map_put 的不一致性设计 → 释放 entry 前调用 nova_value_release
  - 追问：如果 Rust 的 HashMap remove 不 drop 值，能叫内存安全吗？→ **结论：不能。** 这是引用计数完整性的基本要求。

- [nova_runtime.c:367] **nova_list_set 既不释放旧值也不 retain 新值** → 直接覆盖旧 item，旧 item 泄漏；新 item 未 retain，可能导致 use-after-free → 正确的引用计数管理：release 旧值，retain 新值

- [nova_runtime.c:691] **nova_adt_set_field 无引用计数管理** → 与 list_set 同样问题：旧值泄漏，新值未 retain；ADT 字段的生命周期完全没有引用计数管理 → 添加正确的引用计数管理

**Tree-sitter 语法**：

- [grammar.js:614, 618 vs parser.py:672-678] **Tree-sitter 与 parser.py 管道优先级颠倒** → parser.py 中 pipe 优先级 > comparison，tree-sitter 中 comparison 优先级 > pipe；`x > 0 |> f` 两者解析结果完全不同 → 调整 Tree-sitter 优先级，与 parser.py 对齐
  - 追问：如果 GCC 的 C 解析器和 Clang 的 C 解析器对同一个表达式产生不同的 AST，能接受吗？→ **结论：绝对不能。** 语法必须唯一且确定。

#### 中等问题（影响特定场景）

**C 运行时**：
- [nova_runtime.c:1120-1137] JSON 对象 key 缺少 `\u` 转义解码
- [nova_runtime.c:206] nova_string_find NULL/空串返回值语义混乱（返回 0 与"在位置 0 找到"无法区分）
- [nova_runtime.c:1170, 1179, 1187] JSON true/false/null 不验证完整 token（仅根据首字符跳过）
- [nova_runtime.c:135-148] nova_string_new_len(NULL, len) 留未初始化内存
- [nova_runtime.c:79-87] nova_realloc 不更新 g_alloc_count/g_free_count，诊断统计不准
- [nova_runtime.c:1044] JSON 数字解析不检查整数溢出（strtoll 溢出未检查）
- [nova_runtime.c:217-224] nova_string_split 空分隔符按字节切分，不支持 UTF-8 字符边界

**测试套件**：
- 无边界值测试（大数、空值、极值）
- 负面测试覆盖率不足（运行时错误路径）
- 无端到端集成测试（编译→执行→验证输出）
- 并发/多线程测试为零

**Tree-sitter 语法**：
- 缺少泛型类型参数语法（`type Option[T]`）
- 缺少 range 表达式 `..` 和 `step` 关键字
- 缺少 try 表达式 `?` 操作符
- fn 类型语法不完整（缺少 `Fn[...]` 前缀形式）
- match_arm 的 guard 位置与 parser.py 相反

#### 轻微问题（代码质量）

**C 运行时**：
- nova_http_get/post 状态码硬编码 200（已知问题，本轮确认根因为 curl -w 输出未被捕获）
- 临时文件命名不使用 mkstemp，有安全风险

**测试套件**：
- 测试命名风格不一致
- test_nova.py 一个文件 334 个测试，应拆分
- 无 Evaluator-VM 一致性测试框架

**Tree-sitter**：
- 无语法错误恢复（error recovery）规则
- 缺少注释支持的显式 extras 规则
- 无 corpus 测试

#### 测试覆盖统计表
| 测试文件 | 测试数量 | 主要覆盖领域 |
|----------|----------|-------------|
| test_nova.py | 334 | lexer、parser、typecheck、evaluator、ADT、pipe、builtins、loops、I/O、VM |
| test_type_system.py | 55 | 泛型 ADT、类型别名、类型推断、类型错误 |
| test_errors.py | 36 | 错误格式化、错误收集、错误恢复 |
| test_modules.py | 28 | 模块导入导出、循环依赖检测、命名空间 |
| test_ir.py | 93 | HIR/MIR/LIR lowering、pass manager、优化 pass |
| test_c_codegen.py | 52 | C 代码生成、类型映射、运行时集成 |
| test_backends.py | 43 | Cranelift、WasmGC、编译器管线 |
| test_native_backend.py | 99 | x86_64 发射、寄存器分配、原生代码生成 |
| **总计** | **740** | |

#### 原创性分析

**C 运行时**：整体架构（引用计数 + FNV-1a 哈希 + 递归下降 JSON 解析）是标准且成熟的设计，非原创但实现完整。引用计数设计有根本缺陷（容器层无类型感知），导致多处内存泄漏和 use-after-free。

**测试套件**：测试组织合理，覆盖了多层。但 VM 测试（102个）与 Evaluator 测试（约130个）零交叉验证，是最大的测试架构缺陷。

**Tree-sitter 语法**：结构清晰，规则命名规范。但与 parser.py 存在系统性差异（优先级反转、缺失特性、guard 位置相反），表明是人工独立编写而非从语法规范导出。

---

## 第十八轮架构级建议（优先级排序）

### 🔴 P0 级（立即修复，安全/正确性基石）

1. **修复 JSON `\u` 转义堆溢出** → 可利用的安全漏洞
2. **修复类型检查器 TypeVar 万能兼容问题** → 类型系统基本失效
3. **修复嵌套模式匹配失败时栈破坏** → 函数式语言核心特性的 P0 缺陷
4. **修复 LIR 条件分支目标标签完全丢失** → 整个 IR 后端的 if-else 都断裂
5. **修复 MIR 函数出口缺 Return 终结指令** → CFG 完整性的基本不变量
6. **修复 STORE_VAR 语义错误（作用域模型）** → 违反静态作用域原则
7. **修复模块系统路径遍历安全漏洞** → P0 安全漏洞，可读取系统任意文件
8. **修复 Assignment 不检查可变性** → 函数式语言不可变绑定的核心原则

### 🟠 P1 级（高优先级，影响功能正确性）

9. **修复 FOR_ITER BREAK 的 result_list 索引 off-by-one** → for 表达式返回值语义错误
10. **实现真正的 HM 类型推断（unification + let-polymorphism）** → 类型系统架构级重构
11. **修复块级作用域缺失问题** → VM 中 for/match/if 的变量泄漏
12. **修复 NovaConstructor 不支持柯里化** → 函数式语言一等构造器的基本要求
13. **修复管道操作符优先级错误** → 函数式语言核心运算符的解析错误
14. **修复 `?` 操作符不在后缀循环内** → 错误传播操作符核心用法失效
15. **修复推断返回类型不写回环境** → 所有无标注函数返回类型不受约束
16. **修复导出名称不验证 + 导入静默失败** → 模块系统核心功能缺陷
17. **修复 AST 节点 span 信息不完整** → 错误报告和 IDE 功能的基础
18. **添加 Evaluator-VM 一致性测试框架** → 多后端语言的基本质量要求
19. **修复 Tree-sitter 与 parser.py 语法不一致** → 优先级 + 缺失特性 + guard 位置
20. **修复容器引用计数完整性（map_remove/list_set/adt_set_field）** → 大规模内存泄漏
21. **修复 LICM 外提位置错误** → 循环优化 pass 方向性错误

### 🟡 P2 级（中优先级，影响质量/可维护性）

22. **统一闭包语义（引用 vs 值快照）** → 语言规范级别的分歧
23. **修复 while 循环 CONTINUE 依赖启发式检测**
24. **修复 BREAK 前向扫描脆弱设计**
25. **接入 Native 后端到编译管道**
26. **修复 Cranelift 后端 SSA 值传播 + 分支标签**
27. **重写 Wasm 后端控制流翻译**
28. **实现 Parser 语法错误恢复**
29. **修复闭包全量捕获（自由变量分析）**
30. **修复 C 运行时循环引用 GC**
31. **重写 IR 降级链，实现真正的 SSA + Phi 消除**
32. **实现模式匹配穷尽性检查**
33. **建立模块命名空间系统，摆脱 import * 模式**
34. **添加 fuzz 测试、属性测试、边界值测试**

### 🟢 长期规划

35. **实现真正的 GC（标记-清除或分代 GC）**
36. **实现 LSP 语言服务器支持**
37. **实现 Tree-sitter 语法与 parser.py 的完全对齐**
38. **添加 C 后端端到端测试**
39. **实现类型检查器错误恢复**
40. **添加端到端集成测试（所有后端）**

---

---

## [2026-07-15] 第十九轮深度审查报告

### 本轮审查概览

本轮为第19轮全面深度审查，覆盖所有24个模块。审查重点为：验证前18轮问题的修复状态、发现新的深度问题、评估架构级缺陷。

**修复率统计**：前一轮报告的主要问题中，约5%已修复，95%仍存在或部分存在。

---

## [2026-07-15] VM 虚拟机 (vm.py) 第十九轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | MATCH 栈恢复机制、_pop(n) 统一检查有特色 |
| 可行性 | ⭐⭐⭐⭐ | 核心路径可用；循环控制、闭包仍有问题 |
| 正确性 | ⭐⭐ | RETURN 语义分裂、闭包过度捕获、break/continue 嵌套错误 |
| 安全性 | ⭐⭐⭐ | 栈下溢保护已添加；但迭代器状态泄漏、id 问题已部分修复 |
| 一致性 | ⭐⭐⭐ | 与 Evaluator 仍有多处行为差异 |
| 完整性 | ⭐⭐⭐⭐⭐ | 60+ 操作码全部有处理路径 |
| 工程质量 | ⭐⭐ | 状态分散、执行循环重复、代码冗余 |
| 性能 | ⭐⭐ | 闭包全量捕获 dict 拷贝性能差 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [vm.py:553-558] **_pop 统一栈下溢检查已添加，但 BREAK/CONTINUE 等控制流指令仍直接操作栈** → FOR_ITER 中的 BREAK/CONTINUE 弹出 result_list 时绕过 _pop，若栈状态异常仍可能 IndexError → 所有弹栈操作统一走 _pop
  - 追问：如果 Haskell GHC 的 STG 机器栈管理有 bug，能被接受吗？→ **绝对不能。** 栈管理是 VM 最基本的正确性要求。

- [vm.py:717-728] **CONTINUE 在 while 循环中仍依赖启发式检测，for/while 嵌套时 break/continue 目标错误** → 嵌套循环（while 包含 for）中，内层 for 的 break/continue 被错误地当作 while 的 break/continue → 引入统一的循环栈，break/continue 总是针对最内层循环
  - 追问：如果任何生产级语言的 continue 是空实现，能被接受吗？→ **绝对不能。** 控制流语义错误是 P0 级 bug。

- [vm.py:736-738] **闭包仍捕获整个帧 locals 而非仅自由变量** → 每次创建闭包都 dict 浅拷贝所有局部变量，时间 O(n)，阻止 GC 回收不需要的变量 → 编译器分析自由变量，CLOSURE 指令携带自由变量名列表
  - 追问：如果 OCaml 的闭包捕获了整个作用域的 dict 拷贝，性能影响能被接受吗？→ **绝对不能。** 内存使用量可能增加 10-100 倍。

- [vm.py:392] **RETURN 语义不统一：_execute_function 和 _run_code 各有一套实现** → 两个执行循环中 RETURN 的处理逻辑不同，可能导致返回值丢失或栈帧错误 → 统一 RETURN 实现，单一执行循环
  - 追问：如果是 OCaml 的函数调用返回值丢失，能被接受吗？→ **不能。** 函数调用是语言执行核心。

- [vm.py:845,884] **id() 问题已部分修复（改用 _loop_id 计数器），但迭代器状态在函数返回时可能泄漏** → 函数内部的 for 循环提前返回时，_for_iters 中的迭代器状态未清理 → 函数返回时清理当前帧对应的迭代器状态

#### 中等问题（影响特定场景）

- [vm.py:971-989] 模式匹配失败栈恢复机制已添加（_pattern_fail_cleanup），但顶层 match 绑定不清理
- [vm.py:168-208] 内置函数类型检查仍不足，超额参数检查已添加但类型校验缺失
- [vm.py:709-715] BREAK 在 while 循环中用脆弱的前向扫描，依赖 CONST_UNIT 作为标记
- [vm.py:537] mutable 参数未用于不可变性强制，VM 完全信任编译器
- [vm.py:482-1079] _execute_instruction 方法仍过长（近 600 行）

#### 轻微问题（代码质量）

- [vm.py:655,669] JUMP_IF_FALSE 和 POP_JUMP_IF_FALSE 实现重复
- [vm.py:133,138] Frame.locals 命名不一致（locals_ vs locals）
- [vm.py:229-232] _to_float 对 bool 的处理与算术运算不一致
- [vm.py:357] _format_value 遗漏 NovaPartialBuiltin

#### 原创性分析
- **Nova 特色**：match_stack_bases + _pattern_fail_cleanup 统一栈恢复、_pop(n) 集中式下溢检查、_loop_id 自增计数器替代 id()
- **参考已有**：基本栈机设计参考 CPython/JVM；FOR_ITER + LOOP_END 双指令循环

#### Evaluator vs VM 对比
| 行为 | Evaluator | VM | 是否一致 |
|------|-----------|-----|---------|
| 闭包捕获方式 | 整个 Environment 引用 | 当前帧 locals 字典拷贝 | ❌ |
| Builtin 超额参数检查 | ❌ 不检查 | ✅ 检查 | ❌ |
| for 循环作用域 | 每次迭代 child env | 直接写入当前帧 locals | ❌ |
| 递归深度检查 | _call_depth 计数器 | call_stack 长度 | ✅ |
| Unit 值单例 | _UnitValue 类 | UNIT_TYPE 真正单例 | ✅（语义等价） |
| 构造器部分应用 | 支持（BuiltinFn 包装） | 不支持（NovaConstructor 精确匹配） | ❌ |
| 顶层 break/continue | 抛 RuntimeError | 可能静默失败 | ❌ |


---

## [2026-07-15] 编译器 (compiler.py) 第十九轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐⭐ | PIPE_CALL 专用指令、MATCH_START/END 标记、ADT 原生指令 |
| 可行性 | ⭐⭐⭐⭐ | 核心路径可用；嵌套循环、导入命名空间仍有问题 |
| 正确性 | ⭐⭐ | 嵌套循环 break/continue 错误、闭包全量捕获、while 返回值不符 |
| 安全性 | ⭐⭐⭐ | 栈布局大部分路径正确；模式匹配失败由 VM 统一恢复 |
| 一致性 | ⭐⭐⭐ | 跳转回填基本正确；操作码定义与实现仍有不一致 |
| 完整性 | ⭐⭐⭐⭐ | AST 节点基本全覆盖；死代码比例下降 |
| 工程质量 | ⭐⭐ | 仍有大量死代码、重复代码、未使用操作码 |
| 性能 | ⭐⭐ | 闭包全量捕获、常量池形同虚设、多次 import 重复编译 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [compiler.py:491-507] **嵌套循环中 break/continue 目标错误** → for 循环嵌套在 while 内部时，内层 for 的 break/continue 被错误编译为外层 while 的 break/continue → 引入统一的循环栈，记录每层循环类型和信息
  - 追问：如果 OCaml 的编译器嵌套循环中 break 跳错层能被接受吗？→ **绝对不能。** 控制流基本语义错误。

- [compiler.py:403,683] **闭包全量捕获而非自由变量捕获** → CLOSURE 指令只携带 func_name 和 param_count，没有自由变量列表，VM 端全量浅拷贝 → 编译器实现自由变量分析，CLOSURE 携带捕获变量列表
  - 追问：如果 OCaml 的闭包捕获了整个作用域的所有变量，能被接受吗？→ **绝对不能。** 函数式语言编译器的基本优化。

- [compiler.py:273-289,358-359] **导入 TypeDef 时所有变体名泄漏到全局命名空间** → 导出 type Color { Red | Green | Blue } 会导致 Red/Green/Blue 全部进入导入者的全局作用域 → 实现命名空间隔离或要求显式导出每个变体
  - 追问：如果 Haskell 的 import 把模块内所有数据构造器都无提示地带入当前作用域，能被接受吗？→ **不能。** Haskell 有明确的三级粒度控制。

- [compiler.py:1047,1054] **while 循环返回值与文档语义不符** → ast_nodes.py 明确记载"体中最后一个表达式的最后一次迭代的值作为返回值"，但实际总是返回 Unit → 实现"返回最后一次迭代值"语义，引入结果变量
  - 追问：如果 Rust 的 loop 表达式文档说返回 break 值但实际返回 nil，能被接受吗？→ **不能。** 文档和实现不一致是最危险的 bug。

- [compiler.py:300-343] **模块导入内联命名空间隔离仍不完整** → 冲突检测仅警告不阻止，同名绑定后者静默覆盖前者 → 冲突时抛出错误而非警告

#### 中等问题（影响特定场景）

- [compiler.py:597-603] 管道操作中内置函数走 LOAD_VAR 而非 CALL_BUILTIN，效率不一致
- [compiler.py:901-965] 死代码：_compile_pattern_test 和 _compile_pattern_bindings（约 65 行）
- [compiler.py:320-371] 多次 import 同一模块会重复编译声明
- [compiler.py:81] CLOSURE 操作码注释定义 3 个操作数但实际发射 2 个
- [compiler.py:430-435] Some/Ok/Err 作为一等值使用时失败（只能在 FnCall 中特殊处理）

#### 轻微问题（代码质量）

- [compiler.py:75] LOOP 指令定义但从未使用
- [compiler.py:48,169-178] LOAD_CONST 定义但从未使用，常量池形同虚设
- [compiler.py:421-422] CharLiteral 编译为 CONST_STRING，运行时无独立 Char 表示
- [compiler.py:800-803] MATCH_TEST_FLOAT 使用精确相等比较，浮点数语义危险

#### 原创性分析
- **Nova 特色**：MATCH_* 系列指令的"成功时 pop、失败时保留"语义配合 VM 统一栈恢复、FOR_ITER + LOOP_END 配对模型、PIPE_CALL 专用指令、TRY_UNWRAP 统一错误传播
- **参考已有**：基本栈机结构参考 CPython/JVM；跳转回填参考标准编译器教材


---

## [2026-07-15] 求值器 (evaluator.py) 第十九轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 原创性 | ⭐⭐⭐ | 两遍扫描支持相互递归、内置 Option/Result 类型 |
| 可行性 | ⭐⭐⭐⭐ | 核心特性可用；MapExpr 已实现 |
| 正确性 | ⭐⭐⭐ | 闭包"未来可见"语义错误、guard 缺少 Bool 检查 |
| 安全性 | ⭐⭐⭐ | 多处使用 Python truthiness 而非 Nova Bool 严格检查 |
| 一致性 | ⭐⭐⭐ | 与 VM 在闭包、构造器部分应用等方面不一致 |
| 完整性 | ⭐⭐⭐⭐ | 大部分 AST 节点有处理；块级作用域不支持 FnDef |
| 工程质量 | ⭐⭐⭐ | 结构清晰但有重复代码、错误处理不一致 |
| 性能 | ⭐⭐⭐ | 闭包引用语义效率可接受；缺少表达式深度保护 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [evaluator.py:737-742] **闭包捕获整个环境引用导致"未来可见"语义错误** → 同一作用域内的所有 let 绑定都写入同一个 Environment 对象，闭包可以"看到"在它之后定义的变量 → 每个 let/mut 绑定创建新的子环境，或闭包创建时复制自由变量快照
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **绝对不能。** 违反了词法闭包的基本定义。

- [evaluator.py:408-414] **BuiltinFn 超额参数未校验** → 传入参数数量超过 arity 时直接调用 fn.fn(*args)，导致 Python TypeError 泄露 → 添加超额参数检查，抛出 Nova RuntimeError_
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **不能。** 应给出清晰的语言级错误。

- [evaluator.py:1066] **守卫条件缺少 Bool 类型检查** → 使用 Python truthiness 而非严格的 isinstance(..., bool) 检查，与 if/while 不一致 → 添加 Bool 类型检查
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **绝对不能。** 强类型语言的守卫条件必须是 Bool。

- [evaluator.py:1041] **列表推导过滤条件缺少 Bool 类型检查** → 同样使用 Python truthiness，与 if/while 不一致 → 添加 Bool 类型检查

- [evaluator.py:799-800] **MapExpr 中非可哈希键导致 Python TypeError 泄露** → 键为列表/字典等非可哈希类型时，Python 直接抛 TypeError 而非 Nova 错误 → 捕获 TypeError 并转换为 Nova RuntimeError_

#### 中等问题（影响特定场景）

- [evaluator.py:1102-1104] 模式匹配中重复变量名静默覆盖
- [evaluator.py:1016-1047] 列表推导式中 break/continue 信号未捕获
- [evaluator.py:571-626] eval_decl 方法为死代码且与两遍扫描逻辑重复
- [evaluator.py:208] 内置 filter 函数使用 is True 身份检查，与 if 语义不一致
- [evaluator.py:671-869] 块级作用域不支持局部函数定义（FnDef）
- [evaluator.py:716-727] TryExpr 在顶层代码中使用时 ReturnSignal 未被捕获

#### 轻微问题（代码质量）

- [evaluator.py:786-792] Assignment 中 try/except 无意义
- [evaluator.py:694-698] Identifier 查找中 except 捕获 NameError 但环境不会抛出
- [evaluator.py:219-221] _builtin_head 中空列表时 field_names 参数不一致
- [evaluator.py:335-336] _builtin_abs 返回类型不一致（Int 输入返回 Float）
- [evaluator.py:966-979 vs 1019-1030] for 循环与列表推导式的 range 处理代码重复

#### 原创性分析
- **Nova 特色**：两遍扫描程序求值支持相互递归、TryExpr 通过 ReturnSignal 实现错误传播、for 循环作为表达式返回列表
- **参考已有**：经典树遍历解释器架构、环境引用捕获模式（Scheme/Python）、异常实现非局部控制流（Ruby/Smalltalk）


---

## [2026-07-15] 类型检查器 (type_checker.py) 第十九轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| 类型安全性 | ⭐⭐⭐ | 存在严重健全性漏洞：无标注参数永远不会被约束 |
| 类型推断完备性 | ⭐⭐ | 不是真正的 HM 推断，只是带通配符的自底向上标注 |
| 合一算法正确性 | ⭐ | 没有合一算法，只有单向模式匹配 + TypeVar 通配 |
| let 多态实现 | ⭐⭐ | 无泛化/实例化，简单情况因 TypeVar 不可变而"碰巧"工作 |
| 模式匹配完整性 | ⭐⭐⭐⭐ | 基本模式类型检查已实现，但缺少穷尽性和守卫检查 |
| 错误收集机制 | ⭐⭐⭐ | ErrorCollector 存在但多处绕过，且 check_program 不主动抛出 |
| 递归 ADT 支持 | ⭐⭐⭐⭐ | 基本可用，注册顺序正确 |
| 代码质量 | ⭐⭐⭐ | 结构清晰但核心算法有根本性缺陷 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [type_checker.py:558-585] **无类型标注的函数参数永远不会被约束** → _check_decl_body 中对 FnDef 只更新返回类型，参数类型在第一遍注册后不再修改；函数体中对参数的使用不会反推参数类型 → 实现真正的合一算法，在检查函数体时收集约束
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **绝对不能。** 类型系统的核心健全性破坏。

- [type_checker.py:1378-1406] **没有真正的合一（unification）算法** → _types_compatible 是结构相等 + TypeVar 通配，只要一方是 TypeVar 就返回 True；没有双向合一、没有 occurs check → 实现基于 union-find 的真正合一算法
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **不能。** 合一算法是 HM 类型推断的基石。

- [type_checker.py:801-811] **let 多态未实现（无泛化/实例化）** → let 绑定直接存储推断类型，不做泛化；查找时也不做实例化 → 引入类型方案（type scheme），let 绑定时泛化，查找时实例化
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **不能。** let 多态是 HM 类型系统的定义性特征。

- [type_checker.py:178-182] **TypeVar 相等性基于名称而非身份** → 两个不同作用域中同名的 TypeVar 被认为是同一个，存在跨作用域碰撞风险 → 使用对象身份（默认的 __eq__ 和 __hash__）
  - 追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ **不能。** 类型变量的身份是类型系统的基础。

- [type_checker.py:777-792] **管道运算符类型检查完全错误** → 同时尝试第一个和最后一个参数，不做类型变量替换，错误静默 → 重新实现管道类型检查，明确语义为 x |> f == f(x)

#### 中等问题（影响特定场景）

- [type_checker.py:1042-1050] match 守卫表达式的类型从未被检查
- [type_checker.py:813-816] 表达式级 MutBinding 不检查类型标注
- [type_checker.py:766-771, 1313] ErrorCollector 被多处绕过
- [type_checker.py:981-982] ForExpr 遍历 TupleType 时只取第一个元素类型
- [type_checker.py:293-307] 内置 ADT 变体字段类型与构造函数签名使用不同的类型变量名
- [type_checker.py:699-711] 缺少模式匹配穷尽性检查
- [type_checker.py:387-404] check_program 在 collect_errors 模式下不主动抛出

#### 轻微问题（代码质量）

- [type_checker.py:169-176] TypeVar 类级计数器永不重置
- [type_checker.py:1022-1036] ListComprehension 的环境切换冗余
- [type_checker.py:995-999] WhileExpr 返回 body 类型语义存疑
- [type_checker.py:953-965] TryExpr 不检查外围函数返回类型

#### 原创性分析
类型检查器最根本的问题是架构层面的：试图用"TypeVar 作为通配符 + 单向匹配 + 不可变类型变量"的方式模拟 HM 推断，但缺少合一、泛化、实例化三大支柱。本质更接近一个带类型孔的类型检查器，而非类型推断器。一阶 let 多态"碰巧"工作是因为 TypeVar 不可变 + 每次调用独立创建 bindings 字典，这是一种"巧合的多态"。


---

## [2026-07-15] 词法/语法分析器 (lexer.py + parser.py) 第十九轮审查报告

### 总体评分
| 维度 | Lexer | Parser | 说明 |
|------|-------|--------|------|
| Token/AST 覆盖 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 主要语法元素均有覆盖；部分死 token |
| 错误恢复 | ⭐⭐⭐ | ⭐ | Lexer 能跳过非法字符；Parser 遇错即停 |
| 位置准确性 | ⭐⭐ | ⭐⭐ | 大多只有起始位置无完整跨度 |
| 运算符优先级 | — | ⭐⭐ | 管道优先级错误、比较/相等性左结合有误 |
| 结合性 | — | ⭐⭐⭐ | 算术/逻辑左结合正确；比较应为无结合 |
| 语法歧义处理 | — | ⭐⭐⭐ | 悬挂 else 已解决；map/block 消歧性能差 |
| 左递归处理 | — | ⭐⭐⭐⭐⭐ | 递归下降 + 优先级分层正确消除左递归 |
| 与 tree-sitter 一致性 | ⭐⭐ | ⭐⭐ | 优先级、guard 位置、<- token 化等多处不一致 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [parser.py:672-678] **管道操作符 |> 优先级严重错误** → _parse_comparison_expr 调用 _parse_pipe 获取操作数，管道优先级高于比较运算符，与函数式语言常规相反 → 将 _parse_pipe 移到优先级链最低端
  - 追问：如果 GCC/Clang 的运算符优先级表与语言规范矛盾，能被接受吗？→ **绝对不能。** 优先级错误是编译器前端最严重的错误类别之一。

- [parser.py:764-767] **? 操作符不在后缀循环内——链式错误传播完全失效** → ? 在 _parse_postfix_expr 的 while 循环之后处理，连续 expr?? 只应用一次 → 将 ? 移入 while 循环内，与函数调用、字段访问、索引访问同级
  - 追问：如果 Rust 的 ? 运算符不能链式调用，能被接受吗？→ **不能。** 链式错误传播是 ? 操作符的核心价值。

- [parser.py:464-466,968-970] **<- 左箭头无专用 token——LT + MINUS 手动组合脆弱且错误** → x < -y 可能被误解析为 x <- y；错误消息不准确 → 在 lexer.py 中添加 LEFT_ARROW token
  - 追问：如果 Haskell 的 <- 是由两个 token 手动组合的，能被接受吗？→ **不能。** 多字符运算符应在词法层面识别。

- [parser.py:672-678] **比较运算符应为无结合性，当前为左结合** → 允许 a < b < c 被解析为 (a < b) < c，比较一个布尔值和 c → 将 while 改为单次 if
  - 追问：如果任何生产级编译器的比较运算符是左结合的，能被接受吗？→ **不能。** 现代语言（Rust, Swift, Haskell）都将比较设为无结合性。

- [lexer.py:155-160] **词法分析器 _make_error 是死代码，错误非结构化** → 所有错误以纯字符串 append 到 errors 列表并直接 print 到 stderr；没有使用 LexerError 类型 → 删除或实际使用 _make_error；所有错误创建结构化对象
  - 追问：如果 GCC 的词法错误只有纯文本消息，没有结构化位置信息，能被接受吗？→ **不能。** 现代编译器的错误必须是结构化的。

- [parser.py 全文] **语法分析器完全没有错误恢复机制** → 遇到第一个语法错误就立即抛出 ParseError 异常并终止；用户每次只能看到一个错误 → 实现 panic mode 错误恢复，使用 ErrorCollector 收集多个错误
  - 追问：如果 GCC 遇到第一个语法错误就停止编译，只报一个错，能被接受吗？→ **不能。** 现代编译器都支持错误恢复。

#### 中等问题（影响特定场景）

- [parser.py:522] match arm 起始 token 列表缺少 CHAR 和 MINUS（负数模式）
- [parser.py:532-538] match arm 的 guard 位置与 tree-sitter 不一致
- [parser.py:474,974] for 循环范围形式使用原始 tuple 而非 AST 节点
- [parser.py:844-884] _is_map_literal 前瞻扫描性能差，可能 O(n²)
- [parser.py:386-391] 块中赋值检测仅支持简单标识符
- [lexer.py:91] UNIT token 类型是死代码
- [lexer.py:88] PIPE_VARIANT token 类型是死代码
- [lexer.py:202-221] 数字字面量不支持科学计数法、多进制、数字分隔符
- [lexer.py:240-251] 字符串/字符转义序列缺少 Unicode 转义和十六进制转义
- [lexer.py:186-200] 不支持块注释 /* */
- [parser.py:956-988] 列表推导式的范围形式不支持 step

#### 轻微问题（代码质量）

- [parser.py:57-62] _advance 到达 EOF 时静默返回
- [lexer.py:256,265,279,306,457] 词法错误直接 print 到 stderr
- [parser.py:530-539] MatchArm 节点没有 span 信息
- [lexer.py:109-110] Token.__repr__ 不显示 end_line/end_col
- [lexer.py:302-308] 空字符字面量错误消息误导

#### 原创性分析
**词法分析器**：低原创性（⭐⭐）。标准的逐字符递归式词法分析器设计。
**语法分析器**：中等原创性（⭐⭐⭐）。递归下降 + 优先级分层是标准做法，但 map 字面量与 block 的消歧策略（前瞻扫描 =>）、PipeExpr 作为独立 AST 节点、TryExpr 作为一等语法结构有一定特色。
**最大工程质量问题**：两个"官方"语法定义（parser.py vs tree-sitter）有多处分歧，缺少统一的语法规范文档作为单一真相来源。


---

## [2026-07-15] 错误处理 + 模块 + 环境 第十九轮审查报告

### 总体评分
| 维度 | errors.py | modules.py | environment.py |
|------|-----------|------------|----------------|
| 正确性 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| 完整性 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 安全性 | ⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐ |
| 一致性 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| 可维护性 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 生产就绪度 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |

### 发现的问题

#### 严重问题（阻碍正常使用 / 安全漏洞）

- [modules.py:124-130] **路径遍历漏洞** → 相对路径导入直接使用 os.path.join + abspath，没有路径边界检查；恶意模块可通过 import "../../../etc/passwd" 读取系统任意文件 → 添加 _is_within_allowed_paths 验证
  - 追问：如果 Deno 允许 import "../../../etc/passwd" 读取系统文件，能被接受吗？→ **绝对不能。** 模块系统的路径沙箱是安全基石。

- [modules.py:244-245 + evaluator.py:655-660] **导出名称不验证存在性，导入静默失败** → _collect_exports 在类型检查之前执行，只收集 ExportDecl 名称不验证是否定义；导入方用 try/except 包裹 lookup，找不到就静默 pass → 类型检查完成后验证导出名称存在性；导入失败抛 ImportError
  - 追问：如果 Python 的 from module import undefined_name 静默失败不报错，能被接受吗？→ **绝对不能。** ImportError 是最基本的错误类型。

- [errors.py:167-171] **span.end_column 无 None 校验** → 只检查 end_line is not None 就直接使用 end_column；如果 end_column 为 None，后续计算导致 TypeError，错误格式化自身崩溃 → 同时检查 end_line 和 end_column 不为 None
  - 追问：如果 Rust 编译器遇到不完整的 span 信息时自身崩溃，能被接受吗？→ **绝对不能。** 错误格式化是编译器的"门面"，自身的健壮性比被格式化的错误更重要。

- [modules.py:330 + environment.py:34-40] **导入的 mut 变量丢失可变性** → Environment.lookup() 只返回值不返回可变性信息；import_module 硬编码 mutable=False → 统一使用 lookup_binding()，导入时保留原始可变性
  - 追问：如果 Rust 的 use 导入的 static mut 变成了只读，能叫语义正确吗？→ **不能。** 这是严重的语义错误。

- [modules.py:293-299] **_collect_exported_types 完全忽略 type_checker 参数** → 接收 type_checker 参数但完全不使用，返回值和 _collect_exports 完全相同；调用后返回值从未被使用 → 真正实现类型导出或删除死代码和误导性方法名

#### 中等问题（影响特定场景）

- [errors.py:396-398] ErrorCollector.get_all() 丢失时间顺序
- [errors.py:409-410] raise_all 将后续错误转为字符串 note，丢失结构化信息
- [evaluator.py 全文] Evaluator 未集成 ErrorCollector
- [errors.py:244] note_start 上下文显示不对称
- [modules.py:124-130] 相对路径导入依赖 search_paths[0] 为 current_dir
- [modules.py:358-363] 全局默认搜索路径与 ModuleResolver 默认路径不一致
- [environment.py:67-73] all_bindings 只返回值不返回可变性
- [errors.py:265-283] _compute_underline 多行末尾行计算不一致

#### 轻微问题（代码质量）

- [errors.py:93] highlight_span 字段命名不一致
- [errors.py:216-229] 相关注释颜色/标签逻辑重复
- [errors.py:260] note 下划线单字符 ^ 与主错误不一致
- [modules.py:98-105] 默认搜索路径包含空字符串
- [modules.py:159-174] resolve_package_path 与 resolve 逻辑重复
- [environment.py:14-20] BindingInfo.name 字段冗余
- [errors.py:186-190] 位置信息无文件名

#### 原创性分析
**errors.py**（⭐⭐⭐）：Rust 风格错误格式化是对 Rustc 的直接借鉴，实现思路标准但多行高亮和中文本地化有一定工作量。
**modules.py**（⭐⭐）：ModuleResolver + ModuleManager 分离是所有语言模块系统的标准架构，加载栈做循环检测是经典 DFS 方法。
**environment.py**（⭐⭐）：作用域链 + 父指针是经典的词法作用域实现，与 Lua、JavaScript、Scheme 的思路完全一致。三个文件中环境模块代码最简洁、bug 最少。


---

## [2026-07-15] 所有后端 第十九轮审查报告

### 总体评分
| 后端 | 评分 | 评价 |
|------|------|------|
| C CodeGen | ⭐⭐⭐ | 功能最完整的后端，但有多处类型安全和 ADT 实现 bug |
| Native Backend | ⭐⭐⭐ | 有较完整的 x86_64 指令编码器和 ELF 生成，但寄存器分配和浮点有严重 bug |
| Cranelift Backend | ⭐⭐ | 生成的 CLIF 格式有大量语法错误，几乎不可能被正确编译 |
| WasmGC Backend | ⭐⭐ | WAT 生成有结构性问题，控制流模型完全错误，GC 支持是纸面的 |
| Compiler Pipeline | ⭐⭐ | 架构设计合理但实现不完整，native 后端映射错误 |
| x86_64 Emitter | ⭐⭐⭐⭐ | 基础指令编码较完整，但有重复定义和 REX 前缀 bug |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [native_backend.py:634-636] **寄存器分配结果与实际使用不一致** → 预分配和自由列表可能分配同一个物理寄存器，导致寄存器冲突 → 统一寄存器分配逻辑，确保预分配的寄存器从自由列表中移除
  - 追问：如果 OCaml 的 native 编译器生成的代码不正确，能被接受吗？→ **绝对不能。** native 后端生成的代码存在寄存器冲突这一根本性正确性问题。

- [native_backend.py:661-751] **LIRBinOp 浮点操作完全缺失** → 所有算术运算都使用 GPR 指令，即使操作数是浮点类型 → 浮点操作使用 SSE2 指令（addsd, subsd, mulsd, divsd）

- [native_backend.py:812-816] **LIRReturn 不处理返回值寄存器** → 注释声称返回值已在 RAX/XMM0，但没有任何代码确保返回值被放入正确的返回寄存器 → 将返回值从 src_locs 移动到 RAX/XMM0

- [cranelift_backend.py:108-135] **生成的 CLIF 格式不符合 Cranelift 语法规范** → 函数声明、块标签、跳转指令、分支指令、函数调用语法都有错误 → 重写 CLIF 生成，严格按照 Cranelift 文档

- [wasm_backend.py:230-232] **WasmGC 控制流模型完全错误** → 每个 LIRLabel 编译为新的 block，但从不关闭；LIRJump 编译为 br 但语义不同 → 重写控制流生成，使用 Wasm 结构化控制流（if/else/end, loop/end, block/end）

- [wasm_backend.py:313-340] **LIRBinOp 操作数从栈上隐式取，无类型检查** → Wasm 是栈式机，但 LIR 是寄存器式的；binop 没有将 src_locs 值压栈 → 每个操作前先将 src_locs 的值压栈

- [compiler_pipeline.py:33-35] **BACKEND_NATIVE 映射到 CraneliftBackend** → 常量名是 BACKEND_NATIVE 但实际后端是 Cranelift，真正的 NativeCodeGen 完全没被使用 → 修正后端映射或统一命名

- [c_codegen.py:210-232] **ADT 结构体使用 union 语义但用 struct 实现** → 所有变体的所有字段放在同一个 struct 中，浪费空间且与 ADT 语义不符 → 使用 union 实现变体字段

- [c_codegen.py:590-600] **TryExpr 假设所有返回类型都是 NovaADT* 且字段名不匹配** → 所有 ? 操作符结果强制转换为 NovaADT*，tag 字段名和常量名都与实际定义不符 → 修正字段名和常量名

#### 中等问题（影响特定场景）

- [x86_64.py:451-473] je_rel32 重复定义
- [x86_64.py:275-287] movsd_reg_imm 的 REX 前缀处理错误
- [native_backend.py:1033-1057] 列表构建在栈上分配，返回后失效（同样问题存在于 tuple 和 ADT）
- [native_backend.py:483-494] 函数调用参数传递中 src_reg 为 None 时静默跳过
- [native_backend.py:809-810] LIRCall 不保存返回值
- [cranelift_backend.py:162-168] LIRBranch 使用硬编码的 block 名（block_true/block_false）
- [cranelift_backend.py:156-157] LIRReturn 不返回值
- [cranelift_backend.py:210-211] 字符串常量的符号名生成重复且无数据
- [wasm_backend.py:161] 字符串扫描中字符串编码错误（b"\\x00" 而非 b"\x00"）
- [c_codegen.py:655-664] match 表达式的 guard 分支缺少闭合 else
- [c_codegen.py:188-195] 顶层声明的变量不区分 let 和 mut

#### 轻微问题（代码质量）

- [x86_64.py:83] mov_reg_imm64 对负数的判断有误
- [native_backend.py:422-424] 线性扫描分配器溢出时直接返回 None
- [native_backend.py:1103-1125] _compile_counted_loop 是空方法
- [cranelift_backend.py:226-232] float_op_map 中缺少取模运算
- [wasm_backend.py:85-110] GC struct 类型定义硬编码且未被使用
- [c_codegen.py:530-534] BreakExpr/ContinueExpr 作为表达式返回字符串

#### 原创性分析
1. **Native Backend**（⭐⭐⭐⭐）：从零实现 x86_64 指令编码和 ELF 文件生成，不依赖外部汇编器/编译器，在 Python 实现的编译器中较少见。
2. **C CodeGen**（⭐⭐⭐）：AST 到 C 的翻译是经典做法，模式匹配、闭包转换等是标准技术。
3. **三层 IR + 多后端架构**（⭐⭐⭐⭐）：HIR→MIR→LIR 三层 IR + 四个后端的设计在同等规模的教学语言中相当完善。
4. **Cranelift/WasmGC**（⭐⭐）：概念验证级别，原创性低且实现深度不足。


---

## [2026-07-15] IR 系统 + Pass 管理器 第十九轮审查报告

### 总体评分
| 维度 | 评分 | 说明 |
|------|------|------|
| IR 节点设计完整性 | ⭐⭐⭐ | 三层结构合理但存在类型不一致和遗漏 |
| SSA 形式正确性 | ⭐⭐ | Phi 节点放置错误，无支配树，SSA 构建有严重缺陷 |
| HIR→MIR 降级正确性 | ⭐⭐ | 多处控制流降级错误，match 降级完全不正确 |
| MIR→LIR 降级正确性 | ⭐⭐⭐ | Phi 节点降级只取第一个源，类型硬编码错误 |
| Pass 依赖与执行顺序 | ⭐⭐ | 无依赖管理，执行顺序硬编码，无 pass 验证 |
| Pass 异常处理 | ⭐⭐⭐ | 管理器本身不吞异常，但多处 pass 内部静默失败 |
| 优化 Pass 正确性 | ⭐⭐ | CSE 有语义错误，LICM 外提位置错误，常量折叠递归不完整 |
| 循环识别与处理 | ⭐⭐ | 回边识别算法错误，嵌套循环完全不支持 |

### 发现的问题

#### 严重问题（阻碍正常使用）

- [mir_lowering.py:351-384] **Match 表达式降级完全错误** → 所有分支通过 MIRJump 无条件串联，第一个分支执行完直接跳到第二个；没有任何模式判定逻辑 → 为每个 arm 生成模式匹配判定，使用条件分支选择分支
  - 追问：如果 LLVM 的 switch 指令降级为顺序 goto，能被接受吗？→ **绝对不能。** 这是控制流图的根本性错误。

- [pass_manager.py:473-480] **MIR 层 CSE 用 MIRLoad 替代重复计算——语义错误** → MIRLoad 的语义是"加载变量"，将 SSA 名赋给 name 字段在语义上完全错误；下游降级会生成加载全局变量的指令 → 添加 MIRCopy/MIRMove 指令用于 SSA 值复制，或直接在使用点替换为原始 SSA 名

- [pass_manager.py:595-607] **LICM 外提位置错误——指令仍在循环体内** → LIR 层插入到 header_idx + 1（header 标签之后）= 循环体开头；MIR 层插入到第一个跳向 header 的前驱块（可能是回边）→ 找到循环的 pre-header，将外提指令插入到 pre-header 末尾
  - 追问：如果 LLVM 的 opt 工具把循环不变量外提到循环体内部，能被接受吗？→ **绝对不能。** LICM 的核心价值就是将循环不变计算移到循环外。

- [mir_lowering.py:333-345] **SSA 构建错误——Phi 节点不完整，支配树缺失** → 只有当分支有值时才添加 Phi 源；没有支配树算法，无法验证 SSA 形式正确性 → 实现支配树算法，基于支配边界放置 Phi 节点

- [pass_manager.py:534-539] **回边识别算法错误——所有后向跳转都被视为循环** → 只要跳转到前面的标签就算循环，没有判断 header 是否支配 back-edge 的源块；嵌套循环完全无法正确处理 → 实现支配树计算；回边定义：边 n→d 是回边当且仅当 d 支配 n

- [pass_manager.py:256-261] **HIR Inlining Pass 是空壳** → 直接 return False，完全没有实现 → 真正实现内联或删除空壳 pass

#### 中等问题（影响特定场景）

- [pass_manager.py:90-120] HIR 常量折叠只处理 BinaryOp，不递归到其他表达式
- [pass_manager.py:130-171] MIR 常量折叠不跨基本块，每个基本块重置 ssa_map
- [lir_lowering.py:204-211] Phi 节点降级为只取第一个源——破坏 SSA 语义
- [mir_lowering.py:396-417] For 循环降级——iterable 直接当条件用，语义错误
- [pass_manager.py:280-283,345] DCE 副作用指令列表不完整——会漏删很多死代码
- [pass_manager.py:747-767] Pass 管理器无依赖管理，执行顺序硬编码
- [hir_lowering.py:285-289] 列表推导式降级为常量空列表
- [lir_lowering.py:149-155] ClosureCreate 降级为字符串常量

#### 轻微问题（代码质量）

- [hir_lowering.py:292-299] HIRBlockExpr 中混合了声明和表达式
- [ir_nodes.py:820-826] LIRBranch 有两个条件来源字段——数据冗余
- [lir_lowering.py:227-228] LIR 返回值类型硬编码为 UNIT_TYPE
- [lir_lowering.py:231-241] MIRSwitch/MIRMatchJump 降级为无条件跳转
- [hir_lowering.py:332-333] HIR 构造器模式的 type_name 为空字符串
- [hir_lowering.py:97-98] AliasDecl 降级时丢失目标类型信息

#### 各 Pass 实现状态表
| Pass 名称 | 层级 | 状态 | 主要问题 |
|-----------|------|------|----------|
| ConstantFolding | HIR | ⚠️ 部分可用 | 仅折叠 HIRBinaryOp，不递归深入其他表达式 |
| Inlining | HIR | ❌ 空壳 | 直接 return False |
| ConstantFolding | MIR | ✅ 基本可用 | 块内整型/浮点二元运算折叠正确 |
| CommonSubexprElimination | MIR | ❌ 语义错误 | 用 MIRLoad 替代 SSA 复用，语义错误 |
| LoopInvariantCodeMotion | MIR | ❌ 基本无效 | 回边检测错误 + 外提目标错误 |
| ConstantFolding | LIR | ✅ 基本可用 | 块内常量折叠正确，支持链式 |
| DeadCodeElimination | LIR | ⚠️ 部分可用 | 无副作用指令列表不全 |
| CommonSubexprElimination | LIR | ✅ 基本可用 | 块内 CSE 正确 |
| LoopInvariantCodeMotion | LIR | ❌ 外提错误 | 插入到循环体起始位置，仍在循环内 |

#### 原创性分析
三层 IR 设计参考了 MLIR Dialect 思想，但实现非常简化。Pass 管理器采用经典的不动点迭代模式。最有特色的是三层都实现了常量折叠且 LIR 层支持链式折叠。但核心的 SSA 构建、循环识别、LICM 等都存在根本性缺陷，表明仍处于"框架搭好了但内容没填实"的阶段。


---

## [2026-07-15] C 运行时 + 测试 + Tree-sitter 第十九轮审查报告

### 总体评分
| 维度 | C 运行时 | 测试套件 | Tree-sitter 语法 |
|------|----------|----------|------------------|
| 内存安全 | 3/10 | — | — |
| 类型安全 | 4/10 | — | — |
| 功能正确性 | 5/10 | — | — |
| 测试覆盖广度 | — | 6/10 | — |
| 测试质量深度 | — | 5/10 | — |
| 语法完整性 | — | — | 6/10 |
| 与 parser.py 一致性 | — | — | 4/10 |
| 综合评分 | 4/10 | 5.5/10 | 4.5/10 |

### 发现的问题

#### 严重问题（阻碍正常使用）

**C 运行时**：

- [nova_runtime.c:1226-1256] **JSON `\u` 转义解码缓冲区分配不足导致堆溢出** → decoded_len 计算中 \u 只计为 1 字节，但 UTF-8 编码 BMP 字符需要 1-3 字节；\u4e2d（中文字符）decoded_len 只增加 1 但实际写入 3 字节 → 堆缓冲区溢出
  - 追问：如果 Python 的 json.loads 有堆溢出漏洞，能发布吗？→ **绝对不能。** 这是可利用的安全漏洞。

- [nova_runtime.c:597-614] **nova_map_remove 不释放 value，内存泄漏** → 只释放了 key 和 entry 结构体，entry->value 从未被释放 → 释放 entry 前调用 nova_value_release

- [nova_runtime.c:363-368] **nova_list_set 既不释放旧值也不 retain 新值** → 直接覆盖旧 item，旧 item 泄漏；新 item 未 retain，可能导致 use-after-free → 正确的引用计数管理

- [nova_runtime.c:689-692] **nova_adt_set_field 无引用计数管理** → 与 list_set 同样问题：旧值泄漏，新值未 retain → 添加正确的引用计数管理

- [nova_runtime.c:99-103] **GC 完全不处理循环引用** → 纯引用计数模型在存在循环时会泄漏，是已知的根本性缺陷 → 实现标记-清扫补充 GC 或文档明确说明限制
  - 追问：如果 Python 的 GC 不处理循环引用，能叫生产级吗？→ **不能。** Python 引用计数为主 + 分代 GC 补充处理循环引用。

**Tree-sitter 语法**：

- [grammar.js:612-624 vs parser.py:672-678] **Tree-sitter 与 parser.py 管道优先级颠倒** → parser.py 中 pipe 优先级 > comparison，tree-sitter 中 comparison > pipe → 调整 Tree-sitter 优先级与 parser.py 对齐
  - 追问：如果 GCC 和 Clang 对同一个表达式产生不同的 AST，能接受吗？→ **绝对不能。** 语法必须唯一且确定。

- [grammar.js 全文] **Tree-sitter 缺少 `?`（try）操作符** → Python 解析器有 TryExpr，但 Tree-sitter 语法中完全没有 → 添加后缀 try 操作符

#### 中等问题（影响特定场景）

**C 运行时**：
- [nova_runtime.c:479-486] nova_list_release 不释放列表元素
- [nova_runtime.c:749-756] nova_adt_release 不释放字段
- [nova_runtime.c:525-538] nova_map_put 中 nova_value_release 类型不安全
- [nova_runtime.c:205-211] nova_string_find NULL/空串返回值语义混乱
- [nova_runtime.c:79-87] nova_realloc 不更新 g_alloc_count/g_free_count
- [nova_runtime.c:1044] JSON 数字解析不检查整数溢出

**测试套件**：
- 无 Evaluator-VM 一致性测试框架
- 无端到端集成测试（编译→执行→验证输出）
- 无边界值测试（大数、空值、极值）
- 负面测试覆盖率不足（运行时错误路径）
- C 运行时无单元测试
- test_nova.py 一个文件 340 个测试，应拆分

**Tree-sitter 语法**：
- 缺少泛型类型参数语法（type Option[T]）
- 缺少 range 表达式 .. 和 step 关键字
- match_arm 的 guard 位置与 parser.py 相反
- fn 类型语法不完整

#### 轻微问题（代码质量）

**C 运行时**：
- [nova_runtime.c:150-166] nova_string_concat 处理 NULL 参数时引用计数不一致
- [nova_runtime.c:370-400] nova_list_concat 和 nova_list_slice 元素未 retain
- 临时文件命名不使用 mkstemp

**测试套件**：
- 测试命名风格不一致
- 无 fuzz 测试、属性测试

**Tree-sitter**：
- 无语法错误恢复（error recovery）规则
- 缺少注释支持的显式 extras 规则
- 无 corpus 测试

#### 测试覆盖统计表
| 测试文件 | 测试数量 | 主要覆盖领域 |
|----------|----------|-------------|
| test_nova.py | ~340 | lexer、parser、typecheck、evaluator、ADT、pipe、builtins、loops、I/O、VM |
| test_type_system.py | ~75 | 泛型 ADT、类型别名、类型推断、类型错误 |
| test_errors.py | ~36 | 错误格式化、错误收集、错误恢复 |
| test_modules.py | ~28 | 模块导入导出、循环依赖、命名空间 |
| test_ir.py | ~93 | HIR/MIR/LIR lowering、pass manager、优化 pass |
| test_c_codegen.py | ~52 | C 代码生成、类型映射、运行时集成 |
| test_backends.py | ~43 | Cranelift、WasmGC、编译器管线 |
| test_native_backend.py | ~116 | x86_64 编码、寄存器分配、原生代码生成 |
| **总计** | **~783** | |

#### 原创性分析

**C 运行时**：采用带引用计数的手动内存管理 + 泛型 void* 指针的混合模式，接近手动管理的 C 库风格，但缺乏类型安全。整体架构（引用计数 + FNV-1a 哈希 + 递归下降 JSON 解析）是标准且成熟的设计，非原创但实现完整。

**测试套件**：测试组织合理，覆盖了多层。但 VM 测试与 Evaluator 测试零交叉验证，是最大的测试架构缺陷。

**Tree-sitter 语法**：结构清晰，规则命名规范。但与 parser.py 存在系统性差异（优先级反转、缺失特性、guard 位置相反），表明是人工独立编写而非从语法规范导出。


---

## 第十九轮架构级建议（优先级排序）

### 🔴 P0 级（立即修复，安全/正确性基石）

1. **修复 JSON `\u` 转义堆溢出** → 可利用的安全漏洞（C 运行时）
2. **修复模块系统路径遍历安全漏洞** → P0 安全漏洞，可读取系统任意文件
3. **修复类型检查器无标注参数不被约束（健全性漏洞）** → 类型系统基本失效
4. **修复合一算法（真正的 HM 推断）** → 类型系统架构级重构
5. **修复 SSA 构建 + 支配树** → 整个 IR 后端的正确性基础
6. **修复 Match 表达式 MIR 降级完全错误** → 所有 match 代码生成错误 CFG
7. **修复 MIR 层 CSE 用 MIRLoad 替代的语义错误** → 所有经过 MIR CSE 的代码可能出错
8. **修复 LICM 外提位置错误** → LICM 完全无效
9. **修复嵌套循环 break/continue 目标错误** → 控制流基本语义错误
10. **修复闭包词法作用域语义（Evaluator "未来可见" + VM 全量捕获）** → 函数式语言核心语义

### 🟠 P1 级（高优先级，影响功能正确性）

11. **修复 RETURN 语义分裂（VM 双执行循环）** → 核心指令语义不统一
12. **修复 while 循环返回值与文档语义不符** → 文档承诺的功能未实现
13. **修复管道操作符优先级错误** → 函数式语言核心运算符的解析错误
14. **修复 `?` 操作符不在后缀循环内** → 错误传播操作符核心用法失效
15. **修复导出名称不验证 + 导入静默失败** → 模块系统核心功能缺陷
16. **修复导入 TypeDef 变体名泄漏** → 命名空间污染
17. **修复管道运算符类型检查错误** → 类型系统核心功能
18. **修复 Native 后端寄存器分配冲突** → 原生后端根本正确性
19. **修复 Native 后端浮点运算缺失** → 浮点计算完全不可用
20. **修复 Cranelift 后端 CLIF 语法错误** → 后端完全不可用
21. **修复 WasmGC 控制流模型错误** → 后端完全不可用
22. **添加 Evaluator-VM 一致性测试框架** → 多后端语言的基本质量要求
23. **修复 Tree-sitter 与 parser.py 语法不一致** → 优先级 + 缺失特性 + guard 位置
24. **修复容器引用计数完整性（map_remove/list_set/adt_set_field/list_release/adt_release）** → 大规模内存泄漏

### 🟡 P2 级（中优先级，影响质量/可维护性）

25. **实现 let 多态（泛化 + 实例化）** → 类型系统 HM 核心功能
26. **修复闭包全量捕获（自由变量分析）** → 性能和语义改进
27. **修复 GC 循环引用处理** → 内存管理完整性
28. **重写 IR 降级链，实现真正的 SSA + Phi 消除** → IR 架构级重构
29. **实现模式匹配穷尽性检查** → 函数式语言类型安全的重要组成
30. **建立模块命名空间系统，摆脱 import * 模式** → 模块系统架构改进
31. **实现 Parser 语法错误恢复** → 开发体验基本要求
32. **实现 Lexer 结构化错误** → 错误报告一致性
33. **统一错误报告路径（ErrorCollector 一致工作）** → 开发体验
34. **添加 fuzz 测试、属性测试、边界值测试** → 测试质量提升
35. **修复 C CodeGen ADT union 布局** → C 后端内存正确性
36. **接入 Native 后端到编译管道** → 后端可用性
37. **修复 Cranelift 后端 SSA 值传播 + 分支标签** → 后端可用性
38. **重写 Wasm 后端控制流翻译** → 后端可用性
39. **修复 `<-` 左箭头 token 化** → 词法分析器基本职责
40. **修复比较/相等性无结合性** → 语法正确性
41. **修复 mut 变量导入丢失可变性** → 语义正确性

### 🟢 长期规划

42. **实现真正的 GC（标记-清除或分代 GC）
43. **实现 LSP 语言服务器支持**
44. **实现 Tree-sitter 语法与 parser.py 的完全对齐**
45. **添加 C 后端端到端测试**
46. **实现类型检查器错误恢复**
47. **添加端到端集成测试（所有后端）**
48. **实现 JIT 编译（基于 Cranelift）**
49. **实现调试支持（栈回溯、断点、单步执行）**
50. **包管理器：依赖解析、版本管理**

---
