"""eval-forge — live demo (Streamlit Community Cloud).

Two halves:

1. the committed view — mirrors the no-arg `python -m eval_forge show` verb:
   reads the committed eval pack and run report and shows which cases passed,
   per-case scores against thresholds, the pack score, and the gate verdict.

2. the interactive runner — you edit the *target* (the mocked model responses)
   and the page calls the REAL engine live: `eval_forge.run.run_pack` grades
   every case, `eval_forge.gate.gate_report` decides pass/fail. break a
   response and watch the case drop below threshold and the gate flip to
   blocked. no network, no secrets, no model key — the fixture IS the call.

Deploy: Streamlit Community Cloud -> New app -> repo AthenaTheOwl/eval-forge,
branch main, main file streamlit_app.py.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st
import yaml

# the real engine — imported from the package, not reimplemented here.
from eval_forge.pack import load_pack as load_pack_validated
from eval_forge.run import run_pack
from eval_forge.gate import gate_report, comment_markdown

REPO = Path(__file__).resolve().parent
PACK_PATH = REPO / "examples" / "rag_correctness_pack.yaml"
REPORT_PATH = REPO / "reports" / "run.json"
TARGET_PATH = REPO / "examples" / "fixture_target" / "responses.json"


def load_pack() -> dict[str, Any]:
    return yaml.safe_load(PACK_PATH.read_text(encoding="utf-8"))


def load_report() -> dict[str, Any] | None:
    if not REPORT_PATH.exists():
        return None
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def load_target_text() -> str:
    return TARGET_PATH.read_text(encoding="utf-8")


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

# --------------------------------------------------------------------------
# interactive: drive the real runner + gate on a target you edit
# --------------------------------------------------------------------------
st.divider()
st.subheader("run the eval yourself")
st.caption(
    "the table above is a committed report. below, you edit the *target* — the "
    "mocked model responses keyed by case input — and this page calls the real "
    "engine live: `run_pack` grades every case, `gate_report` decides the merge. "
    "break a response, re-run, and watch a case fall below threshold and the "
    "gate flip to blocked."
)

if "target_text" not in st.session_state:
    st.session_state.target_text = load_target_text()

bcol1, bcol2 = st.columns(2)
if bcol1.button("load passing target", use_container_width=True):
    st.session_state.target_text = (REPO / "examples" / "fixture_target" / "responses.json").read_text(encoding="utf-8")
if bcol2.button("load regressed target (gate fails)", use_container_width=True):
    st.session_state.target_text = (REPO / "examples" / "fixture_target_regressed" / "responses.json").read_text(encoding="utf-8")

target_text = st.text_area(
    "target responses (JSON) — each case input -> the model's response",
    key="target_text",
    height=320,
)

st.caption(
    "tip: in `recall/supplier_lookup`, drop `doc-supplier-acme-2026` from "
    "`retrieved` to fail recall_at_k. in `abstention/unknown_supplier`, replace "
    "the output with a confident wrong answer to fail abstention."
)

try:
    parsed = json.loads(target_text)
    responses = parsed.get("responses", parsed)
    if not isinstance(responses, dict):
        raise ValueError("target must be an object (or have a 'responses' object)")
except (json.JSONDecodeError, ValueError) as err:
    st.error(f"target is not valid JSON: {err}")
    st.stop()

# the live pack the engine consumes (validated by the real loader)
live_pack = load_pack_validated(PACK_PATH)

try:
    live_report = run_pack(live_pack, responses, target_name="edited-in-app")
except Exception as err:  # e.g. a case input missing from the edited target
    st.error(f"runner could not grade the target: {err}")
    st.stop()

baseline = load_report()
verdict = gate_report(live_report, baseline=baseline, tolerance=0.0)

live_summary = live_report["summary"]
if verdict["passed"]:
    st.success(
        f"gate PASS — {live_summary['passed']}/{live_summary['total']} cases passed · "
        f"score {live_summary['score']:.2f} · merge unblocked"
    )
else:
    nfail = len(verdict["failures"])
    nreg = len(verdict["regressions"])
    st.error(
        f"gate FAIL — {nfail} case(s) below threshold, {nreg} regression(s) vs the "
        f"committed report · score {live_summary['score']:.2f} · merge blocked"
    )

m1, m2, m3 = st.columns(3)
m1.metric("cases passed", f"{live_summary['passed']}/{live_summary['total']}")
m2.metric("pack score", f"{live_summary['score']:.2f}")
m3.metric("gate", "pass" if verdict["passed"] else "fail")

live_rows = [
    {
        "case": r["case_id"],
        "type": r["type"],
        "score": r["score"],
        "threshold": r["threshold"],
        "verdict": r["verdict"],
        "why": r.get("detail", ""),
    }
    for r in live_report["results"]
]
st.dataframe(live_rows, use_container_width=True, hide_index=True)

with st.expander("the PR comment the gate would post (real `comment_markdown` output)"):
    st.code(comment_markdown(live_report, verdict), language="markdown")

st.caption(
    "v0.1 ships one committed example pack + fixture target. the runner, gater, and "
    "graders live in `eval_forge/`; the CLI is `init / run / gate / show`. this page "
    "imports `run_pack` and `gate_report` directly — same code path the CLI runs. "
    "repo: github.com/AthenaTheOwl/eval-forge"
)
