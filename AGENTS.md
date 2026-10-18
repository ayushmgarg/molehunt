# MoleHunt agent rules

Project: forensic document attribution suite (fingerprinted copies, leak analysis, casebook).
Spec: read `SPEC.md` before any task. Do only the phase requested.

1. Python 3.11. No ML or neural libraries (no torch, tensorflow, sklearn, transformers).
2. Deterministic: every random choice derives from HMAC-SHA256 or a seeded RNG passed in.
3. Write tests first (pytest). A task is done only when `pytest -q` passes.
4. Never claim robustness in code, comments, or docs. Robustness comes only from `bench/results` produced by `make bench`.
5. Do not weaken or delete tests to pass. Fix code or ask.
6. Do not hard-code case answers. Answers come only from generated `ground_truth.json`.
7. Synthetic data only. No real names, emails, PII. No network calls or scanning, except the opt-in `molehunt live` LAN demo (PIN-gated, no internet, no scanning).
8. One module per commit. Message: `phase-N: module - what`.
9. Keep modules under 300 lines, typed, with a docstring stating the math or algorithm.
10. After each module write `docs/EXPLAIN_<module>.md` (max 25 lines, plain English, formulas, one worked example) for the viva.
11. For ambiguity, choose the simplest explainable option and log it in `docs/DECISIONS.md`.
12. When asked to review a file, print the complete file, not a diff.
13. Treat erasures as missing data, never as mismatches.
