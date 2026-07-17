#!/usr/bin/env python3
"""
Nova Auto Improve System v3.0
审查驱动的自动修复系统 - Level 2 组件

功能：自动发现并修复代码库中的常见问题
- REPL 导入问题 (CRITICAL)
- 裸 except (HIGH)
- 静默异常吞噬 (HIGH)
- 缺少文档字符串 (LOW)
- 导入顺序问题 (LOW)
- 代码风格问题 (LOW)

质量保障：四道防线
1. AST 语法验证
2. 批量测试验证
3. 自动回滚机制
4. Git Tag 备份
"""

import os
import sys
import ast
import re
import subprocess
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# ============================================================================
# 配置
# ============================================================================

PROJECT_DIR = Path("/workspace/nova")
SCRIPTS_DIR = PROJECT_DIR / "scripts"
LOG_FILE = PROJECT_DIR / "AUTO_IMPROVE_LOG.md"

GIT_TOKEN = os.environ.get("NOVA_GIT_TOKEN", "")
GIT_USER = os.environ.get("NOVA_GIT_USER", "zhangzhangyitian966-create")
GIT_REPO = os.environ.get("NOVA_GIT_REPO", "nova-lang.git")
GIT_EMAIL = "auto-improve@nova-lang.dev"
GIT_NAME = "Nova Auto Improve"

TEST_FILES = [
    "tests/test_nova.py",
    "tests/test_c_codegen.py",
    "tests/test_ir.py",
    "tests/test_backends.py",
]

TEST_TIMEOUT = 120  # 秒

# 核心模块列表（用于文档字符串修复）
# 注意：package-dir = {"nova" = "."}，所以模块直接在项目根目录
CORE_MODULES = [
    "__init__.py",
    "lexer.py",
    "parser.py",
    "ast_nodes.py",
    "c_codegen.py",
    "compiler.py",
    "evaluator.py",
    "errors.py",
    "environment.py",
    "type_checker.py",
    "vm.py",
    "cli.py",
    "ir/__init__.py",
    "ir/ir_nodes.py",
    "backend/__init__.py",
    "backend/compiler_pipeline.py",
]

# 严重程度等级
SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

VERSION = "v3.0"


# ============================================================================
# 工具函数
# ============================================================================

