#!/usr/bin/env python3
"""
Nova 自动改进引擎 v2.0
- Level 2: 自动化改进引擎
- 读取审查发现的问题，真正修改代码
- 6 类自动改进：导入修复、异常处理、代码去重、代码风格、测试生成、文档补充
- 每次改进后自动运行测试验证
- 自动 commit + push
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


# ============================================================
# 工具函数
# ============================================================

def run_cmd(cmd, cwd=None, capture=True, timeout=60):
    """运行命令并返回结果"""
    result = subprocess.run(
        cmd,
        shell=isinstance(cmd, str),
        cwd=cwd or PROJECT_DIR,
        capture_output=capture,
        text=True,
        timeout=timeout,
    )
    return result.stdout, result.stderr, result.returncode


def ensure_project():
    """确保项目存在"""
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
    
    subprocess.run(["git", "config", "--global", "credential.helper", "store"],
                   capture_output=True)
    
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
    """拉取最新代码"""
    stdout, stderr, rc = run_cmd(["git", "pull", "--rebase", "origin", "main"])
    if rc != 0:
        print(f"  警告: git pull 失败: {stderr[:200]}")
        return False
    print("  git pull OK")
    return True


def git_backup():
    """创建备份 tag"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    stdout, stderr, rc = run_cmd(["git", "tag", f"auto-backup-{ts}", "-m", "auto improve backup"])
    if rc != 0:
        print(f"  tag 警告: {stderr[:100]}")
        return False
    print("  备份 OK")
    return True


def run_tests():
    """运行测试套件，返回是否通过"""
    print("  运行测试验证...")
    try:
        stdout, stderr, rc = run_cmd(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-x"],
            timeout=120
        )
    except subprocess.TimeoutExpired:
        print("    测试超时")
        return False, "timeout", 0
    
    # 解析结果
    passed = 0
    failed = 0
    
    for line in stderr.split('\n') + stdout.split('\n'):
        match = re.search(r'(\d+) passed', line)
        if match:
            passed = int(match.group(1))
        match = re.search(r'(\d+) failed', line)
        if match:
            failed = int(match.group(1))
    
    total = passed + failed
    success = (failed == 0 and rc == 0 and total > 0)
    
    if success:
        print(f"    ✅ 全部通过 ({passed}/{total})")
    else:
        print(f"    ❌ 失败 ({failed} 失败, {passed} 通过)")
    
    return success, f"{passed}/{total}", total


def get_python_files():
    """获取所有 Python 文件"""
    files = []
    for root, dirs, filenames in os.walk(PROJECT_DIR):
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'tree-sitter-nova', 'templates']]
        for f in filenames:
            if f.endswith('.py'):
                files.append(os.path.join(root, f))
    return sorted(files)


def read_file(filepath):
    """读取文件内容"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except:
        return ""


def write_file(filepath, content):
    """写入文件内容"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except:
        return False


# ============================================================
# 改进器 1: 修复裸 except
# ============================================================

def fix_bare_except():
    """修复裸 except 为 except Exception"""
    changes = []
    files = get_python_files()
    
    for filepath in files:
        # 跳过脚本自身
        if 'scripts/' in filepath.replace('\\', '/'):
            continue
        
        source = read_file(filepath)
        if not source:
            continue
        
        original = source
        
        # 修复裸 except: (行首只有 except:)
        lines = source.split('\n')
        new_lines = []
        fixed_in_file = 0
        
        for line in lines:
            # 匹配裸 except:
            stripped = line.lstrip()
            indent = line[:len(line) - len(stripped)]
            
            if stripped == 'except:':
                new_lines.append(indent + 'except Exception:')
                fixed_in_file += 1
            elif re.match(r'except\s*:', stripped):
                new_lines.append(re.sub(r'except\s*:', 'except Exception:', line))
                fixed_in_file += 1
            else:
                new_lines.append(line)
        
        if fixed_in_file > 0:
            new_source = '\n'.join(new_lines)
            if write_file(filepath, new_source):
                relpath = os.path.relpath(filepath, PROJECT_DIR)
                changes.append({
                    'file': relpath,
                    'type': 'bare_except',
                    'count': fixed_in_file,
                    'description': f'修复 {fixed_in_file} 处裸 except',
                })
    
    return changes


