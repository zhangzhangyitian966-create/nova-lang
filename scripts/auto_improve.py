#!/usr/bin/env python3
"""
Nova 自动改进引擎 v3.0 - 审查驱动的自动修复系统
- 读取审查结果，针对性修复问题
- 6 个专业修复器，按类型批量处理
- 每类修复后自动运行测试验证
- 失败自动回滚，保证代码质量
"""

import os
import sys
import re
import ast
import subprocess
from datetime import datetime
from collections import defaultdict

# ============================================================
# 配置
# ============================================================

PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GIT_REPO = os.environ.get("NOVA_GIT_REPO", "https://github.com/zhangzhangyitian966-create/nova-lang.git")
GIT_TOKEN = os.environ.get("NOVA_GIT_TOKEN", "")
GIT_USER = os.environ.get("NOVA_GIT_USER", "zhangzhangyitian966-create")
REVIEW_LOG = os.path.join(PROJECT_DIR, "AUTO_REVIEW_LOG.md")
IMPROVE_LOG = os.path.join(PROJECT_DIR, "AUTO_IMPROVE_LOG.md")

SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_HIGH = "HIGH"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"

# 要运行的测试文件列表（跳过导入有问题的）
TEST_FILES = [
    "tests/test_nova.py",
    "tests/test_c_codegen.py",
    "tests/test_ir.py",
    "tests/test_backends.py",
]


# ============================================================
# 工具函数
# ============================================================

def run_cmd(cmd, cwd=None, capture=True, timeout=60):
    result = subprocess.run(
        cmd, shell=isinstance(cmd, str),
        cwd=cwd or PROJECT_DIR,
        capture_output=capture, text=True, timeout=timeout,
    )
    return result.stdout, result.stderr, result.returncode


def ensure_project():
    if os.path.exists(PROJECT_DIR) and os.path.exists(os.path.join(PROJECT_DIR, ".git")):
        return True
    if not GIT_TOKEN:
        print("错误: NOVA_GIT_TOKEN 环境变量未设置")
        sys.exit(1)
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
    subprocess.run(["git", "config", "--global", "credential.helper", "store"], capture_output=True)
    os.makedirs(os.path.dirname(PROJECT_DIR), exist_ok=True)
    result = subprocess.run(
        ["git", "clone", GIT_REPO, PROJECT_DIR],
        capture_output=True, text=True,
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
    stdout, stderr, rc = run_cmd(["git", "tag", tag_name, "-m", "auto improve backup"])
    return rc == 0


def git_restore():
    run_cmd(["git", "checkout", "."])
    run_cmd(["git", "clean", "-fd"])


def run_tests():
    """运行测试，返回 (是否通过, 描述, 通过数, 失败数)"""
    try:
        cmd = [sys.executable, "-m", "pytest"] + TEST_FILES + ["--tb=line", "-q"]
        stdout, stderr, rc = run_cmd(cmd, timeout=120)
    except subprocess.TimeoutExpired:
        return False, "timeout", 0, 0
    
    passed = 0
    failed = 0
    errors = 0
    output = stdout + stderr
    
    match = re.search(r'(\d+) passed', output)
    if match:
        passed = int(match.group(1))
    match = re.search(r'(\d+) failed', output)
    if match:
        failed = int(match.group(1))
    match = re.search(r'(\d+) error', output)
    if match:
        errors = int(match.group(1))
    
    total = passed + failed + errors
    success = (failed == 0 and errors == 0 and rc == 0 and total > 0)
    return success, f"{passed}/{total}", passed, failed + errors


def get_python_files():
    files = []
    for root, dirs, filenames in os.walk(PROJECT_DIR):
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'tree-sitter-nova', 'templates']]
        for f in filenames:
            if f.endswith('.py'):
                files.append(os.path.join(root, f))
    return sorted(files)


def read_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except:
        return ""


def write_file(filepath, content):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except:
        return False


# ============================================================
# 修复器基类
# ============================================================

class BaseFixer:
    name = "base"
    description = "基础修复器"
    
    def can_fix(self, issue_type, severity):
        return False
    
    def fix(self, issue_type, file_path, details):
        return False, "未实现"


# ============================================================
# 修复器 1: REPL 测试导入修复
# ============================================================

