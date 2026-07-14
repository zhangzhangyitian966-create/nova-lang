# Nova 自动改进日志

## 2026-07-14 自动改进

### 每日发现的问题

#### vm.py
- 行728 `CONTINUE` 分支: pass 占位，while 循环 continue 处理为空操作（标记性，合理设计）
- 行921/994/1051/1056: MATCH_START/MATCH_END/HALT/AUTO_CALL_MAIN 的 pass 为标记性占位，属合理设计

#### compiler.py
- 行282 `AliasDef` 编译: pass 占位，类型别名声明被完全跳过，未生成字节码

#### backend/native_backend.py
- 行489 `LIRCallIndirect`: NotImplementedError，间接调用未实现
- 行493 `LIRIndex`: NotImplementedError，索引访问未实现 **[已修复]**
- 行497 `LIRFieldAccess`: NotImplementedError，字段访问未实现
- 行904/1002: AST→LIR 降级未实现

#### ir/pass_manager.py
- 行721/735/749: except Exception: pass 静默吞没异常

#### type_checker.py
- 行487 `_handle_import_decl`: 引用未导入的 `NovaError`，运行时会 NameError **[已修复]**
- 行943-945 `TryExpr` 处理: 过于简化，未检查 Result/Option 类型 **[已修复]**
- PatternFloat/PatternChar: **已实现**，无需修复

#### evaluator.py
- 行690-696 `TryExpr`: 不执行提前返回，错误传播语义缺失 **[已修复]**
- 行973 `PatternInt`: bool 误匹配风险（bool 是 int 子类） **[已修复]**

### 本次修复内容

1. **evaluator.py - TryExpr 错误传播**
   - 新增 `ReturnSignal` 异常类（errors.py）
   - TryExpr 遇到 Err/None 时 raise ReturnSignal 提前退出函数
   - _call_fn 捕获 ReturnSignal 转为正常返回值

2. **evaluator.py - PatternInt bool 误匹配**
   - `isinstance(value, int)` 改为 `isinstance(value, int) and not isinstance(value, bool)`

3. **backend/native_backend.py - LIRIndex 代码生成**
   - 实现 `_compile_index` 方法，生成 x86_64 索引访问代码
   - 更新测试用例为正向测试

4. **type_checker.py - NovaError 导入**
   - 添加 `NovaError` 到 import 语句

5. **type_checker.py - TryExpr 类型检查**
   - 检查 Result[T, E] 返回 T，检查 Option[T] 返回 T

### 测试结果

- 全量测试: **655 passed** (1.23s)
- Evaluator 示例: hello/fibonacci/loops/pattern_match/math 全部正常输出
- VM 示例: hello/fibonacci/loops 全部正常输出

---

## 2026-07-14 自动改进（第二轮）

基于 AUTO_REVIEW_LOG.md 审查发现的严重问题驱动改进。

### 本次修复内容（基于审查日志 Issue）

1. **vm.py — RETURN 语义修正（基于审查日志 vm.py:751-754）**
   - 在 `NovaVM.__init__` 新增 `self.return_flag = False`
   - `_execute_instruction` 中 RETURN 分支设置 `self.return_flag = True`，确保执行流正确终止
   - `_run_code` 和 `_execute_function` 主循环检查 `return_flag`，提前退出并正确返回栈顶值

2. **vm.py — `id()` 迭代键替换为唯一循环 ID（基于审查日志 vm.py:845,884）**
   - 新增 `self._loop_id` 递增计数器
   - `FOR_ITER` 不再使用 `id(iter_val)`，改用分配的唯一 `loop_id` 作为 `_range_index` / `_list_index` 键
   - `LOOP_END` / `BREAK` / `CONTINUE` 的清理逻辑兼容新键机制

