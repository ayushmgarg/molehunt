"""Write benchmark CSVs, plots, and the SPEC Section 6 target check.

Artifacts under ``<out>/results``: runs.csv, survival.csv, runtime.csv, roc.csv,
targets.csv, summary.json (+ collusion.csv); under ``<out>/plots``: accuracy.png,
survival.png (attack x channel heatmap), roc.png, collusion.png.

ROC: for a threshold t on log10 LR, true-accusation rate = share of runs whose
leaker scores above t; false-accusation rate = share of runs where the best
innocent scores above t. Targets compare measured values to the plan's numbers;
a failed target is written as FAIL, never hidden.
"""

from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from molehunt.attacks.harness import BenchmarkRow


def _rate(values: Sequence[bool]) -> float | None:
    return sum(values) / len(values) if values else None


def _write_csv(path: Path, header: Sequence[str], rows: Sequence[Sequence]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def check_targets(rows: Sequence[BenchmarkRow], collusion: Sequence = ()) -> list[tuple]:
    """Return (target, threshold, measured, runs, PASS/FAIL/NO DATA) rows."""
    def top1(select) -> tuple[float | None, int]:
        chosen = [row.top1_correct for row in rows if select(row)]
        return _rate(chosen), len(chosen)

    results = []
    for attack in ("A1", "A2", "A3", "A4", "A5"):
        measured, count = top1(lambda row, attack=attack: row.attack_id == attack)
        results.append((f"top-1 under {attack} (all strengths)", ">= 1.0", measured, count, 1.0))
    measured, count = top1(lambda row: row.attack_id == "A1-A4+A8@0.5")
    results.append(("top-1 under A1-A4 + 50% truncation", ">= 0.95", measured, count, 0.95))
    measured, count = top1(lambda row: row.attack_id == "A7" and row.strength == 0.15)
    results.append(("top-1 under A7 at 0.15", ">= 0.80", measured, count, 0.80))
    fa = _rate([row.false_accusation for row in rows])
    results.append(("false accusation rate (decision rule)", "<= 0.001", fa, len(rows), None))
    pairs = [row.all_caught for row in collusion if row.k == 2]
    results.append(("collusion k=2 both identified (Tardos)", ">= 0.80", _rate(pairs), len(pairs), 0.80))
    output = []
    for name, rule, measured, count, minimum in results:
        if measured is None:
            verdict = "NO DATA"
        elif minimum is None:
            verdict = "PASS" if measured <= 0.001 else "FAIL"
        else:
            verdict = "PASS" if measured >= minimum else "FAIL"
        shown = "" if measured is None else f"{measured:.4f}"
        output.append((name, rule, shown, count, verdict))
    return output


def _plots(rows: Sequence[BenchmarkRow], survival: dict, roc: list, collusion: Sequence,
           plots: Path) -> dict[str, Path]:
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    paths: dict[str, Path] = {}
    groups: dict[tuple[str, float], list[int]] = defaultdict(list)
    for row in rows:
        groups[(row.attack_id, row.strength)].append(int(row.top1_correct))
    figure, axis = plt.subplots(figsize=(9, 4.5))
    for attack_id in sorted({key[0] for key in groups if "+" not in key[0]}):
        points = sorted((s, sum(v) / len(v)) for (a, s), v in groups.items() if a == attack_id)
        axis.plot([p[0] for p in points], [p[1] for p in points], marker="o", label=attack_id)
    axis.set(xlabel="Attack strength", ylabel="Top-1 accuracy", ylim=(0, 1.02))
    axis.grid(alpha=0.25)
    axis.legend(ncol=6, fontsize=8)
    figure.tight_layout()
    paths["accuracy_plot"] = plots / "accuracy.png"
    figure.savefig(paths["accuracy_plot"], dpi=140)
    plt.close(figure)

    channels = sorted({key[2] for key in survival})
    labels = sorted({(key[0], key[1]) for key in survival})
    matrix = [
        [survival[(a, s, c)][0] / survival[(a, s, c)][1] if (a, s, c) in survival else 0.0
         for c in channels]
        for a, s in labels
    ]
    figure, axis = plt.subplots(figsize=(max(5, len(channels) * 0.8), max(3, len(labels) * 0.3)))
    image = axis.imshow(matrix, vmin=0, vmax=1, cmap="cividis", aspect="auto")
    axis.set_xticks(range(len(channels)), channels, rotation=30, ha="right")
    axis.set_yticks(range(len(labels)), [f"{a} / {s:g}" for a, s in labels], fontsize=7)
    figure.colorbar(image, ax=axis, label="Fraction of slots observed")
    figure.tight_layout()
    paths["survival_plot"] = plots / "survival.png"
    figure.savefig(paths["survival_plot"], dpi=140)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(5, 5))
    axis.plot([item[2] for item in roc], [item[1] for item in roc], marker=".")
    axis.set(xlabel="False accusation rate", ylabel="True accusation rate", xscale="symlog",
             title="ROC over log10 LR threshold")
    axis.grid(alpha=0.25)
    figure.tight_layout()
    paths["roc_plot"] = plots / "roc.png"
    figure.savefig(paths["roc_plot"], dpi=140)
    plt.close(figure)

    if collusion:
        figure, axis = plt.subplots(figsize=(6, 4))
        for strategy in sorted({row.strategy for row in collusion}):
            ks = sorted({row.k for row in collusion if row.strategy == strategy})
            rates = [_rate([r.all_caught for r in collusion
                            if r.k == k and r.strategy == strategy]) for k in ks]
            axis.plot(ks, rates, marker="o", label=strategy)
        axis.set(xlabel="Colluders k", ylabel="Fraction with all colluders accused", ylim=(0, 1.02))
        axis.legend()
        axis.grid(alpha=0.25)
        figure.tight_layout()
        paths["collusion_plot"] = plots / "collusion.png"
        figure.savefig(paths["collusion_plot"], dpi=140)
        plt.close(figure)
    return paths


