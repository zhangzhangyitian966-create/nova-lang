#!/bin/bash
# 提交改进更改
set -e

cd "$(dirname "$0")/.."

git config user.email "auto-improve@nova-lang.dev"
git config user.name "Nova Auto Improve"

git add -A

if git diff --cached --quiet; then
    echo "无变更需要提交"
    exit 0
fi

git commit -m "auto: 自动代码改进"
git push origin main

echo "改进更改已提交并推送"
