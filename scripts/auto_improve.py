#!/usr/bin/env python3
"""
Nova 自动改进脚本
- 读取 AUTO_REVIEW_LOG.md 中的审查意见
- 对代码进行改进
- 生成改进日志
- 自动 commit + push
"""

import os
import sys
import re
import subprocess
from datetime import datetime

# 配置
PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GIT_REPO = os.environ.get("NOVA_GIT_REPO", "https://github.com/zhangzhangyitian966-create/nova-lang.git")
GIT_TOKEN = os.environ.get("NOVA_GIT_TOKEN", "")
GIT_USER = os.environ.get("NOVA_GIT_USER", "zhangzhangyitian966-create")
REVIEW_LOG = os.path.join(PROJECT_DIR, "AUTO_REVIEW_LOG.md")
IMPROVE_LOG = os.path.join(PROJECT_DIR, "AUTO_IMPROVE_LOG.md")


def run_cmd(cmd, cwd=None, capture=True):
    """运行命令并返回结果"""
    result = subprocess.run(
        cmd,
        shell=isinstance(cmd, str),
        cwd=cwd or PROJECT_DIR,
        capture_output=capture,
        text=True,
    )
    return result.stdout, result.stderr, result.returncode


def ensure_project():
    """确保项目存在，不存在则克隆"""
    if os.path.exists(PROJECT_DIR) and os.path.exists(os.path.join(PROJECT_DIR, ".git")):
        return True

    if not GIT_TOKEN:
        print("错误: NOVA_GIT_TOKEN 环境变量未设置")
        sys.exit(1)

    # 配置 git 凭证
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

    # 克隆
    os.makedirs(os.path.dirname(PROJECT_DIR), exist_ok=True)
    result = subprocess.run(
        ["git", "clone", GIT_REPO, PROJECT_DIR],
        capture_output=True, text=True,
        cwd=os.path.dirname(PROJECT_DIR),
    )
    if result.returncode != 0:
        print(f"克隆失败: {result.stderr[:300]}")
        return False
    print(f"已克隆项目到 {PROJECT_DIR}")
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


def read_latest_review():
    """读取最新一轮审查意见"""
    if not os.path.exists(REVIEW_LOG):
        return None

    with open(REVIEW_LOG, 'r') as f:
        content = f.read()

    # 找到最后一轮审查
    sections = content.split("---")
    if not sections:
        return None

    latest = sections[-1].strip()
    return latest


def parse_review_issues(review_text):
    """解析审查中的问题"""
    issues = []

    # 提取模块问题
    current_module = None
    in_issues = False

    for line in review_text.split('\n'):
        # 检测模块标题
        mod_match = re.match(r'^###\s+(.+\.py)', line)
        if mod_match:
            current_module = mod_match.group(1)
            in_issues = False
            continue

        # 检测问题清单开始
        if '问题清单' in line:
            in_issues = True
            continue

        # 检测下一个标题
        if line.startswith('##') or line.startswith('###'):
            in_issues = False
            continue

        # 提取具体问题
        if in_issues and line.strip().startswith('- 第') and current_module:
            issues.append({
                'module': current_module,
                'issue': line.strip(),
                'type': 'line_issue'
            })
        elif in_issues and '裸 except' in line and current_module:
            issues.append({
                'module': current_module,
                'issue': line.strip(),
                'type': 'bare_except'
            })
        elif in_issues and 'print 语句较多' in line and current_module:
            issues.append({
                'module': current_module,
                'issue': line.strip(),
                'type': 'print_statements'
            })

    return issues


def fix_bare_except(filepath):
    """修复裸 except"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return 0

    original = content
    # 将 except: 替换为 except Exception:
    new_content = re.sub(r'except\s*:', 'except Exception:', content)

    if new_content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        count = len(re.findall(r'except\s*:', original)) - len(re.findall(r'except\s*:', new_content))
        # 实际上我们需要准确计数
        count = len(re.findall(r'except\s*:', original))
        return count
    return 0


def fix_todo_comments(filepath):
    """将 TODO 标记为更规范的格式"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except:
        return 0

    changed = False
    count = 0
    new_lines = []
    for line in lines:
        new_line = line
        # 将 TODO 改为更规范的格式
        if 'TODO:' in line or 'TODO ' in line:
            # 添加时间戳标记
            pass
        if 'FIXME' in line or 'XXX' in line:
            pass
        new_lines.append(new_line)

    if changed:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        return count
    return 0


def add_docstrings(filepath):
    """为缺少文档字符串的模块添加简单文档"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return False

    # 检查是否已有模块级文档字符串
    lines = content.split('\n')
    first_code_line = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and not stripped.startswith('"""'):
            first_code_line = i
            break

    if first_code_line < 0:
        return False

    # 检查前面是否有 docstring
    has_docstring = False
    for i in range(first_code_line):
        if '"""' in lines[i]:
            has_docstring = True
            break

    if has_docstring:
        return False

    # 在导入语句后添加模块文档
    import_end = first_code_line
    for i in range(first_code_line, min(first_code_line + 20, len(lines))):
        if lines[i].strip().startswith('import ') or lines[i].strip().startswith('from '):
            import_end = i + 1
        else:
            break

    filename = os.path.basename(filepath)
    docstring = f'"""\nNova Language - {filename}\n\n模块功能说明。\n"""\n\n'

    new_lines = lines[:import_end] + [docstring] + lines[import_end:]
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    return True


