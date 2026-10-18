"""Generate symmetric Tardos codes and score candidates with erasure handling."""

from __future__ import annotations

import math
from collections.abc import Sequence

from molehunt.core.keys import digest

_DEFAULT_CUTOFF = 0.03
_UINT64_RANGE = 1 << 64


def _unit_interval(key: bytes, domain: str, employee_id: str, index: int) -> float:
    """Map 64 keyed bits to a deterministic value in [0, 1)."""
    raw = digest(key, domain, employee_id, index.to_bytes(8, "big"))
    return int.from_bytes(raw[:8], "big") / _UINT64_RANGE


def _validate_bias(probability: float) -> None:
    if not 0 < probability < 1:
        raise ValueError("bias probability must be strictly between zero and one")


def generate_tardos_biases(
    key: bytes,
    length: int,
    cutoff: float = _DEFAULT_CUTOFF,
) -> tuple[float, ...]:
    """Draw keyed Tardos probabilities with a symmetric sine-squared bias."""
    if length <= 0:
        raise ValueError("code length must be positive")
    if not 0 < cutoff < math.pi / 4:
        raise ValueError("cutoff must be between zero and pi/4")
    span = math.pi / 2 - 2 * cutoff
    return tuple(
        math.sin(cutoff + span * _unit_interval(key, "tardos-bias", "", index)) ** 2
        for index in range(length)
    )


def generate_tardos_codeword(
    key: bytes,
    employee_id: str,
    biases: Sequence[float],
) -> tuple[int, ...]:
    """Set each keyed symbol to one when its uniform draw is below its bias."""
    if not employee_id:
        raise ValueError("employee id must not be empty")
    if not biases:
        raise ValueError("bias sequence must not be empty")
    for probability in biases:
        _validate_bias(probability)
    return tuple(
        int(_unit_interval(key, "tardos-symbol", employee_id, index) < probability)
        for index, probability in enumerate(biases)
    )


def accusation_score(
    codeword: Sequence[int],
    observed: Sequence[int | None],
    biases: Sequence[float],
) -> float:
    """Compute the symmetric accusation score; erased slots contribute zero."""
    if not (len(codeword) == len(observed) == len(biases)):
        raise ValueError("codeword, observation, and biases must have equal length")
    if any(bit not in (0, 1) for bit in codeword):
        raise ValueError("codeword must be binary")
    if any(bit not in (0, 1, None) for bit in observed):
        raise ValueError("observations must be binary or None")
    score = 0.0
    for candidate_bit, leak_bit, probability in zip(
        codeword, observed, biases, strict=True
    ):
        _validate_bias(probability)
        if leak_bit is None:
            continue
        if leak_bit == 1:
            score += (
                math.sqrt((1 - probability) / probability)
                if candidate_bit == 1
                else -math.sqrt(probability / (1 - probability))
            )
        else:
            score += (
                math.sqrt(probability / (1 - probability))
                if candidate_bit == 0
                else -math.sqrt((1 - probability) / probability)
            )
    return score


def marking_violations(
    colluder_codewords: Sequence[Sequence[int]],
    observed: Sequence[int | None],
) -> list[int]:
    """Return slots that violate the marking assumption among known leak bits."""
    if not colluder_codewords:
        raise ValueError("at least one colluder codeword is required")
    if any(len(word) != len(observed) for word in colluder_codewords):
        raise ValueError("all codewords and observations must have equal length")
    if any(bit not in (0, 1) for word in colluder_codewords for bit in word):
        raise ValueError("colluder codewords must be binary")
    if any(bit not in (0, 1, None) for bit in observed):
        raise ValueError("observations must be binary or None")
    return [
        index
        for index, leak_bit in enumerate(observed)
        if leak_bit is not None
        and all(word[index] == colluder_codewords[0][index] for word in colluder_codewords)
        and leak_bit != colluder_codewords[0][index]
    ]
