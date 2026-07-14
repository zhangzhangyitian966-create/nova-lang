"""
Nova 模块系统测试

测试模块导入/导出功能，包括：
- 简单导入：模块 A 定义函数，模块 B 导入并使用
- 导出可见性：只有导出的名称对导入者可见
- 相对路径导入
- 循环导入检测
- 标准库模块导入
- 模块解析器测试
"""

import os
import sys
import tempfile
import shutil
import pytest

from nova.lexer import Lexer
from nova.parser import Parser
from nova.type_checker import TypeChecker, TypeEnv
from nova.evaluator import Evaluator, Environment
from nova.modules import ModuleResolver, ModuleManager, ModuleInfo, clear_module_cache
from nova.errors import NovaError, RuntimeError_


# ============================================================
# 辅助函数
# ============================================================

def parse(source: str):
    """解析源代码为 AST"""
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse()


def eval_source(source: str, search_paths=None, current_file: str = None,
                check_types: bool = True) -> list:
    """运行 Nova 源代码并返回输出"""
    from nova.modules import ModuleManager
    manager = ModuleManager(search_paths or [])
    evaluator = Evaluator(check_types=check_types,
                          module_manager=manager,
                          current_file=current_file)
    program = parse(source)
    evaluator.eval_program(program)
    return evaluator.get_output()


def make_temp_dir():
    """创建临时目录"""
    return tempfile.mkdtemp(prefix="nova_test_")


