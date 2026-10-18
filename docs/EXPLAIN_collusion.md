# Collusion bit selection

- `collude_bits` receives two or more binary codewords with equal length.
- It selects one output bit independently at each position.
- Majority returns the most common bit; minority returns the less common bit.
- When a vote is tied, seeded random selection chooses one colluder's bit.
- Random selection always chooses one colluder's bit, preserving the marking assumption.
- Min and max are explicit stress strategies and may choose a bit no colluder holds.
- Example: inputs `010` and `110` produce `110` under majority.
- A seed makes every tie or random choice reproducible.
- This module combines fingerprints only; it does not compose or edit document text.