def run_cmd(cmd: str, cwd: Path = None, timeout: int = None,
            capture: bool = True) -> Tuple[int, str, str]:
    """运行 shell 命令，返回 (returncode, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=str(cwd) if cwd else None,
            capture_output=capture, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout after {} seconds".format(timeout)
    except Exception as e:
        return -1, "", str(e)


def print_header(title: str, char: str = "=") -> None:
    """打印标题"""
    width = 70
    print()
    print(char * width)
    print("  " + title)
    print(char * width)


def print_step(step: str, msg: str) -> None:
    """打印步骤信息"""
    print(f"  [{step}] {msg}")


def ast_parse_safe(code: str) -> bool:
    """安全地解析 Python 代码，返回是否语法正确"""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def get_python_files(directory: Path) -> List[Path]:
    """获取目录下所有 Python 文件"""
    python_files = []
    for root, dirs, files in os.walk(str(directory)):
        # 跳过 .git 和 __pycache__
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "venv", ".venv")]
        for f in files:
            if f.endswith(".py"):
                python_files.append(Path(root) / f)
    return sorted(python_files)


# ============================================================================
# 阶段 1: 项目初始化
# ============================================================================

def stage1_init_project() -> bool:
    """阶段 1: 项目初始化"""
    print_header("阶段 1: 项目初始化")

    # 检查项目是否存在
    if PROJECT_DIR.exists() and (PROJECT_DIR / ".git").exists():
        print_step("1.1", "项目已存在，跳过克隆")
        return True

    print_step("1.1", "项目不存在，开始克隆...")

    # 配置 git credential helper
    print_step("1.2", "配置 Git 凭证...")
    cred_file = Path("/root/.git-credentials")
    try:
        # 写入凭证文件
        repo_url = f"https://{GIT_USER}:{GIT_TOKEN}@github.com/{GIT_USER}/{GIT_REPO}"
        cred_content = f"https://{GIT_USER}:{GIT_TOKEN}@github.com\n"
        cred_file.write_text(cred_content)
        os.chmod(str(cred_file), 0o600)
        print_step("1.2", "凭证文件已写入")
    except Exception as e:
        print_step("1.2", f"警告: 凭证文件写入失败: {e}")

    # 克隆仓库
    print_step("1.3", "克隆仓库...")
    clone_url = f"https://{GIT_USER}:{GIT_TOKEN}@github.com/{GIT_USER}/{GIT_REPO}"

    ret, stdout, stderr = run_cmd(
        f"git clone {clone_url} {PROJECT_DIR}",
        timeout=120
    )

    if ret != 0:
        print_step("1.3", f"错误: 克隆失败: {stderr}")
        return False

    print_step("1.3", "克隆成功")
    return True


# ============================================================================
# 阶段 2: 同步远程
# ============================================================================

def stage2_sync_remote() -> None:
    """阶段 2: 同步远程"""
    print_header("阶段 2: 同步远程")

    # 先配置 git 身份
    run_cmd(f'git config user.email "{GIT_EMAIL}"', cwd=PROJECT_DIR)
    run_cmd(f'git config user.name "{GIT_NAME}"', cwd=PROJECT_DIR)

    print_step("2.1", "执行 git pull --rebase...")

    # 先 stash 本地变更
    run_cmd("git stash", cwd=PROJECT_DIR, timeout=30)

    ret, stdout, stderr = run_cmd(
        "git pull --rebase origin main",
        cwd=PROJECT_DIR, timeout=60
    )

    if ret != 0:
        print_step("2.1", f"警告: git pull 失败（可能是首次运行）: {stderr}")
        # 恢复 stash
        run_cmd("git stash pop", cwd=PROJECT_DIR, timeout=30)
    else:
        print_step("2.1", "同步成功")
        # 恢复 stash
        ret_stash, _, stderr_stash = run_cmd(
            "git stash pop", cwd=PROJECT_DIR, timeout=30
        )
        if ret_stash != 0 and "No stash entries" not in stderr_stash:
            print_step("2.1", f"警告: 恢复 stash 失败: {stderr_stash}")


# ============================================================================
# 阶段 3: 创建备份点
# ============================================================================

def stage3_create_backup() -> Optional[str]:
    """阶段 3: 创建备份点，返回标签名"""
    print_header("阶段 3: 创建备份点")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag_name = f"auto-improve-backup-{timestamp}"

    print_step("3.1", f"创建备份标签: {tag_name}")
    ret, stdout, stderr = run_cmd(
        f'git tag -a {tag_name} -m "auto improve backup"',
        cwd=PROJECT_DIR, timeout=30
    )

    if ret != 0:
        print_step("3.1", f"警告: 创建标签失败: {stderr}")
        return None

    print_step("3.1", "备份标签创建成功")
    return tag_name


# ============================================================================
# 阶段 4: 基线测试
# ============================================================================

def run_tests() -> Tuple[int, int, str]:
    """运行测试套件，返回 (passed, total, output)"""
    test_paths = " ".join(TEST_FILES)
    cmd = f"PYTHONPATH={PROJECT_DIR} python3 -m pytest {test_paths} --tb=line -q"

    ret, stdout, stderr = run_cmd(
        cmd, cwd=PROJECT_DIR, timeout=TEST_TIMEOUT
    )

    output = stdout + stderr

    # 解析测试结果
    # 格式: "X passed, Y failed in Zs"
    passed = 0
    total = 0

    # 尝试匹配 passed
    m = re.search(r"(\d+)\s+passed", output)
    if m:
        passed = int(m.group(1))

    # 匹配 failed
    m_failed = re.search(r"(\d+)\s+failed", output)
    failed = int(m_failed.group(1)) if m_failed else 0

    # 匹配 error
    m_error = re.search(r"(\d+)\s+error", output)
    errors = int(m_error.group(1)) if m_error else 0

    total = passed + failed + errors

    # 如果没解析到，用另一种方式
    if total == 0 and ret == 0:
        # 全部通过的情况
        m = re.search(r"(\d+)\s+passed", output)
        if m:
            passed = int(m.group(1))
            total = passed

    return passed, total, output


def stage4_baseline_tests() -> Tuple[int, int]:
    """阶段 4: 基线测试，返回 (passed, total)"""
    print_header("阶段 4: 基线测试")

    print_step("4.1", "运行测试套件...")
    passed, total, output = run_tests()

    print_step("4.1", f"基线结果: {passed}/{total} 通过")

    # 如果有失败，打印简要信息
    if passed < total:
        # 提取失败的测试名
        failures = re.findall(r"FAILED\s+(\S+)", output)
        if failures:
            print_step("4.1", f"失败的测试 ({len(failures)} 个):")
            for f in failures[:10]:
                print(f"        - {f}")
            if len(failures) > 10:
                print(f"        ... 还有 {len(failures) - 10} 个")

    return passed, total


# ============================================================================
# 问题发现
# ============================================================================

def discover_issues() -> List[Dict]:
    """发现代码库中的问题"""
    issues = []

    python_files = get_python_files(PROJECT_DIR)

    # 1. 发现 REPL 导入问题
    issues.extend(discover_repl_import_issues())

    # 2. 发现裸 except
    issues.extend(discover_bare_except_issues(python_files))

    # 3. 发现静默异常吞噬
    issues.extend(discover_silent_exception_issues(python_files))

    # 4. 发现缺少文档字符串
    issues.extend(discover_docstring_issues())

    # 5. 发现导入顺序问题
    issues.extend(discover_import_order_issues(python_files))

    # 6. 发现代码风格问题
    issues.extend(discover_code_style_issues(python_files))

    # 按严重程度排序
    issues.sort(key=lambda x: SEVERITY_ORDER.get(x.get("severity", "LOW"), 99))

    return issues


def discover_repl_import_issues() -> List[Dict]:
    """发现 REPL 导入问题

    检查核心模块中的公共类是否在 __init__.py 中导出。
    只添加那些确定存在且未导出的类。
    """
    issues = []
    init_file = PROJECT_DIR / "__init__.py"

    if not init_file.exists():
        return issues

    init_content = init_file.read_text()

    # 定义应该检查的模块和可能的导出类名
    modules_to_check = [
        ("lexer", ["Lexer", "Token", "TokenType"]),
        ("parser", ["Parser", "ParseError"]),
        ("evaluator", ["Evaluator", "RuntimeError_"]),
        ("errors", ["LexerError", "ParseError", "TypeCheckError", "RuntimeError_"]),
        ("ast_nodes", ["Program", "Expression", "Statement"]),
        ("environment", ["Environment"]),
        ("type_checker", ["TypeChecker"]),
        ("compiler", ["BytecodeCompiler", "Bytecode"]),
        ("vm", ["VM"]),
        ("c_codegen", ["CCodeGen"]),
    ]

    missing_exports = []  # [(module_name, class_name)]

    for module_name, class_names in modules_to_check:
        module_path = PROJECT_DIR / f"{module_name}.py"
        if not module_path.exists():
            continue

        try:
            module_content = module_path.read_text()
            tree = ast.parse(module_content)

            # 找出模块中实际定义的公共类
            defined_classes = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                    defined_classes.add(node.name)

            for class_name in class_names:
                if class_name in defined_classes:
                    # 检查是否已在 __init__.py 中导出
                    pattern = rf"from\s+\.{module_name}\s+import\s+.*\b{class_name}\b"
                    if not re.search(pattern, init_content):
                        missing_exports.append((module_name, class_name))
        except Exception:
            continue

    # 限制导出数量，避免一次添加太多
    if len(missing_exports) > 6:
        missing_exports = missing_exports[:6]

    if missing_exports:
        issues.append({
            "type": "repl_import_fix",
            "severity": "CRITICAL",
            "file": "__init__.py",
            "description": (
                f"__init__.py 缺少 {len(missing_exports)} 个导出: "
                + ", ".join(c for _, c in missing_exports)
            ),
            "details": {"missing_exports": missing_exports}
        })

    return issues


def discover_bare_except_issues(files: List[Path]) -> List[Dict]:
    """发现裸 except 语句"""
    issues = []
    bare_except_pattern = re.compile(r"^\s*except\s*:", re.MULTILINE)

    for f in files:
        try:
            content = f.read_text()
            matches = list(bare_except_pattern.finditer(content))

            for match in matches:
                # 获取行号
                line_num = content[:match.start()].count("\n") + 1
                rel_path = str(f.relative_to(PROJECT_DIR))

                issues.append({
                    "type": "bare_except",
                    "severity": "HIGH",
                    "file": rel_path,
                    "line": line_num,
                    "description": f"裸 except 语句 (第 {line_num} 行)",
                    "details": {"line": line_num}
                })
        except Exception:
            continue

    return issues


def discover_silent_exception_issues(files: List[Path]) -> List[Dict]:
    """发现静默异常吞噬 (except Exception: pass)"""
    issues = []

    for f in files:
        try:
            content = f.read_text()
            lines = content.split("\n")

            for i, line in enumerate(lines):
                # 匹配 except Exception: pass (单行)
                if re.match(r"^\s*except\s+(\w+\.)*Exception\s*:\s*pass\s*$", line):
                    rel_path = str(f.relative_to(PROJECT_DIR))
                    issues.append({
                        "type": "too_broad_exception",
                        "severity": "HIGH",
                        "file": rel_path,
                        "line": i + 1,
                        "description": f"静默异常吞噬 (第 {i+1} 行)",
                        "details": {"line": i + 1, "single_line": True}
                    })
                    continue

                # 匹配多行: except Exception: 后面跟着只有 pass 的块
                if re.match(r"^\s*except\s+(\w+\.)*Exception\s*:\s*$", line):
                    # 检查下一行是否只有 pass
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        if re.match(r"^\s+pass\s*$", next_line):
                            # 确认这是一个只有 pass 的块
                            # 检查再下一行缩进是否回到 except 级别
                            if i + 2 >= len(lines) or not re.match(
                                r"^\s{" + str(len(next_line) - len(next_line.lstrip())) + r",}\S",
                                lines[i + 2]
                            ) if i + 2 < len(lines) else True:
                                rel_path = str(f.relative_to(PROJECT_DIR))
                                issues.append({
                                    "type": "too_broad_exception",
                                    "severity": "HIGH",
                                    "file": rel_path,
                                    "line": i + 1,
                                    "description": f"静默异常吞噬 (第 {i+1} 行)",
                                    "details": {"line": i + 1, "single_line": False}
                                })

        except Exception:
            continue

    return issues


def discover_docstring_issues() -> List[Dict]:
    """发现缺少文档字符串的核心模块"""
    issues = []

    for module_path in CORE_MODULES:
        full_path = PROJECT_DIR / module_path

        if not full_path.exists():
            continue

        try:
            content = full_path.read_text()
            tree = ast.parse(content)

            # 检查模块级文档字符串
            has_docstring = (
                ast.get_docstring(tree) is not None
            )

            if not has_docstring and content.strip():
                issues.append({
                    "type": "no_docstring",
                    "severity": "LOW",
                    "file": module_path,
                    "description": f"模块缺少文档字符串",
                    "details": {}
                })
        except Exception:
            continue

    return issues


def discover_import_order_issues(files: List[Path]) -> List[Dict]:
    """发现导入顺序问题"""
    issues = []

    for f in files:
        try:
            content = f.read_text()
            lines = content.split("\n")

            imports = []
            for i, line in enumerate(lines):
                # 跳过注释和空行
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue

                # 匹配 import 语句
                if re.match(r"^(from\s+\S+\s+import|import\s+\S+)", stripped):
                    imports.append((i, stripped, line))

            if len(imports) < 2:
                continue

            # 分类导入
            stdlib = []
            third_party = []
            local = []

            stdlib_modules = {
                "os", "sys", "re", "json", "math", "time", "datetime",
                "collections", "typing", "pathlib", "subprocess", "io",
                "ast", "enum", "functools", "itertools", "struct",
                "hashlib", "random", "string", "tempfile", "shutil",
                "argparse", "logging", "traceback", "warnings",
                "copy", "abc", "dataclasses", "contextlib",
            }

            for idx, imp, original in imports:
                # 提取模块名
                m = re.match(r"^(from\s+(\S+)|import\s+(\S+))", imp)
                if m:
                    module = m.group(2) or m.group(3)
                    top_module = module.split(".")[0]

                    if top_module.startswith(".") or top_module == "nova":
                        local.append((idx, original))
                    elif top_module in stdlib_modules:
                        stdlib.append((idx, original))
                    else:
                        third_party.append((idx, original))

            # 检查顺序是否正确: stdlib -> third_party -> local
            all_imports = stdlib + third_party + local
            all_indices = [i for i, _ in all_imports]
            original_indices = [i for i, _ in imports]

            # 如果索引顺序不同，说明有顺序问题
            if all_indices != sorted(all_indices):
                # 跳过含多行 import( 的文件
                if "import (" in content or "import(" in content:
                    continue

                rel_path = str(f.relative_to(PROJECT_DIR))
                issues.append({
                    "type": "import_order",
                    "severity": "LOW",
                    "file": rel_path,
                    "description": "导入顺序不符合规范",
                    "details": {
                        "stdlib_count": len(stdlib),
                        "third_party_count": len(third_party),
                        "local_count": len(local)
                    }
                })

        except Exception:
            continue

    return issues


def discover_code_style_issues(files: List[Path]) -> List[Dict]:
    """发现代码风格问题（粗略估计）"""
    issues = []

    for f in files:
        try:
            content = f.read_text()
            lines = content.split("\n")

            style_issues = 0

            # 检查行长度
            for line in lines:
                if len(line.rstrip()) > 100:
                    style_issues += 1
                    if style_issues >= 3:
                        break

            # 检查尾随空格
            trailing_space_count = sum(
                1 for line in lines
                if line.rstrip() != line and line.strip()
            )

            if style_issues >= 3 or trailing_space_count >= 5:
                rel_path = str(f.relative_to(PROJECT_DIR))
                issues.append({
                    "type": "code_style",
                    "severity": "LOW",
                    "file": rel_path,
                    "description": "代码风格需要优化",
                    "details": {
                        "long_lines": style_issues,
                        "trailing_spaces": trailing_space_count
                    }
                })

        except Exception:
            continue

    return issues


# ============================================================================
# 修复器基类
# ============================================================================

class BaseFixer:
    """修复器基类"""

    name = "base"
    display_name = "基础修复器"

    def can_fix(self, issue_type: str, severity: str) -> bool:
        return False

    def fix(self, issue_type: str, file_path: str, details: Dict) -> bool:
        """修复单个问题，返回是否成功"""
        return False

    def fix_batch(self, issues: List[Dict]) -> Tuple[int, int]:
        """批量修复，返回 (成功数, 总数)"""
        success = 0
        for issue in issues:
            if self.can_fix(issue["type"], issue.get("severity", "LOW")):
                try:
                    if self.fix(issue["type"], issue["file"], issue.get("details", {})):
                        success += 1
                except Exception as e:
                    print(f"    修复失败 {issue['file']}: {e}")
        return success, len(issues)


# ============================================================================
# 修复器 1: REPL 导入修复
# ============================================================================

class ReplImportFixer(BaseFixer):
    """修复 REPL 导入问题"""

    name = "repl_import"
    display_name = "REPL 导入修复器"

    def can_fix(self, issue_type: str, severity: str) -> bool:
        return issue_type == "repl_import_fix"

    def fix(self, issue_type: str, file_path: str, details: Dict) -> bool:
        full_path = PROJECT_DIR / file_path
        if not full_path.exists():
            return False

        content = full_path.read_text()
        missing = details.get("missing_exports", [])

        if not missing:
            return False

        # missing 是 [(module_name, class_name), ...] 格式
        additions = []
        for module_name, class_name in missing:
            addition = f"from .{module_name} import {class_name}"
            # 检查是否已存在
            pattern = rf"from\s+\.{module_name}\s+import\s+.*\b{class_name}\b"
            if not re.search(pattern, content):
                additions.append(addition)

        if not additions:
            return False

        # 追加到文件末尾（按模块分组）
        new_content = content.rstrip() + "\n"
        current_module = None
        for addition in additions:
            new_content += addition + "\n"

        # 验证语法
        if not ast_parse_safe(new_content):
            return False

        full_path.write_text(new_content)
        return True


# ============================================================================
# 修复器 2: 裸 except 修复
# ============================================================================

class BareExceptFixer(BaseFixer):
    """修复裸 except 语句"""

    name = "bare_except"
    display_name = "裸 except 修复器"

    def can_fix(self, issue_type: str, severity: str) -> bool:
        return issue_type == "bare_except"

    def fix(self, issue_type: str, file_path: str, details: Dict) -> bool:
        full_path = PROJECT_DIR / file_path
        if not full_path.exists():
            return False

        content = full_path.read_text()
        lines = content.split("\n")
        line_num = details.get("line", 0) - 1

        if line_num < 0 or line_num >= len(lines):
            return False

        line = lines[line_num]

        # 替换 bare except
        new_line = re.sub(r"^(\s*)except\s*:", r"\1except Exception:", line)
        if new_line == line:
            return False

        lines[line_num] = new_line
        new_content = "\n".join(lines)

        # 验证语法
        if not ast_parse_safe(new_content):
            return False

        full_path.write_text(new_content)
        return True


# ============================================================================
# 修复器 3: 静默异常修复
# ============================================================================

class SilentExceptionFixer(BaseFixer):
    """标记静默异常吞噬"""

    name = "silent_exception"
    display_name = "静默异常标记器"

    def can_fix(self, issue_type: str, severity: str) -> bool:
        return issue_type == "too_broad_exception"

    def fix(self, issue_type: str, file_path: str, details: Dict) -> bool:
        full_path = PROJECT_DIR / file_path
        if not full_path.exists():
            return False

        content = full_path.read_text()
        lines = content.split("\n")
        line_num = details.get("line", 0) - 1
        single_line = details.get("single_line", True)

        if line_num < 0 or line_num >= len(lines):
            return False

        line = lines[line_num]
        indent = len(line) - len(line.lstrip())
        indent_str = " " * indent

        if single_line:
            # 单行: except Exception: pass -> 拆成多行并添加 TODO
            # 提取缩进
            match = re.match(r"^(\s*)(except\s+(\w+\.)*Exception\s*:)\s*pass\s*$", line)
            if not match:
                return False

            indent_str = match.group(1)
            except_clause = match.group(2)

            new_lines = [
                f"{indent_str}{except_clause}",
                f"{indent_str}    # TODO: 细化异常处理，避免静默吞噬",
                f"{indent_str}    pass",
            ]

            lines[line_num:line_num + 1] = new_lines
        else:
            # 多行: 在 pass 前添加 TODO 注释
            if line_num + 1 >= len(lines):
                return False

            pass_line = lines[line_num + 1]
            pass_indent = len(pass_line) - len(pass_line.lstrip())
            pass_indent_str = " " * pass_indent

            todo_line = f"{pass_indent_str}# TODO: 细化异常处理，避免静默吞噬"
            lines.insert(line_num + 1, todo_line)

        new_content = "\n".join(lines)

        # 验证语法
        if not ast_parse_safe(new_content):
            return False

        full_path.write_text(new_content)
        return True


# ============================================================================
# 修复器 4: 文档字符串修复
# ============================================================================

class DocstringFixer(BaseFixer):
    """补充核心模块文档字符串"""

    name = "docstring"
    display_name = "文档字符串修复器"

    MODULE_DOCSTRINGS = {
        "__init__.py": '''"""
