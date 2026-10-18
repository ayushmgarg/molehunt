"""Run seeded attack experiments (SPEC Section 6) and record what the detector did.

One run = render the leaker's copy, apply an attack or chain, analyse it against
all N candidates, apply the decision rule. Recorded per run: observed slots n,
leaker matches m, leaker log10 LR, top-1 correct, decision outcome, false
accusation (an innocent attributed), best innocent log10 LR (for the ROC curve),
per-channel survival, runtime.

Protocol (`run_protocol`): for each master and seed, a key derived from the seed,
L = keyed slots, 20 leakers drawn from 50 synthetic employees, every single attack
at each strength, plus the chains A1+A2+A3+A4, then + A8 keeping 25/50/75 percent,
then + A7 at 0.15. Collusion runs use Tardos codes (attacks/collusion_bench.py).
Units (master, seed) run in parallel processes; each unit is fully seeded.
"""

from __future__ import annotations

import hashlib
import math
import random
import time
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from molehunt.analysis import analyze_prepared
from molehunt.attacks.transform import attack_text
from molehunt.core.autoslots import PreparedMaster, prepare_master
from molehunt.core.codes import generate_codewords
from molehunt.core.render import render_text
from molehunt.core.slots import Slot
from molehunt.core.template import Template
from molehunt.detect.align import WORD_CHANNELS

TEXT_ATTACKS = ("A1", "A2", "A2b", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "A11")
CORE = (("A1", 1.0), ("A2", 1.0), ("A3", 1.0), ("A4", 1.0))
CHAINS: dict[str, tuple[tuple[str, float], ...]] = {
    "A1+A2+A3+A4": CORE,
    "A1-A4+A8@0.25": (*CORE, ("A8", 0.25)),
    "A1-A4+A8@0.5": (*CORE, ("A8", 0.5)),
    "A1-A4+A8@0.75": (*CORE, ("A8", 0.75)),
    "A1-A4+A8@0.5+A7@0.15": (*CORE, ("A8", 0.5), ("A7", 0.15)),
}


@dataclass(frozen=True, slots=True)
class BenchmarkRow:
    """Measured result for one master/attack/strength/seed/leaker run."""

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
    master: str = "master"
    outcome: str = ""
    false_accusation: bool = False
    best_innocent_log10_lr: float = 0.0


@dataclass(frozen=True)
class ProtocolConfig:
    """Benchmark protocol sizes; defaults follow SPEC Section 6."""

    masters: tuple[Path, ...]
    employees: int = 50
    leakers: int = 20
    seeds: tuple[int, ...] = tuple(range(10))
    strengths: tuple[float, ...] = (0.15, 0.5, 1.0)
    attacks: tuple[str, ...] = TEXT_ATTACKS
    chains: dict[str, tuple[tuple[str, float], ...]] = field(default_factory=lambda: dict(CHAINS))
    flip_rate: float = 0.15
    alpha: float = 0.001
    workers: int = 1


def bench_key(seed: int) -> bytes:
    """Deterministic per-seed benchmark key (never the examiner's real key)."""
    return hashlib.sha256(f"molehunt benchmark key v1:{seed}".encode()).digest()


def run_case(
    prepared: PreparedMaster,
    codewords: dict[str, tuple[int, ...]],
    leaker: str,
    steps: Sequence[tuple[str, float]],
    *,
    seed: int,
    label: str,
    strength: float,
    master: str = "master",
    flip_rate: float = 0.15,
    alpha: float = 0.001,
) -> BenchmarkRow:
    """Attack one copy with ``steps`` (attack, strength) and record the outcome."""
    started = time.perf_counter()
    variants = [
        (choice.zero, choice.one)
        for choice in prepared.template.choices
        if choice.channel in WORD_CHANNELS
    ]
    text = render_text(prepared.template, prepared.slots, codewords[leaker])
    for step, (attack_id, step_strength) in enumerate(steps):
        text = attack_text(
            text, attack_id, strength=step_strength, seed=seed * 100 + step, variants=variants
        )
    result = analyze_prepared(prepared, text, codewords, flip_rate=flip_rate)
    decision = result.decision(alpha=alpha)
    actual = next(score for score in result.scores if score.candidate_id == leaker)
    innocent = max(
        (score.log10_lr for score in result.scores if score.candidate_id != leaker),
        default=0.0,
    )
    return BenchmarkRow(
        attack_id=label, strength=strength, seed=seed, leaker_id=leaker,
        observed_slots=actual.observed_slots, matches=actual.matches,
        log10_lr=actual.log10_lr, top1_correct=result.scores[0].candidate_id == leaker,
        runtime_seconds=time.perf_counter() - started,
        channel_survival=tuple(
            (channel, seen, total) for channel, (seen, total) in result.channel_survival().items()
        ),
        master=master, outcome=decision.outcome,
        false_accusation=decision.outcome == "attribute" and decision.candidate_id != leaker,
        best_innocent_log10_lr=innocent,
    )


