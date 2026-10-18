"""Rank candidate Tardos codewords using keyed bias-aware accusation scores."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from molehunt.core.tardos import accusation_score


@dataclass(frozen=True, slots=True)
class TardosCandidateScore:
    """Candidate id and accumulated accusation score."""

    candidate_id: str
    score: float


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
