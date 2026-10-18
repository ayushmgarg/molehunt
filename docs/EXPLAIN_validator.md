# Explain: casebook grading (Section 10)

Total = finding (50) + procedure (20) + evidence (15) + calibration (10)
+ time bonus (5) - 5 x hints - 10 x earlier wrong submissions (floor 0).

- Procedure: 5 each for hashing before analysis, a working copy, notes kept,
  and an untouched original (its SHA-256 still equals the generated one).
- Calibration: 10 x (1 - (p - y)^2), p = stated confidence, y = 1 if correct.
- Time bonus: 5 x max(0, 1 - elapsed / par), only when correct.
- Evidence (case-specific): C1 bit string >= 90% right; C2 erasures marked;
  C3 suspect pool exact (naming one person when the pool is larger costs 15);
  C4 rsid ranked above lastModifiedBy; C5 tie stated before fusion;
  C6 +25 per colluder, -25 per innocent; C7 actor named and alternative kept open.
Advance at 60; the third wrong submission closes the case with partial credit.

Worked example: correct, confidence 0.9, all procedure, evidence met, 300 s of
900 s par: 50 + 20 + 15 + 10(1 - 0.01) + 5(1 - 1/3) = 98.2 -> 98.
