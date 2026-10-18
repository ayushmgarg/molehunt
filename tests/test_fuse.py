"""Tests for explicit access priors and log-evidence fusion."""

import pytest

from molehunt.detect.fuse import EVENT_FACTORS, fuse_scores
from molehunt.detect.score import CandidateScore, score_candidates


def scores():
    return (
        CandidateScore("E1", 10, 8, 0.8, 1.9, 0.05, 1.0),
        CandidateScore("E2", 10, 7, 0.7, 1.2, 0.2, 0.5),
        CandidateScore("E3", 10, 4, 0.4, -0.6, 0.8, -0.5),
    )


def test_access_prior_and_likelihood_produce_normalized_posteriors() -> None:
    result = fuse_scores(scores(), {"E1": "direct", "E2": "indirect", "E3": "direct"})
    assert result[0].candidate_id == "E1"
    assert sum(item.posterior or 0 for item in result) == pytest.approx(1)
    assert next(item for item in result if item.candidate_id == "E2").prior < 0.05


def test_documented_log_factors_change_candidate_weight() -> None:
    result = fuse_scores(
        scores(),
        {"E1": "direct", "E2": "direct", "E3": "direct"},
        {"E2": ["after_hours_download", "print_job"]},
    )
    e2 = next(item for item in result if item.candidate_id == "E2")
    assert e2.factors == ("after_hours_download ×3", "print_job ×2")
    assert e2.posterior > next(item.posterior for item in result if item.candidate_id == "E1")
    assert EVENT_FACTORS["print_job"] == 2


def test_no_access_yields_no_posterior_instead_of_a_guess() -> None:
    result = fuse_scores(scores(), {"E1": "none", "E2": "none", "E3": "none"})
    assert all(item.posterior is None for item in result)


def test_unknown_access_and_event_are_rejected() -> None:
    with pytest.raises(ValueError, match="access level"):
        fuse_scores(scores(), {"E1": "unknown"})
    with pytest.raises(ValueError, match="event factor"):
        fuse_scores(scores(), {"E1": "direct"}, {"E1": ["unlisted_event"]})


def test_sensitivity_reports_top_under_weaker_and_stronger_factors() -> None:
    from molehunt.detect.fuse import fusion_sensitivity

    scores = score_candidates([1, 0, 1, 0], {"E1": [1, 0, 1, 0], "E2": [1, 0, 1, 0]})
    access = {"E1": "direct", "E2": "direct"}
    tops = fusion_sensitivity(scores, access, {"E1": ["print_job"]})
    assert tops == {0.5: "E1", 2.0: "E1"}
