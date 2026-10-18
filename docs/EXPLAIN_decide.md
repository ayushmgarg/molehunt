# Explain: decision rule and verbal scale

Ranking alone is not a finding. `decide()` applies two tests.

1. Significance with a family-wise bound. Under H0 an innocent's matches
   m ~ Binomial(n, 0.5), so p_j = P(M >= m_j). With N candidates we flag j only
   if p_j <= alpha / N (Bonferroni). Then P(any innocent flagged) <= alpha.
   Default alpha = 0.001, the plan's 0.1 percent false-accusation target.
2. Separability. The flagged leader must beat every other flagged candidate by
   log10 LR >= 2 (100x). Otherwise the finding is "cannot distinguish".

No flagged candidate gives "no attribution" (insufficient evidence).

Verbal scale on LR (ENFSI-style): 1-10 weak, 10-100 moderate, 100-1,000
moderately strong, 1,000-10,000 strong, 10^4-10^6 very strong, >10^6 extremely
strong. The statement always adds: a match identifies a copy, not a person.

Worked example: N = 50, n = 40, owner m = 38. p = P(M >= 38 | n=40, 0.5) ~ 7e-10
< 0.001/50 = 2e-5, so flagged. With e = 0.15, log10 LR = 38 log10 0.85 + 2 log10 0.15
+ 40 log10 2 ~ 7.7 (extremely strong). The runner-up at m = 24 has log10 LR ~ -2.8,
a margin far above 2, so the outcome is "attribute".
