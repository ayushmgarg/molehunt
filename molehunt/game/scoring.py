"""Grade a case response with binary Brier scoring for stated confidence."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SubmissionGrade:
    """Correctness, Brier loss, and a 0–100 confidence-aware score."""

    correct: bool
    confidence: float
    brier_score: float
    points: int


def grade_response(correct: bool, confidence: float) -> SubmissionGrade:
    """Use `(confidence - outcome)^2`; overconfident errors lose more points."""
    if not isinstance(correct, bool):
        raise TypeError("correct must be a boolean derived from generated ground truth")
    if not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise ValueError("confidence must be finite and between zero and one")
    outcome = float(correct)
    brier = (confidence - outcome) ** 2
    points = math.floor(100 * (1 - brier) + 0.5)
    return SubmissionGrade(correct, confidence, brier, points)
