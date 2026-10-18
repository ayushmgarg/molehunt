"""Rank Tardos codewords and calibrate the accusation threshold by simulation.

Scoring uses the symmetric Tardos sum from ``core/tardos.py``; erasures add 0.

Calibration (SPEC 5.3, "thresholds are calibrated by simulation"): for the
actual leak bits y and biases p, an innocent's codeword is independent of y with
x_i ~ Bernoulli(p_i). We draw ``trials`` such innocent codewords with a seeded
NumPy generator, score each one against y, and set the threshold Z to the
(1 - target / N) quantile of those null scores. With N candidates the chance that
any innocent exceeds Z is then about ``target`` (union bound). Each observed slot
has null mean 0 and variance 1, so z_(1 - target/N) * sqrt(n) is printed as a
Gaussian cross-check only; the simulated value is the one used.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np
from scipy.stats import norm

from molehunt.core.tardos import accusation_score

_CHUNK = 20_000


@dataclass(frozen=True, slots=True)
class TardosCandidateScore:
    """Candidate id and accumulated accusation score."""

    candidate_id: str
    score: float


@dataclass(frozen=True)
class TardosCalibration:
    """Simulated threshold, its inputs, and the sorted null scores behind it."""

    threshold: float
    gaussian_threshold: float
    candidates: int
    target: float
    trials: int
    null_scores: np.ndarray = field(repr=False)


def score_tardos_candidates(
    observations: Sequence[int | None],
    biases: Sequence[float],
    codewords: Mapping[str, Sequence[int]],
) -> tuple[TardosCandidateScore, ...]:
    """Score every employee and return descending scores with stable tie order."""
    if not codewords:
        raise ValueError("at least one candidate codeword is required")
    if len(observations) != len(biases):
        raise ValueError("observations and biases must have equal length")
    results = []
    for candidate_id, codeword in codewords.items():
        if len(codeword) != len(observations):
            raise ValueError("candidate codewords and observations must have equal length")
        results.append(
            TardosCandidateScore(
                candidate_id,
                accusation_score(codeword, observations, biases),
            )
        )
    return tuple(sorted(results, key=lambda item: (-item.score, item.candidate_id)))


def simulate_null_scores(
    observations: Sequence[int | None],
    biases: Sequence[float],
    *,
    trials: int,
    seed: int,
) -> np.ndarray:
    """Score ``trials`` random innocent codewords against the observed leak bits."""
    if len(observations) != len(biases) or trials < 1:
        raise ValueError("observations and biases must match and trials must be positive")
    p = np.asarray(biases, dtype=float)
    observed = np.array([bit is not None for bit in observations])
    y = np.array([bit or 0 for bit in observations])
    plus = np.sqrt((1 - p) / p)
    minus = np.sqrt(p / (1 - p))
    # Score when the innocent bit agrees (x == y) or disagrees, per slot.
    agree = np.where(y == 1, plus, minus) * observed
    disagree = np.where(y == 1, -minus, -plus) * observed
    rng = np.random.default_rng(seed)
    scores = np.empty(trials)
    for start in range(0, trials, _CHUNK):
        size = min(_CHUNK, trials - start)
        bits = rng.random((size, len(p))) < p
        same = bits == (y == 1)
        scores[start : start + size] = np.where(same, agree, disagree).sum(axis=1)
    return scores


def calibrate_threshold(
    observations: Sequence[int | None],
    biases: Sequence[float],
    *,
    candidates: int,
    target: float = 0.001,
    trials: int | None = None,
    seed: int = 0,
) -> TardosCalibration:
    """Set Z at the (1 - target/N) quantile of simulated innocent scores."""
    if candidates < 1 or not 0 < target < 1:
        raise ValueError("candidates must be positive and target in (0, 1)")
    per_candidate = target / candidates
    needed = math.ceil(10 / per_candidate)
    count = max(needed, trials or 0)
    null = np.sort(simulate_null_scores(observations, biases, trials=count, seed=seed))
    threshold = float(np.quantile(null, 1 - per_candidate))
    observed = sum(bit is not None for bit in observations)
    gaussian = float(norm.ppf(1 - per_candidate) * math.sqrt(max(observed, 1)))
    return TardosCalibration(threshold, gaussian, candidates, target, count, null)


def false_accusation_rate(calibration: TardosCalibration, threshold: float) -> float:
    """Estimated chance that at least one of N innocents scores above ``threshold``."""
    null = calibration.null_scores
    above = (len(null) - int(np.searchsorted(null, threshold, side="right"))) / len(null)
    return 1 - (1 - above) ** calibration.candidates


def accuse(scores: Sequence[TardosCandidateScore], threshold: float) -> tuple[str, ...]:
    """Return every candidate whose score exceeds the threshold."""
    return tuple(item.candidate_id for item in scores if item.score > threshold)
