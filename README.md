# eval-forge

An eval-pack runner. Load a typed eval pack, run its cases against a target,
emit a typed run report, and gate on it. Evals as gates, not dashboards: a
dashboard tells you quality regressed last week; a gate blocks the PR that
caused it.

## What it is

eval-forge turns an eval suite into a merge gate. The pack is a typed bundle
of cases — recall@k, citation-faithfulness, abstention, refusal,
tool-call-correctness. The runner scores each case deterministically against a
target. The gate exits non-zero when any case drops below its threshold (or
below a baseline). The pack shape is the load-bearing contract; the runner and
the gate both consume it.

The five checks:

1. **recall@k** — does retrieval return the gold doc in the top k?
2. **citation-faithfulness** — does the cited span actually contain the claim?
3. **abstention** — does the target say it does not know when it should?
4. **refusal** — does the target refuse an out-of-policy request?
5. **tool-call-correctness** — are tool calls within the allowed spec?

## Who it is for

Teams whose AI-PR velocity outran human review. If retrieval quality or refusal
behavior can regress silently between PRs, eval-forge gives you a gate that runs
in CI and blocks the merge with a flat PR comment naming which case dropped and
by how much.

## How to run

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

The committed example pack (`examples/rag_correctness_pack.yaml`) runs against a
committed deterministic fixture target (`examples/fixture_target/responses.json`).
The fixture *is* the mocked model call — no network, no model key. Running it
reproduces the committed `reports/run.json` exactly.

To see the gate fail, point `run` at the regressed fixture and gate against the
healthy baseline:

```bash
python -m eval_forge run examples/rag_correctness_pack.yaml \
  --target examples/fixture_target_regressed --out reports/regressed.json
python -m eval_forge gate reports/regressed.json --baseline reports/run.json
# exits 1; recall and citation dropped below threshold and below baseline
```

## How it connects

- **trace-to-eval-harness** ships the deterministic check primitives (contains /
  refusal / citation-span / abstention). It is the harness; eval-forge is the
  gate. v0.1 vendors the same check semantics so the package stands alone and
  deploys with no extra resolution; the lineage is recorded in `pyproject.toml`
  and `decisions/DEC-EF-002-vendor-harness-checks.md`.
- **trace-to-eval-cli** is the productized trace ingest layer upstream: it turns
  framework traces into the eval cases a pack would run. eval-forge consumes the
  same case-type vocabulary.
- The GitHub App glue (deferred past v0.1) invokes the same CLI under the hood,
  posts `reports/comment.md` verbatim as a PR comment, and sets the check status.

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

## live demo

A deployable Streamlit app reads the committed eval pack and run report and
shows the cases table, per-case score vs threshold, the pack score, and the gate
verdict interactively. No network, no secrets.

Run locally:

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Deploy: Streamlit Community Cloud -> New app -> repo `AthenaTheOwl/eval-forge`,
branch `main`, main file `streamlit_app.py`. It reads `reports/run.json` and
`examples/rag_correctness_pack.yaml` directly, so it needs no configuration.

## License

MIT. See [LICENSE](LICENSE).
