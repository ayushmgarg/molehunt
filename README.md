# MoleHunt

MoleHunt is an offline, synthetic-data suite for document fingerprinting, leak attribution, chain of custody, and guided forensic cases. It is a teaching and validation project, not a claim of court-ready evidence.

## Setup

Requires Windows, macOS, or Linux with [uv](https://docs.astral.sh/uv/) installed. The project pins Python 3.11 in `requires-python`.

```powershell
uv python install 3.11
uv sync
uv run molehunt --help
```

The native desktop workbench is still being built. See `SPEC.md` and `docs/DESIGN.md` for its requirements and interface direction.

## Current engine workflow

Try the current workflow with the bundled synthetic master and roster. Create a key, issue one copy, analyze it, then run a small benchmark:

```powershell
uv run molehunt init
uv run molehunt issue E007 --master data/demo/master.md --output data/demo/issued/E007.txt
uv run molehunt analyze data/demo/issued/E007.txt --master data/demo/master.md --employees data/demo/employees.csv
uv run molehunt bench --master data/demo/master.md --employees data/demo/employees.csv --attacks A1,A3,A8 --strengths 0,0.5,1 --seeds 0,1
```

`issue` accepts `.txt`, `.md`, or `.docx` output. The analyzer reports a ranking and LR; it does not make a final accusation until a decision threshold has been calibrated. `bench` writes run and channel-survival CSV files and plots under `bench/` by default.

Only generated synthetic people, documents, and logs belong in this repository. No network or scanning features are in scope.
