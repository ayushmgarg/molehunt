# Casebook definitions

- Seven YAML files define the case brief, objective, generator type, master, seed offset, tools, and hints.
- The schema rejects unknown fields, including embedded answer keys.
- Briefs are limited to 50 words and each case has three hints.
- A case definition describes a scenario; its solution is generated separately at runtime.
- Case IDs and generator types are validated before any files are made.
- Example: base seed 9 plus the C-01 offset 101 gives its reproducible scenario seed 110.
- Definitions describe all seven syllabus topics; per-player progression and submissions are stored in SQLite.
- The seeded generator writes player files under `public/` and generated truth under `private/`.
- Example: base seed 19 with C-03 offset 303 deterministically selects print metadata and writes `scan.png`.
- C1 markers, print-dot metadata, DOCX metadata, log rows, and Tardos collusion are generated from engine APIs.