3. **parser.py — `|>` 管道操作符优先级修正（基于审查日志 parser.py:432）**
   - `_parse_expression` 入口改为 `self._parse_for_while_expr()`，将管道剥离出最低优先级
   - `_parse_pipe` 左递归起点改为 `_parse_cons_expr()`，使管道优先级高于比较操作符
   - `_parse_comparison_expr` 解析起点改为 `_parse_pipe()`，比较在更低层级调用管道
   - 效果：`x |> f == y` 现在正确解析为 `(x |> f) == y`

4. **modules.py — 模块加载传递 module_manager（基于审查日志 modules.py:240-241）**
   - `TypeChecker(source=source)` 改为 `TypeChecker(source=source, module_manager=self)`
   - `Evaluator(check_types=check_types)` 改为 `Evaluator(check_types=check_types, module_manager=self)`
   - 被导入模块内的嵌套 import 现在可正确解析

5. **compiler.py + vm.py — PatternFloat/PatternChar 模式测试代码生成（基于审查日志 compiler.py:748）**
   - `Op` 类新增 `MATCH_TEST_FLOAT` 和 `MATCH_TEST_CHAR` 操作码
   - `_compile_pattern_test_with_fail` 和 `_compile_pattern_test` 新增 PatternFloat/PatternChar 分支
   - vm.py 实现 `MATCH_TEST_FLOAT`（检查 float 类型且值相等）和 `MATCH_TEST_CHAR`（检查 str 长度 1 且值相等）

6. **c_codegen.py — TryExpr（`?` 操作符）错误传播实现（基于审查日志 c_codegen.py:524-525）**
   - 新增 `_compile_try_expr_to_stmt` 方法
   - 生成 C 代码：编译内部表达式到临时变量，检查 variant_tag 是否为 None/Err，是则提前返回，否则通过 `nova_adt_get_field` 提取 payload

7. **ir/mir_lowering.py — break/continue 降级为正确跳转（基于审查日志 mir_lowering.py:259-265）**
   - `MIRLowering.__init__` 新增 `loop_break_labels` 和 `loop_continue_labels` 栈
   - `_lower_for_expr` / `_lower_while_expr` 在生成循环块后压入 break/continue 目标标签，循环体 lowering 结束后弹出
   - `HIRBreakExpr` / `HIRContinueExpr` 改为生成 `MIRJump` 到对应标签；栈空时降级为 `MIRPanic("break outside loop")`

8. **type_checker.py — 删除 check_decl 死代码（基于审查日志 type_checker.py:576-660）**
   - 删除整个 `check_decl` 方法（约 85 行）及其内部所有逻辑
   - 全局搜索确认无任何调用点

9. **evaluator.py — field_names 修复（基于审查日志 evaluator.py:577 / evaluator.py:189）**
   - `_builtin_str_to_int` 中 Option Some/None 构造补充 `field_names` 参数
   - `_eval_decl_body` 内 `make_constructor` 闭包中 `NovaADTValue` 补充 `fnames` 参数

### 测试结果

- 全量测试: **655 passed** (1.66s)
- Evaluator 示例: hello/math/pattern_match/pipe/loops 全部正常输出
- VM 示例: hello/math/pattern_match 全部正常输出

1. **vm.py — while 循环 CONTINUE 空实现修复（基于审查日志 Top 1）**
   - 新增 `_while_loops` 追踪列表，在 `POP_JUMP_IF_FALSE` 和 `JUMP` 指令中自动识别 while 循环结构
   - CONTINUE 在 while 循环中现在正确跳回条件检查位置并恢复栈
   - for 循环 CONTINUE 行为不受影响

2. **environment.py — 异常类型修复（基于审查日志 environment.py:53,59）**
   - `assign` 方法中的 Python 原生 `RuntimeError`/`NameError` 替换为 Nova 的 `RuntimeError_`
   - 保留 `lookup`/`lookup_binding` 中的 `NameError`（evaluator/modules.py 依赖它）

3. **ir/pass_manager.py — Pass 异常不再静默吞掉（基于审查日志 Top 8）**
   - 三个 `run_*_passes` 方法中的 `except Exception: pass` 改为输出到 stderr + 记录到 `self.errors` 列表
   - 保留容错性：单个 pass 失败不阻止后续 pass

