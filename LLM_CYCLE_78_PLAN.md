# 第 78 轮 Nova LLM 智能开发 · 自动任务规划书（供审阅）

> 生成依据：
> - 架构战略：`ARCHITECTURE_VISION.md`（2026-07-29 生效，备份 tag `llm-dev-arch-decision-20260729-1658`）
> - 任务约束：`.llm_dev_state.json` 中 `task_selection_rules`（架构债务 ≥ 50%、审查驱动 ≥ 1 个、SH-1 启动前置等）
> - 初始流程：原始 6 阶段「计划 → 开发 → 审查 → 修复 → 改进 → 报告」
> - 四层门控：启动提示卡、§1.1 四门禁、架构对齐积分、commit msg hook
>
> 说明：本规划书仅为审阅用，**暂不立即执行**。用户确认通过后，由 `scripts/auto_develop.py` 按以下任务表 + 原始 6 阶段流程执行。

---

## 一、本轮概览

| 项目 | 内容 |
|------|------|
| 轮次 | 第 78 轮（当前 cycles=77 → +1 = 78） |
| 架构战略生效日期 | 2026-07-29 |
| 三项立即架构手术截止 | 第 80 轮（含本轮，**剩余 2 轮**） |
| 本轮计划任务数 | 3 个（默认 max_tasks=3） |
| 架构债务占比 | 2/3 = **66.7%**（≥ 50% 强制门槛 ✅） |
| 审查驱动任务 | 1 个（≥ 1 个强制门槛 ✅） |
| SH-1 启动尝试 | ❌ 不启动（M-ARCH 未完成、Allocator Step1 未完成、不满足 3 轮 100% 测试前置） |
| 目标架构对齐积分 | ≥ **95/100** |

---

## 二、本轮执行的原始 6 阶段流程（不变）

> 门控仅对「任务选择、质量审查、提交落盘」三个位置**追加约束**，不改变原 6 阶段主体流程。

```
阶段 1  计划（Plan）          auto_develop.py §1.1 四门禁 → 拒绝或通过本轮任务表
阶段 2  开发（Develop）       按 task.implement() / task.verify() 逐任务执行（含 Git backup）
阶段 3  审查（Review）        auto_review.py §5.2 四 HIGH gate + 原有增量质量门禁
阶段 4  修复（Fix）           审查产生的 SEV_CRITICAL / SEV_HIGH 必须清零再进入下一阶段
阶段 5  改进（Improve）       auto_improve.py（LOW / 优化类任务）
阶段 6  报告（Report）        生成报告 → 计算架构对齐积分 → 写回 state.json → 提交+推送
```

**追加门控位置**（四层约束，与原始流程正交）：

```
阶段 1 入口     ─── §4.1 启动提示卡（打印架构约束卡）
阶段 1 末尾     ─── §1.1 任务选择门禁（四项：架构截止/债务≥50%/审查≥1/SH1前置）
阶段 3 内部     ─── §5.2 四 HIGH gate（IR 层级泄漏/旧 C 入口/绕 LIR 旁路/SH1 一致性桩）
阶段 6 末尾     ─── §3 架构对齐积分计算 + task_history 落盘
git commit 时  ─── §4.2 commit msg hook（Architecture-Alignment footer 强制）
```

---

## 三、本轮任务表（3 个任务，已通过 §1.1 门禁 dry-run）

### 任务 1（架构债务 · P90 · 立即手术 B）

