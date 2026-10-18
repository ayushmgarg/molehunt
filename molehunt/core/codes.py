"""Derive deterministic single-leaker codewords and compare Hamming distance."""

from __future__ import annotations

from collections.abc import Sequence

from molehunt.core.keys import digest, lowest_bit

Codeword = tuple[int, ...]


def generate_codeword(key: bytes, employee_id: str, length: int) -> Codeword:
    """Derive one binary codeword from the keyed HMAC PRF."""
    if not employee_id:
        raise ValueError("employee id must not be empty")
    if length <= 0:
        raise ValueError("codeword length must be positive")
    return tuple(
        lowest_bit(digest(key, "cw", employee_id, index.to_bytes(8, "big")))
        for index in range(length)
    )


def generate_codewords(
    key: bytes,
    employee_ids: Sequence[str],
    length: int,
) -> dict[str, Codeword]:
    """Generate codewords for a roster, rejecting repeated or empty identifiers."""
    if len(set(employee_ids)) != len(employee_ids):
        raise ValueError("employee ids must be unique")
    if any(not employee_id for employee_id in employee_ids):
        raise ValueError("employee ids must not be empty")
    return {
        employee_id: generate_codeword(key, employee_id, length)
        for employee_id in employee_ids
    }


def hamming_distance(first: Sequence[int], second: Sequence[int]) -> int:
    """Count unequal bit positions in two equal-length binary words."""
    if len(first) != len(second):
        raise ValueError("codewords must have equal length")
    if any(bit not in (0, 1) for bit in (*first, *second)):
        raise ValueError("codewords must be binary")
    return sum(left != right for left, right in zip(first, second, strict=True))


def minimum_hamming_distance(codewords: Sequence[Sequence[int]]) -> int:
    """Return the minimum pairwise distance, requiring at least two words."""
    if len(codewords) < 2:
        raise ValueError("at least two codewords are required")
    first_length = len(codewords[0])
    if any(len(word) != first_length for word in codewords):
        raise ValueError("all codewords must have equal length")
    return min(
        hamming_distance(codewords[left], codewords[right])
        for left in range(len(codewords) - 1)
        for right in range(left + 1, len(codewords))
    )
