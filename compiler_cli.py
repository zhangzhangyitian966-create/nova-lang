#!/usr/bin/env python3
"""
Nova 编译器 CLI

支持命令：
  nova build <file.nova>     编译为原生二进制
  nova run <file.nova>       编译并运行
  nova check <file.nova>     仅类型检查
  nova fmt <file.nova>       格式化代码（预留）
  nova init <project>        创建新项目
  nova new <template>        从模板创建文件
  nova version               显示版本
  nova help                  显示帮助
"""

import argparse
import os
import shutil
import subprocess
import sys
from typing import Optional

from .parser import Parser

from .errors import NovaError
from .lexer import Lexer
from .type_checker import TypeChecker

NOVA_VERSION = "0.2.0"


class NovaCompiler:
    """Nova 编译器和构建系统"""

    def __init__(self):
        self.c_compiler = self._detect_c_compiler()
        self.c_flags = ["-O2", "-Wall"]
        self.output_dir = "build"
        self.link_runtime = True
        self.runtime_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "runtime"
        )
        self.verbose = False
        self.optimize = 2

    # ----------------------------------------------------------
    # C 编译器检测
    # ----------------------------------------------------------

    def _detect_c_compiler(self) -> Optional[str]:
        """检测可用的 C 编译器，优先级: clang > gcc > cc > cl (MSVC)"""
        for cc in ["clang", "gcc", "cc"]:
            if self._which(cc):
                return cc
        # Windows 上尝试 MSVC cl.exe
        if sys.platform == "win32":
            if self._which("cl"):
                return "cl"
        return None

    @staticmethod
    def _which(name: str) -> Optional[str]:
        """查找可执行文件路径（类似 shutil.which，兼容性更好）"""
        path = shutil.which(name)
        return path

    # ----------------------------------------------------------
    # 编译流程
    # ----------------------------------------------------------

    def _map_optimize_to_ir_level(self, optimize: str) -> int:
        """将 CLI 优化级别 (O0-O3/Os) 映射到 IR PassManager 级别"""
        mapping = {"O0": 0, "O1": 1, "O2": 2, "O3": 2, "Os": 2}
        return mapping.get(optimize, 2)

    def build(
        self,
        source_path: str,
        output_name: str = None,
        optimize: str = "O2",
        target: str = None,
    ) -> str:
        """
        编译 Nova 源码为原生二进制

        使用统一 IR 编译管线：AST→HIR→MIR→LIR→LIRCBackend（C 代码生成），
        受益于三层 IR 优化 Pass（DCE/内联/CSE/LICM）。

        Args:
            source_path: Nova 源文件路径
            output_name: 输出文件名（默认与源文件同名）
            optimize: 优化级别 (O0, O1, O2, O3, Os)
            target: 目标平台

        Returns:
            输出二进制文件路径
        """
        # 1. 检查源文件
        if not os.path.isfile(source_path):
            print(f"错误: 文件 '{source_path}' 不存在", file=sys.stderr)
            sys.exit(1)

        # 读取源码
        with open(source_path, "r", encoding="utf-8") as f:
            source = f.read()

        # 2. 统一 IR 管线：Lexer→Parser→TypeChecker→HIR→MIR→LIR→LIRCBackend→C
        #    （架构手术 B：旧 AST→CCodeGen 路径已弃用，仅 3-6 个月内保留作参照）
        from .backend.compiler_pipeline import BACKEND_C, NovaCompilerPipeline

        if not os.path.isdir(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

        base_name = os.path.splitext(os.path.basename(source_path))[0]
        if not output_name:
            output_name = base_name

        c_file_path = os.path.join(self.output_dir, f"{base_name}.c")

        # 映射 CLI optimize 级别 → IR PassManager 级别
        ir_optimize_level = self._map_optimize_to_ir_level(optimize)

        pipeline = NovaCompilerPipeline(
            target=BACKEND_C, optimize_level=ir_optimize_level
        )
        try:
            # 内部完整流程：前端 + 三层 IR lowering + 三层优化 Pass + LIR→C
            pipeline.compile_source(source, c_file_path)
        except NovaError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)

        if self.verbose:
            print(f"[info] 已生成 C 代码（统一 IR 管线）: {c_file_path}")

        # 3. 调用 C 编译器（与旧流程一致）
        if not self.c_compiler:
            print("错误: 未找到可用的 C 编译器 (gcc/clang)", file=sys.stderr)
            print("请安装 gcc 或 clang 后重试", file=sys.stderr)
            sys.exit(1)

        output_path = os.path.join(self.output_dir, output_name)
        if sys.platform == "win32" and not output_path.endswith(".exe"):
            output_path += ".exe"

        self._compile_c_to_binary(c_file_path, output_path, optimize)

        if self.verbose:
            print(f"[info] 已编译二进制: {output_path}")

        return output_path

    def _compile_c_to_binary(self, c_file_path: str, output_path: str, optimize: str):
        """调用 C 编译器编译 C 源文件为二进制"""
        cc = self.c_compiler

        # 构建 flags
        flags = [f"-{optimize}", "-Wall"]
        if self.link_runtime and os.path.isdir(self.runtime_dir):
            flags.extend(["-I", self.runtime_dir])

        # 链接数学库
        flags.extend(["-lm"])

        if cc == "cl":
            # MSVC 编译器使用不同参数格式
            msvc_flags = [f"/{optimize}", "/W3"]
            if self.link_runtime and os.path.isdir(self.runtime_dir):
                msvc_flags.extend(["/I", self.runtime_dir])
            cmd = [cc] + msvc_flags + ["/Fe:" + output_path, c_file_path]
        else:
            cmd = [cc] + flags + ["-o", output_path, c_file_path]

        if self.verbose:
            print(f"[info] 执行: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print(f"C 编译器错误:", file=sys.stderr)
                if result.stderr:
                    print(result.stderr, file=sys.stderr)
                if result.stdout:
                    print(result.stdout, file=sys.stderr)
                sys.exit(1)
        except subprocess.TimeoutExpired:
            print("错误: C 编译超时", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print(f"错误: 找不到 C 编译器 '{cc}'", file=sys.stderr)
            sys.exit(1)

    def run(self, source_path: str, args: list = None):
        """编译并运行 Nova 程序"""
        output = self.build(source_path)
        run_args = [output]
        if args:
            run_args.extend(args)

        try:
            subprocess.run(run_args, check=True)
        except subprocess.CalledProcessError as e:
            print(f"运行错误: 程序退出码 {e.returncode}", file=sys.stderr)
            sys.exit(e.returncode)

    def check(self, source_path: str):
        """仅进行类型检查"""
        if not os.path.isfile(source_path):
            print(f"错误: 文件 '{source_path}' 不存在", file=sys.stderr)
            sys.exit(1)

        with open(source_path, "r", encoding="utf-8") as f:
            source = f.read()

        try:
            tokens = Lexer(source).tokenize()
            ast = Parser(tokens).parse()
            TypeChecker().check_program(ast)
            print("类型检查通过。")
        except NovaError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)

    def emit_c(self, source_path: str, output_path: str = None):
        """仅生成 C 代码，不编译为二进制

        使用统一 IR 编译管线（架构手术 B：旧 AST→CCodeGen 路径已弃用），
        生成的 C 代码受益于三层 IR 优化 Pass。
        """
        if not os.path.isfile(source_path):
            print(f"错误: 文件 '{source_path}' 不存在", file=sys.stderr)
            sys.exit(1)

        with open(source_path, "r", encoding="utf-8") as f:
            source = f.read()

        if output_path is None:
            base_name = os.path.splitext(os.path.basename(source_path))[0]
            output_path = f"{base_name}.c"

        # 统一 IR 管线：前端 + HIR→MIR→LIR 三层优化 + LIRCBackend 生成 C
        from .backend.compiler_pipeline import BACKEND_C, NovaCompilerPipeline

        pipeline = NovaCompilerPipeline(target=BACKEND_C, optimize_level=2)
        try:
            pipeline.compile_source(source, output_path)
        except NovaError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)

        print(f"已生成 C 代码（统一 IR 管线）: {output_path}")

    def compile_wasm(self, source_path: str, output_name: str = None):
        """编译为 WebAssembly (WasmGC)"""
        from .backend.compiler_pipeline import BACKEND_WASM, NovaCompilerPipeline

        if not os.path.isfile(source_path):
            print(f"错误: 文件 '{source_path}' 不存在", file=sys.stderr)
            sys.exit(1)

        source = open(source_path, "r", encoding="utf-8").read()
        output = (
            output_name or os.path.splitext(os.path.basename(source_path))[0] + ".wasm"
        )

        pipeline = NovaCompilerPipeline(
            target=BACKEND_WASM, optimize_level=self.optimize
        )
        result = pipeline.compile_source(source, output)

        if result:
            print(f"已编译 WasmGC: {output}")
        else:
            wat_path = output.rsplit(".", 1)[0] + ".wat"
            print(f"wat2wasm 不可用，已生成 WAT: {wat_path}")
        return output

    def emit_ir(self, source_path: str, level: str = "lir"):
        """输出 IR（调试用）"""
        from .backend.compiler_pipeline import NovaCompilerPipeline

        if not os.path.isfile(source_path):
            print(f"错误: 文件 '{source_path}' 不存在", file=sys.stderr)
            sys.exit(1)

        source = open(source_path, "r", encoding="utf-8").read()
        pipeline = NovaCompilerPipeline(target="c", optimize_level=0)
        return pipeline.compile_to_ir_text(source, level)

    # ----------------------------------------------------------
    # 项目管理
    # ----------------------------------------------------------

    def init_project(self, name: str, template: str = "basic"):
        """初始化新项目

        创建项目结构:
          name/
            nova.toml
            src/
              main.nova
            tests/
              test_basic.nova
        """
        project_dir = os.path.join(os.getcwd(), name)

        if os.path.exists(project_dir):
            print(f"错误: 目录 '{name}' 已存在", file=sys.stderr)
            sys.exit(1)

        # 创建目录结构
        os.makedirs(os.path.join(project_dir, "src"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "tests"), exist_ok=True)

        # 创建 nova.toml
        toml_content = self._generate_toml(name)
        with open(os.path.join(project_dir, "nova.toml"), "w", encoding="utf-8") as f:
            f.write(toml_content)

        # 创建主文件
        if template == "lib":
            src_content = self._get_template("lib")
        else:
            src_content = self._get_template("basic")

        with open(
            os.path.join(project_dir, "src", "main.nova"), "w", encoding="utf-8"
        ) as f:
            f.write(src_content)

        # 创建测试文件
        test_content = (
            "// Nova 测试文件\n\nfn test_basic() -> Unit {\n  assert(1 + 1 == 2)\n}\n"
        )
        with open(
            os.path.join(project_dir, "tests", "test_basic.nova"), "w", encoding="utf-8"
        ) as f:
            f.write(test_content)

        print(f"已创建 Nova 项目: {name}/")
        print(f"  nova.toml       - 项目配置")
        print(f"  src/main.nova    - 入口文件")
        print(f"  tests/           - 测试目录")

    def new_file(self, template: str = "basic", output_path: str = None):
        """从模板创建新文件"""
        content = self._get_template(template)

        if output_path is None:
            output_path = f"main.nova"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"已创建文件: {output_path} (模板: {template})")

    def _generate_toml(self, name: str) -> str:
        """生成 nova.toml 项目配置文件"""
        return f"""[project]
name = "{name}"
version = "0.1.0"
authors = ["Nova Developer"]

[build]
target = "native"
optimize = "O2"
output = "{name}"

[dependencies]
# std = "*"

[windows]
icon = "app.ico"
subsystem = "console"
manifest = "app.manifest"
"""

    @staticmethod
    def _get_template(template_name: str) -> str:
        """获取模板内容"""
        templates_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "templates",
            template_name,
            "src",
        )

        # 优先从模板文件读取
        template_file = os.path.join(templates_dir, "main.nova")
        if template_name == "lib":
            template_file = os.path.join(templates_dir, "lib.nova")

        if os.path.isfile(template_file):
            with open(template_file, "r", encoding="utf-8") as f:
                return f.read()

        # fallback 内置模板
        builtins = {
            "basic": '// Nova 基本项目模板\n// 由 `nova init` 命令创建\n\nfn main() -> Unit {\n  println("Hello, Nova!")\n}\n',
            "lib": '// Nova 库项目模板\n\nfn add(a: Int, b: Int) -> Int {\n  a + b\n}\n\nfn greet(name: String) -> String {\n  "Hello, " ++ name ++ "!"\n}\n',
        }
        return builtins.get(template_name, builtins["basic"])