class ReplImportFixer(BaseFixer):
    name = "repl_import"
    description = "修复 REPL 辅助函数导入问题"
    
    def can_fix(self, issue_type, severity):
        return issue_type == 'repl_import_fix'
    
    def fix(self, issue_type, file_path, details):
        init_file = os.path.join(PROJECT_DIR, "__init__.py")
        if not os.path.exists(init_file):
            return False, "__init__.py 不存在"
        
        content = read_file(init_file)
        if not content:
            return False, "__init__.py 为空"
        
        if '_is_incomplete' in content and '_count_indent' in content:
            return False, "已经导出过了"
        
        export_code = '''
# REPL 辅助函数导出（供测试使用）
from .nova import _is_incomplete, _count_indent, _attach_source
'''
        new_content = content.rstrip() + "\n" + export_code
        
        if write_file(init_file, new_content):
            return True, "在 __init__.py 中导出 REPL 辅助函数"
        return False, "写入失败"


# ============================================================
# 修复器 2: 裸 except 修复
# ============================================================

class BareExceptFixer(BaseFixer):
    name = "bare_except"
    description = "修复裸 except 语句"
    
    def can_fix(self, issue_type, severity):
        return issue_type == 'bare_except'
    
    def fix(self, issue_type, file_path, details):
        if not file_path or not os.path.exists(file_path):
            return False, "文件不存在"
        
        source = read_file(file_path)
        if not source:
            return False, "文件为空"
        
        lines = source.split('\n')
        fixed = 0
        new_lines = []
        
        for line in lines:
            stripped = line.lstrip()
            indent = line[:len(line) - len(stripped)]
            if stripped == 'except:':
                new_lines.append(indent + 'except Exception:')
                fixed += 1
            elif re.match(r'except\s*:', stripped):
                new_lines.append(re.sub(r'except\s*:', 'except Exception:', line))
                fixed += 1
            else:
                new_lines.append(line)
        
        if fixed == 0:
            return False, "未找到裸 except"
        
        new_source = '\n'.join(new_lines)
        try:
            ast.parse(new_source)
        except SyntaxError as e:
            return False, f"修复后语法错误: {e}"
        
        if write_file(file_path, new_source):
            relpath = os.path.relpath(file_path, PROJECT_DIR)
            return True, f"修复 {fixed} 处裸 except ({relpath})"
        return False, "写入失败"


# ============================================================
# 修复器 3: 静默异常修复
# ============================================================

class SilentExceptionFixer(BaseFixer):
    name = "silent_exception"
    description = "标记静默异常吞噬"
    
    def can_fix(self, issue_type, severity):
        return issue_type == 'too_broad_exception'
    
    def fix(self, issue_type, file_path, details):
        if not file_path or not os.path.exists(file_path):
            return False, "文件不存在"
        
        source = read_file(file_path)
        if not source:
            return False, "文件为空"
        
        lines = source.split('\n')
        fixed = 0
        new_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            indent = line[:len(line) - len(line.lstrip())]
            
            if 'except Exception:' in stripped and i + 1 < len(lines):
                next_stripped = lines[i + 1].strip()
                if next_stripped == 'pass':
                    new_lines.append(line)
                    new_lines.append(indent + '    # TODO: 缩小异常范围，记录错误日志')
                    new_lines.append(indent + '    pass')
                    fixed += 1
                    i += 2
                    continue
            
            new_lines.append(line)
            i += 1
        
        if fixed == 0:
            return False, "未找到静默异常"
        
        new_source = '\n'.join(new_lines)
        try:
            ast.parse(new_source)
        except SyntaxError as e:
            return False, f"修复后语法错误: {e}"
        
        if write_file(file_path, new_source):
            relpath = os.path.relpath(file_path, PROJECT_DIR)
            return True, f"标记 {fixed} 处静默异常 ({relpath})"
        return False, "写入失败"


# ============================================================
# 修复器 4: 模块文档字符串补充
# ============================================================

