import json
from pathlib import Path

import pytest

from eval_forge.cli import main

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "examples" / "customer_config.yaml"


# ---- gate: bad report input exits non-zero with an actionable message --------


def test_gate_missing_report_reports_and_exits_non_zero(tmp_path, capsys):
    code = main(["gate", str(tmp_path / "nope.json")])
    assert code == 2
    err = capsys.readouterr().err
    assert "report not found" in err
    assert "nope.json" in err


def test_gate_non_json_report_reports_and_exits_non_zero(tmp_path, capsys):
    bad = tmp_path / "garbage.json"
    bad.write_text("{not json", encoding="utf-8")
    code = main(["gate", str(bad)])
    assert code == 2
    assert "not valid JSON" in capsys.readouterr().err


def test_gate_wrong_shape_report_reports_and_exits_non_zero(tmp_path, capsys):
    wrong = tmp_path / "wrong.json"
    wrong.write_text('{"foo": 1}', encoding="utf-8")
    code = main(["gate", str(wrong)])
    assert code == 2
    assert "no results" in capsys.readouterr().err


# ---- init: bad config / shape input exits non-zero with a message ------------


def test_init_missing_config_reports_and_exits_non_zero(tmp_path, capsys):
    code = main(
        ["init", "--shape", "rag", "--config", str(tmp_path / "nope.yaml"),
         "--out", str(tmp_path / "out")]
    )
    assert code == 2
    err = capsys.readouterr().err
    assert "config not found" in err
    assert "nope.yaml" in err


def test_init_unknown_shape_reports_and_exits_non_zero(tmp_path, capsys):
    code = main(
        ["init", "--shape", "banana", "--config", str(CONFIG),
         "--out", str(tmp_path / "out")]
    )
    assert code == 2
    err = capsys.readouterr().err
    assert "no template for shape 'banana'" in err


def test_init_config_missing_template_key_reports_and_exits_non_zero(tmp_path, capsys):
    # config drops cited_claim, which templates/rag/eval_pack.yaml requires
    incomplete = tmp_path / "incomplete.yaml"
    incomplete.write_text(
        "corpus: c\nrefusal_policy: r\ntool_spec: t\ngold_doc: g\n", encoding="utf-8"
    )
    code = main(
        ["init", "--shape", "rag", "--config", str(incomplete),
         "--out", str(tmp_path / "out")]
    )
    assert code == 2
    assert "cited_claim" in capsys.readouterr().err


# ---- show: a report the gate rejects exits non-zero with a message -----------


def test_show_duplicate_case_ids_reports_and_exits_non_zero(tmp_path, capsys):
    result = {"case_id": "same", "type": "recall_at_k", "score": 1.0,
              "threshold": 1.0, "verdict": "pass"}
    dup = tmp_path / "dup.json"
    dup.write_text(
        json.dumps({"run_id": "r", "pack_id": "p", "results": [result, result],
                    "summary": {"score": 1.0, "passed": 2, "total": 2}}),
        encoding="utf-8",
    )
    code = main(["show", str(dup)])
    assert code == 2
    assert "case_id values must be non-empty and unique" in capsys.readouterr().err


@pytest.mark.parametrize(
    "content, message",
    [(None, "report not found"), ("{", "not valid JSON"), ("[]", "is not a JSON object")],
)
def test_show_unreadable_report_reports_and_exits_non_zero(tmp_path, capsys, content, message):
    path = tmp_path / "report.json"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    assert main(["show", str(path)]) == 2
    assert message in capsys.readouterr().err


# ---- gate: content binding (DEC-EF-005) ---------------------------------------


def test_gate_blocks_a_case_edited_under_the_same_id(tmp_path, capsys):
    pack = (REPO / "examples" / "rag_correctness_pack.yaml").read_text(encoding="utf-8")
    edited = tmp_path / "pack.yaml"
    edited.write_text(
        pack.replace("gold_doc: doc-supplier-acme-2026", "gold_doc: doc-supplier-globex-2025")
        .replace("claim: acme is a tier-2 supplier", "claim: acme spend was 4.2m"),
        encoding="utf-8",
    )
    current = tmp_path / "current.json"
    assert main(["run", str(edited), "--target", str(REPO / "examples" / "fixture_target_regressed"), "--out", str(current)]) == 0
    capsys.readouterr()
    code = main(["gate", str(current), "--baseline", str(REPO / "reports" / "run.json")])
    out = capsys.readouterr().out
    assert code == 1
    assert "5/5 cases passed" in out and "PR blocked" in out
    assert "`recall_at_5_supplier_lookup` changed since the baseline" in out
    assert "`citation_faithfulness_tier` changed since the baseline" in out


def test_gate_warns_on_a_baseline_without_hashes(tmp_path, capsys):
    committed = json.loads((REPO / "reports" / "run.json").read_text(encoding="utf-8"))
    for result in committed["results"]:
        result.pop("case_hash")
    old = tmp_path / "old_baseline.json"
    old.write_text(json.dumps(committed), encoding="utf-8")
    code = main(["gate", str(REPO / "reports" / "run.json"), "--baseline", str(old)])
    captured = capsys.readouterr()
    assert code == 0
    assert "warning: baseline has no case_hash for 5 case(s)" in captured.err
    assert "DEC-EF-005" in captured.err