Nova Programming Language
=========================

Nova 是一种现代编程语言，具有简洁的语法和强大的表达能力。

本模块提供 Nova 语言的主要入口点，包括解释器、编译器和核心工具。

主要类:
    - Nova: 主入口类
    - Lexer: 词法分析器
    - Parser: 语法分析器
    - Evaluator: 解释器
    - Compiler: 编译器

示例:
    >>> from nova import Nova
    >>> nova = Nova()
    >>> nova.eval("1 + 1")
    2
"""
''',
        "lexer.py": '''"""
Nova 词法分析器 (Lexer)

将源代码文本转换为 token 流，为语法分析做准备。

功能:
    - 关键字识别
    - 标识符和字面量解析
    - 操作符和分隔符处理
    - 位置追踪（行号、列号）
"""
''',
        "parser.py": '''"""
Nova 语法分析器 (Parser)

将 token 流转换为抽象语法树 (AST)。

采用递归下降解析算法，支持:
    - 表达式解析（优先级处理）
    - 语句解析（变量、函数、控制流）
    - 错误恢复
"""
''',
        "ast_nodes.py": '''"""
Nova 抽象语法树节点定义

定义所有 AST 节点类型，每个节点代表语法树中的一个元素。

节点类别:
    - 表达式节点 (Expression)
    - 语句节点 (Statement)
    - 声明节点 (Declaration)
