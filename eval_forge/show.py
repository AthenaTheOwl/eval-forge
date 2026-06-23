"""`eval_forge show` — print the latest run report readably.

No-arg friendly: with no path it reads the newest report under reports/.
Prints the cases table, each pass/fail, the score, and the gate verdict.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .gate import gate_report
from .pack import REPO_ROOT

REPORTS_DIR = REPO_ROOT / "reports"


def latest_report_path(reports_dir: Path | None = None) -> Path | None:
    reports_dir = reports_dir or REPORTS_DIR
    if not reports_dir.exists():
        return None
    files = sorted(reports_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def render(report: dict[str, Any]) -> str:
    verdict = gate_report(report)
    s = report["summary"]
    lines: list[str] = []
    lines.append(f"run    {report['run_id']}")
    lines.append(f"pack   {report['pack_id']}")
    lines.append(f"target {report.get('target', '?')}")
    lines.append("")

    cid_w = max((len(r["case_id"]) for r in report["results"]), default=4)
    type_w = max((len(r["type"]) for r in report["results"]), default=4)
    header = f"  {'case'.ljust(cid_w)}  {'type'.ljust(type_w)}  score  thr   verdict"
    lines.append(header)
    lines.append("  " + "-" * (len(header) - 2))
    for r in report["results"]:
        mark = "pass" if r["verdict"] == "pass" else "FAIL"
        lines.append(
            f"  {r['case_id'].ljust(cid_w)}  {r['type'].ljust(type_w)}  "
            f"{r['score']:.2f}   {r['threshold']:.2f}  {mark}"
        )
    lines.append("")
    lines.append(f"score  {s['score']:.2f}   passed {s['passed']}/{s['total']}")
    gate_line = "PASS - merge unblocked" if verdict["passed"] else "FAIL - merge blocked"
    lines.append(f"gate   {gate_line}")
    if not verdict["passed"]:
        for f in verdict["failures"]:
            lines.append(f"       {f['case_id']}: {f.get('detail', 'below threshold')}")
    return "\n".join(lines)


def show(path: str | Path | None = None) -> int:
    if path is None:
        path = latest_report_path()
        if path is None:
            print("no run report found under reports/. run `eval-forge run` first.")
            return 1
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    print(render(report))
    return 0
