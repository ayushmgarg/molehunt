# Native workbench shell

- The PySide6 window is a front end for the same engine functions used by the CLI.
- Tabs provide evidence analysis, copy issuance, intake/custody, the Red Team benchmark, and the Casebook.
- The issue tab registers a template and issues copies through the shared SQLite-backed API.
- Intake stores original/working paths, the evidence hash, and the custody mirror in that registry.
- The Casebook tab generates seeded public evidence, displays hints, checks a submitted answer against private generated truth, and records confidence grades.
- Starting a case enables Casebook mode, which gates tabs and individual inspection actions by persisted tool unlocks; Lab mode can be restored with its checkbox.
- The analysis view shows the candidate table, evidence hash, observed-slot count, and optional DOCX report.
- An optional fusion CSV adds a separate posterior table with access priors and the named event factors.
- Its slot matrix marks each candidate slot with a circle for match, cross for mismatch, and dash for erasure.
- The UI uses the warm-paper and dark-bench colors selected in the design brief.
- If Qt cannot discover system fonts, the app registers an installed Segoe UI/DejaVu/Arial fallback.
- Evidence analysis, intake, custody verification, and benchmarks run on a background thread.
- Example: choose `data/demo/master.md`, issue E007, then analyze the resulting text copy.
- Results label rankings as copy attribution and state that thresholds remain uncalibrated.
- The Evidence tools tab lists intake records, shows raw hex bytes and ASCII, maps selected UTF-8 bytes to characters, and lists non-printing characters in decoded text.
- Timeline, OOXML views, diff overlays, and keyboard-virtualized evidence panels remain in development.
