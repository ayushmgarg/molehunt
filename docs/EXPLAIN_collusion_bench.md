# Explain: collusion benchmark (A12 + Tardos)

For each master, seed, k in {2, 3} and merge strategy (majority, minority,
random): issue Tardos codewords to 50 synthetic employees, pick k colluders with
a seeded RNG, merge their bits slot-wise (`collude_bits`), render the merged copy,
read it back through alignment, score all candidates, calibrate Z by simulation
for a 0.001 family-wise false-accusation target, and accuse scores above Z.

Recorded: colluders, accused, all_caught (every colluder accused), number of
innocents accused, Z, runtime. The plot shows k vs share with all colluders caught.

Worked example: k = 2, majority merge. Where the two copies agree the leak keeps
that bit; where they differ it takes a seeded random choice. Both colluders
score far above Z ~ 4.1 x sqrt(n); an innocent's score has mean 0 and sd sqrt(n).
