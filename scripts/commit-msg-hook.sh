#!/usr/bin/env bash
# ============================================================
# Nova git commit-msg hook
# ARCHITECTURE_VISION.md §4.2 强制约束：commit message 必须
# 包含 Architecture-Alignment footer（任务锚点 + 架构对齐分数）。
#
# 安装: cp scripts/commit-msg-hook.sh .git/hooks/commit-msg
#       chmod +x .git/hooks/commit-msg
# 卸载: rm -f .git/hooks/commit-msg
# ============================================================

set -e

COMMIT_MSG_FILE="$1"

# 允许跳过：NOVA_SKIP_ALIGNMENT_HOOK=1 git commit ...
if [ "${NOVA_SKIP_ALIGNMENT_HOOK:-0}" = "1" ]; then
    exit 0
fi

# 合并提交、fixup、squash、 amend 已有 Align 的跳过
first_line=$(head -n 1 "$COMMIT_MSG_FILE" 2>/dev/null || true)
if echo "$first_line" | grep -qE "^(Merge |Fixup! |squash! )"; then
    exit 0
fi

if grep -q "^Architecture-Alignment:" "$COMMIT_MSG_FILE" 2>/dev/null; then
    exit 0
fi

echo ""
echo "  🔴 架构门禁（git commit-msg hook）失败："
echo "     commit message 缺少 'Architecture-Alignment:' footer 行。"
echo ""
echo "  正确格式示例（auto_develop.py 会自动生成，无需手写）："
echo "  -------------------------------------------------------------------"
echo "  auto: 第 78 轮自动开发 - 2 个功能 (v1.0) score=95"
echo ""
echo "  本轮自动开发结果摘要："
echo "  - [completed] deprecate_cranelift_backend"
echo "  - [completed] refactor_eval_convert_cc15"
echo ""
echo "  Architecture-Alignment: deprecate_cranelift_backend=[§2.3 强制] + refactor_eval_convert_cc15=[§5.1 建议] score=95"
echo "  Planned-Tasks: deprecate_cranelift_backend,refactor_eval_convert_cc15"
echo "  Task-Sources: architecture_mandatory,review_driven"
echo "  -------------------------------------------------------------------"
echo ""
echo "  如为人类手工提交（非 auto_develop 发起），可临时跳过："
echo "    NOVA_SKIP_ALIGNMENT_HOOK=1 git commit ..."
echo ""
exit 1
