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