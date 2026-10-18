# MoleHunt stack decision

**Pick: Python 3.11 core + PySide6 desktop.** This is a project-fit choice, not a familiarity default: Unicode, OOXML, image work, statistics, and viva-ready readability dominate the engine; Qt supplies the custom virtualized bench widgets without a web view or second language. The brief replaces the plan’s web UI with native Qt.

Scores use the required 1–5 scale. Weighted score = `sum(weight × rating) / 100`.

| Candidate | Engine 20 | GUI 20 | Verify 15 | Setup 15 | Headless 10 | Explain 10 | Speed 5 | Delivery 5 | /5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A. Python + PySide6 | 5 | 5 | 5 | 5 | 5 | 5 | 4 | 4 | **4.90** |
| B. Python + web UI | 5 | 3 | 5 | 5 | 5 | 5 | 4 | 3 | 4.45 |
| C. Rust + egui/Tauri | 3 | 4 | 3 | 2 | 5 | 3 | 5 | 2 | 3.25 |
| D. C# + Avalonia | 4 | 4 | 4 | 2 | 4 | 3 | 4 | 3 | 3.50 |
| E. Go + Fyne | 3 | 2 | 3 | 1 | 4 | 4 | 4 | 2 | 2.70 |
| F. Java + JavaFX | 3 | 4 | 3 | 2 | 3 | 3 | 4 | 2 | 3.10 |

Windows has Python 3.14 and uv-managed Python 3.11.10, Rust/Cargo 1.75, Java 21, Node 24, .NET SDKs 6/9; Go is absent. The .NET 9 CLI is missing its 9.0.19 runtime. Python already has python-docx, lxml, Pillow, NumPy, SciPy, Matplotlib, PyYAML, pytest, and Tkinter; PySide6 Essentials is now installed in the project environment. Python wins engine fit, headless testing, explainability, and the three-week delivery window. Rust and Go add library/UI work for speed we do not need. Avalonia and JavaFX bring more toolchain setup and weaker engine fit. The trade-off is a sizable Qt binding; Python 3.14 does not meet the spec.

## Risks / mitigations

1. Python launcher does not list uv’s Python: use uv’s pinned 3.11 environment.
2. Qt install/render risk: pin PySide6; check Windows and offscreen rendering early.
3. 1 GB files: file-backed paging; paint visible hex rows only.
4. UI stalls: run analysis in a worker; return immutable results to UI.
5. Fonts absent: bundle the four chosen OFL families and licenses; retain fallbacks.

## Install and run (PowerShell)

With [uv](https://docs.astral.sh/uv/) installed, run at the repository root:

```powershell
uv python install 3.11
uv sync --python 3.11
uv run molehunt serve
```

Later launch: `uv run molehunt serve`. `uv.lock` will pin dependencies and `requires-python` will constrain the runtime.
