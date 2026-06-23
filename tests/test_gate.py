from pathlib import Path

from eval_forge.gate import comment_markdown, gate_report
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
