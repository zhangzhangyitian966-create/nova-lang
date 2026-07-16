# Nova 自动改进日志

## 2026-07-16 自动改进（第三十三轮）

基于 AUTO_REVIEW_LOG.md 第二十七轮审查日志的 P0 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py
- **顶层match绑定变量泄漏到globals（vm.py:1378-1386）**：MATCH_START/MATCH_ARM_START/MATCH_END 的 match_snapshots 机制只在函数帧内（call_stack非空）生效，顶层match arm绑定的变量永久泄漏到globals且arm之间不清理
  - 审查日志追问结论：不能接受。作用域规则是语言的基础契约
  - 根因：实现时错误认为"顶层本身就是全局作用域不需要快照"，忽略了match arm之间的作用域隔离
  - 影响：顶层match表达式中，前一个arm绑定的变量会泄漏到后一个arm，以及match之后的代码
  - 验证：顶层match两个arm分别绑定不同变量名，第二个arm能访问第一个arm的绑定

#### evaluator.py
- **`_builtin_filter`谓词非Bool时使用`is True`静默失败（evaluator.py:266）**：谓词返回Nova Bool ADT类型或任何非Python True的真值时，`is True`判定为False，所有元素被静默过滤为空列表
  - 审查日志追问结论：绝对不能。这是类型安全的基本要求
  - 根因：直接用Python身份检查替代类型检查，假设谓词总是返回Python原生bool
  - 影响：使用Nova Bool类型（如模式匹配守卫、ADT构造的Bool）的filter函数总是返回空列表
  - 验证：filter (fn x -> if x > 0 then True else False) [1,2,3] 返回空列表

- **字符串索引返回Python str而非NovaChar（evaluator.py:996-1009）**：IndexExpr对字符串索引直接返回Python str单字符，与字符字面量的NovaChar类型不一致，导致`"abc"[0] == 'a'`为False
  - 审查日志追问结论：不能。类型一致性是静态类型语言的基础
  - 根因：实现索引操作时未考虑字符类型，直接依赖Python的str索引行为
  - 影响：字符串索引结果与字符字面量类型不匹配，相等性检查失败
  - 验证：VM中同样存在此问题，两处实现都未包装NovaChar

#### errors.py
- **单线下划线off-by-one，所有错误高亮少一个字符（errors.py:271-274）**：lexer的end_col是包含式的，但下划线计算按排除式处理，`end_col - start_col`个caret应为`end_col - start_col + 1`
  - 审查日志追问结论：绝对不能。错误高亮必须精确到字符级，这是生产级编译器的基本要求
  - 根因：未统一end_col语义，lexer用包含式，错误格式化按排除式计算
  - 影响：所有单字符token的错误高亮没有caret，多字符token少最后一个字符的高亮
  - 验证：对span(1,1,1,1)应显示1个caret，实际显示0个

- **RelatedNote跨文件错误显示主错误的源码（errors.py:232-261）**：RelatedNote没有自己的source_code字段，渲染时使用主错误的source_code，指向不同文件时显示的代码行完全错误
  - 审查日志追问结论：（隐含在错误系统质量要求中）
  - 根因：RelatedNote设计时假设note与主错误在同一文件，未考虑跨文件场景
  - 影响：跨模块的类型错误、导入错误等的RelatedNote显示误导性的源码上下文
  - 验证：在模块A中定义、模块B中使用的符号发生错误时，RelatedNote显示模块A的行号但内容是模块B的代码

#### modules.py
- **包导入路径遍历漏洞，可通过`..`跳出搜索目录（modules.py:134-138）**：包导入路径直接拼接到search_path后未做安全检查，`std/../../etc/passwd`形式可读取任意文件
  - 审查日志追问结论：绝对不能。这是严重的安全漏洞
  - 根因：实现模块解析时只考虑了功能正确性，未考虑安全边界
  - 影响：恶意模块可构造路径读取系统敏感文件（如存在且后缀匹配）
  - 验证：构造包含`..`段的包路径，解析后的绝对路径不在search_path内

#### lexer.py + parser.py
- **`<-`由LT+MINUS双token合成，歧义风险高（parser.py:470-472）**：`for x < -1 { ... }`会被误解析为范围循环，因为解析器看到LT后直接消费MINUS构成`<-`
  - 审查日志追问结论：不能。生产级语言将`<-`作为单一token处理
  - 根因：为省事在parser层面合成token，未在lexer层面做专用token
  - 影响：比较表达式`x < -1`出现在for循环位置时被误解析为范围循环
  - 验证：`for x < -1 { x }` 应该报错（不是合法的for语法）但实际被解析为范围循环

- **编译器管道完全忽略词法错误（compiler_pipeline.py:50）**：lexer.errors中的非法字符、未闭合字符串等在主编译管道中被完全丢弃，带词法错误的代码继续进入parser
  - 审查日志追问结论：绝对不能。词法错误应当阻止编译继续
  - 根因：实现编译管道时只考虑了happy path，未集成错误收集
  - 影响：词法错误产生级联的语法错误，用户看到的错误信息与真正的问题无关
  - 验证：输入含非法字符的代码，错误报告指向语法错误而非词法错误

- **match分支检测遗漏负数模式起始Token（parser.py:528）**：`_parse_match_expr`的while循环检测更多分支时未包含TokenType.MINUS，第二个及之后的分支以负数开头时被误判为分支结束
  - 审查日志追问结论：是bug。明确的功能不完整
  - 根因：枚举模式起始token时漏掉了负数模式的MINUS
  - 影响：`match x { 0 => "zero", -1 => "neg", _ => "other" }` 中 `-1` 分支无法被解析
  - 验证：多分支match中第二个分支以负整数/负浮点数开头，解析失败

### 本次修复内容（基于审查日志第二十七轮 Issue）

1. **vm.py — 顶层match绑定泄漏修复（基于审查日志第二十七轮VM严重问题 #5）**
   - 为顶层代码实现与函数帧对称的 `match_snapshots` 机制
   - VM.__init__ 新增 `_top_match_snapshots: List[set] = []`
   - MATCH_START：顶层时保存 globals 当前所有键的快照并入栈
   - MATCH_ARM_START：顶层时恢复快照（删除新增变量）后重新保存
   - MATCH_END：顶层时恢复快照并出栈
   - 嵌套match通过栈结构正确处理

2. **evaluator.py + vm.py — filter谓词类型检查（基于审查日志第二十七轮Evaluator严重问题 #1 / VM中等问题延伸）**
   - 将 `_builtin_filter` 中的 `is True` 改为显式Bool类型检查
   - 兼容Python原生bool和Nova Bool ADT两种表示
   - 非Bool类型时抛出 `RuntimeError_("filter 谓词必须返回 Bool 类型")`
   - Evaluator和VM两处同步修复

3. **evaluator.py + vm.py — 字符串索引返回NovaChar（基于审查日志第二十七轮Evaluator严重问题 #3 / VM一致性问题）**
   - Evaluator的IndexExpr处理中，字符串索引结果包装为NovaChar
   - VM的INDEX操作码中，字符串索引结果包装为NovaChar
   - 列表/元组/Map索引不受影响
   - 两端同步修复保证语义一致

4. **errors.py — 错误下划线off-by-one修复 + RelatedNote源码隔离（基于审查日志第二十七轮错误处理严重问题 #1/#2/#6）**
   - 单行caret数量：`end_col - start_col` → `end_col - start_col + 1`
   - 多行首行caret：修正为包含最后一列
   - 多行末行caret：修正为从第1列到end_col共end_col个
   - RelatedNote下划线重构为复用 `_compute_underline`（消除重复代码+自动修复off-by-one）
   - RelatedNote新增 `source_code` 字段，渲染时优先使用note自己的源码
   - add_note/add_help 新增可选 source_code 参数

5. **modules.py — 包导入路径遍历安全加固（基于审查日志第二十七轮模块系统严重问题 #2）**
   - 包路径防御性检查：包含 `..` 段时直接抛出错误
   - 路径范围验证：解析后的绝对路径必须在对应search_path内
   - 相对导入（`./`、`../` 开头）保持不变（设计上允许）

6. **lexer.py + parser.py — LEFT_ARROW专用token + 负数模式分支修复 + 词法错误检查（基于审查日志第二十七轮词法/语法分析器严重问题 #1/#2/#3）**
   - lexer新增 `LEFT_ARROW` token类型，`<-`作为单一token识别
   - parser的 `_parse_for_expr` 和 `_parse_list_comprehension` 改用 LEFT_ARROW
   - `_parse_match_expr` 分支检测token列表添加 `TokenType.MINUS`
   - 编译管道所有入口点添加词法错误检查
   - backend/compiler_pipeline.py、_cli.py、compiler_cli.py 等入口同步添加
   - 新增10个测试用例覆盖所有修复点

### 测试结果

- 全量测试: **960 passed** (1.42s)
- Evaluator 示例: hello/fibonacci/pattern_match/loops/math/pipe/list_comprehension/file_io 全部正常输出
- VM 示例: hello/fibonacci/pattern_match/loops/math/list_comprehension/pipe/file_io 全部正常输出
- 顶层match绑定隔离: arm之间变量不泄漏 ✅ / match结束后绑定清理 ✅
- filter谓词类型检查: Python bool ✅ / Nova Bool ADT ✅ / 非Bool抛错 ✅
- 字符串索引NovaChar: `"abc"[0] == 'a'` 返回True ✅
- 错误下划线修正: 单行end_col包含式正确 ✅ / RelatedNote复用统一方法 ✅
- RelatedNote跨文件: 自有source_code优先 ✅ / 无则回退主错误 ✅
- 路径遍历防护: `..`段检测 ✅ / search_path范围检查 ✅
- LEFT_ARROW专用token: `<-`单一token ✅ / `<`比较不受影响 ✅
- 词法错误检查: 所有编译入口点均检查 ✅
- 负数模式分支: 多分支match中负整数/负浮点数正确解析 ✅

---

## 2026-07-16 自动改进（第三十二轮）

基于 AUTO_REVIEW_LOG.md 第二十六轮审查日志的 P0/P1 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### compiler.py
- **`&&` 运算符使用 POP_JUMP_IF_FALSE 污染 _while_loops 栈（compiler.py:544）**：`&&` 短路求值使用 `POP_JUMP_IF_FALSE`，该指令在 VM 中有 while 循环跟踪副作用，导致 `true && true` 执行后 `_while_loops` 栈残留假条目
  - 审查日志追问结论：不能接受。逻辑运算符不应干扰循环控制状态
  - 根因：修复栈丢失问题时直接选用了 POP_JUMP_IF_FALSE，未考虑其 while 循环跟踪副作用
  - 影响：嵌套在循环内的 `&&` 表达式可能导致 break/continue 行为异常
  - 验证：VM 执行 `true && true` 后检查 `_while_loops`，发现残留一条 end_ip 记录

#### 测试基础设施
- **无 Evaluator vs VM 一致性测试（P0 级质量基础设施缺失）**：两个后端语义漂移无法检测，只能靠人工审查发现不一致
  - 审查日志追问结论：不能接受。双后端语言必须有一致性测试保障
  - 根因：项目早期只有 Evaluator，后来添加 VM 时未同步建立一致性测试体系
  - 影响：之前已发现 Unit bool 语义、闭包捕获语义、范围迭代语义等多处不一致

### 本次修复内容（基于审查日志 Issue）

1. **compiler.py — `&&` 运算符改用 JUMP_IF_FALSE（基于审查日志 compiler.py:493-500 / 第二十六轮严重问题延伸）**
   - 将 `&&` 的 `POP_JUMP_IF_FALSE` 改为 `JUMP_IF_FALSE`，与 `||` 的实现对称
   - 消除 `_while_loops` 栈被逻辑运算符污染的问题
   - 新增 2 个测试用例：`&&` 和 `||` 均不污染循环栈

2. **tests/test_consistency.py — 建立 Evaluator vs VM 一致性测试套件（基于审查日志 P0 问题 #8）**
   - 新建一致性测试框架：`run_both()` 同时运行两端、`_normalize_value()` 规范化值比较
   - 57 个测试用例覆盖 12 大类：算术、字符串、列表、布尔逻辑、元组、ADT、函数、管道、范围迭代、错误传播、打印输出、边界情况
   - 两端值规范化处理：NovaADTValue、NovaClosure、NovaChar、Unit 等不同类统一比较
   - 所有 57 个测试全部通过，验证当前两端核心语义一致

### 测试结果

- 全量测试: **950+ passed** (合并第三十一轮修复和本轮新增)
- Evaluator 示例: hello/fibonacci/pattern_match/loops/math/pipe/list_comprehension 全部正常输出
- VM 示例: hello/fibonacci/pattern_match 全部正常输出
- `&&` 栈污染修复: `_while_loops` 执行后为空 ✅ / 与 `||` 对称 ✅
- 一致性测试: 57 个测试全部通过 ✅ / 12 大类核心功能语义一致 ✅

---

## 2026-07-16 自动改进（第三十一轮）

基于 AUTO_REVIEW_LOG.md 第二十七轮审查日志的 P0/P1 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py
- **TRY_UNWRAP 提前返回路径不弹出栈顶值（vm.py:575-577）**：`_execute_function` 中 RETURN 路径和 return_flag 路径都用 `self.stack.pop()` 弹出返回值，唯独 TRY_UNWRAP 提前返回路径用 `self.stack[-1]` 只读取不弹出，三条返回路径栈操作不一致
  - 根因：TRY_UNWRAP 指令在 None/Err 分支直接返回 True 不弹栈，`_execute_function` 收到信号后用 peek 取值，设计上与 RETURN 路径不统一
  - 影响：当前被 `_call_fn` 的 `frame.base_sp` 栈截断掩盖，暂无功能性 bug，但违反 VM 栈管理一致性原则，增加维护风险和栈不平衡隐患
  - 验证：RETURN 路径（572行）`self.stack.pop()` vs TRY_UNWRAP 路径（577行）`self.stack[-1]`，代码静态对比确认

- **read_line 内置函数不捕获 EOFError，EOF 时崩溃（vm.py:237）**：VM 的 read_line 用 lambda 内联实现直接调用 `input()`，遇到 EOF 时抛出 Python 原生 EOFError 导致崩溃；Evaluator 版则捕获 EOFError 返回空字符串，两条执行路径行为不一致
  - 根因：为省事用 lambda 一行实现 read_line，未做异常捕获和边界处理
  - 影响：用户按 Ctrl+D 或管道输入耗尽时程序崩溃输出 Python traceback，而非优雅处理；与 Evaluator 语义不一致
  - 验证：Evaluator `_builtin_read_line` 有 try/except EOFError（evaluator.py:240-244），VM 版 lambda 无任何异常处理

- **range 步长为 0 时静默空循环，与 Evaluator 不一致（vm.py:1209）**：VM 的 FOR_ITER range 分支条件 `(step > 0 and current <= end) or (step < 0 and current >= end)` 在 step==0 时两侧均为 False，直接进入迭代结束分支，静默返回空列表；Evaluator 则显式抛出 RuntimeError
  - 根因：实现 range 迭代时只考虑了正负步长，遗漏 step==0 的错误检查分支
  - 影响：步长为 0 几乎总是编程错误，静默空循环掩盖 bug；两条执行路径行为不一致，违反语言语义唯一性
  - 验证：Evaluator 抛 `RuntimeError_("range 步长不能为 0")`（evaluator.py:1175），VM 静默产生空列表，代码静态对比确认

#### compiler.py
- **模块导入名称冲突检测不完整，未检查全局变量和ADT构造器（compiler.py:366-373）**：导入声明的同名冲突检测仅检查 `self.bytecode.functions` 和 `self._builtin_names`，完全不检查已编译的全局 let/mut 绑定和 ADT 构造器名称，导入的同名变量会静默覆盖
  - 根因：冲突检测逻辑（第369行）只对比函数表和内置函数名集合，编译器没有维护全局变量名称集合，let/mut 绑定和 ADT 构造器（如 `None`/`Some`/自定义 variant）编译时只发射 `STORE_VAR` 不记录名称
  - 影响：若主模块先定义 `let x = 42` 再导入导出了 `x` 的模块，导入的 `x` 会静默覆盖原全局变量，无任何警告；导入的 ADT 构造器可覆盖内置构造器（如 `Some`）
  - 验证：构造两个模块，主模块 `let x = 1` 后导入一个导出 `x = 2` 的模块，打印 `x` 得到 2 且无 warning

- **for 循环 break_patches 字段创建但从不使用（compiler.py:1030-1034, 1148-1152）**：`_compile_for` 和 `_compile_list_comprehension` 的 for 循环栈帧中都创建了 `break_patches: []` 空列表，但 for 循环的 break 走 VM 级 `_for_iters` 路径，从不读写该字段，是死代码
  - 根因：统一 `_loop_stack` 结构时为了与 while 循环的栈帧格式一致而保留了 `break_patches` 字段，但 for 循环的 break 由 VM 通过 `_for_iters` 栈在运行时处理，不需要编译期回填
  - 影响：代码维护性问题——易误导后续开发者认为 for 循环也有编译期 break 回填逻辑；微小的内存开销
  - 验证：grep `break_patches` 显示仅 while 循环有读写，for 的两处只写不读

#### type_checker.py
- **_types_compatible 缺少 TupleType 递归兼容检查（type_checker.py:1546-1574）**：类型兼容性检查函数对 FnType/ListType/MapType/ADTType 都有递归处理，唯独 TupleType 缺失，只能依赖 __eq__ 精确相等
  - 根因：实现 _types_compatible 时遗漏 TupleType 分支，与同文件 _collect_type_bindings 对 TupleType 的完整处理形成对比
  - 影响：元组元素含 TypeVar 或嵌套需兼容判断的复合类型时，_types_compatible 错误返回 False，可能导致泛型函数与元组参数交互时的类型误报
  - 验证：构造包含嵌套类型变量的元组作为参数调用泛型函数，观察是否被错误判定为不兼容

- **? 操作符在函数外（顶层）静默通过（type_checker.py:1001,1022）**：TryExpr 类型检查中，_current_fn_return_type 为 None 时直接跳过返回类型兼容性验证，而 None 同时表示"顶层代码"和"待推断函数"两种语义
  - 根因：_current_fn_return_type = None 未区分顶层代码与无注解函数，导致顶层 ? 操作符完全不做验证
  - 影响：顶层代码中使用 ? 操作符不报错，类型检查器无法捕获该语义错误，与 VM 层静默失败问题形成双重隐患
  - 验证：在顶层代码（非函数体内）写 Option/Result 值 + ? 操作符，类型检查应报错但实际通过

