# Requirements — Foundation

Brand prefix: EF (eval-forge).

## Pack-generation requirements

- **R-EF-001** — The repo SHALL define an eval-pack schema
  `schemas/eval_pack.schema.json` covering: pack_id, target_repo,
  target_shape, cases[], thresholds, baseline_run_ref.
- **R-EF-002** — Target shapes SHALL include at minimum: `rag`,
  `agent`, `hybrid`. Each shape has a curated template in
  `templates/<shape>/eval_pack.yaml`.
- **R-EF-003** — A case SHALL specify: type (one of `recall_at_k`,
  `citation_faithfulness`, `abstention`, `refusal`,
  `tool_call_correctness`), input, expected behavior, and threshold.
- **R-EF-004** — `eval_forge init` SHALL produce a pack by copying
  the relevant template and inserting customer-supplied
  configuration (corpus paths, refusal-policy file, tool spec).
  It SHALL NOT invent cases via LLM in v0.

## Runner requirements

- **R-EF-005** — The runner SHALL execute the pack against the
  target repo's current code and emit a typed report matching
  `schemas/run_report.schema.json`.
- **R-EF-006** — The runner SHALL re-use the trace + eval primitives
  from `trace-to-eval-harness` where possible; this repo is the
  packaging layer, not a fork of the harness.

## Gate requirements

- **R-EF-007** — `eval_forge gate` SHALL exit non-zero when any case
  drops below its baseline by more than the configured threshold.
- **R-EF-008** — The gate SHALL produce a PR-comment-shaped markdown
  artifact suitable for posting verbatim by the GitHub App.

## App requirements

- **R-EF-009** — The GitHub App skeleton SHALL accept `pull_request`
  webhooks, check out the head ref, invoke the runner, and post the
  PR comment plus check status.
- **R-EF-010** — The App SHALL run inside the customer's own CI by
  default; v0 ships no hosted runner.

## Voice and gate requirements

- **R-EF-011** — The PR-comment markdown SHALL pass voice_lint.
- **R-EF-012** — The repo SHALL dogfood itself: an
  `evals/eval-forge.yaml` pack runs in this repo's CI.
