#!/usr/bin/env python3
"""
SH-1 Parity Baseline Builder — Self-Hosting 字节级一致性基线脚本。

【里程碑关联】M-SH1（Self-Hosting SH-1：lexer+parser 字节级一致）前置闸门 3/3。
【冻结文档】SYNTAX_FREEZE_v0.5.md §8 / §10.2 明确要求的两大产物之一。
【功能】
  1. 读取 examples/ 目录下 8 个基准 .nova 文件（SH-1 parity fixture set）
  2. 通过 Python 参考 parser 解析得到 Program AST
  3. 确定性序列化为 JSON（字段名顺序 = dataclass 定义顺序，与 SYNTAX_FREEZE §5/§6 对齐）
  4. 计算每个 AST JSON 的 MD5 锚点
  5. 输出 baseline.json：基准文件名 → {ast_md5, ast_json_path, source_md5}
  6. 同时把每个基准的 AST JSON 落盘到 fixtures/sh1_parity/*.json，供 Nova 侧实现直接字节对比

【用法】
  cd /workspace/nova && python3 scripts/sh1_baseline.py

【输出】
  - fixtures/sh1_parity/baseline.json        主清单（CI 可读取做回归锚点）
  - fixtures/sh1_parity/<name>.ast.json      8 基准的 AST JSON 原文（逐字节对比用）

【保证】
  * 字段顺序确定性：dataclasses.asdict() 按声明顺序，且 JSON sort_keys=False
  * 数值/字符串无歧义：int 按十进制，float 按 repr()，字符串按 UTF-8 JSON 转义
  * span 保留：line/column 参与 MD5（意味着行号/列号也冻结，符合 SH-1 严格定义）
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

# ------------------------------------------------------------
# 包路径：支持直接脚本式运行（python3 scripts/sh1_baseline.py）
# ------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent                              # /workspace/nova
_PKG_PARENT = _ROOT.parent                        # /workspace （nova 包的父目录，import nova.parser 需要）
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from nova.lexer import Lexer                         # noqa: E402
from nova.parser import Parser, ParseError            # noqa: E402


# ------------------------------------------------------------
# 8 基准文件集合（SH-1 parity fixture set · 冻结）
# ------------------------------------------------------------
BASELINE_FILES = [
    "hello.nova",
    "fibonacci.nova",
    "loops.nova",
    "math.nova",
    "list_comprehension.nova",
    "pattern_match.nova",
    "pipe.nova",
    "file_io.nova",
]


def _to_jsonable(obj: Any) -> Any:
    """递归把 dataclass / 基本类型转换为可 JSON 序列化的结构。

    * dataclass → {"$type": "ClassName", "fields": {...}}
      （$type 前缀确保同形异构节点（如 ListExpr vs TupleExpr）MD5 不冲突）
    * list / tuple → [item0, item1, ...]
    * set → sorted(list) （保证确定性顺序）
    * int / str / float / bool / None → 原样
    * 其它 → str(obj) 兜底
    """
    if obj is None:
        return None
    if isinstance(obj, bool):  # bool 是 int 子类，先判
        return obj
    if isinstance(obj, (int, str, float)):
        return obj
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {
            "$type": type(obj).__name__,
            "fields": {
                f.name: _to_jsonable(getattr(obj, f.name))
                for f in dataclasses.fields(obj)
            },
        }
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        # dict 键按 str 排序，避免同内容不同顺序导致 MD5 漂移
        return {str(k): _to_jsonable(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}
    if isinstance(obj, set):
        return [_to_jsonable(x) for x in sorted(obj, key=lambda x: str(x))]
    # 兜底：转字符串，不静默忽略
    return {"$unhandled": type(obj).__name__, "$repr": repr(obj)}


def _md5_hex(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def build_one_baseline(source_path: Path, out_dir: Path) -> dict:
    """对单个 nova 源文件构建 baseline 记录。"""
    src_text = source_path.read_text(encoding="utf-8")
    tokens = Lexer(src_text).tokenize()
    parser = Parser(tokens, source=source_path.name)
    program = parser.parse()

    ast_obj = _to_jsonable(program)
    # ensure_ascii=False + sort_keys=False → 字段顺序严格 = dataclass 声明顺序
    ast_json_bytes = json.dumps(
        ast_obj, ensure_ascii=False, indent=2, sort_keys=False
    ).encode("utf-8")

    # 落盘 AST JSON
    ast_json_path = out_dir / f"{source_path.stem}.ast.json"
    ast_json_path.write_bytes(ast_json_bytes)

    return {
        "source_file": f"examples/{source_path.name}",
        "source_md5": _md5_hex(src_text.encode("utf-8")),
        "source_lines": len(src_text.splitlines()),
        "ast_json_file": f"fixtures/sh1_parity/{ast_json_path.name}",
        "ast_md5": _md5_hex(ast_json_bytes),
        "ast_json_bytes": len(ast_json_bytes),
    }


def main() -> int:
    examples_dir = _ROOT / "examples"
    out_dir = _ROOT / "fixtures" / "sh1_parity"
    out_dir.mkdir(parents=True, exist_ok=True)

    records: dict[str, dict] = {}
    errors: list[str] = []

    for name in BASELINE_FILES:
        src = examples_dir / name
        if not src.exists():
            errors.append(f"[SKIP] 缺失基准文件：examples/{name}")
            continue
        try:
            rec = build_one_baseline(src, out_dir)
            records[name] = rec
            print(
                f"[OK] {name:<24s}  source_lines={rec['source_lines']:<4d}  "
                f"ast_md5={rec['ast_md5'][:10]}...  ast_bytes={rec['ast_json_bytes']}"
            )
        except ParseError as e:
            errors.append(f"[FAIL] {name}: ParseError @ L{e.line}:C{e.column} {e.message}")
        except Exception as e:  # noqa: BLE001 — 顶层兜底，脚本式运行直接报告
            errors.append(f"[FAIL] {name}: {type(e).__name__}: {e}")

    # 写 baseline 清单
    baseline = {
        "schema_version": "sh1-parity-v1.0",
        "generated_by": "scripts/sh1_baseline.py (Python reference parser)",
        "syntax_freeze": "SYNTAX_FREEZE_v0.5.md",
        "baseline_count": len(records),
        "baseline_files": BASELINE_FILES,
        "records": records,
    }
    baseline_path = out_dir / "baseline.json"
    baseline_path.write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    print()
    print(f"[DONE] 成功 {len(records)}/{len(BASELINE_FILES)} 个基准文件")
    print(f"[DONE] baseline 清单：{baseline_path}")
    if errors:
        print("[WARN] 以下问题需关注：")
        for e in errors:
            print(f"       - {e}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