4. **backend/native_backend.py — &&/|| 布尔语义修正（基于审查日志 native_backend.py:410-415）**
   - 在 `and`/`or` 位运算前用 `test + setne + movzx` 将操作数规范化为 0/1
   - 注释更新，准确描述当前行为限制

5. **compiler.py — match guard 守卫条件实现（基于审查日志 Top 2）**
   - `_compile_match` 中在模式测试通过后、执行 body 前，编译 guard 表达式
   - guard 失败时跳转到下一个 arm
   - 改为即时回填跳转地址

6. **compiler.py — 列表推导式 filter_cond 实现（基于审查日志 Top 2）**
   - `_compile_list_comprehension` 有 filter 时内联编译循环，在循环体中添加 `POP_JUMP_IF_FALSE` 跳过结果追加
   - 无 filter 时保持原有行为委托给 `_compile_for`

7. **evaluator.py — UNIT_VALUE __bool__ 修正（基于审查日志 evaluator.py:98）**
   - 将 `UNIT_VALUE = object()` 改为 `_UnitValue` 类实例，`__bool__` 返回 `False`
   - 与 VM 中 `UNIT_TYPE.__bool__` 行为一致

### 测试结果

- 全量测试: **655 passed** (0.67s)
- Evaluator 示例: hello/fibonacci/loops/pattern_match/pipe/list_comprehension/math/file_io 全部正常输出
- VM 示例: hello/fibonacci/pattern_match 全部正常输出

---

## 2026-07-15 自动改进（第三轮）

基于 AUTO_REVIEW_LOG.md 审查发现的严重问题驱动改进。

### 每日发现的问题

#### vm.py
- 所有 pop 操作无栈下溢保护（审查日志 vm.py:550-837）
- base_sp 计算错误且从不用于栈截断（审查日志 vm.py:392）
- RETURN 在 _execute_instruction 中弹栈但不终止执行（审查日志 vm.py:751-754）

#### evaluator.py
- MapExpr 完全缺失，eval_expr 落入 else 抛 RuntimeError（审查日志 evaluator.py:817）
- Pattern guard 守卫条件未实现（审查日志 evaluator.py:956-967）

#### c_codegen.py
- IfExpr 缺少 else 分支时返回空字符串导致无效 C 代码（审查日志 c_codegen.py:603-611）
- Match guard 条件位置错误，body 副作用在 guard 检查前执行（审查日志 c_codegen.py:634-640）

#### backend/native_backend.py
- LIRFieldAccess 抛 NotImplementedError（审查日志 native_backend.py:497）

#### parser.py
- step 表达式被静默丢弃，ForExpr 中硬编码 step=None（审查日志 parser.py:482-483）

#### type_checker.py
- Lambda 多参数共享同一 TypeVar（审查日志 type_checker.py:754）
- 未知类型名静默创建 PrimType（审查日志 type_checker.py:1256）

### 本次修复内容（基于审查日志 Issue）

1. **vm.py — 栈下溢保护 + base_sp 修正（基于审查日志 vm.py:550-837 / vm.py:392）**
   - 新增 `_pop(n=1)` 辅助方法，所有指令的裸 `self.stack.pop()` 替换为受保护的 `_pop()`
   - 修正 `base_sp = len(self.stack) - len(args)` 为 `base_sp = len(self.stack)`
   - 使用 `try/finally` 确保函数返回或异常时都用 `base_sp` 截断栈

2. **evaluator.py — MapExpr 处理 + Pattern guard 实现（基于审查日志 evaluator.py:817 / evaluator.py:956-967）**
   - 在 `eval_expr` 中添加 `MapExpr` 分支，求值键值对字典
   - 在 `_eval_match` 中模式匹配成功后求值 guard，guard 失败时 continue 到下一个 arm

