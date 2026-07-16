#!/bin/bash
# 提交审查更改
set -e

cd "$(dirname "$0")/.."

git config user.email "auto-review@nova-lang.dev"
git config user.name "Nova Auto Review"

git add AUTO_REVIEW_LOG.md scripts/

if git diff --cached --quiet; then
    echo "无变更需要提交"
    exit 0
fi

git commit -m "auto: 自动审查报告更新"
git push origin main

echo "审查更改已提交并推送"