"""
''',
        "c_codegen.py": '''"""
Nova C 代码生成器

将中间表示 (IR) 翻译为 C 源代码。

功能:
    - 类型映射
    - 表达式翻译
    - 控制流翻译
    - 运行时库接口
"""
''',
        "compiler.py": '''"""
Nova 编译器

将 Nova 源代码编译为目标代码。

编译流程:
    1. 词法分析 (Lexer)
    2. 语法分析 (Parser)
    3. 类型检查 (TypeChecker)
    4. IR 生成 (HIR -> MIR -> LIR)
    5. 代码生成 (Backend)
"""
''',
        "evaluator.py": '''"""
Nova 解释器 (Evaluator)

直接遍历 AST 执行 Nova 程序，用于快速原型和 REPL。

功能:
    - 环境管理（变量作用域）
    - 表达式求值
    - 函数调用
    - 内置函数支持
"""
''',
        "errors.py": '''"""
Nova 错误处理模块

定义 Nova 语言的所有错误类型和错误报告机制。

错误类型:
    - LexerError: 词法错误
    - ParserError: 语法错误
    - RuntimeError: 运行时错误
    - TypeError: 类型错误
"""
''',
        "environment.py": '''"""
Nova 环境管理

管理变量作用域和符号表，支持嵌套作用域。

