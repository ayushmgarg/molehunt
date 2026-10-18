"""Measure Tardos collusion tracing: do we name all k colluders and no innocent?

For each master, seed, k, and merge strategy (A12): issue Tardos copies to N
synthetic employees with the per-seed benchmark key, merge k random colluders'
codewords slot-wise, render the merged copy, read it back through alignment,
score every candidate, calibrate Z by simulation for the target family-wise
false-accusation rate, and accuse every score above Z.
"""

from __future__ import annotations

import random
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from molehunt.analysis import observe, tardos_codewords
from molehunt.attacks.collusion import collude_bits
from molehunt.attacks.harness import bench_key
from molehunt.core.autoslots import prepare_master
from molehunt.core.render import render_text
from molehunt.detect.tardos import accuse, calibrate_threshold, score_tardos_candidates


@dataclass(frozen=True, slots=True)
class CollusionRow:
    """Result of one collusion trial."""

    master: str
    seed: int
    k: int
    strategy: str
    colluders: tuple[str, ...]
    accused: tuple[str, ...]
    all_caught: bool
    innocents_accused: int
    threshold: float
    runtime_seconds: float


def _unit(args: tuple[Path, int, tuple[int, ...], tuple[str, ...], int, float]) -> list[CollusionRow]:
    path, seed, ks, strategies, employees, target = args
    key = bench_key(seed)
    prepared = prepare_master(path.read_text(encoding="utf-8"), key)
    roster = [f"E{index:03}" for index in range(1, employees + 1)]
    biases, codewords = tardos_codewords(key, roster, len(prepared.slots))
    rng = random.Random(f"collusion:{path.stem}:{seed}")
    rows = []
    for k in ks:
        for strategy in strategies:
            started = time.perf_counter()
            colluders = tuple(sorted(rng.sample(roster, k)))
            merged = collude_bits([codewords[item] for item in colluders], strategy, seed=seed)
            text = render_text(prepared.template, prepared.slots, merged)
            _, observations = observe(prepared, text)
            scores = score_tardos_candidates(observations, biases, codewords)
            calibration = calibrate_threshold(
                observations, biases, candidates=employees, target=target, seed=seed
            )
            accused = accuse(scores, calibration.threshold)
            rows.append(CollusionRow(
                path.stem, seed, k, strategy, colluders, accused,
                set(colluders) <= set(accused),
                len(set(accused) - set(colluders)),
                calibration.threshold, time.perf_counter() - started,
            ))
    return rows


def run_collusion(
    masters: tuple[Path, ...],
    seeds: tuple[int, ...],
    *,
    ks: tuple[int, ...] = (2, 3),
    strategies: tuple[str, ...] = ("majority", "minority", "random"),
    employees: int = 50,
    target: float = 0.001,
    workers: int = 1,
) -> tuple[CollusionRow, ...]:
    """Run every (master, seed) collusion unit, optionally in worker processes."""
    units = [(path, seed, ks, strategies, employees, target) for path in masters for seed in seeds]
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            batches = list(pool.map(_unit, units))
    else:
        batches = [_unit(unit) for unit in units]
    return tuple(row for batch in batches for row in batch)
