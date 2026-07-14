# Nova 编程语言

[![CI](https://github.com/zhangzhangyitian966-create/nova-lang/actions/workflows/ci.yml/badge.svg)](https://github.com/zhangzhangyitian966-create/nova-lang/actions)

Nova 是一门表达式导向、强静态类型、函数式核心的通用编程语言。

## 特性

- **表达式导向** — if、match、for、while 全部返回值，一切皆表达式
- **强静态类型** — Hindley-Milner 类型推断，编译时捕获错误
- **函数式核心** — 闭包、高阶函数、模式匹配、管道操作符
- **安全** — 无空值（Option/Result 替代 null）、不可变优先
- **多后端编译** — Python 解释器、字节码 VM、C 原生编译、x86_64 原生、WasmGC
- **现代化错误报告** — Rust 风格多行高亮、ANSI 颜色、批量错误收集
- **完善的类型系统** — 泛型 ADT、类型参数检查、类型别名递归展开

## 安装

```bash
pip install nova-lang
```

或从源码安装：

```bash
git clone https://github.com/zhangzhangyitian966-create/nova-lang.git
cd nova-lang
pip install -e ".[all]"
```

## 快速开始

### REPL 交互模式

```bash
nova
```

```
Nova 编程语言 v0.4.0
输入表达式或声明，按 Enter 求值
:help 查看帮助，:quit 退出

nova> let x = 42
nova> x
=> 42 : Int
nova> let greet = |name: String| -> String { "Hello, " ++ name ++ "!" }
nova> greet("Nova")
=> "Hello, Nova!" : String
nova> for i <- 1..6 { i * i }
=> [1, 4, 9, 16, 25, 36] : List[Int]
nova> :quit
```

### 运行程序

```bash
# 使用字节码 VM（默认）
nova run examples/hello.nova

# 使用 C 后端编译为原生二进制
nova build examples/hello.nova

# 编译并运行
nova run --native examples/fibonacci.nova

# 仅类型检查
nova check examples/loops.nova
```

### 语法示例

#### Hello World
```nova
fn main() -> Unit {
  print("Hello, Nova!")
}
```

#### 函数定义
```nova
fn fibonacci(n: Int) -> Int {
  if n <= 1 then n
  else fibonacci(n - 1) + fibonacci(n - 2)
}

fn main() -> Unit {
  print(int_to_str(fibonacci(10)))
}
```

#### 模式匹配
```nova
type Shape {
  Circle(r: Float)
  Rect(w: Float, h: Float)
}

fn area(s: Shape) -> Float {
  match s {
    Circle(r)  -> 3.14159 * r * r
    Rect(w, h) -> w * h
  }
}

fn main() -> Unit {
  let c = Circle(5.0)
  print(float_to_str(area(c)))
}
```

#### 管道操作
```nova
fn main() -> Unit {
  let result = [1, 2, 3, 4, 5]
    |> filter(|x| x > 2)
    |> map(|x| x * x)
    |> sum
  print(int_to_str(result))
}
```

#### 列表推导式
```nova
fn main() -> Unit {
  let squares = [x * x for x <- 1..11]
  let evens = [x for x <- 1..21 if x % 2 == 0]
}
```

#### 代数数据类型（ADT）
```nova
type Option[T] {
  Some(value: T)
  None
}

type Result[T, E] {
  Ok(value: T)
  Err(error: E)
}

fn safe_divide(a: Int, b: Int) -> Result[Int, String] {
  if b == 0 then Err("division by zero")
  else Ok(a / b)
}
```

## 类型系统

| 类型 | 说明 | 示例 |
|------|------|------|
| `Int` | 64位整数 | `42` |
| `Float` | 64位浮点 | `3.14` |
| `String` | UTF-8 字符串 | `"hello"` |
| `Bool` | 布尔值 | `true`, `false` |
| `List[T]` | 列表 | `[1, 2, 3]` |
| `Map[K, V]` | 哈希表 | `{"a": 1}` |
| `Tuple(T1, T2)` | 元组 | `(1, "a")` |
| `(A) -> B` | 函数类型 | `|x: Int| x * 2` |
| `Option[T]` | 可选值 | `Some(42)`, `None` |
| `Result[T, E]` | 错误处理 | `Ok(value)`, `Err(msg)` |

## 内置函数

### I/O
- `print(value)` — 输出值
- `read_line()` — 读取一行
- `read_file(path)` — 读取文件
- `write_file(path, content)` — 写入文件
- `file_exists(path)` — 检查文件存在

### 字符串
- `int_to_str(i)` — 整数转字符串
- `float_to_str(f)` — 浮点转字符串
- `str_to_int(s)` — 字符串转整数
- `str_len(s)` — 字符串长度
- `string_split(s, sep)` — 字符串分割

### 数学
- `sqrt(x)`, `sin(x)`, `cos(x)`, `tan(x)`
- `pow(base, exp)`, `log(x)`, `log10(x)`, `exp(x)`
- `floor(x)`, `ceil(x)`, `round(x)`
- `abs(x)`, `min(a, b)`, `max(a, b)`, `pi()`

### 列表
- `filter(pred, list)` — 过滤
- `map(fn, list)` — 映射
- `sum(list)` — 求和
- `head(list)` — 首个元素（Option）
- `tail(list)` — 剩余元素（Option）
- `list_length(list)` — 长度

### JSON
- `json_parse(text)` — 解析 JSON
- `json_stringify(value)` — 序列化为 JSON

## 编译目标

| 命令 | 目标 | 说明 |
|------|------|------|
| `nova run file.nova` | 字节码 VM | 默认，快速迭代 |
| `nova run --eval file.nova` | Python 解释器 | 调试 |
| `nova build file.nova` | C 编译 | 原生二进制（需要 gcc/clang） |
| `nova run --native file.nova` | 自研 x86_64 | 零依赖原生编译 |
| `nova compile-wasm file.nova` | WasmGC | WebAssembly（浏览器） |
| `nova emit-c file.nova` | C 代码输出 | 查看生成的 C 代码 |
| `nova emit-ir file.nova` | IR 输出 | 查看中间表示 |

## REPL 命令

| 命令 | 说明 |
|------|------|
| `:help` | 显示帮助 |
| `:type expr` | 显示表达式的推断类型 |
| `:env` | 显示当前环境中的绑定 |
| `:ast expr` | 显示 AST 结构 |
| `:clear` | 清除当前环境 |
| `:quit` / `:q` | 退出 |

## 项目统计

| 指标 | 数值 |
|------|------|
| 测试用例 | **471 个**，全部通过 |
| 代码行数 | 20,000+ |
| 支持后端 | 5 个（解释器 / VM / C / x86_64 / WasmGC）|
| CI 覆盖 | Python 3.10-3.13 |

## 项目结构

```
nova/
├── _cli.py           # 主入口
├── __main__.py       # python -m nova 入口
├── pyproject.toml    # 包配置
├── lexer.py          # 词法分析器
├── parser.py         # 语法分析器
├── ast_nodes.py      # AST 节点
├── type_checker.py   # 类型检查器（泛型 ADT、类型推断）
├── evaluator.py      # Python 解释器
├── compiler.py       # 字节码编译器
├── vm.py             # 栈式虚拟机
├── c_codegen.py      # C 代码生成器
├── environment.py    # 环境管理
├── errors.py         # 错误类型（多行高亮、ANSI颜色、批量收集）
├── ir/               # 三层中间表示（HIR/MIR/LIR）
│   ├── ir_nodes.py
│   ├── hir_lowering.py
│   ├── mir_lowering.py
│   ├── lir_lowering.py
│   └── pass_manager.py
├── backend/          # 后端代码生成
│   ├── x86_64.py     # x86_64 指令编码器
│   ├── native_backend.py  # 自研原生后端（SSE2/System V ABI）
│   ├── cranelift_backend.py
│   ├── wasm_backend.py
│   └── compiler_pipeline.py
├── runtime/          # C 运行时库
│   ├── nova_runtime.h
│   ├── nova_runtime.c
│   └── std_impl/     # 标准库模块
├── tree-sitter-nova/ # Tree-sitter 语法
├── examples/         # 示例程序
└── tests/            # 测试（471 个）
```

## 发展路线图

### v0.4.0（当前）— 已完成
- [x] 原生后端：浮点常量、字符串常量、参数传递（System V ABI）、分支指令
- [x] 类型系统：泛型 ADT、类型参数数量检查、类型别名递归展开
- [x] 错误处理：SourceSpan 多行高亮、ANSI 颜色、ErrorCollector 批量收集
- [x] 471 个测试覆盖核心功能

### v0.5.0（短期）
- [ ] 完善原生后端：循环、闭包捕获、模式匹配代码生成
- [ ] 优化器：常量折叠、死代码消除、内联等 LIR Pass
- [ ] 标准库扩展：并发原语、网络 I/O
- [ ] 模块系统：import/export 支持

### v0.6.0（中期）
- [ ] JIT 编译：基于 Cranelift 的运行时编译
- [ ] 垃圾回收：增量标记-清除或引用计数
- [ ] 调试支持：栈回溯、断点、单步执行
- [ ] 包管理器：依赖解析、版本管理

### v1.0.0（长期）
- [ ] 生产级性能：与主流语言竞争
- [ ] IDE 支持：LSP 语言服务器、自动补全、跳转定义
- [ ] 完整文档：语言规范、标准库 API、教程
- [ ] 生态系统：包仓库、CI/CD 集成

## 许可证

MIT License