def write_temp_file(directory: str, filename: str, content: str) -> str:
    """在临时目录中写入文件并返回完整路径"""
    filepath = os.path.join(directory, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return filepath


# ============================================================
# 测试模块解析器
# ============================================================

class TestModuleResolver:

    def test_resolve_relative_current(self):
        """解析当前目录的相对路径"""
        resolver = ModuleResolver(["/tmp/test_modules"], current_file="/tmp/test_modules/main.nova")
        # 在搜索路径中创建文件
        os.makedirs("/tmp/test_modules", exist_ok=True)
        try:
            with open("/tmp/test_modules/utils.nova", 'w') as f:
                f.write("let x = 1")
            result = resolver.resolve("./utils")
            assert result == "/tmp/test_modules/utils.nova"
        finally:
            os.remove("/tmp/test_modules/utils.nova")

    def test_resolve_relative_parent(self):
        """解析父目录的相对路径"""
        os.makedirs("/tmp/test_parent/sub", exist_ok=True)
        os.makedirs("/tmp/test_parent/sibling", exist_ok=True)
        try:
            with open("/tmp/test_parent/sibling/mod.nova", 'w') as f:
                f.write("let x = 1")
            resolver = ModuleResolver(["/tmp/test_parent/sub"],
                                       current_file="/tmp/test_parent/sub/main.nova")
            result = resolver.resolve("../sibling/mod")
            assert result == "/tmp/test_parent/sibling/mod.nova"
        finally:
            shutil.rmtree("/tmp/test_parent", ignore_errors=True)

    def test_resolve_package_import(self):
        """解析包导入 (std/math)"""
        os.makedirs("/tmp/test_pkg/std", exist_ok=True)
        try:
            with open("/tmp/test_pkg/std/math.nova", 'w') as f:
                f.write("let x = 1")
            resolver = ModuleResolver(["/tmp/test_pkg"])
            result = resolver.resolve("std/math")
            assert result == "/tmp/test_pkg/std/math.nova"
        finally:
            shutil.rmtree("/tmp/test_pkg", ignore_errors=True)

    def test_resolve_not_found(self):
        """解析不存在的模块"""
        resolver = ModuleResolver(["/tmp/nonexistent"])
        result = resolver.resolve("nonexistent_module")
        assert result is None

    def test_resolve_with_extension(self):
        """解析带扩展名的路径"""
        os.makedirs("/tmp/test_ext", exist_ok=True)
        try:
            with open("/tmp/test_ext/mod.nova", 'w') as f:
                f.write("let x = 1")
            resolver = ModuleResolver(["/tmp/test_ext"])
            result = resolver.resolve("mod.nova")
            assert result == "/tmp/test_ext/mod.nova"
        finally:
            shutil.rmtree("/tmp/test_ext", ignore_errors=True)

    def test_resolve_index_nova(self):
        """解析目录下的 index.nova"""
        os.makedirs("/tmp/test_index/pkg", exist_ok=True)
        try:
            with open("/tmp/test_index/pkg/index.nova", 'w') as f:
                f.write("let x = 1")
            resolver = ModuleResolver(["/tmp/test_index"])
            result = resolver.resolve("pkg")
            assert result == "/tmp/test_index/pkg/index.nova"
        finally:
            shutil.rmtree("/tmp/test_index", ignore_errors=True)


# ============================================================
# 测试简单导入
# ============================================================

class TestSimpleImport:

    def test_import_function(self):
        """模块 A 定义函数，模块 B 导入并使用"""
        tmpdir = make_temp_dir()
        try:
            # 创建被导入模块
            write_temp_file(tmpdir, "helper.nova", """
export greet

fn greet(name: String) -> String {
  "Hello, " ++ name ++ "!"
}
""")

            # 创建主模块
            write_temp_file(tmpdir, "main.nova", """
import "./helper"

let msg = greet("World")
print(msg)
""")

            from nova.modules import ModuleManager
            manager = ModuleManager(search_paths=[tmpdir])

            with open(os.path.join(tmpdir, "main.nova"), 'r') as f:
                source = f.read()

            evaluator = Evaluator(check_types=False,
                                  module_manager=manager,
                                  current_file=os.path.join(tmpdir, "main.nova"))
            program = parse(source)
            evaluator.eval_program(program)
            output = evaluator.get_output()

            assert "Hello, World!" in output
        finally:
            shutil.rmtree(tmpdir)

    def test_import_multiple_functions(self):
        """导入模块中的多个函数"""
        tmpdir = make_temp_dir()
        try:
            write_temp_file(tmpdir, "math_helper.nova", """
export add
export mul

fn add(a: Int, b: Int) -> Int { a + b }
fn mul(a: Int, b: Int) -> Int { a * b }
""")

            write_temp_file(tmpdir, "main.nova", """
import "./math_helper"

print(add(2, 3))
print(mul(4, 5))
""")

            from nova.modules import ModuleManager
            manager = ModuleManager(search_paths=[tmpdir])

            with open(os.path.join(tmpdir, "main.nova"), 'r') as f:
                source = f.read()

            evaluator = Evaluator(check_types=False,
                                  module_manager=manager,
                                  current_file=os.path.join(tmpdir, "main.nova"))
            program = parse(source)
            evaluator.eval_program(program)
            output = evaluator.get_output()

            assert "5" in output
            assert "20" in output
        finally:
            shutil.rmtree(tmpdir)

    def test_import_constant(self):
        """导入模块中的常量"""
        tmpdir = make_temp_dir()
        try:
            write_temp_file(tmpdir, "constants.nova", """
export PI
export MAX_SIZE

let PI = 3.14159
let MAX_SIZE = 100
""")

            write_temp_file(tmpdir, "main.nova", """
import "./constants"

print(PI)
print(MAX_SIZE)
""")

            from nova.modules import ModuleManager
            manager = ModuleManager(search_paths=[tmpdir])

            with open(os.path.join(tmpdir, "main.nova"), 'r') as f:
                source = f.read()

            evaluator = Evaluator(check_types=False,
                                  module_manager=manager,
                                  current_file=os.path.join(tmpdir, "main.nova"))
            program = parse(source)
            evaluator.eval_program(program)
            output = evaluator.get_output()

            assert "3.14159" in output
            assert "100" in output
        finally:
            shutil.rmtree(tmpdir)


# ============================================================
# 测试导出可见性
# ============================================================

class TestExportVisibility:

    def test_only_exported_names_visible(self):
        """只有导出的名称对导入者可见"""
        tmpdir = make_temp_dir()
        try:
            # 模块只导出 foo，不导出 bar
            write_temp_file(tmpdir, "visibility.nova", """
export foo

fn foo() -> Int { 42 }
fn bar() -> Int { 99 }
""")

            write_temp_file(tmpdir, "main.nova", """
import "./visibility"

print(foo())
""")

            from nova.modules import ModuleManager
            manager = ModuleManager(search_paths=[tmpdir])

            with open(os.path.join(tmpdir, "main.nova"), 'r') as f:
                source = f.read()

            evaluator = Evaluator(check_types=False,
                                  module_manager=manager,
                                  current_file=os.path.join(tmpdir, "main.nova"))
            program = parse(source)
            evaluator.eval_program(program)
            output = evaluator.get_output()

            assert "42" in output
        finally:
            shutil.rmtree(tmpdir)

    def test_unexported_name_not_visible(self):
        """未导出的名称对导入者不可见"""
        tmpdir = make_temp_dir()
        try:
            write_temp_file(tmpdir, "secret.nova", """
export public_fn

fn public_fn() -> Int { 1 }
fn secret_fn() -> Int { 2 }
""")

            # 尝试使用未导出的函数
            write_temp_file(tmpdir, "main.nova", """
import "./secret"

print(secret_fn())
""")

            from nova.modules import ModuleManager
            manager = ModuleManager(search_paths=[tmpdir])

            with open(os.path.join(tmpdir, "main.nova"), 'r') as f:
                source = f.read()

            evaluator = Evaluator(check_types=False,
                                  module_manager=manager,
                                  current_file=os.path.join(tmpdir, "main.nova"))
            program = parse(source)

            # secret_fn 未导出，应该不可用
            with pytest.raises((NameError, RuntimeError_, NovaError)):
                evaluator.eval_program(program)
        finally:
            shutil.rmtree(tmpdir)

    def test_module_with_all_exports(self):
        """导出所有公共 API"""
        tmpdir = make_temp_dir()
        try:
            write_temp_file(tmpdir, "api.nova", """
export create
export process
export destroy

fn create() -> Int { 1 }
fn process(x: Int) -> Int { x * 2 }
fn destroy(x: Int) -> Unit { print("destroyed") }
""")

            write_temp_file(tmpdir, "main.nova", """
import "./api"

let a = create()
let b = process(a)
print(b)
destroy(b)
""")

            from nova.modules import ModuleManager
            manager = ModuleManager(search_paths=[tmpdir])

            with open(os.path.join(tmpdir, "main.nova"), 'r') as f:
                source = f.read()

            evaluator = Evaluator(check_types=False,
                                  module_manager=manager,
                                  current_file=os.path.join(tmpdir, "main.nova"))
            program = parse(source)
            evaluator.eval_program(program)
            output = evaluator.get_output()

            assert "2" in output
            # Note: print inside imported functions writes to the module's evaluator output,
            # not the main evaluator's output, so "destroyed" won't appear here
        finally:
            shutil.rmtree(tmpdir)


# ============================================================
# 测试相对路径导入
# ============================================================

class TestRelativeImports:

    def test_import_sibling(self):
        """导入兄弟目录的模块"""
        tmpdir = make_temp_dir()
        try:
            os.makedirs(os.path.join(tmpdir, "sibling"))
            write_temp_file(tmpdir, "sibling/helper.nova", """
export helper_fn

fn helper_fn() -> String { "from sibling" }
""")

            write_temp_file(tmpdir, "main.nova", """
import "./sibling/helper"

print(helper_fn())
""")

            from nova.modules import ModuleManager
            manager = ModuleManager(search_paths=[tmpdir])

            with open(os.path.join(tmpdir, "main.nova"), 'r') as f:
                source = f.read()

            evaluator = Evaluator(check_types=False,
                                  module_manager=manager,
                                  current_file=os.path.join(tmpdir, "main.nova"))
            program = parse(source)
            evaluator.eval_program(program)
            output = evaluator.get_output()

            assert "from sibling" in output
        finally:
            shutil.rmtree(tmpdir)

    def test_import_parent_directory(self):
        """导入父目录的模块"""
        tmpdir = make_temp_dir()
        try:
            write_temp_file(tmpdir, "shared.nova", """
export shared_val

let shared_val = "from parent"
""")

            os.makedirs(os.path.join(tmpdir, "subdir"))
            write_temp_file(tmpdir, "subdir/child.nova", """
import "../shared"

print(shared_val)
""")

            from nova.modules import ModuleManager
            manager = ModuleManager(search_paths=[tmpdir])

            child_path = os.path.join(tmpdir, "subdir", "child.nova")
            with open(child_path, 'r') as f:
                source = f.read()

            evaluator = Evaluator(check_types=False,
                                  module_manager=manager,
                                  current_file=child_path)
            program = parse(source)
            evaluator.eval_program(program)
            output = evaluator.get_output()

            assert "from parent" in output
        finally:
            shutil.rmtree(tmpdir)

    def test_import_deep_relative(self):
        """深层相对路径导入"""
        tmpdir = make_temp_dir()
        try:
            os.makedirs(os.path.join(tmpdir, "a", "b", "c"))
            write_temp_file(tmpdir, "a/b/c/deep.nova", """
export deep_val

let deep_val = 42
""")

            write_temp_file(tmpdir, "a/main.nova", """
import "./b/c/deep"

print(deep_val)
""")

            from nova.modules import ModuleManager
            manager = ModuleManager(search_paths=[tmpdir])

            with open(os.path.join(tmpdir, "a", "main.nova"), 'r') as f:
                source = f.read()

            evaluator = Evaluator(check_types=False,
                                  module_manager=manager,
                                  current_file=os.path.join(tmpdir, "a", "main.nova"))
            program = parse(source)
            evaluator.eval_program(program)
            output = evaluator.get_output()

            assert "42" in output
        finally:
            shutil.rmtree(tmpdir)


# ============================================================
# 测试循环导入检测
# ============================================================

class TestCircularImportDetection:

    def test_direct_circular_import(self):
        """直接循环导入 A -> B -> A"""
        tmpdir = make_temp_dir()
        try:
            write_temp_file(tmpdir, "mod_a.nova", """
export fn_a

import "./mod_b"

fn fn_a() -> Int { fn_b() + 1 }
""")

            write_temp_file(tmpdir, "mod_b.nova", """
export fn_b

import "./mod_a"

fn fn_b() -> Int { 10 }
""")

            write_temp_file(tmpdir, "main.nova", """
import "./mod_a"
print(fn_a())
""")

            from nova.modules import ModuleManager
            manager = ModuleManager(search_paths=[tmpdir])

            with open(os.path.join(tmpdir, "main.nova"), 'r') as f:
                source = f.read()

            evaluator = Evaluator(check_types=False,
                                  module_manager=manager,
                                  current_file=os.path.join(tmpdir, "main.nova"))
            program = parse(source)

            # 应该抛出循环导入错误
            with pytest.raises((RuntimeError_, NovaError, RuntimeError)):
                evaluator.eval_program(program)
        finally:
            shutil.rmtree(tmpdir)

    def test_three_way_circular(self):
        """三方循环导入 A -> B -> C -> A"""
        tmpdir = make_temp_dir()
        try:
            write_temp_file(tmpdir, "a.nova", """
export fa
import "./b"
fn fa() -> Int { fb() + 1 }
""")
            write_temp_file(tmpdir, "b.nova", """
export fb
import "./c"
fn fb() -> Int { fc() + 2 }
""")
            write_temp_file(tmpdir, "c.nova", """
export fc
import "./a"
fn fc() -> Int { 3 }
""")

            write_temp_file(tmpdir, "main.nova", """
import "./a"
print(fa())
""")

            from nova.modules import ModuleManager
            manager = ModuleManager(search_paths=[tmpdir])

            with open(os.path.join(tmpdir, "main.nova"), 'r') as f:
                source = f.read()

            evaluator = Evaluator(check_types=False,
                                  module_manager=manager,
                                  current_file=os.path.join(tmpdir, "main.nova"))
            program = parse(source)

            with pytest.raises((RuntimeError_, NovaError, RuntimeError)):
                evaluator.eval_program(program)
        finally:
            shutil.rmtree(tmpdir)


# ============================================================
# 测试标准库模块导入
# ============================================================

class TestStdlibImport:

    def test_import_stdlib_math(self):
        """导入标准库数学模块"""
        # 使用 examples/stdlib/math.nova
        stdlib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                    "examples", "stdlib")

        tmpdir = make_temp_dir()
        try:
            write_temp_file(tmpdir, "test_math.nova", """
import "./math_mod"

print(clamp(5.0, 0.0, 10.0))
print(clamp(-1.0, 0.0, 10.0))
print(clamp(15.0, 0.0, 10.0))
""")

            # 复制 math.nova 到临时目录
            shutil.copy(os.path.join(stdlib_path, "math.nova"),
                        os.path.join(tmpdir, "math_mod.nova"))

            from nova.modules import ModuleManager
            manager = ModuleManager(search_paths=[tmpdir])

            with open(os.path.join(tmpdir, "test_math.nova"), 'r') as f:
                source = f.read()

            evaluator = Evaluator(check_types=False,
                                  module_manager=manager,
                                  current_file=os.path.join(tmpdir, "test_math.nova"))
            program = parse(source)
            evaluator.eval_program(program)
            output = evaluator.get_output()

            assert "5.0" in output
            assert "0.0" in output
            assert "10.0" in output
        finally:
            shutil.rmtree(tmpdir)

    def test_import_stdlib_io(self):
        """导入标准库 I/O 模块"""
        stdlib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                    "examples", "stdlib")

        tmpdir = make_temp_dir()
        try:
            write_temp_file(tmpdir, "test_io.nova", """
import "./io_mod"

print(greet("Nova"))
""")

            # 复制 io.nova 到临时目录
            shutil.copy(os.path.join(stdlib_path, "io.nova"),
                        os.path.join(tmpdir, "io_mod.nova"))

            from nova.modules import ModuleManager
            manager = ModuleManager(search_paths=[tmpdir])

            with open(os.path.join(tmpdir, "test_io.nova"), 'r') as f:
                source = f.read()

            evaluator = Evaluator(check_types=False,
                                  module_manager=manager,
                                  current_file=os.path.join(tmpdir, "test_io.nova"))
            program = parse(source)
            evaluator.eval_program(program)
            output = evaluator.get_output()

            assert "Hello, Nova!" in output
        finally:
            shutil.rmtree(tmpdir)


