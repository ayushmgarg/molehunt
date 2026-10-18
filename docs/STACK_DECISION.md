# MoleHunt stack decision

**Pick: Python 3.11 core + PySide6 desktop.** This is a project-fit choice, not a familiarity default: Unicode, OOXML, image work, statistics, and viva-ready readability dominate the engine; Qt supplies the custom virtualized bench widgets without a web view or second language. The brief replaces the plan’s web UI with native Qt.

Scores use the required 1–5 scale. Weighted score = `sum(weight × rating) / 100`.

| Candidate | Engine 20 | GUI 20 | Verify 15 | Setup 15 | Headless 10 | Explain 10 | Speed 5 | Delivery 5 | /5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A. Python + PySide6 | 5 | 5 | 5 | 3 | 5 | 5 | 4 | 4 | **4.60** |
| B. Python + web UI | 5 | 3 | 5 | 3 | 5 | 5 | 4 | 3 | 4.15 |
| C. Rust + egui/Tauri | 3 | 4 | 3 | 2 | 5 | 3 | 5 | 2 | 3.25 |
| D. C# + Avalonia | 4 | 4 | 4 | 2 | 4 | 3 | 4 | 3 | 3.50 |
| E. Go + Fyne | 3 | 2 | 3 | 1 | 4 | 4 | 4 | 2 | 2.70 |
| F. Java + JavaFX | 3 | 4 | 3 | 2 | 3 | 3 | 4 | 2 | 3.10 |

Windows has Python 3.14 (not the required 3.11), Rust/Cargo 1.75, Java 21, Node 24, and .NET SDKs 6/9; Go is absent. The .NET 9 CLI is missing its 9.0.19 runtime. No candidate GUI toolkit is installed. Python already has python-docx, lxml, Pillow, NumPy, SciPy, Matplotlib, PyYAML, pytest, and Tkinter; PySide6 and Python 3.11 must be installed. Python wins engine fit, headless testing, explainability, and the three-week delivery window. Rust and Go add library/UI work for speed we do not need. Avalonia and JavaFX are capable but bring more toolchain setup and weaker engine fit. The trade-off is installing Python 3.11 and a sizable Qt binding; Python 3.14 does not meet the spec.

## Risks / mitigations

1. Python 3.11 absent: install x64, verify `py -3.11`, pin it in setup.
2. Qt install/render risk: pin PySide6; check Windows and offscreen rendering early.
3. 1 GB files: file-backed paging; paint visible hex rows only.
4. UI stalls: run analysis in a worker; return immutable results to UI.
5. Fonts absent: bundle the four chosen OFL families and licenses; retain fallbacks.

## Install and run (PowerShell)

Install Python 3.11 x64 and the launcher from [python.org](https://www.python.org/downloads/), then run at the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\molehunt.exe serve
```

Later launch: `.\.venv\Scripts\molehunt.exe serve`. The editable install will pin dependencies and define this entry point.
