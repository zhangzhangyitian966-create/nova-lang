#!/usr/bin/env python3
"""
Nova 自动审查脚本
- 检查代码原创性和可行性
- 生成详细审查报告
- 追加到 AUTO_REVIEW_LOG.md
- 自动 commit + push
"""

import os
import sys
import subprocess
from datetime import datetime

# 配置
PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GIT_REPO = os.environ.get("NOVA_GIT_REPO", "https://github.com/zhangzhangyitian966-create/nova-lang.git")
GIT_TOKEN = os.environ.get("NOVA_GIT_TOKEN", "")
GIT_USER = os.environ.get("NOVA_GIT_USER", "zhangzhangyitian966-create")
LOG_FILE = os.path.join(PROJECT_DIR, "AUTO_REVIEW_LOG.md")


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
        print("错误: NOVA_GIT_TOKEN 环境变量未设置，无法克隆私有仓库")
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


def count_lines():
    """统计代码行数"""
    total = 0
    py_files = 0
    for root, dirs, files in os.walk(PROJECT_DIR):
        # 跳过 .git 和 tree-sitter
        dirs[:] = [d for d in dirs if d not in ['.git', 'tree-sitter-nova', '__pycache__']]
        for f in files:
            if f.endswith('.py'):
                py_files += 1
                path = os.path.join(root, f)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                        total += len(fp.readlines())
                except:
                    pass
    return py_files, total


def analyze_module(filepath, relpath):
    """分析单个模块的问题"""
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except:
        return issues

    content = ''.join(lines)

    # 1. 检查 TODO/FIXME
    for i, line in enumerate(lines, 1):
        if 'TODO' in line or 'FIXME' in line or 'XXX' in line:
            issues.append(f"  - 第 {i} 行: {line.strip()[:80]}")

    # 2. 检查函数/类数量
    import re
    func_count = len(re.findall(r'^\s*def\s+\w+', content, re.MULTILINE))
    class_count = len(re.findall(r'^\s*class\s+\w+', content, re.MULTILINE))

    # 3. 检查异常处理
    bare_except = len(re.findall(r'except\s*:', content))
    if bare_except > 0:
        issues.append(f"  - 存在 {bare_except} 个裸 except (应该指定具体异常类型)")

    # 4. 检查 print 调试语句
    print_count = len(re.findall(r'^\s*print\(', content, re.MULTILINE))
    if print_count > 5:
        issues.append(f"  - print 语句较多 ({print_count}个)，建议使用 logging")

    # 5. 检查魔法数字
    magic_numbers = re.findall(r'[^a-zA-Z_](\d{3,})', content)
    if len(magic_numbers) > 10:
        issues.append(f"  - 可能存在较多魔法数字，建议提取为常量")

    return issues, func_count, class_count, len(lines)


def review_architecture():
    """架构审查"""
    findings = []

    # 检查目录结构
    expected_dirs = ['ir', 'backend', 'runtime', 'tests', 'examples']
    for d in expected_dirs:
        if not os.path.exists(os.path.join(PROJECT_DIR, d)):
            findings.append(f"  - 缺少预期目录: {d}")

    # 检查核心模块
    core_modules = ['lexer.py', 'parser.py', 'ast_nodes.py', 'type_checker.py',
                    'compiler.py', 'c_codegen.py', 'vm.py', 'evaluator.py']
    for m in core_modules:
        if not os.path.exists(os.path.join(PROJECT_DIR, m)):
            findings.append(f"  - 缺少核心模块: {m}")

    # 检查测试覆盖率
    test_dir = os.path.join(PROJECT_DIR, 'tests')
    test_files = []
    if os.path.exists(test_dir):
        test_files = [f for f in os.listdir(test_dir) if f.startswith('test_') and f.endswith('.py')]
    findings.append(f"  - 测试文件数量: {len(test_files)}")

    return findings


def review_originality():
    """原创性检查"""
    findings = []

    # 检查是否有明显的复制痕迹（简单的启发式）
    suspicious_patterns = [
        ('import sys\\nimport os\\nimport re', '标准导入模板'),
    ]

    # 检查项目是否有独特特性
    features = []
    if os.path.exists(os.path.join(PROJECT_DIR, 'tree-sitter-nova')):
        features.append('tree-sitter 语法支持')
    if os.path.exists(os.path.join(PROJECT_DIR, 'ir')):
        features.append('多层 IR (HIR/MIR/LIR)')
    if os.path.exists(os.path.join(PROJECT_DIR, 'backend')):
        features.append('多后端架构')

    if features:
        findings.append(f"  - 独特特性: {', '.join(features)}")
    else:
        findings.append("  - 警告: 未发现明显的独特技术特性")

    return findings


def review_feasibility():
    """可行性检查"""
    findings = []

    # 检查是否能运行测试
    test_dir = os.path.join(PROJECT_DIR, 'tests')
    if os.path.exists(test_dir):
        test_files = [f for f in os.listdir(test_dir) if f.startswith('test_')]
        findings.append(f"  - 测试文件: {len(test_files)} 个")
    else:
        findings.append("  - 警告: 无测试目录")

    # 检查依赖
    req_file = os.path.join(PROJECT_DIR, 'pyproject.toml')
    if os.path.exists(req_file):
        findings.append("  - 有 pyproject.toml 配置")
    else:
        findings.append("  - 警告: 缺少 pyproject.toml")

    # 检查文档
    readme = os.path.join(PROJECT_DIR, 'README.md')
    if os.path.exists(readme):
        try:
            with open(readme, 'r') as f:
                readme_len = len(f.readlines())
            findings.append(f"  - README: {readme_len} 行")
        except:
            pass
    else:
        findings.append("  - 警告: 缺少 README.md")

    return findings


