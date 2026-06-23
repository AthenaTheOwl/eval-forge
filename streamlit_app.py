"""eval-forge — live demo (Streamlit Community Cloud).

Mirrors the no-arg `python -m eval_forge show` verb: reads the committed eval
pack and run report and shows, interactively, which cases passed, the per-case
scores against thresholds, the pack score, and the gate verdict. No network, no
secrets, no model key — runs entirely off the committed example fixture.

Deploy: Streamlit Community Cloud -> New app -> repo AthenaTheOwl/eval-forge,
branch main, main file streamlit_app.py.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st
import yaml

REPO = Path(__file__).resolve().parent
PACK_PATH = REPO / "examples" / "rag_correctness_pack.yaml"
REPORT_PATH = REPO / "reports" / "run.json"


def load_pack() -> dict[str, Any]:
    return yaml.safe_load(PACK_PATH.read_text(encoding="utf-8"))


def load_report() -> dict[str, Any] | None:
    if not REPORT_PATH.exists():
        return None
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


st.set_page_config(page_title="eval-forge — eval gate", layout="wide")
st.title("eval-forge")
st.caption(
    "an eval-pack runner. evals as gates, not dashboards: a pack runs every PR, "
    "and any case below its threshold blocks the merge. this page reads the "
    "committed example run report — no network, no model key."
)

report = load_report()
if report is None:
    st.warning("no run report found at reports/run.json")
    st.stop()

pack = load_pack()
summary = report["summary"]
gate_passed = summary["failed"] == 0

# verdict banner
if gate_passed:
    st.success(
        f"gate PASS — {summary['passed']}/{summary['total']} cases passed · "
        f"score {summary['score']:.2f} · merge unblocked"
    )
else:
    st.error(
        f"gate FAIL — {summary['failed']}/{summary['total']} cases below threshold · "
        f"score {summary['score']:.2f} · merge blocked"
    )

c1, c2, c3, c4 = st.columns(4)
c1.metric("pack", report["pack_id"])
c2.metric("cases passed", f"{summary['passed']}/{summary['total']}")
c3.metric("score", f"{summary['score']:.2f}")
c4.metric("gate", "pass" if gate_passed else "fail")

st.subheader("cases")
only_fail = st.toggle("show only failures", value=False)
rows = [
    {
        "case": r["case_id"],
        "type": r["type"],
        "score": r["score"],
        "threshold": r["threshold"],
        "verdict": r["verdict"],
        "detail": r.get("detail", ""),
    }
    for r in report["results"]
    if not only_fail or r["verdict"] == "fail"
]
st.dataframe(rows, use_container_width=True, hide_index=True)

with st.expander("the eval pack (typed contract the runner + gate consume)"):
    st.caption(
        f"pack `{pack['pack_id']}` · shape `{pack.get('target_shape')}` · "
        f"target `{pack.get('target_repo', 'n/a')}`"
    )
    st.code(yaml.safe_dump(pack, sort_keys=False), language="yaml")

with st.expander("what the five checks mean"):
    st.markdown(
        "- **recall_at_k** — did retrieval return the gold doc in the top k?\n"
        "- **citation_faithfulness** — does the cited span actually contain the claim?\n"
        "- **abstention** — did the target say it does not know when it should?\n"
        "- **refusal** — did the target refuse an out-of-policy request?\n"
        "- **tool_call_correctness** — were tool calls within the allowed spec?"
    )

st.caption(
    "v0.1 ships one committed example pack + fixture target. the runner, gater, and "
    "graders live in `eval_forge/`; the CLI is `init / run / gate / show`. "
    "repo: github.com/AthenaTheOwl/eval-forge"
)
