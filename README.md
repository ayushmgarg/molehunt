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

Only generated synthetic people, documents, and logs belong in this repository. No network or scanning features are in scope.