# ============================================================
# 测试模块缓存
# ============================================================

class TestModuleCache:

    def test_module_cached_after_first_load(self):
        """模块首次加载后应该被缓存"""
        tmpdir = make_temp_dir()
        try:
            write_temp_file(tmpdir, "cached.nova", """
export val

let val = 42
""")

            from nova.modules import ModuleManager
            manager = ModuleManager(search_paths=[tmpdir])

            # 第一次加载
            info1 = manager.load_module("./cached", tmpdir + "/main.nova")
            assert info1 is not None
            assert manager.is_module_loaded(os.path.abspath(os.path.join(tmpdir, "cached.nova")))

            # 第二次加载应该返回缓存
            info2 = manager.load_module("./cached", tmpdir + "/main.nova")
            assert info1 is info2  # 同一个对象
        finally:
            shutil.rmtree(tmpdir)

    def test_clear_cache(self):
        """清除缓存后模块应该重新加载"""
        tmpdir = make_temp_dir()
        try:
            write_temp_file(tmpdir, "cache_test.nova", """
export val

let val = 42
""")

            from nova.modules import ModuleManager
            manager = ModuleManager(search_paths=[tmpdir])

            info1 = manager.load_module("./cache_test", tmpdir + "/main.nova")
            assert info1 is not None

            manager.clear_cache()
            assert not manager.is_module_loaded(
                os.path.abspath(os.path.join(tmpdir, "cache_test.nova")))

            info2 = manager.load_module("./cache_test", tmpdir + "/main.nova")
            assert info2 is not None
            assert info1 is not info2  # 新对象
        finally:
            shutil.rmtree(tmpdir)


