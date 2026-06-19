# Tasks — Foundation

## PR 0002 — pack schema, RAG template, CLI skeleton

- [ ] Write `schemas/eval_pack.schema.json` matching R-EF-001 and
      R-EF-003.
- [ ] Write `schemas/run_report.schema.json` matching R-EF-005.
- [ ] Author `templates/rag/eval_pack.yaml`.
- [ ] Stub `src/eval_forge/__init__.py` and CLI entry point with
      `init`, `run`, `gate` subcommands.
- [ ] Implement `src/eval_forge/init.py` (template + config merge).
- [ ] Add `scripts/voice_lint.py` (copy template).
- [ ] Add `scripts/validate_schemas.py`.
- [ ] Add `pyproject.toml` with `trace-to-eval-harness` as a dep.
- [ ] Write `tests/test_init_rag.py` against a fixture customer
      config.

## PR 0003 — runner, gate, and dogfood pack

- [ ] Implement `src/eval_forge/run.py` (imports from
      trace-to-eval-harness; emits typed report).
- [ ] Implement `src/eval_forge/gate.py` (baseline diff + PR comment
      markdown).
- [ ] Author `templates/agent/eval_pack.yaml`.
- [ ] Author `evals/eval-forge.yaml` — this repo's own dogfood pack.
- [ ] Wire CI to run `eval_forge run evals/ --fail-on-regression`.
- [ ] Write `tests/test_gate_regression_detection.py`.

## PR 0004 — GitHub App skeleton

- [ ] Author `app/webhook.py` accepting `pull_request` events.
- [ ] Author `app/manifest.yaml` for App installation.
- [ ] Document App-installation flow in
      `docs/installing-the-app.md`.
- [ ] Land `decisions/DEC-EF-001-customer-ci-not-hosted-runner.md`.
- [ ] Tag `v0.1` once all gates pass on this repo's own CI.