- **ForExpr/ListComprehension 非列表迭代静默通过（type_checker.py:1070-1071,1107-1108）**：for 循环和列表推导式的迭代对象不是 ListType 也不是 TupleType 时，创建 TypeVar 兜底而非报错，Int/String/Map 等类型均可"迭代"
  - 根因：实现时用 TypeVar 作为兜底分支，假设后续推断会约束，但迭代操作本身就要求对象是列表或 range
  - 影响：对 Int、String、Map、Bool 等非列表类型使用 for 循环或列表推导式时，类型检查器不报错，只有运行时才失败
  - 验证：`for x in 42 { x }` 或 `[x * 2 for x in "hello"]` 应在类型检查阶段报错但实际通过

### 本次修复内容（基于审查日志 Issue）

1. **vm.py — 三项 VM 严重问题修复（基于审查日志第二十七轮 VM 严重问题 #1/#2/#3）**
   - **TRY_UNWRAP 提前返回路径栈一致化**：`_execute_function` 中 TRY_UNWRAP 路径的 `self.stack[-1]` 改为 `self.stack.pop()`，与 RETURN 路径和 return_flag 路径保持一致，消除栈管理不一致隐患
   - **read_line EOF 错误捕获**：将 lambda 内联实现改为独立 `_builtin_read_line` 方法，捕获 `EOFError` 返回空字符串，与 Evaluator 行为一致
   - **range step=0 错误抛出**：FOR_ITER 的 range 分支添加 `step == 0` 检查，抛出 `RuntimeError_("range 步长不能为 0")`，与 Evaluator 语义统一

2. **compiler.py — 两项编译器问题修复（基于审查日志第二十七轮编译器严重问题 #3/#4）**
   - **模块导入名称冲突检测完善**：新增 `_global_names` 集合跟踪全局变量名（let/mut 绑定、函数、ADT 构造器），导入时三重检查（functions + builtin_names + global_names），冲突时抛出 RuntimeError_ 替代静默覆盖
   - **for 循环 break_patches 死代码清理**：从 `_compile_for` 和 `_compile_list_comprehension` 的 for 循环栈帧中移除 `break_patches: []` 字段（for 循环 break 走 VM 级 `_for_iters` 路径，无需编译器回填），while 循环保留不变

3. **type_checker.py — 三项类型检查器严重问题修复（基于审查日志第二十七轮类型检查器严重问题 #3/#7/#8）**
   - **_types_compatible 添加 TupleType 递归检查**：参考 ListType 的处理方式，为 TupleType 添加元素级递归兼容检查，修复所有复合类型唯独元组漏掉的 copy-paste 遗漏
   - **? 操作符顶层使用报错**：新增 `_in_function` 标志区分顶层与函数内部，顶层使用 `?` 时报错 `"? 操作符只能在函数内部使用"`，无返回类型注解的函数内部仍正常工作
   - **ForExpr/ListComprehension 非列表迭代报错**：迭代对象不是 ListType 也不是 TypeVar 时，报告类型错误而非静默创建 TypeVar 兜底，增强类型系统防护能力

### 测试结果

- 全量测试: **878 passed** (1.45s)
- Evaluator 示例: hello/fibonacci/pattern_match/loops/list_comprehension/pipe/math/file_io 全部正常输出
- VM 示例: hello/fibonacci/pattern_match/loops/list_comprehension/pipe/math/file_io 全部正常输出
- VM TRY_UNWRAP 栈一致化: 三条返回路径统一 pop 语义 ✅
- VM read_line EOF: 捕获 EOFError 返回空串 ✅ / 与 Evaluator 行为一致 ✅
- VM range step=0: 步长为 0 时抛出 RuntimeError_ ✅ / 与 Evaluator 语义统一 ✅
- 编译器导入冲突: 全局变量/ADT 构造器名冲突检测 ✅ / 冲突时抛错而非静默覆盖 ✅
- 编译器 for break_patches: 死代码已清理 ✅ / while 循环不受影响 ✅
- 类型检查器 TupleType: 递归兼容检查已添加 ✅
- 类型检查器顶层 ?: 顶层使用报错 ✅ / 函数内正常工作 ✅
- 类型检查器 for 迭代: 非列表类型迭代报错 ✅ / TypeVar 暂不报错 ✅

---

---

## 2026-07-16 自动改进（第三十轮）

基于 AUTO_REVIEW_LOG.md 第二十六轮审查日志的 P0/P1 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### evaluator.py
- **闭包捕获是引用语义，与 VM 的值语义根本不一致（evaluator.py:46-53, 450-469）**：Evaluator 中闭包修改 mut 捕获变量会影响外部，VM 中则不会，同一程序在两个后端产生不同结果
  - 审查日志追问结论：不能接受。同一语言的不同执行路径必须语义一致，这是最基本的正确性要求
  - 根因：Evaluator 的 NovaClosure 持有 Environment 引用，赋值沿作用域链向上修改外部环境；VM 的 NovaClosure 持有 captured_vars 值副本，赋值只修改本地帧
  - 影响：所有包含闭包 + mut 捕获变量 + 赋值的程序，在两个后端结果不同
  - 验证：`make_counter` 函数中闭包递增 mut 变量，Evaluator 返回递增后的值，VM 返回初始值

#### compiler.py + vm.py
- **CharLiteral 被编译为 CONST_STRING，字符类型完全缺失（compiler.py:424-425）**：'a' 与 "a" 在运行时无法区分，都用 Python str 表示，类型系统根基被破坏
  - 审查日志追问结论：完全不能接受。Char 是独立的基本类型，与 String 明确区分
  - 根因：compiler.py 将 CharLiteral 编译为 CONST_STRING 指令，运行时 Char 与 String 共用 Python str 类型
  - 影响：`'a' == "a"` 返回 True、Char 可参与字符串拼接、Char 模式匹配用 `len(str)==1` hack
  - 验证：类型检查器层面 Char 与 String 是不同类型，但运行时完全无法区分

#### type_checker.py
- **PatternList 仅检查元素类型，不验证模式长度（type_checker.py:1239-1244）**：列表模式匹配时只检查主题类型是否为 ListType 及元素类型兼容性，完全不检查模式元素数量与列表长度是否匹配
  - 审查日志追问结论：中等问题。当前 PatternList 无 rest 模式，应为固定长度匹配，应当检查长度
  - 根因：实现时参考了列表同质特性忽略了长度检查，与同文件 PatternTuple 的严谨实现不一致

- **逻辑操作符错误消息硬编码为 '&&'，|| 时消息错误（type_checker.py:1296,1299）**：逻辑操作符类型检查中，左右操作数非 Bool 时的错误消息永远显示 `'&&'`，即使实际操作符是 `||`
  - 审查日志追问结论：轻微问题。功能正确但错误消息误导用户
  - 根因：复制粘贴错误，消息中硬编码了 `'&&'` 字符串，未使用 `expr.op` 变量

- **ForExpr/ListComprehension 中 Tuple 遍历取第一个元素类型（type_checker.py:1072-1073, 1108-1109）**：类型检查器允许对元组进行 for 遍历，且取第一个元素类型作为循环变量类型
  - 审查日志追问结论：中等问题。元组本不应支持 for 遍历，VM 运行时会抛出 RuntimeError_
  - 根因：类型检查器错误假设元组可迭代且元素类型一致，与 VM 的 FOR_ITER 语义不一致

- **FnCall 中绕过 _report_error 直接调用 error_collector.add（type_checker.py:781-786）**：对 TypeVar 类型值进行函数调用时，直接手动构造 TypeCheckError，而不是使用统一的 _report_error 方法
  - 审查日志追问结论：轻微问题。错误报告路径不一致，可能导致收集模式行为差异
  - 根因：早期实现遗留，统一错误报告路径时遗漏了这一处

### 本次修复内容（基于审查日志 Issue）

1. **evaluator.py — 闭包语义统一为值语义（基于审查日志 evaluator.py:46-53 / 第二十六轮严重问题 #1）**
   - 闭包创建时复制捕获变量的值，而非保存环境引用
   - 闭包内赋值只修改本地副本，不影响外部环境，与 VM 行为一致
   - 新增测试：闭包 mut 变量捕获语义一致性

2. **compiler.py + vm.py — Char 类型独立支持（基于审查日志 compiler.py:424-425 / 第二十六轮严重问题 #2）**
   - 新增 Op.CONST_CHAR 指令
   - compiler.py 中 CharLiteral 改为发射 CONST_CHAR
   - vm.py 中新增 NovaChar 运行时值类，实现 CONST_CHAR 指令
   - 修改比较/拼接等操作区分 Char 与 String
   - 新增测试：Char 与 String 类型区分、Char 模式匹配

3. **type_checker.py — 四项问题修复（基于审查日志第二十六轮中等/轻微问题）**
   - PatternList 添加模式长度检查
   - 逻辑操作符错误消息使用实际操作符
   - ForExpr/ListComprehension 中元组遍历改为报错
   - FnCall 错误报告统一使用 _report_error
   - 新增对应测试用例

### 测试结果

- 全量测试: **878 passed** (1.06s)
- Evaluator 示例: hello/fibonacci/pattern_match/loops/pipe/math/list_comprehension 全部正常输出
- VM 示例: hello/fibonacci/pattern_match 全部正常输出
- 闭包语义统一: 闭包内 mut 变量修改不影响外部 ✅ / 与 VM 行为一致 ✅
- Char 类型独立: Char 与 String `==` 返回 False ✅ / Char 比较正常 ✅ / Char 拼接报错 ✅
- 类型检查器修复: 逻辑操作符消息正确 ✅ / Tuple 遍历报错 ✅ / FnCall 错误路径统一 ✅

---

## 2026-07-16 自动改进（第二十九轮）

基于 AUTO_REVIEW_LOG.md 第二十六轮审查日志的 P0/P1 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py
- **顶层 TRY_UNWRAP 静默失败，错误值丢失（vm.py:577-587）**：顶层 `?` 操作符触发错误传播时程序静默退出，错误值残留在栈上，用户永远不知道程序为什么没有输出
  - 审查日志追问结论：不能接受。顶层错误传播应该有明确定义的行为（报错或崩溃），而非静默失败
  - 根因：`_run_code` 检测到 TRY_UNWRAP 提前返回时仅返回 False，`run()` 仅跳过 `_auto_call_main()`，未抛出 RuntimeError_
  - 影响：所有在顶层代码使用 `?` 且遇到 Err/None 的程序都会静默失败
  - 验证：构造 Err 值 + TRY_UNWRAP 的字节码，VM 运行后无任何错误，栈上残留 Err 值

- **FIELD_ACCESS 元组索引越界未捕获为 RuntimeError（vm.py:1065-1066）**：元组字段访问越界时抛出 Python 原生 IndexError 而非 Nova RuntimeError_，与 evaluator 行为不一致
  - 审查日志追问结论：不能接受。生产级 VM 必须将所有内部运行时错误统一为语言定义的错误类型
  - 根因：`obj[int(field)]` 直接访问，无 try-except 包裹
  - 延伸：ADT 索引访问（vm.py:1068-1070）同样存在 IndexError 逃逸问题
  - 验证：构造越界元组字段访问字节码，抛出原生 `IndexError: tuple index out of range`

- **BUILD_MAP 键不可哈希时抛出 Python 原生 TypeError（vm.py:1035-1045）**：不可哈希键导致 Python TypeError 直接逃逸，对比 evaluator 有详细可哈希性检查和友好错误信息
  - 审查日志追问结论：不能接受。统一错误类型是生产级解释器/VM 的基本要求
  - 根因：`result[key] = val` 直接赋值，无 try-except 包裹
  - 验证：用列表作为键构造 BUILD_MAP 字节码，抛出原生 `TypeError: unhashable type: 'list'`

#### compiler.py
- **模式匹配非穷尽时静默返回 Unit（compiler.py:780-783）**：所有 arm 都匹配失败时，弹出 subject 后压入 CONST_UNIT 作为默认值，整个 match 表达式静默返回 Unit，既无编译期穷尽性检查，也无运行时报错
  - 审查日志追问结论：绝对不能。非穷尽模式匹配是类型安全的核心保证之一，静默返回 Unit 会掩盖逻辑错误
  - 根因：type_checker 完全没有实现 match 穷尽性检查，编译器默认路径直接返回 Unit
  - 影响：所有不包含通配符 arm 的 match 表达式，只要主题值不匹配任何 arm，就会静默返回 Unit

- **带过滤条件的列表推导式不推入 _loop_stack（compiler.py:1126-1167）**：`_compile_list_comprehension` 有两条路径——无过滤时委托给 `_compile_for`（会推入 _loop_stack），有过滤时内联编译（完全不推入 _loop_stack），两条路径实现不一致
  - 审查日志追问结论：需要修复一致性。虽然当前 break 碰巧能工作，但编译器层面 _loop_stack 状态不一致，嵌套循环场景下可能出错
  - 根因：有过滤路径是独立内联实现的，复制了 for 循环的字节码生成逻辑，但遗漏了 _loop_stack 的推入/弹出

#### evaluator.py
- **ForExpr 完全忽略 step 字段，依赖 tuple hack（evaluator.py:1037-1071）**：AST 节点的 step 字段从未被读取，通过检查是否为 ("range", ...) 元组判断范围循环
  - 审查日志追问结论：不能接受。这是典型的"stringly typed"反模式，AST 字段被忽略转而依赖非类型化的 tuple 结构
  - 根因：早期实现用 tuple hack 传递 range 信息，后来添加 step 字段时未重构 evaluator 和 compiler
  - 影响：技术债务，维护困难，step 信息在 AST 中冗余存储两份

### 本次修复内容（基于审查日志 Issue）

1. **vm.py — VM 错误处理三项修复（基于审查日志 vm.py:577-587 / 第二十六轮严重问题 #1/#2/#3）**
   - **顶层 TRY_UNWRAP 静默失败修复**：`run()` 方法中检测到 TRY_UNWRAP 提前返回时抛出 `RuntimeError_("? 操作符不能在顶层使用")`，与 evaluator 行为一致
   - **FIELD_ACCESS 索引越界修复**：元组和 ADT 字段索引越界时捕获 IndexError，转换为 RuntimeError_，错误消息分别为 "元组索引越界" 和 "ADT字段索引越界"
   - **BUILD_MAP 不可哈希键修复**：构建 Map 时捕获 TypeError，遍历找到第一个不可哈希键并给出精确错误消息，与 evaluator 处理方式一致
   - 新增 5 个测试用例：顶层 `?` (None/Err) 报错、元组索引越界、ADT 索引越界、不可哈希键

2. **compiler.py — 模式匹配非穷尽 + 列表推导式循环栈修复（基于审查日志 compiler.py:780-783 / 第二十六轮严重问题 #3/#5）**
   - **模式匹配非穷尽修复**：errors.py 新增 `MatchFailure` 错误类，vm.py 新增 `__match_failure` 内置函数，编译器将默认路径从 `POP + CONST_UNIT` 改为调用 `__match_failure` 抛出匹配失败错误
   - **带过滤列表推导式循环栈修复**：有过滤条件的路径也推入 `_loop_stack`，与无过滤路径（`_compile_for`）保持一致，确保嵌套循环中 break/continue 编译正确
   - 新增 4 个测试用例：非穷尽 match 抛 MatchFailure、通配符 match 正常、带过滤列表推导式、嵌套循环带过滤推导式

3. **evaluator.py — ForExpr step 字段重构（基于审查日志 evaluator.py:1037-1071 / 第二十六轮严重问题 #3）**
   - 范围循环检测从完全依赖 tuple hack 改为优先检查 `expr.step is not None`
   - 步长获取从 `expr.iterable[3]` 改为优先从 `expr.step` 字段获取
   - 保留元组格式作为回退判断，确保向后兼容
   - 消除了 "stringly typed" 反模式，代码更清晰可维护

### 测试结果

- 全量测试: **878 passed** (1.04s)
- Evaluator 示例: hello/fibonacci/pattern_match/loops/math/pipe/list_comprehension/file_io 全部正常输出
- VM 示例: hello/fibonacci/pattern_match/loops/math/pipe/list_comprehension/file_io 全部正常输出
- VM 顶层 TRY_UNWRAP: 顶层 None/Err 的 `?` 正确抛出 RuntimeError_ ✅
- VM FIELD_ACCESS 越界: 元组/ADT 索引越界正确抛出 RuntimeError_ ✅
- VM BUILD_MAP 不可哈希键: 正确抛出 RuntimeError_ ✅
- 模式匹配非穷尽: 非穷尽 match 抛出 MatchFailure ✅ / 通配符 match 正常 ✅
- 列表推导式循环栈: 带过滤推导式基本功能 ✅ / 嵌套循环带过滤 ✅
- ForExpr step 重构: 所有 for/loop 相关测试通过 ✅

---

## 2026-07-16 自动改进（第二十八轮）

基于 AUTO_REVIEW_LOG.md 第二十五轮审查日志的 P0/P1 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### compiler.py + vm.py
- **多字段构造器/元组/列表模式中混合测试-绑定模式的栈错位（compiler.py:834-860）**：MATCH_CONSTRUCTOR/MATCH_TEST_TUPLE/MATCH_TEST_LIST 逆序压栈字段值，`_compile_pattern_test_with_fail` 正序递归测试，测试模式成功时弹出栈顶值，非测试模式（PatternIdentifier/PatternWildcard）不弹出，中间有标识符模式时后续字段测试读取错误的栈位置
  - 审查日志追问结论：绝对不能，元组/构造器模式中混合字面量和变量绑定是最常见的用法之一，这种 bug 在生产级编译器中是 P0 级缺陷
  - 根因：非测试模式在测试阶段不消耗栈值，导致后续字段测试读取错位的栈位置
  - 影响：所有包含 2 个以上字段且中间存在标识符/通配符模式的构造器、元组、列表模式都会错误匹配

#### evaluator.py
- **TryExpr 在顶层代码中导致未捕获的 ReturnSignal 异常崩溃（evaluator.py:741-752）**：`?` 操作符通过抛出 ReturnSignal 实现提前返回，仅在 `_call_fn` 中被捕获；顶层使用时 ReturnSignal 一直向上抛出
  - 审查日志追问结论：不能，语言构造在任何上下文中都应该有定义良好的行为或明确的错误
  - 根因：顶层求值路径（eval_program → _eval_decl_body → eval_expr）不经过 _call_fn，没有 ReturnSignal 捕获
  - 延伸发现：BreakSignal 和 ContinueSignal 同样存在顶层崩溃问题

