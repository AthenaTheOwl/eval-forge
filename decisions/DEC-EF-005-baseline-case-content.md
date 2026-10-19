# DEC-EF-005 — bind baseline coverage to case content

## Status

Accepted (2026-10-19). Amends DEC-EF-004.

## Context

DEC-EF-004 binds baseline coverage by `case_id` only, and its Consequences say
the gate "does not prove that a case's text … stayed equivalent." That leaves a
same-id edit open. Rewriting a failing case's expected answer to match what the
regressed target now returns passes the gate.

Reproduced against the example pack. With the regressed fixture target, the gate
blocks: `recall_at_5_supplier_lookup` and `citation_faithfulness_tier` fail.
Change the first case's `gold_doc` to `doc-supplier-globex-2025` and the second
case's `claim` to `acme spend was 4.2m`, run again, and gate against the healthy
baseline. The result is 5/5, `passed=True`, exit 0. Every case id is still
present, so DEC-EF-004 has nothing to report.

## Decision

Each run-report result carries `case_hash`: `sha256:` plus the SHA-256 of the
case definition the result was graded against, serialized as canonical JSON
(sorted keys, no whitespace). The hash covers every field of the case: `id`,
`type`, `input`, `expect`, `threshold`, and anything else the pack puts there.

When a baseline is given, the gate compares hashes for every case id present in
both reports:

- Baseline and current hashes differ: the case goes in `changed_cases` and
  blocks the verdict, independent of score and tolerance. The PR comment names
  the case and both hash prefixes.
- The baseline has a hash and the current result has none: the case is also
  listed in `changed_cases`, because removing the hash would otherwise skip the
  check.
- The baseline has no hash: the case goes in `unhashed_cases`. It does not
  block. The CLI prints a warning to stderr and the PR comment adds a warning
  line.

A `case_hash` that is present but not a non-empty string is invalid input
(exit 2), as for the other gated fields.

To accept an intended edit, review it and record a new baseline from the edited
pack, the same path DEC-EF-004 sets for retiring a case.

## Why

- Same-id content is part of what the baseline vouches for. A threshold lowered
  to 0.0 or an expectation rewritten to the regressed output keeps the score
  and coverage unchanged while the meaning of the case changes.
- Hashing the case definition, not the grader output, catches the edit without
  the gate needing the pack. The report stays self-contained.
- Canonical JSON keeps the hash stable across YAML layout and key order, so
  reformatting a pack does not trigger a review.
- `case_hash` is optional in `schemas/run_report.schema.json`. Baselines
  written before this change still load and still gate on coverage and score.
  Blocking on them would fail every existing pipeline until it re-records a
  baseline. A warning keeps them running and tells them their content is not
  bound.

## Consequences

- `reports/run.json` was re-recorded with hashes. Results and summary are
  otherwise unchanged.
- A baseline without hashes is only as strong as DEC-EF-004: coverage and score.
  Re-record it with this version to bind case content.
- The hash covers the case definition only. The target, model, dataset, grader
  code, and environment are still outside it, as DEC-EF-004 says. Pin those
  separately for a release decision.
- Any edit to a case, including a harmless one such as a corrected typo in
  `expect.reason`, needs a reviewed baseline. That review is the intended cost.
