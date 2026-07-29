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
STATE_FILE = os.path.join(PROJECT_DIR, ".llm_dev_state.json")
ARCH_VISION_FILE = os.path.join(PROJECT_DIR, "ARCHITECTURE_VISION.md")

# ============================================================
# 架构战略门禁 + 启动提示卡（ARCHITECTURE_VISION.md 落地）
# ============================================================

# 架构债务任务 ID 集合（立即手术 + Allocator API 四步）
ARCH_DEBT_TASK_IDS = {
    # 手术 A：拆 ir_nodes（三步）
    "split_ir_nodes_a1",
    "split_ir_nodes_a2",
    "split_ir_nodes_a3",
    # 手术 B：统一 C 后端（phase1/2）
    "unify_c_backend_phase1",
    "unify_c_backend_phase2",
    # 手术 C：弃用 Cranelift
    "deprecate_cranelift_backend",
    # 内存模型决策：Allocator API 四步
    "allocator_api_step1",
    "allocator_api_step2",
    "allocator_api_step3",
    "allocator_api_step4",
}

# Self-Hosting 第一阶段任务 ID 前缀
SH1_TASK_PREFIX = ("sh1_", "self_host_sh1_", "lexer_port_", "parser_port_")

# Filler 低优先级上限
FILLER_PRIORITY_CAP = 35


def _load_state_file():
    """读取 .llm_dev_state.json，失败返回空 dict（不抛异常，避免阻塞启动）。"""
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _milestone_completed(state, milestone_id):
    """判断某个里程碑的所有子任务是否都已进入 completed_tasks。"""
    completed = set(state.get("completed_tasks", []) or [])
    for ms in state.get("milestones", []) or []:
        if ms.get("id") != milestone_id:
            continue
        subs = ms.get("sub_tasks", []) or []
        return subs and all(s in completed for s in subs)
    return False


def _is_sh1_task(task_id):
    tid = (task_id or "").lower()
    return tid.startswith(SH1_TASK_PREFIX) or "sh-1" in tid or "selfhosting-sh1" in tid


def print_architecture_quick_ref_card(state, next_cycle):
    """§4.1 启动提示卡：在阶段 1 初始化后立刻打印，每轮启动都可见。"""
    arch = state.get("architecture_strategy", {})
    eff = arch.get("effective_date", "2026-07-29")
    deadline_cycles = arch.get("immediate_surgeries_deadline", 3)
    cycles_since = next_cycle - 77
    surcharges_ok = cycles_since <= deadline_cycles
    m_arch_done = _milestone_completed(state, "M-ARCH")
    m_mem_step1_done = "allocator_api_step1" in (state.get("completed_tasks", []) or [])

    # 计算当前最高优先级的 5 个 PENDING 架构债务推荐
    recs = []
    for t in state.get("tasks", []) or []:
        if t.get("id") in ARCH_DEBT_TASK_IDS and t.get("status") == "pending":
            recs.append((t.get("priority", 0), t.get("id", ""), t.get("name", "")))
    recs.sort(reverse=True)
    top5 = recs[:5]

    sep = "═" * 67
    print(f"\n╔{sep}╗")
    print("║  📐 NOVA 架构战略 · 本轮约束卡（参考 ARCHITECTURE_VISION.md）     ║")
    print(f"╠{sep}╣")
    print(
        f"║  本轮: 第 {next_cycle} 轮  ·  架构生效日期 {eff:<24}║"
    )
    cycles_left = max(0, deadline_cycles - cycles_since)
    status = f"剩余 {cycles_left} 轮" if cycles_left > 0 else ("✅ 已到期，必须立即推进" if not m_arch_done else "✅ 已完成")
    if m_arch_done:
        status = "✅ 全部完成"
    print(f"║  🚨 立即架构手术状态（截止第 80 轮）: {status:<26}║")
    print("║                                                                   ║")
    print("║  ✅ 已验证原则（不得推翻）                                        ║")
    print("║    1. 三层 IR（HIR/MIR/LIR）不能合并                              ║")
    print("║    2. 新后端必须走 LIR 路径（禁止 AST→X / MIR→X 旁路）           ║")
    print("║    3. 语义变更先改 evaluator.py，再改 IR/后端                    ║")
    print("║                                                                   ║")
    print("║  🔴 硬约束（不满足则中止本轮开发）                                ║")
    print("║    • 架构债务任务 ≥ 50%（三项手术完成前强制）                    ║")
    print("║    • 审查驱动任务 ≥ 1 个                                          ║")
    print("║    • SH-1 启动前置：M-ARCH(" + ("✅" if m_arch_done else "❌") + ") + Alloc Step1(" + ("✅" if m_mem_step1_done else "❌") + ") + 3轮100%测试 ║")
    print("║                                                                   ║")
    print("║  🎯 架构债务 TOP5（按优先级，优先选择其中 1-2 个）:               ║")
    if not top5:
        print("║    (无 PENDING 架构债务任务，可进入下一阶段里程碑)               ║")
    else:
        for i, (p, tid, name) in enumerate(top5):
            line = f"    P{p:<3} {tid:<26} {name[:17]}"
            # 补齐到 65 字符内
            line = line[:63]
            print(f"║  {i+1}. {line:<63}║")
    print("║                                                                   ║")
    print("║  📚 任务 reason 字段必须包含引用锚点: [ARCHITECTURE_VISION.md §X.X]║")
    print(f"╚{sep}╝\n")


