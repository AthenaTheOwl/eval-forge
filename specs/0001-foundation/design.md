# Design — Foundation

## Shape

Three commands, one schema, one App glue layer.

```
        templates/<shape>/eval_pack.yaml
                     |
                  init   (per-repo, once + on-shape-change)
                     v
              evals/<repo>.yaml
                     |
                   run    (every PR, in customer CI)
                     v
              reports/<run_id>.json
                     |
                  gate    (every PR, in customer CI)
                     v
        PR comment + check status (posted by GitHub App)
```

## Why templates, not LLM generation

LLM-generated eval cases for "your codebase" are confidently wrong
in deep ways. They invent plausible-looking checks that do not
correspond to the customer's actual data, refusal policy, or tool
spec. The customer cannot tell the difference until production
regressions arrive.

Templates plus customer configuration are boring and reliable. The
template knows what shape of cases exist for a RAG repo. The
customer supplies the corpus paths, the refusal policy file, the
allowed tool spec. The init command stitches them. This is the
*gate* discipline: the typed shape is more important than the
contents of any one case.

## Reuse from trace-to-eval-harness

The runner does not reimplement deterministic check primitives. It
imports them from `trace-to-eval-harness` and packages them with
GitHub App glue and per-shape templates. That repo is the harness.
This repo is the gate.

## Per-shape template sketch

```yaml
# templates/rag/eval_pack.yaml
pack_id: rag-default
target_shape: rag
cases:
  - id: recall_at_5_hand_curated
    type: recall_at_k
    k: 5
    inputs_file: "{{corpus}}/recall_inputs.jsonl"
    threshold: 0.85
  - id: citation_faithfulness_basic
    type: citation_faithfulness
    inputs_file: "{{corpus}}/citation_inputs.jsonl"
    threshold: 0.90
  - id: abstention_oov
    type: abstention
    inputs_file: "{{refusal_policy}}/oov_cases.jsonl"
    threshold: 0.95
  - id: refusal_in_policy
    type: refusal
    inputs_file: "{{refusal_policy}}/blocked_cases.jsonl"
    threshold: 1.0
  - id: tool_call_correctness_top_5
    type: tool_call_correctness
    inputs_file: "{{tool_spec}}/top_5_calls.jsonl"
    threshold: 1.0
```

The `{{...}}` placeholders are filled by `eval_forge init` from
customer config.

## Run report sketch

```json
{
  "run_id": "ef-2026-06-19-abc123",
  "pack_id": "rag-default",
  "head_ref": "feat/new-retriever",
  "baseline_ref": "main@abc999",
  "results": [
    {"case_id": "recall_at_5_hand_curated", "score": 0.82,
     "baseline": 0.91, "delta": -0.09, "threshold": 0.85,
     "verdict": "fail"},
    ...
  ],
  "summary": {"passed": 4, "failed": 1, "regressed": 1}
}
```

## GitHub App glue

The App is a thin Python webhook handler. It clones the head ref,
runs `eval_forge run` inside the customer's CI image, posts a
markdown comment with the report, and sets the check status. The
App holds no customer data — runs happen inside customer CI.

## Dependencies

- `pydantic` for typed packs / reports.
- `jsonschema` for validation.
- `pyyaml` for templates.
- `trace-to-eval-harness` as a library dependency.
- `aiohttp` for the GitHub App webhook handler (PR 0003+).

## What is deliberately NOT in v0

- A hosted runner. Customer CI only.
- LLM-driven case generation.
- Non-Python target adapters.
- Multi-repo orchestration.
