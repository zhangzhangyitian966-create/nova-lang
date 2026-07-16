#!/usr/bin/env python3
"""
自动审查主脚本。
运行方式：python3 scripts/auto_review.py
这个脚本会：
1. 读 vm.py
2. 搜索 TODO/FIXME/pass/NotImplementedError
3. 生成审查报告
4. 追加到 AUTO_REVIEW_LOG.md
5. git commit + push
"""
import os
import re
import subprocess
import sys
from datetime import datetime

PROJECT_DIR = "/workspace/nova"
REVIEW_FILES = [
    "vm.py",
    "compiler.py",
    "evaluator.py",
    "type_checker.py",
    "lexer.py",
    "parser.py",
    "c_codegen.py",
    "errors.py",
    "modules.py",
    "environment.py",
    "ast_nodes.py",
    "backend/native_backend.py",
    "backend/cranelift_backend.py",
    "backend/wasm_backend.py",
    "backend/x86_64.py",
    "backend/compiler_pipeline.py",
    "ir/ir_nodes.py",
    "ir/hir_lowering.py",
    "ir/mir_lowering.py",
    "ir/lir_lowering.py",
    "ir/pass_manager.py",
]

PATTERNS = [
    (r"TODO|FIXME|HACK|XXX", "中等", "遗留标记"),
    (r"NotImplementedError", "严重", "未实现功能"),
    (r"^\s*pass\s*$", "中等", "空实现"),
    (r"raise RuntimeError", "轻微", "运行时错误"),
]

