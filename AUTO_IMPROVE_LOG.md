# Nova 语言自动完善日志

## 项目状态

| 指标 | 当前值 |
|------|--------|
| 版本 | v0.5.0 |
| 测试数 | 655 |
| 最后更新 | 2026-07-14 |

## 已完成的改进

### 2026-07-14（初始）
- CI 修复：Python 模块路径、C runtime 测试目标
- 包结构修复：nova.py 重命名为 _cli.py，统一 nova.* 导入
- 工具升级：setuptools 83.0、pytest 8.0、actions/checkout@v5、Node.js 24
- MIRInstruction/LIRInstr 添加 @dataclass 装饰器
- v0.4.0：原生后端（浮点/字符串/参数传递/分支）、类型系统（泛型 ADT）、错误处理（SourceSpan/ANSI/批量收集）
- 诊断报告 12 个 Bug 修复（P0 #1-5、P1 #7-9、P2 #11/13/14）
- v0.5.0：原生后端完善（比较/一元/ADT/List/全局变量）、优化器 Pass（常量折叠/DCE/CSE/LICM）、模块系统
- VM 栈布局文档、编译器空循环修复、VM 集成测试补全、C 代码生成器重构

## 待改进项（优先级排序）

### P0 - 必须修复
- [ ] C 代码生成器：复杂嵌套表达式仍有边界问题
- [ ] native_backend：LIRCallIndirect、LIRIndex、LIRFieldAccess 未实现
- [ ] Cranelift/Wasm 后端仅生成文本，不可执行

### P1 - 重要功能
- [ ] 标准库扩充：字符串处理（split/join/trim/replace）、更多数学函数
- [ ] REPL 增强：自动补全、历史记录、多行编辑
- [ ] examples/ 示例程序：每个特性至少一个可运行的示例
- [ ] VM 性能优化：跳转表、内联缓存、JIT 热点检测

### P2 - 改进体验
- [ ] 错误恢复：类型检查器收集模式下继续检查后续声明
- [ ] 更好的 REPL 错误提示
- [ ] 代码文档：为每个模块添加 docstring
- [ ] 配置文件支持：nova.toml 项目配置

### P3 - 长期目标
- [ ] 自举：用 Nova 写 Nova 编译器
- [ ]脱离 Python 运行时
- [ ] LSP 语言服务器
- [ ] 包管理器
- [ ] 调试器（断点、单步、变量查看）

## 每日发现的问题

### 2026-07-14（Agent 1 检查）
1. **vm.py:724** — `while` 循环中 `continue` 被静默忽略（`pass`）。
   - Compiler 正确生成 `Op.CONTINUE`，但 VM 的 `while` 分支为空操作。
   - 当前测试未覆盖 `while + continue`，655 个测试全部通过无法发现此问题。
   - **优先级：P0**

2. **vm.py:1059** — `TRY_UNWRAP` 指令未实现错误传播。
   - 仅 `peek` 栈顶值判断是否 `None`/`Err`，随后 `pass`，无任何实际动作。
   - `try?` 表达式在 VM 路径下既不 unwrap 也不提前返回。
   - 测试集中无 `try?` 相关用例。
   - **优先级：P1**

### 2026-07-14（Agent 2 检查）
- **native_backend.py**
  - `FLOAT_NEG`（行 447）为空壳 `pass`，浮点取反未实际发射机器码。
  - `LIRCallIndirect`、`LIRIndex`、`LIRFieldAccess`（行 493/497/501）仍抛出 `NotImplementedError`。
  - `SimpleNativeCompiler.compile_source` 与 `_build_simple_lir`（行 908/1006）未实现 AST->LIR lowering。
- **pass_manager.py**
  - `run_hir_passes` / `run_mir_passes` / `run_lir_passes`（行 721/735/749）使用 `except Exception: pass` 静默吞掉所有 Pass 异常，需改为日志记录或诊断收集。
  - MIR 层 LICM（行 640）对 `false_target` 回边识别为空壳 `pass`，仅处理 `true_target`。
- **测试**：`tests/test_native_backend.py` + `tests/test_ir.py` 共 177 项全部通过。

### 2026-07-14（Agent 3 检查）
- **type_checker.py:1020-1084** — `_check_pattern` 方法缺失 `PatternFloat` 和 `PatternChar` 处理。
  - `PatternFloat` 已局部导入但无对应 `elif` 分支；`PatternChar` 未导入且无处理分支。
  - 当匹配表达式使用浮点/字符字面量模式时，类型检查器会静默漏过，不进行检查也不绑定变量。
  - evaluator.py 的 `_match_pattern` 已完整处理这两种模式，说明 AST 节点本身支持。
  - 测试 39/39 通过，但未覆盖这两种模式匹配场景。
  - **优先级：P0**

## 改进历史

### 2026-07-14（自动改进批次）
- **vm.py** — 实现 TRY_UNWRAP 指令：Some/Ok 时 unwrap 内部值，None/Err 时触发提前返回（修改 _execute_instruction 返回 bool）
- **backend/native_backend.py** — 实现 FLOAT_NEG 浮点取反机器码发射（xorpd + subsd 方案）
- **type_checker.py** — 补全 _check_pattern 对 PatternFloat 和 PatternChar 的类型检查
- **单元测试**：655 passed（tests/）、177 passed（backend/ir/）、39 passed（type_system/），无失败
- **示例测试**：Evaluator 路径 5 个示例、VM 路径 3 个示例全部正常运行