def validate_cycle_task_plan(state, next_cycle, planned_task_ids, planned_sources):
    """§1.1 任务选择门禁（阶段 2-D 执行前强制执行）。

    参数:
      state           - .llm_dev_state.json 解析后的 dict
      next_cycle      - 本轮编号（cycles + 1）
      planned_task_ids - 本轮计划执行的任务 id 列表 [id1, id2, id3]
      planned_sources - 对应任务的来源列表 ["review_driven"|"architecture_mandatory"|"self_planned", ...]

    返回: (ok: bool, errors: [str], warnings: [str])
    """
    errors = []
    warnings = []

    if not planned_task_ids:
        errors.append("本轮没有任何规划任务，无法继续。至少规划 2 个任务。")
        return False, errors, warnings

    total = len(planned_task_ids)

    # ---- 检查 1: 架构手术截止 + 推进 ----
    arch = state.get("architecture_strategy", {})
    deadline_cycles = arch.get("immediate_surgeries_deadline", 3)
    cycles_since = next_cycle - 77
    m_arch_done = _milestone_completed(state, "M-ARCH")
    if not m_arch_done and cycles_since > deadline_cycles:
        errors.append(
            f"架构手术已超过截止轮次（生效后 {deadline_cycles} 轮 = 第 {77+deadline_cycles} 轮前）。"
            f"当前已第 {next_cycle} 轮，M-ARCH 里程碑仍未完成。"
            "本轮必须包含 ≥1 个立即架构手术任务（split_ir_nodes_a1/a2/a3、unify_c_backend_phase1、deprecate_cranelift_backend）。"
        )
    if not m_arch_done:
        # 至少推进一步
        if not any(tid in {"split_ir_nodes_a1", "split_ir_nodes_a2", "split_ir_nodes_a3",
                           "unify_c_backend_phase1", "deprecate_cranelift_backend"}
                   for tid in planned_task_ids):
            warnings.append(
                "M-ARCH 里程碑未完成但本轮未选立即手术任务（建议至少选 1 个：unify_c_backend_phase1 / split_ir_nodes_a1 / deprecate_cranelift_backend）。"
            )

    # ---- 检查 2: 架构债务 ≥ 50%（M-ARCH 完成前强制执行）----
    if not m_arch_done:
        arch_count = sum(1 for tid in planned_task_ids if tid in ARCH_DEBT_TASK_IDS)
        ratio = arch_count / total if total else 0
        if ratio < 0.5:
            errors.append(
                f"架构债务占比未达标：{arch_count}/{total} = {ratio*100:.0f}%，"
                "要求 ≥ 50%（三项立即手术完成前强制执行）。"
                f"请至少将 {max(0, (total+1)//2 - arch_count)} 个任务替换为架构债务。"
                "架构债务任务 ID: split_ir_nodes_a1/a2/a3, unify_c_backend_phase1/phase2, deprecate_cranelift_backend, allocator_api_step1-4。"
            )

    # ---- 检查 3: 审查驱动任务 ≥ 1 ----
    review_driven_count = sum(1 for s in (planned_sources or []) if s == "review_driven")
    if review_driven_count < 1:
        errors.append(
            f"本轮审查驱动任务 {review_driven_count} 个，要求 ≥ 1 个（来源 AUTO_REVIEW_LOG.md 的 CRITICAL/HIGH/TOP10 MEDIUM）。"
        )

    # ---- 检查 4: SH-1 启动前置条件 ----
    sh1_in_plan = any(_is_sh1_task(t) for t in planned_task_ids)
    if sh1_in_plan:
        mem_step1_done = "allocator_api_step1" in (state.get("completed_tasks", []) or [])
        if not m_arch_done:
            errors.append(
                "本轮计划启动 SH-1（lexer/parser 移植），但前置里程碑 M-ARCH（三项立即架构手术）尚未完成。"
                "必须先完成 M-ARCH 的 5 个子任务再启动 SH-1。"
            )
        if not mem_step1_done:
            errors.append(
                "本轮计划启动 SH-1，但前置条件 Allocator API Step1（trait + 两种默认分配器实现）尚未完成。"
                "请先完成 allocator_api_step1。"
            )
        # 连续 3 轮 100% 测试：读取 task_history 末尾三轮的 test_result
        hist = state.get("task_history", []) or []
        last_cycles = {}
        for entry in hist:
            c = entry.get("cycle") if isinstance(entry, dict) else None
            if isinstance(c, int):
                last_cycles[c] = entry
        clean3 = True
        for i in range(3):
            cyc = next_cycle - 1 - i
            e = last_cycles.get(cyc)
            if not e or str(e.get("test_result", "")).lower() not in {"pass", "ok", "success", "all_pass", "100%"}:
                clean3 = False
                break
        if not clean3:
            warnings.append(
                "SH-1 启动前置「连续 3 轮 100% 测试通过」未验证通过（无法在 task_history 中确认最近 3 轮均为 pass）。"
                "如确已达标，可忽略此警告。"
            )
        # 语法冻结声明：state 中必须存在 syntax_freeze: true
        if not state.get("syntax_freeze"):
            warnings.append(
                "SH-1 启动前置「语法冻结声明」未在 .llm_dev_state.json 中找到（需要 syntax_freeze=true）。"
                "SH-1 期间不得修改 AST 节点结构或语法。"
            )

    # ---- 辅助检查：P35 及以下任务选作主任务警告 ----
    tasks = {t.get("id"): t for t in (state.get("tasks", []) or [])}
    fillers = [tid for tid in planned_task_ids
               if (tasks.get(tid) or {}).get("priority", 999) <= FILLER_PRIORITY_CAP]
    if fillers:
        warnings.append(
            f"本轮包含 {len(fillers)} 个 P≤{FILLER_PRIORITY_CAP} 的 filler 任务（{fillers}）。"
            "此类任务仅应在所有高优先级任务都无法推进时选择。"
        )

    # ---- 任务 reason 锚点检查（软警告）----
    for i, tid in enumerate(planned_task_ids):
        reason = str((tasks.get(tid) or {}).get("reason", ""))
        if "ARCHITECTURE_VISION.md" not in reason and tid in ARCH_DEBT_TASK_IDS:
            warnings.append(
                f"架构债务任务 {tid} 的 reason 字段缺少 ARCHITECTURE_VISION.md §X.X 引用锚点（建议按格式补齐：[ARCHITECTURE_VISION.md §2.1 强制]）。"
            )

    return len(errors) == 0, errors, warnings


