# Analysis workbench actions

- The analysis path parses the master, allocates keyed slots, aligns the evidence, extracts bits, and scores candidates.
- Missing slot observations are stored as `None` and shown as erasures in the slot matrix.
- Candidate codewords use the same key and slot count as issuance.
- Optional log fusion adds a separate posterior table and retains its rationale.
- Report export uses the current evidence hash, observed count, candidate scores, and optional fusion scores.
- The Red Team button runs a fixed seeded set: A1, A3, and A8 at strengths 0, 0.5, and 1.
- Example: three attacks × three strengths × one seed produce nine benchmark runs.
- All engine work runs outside Qt widget callbacks; rendering occurs on the main thread.
