import json
from pathlib import Path

import jsonschema

from eval_forge.run import run

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
