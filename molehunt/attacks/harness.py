"""Run seeded attack experiments and write CSV and plot artifacts."""

from __future__ import annotations

import csv
import math
import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from molehunt.attacks.transform import attack_text
from molehunt.core.codes import generate_codewords
from molehunt.core.render import render_text
from molehunt.core.slots import Slot
from molehunt.core.template import Template
from molehunt.detect.align import align_to_master
from molehunt.detect.extract import extract_variants
from molehunt.detect.score import score_candidates


@dataclass(frozen=True, slots=True)
class BenchmarkRow:
    """Measured result for one employee/attack/strength/seed run."""

    attack_id: str
    strength: float
    seed: int
    leaker_id: str
    observed_slots: int
    matches: int
    log10_lr: float
    top1_correct: bool
    runtime_seconds: float
    channel_survival: tuple[tuple[str, int, int], ...]


def run_text_benchmark(
    template: Template,
    slots: Sequence[Slot],
    key: bytes,
    employee_ids: Sequence[str],
    *,
    attack_ids: Sequence[str] = tuple(f"A{i}" for i in range(1, 11)),
    strengths: Sequence[float] = (0.25, 0.5, 0.75, 1.0),
    seeds: Sequence[int] = (0,),
    flip_rate: float = 0.15,
) -> tuple[BenchmarkRow, ...]:
    """Run each text attack against each synthetic copy and record actual detector results."""
    if len(employee_ids) < 2:
        raise ValueError("benchmark needs at least two employee IDs")
    if len(set(employee_ids)) != len(employee_ids):
        raise ValueError("employee IDs must be unique")
    if not slots:
        raise ValueError("benchmark needs at least one slot")
    if any(attack_id not in {f"A{i}" for i in range(1, 11)} for attack_id in attack_ids):
        raise ValueError("text benchmark supports attacks A1 through A10")
    if any(not math.isfinite(value) or not 0 <= value <= 1 for value in strengths):
        raise ValueError("attack strengths must be between zero and one")
    codewords = generate_codewords(key, employee_ids, len(slots))
    variant_pairs = [(choice.zero, choice.one) for choice in template.choices]
    rows = []
    for attack_id in attack_ids:
        for strength in strengths:
            for seed in seeds:
                for leaker_id in employee_ids:
                    started = time.perf_counter()
                    clean = render_text(template, slots, codewords[leaker_id])
                    attacked = attack_text(
                        clean,
                        attack_id,
                        strength=strength,
                        seed=seed,
                        variants=variant_pairs,
                    )
                    windows = align_to_master(template, slots, attacked)
                    extracted = extract_variants(attacked, windows)
                    observations = [
                        next(item.bit for item in extracted if item.slot_index == index)
                        for index in range(len(slots))
                    ]
                    scores = score_candidates(observations, codewords, flip_rate=flip_rate)
                    actual = next(score for score in scores if score.candidate_id == leaker_id)
                    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
                    slots_by_index = {slot.index: slot for slot in slots}
                    for observation in extracted:
                        counts[slots_by_index[observation.slot_index].channel][1] += 1
                        counts[slots_by_index[observation.slot_index].channel][0] += int(
                            observation.bit is not None
                        )
                    elapsed = time.perf_counter() - started
                    rows.append(
                        BenchmarkRow(
                            attack_id=attack_id,
                            strength=strength,
                            seed=seed,
                            leaker_id=leaker_id,
                            observed_slots=actual.observed_slots,
                            matches=actual.matches,
                            log10_lr=actual.log10_lr,
                            top1_correct=scores[0].candidate_id == leaker_id,
                            runtime_seconds=elapsed,
                            channel_survival=tuple(
                                (channel, count[0], count[1])
                                for channel, count in sorted(counts.items())
                            ),
                        )
                    )
    return tuple(rows)


def write_benchmark(rows: Sequence[BenchmarkRow], output_dir: str | Path) -> dict[str, Path]:
    """Write per-run CSV, channel survival CSV, and accuracy/survival PNG plots."""
    if not rows:
        raise ValueError("no benchmark rows to write")
    output = Path(output_dir)
    results_dir = output / "results"
    plots_dir = output / "plots"
    results_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)
    runs_path = results_dir / "runs.csv"
    with runs_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "attack_id", "strength", "seed", "leaker_id", "observed_slots",
                "matches", "top1_correct", "log10_lr", "runtime_seconds",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.attack_id,
                    row.strength,
                    row.seed,
                    row.leaker_id,
                    row.observed_slots,
                    row.matches,
                    int(row.top1_correct),
                    row.log10_lr,
                    f"{row.runtime_seconds:.8f}",
                ]
            )

    survival: dict[tuple[str, float, str], list[int]] = defaultdict(lambda: [0, 0])
    for row in rows:
        for channel, present, total in row.channel_survival:
            bucket = survival[(row.attack_id, row.strength, channel)]
            bucket[0] += present
            bucket[1] += total
    survival_path = results_dir / "survival.csv"
    with survival_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["attack_id", "strength", "channel", "survived", "total", "fraction"])
        for (attack_id, strength, channel), (present, total) in sorted(survival.items()):
            writer.writerow([attack_id, strength, channel, present, total, present / total])

    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    groups: dict[tuple[str, float], list[int]] = defaultdict(list)
    for row in rows:
        groups[(row.attack_id, row.strength)].append(int(row.top1_correct))
    figure, axis = plt.subplots(figsize=(9, 4.5))
    for attack_id in sorted({key[0] for key in groups}):
        points = sorted(
            (strength, sum(values) / len(values))
            for (candidate_attack, strength), values in groups.items()
            if candidate_attack == attack_id
        )
        axis.plot([point[0] for point in points], [point[1] for point in points], marker="o", label=attack_id)
    axis.set(xlabel="Attack strength", ylabel="Top-1 accuracy", ylim=(0, 1.02))
    axis.grid(alpha=0.25)
    axis.legend(ncol=5, fontsize=8)
    figure.tight_layout()
    accuracy_path = plots_dir / "accuracy.png"
    figure.savefig(accuracy_path, dpi=140)
    plt.close(figure)

    channels = sorted({key[2] for key in survival})
    attack_strengths = sorted({(key[0], key[1]) for key in survival})
    matrix = [
        [
            survival[(attack_id, strength, channel)][0]
            / survival[(attack_id, strength, channel)][1]
            if (attack_id, strength, channel) in survival
            else 0.0
            for channel in channels
        ]
        for attack_id, strength in attack_strengths
    ]
    figure, axis = plt.subplots(figsize=(max(5, len(channels) * 0.8), max(3, len(matrix) * 0.32)))
    image = axis.imshow(matrix, vmin=0, vmax=1, cmap="cividis", aspect="auto")
    axis.set_xticks(range(len(channels)), channels, rotation=30, ha="right")
    axis.set_yticks(range(len(attack_strengths)), [f"{a} / {s:g}" for a, s in attack_strengths])
    figure.colorbar(image, ax=axis, label="Observed fraction")
    figure.tight_layout()
    survival_plot = plots_dir / "survival.png"
    figure.savefig(survival_plot, dpi=140)
    plt.close(figure)
    return {
        "runs": runs_path,
        "survival": survival_path,
        "accuracy_plot": accuracy_path,
        "survival_plot": survival_plot,
    }
