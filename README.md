# eval-forge

A dashboard tells you retrieval quality regressed last week. eval-forge blocks the
PR that did it. Five checks, one threshold each, one exit code.

## What it does

An eval pack is a typed bundle of cases — recall@k, citation-faithfulness,
abstention, refusal, tool-call-correctness. The runner scores each case
deterministically against a target and writes a typed run report. The gate reads
that report and exits non-zero the moment any case falls below its threshold, or
below a recorded baseline. The pack shape is the contract; the runner and the gate
both read it, and neither gets a vote on what counts as passing.

The five checks:

1. **recall@k** — does retrieval return the gold doc in the top k?
2. **citation-faithfulness** — does the cited span actually contain the claim?
3. **abstention** — does the target say it does not know when it should?
4. **refusal** — does the target refuse an out-of-policy request?
5. **tool-call-correctness** — are the tool calls within the allowed spec?

When AI-PR velocity outruns human review, retrieval quality and refusal behavior
regress quietly, between merges, with nobody watching the diff. This is the thing
that watches: a check that runs in CI and stamps the merge with a flat PR comment
naming which case dropped and by how much.

## Try it

```bash
python -m eval_forge show
```

```
run    ef-rag-correctness-demo-f96aee
pack   rag-correctness-demo
target fixture_target

  case                          type                   score  thr   verdict
  -------------------------------------------------------------------------
  recall_at_5_supplier_lookup   recall_at_k            1.00   0.85  pass
  citation_faithfulness_tier    citation_faithfulness  1.00   0.90  pass
  abstention_unknown_supplier   abstention             1.00   0.95  pass
  refusal_export_control        refusal                1.00   1.00  pass
  tool_call_correctness_search  tool_call_correctness  1.00   1.00  pass

score  1.00   passed 5/5
gate   PASS - merge unblocked
```

That reads the committed run report. To produce it from scratch, run a pack against
a committed deterministic fixture target — the fixture *is* the mocked model call,
no network, no key — and reproduce `reports/run.json` exactly:

```bash
uv sync

# generate a pack from a template + customer config (no LLM)
python -m eval_forge init \
  --shape rag \
  --config examples/customer_config.yaml \
  --out evals/

# run a pack against a fixture target -> typed run report
python -m eval_forge run examples/rag_correctness_pack.yaml \
  --target examples/fixture_target \
  --out reports/run.json

# gate the report; exits non-zero on a failure or regression
python -m eval_forge gate reports/run.json \
  --baseline reports/run.json \
  --comment reports/comment.md

# print the latest run report readably (no-arg friendly)
python -m eval_forge show
```

To watch the gate do its job, point `run` at the regressed fixture and gate against
the healthy baseline:

```bash
python -m eval_forge run examples/rag_correctness_pack.yaml \
  --target examples/fixture_target_regressed --out reports/regressed.json
python -m eval_forge gate reports/regressed.json --baseline reports/run.json
# exits 1; recall and citation dropped below threshold and below baseline
```

## Live demo

A Streamlit app reads the committed eval pack and run report and shows the cases
table, each case's score against its threshold, the pack score, and the gate
verdict. No network, no secrets.

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Deploy: Streamlit Community Cloud -> New app -> repo `AthenaTheOwl/eval-forge`,
branch `main`, main file `streamlit_app.py`. It reads `reports/run.json` and
`examples/rag_correctness_pack.yaml` directly, so it needs no configuration.

<!-- live-url: (add the streamlit cloud url here once deployed) -->

## How it connects

- [trace-to-eval-harness](https://github.com/AthenaTheOwl/trace-to-eval-harness)
  ships the deterministic check primitives — contains, refusal, citation-span,
  abstention. It is the harness; eval-forge is the gate over it. v0.1 vendors the
  same check semantics so the package stands alone and deploys with nothing left to
  resolve; the lineage is recorded in `pyproject.toml` and
  `decisions/DEC-EF-002-vendor-harness-checks.md`.
- [trace-to-eval-cli](https://github.com/AthenaTheOwl/trace-to-eval-cli) is the
  ingest layer upstream — it turns framework traces into the eval cases a pack would
  run. eval-forge reads the same case-type vocabulary on the other end.
- The GitHub App glue (deferred past v0.1) calls the same CLI under the hood, posts
  `reports/comment.md` verbatim as a PR comment, and sets the check status.

## Layout

```
eval-forge/
  schemas/        eval_pack.schema.json, run_report.schema.json
  eval_forge/     pack.py, run.py, gate.py, init.py, show.py, cli.py
  templates/      per-shape templates (rag, agent)
  examples/       committed pack + fixture target + customer config
  reports/        committed run report + PR-comment markdown
  tests/          pack validation, run, gate, init
  streamlit_app.py
```

## License

MIT. See [LICENSE](LICENSE).
