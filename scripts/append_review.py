#!/usr/bin/env python3
"""追加审查报告到 AUTO_REVIEW_LOG.md

用法:
    python scripts/append_review.py "轮次名称" < report.md
    python scripts/append_review.py "轮次名称" --from-file report_content.txt
"""
import sys
import os
from datetime import datetime

def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/append_review.py '轮次名称' < report.md")
        sys.exit(1)

    round_name = sys.argv[1]

    # 从 stdin 读取报告内容
    content = sys.stdin.read()

    if not content.strip():
        print("错误: 报告内容为空")
        sys.exit(1)

    log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "AUTO_REVIEW_LOG.md")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    with open(log_path, "a") as f:
        f.write(f"\n---\n\n## {timestamp} {round_name}\n\n")
        f.write(content)
        f.write("\n")

    print(f"已追加审查报告: {round_name}")
    print(f"文件: {log_path}")

if __name__ == "__main__":
    main()
