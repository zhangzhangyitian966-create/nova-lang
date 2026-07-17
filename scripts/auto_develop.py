#!/usr/bin/env python3
"""
Nova 自动开发引擎 v1.0
- Level 3: 自主功能开发系统
- 从开发路线图中选择任务，自主实现新功能
- 每个任务完成后自动测试验证
- 成功则提交，失败则记录并继续下一个任务
"""

import os
import sys
import re
import ast
import subprocess
import json
from datetime import datetime
from collections import defaultdict

PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GIT_REPO = os.environ.get(
    "NOVA_GIT_REPO", "https://github.com/zhangzhangyitian966-create/nova-lang.git"
)
GIT_TOKEN = os.environ.get("NOVA_GIT_TOKEN", "")
GIT_USER = os.environ.get("NOVA_GIT_USER", "zhangzhangyitian966-create")
DEV_LOG = os.path.join(PROJECT_DIR, "AUTO_DEVELOP_LOG.md")
ROADMAP_FILE = os.path.join(PROJECT_DIR, "DEVELOPMENT_ROADMAP.md")
PROGRESS_FILE = os.path.join(PROJECT_DIR, ".dev_progress.json")

TEST_FILES = [
    "tests/test_nova.py",
    "tests/test_c_codegen.py",
    "tests/test_ir.py",
    "tests/test_backends.py",
]


def run_cmd(cmd, cwd=None, capture=True, timeout=60):
    result = subprocess.run(
        cmd,
        shell=isinstance(cmd, str),
        cwd=cwd or PROJECT_DIR,
        capture_output=capture,
        text=True,
        timeout=timeout,
    )
    return result.stdout, result.stderr, result.returncode


def setup_git_credentials():
    if not GIT_TOKEN:
        return
    os.makedirs("/root", exist_ok=True)
    cred_file = "/root/.git-credentials"
    cred_line = f"https://{GIT_USER}:{GIT_TOKEN}@github.com"
    existing = ""
    if os.path.exists(cred_file):
        with open(cred_file, "r") as f:
            existing = f.read()
    if GIT_TOKEN not in existing:
        with open(cred_file, "w") as f:
            f.write(cred_line + "\n")
        os.chmod(cred_file, 0o600)
    run_cmd(["git", "config", "--global", "credential.helper", "store"])


def ensure_project():
    if os.path.exists(PROJECT_DIR) and os.path.exists(
        os.path.join(PROJECT_DIR, ".git")
    ):
        return True
    if not GIT_TOKEN:
        print("错误: NOVA_GIT_TOKEN 环境变量未设置")
        sys.exit(1)
    setup_git_credentials()
    os.makedirs(os.path.dirname(PROJECT_DIR), exist_ok=True)
    result = subprocess.run(
        ["git", "clone", GIT_REPO, PROJECT_DIR],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(PROJECT_DIR),
    )
    if result.returncode != 0:
        print(f"克隆失败: {result.stderr[:300]}")
        return False
    return True


def git_pull():
    stdout, stderr, rc = run_cmd(["git", "pull", "--rebase", "origin", "main"])
    if rc != 0:
        print(f"  警告: git pull 失败: {stderr[:200]}")
        return False
    return True


def git_backup(tag_name):
    stdout, stderr, rc = run_cmd(["git", "tag", tag_name, "-m", "auto dev backup"])
    return rc == 0


def git_restore():
    """安全回滚 - 只回滚源码，保留脚本自身"""
    # 只回滚已追踪的文件，但保留 scripts/ 目录
    run_cmd(["git", "checkout", "--", "ir/", "backend/", "runtime/", "tests/", "*.py"])
    run_cmd(
        [
            "git",
            "checkout",
            "--",
            "cli.py",
            "lexer.py",
            "parser.py",
            "evaluator.py",
            "compiler.py",
            "vm.py",
            "c_codegen.py",
            "type_checker.py",
            "ast_nodes.py",
            "errors.py",
            "environment.py",
            "compiler_cli.py",
        ]
    )


