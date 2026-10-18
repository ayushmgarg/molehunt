"""Tests for keyed single-leaker codewords and Hamming distance."""

import pytest

from molehunt.core.codes import (
    generate_codeword,
    generate_codewords,
    hamming_distance,
    minimum_hamming_distance,
)


def test_codeword_is_deterministic_and_binary() -> None:
    first = generate_codeword(b"k" * 32, "employee-01", 256)
    assert first == generate_codeword(b"k" * 32, "employee-01", 256)
    assert len(first) == 256
    assert set(first) <= {0, 1}


def test_employee_id_and_key_separate_codewords() -> None:
    assert generate_codeword(b"k" * 32, "employee-01", 256) != generate_codeword(
        b"k" * 32, "employee-02", 256
    )
    assert generate_codeword(b"k" * 32, "employee-01", 256) != generate_codeword(
        b"z" * 32, "employee-01", 256
    )


def test_generate_many_codewords_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="unique"):
        generate_codewords(b"k" * 32, ["e1", "e1"], 8)


def test_generate_many_codewords_are_unique_for_demo_roster() -> None:
    roster = [f"E{i:03}" for i in range(50)]
    codewords = generate_codewords(b"k" * 32, roster, 256)
    assert len(set(codewords.values())) == 50


@pytest.mark.parametrize("length", [0, -1])
def test_generation_rejects_nonpositive_lengths(length: int) -> None:
    with pytest.raises(ValueError, match="positive"):
        generate_codeword(b"k" * 32, "e1", length)


def test_hamming_distance_and_minimum() -> None:
    codewords = [(0, 0, 0), (1, 0, 1), (1, 1, 1)]
    assert hamming_distance(codewords[0], codewords[1]) == 2
    assert minimum_hamming_distance(codewords) == 1


def test_distance_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="equal length"):
        hamming_distance([0, 1], [0])
    with pytest.raises(ValueError, match="binary"):
        hamming_distance([0, 2], [0, 1])
    with pytest.raises(ValueError, match="two"):
        minimum_hamming_distance([(0, 1)])