#### type_checker.py
- **块表达式中 MutBinding 不检查类型标注（type_checker.py:847-850）**：在 check_expr 中处理 MutBinding 时，完全忽略了 expr.type_annotation，块内的 `mut x: Int = "hello"` 不会报类型错误
  - 审查日志追问结论：绝对不能，类型标注是用户与编译器的契约，忽略标注等于破坏类型安全保证
  - 根因：MutBinding 分支是 LetBinding 分支的简化复制，粘贴时遗漏了 type_annotation 检查逻辑

### 本次修复内容（基于审查日志 Issue）

1. **compiler.py — 模式匹配多字段混合模式栈错位修复（基于审查日志 compiler.py:834-860 / 第二十五轮严重问题 #1）**
   - 采用"测试阶段统一弹栈"方案：_compile_pattern_test_with_fail 中每个字段模式都消耗一个栈值
   - PatternWildcard：从空操作改为生成 Op.POP，弹出对应字段值
   - PatternIdentifier（非构造器）：从空操作改为生成 Op.MATCH_BIND，弹出并绑定变量
   - _compile_pattern_extract_and_bind 中对应简化：标识符/通配符/字面量均改为 pass（已在测试阶段处理）
   - 新增 11 个测试用例：构造器先绑定后字面量、三字段混合、通配符混合、元组混合、列表混合、嵌套构造器混合等

2. **evaluator.py — 顶层 TryExpr/Break/Continue 崩溃修复（基于审查日志 evaluator.py:741-752 / 第二十五轮严重问题 #3）**
   - eval_program 第二遍循环：对 _eval_decl_body 调用包裹 try/except，捕获三种控制流信号
   - ReturnSignal → RuntimeError_("? 操作符不能在顶层使用")
   - BreakSignal → RuntimeError_("break 不能在顶层使用")
   - ContinueSignal → RuntimeError_("continue 不能在顶层使用")
   - eval_decl 方法：同样添加外层保护，重构为外层方法 + _eval_decl_inner 内部实现
   - 新增 7 个测试用例：顶层 Err/None 的 ?、顶层表达式 ?、函数内 ? 回归、顶层 break、顶层 continue

3. **type_checker.py — MutBinding 类型标注检查修复（基于审查日志 type_checker.py:847-850 / 第二十五轮严重问题 #5）**
   - check_expr 中 MutBinding 分支补充与 LetBinding 对称的 type_annotation 检查逻辑
   - 类型不匹配时通过 _report_error 报告错误
   - 新增 3 个测试用例：块内 mut 类型不匹配报错、块内 mut 类型匹配通过、函数体内 mut 类型不匹配报错

### 测试结果

- 全量测试: **869 passed** (1.42~2.18s)
- Evaluator 示例: hello/fibonacci/pattern_match/loops/math/pipe/list_comprehension/file_io 全部正常输出
- VM 示例: hello/fibonacci/pattern_match/loops/math/pipe/list_comprehension/file_io 全部正常输出
- 模式匹配栈错位: 先绑定后字面量 ✅ / 三字段混合 ✅ / 通配符混合 ✅ / 元组混合 ✅ / 列表混合 ✅ / 嵌套构造器 ✅
- 顶层 TryExpr 修复: 顶层 Err/None 报错 ✅ / 函数内正常工作 ✅ / break/continue 顶层报错 ✅
- MutBinding 类型标注: 块内不匹配报错 ✅ / 块内匹配通过 ✅ / 函数体内不匹配报错 ✅

---

## 2026-07-16 自动改进（第二十七轮）

基于 AUTO_REVIEW_LOG.md 第二十四轮审查日志的 P0/P1 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py + compiler.py
- **MATCH_CONSTRUCTOR 不检查 type_name，跨类型构造器可错误匹配（vm.py:1294-1312 / compiler.py:827,834）**：仅检查 `variant_name` 和字段数量，完全不检查 `type_name`，两个不同 ADT 类型的同名同参变体会混淆
  - 审查日志追问结论：绝对不能，构造器在类型系统中是由类型+变体名共同唯一标识的
  - 根因：编译器生成 MATCH_CONSTRUCTOR 时只传了 variant_name 和 field_count，没有传 type_name；VM 端也没有 type_name 检查逻辑
  - evaluator 端同样有此问题（evaluator.py:1180-1190）

#### ir/pass_manager.py
- **Pass 管理器完全没有异常处理机制（pass_manager.py:713-744）**：三个入口函数（run_hir_passes/run_mir_passes/run_lir_passes）中 pass_.run() 调用完全裸露，任何一个 Pass 抛出异常都会直接中断整个管道，无错误上下文（哪个 pass、第几轮迭代）
  - 审查日志追问结论：绝对不能接受，生产级编译器要么正确报告错误并终止，要么优雅降级并记录
  - 根因：Pass 执行循环未用 try/except 包裹，缺少 PassError 包装类

#### type_checker.py
- **TypeVar.__eq__ 基于 name 而非 identity，作为 dict key 时同名变量被混淆（type_checker.py:178-179）**：两个同名不同实例的 TypeVar 会被视为同一个 key，在复杂嵌套泛型场景中可能导致类型推断错误
  - 审查日志追问结论：不能接受，OCaml 的类型变量每个都有唯一的 identity，绝不会因为名字相同而混淆
  - 根因：__eq__ 和 __hash__ 基于 name 字符串；3 处 type_param_map 用 TypeVar(tp) 新建对象作 key，依赖 name 匹配才能工作

### 本次修复内容（基于审查日志 Issue）

1. **vm.py + compiler.py — MATCH_CONSTRUCTOR 增加 type_name 检查（基于审查日志 vm.py:1286-1289 / 第二十四轮严重问题 #2）**
   - 编译器：MATCH_CONSTRUCTOR 操作数从 3 个增加为 4 个（增加 type_name）
   - 编译器：从 _adt_constructors 表中获取 type_name 传入指令
   - VM：MATCH_CONSTRUCTOR 实现增加 type_name 检查
   - evaluator：同步增加 type_name 检查（如果 PatternConstructor 有类型信息）
   - 补充测试：不同类型同名 variant 不会误匹配

2. **ir/pass_manager.py — Pass 执行异常包装（基于审查日志 pass_manager.py:713-744 / 第二十四轮严重问题 #5）**
   - errors.py 新增 PassError 错误类（继承 NovaError）
   - 三个入口函数用 try/except 包裹 pass_.run()
   - 捕获异常后包装为 PassError，附加上下文（pass 名称、迭代轮次、pass 类型）
   - 保持"异常向上传播"的默认语义，不破坏现有测试

3. **type_checker.py — TypeVar 改用 identity 比较（基于审查日志 type_checker.py:178-179 / 第二十四轮严重问题 #1）**
   - TypeVar.__eq__ 改为 identity 比较（self is other）
   - TypeVar.__hash__ 改为基于 id(self)
   - 重构 3 处 type_param_map：从 Dict[TypeVar, NovaType] 改为 Dict[str, NovaType]（用类型参数名作 key）
   - ADT 定义的 local_types 修复：复用 adt_ty 的 type_params 实例而非新建 TypeVar
   - _substitute_type_vars 支持两种 bindings 格式（str key 和 TypeVar key）
   - 确保现有 100 个测试全部通过

### 测试结果

- 全量测试: **848 passed** (1.19s)
- Evaluator 示例: hello/fibonacci/pattern_match/math/loops/pipe/list_comprehension/file_io 全部正常输出
- VM 示例: hello/fibonacci/pattern_match 全部正常输出
- MATCH_CONSTRUCTOR type_name 检查: 不同类型同名 variant 不会误匹配 ✅ / 同类型同 variant 正确匹配 ✅ / 带字段 variant 正确检查 ✅
- Pass 异常包装: PassError 包含 pass_name/pass_type/iteration/original_error ✅ / 异常链保留 (__cause__) ✅
- TypeVar identity 比较: 泛型推断正常 ✅ / ADT 字段类型替换正常 ✅ / 模式匹配类型替换正常 ✅ / _instantiate 正常 ✅

---

## 2026-07-16 自动改进（第二十六轮）

基于 AUTO_REVIEW_LOG.md 第二十四轮审查日志的 P0/P1 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py
- **局部变量可变性检查完全失效（vm.py:672-675）**：STORE_VAR 使用指令的 `mutable` 标志而非变量自身属性判断可变性，编译器赋值总是生成 `mutable=True`，导致不可变局部变量可被随意修改
  - 审查日志追问结论：绝对不能，不可变性是函数式语言最核心的语义保证之一
  - 根因：Frame 类只有 locals 存值，没有 local_mutable 跟踪可变性；编译器赋值恒传 True 绕过检查

#### evaluator.py
- **`_call_depth` / `_eval_depth` 递增在 try 块外，清理逻辑重复（evaluator.py:450-465 / 680-687）**：深度递增和超限检查在 try 外，超限路径需要手动回退，finally 又回退一次，结构脆弱易引入双重递减 bug
  - 审查日志追问结论：不能接受，典型的资源管理错误，会导致运行时状态不一致
  - 当前功能正确但结构有缺陷，未来重构极易引入 bug

#### type_checker.py
- **TryExpr 类型检查不完整，`?` 操作符不检查函数返回类型兼容性（type_checker.py:974-986）**：完全没有检查 `?` 所在函数的返回类型是否与错误类型兼容，相当于完全破坏了 `?` 操作符的类型安全性
  - 审查日志追问结论：不能接受，这相当于完全破坏了 `?` 操作符的类型安全性
  - 根因：TypeChecker 没有跟踪当前函数返回类型的状态

### 本次修复内容（基于审查日志 Issue）

1. **vm.py — 局部变量可变性检查修复（基于审查日志 vm.py:672-675 / 第二十四轮严重问题 #1）**
   - Frame 类新增 `local_mutable: set` 字段，跟踪哪些局部变量是可变的
   - STORE_VAR 赋值路径从 `if not mutable:` 改为 `if name not in frame.local_mutable:`
   - STORE_VAR 绑定路径在创建变量时，若 mutable=True 则将变量名加入 local_mutable 集合
   - NovaClosure 新增 `captured_mutable` 字段，闭包创建时同时捕获可变性信息
   - `_call_closure` 创建 Frame 时传入 captured_mutable 作为初始 local_mutable
   - MATCH_BIND 绑定的变量默认不可变（不加入集合）
   - MATCH_END 清理局部变量时同步清理 local_mutable
   - 新增 5 个测试用例：let 不可变赋值报错、mut 赋值正常、参数赋值报错、闭包捕获可变变量、闭包捕获不可变变量

2. **evaluator.py — 深度计数结构重构（基于审查日志 evaluator.py:450-465 / 第二十四轮严重问题 #2）**
   - `_call_fn` 方法：将 `_call_depth += 1` 和超限检查从 try 外移入 try 内
   - 移除超限路径中的手动回退代码（`_call_depth -= 1` 和 `env = old_env`）
   - `eval_expr` 方法：将 `_eval_depth += 1` 和超限检查同样移入 try 内
   - 由 `finally` 块统一处理所有清理路径，消除重复清理逻辑
   - 新增 8 个测试用例：call_depth 超限归零、正常归零、嵌套归零、环境恢复、eval_depth 超限归零、正常求值归零、深层嵌套归零、溢出时同步归零

3. **type_checker.py — TryExpr 类型检查完善（基于审查日志 type_checker.py:974-986 / 第二十四轮严重问题 #5）**
   - TypeChecker 新增 `_current_fn_return_type` 状态字段，跟踪当前函数返回类型
   - `_check_decl_body` 中 FnDef 处理：检查函数体前后保存/恢复当前返回类型
   - 重写 TryExpr 类型检查逻辑：
     - Option `?`：若函数返回类型已知且不是 Option 则报错
     - Result `?`：若函数返回类型是 Result 则检查错误类型兼容，若是其他类型则报错
     - TypeVar（待推断）暂不报错
   - 新增 6 个测试用例：Option 在 Option 函数中、Result 在 Result 函数中、Option 在 Int 函数中报错、Result 错误类型不兼容报错、Option 在 Result 函数中报错、非 ADT 使用 ? 报错

### 测试结果

- 全量测试: **842 passed** (1.02s)
- Evaluator 示例: hello/fibonacci/pattern_match/loops/math/list_comprehension/pipe/file_io 全部正常输出
- VM 示例: hello/fibonacci/pattern_match 全部正常输出
- 局部可变性检查: let 不可变赋值报错 ✅ / mut 赋值正常 ✅ / 参数赋值报错 ✅ / 闭包捕获可变性正确传递 ✅
- 深度计数重构: 超限后归零 ✅ / 正常调用归零 ✅ / 嵌套正确 ✅ / 环境恢复正确 ✅
- TryExpr 类型检查: Option/Result 正向用例通过 ✅ / 错误传播类型不兼容报错 ✅ / 跨类型传播报错 ✅

---

## 2026-07-16 自动改进（第二十五轮）

基于 AUTO_REVIEW_LOG.md 第二十三轮审查日志的 P0/P1 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py
- **while 循环 BREAK 栈深度 off-by-one（vm.py:920-924）**：`del self.stack[base_sp + 1:]` 保留了多余的 1 个元素，break 退出后栈上残留 body 的第一个值，栈不平衡
  - 审查日志追问结论：绝对不能，栈式 VM 最基础的不变式（stack invariant）破坏
  - 根因：base_sp 是 result 槽之后的深度，result 在 base_sp-1，截断应从 base_sp 开始而非 base_sp+1

- **while 循环 CONTINUE 栈深度 off-by-one（vm.py:949-955）**：每次 continue 都会在栈上多残留一个元素，循环 N 次后泄漏 N 个元素
  - 审查日志追问结论：绝对不能，典型的栈上溢 bug，会导致难以调试的内存安全问题

#### evaluator.py
- **取模运算除零未捕获 Python 异常（evaluator.py:950-953）**：`%` 操作缺少除零检查，right == 0 时 Python ZeroDivisionError 直接向上抛出
  - 审查日志追问结论：绝对不能接受，任何生产级编译器必须将所有运行时错误统一包装
  - 延伸发现：浮点除法 `10.0 / 0.0` 同样逃逸（只有 int/int 分支做了检查）

- **二元运算类型错误未统一捕获，Python TypeError 直接逃逸（evaluator.py:930-977）**：`+`, `-`, `*`, `/`, `%` 只检查了 Bool 类型，完全没有检查操作数是否为数字类型
  - 审查日志追问结论：不能接受，类型安全语言的运行时错误必须全部通过语言自身的错误系统报告
  - 延伸发现：`3 * "hello"` 静默返回字符串重复，连异常都没有

#### type_checker.py
- **内置 Option/Result 的构造函数类型变量全局共享导致类型污染（type_checker.py:293-307）**：`_setup_builtins` 中创建的 TypeVar 是全局共享的单一对象，每次使用都是同一个，缺少 instantiate 机制
  - 审查日志追问结论：不能，OCaml 中每个多态值的使用都会实例化新鲜的类型变量
  - 影响：`map(Some, [1,2,3])` 推断为 `List[Option[opt_t]]` 而非 `List[Option[Int]]`

### 本次修复内容（基于审查日志 Issue）

1. **vm.py — while 循环 BREAK 栈深度修复（基于审查日志 vm.py:920-924 / 第二十三轮严重问题 #1）**
   - BREAK 截断从 `del self.stack[base_sp + 1:]` 改为 `del self.stack[base_sp:]`
   - 条件判断从 `base_sp + 1 < len(self.stack)` 改为 `base_sp < len(self.stack)`
   - break 退出后栈深度 = base_sp，与正常退出一致，栈平衡

2. **vm.py — while 循环 CONTINUE 栈深度修复（基于审查日志 vm.py:949-955 / 第二十三轮严重问题 #2）**
   - CONTINUE 截断从 `del self.stack[base_sp + 1:]` 改为 `del self.stack[base_sp:]`
   - 每次 continue 后栈深度 = base_sp，不会逐次泄漏
   - 新增 6 个测试用例验证 break/continue 栈平衡（单层、嵌套、函数内）

3. **evaluator.py — 算术运算全面类型检查 + 除零检查 + try/except 兜底（基于审查日志 evaluator.py:950-953 / 第二十三轮严重问题 #1）**
   - 为 `+`, `-`, `*`, `/`, `%` 五个操作符统一添加数字类型检查（int/float）
   - 为 `%` 添加完整除零检查（int 和 float）
   - 为 `/` 的 float 分支补全除零检查
   - 所有运算包裹在 try/except 中，ZeroDivisionError 和 TypeError 统一包装为 RuntimeError_
   - 一元负号运算同步添加类型检查和兜底
   - 新增 10 个测试用例（除零 4 个 + 类型不匹配 6 个）

4. **type_checker.py — 类型变量 instantiate 机制（基于审查日志 type_checker.py:293-307 / 第二十三轮严重问题 #3）**
   - 新增 `_instantiate(self, ty)` 方法：递归遍历类型，将 TypeVar 替换为全新的 TypeVar 副本
   - 使用 `id(ty)` 作为 mapping 的 key，避免基于 name 的 `__eq__` 导致的混淆
   - 在表达式的 Identifier 查找中调用 `_instantiate`，每次使用泛型值得到独立的类型变量
   - 增强 `_collect_type_bindings`：TypeVar 已绑定时递归向下传递约束
   - 增强 `_substitute_type_vars`：支持传递替换，递归替换所有子结构
   - 新增 5 个测试用例：map+Some 组合推断、多次使用独立性、高阶函数谓词、head 实例化、None 多类型兼容

### 测试结果

- 全量测试: **823 passed** (1.74s)
- Evaluator 示例: hello/fibonacci/pattern_match/pipe/loops 全部正常输出
- VM 示例: hello/fibonacci/pattern_match 全部正常输出
- while break/continue 栈平衡: 单层/嵌套/函数内全部栈平衡 ✅
- 算术运算除零: int/float 的 `/` 和 `%` 全部正确抛出 RuntimeError_ ✅
- 算术运算类型检查: 非数字操作数正确抛出 RuntimeError_ ✅
- 类型变量实例化: `map(Some, [1,2,3])` 正确推断为 `List[Option[Int]]` ✅

---

## 2026-07-16 自动改进（第二十四轮）

基于 AUTO_REVIEW_LOG.md 第二十二轮审查日志的 P0/P1 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py
- **TRY_UNWRAP 提前返回不清理迭代器状态（vm.py:1399-1418 / 425-479）**：`_call_closure` 的 finally 块只恢复栈和帧，完全不清理 `_for_iters`、`_while_loops`、`_range_index`、`_list_index` 四个循环状态结构
  - 审查日志追问结论：绝对不能，典型的资源泄漏+状态错乱 bug
  - 复现：单层 for 循环内 `?` 提前返回 → `_for_iters` 残留 1 条、`_list_index` 残留 1 键
  - 影响：内存泄漏 + 同一 VM 实例后续循环行为错乱