def run_tests():
    try:
        cmd = [sys.executable, "-m", "pytest"] + TEST_FILES + ["--tb=line", "-q"]
        stdout, stderr, rc = run_cmd(cmd, timeout=120)
    except subprocess.TimeoutExpired:
        return False, "timeout", 0, 0

    passed = 0
    failed = 0
    errors = 0
    output = stdout + stderr

    match = re.search(r"(\d+) passed", output)
    if match:
        passed = int(match.group(1))
    match = re.search(r"(\d+) failed", output)
    if match:
        failed = int(match.group(1))
    match = re.search(r"(\d+) error", output)
    if match:
        errors = int(match.group(1))

    total = passed + failed + errors
    success = failed == 0 and errors == 0 and rc == 0 and total > 0
    return success, f"{passed}/{total}", passed, failed + errors


def read_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def write_file(filepath, content):
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception:
        return False


# ============================================================
# 开发任务基类
# ============================================================


class DevTask:
    task_id = ""
    name = ""
    description = ""
    difficulty = ""
    priority = 0
    category = ""
    estimated_effort = ""

    def is_completed(self):
        return False

    def implement(self):
        return False, "未实现"

    def verify(self):
        success, desc, _, _ = run_tests()
        return success, desc


# ============================================================
# 任务1: 死代码消除 Pass
# ============================================================


