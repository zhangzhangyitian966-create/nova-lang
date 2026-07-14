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

（记录每天发现的新 bug 和改进建议）

## 改进历史

（记录每天的改进内容、修改的文件、测试结果）

