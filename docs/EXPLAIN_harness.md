# Explain: benchmark harness

One run: render the leaker's copy, apply an attack (or chain), analyse it against
all N candidates, apply the decision rule. Recorded: n observed slots, matches m,
leaker log10 LR, top-1 correct, outcome, false accusation (an innocent was
attributed), best innocent log10 LR, per-channel survival, runtime.

Protocol (`run_protocol`, SPEC Section 6): masters x seeds are independent units
run in worker processes. Each unit uses the key `SHA-256("molehunt benchmark key
v1:<seed>")`, 50 synthetic employees, 20 leakers drawn with a seeded RNG, every
attack (A1, A2, A2b, A3-A11) at strengths 0.15/0.5/1.0, and chains
A1+A2+A3+A4, then + A8 keeping 25/50/75 percent, then + A7 at 0.15.

Counts: 3 masters x 10 seeds x 20 leakers x (12 x 3 + 5) = 24,600 runs.

Top-1 accuracy = correct top ranks / runs. False-accusation rate = runs where the
decision attributes an innocent / runs. Survival = observed / total slots per channel.

Worked example: 8 correct top ranks in 10 runs gives 0.8; if 1 of 10,000 runs
attributes an innocent the measured false-accusation rate is 0.0001.
Numbers describe only these synthetic masters, attacks, and seeds.