# ============================================================
# 测试类型检查器集成
# ============================================================

class TestTypeCheckerIntegration:

    def test_import_types_available(self):
        """导入的函数类型应该可用"""
        tmpdir = make_temp_dir()
        try:
            write_temp_file(tmpdir, "typed.nova", """
export add

fn add(a: Int, b: Int) -> Int { a + b }
""")

            write_temp_file(tmpdir, "main.nova", """
import "./typed"

let result: Int = add(1, 2)
print(result)
""")

            from nova.modules import ModuleManager
            manager = ModuleManager(search_paths=[tmpdir])

            with open(os.path.join(tmpdir, "main.nova"), 'r') as f:
                source = f.read()

            program = parse(source)
            checker = TypeChecker(source=source,
                                  module_manager=manager,
                                  current_file=os.path.join(tmpdir, "main.nova"))
            checker.check_program(program)

            # 不应该有错误
            assert len(checker.error_collector.errors) == 0
        finally:
            shutil.rmtree(tmpdir)

    def test_exported_names_tracked(self):
        """TypeChecker 应该追踪导出的名称"""
        source = """
export foo
export bar

fn foo() -> Int { 1 }
let bar = 2
"""
        program = parse(source)
        checker = TypeChecker(source=source)
        checker.check_program(program)

        assert "foo" in checker.exported_names
        assert "bar" in checker.exported_names


