# Attack benchmark harness

- `run_text_benchmark` issues one synthetic copy per employee, applies each requested attack, then runs alignment and scoring.
- A run is identified by attack, strength, seed, and synthetic employee ID.
- Top-1 accuracy is the fraction of runs where the highest-scoring candidate is the known synthetic leaker.
- Channel survival is `observed bits / eligible slots`, with erasures counted as not observed.
- Runtime is measured around rendering, attack, extraction, and candidate scoring.
- Example: 8 correct top ranks across 10 runs gives top-1 accuracy `8/10 = 0.8`.
- `write_benchmark` writes per-run and per-channel CSV data plus accuracy and survival plots.
- Artifacts describe only the supplied template, roster, attacks, strengths, and seeds.
- Thresholds and attack realism require broader empirical calibration; plots alone do not establish robustness.
