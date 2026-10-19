# DEC-EF-004 — missing baseline cases block the gate

## Status

Accepted (2026-10-18). Amended by DEC-EF-005 (2026-10-19), which binds each
baseline case to its content.

## Context

A perfect average over a smaller set cannot establish that the old regression
suite still passes.

## Decision

The gate now compares the baseline case identifiers with the current report
before accepting score deltas. Every missing baseline identifier appears in
`missing_cases` and blocks the verdict, independent of score tolerance. An
intentionally retired case requires explicit review of a replacement baseline.

New cases are allowed. Empty reports and duplicate identifiers are invalid
input. Existing report schemas stay unchanged; `missing_cases` belongs to the
derived gate verdict.

## Why

Empty reports and duplicate identifiers are rejected because neither gives an
unambiguous set of observations to compare.

## Consequences

The gate checks recorded coverage; it does not prove that a case's text,
dataset, model, or environment stayed equivalent. Pin those artifacts separately
when making a release decision.

DEC-EF-005 closes the case-text part of this gap: a case whose content hash
differs from the baseline's for the same identifier now blocks the gate.
Dataset, model, and environment are still outside the check.
