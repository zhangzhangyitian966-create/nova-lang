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