def git(cmd):
    result = subprocess.run(["git"] + cmd, cwd=PROJECT_DIR,
                          capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def review_file(filepath):
    """审查单个文件，返回问题列表"""
    full_path = os.path.join(PROJECT_DIR, filepath)
    if not os.path.exists(full_path):
        return []

    issues = []
    with open(full_path, "r") as f:
        lines = f.readlines()

    for i, line in enumerate(lines, 1):
        for pattern, severity, desc in PATTERNS:
            if re.search(pattern, line):
                # 跳过注释中的 TODO 也算问题，但标注
                context = line.strip()[:80]
                issues.append({
                    "file": filepath,
                    "line": i,
                    "severity": severity,
                    "desc": f"{desc}: {context}",
                })
                break  # 一行只记录一次

    # 检查文件末尾是否有未完成的结构（简单启发式）
    if len(lines) > 0:
        last_lines = "\n".join(lines[-10:])
        if "return" not in last_lines and "pass" not in last_lines:
            if len(lines) > 50:  # 只检查较长的文件
                # 检查最后一个函数/方法是否完整
                pass  # 太复杂，跳过

    return issues

def check_vm_stack_safety(filepath="vm.py"):
    """检查 VM 栈操作安全性"""
    full_path = os.path.join(PROJECT_DIR, filepath)
    if not os.path.exists(full_path):
        return []
    issues = []
    with open(full_path, "r") as f:
        content = f.read()
        lines = content.split("\n")

    # 检查 self.stack.pop() 是否都有对应的 push 或错误检查
    pop_count = len(re.findall(r"self\.stack\.pop\(\)", content))
    push_count = len(re.findall(r"self\.stack\.append\(", content))
    if pop_count > push_count + 10:  # 允许一些误差
        issues.append({
            "file": filepath,
            "line": 0,
            "severity": "严重",
            "desc": f"栈操作不平衡: pop({pop_count}) vs push({push_count})，可能存在栈下溢风险",
        })

    # 检查 CONTINUE 指令是否有实际实现
    for i, line in enumerate(lines, 1):
        if "CONTINUE" in line and "opcode == Op.CONTINUE" in line:
            # 看接下来 10 行有没有实际操作
            block = "\n".join(lines[i:i+10])
            if "pass" in block and "ip =" not in block:
                issues.append({
                    "file": filepath,
                    "line": i,
                    "severity": "严重",
                    "desc": "CONTINUE 指令可能是空实现（while 循环中无跳转逻辑）",
                })
            break

    return issues

def check_type_safety(filepath="type_checker.py"):
    """检查类型安全性"""
    full_path = os.path.join(PROJECT_DIR, filepath)
    if not os.path.exists(full_path):
        return []
    issues = []
    with open(full_path, "r") as f:
        content = f.read()

    # 检查 ADTType.__eq__ 是否比较了 type_params
    if "class ADTType" in content:
        # 找到 ADTType 的 __eq__ 方法
        match = re.search(r"class ADTType.*?def __eq__.*?\n(.*?)(?=\n    def |\nclass |\Z)", content, re.DOTALL)
        if match and "type_params" not in match.group(1) and "type_param" not in match.group(1):
            issues.append({
                "file": filepath,
                "line": 0,
                "severity": "严重",
                "desc": "ADTType.__eq__ 未比较类型参数，Option[Int] == Option[String] 会返回 True，类型安全漏洞",
            })

    return issues

def main():
    print("=== Nova 自动审查 ===")
    print(f"时间: {datetime.now()}")

    # git pull
    print("\n[1/5] git pull...")
    stdout, stderr, rc = git(["pull", "--rebase", "origin", "main"])
    if rc != 0:
        print(f"  警告: git pull 失败: {stderr[:200]}")
    else:
        print("  OK")

    # 确定轮次
    log_path = os.path.join(PROJECT_DIR, "AUTO_REVIEW_LOG.md")
    round_num = 1
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            content = f.read()
        # 数一下有多少轮
        rounds = re.findall(r"第\d+轮", content)
        if rounds:
            # 取最大的数字
            nums = [int(re.search(r"\d+", r).group()) for r in rounds]
            round_num = max(nums) + 1
    print(f"[2/5] 第 {round_num} 轮审查")

    # 审查文件
    print("[3/5] 审查代码...")
    all_issues = []
    for f in REVIEW_FILES:
        issues = review_file(f)
        all_issues.extend(issues)
        if issues:
            print(f"  {f}: {len(issues)} 个问题")

    # 专项检查
    all_issues.extend(check_vm_stack_safety())
    all_issues.extend(check_type_safety())

    # 分类
    severe = [i for i in all_issues if i["severity"] == "严重"]
    medium = [i for i in all_issues if i["severity"] == "中等"]
    mild = [i for i in all_issues if i["severity"] == "轻微"]

    print(f"  总计: {len(all_issues)} 个问题 (严重:{len(severe)} 中等:{len(medium)} 轻微:{len(mild)})")

    # 生成报告
    print("[4/5] 生成审查报告...")
    report_lines = []
    report_lines.append(f"审查文件: {len(REVIEW_FILES)} 个")
    report_lines.append(f"发现问题: {len(all_issues)} 个 (严重:{len(severe)} 中等:{len(medium)} 轻微:{len(mild)})")
    report_lines.append("")

    report_lines.append("### 严重问题")
    for i, issue in enumerate(severe[:15], 1):  # 最多列 15 个
        line_info = f":{issue['line']}" if issue['line'] > 0 else ""
        report_lines.append(f"{i}. [{issue['file']}{line_info}] {issue['desc']}")
        report_lines.append(f"   追问：如果是 OCaml/Haskell 的编译器，这个 bug 能被接受吗？→ 不能，这是必须修复的基础正确性问题")
    if len(severe) > 15:
        report_lines.append(f"... 还有 {len(severe) - 15} 个严重问题")
    if not severe:
        report_lines.append("（无）")
    report_lines.append("")

    report_lines.append("### 中等问题")
    for i, issue in enumerate(medium[:20], 1):
        line_info = f":{issue['line']}" if issue['line'] > 0 else ""
        report_lines.append(f"{i}. [{issue['file']}{line_info}] {issue['desc']}")
    if len(medium) > 20:
        report_lines.append(f"... 还有 {len(medium) - 20} 个中等问题")
    if not medium:
        report_lines.append("（无）")
    report_lines.append("")

    report_lines.append("### 轻微问题")
    for i, issue in enumerate(mild[:20], 1):
        line_info = f":{issue['line']}" if issue['line'] > 0 else ""
        report_lines.append(f"{i}. [{issue['file']}{line_info}] {issue['desc']}")
    if len(mild) > 20:
        report_lines.append(f"... 还有 {len(mild) - 20} 个轻微问题")
    if not mild:
        report_lines.append("（无）")

    report = "\n".join(report_lines)

    # 追加到日志
    append_script = os.path.join(PROJECT_DIR, "scripts", "append_review.py")
    if os.path.exists(append_script):
        tmp_file = os.path.join(PROJECT_DIR, ".review_tmp.md")
        with open(tmp_file, "w") as f:
            f.write(report)
        result = subprocess.run(
            ["python3", "scripts/append_review.py", f"第{round_num}轮全模块自动审查"],
            cwd=PROJECT_DIR,
            input=report,
            capture_output=True,
            text=True,
        )
        os.remove(tmp_file)
        print(f"  {result.stdout.strip()}")
    else:
        print("  警告: append_review.py 不存在，跳过追加")

    # git commit + push
    print("[5/5] 提交推送...")
    git(["add", "-A"])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    stdout, stderr, rc = git(["commit", "-m", f"auto-review: {ts} 第{round_num}轮全模块审查"])
    if rc != 0:
        print(f"  commit: {stderr[:200]}")
    else:
        print("  commit OK")

    stdout, stderr, rc = git(["push", "origin", "main"])
    if rc != 0:
        print(f"  push 警告: {stderr[:200]}")
    else:
        print("  push OK")

    print("\n=== 审查完成 ===")

if __name__ == "__main__":
    main()