- **顶层 TRY_UNWRAP 失败后仍执行 main()（vm.py:507-511）**：`_run_code` 遇到 TRY_UNWRAP early return 只是 break 退出循环，不返回状态；`run()` 无条件调用 `_auto_call_main()`
  - 审查日志追问结论：绝对不能，静默忽略错误是严重的语义错误
  - 复现：`fn main() { print("called") }; let x = None?` → VM 输出 "called"，Evaluator 抛出 ReturnSignal 终止程序
  - 与 Evaluator 语义不一致

- **CONTINUE/BREAK 在无对应循环时静默失败（vm.py:926-947 / 888-924）**：CONTINUE 无循环上下文时完全静默 fall through；BREAK 无循环时走脆弱前向扫描
  - 审查日志追问结论：不能，break/continue 不在循环中是静态错误
  - 与 Evaluator 不一致：Evaluator 中 BreakSignal/ContinueSignal 会向上传播

#### lexer.py
- **字符串末尾反斜杠 + EOF 导致词法分析器崩溃（lexer.py:236-238）**：`"hello\` 这种输入触发 IndexError，恶意输入可导致进程级崩溃
  - 审查日志追问结论：绝对不能，P0 级崩溃性 bug
  - 根因：`_read_string` 跳过反斜杠后直接 `_advance()` 读转义字符，未检查 EOF

- **字符字面量末尾反斜杠 + EOF 同样崩溃（lexer.py:284-286）**：`'\` 触发 IndexError，与字符串问题同理
  - 审查日志追问结论：绝对不能，P0 级崩溃性 bug

#### parser.py
- **Fn[...] 函数类型返回类型恒为 Unit（parser.py:335-346）**：`Fn[Int, Bool]` 被解析为 `(Int, Bool) -> Unit` 而非 `(Int) -> Bool`
  - 审查日志追问结论：绝对不能，类型系统层面的基本正确性问题
  - 根因：所有类型参数全部放入 params，return_type 硬编码为 TypeUnit

- **? 操作符只能应用一次，无法链式调用（parser.py:764-768）**：`expr??`、`foo?()`、`foo?.bar` 全部语法错误
  - 审查日志追问结论：不能，? 是后缀运算符，应与其他后缀操作同优先级
  - 根因：`?` 在后缀 while 循环外面，函数调用/字段访问/索引访问在循环内

#### evaluator.py
- **表达式求值无递归深度保护（evaluator.py:676-885）**：eval_expr 是纯递归实现，深度嵌套表达式会触发 Python RecursionError
  - 审查日志追问结论：不能，DoS 攻击向量
  - 复现：100 层嵌套算术表达式就触发 RecursionError
  - `_call_depth` 只保护函数调用递归，不保护表达式嵌套递归

- **Block 求值缺少 try-finally，异常路径环境泄漏（evaluator.py:766-776）**：BreakSignal/ContinueSignal/ReturnSignal/RuntimeError_ 等异常导致 `self.env = old_env` 不执行
  - 审查日志追问结论：绝对不能，P0 级严重缺陷
  - 复现：while 循环体内 break 后，循环体 Block 中定义的变量泄漏到外部
  - 对比：`_call_fn` 和 `_eval_for_expr` 都正确使用了 try-finally

- **while 循环体没有独立作用域，与 for 循环不一致（evaluator.py:1015-1030）**：for 循环每次迭代创建 child_env，while 直接在当前环境执行
  - 审查日志追问结论：不能，违反最少意外原则
  - 与问题 2 有叠加效应：while 无 try-finally 兜底，Block 泄漏后环境永久污染

### 本次修复内容（基于审查日志 Issue）

1. **vm.py — TRY_UNWRAP 提前返回清理迭代器状态（基于审查日志 vm.py:1399-1418 / 第二十二轮 P0 级 #4）**
   - `_call_closure` 入口保存四个循环状态的深度/键集合
   - `_for_iters`（list）：保存 len，finally 中截断多余元素
   - `_while_loops`（list）：保存 len，finally 中截断多余元素
   - `_range_index`（dict）：保存调用前 keys 集合，finally 中删除新增 key
   - `_list_index`（dict）：同理
   - 函数提前返回时内部循环状态正确清理，不泄漏到外层

2. **vm.py — 顶层 TRY_UNWRAP 失败后不执行 main()（基于审查日志 vm.py:507-511 / 第二十二轮 P1 级 #17）**
   - `_run_code` 改为返回 bool：True=正常结束，False=TRY_UNWRAP 提前返回
   - `run()` 根据返回值决定是否调用 `_auto_call_main()`
   - 顶层 `?` 失败时程序正确终止，与 Evaluator 语义一致

3. **vm.py — CONTINUE/BREAK 无循环时报错（基于审查日志 vm.py:926-947 / 第二十二轮 P1 级 #29）**
   - BREAK 无循环上下文时抛出 RuntimeError_："'break' 不在循环中"
   - CONTINUE 无循环上下文时抛出 RuntimeError_："'continue' 不在循环中"
   - 移除 BREAK 的脆弱前向扫描 fallback
   - 与 Evaluator 行为一致

4. **lexer.py — 字符串/字符反斜杠+EOF 崩溃修复（基于审查日志 lexer.py:236-238 / 第二十二轮 P0 级 #14）**
   - `_read_string()` 跳过反斜杠后增加 EOF 检查
   - `_read_char()` 同理添加 EOF 检查
   - 到达 EOF 时按未闭合字符串/字符处理，避免 IndexError 崩溃
   - 两处修复模式一致，防御恶意输入导致的 DoS

5. **parser.py — Fn[...] 返回类型解析修复（基于审查日志 parser.py:335-346 / 第二十二轮 P1 级 #22）**
   - 读取所有类型参数到 params 列表
   - 非空时：取最后一个作为 return_type，其余作为 param_types
   - 空列表时（`Fn[]`）：param_types 为空，return_type = TypeUnit
   - `Fn[Int, Bool]` 现在正确解析为 `(Int) -> Bool`

6. **parser.py — ? 操作符链式调用支持（基于审查日志 parser.py:764-768 / 第二十二轮 P1 级 #21）**
   - 将 `?` 解析从后缀 while 循环外部移入循环内部
   - 与函数调用、字段访问、索引访问同级
   - 支持 `expr??`、`foo?()`、`foo?.bar` 等链式用法

7. **evaluator.py — 表达式递归深度保护（基于审查日志 evaluator.py:676-885 / 第二十二轮 P0 级 #15）**
   - 新增 `_eval_depth` 计数器和 `MAX_EVAL_DEPTH = 1000`
   - `eval_expr` 入口递增并检查阈值，超过抛 RuntimeError_("表达式嵌套过深")
   - try-finally 确保退出时递减计数器
   - 与 `_call_depth` / `MAX_CALL_DEPTH` 模式一致

8. **evaluator.py — Block try-finally 环境恢复（基于审查日志 evaluator.py:766-776 / 第二十二轮 P1 级 #16）**
   - 用 try-finally 包裹 Block 体求值
   - finally 中执行 `self.env = old_env`
   - BreakSignal/ContinueSignal/ReturnSignal/RuntimeError_ 等异常路径环境正确恢复
   - 与 `_call_fn` / `_eval_for_expr` 模式一致

9. **evaluator.py — while 循环独立作用域（基于审查日志 evaluator.py:1015-1030 / 第二十二轮 P2 级 #35）**
   - 参考 `_eval_for_expr` 结构重写 `_eval_while_expr`
   - 每次迭代创建 child_env，与 for 循环统一
   - 外层 try-finally 确保环境恢复
   - ContinueSignal 从 continue 改为 pass（finally 先执行环境恢复，再由循环自然进入下一轮）

### 测试结果

- 全量测试: **802 passed** (1.1s)
- Evaluator 示例: hello/fibonacci/pattern_match/loops/pipe/math/list_comprehension 全部正常输出
- VM 示例: hello/fibonacci/pattern_match 全部正常输出
- TRY_UNWRAP 循环状态清理: 函数提前返回后 `_for_iters`/`_while_loops` 正确截断 ✅
- 顶层 ? 失败终止: main() 不再被调用 ✅
- break/continue 无循环报错: 正确抛出 RuntimeError_ ✅
- 字符串/字符 EOF 崩溃: 不再触发 IndexError ✅
- Fn[] 返回类型: `Fn[Int, Bool]` 正确解析为 `(Int) -> Bool` ✅
- ? 链式调用: `expr??`/`foo?()`/`foo?.bar` 正确解析 ✅
- 表达式深度保护: 超深嵌套抛友好错误而非 RecursionError ✅
- Block 环境恢复: break/continue/异常后环境不泄漏 ✅
- while 作用域: 与 for 循环一致，每次迭代独立作用域 ✅

---

## 2026-07-16 自动改进（第二十三轮）

基于 AUTO_REVIEW_LOG.md 第二十轮审查日志的 P1 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### compiler.py + vm.py
- **while 循环返回值与语义规范不一致（compiler.py:1040-1070）**：ast_nodes.py 明确声明 while 循环"返回体中最后一个表达式的最后一次迭代的值"，但编译器直接 POP 丢弃 body 结果，循环结束后压入 CONST_UNIT；VM 执行路径中 break 也跳转到 CONST_UNIT 后，返回值永远是 unit
  - 审查日志追问结论：不能，文档和实现不一致是最危险的 bug
  - 复现：`mut i = 0; let result = while i < 3 { i = i + 1; i }; print(result)` Evaluator 输出 3，VM 输出 ()
  - 现状：Evaluator 正确，VM/编译器错误；所有 11 个 while 测试都不检查返回值，只验证副作用

#### parser.py
- **管道操作符 |> 优先级严重错误（parser.py:672-678）**：管道优先级高于比较运算符，`a == b |> f` 被解析为 `a == (b |> f)` 而非 `(a == b) |> f`，与 Elm/F# 等函数式语言常规相反
  - 审查日志追问结论：绝对不能，优先级错误是编译器前端最严重的错误类别之一
  - 现状：_parse_pipe 被 _parse_comparison_expr 调用（管道 > 比较），正确应该是比较 > 管道
  - 参考：Elm 管道优先级 0（最低），F# 管道优先级极低（仅高于 ; let 等）

#### type_checker.py
- **管道运算符类型检查完全错误（type_checker.py:777-792）**：同时检查第一个和最后一个参数、不做类型变量绑定、类型不匹配不报错、非函数右侧不报错——四大问题导致管道类型检查形同虚设
  - 审查日志追问结论：绝对不能，管道是函数式语言的核心运算符
  - 复现1：`fn id(x) { x }; 42 |> id` 返回类型是未绑定的类型变量而非 Int
  - 复现2：`"hello" |> fn(x: Int) { x + 1 }` 不报错
  - 复现3：`42 |> 100` 不报错（右侧非函数）

### 本次修复内容（基于审查日志 Issue）

1. **compiler.py + vm.py — while 循环返回最后一次迭代值（基于审查日志 compiler.py:1040-1070 / 第二十轮 P1 级 #12）**
   - 新增 `SWAP` 操作码（Op.SWAP + VM 实现），用于交换栈顶两个元素
   - `_compile_while` 重写：循环开始前压入 CONST_UNIT 作为结果槽，每次迭代 body 后用 SWAP+POP 替换结果槽
   - VM BREAK/CONTINUE 的 while 路径：保留结果槽（base_sp 处），只清理 body 中间值
   - JUMP while 回跳检测：从依赖下一条指令是 CONST_UNIT 改为通过 _while_loops 非空判断
   - 语义：正常结束返回最后一次迭代值，零次迭代返回 UNIT，break 返回 break 前最后一次完整迭代值

2. **parser.py — 修复管道操作符优先级（基于审查日志 parser.py:672-678 / 第二十轮 P1 级 #13）**
   - 将 `_parse_pipe` 从比较运算符之下移动到相等性运算符之上
   - 优先级变化：`or → and → equality → comparison → pipe` 改为 `or → and → pipe → equality → comparison`
   - 管道优先级现在低于相等性和比较、高于逻辑与，与 Elm/F# 设计一致
   - 新增 3 个测试：低于相等性、低于比较、高于逻辑与

3. **type_checker.py — 重写管道运算符类型检查（基于审查日志 type_checker.py:777-792 / 第二十轮 P1 级 #16）**
   - 修复四大 bug：同时检查首尾参数 → 只检查第一个参数；不做类型变量绑定 → 完整绑定替换；类型不匹配不报错 → 正确报错；非函数右侧不报错 → 正确报错
   - 参考 CallExpr 实现，使用 _collect_type_bindings + _substitute_type_vars 做完整类型推断
   - 支持多参数函数部分应用：管道后返回剩余参数的柯里化函数类型
   - 新增 6 个测试：基本管道、泛型管道、类型不匹配、非函数右侧、多参数部分应用、多参数返回函数类型

### 测试结果

- 全量测试: **802 passed** (1.11s)
- Evaluator 示例: hello/fibonacci/pattern_match/loops/math/pipe/list_comprehension 全部正常输出
- VM 示例: hello/math/pattern_match 全部正常输出
- while 循环返回值（VM）: `while i < 3 { i = i + 1; i }` 返回 3 ✅
- 管道优先级: `2 + 3 |> double` 结果为 10（先加后管道） ✅
- 管道类型检查: 6 个新增测试全部通过 ✅
- 管道优先级: 3 个新增测试全部通过 ✅

---

## 2026-07-16 自动改进（第二十二轮）

基于 AUTO_REVIEW_LOG.md 第二十轮审查日志的 P1/P2 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py / compiler.py
- **STORE_VAR 函数内无法修改全局 mut 变量（vm.py:634-652）**：函数作用域中 STORE_VAR 对未定义变量直接在局部创建，不沿作用域链查找全局可变变量；与 evaluator 的 Environment.assign 语义不一致 → 添加 global_mutable 集合跟踪全局可变性，赋值模式下沿作用域链查找
  - 审查日志追问结论：绝对不能接受，两条执行路径语义不一致是致命缺陷
  - 复现：`mut x = 0; fn f() { x = x + 1 }; f(); print(x)` VM 输出 0，evaluator 输出 1

#### type_checker.py
- **match 守卫条件完全缺少类型检查（type_checker.py:1042-1050）**：`check_match_arm` 方法只检查模式和分支体，完全跳过 `arm.guard`，非 Bool 类型守卫只能在运行时才报错 → 在子环境中对守卫条件执行 Bool 类型检查
  - 审查日志追问结论：绝对不能，强类型语言的守卫条件必须是 Bool
  - 复现：`match 42 { n when 123 => "bad" }` 类型检查通过，运行时才抛 RuntimeError_

#### backend/native_backend.py
- **LIRLoadConst 不支持 closure 类型常量（native_backend.py:664-667）**：MIRClosureCreate 被降级为 LIRLoadConst(const_type="closure")，但 native_backend 只处理 int/float/bool/string，闭包场景直接抛 NotImplementedError → 添加 closure 类型处理，用 RIP-relative LEA 加载函数符号地址
  - 配套修复：lir_lowering.py 中 MIRCall 区分直接调用（函数名）和间接调用（闭包 SSA 变量），后者生成 LIRCallIndirect

### 本次修复内容（基于审查日志 Issue）

1. **vm.py + compiler.py — STORE_VAR 支持函数内修改全局 mut 变量（基于审查日志 vm.py:634-652 / 第二十轮严重问题 "函数修改全局 mut 变量不一致"）**
   - NovaVM 新增 `global_mutable: set` 集合跟踪全局可变变量名
   - STORE_VAR 新增第三个操作数 `is_assignment`，区分绑定模式（let/mut 声明）和赋值模式（`x = val`）
   - 赋值模式下：局部不存在时，先检查全局是否存在且可变 → 是则修改全局，否则报错
   - 绑定模式下：保持原有行为（顶层创建全局并维护 global_mutable，函数内创建局部）
   - compiler.py 中 Assignment 编译时传入第三个操作数 True
   - 新增 10 个测试用例覆盖各种场景

2. **type_checker.py — match 守卫条件 Bool 类型检查（基于审查日志 type_checker.py / 第二十轮 P1 级 #22 守卫条件类型检查缺失）**
   - `check_match_arm` 方法中增加守卫条件类型检查
   - 守卫在模式绑定的子环境中求值（可引用模式变量）
   - 使用 `_types_compatible` 检查 BOOL_T 兼容性
   - 错误信息："match 守卫条件必须是 Bool 类型，得到 {类型}"
   - 新增 8 个测试用例：比较运算守卫、逻辑运算守卫、模式变量引用、Int/String/Unit 错误守卫、多 arm 场景

3. **backend/native_backend.py + ir/lir_lowering.py — 闭包常量加载 + MIRCall 区分直接/间接调用（基于审查日志 native_backend.py:489 / 第二十轮严重问题 "LIRCallIndirect 抛 NotImplementedError" 延伸修复）**
   - native_backend 新增 `closure_relocations` 列表记录函数符号重定位
   - 新增 `_compile_const_closure` 方法：解析 `<closure:fn_name>`，用 LEA RIP-relative 加载函数地址
   - `_patch_code` 中添加 closure 重定位回填
   - `_collect_vreg_info` 支持 closure 类型虚拟寄存器命名
   - lir_lowering.py 中 MIRCall 判断 callee 是否为 SSA 变量：是则生成 LIRCallIndirect（src_locs[0]=函数指针），否则生成 LIRCall
   - 新增 2 个测试用例验证闭包常量编译

### 测试结果

- 全量测试: **793 passed** (1.88s)
- Evaluator 示例: hello/fibonacci/pattern_match/loops/math 全部正常输出
- VM 示例: hello/fibonacci/pattern_match 全部正常输出
- VM 全局 mut 变量修改: 函数内两次调用后 count=2 ✅
- 类型检查器守卫条件: 8 个新增测试全部通过 ✅
- Native 后端闭包常量: 2 个新增测试全部通过 ✅

---

## 2026-07-15 自动改进（第二十轮）

基于 AUTO_REVIEW_LOG.md 第十八轮审查日志的 P0 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py
- **嵌套模式匹配失败路径栈泄漏（vm.py:1159-1209）**：嵌套子模式测试失败时，栈上残留已解构的中间值；虽然 MATCH_TEST_* 失败时不 pop，但外层解构已替换栈顶，fail_cleanup 的单次 POP 不足以恢复 → 在 MATCH_START 记录 match_base_sp，失败时由 VM 统一恢复栈
  - 复现：`match [1,2,3] { [4,2,3] -> 100 | _ -> 200 }` 失败后栈泄漏 2 个值
  - 审查日志追问结论：绝对不能接受。模式匹配是函数式语言核心控制流。

