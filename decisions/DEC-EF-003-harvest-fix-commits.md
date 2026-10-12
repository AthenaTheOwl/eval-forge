# DEC-EF-003 — harvest environments from fix commits

## Status

Accepted (2026-10-12).

## Context

A repository's history already holds graded tasks nobody has to write: a commit
that fixes a bug and adds a test says "this test fails before the change and
passes after it." SWE-bench (Jimenez et al., 2023,
https://arxiv.org/abs/2310.06770) builds its task instances this way and calls
the grading tests `FAIL_TO_PASS`. eval-forge could not read a repo's history.

## Decision

Add `eval-forge harvest`. A candidate is a non-merge commit among the last
`--max-commits` that touches a source file and a test module (`test_*.py` or
`*_test.py`). For each candidate, in one temporary git worktree: check out the
parent, overlay the commit's test-side files, run the touched test modules,
which must fail; then check out the commit and run them again, which must pass.

A pair that holds becomes an environment case `{id, base_sha, fix_sha,
fail_to_pass, test_cmd}`, typed by `schemas/env_case.schema.json`. Every other
pair is dropped with a reason: `passes_before`, `fails_after`, or `flaky`.

## Why

- The claim is checked, not assumed. A commit subject that says "fix" proves
  nothing; the two test runs do.
- Each side runs twice. A flaky test would misclassify the pair either way, so
  a side whose runs disagree drops it.
- A worktree leaves the caller's checkout untouched, and `git clean` before each
  run keeps one run's leftovers out of the next.
- `test_cmd`'s exit code is the only grader, so any runner works; pytest is the
  default.

## Consequences

- Harvesting executes the target repo's tests. The README says to point it only
  at repos you trust.
- `fail_to_pass` is file-level. Test-id granularity is a later change that keeps
  the schema's shape.
- `harvest` produces environments only. Running an agent in them is out of scope.
