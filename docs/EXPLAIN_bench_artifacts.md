# Explain: benchmark artifacts and target check

Files in `bench/results`: `runs.csv` (one row per run), `survival.csv` (attack x
strength x channel: survived/total), `runtime.csv` (mean/median/max seconds per
attack), `roc.csv`, `collusion.csv`, `targets.csv`, `summary.json`.
Plots in `bench/plots`: accuracy vs strength, survival heatmap, ROC, collusion.

ROC: for threshold t on log10 LR, true rate = share of runs with leaker LR > t,
false rate = share of runs where the best innocent LR > t.

Targets (SPEC 6): top-1 = 1.0 under each of A1-A5; >= 0.95 under A1-A4 + 50%
truncation; >= 0.80 under A7 at 0.15; false accusation <= 0.001; collusion k=2
both identified >= 0.80. Each row says PASS, FAIL, or NO DATA. A FAIL is reported
as measured; the detector is not tuned to make it pass.

Worked example: if 598 of 600 A7@0.15 runs rank the leaker first, measured =
0.9967 >= 0.80, verdict PASS.