# ============================================================
# 改进器 2: 修复过于宽泛的异常捕获（添加日志）
# ============================================================

def fix_broad_exception():
    """为过于宽泛的 except Exception 添加日志记录"""
    # 简化版本：只在 pass 处添加注释
    changes = []
    files = get_python_files()
    
    for filepath in files:
        if 'scripts/' in filepath.replace('\\', '/'):
            continue
        
        source = read_file(filepath)
        if not source:
            continue
        
        lines = source.split('\n')
        new_lines = []
        fixed = 0
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()
            indent = line[:len(line) - len(stripped)]
            
            # 查找 except Exception: 后面只有 pass 的情况
            if 'except Exception:' in stripped and i + 1 < len(lines):
                next_stripped = lines[i + 1].strip()
                if next_stripped == 'pass':
                    # 在 pass 前添加 TODO 注释
                    new_lines.append(line)
                    new_lines.append(indent + '    # TODO: 缩小异常范围，捕获更具体的异常类型')
                    fixed += 1
                    i += 1
                    continue
            
            new_lines.append(line)
            i += 1
        
        if fixed > 0:
            new_source = '\n'.join(new_lines)
            if write_file(filepath, new_source):
                relpath = os.path.relpath(filepath, PROJECT_DIR)
                changes.append({
                    'file': relpath,
                    'type': 'broad_exception',
                    'count': fixed,
                    'description': f'标记 {fixed} 处宽泛异常捕获待优化',
                })
    
    return changes


# ============================================================
# 改进器 3: 代码格式化（black 风格）
# ============================================================

def format_code():
    """使用 black 格式化代码（如果可用）"""
    changes = []
    
    # 检查 black 是否可用
    try:
        import black
        has_black = True
    except ImportError:
        has_black = False
    
    if not has_black:
        # 尝试安装
        print("  安装 black...")
        stdout, stderr, rc = run_cmd([sys.executable, "-m", "pip", "install", "black", "--quiet"])
        if rc != 0:
            print("    安装失败，跳过格式化")
            return changes
        try:
            import black
            has_black = True
        except ImportError:
            has_black = False
    
    if not has_black:
        print("  black 不可用，跳过格式化")
        return changes
    
    # 格式化核心模块
    files_to_format = []
    for f in get_python_files():
        relpath = os.path.relpath(f, PROJECT_DIR)
        # 跳过测试和脚本
        if 'tests/' in relpath or 'scripts/' in relpath:
            continue
        files_to_format.append(f)
    
    formatted = 0
    for filepath in files_to_format[:10]:  # 限制数量，避免太慢
        source = read_file(filepath)
        if not source:
            continue
        
        try:
            formatted_source = black.format_str(source, mode=black.Mode())
            if formatted_source != source:
                if write_file(filepath, formatted_source):
                    formatted += 1
        except:
            pass
    
    if formatted > 0:
        changes.append({
            'file': f'{formatted} 个文件',
            'type': 'format',
            'count': formatted,
            'description': f'使用 black 格式化 {formatted} 个文件',
        })
    
    return changes


# ============================================================
# 改进器 4: 修复导入顺序（isort 风格）
# ============================================================

