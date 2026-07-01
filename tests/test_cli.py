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