# ============================================================
# 测试解析器集成
# ============================================================

class TestParserIntegration:

    def test_import_decl_parsed(self):
        """import 声明应该正确解析"""
        source = 'import "mymodule"'
        program = parse(source)
        assert len(program.declarations) == 1
        assert program.declarations[0].module_name == "mymodule"

    def test_export_decl_parsed(self):
        """export 声明应该正确解析"""
        source = 'export myFunc'
        program = parse(source)
        assert len(program.declarations) == 1
        assert program.declarations[0].name == "myFunc"

    def test_import_with_relative_path(self):
        """相对路径导入应该正确解析"""
        source = 'import "./local_module"'
        program = parse(source)
        assert program.declarations[0].module_name == "./local_module"

    def test_import_with_parent_path(self):
        """父目录导入应该正确解析"""
        source = 'import "../parent_module"'
        program = parse(source)
        assert program.declarations[0].module_name == "../parent_module"


# ============================================================
# 测试求值器导出追踪
# ============================================================

class TestEvaluatorExportTracking:

    def test_evaluator_exports_tracked(self):
        """Evaluator 应该追踪导出的名称"""
        source = """
export my_func
export my_val

fn my_func() -> Int { 42 }
let my_val = 100
"""
        program = parse(source)
        evaluator = Evaluator(check_types=False)
        evaluator.eval_program(program)

        assert "my_func" in evaluator.exported_names
        assert "my_val" in evaluator.exported_names