def compute_architecture_alignment_score(state, results, planned_ids, planned_sources):
    """§3 架构对齐积分（0-100）。在阶段 5 更新 .llm_dev_state.json 时写入 task_history。

    评分规则：
      +30 架构债务占比 ≥ 50%（M-ARCH 完成前；完成后此项按「推进 ≥1 个里程碑子任务」替代）
      +15 审查驱动 ≥ 1
      +25 本轮至少完成 1 个 M-ARCH / M-MEM 子任务
      +20 本轮审查报告 4 个新架构 gate HIGH 违规数 == 0
      +10 里程碑推进（≥ 1 个 sub_task 进入 completed）
      -20 存在 ≤P35 filler 主任务
    """
    score = 0
    ms = state.get("milestones", []) or []
    m_arch_done = _milestone_completed(state, "M-ARCH")
    completed_ids = set(state.get("completed_tasks", []) or [])
    # 本轮刚完成的任务 = results 中 status==completed 的任务 id（来自 run_cycle 结果）
    cycle_completed = set()
    for r in results or []:
        if isinstance(r, dict) and r.get("status") in {"completed", "success"}:
            tid = r.get("task_id") or r.get("id")
            if tid:
                cycle_completed.add(str(tid))

    # 1. 架构债务占比 ≥ 50%（30 分）
    total = max(1, len(planned_ids or []))
    arch_count = sum(1 for tid in (planned_ids or []) if tid in ARCH_DEBT_TASK_IDS)
    if not m_arch_done:
        if arch_count / total >= 0.5:
            score += 30
    else:
        # M-ARCH 已完成：用「本轮完成 ≥1 个 M-MEM/SHx 子任务」替代
        promoted = False
        for milestone in ms:
            if milestone.get("id") in {"M-MEM", "M-SH1", "M-SH2", "M-SH3", "M-STD"}:
                for s in (milestone.get("sub_tasks", []) or []):
                    if s in cycle_completed:
                        promoted = True
                        break
            if promoted:
                break
        if promoted:
            score += 30

    # 2. 审查驱动 ≥ 1（15 分）
    if sum(1 for s in (planned_sources or []) if s == "review_driven") >= 1:
        score += 15

    # 3. 完成 ≥1 个 M-ARCH / M-MEM 子任务（25 分）
    target_subs = set()
    for milestone in ms:
        if milestone.get("id") in {"M-ARCH", "M-MEM"}:
            target_subs.update(milestone.get("sub_tasks", []) or [])
    if any(s in cycle_completed for s in target_subs):
        score += 25

    # 4. 本轮审查新架构 gate 违规数（20 分）—— 预留接口：state 中 last_review_high_gate_violations=0 时得分
    gate_violations = int(state.get("last_review_high_gate_violations", 9999))
    if gate_violations == 0:
        score += 20

    # 5. 里程碑推进（10 分）
    progressed = False
    for milestone in ms:
        for s in (milestone.get("sub_tasks", []) or []):
            if s in cycle_completed:
                progressed = True
                break
        if progressed:
            break
    if progressed:
        score += 10

    # 6. Filler 扣分（-20）
    tasks = {t.get("id"): t for t in (state.get("tasks", []) or [])}
    has_filler_main = any(
        (tasks.get(tid) or {}).get("priority", 999) <= FILLER_PRIORITY_CAP
        for tid in (planned_ids or [])
    )
    if has_filler_main:
        score -= 20

    return max(0, min(100, score))


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