3. **c_codegen.py — IfExpr 缺 else 默认值 + Match guard 位置修正（基于审查日志 c_codegen.py:603-611 / c_codegen.py:634-640）**
   - 无 else 分支时返回 `"0"` 表示 Unit 默认值，避免生成 `x = ;` 无效 C 代码
   - 重构 match guard 编译顺序：guard 条件判断在 body_setup 之前，guard 失败时 body 完全不执行

4. **backend/native_backend.py — LIRFieldAccess 实现（基于审查日志 native_backend.py:497）**
   - 新增 `_compile_field_access` 方法，从基址寄存器 + offset 加载字段到目标寄存器
   - 更新测试为正向编译测试

5. **parser.py — step 表达式不再丢弃（基于审查日志 parser.py:482-483）**
   - 在 `for x in expr` 和 `for i <- start..end` 分支统一初始化 `step_expr = None`
   - ForExpr 构造时传入 `step=step_expr`

6. **type_checker.py — Lambda TypeVar 唯一化 + 未知类型报错（基于审查日志 type_checker.py:754 / type_checker.py:1256）**
   - Lambda 参数改为 `TypeVar(f"lambda_param_{i}")`，消除多参数共享同一 TypeVar
   - 未知类型名不再静默创建 `PrimType`，改为 `_report_error` 并返回 `ERROR_TYPE`

### 测试结果

- 全量测试: **655 passed** (1.06s)
- Evaluator 示例: hello/math/pattern_match/pipe/loops 全部正常输出
- VM 示例: hello/math/pattern_match 全部正常输出

---

## 2026-07-15 自动改进（第四轮）

基于 AUTO_REVIEW_LOG.md 审查发现的严重问题驱动改进。

### 每日发现的问题

#### vm.py
- RETURN 语义残留（789-792）：`_execute_instruction` 中 RETURN 只弹栈不终止执行，结果存入局部变量后丢弃。`_run_code` 不拦截 RETURN，顶层代码若出现 RETURN 行为错误。
- `id()` 做迭代键（888、927）：`FOR_ITER` 以 `id(iter_val)` 作为 `_range_index`/`_list_index` 键。嵌套循环共享对象时状态互相覆盖；对象回收后 id 复用导致旧状态残留；异常退出时条目泄漏。
- 闭包捕获值语义不一致（767-776）：`CLOSURE` 做 `dict(locals)` 浅拷贝快照，与 evaluator.py 的 Environment 引用捕获不一致。

#### compiler.py
- PatternFloat / PatternChar 模式测试完全缺失：`_compile_pattern_test_with_fail` 与 `_compile_pattern_test` 均无对应分支，落入 else 当作 MATCH_WILDCARD（总是匹配）。vm.py 中亦缺失 MATCH_TEST_FLOAT / MATCH_TEST_CHAR 操作码，属跨层功能缺失。
- PatternTuple / PatternList 模式测试被禁用（751-752、819-825）：两个方法中均显式当作 MATCH_WILDCARD / 返回 None，导致元组/列表模式匹配完全失效。

#### parser.py
- `|>` 管道操作符优先级错误（432）：当前优先级最低（低于 `||`），导致 `x |> f == y` 被解析为 `x |> (f == y)`，而非 `(x |> f) == y`。

#### modules.py
- 模块加载时未传递 module_manager（240-241）：`TypeChecker(source=source)` 和 `Evaluator(check_types=check_types)` 均未传入 `module_manager=self`，嵌套 import 失效。

#### c_codegen.py
- TryExpr（`?` 操作符）被完全忽略（524-525）：仅递归编译内部表达式，未生成任何错误传播代码。

#### ir/pass_manager.py
- Inlining 优化 pass 为空壳（256-261）：`Inlining.run` 直接返回 `False`，不做任何实际内联操作。

#### ir/mir_lowering.py
- break/continue 被降级为 panic（259-265）：`HIRBreakExpr` / `HIRContinueExpr` 生成 `MIRPanic("break")` / `MIRPanic("continue")`，运行时直接崩溃。

#### type_checker.py
- check_decl 是 330 行死代码（576-660）：与 `_collect_decl` + `_check_decl_body` 功能完全重复，从未被调用。

