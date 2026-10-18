"""Tests for binomial and likelihood-ratio candidate scoring."""

import math

import pytest

from molehunt.detect.score import score_candidates


def test_scores_rank_matches_and_report_statistics() -> None:
    candidates = {"E1": [1, 1, 1, 1], "E2": [0, 0, 0, 0]}
    scores = score_candidates([1, 1, 1, 1], candidates, flip_rate=0.1)
    assert [score.candidate_id for score in scores] == ["E1", "E2"]
    assert scores[0].observed_slots == 4
    assert scores[0].matches == 4
    assert scores[0].match_fraction == 1
    assert scores[0].z_score == pytest.approx(2)
    assert scores[0].binomial_p == pytest.approx(1 / 16)
    assert scores[0].log10_lr == pytest.approx(math.log10((0.9**4) / (0.5**4)))


def test_erasures_are_excluded_from_matches_and_denominator() -> None:
    score = score_candidates([1, None, 1, None], {"E1": [1, 0, 1, 0]}, flip_rate=0.1)[0]
    assert score.observed_slots == 2
    assert score.matches == 2
    assert score.match_fraction == 1
    assert score.binomial_p == pytest.approx(0.25)


def test_no_observed_slots_are_not_evidence() -> None:
    scores = score_candidates([None, None], {"E2": [0, 0], "E1": [1, 1]})
    assert [score.candidate_id for score in scores] == ["E1", "E2"]
    assert all(score.observed_slots == 0 for score in scores)
    assert all(score.binomial_p == 1 for score in scores)
    assert all(score.log10_lr == 0 for score in scores)


def test_score_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="flip rate"):
        score_candidates([1], {"E1": [1]}, flip_rate=0.5)
    with pytest.raises(ValueError, match="equal length"):
        score_candidates([1], {"E1": [1, 0]})
    with pytest.raises(ValueError, match="binary"):
        score_candidates([2], {"E1": [1]})
    with pytest.raises(ValueError, match="at least one"):
        score_candidates([1], {})
