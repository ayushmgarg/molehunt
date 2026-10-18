# Explain: analysis CLI

`init` creates the local 32-byte key file, SQLite registry, and custody log without
printing the key contents.
`register` parses a master, derives its keyed slot map, and stores the master digest and
slot anchors in SQLite. Reusing an ID fails instead of replacing that record.
`suggest-slots` exports curated lexical and spelling proposals with source offsets and
context; it never changes the source file, and each pair needs human approval.
`issue` accepts a registered master ID or path, checks the stored SHA-256, then derives
a codeword from the key and synthetic employee ID. It renders a text, Markdown, or DOCX
copy and records its hash, path, format, master, and synthetic employee in SQLite.
`analyze` reads a master template, CSV roster IDs, and evidence; then calls the same
parse, slot, align, extract, and score functions used by the library.
With `--logs`, it also reads `employee_id,access_level,event` rows and prints a separate
posterior ranking with each access prior and named event multiplier. The report includes
both the original fingerprint ranking and the log-fusion explanation.
`bench` renders synthetic copies, runs the selected attacks, then records rankings,
per-channel survival, and elapsed time as CSV and plots.
`attack --name A3 copy.txt -o scrubbed.txt` applies one seeded A1–A10 or A2b text
transform to a copy and refuses to overwrite its input.
`custody add` records a file's SHA-256 in the JSONL chain and SQLite mirror;
`custody verify` checks the JSONL event chain and `custody show` lists its events.
`intake` creates case-scoped original and working copies and starts the custody log.
`analyze --report output.docx` or `output.pdf` writes a ranking report with the evidence hash and stated limits.
`serve` opens the PySide6 interface for the same issue, analysis, intake, and benchmark flows.

For each attack/strength/seed/employee combination, top-1 accuracy is
`correct highest-ranked candidates / number of runs`.

The printed ranking is not a final accusation. Its threshold stays unset until the
benchmark measures an error rate. PNG input currently reports C7 metadata only; OCR is
not implemented.

Worked run: initialize once, register the master, then issue by registry ID. For analysis,
pass the leak path, source master path, and `--employees` roster.
The report begins with the raw evidence SHA-256 for traceability.
Worked benchmark: pass a synthetic template and roster to `bench --attacks A1,A3
--strengths 0,1 --seeds 7`; it creates `results/` and `plots/` under the output folder.
