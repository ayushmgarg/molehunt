"""Rank candidates with match statistics, a binomial null, and likelihood ratio."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from scipy.stats import binom


@dataclass(frozen=True, slots=True)
class CandidateScore:
    """Candidate-specific summary over observed (non-erased) slot bits."""

    candidate_id: str
    observed_slots: int
    matches: int
    match_fraction: float | None
    z_score: float
    binomial_p: float
    log10_lr: float


def score_candidates(
    observations: Sequence[int | None],
    codewords: Mapping[str, Sequence[int]],
    *,
    flip_rate: float = 0.15,
) -> tuple[CandidateScore, ...]:
    """Score candidates; the null is 0.5 matches and erasures are omitted."""
    if not 0 < flip_rate < 0.5:
        raise ValueError("flip rate must be strictly between zero and 0.5")
    if not codewords:
        raise ValueError("at least one candidate codeword is required")
    if any(bit not in (0, 1, None) for bit in observations):
        raise ValueError("observations must be binary or None")
    observed_count = sum(bit is not None for bit in observations)
    results = []
    for candidate_id, codeword in codewords.items():
        if not candidate_id:
            raise ValueError("candidate ids must not be empty")
        if len(codeword) != len(observations):
            raise ValueError("candidate codewords and observations must have equal length")
        if any(bit not in (0, 1) for bit in codeword):
            raise ValueError("candidate codewords must be binary")
        matches = sum(
            observed is not None and observed == expected
            for observed, expected in zip(observations, codeword, strict=True)
        )
        if observed_count:
            fraction = matches / observed_count
            z_score = (matches - observed_count / 2) / math.sqrt(observed_count / 4)
            binomial_p = float(binom.sf(matches - 1, observed_count, 0.5))
            log10_lr = (
                matches * math.log10(1 - flip_rate)
                + (observed_count - matches) * math.log10(flip_rate)
                - observed_count * math.log10(0.5)
            )
        else:
            fraction = None
            z_score = 0.0
            binomial_p = 1.0
            log10_lr = 0.0
        results.append(
            CandidateScore(
                candidate_id=candidate_id,
                observed_slots=observed_count,
                matches=matches,
                match_fraction=fraction,
                z_score=z_score,
                binomial_p=binomial_p,
                log10_lr=log10_lr,
            )
        )
    return tuple(sorted(results, key=lambda item: (-item.log10_lr, item.candidate_id)))
