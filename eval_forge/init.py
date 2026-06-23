"""`eval_forge init` — generate a pack from a per-shape template plus config.

No LLM. The template knows what shape of cases exist for a RAG / agent repo;
the customer config supplies the corpus, refusal-policy, and tool-spec keys.
init stitches them by substituting {{...}} placeholders. The typed shape is
what holds, not the contents of any one case.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .pack import REPO_ROOT, validate_pack

TEMPLATES_DIR = REPO_ROOT / "templates"

_PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def _fill(text: str, config: dict[str, Any]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in config:
            raise KeyError(f"config is missing key {key!r} required by the template")
        return str(config[key])

    return _PLACEHOLDER.sub(repl, text)


def init_pack(shape: str, config: dict[str, Any]) -> dict[str, Any]:
    """Build a pack dict for `shape`, filling template placeholders from config."""
    template_path = TEMPLATES_DIR / shape / "eval_pack.yaml"
    if not template_path.exists():
        known = sorted(p.name for p in TEMPLATES_DIR.iterdir() if p.is_dir())
        raise FileNotFoundError(f"no template for shape {shape!r}; have: {known}")
    raw = template_path.read_text(encoding="utf-8")
    filled = _fill(raw, config)
    pack = yaml.safe_load(filled)
    validate_pack(pack)
    return pack


def load_config(path: str | Path) -> dict[str, Any]:
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"customer config {path} is not a mapping")
    return doc


def write_pack(pack: dict[str, Any], out_dir: str | Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{pack['pack_id']}.yaml"
    out_path.write_text(yaml.safe_dump(pack, sort_keys=False), encoding="utf-8")
    return out_path
