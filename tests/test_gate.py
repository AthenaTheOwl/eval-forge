from pathlib import Path

import pytest

from eval_forge.gate import GateError, comment_markdown, gate_report
from eval_forge.run import run

REPO = Path(__file__).resolve().parent.parent
PACK = REPO / "examples" / "rag_correctness_pack.yaml"
TARGET = REPO / "examples" / "fixture_target"
REGRESSED = REPO / "examples" / "fixture_target_regressed"


def test_gate_passes_on_healthy_report():
    verdict = gate_report(run(PACK, TARGET))
    assert verdict["passed"] is True
    assert verdict["failures"] == []


def test_gate_fails_on_threshold_breach():
    verdict = gate_report(run(PACK, REGRESSED))
    assert verdict["passed"] is False
    failed = {f["case_id"] for f in verdict["failures"]}
    assert "recall_at_5_supplier_lookup" in failed


def test_gate_detects_regression_vs_baseline():
    baseline = run(PACK, TARGET)        # all scores 1.0
    current = run(PACK, REGRESSED)      # recall + citation dropped to 0
    verdict = gate_report(current, baseline=baseline, tolerance=0.0)
    assert verdict["passed"] is False
    regressed = {r["case_id"] for r in verdict["regressions"]}
    assert "recall_at_5_supplier_lookup" in regressed
    assert "citation_faithfulness_tier" in regressed


def test_gate_passes_when_no_regression_vs_equal_baseline():
    report = run(PACK, TARGET)
    verdict = gate_report(report, baseline=report, tolerance=0.0)
    assert verdict["passed"] is True
    assert verdict["regressions"] == []


def test_comment_markdown_is_flat_and_complete():
    report = run(PACK, REGRESSED)
    verdict = gate_report(report)
    md = comment_markdown(report, verdict)
    assert "eval-forge" in md
    assert "below threshold:" in md
    assert "recall_at_5_supplier_lookup" in md


def test_dropped_baseline_case_blocks_even_when_remaining_cases_pass():
    baseline = run(PACK, TARGET)
    current = {**baseline, "results": baseline["results"][1:]}
    missing = baseline["results"][0]["case_id"]
    verdict = gate_report(current, baseline=baseline, tolerance=1.0)
    assert verdict["passed"] is False
    assert verdict["missing_cases"] == [missing]
    assert verdict["regressions"] == []
    md = comment_markdown(current, verdict)
    assert "PR blocked" in md and missing in md
    assert "was not evaluated" in md


def test_added_case_does_not_count_as_lost_coverage():
    report = run(PACK, TARGET)
    baseline = {**report, "results": report["results"][1:]}
    assert gate_report(report, baseline=baseline)["passed"] is True


@pytest.mark.parametrize("results", [[], [{"case_id": "same"}, {"case_id": "same"}]])
def test_empty_or_ambiguous_case_coverage_is_bad_input(results):
    with pytest.raises(GateError):
        gate_report({"results": results, "summary": {"score": 1.0}})