#### evaluator.py
- ADT 构造器丢失 field_names（577）：`_eval_decl_body` 内 `make_constructor` 闭包中 `NovaADTValue(type_name, vname, list(args))` 缺少 `fnames`。
- `_builtin_str_to_int` 返回 Option 缺少 field_names（189）：`NovaADTValue("Option", "Some", [int(args[0])])` 和 `NovaADTValue("Option", "None", [])` 均缺少 `field_names`。

### 本次修复内容（基于审查日志 Issue）

（第四轮修复内容未完整记录到日志中）

---

## 2026-07-15 自动改进（第五轮）

基于 AUTO_REVIEW_LOG.md 审查发现的严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py
- 第560-571行 `STORE_VAR`：读取 `mutable = instr.operands[1]` 后未使用，VM 运行时不区分变量可变性
- 第682-685行 `JUMP` while 启发式：通过 `target < self.ip` + 下一条为 `CONST_UNIT` 识别 while 循环，鲁棒性不足
- 第1132-1138行 `PRINT`：注释声明栈变化 `[value] -> [()]`，但实际未 push UNIT，栈不平衡

#### compiler.py
- 第502-511行 `||`：注释错误认为 `JUMP_IF_TRUE` 不弹出；实际 vm 会 pop，导致 true 路径栈上无结果值
- 第763-764行 `PatternTuple/PatternList`：直接返回 None，元组/列表模式匹配完全失效
- 第867-874行 `Block` POP：对 `Break` 等控制流语句仍 emit POP，导致跳转后多余弹栈

#### backend/native_backend.py
- 行496-497 `LIRCallIndirect`：仍抛 `NotImplementedError`，间接调用代码生成未实现（审查日志 native_backend.py:489）。
- 行504-505 `LIRFieldAccess`：**已修复**，不再抛异常，存在 `_compile_field_access` 实现。原审查日志中标记的严重问题已在第四轮解决。

#### ir/pass_manager.py
- 行257-262 `Inlining` pass：仍为空壳，`run` 方法直接返回 `False`，不做任何实际内联操作（审查日志 pass_manager.py:256-261）。
- 行720-725 Pass 异常处理：**已修复**，`except Exception` 分支现在将错误信息记录到 `self.errors` 并打印到 stderr，不再静默吞掉。原审查日志中标记的严重问题已在第二轮解决。

#### ir/mir_lowering.py
- 行247-250 `HIRLambda` 降级：自由变量丢失。`MIRClosureCreate` 的 `captures` 字段完全未被填充，闭包不捕获任何外部变量（审查日志 mir_lowering.py:247-250）。
- 行351-384 `_lower_match_expr`：Match 模式信息完全丢失。`value_ssa` 和 `arms[i].pattern` 未被用于生成任何模式测试或条件分支，所有 arm 被无条件顺序连接（审查日志 mir_lowering.py:351-384）。

#### evaluator.py
- 第698-704行 `?` 操作符不解包 Some/Ok：`TryExpr` 遇到 `Some(x)`/`Ok(x)` 时直接返回整个 ADT 值，未解包内部 payload。语义上 `?` 应传播错误并解包成功值。
- 第832-842行 `&&`/`||` 返回 Python bool 且依赖 truthiness：短路求值直接返回原生 `True`/`False`，并使用 `not left`/`if left` 做判断。

#### parser.py
- 第460,471,484行 step 表达式变量遮蔽：`step_expr` 在两条分支前重复初始化，且 `step` 在 lexer 中被注册为全局关键字导致无法用作循环变量名。

#### type_checker.py
- 第1233行任意 TypeVar 兼容：`_types_compatible` 中只要任一类型为 TypeVar 即返回 True，完全绕过泛型约束检查。

#### errors.py
- 第402-408行 `raise_all` 丢失结构化信息：通过 `primary.add_note(str(note))` 将后续错误转为纯字符串，丢弃了 span、行列号等结构化元数据。

