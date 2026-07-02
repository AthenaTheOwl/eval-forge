"""Gate a run report: pass / fail, plus a PR-comment-shaped markdown artifact.

Two gate modes, both deterministic:
  - threshold gate: any case below its own threshold fails the gate.
  - regression gate: if a baseline report is supplied, any case whose score
    dropped below baseline by more than `tolerance` fails the gate.

The gate exit code is what blocks the PR. The markdown is the customer surface
the GitHub App would post verbatim; it stays flat — the delta speaks for itself.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class GateError(ValueError):
    """The run report could not be loaded, parsed, or gated."""


def _index_by_case(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {r["case_id"]: r for r in report.get("results", [])}


def gate_report(
    report: dict[str, Any],
    *,
    baseline: dict[str, Any] | None = None,
    tolerance: float = 0.0,
) -> dict[str, Any]:
    """Return a gate verdict dict: {passed: bool, failures: [...], regressions: [...]}."""
    failures: list[dict[str, Any]] = []
    regressions: list[dict[str, Any]] = []

    results = report.get("results")
    if not isinstance(results, list):
        raise GateError("report has no results; is this an eval-forge run report?")

    base_index = _index_by_case(baseline) if baseline else {}

    for r in results:
        if r["verdict"] == "fail":
            failures.append(r)
        if baseline:
            prev = base_index.get(r["case_id"])
            if prev is not None:
                delta = r["score"] - prev["score"]
                if delta < -tolerance:
                    regressions.append(
                        {
                            "case_id": r["case_id"],
                            "from": prev["score"],
                            "to": r["score"],
                            "delta": round(delta, 4),
                        }
                    )

    passed = not failures and not regressions
    summary = report.get("summary")
    if not isinstance(summary, dict) or "score" not in summary:
        raise GateError("report has no summary.score; is this an eval-forge run report?")
    return {
        "passed": passed,
        "failures": failures,
        "regressions": regressions,
        "score": summary["score"],
    }


def comment_markdown(report: dict[str, Any], verdict: dict[str, Any]) -> str:
    """Build the PR-comment markdown. Flat, no marketing words."""
    summary = report["summary"]
    head = "passed" if verdict["passed"] else "blocked"
    lines = [
        f"### eval-forge — PR {head}",
        "",
        f"pack `{report['pack_id']}` · {summary['passed']}/{summary['total']} cases passed "
        f"· score {summary['score']:.2f}",
        "",
        "| case | type | score | threshold | verdict |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in report["results"]:
        lines.append(
            f"| `{r['case_id']}` | {r['type']} | {r['score']:.2f} | "
            f"{r['threshold']:.2f} | {r['verdict']} |"
        )

    if verdict["regressions"]:
        lines.append("")
        lines.append("regressions vs baseline:")
        for reg in verdict["regressions"]:
            lines.append(
                f"- `{reg['case_id']}` dropped from {reg['from']:.2f} to "
                f"{reg['to']:.2f} ({reg['delta']:+.2f})."
            )

    if verdict["failures"]:
        lines.append("")
        lines.append("below threshold:")
        for f in verdict["failures"]:
            lines.append(
                f"- `{f['case_id']}` scored {f['score']:.2f}, "
                f"threshold {f['threshold']:.2f}. {f.get('detail', '')}".rstrip()
            )

    if verdict["passed"]:
        lines.append("")
        lines.append("no case dropped below threshold or baseline. merge unblocked.")

    lines.append("")
    return "\n".join(lines)


def load_report(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise GateError(f"report not found: {path}")
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as err:
        raise GateError(f"report is not valid JSON: {path} ({err})")
    if not isinstance(doc, dict):
        raise GateError(f"report {path} is not a JSON object")
    return doc
