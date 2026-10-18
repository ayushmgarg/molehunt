# Explain: Tardos ranking and threshold calibration

Score. For leak bit y_i, candidate bit x_i and bias p_i the slot adds
+sqrt((1-p)/p) if y=1,x=1; -sqrt(p/(1-p)) if y=1,x=0;
+sqrt(p/(1-p)) if y=0,x=0; -sqrt((1-p)/p) if y=0,x=1. Erasures add 0.

Threshold by simulation. An innocent's bits are independent of the leak:
x_i ~ Bernoulli(p_i). We draw T innocent codewords with a seeded NumPy RNG,
score them against the real leak, and take Z = quantile(null, 1 - target/N).
T is at least 10 / (target/N) so the tail quantile rests on >= 10 samples.
Union bound: P(any of N innocents > Z) <= N * target/N = target.

Each observed slot has null mean 0 and variance 1, so Z ~ z_(1-target/N) sqrt(n)
is a Gaussian cross-check printed beside the simulated Z.

`false_accusation_rate(Z')` reads the same null sample for any slider value Z':
1 - (1 - P(null > Z'))^N.

Worked example: N = 30, target = 0.001, n = 300 observed slots. target/N = 3.3e-5,
z = 3.99, Gaussian Z ~ 3.99 x sqrt(300) ~ 69. Two colluders merging by majority
score well above this; innocents stay near 0 +/- 17.
