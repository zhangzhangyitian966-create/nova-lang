#!/usr/bin/env python3
"""
Nova 深度自动审查系统 v2.0
Level 1: 深度审查系统 - 发现问题

执行 Nova 编程语言项目的全面代码审查，包括：
- AST 级代码质量分析（20+ 检测项）
- 架构审查（模块依赖、循环依赖、耦合度）
- 测试分析（pytest 测试套件）
- 复杂度分析（圈复杂度）
- 报告生成与 Git 提交
"""

import os
import sys
import ast
import re
import json
import subprocess
import traceback
import datetime
from collections import defaultdict
from pathlib import Path

# ============================================================
# 配置
# ============================================================

PROJECT_DIR = Path("/workspace/nova")
SCRIPTS_DIR = PROJECT_DIR / "scripts"
REPORT_FILE = PROJECT_DIR / "AUTO_REVIEW_LOG.md"

GIT_TOKEN = os.environ.get("NOVA_GIT_TOKEN", "")
GIT_USER = os.environ.get("NOVA_GIT_USER", "zhangzhangyitian966-create")
GIT_REPO = os.environ.get("NOVA_GIT_REPO", "nova-lang.git")
GIT_EMAIL = "auto-review@nova-lang.dev"
GIT_NAME = "Nova Auto Review"

# 排除目录
EXCLUDE_DIRS = {".git", "__pycache__", "scripts", "node_modules", "build", "dist"}

# 严重级别
SEV_CRITICAL = "CRITICAL"
SEV_HIGH = "HIGH"
SEV_MEDIUM = "MEDIUM"
SEV_LOW = "LOW"

# 复杂度阈值
CC_HIGH_THRESHOLD = 15
FUNCTION_LENGTH_THRESHOLD = 100
CLASS_METHODS_THRESHOLD = 20
GOD_MODULE_OUTDEGREE = 10

# 测试超时（秒）
TEST_TIMEOUT = 120


# ============================================================
# 工具函数
# ============================================================


def log(msg, level="INFO"):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}", flush=True)


def get_python_files(base_dir):
    """获取所有 Python 文件，排除指定目录"""
    files = []
    for root, dirs, filenames in os.walk(base_dir):
        # 排除目录
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in filenames:
            if f.endswith(".py"):
                files.append(Path(root) / f)
    return sorted(files)


