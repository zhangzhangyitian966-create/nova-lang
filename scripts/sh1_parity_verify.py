#!/usr/bin/env python3
"""
SH-1 Parity Verify Tool — Python 参考实现 vs Nova 自举实现 逐字节一致性 diff。

【里程碑关联】M-SH1（Self-Hosting SH-1：lexer+parser 字节级一致）前置闸门 3/3。
【冻结文档】SYNTAX_FREEZE_v0.5.md §8 / §10.2 明确要求的两大产物之二。
【功能】
  1. 读取 fixtures/sh1_parity/baseline.json 中的 8 基准 MD5 锚点
  2. --mode=python：重新用 Python 参考 parser 跑一遍，验证 baseline 未漂移（CI 回归）
  3. --mode=nova  ：调用 `nova compile --dump-ast-json <file>`（未来 Nova 自举编译器），
                    产出的 AST JSON 与 baseline 锚点逐字节比较，输出差异
  4. 两种模式都输出结构化 JSON 报告 + 人类可读摘要，退出码 = 不一致数量

【用法】
  # CI 回归：验证 Python 参考 parser 与 baseline 锚点未漂移
  python3 scripts/sh1_parity_verify.py --mode python

  # SH-1 验证：对比 Nova 自举编译器输出与 baseline
  python3 scripts/sh1_parity_verify.py --mode nova --nova-bin ./build/nova-stage1

【输出】
  - stdout：人类可读摘要（每基准 PASS/FAIL + fail 原因前 500 字节 diff）
  - fixtures/sh1_parity/verify_report.json：结构化报告，CI 可解析
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent                              # /workspace/nova
_PKG_PARENT = _ROOT.parent                        # /workspace （nova 包父目录，import nova.parser 需要）
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))
if str(_HERE) not in sys.path:                    # import sh1_baseline 需要
    sys.path.insert(0, str(_HERE))


# ------------------------------------------------------------
# 数据结构
# ------------------------------------------------------------

@dataclass
class FileResult:
    baseline: str               # 基准文件名 e.g. "hello.nova"
    status: str                 # "PASS" | "FAIL" | "SKIP" | "ERROR"
    expected_md5: str
    actual_md5: Optional[str] = None
    byte_diff_count: Optional[int] = None
    diff_preview: Optional[str] = None   # 人类可读的差异预览（限长）
    detail: str = ""


@dataclass
class VerifyReport:
    mode: str
    schema_version: str = "sh1-parity-v1.0"
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    results: list[FileResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped + self.errors


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _md5_hex(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _load_baseline() -> dict:
    p = _ROOT / "fixtures" / "sh1_parity" / "baseline.json"
    if not p.exists():
        raise FileNotFoundError(
            f"baseline 清单不存在：{p}。请先运行 python3 scripts/sh1_baseline.py"
        )
    return json.loads(p.read_text(encoding="utf-8"))


def _byte_diff_count(a: bytes, b: bytes) -> tuple[int, str]:
    """逐字节比较两个 bytes，返回 (不同字节数, 前 500 字符的人类可读差异预览)"""
    n = min(len(a), len(b))
    diffs = 0
    first_diff_idx: Optional[int] = None
    for i in range(n):
        if a[i] != b[i]:
            diffs += 1
            if first_diff_idx is None:
                first_diff_idx = i
    # 长度差异也算
    diffs += abs(len(a) - len(b))

    if first_diff_idx is None and len(a) == len(b):
        return 0, ""
    # 预览：第一个差异点前后各 40 字节的 hex + ascii
    idx = first_diff_idx if first_diff_idx is not None else min(len(a), len(b))
    start = max(0, idx - 20)
    end_a = min(len(a), idx + 40)
    end_b = min(len(b), idx + 40)
    snippet_a = a[start:end_a]
    snippet_b = b[start:end_b]
    preview = (
        f"first_diff_at_byte={idx} (0x{idx:x}), total_diffs={diffs}, "
        f"len_expected={len(a)} vs len_actual={len(b)}\n"
        f"  expected[{start}:{end_a}] = {snippet_a!r}\n"
        f"  actual  [{start}:{end_b}] = {snippet_b!r}"
    )
    return diffs, preview[:500]


# ------------------------------------------------------------
# Mode = python （验证 baseline 未漂移 · CI 用）
# ------------------------------------------------------------

def _run_python_mode(baseline: dict) -> VerifyReport:
    # 延迟导入：避免 --mode=nova 时也强制需要 parser 包路径
    from nova.lexer import Lexer                              # noqa: E402
    from nova.parser import Parser, ParseError                # noqa: E402
    import sh1_baseline as _sh1b                              # noqa: E402
    _to_jsonable = _sh1b._to_jsonable                         # noqa: E402

    report = VerifyReport(mode="python")
    for name in baseline["baseline_files"]:
        rec = baseline["records"].get(name)
        if rec is None:
            report.skipped += 1
            report.results.append(FileResult(
                baseline=name, status="SKIP",
                expected_md5="(missing record)",
                detail="baseline.json 中无该基准记录",
            ))
            continue
        src_path = _ROOT / rec["source_file"]
        try:
            src = src_path.read_text(encoding="utf-8")
            tokens = Lexer(src).tokenize()
            program = Parser(tokens, source=src_path.name).parse()
            ast_json = json.dumps(
                _to_jsonable(program), ensure_ascii=False, indent=2, sort_keys=False
            ).encode("utf-8")
            actual_md5 = _md5_hex(ast_json)
        except ParseError as e:
            report.errors += 1
            report.results.append(FileResult(
                baseline=name, status="ERROR", expected_md5=rec["ast_md5"],
                detail=f"ParseError L{e.line}:C{e.column} {e.message}",
            ))
            continue
        except Exception as e:  # noqa: BLE001
            report.errors += 1
            report.results.append(FileResult(
                baseline=name, status="ERROR", expected_md5=rec["ast_md5"],
                detail=f"{type(e).__name__}: {e}",
            ))
            continue

        expected_path = _ROOT / rec["ast_json_file"]
        expected_bytes = expected_path.read_bytes()
        diff_count, preview = _byte_diff_count(expected_bytes, ast_json)

        if actual_md5 == rec["ast_md5"] and diff_count == 0:
            report.passed += 1
            report.results.append(FileResult(
                baseline=name, status="PASS",
                expected_md5=rec["ast_md5"], actual_md5=actual_md5,
                byte_diff_count=0,
            ))
        else:
            report.failed += 1
            report.results.append(FileResult(
                baseline=name, status="FAIL",
                expected_md5=rec["ast_md5"], actual_md5=actual_md5,
                byte_diff_count=diff_count, diff_preview=preview,
                detail="Python parser 输出与 baseline 逐字节不一致（baseline 漂移）",
            ))
    return report


# ------------------------------------------------------------
# Mode = nova （对比 Nova 自举编译器输出 · SH-1 移植验证用）
# ------------------------------------------------------------

def _run_nova_mode(baseline: dict, nova_bin: str) -> VerifyReport:
    report = VerifyReport(mode="nova")
    if not Path(nova_bin).expanduser().exists():
        # 不直接报错：把所有基准标记为 SKIP + 顶部 detail 说明
        msg = f"Nova 二进制不存在：{nova_bin}。请先构建 Nova 自举编译器后再运行 --mode=nova。"
        for name in baseline["baseline_files"]:
            rec = baseline["records"].get(name, {})
            report.skipped += 1
            report.results.append(FileResult(
                baseline=name, status="SKIP",
                expected_md5=rec.get("ast_md5", ""),
                detail=msg,
            ))
        # 把消息挂到第一个 SKIP 结果上
        return report

    for name in baseline["baseline_files"]:
        rec = baseline["records"].get(name)
        if rec is None:
            report.skipped += 1
            report.results.append(FileResult(
                baseline=name, status="SKIP", expected_md5="",
                detail="baseline.json 中无记录",
            ))
            continue
        src_path = _ROOT / rec["source_file"]
        try:
            proc = subprocess.run(
                [nova_bin, "compile", "--dump-ast-json", str(src_path)],
                capture_output=True, timeout=60, check=False,
            )
            if proc.returncode != 0:
                report.errors += 1
                report.results.append(FileResult(
                    baseline=name, status="ERROR", expected_md5=rec["ast_md5"],
                    detail=(
                        f"nova 返回码={proc.returncode}\n"
                        f"stderr={(proc.stderr.decode('utf-8', errors='replace'))[:400]}"
                    ),
                ))
                continue
            actual_bytes = proc.stdout
            actual_md5 = _md5_hex(actual_bytes)
        except subprocess.TimeoutExpired:
            report.errors += 1
            report.results.append(FileResult(
                baseline=name, status="ERROR", expected_md5=rec["ast_md5"],
                detail="nova 运行超时 (>60s)",
            ))
            continue
        except Exception as e:  # noqa: BLE001
            report.errors += 1
            report.results.append(FileResult(
                baseline=name, status="ERROR", expected_md5=rec["ast_md5"],
                detail=f"{type(e).__name__}: {e}",
            ))
            continue

        expected_bytes = (_ROOT / rec["ast_json_file"]).read_bytes()
        diff_count, preview = _byte_diff_count(expected_bytes, actual_bytes)

        if actual_md5 == rec["ast_md5"] and diff_count == 0:
            report.passed += 1
            report.results.append(FileResult(
                baseline=name, status="PASS",
                expected_md5=rec["ast_md5"], actual_md5=actual_md5,
                byte_diff_count=0,
            ))
        else:
            report.failed += 1
            report.results.append(FileResult(
                baseline=name, status="FAIL",
                expected_md5=rec["ast_md5"], actual_md5=actual_md5,
                byte_diff_count=diff_count, diff_preview=preview,
                detail="Nova 编译器输出与 baseline 逐字节不一致（SH-1 parity 未通过）",
            ))
    return report


# ------------------------------------------------------------
# 输出
# ------------------------------------------------------------

def _print_human_summary(report: VerifyReport) -> None:
    print()
    print("=" * 72)
    print(f"  SH-1 Parity Verify  —  mode={report.mode}   total={report.total}")
    print(f"    PASS={report.passed}  FAIL={report.failed}  SKIP={report.skipped}  ERROR={report.errors}")
    print("=" * 72)
    for r in report.results:
        tag = {"PASS": "\033[32mPASS\033[0m", "FAIL": "\033[31mFAIL\033[0m",
               "SKIP": "\033[33mSKIP\033[0m", "ERROR": "\033[35mERROR\033[0m"}.get(r.status, r.status)
        print(f"  {tag}  {r.baseline:<28s}  md5_exp={r.expected_md5[:10]}…  md5_act={(r.actual_md5 or '—')[:10]}…")  # noqa: E501
        if r.status == "FAIL" and r.diff_preview:
            print(f"        ↳ {r.diff_preview.splitlines()[0]}")
        if r.status == "ERROR" and r.detail:
            print(f"        ↳ {r.detail[:120]}")
    print()
    print(f"  退出码 = FAIL + ERROR = {report.failed + report.errors}")
    print()


def _write_report_json(report: VerifyReport) -> Path:
    out = _ROOT / "fixtures" / "sh1_parity" / "verify_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(report)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
                   encoding="utf-8")
    return out


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="SH-1 Parity Verify Tool")
    ap.add_argument("--mode", choices=["python", "nova"], default="python",
                    help="python=验证 baseline 未漂移(CI用)；nova=对比 Nova 自举编译器输出")
    ap.add_argument("--nova-bin", default="./build/nova-stage1",
                    help="--mode=nova 时使用的 Nova 编译器二进制路径")
    args = ap.parse_args(argv)

    try:
        baseline = _load_baseline()
    except FileNotFoundError as e:
        print(f"\033[31m[FATAL]\033[0m {e}", file=sys.stderr)
        return 3

    if args.mode == "python":
        report = _run_python_mode(baseline)
    else:
        report = _run_nova_mode(baseline, args.nova_bin)

    report_path = _write_report_json(report)
    _print_human_summary(report)
    print(f"  结构化报告：{report_path}")

    return report.failed + report.errors


if __name__ == "__main__":
    raise SystemExit(main())
