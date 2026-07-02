import json
from pathlib import Path

import jsonschema

from eval_forge.run import (
    grade_abstention,
    grade_refusal,
    grade_tool_call_correctness,
    run,
)

REPO = Path(__file__).resolve().parent.parent
PACK = REPO / "examples" / "rag_correctness_pack.yaml"
TARGET = REPO / "examples" / "fixture_target"
REGRESSED = REPO / "examples" / "fixture_target_regressed"
REPORT_SCHEMA = json.loads(
    (REPO / "schemas" / "run_report.schema.json").read_text(encoding="utf-8")
)


def test_run_against_healthy_fixture_passes_all():
    report = run(PACK, TARGET)
    assert report["summary"]["total"] == 5
    assert report["summary"]["passed"] == 5
    assert report["summary"]["failed"] == 0
    assert report["summary"]["score"] == 1.0
    assert all(r["verdict"] == "pass" for r in report["results"])


def test_run_report_matches_schema():
    report = run(PACK, TARGET)
    jsonschema.validate(instance=report, schema=REPORT_SCHEMA)


def test_run_is_deterministic():
    a = run(PACK, TARGET)
    b = run(PACK, TARGET)
    assert a == b


def test_run_against_regressed_fixture_fails_recall_and_citation():
    report = run(PACK, REGRESSED)
    failed = {r["case_id"] for r in report["results"] if r["verdict"] == "fail"}
    assert "recall_at_5_supplier_lookup" in failed
    assert "citation_faithfulness_tier" in failed
    assert report["summary"]["failed"] == 2


def test_committed_report_matches_fresh_run():
    committed = json.loads((REPO / "reports" / "run.json").read_text(encoding="utf-8"))
    fresh = run(PACK, TARGET)
    # run_id/target derive from the path name used by the CLI; compare results + summary
    assert fresh["results"] == committed["results"]
    assert fresh["summary"] == committed["summary"]


# ---- grader fail branches ----------------------------------------------------
# The example fixtures keep abstention/refusal/tool cases passing, so a fresh
# run never reaches these 0.0 returns. Pin them by calling the graders directly.


def test_grade_abstention_scores_zero_when_target_answered():
    score, detail = grade_abstention({}, {"output": "Acme is a tier-2 supplier."})
    assert score == 0.0
    assert detail == "target answered when it should have abstained"


def test_grade_refusal_scores_zero_when_target_complied():
    score, detail = grade_refusal({}, {"output": "Sure, here is how to do that."})
    assert score == 0.0
    assert detail == "target did not refuse an out-of-policy request"


def test_grade_tool_call_correctness_scores_zero_on_disallowed_tool():
    case = {"expect": {"allowed_tools": ["search_corpus", "fetch_doc"]}}
    resp = {"tool_calls": ["search_corpus", "delete_all"]}
    score, detail = grade_tool_call_correctness(case, resp)
    assert score == 0.0
    assert detail == "tool call(s) outside allowed set: ['delete_all']"


def test_grade_tool_call_correctness_scores_zero_on_no_calls():
    case = {"expect": {"allowed_tools": ["search_corpus"]}}
    score, detail = grade_tool_call_correctness(case, {"tool_calls": []})
    assert score == 0.0
    assert detail == "no tool call observed"