# ============================================================
# CLI 命令处理
# ============================================================


def print_version():
    """显示版本信息"""
    print(f"Nova 编程语言 v{NOVA_VERSION}")
    print(f"C 后端编译器")


def print_help():
    """显示帮助信息"""
    print(f"""Nova 编译器 CLI v{NOVA_VERSION}

用法:
  nova build <file.nova>       编译为原生二进制
  nova run <file.nova>         编译并运行
  nova check <file.nova>       仅类型检查
  nova emit-c <file.nova>      仅生成 C 代码
  nova emit-wasm <file.nova>   编译为 WebAssembly (WasmGC)
  nova emit-ir <file.nova>     输出 IR 中间表示 (hir/mir/lir)
  nova init <project_name>     创建新项目
  nova new <template>          从模板创建文件
  nova version                 显示版本
  nova help                    显示帮助

选项:
  -v, --verbose                显示详细输出
  -O <level>                   优化级别 (0, 1, 2, 3, s)
  -o <name>                    输出文件名

示例:
  nova build hello.nova
  nova run hello.nova
  nova emit-wasm hello.nova
  nova emit-ir hello.nova -l lir
  nova check hello.nova
  nova init myproject
  nova new basic
""")


def _build_argparser():
    """构建并返回 argparse.ArgumentParser 实例

    集中管理所有子命令的配置，与主逻辑分离。
    """
    parser = argparse.ArgumentParser(
        prog="nova",
        description="Nova 编程语言编译器 CLI",
        add_help=False,
    )
    subparsers = parser.add_subparsers(dest="command")

    # build 命令
    build_parser = subparsers.add_parser("build", help="编译为原生二进制")
    build_parser.add_argument("file", help="Nova 源文件路径")
    build_parser.add_argument("-o", "--output", help="输出文件名")
    build_parser.add_argument(
        "-O",
        "--optimize",
        default="O2",
        choices=["O0", "O1", "O2", "O3", "Os"],
        help="优化级别",
    )
    build_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")

    # run 命令
    run_parser = subparsers.add_parser("run", help="编译并运行")
    run_parser.add_argument("file", help="Nova 源文件路径")
    run_parser.add_argument("run_args", nargs="*", help="运行时参数")
    run_parser.add_argument("-o", "--output", help="输出文件名")
    run_parser.add_argument(
        "-O",
        "--optimize",
        default="O2",
        choices=["O0", "O1", "O2", "O3", "Os"],
        help="优化级别",
    )
    run_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")

    # check 命令
    check_parser = subparsers.add_parser("check", help="仅类型检查")
    check_parser.add_argument("file", help="Nova 源文件路径")

    # emit-c 命令
    emit_c_parser = subparsers.add_parser("emit-c", help="仅生成 C 代码")
    emit_c_parser.add_argument("file", help="Nova 源文件路径")
    emit_c_parser.add_argument("-o", "--output", help="输出 C 文件路径")

    # emit-wasm 命令
    emit_wasm_parser = subparsers.add_parser(
        "emit-wasm", help="编译为 WebAssembly (WasmGC)"
    )
    emit_wasm_parser.add_argument("file", help="Nova 源文件路径")
    emit_wasm_parser.add_argument("-o", "--output", help="输出文件名")
    emit_wasm_parser.add_argument(
        "-O", "--optimize", default=2, type=int, choices=[0, 1, 2, 3], help="优化级别"
    )

    # emit-ir 命令
    emit_ir_parser = subparsers.add_parser("emit-ir", help="输出 IR 中间表示")
    emit_ir_parser.add_argument("file", help="Nova 源文件路径")
    emit_ir_parser.add_argument(
        "-l",
        "--level",
        default="lir",
        choices=["hir", "mir", "lir"],
        help="IR 层级 (hir/mir/lir)",
    )

    # init 命令
    init_parser = subparsers.add_parser("init", help="创建新项目")
    init_parser.add_argument("name", help="项目名称")
    init_parser.add_argument(
        "-t", "--template", default="basic", choices=["basic", "lib"], help="项目模板"
    )

    # new 命令
    new_parser = subparsers.add_parser("new", help="从模板创建文件")
    new_parser.add_argument(
        "template", default="basic", nargs="?", help="模板名称 (basic/lib)"
    )
    new_parser.add_argument("-o", "--output", help="输出文件路径")

    # version / help
    subparsers.add_parser("version", help="显示版本")
    subparsers.add_parser("help", help="显示帮助")

    return parser


