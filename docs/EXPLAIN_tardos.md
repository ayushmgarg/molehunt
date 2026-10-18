# Explain: Tardos codes

Each slot receives keyed bias `p = sin²(r)`, with `r` uniform between
the cutoff and `pi/2 - cutoff`. A code bit is one when its keyed uniform draw is `< p`.
This symmetric distribution favours both near-zero and near-one probabilities.

Candidate scores use the specified symmetric Tardos formula per observed bit.
Matches add weight; mismatches subtract weight; erasures add zero.
`marking_violations` detects a leak bit that contradicts all colluders' shared bit.

Worked example: at `p = 0.25`, a candidate zero matching leak zero adds
`sqrt(0.25 / 0.75)`. An erased slot adds nothing.

The score is not itself a calibrated accusation threshold. Thresholds require simulation.
