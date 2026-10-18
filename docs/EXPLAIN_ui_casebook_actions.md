# Casebook workbench actions

- `CasebookActions` connects player controls to the seeded case and progression services.
- Starting a case stores progress before generating a unique output folder for the selected seed.
- Hints are obtained from the case definition and recorded by the progression service.
- Answer checking reads the private generated `ground_truth.json` for the current case instance.
- The check compares case-specific fields, such as an owner ID, printer ID, or a set of colluders.
- Confidence grading uses the Brier score: `B = (p - o)^2`, where `o` is 1 for correct and 0 otherwise.
- Example: confidence 0.8 on a correct answer gives `(0.8 - 1)^2 = 0.04`.
- Starting a case turns on Casebook mode and enables only tabs and controls listed in that case's earned tools.
- The ranked detector stays hidden until its `auto_detector` unlock; the manual candidate matrix can unlock earlier.
- The UI action layer does not contain case answers; generated truth remains the source of expected values.