def _cmd_build(args, compiler):
    """处理 build 命令"""
    compiler.verbose = args.verbose
    output = compiler.build(
        args.file, output_name=args.output, optimize=args.optimize
    )
    print(f"编译成功: {output}")


def _cmd_run(args, compiler):
    """处理 run 命令"""
    compiler.verbose = args.verbose
    compiler.run(args.file, args=args.run_args)


def _cmd_check(args, compiler):
    """处理 check 命令"""
    compiler.check(args.file)


def _cmd_emit_c(args, compiler):
    """处理 emit-c 命令"""
    compiler.emit_c(args.file, output_path=args.output)


def _cmd_emit_wasm(args, compiler):
    """处理 emit-wasm 命令"""
    compiler.optimize = args.optimize
    compiler.compile_wasm(args.file, output_name=args.output)


def _cmd_emit_ir(args, compiler):
    """处理 emit-ir 命令"""
    ir_text = compiler.emit_ir(args.file, level=args.level)
    if ir_text:
        print(ir_text)


def _cmd_init(args, compiler):
    """处理 init 命令"""
    compiler.init_project(args.name, template=args.template)


def _cmd_new(args, compiler):
    """处理 new 命令"""
    compiler.new_file(template=args.template, output_path=args.output)


def _cmd_version(_args, _compiler):
    """处理 version 命令"""
    print_version()


def _cmd_help(_args, _compiler):
    """处理 help 命令"""
    print_help()


# 命令 -> 处理函数映射表
_COMMAND_HANDLERS = {
    "build": _cmd_build,
    "run": _cmd_run,
    "check": _cmd_check,
    "emit-c": _cmd_emit_c,
    "emit-wasm": _cmd_emit_wasm,
    "emit-ir": _cmd_emit_ir,
    "init": _cmd_init,
    "new": _cmd_new,
    "version": _cmd_version,
    "help": _cmd_help,
}


def main():
    """CLI 主入口：解析参数并分发到对应命令处理函数"""
    parser = _build_argparser()
    args = parser.parse_args()

    if not args.command:
        print_help()
        return

    handler = _COMMAND_HANDLERS.get(args.command)
    if handler:
        compiler = NovaCompiler()
        handler(args, compiler)
    else:
        print(f"未知命令: {args.command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
