# First PR (after scaffold)

The literal first PR after this v0 scaffold is PR 0002: pack schema,
the RAG template, and the CLI `init` subcommand.

## Scope

One PR. No runner, no gate, no GitHub App yet. The pack shape is
the load-bearing decision; everything downstream consumes it.

## Files added

```
schemas/eval_pack.schema.json
schemas/run_report.schema.json
templates/rag/eval_pack.yaml
src/eval_forge/__init__.py
src/eval_forge/__main__.py
src/eval_forge/cli.py
src/eval_forge/init.py
scripts/voice_lint.py
scripts/validate_schemas.py
tests/fixtures/customer_config.yaml
tests/fixtures/customer_repo/.gitkeep
tests/test_init_rag.py
pyproject.toml
```

## Files changed

```
README.md         # "How to run" gets the init command for real
AGENTS.md         # uncomment the gate block
```

## Why this scope

The pack schema and the RAG template together pin the contract that
every later PR builds against. Once they are in, the runner has a
typed target and the gate has a typed input.

The `init` subcommand is intentionally limited to template-plus-
config merging. No LLM. No discovery. The customer config file is
the operator's responsibility; the CLI's job is to stitch.

The dogfood pack `evals/eval-forge.yaml` does not land yet — it
arrives in PR 0003 with the runner. v0 of the schema lands here so
PR 0003 has a typed shape to write into.

## Verification

```bash
python -m pip install -e .[dev]
python -m pytest                       # test_init_rag passes
python scripts/voice_lint.py README.md AGENTS.md templates/
python scripts/validate_schemas.py schemas/ templates/
python -m eval_forge init \
  --shape rag \
  --config tests/fixtures/customer_config.yaml \
  --out /tmp/evals/
```

The last command produces `/tmp/evals/rag-default.yaml`. It
validates against the schema. It has exactly the five case types
from `templates/rag/eval_pack.yaml` with the placeholders filled.

## Out of scope (deferred to PR 0003)

- The runner.
- The gate.
- The dogfood pack.
- The GitHub App.

## Decision record

PR 0002 lands `decisions/DEC-EF-000-templates-not-llm-generation.md`
naming why eval cases come from human-curated templates plus
customer config, never from LLM analysis of the customer repo.