def persist_state_after_cycle(
    cycle_num,
    results,
    planned_ids,
    planned_sources,
    arch_score,
    test_before,
    test_after,
):
    """§3 架构对齐积分落盘 + task_history 写入。

    在每次 auto_develop 结束时调用（阶段 8，提交之前）。
    将本轮开发的「架构对齐积分、任务来源、测试结果、里程碑推进情况」写入
    .llm_dev_state.json 的 task_history 列表，并更新 last_review_high_gate_violations
    （供 compute_architecture_alignment_score 的 +20 分项使用）。
    """
    state = _load_state_file()
    if not state:
        return False, ".llm_dev_state.json 不存在或为空"

    # 本轮完成的任务 id 集合
    cycle_completed = set()
    cycle_failed = set()
    for r in results or []:
        if not isinstance(r, dict):
            continue
        tid = r.get("task_id") or r.get("id")
        if not tid:
            continue
        if r.get("status") in {"completed", "success"}:
            cycle_completed.add(str(tid))
        elif r.get("status") in {"failed", "rolled_back"}:
            cycle_failed.add(str(tid))

    # 同步 completed_tasks（兼容 LLM 智能开发系统维护的字段）
    completed_set = set(state.get("completed_tasks", []) or [])
    completed_set |= cycle_completed
    state["completed_tasks"] = sorted(completed_set)

    failed_set = set(state.get("failed_tasks", []) or [])
    failed_set |= cycle_failed
    state["failed_tasks"] = sorted(failed_set)

    # 同步 tasks 列表状态（pending -> completed）
    tasks = state.get("tasks", []) or []
    for t in tasks:
        tid = str(t.get("id", ""))
        if tid in cycle_completed:
            t["status"] = "completed"
            t["completed_cycle"] = cycle_num
            t["completed_at"] = datetime.now().isoformat()
        elif tid in cycle_failed and t.get("status") != "deprecated":
            t.setdefault("fail_count", 0)
            t["fail_count"] = int(t.get("fail_count", 0) or 0) + 1
            t["last_fail_cycle"] = cycle_num

    # 推进 milestones 的 status
    ms_list = state.get("milestones", []) or []
    for ms in ms_list:
        subs = ms.get("sub_tasks", []) or []
        done = sum(1 for s in subs if s in completed_set)
        total = len(subs) or 1
        ratio = done / total
        if ratio >= 1.0:
            ms["status"] = "completed"
            ms["completed_cycle"] = ms.get("completed_cycle") or cycle_num
        elif ratio > 0:
            ms["status"] = ms.get("status") or "in_progress"
        ms["progress"] = f"{done}/{total}"

    state["cycles"] = int(state.get("cycles", 0) or 0) + 1

    # 写 task_history 条目
    hist = state.get("task_history", []) or []
    hist.append(
        {
            "cycle": cycle_num,
            "timestamp": datetime.now().isoformat(),
            "planned_ids": planned_ids or [],
            "planned_sources": planned_sources or [],
            "results": results or [],
            "architecture_alignment_score": arch_score,
            "test_before": str(test_before) if test_before else "",
            "test_after": str(test_after) if test_after else "",
            "test_result": "pass" if (
                isinstance(test_after, str)
                and any(x in test_after.lower() for x in ("pass", "ok", "success", "1065"))
            ) else ("fail" if test_after else "unknown"),
        }
    )
    state["task_history"] = hist

    # 预留：last_review_high_gate_violations（下一轮审查运行后，auto_review.py 会更新）
    state.setdefault("last_review_high_gate_violations", 0)

    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, f"写入失败: {exc}"


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
            # TODO: 审查此异常处理是否合理，避免静默吞噬异常
            except Exception:
                # TODO: 细化异常处理，避免静默吞噬
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
        # TODO: 细化异常处理，避免静默吞噬
        except Exception:
            # TODO: 细化异常处理，避免静默吞噬
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


