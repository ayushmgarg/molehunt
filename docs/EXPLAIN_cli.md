# Explain: command-line interface

`cli.py` imports three command modules that register on one Typer app
(`cli_app.py` holds the app and shared helpers, keeping each file < 300 lines).

Lab (`cli_lab.py`): `init` (key, SQLite, custody log; never prints the key),
`suggest-slots`, `register`, `roster --count 50 --seed 0 -o roster.csv`,
`issue E007 --master M1 -o copy.txt` or batch `issue --master M1 --employees
roster.csv --format txt,docx --out-dir issued/` (`--code tardos` for collusion
mode), `analyze leak.txt --master m.md --employees roster.csv [--logs access.csv]
[--report r.docx] [--collusion]`, `attack --name A3 --strength 0.5`.

Evidence (`cli_evidence.py`): `intake` / `custody intake` (read-only original +
working copy + custody entry), `custody add | verify | show`, `custody demo`
(8-entry chain, one flipped byte, verify prints `BROKEN at seq 7`), and
`report --case C-001 -o report.docx` (full Section 8 report from the registry).

Benchmark (`cli_bench.py`): `bench` with no `--master` runs the Section 6 protocol
over `data/masters` (3 masters x 50 employees x 20 leakers x 12 attacks x 3
strengths x 10 seeds + chains + Tardos collusion) in parallel workers. `--master`
with `--employees` runs a quick single-master benchmark (seed list in `--seeds`).

Finding wording: `analyze` prints the ranking, then `Finding (<outcome>)` from the
decision rule, e.g. "attribute" with the verbal LR phrase and the copy-vs-person caveat.

Worked example: `molehunt analyze issued/E007.txt --master data/masters/m1_roadmap.md
--employees data/demo/roster50.csv` prints 50 rows with E007 first and
`Finding (attribute): ... copy issued to E007 ...`.
