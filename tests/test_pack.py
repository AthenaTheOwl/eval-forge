from pathlib import Path

import pytest

from eval_forge.pack import PackError, load_pack, validate_pack

REPO = Path(__file__).resolve().parent.parent
EXAMPLE_PACK = REPO / "examples" / "rag_correctness_pack.yaml"


def test_example_pack_loads_and_validates():
    pack = load_pack(EXAMPLE_PACK)
    assert pack["pack_id"] == "rag-correctness-demo"
    assert pack["target_shape"] == "rag"
    assert len(pack["cases"]) == 5
    types = {c["type"] for c in pack["cases"]}
    assert "recall_at_k" in types
    assert "refusal" in types


def test_validate_rejects_unknown_case_type():
    bad = {
        "pack_id": "x",
        "target_shape": "rag",
        "cases": [
            {"id": "c1", "type": "nonsense", "input": "k", "expect": {}, "threshold": 0.5}
        ],
    }
    with pytest.raises(PackError):
        validate_pack(bad)


def test_validate_rejects_duplicate_case_id():
    bad = {
        "pack_id": "x",
        "target_shape": "rag",
        "cases": [
            {"id": "dup", "type": "refusal", "input": "a", "expect": {}, "threshold": 1.0},
            {"id": "dup", "type": "refusal", "input": "b", "expect": {}, "threshold": 1.0},
        ],
    }
    with pytest.raises(PackError):
        validate_pack(bad)


def test_validate_rejects_threshold_out_of_range():
    bad = {
        "pack_id": "x",
        "target_shape": "rag",
        "cases": [
            {"id": "c1", "type": "refusal", "input": "a", "expect": {}, "threshold": 2.0}
        ],
    }
    with pytest.raises(PackError):
        validate_pack(bad)