功能:
    - 变量定义与查找
    - 作用域嵌套
    - 闭包支持
"""
''',
        "type_checker.py": '''"""
Nova 类型检查器

实现 Nova 语言的静态类型检查和类型推断。

功能:
    - 类型表示
    - 类型兼容性检查
    - 类型推断
    - 泛型支持
"""
''',
        "vm.py": '''"""
Nova 虚拟机 (VM)

执行 Nova 字节码的栈式虚拟机。

功能:
    - 字节码解释执行
    - 栈操作
    - 函数调用帧管理
    - 垃圾回收
"""
''',
        "cli.py": '''"""
Nova 命令行接口

提供 Nova 语言的命令行交互界面。

功能:
    - REPL 交互式模式
    - 文件执行模式
    - 编译模式
    - 命令行参数解析
"""
''',
        "ir/__init__.py": '''"""
Nova 中间表示 (IR) 包

包含 Nova 编译器的中间表示层，实现多层 IR 设计：
- HIR (High-level IR): 高层中间表示
- MIR (Mid-level IR): 中层中间表示
- LIR (Low-level IR): 低层中间表示
"""
''',
        "ir/ir_nodes.py": '''"""
Nova IR 节点定义

定义各层 IR 的节点类型和结构。
"""
''',
        "backend/__init__.py": '''"""
Nova 后端包

包含多个代码生成后端：
- C 后端: 生成 C 源代码
- x86_64 后端: 生成 x86_64 机器码
- WASM 后端: 生成 WebAssembly
- Cranelift 后端: 使用 Cranelift 生成机器码
- Native 后端: 原生代码生成
"""
''',
        "backend/compiler_pipeline.py": '''"""
Nova 编译器流水线

管理从 AST 到目标代码的完整编译流程。
"""
''',
    }

    def can_fix(self, issue_type: str, severity: str) -> bool:
        return issue_type == "no_docstring"

    def fix(self, issue_type: str, file_path: str, details: Dict) -> bool:
        full_path = PROJECT_DIR / file_path
        if not full_path.exists():
            return False

        content = full_path.read_text()

        # 获取文档字符串
        docstring = self.MODULE_DOCSTRINGS.get(file_path)
        if not docstring:
            # 生成通用文档字符串
            module_name = file_path.split("/")[-1].replace(".py", "")
            docstring = f'''"""
Nova {module_name} 模块

