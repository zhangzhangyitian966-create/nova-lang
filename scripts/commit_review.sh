#!/bin/bash
# 审查辅助脚本：将审查报告追加到日志并提交
# 用法: bash scripts/commit_review.sh "轮次名称" report_content.md
set -e

cd /workspace/nova

ROUND_NAME="$1"
REPORT_FILE="$2"

if [ -z "$ROUND_NAME" ] || [ -z "$REPORT_FILE" ]; then
    echo "用法: bash scripts/commit_review.sh '轮次名称' report_file.md"
    exit 1
fi

if [ ! -f "$REPORT_FILE" ]; then
    echo "错误: 报告文件不存在: $REPORT_FILE"
    exit 1
fi

# 追加到日志
python3 scripts/append_review.py "$ROUND_NAME" < "$REPORT_FILE"

# 提交
TS=$(date +%Y%m%d_%H%M%S)
git add -A
git commit -m "auto-review: $TS - $ROUND_NAME"
git push origin main

echo "审查报告已提交: $ROUND_NAME"
