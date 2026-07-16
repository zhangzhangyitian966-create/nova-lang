#!/usr/bin/env python3
"""
Nova LLM 智能开发系统 - 状态管理与工具函数

提供：
- 开发状态持久化（JSON）
- 开发日志管理
- Git 备份与回滚
- 测试运行工具
- 路线图生成
"""

import os
import sys
import re
import json
import subprocess
from datetime import datetime
from collections import defaultdict

# 配置
PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE = os.path.join(PROJECT_DIR, ".llm_dev_state.json")
DEV_LOG = os.path.join(PROJECT_DIR, "LLM_DEV_LOG.md")
ROADMAP_FILE = os.path.join(PROJECT_DIR, "LLM_ROADMAP.md")

TEST_FILES = [
    "tests/test_nova.py",
    "tests/test_c_codegen.py",
    "tests/test_ir.py",
    "tests/test_backends.py",
]


def run_cmd(cmd, cwd=None, capture=True, timeout=120):
    """运行命令"""
    result = subprocess.run(
        cmd, shell=isinstance(cmd, str),
        cwd=cwd or PROJECT_DIR,
        capture_output=capture, text=True, timeout=timeout,
    )
    return result.stdout, result.stderr, result.returncode


def git_backup(tag_name):
    """创建备份 tag"""
    stdout, stderr, rc = run_cmd(["git", "tag", tag_name, "-m", f"LLM dev backup: {tag_name}"])
    return rc == 0


def git_restore_to_tag(tag_name):
    """回滚到指定 tag"""
    run_cmd(["git", "reset", "--hard", tag_name])
    run_cmd(["git", "clean", "-fd"])


def git_restore_hard():
    """硬回滚到 HEAD"""
    run_cmd(["git", "checkout", "."])
    run_cmd(["git", "clean", "-fd"])


def git_commit_and_push(message):
    """提交并推送"""
    run_cmd(["git", "config", "user.email", "llm-dev@nova-lang.dev"])
    run_cmd(["git", "config", "user.name", "Nova LLM Developer"])
    run_cmd(["git", "add", "-A"])
    stdout, stderr, rc = run_cmd(["git", "status", "--porcelain"])
    if not stdout.strip():
        return True, "无变更"
    stdout, stderr, rc = run_cmd(["git", "commit", "-m", message])
    if rc != 0:
        return False, f"commit 失败: {stderr[:200]}"
    stdout, stderr, rc = run_cmd(["git", "push", "origin", "main"])
    if rc != 0:
        return False, f"push 失败: {stderr[:200]}"
    return True, "成功"


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


def load_state():
    """加载开发状态"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        'cycles': 0,
        'completed_tasks': [],
        'failed_tasks': [],
        'task_history': [],
        'current_cycle': None,
    }


def save_state(state):
    """保存开发状态"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except:
        pass