| 字段 | 内容 |
|------|------|
| **ID** | `unify_c_backend_phase1` |
| **名称** | 统一 C 后端 Phase 1（路径隔离 + 旧后端标记弃用） · 架构手术 B |
| **来源** | `architecture_mandatory`（三项立即架构手术 §2.2） |
| **优先级** | **P90**（最高档） |
| **难度 / 预估** | medium / 2 小时 |
| **架构锚点** | `[ARCHITECTURE_VISION.md §2.2]` `[§5.2 检查 5 强制]` |
| **里程碑** | M-ARCH（三项立即手术，3 轮内完成） |
| **前置依赖** | 无（手术 B 与手术 A 可并行，Phase 1 不改动 ADT/match） |
| **核心动作** | ① 新建 `backend/c/` 目录，将新 C 后端模块移入 `backend/c/codegen*.py` 等；② 旧 `c_codegen.py` 顶部加 `DEPRECATION_WARNING` 与 `DeprecationWarning` 日志；③ 入口 `compiler_cli.py` 仅允许通过 `backend/c/` 调用，禁止直接 `from c_codegen import *`；④ 保留兼容 re-export `ir/ir_nodes.py` 指向（未动手术 A，不破坏其它模块） |
| **交付物** | `backend/c/` 目录 + 旧 `c_codegen.py` 弃用标记 + `compiler_cli.py` 路径切换 + 1065 测试 100% 通过 |
| **通过标准** | `python3 -m pytest tests -q` 1065 passed / 0 failed；gate_ast_to_backend_shortcut 无新违规；入口文件不再直接 import 旧 c_codegen |

### 任务 2（架构债务 · P90 · 立即手术 A-1）

| 字段 | 内容 |
|------|------|
| **ID** | `split_ir_nodes_a1` |
| **名称** | 拆分 ir_nodes A1：抽 ir_types.py（共享类型常量） · 架构手术 A-1 |
| **来源** | `architecture_mandatory`（三项立即架构手术 §2.1） |
| **优先级** | **P90**（最高档） |
| **难度 / 预估** | medium / 2 小时 |
| **架构锚点** | `[ARCHITECTURE_VISION.md §2.1]` `[§5.1 建议 HIR/MIR/LIR 解耦]` |
| **里程碑** | M-ARCH（三项立即手术，3 轮内完成） |
| **前置依赖** | 无（A1 只抽类型常量，不拆 Node 类，风险最小） |
| **核心动作** | ① 新建 `ir/ir_types.py`，把 `ir/ir_nodes.py` 中纯类型枚举/常量（`TypeKind`、IR Opcode、BinaryOp 等与 AST/Node 无关的常量）移动；② 在 `ir/ir_nodes.py` 保留 `from ir.ir_types import *` 的 re-export，不破坏外部导入；③ 更新 3-5 个高频 import 点，消去对 `ir_nodes.*常量` 的直接依赖（减少 A2 工作量）；④ 1065 测试全绿 |
| **交付物** | `ir/ir_types.py`（~150 行） + `ir/ir_nodes.py` 变薄 re-export + 外部 import 点更新 + 1065 测试 100% 通过 |
| **通过标准** | `python3 -m pytest tests -q` 1065 passed / 0 failed；`ir_types.py` 中包含 80% 以上的 IR 纯常量；`ir/ir_nodes.py` 相比本轮前减少 ≥ 120 行 |

### 任务 3（审查驱动 · P35 · HIGH 级遗留问题清理）

| 字段 | 内容 |
|------|------|
| **ID** | `low_quality_issues_cleanup_review_v77` |
| **名称** | 审查驱动：清理第 77 轮审查报告中 HIGH 级问题（sys.path hack + 增量质量门禁） |
| **来源** | `review_driven`（**满足 ≥ 1 个审查驱动任务的强制门槛** ✅） |
| **优先级** | P35（作为 filler，本轮放在第 3 位，前 2 个完成后再执行） |
| **难度 / 预估** | easy / 1 小时 |
| **架构锚点** | `[AUTO_REVIEW_LOG.md HIGH 级问题 P1]` `[ARCHITECTURE_VISION.md §5.3 原创性-不引入三方包]` |
| **里程碑** | 非里程碑（审查清理常规任务） |
| **前置依赖** | 任务 1、2 完成（防止前两个任务引入新的 import 问题，清理后被覆盖） |
| **核心动作** | ① 移除 `tests/test_mir_lowering_unit.py:16` 的 `sys.path.insert(0, ...)`，改用 `pytest.ini` 或 `pyproject.toml` 的 `testpaths/pythonpath` 机制；② 处理增量质量门禁遗留 HIGH：新增代码 docstring 补齐、魔法数字提常量、命名规范修正（**仅限本轮新增代码**）；③ 禁止引入三方包（§5.3） |
| **交付物** | `tests/test_mir_lowering_unit.py` 无 sys.path hack；`pytest.ini` 或 `pyproject.toml` 更新测试路径；auto_review 重跑后 HIGH 级问题数 = 0；1065 测试全绿 |
| **通过标准** | auto_review 重跑后 sys_path_hack 消失；增量门禁 HIGH = 0；`python3 -m pytest tests -q` 1065 passed / 0 failed |

