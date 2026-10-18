"""Tests for deterministic symmetric Tardos codes and scoring."""

import math

import pytest

from molehunt.core.tardos import (
    accusation_score,
    generate_tardos_biases,
    generate_tardos_codeword,
    marking_violations,
)


def test_biases_are_deterministic_and_inside_cutoff() -> None:
    first = generate_tardos_biases(b"k" * 32, 512)
    assert first == generate_tardos_biases(b"k" * 32, 512)
    assert len(first) == 512
    assert all(math.sin(0.03) ** 2 <= p <= math.cos(0.03) ** 2 for p in first)
    assert first != generate_tardos_biases(b"z" * 32, 512)


def test_biases_reject_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="positive"):
        generate_tardos_biases(b"k" * 32, 0)
    with pytest.raises(ValueError, match="cutoff"):
        generate_tardos_biases(b"k" * 32, 8, cutoff=0)


def test_codeword_is_deterministic_and_matches_biases_length() -> None:
    biases = generate_tardos_biases(b"k" * 32, 128)
    word = generate_tardos_codeword(b"k" * 32, "employee-7", biases)
    assert word == generate_tardos_codeword(b"k" * 32, "employee-7", biases)
    assert len(word) == len(biases)
    assert set(word) <= {0, 1}


def test_codeword_rejects_empty_employee_and_invalid_bias() -> None:
    with pytest.raises(ValueError, match="employee"):
        generate_tardos_codeword(b"k" * 32, "", [0.5])
    with pytest.raises(ValueError, match="strictly between"):
        generate_tardos_codeword(b"k" * 32, "e1", [1.0])


def test_accusation_score_matches_symmetric_formula_and_skips_erasure() -> None:
    score = accusation_score(
        [1, 0, 1, 1],
        [1, 0, None, 1],
        [0.5, 0.25, 0.5, 0.75],
    )
    assert score == pytest.approx(1 + math.sqrt(1 / 3) + math.sqrt(1 / 3))


def test_mismatch_reduces_score() -> None:
    match = accusation_score([1], [1], [0.2])
    mismatch = accusation_score([0], [1], [0.2])
    assert match > 0
    assert mismatch < 0


def test_score_rejects_invalid_values_and_lengths() -> None:
    with pytest.raises(ValueError, match="equal length"):
        accusation_score([1], [1, 0], [0.5])
    with pytest.raises(ValueError, match="binary"):
        accusation_score([2], [1], [0.5])
    with pytest.raises(ValueError, match="strictly between"):
        accusation_score([1], [1], [0])


def test_marking_assumption_violations_ignore_erased_slots() -> None:
    colluders = [(0, 1, 0, 1), (0, 0, 0, 1)]
    assert marking_violations(colluders, [1, 1, 0, None]) == [0]


def test_marking_assumption_rejects_bad_codewords() -> None:
    with pytest.raises(ValueError, match="at least one"):
        marking_violations([], [0])
    with pytest.raises(ValueError, match="equal length"):
        marking_violations([(0, 1)], [0])