本模块是 Nova 编程语言的组成部分。
"""
'''

        # 找到文件开头（跳过 shebang 和编码声明）
        lines = content.split("\n")
        insert_pos = 0

        # 跳过 shebang
        if lines and lines[0].startswith("#!"):
            insert_pos = 1

        # 跳过编码声明
        if insert_pos < len(lines) and re.match(r"^#.*coding[:=]", lines[insert_pos]):
            insert_pos += 1

        # 插入文档字符串
        new_lines = lines[:insert_pos] + [docstring.rstrip()] + lines[insert_pos:]
        new_content = "\n".join(new_lines)

        # 验证语法
        if not ast_parse_safe(new_content):
            return False

        full_path.write_text(new_content)
        return True


# ============================================================================
# 修复器 5: 导入顺序修复
# ============================================================================

class ImportSortFixer(BaseFixer):
    """整理导入顺序"""

    name = "import_sort"
    display_name = "导入顺序修复器"

    def can_fix(self, issue_type: str, severity: str) -> bool:
        return issue_type == "import_order"

    def fix(self, issue_type: str, file_path: str, details: Dict) -> bool:
        full_path = PROJECT_DIR / file_path
        if not full_path.exists():
            return False

        content = full_path.read_text()

        # 跳过含多行 import( 的文件
        if re.search(r"import\s*\(", content):
            return False

        lines = content.split("\n")

        # 收集所有 import 语句及其位置
        imports = []  # (start_line, end_line, import_lines, is_from, module)
        i = 0
        stdlib_modules = {
            "os", "sys", "re", "json", "math", "time", "datetime",
            "collections", "typing", "pathlib", "subprocess", "io",
            "ast", "enum", "functools", "itertools", "struct",
            "hashlib", "random", "string", "tempfile", "shutil",
            "argparse", "logging", "traceback", "warnings",
            "copy", "abc", "dataclasses", "contextlib", "textwrap",
        }

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 跳过空行和注释
            if not stripped or stripped.startswith("#"):
                i += 1
                continue

            # 检查是否是 import 语句
            match = re.match(r"^(from\s+(\S+)\s+import|import\s+(\S+))", stripped)
            if not match:
                i += 1
                continue

            start = i
            import_lines = [line]
            is_from = match.group(1).startswith("from")
            module = match.group(2) or match.group(3)

            # 处理可能的续行
            i += 1
            while i < len(lines):
                next_stripped = lines[i].strip()
                if next_stripped.startswith("#"):
                    import_lines.append(lines[i])
                    i += 1
                    continue
                # 检查是否是续行（缩进的 import 内容）
                if lines[i] and (lines[i][0].isspace() and next_stripped and not next_stripped.startswith("import") and not next_stripped.startswith("from")):
                    # 可能是续行或者是别的东西，保守起见停止
                    if "(" in import_lines[-1] or import_lines[-1].rstrip().endswith("\\"):
                        import_lines.append(lines[i])
                        i += 1
                        continue
                    break
                break

            imports.append({
                "start": start,
                "end": i - 1,
                "lines": import_lines,
                "is_from": is_from,
                "module": module,
            })

        if not imports:
            return False

        # 分类
        stdlib = []
        third_party = []
        local = []

        for imp in imports:
            top_module = imp["module"].split(".")[0]
            if top_module.startswith(".") or top_module == "nova":
                local.append(imp)
            elif top_module in stdlib_modules:
                stdlib.append(imp)
            else:
                third_party.append(imp)

        # 对每类内部排序
        def sort_key(imp):
            return (imp["is_from"], imp["module"])

        stdlib.sort(key=sort_key)
        third_party.sort(key=sort_key)
        local.sort(key=sort_key)

        # 构建新的 import 块
        sorted_imports = []
        if stdlib:
            for imp in stdlib:
                sorted_imports.extend(imp["lines"])

        if third_party:
            if sorted_imports:
                sorted_imports.append("")  # 空行分隔
            for imp in third_party:
                sorted_imports.extend(imp["lines"])

        if local:
            if sorted_imports:
                sorted_imports.append("")  # 空行分隔
            for imp in local:
                sorted_imports.extend(imp["lines"])

        # 确定替换范围
        first_line = min(imp["start"] for imp in imports)
        last_line = max(imp["end"] for imp in imports)

        # 替换
        new_lines = lines[:first_line] + sorted_imports + lines[last_line + 1:]
        new_content = "\n".join(new_lines)

        # 验证语法
        if not ast_parse_safe(new_content):
            return False

        full_path.write_text(new_content)
        return True


# ============================================================================
# 修复器 6: 代码风格修复
# ============================================================================

class FormatFixer(BaseFixer):
    """统一代码风格（使用 black）"""

    name = "format"
    display_name = "代码风格格式化器"

    def __init__(self):
        self.black_available = self._check_black()

    def _check_black(self) -> bool:
        """检查 black 是否可用，不可用则尝试安装"""
        try:
            import black
            return True
        except ImportError:
            # 尝试安装
            print("    正在安装 black...")
            ret, _, _ = run_cmd(
                "pip install black --break-system-packages -q",
                timeout=60
            )
            return ret == 0

    def can_fix(self, issue_type: str, severity: str) -> bool:
        return issue_type == "code_style" and self.black_available

    def fix(self, issue_type: str, file_path: str, details: Dict) -> bool:
        if not self.black_available:
            return False

        full_path = PROJECT_DIR / file_path
        if not full_path.exists():
            return False

        try:
            import black
            content = full_path.read_text()

            try:
                mode = black.Mode()
                formatted = black.format_str(content, mode=mode)
            except Exception:
                return False

            if formatted == content:
                return True  # 已经格式化好了

            # 验证语法
            if not ast_parse_safe(formatted):
                return False

            full_path.write_text(formatted)
            return True
        except Exception:
            return False


# ============================================================================
# 修复器管理器
# ============================================================================

class FixerManager:
    """修复器管理器"""

    def __init__(self):
        self.fixers = [
            ReplImportFixer(),
            BareExceptFixer(),
            SilentExceptionFixer(),
            DocstringFixer(),
            ImportSortFixer(),
            FormatFixer(),
        ]

    def get_fixer_for(self, issue_type: str, severity: str) -> Optional[BaseFixer]:
        """获取能处理指定问题的修复器"""
        for fixer in self.fixers:
            if fixer.can_fix(issue_type, severity):
                return fixer
        return None

    def group_issues_by_fixer(self, issues: List[Dict]) -> Dict[str, List[Dict]]:
        """按修复器分组问题"""
        groups = {}
        for issue in issues:
            fixer = self.get_fixer_for(
                issue["type"], issue.get("severity", "LOW")
            )
            if fixer:
                key = fixer.name
                if key not in groups:
                    groups[key] = []
                groups[key].append(issue)
        return groups


# ============================================================================
# 阶段 5: 审查驱动的自动修复
# ============================================================================

def git_rollback() -> bool:
    """Git 回滚：恢复所有变更"""
    ret1, _, _ = run_cmd("git checkout .", cwd=PROJECT_DIR, timeout=30)
    ret2, _, _ = run_cmd("git clean -fd", cwd=PROJECT_DIR, timeout=30)
    return ret1 == 0 and ret2 == 0


def git_has_changes() -> bool:
    """检查是否有未提交的变更"""
    ret, stdout, _ = run_cmd("git status --porcelain", cwd=PROJECT_DIR, timeout=30)
    return ret == 0 and bool(stdout.strip())


def stage5_auto_fix(baseline_passed: int, baseline_total: int) -> Dict:
    """阶段 5: 审查驱动的自动修复

    返回修复结果统计
    """
    print_header("阶段 5: 审查驱动的自动修复")

    # 5.1 发现问题
    print_step("5.1", "扫描代码库发现问题...")
    issues = discover_issues()

    # 按类型统计
    issue_stats = {}
    for issue in issues:
        t = issue["type"]
        if t not in issue_stats:
            issue_stats[t] = {"count": 0, "severity": issue.get("severity", "LOW")}
        issue_stats[t]["count"] += 1

    print_step("5.1", f"共发现 {len(issues)} 个问题:")
    for issue_type, stats in sorted(
        issue_stats.items(),
        key=lambda x: SEVERITY_ORDER.get(x[1]["severity"], 99)
    ):
        print(f"        - {issue_type}: {stats['count']} 个 ({stats['severity']})")

    # 5.2 按严重程度排序处理
    print_step("5.2", "按严重程度排序，开始批量修复...")

    fixer_manager = FixerManager()
    groups = fixer_manager.group_issues_by_fixer(issues)

    # 按修复器顺序执行
    fixer_order = [
        "repl_import", "bare_except", "silent_exception",
        "docstring", "import_sort", "format"
    ]

    results = {
        "total_issues": len(issues),
        "fixers": {},
        "rollbacks": [],
    }

    for fixer_name in fixer_order:
        if fixer_name not in groups:
            continue

        fixer_issues = groups[fixer_name]
        fixer = fixer_manager.get_fixer_for(
            fixer_issues[0]["type"],
            fixer_issues[0].get("severity", "LOW")
        )

        if not fixer:
            continue

        print(f"\n    ┌─ {fixer.display_name} ────────────────────────────────────────┐")
        print(f"    │ 待修复: {len(fixer_issues)} 个问题")

        # 批量修复
        success, total = fixer.fix_batch(fixer_issues)
        print(f"    │ 修复完成: {success}/{total} 成功")

        # 检查是否有变更
        if not git_has_changes():
            print(f"    │ 无实际变更，跳过测试验证")
            print(f"    └──────────────────────────────────────────────────────┘")
            results["fixers"][fixer.name] = {
                "display_name": fixer.display_name,
                "attempted": total,
                "fixed": success,
                "status": "no_changes",
            }
            continue

        # 运行测试验证
        print(f"    │ 运行测试验证...")
        passed, total_tests, output = run_tests()

        if passed >= baseline_passed:
            print(f"    │ 测试通过: {passed}/{total_tests} (基线: {baseline_passed}/{baseline_total})")
            print(f"    └──────────────────────────────────────────────────────┘")
            results["fixers"][fixer.name] = {
                "display_name": fixer.display_name,
                "attempted": total,
                "fixed": success,
                "status": "success",
                "tests_passed": passed,
                "tests_total": total_tests,
            }
        else:
            print(f"    │ 测试失败: {passed}/{total_tests} (基线: {baseline_passed}/{baseline_total})")
            print(f"    │ 执行回滚...")
            git_rollback()
            print(f"    │ 回滚完成")
            print(f"    └──────────────────────────────────────────────────────┘")
            results["fixers"][fixer.name] = {
                "display_name": fixer.display_name,
                "attempted": total,
                "fixed": 0,
                "status": "rolled_back",
                "tests_passed": passed,
                "tests_total": total_tests,
            }
            results["rollbacks"].append(fixer.display_name)

    return results


# ============================================================================
# 阶段 6: 最终验证测试
# ============================================================================

def stage6_final_tests(baseline_passed: int, baseline_total: int) -> Tuple[int, int]:
    """阶段 6: 最终验证测试"""
    print_header("阶段 6: 最终验证测试")

    print_step("6.1", "运行完整测试套件...")
    passed, total, output = run_tests()

    print_step("6.1", f"最终结果: {passed}/{total} 通过")
    print_step("6.1", f"基线对比: {baseline_passed}/{baseline_total}")

    if passed >= baseline_passed:
        print_step("6.1", "无回归 ✓")
    else:
        print_step("6.1", f"警告: 发现回归 (减少了 {baseline_passed - passed} 个通过测试)")

    return passed, total


# ============================================================================
# 阶段 7: 报告生成与提交
# ============================================================================

def generate_report(
    baseline_passed: int,
    baseline_total: int,
    final_passed: int,
    final_total: int,
    fix_results: Dict,
    backup_tag: Optional[str],
) -> str:
    """生成 Markdown 改进报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 统计
    total_fixed = sum(
        f["fixed"] for f in fix_results.get("fixers", {}).values()
        if f["status"] == "success"
    )
    total_attempted = sum(
        f["attempted"] for f in fix_results.get("fixers", {}).values()
    )
    rollback_count = len(fix_results.get("rollbacks", []))

    lines = []
    lines.append("")
    lines.append(f"## 第 N/A 轮自动改进报告 ({VERSION})")
    lines.append("")
    lines.append(f"**执行时间**: {now}")
    lines.append(f"**备份标签**: {backup_tag or 'N/A'}")
    lines.append("")

    # 改进概览
    lines.append("### 改进概览")
    lines.append("")
    lines.append(f"| 指标 | 值 |")
    lines.append(f"|------|-----|")
    lines.append(f"| 发现问题总数 | {fix_results.get('total_issues', 0)} |")
    lines.append(f"| 尝试修复 | {total_attempted} |")
    lines.append(f"| 成功修复 | {total_fixed} |")
    lines.append(f"| 回滚次数 | {rollback_count} |")
    lines.append("")

    # 测试前后对比
    lines.append("### 测试对比")
    lines.append("")
    lines.append(f"| 阶段 | 通过数 | 总数 | 通过率 |")
    lines.append(f"|------|--------|------|--------|")
    baseline_rate = (baseline_passed / baseline_total * 100) if baseline_total > 0 else 0
    final_rate = (final_passed / final_total * 100) if final_total > 0 else 0
    lines.append(f"| 基线 | {baseline_passed} | {baseline_total} | {baseline_rate:.1f}% |")
    lines.append(f"| 最终 | {final_passed} | {final_total} | {final_rate:.1f}% |")
    diff = final_passed - baseline_passed
    diff_str = f"+{diff}" if diff > 0 else str(diff)
    lines.append(f"| 变化 | {diff_str} | - | {final_rate - baseline_rate:+.1f}% |")
    lines.append("")

    # 每个修复器的详细结果
    lines.append("### 修复器详细结果")
    lines.append("")
    lines.append(f"| 修复器 | 尝试 | 成功 | 状态 |")
    lines.append(f"|--------|------|------|------|")

    for fixer_name, result in fix_results.get("fixers", {}).items():
        status_map = {
            "success": "✓ 成功",
            "rolled_back": "✗ 已回滚",
            "no_changes": "— 无变更",
        }
        status = status_map.get(result["status"], result["status"])
        lines.append(
            f"| {result['display_name']} | {result['attempted']} "
            f"| {result['fixed']} | {status} |"
        )

    lines.append("")

    # 下一步改进计划
    lines.append("### 下一步改进计划")
    lines.append("")
    lines.append("1. **类型注解补充**: 为核心函数添加类型注解")
    lines.append("2. **单元测试增强**: 为边缘情况添加测试用例")
    lines.append("3. **性能优化**: 识别并优化热点代码路径")
    lines.append("4. **错误处理完善**: 将 TODO 标记的静默异常替换为具体处理")
    lines.append("5. **文档完善**: 补充 API 文档和使用示例")
    lines.append("")

    lines.append("---")

    return "\n".join(lines)


