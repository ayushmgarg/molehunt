# Workbench page builder

- `build_pages` creates the Qt tabs and connects buttons to methods on the window controller.
- The controller owns forensic logic; page widgets contain input fields and display regions.
- Each path field has a browse button; output fields use a save dialog.
- The analysis tab reserves a table for candidate ranking and a text area for evidence metadata.
- A second table shows candidate-by-slot comparisons with distinct match, mismatch, and erasure symbols.
- Evidence tools show registry intake rows, byte/Unicode details, and a line diff against the chosen master.
- Casebook mode disables tabs and individual tools until the selected case's progression grants them.
- The timestamped timeline panel has a searchable event table and a separate list of pinned findings.
- Example: clicking Run analysis calls the controller's analysis handler using the selected paths.
- The selected dark bench, paper, and amber colors come from `docs/DESIGN.md`.