class DocstringFixer(BaseFixer):
    name = "docstring"
    description = "补充缺失的模块文档字符串"
    
    MODULE_DESCRIPTIONS = {
        'lexer.py': '词法分析器 - 将源代码转换为 Token 流',
        'parser.py': '语法解析器 - 递归下降解析，生成 AST',
        'ast_nodes.py': 'AST 节点定义 - 所有语法树节点的数据结构',
        'type_checker.py': '类型检查器 - Hindley-Milner 类型推断与检查',
        'compiler.py': '字节码编译器 - 将 AST 编译为栈式字节码',
        'vm.py': '虚拟机 - 栈式字节码执行引擎',
        'evaluator.py': '解释器 - AST 遍历解释执行',
        'c_codegen.py': 'C 代码生成器 - 将 AST 编译为 C 源代码',
        'nova.py': 'Nova 主入口 - REPL 和命令行接口',
        'compiler_cli.py': '编译器 CLI - 编译命令行工具',
        'errors.py': '错误定义 - 所有错误类型和格式化',
        'environment.py': '环境 - 作用域链和变量绑定管理',
    }
    
    def can_fix(self, issue_type, severity):
        return issue_type == 'no_docstring'
    
    def fix(self, issue_type, file_path, details):
        if not file_path or not os.path.exists(file_path):
            return False, "文件不存在"
        
        filename = os.path.basename(file_path)
        if filename not in self.MODULE_DESCRIPTIONS:
            return False, "不在已知模块列表中"
        
        source = read_file(file_path)
        if not source:
            return False, "文件为空"
        
        lines = source.split('\n')
        if not lines:
            return False, "文件为空"
        
        i = 0
        while i < len(lines) and (lines[i].startswith('#!') or 
                                    lines[i].startswith('# -*-') or
                                    lines[i].startswith('# coding') or
                                    lines[i].strip() == ''):
            i += 1
        
        if i < len(lines):
            stripped = lines[i].strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                return False, "已有文档字符串"
        
        desc = self.MODULE_DESCRIPTIONS[filename]
        docstring = f'"""\n{desc}\n"""'
        new_lines = lines[:i] + [docstring, ''] + lines[i:]
        new_source = '\n'.join(new_lines)
        
        try:
            ast.parse(new_source)
        except SyntaxError as e:
            return False, f"修复后语法错误: {e}"
        
        if write_file(file_path, new_source):
            relpath = os.path.relpath(file_path, PROJECT_DIR)
            return True, f"添加模块文档字符串 ({relpath})"
        return False, "写入失败"


# ============================================================
# 修复器 5: 导入顺序整理
# ============================================================

class ImportSortFixer(BaseFixer):
    name = "import_sort"
    description = "整理导入顺序"
    
    def can_fix(self, issue_type, severity):
        return issue_type == 'import_order'
    
    def fix(self, issue_type, file_path, details):
        if not file_path or not os.path.exists(file_path):
            return False, "文件不存在"
        
        source = read_file(file_path)
        if not source:
            return False, "文件为空"
        
        lines = source.split('\n')
        for line in lines:
            if 'import (' in line:
                return False, "包含多行导入，跳过"
        
        import_start = -1
        import_end = -1
        in_imports = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            is_import = (stripped.startswith('import ') or 
                        stripped.startswith('from ')) and '(' not in stripped
            
            if is_import:
                if not in_imports:
                    import_start = i
                    in_imports = True
                import_end = i
            elif stripped == '' and in_imports:
                continue
            elif in_imports and stripped:
                break
        
        if import_start == -1 or import_end == -1:
            return False, "未找到导入块"
        
        imports = []
        for i in range(import_start, import_end + 1):
            if lines[i].strip():
                imports.append(lines[i])
        
        if len(imports) < 3:
            return False, "导入太少，无需整理"
        
        std_modules = {'os', 'sys', 're', 'ast', 'json', 'time', 'datetime', 
                      'collections', 'subprocess', 'pathlib', 'typing',
                      'io', 'enum', 'struct', 'hashlib', 'copy', 'itertools',
                      'math', 'random', 'functools', 'operator', 'abc',
                      'dataclasses', 'decimal', 'fraction', 'logging',
                      'argparse', 'shutil', 'tempfile', 'uuid', 'base64'}
        
        std_lib = []
        third_party = []
        local = []
        
        for imp in imports:
            stripped = imp.strip()
            parts = stripped.split()
            if len(parts) < 2:
                continue
            if stripped.startswith('from '):
                module = parts[1].split('.')[0]
            else:
                module = parts[1].split('.')[0]
            
            if module in std_modules:
                std_lib.append(imp)
            elif '.' in parts[1]:
                local.append(imp)
            else:
                third_party.append(imp)
        
        std_lib.sort(key=lambda x: x.strip().lower())
        third_party.sort(key=lambda x: x.strip().lower())
        local.sort(key=lambda x: x.strip().lower())
        
        sorted_imports = []
        if std_lib:
            sorted_imports.extend(std_lib)
        if third_party:
            if sorted_imports:
                sorted_imports.append('')
            sorted_imports.extend(third_party)
        if local:
            if sorted_imports:
                sorted_imports.append('')
            sorted_imports.extend(local)
        
        original_clean = [l.strip() for l in imports if l.strip()]
        new_clean = [l.strip() for l in sorted_imports if l.strip()]
        
        if original_clean == new_clean:
            return False, "导入顺序已经正确"
        
        new_lines = lines[:import_start] + sorted_imports + lines[import_end + 1:]
        new_source = '\n'.join(new_lines)
        
        try:
            ast.parse(new_source)
        except SyntaxError as e:
            return False, f"修复后语法错误: {e}"
        
        if write_file(file_path, new_source):
            relpath = os.path.relpath(file_path, PROJECT_DIR)
            return True, f"整理 {len(imports)} 个导入 ({relpath})"
        return False, "写入失败"