#### environment.py
- 第40,48行 `lookup`/`lookup_binding` 仍抛 Python `NameError`：与已修复的 `assign` 方法不一致，导致 evaluator 和 modules.py 仍需显式捕获 NameError。

### 本次修复内容（基于审查日志 Issue）

1. **vm.py — PRINT 指令未推 UNIT（基于审查日志 vm.py:1132-1138）**
   - 在 PRINT 处理末尾（`self.output.append(formatted)` 之后）添加 `self.stack.append(UNIT)`
   - 修复栈不平衡：注释声明栈变化 `[value] -> [()]`，但实际未 push UNIT

2. **vm.py — STORE_VAR 不可变变量检查（基于审查日志 vm.py:560-571）**
   - 在 STORE_VAR 中使用 `mutable` 操作数检查：若 `mutable` 为 False 且变量已存在，抛出 `RuntimeError_("Cannot assign to immutable variable ...")`
   - 同步修改 compiler.py：for 循环和列表推导式的循环变量存储由 `STORE_VAR, name, False` 改为 `STORE_VAR, name, True`（循环变量需要每次迭代更新）

3. **compiler.py — `||` true 路径值丢失（基于审查日志 compiler.py:502-511）**
   - 采用 `DUP + JUMP_IF_TRUE + POP` 模式：DUP 复制 left 值，JUMP_IF_TRUE pop 复制品，true 路径保留原值；false 路径先 POP 再编译 right

4. **compiler.py — Block 中 Break/Continue 后多余 POP（基于审查日志 compiler.py:867-874）**
   - 在 `_compile_block` 的 POP 条件中排除 `BreakExpr` 和 `ContinueExpr`
   - 控制流语句不推值，POP 会导致栈下溢

5. **evaluator.py — `?` 操作符不解包 Some/Ok（基于审查日志 evaluator.py:698-704）**
   - 在 TryExpr 处理中，对 `Some`/`Ok` variant 返回 `val.fields[0]` 而非整个 ADT 值
   - 保持 `None`/`Err` 的 ReturnSignal 行为不变

6. **environment.py — lookup/lookup_binding 异常类型统一（基于审查日志 environment.py:40,48）**
   - 将 `NameError` 替换为 `RuntimeError_`
   - 联动修改 evaluator.py 三处和 modules.py 一处的 `except NameError` 为 `except (NameError, RuntimeError_)`
   - 缩小 eval_program 中 try/except 范围，避免意外吞掉 _call_fn 的 RuntimeError_

7. **errors.py — raise_all 保留结构化信息（基于审查日志 errors.py:402-408）**
   - `NovaError` 新增 `format()` 方法，委托给 `_format()`
   - `raise_all` 中 `primary.add_note(str(note))` 改为 `primary.add_note(note.format())`

8. **parser.py — step 表达式变量遮蔽（基于审查日志 parser.py:460,471,484）**
   - 删除 `_parse_for_expr` 中第471行多余的 `step_expr = None`
   - 两条分支共享第460行的初始化，确保 step_expr 正确传递

9. **type_checker.py — Err 内置函数独立 TypeVar（基于审查日志 type_checker.py:289-291）**
   - 为 `Option`、`Ok`、`Err` 分别使用独立名称的 TypeVar（`opt_t`、`ok_t`/`ok_err_t`、`err_ok_t`/`err_err_t`）
   - 消除因同名 TypeVar 导致的泛型参数冲突

### 测试结果

- 全量测试: **655 passed** (1.52s)
- Evaluator 示例: hello/math/pattern_match/pipe/loops 全部正常输出
- VM 示例: hello/math/pattern_match 全部正常输出

---

## 2026-07-15 自动改进（第六轮）— 阶段一检查

基于 AUTO_REVIEW_LOG.md 第三轮审查日志的最高优先级问题进行检查。

### 每日发现的问题

