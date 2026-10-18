# Explain: player tools (reading order and registry match)

`document_order_bits(template, text)` aligns the suspect to the master and returns
one value per authored slot in reading order: 0, 1, or None (erasure).

`match_registry(observed, registry)` compares with each employee's registry bits
over observed slots only (rule 13: erasures are missing data, not mismatches):
matches m, observed n, disagreements n - m. Rows sort by fewest disagreements.

Worked example: observed `1 0 None 1`, registry A = `1011`, B = `0001`.
A: n = 3, m = 3, disagreements 0. B: n = 3, m = 2 (slot 1 differs), 1. A ranks
first. Slot 3 is skipped for both, so an erasure never counts against anyone.