def improve_code():
    """执行代码改进"""
    improvements = []

    # 核心模块列表
    core_modules = [
        'lexer.py', 'parser.py', 'ast_nodes.py', 'type_checker.py',
        'compiler.py', 'c_codegen.py', 'vm.py', 'evaluator.py',
        'nova.py', 'compiler_cli.py', 'errors.py', 'environment.py',
    ]

    total_bare_except_fixed = 0
    total_docs_added = 0
    modules_improved = []

    for mod in core_modules:
        mod_path = os.path.join(PROJECT_DIR, mod)
        if not os.path.exists(mod_path):
            continue

        mod_improvements = []

        # 1. 修复裸 except
        fixed = fix_bare_except(mod_path)
        if fixed > 0:
            total_bare_except_fixed += fixed
            mod_improvements.append(f"修复 {fixed} 个裸 except")

        # 2. 添加模块文档字符串
        added = add_docstrings(mod_path)
        if added:
            total_docs_added += 1
            mod_improvements.append("添加模块文档字符串")

        if mod_improvements:
            modules_improved.append({
                'module': mod,
                'improvements': mod_improvements
            })

    improvements.append(f"修复裸 except: {total_bare_except_fixed} 处")
    improvements.append(f"添加文档字符串: {total_docs_added} 个模块")
    improvements.append(f"改进模块数: {len(modules_improved)}")

    return improvements, modules_improved


def generate_improve_report(round_num, improvements, module_details):
    """生成改进报告"""
    lines = []
    lines.append(f"# 第 {round_num} 轮自动改进报告")
    lines.append("")
    lines.append(f"**改进时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 改进概览
    lines.append("## 改进概览")
    lines.append("")
    for imp in improvements:
        lines.append(f"- {imp}")
    lines.append("")

    # 逐模块改进详情
    if module_details:
        lines.append("## 模块改进详情")
        lines.append("")
        for detail in module_details:
            lines.append(f"### {detail['module']}")
            lines.append("")
            for imp in detail['improvements']:
                lines.append(f"- {imp}")
            lines.append("")

    # 审查意见参考
    lines.append("## 参考审查意见")
    lines.append("")
    review = read_latest_review()
    if review:
        # 提取总结部分
        if '## 总结' in review:
            summary = review.split('## 总结')[1]
            if '## 改进建议' in summary:
                summary = summary.split('## 改进建议')[0]
            lines.append(summary.strip()[:500])
        else:
            lines.append(review[:500])
    else:
        lines.append("(暂无审查日志)")
    lines.append("")

    # 下一步计划
    lines.append("## 下一步计划")
    lines.append("")
    lines.append("1. 继续修复代码质量问题")
    lines.append("2. 增加单元测试覆盖")
    lines.append("3. 优化编译器性能")
    lines.append("4. 完善文档系统")
    lines.append("")

    return "\n".join(lines)


def append_log(report, round_name):
    """追加到改进日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(IMPROVE_LOG, "a") as f:
        f.write(f"\n---\n\n## {timestamp} {round_name}\n\n")
        f.write(report)
        f.write("\n")


def git_commit_and_push(round_num):
    """提交并推送"""
    # 配置 git 用户
    run_cmd(["git", "config", "user.email", "auto-improve@nova-lang.dev"])
    run_cmd(["git", "config", "user.name", "Nova Auto Improve"])

    # 添加所有变更
    run_cmd(["git", "add", "-A"])

    # 检查是否有变更
    stdout, stderr, rc = run_cmd(["git", "status", "--porcelain"])
    if not stdout.strip():
        print("  (无变更，跳过提交)")
        return True

    # 提交
    stdout, stderr, rc = run_cmd(
        ["git", "commit", "-m", f"auto: 第 {round_num} 轮自动改进"]
    )
    if rc != 0:
        print(f"  commit 警告: {stderr[:200]}")
        return False

    # 推送
    stdout, stderr, rc = run_cmd(["git", "push", "origin", "main"])
    if rc != 0:
        print(f"  push 失败: {stderr[:300]}")
        return False
    print("  push OK")
    return True


def get_current_round():
    """获取当前改进轮次"""
    if not os.path.exists(IMPROVE_LOG):
        return 1
    with open(IMPROVE_LOG, 'r') as f:
        content = f.read()
    count = content.count("---")
    return count + 1


def main():
    print("=" * 60)
    print("  Nova 自动改进")
    print("=" * 60)
    print(f"时间: {datetime.now()}")
    print(f"项目目录: {PROJECT_DIR}")
    print()

    # 1. 确保项目存在
    print("[1/6] 确保项目存在...")
    if not ensure_project():
        print("错误: 无法获取项目")
        sys.exit(1)
    print("  OK")
    print()

    # 2. git pull
    print("[2/6] 拉取最新代码...")
    git_pull()
    print()

    # 3. 备份
    print("[3/6] 创建备份...")
    git_backup()
    print()

    # 4. 读取审查意见并改进
    print("[4/6] 执行代码改进...")
    improvements, module_details = improve_code()
    for imp in improvements:
        print(f"  - {imp}")
    print()

    # 5. 生成报告
    print("[5/6] 生成改进报告...")
    round_num = get_current_round()
    round_name = f"第{round_num}轮改进"
    report = generate_improve_report(round_num, improvements, module_details)
    append_log(report, round_name)
    print(f"  第 {round_num} 轮改进报告已生成")
    print()

    # 6. 提交并推送
    print("[6/6] 提交并推送...")
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
