# Explain: Tardos candidate ranking

Candidate Tardos codewords are scored with the slot bias and observed leak bit.
Each slot uses the symmetric contribution from `core/tardos.py`.
An erasure contributes zero. Ties sort by synthetic employee ID.

Worked example: if a candidate has bit 1, the leak bit is 1, and `p=0.25`,
the slot adds `sqrt(0.75 / 0.25) = sqrt(3)`.
The final score is not an accusation threshold; calibration belongs to benchmarking.
