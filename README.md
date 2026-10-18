# MoleHunt

MoleHunt is an offline, synthetic-data suite for document fingerprinting, leak attribution, chain of custody, and guided forensic cases. It is a teaching and validation project, not a claim of court-ready evidence.

## Setup

Requires Windows, macOS, or Linux with [uv](https://docs.astral.sh/uv/) installed. The project pins Python 3.11 in `requires-python`.

```powershell
uv python install 3.11
uv sync
uv run molehunt --help
```

Run the desktop bench with `uv run molehunt serve` when the workbench phase is complete. See `SPEC.md` and `docs/DESIGN.md` for requirements and interface direction.

## Current engine workflow

Create a local key, then analyze a text or DOCX leak against a variation-marked master and a synthetic roster CSV with an `id` column:

```powershell
uv run molehunt init
uv run molehunt analyze data/evidence/leak.txt --master data/masters/master.md --employees data/employees.csv
```

The analyzer reports a ranking and LR. It does not make a final accusation until a decision threshold has been calibrated by the benchmark.

Only generated synthetic people, documents, and logs belong in this repository. No network or scanning features are in scope.
