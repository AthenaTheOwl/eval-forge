# EvalForge

A GitHub App plus CLI that takes a customer's RAG or agent codebase,
generates a recall@5 + citation-faithfulness + abstention +
refusal-suite + tool-call-correctness eval pack, runs it in CI on
every PR, and surfaces regressions before merge.

## What this is

LangSmith, Braintrust, and Promptfoo ship eval dashboards. EvalForge
ships eval *gates*. The difference matters: a dashboard tells you
that quality regressed last week; a gate blocks the PR that caused
it. AI-PR velocity outran human review at every serious shop in
2026. Evals that don't gate get ignored.

This repo is the productization of the eval suite that
`supplier-risk-rag-agent` already runs in CI. The five checks are:

1. recall@5 — does retrieval return the correct doc in the top 5?
2. citation-faithfulness — does the cited span actually contain the
   claim?
3. abstention — does the agent say "I don't know" when it should?
4. refusal-suite — does the agent refuse out-of-policy requests?
5. tool-call-correctness — when a tool is invoked, do the args match
   the spec?

## Status

v0 scaffold. No implementation yet. Specs in `specs/0001-foundation/`
name the eval-pack schema, the per-shape templates, and the GitHub
App skeleton. PR 0002 lands the CLI that generates and runs a pack
against a fixture RAG repo.

## How to run

Placeholder. Will land in spec 0002. The intended invocation:

```bash
python -m eval_forge init \
  --repo ../supplier-risk-rag-agent \
  --shape rag \
  --out evals/
python -m eval_forge run evals/ --report reports/run.md
python -m eval_forge gate reports/run.md --fail-on-regression
```

The GitHub App invokes the same CLI under the hood, posts the report
as a PR comment, and sets the check status.

## Layout

```
eval-forge/
  README.md
  LICENSE
  AGENTS.md
  .gitignore
  specs/
    0001-foundation/
      requirements.md
      design.md
      tasks.md
      acceptance.md
  docs/
    first-pr.md
  templates/             # per-shape eval-pack templates
  src/                   # arrives in PR 0002
  app/                   # GitHub App glue; arrives in PR 0003
```

## Why this exists

`supplier-risk-rag-agent` runs the exact eval suite (recall@5,
citation-faithfulness, abstention, refusal) in CI today. The
trace-to-eval-harness repo is the open-source prototype. The
framing — *evals as gates, not dashboards* — is the differentiator
against vendors with a year of head start. This repo packages the
discipline.

## Sibling to

- `proof-gate-runner` (same gate-discipline framing for voice / spec
  gates, not eval gates)
- `trace-to-eval-harness` (the trace-format prototype this builds on)
- `agent-notary-layer` (provides receipt schema downstream of eval
  gate verdicts)

## License

MIT. See [LICENSE](LICENSE).
