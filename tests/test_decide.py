"""Tests for the verbal LR scale and the attribution decision rule."""

import pytest

from molehunt.detect.decide import decide, verbal_scale
from molehunt.detect.score import CandidateScore, score_candidates


@pytest.mark.parametrize(
    ("log10_lr", "phrase"),
    [
        (-0.5, "no support"),
        (0.0, "no support"),
        (0.5, "weak support"),
        (1.5, "moderate support"),
        (2.5, "moderately strong support"),
        (3.5, "strong support"),
        (5.5, "very strong support"),
        (6.5, "extremely strong support"),
    ],
)
def test_verbal_scale_bins(log10_lr: float, phrase: str) -> None:
    assert verbal_scale(log10_lr) == phrase


def test_clear_leader_is_attributed_with_copy_level_wording() -> None:
    codewords = {"A": (0, 1) * 40, "B": (1, 0) * 40, "C": (0, 0, 1, 1) * 20}
    scores = score_candidates(list(codewords["A"]), codewords)
    decision = decide(scores, candidates=3)
    assert decision.outcome == "attribute"
    assert decision.candidate_id == "A"
    assert "copy issued to A" in decision.statement
    assert "not by itself" in decision.statement
    assert decision.familywise_bound == pytest.approx(0.001)


def test_two_identical_candidates_cannot_be_distinguished() -> None:
    shared = (0, 1, 1, 0) * 15
    codewords = {"A": shared, "B": shared, "C": tuple(1 - bit for bit in shared)}
    decision = decide(score_candidates(list(shared), codewords), candidates=3)
    assert decision.outcome == "cannot distinguish"
    assert set(decision.tied) == {"A", "B"}
    assert decision.candidate_id is None


def test_too_few_observed_slots_give_no_attribution() -> None:
    codewords = {"A": (0, 1, 1, 0, 1), "B": (1, 0, 0, 1, 0)}
    observed = [0, None, None, None, None]
    decision = decide(score_candidates(observed, codewords), candidates=2)
    assert decision.outcome == "no attribution"
    assert "insufficient" in decision.statement


def test_decision_requires_scores_and_valid_parameters() -> None:
    with pytest.raises(ValueError):
        decide((), candidates=1)
    score = CandidateScore("A", 10, 10, 1.0, 3.2, 0.001, 3.0)
    with pytest.raises(ValueError):
        decide((score,), candidates=1, alpha=0)