class TaskDCE(DevTask):
    task_id = "dce_pass"
    name = "实现死代码消除 Pass"
    description = "在 HIR 层实现 DeadCodeElimination Pass，移除未使用的 let 绑定"
    difficulty = "easy"
    priority = 90
    category = "optimization"
    estimated_effort = "1-2 小时"

    def is_completed(self):
        filepath = os.path.join(PROJECT_DIR, "ir", "pass_manager.py")
        content = read_file(filepath)
        if not content:
            return False
        lines = content.split("\n")
        in_dce = False
        for i, line in enumerate(lines):
            if "class DeadCodeElimination" in line:
                in_dce = True
                continue
            if in_dce and line.startswith("class "):
                break
            if in_dce and "def run(self" in line:
                method_lines = []
                for j in range(i + 1, len(lines)):
                    if (
                        lines[j].strip()
                        and not lines[j].startswith(" " * 8)
                        and not lines[j].startswith("\t")
                    ):
                        if lines[j].startswith("class ") or lines[j].startswith("def "):
                            break
                    method_lines.append(lines[j])
                method_body = "\n".join(method_lines).strip()
                if method_body == "return False" or method_body == "pass":
                    return False
                if len(method_body) < 100:
                    return False
                return True
        return False

    def implement(self):
        filepath = os.path.join(PROJECT_DIR, "ir", "pass_manager.py")
        content = read_file(filepath)
        if not content:
            return False, "无法读取 pass_manager.py"
        if self.is_completed():
            return False, "已经实现过了"

        lines = content.split("\n")
        new_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            if "class DeadCodeElimination(Pass):" in line:
                dce_code = '''class DeadCodeElimination(Pass):
    """死代码消除

    移除未使用的 let 绑定和无副作用的表达式语句。
    """

    name = "dead_code_elimination"

    PURE_OPS = {
        "+", "-", "*", "/", "%", "==", "!=", "<", ">", "<=", ">=",
        "&&", "||",
    }

    def run(self, hir_module):
        changed = False
        for decl in hir_module.declarations:
            if isinstance(decl, HIRFnDecl):
                changed |= self._eliminate_fn(decl.fn_def)
            elif isinstance(decl, HIRLetDecl):
                pass
        return changed

    def _eliminate_fn(self, fn):
        return self._eliminate_expr(fn.body)

    def _eliminate_expr(self, expr):
        changed = False
        if isinstance(expr, HIRBlockExpr):
            changed |= self._eliminate_block(expr)
        elif isinstance(expr, HIRIfExpr):
            changed |= self._eliminate_expr(expr.condition)
            changed |= self._eliminate_expr(expr.consequence)
            if expr.alternative:
                changed |= self._eliminate_expr(expr.alternative)
        elif isinstance(expr, HIRBinaryOp):
            changed |= self._eliminate_expr(expr.left)
            changed |= self._eliminate_expr(expr.right)
        return changed

    def _eliminate_block(self, block):
        changed = False
        if not hasattr(block, "stmts") or not block.stmts:
            return changed

        used_names = set()
        for stmt in block.stmts:
            self._collect_used_names(stmt, used_names)
        if hasattr(block, "result") and block.result:
            self._collect_used_names(block.result, used_names)

        new_stmts = []
        for stmt in block.stmts:
            if isinstance(stmt, HIRLetDecl):
                if stmt.name in used_names:
                    new_stmts.append(stmt)
                else:
                    if self._has_side_effect(stmt.value):
                        new_stmts.append(stmt)
                    else:
                        changed = True
            else:
                new_stmts.append(stmt)

        if changed:
            block.stmts = new_stmts

        for stmt in block.stmts:
            if hasattr(stmt, "value"):
                changed |= self._eliminate_expr(stmt.value)
            if hasattr(stmt, "fn_def"):
                changed |= self._eliminate_fn(stmt.fn_def)

        if hasattr(block, "result") and block.result:
            changed |= self._eliminate_expr(block.result)

        return changed

    def _collect_used_names(self, expr, used):
        if isinstance(expr, HIRIdentifier):
            used.add(expr.name)
        elif isinstance(expr, HIRBinaryOp):
            self._collect_used_names(expr.left, used)
            self._collect_used_names(expr.right, used)
        elif isinstance(expr, HIRUnaryOp):
            self._collect_used_names(expr.operand, used)
        elif isinstance(expr, HIRIfExpr):
            self._collect_used_names(expr.condition, used)
            self._collect_used_names(expr.consequence, used)
            if expr.alternative:
                self._collect_used_names(expr.alternative, used)
        elif isinstance(expr, HIRCallExpr):
            self._collect_used_names(expr.fn_expr, used)
            for arg in expr.args:
                self._collect_used_names(arg, used)
        elif hasattr(expr, "stmts"):
            for stmt in expr.stmts:
                self._collect_used_names(stmt, used)
            if hasattr(expr, "result") and expr.result:
                self._collect_used_names(expr.result, used)
        elif isinstance(expr, HIRLetDecl):
            self._collect_used_names(expr.value, used)

    def _has_side_effect(self, expr):
        if isinstance(expr, HIRCallExpr):
            return True
        if isinstance(expr, HIRBinaryOp):
            if expr.op in self.PURE_OPS:
                return self._has_side_effect(expr.left) or self._has_side_effect(expr.right)
            return True
        if isinstance(expr, HIRUnaryOp):
            return self._has_side_effect(expr.operand)
        if isinstance(expr, HIRIfExpr):
            return (self._has_side_effect(expr.condition) or
                    self._has_side_effect(expr.consequence) or
                    (expr.alternative and self._has_side_effect(expr.alternative)))
        if hasattr(expr, "stmts"):
            for stmt in expr.stmts:
                if hasattr(stmt, "value") and self._has_side_effect(stmt.value):
                    return True
            if hasattr(expr, "result") and expr.result:
                return self._has_side_effect(expr.result)
            return False
        return False
'''
                new_lines.append(dce_code.rstrip())
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    if (
                        next_line
                        and not next_line.startswith(" ")
                        and not next_line.startswith("\t")
                        and next_line.strip()
                    ):
                        if next_line.startswith("class ") or next_line.startswith("@"):
                            break
                    i += 1
                continue

            new_lines.append(line)
            i += 1

        new_content = "\n".join(new_lines)
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            return False, f"实现后语法错误: {e}"

        if write_file(filepath, new_content):
            return True, "实现了死代码消除 Pass (DCE)"
        return False, "写入失败"


