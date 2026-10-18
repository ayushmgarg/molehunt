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


def _collusion_setup(seed: int = 0):
    from molehunt.attacks.collusion import collude_bits
    from molehunt.core.tardos import generate_tardos_biases, generate_tardos_codeword

    key = bytes(range(32))
    biases = generate_tardos_biases(key, 300)
    roster = [f"E{index:02}" for index in range(30)]
    codewords = {item: generate_tardos_codeword(key, item, biases) for item in roster}
    leak = collude_bits([codewords["E04"], codewords["E19"]], "majority", seed=seed)
    return biases, codewords, list(leak)


def test_null_simulation_is_seeded_and_near_unit_variance_per_slot() -> None:
    from molehunt.detect.tardos import simulate_null_scores

    biases, _, leak = _collusion_setup()
    first = simulate_null_scores(leak, biases, trials=4000, seed=5)
    assert (first == simulate_null_scores(leak, biases, trials=4000, seed=5)).all()
    assert abs(float(first.mean())) < 1.5
    assert 0.8 < float(first.var()) / len(leak) < 1.2


def test_calibrated_threshold_accuses_colluders_and_no_innocent() -> None:
    from molehunt.detect.tardos import accuse, calibrate_threshold, false_accusation_rate

    biases, codewords, leak = _collusion_setup()
    calibration = calibrate_threshold(leak, biases, candidates=30, target=0.001, seed=1)
    assert calibration.trials >= 10 * 30 / 0.001
    assert calibration.threshold > 0
    assert abs(calibration.threshold - calibration.gaussian_threshold) < 0.25 * calibration.gaussian_threshold
    scores = score_tardos_candidates(leak, biases, codewords)
    assert set(accuse(scores, calibration.threshold)) == {"E04", "E19"}
    estimate = false_accusation_rate(calibration, calibration.threshold)
    assert 0 < estimate <= 0.002
    assert false_accusation_rate(calibration, 0.0) > 0.5


def test_erasures_shrink_the_threshold() -> None:
    from molehunt.detect.tardos import calibrate_threshold

    biases, _, leak = _collusion_setup()
    erased = [None if index % 2 else bit for index, bit in enumerate(leak)]
    full = calibrate_threshold(leak, biases, candidates=30, seed=2).threshold
    half = calibrate_threshold(erased, biases, candidates=30, seed=2).threshold
    assert half < full
