#!/usr/bin/env python3
"""
Nova 编程语言 - 主入口

支持两种运行模式：
1. 运行源文件：python nova.py file.nova
2. 交互式 REPL：python nova.py （不带参数）
3. 表达式求值：python nova.py -e "表达式"

命令行参数：
- nova.py file.nova           使用 VM 执行（默认）
- nova.py --vm file.nova      使用 VM 执行
- nova.py --eval file.nova    使用树遍历解释器
- nova.py --check file.nova   仅类型检查
- nova.py --dump-bytecode file.nova  编译并打印字节码
"""

import sys

from .parser import Parser

from .errors import NovaError
from .evaluator import Evaluator
from .lexer import Lexer
from .type_checker import TypeChecker

# CLI 运行中可能遇到的非预期异常类型（最后防线范围）
# 明确排除 SystemExit / KeyboardInterrupt 等应由上层处理的异常
_CLI_UNEXPECTED_ERRORS = (
    TypeError,
    AttributeError,
    KeyError,
    ValueError,
    IndexError,
    NameError,
    RuntimeError,
    ZeroDivisionError,
)


def run_source(
    source: str,
    check_types: bool = True,
    capture_output: bool = False,
    use_vm: bool = True,
):
    """
    运行 Nova 源代码

    Args:
        source: Nova 源代码字符串
        check_types: 是否进行类型检查
        capture_output: 是否捕获 print 输出（用于测试）
        use_vm: 是否使用 VM 执行（True）或树遍历解释器（False）

    Returns:
        如果 capture_output 为 True，返回 print 输出列表；否则返回 None
    """
    try:
        # 1. 词法分析
        lexer = Lexer(source)
        tokens = lexer.tokenize()

        # 2. 语法分析
        parser = Parser(tokens)
        ast = parser.parse()

        # 3. 类型检查
        if check_types:
            checker = TypeChecker()
            checker.check_program(ast)

        # 4. 执行
        if use_vm:
            from .compiler import BytecodeCompiler
            from .vm import NovaVM

            compiler = BytecodeCompiler()
            bytecode = compiler.compile(ast)
            vm = NovaVM(bytecode)
            vm.run()
            if capture_output:
                return vm.get_output()
        else:
            evaluator = Evaluator(check_types=check_types)
            evaluator.eval_program(ast)
            if capture_output:
                return evaluator.get_output()

        return None

    except NovaError as e:
        print(f"错误: {e}", file=sys.stderr)
        if capture_output:
            raise
        sys.exit(1)
    except _CLI_UNEXPECTED_ERRORS as e:
        # 最后防线：捕获常见的非预期异常，防止程序崩溃时无任何输出
        # 正常情况下所有错误都应包装为 NovaError；SystemExit/KeyboardInterrupt 等
        # 致命异常不应被此处捕获，确保用户可通过 Ctrl+C 中断程序
        import traceback
        print(f"内部错误: {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        if capture_output:
            raise
        sys.exit(1)


def dump_bytecode_file(filepath: str):
    """编译文件并打印字节码"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except FileNotFoundError:
        print(f"错误: 文件 '{filepath}' 不存在", file=sys.stderr)
        sys.exit(1)

    from .parser import Parser

    from .compiler import BytecodeCompiler, dump_bytecode
    from .lexer import Lexer

    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    compiler = BytecodeCompiler()
    bytecode = compiler.compile(ast)
    print(dump_bytecode(bytecode))


def run_file(filepath: str, use_vm: bool = True):
    """运行 Nova 源文件"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except FileNotFoundError:
        print(f"错误: 文件 '{filepath}' 不存在", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"错误: 无法读取文件 '{filepath}': {e}", file=sys.stderr)
        sys.exit(1)

    run_source(source, use_vm=use_vm)


def run_repl():
    """交互式 REPL（使用树遍历解释器作为 fallback）"""
    print("Nova 编程语言 v0.2.0 (VM + Interpreter)")
    print('输入 "exit" 或按 Ctrl+D 退出')
    print()

    from .environment import Environment

    evaluator = Evaluator(check_types=False)
    buffer = ""

    while True:
        try:
            if buffer:
                prompt = "  ... "
            else:
                prompt = "nova> "

            line = input(prompt)
            buffer += line + "\n"

            if _is_incomplete(buffer):
                continue

            source = buffer.strip()
            buffer = ""

            if source.lower() in ("exit", "quit"):
                break

            if not source:
                continue

            # 尝试词法分析
            lexer = Lexer(source)
            tokens = lexer.tokenize()

            # 尝试语法分析
            parser = Parser(tokens)
            ast = parser.parse()

            # 可选类型检查（REPL 中类型错误不阻止执行，仅警告）
            try:
                checker = TypeChecker()
                checker.check_program(ast)
            except NovaError as e:
                print(f"类型警告: {e}", file=sys.stderr)

            # 求值（REPL 使用解释器）
            evaluator.clear_output()
            evaluator.env = Environment()
            evaluator._setup_builtins()
            evaluator.eval_program(ast)

        except KeyboardInterrupt:
            print()
            buffer = ""
        except EOFError:
            print()
            break
        except NovaError as e:
            print(f"错误: {e}", file=sys.stderr)
            buffer = ""
        except _CLI_UNEXPECTED_ERRORS as e:
            # 最后防线：REPL 中捕获常见的非预期异常，防止单条语句导致整个 REPL 崩溃
            # SystemExit / KeyboardInterrupt 等致命异常由上层处理（Ctrl+C / Ctrl+D）
            import traceback
            print(f"内部错误: {type(e).__name__}: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            buffer = ""


# 括号配对映射：闭合括号 -> 开启括号
_CLOSE_TO_OPEN = {")": "(", "}": "{", "]": "["}
# 开启括号集合
_OPEN_BRACKETS = set(_CLOSE_TO_OPEN.values())


def _is_incomplete(source: str) -> bool:
    """检查代码块是否不完整（括号未闭合）

    逐字符扫描源码，忽略双引号字符串内的括号，
    统计 {} / () / [] 的嵌套深度。任一深度大于 0 则视为不完整。
    """
    counts = {"(": 0, "{": 0, "[": 0}
    in_string = False

    for ch in source:
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in _OPEN_BRACKETS:
            counts[ch] += 1
        elif ch in _CLOSE_TO_OPEN:
            counts[_CLOSE_TO_OPEN[ch]] -= 1

    return any(d > 0 for d in counts.values())


def _count_indent(line: str) -> int:
    """计算一行的缩进级别（未闭合的 { - 已闭合的 }）"""
    depth = 0
    in_string = False
    for ch in line:
        if ch == '"' and not in_string:
            in_string = True
        elif ch == '"' and in_string:
            in_string = False
        elif in_string:
            continue
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
    return depth


def _attach_source(err, source: str):
    """为错误对象附加源码上下文"""
    if err.source_code is None and source is not None:
        err.source_code = source


def _read_source_file(filepath: str) -> str:
    """读取源码文件，处理常见的 IO 错误并退出"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"错误: 文件 '{filepath}' 不存在", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"错误: 无法读取文件 '{filepath}': {e}", file=sys.stderr)
        sys.exit(1)


def _cmd_repl(_args):
    """启动交互式 REPL"""
    run_repl()


def _cmd_eval(args):
    """求值表达式"""
    if len(args) < 1:
        print('用法: nova.py -e "表达式"', file=sys.stderr)
        sys.exit(1)
    run_source(args[0])


def _cmd_help(_args):
    """打印帮助信息"""
    print("Nova 编程语言解释器 v0.2.0")
    print()
    print("用法:")
    print("  nova.py                        启动交互式 REPL")
    print("  nova.py <file.nova>              使用 VM 运行 Nova 源文件（默认）")
    print("  nova.py --vm <file.nova>         使用 VM 运行")
    print("  nova.py --eval <file.nova>       使用树遍历解释器运行")
    print("  nova.py --check <file.nova>      仅类型检查")
    print("  nova.py --dump-bytecode <file.nova>  编译并打印字节码")
    print('  nova.py -e "expr"               求值表达式')


def _cmd_vm(args):
    """使用 VM 运行源文件"""
    if len(args) < 1:
        print("用法: nova.py --vm <file.nova>", file=sys.stderr)
        sys.exit(1)
    run_file(args[0], use_vm=True)


def _cmd_eval_file(args):
    """使用树遍历解释器运行源文件"""
    if len(args) < 1:
        print("用法: nova.py --eval <file.nova>", file=sys.stderr)
        sys.exit(1)
    run_file(args[0], use_vm=False)


def _cmd_check(args):
    """仅进行类型检查"""
    if len(args) < 1:
        print("用法: nova.py --check <file.nova>", file=sys.stderr)
        sys.exit(1)
    source = _read_source_file(args[0])
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    checker = TypeChecker()
    checker.check_program(ast)
    print("类型检查通过")


def _cmd_dump_bytecode(args):
    """编译并打印字节码"""
    if len(args) < 1:
        print("用法: nova.py --dump-bytecode <file.nova>", file=sys.stderr)
        sys.exit(1)
    dump_bytecode_file(args[0])


# 命令 -> 处理函数映射表
_COMMAND_HANDLERS = {
    "-e": _cmd_eval,
    "-h": _cmd_help,
    "--help": _cmd_help,
    "--vm": _cmd_vm,
    "--eval": _cmd_eval_file,
    "--check": _cmd_check,
    "--dump-bytecode": _cmd_dump_bytecode,
}


def main():
    """主函数：解析命令行参数并分发到对应处理函数"""
    if len(sys.argv) < 2:
        run_repl()
        return

    cmd = sys.argv[1]
    handler = _COMMAND_HANDLERS.get(cmd)
    if handler:
        handler(sys.argv[2:])
    else:
        run_file(cmd)


if __name__ == "__main__":
    main()