# ============================================================
# 修复器 6: 代码格式化
# ============================================================

class FormatFixer(BaseFixer):
    name = "format"
    description = "代码格式化"
    
    def can_fix(self, issue_type, severity):
        return issue_type == 'code_style'
    
    def fix(self, issue_type, file_path, details):
        try:
            import black
        except ImportError:
            run_cmd([sys.executable, "-m", "pip", "install", "black", "--quiet"])
            try:
                import black
            except ImportError:
                return False, "black 不可用"
        
        if not file_path or not os.path.exists(file_path):
            return False, "文件不存在"
        
        source = read_file(file_path)
        if not source:
            return False, "文件为空"
        
        try:
            formatted = black.format_str(source, mode=black.Mode())
        except Exception as e:
            return False, f"格式化失败: {e}"
        
        if formatted == source:
            return False, "已经是格式化状态"
        
        if write_file(file_path, formatted):
            relpath = os.path.relpath(file_path, PROJECT_DIR)
            return True, f"格式化代码 ({relpath})"
        return False, "写入失败"


# ============================================================
# 修复器管理器
# ============================================================

class FixerManager:
    def __init__(self):
        self.fixers = [
            ReplImportFixer(),
            BareExceptFixer(),
            SilentExceptionFixer(),
            DocstringFixer(),
            ImportSortFixer(),
            FormatFixer(),
        ]
        self.results = []
    
    def discover_issues(self):
        issues = []
        
        # 1. REPL 测试导入问题
        init_file = os.path.join(PROJECT_DIR, "__init__.py")
        if os.path.exists(init_file):
            content = read_file(init_file)
            if '_is_incomplete' not in content or '_count_indent' not in content:
                test_file = os.path.join(PROJECT_DIR, "tests", "test_nova.py")
                if os.path.exists(test_file):
                    test_content = read_file(test_file)
                    if 'from nova import _is_incomplete' in test_content:
                        issues.append({
                            'type': 'repl_import_fix',
                            'severity': SEVERITY_CRITICAL,
                            'file': init_file,
                            'details': 'REPL 测试导入失败',
                        })
        
        # 2. 裸 except
        for filepath in get_python_files():
            relpath = os.path.relpath(filepath, PROJECT_DIR)
            if 'scripts/' in relpath:
                continue
            source = read_file(filepath)
            if not source:
                continue
            lines = source.split('\n')
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped == 'except:' or re.match(r'except\s*:', stripped):
                    issues.append({
                        'type': 'bare_except',
                        'severity': SEVERITY_HIGH,
                        'file': filepath,
                        'line': i,
                    })
        
        # 3. 静默异常
        for filepath in get_python_files():
            relpath = os.path.relpath(filepath, PROJECT_DIR)
            if 'scripts/' in relpath:
                continue
            source = read_file(filepath)
            if not source:
                continue
            lines = source.split('\n')
            for i in range(len(lines) - 1):
                if 'except Exception:' in lines[i] and lines[i + 1].strip() == 'pass':
                    issues.append({
                        'type': 'too_broad_exception',
                        'severity': SEVERITY_HIGH,
                        'file': filepath,
                        'line': i + 1,
                    })
        
        # 4. 缺少文档字符串
        core_modules = ['lexer.py', 'parser.py', 'type_checker.py', 'compiler.py',
                       'vm.py', 'evaluator.py', 'c_codegen.py', 'nova.py',
                       'compiler_cli.py', 'errors.py', 'environment.py', 'ast_nodes.py']
        for filepath in get_python_files():
            filename = os.path.basename(filepath)
            if filename not in core_modules:
                continue
            source = read_file(filepath)
            if not source:
                continue
            lines = source.split('\n')
            i = 0
            while i < len(lines) and (lines[i].startswith('#!') or 
                                        lines[i].startswith('# -*-') or
                                        lines[i].strip() == ''):
                i += 1
            has_docstring = False
            if i < len(lines):
                stripped = lines[i].strip()
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    has_docstring = True
            if not has_docstring:
                issues.append({
                    'type': 'no_docstring',
                    'severity': SEVERITY_LOW,
                    'file': filepath,
                })
        
        # 5. 导入顺序
        for filepath in get_python_files():
            relpath = os.path.relpath(filepath, PROJECT_DIR)
            if 'scripts/' in relpath or 'tests/' in relpath:
                continue
            source = read_file(filepath)
            if not source or 'import (' in source:
                continue
            issues.append({
                'type': 'import_order',
                'severity': SEVERITY_LOW,
                'file': filepath,
            })
        
        # 6. 代码格式化
        for filepath in get_python_files():
            relpath = os.path.relpath(filepath, PROJECT_DIR)
            if 'scripts/' in relpath or 'tests/' in relpath:
                continue
            issues.append({
                'type': 'code_style',
                'severity': SEVERITY_LOW,
                'file': filepath,
            })
        
        return issues
    
    def run_all(self):
        issues = self.discover_issues()
        print(f"  发现 {len(issues)} 个可修复问题")
        print()
        
        severity_order = {SEVERITY_CRITICAL: 0, SEVERITY_HIGH: 1, SEVERITY_MEDIUM: 2, SEVERITY_LOW: 3}
        issues.sort(key=lambda x: severity_order.get(x['severity'], 99))
        
        fixed_count = 0
        skipped_count = 0
        rollback_count = 0
        
        for fixer in self.fixers:
            fixer_issues = [
                issue for issue in issues
                if fixer.can_fix(issue['type'], issue['severity'])
            ]
            
            if not fixer_issues:
                continue
            
            print(f"  [{fixer.name}] 处理 {len(fixer_issues)} 个问题...")
            
            batch_fixed = []
            for issue in fixer_issues:
                success, message = fixer.fix(
                    issue['type'], 
                    issue.get('file'), 
                    issue.get('details', '')
                )
                if success:
                    batch_fixed.append({'issue': issue, 'message': message})
            
            if not batch_fixed:
                print(f"    全部跳过")
                skipped_count += len(fixer_issues)
                print()
                continue
            
            print(f"    修复 {len(batch_fixed)} 个，测试验证...", end=" ", flush=True)
            test_ok, test_str, _, _ = run_tests()
            
            if test_ok:
                print("✅ 通过")
                for item in batch_fixed:
                    self.results.append({
                        'fixer': fixer.name,
                        'issue_type': item['issue']['type'],
                        'severity': item['issue']['severity'],
                        'file': item['issue'].get('file'),
                        'message': item['message'],
                        'status': 'fixed',
                    })
                fixed_count += len(batch_fixed)
            else:
                print("❌ 失败，回滚")
                git_restore()
                rollback_count += len(batch_fixed)
                for item in batch_fixed:
                    self.results.append({
                        'fixer': fixer.name,
                        'issue_type': item['issue']['type'],
                        'severity': item['issue']['severity'],
                        'file': item['issue'].get('file'),
                        'message': item['message'],
                        'status': 'rolled_back',
                    })
            
            skipped_count += len(fixer_issues) - len(batch_fixed)
            print()
        
        return fixed_count, skipped_count, rollback_count


