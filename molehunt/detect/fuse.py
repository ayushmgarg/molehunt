"""Combine fingerprint likelihoods with explicit access and event factors."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from molehunt.detect.score import CandidateScore

ACCESS_PRIORS = {"direct": 1.0, "indirect": 0.05, "none": 0.0}
EVENT_FACTORS = {
    "after_hours_download": 3.0,
    "print_job": 2.0,
    "badge_entry": 1.5,
    "unknown_ip": 2.0,
    "unusual_auth": 2.0,
}


@dataclass(frozen=True, slots=True)
class FusedScore:
    """Prior, fingerprint likelihood, and normalized posterior for one candidate."""

    candidate_id: str
    prior: float
    log10_lr: float
    posterior: float | None
    factors: tuple[str, ...]
    rationale: tuple[str, ...]


def fuse_scores(
    scores: Sequence[CandidateScore],
    access: Mapping[str, str],
    events: Mapping[str, Sequence[str]] | None = None,
) -> tuple[FusedScore, ...]:
    """Fuse normalized access weights, named event multipliers, and LR in log space."""
    if not scores:
        raise ValueError("at least one candidate score is required")
    event_map = events or {}
    base_weights: dict[str, float] = {}
    factors_by_candidate: dict[str, tuple[str, ...]] = {}
    rationale_by_candidate: dict[str, tuple[str, ...]] = {}
    log_weights: dict[str, float] = {}
    for score in scores:
        access_level = access.get(score.candidate_id, "none")
        if access_level not in ACCESS_PRIORS:
            raise ValueError(f"unknown access level: {access_level}")
        base = ACCESS_PRIORS[access_level]
        event_ids = tuple(event_map.get(score.candidate_id, ()))
        unknown = [event for event in event_ids if event not in EVENT_FACTORS]
        if unknown:
            raise ValueError(f"unknown event factor: {unknown[0]}")
        multiplier = math.prod(EVENT_FACTORS[event] for event in event_ids)
        weight = base * multiplier
        base_weights[score.candidate_id] = base
        factors_by_candidate[score.candidate_id] = tuple(
            f"{event} ×{EVENT_FACTORS[event]:g}" for event in event_ids
        )
        rationale = [
            "direct access" if access_level == "direct" else
            "indirect access (0.05 base weight)" if access_level == "indirect" else
            "no logged access"
        ]
        rationale.extend(factors_by_candidate[score.candidate_id])
        rationale_by_candidate[score.candidate_id] = tuple(rationale)
        log_weights[score.candidate_id] = (
            math.log(weight) + score.log10_lr * math.log(10)
            if weight > 0
            else -math.inf
        )

    total_base = sum(base_weights.values())
    priors = {
        candidate_id: weight / total_base if total_base else 0.0
        for candidate_id, weight in base_weights.items()
    }
    finite = [value for value in log_weights.values() if math.isfinite(value)]
    if finite:
        maximum = max(finite)
        exponentials = {
            candidate_id: math.exp(value - maximum) if math.isfinite(value) else 0.0
            for candidate_id, value in log_weights.items()
        }
        denominator = sum(exponentials.values())
        posteriors: dict[str, float | None] = {
            candidate_id: value / denominator for candidate_id, value in exponentials.items()
        }
    else:
        posteriors = {candidate_id: None for candidate_id in base_weights}

    results = [
        FusedScore(
            candidate_id=score.candidate_id,
            prior=priors[score.candidate_id],
            log10_lr=score.log10_lr,
            posterior=posteriors[score.candidate_id],
            factors=factors_by_candidate[score.candidate_id],
            rationale=rationale_by_candidate[score.candidate_id],
        )
        for score in scores
    ]
    return tuple(
        sorted(
            results,
            key=lambda item: (
                item.posterior is None,
                -(item.posterior or 0.0),
                item.candidate_id,
            ),
        )
    )
