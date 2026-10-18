"""Merge multiple employee codewords with seeded collusion strategies."""

from __future__ import annotations

import random
from collections.abc import Sequence

STRATEGIES = frozenset({"majority", "minority", "random", "min", "max"})


def collude_bits(
    copies: Sequence[Sequence[int]],
    strategy: str = "majority",
    *,
    seed: int = 0,
) -> tuple[int, ...]:
    """Select one observed bit per slot using a reproducible collusion strategy."""
    if len(copies) < 2:
        raise ValueError("collusion needs at least two copies")
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown collusion strategy: {strategy}")
    length = len(copies[0])
    if any(len(copy) != length for copy in copies):
        raise ValueError("colluder codewords must have equal length")
    if any(bit not in (0, 1) for copy in copies for bit in copy):
        raise ValueError("colluder codewords must be binary")
    rng = random.Random(seed)
    result = []
    for position in range(length):
        values = [copy[position] for copy in copies]
        zeros = values.count(0)
        ones = len(values) - zeros
        if strategy == "min":
            result.append(min(values))
        elif strategy == "max":
            result.append(max(values))
        elif strategy == "random" or zeros == ones:
            result.append(rng.choice(values))
        elif strategy == "majority":
            result.append(int(ones > zeros))
        elif zeros == 0:
            result.append(1)
        elif ones == 0:
            result.append(0)
        else:
            result.append(int(ones < zeros))
    return tuple(result)