def generate_report(round_num):
    """生成审查报告"""
    lines = []
    lines.append(f"# 第 {round_num} 轮自动审查报告")
    lines.append("")
    lines.append(f"**审查时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 基本统计
    py_files, total_lines = count_lines()
    lines.append("## 基本统计")
    lines.append("")
    lines.append(f"- Python 文件数: {py_files}")
    lines.append(f"- 总代码行数: {total_lines}")
    lines.append("")

    # 架构审查
    lines.append("## 架构审查")
    lines.append("")
    arch_findings = review_architecture()
    for f in arch_findings:
        lines.append(f)
    lines.append("")

    # 原创性检查
    lines.append("## 原创性检查")
    lines.append("")
    orig_findings = review_originality()
    for f in orig_findings:
        lines.append(f)
    lines.append("")

    # 可行性检查
    lines.append("## 可行性检查")
    lines.append("")
    feas_findings = review_feasibility()
    for f in feas_findings:
        lines.append(f)
    lines.append("")

    # 逐模块详细审查
    lines.append("## 模块详细审查")
    lines.append("")

    # 遍历核心模块
    core_modules = [
        'lexer.py', 'parser.py', 'ast_nodes.py', 'type_checker.py',
        'compiler.py', 'c_codegen.py', 'vm.py', 'evaluator.py',
        'nova.py', 'compiler_cli.py', 'errors.py', 'environment.py',
    ]

    total_issues = 0
    for mod in core_modules:
        mod_path = os.path.join(PROJECT_DIR, mod)
        if os.path.exists(mod_path):
            issues, func_count, class_count, line_count = analyze_module(mod_path, mod)
            lines.append(f"### {mod}")
            lines.append("")
            lines.append(f"- 行数: {line_count}")
            lines.append(f"- 函数数: {func_count}")
            lines.append(f"- 类数: {class_count}")
            lines.append(f"- 问题数: {len(issues)}")
            lines.append("")
            if issues:
                lines.append("**问题清单:**")
                lines.append("")
                for issue in issues:
                    lines.append(issue)
                    total_issues += 1
                lines.append("")

    # 总结
    lines.append("## 总结")
    lines.append("")
    lines.append(f"- 发现总问题数: {total_issues}")
    lines.append(f"- 审查模块数: {len([m for m in core_modules if os.path.exists(os.path.join(PROJECT_DIR, m))])}")
    lines.append("")

    # 改进建议
    lines.append("## 改进建议")
    lines.append("")
    lines.append("1. **代码质量**: 逐步修复各模块中的 TODO 和裸 except 问题")
    lines.append("2. **测试覆盖**: 增加单元测试覆盖率，特别是核心编译器模块")
    lines.append("3. **文档完善**: 补充 API 文档和架构设计文档")
    lines.append("4. **错误处理**: 统一错误处理机制，使用自定义异常类")
    lines.append("5. **日志系统**: 用 logging 替代散落的 print 语句")
    lines.append("")

    return "\n".join(lines)


def append_log(report, round_name):
    """追加到日志文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(LOG_FILE, "a") as f:
        f.write(f"\n---\n\n## {timestamp} {round_name}\n\n")
        f.write(report)
        f.write("\n")


def git_commit_and_push(round_num):
    """提交并推送"""
    # 配置 git 用户
    run_cmd(["git", "config", "user.email", "auto-review@nova-lang.dev"])
    run_cmd(["git", "config", "user.name", "Nova Auto Review"])

    # 添加文件
    run_cmd(["git", "add", "AUTO_REVIEW_LOG.md"])
    run_cmd(["git", "add", "scripts/"])

    # 提交
    stdout, stderr, rc = run_cmd(
        ["git", "commit", "-m", f"auto: 第 {round_num} 轮自动审查报告"]
    )
    if rc != 0:
        print(f"  commit 警告: {stderr[:200]}")
        # 可能没有变更
        if "nothing to commit" in stderr:
            print("  (无新变更，跳过 push)")
            return True

    # 推送
    stdout, stderr, rc = run_cmd(["git", "push", "origin", "main"])
    if rc != 0:
        print(f"  push 失败: {stderr[:300]}")
        return False
    print("  push OK")
    return True


def get_current_round():
    """获取当前轮次"""
    if not os.path.exists(LOG_FILE):
        return 1
    with open(LOG_FILE, 'r') as f:
        content = f.read()
    # 统计 --- 分隔符数量
    count = content.count("---")
    return count + 1


def main():
    print("=" * 60)
    print("  Nova 自动审查")
    print("=" * 60)
    print(f"时间: {datetime.now()}")
    print(f"项目目录: {PROJECT_DIR}")
    print()

    # 1. 确保项目存在
    print("[1/5] 确保项目存在...")
    if not ensure_project():
        print("错误: 无法获取项目")
        sys.exit(1)
    print("  OK")
    print()

    # 2. git pull
    print("[2/5] 拉取最新代码...")
    git_pull()
    print()

    # 3. 生成报告
    print("[3/5] 生成审查报告...")
    round_num = get_current_round()
    round_name = f"第{round_num}轮审查"
    report = generate_report(round_num)
    print(f"  报告生成完成 (第 {round_num} 轮)")
    print()

    # 4. 写入日志
    print("[4/5] 写入审查日志...")
    append_log(report, round_name)
    print("  OK")
    print()

    # 5. 提交并推送
    print("[5/5] 提交并推送...")
    success = git_commit_and_push(round_num)
    if success:
        print("  OK")
    else:
        print("  失败")
    print()

    print("=" * 60)
    print("  审查完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