---

## 四、任务约束 & 来源配比

| 类别 | 数量 | 占比 | 是否达标 |
|------|------|------|----------|
| 架构债务（architecture_mandatory / architecture_debt） | **2** | **66.7%** | ✅ ≥ 50% |
| 审查驱动（review_driven） | **1** | **33.3%** | ✅ ≥ 1 个 |
| self_planned / 其它 | 0 | 0% | ✅（M-ARCH 完成前不允许 filler 超 1/3） |

---

## 五、风险与降级策略

| 风险 | 概率 | 影响 | 降级方案 |
|------|------|------|----------|
| 任务 1（手术 B）切换 compiler_cli 入口后，部分 C 生成测试失败 | 中 | 高 | 立即回滚到 backup tag；把「仅迁移目录、不切入口」作为交付物，入口切换留到第 79 轮手术 B-1 子任务 |
| 任务 2（拆 A1）移动 ir_types 后 10+ 模块 import 失败 | 中 | 中 | 先只移最安全的 30% 常量（Opcode 等），余下 TypeKind 留到 A2；保证 1065 测试绿 |
| 任务 3（清理 sys.path hack）后 CI 环境测试路径出错 | 低 | 低 | 先加 `pytest.ini` 作为主方案，失败则用 `pyproject.toml [tool.pytest.ini_options]` 再试；再不济保留 `conftest.py` 级别的最小 sys.path 注入 |
| 三轮手术截止逼近（本轮后只剩 1 轮） | 高 | 高 | **第 79 轮强制 3/3 架构债务（A2 + A3 + Cranelift 弃用）**，100% 架构债务占比，不允许任何 filler；若仍完不成，第 80 轮起启用 §1.1 检查 1，中止本轮开发并要求架构决策补充（按 ARCHITECTURE_VISION.md §1.1 硬约束） |

---

## 六、阶段 6 交付产物清单（每轮结束必须齐全）

1. **Git 提交**：形如 `auto: 第 78 轮自动开发 - 3 个功能 (v1.0) score=NN`，包含 footer 行：
   - `Architecture-Alignment: unify_c_backend_phase1=[§2.2 强制] + split_ir_nodes_a1=[§2.1 强制] + low_quality_issues_cleanup_review_v77=[§5.3 建议] score=NN`
   - `Planned-Tasks: unify_c_backend_phase1,split_ir_nodes_a1,low_quality_issues_cleanup_review_v77`
   - `Task-Sources: architecture_mandatory,architecture_mandatory,review_driven`
2. **报告文件**：`LLM_DEV_LOG.md` 追加一条 `## 第 78 轮 ...`
3. **状态落盘**：`.llm_dev_state.json` 中 `task_history[-1]` 含 score + results；`tasks[].status` 同步；`milestones[M-ARCH].progress` 更新
4. **审查报告**：`AUTO_REVIEW_LOG.md` 追加最新一轮审查（四 HIGH gate 全通过、增量门禁 HIGH=0）
5. **测试基线**：`python3 -m pytest tests -q` → `1065 passed in XX.XXs`（0 failed）

---

## 七、用户确认项（审阅请回复 A/B/C）

- **A. 通过**：按本规划书执行第 78 轮（3 任务表 + 6 阶段 + 四层门控）
- **B. 微调**：调整任务顺序/替换某个任务/增加任务数（请注明具体改动）
- **C. 先跑审查**：只先执行阶段 1~3（计划 + 开发 + 审查），阶段 4~6 等看完审查报告再决定

> 规划不立即执行，等你确认回复后才开始。
