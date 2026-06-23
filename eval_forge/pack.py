"""Load and validate an eval pack.

A pack is YAML or JSON on disk. `load_pack` reads it, validates it against
schemas/eval_pack.schema.json, and returns a plain dict. Validation failures
raise PackError with a flat, customer-shaped message.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "eval_pack.schema.json"

CASE_TYPES = (
    "recall_at_k",
    "citation_faithfulness",
    "abstention",
    "refusal",
    "tool_call_correctness",
)


class PackError(ValueError):
    """A pack failed to load or validate."""


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _read_doc(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        return yaml.safe_load(text)
    if path.suffix.lower() == ".json":
        return json.loads(text)
    # fall back to yaml, which is a superset of json
    return yaml.safe_load(text)


def validate_pack(pack: dict[str, Any]) -> None:
    """Validate a pack dict against the schema. Raises PackError on failure."""
    schema = _load_schema()
    try:
        jsonschema.validate(instance=pack, schema=schema)
    except jsonschema.ValidationError as err:
        where = "/".join(str(p) for p in err.absolute_path) or "<root>"
        raise PackError(f"pack invalid at {where}: {err.message}") from err

    seen: set[str] = set()
    for case in pack["cases"]:
        cid = case["id"]
        if cid in seen:
            raise PackError(f"duplicate case id {cid!r}")
        seen.add(cid)


def load_pack(path: str | Path) -> dict[str, Any]:
    """Read a pack file, validate it, return the dict."""
    path = Path(path)
    if path.is_dir():
        candidates = sorted(
            [p for p in path.iterdir() if p.suffix.lower() in (".yaml", ".yml", ".json")]
        )
        if not candidates:
            raise PackError(f"no pack file found in {path}")
        path = candidates[0]
    if not path.exists():
        raise PackError(f"pack not found: {path}")

    doc = _read_doc(path)
    if not isinstance(doc, dict):
        raise PackError(f"pack {path} is not a mapping")
    validate_pack(doc)
    return doc