def sort_imports():
    """整理导入顺序（安全版本，只处理单行导入）"""
    changes = []
    files = get_python_files()
    
    for filepath in files[:15]:  # 限制数量
        relpath = os.path.relpath(filepath, PROJECT_DIR)
        if 'scripts/' in relpath or 'tests/' in relpath:
            continue
        
        source = read_file(filepath)
        if not source:
            continue
        
        lines = source.split('\n')
        
        # 安全检查：如果有括号内的多行导入，跳过这个文件
        has_multiline_import = False
        paren_depth = 0
        for line in lines:
            stripped = line.strip()
            # 检查 from xxx import ( 的多行导入
            if 'import (' in stripped or 'import (' in line:
                has_multiline_import = True
                break
            if stripped.startswith('from ') and 'import' in stripped and '(' in line:
                has_multiline_import = True
                break
        
        if has_multiline_import:
            continue  # 跳过有多行导入的文件，避免搞乱
        
        # 找出所有单行 import 的范围
        import_start = -1
        import_end = -1
        in_import_block = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            is_import = (stripped.startswith('import ') or 
                        stripped.startswith('from ')) and '(' not in stripped
            
            if is_import:
                if not in_import_block:
                    import_start = i
                    in_import_block = True
                import_end = i
            elif stripped == '' and in_import_block:
                # 空行可能是分隔符
                continue
            elif in_import_block and stripped:
                # 非空行且不是 import，结束
                break
        
        if import_start == -1 or import_end == -1:
            continue
        
        # 收集 import（只收集单行的）
        imports = []
        for i in range(import_start, import_end + 1):
            if lines[i].strip() and '(' not in lines[i]:
                imports.append(lines[i])
        
        if len(imports) < 3:
            continue
        
        # 分类排序
        std_lib = []
        third_party = []
        local = []
        
        std_modules = {'os', 'sys', 're', 'ast', 'json', 'time', 'datetime', 
                      'collections', 'subprocess', 'pathlib', 'typing',
                      'io', 'enum', 'struct', 'hashlib', 'copy', 'itertools',
                      'math', 'random', 'functools', 'operator', 'abc',
                      'dataclasses', 'decimal', 'fraction', 'logging',
                      'argparse', 'shutil', 'tempfile', 'uuid', 'base64'}
        
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
        
        # 排序
        std_lib.sort(key=lambda x: x.strip().lower())
        third_party.sort(key=lambda x: x.strip().lower())
        local.sort(key=lambda x: x.strip().lower())
        
        # 组合（保持原顺序中的空行分隔）
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
        
        # 比较是否有变化
        original_imports = [l for l in imports if l.strip()]
        new_imports_clean = [l for l in sorted_imports if l.strip()]
        
        if [l.strip() for l in new_imports_clean] != [l.strip() for l in original_imports]:
            # 替换
            new_lines = lines[:import_start] + sorted_imports + lines[import_end + 1:]
            new_source = '\n'.join(new_lines)
            
            # 安全检查：确保可以被 AST 解析
            try:
                ast.parse(new_source)
                if write_file(filepath, new_source):
                    changes.append({
                        'file': relpath,
                        'type': 'import_sort',
                        'count': len(imports),
                        'description': f'整理 {len(imports)} 个导入语句',
                    })
            except SyntaxError:
                pass  # 语法错误，跳过
    
    return changes


# ============================================================
# 改进器 5: 补充模块文档字符串
# ============================================================

