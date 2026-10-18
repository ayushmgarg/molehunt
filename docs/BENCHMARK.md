# Benchmark results (archived run)

Command: `uv run molehunt bench --workers 8` (3 masters x 50 employees x 20 leakers
x 12 attacks x 3 strengths x 10 seeds + 6 chains + 180 Tardos collusion trials).
25,200 runs, 1,228 s on 8 cores (rerun after the weak-spot fixes). Raw `runs.csv` SHA-256 in `benchmark/runs.sha256`;
all tables and plots in `docs/benchmark/`. Numbers apply only to these synthetic
masters, attacks, and seeds.

## Section 6 targets: 9 / 9 PASS

| Target | Rule | Measured |
|---|---|---|
| top-1 under A1, A2, A3, A4, A5 (each) | 1.0 | 1.0000 |
| top-1 under A1-A4 + 50% truncation | >= 0.95 | 1.0000 |
| top-1 under A7 at 0.15 | >= 0.80 | 1.0000 |
| false-accusation rate (decision rule) | <= 0.001 | 0.00008 (2 of 25,200) |
| collusion k=2 both colluders identified | >= 0.80 | 0.9556 (0 innocents accused) |

## Weak spots and what changed

| Attack | Before fixes | After fixes | Fix |
|---|---|---|---|
| Full scrub + dictionary canonicalisation (A5, A2b, A4, A6) | top-1 0.11, **4 false accusations** | top-1 0.39, **0 false accusations** (mostly "no attribution") | forged (all-one-value) channels become erasures |
| A6 dictionary canonicalisation alone | observed error 0.24 | observed error 0.07 | same |
| A9 paragraph shuffle at 1.0 | ~80 of 265 slots read | 264.5 of 265 | paragraphs restored to master order before alignment |
| A10 flip every variant at 1.0 | top-1 0.57, 2 false accusations | unchanged | left as measured: needs the full dictionary, copy then reads as noise |

Still true: punctuation slots normalised by A4 read as bit 0 when only part of the
channel is touched; heavy truncation (keep 15%) leaves ~37 slots, still attributed.

See `docs/benchmark/attacks.csv` for every attack and strength, and
`survival.csv` / `plots/survival.png` for the share read correctly per channel.
