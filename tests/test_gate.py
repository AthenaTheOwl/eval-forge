import copy
from pathlib import Path

import pytest

from eval_forge.gate import GateError, comment_markdown, gate_report
from eval_forge.pack import load_pack
from eval_forge.run import load_target, run, run_pack

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


@pytest.mark.parametrize(
    "results", [[], [{"case_id": "same"}, {"case_id": "same"}], [{"id": "x"}]]
)
def test_bad_baseline_is_named_in_the_error(results):
    report = run(PACK, TARGET)
    with pytest.raises(GateError, match=r"\bbaseline\b"):
        gate_report(report, baseline={"results": results, "summary": {"score": 1.0}})


@pytest.mark.parametrize("field", ["verdict", "score"])
def test_result_missing_a_gated_field_is_bad_input(field):
    report = run(PACK, TARGET)
    broken = {**report, "results": [dict(r) for r in report["results"]]}
    del broken["results"][0][field]
    with pytest.raises(GateError, match="^report .*numeric score"):
        gate_report(broken)
    with pytest.raises(GateError, match="^baseline .*numeric score"):
        gate_report(report, baseline=broken)


# ---- content binding (DEC-EF-005) --------------------------------------------


def _edited_pack():
    """The example pack with the two cases the regressed target fails rewritten
    so the regressed responses satisfy them, under the same case ids."""
    pack = load_pack(PACK)
    edited = copy.deepcopy(pack)
    by_id = {case["id"]: case for case in edited["cases"]}
    by_id["recall_at_5_supplier_lookup"]["expect"]["gold_doc"] = "doc-supplier-globex-2025"
    by_id["citation_faithfulness_tier"]["expect"]["claim"] = "acme spend was 4.2m"
    return pack, edited


def test_editing_a_failing_case_under_the_same_id_blocks():
    pack, edited = _edited_pack()
    baseline = run_pack(pack, load_target(TARGET))
    current = run_pack(edited, load_target(REGRESSED))
    # the edit makes every case pass, so only the content binding can catch it
    assert current["summary"]["failed"] == 0
    verdict = gate_report(current, baseline=baseline, tolerance=0.0)
    assert verdict["passed"] is False
    assert verdict["failures"] == [] and verdict["regressions"] == []
    assert verdict["missing_cases"] == []
    changed = {c["case_id"]: c for c in verdict["changed_cases"]}
    assert set(changed) == {"recall_at_5_supplier_lookup", "citation_faithfulness_tier"}
    assert all(c["from"] != c["to"] and c["to"].startswith("sha256:") for c in changed.values())
    md = comment_markdown(current, verdict)
    assert "PR blocked" in md
    assert "baseline cases whose content changed:" in md
    assert "`recall_at_5_supplier_lookup` changed since the baseline" in md


def test_lowering_a_threshold_under_the_same_id_blocks():
    pack = load_pack(PACK)
    edited = copy.deepcopy(pack)
    edited["cases"][0]["threshold"] = 0.0
    baseline = run_pack(pack, load_target(TARGET))
    verdict = gate_report(run_pack(edited, load_target(REGRESSED)), baseline=baseline, tolerance=1.0)
    assert [c["case_id"] for c in verdict["changed_cases"]] == [pack["cases"][0]["id"]]
    assert verdict["passed"] is False


def test_stripping_the_hash_from_the_current_report_blocks():
    baseline = run(PACK, TARGET)
    current = copy.deepcopy(baseline)
    del current["results"][0]["case_hash"]
    verdict = gate_report(current, baseline=baseline)
    assert verdict["passed"] is False
    assert verdict["changed_cases"] == [
        {"case_id": baseline["results"][0]["case_id"], "from": baseline["results"][0]["case_hash"], "to": None}
    ]
    assert "has no content hash in the current report" in comment_markdown(current, verdict)


def test_unchanged_cases_pass_and_report_no_changes():
    report = run(PACK, TARGET)
    verdict = gate_report(copy.deepcopy(report), baseline=report)
    assert verdict["passed"] is True
    assert verdict["changed_cases"] == [] and verdict["unhashed_cases"] == []


def test_baseline_without_hashes_still_gates_on_coverage_and_warns():
    report = run(PACK, TARGET)
    old_baseline = copy.deepcopy(report)
    for result in old_baseline["results"]:
        del result["case_hash"]
    _, edited = _edited_pack()
    current = run_pack(edited, load_target(REGRESSED))
    verdict = gate_report(current, baseline=old_baseline)
    # backward compatible: an old baseline cannot bind content, so it does not block
    assert verdict["passed"] is True
    assert verdict["changed_cases"] == []
    assert verdict["unhashed_cases"] == sorted(r["case_id"] for r in report["results"])
    assert "warning: the baseline has no content hash for 5 case(s)" in comment_markdown(
        current, verdict
    )
    # coverage from DEC-EF-004 still applies to an old baseline
    dropped = {**current, "results": current["results"][1:]}
    assert gate_report(dropped, baseline=old_baseline)["passed"] is False


@pytest.mark.parametrize("bad", [123, ""])
def test_non_string_case_hash_is_bad_input(bad):
    report = run(PACK, TARGET)
    broken = copy.deepcopy(report)
    broken["results"][0]["case_hash"] = bad
    with pytest.raises(GateError, match="^report .*case_hash"):
        gate_report(broken)
    with pytest.raises(GateError, match="^baseline .*case_hash"):
        gate_report(report, baseline=broken)