#### compiler.py
- **嵌套模式匹配失败时栈不平衡（compiler.py:836-861）**：`_compile_match` 的失败清理只 emit 一个 POP，假设失败时栈上只有 dup 副本；但 PatternConstructor/PatternTuple/PatternList 的主测试成功后会展开 N 个字段/元素，子模式失败时栈上残留 N-k 个值，单个 POP 无法清理干净 → VM 端在 MATCH_START 记录 match_base_sp，失败时截断栈到 base_sp+1
  - 与 vm.py 问题配套，两端协同修复
  - 测试状态：原 772 passed（栈泄漏不影响结果正确性，现有测试未覆盖栈平衡检查）

#### type_checker.py
- **Assignment 完全不检查目标是否为可变绑定（type_checker.py:803-814）**：Assignment 分支只检查变量是否存在和类型兼容，不区分 let/mut，对不可变 let 绑定赋值不会触发类型错误
  - 根本原因：`TypeEnv`（type_checker.py:192-229）的 `define()`/`lookup()` 只存储类型，**完全没有可变性信息**，LetBinding 和 MutBinding 在类型环境中无区别
  - 对比：运行时 `Environment`（environment.py:50-61）的 `assign()` 方法正确检查了 `binding.mutable`，VM 的 STORE_VAR 也有检查，但类型检查层缺失
  - 审查日志追问结论：绝对不能。不可变性是函数式语言的核心原则。

### 本次修复内容（基于审查日志 Issue）

1. **vm.py — 嵌套模式匹配失败统一栈恢复（基于审查日志 vm.py:1159-1209 / 第十八轮严重问题 #1）**
   - Frame 类新增 `match_stack_bases` 列表保存每个 match 块的栈底指针
   - 新增 `_pattern_fail_cleanup(fail_ip)` 方法：将栈截断到 `base_sp + 1`（保留 original subject）后跳转
   - MATCH_START 记录当前栈顶（original subject 位置）到 match_stack_bases
   - 所有 MATCH_TEST_* / MATCH_CONSTRUCTOR 失败路径改为调用 `_pattern_fail_cleanup`
   - MATCH_END 弹出 match_stack_bases 栈顶
   - 同时修复 `_pattern_fail_cleanup` 的跳转偏移：从 `fail_ip + 1` 改为 `fail_ip`（VM 统一恢复栈，无需跳过编译器 POP）

2. **compiler.py — 移除模式匹配失败路径的 POP 清理指令（基于审查日志 compiler.py:836-861 / 第十八轮严重问题 #1）**
   - `_compile_match` 中移除 `fail_cleanup_pos` 的 POP 指令生成
   - `fail_ip` 直接指向下一 arm 的 `MATCH_ARM_START`，不再经过 POP 清理
   - 栈恢复完全由 VM 端的 `_pattern_fail_cleanup` 统一负责
   - 简化了编译逻辑，不再需要为每个失败点计算需要弹出的值数量

3. **type_checker.py — Assignment 可变性检查 + TypeEnv 可变性跟踪（基于审查日志 type_checker.py:796-807 / 第十八轮严重问题 #2）**
   - TypeEnv 内部存储从 `types: Dict[str, NovaType]` 改为 `_bindings: Dict[str, tuple]`，每个值为 `(type, mutable)` 元组
   - 保留 `types` 作为只读 property，向后兼容
   - `define(name, ty, mutable=False)` 增加 mutable 参数（默认 False）
   - 新增 `is_mutable(name)` 方法沿作用域链查找绑定可变性
   - LetBinding 调用 `define(..., mutable=False)`，MutBinding 调用 `define(..., mutable=True)`
   - Assignment 分支增加可变性检查，不可变则报错：`不能对不可变绑定 '<name>' 赋值`
   - 新增 11 个测试用例覆盖各种场景

### 测试结果

- 全量测试: **783 passed** (2.19s)
- Evaluator 示例: hello/functions/pattern_match/adt/loops 全部正常输出
- VM 示例: hello/functions/pattern_match 全部正常输出
- 嵌套模式匹配栈恢复: 失败后栈平衡，只保留 original subject ✅
- Assignment 可变性检查: let 绑定赋值正确报错，mut 绑定正常通过 ✅
- 模式匹配回归: 所有 47 个模式匹配测试全部通过 ✅

---

## 2026-07-15 自动改进（第十九轮）

基于 AUTO_REVIEW_LOG.md 第十六轮审查日志的 P0 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py
- **MATCH_BIND 失败分支绑定残留（vm.py:1137-1145）**：MATCH_BIND 直接写入 frame.locals，模式匹配 arm1 部分匹配后子模式失败跳转到 arm2 时，arm1 的绑定仍残留 → MATCH_START 保存快照，MATCH_ARM_START/MATCH_END 恢复快照
- **STORE_VAR 函数体内静默创建全局（vm.py:592-605）**：函数内对未定义变量执行 STORE_VAR 时 fallback 到写入 self.globals，违背静态作用域 → 函数作用域内 STORE_VAR 始终写入 frame.locals
- **内置函数超额参数未检查（vm.py:356-370）**：NovaBuiltinFn 只检查参数不足不检查过多，多余参数被 Python *args 静默忽略 → 添加 len(args) > fn.arity 检查

#### backend/native_backend.py
- **LinearScanAllocator 完整实现但从未被调用**：线性扫描寄存器分配器只在单元测试中使用，实际编译流程用的是简单的按需分配 → 集成到 _compile_function 中，活跃区间分析 + 线性扫描分配，失败时 fallback 到按需分配

#### type_checker.py
- **函数返回类型推断后不更新环境（type_checker.py:543-563）**：无 return_type 标注的函数推断出 body_type 后从未写回环境，调用处返回类型永远是 TypeVar → _check_decl_body 中推断后写回环境
- **TypeVar 函数调用 duck typing 直接放行（type_checker.py:740-750）**：callee_ty 是 TypeVar 时直接放行，不做任何检查 → 记录到 error_collector 但继续放行（温和策略，待类型推断能力增强后再严格化）

### 本次修复内容（基于审查日志 Issue）

1. **vm.py — 内置函数超额参数检查（基于审查日志 vm.py:358-363 / 第十六轮严重问题 #10）**
   - `_call_fn` 中 NovaBuiltinFn 和 NovaPartialBuiltin 两个路径都添加超额参数检查
   - 错误信息：`函数 '<name>' 期望 <arity> 个参数，得到 <实际数量> 个`
   - 同时修复 NovaPartialBuiltin 参数不足检查的 bug（用 fn.builtin.arity 而非 fn.arity）
   - 新增 2 个测试用例：内置函数超额参数、部分应用内置函数超额参数

2. **vm.py — STORE_VAR 函数作用域隔离（基于审查日志 vm.py:592-605 / 第十六轮严重问题 #2）**
   - 函数作用域内的 STORE_VAR 始终写入 frame.locals（变量不存在则创建）
   - 永远不会 fallback 到写入全局变量
   - 修复了函数中 let/mut 绑定错误地创建为全局变量的根本问题
   - 新增 2 个测试用例：函数内 let 是局部变量、函数不能隐式创建全局

3. **vm.py + compiler.py — MATCH_BIND 作用域隔离（基于审查日志 vm.py:1137-1145 / 第十六轮严重问题 #4）**
   - 编译器：每个 match arm 开头新增 MATCH_ARM_START 指令
   - Frame 类：新增 match_snapshots 列表保存局部变量名快照
   - MATCH_START：保存当前 locals key 集合到快照栈
   - MATCH_ARM_START：恢复最近快照，清理上一个 arm 残留绑定
   - MATCH_END：弹出快照，删除 match 过程中新增的所有变量
   - 新增 2 个测试用例：失败 arm 绑定不残留、match 结束后绑定清理

4. **backend/native_backend.py — LinearScanAllocator 集成到编译流程（基于审查日志 native_backend.py / 第十六轮严重问题 #12）**
   - 新增 `_collect_vreg_info()` 从指令提取虚拟寄存器使用信息
   - 新增 `_analyze_live_intervals()` 计算每个 vreg 的活跃区间
   - 新增 `_run_linear_scan_alloc()` 运行线性扫描分配，溢出则返回 None
   - `_compile_function` 中先做线性扫描分配，结果传给 `_compile_body`
   - `_alloc_vreg` 支持 preallocated 参数，优先使用预分配的寄存器
   - Fallback 机制：寄存器不足时自动回退到按需分配，编译不中断
   - 新增 17 个测试用例：活跃区间分析、线性扫描集成、寄存器复用、fallback 等

5. **type_checker.py — 函数返回类型推断写回环境（基于审查日志 type_checker.py:543-563 / 第十六轮严重问题 #5）**
   - `_check_decl_body` 的 FnDef 分支中，无 return_type 标注时用推断出的 body_type 更新环境
   - 构造新的 FnType 并通过 self.env.define() 写回
   - 新增 5 个测试用例：Int返回推断、String返回推断、调用结果类型、嵌套调用、有标注不变

6. **type_checker.py — TypeVar 函数调用诊断增强（基于审查日志 type_checker.py:740-750 / 第十六轮严重问题 #6）**
   - 保留温和策略（记录错误但继续放行），避免破坏高阶函数场景
   - 错误信息规范化，统一使用 TypeCheckError 和 error_collector
   - 新增 4 个测试用例：TypeVar调用收集错误、不崩溃、高阶函数仍工作、已知函数无错误

### 测试结果

- 全量测试: **772 passed** (1.54s)
- Evaluator 示例: hello/fibonacci/pattern_match/loops/math/pipe/list_comprehension 全部正常输出
- VM 示例: hello/fibonacci/pattern_match/loops/math/pipe/list_comprehension 全部正常输出
- 内置函数超额参数: `abs(5.0, 10.0)` 正确抛出 RuntimeError_ ✅
- STORE_VAR 作用域: 函数内变量不污染全局 ✅
- MATCH_BIND 作用域隔离: 失败 arm 绑定不残留 ✅
- LinearScan 集成: 寄存器正确复用，fallback 正常工作 ✅
- 返回类型推断: 无标注函数返回类型被正确推断并写回环境 ✅
- TypeVar 函数调用: 诊断信息正确收集 ✅

---

## 2026-07-15 自动改进（第十八轮）

基于 AUTO_REVIEW_LOG.md 第十六轮审查日志的 P0 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py
- **TRY_UNWRAP 仅检查 variant_name 不检查 type_name（vm.py:1276-1280）**：`val.variant_name in ("None", "Err")` 只匹配 variant 名称，自定义 ADT 只要 variant 叫 Some/None/Ok/Err 就会被误当作 Option/Result → 同时检查 `val.type_name in ("Option", "Result")`
- **算术运算完全不区分 bool 和 int（vm.py:608-651）**：ADD/SUB/MUL/DIV/MOD/NEG 均无 `isinstance(val, bool)` 检查，Python 中 bool 是 int 子类，True+1=2 等会静默通过 → 所有算术运算前排除 bool 操作数（对比 EQ/LT 等比较运算已有 bool 检查）
- **内置函数无超额参数检查（vm.py:358-363）**：所有 arity > 0 的内置函数可传入任意多参数，多余参数被 Python *args 静默忽略 → 添加 if fn.arity > 0 and len(args) > fn.arity 检查

#### evaluator.py
- **TryExpr `?` 运算符仅检查 variant_name 不检查 type_name（evaluator.py:718-724）**：`val.variant_name in ("None", "Err")` 等判断只看 variant，自定义 ADT 的 Some/Err 会被错误传播或解包 → 增加 `val.type_name in ("Option", "Result")` 前置检查
- **算术运算不区分 bool 和 int（evaluator.py:887-900）**：`+`/`-`/`*`/`/`/`%` 均无 bool 类型检查，与比较运算（==/!=/</> 已有 bool 检查）不一致 → 算术运算前排除 bool 操作数，抛类型错误
- **短路逻辑运算 &&/|| 不做类型检查（evaluator.py:872-882）**：直接用 if not left 判断，没有检查 left 是否为 bool 类型 → 在短路求值前添加 isinstance(left, bool) 检查

#### backend/native_backend.py
- **LIRBinOp 完全忽略 dst_loc，结果总是写入 left_reg（native_backend.py:410-485）**：整个 LIRBinOp 处理分支零引用 instr.dst_loc，二元运算结果始终写入第一个操作数寄存器（left_reg），破坏操作数原值且结果永远到不了正确的目标虚拟寄存器 → 应为 dst_loc 分配寄存器，结果写入目标寄存器
- **LIRUnaryOp 同样忽略 dst_loc（native_backend.py:487-513）**：与 LIRBinOp 相同问题，一元运算结果直接修改 operand_reg，未写入 dst_loc 指定的目标位置 → 同上
- **src_locs 操作数查找失败时静默回退到 RAX/RCX（native_backend.py:412-419）**：vregs.get(key, RAX) 在虚拟寄存器未分配时静默使用 RAX/RCX，可能导致操作数读取错误位置的值且无任何报错 → 寄存器未找到时应显式报错或正确分配

#### type_checker.py
- **PatternConstructor 不校验主题类型是否为对应 ADT（type_checker.py:1043-1076）**：构造器模式只查找构造器定义和检查字段数量，完全不检查 subject_type 是否为 ADT 以及是否为对应 ADT 类型，`match 42 { Some(x) => ... }` 不会被类型检查器捕获 → 添加 isinstance(subject_type, ADTType) 和名称匹配检查
- **for 循环/列表推导循环变量类型不推断（type_checker.py:953, 981）**：ForExpr 和 ListComprehension 的循环变量硬编码为 TypeVar("for_elem"/"lc_elem")，不从可迭代对象推断元素类型，range 循环变量也不是 Int → 列表遍历取 ListType.elem_type，range 循环设为 INT_T

### 本次修复内容（基于审查日志 Issue）

1. **vm.py + evaluator.py — TRY_UNWRAP/`?` 运算符 type_name 类型安全修复（基于审查日志 vm.py:1269-1283 / 第十六轮严重问题 #5）**
   - **vm.py TRY_UNWRAP**：先检查 `val.type_name in ("Option", "Result")`，不满足则抛 RuntimeError_
   - **evaluator.py TryExpr**：同样增加 type_name 前置检查
   - 错误信息统一：`? 操作符只能在 Option 或 Result 类型上使用，得到 <type_name>`
   - 新增 4 个测试用例：自定义ADT Some报错、自定义ADT Err报错、Option.Some回归、Result.Ok回归（Evaluator+VM 两端）

2. **vm.py + evaluator.py — 算术运算 bool/int 强类型区分（基于审查日志 vm.py:608-651 / 第十六轮严重问题 #3）**
   - **vm.py**：ADD/SUB/MUL/DIV/MOD/NEG 所有算术指令添加 `isinstance(val, bool)` 检查
   - **evaluator.py**：`+`/`-`/`*`/`/`/`%` 二元运算 + 一元 `-` 添加 bool 类型排除
   - 错误信息：`算术运算 '+' 的操作数不能是 Bool 类型`
   - 与比较运算（EQ/LT 等）已有 bool 检查形成一致的类型安全防线
   - 新增 8 个测试用例：True+1、False*5、True/2、-True 报错 + 正常 Int 运算回归（Evaluator+VM 两端）

3. **evaluator.py — 短路逻辑运算 &&/|| 类型检查（基于审查日志 evaluator.py:872-882 / 第十六轮严重问题 #2）**
   - `&&` 操作：左操作数求值后检查 `isinstance(left, bool)`，右操作数同理
   - `||` 操作：同上
   - 错误信息：`逻辑运算 '&&' 的操作数必须是 Bool 类型`
   - 与 if/while 条件的 Bool 检查保持一致
   - 新增 4 个测试用例：42&&true报错、""||false报错、true&&42报错 + 正常 Bool 运算回归

4. **backend/native_backend.py — LIRBinOp/LIRUnaryOp dst_loc 结果目标修复（基于审查日志 native_backend.py:410-485 / 第十六轮严重问题 #2）**
   - 新增 `_get_vreg()` 辅助方法，虚拟寄存器未分配时抛明确错误而非静默回退
   - **LIRBinOp**：从 `instr.dst_loc` 获取目标寄存器名，用 `_alloc_vreg` 分配，运算后 mov 到目标
   - **LIRUnaryOp**：同样修复，结果从 operand_reg 移动到 dst_reg
   - 修复 src_locs 查找：改用 `_get_vreg()`，未分配时抛 `ValueError("Native 后端：虚拟寄存器 '{name}' 未分配")`
   - 新增 11 个测试用例：BinOp dst_loc、多 vreg 连续运算、比较运算 dst_loc、UnaryOp dst_loc、vreg 未分配报错等

5. **type_checker.py — PatternConstructor 主题类型校验（基于审查日志 type_checker.py:1043-1076 / 第十六轮严重问题 #7）**
   - 在 `_check_pattern` 的 PatternConstructor 分支添加两层校验：
     - `isinstance(subject_type, ADTType)` — 主题必须是 ADT 类型
     - `subject_type.name == adt_name` — 主题 ADT 名称必须匹配
   - 错误信息：`构造器 'Some' 与类型 Int 不匹配`
   - 与 PatternInt/PatternFloat/PatternTuple 等其他 Pattern 类型的校验风格一致
   - 新增 4 个测试用例：Int匹配Some报错、String匹配Ok报错、Some正确使用通过、同一ADT不同构造器通过

6. **type_checker.py — for 循环/列表推导循环变量类型推断（基于审查日志 type_checker.py:953,981 / 第十六轮严重问题 #8）**
   - **ForExpr range 分支**：循环变量类型从 `TypeVar("for_elem")` 改为 `INT_T`
   - **ForExpr 列表分支**：从 `iter_ty` 推断元素类型——ListType 用 elem_type，TupleType 用第一个元素类型
   - **ListComprehension**：同理修复 range 分支和列表分支
   - 新增 8 个测试用例：for列表Int加法通过、for列表Int拼接报错、for range通过、列表推导同理（4个）

### 测试结果

- 全量测试: **740 passed** (1.31s)
- Evaluator 示例: hello/functions/pattern_match/adt/loops/math/pipe/list_comprehension/file_io 全部正常输出
- VM 示例: hello/functions/pattern_match/loops/math/list_comprehension/pipe 全部正常输出
- TRY_UNWRAP type_name: 自定义 ADT 的 Some/Err 被 `?` 正确拒绝 ✅
- 算术 bool 检查: `True + 1` 正确抛出 RuntimeError_ ✅
- 短路逻辑类型检查: `42 && true` 正确抛出 RuntimeError_ ✅
- Native 后端 dst_loc: BinOp/UnaryOp 结果正确写入目标寄存器 ✅
- PatternConstructor 主题校验: `match 42 { Some(x) => ... }` 被类型检查器正确捕获 ✅
- 循环变量类型推断: for/list_comprehension 正确从可迭代对象推断元素类型 ✅

