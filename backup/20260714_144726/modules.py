"""
Nova 编程语言 - 模块系统

实现模块导入/导出功能，包括：
- 模块路径解析（相对路径、包导入）
- 模块缓存
- 循环导入检测
- 导入/导出管理

模块系统工作流程：
1. ModuleResolver 负责解析 import 路径到文件路径
2. ModuleManager 负责加载、类型检查、缓存模块
3. TypeChecker 和 Evaluator 集成导入/导出功能
"""

import os
import sys
from typing import Dict, List, Optional, Set, Any, Tuple
from pathlib import Path

from nova.lexer import Lexer
from nova.parser import Parser
from nova.type_checker import TypeChecker, TypeEnv
from nova.evaluator import Evaluator, Environment
from nova.ast_nodes import (
    Program, ImportDecl, ExportDecl, FnDef, LetBinding, MutBinding, TypeDef, AliasDef,
    Span,
)
from nova.errors import NovaError, RuntimeError_


# ============================================================
# 模块信息
# ============================================================

class ModuleInfo:
    """已加载模块的信息"""

    def __init__(self, file_path: str, source: str, program: Program,
                 type_env: TypeEnv, eval_env: Environment):
        self.file_path = file_path
        self.source = source
        self.program = program
        self.type_env = type_env  # 类型环境
        self.eval_env = eval_env  # 求值环境
        self.exported_names: Set[str] = set()  # 导出的名称
        self.is_loaded = True

    def get_exported_bindings(self) -> Dict[str, Any]:
        """获取所有导出的绑定"""
        result = {}
        for name in self.exported_names:
            try:
                value = self.eval_env.lookup(name)
                result[name] = value
            except NameError:
                pass
        return result

    def get_exported_types(self) -> Dict[str, Any]:
        """获取所有导出的类型"""
        result = {}
        for name in self.exported_names:
            ty = self.type_env.lookup(name)
            if ty is not None:
                result[name] = ty
        return result


# ============================================================
# 模块解析器
# ============================================================

class ModuleResolver:
    """模块路径解析器

    支持的导入形式：
    - 相对路径: import "./local_module.nova"
    - 相对路径: import "../sibling_module.nova"
    - 包导入: import "std/math"
    - 绝对路径: import "/absolute/path/to/module.nova"
    """

    def __init__(self, search_paths: List[str] = None, current_file: str = None):
        """
        Args:
            search_paths: 模块搜索路径列表
            current_file: 当前正在编译的文件路径（用于解析相对导入）
        """
        self.search_paths = search_paths or []
        if current_file:
            # 将当前文件的目录添加到搜索路径（相对路径基准）
            current_dir = os.path.dirname(os.path.abspath(current_file))
            if current_dir not in self.search_paths:
                self.search_paths.insert(0, current_dir)

        # 默认搜索路径
        default_paths = [
            "",  # 当前目录
            "./modules",  # modules 子目录
            "../stdlib",  # 兄弟目录 stdlib
        ]
        for path in default_paths:
            if path not in self.search_paths:
                self.search_paths.append(path)

    def resolve(self, module_path: str) -> Optional[str]:
        """
        解析模块路径为绝对文件路径

        Args:
            module_path: 模块路径（如 "std/math", "./local", "../sibling"）

        Returns:
            绝对文件路径，如果找不到则返回 None
        """
        # 1. 绝对路径
        if os.path.isabs(module_path):
            if module_path.endswith('.nova'):
                return module_path if os.path.isfile(module_path) else None
            return self._try_extensions(module_path)

        # 2. 相对路径
        if module_path.startswith('./') or module_path.startswith('../'):
            # 相对于当前文件目录
            if self.search_paths:
                current_dir = self.search_paths[0]
                abs_path = os.path.abspath(os.path.join(current_dir, module_path))
                return self._try_extensions(abs_path)
            return None

        # 3. 包导入（std/math）
        # 搜索所有搜索路径
        for search_path in self.search_paths:
            abs_path = os.path.abspath(os.path.join(search_path, module_path))
            result = self._try_extensions(abs_path)
            if result:
                return result

        return None

    def _try_extensions(self, base_path: str) -> Optional[str]:
        """尝试不同的文件扩展名"""
        # 首先尝试直接作为文件路径（如果带扩展名）
        if os.path.isfile(base_path):
            return base_path

        # 尝试 .nova 扩展名
        if os.path.isfile(base_path + '.nova'):
            return base_path + '.nova'

        # 尝试作为目录下的 index.nova
        index_path = os.path.join(base_path, 'index.nova')
        if os.path.isfile(index_path):
            return index_path

        return None

    def resolve_package_path(self, module_path: str) -> Optional[str]:
        """
        解析包路径（如 "std/math"）为可能的模块目录

        Returns:
            包的根目录路径，或 None
        """
        # 移除 .nova 扩展名（如果有）
        clean_path = module_path.removesuffix('.nova')

        for search_path in self.search_paths:
            package_path = os.path.abspath(os.path.join(search_path, clean_path))
            if os.path.isdir(package_path):
                return package_path

        return None


# ============================================================
# 模块管理器
# ============================================================