# ============================================================
# 任务2: 修复原生后端测试导入
# ============================================================


class TaskFixNativeTestImport(DevTask):
    task_id = "fix_native_test_import"
    name = "修复原生后端测试导入"
    description = "修复 test_native_backend.py 中的导入路径"
    difficulty = "easy"
    priority = 85
    category = "test"
    estimated_effort = "30 分钟"

    def is_completed(self):
        filepath = os.path.join(PROJECT_DIR, "tests", "test_native_backend.py")
        if not os.path.exists(filepath):
            return True
        content = read_file(filepath)
        if not content:
            return True
        if "from nova.backend" in content:
            return False
        return True

    def implement(self):
        filepath = os.path.join(PROJECT_DIR, "tests", "test_native_backend.py")
        if not os.path.exists(filepath):
            return False, "测试文件不存在"

        content = read_file(filepath)
        if not content:
            return False, "文件为空"

        other_test = os.path.join(PROJECT_DIR, "tests", "test_backends.py")
        other_content = read_file(other_test)
        sys_path_line = ""
        for line in other_content.split("\n"):
            if "sys.path.insert" in line:
                sys_path_line = line
                break

        if not sys_path_line:
            return False, "找不到参考的导入模式"

        lines = content.split("\n")
        new_lines = []
        added_sys_path = False

        for line in lines:
            if "from nova.backend" in line:
                if not added_sys_path:
                    new_lines.append("import sys")
                    new_lines.append("import os")
                    new_lines.append(sys_path_line)
                    new_lines.append("")
                    added_sys_path = True
                new_line = line.replace("from nova.backend", "from backend")
                new_lines.append(new_line)
            elif line.startswith("import nova"):
                continue
            else:
                new_lines.append(line)

        new_content = "\n".join(new_lines)

        try:
            ast.parse(new_content)
        except SyntaxError as e:
            return False, f"修复后语法错误: {e}"

        if write_file(filepath, new_content):
            return True, "修复了原生后端测试导入路径"
        return False, "写入失败"


# ============================================================
# 任务3: 函数内联 Pass 框架
# ============================================================