def append_log(content, cycle_num):
    """追加开发日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(DEV_LOG, "a") as f:
        f.write(f"\n---\n\n## {timestamp} 第{cycle_num}轮LLM智能开发\n\n")
        f.write(content)
        f.write("\n")


def get_cycle_num():
    """获取当前轮次"""
    state = load_state()
    return state.get('cycles', 0) + 1


def generate_roadmap(tasks):
    """生成路线图文档"""
    lines = []
    lines.append("# Nova LLM 智能开发路线图")
    lines.append("")
    lines.append(f"**更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("本路线图由 LLM 智能开发系统动态维护。")
    lines.append("")
    
    # 按分类分组
    categories = defaultdict(list)
    for task in tasks:
        categories[task.get('category', 'other')].append(task)
    
    cat_names = {
        'optimization': '🚀 优化 Pass',
        'ir': '🔧 IR 降级',
        'backend': '⚙️  后端开发',
        'stdlib': '📚 标准库',
        'test': '🧪 测试完善',
        'refactor': '♻️  代码重构',
        'feature': '✨ 新功能',
    }
    
    for cat, cat_tasks in sorted(categories.items()):
        name = cat_names.get(cat, cat)
        lines.append(f"## {name}")
        lines.append("")
        lines.append("| 状态 | 任务 | 难度 | 优先级 | 预计 |")
        lines.append("|------|------|------|--------|------|")
        
        for task in sorted(cat_tasks, key=lambda t: -t.get('priority', 0)):
            status = task.get('status', 'pending')
            icon = {
                'completed': '✅',
                'in_progress': '🔄',
                'failed': '❌',
                'pending': '⏳',
            }.get(status, '⏳')
            lines.append(
                f"| {icon} | {task.get('name', '?')} | "
                f"{task.get('difficulty', '?')} | "
                f"{task.get('priority', 0)} | "
                f"{task.get('estimated', '?')} |"
            )
        lines.append("")
    
    content = "\n".join(lines)
    try:
        with open(ROADMAP_FILE, 'w') as f:
            f.write(content)
    except:
        pass
    return content


# 预置的开发任务池（初始种子，LLM 可以自行添加）
DEFAULT_TASKS = [
    {
        'id': 'dce_pass',
        'name': '实现死代码消除 Pass (DCE)',
        'description': '在 HIR 层实现 DeadCodeElimination Pass，移除未使用的 let 绑定和无副作用表达式',
        'difficulty': 'easy',
        'priority': 90,
        'category': 'optimization',
        'estimated': '1-2 小时',
        'status': 'pending',
    },
    {
        'id': 'inlining_pass',
        'name': '实现函数内联 Pass',
        'description': '实现 Inlining Pass，内联小型单表达式函数',
        'difficulty': 'medium',
        'priority': 80,
        'category': 'optimization',
        'estimated': '2-4 小时',
        'status': 'pending',
    },
    {
        'id': 'fix_native_test',
        'name': '修复原生后端测试导入',
        'description': '修复 test_native_backend.py 的导入路径问题',
        'difficulty': 'easy',
        'priority': 85,
        'category': 'test',
        'estimated': '30 分钟',
        'status': 'pending',
    },
    {
        'id': 'cse_pass',
        'name': '实现公共子表达式消除 Pass (CSE)',
        'description': '在 MIR 层实现基于哈希的公共子表达式消除',
        'difficulty': 'medium',
        'priority': 70,
        'category': 'optimization',
        'estimated': '3-5 小时',
        'status': 'pending',
    },
    {
        'id': 'fix_list_comprehension',
        'name': '修复列表推导式 MIR 降级',
        'description': '列表推导式当前直接返回空列表，需展开为 for 循环+list_push',
        'difficulty': 'medium',
        'priority': 85,
        'category': 'ir',
        'estimated': '1-2 天',
        'status': 'pending',
    },
    {
        'id': 'fix_break_continue',
        'name': '修复 break/continue 控制流',
        'description': 'break/continue 当前用 panic 代替，需实现正确的循环控制流',
        'difficulty': 'medium',
        'priority': 88,
        'category': 'ir',
        'estimated': '1-2 天',
        'status': 'pending',
    },
    {
        'id': 'fix_phi_lowering',
        'name': '修复 Phi 节点降级',
        'description': 'Phi 节点当前只取第一个 source，需正确降级为前驱块 copy 指令',
        'difficulty': 'hard',
        'priority': 75,
        'category': 'ir',
        'estimated': '2-4 天',
        'status': 'pending',
    },
    {
        'id': 'wasmgc_storereg',
        'name': '补充 WasmGC StoreReg 实现',
        'description': 'WasmGC 后端 LIRStoreReg 是空 pass，需实现为 local.set',
        'difficulty': 'easy',
        'priority': 65,
        'category': 'backend',
        'estimated': '1 小时',
        'status': 'pending',
    },
    {
        'id': 'native_call_abi',
        'name': '实现原生后端函数调用 ABI',
        'description': '实现 System V AMD64 ABI 参数传递和 call 地址回填',
        'difficulty': 'hard',
        'priority': 72,
        'category': 'backend',
        'estimated': '3-5 天',
        'status': 'pending',
    },
    {
        'id': 'licm_pass',
        'name': '实现循环不变量外提 Pass (LICM)',
        'description': '在 MIR 层识别循环，将不变运算外提到循环外',
        'difficulty': 'hard',
        'priority': 60,
        'category': 'optimization',
        'estimated': '1-2 周',
        'status': 'pending',
    },
]


def init_tasks_if_empty():
    """如果任务池为空，初始化默认任务"""
    state = load_state()
    if 'tasks' not in state or not state['tasks']:
        state['tasks'] = DEFAULT_TASKS
        save_state(state)
    return state


if __name__ == "__main__":
    # 初始化
    init_tasks_if_empty()
    state = load_state()
    generate_roadmap(state.get('tasks', DEFAULT_TASKS))
    print(f"已初始化 LLM 开发系统")
    print(f"任务数: {len(state.get('tasks', []))}")
    print(f"已完成: {len(state.get('completed_tasks', []))}")
    print(f"轮次: {state.get('cycles', 0)}")