class ModuleManager:
    """模块管理器：负责加载、类型检查、缓存模块"""

    def __init__(self, search_paths: List[str] = None):
        self.search_paths = search_paths or []
        self.modules: Dict[str, ModuleInfo] = {}  # file_path -> ModuleInfo
        self.loading_stack: List[str] = []  # 正在加载的模块（用于循环导入检测）
        self.type_checkers: Dict[str, TypeChecker] = {}  # file_path -> TypeChecker
        self.evaluators: Dict[str, Evaluator] = {}  # file_path -> Evaluator

    def load_module(self, module_path: str, current_file: str = None,
                    check_types: bool = True) -> Optional[ModuleInfo]:
        """
        加载模块

        Args:
            module_path: 模块路径
            current_file: 当前文件路径（用于解析相对导入）
            check_types: 是否进行类型检查

        Returns:
            ModuleInfo，如果加载失败则返回 None
        """
        # 解析路径
        resolver = ModuleResolver(self.search_paths, current_file)
        file_path = resolver.resolve(module_path)

        if not file_path:
            raise RuntimeError_(f"找不到模块: {module_path}")

        # 检查缓存
        if file_path in self.modules:
            return self.modules[file_path]

        # 循环导入检测
        if file_path in self.loading_stack:
            cycle = " -> ".join(self.loading_stack + [file_path])
            raise RuntimeError_(f"循环导入检测: {cycle}")

        # 读取源文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
        except IOError as e:
            raise RuntimeError_(f"无法读取模块文件 '{file_path}': {e}")

        # 添加到加载栈
        self.loading_stack.append(file_path)

        try:
            # 词法分析
            lexer = Lexer(source)
            tokens = lexer.tokenize()

            # 语法分析
            parser = Parser(tokens)
            program = parser.parse()

            # 创建独立的类型检查器和求值器
            type_checker = TypeChecker(source=source)
            evaluator = Evaluator(check_types=check_types)

            # 收集导出的名称
            exported_names = self._collect_exports(program)
            exported_types = self._collect_exported_types(program, type_checker)

            # 类型检查
            if check_types:
                type_checker.check_program(program)

            # 求值（第一遍：注册函数和类型）
            evaluator.eval_program(program)

            # 创建模块信息
            module_info = ModuleInfo(
                file_path=file_path,
                source=source,
                program=program,
                type_env=type_checker.env,
                eval_env=evaluator.env,
            )
            module_info.exported_names = exported_names

            # 缓存模块
            self.modules[file_path] = module_info
            self.type_checkers[file_path] = type_checker
            self.evaluators[file_path] = evaluator

            return module_info

        finally:
            # 从加载栈中移除
            if file_path in self.loading_stack:
                self.loading_stack.remove(file_path)

    def _collect_exports(self, program: Program) -> Set[str]:
        """收集所有导出的名称"""
        exported = set()
        for decl in program.declarations:
            if isinstance(decl, ExportDecl):
                exported.add(decl.name)
            elif isinstance(decl, FnDef):
                # 函数需要显式导出
                pass
            elif isinstance(decl, (LetBinding, MutBinding)):
                # let/mut 绑定需要显式导出
                pass
            elif isinstance(decl, (TypeDef, AliasDef)):
                # 类型定义需要显式导出
                pass
        return exported

    def _collect_exported_types(self, program: Program, type_checker: TypeChecker) -> Set[str]:
        """收集所有导出的类型"""
        exported = set()
        for decl in program.declarations:
            if isinstance(decl, ExportDecl):
                exported.add(decl.name)
        return exported

    def get_module_info(self, file_path: str) -> Optional[ModuleInfo]:
        """获取已加载的模块信息"""
        return self.modules.get(file_path)

    def import_module(self, module_path: str, current_file: str = None,
                     target_env: TypeEnv = None, target_eval_env: Environment = None,
                     check_types: bool = True) -> Dict[str, Any]:
        """
        导入模块并将导出的绑定添加到目标环境

        Args:
            module_path: 模块路径
            current_file: 当前文件路径
            target_env: 目标类型环境（TypeEnv）
            target_eval_env: 目标求值环境（Environment）
            check_types: 是否进行类型检查

        Returns:
            导出的绑定字典 {name: value}
        """
        module_info = self.load_module(module_path, current_file, check_types)
        if not module_info:
            raise RuntimeError_(f"无法加载模块: {module_path}")

        # 将导出的绑定添加到目标环境
        exported_bindings = module_info.get_exported_bindings()

        if target_eval_env:
            for name, value in exported_bindings.items():
                target_eval_env.define(name, value, mutable=False)

        # 将导出的类型添加到目标类型环境
        exported_types = module_info.get_exported_types()

        if target_env:
            for name, ty in exported_types.items():
                target_env.define(name, ty)

        return exported_bindings

    def is_module_loaded(self, file_path: str) -> bool:
        """检查模块是否已加载"""
        return file_path in self.modules

    def clear_cache(self):
        """清除所有模块缓存"""
        self.modules.clear()
        self.loading_stack.clear()
        self.type_checkers.clear()
        self.evaluators.clear()


# ============================================================
# 全局模块管理器实例
# ============================================================

# 默认的模块搜索路径
_DEFAULT_SEARCH_PATHS = [
    "",  # 当前目录
    "./modules",  # modules 子目录
    "./stdlib",  # stdlib 目录
    "../stdlib",  # 父目录的 stdlib
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "runtime/std_impl"),
]

_global_module_manager = ModuleManager(_DEFAULT_SEARCH_PATHS)


def get_global_module_manager() -> ModuleManager:
    """获取全局模块管理器实例"""
    return _global_module_manager


def import_module(module_path: str, current_file: str = None,
                 target_env: TypeEnv = None, target_eval_env: Environment = None,
                 check_types: bool = True) -> Dict[str, Any]:
    """
    使用全局模块管理器导入模块

    Args:
        module_path: 模块路径
        current_file: 当前文件路径
        target_env: 目标类型环境
        target_eval_env: 目标求值环境
        check_types: 是否进行类型检查

    Returns:
        导出的绑定字典
    """
    manager = get_global_module_manager()
    return manager.import_module(
        module_path, current_file, target_env, target_eval_env, check_types
    )


def clear_module_cache():
    """清除全局模块缓存"""
    get_global_module_manager().clear_cache()