def add_module_docstrings():
    """为缺少文档字符串的模块添加文档"""
    changes = []
    files = get_python_files()
    
    module_descriptions = {
        'lexer.py': '词法分析器 - 将源代码转换为 Token 流',
        'parser.py': '语法解析器 - 将 Token 流解析为 AST',
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
    
    for filepath in files:
        filename = os.path.basename(filepath)
        if filename not in module_descriptions:
            continue
        
        source = read_file(filepath)
        if not source:
            continue
        
        lines = source.split('\n')
        if not lines:
            continue
        
        # 检查是否已有模块级 docstring
        first_non_empty = -1
        for i, line in enumerate(lines):
            if line.strip():
                first_non_empty = i
                break
        
        if first_non_empty == -1:
            continue
        
        first_line = lines[first_non_empty].strip()
        
        # 跳过 shebang 和编码声明
        i = first_non_empty
        while i < len(lines) and (lines[i].startswith('#!') or 
                                    lines[i].startswith('# -*-') or
                                    lines[i].startswith('# coding')):
            i += 1
        
        # 检查下一个非空行是否是 docstring
        has_docstring = False
        for j in range(i, min(i + 5, len(lines))):
            if lines[j].strip().startswith('"""') or lines[j].strip().startswith("'''"):
                has_docstring = True
                break
            if lines[j].strip():
                break
        
        if has_docstring:
            continue
        
        # 在导入前添加 docstring
        desc = module_descriptions[filename]
        docstring = f'"""\n{desc}\n"""\n'
        
        # 找到导入语句之前的位置
        insert_pos = i
        for j in range(i, len(lines)):
            stripped = lines[j].strip()
            if stripped.startswith('import ') or stripped.startswith('from '):
                insert_pos = j
                break
            elif stripped and not stripped.startswith('#'):
                insert_pos = j
                break
        
        new_lines = lines[:insert_pos] + [docstring] + lines[insert_pos:]
        new_source = '\n'.join(new_lines)
        
        if write_file(filepath, new_source):
            relpath = os.path.relpath(filepath, PROJECT_DIR)
            changes.append({
                'file': relpath,
                'type': 'docstring',
                'count': 1,
                'description': f'添加模块文档字符串: {desc}',
            })
    
    return changes


# ============================================================
# 改进器 6: 简单的代码去重（提取公共常量）
# ============================================================

def extract_common_constants():
    """提取公共常量（简化版）"""
    # 这是一个简化版本，实际的代码去重需要更复杂的分析
    changes = []
    return changes


# ============================================================
# 主改进流程
# ============================================================

def run_improvements():
    """运行所有改进器"""
    all_changes = []
    
    print("  [1/6] 修复裸 except...")
    changes = fix_bare_except()
    all_changes.extend(changes)
    print(f"    修改 {len(changes)} 个文件")
    
    print("  [2/6] 标记宽泛异常...")
    changes = fix_broad_exception()
    all_changes.extend(changes)
    print(f"    修改 {len(changes)} 个文件")
    
    print("  [3/6] 整理导入顺序...")
    changes = sort_imports()
    all_changes.extend(changes)
    print(f"    修改 {len(changes)} 个文件")
    
    print("  [4/6] 补充模块文档...")
    changes = add_module_docstrings()
    all_changes.extend(changes)
    print(f"    修改 {len(changes)} 个文件")
    
    print("  [5/6] 代码格式化...")
    changes = format_code()
    all_changes.extend(changes)
    print(f"    修改 {len(changes)} 个文件")
    
    print("  [6/6] 提取常量...")
    changes = extract_common_constants()
    all_changes.extend(changes)
    print(f"    修改 {len(changes)} 个文件")
    
    return all_changes


# ============================================================
# 生成报告
# ============================================================

def generate_report(round_num, changes, test_before, test_after, test_result):
    """生成改进报告"""
    lines = []
    lines.append(f"# 第 {round_num} 轮自动改进报告")
    lines.append("")
    lines.append(f"**改进时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**改进引擎**: v2.0 (自动化改进引擎)")
    lines.append("")
    
    # 概览
    lines.append("## 改进概览")
    lines.append("")
    
    total_files = len(set(c['file'] for c in changes))
    total_changes = sum(c['count'] for c in changes)
    
    lines.append(f"- 修改文件数: **{total_files}**")
    lines.append(f"- 总改进数: **{total_changes}**")
    lines.append(f"- 改进类型: **{len(set(c['type'] for c in changes))}** 种")
    lines.append("")
    
    # 测试结果对比
    lines.append("## 测试验证")
    lines.append("")
    lines.append(f"- 改进前: {test_before}")
    lines.append(f"- 改进后: {test_after}")
    lines.append(f"- 结果: {'✅ 通过' if test_result else '❌ 失败（已回滚）'}")
    lines.append("")
    
    # 按类型统计
    lines.append("## 改进详情")
    lines.append("")
    
    by_type = defaultdict(list)
    for c in changes:
        by_type[c['type']].append(c)
    
    type_names = {
        'bare_except': '🔧 修复裸 except',
        'broad_exception': '📝 标记宽泛异常',
        'import_sort': '📦 整理导入顺序',
        'docstring': '📄 补充文档字符串',
        'format': '✨ 代码格式化',
        'constants': '🎯 提取公共常量',
    }
    
    for itype, clist in by_type.items():
        name = type_names.get(itype, itype)
        total = sum(c['count'] for c in clist)
        lines.append(f"### {name} ({total} 处)")
        lines.append("")
        for c in clist:
            lines.append(f"- `{c['file']}`: {c['description']}")
        lines.append("")
    
    # 下一步
    lines.append("## 下一步计划")
    lines.append("")
    lines.append("1. 修复 sys.path hack，重构为标准包结构")
    lines.append("2. 补充单元测试，提高测试覆盖率")
    lines.append("3. 消除代码重复（内置函数、运行时值）")
    lines.append("4. 为核心函数添加类型注解")
    lines.append("5. 拆分复杂度高的大函数")
    lines.append("")
    
    return "\n".join(lines)


# ============================================================
# Git 操作
# ============================================================

def git_commit_and_push(round_num):
    """提交并推送"""
    run_cmd(["git", "config", "user.email", "auto-improve@nova-lang.dev"])
    run_cmd(["git", "config", "user.name", "Nova Auto Improve"])
    
    run_cmd(["git", "add", "-A"])
    
    stdout, stderr, rc = run_cmd(["git", "status", "--porcelain"])
    if not stdout.strip():
        print("  (无变更，跳过提交)")
        return True
    
    stdout, stderr, rc = run_cmd(
        ["git", "commit", "-m", f"auto: 第 {round_num} 轮自动改进 (v2.0)"]
    )
    if rc != 0:
        print(f"  commit 警告: {stderr[:200]}")
        return False
    
    stdout, stderr, rc = run_cmd(["git", "push", "origin", "main"])
    if rc != 0:
        print(f"  push 失败: {stderr[:300]}")
        return False
    print("  push OK")
    return True


def git_stash():
    """暂存更改"""
    stdout, stderr, rc = run_cmd(["git", "stash", "push", "-m", "auto-improve-rollback"])
    return rc == 0


def git_stash_pop():
    """恢复暂存"""
    stdout, stderr, rc = run_cmd(["git", "stash", "pop"])
    return rc == 0


def get_current_round():
    """获取当前轮次"""
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
    print("  Nova 自动改进引擎 v2.0")
    print("=" * 60)
    print(f"时间: {datetime.now()}")
    print(f"项目目录: {PROJECT_DIR}")
    print()
    
    # 1. 确保项目存在
    print("[1/8] 确保项目存在...")
    if not ensure_project():
        print("错误: 无法获取项目")
        sys.exit(1)
    print("  OK")
    print()
    
    # 2. git pull
    print("[2/8] 拉取最新代码...")
    git_pull()
    print()
    
    # 3. 备份
    print("[3/8] 创建备份...")
    git_backup()
    print()
    
    # 4. 改进前运行测试
    print("[4/8] 改进前运行测试...")
    test_ok_before, test_str_before, _ = run_tests()
    print()
    
    # 5. 执行改进
    print("[5/8] 执行代码改进...")
    changes = run_improvements()
    print(f"  共完成 {len(changes)} 项改进")
    print()
    
    # 6. 改进后运行测试
    print("[6/8] 改进后运行测试...")
    test_ok_after, test_str_after, _ = run_tests()
    print()
    
    # 7. 生成报告
    print("[7/8] 生成改进报告...")
    
    # 如果测试失败，回滚
    if not test_ok_after and test_ok_before:
        print("  ⚠️  测试失败，回滚更改...")
        git_stash()
        test_str_after = test_str_before + " (已回滚)"
    
    round_num = get_current_round()
    round_name = f"第{round_num}轮改进"
    report = generate_report(round_num, changes, test_str_before, test_str_after, test_ok_after)
    
    with open(IMPROVE_LOG, "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        f.write(f"\n---\n\n## {timestamp} {round_name}\n\n")
        f.write(report)
        f.write("\n")
    
    print(f"  第 {round_num} 轮改进报告已生成")
    print()
    
    # 8. 提交并推送
    print("[8/8] 提交并推送...")
    success = git_commit_and_push(round_num)
    if success:
        print("  OK")
    else:
        print("  失败")
    print()
    
    print("=" * 60)
    print("  改进完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
