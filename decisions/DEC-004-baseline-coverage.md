# DEC-004: Missing baseline cases block the gate

Date: 2026-10-18

A perfect average over a smaller set cannot establish that the old regression
suite still passes. The gate now compares the baseline case identifiers with the
current report before accepting score deltas. Every missing baseline identifier
appears in `missing_cases` and blocks the verdict, independent of score tolerance.
An intentionally retired case requires explicit review of a replacement baseline.

New cases are allowed. Empty reports and duplicate identifiers are invalid input:
neither gives an unambiguous set of observations to compare. Existing report
schemas stay unchanged; `missing_cases` belongs to the derived gate verdict.

This is a bounded implementation of the change-applicability discipline in
[AI Product Team's process-change workflow](https://github.com/3orionkings/ai-product-team/blob/main/workflows/process-change.md).
It checks recorded coverage; it does not prove that a case's text, dataset, model,
or environment stayed equivalent. Pin those artifacts separately when making a
release decision.
