# Explain: analysis CLI

`init` creates the local 32-byte key file without printing its contents.
`issue` derives a codeword from the key and synthetic employee ID, then renders a text
or DOCX copy using the master template's keyed slot map.
`analyze` reads a master template, CSV roster IDs, and evidence; then calls the same
parse, slot, align, extract, and score functions used by the library.
`bench` renders synthetic copies, runs the selected attacks, then records rankings,
per-channel survival, and elapsed time as CSV and plots.
`custody add` records a file's SHA-256; `custody verify` checks the JSONL event chain.
`intake` creates case-scoped original and working copies and starts the custody log.
`analyze --report output.docx` adds a DOCX ranking report with the evidence hash and stated limits.
`serve` opens the PySide6 interface for the same issue, analysis, intake, and benchmark flows.

For each attack/strength/seed/employee combination, top-1 accuracy is
`correct highest-ranked candidates / number of runs`.

The printed ranking is not a final accusation. Its threshold stays unset until the
benchmark measures an error rate. PNG input currently reports C7 metadata only; OCR is
not implemented.

Worked run: initialize once, then pass the leak path, `--master`, and `--employees`.
The report begins with the raw evidence SHA-256 for traceability.
Worked benchmark: pass a synthetic template and roster to `bench --attacks A1,A3
--strengths 0,1 --seeds 7`; it creates `results/` and `plots/` under the output folder.