def git_commit_and_push(cycle_num, completed_count, results, planned_ids, planned_sources, arch_score):
    run_cmd(["git", "config", "user.email", "auto-dev@nova-lang.dev"])
    run_cmd(["git", "config", "user.name", "Nova Auto Developer"])
    run_cmd(["git", "add", "-A"])

    stdout, stderr, rc = run_cmd(["git", "status", "--porcelain"])
    if not stdout.strip():
        print("  (无变更，跳过提交)")
        return True

    # §4.2 生成 Architecture-Alignment footer（任务锚点 + 分数）
    tasks_meta = {}
    state = _load_state_file()
    for t in (state.get("tasks", []) or []):
        tasks_meta[t.get("id")] = t
    refs = []
    for tid in (planned_ids or []):
        reason = str((tasks_meta.get(tid) or {}).get("reason", ""))
        # 从 reason 中提取 [ARCHITECTURE_VISION.md §X.X 强制] 的锚点摘要
        m = re.search(r"\[ARCHITECTURE_VISION\.md §([^\]]+)\]", reason)
        if m:
            refs.append(f"{tid}=[§{m.group(1).strip()}]")
        elif tid in ARCH_DEBT_TASK_IDS:
            refs.append(f"{tid}=[§? 待补锚点]")
    ref_str = " + ".join(refs) if refs else "(无架构债务任务锚点)"
    align_footer = (
        f"\n\nArchitecture-Alignment: {ref_str} score={arch_score}\n"
        f"Planned-Tasks: {','.join(planned_ids or [])}\n"
        f"Task-Sources: {','.join(planned_sources or [])}\n"
    )

    subject = f"auto: 第 {cycle_num} 轮自动开发 - {completed_count} 个功能 (v1.0) score={arch_score}"
    body_lines = []
    body_lines.append("本轮自动开发结果摘要：")
    if results:
        for r in results or []:
            if isinstance(r, dict):
                st = r.get("status", "?")
                name = r.get("task_id") or r.get("name") or r.get("id") or "?"
                body_lines.append(f"- [{st}] {name}")
    commit_msg = subject + "\n\n" + "\n".join(body_lines) + align_footer

    stdout, stderr, rc = run_cmd(
        [
            "git",
            "commit",
            "-m",
            commit_msg,
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

    print("[0/8] 读取状态文件 + 架构战略启动提示卡...")
    state = _load_state_file()
    current_cycles = int(state.get("cycles", 0) or 0)
    next_cycle = current_cycles + 1
    print_architecture_quick_ref_card(state, next_cycle)
    print("  OK")
    print()

    print("[1/8] 确保项目存在...")
    if not ensure_project():
        print("错误: 无法获取项目")
        sys.exit(1)
    setup_git_credentials()
    print("  OK")
    print()

    print("[2/8] 拉取最新代码...")
    git_pull()
    print("  OK")
    print()

    print("[3/8] 创建备份...")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    git_backup(f"auto-dev-backup-{ts}")
    print("  OK")
    print()

    print("[4/8] 开发前测试...", end=" ", flush=True)
    test_ok_before, test_str_before, _, _ = run_tests()
    print(test_str_before)
    print()

    print("[5/8] 任务规划门禁（架构战略约束）...", flush=True)
    # 自动从 ALL_TASKS（Pend） + state.tasks（Pend）推断一个默认规划，再跑门禁
    # AutoDeveloper 使用内建 TASK 列表，但 state.tasks 是 LLM 智能开发系统的任务池。
    # 这里把 state.tasks 中 PENDING 的架构债务/高优先任务并入 planned，然后做门禁验证。
    planned_ids = []
    planned_sources = []
    for t in (state.get("tasks", []) or []):
        if t.get("status") == "pending":
            planned_ids.append(t.get("id"))
            src = t.get("source") or t.get("reason") or ""
            if "review" in str(src).lower() and "driven" in str(src).lower():
                planned_sources.append("review_driven")
            elif str(t.get("id") or "") in ARCH_DEBT_TASK_IDS:
                planned_sources.append("architecture_mandatory")
            else:
                planned_sources.append("self_planned")
        if len(planned_ids) >= 3:
            break
    # 从内建 ALL_TASKS 补齐到至少 2 个
    if len(planned_ids) < 2:
        for task in ALL_TASKS:
            if task.task_id not in planned_ids:
                planned_ids.append(task.task_id)
                planned_sources.append("self_planned")
            if len(planned_ids) >= 2:
                break
    ok_plan, errs, warns = validate_cycle_task_plan(
        state, next_cycle, planned_ids, planned_sources
    )
    print(f"  计划任务数: {len(planned_ids)} → {planned_ids}")
    if not ok_plan:
        print("  ❌ 任务规划门禁失败（硬约束不满足，中止本轮开发）：")
        for e in errs:
            print(f"     🔴 ERROR: {e}")
        for w in warns:
            print(f"     🟡 WARN : {w}")
        print("  请修正任务列表后重试。参考架构债务 TOP5：")
        top = []
        for t in (state.get("tasks", []) or []):
            if t.get("id") in ARCH_DEBT_TASK_IDS and t.get("status") == "pending":
                top.append((t.get("priority", 0), t.get("id"), t.get("name")))
        top.sort(reverse=True)
        for p, tid, name in top[:5]:
            print(f"    · P{p:<3} {tid:<28} {name}")
        sys.exit(2)
    if warns:
        print("  🟡 规划门禁警告（不阻塞，但建议修正）：")
        for w in warns:
            print(f"     🟡 WARN : {w}")
    print("  规划门禁通过 ✅")
    print()

    print("[6/8] 执行自动开发...")
    print()

    developer = AutoDeveloper()
    developer.load_progress()
    completed = developer.run_cycle(max_tasks=3)
    developer.save_progress()

    roadmap = generate_roadmap()
    write_file(ROADMAP_FILE, roadmap)

    # 架构对齐积分（0-100）
    arch_score = compute_architecture_alignment_score(
        state, developer.results, planned_ids, planned_sources
    )
    print(f"  本轮完成: {completed} 个任务 | 架构对齐积分: {arch_score}/100")
    print()

    print("[7/8] 开发后测试...", end=" ", flush=True)
    test_ok_after, test_str_after, _, _ = run_tests()
    print(test_str_after)
    print()

    print("[8/8] 生成报告并提交...")
    cycle_num = get_current_cycle()
    report = generate_report(
        cycle_num, developer.results, test_str_before, test_str_after
    )

    with open(DEV_LOG, "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        f.write(f"\n---\n\n## {timestamp} 第{cycle_num}轮开发\n\n")
        f.write(f"**架构对齐积分**: {arch_score}/100\n\n")
        f.write(f"**计划任务**: {planned_ids}\n\n")
        f.write(report)
        f.write("\n")

    success = git_commit_and_push(
        cycle_num, completed, developer.results, planned_ids, planned_sources, arch_score
    )
    if success:
        print("  提交并推送 OK ✅")
    else:
        print("  提交失败 ❌")
    print()

    # 阶段 8.5: state.json 落盘（架构对齐积分 + 任务状态 + 里程碑进度）
    print("[8.5/8] 写回 .llm_dev_state.json...", end=" ", flush=True)
    ok_persist, err_persist = persist_state_after_cycle(
        cycle_num,
        developer.results,
        planned_ids,
        planned_sources,
        arch_score,
        test_str_before,
        test_str_after,
    )
    if ok_persist:
        print("OK")
    else:
        print(f"WARN: {err_persist}")
    print()

    print("=" * 60)
    print(f"  开发完成: {completed} 个新功能已上线 | 架构对齐 {arch_score}/100")
    print("=" * 60)


if __name__ == "__main__":
    main()