def run_text_benchmark(
    template: Template,
    slots: Sequence[Slot],
    key: bytes,
    employee_ids: Sequence[str],
    *,
    attack_ids: Sequence[str] = TEXT_ATTACKS,
    strengths: Sequence[float] = (0.25, 0.5, 0.75, 1.0),
    seeds: Sequence[int] = (0,),
    flip_rate: float = 0.15,
) -> tuple[BenchmarkRow, ...]:
    """Every employee leaks under every single attack, strength, and seed."""
    if len(employee_ids) < 2 or len(set(employee_ids)) != len(employee_ids):
        raise ValueError("benchmark needs at least two unique employee IDs")
    if not slots:
        raise ValueError("benchmark needs at least one slot")
    if any(attack_id not in TEXT_ATTACKS for attack_id in attack_ids):
        raise ValueError(f"text benchmark supports attacks {', '.join(TEXT_ATTACKS)}")
    if any(not math.isfinite(value) or not 0 <= value <= 1 for value in strengths):
        raise ValueError("attack strengths must be between zero and one")
    prepared = PreparedMaster(template, tuple(slots), {})
    codewords = generate_codewords(key, list(employee_ids), len(slots))
    return tuple(
        run_case(
            prepared, codewords, leaker, ((attack_id, strength),), seed=seed,
            label=attack_id, strength=strength, flip_rate=flip_rate,
        )
        for attack_id in attack_ids
        for strength in strengths
        for seed in seeds
        for leaker in employee_ids
    )


def _protocol_unit(args: tuple[Path, int, ProtocolConfig]) -> list[BenchmarkRow]:
    """All runs for one (master, seed) pair; safe to execute in a worker process."""
    path, seed, config = args
    key = bench_key(seed)
    prepared = prepare_master(path.read_text(encoding="utf-8"), key)
    roster = [f"E{index:03}" for index in range(1, config.employees + 1)]
    codewords = generate_codewords(key, roster, len(prepared.slots))
    leakers = random.Random(f"{path.stem}:{seed}").sample(roster, config.leakers)
    common = {"seed": seed, "master": path.stem, "flip_rate": config.flip_rate,
              "alpha": config.alpha}
    rows = []
    for leaker in leakers:
        for attack_id in config.attacks:
            for strength in config.strengths:
                rows.append(run_case(prepared, codewords, leaker, ((attack_id, strength),),
                                     label=attack_id, strength=strength, **common))
        for label, steps in config.chains.items():
            rows.append(run_case(prepared, codewords, leaker, steps, label=label,
                                 strength=1.0, **common))
    return rows


def run_protocol(config: ProtocolConfig) -> tuple[BenchmarkRow, ...]:
    """Run every (master, seed) unit, in parallel when ``workers`` > 1."""
    if not config.masters:
        raise ValueError("protocol needs at least one master")
    if config.leakers > config.employees:
        raise ValueError("leakers cannot exceed employees")
    units = [(path, seed, config) for path in config.masters for seed in config.seeds]
    if config.workers > 1:
        with ProcessPoolExecutor(max_workers=config.workers) as pool:
            batches = list(pool.map(_protocol_unit, units))
    else:
        batches = [_protocol_unit(unit) for unit in units]
    return tuple(row for batch in batches for row in batch)


def write_benchmark(rows: Sequence[BenchmarkRow], output_dir: str | Path, **extra) -> dict[str, Path]:
    """Compatibility entry point; artifacts are written by ``bench_artifacts``."""
    from molehunt.attacks.bench_artifacts import write_artifacts

    return write_artifacts(rows, Path(output_dir), **extra)