---

## 2026-07-15 自动改进（第十七轮）

基于 AUTO_REVIEW_LOG.md 第十五轮审查日志的 P0 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### evaluator.py
- **负步长 range 循环计算错误（evaluator.py:946, 993）**：`range(start, end + 1, step)` 对负步长完全错误，`end + 1` 只对正步长正确 → 正负步长分支判断 + 零步长报错 **[已修复]**
- **TryExpr 对非 ADT 值静默放行（evaluator.py:718-724）**：`?` 运算符仅对 NovaADTValue 做判断，`42?`、`"hello"?` 静默通过 → 非 ADT 值和未知 variant 均抛 RuntimeError_ **[已修复]**

#### ir/pass_manager.py
- **Pass 管理器静默吞掉所有 Pass 异常（pass_manager.py:720-757）**：三个 run_*_passes 方法均捕获所有异常仅打印到 stderr，不中断执行、不向上传播，self.errors 从未被读取 → 移除 try-except，异常直接传播 **[已修复]**

#### type_checker.py
- **== 和 != 操作符完全不检查操作数类型兼容性（type_checker.py:1126-1132）**：`42 == "hello"` 不会被类型检查器捕获，两个操作数类型不同也能通过 → 使用 _types_compatible 添加类型兼容性检查 **[已修复]**

### 本次修复内容（基于审查日志 Issue）

1. **evaluator.py — 负步长 range 循环修复（基于审查日志 evaluator.py:946 / 第十五轮严重问题 #1）**
   - `_eval_for_expr` 和 `_eval_list_comprehension` 两处 `range(start, end + 1, step)` 改为正负步长分支
   - 正步长：`range(start, end + 1, step)`
   - 负步长：`range(start, end - 1, step)`
   - 零步长：抛 `RuntimeError_("range 步长不能为 0")`
   - 新增 4 个测试用例：for 负步长-1、for 负步长-2、列表推导负步长、列表推导负步长带过滤

2. **evaluator.py — TryExpr 非 ADT 值类型安全修复（基于审查日志 evaluator.py:718-724 / 第十五轮严重问题 #2）**
   - TryExpr 处理中，非 NovaADT 值抛 RuntimeError_
   - 未知 variant 的 ADT 值（非 Option/Result）也抛 RuntimeError_
   - 错误信息：`? 操作符只能在 Option 或 Result 类型上使用，得到 <类型名>`
   - 新增 4 个测试用例：整数?报错、字符串?报错、未知ADT variant（无字段）报错、未知ADT variant（带字段）报错

3. **ir/pass_manager.py — Pass 异常静默吞掉修复（基于审查日志 pass_manager.py:720-757 / 第十五轮严重问题 #1）**
   - 删除 `run_hir_passes`、`run_mir_passes`、`run_lir_passes` 三个方法中的 try-except 块
   - Pass 失败时异常直接向上传播，不再静默继续
   - 删除未使用的 `self.errors` 列表和 `import sys`
   - 新增 3 个测试用例：HIR pass 异常传播、MIR pass 异常传播、LIR pass 异常传播

4. **type_checker.py — ==/!= 操作数类型兼容性检查（基于审查日志 type_checker.py:1126-1132 / 第十五轮严重问题 #8）**
   - 在比较操作处理中，为 `==` 和 `!=` 添加 `_types_compatible(left_ty, right_ty)` 检查
   - 类型不兼容时报错：`操作符 '==' 的操作数类型不兼容：<左类型> 和 <右类型>`
   - 与 `<`/`>` 等运算符形成一致的类型检查防御
   - 新增 4 个测试用例：Int==String报错、Int!=String报错、Int==Int通过、List[Int]==List[String]报错

### 测试结果

- 全量测试: **695 passed** (1.40s)
- Evaluator 示例: hello/fibonacci/pattern_match/loops/math 全部正常输出
- VM 示例: hello/fibonacci/pattern_match 全部正常输出
- 负步长 range: `for i <- 5..0 step -1` 正确产出 [5,4,3,2,1,0] ✅
- TryExpr 类型安全: `42?` 正确抛出 RuntimeError_ ✅
- Pass 异常传播: pass 失败时异常正确向上传播 ✅
- ==/!= 类型检查: `42 == "hello"` 被类型检查器正确捕获 ✅

---

## 2026-07-15 自动改进（第十六轮）

基于 AUTO_REVIEW_LOG.md 第十四轮审查日志的 P0 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### evaluator.py
- **NovaClosure 部分应用完全失效——捕获参数从未进入作用域（evaluator.py:416-431）**：`partially_applied` 函数是死代码，返回的 NovaClosure 直接复用原始 body 和 env，已捕获参数完全不在作用域中 → 创建子环境绑定捕获参数 **[已修复]**

#### compiler.py
- **构造器模式的字段子模式从未被测试（compiler.py:836-839）**：PatternConstructor 仅发出 MATCH_CONSTRUCTOR 测试名称和字段数，完全没有递归测试字段子模式，导致 `Some(0)` 错误匹配 `Some(42)` → 递归生成字段子模式测试指令 **[已修复]**

#### vm.py
- **闭包调用缺少参数数量校验——参数过多静默丢弃（vm.py:393-397）**：传入参数多于形参时，多余参数被静默丢弃，调用方错误无法及时发现 → 添加参数数量检查，过多时抛 RuntimeError_ **[已修复]**
- **闭包缺少部分应用（柯里化）支持（vm.py:379-380）**：NovaClosure 分支直接调用 _call_closure，参数不足时不返回部分应用闭包 → 在 _call_fn 中添加部分应用逻辑，复用 NovaClosure 类存储已捕获参数 **[已修复]**
- **_call_closure 参数绑定偏移错误（vm.py:422-423）**：部分应用的闭包被调用时，新参数从 param_names[0] 开始绑定，覆盖已捕获的参数 → 根据已绑定数量计算偏移量，从剩余参数位置开始绑定 **[已修复]**

### 本次修复内容（基于审查日志 Issue）

1. **evaluator.py — NovaClosure 部分应用修复（基于审查日志 evaluator.py:416-431 / 第十四轮严重问题 #1）**
   - 删除死代码 `partially_applied` 函数
   - 创建捕获环境 `captured_env = fn.env.child()`
   - 遍历已捕获参数，通过 `captured_env.define(param.name, arg)` 绑定到子环境
   - 返回的 NovaClosure 使用扩展后的 `captured_env`
   - 后续调用时通过作用域链找到已捕获的参数
   - 新增 4 个测试用例：双参数部分应用、三参数链式、lambda 部分应用、闭包环境+部分应用组合

2. **compiler.py — 构造器模式字段子模式递归测试（基于审查日志 compiler.py:836-839 / 第十四轮严重问题 #1）**
   - `_compile_pattern_test_with_fail` 的 PatternConstructor 分支仿照 PatternTuple/PatternList 模式
   - 发射 MATCH_CONSTRUCTOR 后，遍历每个字段子模式递归调用 `_compile_pattern_test_with_fail`
   - 收集所有 fail 位置统一返回，由上层回填
   - 与 MATCH_TEST_TUPLE/MATCH_TEST_LIST 栈行为一致：匹配成功后弹出 subject 并压入 reversed 字段
   - 新增 4 个测试用例：字段不匹配、字段匹配、自定义ADT、嵌套构造器子模式

3. **vm.py — 闭包参数数量校验（基于审查日志 vm.py:395-397 / 第十四轮严重问题 #1）**
   - `_call_closure` 开头添加参数数量校验：`len(args) > closure.param_count` 时抛 RuntimeError_
   - 错误消息风格与 Evaluator 和 NovaConstructor 保持一致
   - 同时修复了参数绑定偏移问题（为部分应用做准备）
   - 新增 2 个测试用例：CALL 指令参数过多、PIPE_CALL 参数过多

4. **vm.py — 闭包部分应用/柯里化支持（基于审查日志 vm.py:379-429 / 第十四轮严重问题 #2）**
   - `_call_fn` 的 NovaClosure 分支添加参数不足检查
   - 参数不足时创建新的 NovaClosure，已提供的参数合并到 captured_vars
   - 复用 NovaClosure 类，param_count 表示剩余参数数量
   - `_call_closure` 中根据 `already_bound = total_params - closure.param_count` 计算绑定偏移量
   - 与 Evaluator 的部分应用行为保持一致
   - 新增 2 个测试用例：双参数部分应用、三参数链式部分应用

### 测试结果

- 全量测试: **680 passed** (0.76s)
- Evaluator 示例: hello/fibonacci/pattern_match/loops/math 全部正常输出
- VM 示例: hello/fibonacci/pattern_match 全部正常输出
- Evaluator 部分应用: `add(3)(7) = 10` ✅
- VM 部分应用: `add(3)(7) = 10` ✅
- 构造器字段子模式: `Some(0)` 不匹配 `Some(42)` ✅
- 参数过多校验: VM 和 Evaluator 均正确抛出 RuntimeError_ ✅

---

## 2026-07-15 自动改进（第十五轮）

基于 AUTO_REVIEW_LOG.md 第十三轮审查日志的 P0 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py
- **while 循环 BREAK 不清理栈且不弹出 _while_loops（vm.py:758-760）**：带操作数的 while BREAK 仅设置 ip，不清理循环体栈残留值，也不弹出 _while_loops 条目 → 使用 base_sp 截断栈 + 弹出循环条目 **[已修复]**
- **`_run_code` 无 try/finally 异常安全保护（vm.py:469-500）**：状态恢复代码不在 finally 块中，执行中抛异常时 VM 全局状态被破坏 → 改为 try/finally 结构 **[已修复]**
- **JUMP_IF_FALSE/JUMP_IF_TRUE/POP_JUMP_IF_FALSE 无 Bool 类型检查（vm.py:711-734）**：直接用 Python truthiness 判断条件，非 Bool 值也能通过 → 添加 `isinstance(cond, bool)` 检查 **[已修复]**
- **AND/OR/NOT 逻辑指令无 Bool 类型检查（vm.py:681-698）**：直接 `a and b` / `a or b` / `not a`，非 Bool 值也能操作 → 添加 Bool 类型检查 **[已修复]**

#### evaluator.py
- **if 条件接受非 Bool 值（evaluator.py:741-747）**：`if cond:` 直接使用 Python truthiness，任何值都可作为条件 → 添加 `isinstance(cond, bool)` 检查 **[已修复]**
- **while 条件接受非 Bool 值（evaluator.py:967-968）**：`if not cond:` 同样无类型检查 → 同上修复 **[已修复]**
- **`!` 操作符接受非 Bool 操作数（evaluator.py:928-929）**：`not operand` 对任意值生效 → 添加 Bool 类型检查 **[已修复]**

### 本次修复内容（基于审查日志 Issue）

1. **vm.py — while BREAK 栈清理 + _while_loops 弹出（基于审查日志 vm.py:751-756 / 第十三轮严重问题 #2）**
   - 带操作数的 while BREAK 分支：从 `_while_loops` 栈顶弹出循环信息
   - 使用 `base_sp` 截断栈，清理循环体产生的中间值
   - 然后跳转到 `end_pos`
   - 修复后与 CONTINUE 和 for BREAK 行为保持一致
   - 新增 4 个测试用例：基本 break、首次迭代 break、嵌套 break、break 后栈不污染

2. **vm.py — _run_code 异常安全保护（基于审查日志 vm.py:469-500 / 第十三轮严重问题 #3）**
   - 将 `_run_code` 改为 try/finally 结构
   - 状态保存（saved_code/saved_constants/saved_ip）保持在 try 之前
   - 整个 while 执行循环放入 try 块
   - 状态恢复（code/constants/ip/return_flag）全部移入 finally 块
   - 与 `_call_closure` 的 try/finally 模式保持一致

3. **evaluator.py + vm.py — if/while/逻辑操作符强类型检查（基于审查日志 evaluator.py:741-747 / 第十三轮严重问题 #1）**
   - **evaluator.py**：IfExpr 分支、_eval_while_expr、_eval_unary_op 的 `!` 操作符添加 Bool 类型检查
   - **vm.py**：JUMP_IF_FALSE/JUMP_IF_TRUE/POP_JUMP_IF_FALSE 添加条件 Bool 检查
   - **vm.py**：AND/OR/NOT 逻辑指令添加操作数 Bool 检查
   - 错误消息风格与 type_checker.py 保持一致
   - 形成多层防御：类型检查器静态检查 + 运行时动态检查

### 测试结果

- 全量测试: **668 passed** (1.44s)
- Evaluator 示例: hello/fibonacci/pattern_match/loops/math 全部正常输出
- VM 示例: hello/fibonacci/pattern_match 全部正常输出
- while BREAK: 基本/首次迭代/嵌套/栈不污染 4 个测试全部通过 ✅
- 强类型检查: `if 42 then 1 else 2` 正确抛出 RuntimeError_ ✅

---

## 2026-07-15 自动改进（第十四轮）

基于 AUTO_REVIEW_LOG.md 第十二轮审查日志的 P0 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py
- **MOD 除零保护完全缺失（vm.py:605-609）**：`a % b` 未检查除零，抛出未包装的 Python ZeroDivisionError → 添加 try/except ZeroDivisionError **[已修复]**
- **DIV 浮点除零未处理（vm.py:597-603）**：整数除零已检查，但浮点除法 `a / b` 浮点分支未检查 → 统一改为 try/except 模式 **[已修复]**
- **INDEX 异常未包装为 Nova 运行时错误（vm.py:871-875）**：`obj[index]` 的 IndexError/KeyError/TypeError 直接泄漏 → 用 try/except 包装为 RuntimeError_ **[已修复]**

#### compiler.py
- **lambda 嵌套子函数丢失（compiler.py:650-671）**：`_compile_lambda` 只提取 code/constants，未将 fn_bytecode.functions 回写到外层 → 添加子函数收集和回写循环 **[已修复]**

#### parser.py + ast_nodes.py + evaluator.py + type_checker.py + ir/hir_lowering.py
- **索引访问 `expr[index]` 未实现（parser.py:733-763）**：`_parse_postfix_expr` 缺少 LBRACKET 处理，AST 节点未定义，Evaluator 未实现 → 完整实现6层（AST/Parser/Evaluator/Compiler/HIR/TypeChecker **[已修复]**

### 本次修复内容（基于审查日志 Issue）

1. **vm.py — MOD 除零保护（基于审查日志 vm.py:605-609 / 第十二轮严重问题 #1）**
   - MOD 指令处理添加 `try/except ZeroDivisionError`，捕获后抛出 `RuntimeError_("除零错误")`
   - 同时修复 DIV 浮点除零：将整数/浮点分支统一包裹在 try/except 中，不再依赖手动 `b == 0` 检查
   - 确保 `0.0` 等浮点除零也能被正确捕获

2. **vm.py — INDEX 异常包装（基于审查日志 vm.py:871-875 / 第十二轮严重问题 #2）**
   - INDEX 指令用 try/except 包裹 `obj[index]`
   - 分别捕获 IndexError（列表/元组越界）、KeyError（字典键不存在）、TypeError（类型不支持索引）
   - 统一包装为 RuntimeError_

3. **compiler.py — lambda 嵌套子函数丢失（基于审查日志 compiler.py:650-671 / 第十二轮严重问题 #4）**
   - `_compile_lambda` 方法参照 `_compile_function` 的正确做法
   - 新增 `fn_sub_functions = dict(fn_bytecode.functions)` 收集嵌套子函数
   - 注册当前 lambda 后，遍历回写所有子函数到外层 bytecode.functions
   - 修复 `|x| |y| x + y` 等嵌套 lambda 不再丢失内层函数

4. **索引访问 `expr[index]` 完整实现（基于审查日志 parser.py:733-763 / 第十二轮严重问题 #8）**
   - **ast_nodes.py**：新增 `IndexExpr` 数据类（target, index, span）
   - **parser.py**：`_parse_postfix_expr` 新增 LBRACKET 分支，解析 `expr[index]`
   - **evaluator.py**：`eval_expr` 新增 IndexExpr 分支，支持 list/tuple/str/dict 索引
   - **compiler.py**：`_compile_expr` 新增 IndexExpr 编译，发射 Op.INDEX
   - **ir/hir_lowering.py**：新增 AST IndexExpr → HIRIndexExpr 降级
   - **type_checker.py**：新增 IndexExpr 类型检查，支持 List[T]/Map[K,V]/String 三种目标类型推导

### 测试结果