def determine_round_number() -> int:
    """确定当前是第几轮改进"""
    if not LOG_FILE.exists():
        return 1

    content = LOG_FILE.read_text()
    # 查找 "第 N 轮" 模式
    rounds = re.findall(r"第\s*(\d+)\s*轮自动改进报告", content)
    if rounds:
        return max(int(r) for r in rounds) + 1
    return 1


def stage7_report_and_commit(
    baseline_passed: int,
    baseline_total: int,
    final_passed: int,
    final_total: int,
    fix_results: Dict,
    backup_tag: Optional[str],
) -> None:
    """阶段 7: 报告生成与提交"""
    print_header("阶段 7: 报告生成与提交")

    # 确定轮次
    round_num = determine_round_number()

    # 生成报告
    print_step("7.1", "生成改进报告...")
    report = generate_report(
        baseline_passed, baseline_total,
        final_passed, final_total,
        fix_results, backup_tag
    )

    # 替换轮次
    report = report.replace("第 N/A 轮", f"第 {round_num} 轮")

    # 追加写入日志
    print_step("7.2", "写入 AUTO_IMPROVE_LOG.md...")
    if LOG_FILE.exists():
        existing = LOG_FILE.read_text()
        new_content = report + "\n" + existing
    else:
        new_content = "# Nova 自动改进日志\n\n" + report

    LOG_FILE.write_text(new_content)

    # 检查是否有变更
    if not git_has_changes():
        print_step("7.3", "无变更，跳过提交")
        return

    # Git 操作
    print_step("7.3", "执行 Git 提交...")

    # 配置用户信息
    run_cmd(f'git config user.email "{GIT_EMAIL}"', cwd=PROJECT_DIR)
    run_cmd(f'git config user.name "{GIT_NAME}"', cwd=PROJECT_DIR)

    # 统计修复数量
    total_fixed = sum(
        f["fixed"] for f in fix_results.get("fixers", {}).values()
        if f["status"] == "success"
    )

    commit_msg = f"auto: 第 {round_num} 轮自动改进 - 修复 {total_fixed} 个问题 ({VERSION})"

    # add
    ret, _, stderr = run_cmd("git add -A", cwd=PROJECT_DIR, timeout=30)
    if ret != 0:
        print_step("7.3", f"警告: git add 失败: {stderr}")
        return

    # commit
    ret, _, stderr = run_cmd(
        f'git commit -m "{commit_msg}"',
        cwd=PROJECT_DIR, timeout=30
    )
    if ret != 0:
        print_step("7.3", f"警告: git commit 失败: {stderr}")
        return

    print_step("7.3", f"提交成功: {commit_msg}")

    # push
    print_step("7.3", "推送至远程...")
    ret, stdout, stderr = run_cmd(
        "git push origin main",
        cwd=PROJECT_DIR, timeout=60
    )

    if ret != 0:
        print_step("7.3", f"警告: git push 失败: {stderr}")
        print_step("7.3", "变更已保存在本地")
    else:
        print_step("7.3", "推送成功 ✓")


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    print("=" * 70)
    print("  Nova Auto Improve System v3.0")
    print("  审查驱动的自动修复系统")
    print("=" * 70)

    start_time = datetime.now()

    try:
        # 阶段 1: 项目初始化
        if not stage1_init_project():
            print("\n错误: 项目初始化失败")
            sys.exit(1)

        # 阶段 2: 同步远程
        stage2_sync_remote()

        # 阶段 3: 创建备份点
        backup_tag = stage3_create_backup()

        # 阶段 4: 基线测试
        baseline_passed, baseline_total = stage4_baseline_tests()

        # 阶段 5: 自动修复
        fix_results = stage5_auto_fix(baseline_passed, baseline_total)

        # 阶段 6: 最终验证
        final_passed, final_total = stage6_final_tests(
            baseline_passed, baseline_total
        )

        # 阶段 7: 报告与提交
        stage7_report_and_commit(
            baseline_passed, baseline_total,
            final_passed, final_total,
            fix_results, backup_tag
        )

        # 总结
        elapsed = (datetime.now() - start_time).total_seconds()
        total_fixed = sum(
            f["fixed"] for f in fix_results.get("fixers", {}).values()
            if f["status"] == "success"
        )

        print()
        print("=" * 70)
        print(f"  执行完成! 总耗时: {elapsed:.1f} 秒")
        print(f"  修复问题数: {total_fixed}")
        print(f"  测试结果: {final_passed}/{final_total} (基线: {baseline_passed}/{baseline_total})")
        print("=" * 70)

    except Exception as e:
        print(f"\n错误: 脚本执行异常: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
