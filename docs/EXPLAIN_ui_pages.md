# Workbench page builder

- `build_pages` creates the Qt tabs and connects buttons to methods on the window controller.
- The controller owns forensic logic; page widgets contain input fields and display regions.
- Each path field has a browse button; output fields use a save dialog.
- The analysis tab reserves a table for candidate ranking and a text area for evidence metadata.
- Example: clicking Run analysis calls the controller's analysis handler using the selected paths.
- The selected dark bench, paper, and amber colors come from `docs/DESIGN.md`.
