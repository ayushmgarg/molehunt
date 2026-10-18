# MoleHunt

MoleHunt is an offline, synthetic-data suite for document fingerprinting, leak attribution, chain of custody, and guided forensic cases. It is a teaching and validation project, not a claim of court-ready evidence.

## Setup

Requires Windows, macOS, or Linux with [uv](https://docs.astral.sh/uv/) installed. The project pins Python 3.11 in `requires-python`.

```powershell
uv python install 3.11
uv sync
uv run molehunt --help
```

Open the current native desktop workbench with `uv run molehunt serve`. It includes copy issuance, analysis, intake/custody, and a seeded Red Team bench. The casebook and several advanced forensic views remain in development. See `SPEC.md` and `docs/DESIGN.md` for the full target.

## Current engine workflow

Try the current workflow with the bundled synthetic master and roster. Create a key, issue one copy, analyze it, then run a small benchmark:

```powershell
uv run molehunt init
uv run molehunt suggest-slots data/demo/master.md --output reports/slot-suggestions.csv
uv run molehunt register data/demo/master.md --master-id demo-master
uv run molehunt issue E007 --master demo-master --output data/demo/issued/E007.txt
uv run molehunt analyze data/demo/issued/E007.txt --master data/demo/master.md --employees data/demo/employees.csv --report reports/generated/E007.docx
uv run molehunt bench --master data/demo/master.md --employees data/demo/employees.csv --attacks A1,A3,A8 --strengths 0,0.5,1 --seeds 0,1
```

`init` creates the local key, SQLite registry, and custody log. `register` stores a master and its keyed slot map; `issue` accepts a registered master ID or path and records the synthetic employee and issued copy. Issue output accepts `.txt`, `.md`, or `.docx`. The analyzer reports a ranking and LR; it does not make a final accusation until a decision threshold has been calibrated. `bench` writes run and channel-survival CSV files and plots under `bench/` by default.

`suggest-slots` exports curated lexical and spelling candidates with offsets and surrounding context. Review every proposal for meaning and grammar before adding variation markers to a master.

Optional log fusion uses `analyze ... --logs access.csv`; the CSV columns are `employee_id,access_level,event`, with access levels `direct`, `indirect`, or `none` and documented event names such as `print_job` or `after_hours_download`. The report preserves fingerprint scores and adds the fused posterior and applied factors. These log weights are demo assumptions, not calibrated probabilities.

Only generated synthetic people, documents, and logs belong in this repository. No network or scanning features are in scope.