class TaskInlining(DevTask):
    task_id = "inlining_pass"
    name = "实现函数内联 Pass 框架"
    description = "在 HIR 层实现 Inlining Pass 框架，识别可内联函数"
    difficulty = "medium"
    priority = 75
    category = "optimization"
    estimated_effort = "2-4 小时"

    def is_completed(self):
        filepath = os.path.join(PROJECT_DIR, "ir", "pass_manager.py")
        content = read_file(filepath)
        if not content:
            return False
        lines = content.split("\n")
        in_inlining = False
        for i, line in enumerate(lines):
            if "class Inlining(Pass):" in line:
                in_inlining = True
                continue
            if in_inlining and line.startswith("class "):
                break
            if in_inlining and "def run(self" in line:
                method_lines = []
                for j in range(i + 1, len(lines)):
                    if (
                        lines[j].strip()
                        and not lines[j].startswith(" " * 8)
                        and not lines[j].startswith("\t")
                    ):
                        if lines[j].startswith("class ") or lines[j].startswith("def "):
                            break
                    method_lines.append(lines[j])
                method_body = "\n".join(method_lines).strip()
                if method_body == "return False" or method_body == "pass":
                    return False
                if len(method_body) < 100:
                    return False
                return True
        return False

    def implement(self):
        filepath = os.path.join(PROJECT_DIR, "ir", "pass_manager.py")
        content = read_file(filepath)
        if not content:
            return False, "无法读取 pass_manager.py"
        if self.is_completed():
            return False, "已经实现过了"

        lines = content.split("\n")
        new_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            if "class Inlining(Pass):" in line:
                inlining_code = '''class Inlining(Pass):
    """函数内联

    内联小型函数（单表达式函数体、无递归、参数少）。
    当前版本：框架实现，识别可内联函数。
    """

    name = "inlining"
    MAX_INLINE_SIZE = 3
    MAX_PARAMS = 4

    def run(self, hir_module):
        changed = False
        inlineable = {}
        for decl in hir_module.declarations:
            if isinstance(decl, HIRFnDecl):
                fn = decl.fn_def
                if self._is_inlineable(fn):
                    inlineable[fn.name] = fn

        if not inlineable:
            return False

        for decl in hir_module.declarations:
            if isinstance(decl, HIRFnDecl):
                changed |= self._scan_fn(decl.fn_def, inlineable)

        return changed

    def _is_inlineable(self, fn):
        if fn.is_recursive:
            return False
        if len(fn.params) > self.MAX_PARAMS:
            return False
        body = fn.body
        if isinstance(body, HIRBlockExpr):
            if hasattr(body, "stmts") and not body.stmts:
                if hasattr(body, "result") and body.result:
                    return True
            return False
        return not isinstance(body, HIRBlockExpr)

    def _scan_fn(self, fn, inlineable):
        return self._scan_expr(fn.body, inlineable)

    def _scan_expr(self, expr, inlineable):
        changed = False
        if isinstance(expr, HIRCallExpr):
            for arg in expr.args:
                changed |= self._scan_expr(arg, inlineable)
            if isinstance(expr.fn_expr, HIRIdentifier):
                if expr.fn_expr.name in inlineable:
                    pass
        elif isinstance(expr, HIRBinaryOp):
            changed |= self._scan_expr(expr.left, inlineable)
            changed |= self._scan_expr(expr.right, inlineable)
        elif isinstance(expr, HIRIfExpr):
            changed |= self._scan_expr(expr.condition, inlineable)
            changed |= self._scan_expr(expr.consequence, inlineable)
            if expr.alternative:
                changed |= self._scan_expr(expr.alternative, inlineable)
        return changed
'''
                new_lines.append(inlining_code.rstrip())
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    if (
                        next_line
                        and not next_line.startswith(" ")
                        and not next_line.startswith("\t")
                        and next_line.strip()
                    ):
                        if next_line.startswith("class ") or next_line.startswith("@"):
                            break
                    i += 1
                continue

            new_lines.append(line)
            i += 1

        new_content = "\n".join(new_lines)
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            return False, f"实现后语法错误: {e}"

        if write_file(filepath, new_content):
            return True, "实现了函数内联 Pass 框架"
        return False, "写入失败"


# ============================================================
# 任务注册表
# ============================================================

ALL_TASKS = [
    TaskDCE(),
    TaskFixNativeTestImport(),
    TaskInlining(),
]


# ============================================================
# 自动开发引擎
# ============================================================