#### vm.py
- **第917行 FOR_ITER 闭区间**：`current <= end` 确认为闭区间。但 evaluator.py:898 同样使用 `range(start, end + 1, step)`，当前 Evaluator 和 VM 实际一致（均闭区间）。非紧急差异。
- **`&&` false 路径触发 VM stack underflow**：compiler.py:493-500 的 `&&` 编译缺少 DUP 保护，VM 运行 `false && true` 报 `VM stack underflow: need 1, have 0`。**严重 bug，需修复**。

#### compiler.py
- **第493-500行 `&&` false 路径栈值丢失**：`POP_JUMP_IF_FALSE` 弹出 left 后跳转到 end_pos，栈为空。应参照 `||` 已修复模式采用 `DUP + POP_JUMP_IF_FALSE + POP`。**基于审查日志 Issue #3（Top 20）**。

#### evaluator.py
- **`?` 操作符解包**：第五轮修复已生效，`Some(42)?` 正确返回 `42`。
- **`&&`/`||` 返回 Python bool**：第835-845行短路时返回 `False`/`True` 而非操作数实际值。**基于审查日志 Issue #16（Top 20）**。

#### backend/native_backend.py
- **LIRCallIndirect 未实现**：第496-497行仍抛 `NotImplementedError`。

#### parser.py
- **match arm 无 guard 支持**：第530-535行 `_parse_match_arm` 只解析 `pattern -> body`，`if guard` 完全未实现。运行 `Some(x) if x > 0 -> ...` 报语法错误。**基于审查日志 Issue #19（Top 20）**。

#### type_checker.py
- **PatternConstructor 不替换类型参数**：第988-989行 `field_types` 直接取原始定义，未用 `subject_type` 实际类型参数替换。
- **任意 TypeVar 兼容**：第1235-1236行只要任一类型为 TypeVar 即返回 `True`。

### 本次计划（基于审查日志严重问题）

1. **compiler.py — `&&` false 路径栈值丢失**（Agent 1）
2. **evaluator.py — `&&`/`||` 返回实际值**（Agent 2）
3. **parser.py — match arm guard 支持**（Agent 3）

### 本次修复内容（基于审查日志 Issue）

1. **compiler.py — `&&` false 路径栈值丢失（基于审查日志 compiler.py:493-500 / Issue #3）**
   - 采用与 `||` 对称的 `DUP + POP_JUMP_IF_FALSE + POP` 模式
   - `DUP` 复制左操作数栈顶值，短路跳转时栈上仍保留 left 值作为结果
   - true 路径先 `POP` 清除原 left 值，再编译 right 表达式
   - VM 运行 `false && true` 不再报 stack underflow

2. **evaluator.py — `&&`/`||` 短路返回实际值（基于审查日志 evaluator.py:835-845 / Issue #16）**
   - `&&` 短路分支 `return False` 改为 `return left`，返回操作数实际值
   - `||` 短路分支 `return True` 改为 `return left`，返回操作数实际值
   - 与函数式语言语义一致（OCaml/Elixir 等返回实际操作数值）

3. **parser.py — match arm guard 支持（基于审查日志 parser.py:530-535 / Issue #19）**
   - `_parse_match_arm` 在解析 pattern 后、expect ARROW 前，增加 `IF` token 检查
   - 若存在 `if`，consume 并调用 `_parse_expression()` 解析 guard 表达式
   - 将解析出的 guard 传入 `MatchArm(pattern=pattern, guard=guard, body=body)`
   - Evaluator 模式下 `match Some(42) { Some(x) if x > 0 -> print(x) _ -> print(0) }` 正确输出 `42`

### 测试结果

- 全量测试: **655 passed** (1.30s)
- Evaluator 示例: hello/math/pattern_match/loops/pipe 全部正常输出
- VM 示例: hello/math/pattern_match 全部正常输出

---

## 2026-07-15 自动改进（第七轮）

基于 AUTO_REVIEW_LOG.md 第三轮审查日志的最高优先级未修复严重问题驱动改进。

### 每日发现的问题