def write_artifacts(rows: Sequence[BenchmarkRow], output: Path, collusion: Sequence = ()) -> dict[str, Path]:
    """Write all CSV, JSON, and PNG artifacts; return their paths by label."""
    if not rows:
        raise ValueError("no benchmark rows to write")
    results, plots = output / "results", output / "plots"
    results.mkdir(parents=True, exist_ok=True)
    plots.mkdir(parents=True, exist_ok=True)
    paths = {"runs": _write_csv(results / "runs.csv", (
        "master", "attack_id", "strength", "seed", "leaker_id", "observed_slots", "matches",
        "top1_correct", "log10_lr", "outcome", "false_accusation", "best_innocent_log10_lr",
        "runtime_seconds"), [
        (r.master, r.attack_id, r.strength, r.seed, r.leaker_id, r.observed_slots, r.matches,
         int(r.top1_correct), f"{r.log10_lr:.4f}", r.outcome, int(r.false_accusation),
         f"{r.best_innocent_log10_lr:.4f}", f"{r.runtime_seconds:.5f}") for r in rows])}
    survival: dict[tuple[str, float, str], list[int]] = defaultdict(lambda: [0, 0])
    for row in rows:
        for channel, present, total in row.channel_survival:
            survival[(row.attack_id, row.strength, channel)][0] += present
            survival[(row.attack_id, row.strength, channel)][1] += total
    paths["survival"] = _write_csv(
        results / "survival.csv", ("attack_id", "strength", "channel", "survived", "total", "fraction"),
        [(a, s, c, p, t, f"{p / t:.4f}") for (a, s, c), (p, t) in sorted(survival.items())])
    timing: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        timing[row.attack_id].append(row.runtime_seconds)
    paths["runtime"] = _write_csv(results / "runtime.csv", ("attack_id", "runs", "mean_s", "median_s", "max_s"), [
        (a, len(v), f"{statistics.mean(v):.4f}", f"{statistics.median(v):.4f}", f"{max(v):.4f}")
        for a, v in sorted(timing.items())])
    roc = []
    for step in range(-10, 81):
        threshold = step / 2
        roc.append((threshold, _rate([r.log10_lr > threshold for r in rows]),
                    _rate([r.best_innocent_log10_lr > threshold for r in rows])))
    paths["roc"] = _write_csv(results / "roc.csv", ("log10_lr_threshold", "true_rate", "false_rate"),
                              [(t, f"{a:.4f}", f"{b:.5f}") for t, a, b in roc])
    if collusion:
        paths["collusion"] = _write_csv(results / "collusion.csv", (
            "master", "seed", "k", "strategy", "colluders", "accused", "all_caught",
            "innocents_accused", "threshold", "runtime_seconds"), [
            (c.master, c.seed, c.k, c.strategy, " ".join(c.colluders), " ".join(c.accused),
             int(c.all_caught), c.innocents_accused, f"{c.threshold:.2f}", f"{c.runtime_seconds:.3f}")
            for c in collusion])
    targets = check_targets(rows, collusion)
    paths["targets"] = _write_csv(results / "targets.csv", ("target", "rule", "measured", "runs", "verdict"), targets)
    summary = {
        "runs": len(rows),
        "top1_accuracy": round(_rate([r.top1_correct for r in rows]), 5),
        "false_accusation_rate": round(_rate([r.false_accusation for r in rows]), 6),
        "outcomes": {o: sum(r.outcome == o for r in rows) for o in sorted({r.outcome for r in rows})},
        "collusion_trials": len(collusion),
        "collusion_innocents_accused": sum(c.innocents_accused for c in collusion),
        "targets": {name: verdict for name, _, _, _, verdict in targets},
    }
    paths["summary"] = results / "summary.json"
    paths["summary"].write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    paths.update(_plots(rows, survival, roc, collusion, plots))
    return paths
