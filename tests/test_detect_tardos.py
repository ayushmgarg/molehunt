"""Tests for candidate ranking with Tardos accusation scores."""

import pytest

from molehunt.detect.tardos import score_tardos_candidates


def test_tardos_candidates_rank_by_symmetric_score() -> None:
    scores = score_tardos_candidates(
        [1, None],
        [0.25, 0.5],
        {"E2": [0, 0], "E1": [1, 1]},
    )
    assert [item.candidate_id for item in scores] == ["E1", "E2"]
    assert scores[0].score > 0
    assert scores[1].score < 0


def test_tardos_candidate_lengths_must_match() -> None:
    with pytest.raises(ValueError, match="equal length"):
        score_tardos_candidates([1], [0.5], {"E1": [1, 0]})


def test_all_erasure_scores_are_zero_and_tie_breaks_by_id() -> None:
    result = score_tardos_candidates([None], [0.5], {"E2": [0], "E1": [1]})
    assert [item.candidate_id for item in result] == ["E1", "E2"]
    assert all(item.score == 0 for item in result)
