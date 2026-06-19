# Acceptance — v0 Foundation

"v0 done" means the CLI generates a pack from a template plus
customer config, runs it against a fixture RAG repo, emits a typed
report, and the gate correctly fails on a synthetic regression.

## Commands a reviewer must be able to run

```bash
python -m pip install -e .[dev]

python -m eval_forge init \
  --shape rag \
  --config tests/fixtures/customer_config.yaml \
  --out evals/

python -m eval_forge run evals/ \
  --target tests/fixtures/customer_repo \
  --out reports/run.json

python -m eval_forge gate reports/run.json \
  --baseline tests/fixtures/baseline_run.json \
  --comment reports/comment.md
```

The gate command exits 0 against the matching baseline and exits 1
against the synthetic-regression baseline in
`tests/fixtures/regressed_baseline.json`.

## Gates that must pass

- `python -m pytest` exits 0.
- `python scripts/voice_lint.py README.md AGENTS.md templates/
  reports/comment.md` exits 0.
- `python scripts/validate_schemas.py schemas/ templates/ evals/`
  exits 0.
- The dogfood pack `evals/eval-forge.yaml` runs in this repo's own
  CI and gates merges.

## Artifacts that must exist

- `templates/rag/eval_pack.yaml` and `templates/agent/eval_pack.yaml`.
- `evals/eval-forge.yaml` — dogfood pack.
- `tests/fixtures/customer_config.yaml` plus
  `tests/fixtures/customer_repo/`.
- `reports/comment.md` — example PR-comment markdown.
- `decisions/DEC-EF-001-customer-ci-not-hosted-runner.md`.

## Out of scope for v0

- Hosted runner infrastructure.
- LLM-driven case generation.
- Non-Python target repos.
- A web dashboard. The artifact is the PR comment plus the check
  status.

## What "done" feels like

A reviewer points the CLI at the `supplier-risk-rag-agent` repo with
a config file, gets a generated pack, runs it, gets a report. They
inject a regression into that repo, re-run, and watch the gate exit
non-zero with a clean PR-comment markdown explaining which case
failed and by how much. That is the bar.
