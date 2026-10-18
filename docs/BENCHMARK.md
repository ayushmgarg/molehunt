# Benchmark results (archived run)

Command: `uv run molehunt bench --workers 8` (3 masters x 50 employees x 20 leakers
x 12 attacks x 3 strengths x 10 seeds + 6 chains + 180 Tardos collusion trials).
25,200 runs, 1,136 s on 8 cores. Raw `runs.csv` SHA-256 in `benchmark/runs.sha256`;
all tables and plots in `docs/benchmark/`. Numbers apply only to these synthetic
masters, attacks, and seeds.

## Section 6 targets: 9 / 9 PASS

| Target | Rule | Measured |
|---|---|---|
| top-1 under A1, A2, A3, A4, A5 (each) | 1.0 | 1.0000 |
| top-1 under A1-A4 + 50% truncation | >= 0.95 | 1.0000 |
| top-1 under A7 at 0.15 | >= 0.80 | 1.0000 |
| false-accusation rate (decision rule) | <= 0.001 | 0.0002 (6 of 25,200) |
| collusion k=2 both colluders identified | >= 0.80 | 0.9556 (0 innocents accused) |

## Weak spots (report these honestly)

- **Full scrub + dictionary canonicalisation (A5, A2b, A4, then A6)**: top-1 0.11,
  4 false accusations in 600 runs, mean observed error 0.46. An attacker holding the
  variant dictionary forges bit 0 everywhere; this is the plan's "hard case".
- **A10 noise at strength 1.0** (every variant flipped): top-1 0.57, attribution
  only 0.3%, 2 false accusations.
- **A6 alone**: forged bits raise observed error to 0.24; invisible channels still
  carry the attribution.
- **A9 reorder at 1.0**: observed slots fall to ~80 of 265 (alignment is monotonic).
- **A4 / punctuation slots** read as bit 0 after normalisation (forged, not erased).

See `docs/benchmark/attacks.csv` for every attack and strength, and
`survival.csv` / `plots/survival.png` for correct-read share per channel.