def read_file(filepath):
    """安全读取文件"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def count_lines(content):
    """统计行数"""
    if not content:
        return 0
    return len(content.splitlines())


# ============================================================
# 阶段 1: 项目初始化
# ============================================================


def phase1_init():
    """检查项目是否存在，不存在则克隆"""
    log("=" * 60)
    log("阶段 1: 项目初始化")
    log("=" * 60)

    if PROJECT_DIR.exists() and (PROJECT_DIR / ".git").exists():
        log(f"项目已存在: {PROJECT_DIR}")
        return True

    log("项目不存在，开始克隆...")

    # 配置 git credential
    if GIT_TOKEN:
        credential_file = Path("/root/.git-credentials")
        cred_content = f"https://{GIT_USER}:{GIT_TOKEN}@github.com"
        try:
            credential_file.write_text(cred_content + "\n")
            os.chmod(credential_file, 0o600)
            subprocess.run(
                ["git", "config", "--global", "credential.helper", "store"],
                check=False,
                capture_output=True,
            )
            log("Git credential 已配置")
        except Exception as e:
            log(f"配置 credential 失败: {e}", "WARN")

    # 构建 clone URL
    if GIT_TOKEN:
        repo_url = f"https://{GIT_USER}:{GIT_TOKEN}@github.com/{GIT_USER}/{GIT_REPO}"
    else:
        repo_url = f"https://github.com/{GIT_USER}/{GIT_REPO}"

    try:
        result = subprocess.run(
            ["git", "clone", repo_url, str(PROJECT_DIR)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            log(f"克隆失败: {result.stderr}", "ERROR")
            return False
        log("项目克隆成功")
        return True
    except subprocess.TimeoutExpired:
        log("克隆超时", "ERROR")
        return False
    except Exception as e:
        log(f"克隆异常: {e}", "ERROR")
        return False


# ============================================================
# 阶段 2: 同步远程
# ============================================================


def phase2_sync():
    """Git pull 同步最新代码"""
    log("=" * 60)
    log("阶段 2: 同步远程")
    log("=" * 60)

    try:
        result = subprocess.run(
            ["git", "pull", "--rebase", "origin", "main"],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            log(f"git pull 失败: {result.stderr}", "WARN")
            log("将使用本地代码继续审查", "WARN")
        else:
            log("代码已同步到最新")
            if result.stdout.strip():
                log(result.stdout.strip())
    except subprocess.TimeoutExpired:
        log("git pull 超时，使用本地代码", "WARN")
    except Exception as e:
        log(f"git pull 异常: {e}", "WARN")

    return True


# ============================================================
# 阶段 3: AST 级代码质量分析
# ============================================================


class CodeIssue:
    """代码问题"""

    def __init__(self, severity, issue_type, file, line, message, snippet=""):
        self.severity = severity
        self.issue_type = issue_type
        self.file = str(file)
        self.line = line
        self.message = message
        self.snippet = snippet

    def to_dict(self):
        return {
            "severity": self.severity,
            "type": self.issue_type,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "snippet": self.snippet,
        }


class ASTAnalyzer(ast.NodeVisitor):
    """AST 分析器"""

    def __init__(self, filepath, source_lines):
        self.filepath = filepath
        self.source_lines = source_lines
        self.issues = []
        self.imports = set()  # 模块级 import
        self.function_count = 0
        self.class_count = 0
        self.function_complexities = {}  # func_name -> complexity
        self.current_function = None
        self.current_class = None
        self.class_method_count = defaultdict(int)

    def add_issue(self, severity, issue_type, line, message):
        snippet = ""
        if 0 < line <= len(self.source_lines):
            snippet = self.source_lines[line - 1].strip()
        rel_path = (
            self.filepath.relative_to(PROJECT_DIR)
            if self.filepath.is_absolute()
            else self.filepath
        )
        self.issues.append(
            CodeIssue(severity, issue_type, rel_path, line, message, snippet)
        )

    def get_line_snippet(self, lineno):
        if 0 < lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1].strip()
        return ""

    # ---- Import 处理 ----

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.add(node.module)
        self.generic_visit(node)

    # ---- Class / Function ----

    def visit_ClassDef(self, node):
        self.class_count += 1
        self.current_class = node.name
        method_count = 0
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_count += 1
        self.class_method_count[node.name] = method_count

        if method_count > CLASS_METHODS_THRESHOLD:
            self.add_issue(
                SEV_MEDIUM,
                "class_too_large",
                node.lineno,
                f"类 '{node.name}' 方法过多 ({method_count} > {CLASS_METHODS_THRESHOLD})",
            )

        # 检查 docstring
        if not ast.get_docstring(node):
            self.add_issue(
                SEV_LOW, "no_docstring", node.lineno, f"类 '{node.name}' 缺少文档字符串"
            )

        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, node):
        self._analyze_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._analyze_function(node)

    def _analyze_function(self, node):
        self.function_count += 1
        self.current_function = node.name

        # 计算函数长度
        func_lines = node.end_lineno - node.lineno + 1 if node.end_lineno else 0
        if func_lines > FUNCTION_LENGTH_THRESHOLD:
            self.add_issue(
                SEV_MEDIUM,
                "function_too_long",
                node.lineno,
                f"函数 '{node.name}' 过长 ({func_lines} 行 > {FUNCTION_LENGTH_THRESHOLD} 行)",
            )

        # 计算圈复杂度
        cc = self._calc_cyclomatic_complexity(node)
        full_name = (
            f"{self.current_class}.{node.name}" if self.current_class else node.name
        )
        self.function_complexities[full_name] = cc

        if cc > CC_HIGH_THRESHOLD:
            self.add_issue(
                SEV_MEDIUM,
                "cyclomatic_complexity",
                node.lineno,
                f"函数 '{full_name}' 圈复杂度过高 (CC={cc} > {CC_HIGH_THRESHOLD})",
            )

        # 检查 docstring (排除 __init__ 等特殊方法的严格要求？这里统一检查)
        if not ast.get_docstring(node):
            self.add_issue(
                SEV_LOW,
                "no_docstring",
                node.lineno,
                f"函数 '{full_name}' 缺少文档字符串",
            )

        # 检查命名规范
        if self.current_class is None:  # 顶层函数
            if not re.match(r"^[a-z_][a-z0-9_]*$", node.name):
                self.add_issue(
                    SEV_LOW,
                    "inconsistent_naming",
                    node.lineno,
                    f"函数名 '{node.name}' 不符合 snake_case 规范",
                )

        self.generic_visit(node)
        self.current_function = None

    def _calc_cyclomatic_complexity(self, node):
        """计算圈复杂度"""
        cc = 1  # 基础复杂度
        for child in ast.walk(node):
            if isinstance(
                child,
                (ast.If, ast.For, ast.While, ast.With, ast.AsyncFor, ast.AsyncWith),
            ):
                cc += 1
            elif isinstance(child, ast.ExceptHandler):
                cc += 1
            elif isinstance(child, ast.BoolOp):
                # and/or 操作符，每个操作符 +1
                # BoolOp 的 op 是一个，values 是多个，数量是 len(values)-1
                cc += len(child.values) - 1
        return cc

    # ---- 异常处理 ----

    def visit_ExceptHandler(self, node):
        if node.type is None:
            # 裸 except
            self.add_issue(
                SEV_HIGH,
                "bare_except",
                node.lineno,
                "裸 except 捕获所有异常，可能隐藏错误",
            )
        elif isinstance(node.type, ast.Name):
            if node.type.id == "Exception":
                self.add_issue(
                    SEV_MEDIUM,
                    "too_broad_exception",
                    node.lineno,
                    "过于宽泛的 except Exception，建议捕获具体异常类型",
                )
            elif node.type.id == "BaseException":
                self.add_issue(
                    SEV_HIGH,
                    "too_broad_exception",
                    node.lineno,
                    "except BaseException 过于宽泛，可能捕获系统级异常",
                )
        self.generic_visit(node)

    # ---- 调用检测 ----

    def visit_Call(self, node):
        func_name = self._get_call_name(node)

        if func_name == "eval":
            self.add_issue(
                SEV_CRITICAL, "eval_usage", node.lineno, "使用 eval() 存在代码注入风险"
            )
        elif func_name == "exec":
            self.add_issue(
                SEV_CRITICAL, "exec_usage", node.lineno, "使用 exec() 存在代码注入风险"
            )
        elif func_name in (
            "pickle.load",
            "pickle.loads",
            "marshal.load",
            "marshal.loads",
        ):
            self.add_issue(
                SEV_HIGH,
                "unsafe_deserialization",
                node.lineno,
                f"使用 {func_name}() 存在不安全反序列化风险",
            )
        elif func_name == "subprocess.call" or func_name.endswith(".Popen"):
            # 检查 shell=True
            for kw in node.keywords:
                if (
                    kw.arg == "shell"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value is True
                ):
                    self.add_issue(
                        SEV_HIGH,
                        "subprocess_shell_true",
                        node.lineno,
                        "subprocess 使用 shell=True 存在命令注入风险",
                    )
                    break

        self.generic_visit(node)

    def _get_call_name(self, node):
        """获取调用的函数名"""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return ""

    # ---- 嵌套循环检测 ----

    def visit_For(self, node):
        depth = self._count_loop_depth(node)
        if depth >= 4:
            self.add_issue(
                SEV_MEDIUM,
                "nested_loop",
                node.lineno,
                f"深层嵌套循环 (深度={depth})，建议重构",
            )
        self.generic_visit(node)

    def visit_While(self, node):
        depth = self._count_loop_depth(node)
        if depth >= 4:
            self.add_issue(
                SEV_MEDIUM,
                "nested_loop",
                node.lineno,
                f"深层嵌套循环 (深度={depth})，建议重构",
            )
        self.generic_visit(node)

    def _count_loop_depth(self, node, current_depth=0):
        """计算循环嵌套深度"""
        max_depth = current_depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.For, ast.While, ast.AsyncFor)):
                depth = self._count_loop_depth(child, current_depth + 1)
                max_depth = max(max_depth, depth)
            else:
                depth = self._count_loop_depth(child, current_depth)
                max_depth = max(max_depth, depth)
        return max_depth


def line_level_analysis(filepath, source_lines):
    """行级代码分析（补充 AST 分析）"""
    issues = []
    rel_path = filepath.relative_to(PROJECT_DIR) if filepath.is_absolute() else filepath

    for i, line in enumerate(source_lines, 1):
        stripped = line.strip()

        # 跳过空行和注释
        if not stripped or stripped.startswith("#"):
            continue

        # TODO/FIXME/XXX/HACK 检测
        if re.search(r"#\s*(TODO|FIXME|XXX|HACK|BUG|OPTIMIZE)", line, re.IGNORECASE):
            match = re.search(
                r"(TODO|FIXME|XXX|HACK|BUG|OPTIMIZE)[^#\n]*", line, re.IGNORECASE
            )
            msg = match.group(0).strip() if match else "遗留注释"
            issues.append(
                CodeIssue(
                    SEV_LOW, "todo_fixme", rel_path, i, f"遗留注释: {msg}", stripped
                )
            )

        # print 调试语句（排除明确的生产代码模式）
        if re.match(r"^\s*print\s*\(", line) and "print(" in line:
            # 简单启发：排除有注释说明的、明显生产用的
            if not re.search(
                r"#.*(production|intentional|required)", line, re.IGNORECASE
            ):
                issues.append(
                    CodeIssue(
                        SEV_LOW,
                        "print_debug",
                        rel_path,
                        i,
                        "调试用 print 语句，建议使用日志系统",
                        stripped,
                    )
                )

        # 魔法数字（简单启发式）
        # 跳过常见的：0, 1, -1, 2, 10, 100, 1000, 0.5, 24, 60, 等
        if re.search(r"\b(\d+)\b", stripped):
            nums = re.findall(r"\b(\d+)\b", stripped)
            for num_str in nums:
                num = int(num_str)
                # 排除常见的"非魔法"数字
                common = {0, 1, 2, 3, 4, 5, 10, 24, 60, 100, 1000, 1024, 3600, 86400}
                if num not in common and len(str(num)) <= 5:
                    # 确保是在代码中而不是注释或字符串中
                    # 简化：检查行不只是 import/注释
                    if not stripped.startswith(("import ", "from ", "#", '"', "'")):
                        # 只报告每行第一个魔法数字
                        issues.append(
                            CodeIssue(
                                SEV_LOW,
                                "magic_number",
                                rel_path,
                                i,
                                f"魔法数字 {num_str}，建议定义为命名常量",
                                stripped,
                            )
                        )
                        break

        # sys.path hack
        if re.search(r"sys\.path\.(append|insert)", line):
            issues.append(
                CodeIssue(
                    SEV_HIGH,
                    "sys_path_hack",
                    rel_path,
                    i,
                    "sys.path 修改，非标准导入方式",
                    stripped,
                )
            )

    return issues


def phase3_ast_analysis():
    """AST 级代码质量分析"""
    log("=" * 60)
    log("阶段 3: AST 级代码质量分析")
    log("=" * 60)

    py_files = get_python_files(PROJECT_DIR)
    log(f"扫描 {len(py_files)} 个 Python 文件")

    all_issues = []
    total_lines = 0
    total_functions = 0
    total_classes = 0
    all_complexities = {}  # file -> {func_name: cc}

    for filepath in py_files:
        content = read_file(filepath)
        if not content:
            continue

        source_lines = content.splitlines()
        total_lines += len(source_lines)

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            log(f"解析失败 {filepath.name}: {e}", "WARN")
            continue

        analyzer = ASTAnalyzer(filepath, source_lines)
        analyzer.visit(tree)

        all_issues.extend(analyzer.issues)
        total_functions += analyzer.function_count
        total_classes += analyzer.class_count

        rel_path = str(filepath.relative_to(PROJECT_DIR))
        all_complexities[rel_path] = analyzer.function_complexities

        # 行级分析
        line_issues = line_level_analysis(filepath, source_lines)
        all_issues.extend(line_issues)

    # 未使用导入检测（单独做，因为需要跨函数分析）
    for filepath in py_files:
        content = read_file(filepath)
        if not content:
            continue
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue

        # 收集所有 import 的名字
        imported_names = {}  # name -> lineno
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name.split(".")[0]
                    imported_names[name] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    if name != "*":
                        imported_names[name] = node.lineno

        if not imported_names:
            continue

        # 收集所有使用的名字（简单方法：扫描所有 Name 节点）
        used_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used_names.add(node.id)
            # 也检查属性访问的第一个名字
            elif isinstance(node, ast.Attribute):
                current = node
                while isinstance(current, ast.Attribute):
                    current = current.value
                if isinstance(current, ast.Name):
                    used_names.add(current.id)
            # 字符串注解中的名字
            elif isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                # 检查装饰器
                for dec in node.decorator_list:
                    for n in ast.walk(dec):
                        if isinstance(n, ast.Name):
                            used_names.add(n.id)

        rel_path = filepath.relative_to(PROJECT_DIR)
        for name, lineno in imported_names.items():
            if name not in used_names:
                all_issues.append(
                    CodeIssue(
                        SEV_MEDIUM,
                        "unused_import",
                        rel_path,
                        lineno,
                        f"未使用的导入: '{name}'",
                        (
                            source_lines[lineno - 1].strip()
                            if lineno <= len(source_lines)
                            else ""
                        ),
                    )
                )

    # 统计
    severity_counts = defaultdict(int)
    type_counts = defaultdict(int)
    for issue in all_issues:
        severity_counts[issue.severity] += 1
        type_counts[issue.issue_type] += 1

    log(f"发现 {len(all_issues)} 个问题")
    log(f"  CRITICAL: {severity_counts[SEV_CRITICAL]}")
    log(f"  HIGH:     {severity_counts[SEV_HIGH]}")
    log(f"  MEDIUM:   {severity_counts[SEV_MEDIUM]}")
    log(f"  LOW:      {severity_counts[SEV_LOW]}")
    log(f"文件数: {len(py_files)}, 总行数: {total_lines}")
    log(f"函数数: {total_functions}, 类数: {total_classes}")

    return {
        "files": len(py_files),
        "total_lines": total_lines,
        "total_functions": total_functions,
        "total_classes": total_classes,
        "issues": [i.to_dict() for i in all_issues],
        "severity_counts": dict(severity_counts),
        "type_counts": dict(type_counts),
        "complexities": all_complexities,
    }


# ============================================================
# 阶段 4: 架构审查
# ============================================================


def phase4_architecture(ast_result):
    """架构审查"""
    log("=" * 60)
    log("阶段 4: 架构审查")
    log("=" * 60)

    py_files = get_python_files(PROJECT_DIR)

    # 构建模块依赖图
    # 模块名 -> 依赖的模块名集合
    dependency_graph = defaultdict(set)
    module_files = {}  # 模块名 -> 文件路径

    for filepath in py_files:
        content = read_file(filepath)
        if not content:
            continue

        rel_path = filepath.relative_to(PROJECT_DIR)
        # 转换为模块名
        parts = list(rel_path.parts)
        if parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]  # 去掉 .py
        if parts[-1] == "__init__":
            parts = parts[:-1]  # __init__.py 对应包本身
        module_name = ".".join(parts)
        module_files[module_name] = str(rel_path)

        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    dep = alias.name
                    # 只关注项目内部模块（以 nova 开头或匹配已知模块名）
                    if dep.startswith("nova") or dep in module_files:
                        dependency_graph[module_name].add(dep)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    dep = node.module
                    # 相对导入处理
                    if node.level > 0:
                        # 简化：相对导入转换为绝对导入
                        base_parts = module_name.split(".")
                        if node.level >= len(base_parts):
                            base = []
                        else:
                            base = base_parts[: -node.level]
                        if dep:
                            full_dep = ".".join(base + [dep]) if base else dep
                        else:
                            full_dep = ".".join(base) if base else ""
                        if full_dep:
                            dependency_graph[module_name].add(full_dep)
                    else:
                        if dep.startswith("nova") or dep in module_files:
                            dependency_graph[module_name].add(dep)

    # 过滤：只保留项目内部模块
    all_modules = set(module_files.keys())
    filtered_graph = defaultdict(set)
    for mod, deps in dependency_graph.items():
        if mod in all_modules:
            for dep in deps:
                if dep in all_modules and dep != mod:
                    filtered_graph[mod].add(dep)

    # 检测循环依赖（DFS）
    def find_cyclic_dependencies(graph):
        visited = set()
        rec_stack = set()
        cycles = []
        path = []

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # 找到循环
                    idx = path.index(neighbor)
                    cycle = path[idx:] + [neighbor]
                    cycles.append(cycle)

            path.pop()
            rec_stack.remove(node)

        for node in graph:
            if node not in visited:
                dfs(node)

        # 去重（循环可能从不同起点被发现多次）
        unique_cycles = []
        seen = set()
        for cycle in cycles:
            # 规范化：旋转到最小元素开头
            core = cycle[:-1]  # 去掉重复的末尾
            if not core:
                continue
            min_idx = core.index(min(core))
            normalized = tuple(core[min_idx:] + core[:min_idx])
            if normalized not in seen:
                seen.add(normalized)
                unique_cycles.append(list(normalized) + [normalized[0]])

        return unique_cycles

    cycles = find_cyclic_dependencies(filtered_graph)

    # 计算耦合度
    in_degree = defaultdict(int)
    out_degree = defaultdict(int)

    for mod in all_modules:
        out_degree[mod] = len(filtered_graph.get(mod, set()))
        in_degree[mod] = 0

    for mod, deps in filtered_graph.items():
        for dep in deps:
            in_degree[dep] += 1

    # 上帝模块（出度 > 阈值）
    god_modules = [
        (mod, out_degree[mod])
        for mod in all_modules
        if out_degree[mod] > GOD_MODULE_OUTDEGREE
    ]
    god_modules.sort(key=lambda x: -x[1])

    # 高被依赖模块（入度高）
    top_indegree = sorted(in_degree.items(), key=lambda x: -x[1])[:10]
    top_outdegree = sorted(out_degree.items(), key=lambda x: -x[1])[:10]

    # 平均依赖数
    total_deps = sum(out_degree.values())
    avg_deps = total_deps / len(all_modules) if all_modules else 0

    # sys.path hack 统计
    sys_path_hacks = [i for i in ast_result["issues"] if i["type"] == "sys_path_hack"]

    # 代码量分布（按目录）
    dir_lines = defaultdict(int)
    dir_files = defaultdict(int)
    for filepath in py_files:
        content = read_file(filepath)
        lines = count_lines(content)
        rel_path = filepath.relative_to(PROJECT_DIR)
        if len(rel_path.parts) > 1:
            top_dir = rel_path.parts[0]
        else:
            top_dir = "(root)"
        dir_lines[top_dir] += lines
        dir_files[top_dir] += 1

    log(f"模块总数: {len(all_modules)}")
    log(f"循环依赖: {len(cycles)} 个")
    if cycles:
        for i, cycle in enumerate(cycles[:5], 1):
            log(f"  循环 {i}: {' -> '.join(cycle)}")
    log(f"平均依赖数: {avg_deps:.2f}")
    log(f"上帝模块: {len(god_modules)} 个")
    for mod, deg in god_modules[:5]:
        log(f"  {mod}: 出度={deg}")

    return {
        "total_modules": len(all_modules),
        "cycles": cycles,
        "in_degree": dict(in_degree),
        "out_degree": dict(out_degree),
        "avg_deps": round(avg_deps, 2),
        "god_modules": god_modules,
        "top_indegree": top_indegree,
        "top_outdegree": top_outdegree,
        "sys_path_hacks": len(sys_path_hacks),
        "dir_distribution": {
            d: {"lines": l, "files": dir_files[d]}
            for d, l in sorted(dir_lines.items(), key=lambda x: -x[1])
        },
        "module_files": module_files,
        "dependency_graph": {k: list(v) for k, v in filtered_graph.items()},
    }


# ============================================================
# 阶段 5: 测试分析
# ============================================================


def phase5_testing():
    """运行 pytest 测试分析"""
    log("=" * 60)
    log("阶段 5: 测试分析")
    log("=" * 60)

    # 查找测试文件
    test_files = []
    for pattern in ["test_*.py", "*_test.py"]:
        test_files.extend(PROJECT_DIR.rglob(pattern))

    # 排除 scripts 等目录
    test_files = [
        f for f in test_files if not any(part in EXCLUDE_DIRS for part in f.parts)
    ]

    if not test_files:
        log("未找到测试文件，跳过测试分析", "WARN")
        return {"status": "no_tests", "tests_found": 0}

    log(f"找到 {len(test_files)} 个测试文件")

    try:
        # 确保 nova 包可用（安装开发模式）
        install_cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-e",
            str(PROJECT_DIR),
            "--break-system-packages",
            "-q",
        ]
        subprocess.run(
            install_cmd,
            capture_output=True,
            timeout=60,
        )

        # 先检查 pytest 是否可用
        check = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if check.returncode != 0:
            log("pytest 未安装，尝试安装...", "WARN")
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "pytest",
                    "pytest-timeout",
                    "--break-system-packages",
                    "-q",
                ],
                capture_output=True,
                timeout=60,
            )

        # 用 JSON 格式输出以便解析
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(PROJECT_DIR),
            "-v",
            "--tb=short",
            "-p",
            "no:cacheprovider",
            "--json-report",
            "--json-report-file=/tmp/pytest_report.json",
        ]

        # 先装 pytest-json-report
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "pytest-json-report",
                "--break-system-packages",
                "-q",
            ],
            capture_output=True,
            timeout=60,
        )

        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=TEST_TIMEOUT,
        )

        # 解析 JSON 报告
        report_data = {}
        report_file = Path("/tmp/pytest_report.json")
        if report_file.exists():
            try:
                report_data = json.loads(report_file.read_text())
            except json.JSONDecodeError:
                pass

        if report_data:
            summary = report_data.get("summary", {})
            passed = summary.get("passed", 0)
            failed = summary.get("failed", 0)
            errors = summary.get("error", 0)
            skipped = summary.get("skipped", 0)
            total = summary.get("total", 0)
            duration = summary.get("duration", 0)
            pass_rate = (passed / total * 100) if total > 0 else 0

            # 失败测试清单
            failed_tests = []
            for test in report_data.get("tests", []):
                if test.get("outcome") in ("failed", "error"):
                    failed_tests.append(
                        {
                            "name": test.get("nodeid", ""),
                            "outcome": test.get("outcome", ""),
                            "message": (
                                test.get("call", {}).get("longrepr", "")
                                or test.get("setup", {}).get("longrepr", "")
                            )[:300],
                        }
                    )

            log(f"测试结果: {passed}/{total} 通过 ({pass_rate:.1f}%)")
            log(f"  通过: {passed}, 失败: {failed}, 错误: {errors}, 跳过: {skipped}")
            log(f"  耗时: {duration:.2f}s")

            return {
                "status": "completed",
                "total": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "skipped": skipped,
                "pass_rate": round(pass_rate, 1),
                "duration": round(duration, 2),
                "failed_tests": failed_tests[:5],
            }
        else:
            # 用 stdout 简单解析
            lines = result.stdout.strip().splitlines()
            summary_line = ""
            for line in reversed(lines):
                if "passed" in line or "failed" in line:
                    summary_line = line
                    break

            log(f"测试完成: {summary_line}")
            return {"status": "completed", "raw_output": result.stdout[-2000:]}

    except subprocess.TimeoutExpired:
        log(f"测试运行超时（>{TEST_TIMEOUT}s）", "WARN")
        return {"status": "timeout", "timeout": TEST_TIMEOUT}
    except Exception as e:
        log(f"测试运行异常: {e}", "WARN")
        log(traceback.format_exc(), "DEBUG")
        return {"status": "error", "error": str(e)}


# ============================================================
# 阶段 6: 复杂度分析
# ============================================================


def phase6_complexity(ast_result):
    """复杂度分析"""
    log("=" * 60)
    log("阶段 6: 复杂度分析")
    log("=" * 60)

    all_funcs = []  # (file, func_name, cc)

    for filepath, funcs in ast_result.get("complexities", {}).items():
        for func_name, cc in funcs.items():
            all_funcs.append((filepath, func_name, cc))

    # 按复杂度排序
    all_funcs.sort(key=lambda x: -x[2])

    top10 = all_funcs[:10]

    # 统计分布
    cc_distribution = defaultdict(int)
    for _, _, cc in all_funcs:
        if cc <= 5:
            cc_distribution["1-5 (简单)"] += 1
        elif cc <= 10:
            cc_distribution["6-10 (中等)"] += 1
        elif cc <= 15:
            cc_distribution["11-15 (复杂)"] += 1
        elif cc <= 25:
            cc_distribution["16-25 (高复杂)"] += 1
        else:
            cc_distribution["25+ (极复杂)"] += 1

    log(f"总函数数: {len(all_funcs)}")
    log(
        f"平均复杂度: {sum(cc for _,_,cc in all_funcs)/len(all_funcs):.2f}"
        if all_funcs
        else "无函数"
    )
    log("Top 10 最复杂函数:")
    for i, (fpath, fname, cc) in enumerate(top10, 1):
        log(f"  {i}. {fname} (CC={cc}) - {fpath}")

    return {
        "total_functions": len(all_funcs),
        "avg_complexity": (
            round(sum(cc for _, _, cc in all_funcs) / len(all_funcs), 2)
            if all_funcs
            else 0
        ),
        "max_complexity": all_funcs[0][2] if all_funcs else 0,
        "top10": [{"file": f, "function": n, "complexity": c} for f, n, c in top10],
        "distribution": dict(cc_distribution),
    }


# ============================================================
# 阶段 7: 报告生成与提交
# ============================================================


def determine_review_round():
    """确定当前是第几轮审查"""
    if not REPORT_FILE.exists():
        return 1
    content = REPORT_FILE.read_text()
    # 数分隔符
    count = content.count("---")
    return count + 1


def generate_report(
    ast_result, arch_result, test_result, complexity_result, review_round
):
    """生成 Markdown 审查报告"""
    log("=" * 60)
    log("阶段 7: 报告生成")
    log("=" * 60)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 计算问题总数
    total_issues = len(ast_result["issues"])
    sev_counts = ast_result["severity_counts"]

    # 按严重级别分组问题
    critical_issues = [i for i in ast_result["issues"] if i["severity"] == SEV_CRITICAL]
    high_issues = [i for i in ast_result["issues"] if i["severity"] == SEV_HIGH]
    medium_issues = [i for i in ast_result["issues"] if i["severity"] == SEV_MEDIUM]
    low_issues = [i for i in ast_result["issues"] if i["severity"] == SEV_LOW]

    # 生成报告
    lines = []
    lines.append("---")
    lines.append("")
    lines.append(f"# 第 {review_round} 轮 Nova 深度审查报告 (v2.0)")
    lines.append("")
    lines.append(f"> 生成时间: {now}")
    lines.append(f"> 审查版本: v0.3.0")
    lines.append("")

    # ---- 审查概览 ----
    lines.append("## 1. 审查概览")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 扫描文件数 | {ast_result['files']} |")
    lines.append(f"| 代码行数 | {ast_result['total_lines']:,} |")
    lines.append(f"| 函数总数 | {ast_result['total_functions']} |")
    lines.append(f"| 类总数 | {ast_result['total_classes']} |")
    lines.append(f"| 发现问题数 | **{total_issues}** |")
    lines.append(f"| CRITICAL | {sev_counts.get(SEV_CRITICAL, 0)} |")
    lines.append(f"| HIGH | {sev_counts.get(SEV_HIGH, 0)} |")
    lines.append(f"| MEDIUM | {sev_counts.get(SEV_MEDIUM, 0)} |")
    lines.append(f"| LOW | {sev_counts.get(SEV_LOW, 0)} |")
    lines.append("")

    # 严重程度分布可视化（文本）
    lines.append("### 严重程度分布")
    lines.append("")
    for sev, label, color in [
        (SEV_CRITICAL, "CRITICAL", "🔴"),
        (SEV_HIGH, "HIGH", "🟠"),
        (SEV_MEDIUM, "MEDIUM", "🟡"),
        (SEV_LOW, "LOW", "🟢"),
    ]:
        count = sev_counts.get(sev, 0)
        bar_len = int(count / max(total_issues, 1) * 40)
        lines.append(f"- {color} **{label}**: {count} 个")
    lines.append("")

    # ---- 代码质量审查 ----
    lines.append("## 2. 代码质量审查")
    lines.append("")

    # 问题类型分布
    lines.append("### 2.1 问题类型分布")
    lines.append("")
    type_counts = ast_result["type_counts"]
    sorted_types = sorted(type_counts.items(), key=lambda x: -x[1])
    lines.append("| 问题类型 | 数量 | 严重级别 |")
    lines.append("|----------|------|----------|")
    # 确定每个类型的最高严重级别
    type_max_sev = {}
    for issue in ast_result["issues"]:
        t = issue["type"]
        s = issue["severity"]
        sev_order = {SEV_CRITICAL: 0, SEV_HIGH: 1, SEV_MEDIUM: 2, SEV_LOW: 3}
        if t not in type_max_sev or sev_order[s] < sev_order[type_max_sev[t]]:
            type_max_sev[t] = s
    for t, c in sorted_types:
        lines.append(f"| {t} | {c} | {type_max_sev.get(t, SEV_LOW)} |")
    lines.append("")

    # 高优先级问题
    lines.append("### 2.2 高优先级问题 (CRITICAL + HIGH)")
    lines.append("")
    high_priority = critical_issues + high_issues
    if high_priority:
        for i, issue in enumerate(high_priority[:20], 1):
            lines.append(f"{i}. **[{issue['severity']}] {issue['type']}**")
            lines.append(f"   - 文件: `{issue['file']}:{issue['line']}`")
            lines.append(f"   - 描述: {issue['message']}")
            if issue.get("snippet"):
                lines.append(f"   - 代码: `{issue['snippet'][:100]}`")
            lines.append("")
        if len(high_priority) > 20:
            lines.append(f"> 还有 {len(high_priority) - 20} 个高优先级问题未列出")
            lines.append("")
    else:
        lines.append("✅ 无高优先级问题")
        lines.append("")

    # 各模块问题统计
    lines.append("### 2.3 各模块问题统计 (Top 10)")
    lines.append("")
    module_issues = defaultdict(int)
    for issue in ast_result["issues"]:
        # 取顶层目录作为模块
        fpath = issue["file"]
        parts = fpath.split("/")
        module = parts[0] if len(parts) > 1 else "(root)"
        module_issues[module] += 1
    sorted_modules = sorted(module_issues.items(), key=lambda x: -x[1])[:10]
    lines.append("| 模块 | 问题数 |")
    lines.append("|------|--------|")
    for mod, count in sorted_modules:
        lines.append(f"| {mod} | {count} |")
    lines.append("")

    # ---- 架构审查 ----
    lines.append("## 3. 架构审查")
    lines.append("")
    lines.append("### 3.1 模块概览")
    lines.append("")
    lines.append(f"- 模块总数: **{arch_result['total_modules']}**")
    lines.append(f"- 平均依赖数: **{arch_result['avg_deps']}**")
    lines.append(f"- 循环依赖: **{len(arch_result['cycles'])}** 个")
    lines.append(f"- sys.path hack: **{arch_result['sys_path_hacks']}** 处")
    lines.append("")

    # 循环依赖
    if arch_result["cycles"]:
        lines.append("### 3.2 循环依赖")
        lines.append("")
        for i, cycle in enumerate(arch_result["cycles"][:10], 1):
            lines.append(f"{i}. `{' → '.join(cycle)}`")
        if len(arch_result["cycles"]) > 10:
            lines.append(f"> 还有 {len(arch_result['cycles']) - 10} 个循环依赖")
        lines.append("")
    else:
        lines.append("### 3.2 循环依赖")
        lines.append("")
        lines.append("✅ 未发现循环依赖")
        lines.append("")

    # 耦合度分析
    lines.append("### 3.3 耦合度分析")
    lines.append("")
    lines.append("#### 高被依赖模块 (入度 Top 10)")
    lines.append("")
    lines.append("| 模块 | 入度 (被依赖数) |")
    lines.append("|------|----------------|")
    for mod, deg in arch_result["top_indegree"][:10]:
        lines.append(f"| {mod} | {deg} |")
    lines.append("")

    lines.append("#### 高依赖模块 (出度 Top 10)")
    lines.append("")
    lines.append("| 模块 | 出度 (依赖数) |")
    lines.append("|------|--------------|")
    for mod, deg in arch_result["top_outdegree"][:10]:
        lines.append(f"| {mod} | {deg} |")
    lines.append("")

    # 上帝模块
    if arch_result["god_modules"]:
        lines.append("### 3.4 上帝模块 (出度 > 10)")
        lines.append("")
        for mod, deg in arch_result["god_modules"]:
            lines.append(f"- **{mod}**: 依赖 {deg} 个模块")
        lines.append("")

    # 代码量分布
    lines.append("### 3.5 代码量分布")
    lines.append("")
    lines.append("| 目录 | 文件数 | 行数 | 占比 |")
    lines.append("|------|--------|------|------|")
    total_lines = sum(d["lines"] for d in arch_result["dir_distribution"].values())
    for dname, dinfo in arch_result["dir_distribution"].items():
        pct = dinfo["lines"] / total_lines * 100 if total_lines else 0
        lines.append(
            f"| {dname} | {dinfo['files']} | {dinfo['lines']:,} | {pct:.1f}% |"
        )
    lines.append("")

    # ---- 测试分析 ----
    lines.append("## 4. 测试分析")
    lines.append("")
    if test_result.get("status") == "completed":
        lines.append(f"- 测试总数: **{test_result.get('total', 0)}**")
        lines.append(f"- 通过数: ✅ {test_result.get('passed', 0)}")
        lines.append(f"- 失败数: ❌ {test_result.get('failed', 0)}")
        lines.append(f"- 错误数: ⚠️  {test_result.get('errors', 0)}")
        lines.append(f"- 跳过数: ⏭️  {test_result.get('skipped', 0)}")
        lines.append(f"- 通过率: **{test_result.get('pass_rate', 0)}%**")
        lines.append(f"- 耗时: {test_result.get('duration', 0)}s")
        lines.append("")

        if test_result.get("failed_tests"):
            lines.append("### 4.1 失败测试 (Top 5)")
            lines.append("")
            for i, ft in enumerate(test_result["failed_tests"], 1):
                lines.append(f"{i}. **{ft['name']}**")
                lines.append(f"   - 结果: {ft['outcome']}")
                lines.append(f"   - 错误: {ft['message'][:200]}")
                lines.append("")
    elif test_result.get("status") == "timeout":
        lines.append(f"⚠️ 测试运行超时（>{test_result.get('timeout', 120)}s）")
        lines.append("")
    elif test_result.get("status") == "no_tests":
        lines.append("ℹ️ 未找到测试文件")
        lines.append("")
    else:
        lines.append(f"⚠️ 测试运行异常: {test_result.get('error', 'unknown')}")
        lines.append("")

    # ---- 复杂度分析 ----
    lines.append("## 5. 复杂度分析")
    lines.append("")
    lines.append(f"- 函数总数: **{complexity_result['total_functions']}**")
    lines.append(f"- 平均圈复杂度: **{complexity_result['avg_complexity']}**")
    lines.append(f"- 最高复杂度: **{complexity_result['max_complexity']}**")
    lines.append("")

    lines.append("### 5.1 复杂度分布")
    lines.append("")
    lines.append("| 复杂度区间 | 函数数 |")
    lines.append("|------------|--------|")
    for bucket in [
        "1-5 (简单)",
        "6-10 (中等)",
        "11-15 (复杂)",
        "16-25 (高复杂)",
        "25+ (极复杂)",
    ]:
        lines.append(
            f"| {bucket} | {complexity_result['distribution'].get(bucket, 0)} |"
        )
    lines.append("")

    lines.append("### 5.2 Top 10 最复杂函数")
    lines.append("")
    lines.append("| 排名 | 函数 | 文件 | 圈复杂度 |")
    lines.append("|------|------|------|----------|")
    for i, item in enumerate(complexity_result["top10"], 1):
        lines.append(
            f"| {i} | {item['function']} | `{item['file']}` | {item['complexity']} |"
        )
    lines.append("")

    # ---- 改进建议 ----
    lines.append("## 6. 改进建议")
    lines.append("")

    suggestions_p0 = []  # 立即修复
    suggestions_p1 = []  # 尽快修复
    suggestions_p2 = []  # 计划修复
    suggestions_p3 = []  # 优化建议

    # P0: CRITICAL 级问题
    if critical_issues:
        suggestions_p0.append(f"修复 {len(critical_issues)} 个 CRITICAL 级别问题")
        for issue in critical_issues[:5]:
            suggestions_p0.append(
                f"  - [{issue['type']}] {issue['file']}:{issue['line']} - {issue['message']}"
            )

    # 测试全挂
    if (
        test_result.get("status") == "completed"
        and test_result.get("pass_rate", 100) < 30
    ):
        suggestions_p0.append(
            f"修复测试套件（当前通过率仅 {test_result['pass_rate']}%）"
        )

    # 循环依赖
    if arch_result["cycles"]:
        suggestions_p0.append(f"解决 {len(arch_result['cycles'])} 个循环依赖")

    # P1: HIGH 级问题
    if high_issues:
        suggestions_p1.append(f"修复 {len(high_issues)} 个 HIGH 级别问题")

    # 上帝模块
    if arch_result["god_modules"]:
        suggestions_p1.append(
            f"重构 {len(arch_result['god_modules'])} 个上帝模块以降低耦合"
        )

    # sys.path hack
    if arch_result["sys_path_hacks"] > 0:
        suggestions_p1.append("移除 sys.path hack，改用标准包结构")

    # P2: MEDIUM 级问题
    medium_count = len(medium_issues)
    if medium_count > 0:
        suggestions_p2.append(
            f"处理 {medium_count} 个 MEDIUM 级别问题（函数过长、圈复杂度、未使用导入等）"
        )

    # P3: LOW 级问题 + 优化
    low_count = len(low_issues)
    if low_count > 0:
        suggestions_p3.append(
            f"清理 {low_count} 个 LOW 级别问题（TODO、命名规范、魔法数字等）"
        )

    # 复杂度优化
    high_cc_count = sum(1 for f in complexity_result["top10"] if f["complexity"] > 15)
    if high_cc_count > 0:
        suggestions_p3.append(f"重构 Top 10 复杂函数中 {high_cc_count} 个 CC>15 的函数")

    # 测试覆盖率（如果测试少）
    if test_result.get("status") == "no_tests":
        suggestions_p2.append("建立测试套件，覆盖核心功能")

    lines.append("### P0 - 立即修复")
    lines.append("")
    if suggestions_p0:
        for s in suggestions_p0:
            lines.append(f"- {s}")
    else:
        lines.append("✅ 无 P0 级问题")
    lines.append("")

    lines.append("### P1 - 高优先级")
    lines.append("")
    if suggestions_p1:
        for s in suggestions_p1:
            lines.append(f"- {s}")
    else:
        lines.append("✅ 无 P1 级问题")
    lines.append("")

    lines.append("### P2 - 中优先级")
    lines.append("")
    if suggestions_p2:
        for s in suggestions_p2:
            lines.append(f"- {s}")
    else:
        lines.append("✅ 无 P2 级问题")
    lines.append("")

    lines.append("### P3 - 低优先级 / 优化")
    lines.append("")
    if suggestions_p3:
        for s in suggestions_p3:
            lines.append(f"- {s}")
    else:
        lines.append("✅ 无 P3 级问题")
    lines.append("")

    # ---- 底部 ----
    lines.append("---")
    lines.append("")
    lines.append(f"*本报告由 Nova Auto Review v2.0 自动生成*")
    lines.append("")

    report_content = "\n".join(lines)

    # 写入文件（追加模式）
    if REPORT_FILE.exists():
        existing = REPORT_FILE.read_text()
        new_content = existing + "\n" + report_content
    else:
        # 第一个报告前面不加 ---
        new_content = report_content
        # 去掉开头的 ---
        if new_content.startswith("---\n"):
            new_content = new_content[4:]

    REPORT_FILE.write_text(new_content)
    log(f"报告已写入: {REPORT_FILE}")
    log(f"报告长度: {len(new_content)} 字符")

    return report_content


def git_commit_and_push(review_round):
    """Git 提交并推送"""
    log("Git 操作: 提交审查报告")

    try:
        # 配置 git 用户
        subprocess.run(
            ["git", "config", "user.email", GIT_EMAIL],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            timeout=10,
        )
        subprocess.run(
            ["git", "config", "user.name", GIT_NAME],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            timeout=10,
        )

        # 检查是否有变更
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if not result.stdout.strip():
            log("无变更，跳过 commit", "WARN")
            return False

        # 添加文件
        subprocess.run(
            ["git", "add", "AUTO_REVIEW_LOG.md", "scripts/"],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            timeout=10,
        )

        # 提交
        commit_msg = f"auto: 第 {review_round} 轮深度审查报告 (v2.0)"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            log(f"commit 失败: {result.stderr}", "WARN")
            return False
        log(f"已提交: {commit_msg}")

        # 推送
        result = subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            log(f"push 失败: {result.stderr}", "ERROR")
            return False
        log("已推送到远程 main 分支")
        return True

    except subprocess.TimeoutExpired:
        log("Git 操作超时", "ERROR")
        return False
    except Exception as e:
        log(f"Git 操作异常: {e}", "ERROR")
        return False


# ============================================================
# 主流程
# ============================================================


def main():
    log("Nova 深度自动审查系统 v2.0 启动")
    log(f"项目目录: {PROJECT_DIR}")
    log("")

    try:
        # 阶段 1: 项目初始化
        if not phase1_init():
            log("项目初始化失败，退出", "ERROR")
            sys.exit(1)

        # 阶段 2: 同步远程
        phase2_sync()

        # 阶段 3: AST 级代码质量分析
        ast_result = phase3_ast_analysis()

        # 阶段 4: 架构审查
        arch_result = phase4_architecture(ast_result)

        # 阶段 5: 测试分析
        test_result = phase5_testing()

        # 阶段 6: 复杂度分析
        complexity_result = phase6_complexity(ast_result)

        # 阶段 7: 报告生成与提交
        review_round = determine_review_round()
        generate_report(
            ast_result, arch_result, test_result, complexity_result, review_round
        )
        git_commit_and_push(review_round)

        log("")
        log("=" * 60)
        log("✅ 审查完成！")
        log(f"报告位置: {REPORT_FILE}")
        log("=" * 60)

    except Exception as e:
        log(f"脚本异常: {e}", "ERROR")
        log(traceback.format_exc(), "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
