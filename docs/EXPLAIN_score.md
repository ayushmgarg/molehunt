# Explain: candidate scoring

Scoring ignores every `None` erasure. For `n` observed slots, the null model expects
matches from Binomial(`n`, 0.5). The z-score measures distance from `n/2`; the tail
probability reports how often chance reaches at least the observed match count.

The likelihood ratio compares a candidate with per-slot flip rate `e` against the
0.5 null: `((1-e)^m * e^(n-m)) / 0.5^n`. It is evidence weight, not guilt probability.
No observations produce neutral scores and a deterministic alphabetical tie order.

Worked example: 4 matches from 4 slots gives z=2 and null tail p=1/16.
At `e=0.1`, LR is `0.9^4 / 0.5^4 = 10.4976`.
