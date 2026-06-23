# DEC-EF-002 — vendor the harness check semantics in v0.1

## Status

Accepted (2026-06-22).

## Context

The design names `trace-to-eval-harness` as the source of the deterministic
check primitives, and frames eval-forge as the packaging-plus-gate layer over
that harness. The harness is a local sibling repo. It is not published to PyPI,
and a deployable Streamlit Community Cloud build resolves dependencies from
`requirements.txt` against PyPI only.

## Decision

v0.1 vendors the check semantics — contains / refusal / citation-span /
abstention, plus recall@k and tool-call-correctness — directly in
`eval_forge/run.py` rather than importing the harness package. The grader
functions mirror the harness's `runner.py` check behavior.

## Why

- A hard import of an unpublished sibling would break the one-step deploy bar
  the portfolio holds for every deployable repo. The Streamlit demo must boot
  with `streamlit + PyYAML` and nothing else.
- The check semantics are small, deterministic, and stable. Vendoring them costs
  little and keeps the package standing alone.
- The lineage stays explicit: `pyproject.toml` documents the swap path, and this
  record names it.

## Consequences

- When trace-to-eval-harness publishes, swap the vendored graders for an optional
  `[project.optional-dependencies] harness = ["trace-to-eval-harness>=0.1"]` and
  delegate to its `CHECKS` registry. The pack/report schemas do not change.
- Until then, any change to a check's semantics lands in both repos by hand. The
  shared schema vocabulary (the five case types) is the contract that keeps them
  aligned.