- 全量测试: **664 passed** (1.07s)
- Evaluator 示例: hello/fibonacci/pattern_match/loops/math 全部正常输出
- VM 示例: hello/fibonacci/pattern_match 全部正常输出
- 嵌套 lambda: `|x| |y| x + y` 调用 `f(10)(5) = 15 ✅
- MOD 除零: 正确抛出 RuntimeError_("除零错误") ✅
- 索引访问: 列表/字符串/字典索引及越界错误均正确 ✅

---

## 2026-07-15 自动改进（第十三轮）

基于 AUTO_REVIEW_LOG.md 第九轮/第十轮审查日志的 P0 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py
- **DUP 指令无栈空检查（vm.py:1168-1171）**：直接 `self.stack[-1]`，空栈时抛 Python IndexError → 添加空栈检查 **[已修复]**
- **MATCH_TEST_* 系列指令无栈空检查（vm.py:1006-1059）**：5 个模式匹配指令均直接访问栈顶，空栈时抛 IndexError → 添加空栈检查 **[已修复]**
- **STORE_VAR 静默创建全局变量（vm.py:560-573）**：编译器架构中所有顶层绑定首次定义均依赖 STORE_VAR 写入 globals，直接禁止会破坏 let/fn/type 声明 → 需先引入全局变量预定义机制，本轮未修

#### compiler.py
- **HALT 在 AUTO_CALL_MAIN 之前（compiler.py:253-254）**：VM 碰到 HALT 先停止，AUTO_CALL_MAIN 永远不执行 → 交换顺序 **[已修复]**

#### evaluator.py
- **NovaADTValue 缺少 __hash__（evaluator.py:59-78）**：与 VM 行为不一致，不可哈希 → 添加与 vm.py 对称的 __hash__ **[已修复]**
- **Assignment 捕获 Python RuntimeError（evaluator.py:775-782）**：environment.py 的 assign 实际抛 Nova RuntimeError_，原 except RuntimeError 永远捕获不到 → 改为 except RuntimeError_ **[已修复]**

### 本次修复内容（基于审查日志 Issue）

1. **vm.py — DUP + MATCH_TEST_* 栈空检查（基于审查日志 vm.py:1165-1168 / P0 栈管理）**
   - DUP 指令：添加 `if not self.stack: raise RuntimeError_("VM stack underflow: DUP")`
   - MATCH_TEST_INT/BOOL/STRING/FLOAT/CHAR：各添加对应空栈检查，抛出 RuntimeError_

2. **compiler.py — HALT/AUTO_CALL_MAIN 顺序修正（基于审查日志 compiler.py:253-254 / P0 #1）**
   - `compile` 方法末尾交换两行：`AUTO_CALL_MAIN` 在前，`HALT` 在后
   - 确保 VM 执行完主程序声明后能正确触发 main 函数自动调用

3. **evaluator.py — NovaADTValue __hash__（基于审查日志 evaluator.py:59-78 / P0 #10）**
   - 添加 `__hash__` 方法：`hash((self.type_name, self.variant_name, tuple(self.fields)))`
   - 与 vm.py 中 NovaADTValue.__hash__ 实现完全一致

4. **evaluator.py — Assignment 异常捕获修正（基于审查日志 evaluator.py:775-782）**
   - `except RuntimeError` 改为 `except RuntimeError_`
   - 正确捕获 environment.py assign 抛出的 Nova 运行时错误

### 测试结果

- 全量测试: **664 passed** (1.00s)
- Evaluator 示例: hello/math/pattern_match/loops/fibonacci 全部正常输出
- VM 示例: hello/math/pattern_match 全部正常输出

---

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

## 2026-07-15 自动改进（第十二轮）

基于 AUTO_REVIEW_LOG.md 第八轮审查日志的最高优先级未修复严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py
- **TRY_UNWRAP 对非ADT值静默通过（vm.py:1189-1199）**：非 Option/Result 值不解包也不报错，原值留在栈上。违反 `?` 操作符语义。→ 增加 else 分支抛 RuntimeError_

#### evaluator.py
- **_call_fn env 恢复不在 finally 中（evaluator.py:452-454）**：`self.env = old_env` 在 finally 块外，非预期异常导致环境泄漏。→ 移入 finally
- **NovaADTValue.__eq__ 未比较 type_name（evaluator.py:75-78）**：同名 variant 跨 ADT 类型错误相等。→ 增加 type_name 比较

#### compiler.py
- **match guard 失败时销毁 subject（compiler.py:717-748）**：模式测试成功后 subject 被弹出，guard 失败跳到下一个 arm 时栈上已无 subject，后续 arm 的 MATCH_TEST_* 会栈下溢。→ 每个 arm 开始前 DUP subject

#### type_checker.py
- **二元操作错误后返回具体类型（type_checker.py:1068,1074,1081,1089,1097,1111,1116）**：多处错误分支返回 INT_T/STRING_T/BOOL_T 而非 ERROR_TYPE，导致级联错误。→ 统一返回 ERROR_TYPE
- **TryExpr 对非 Result/Option 静默通过（type_checker.py:887-895）**：非 Result/Option 类型直接返回 inner_ty 不报错。→ 增加 else 分支报错
- **FnCall TypeVar callee duck typing 放行（type_checker.py:740-743）**：TypeVar callee 不约束为函数类型，高阶函数类型错误完全静默。→ 报告错误

### 本次修复内容（基于审查日志 Issue）

1. **vm.py — TRY_UNWRAP 非 ADT 值报错（基于审查日志 VM-8-3）**
   - TRY_UNWRAP 指令处理末尾增加 else 分支
   - 非 Option/Result 类型值抛出 `RuntimeError_("TRY_UNWRAP: 期望 Option 或 Result 类型，得到 {type(val).__name__}")`

2. **evaluator.py — _call_fn env 恢复移入 finally（基于审查日志 EVAL-8-3）**
   - `self.env = old_env` 从 finally 块外移入 finally 块内
   - 确保非预期异常时环境变量也能正确恢复

3. **evaluator.py + vm.py — NovaADTValue.__eq__ 增加 type_name 比较（基于审查日志 EVAL-8-5）**
   - 两处 __eq__ 方法均增加 `self.type_name == other.type_name` 条件
   - 防止不同 ADT 类型拥有同名 variant 时错误相等
   - vm.py 中 __hash__ 同步加入 type_name 保持一致性

4. **compiler.py — match guard 失败时 DUP subject 保护（基于审查日志 CMP-8-2）**
   - 每个 arm 开头 emit DUP 复制 subject
   - 模式测试失败时先 POP DUP 副本再跳到下一个 arm
   - guard 失败直接跳到下一个 arm（extract_and_bind 已消费 DUP 副本）
   - 成功路径在 body 前 POP 原始 subject

5. **type_checker.py — 二元/一元操作错误返回 ERROR_TYPE（基于审查日志 TC-8-中等问题集）**
   - 7 处错误分支统一返回 ERROR_TYPE（算术/取模/拼接/比较/逻辑/一元负/一元非）

6. **type_checker.py — TryExpr 非 Result/Option 报错（基于审查日志 TC-8-中等问题集）**
   - 非 Result/Option 类型增加 else 分支报告 `"? 操作符只能在 Option 或 Result 类型上使用"`

7. **type_checker.py — FnCall TypeVar callee 错误报告（基于审查日志 TC-8-中等问题集）**
   - TypeVar callee 通过 error_collector.add() 记录"无法对未确定类型的值进行函数调用"
   - 不抛异常不阻止编译，保持向后兼容

### 测试结果

- 全量测试: **664 passed** (0.93s)
- Evaluator 示例: hello/math/pattern_match/list_comprehension/loops 全部正常输出
- VM 示例: hello/math/pattern_match 全部正常输出

---

## 2026-07-15 自动改进（第八轮）

基于 AUTO_REVIEW_LOG.md 第五轮审查日志的最高优先级未修复严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py
- **return_flag 跨调用边界干扰（vm.py:172）**：`_call_closure` 调用 `_execute_function` 前没有重置 `return_flag`。当前安全（因为 `_execute_function` 内部优先处理 RETURN 不经过 `_execute_instruction`），但缺乏防御性编程，未来重构可能引入 bug。→ 添加防御性重置
- **`_pop(n)` 返回类型不一致（vm.py:500-507）**：n==1 返回裸值，n>1 返回列表。49 处调用点中 7 处需要手动 `if count == 1:` 补偿，增加维护负担。→ 统一返回列表

#### evaluator.py
- **Block env 不恢复（evaluator.py:738-748）**：Block 表达式处理和 `_eval_match` arm body/guard 中 BreakSignal/ContinueSignal/ReturnSignal 跳过 env 恢复，导致环境泄漏。→ 改为 try/finally
- **顶层 ? ReturnSignal 未捕获（evaluator.py:470-471）**：顶层第二遍遍历不捕获 ReturnSignal，顶层 `?` 操作符导致程序崩溃。→ 添加 try/except

#### compiler.py
- **模块导入无命名空间隔离（compiler.py:300-343）**：导入模块的导出声明直接内联编译为 STORE_VAR 进入全局变量表，同名覆盖无警告。→ 添加冲突检测 warning

### 本次修复内容（基于审查日志 Issue）

1. **vm.py — `_call_closure` 防御性 return_flag 重置（基于审查日志 vm.py:172）**
   - 在 `_call_closure` 的 `try:` 块之前添加 `self.return_flag = False`
   - 防止 return_flag 跨调用边界干扰外层执行

2. **vm.py — `_pop(n)` 统一返回列表（基于审查日志 vm.py:500-507）**
   - 删除 `if n == 1: return self.stack.pop()` 特殊分支
   - `_pop(n)` 现在始终返回列表：n==0 → []，n==1 → [value]，n>1 → [values]
   - 11 处裸值调用点改为 `self._pop()[0]` 或 `self._pop(1)[0]`
   - 删除 7 处 `if count == 1:` / `if arg_count == 1:` 补偿代码

3. **evaluator.py — Block/match env try/finally 恢复（基于审查日志 evaluator.py:738-748）**
   - Block 表达式处理改为 `try/finally` 确保 `self.env = old_env` 始终执行
   - `_eval_match` 中 guard 求值和 arm body 求值同样改为 `try/finally`
   - BreakSignal/ContinueSignal/ReturnSignal 不再导致环境泄漏

4. **evaluator.py — eval_program 捕获 ReturnSignal（基于审查日志 evaluator.py:470-471）**
   - 在 eval_program 第二遍遍历外层添加 `try/except ReturnSignal`
   - 顶层 `?` 操作符的提前返回视为程序正常结束

5. **compiler.py — 模块导入同名冲突检测（基于审查日志 compiler.py:300-343）**
   - 新增 `_get_decl_name` 辅助方法，从声明中提取名称
   - `_compile_import` 中编译每个导出声明前检查同名冲突
   - 同名时输出 `warning: import 'xxx' shadows existing binding` 到 stderr
   - 不阻止导入，仅警告，保持向后兼容

### 测试结果

- 全量测试: **655 passed** (1.45s)
- Evaluator 示例: hello/loops/fibonacci/pattern_match/list_comprehension 全部正常输出
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

---

## 2026-07-15 自动改进（第九轮）

基于 AUTO_REVIEW_LOG.md 第五轮审查日志的最高优先级未修复严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py
- **EQ/NEQ bool/int 交叉比较（vm.py:622-632）**：直接使用 Python `==`/`!=`，因 bool 是 int 子类导致 `true == 1` 错误返回 True。LT/GT/LTE/GTE 同样有此问题，且 bool 与 string 比较会泄漏 Python TypeError。**严重问题，已修复**。
- **BUILD_MAP 单元素崩溃（vm.py:833-843）**：第八轮 `_pop(n)` 统一返回列表后已修复，当前无越界问题。确认已修复。

#### evaluator.py
- **无递归深度保护（evaluator.py:401-444）**：`_call_fn` 无深度计数器，无限递归触发 Python RecursionError 裸栈崩溃。VM 有 MAX_CALL_DEPTH=1000 但 Evaluator 没有。**严重问题，已修复**。
- **EQ/NEQ bool/int 交叉比较（evaluator.py:866-869）**：与 VM 同病。**已修复**。

#### runtime/nova_runtime.c
- **HTTP 命令注入（nova_runtime.c:1644-1646, 1692-1695）**：`nova_http_get`/`nova_http_post` 使用 `system()` 执行拼接了用户 URL 的 curl 命令，URL 中的 `"` 字符可注入任意 shell 命令。**CVE 级别安全漏洞，五轮未修，已修复**。
- **Map.put 内存泄漏（nova_runtime.c:525）**：`nova_map_put` 更新已有 key 时直接覆盖 value，未释放旧 value 引用计数。**已修复**。

#### backend/native_backend.py
- **LIRReturn 缺少 epilogue（native_backend.py:460-463）**：`LIRReturn` 直接调用 `e.ret()` 发射裸 ret 指令，跳过栈帧恢复和 callee-saved 寄存器恢复，导致使用显式 return 的函数栈损坏。**严重问题，已修复**。

#### lexer.py
- **未闭合字符串/字符终止词法分析（lexer.py:252,256,265,287）**：`_read_string`/`_read_char` 遇到未闭合字面量时直接 `raise` 终止，与第七轮已修复的非法字符"跳过+收集"策略不一致。**严重问题，五轮未修，已修复**。

#### parser.py
- **`|>` 管道操作符优先级（parser.py:432-439, 672-678）**：经检查，当前 `|>` 优先级高于比较运算符，与 Elixir 设计一致。代码注释明确标注"优先级：高于比较，低于 cons"。第二轮审查已降级为中等。**确认为有意设计，非 bug**。

### 本次修复内容（基于审查日志 Issue）

1. **vm.py — EQ/NEQ/LT/GT/LTE/GTE bool/int 交叉比较修复（基于审查日志 vm.py:622-632 / Top 5th #1）**
   - EQ：当一边是 bool 另一边不是时，压入 `False`（而非让 Python `==` 把 True 当作 1）
   - NEQ：对称压入 `True`
   - LT/GT/LTE/GTE：bool 与非 bool 比较时抛出 `RuntimeError_("类型错误：Bool 不能与非 Bool 类型进行比较")`，避免 Python TypeError 泄漏
   - bool 与 bool 之间的比较仍正常工作

2. **evaluator.py — EQ/NEQ bool/int 交叉比较修复（基于审查日志 evaluator.py:866-869）**
   - `_eval_binary_op` 中 EQ/NEQ 做与 VM 对称的修改
   - 当一边是 bool 另一边不是时，EQ 返回 False，NEQ 返回 True

3. **evaluator.py — 递归深度保护（基于审查日志 evaluator.py:106 / Top 5th #6）**
   - `__init__` 新增 `self._call_depth = 0` 和 `self.MAX_CALL_DEPTH = 1000`（与 VM 一致）
   - `_call_fn` 的 NovaClosure 分支中递增 `_call_depth`，超限时抛出 `RuntimeError_("栈溢出：调用深度超过限制")`
   - `finally` 块确保深度计数器在正常返回、ReturnSignal 及异常路径下都被正确递减

4. **runtime/nova_runtime.c — HTTP 命令注入修复（基于审查日志 nova_runtime.c:1645 / Top 5th #15）**
   - `nova_http_get`：删除 `system(snprintf(...))` shell 拼接，改为 POSIX `fork()` + `execlp("curl", ...)` 直接执行（URL 作为独立 argv，不经 shell）；Windows 用 `_spawnlp`
   - `nova_http_post`：同样替换为 fork+execlp，请求体通过 `@file` 参数传递
   - `nova_system`：保留 `system()` 但添加安全注释（该函数语义即执行任意命令，非 URL 注入）

5. **runtime/nova_runtime.c — Map.put 内存泄漏修复（基于审查日志 nova_runtime.c:525 / Top 5th #17）**
   - `nova_map_put` 更新已有 key 时，覆盖前先 `nova_value_release((NovaValue*)entry->value)` 释放旧值引用计数

6. **backend/native_backend.py — LIRReturn epilogue 修复（基于审查日志 native_backend.py:460-463 / Top 5th #18）**
   - 新增 `_emit_epilogue(self, e, func)` 方法：恢复栈帧 + pop callee-saved 寄存器 + ret
   - `LIRReturn` 处理由裸 `e.ret()` 改为 `self._emit_epilogue(e, func)`
   - `_compile_function` 末尾 fall-through epilogue 复用同一方法，消除重复代码

7. **lexer.py — 未闭合字符串/字符不再终止词法分析（基于审查日志 lexer.py:252 / Top 5th #13）**
   - `_read_string` 和 `_read_char` 中四处 `raise self._make_error(...)` 改为与非法字符一致的"收集错误 + 跳过 + 继续"模式
   - 错误信息格式统一为 `词法错误：<描述> (行:{line}, 列:{col})`
   - 新增 6 个测试用例覆盖未闭合字符串/字符场景

### 测试结果

- 全量测试: **661 passed** (1.36s)
- Evaluator 示例: hello/fibonacci/pattern_match/loops/pipe 全部正常输出
- VM 示例: hello/fibonacci/pattern_match 全部正常输出
- C 语法检查: `gcc -fsyntax-only -Wall -Wextra` 零警告零错误
- C 运行时测试: `test_runtime.c` 编译运行通过

---

## 2026-07-15 自动改进（第十轮）

基于 AUTO_REVIEW_LOG.md 第六轮审查日志的最高优先级未修复严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py
- **CONCAT (`++`) 运算符语义错误（vm.py:616-620）**：`str(a) + str(b)` 强制字符串化，`[1,2] ++ [3,4]` 产生 `"[1, 2][3, 4]"` 而非列表拼接。与 Evaluator 的 `left + right` 不一致。→ 改为 `a + b` **[已修复]**
- **while 循环 BREAK 脆弱的前向扫描（vm.py:765-771）**：逐条扫描 LOOP_END/CONST_UNIT 定位跳转目标。→ 改为编译器附带操作数 **[已修复]**
- **CLOSURE 捕获整个帧（vm.py:794-803）**：`dict(locals)` 浅拷贝过度捕获。→ 需编译器做自由变量分析，本轮未修

#### compiler.py
- **BREAK/CONTINUE 不带操作数（compiler.py:487,490）**：while 循环的 break 依赖运行时前向扫描。→ 新增 `_while_end_stack` 回填机制 **[已修复]**

#### evaluator.py
- **_builtin_head/tail 缺少 field_names（evaluator.py:217-218）**：返回 Option ADT 时缺少 `field_names=["value"]`，导致字段命名访问不工作。→ 添加 field_names **[已修复]**
- **_call_fn 中 break/continue 未捕获（evaluator.py:444-451）**：BreakSignal/ContinueSignal 可逃出函数调用边界。→ 添加 except 捕获并报 RuntimeError_ **[已修复]**

#### backend/native_backend.py
- **LIRCallIndirect NotImplementedError（native_backend.py:504-505）**：间接调用代码生成未实现。→ 实现 `_compile_call_indirect` **[已修复]**

### 本次修复内容（基于审查日志 Issue）

1. **vm.py — CONCAT (`++`) 运算符语义修正（基于审查日志 vm.py:616-620 / Top 10 #3）**
   - 将 `self.stack.append(str(a) + str(b))` 改为 `self.stack.append(a + b)`
   - Python 原生 `+` 按类型分发：list+list 列表拼接、str+str 字符串拼接、int+int 数值加法
   - 与 Evaluator 的 `left + right` 行为一致，两条路径统一

2. **compiler.py — BREAK 指令附带操作数（基于审查日志 compiler.py:487 / Top 10 #2）**
   - 新增 `_while_end_stack: List[int]` 栈，跟踪 while 循环中 BREAK 的回填位置
   - `_compile_while` 在循环体编译前 push 回填列表，编译结束后用 end_pos 回填所有 BREAK 操作数
   - BREAK 编译时检查 `_while_end_stack` 非空则 emit `BREAK, end_pos` 并记录位置供回填

3. **vm.py — BREAK 优先使用操作数跳转（基于审查日志 vm.py:765-771 / Top 10 #2）**
   - BREAK 处理优先检查 `instr.operands`，有操作数时直接 `self.ip = operands[0]` 跳转
   - 无操作数时走 `_for_iters` 路径（for 循环），最后保留旧前向扫描作为 fallback
   - while 循环的 break 不再需要运行时扫描字节码

4. **evaluator.py — _builtin_head/tail 添加 field_names（基于审查日志 evaluator.py:217-218）**
   - `_builtin_head` 的 `NovaADTValue("Option", "Some", [lst[0]])` 添加 `field_names=["value"]`
   - `_builtin_head` 的 `NovaADTValue("Option", "None", [])` 添加 `field_names=["value"]`
   - `_builtin_tail` 同样添加 field_names 参数
   - 与 `_setup_builtins` 中 Option 构造方式一致

