from pathlib import Path

from eval_forge.init import init_pack, load_config
from eval_forge.pack import validate_pack

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "examples" / "customer_config.yaml"


def test_init_rag_fills_template_and_validates():
    config = load_config(CONFIG)
    pack = init_pack("rag", config)
    validate_pack(pack)
    assert pack["pack_id"] == "rag-default"
    assert len(pack["cases"]) == 5
    # placeholders resolved
    recall = next(c for c in pack["cases"] if c["type"] == "recall_at_k")
    assert recall["expect"]["gold_doc"] == "doc-supplier-acme-2026"
    assert "{{" not in recall["input"]


def test_init_agent_shape():
    config = load_config(CONFIG)
    pack = init_pack("agent", config)
    validate_pack(pack)
    assert pack["target_shape"] == "agent"
