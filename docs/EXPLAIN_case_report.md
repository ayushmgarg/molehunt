# Explain: case report and tamper demo

`build_case_report` reads a case's evidence rows from SQLite, re-hashes each
read-only original (`hash ok` / `HASH MISMATCH`), verifies the case custody chain
(`chain verified (n)` / `chain BROKEN at seq k`), analyses the first text or DOCX
working copy, and writes the Section 8 report with a slot-matrix excerpt
(top 5 candidates x first 24 observed slots: o match, x mismatch) and the first
128 bytes as a hex excerpt.

`tamper_demo` writes an 8-entry chain, flips the bits of one byte in entry 7
("EX-DEMO" becomes "EX-DEMP"), and verifies again. Because
entry_hash = SHA-256(prev_hash || canonical_json(entry)), entry 7's stored hash no
longer matches, so verification stops with `BROKEN at seq 7`.

Worked example: `molehunt custody demo` prints `VERIFIED: 8 entries` then
`BROKEN at seq 7`.
