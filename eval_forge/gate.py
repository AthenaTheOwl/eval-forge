"""Gate a run report: pass / fail, plus a PR-comment-shaped markdown artifact.

Two gate modes, both deterministic:
  - threshold gate: any case below its own threshold fails the gate.
  - regression gate: if a baseline report is supplied, any case whose score
    dropped below baseline by more than `tolerance` fails the gate, and so
    does any baseline case missing from the report (DEC-EF-004).

The gate exit code is what blocks the PR. The markdown is the customer surface
the GitHub App would post verbatim; it stays flat — the delta speaks for itself.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class GateError(ValueError):
    """The run report could not be loaded, parsed, or gated."""


def _index_by_case(report: dict[str, Any], label: str) -> dict[str, dict[str, Any]]:
    results = report.get("results")
    if not isinstance(results, list) or not results:
        raise GateError(f"{label} has no results; is this an eval-forge run report?")
    indexed = {}
    for result in results:
        if not isinstance(result, dict) or not isinstance(result.get("case_id"), str):
            raise GateError(f"every {label} result needs a string case_id")
        case_id = result["case_id"]
        if not case_id or case_id in indexed:
            raise GateError(f"{label} case_id values must be non-empty and unique")
        indexed[case_id] = result
    for case_id, result in indexed.items():
        score = result.get("score")
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or result.get("verdict") not in ("pass", "fail")
        ):
            raise GateError(
                f"{label} result {case_id!r} needs a numeric score and a verdict of pass or fail"
            )
    return indexed


def gate_report(
    report: dict[str, Any],
    *,
    baseline: dict[str, Any] | None = None,
    tolerance: float = 0.0,
) -> dict[str, Any]:
    """Return a gate verdict dict: {passed, failures, regressions, missing_cases, score}."""
    failures: list[dict[str, Any]] = []
    regressions: list[dict[str, Any]] = []

    current_index = _index_by_case(report, "report")
    results = list(current_index.values())
    base_index = _index_by_case(baseline, "baseline") if baseline is not None else {}
    missing_cases = sorted(set(base_index) - set(current_index))

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

    passed = not failures and not regressions and not missing_cases
    summary = report.get("summary")
    if not isinstance(summary, dict) or "score" not in summary:
        raise GateError("report has no summary.score; is this an eval-forge run report?")
    return {
        "passed": passed,
        "failures": failures,
        "regressions": regressions,
        "missing_cases": missing_cases,
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

    if verdict.get("missing_cases"):
        lines.extend(["", "baseline cases missing from current report:"])
        for case_id in verdict["missing_cases"]:
            lines.append(f"- `{case_id}` was not evaluated. Restore it or explicitly review a new baseline.")

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
