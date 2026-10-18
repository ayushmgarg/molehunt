"""Tests for confidence-sensitive case response grades."""

import pytest

from molehunt.game.scoring import grade_response


def test_confident_correct_answers_earn_more_points() -> None:
    confident = grade_response(True, 0.9)
    unsure = grade_response(True, 0.6)
    assert confident.brier_score == pytest.approx(0.01)
    assert confident.points == 99
    assert unsure.points == 84


def test_overconfident_wrong_answer_is_penalized() -> None:
    assert grade_response(False, 0.9).points == 19
    assert grade_response(False, 0.5).points == 75
    assert grade_response(True, 1.0).points == 100


@pytest.mark.parametrize("confidence", [-0.1, 1.1, float("nan"), float("inf")])
def test_grade_rejects_invalid_confidence(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence"):
        grade_response(True, confidence)