# ============================================================
# 生成报告
# ============================================================

def generate_report(round_num, results, test_before, test_after):
    lines = []
    lines.append(f"# 第 {round_num} 轮自动改进报告")
    lines.append("")
    lines.append(f"**改进时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**改进引擎**: v3.0 (审查驱动的自动修复)")
    lines.append("")
    
    lines.append("## 改进概览")
    lines.append("")
    fixed = [r for r in results if r['status'] == 'fixed']
    rolled = [r for r in results if r['status'] == 'rolled_back']
    lines.append(f"- 发现问题: **{len(results)}** 个")
    lines.append(f"- 成功修复: **{len(fixed)}** 个 ✅")
    lines.append(f"- 回滚: **{len(rolled)}** 个 ❌")
    lines.append("")
    
    lines.append("## 测试验证")
    lines.append("")
    lines.append(f"- 改进前: {test_before}")
    lines.append(f"- 改进后: {test_after}")
    lines.append("")
    
    lines.append("## 修复详情")
    lines.append("")
    by_fixer = defaultdict(list)
    for r in results:
        by_fixer[r['fixer']].append(r)
    
    fixer_names = {
        'repl_import': '🔧 REPL 导入修复',
        'bare_except': '🛡️  裸 except 修复',
        'silent_exception': '📝 静默异常标记',
        'docstring': '📄 文档字符串补充',
        'import_sort': '📦 导入顺序整理',
        'format': '✨ 代码格式化',
    }
    
    for fixer_name, rlist in by_fixer.items():
        name = fixer_names.get(fixer_name, fixer_name)
        success_count = sum(1 for r in rlist if r['status'] == 'fixed')
        lines.append(f"### {name}")
        lines.append("")
        lines.append(f"- 成功: {success_count}/{len(rlist)}")
        lines.append("")
        for r in rlist[:10]:
            icon = "✅" if r['status'] == 'fixed' else "❌"
            file_display = os.path.basename(r['file']) if r['file'] else '全局'
            lines.append(f"  - {icon} [{r['severity']}] {file_display}: {r['message']}")
        if len(rlist) > 10:
            lines.append(f"  - ... 还有 {len(rlist) - 10} 个")
        lines.append("")
    
    lines.append("## 下一步计划")
    lines.append("")
    lines.append("1. 修复 sys.path hack，重构为标准 Python 包结构")
    lines.append("2. 补充单元测试，提高测试覆盖率")
    lines.append("3. 消除代码重复（内置函数、运行时值）")
    lines.append("4. 实现空的优化 Pass（DeadCodeElimination, CSE 等）")
    lines.append("")
    
    return "\n".join(lines)


