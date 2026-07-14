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
import os

# 确保导入路径正确
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer
from parser import Parser
from type_checker import TypeChecker
from evaluator import Evaluator
from errors import NovaError


def run_source(source: str, check_types: bool = True, capture_output: bool = False, use_vm: bool = True):
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
            from compiler import BytecodeCompiler
            from vm import NovaVM
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
    except Exception as e:
        print(f"内部错误: {e}", file=sys.stderr)
        if capture_output:
            raise
        sys.exit(1)


def dump_bytecode_file(filepath: str):
    """编译文件并打印字节码"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
    except FileNotFoundError:
        print(f"错误: 文件 '{filepath}' 不存在", file=sys.stderr)
        sys.exit(1)

    from compiler import BytecodeCompiler, dump_bytecode
    from lexer import Lexer
    from parser import Parser

    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    compiler = BytecodeCompiler()
    bytecode = compiler.compile(ast)
    print(dump_bytecode(bytecode))


def run_file(filepath: str, use_vm: bool = True):
    """运行 Nova 源文件"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
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

    from environment import Environment
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

            # 可选类型检查
            try:
                checker = TypeChecker()
                checker.check_program(ast)
            except Exception:
                pass

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
        except Exception as e:
            print(f"内部错误: {e}", file=sys.stderr)
            buffer = ""


def _is_incomplete(source: str) -> bool:
    """检查代码块是否不完整（括号未闭合）"""
    depth_brace = 0
    depth_paren = 0
    depth_bracket = 0
    in_string = False

    for ch in source:
        if ch == '"' and not in_string:
            in_string = True
        elif ch == '"' and in_string:
            in_string = False
        elif in_string:
            continue
        elif ch == '{':
            depth_brace += 1
        elif ch == '}':
            depth_brace -= 1
        elif ch == '(':
            depth_paren += 1
        elif ch == ')':
            depth_paren -= 1
        elif ch == '[':
            depth_bracket += 1
        elif ch == ']':
            depth_bracket -= 1

    return depth_brace > 0 or depth_paren > 0 or depth_bracket > 0


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
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
    return depth


def _attach_source(err, source: str):
    """为错误对象附加源码上下文"""
    if err.source_code is None and source is not None:
        err.source_code = source


def main():
    """主函数"""
    if len(sys.argv) < 2:
        run_repl()
    elif sys.argv[1] == "-e":
        if len(sys.argv) < 3:
            print("用法: nova.py -e \"表达式\"", file=sys.stderr)
            sys.exit(1)
        run_source(sys.argv[2])
    elif sys.argv[1] in ("-h", "--help"):
        print("Nova 编程语言解释器 v0.2.0")
        print()
        print("用法:")
        print("  nova.py                        启动交互式 REPL")
        print("  nova.py <file.nova>              使用 VM 运行 Nova 源文件（默认）")
        print("  nova.py --vm <file.nova>         使用 VM 运行")
        print("  nova.py --eval <file.nova>       使用树遍历解释器运行")
        print("  nova.py --check <file.nova>      仅类型检查")
        print("  nova.py --dump-bytecode <file.nova>  编译并打印字节码")
        print("  nova.py -e \"expr\"               求值表达式")
    elif sys.argv[1] == "--vm":
        if len(sys.argv) < 3:
            print("用法: nova.py --vm <file.nova>", file=sys.stderr)
            sys.exit(1)
        run_file(sys.argv[2], use_vm=True)
    elif sys.argv[1] == "--eval":
        if len(sys.argv) < 3:
            print("用法: nova.py --eval <file.nova>", file=sys.stderr)
            sys.exit(1)
        run_file(sys.argv[2], use_vm=False)
    elif sys.argv[1] == "--check":
        if len(sys.argv) < 3:
            print("用法: nova.py --check <file.nova>", file=sys.stderr)
            sys.exit(1)
        try:
            with open(sys.argv[2], 'r', encoding='utf-8') as f:
                source = f.read()
        except FileNotFoundError:
            print(f"错误: 文件 '{sys.argv[2]}' 不存在", file=sys.stderr)
            sys.exit(1)
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        checker = TypeChecker()
        checker.check_program(ast)
        print("类型检查通过")
    elif sys.argv[1] == "--dump-bytecode":
        if len(sys.argv) < 3:
            print("用法: nova.py --dump-bytecode <file.nova>", file=sys.stderr)
            sys.exit(1)
        dump_bytecode_file(sys.argv[2])
    else:
        run_file(sys.argv[1])


if __name__ == "__main__":
    main()