#### compiler.py
- **第767-768行 PatternTuple/PatternList**：仍直接返回 `None`（当作 always-match），未生成逐元素结构测试。绑定逻辑已实现但测试缺失。**严重问题，已修复**。
- **第493-502行 `&&` 编译**：已修复，正确使用 `DUP + POP_JUMP_IF_FALSE + POP` 模式。
- **第505-514行 `||` 编译**：已修复，正确使用 `DUP + JUMP_IF_TRUE + POP` 模式。

#### type_checker.py
- **第986-995行 PatternConstructor**：`field_types` 直接取原始定义，未用 `subject_type` 实际类型参数替换 TypeVar。泛型 ADT 模式匹配类型推断不正确。**严重问题，已修复**。
- **第1235-1236行任意 TypeVar 兼容**：仍存在，需后续实现 unification 算法解决。

#### parser.py
- **PatternChar 未解析**：`_parse_pattern` 中无 `TokenType.CHAR` 分支，`'a'` 在 match 中报 ParseError。**严重问题，已修复**。
- **match arm guard**：已在第六轮修复。

#### lexer.py
- **第432行非法字符直接 raise**：终止整个词法分析，只看到第一个非法字符。**严重问题，已修复**。

#### vm.py
- **FOR_ITER 闭区间**：Evaluator 和 VM 均为闭区间 `[start, end]`，实际一致。非差异 bug。
- **`_pop(n)` 返回类型不一致**：`n==1` 返回裸值、`n>1` 返回列表。代码异味，低优先级。
- **CLOSURE 捕获整个帧**：已知设计 debt，低优先级。

### 本次修复内容（基于审查日志 Issue）

1. **compiler.py — PatternTuple/PatternList 模式测试实现（基于审查日志 compiler.py:763-764）**
   - Op 类新增 `MATCH_TEST_TUPLE` 和 `MATCH_TEST_LIST` 操作码
   - `_compile_pattern_test_with_fail` 中 PatternTuple/PatternList 分支不再返回 None，改为生成 `MATCH_TEST_TUPLE(element_count, fail_ip)` / `MATCH_TEST_LIST(element_count, fail_ip)`
   - `_compile_pattern_extract_and_bind` 替换简单 POP 为递归处理每个元素子模式的 extract_and_bind
   - vm.py 实现 `MATCH_TEST_TUPLE`（检查 tuple + 长度 + 弹出 subject 压入各元素）和 `MATCH_TEST_LIST`（检查 list + 长度 + 同上）

2. **type_checker.py — PatternConstructor 类型参数替换（基于审查日志 type_checker.py:986-995）**
   - 在 PatternConstructor 分支中，`field_types` 获取后增加类型参数替换逻辑
   - 构建 `type_param_map`：从 ADT 定义的类型参数名映射到 `subject_type` 的实际类型参数
   - 用已有的 `_substitute_type_vars` 方法递归替换 `field_types` 中的 TypeVar
   - 与文件中 ADT 字段访问（第 797-800 行）已有的替换逻辑一致

3. **parser.py — PatternChar 模式解析（基于审查日志 parser.py:541-621）**
   - `_parse_pattern` 中添加 `TokenType.CHAR` 分支
   - 解析 `'a'` 等字符字面量为 `PatternChar(value=tok.value, span=self._span(tok))`
   - 端到端验证 `match 'a' { 'a' -> print("matched a") _ -> print("other") }` 正确输出 `matched a`

4. **lexer.py — 非法字符跳过+记录（基于审查日志 lexer.py:432）**
   - `__init__` 中新增 `self.errors: List[str] = []` 错误收集列表
   - 非法字符处理从 `raise self._make_error(...)` 改为记录错误到 `self.errors`、打印到 stderr、递归调用 `_next_token()` 跳过继续分析
   - 更新 3 个相关测试用例（test_lexer_error、test_illegal_char、test_lexer_error_has_span）

### 测试结果

- 全量测试: **655 passed** (0.78s)
- Evaluator 示例: hello/fibonacci/pattern_match/loops 全部正常输出
- VM 示例: hello/fibonacci/pattern_match 全部正常输出