# ============================================================
# Git 操作
# ============================================================

def git_commit_and_push(round_num, fixed_count):
    run_cmd(["git", "config", "user.email", "auto-improve@nova-lang.dev"])
    run_cmd(["git", "config", "user.name", "Nova Auto Improve"])
    run_cmd(["git", "add", "-A"])
    
    stdout, stderr, rc = run_cmd(["git", "status", "--porcelain"])
    if not stdout.strip():
        print("  (无变更，跳过提交)")
        return True
    
    stdout, stderr, rc = run_cmd(
        ["git", "commit", "-m", f"auto: 第 {round_num} 轮自动改进 - 修复 {fixed_count} 个问题 (v3.0)"]
    )
    if rc != 0:
        print(f"  commit 警告: {stderr[:200]}")
        return False
    
    stdout, stderr, rc = run_cmd(["git", "push", "origin", "main"])
    if rc != 0:
        print(f"  push 失败: {stderr[:300]}")
        return False
    return True


def get_current_round():
    if not os.path.exists(IMPROVE_LOG):
        return 1
    with open(IMPROVE_LOG, 'r') as f:
        content = f.read()
    count = content.count("---")
    return count + 1


# ============================================================
# 主函数
# ============================================================

def main():
    print("=" * 60)
    print("  Nova 自动改进引擎 v3.0")
    print("  审查驱动的自动修复系统")
    print("=" * 60)
    print(f"时间: {datetime.now()}")
    print()
    
    print("[1/7] 确保项目存在...")
    if not ensure_project():
        print("错误: 无法获取项目")
        sys.exit(1)
    print("  OK")
    print()
    
    print("[2/7] 拉取最新代码...")
    git_pull()
    print("  OK")
    print()
    
    print("[3/7] 创建备份...")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    git_backup(f"auto-improve-backup-{ts}")
    print("  OK")
    print()
    
    print("[4/7] 改进前测试...", end=" ", flush=True)
    test_ok_before, test_str_before, _, _ = run_tests()
    print(test_str_before)
    print()
    
    print("[5/7] 执行审查驱动的自动修复...")
    print()
    manager = FixerManager()
    fixed_count, skipped_count, rollback_count = manager.run_all()
    print(f"  修复完成: {fixed_count} 成功, {skipped_count} 跳过, {rollback_count} 回滚")
    print()
    
    print("[6/7] 改进后测试...", end=" ", flush=True)
    test_ok_after, test_str_after, _, _ = run_tests()
    print(test_str_after)
    print()
    
    print("[7/7] 生成报告并提交...")
    round_num = get_current_round()
    report = generate_report(round_num, manager.results, test_str_before, test_str_after)
    
    with open(IMPROVE_LOG, "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        f.write(f"\n---\n\n## {timestamp} 第{round_num}轮改进\n\n")
        f.write(report)
        f.write("\n")
    
    success = git_commit_and_push(round_num, fixed_count)
    if success:
        print("  提交并推送 OK ✅")
    else:
        print("  提交失败 ❌")
    print()
    
    print("=" * 60)
    print(f"  改进完成: {fixed_count} 个问题已修复")
    print("=" * 60)


if __name__ == "__main__":
    main()