5. **evaluator.py — _call_fn 捕获 break/continue（基于审查日志 evaluator.py:444-451）**
   - NovaClosure 分支新增 `except BreakSignal: raise RuntimeError_("break 不能出现在函数体内")`
   - 新增 `except ContinueSignal: raise RuntimeError_("continue 不能出现在函数体内")`
   - 防止控制流信号逃出函数调用边界

6. **backend/native_backend.py — LIRCallIndirect 代码生成实现（基于审查日志 native_backend.py:504-505）**
   - 新增 `_compile_call_indirect` 方法，实现 x86_64 间接调用
   - 函数指针移入 R11 寄存器，参数按 System V AMD64 ABI 传递（rdi/rsi/rdx/rcx/r8/r9）
   - 浮点参数通过 XMM0-XMM7 传递，超出寄存器限制的参数压栈
   - 发射 `call *%r11`（机器码 FF D3），调用后恢复栈指针

### 测试结果

- 全量测试: **662 passed** (1.10s)
- Evaluator 示例: hello/fibonacci/loops/pattern_match/math 全部正常输出
- VM 示例: hello/fibonacci/pattern_match 全部正常输出

## 2026-07-15 自动改进（第十一轮）

基于 AUTO_REVIEW_LOG.md 第七轮审查日志的 Top 10 严重问题驱动改进。阶段一 3 个 Explore 并行检查确认问题状态，阶段二 3 个开发 Agent 并行修复，阶段三 3 个并行测试验证。

### 每日发现的问题

#### vm.py
- **while 循环 CONTINUE 首次迭代崩溃（vm.py:787-795）**：`loop_start` 在 POP_JUMP_IF_FALSE 中初始化为 None，仅由循环体末尾 JUMP 指令回填。若 CONTINUE 在首次迭代触发（JUMP 尚未执行），`self.ip = None` 导致 TypeError 崩溃。→ 借鉴 BREAK 的操作数回填机制，为 CONTINUE 添加 `_while_start_stack` **[已修复]**

#### compiler.py
- **CONTINUE 不带操作数（compiler.py:490）**：while 循环的 continue 依赖运行时 `loop_info["loop_start"]`，首次迭代时为 None。→ 新增 `_while_start_stack` 并在 CONTINUE 指令附带 loop_start 操作数 **[已修复]**

#### c_codegen.py
- **C 后端闭包环境指针硬编码为 NULL（c_codegen.py:876,897）**：`(void)_nova_closure_env;` 丢弃环境参数，`nova_closure_new(fn, NULL, 0)` 硬编码 NULL。闭包无法引用外层变量。→ 实现作用域栈 `_scope_stack` 和变量捕获分析 **[已修复]**

#### ir/hir_lowering.py
- **Range 迭代被完全丢弃（hir_lowering.py:150）**：`return HIRIdentifier("_range")` 返回不存在的标识符，start/end/step 信息全部丢失。→ 生成 `HIRCallExpr(HIRIdentifier("range"), [start, end, step])` **[已修复]**

#### parser.py
- **MapExpr 完全无法解析（parser.py:829-831）**：遇到 `{` 直接调用 `_parse_block()`，无前瞻区分 block 和 map 字面量。MapExpr AST 节点已定义但从未被创建。→ 新增 `_is_map_literal()` 前瞻和 `_parse_map_expr()` 方法 **[已修复]**

#### type_checker.py
- **MapExpr 类型检查完全缺失（type_checker.py:926-928）**：check_expr 无 MapExpr 分支，落入 else 报"未知表达式类型"。→ 新增 MapExpr 类型检查分支，返回 `MapType(key_type, value_type)` **[已修复]**

### 本次修复内容（基于审查日志 Issue）

1. **vm.py + compiler.py — while CONTINUE 首次迭代崩溃修复（基于审查日志 VM-7-1 / Top 10 #3）**
   - compiler.py: 新增 `self._while_start_stack: List[int] = []`
   - compiler.py: `_compile_while` 中编译循环体前 push loop_start，编译完后 pop
   - compiler.py: `ContinueExpr` 处理：while 循环中 emit `CONTINUE, loop_start`；for 循环中保持无操作数
   - vm.py: CONTINUE 处理优先使用 `instr.operands[0]` 作为 loop_start，无操作数时回退到 `loop_info["loop_start"]`
   - 新增测试: `test_vm_while_continue` 和 `test_vm_while_continue_first_iteration`

2. **c_codegen.py — C 后端闭包变量捕获实现（基于审查日志 CCGEN-7-1 / Top 10 #4）**
   - 新增作用域栈 `_scope_stack`，记录每层作用域中 `{nova_name: c_type}`
   - 新增 `_push_scope`/`_pop_scope`/`_add_var`/`_collect_captured`/`_box_to_voidptr`/`_unbox_from_voidptr` 辅助方法
   - `_collect_captured` 采用 VM 的 `dict(locals)` 方式收集所有可见变量（排除 lambda 自身参数，内层遮蔽外层）
   - `_compile_lambda_to_stmt` 重写：有捕获时通过 `((void**)_nova_closure_env)[i]` 拆箱声明局部变量；创建闭包时构造 `void* cap[N]` 数组传入 `nova_closure_new(fn, cap, count)`

3. **ir/hir_lowering.py — HIR Range 迭代修复（基于审查日志 HIR-7-1 / Top 10 #7）**
   - `_lower_iterable` 中 range 分支不再返回 `HIRIdentifier("_range")`
   - 改为降级 start/end/step 后生成 `HIRCallExpr(HIRIdentifier("range"), [start, end, step])`
   - 无步长时默认 `HIRIntLiteral(1)`

4. **parser.py — MapExpr 解析实现（基于审查日志 PARSER-7-1 / Top 10 #9）**
   - 新增 `_is_map_literal()` 前瞻判断：`{}` 为空 map；匹配的 `{...}` 内部顶层出现 `=>` (FAT_ARROW) 则为 map
   - 深度跟踪确保嵌套结构中内层 map 的 `=>` 不让外层被误判
   - 新增 `_parse_map_expr()`：解析 `{ key => value, key => value, ... }`，返回 `MapExpr(pairs=[(key, value), ...])`

5. **type_checker.py — MapExpr 类型检查实现（基于审查日志 TC-7-4）**
   - 在 `check_expr` 中 `TupleExpr` 分支后新增 `MapExpr` 分支
   - 空 map 返回 `MapType(TypeVar, TypeVar)`
   - 非空时检查所有 key/value 类型一致性，返回 `MapType(first_key, first_val)`

### 测试结果

- 全量测试: **664 passed** (0.94s)
- Evaluator 示例: hello/fibonacci/pattern_match/list_comprehension/loops 全部正常输出
- VM 示例: hello/fibonacci/pattern_match 全部正常输出

---

## 2026-07-15 自动改进（第十二轮）

基于 AUTO_REVIEW_LOG.md 第八轮审查日志的 P0 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py
- **CONCAT（++）语义错误（vm.py:616-621）**：`a + b` 允许 int/float/bool/list 参与 ++，与类型检查器语义不一致。→ 限制为仅 str 类型可拼接 **[已修复]**

#### compiler.py
- **无 else 的 if 表达式栈泄漏（compiler.py:693-703）**：then_branch 后缺少 JUMP 跳过 CONST_UNIT，导致 true 路径栈上同时留下 then 值和 Unit。→ 插入 JUMP 跳过 CONST_UNIT **[已修复]**

#### evaluator.py
- **_call_fn 环境恢复不在 finally（evaluator.py:433-455）**：非 Return/Break/Continue 异常后 env 不恢复。→ 移入 finally **[已修复]**
- **match guard/body 环境恢复不在 finally（evaluator.py:989-1006）**：guard 或 body 异常后 env 不恢复。→ 改为 try/finally **[已修复]**

### 本次修复内容（基于审查日志 Issue）

1. **vm.py + evaluator.py — CONCAT 运行时类型守卫（基于审查日志 vm.py:616-621 / P0 #5）**
   - vm.py: CONCAT 指令处理增加 `isinstance(a, str) and isinstance(b, str)` 检查，非字符串抛 RuntimeError_
   - evaluator.py: `++` 二元操作同样增加类型检查
   - 消除 int/float/bool 误用 ++ 的歧义，与类型检查器语义一致

2. **compiler.py — 无 else if 表达式 JUMP 跳过 CONST_UNIT（基于审查日志 compiler.py:693-703 / P0 #3）**
   - `_compile_if` 无 else 分支时，在 then_branch 后 emit `JUMP` 跳过 `CONST_UNIT`
   - 修复前：`if true then 1` 执行后栈上同时有 `1` 和 `Unit`
   - 修复后：true 路径直接跳转到 CONST_UNIT 之后，栈上只保留 then 的值

3. **evaluator.py — _call_fn + match 环境恢复 try/finally（基于审查日志 evaluator.py:433-455,989-1006 / P0 #5）**
   - `_call_fn` 将 `self.env = old_env` 从 finally 外部移入 finally 内部
   - `_eval_match` guard 处理用 try/finally 包裹 `eval_expr(arm.guard)`
   - `_eval_match` body 处理用 try/finally 包裹 `eval_expr(arm.body)`
   - 消除异常导致的环境泄漏风险

### 测试结果

- 全量测试: **664 passed** (1.04s)
- Evaluator 示例: hello/fibonacci/pattern_match/math/loops 全部正常输出
- VM 示例: hello/fibonacci/pattern_match 全部正常输出

---

## 2026-07-15 自动改进（第十三轮）

基于 AUTO_REVIEW_LOG.md 第十一轮审查日志的严重/中等问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### vm.py
- **MATCH_TEST_TUPLE 无栈空检查（vm.py:1112）**：直接 `self.stack[-1]`，空栈时抛 Python IndexError → 添加空栈检查 **[已修复]**
- **MATCH_TEST_LIST 无栈空检查（vm.py:1126）**：同上 → 添加空栈检查 **[已修复]**
- **TRY_UNWRAP 无栈空检查（vm.py:1208）**：同上 → 添加空栈检查 **[已修复]**

#### compiler.py
- **嵌套模式匹配不生成子模式测试（compiler.py:869-878）**：`match x { (1, "hello") -> ... }` 只检查元组长度，不测试内部值 → 递归生成子模式测试指令 **[已修复]**

#### evaluator.py
- **比较运算 bool 类型安全缺失（evaluator.py:893-900）**：`<`/`>`/`<=`/`>=` 未隔离 bool 与 int，导致 `True < 2` 可通过 → 添加 bool 混用检查 **[已修复]**

### 本次修复内容（基于审查日志 Issue）

1. **vm.py — MATCH_TEST_TUPLE/MATCH_TEST_LIST/TRY_UNWRAP 栈空检查（基于审查日志 vm.py:1112/1126/1208）**
   - MATCH_TEST_TUPLE: 添加 `if not self.stack: raise RuntimeError_("VM stack underflow: MATCH_TEST_TUPLE")`
   - MATCH_TEST_LIST: 同上，消息为 `MATCH_TEST_LIST`
   - TRY_UNWRAP: 同上，消息为 `TRY_UNWRAP`
   - 风格与 DUP、MATCH_TEST_INT 等已修复指令完全一致

2. **compiler.py — 嵌套模式匹配子模式测试生成（基于审查日志 compiler.py:869-878 / 第十一轮严重问题）**
   - `_compile_pattern_test_with_fail` 返回类型由 `Optional[int]` 改为 `List[int]`
   - PatternTuple/PatternList 分支：发射主测试指令后，遍历每个子模式递归调用 `_compile_pattern_test_with_fail`，收集所有 fail 位置统一返回
   - `_compile_match` 回填逻辑改为遍历列表，统一回填到 `fail_cleanup_pos`
   - 单变量绑定模式（如 `(a, b)`）语义不变（PatternIdentifier 返回空列表，不额外生成测试）

3. **evaluator.py — 比较运算 bool 类型隔离（基于审查日志 evaluator.py:893-900）**
   - `<`/`>`/`<=`/`>=` 合并为统一分支，添加 `isinstance(left, bool) != isinstance(right, bool)` 检查
   - bool 与非 bool 混用时抛出 `RuntimeError_("类型错误：Bool 类型只能与 Bool 类型进行比较")`
   - 与 `==`/`!=` 及 VM 第九轮修复行为一致

### 测试结果

- 全量测试: **664 passed** (0.90s–1.16s)
- Evaluator 示例: hello/math/pattern_match/list_comprehension/loops 全部正常输出
- VM 示例: hello/fibonacci/pattern_match 全部正常输出

---

## 2026-07-16 自动改进（第二十一轮）

基于 AUTO_REVIEW_LOG.md 第十九轮审查日志的 P0 级严重问题驱动改进（阶段一检查 + 阶段二开发 + 阶段三测试）。

### 每日发现的问题

#### compiler.py + vm.py
- **嵌套循环 break/continue 跨类型嵌套目标错误（compiler.py:491-507, vm.py:858-915）**：当 while 包含 for 时，内层 for 的 break/continue 被错误地作用于外层 while
  - 编译器根因：只用 `_while_end_stack` 跟踪 while 循环，for 循环无栈跟踪，BreakExpr 只检查 while 栈是否非空
  - VM 根因：BREAK 优先检查操作数（while 路径），CONTINUE 优先检查 `_for_iters`（for 路径），判断方向不一致
  - 复现：`mut i = 1 while i <= 3 { for x in [10,20,30] { if x == 20 then break } i = i + 1 }` → while 只执行 1 次
  - 审查日志追问结论：绝对不能。控制流基本语义错误是 P0 级 bug。

#### evaluator.py
- **BuiltinFn 超额参数未校验（evaluator.py:408-414）**：`_call_fn` 的 BuiltinFn 分支只检查参数不足的部分应用，未检查参数超额，多余参数被静默吞掉（如 `abs(1,2)` 返回 1.0）→ 添加超额参数检查，抛 RuntimeError_
- **守卫条件缺少 Bool 类型检查（evaluator.py:1066）**：guard 求值结果直接用于 `if not guard_val`，无 `isinstance(..., bool)` 校验，非 Bool 值可当 guard 使用 → 添加 Bool 类型检查
- **列表推导过滤条件缺少 Bool 类型检查（evaluator.py:1041）**：`filter_cond` 求值结果直接用于 `if not ...`，无 Bool 类型校验 → 添加 Bool 类型检查
- **MapExpr 中非可哈希键导致 Python TypeError 泄露（evaluator.py:799-800）**：字典推导式中 key 为非可哈希值时抛出原生 Python TypeError，泄露到底层异常 → 捕获 TypeError 并转为 RuntimeError_

#### backend/native_backend.py
- **预分配寄存器未从 free 列表移除（native_backend.py:202-218）**：`_alloc_vreg` 使用 preallocated 时不从 free_gprs/free_xmms 中移除，后续按需分配可能复用同一物理寄存器，造成数据覆盖 → 使用预分配后从对应 free 列表移除
- **LIRReturn 不处理返回值寄存器（native_backend.py:812-816）**：完全忽略 instr.src_locs，假设返回值已在 RAX/XMM0，当返回值在其他寄存器时返回错误值 → 从 src_locs 获取返回值并移动到 RAX/XMM0
- **LIRBinOp 浮点操作完全缺失（native_backend.py:661-758）**：所有二元运算都使用整数指令（add/sub/cmp），浮点操作数会产生错误机器码 → 浮点操作使用 SSE2 指令（addsd/subsd/mulsd/divsd/ucomisd）

### 本次修复内容（基于审查日志 Issue）

1. **compiler.py + vm.py — 嵌套循环 break/continue 统一循环栈修复（基于审查日志第十九轮 vm.py:717-728 / compiler.py:491-507 严重问题 #1）**
   - **编译器端**：新增 `_loop_stack` 统一循环栈，每个元素为 `{type, break_patches, continue_target}`
     - `_compile_while`：push while 类型栈帧，替换原有双栈机制
     - `_compile_for`：新增 push for 类型栈帧，退出时 pop
     - BreakExpr/ContinueExpr：通过 `_loop_stack[-1]["type"]` 判断最内层循环类型
   - **VM 端**：BREAK 和 CONTINUE 统一判断逻辑——优先检查操作数是否存在
     - 有操作数 → while 循环（操作数即跳转目标）
     - 无操作数 → for 循环（通过 `_for_iters` 栈处理）
   - 支持 while↔for 任意嵌套组合，break/continue 始终作用于最内层循环

2. **evaluator.py — 4个类型安全严重问题修复（基于审查日志第十九轮 evaluator.py 严重问题）**
   - **BuiltinFn 超额参数检查**：`_call_fn` 的 BuiltinFn 分支添加 `fn.arity > 0 and len(args) > fn.arity` 检查，与 VM 端错误信息格式一致
   - **守卫条件 Bool 检查**：`_eval_match` 中 guard 求值后添加 `isinstance(guard_val, bool)` 检查
   - **列表推导过滤条件 Bool 检查**：ListComprehension 过滤条件求值后添加 Bool 检查
   - **MapExpr 非可哈希键错误处理**：字典推导式用 try/except 包裹，捕获 TypeError 并定位第一个不可哈希键后转为 RuntimeError_

3. **backend/native_backend.py + backend/x86_64.py — Native后端3个严重问题修复（基于审查日志第十九轮 native_backend.py 严重问题）**
   - **寄存器分配冲突修复**：`_alloc_vreg` 使用预分配寄存器后，从 `free_gprs` 或 `free_xmms` 中移除该寄存器，防止同物理寄存器被分配给多个 vreg
   - **LIRReturn 返回值寄存器处理**：从 `src_locs` 获取返回值位置，整数移到 RAX，浮点移到 XMM0
   - **LIRBinOp 浮点操作支持**：新增 `is_float_op` 判断，浮点算术使用 SSE2 addsd/subsd/mulsd/divsd，浮点比较使用 ucomisd + setcc
   - **x86_64.py**：新增 setb、seta、setbe、setae 四条 setcc 指令，用于浮点比较

### 测试结果

- 全量测试: **783 passed** (1.79s)
- Evaluator 示例: hello/fibonacci/pattern_match/loops/pipe 全部正常输出
- VM 示例: hello/fibonacci/pattern_match 全部正常输出
- 嵌套循环 break/continue: while↔for 跨类型嵌套全部正确 ✅
- evaluator 类型安全: 4个修复点全部正确报错 ✅
- native 后端: 116 passed，寄存器分配/返回值/浮点运算全部正常 ✅