class AutoDeveloper:
    def __init__(self):
        self.completed_tasks = []
        self.failed_tasks = []
        self.results = []

    def load_progress(self):
        if os.path.exists(PROGRESS_FILE):
            try:
                with open(PROGRESS_FILE, "r") as f:
                    data = json.load(f)
                    self.completed_tasks = data.get("completed", [])
                    self.failed_tasks = data.get("failed", [])
            except Exception:
                pass

    def save_progress(self):
        data = {
            "completed": self.completed_tasks,
            "failed": self.failed_tasks,
            "last_update": datetime.now().isoformat(),
        }
        try:
            with open(PROGRESS_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def get_next_task(self):
        candidates = []
        for task in ALL_TASKS:
            if task.task_id in self.completed_tasks:
                continue
            if task.task_id in self.failed_tasks:
                continue
            if task.is_completed():
                self.completed_tasks.append(task.task_id)
                continue
            candidates.append(task)

        if not candidates:
            return None

        candidates.sort(key=lambda t: -t.priority)
        return candidates[0]

    def run_task(self, task):
        print(f"  🚀 开发任务: {task.name}")
        print(f"     难度: {task.difficulty} | 预估: {task.estimated_effort}")
        print(f"     描述: {task.description}")
        print()

        backup_tag = (
            f"dev-backup-{task.task_id}-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        git_backup(backup_tag)

        print("     实现中...", end=" ", flush=True)
        success, msg = task.implement()

        if not success:
            print(f"❌ {msg}")
            self.failed_tasks.append(task.task_id)
            self.results.append(
                {
                    "task_id": task.task_id,
                    "task_name": task.name,
                    "status": "failed",
                    "message": msg,
                }
            )
            git_restore()
            return False

        print(f"✅ {msg}")

        print("     验证中...", end=" ", flush=True)
        verify_ok, verify_msg = task.verify()

        if not verify_ok:
            print(f"❌ {verify_msg}")
            print("     回滚中...", end=" ", flush=True)
            git_restore()
            print("已回滚")
            self.failed_tasks.append(task.task_id)
            self.results.append(
                {
                    "task_id": task.task_id,
                    "task_name": task.name,
                    "status": "rolled_back",
                    "message": f"{msg} | 验证失败: {verify_msg}",
                }
            )
            return False

        print(f"✅ {verify_msg}")
        self.completed_tasks.append(task.task_id)
        self.results.append(
            {
                "task_id": task.task_id,
                "task_name": task.name,
                "status": "completed",
                "message": msg,
            }
        )
        return True

    def run_cycle(self, max_tasks=3):
        completed = 0
        for _ in range(max_tasks):
            task = self.get_next_task()
            if not task:
                break
            if self.run_task(task):
                completed += 1
            print()
        return completed


# ============================================================
# 报告
# ============================================================


def generate_report(cycle_num, results, test_before, test_after):
    lines = []
    lines.append(f"# 第 {cycle_num} 轮自动开发报告")
    lines.append("")
    lines.append(f"**开发时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**开发引擎**: v1.0 (自主功能开发系统)")
    lines.append("")

    lines.append("## 开发概览")
    lines.append("")
    completed = [r for r in results if r["status"] == "completed"]
    failed = [r for r in results if r["status"] == "failed"]
    rolled = [r for r in results if r["status"] == "rolled_back"]

    lines.append(f"- 尝试任务: **{len(results)}** 个")
    lines.append(f"- 成功完成: **{len(completed)}** 个 ✅")
    lines.append(f"- 实现失败: **{len(failed)}** 个 ❌")
    lines.append(f"- 验证回滚: **{len(rolled)}** 个 ↩️")
    lines.append("")

    lines.append("## 测试验证")
    lines.append("")
    lines.append(f"- 开发前: {test_before}")
    lines.append(f"- 开发后: {test_after}")
    lines.append("")

    lines.append("## 开发详情")
    lines.append("")

    for result in results:
        icon = {"completed": "✅", "failed": "❌", "rolled_back": "↩️"}.get(
            result["status"], "❓"
        )
        status = {
            "completed": "已完成",
            "failed": "实现失败",
            "rolled_back": "验证失败已回滚",
        }.get(result["status"], "未知")
        lines.append(f"### {icon} {result['task_name']} ({status})")
        lines.append("")
        lines.append(f"- **ID**: {result['task_id']}")
        lines.append(f"- **结果**: {result['message']}")
        lines.append("")

    lines.append("## 路线图进度")
    lines.append("")
    total = len(ALL_TASKS)
    done = len(
        [
            t
            for t in ALL_TASKS
            if t.is_completed()
            or t.task_id
            in [r["task_id"] for r in results if r["status"] == "completed"]
        ]
    )
    lines.append(f"- 总任务数: {total}")
    lines.append(f"- 已完成: {done}")
    lines.append(f"- 进度: {done/total*100:.0f}%")
    lines.append("")

    return "\n".join(lines)


def generate_roadmap():
    lines = []
    lines.append("# Nova 自动开发路线图")
    lines.append("")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("本路线图由自动开发系统维护，按优先级排序。")
    lines.append("")

    categories = defaultdict(list)
    for task in ALL_TASKS:
        categories[task.category].append(task)

    cat_names = {
        "optimization": "🚀 优化 Pass",
        "ir": "🔧 IR 降级",
        "backend": "⚙️  后端开发",
        "stdlib": "📚 标准库",
        "test": "🧪 测试完善",
    }

    for cat, tasks in sorted(categories.items()):
        name = cat_names.get(cat, cat)
        lines.append(f"## {name}")
        lines.append("")
        lines.append("| 状态 | 任务 | 难度 | 优先级 | 预估 |")
        lines.append("|------|------|------|--------|------|")
        for task in sorted(tasks, key=lambda t: -t.priority):
            status = "✅" if task.is_completed() else "⏳"
            lines.append(
                f"| {status} | {task.name} | {task.difficulty} | {task.priority} | {task.estimated_effort} |"
            )
        lines.append("")

    return "\n".join(lines)


# ============================================================
# Git
# ============================================================


def git_commit_and_push(cycle_num, completed_count):
    run_cmd(["git", "config", "user.email", "auto-dev@nova-lang.dev"])
    run_cmd(["git", "config", "user.name", "Nova Auto Developer"])
    run_cmd(["git", "add", "-A"])

    stdout, stderr, rc = run_cmd(["git", "status", "--porcelain"])
    if not stdout.strip():
        print("  (无变更，跳过提交)")
        return True

    stdout, stderr, rc = run_cmd(
        [
            "git",
            "commit",
            "-m",
            f"auto: 第 {cycle_num} 轮自动开发 - {completed_count} 个功能 (v1.0)",
        ]
    )
    if rc != 0:
        print(f"  commit 警告: {stderr[:200]}")
        return False

    stdout, stderr, rc = run_cmd(["git", "push", "origin", "main"])
    if rc != 0:
        print(f"  push 失败: {stderr[:300]}")
        return False
    return True


def get_current_cycle():
    if not os.path.exists(DEV_LOG):
        return 1
    with open(DEV_LOG, "r") as f:
        content = f.read()
    count = content.count("---")
    return count + 1


# ============================================================
# 主函数
# ============================================================


def main():
    print("=" * 60)
    print("  Nova 自动开发引擎 v1.0")
    print("  自主功能开发系统")
    print("=" * 60)
    print(f"时间: {datetime.now()}")
    print()

    print("[1/7] 确保项目存在...")
    if not ensure_project():
        print("错误: 无法获取项目")
        sys.exit(1)
    setup_git_credentials()
    print("  OK")
    print()

    print("[2/7] 拉取最新代码...")
    git_pull()
    print("  OK")
    print()

    print("[3/7] 创建备份...")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    git_backup(f"auto-dev-backup-{ts}")
    print("  OK")
    print()

    print("[4/7] 开发前测试...", end=" ", flush=True)
    test_ok_before, test_str_before, _, _ = run_tests()
    print(test_str_before)
    print()

    print("[5/7] 执行自动开发...")
    print()

    developer = AutoDeveloper()
    developer.load_progress()
    completed = developer.run_cycle(max_tasks=3)
    developer.save_progress()

    roadmap = generate_roadmap()
    write_file(ROADMAP_FILE, roadmap)

    print(f"  本轮完成: {completed} 个任务")
    print()

    print("[6/7] 开发后测试...", end=" ", flush=True)
    test_ok_after, test_str_after, _, _ = run_tests()
    print(test_str_after)
    print()

    print("[7/7] 生成报告并提交...")
    cycle_num = get_current_cycle()
    report = generate_report(
        cycle_num, developer.results, test_str_before, test_str_after
    )

    with open(DEV_LOG, "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        f.write(f"\n---\n\n## {timestamp} 第{cycle_num}轮开发\n\n")
        f.write(report)
        f.write("\n")

    success = git_commit_and_push(cycle_num, completed)
    if success:
        print("  提交并推送 OK ✅")
    else:
        print("  提交失败 ❌")
    print()

    print("=" * 60)
    print(f"  开发完成: {completed} 个新功能已上线")
    print("=" * 60)


if __name__ == "__main__":
    main()
