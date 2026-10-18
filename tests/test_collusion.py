"""Tests for slot-wise collusion strategies."""

import pytest

from molehunt.attacks.collusion import collude_bits


def test_majority_and_minority_strategies() -> None:
    copies = [(0, 1, 1, 0), (1, 0, 1, 0), (1, 0, 0, 0)]
    assert collude_bits(copies, "majority", seed=4) == (1, 0, 1, 0)
    assert collude_bits(copies, "minority", seed=4) == (0, 1, 0, 0)


def test_random_strategy_is_deterministic() -> None:
    copies = [(0, 0, 1, 1), (1, 1, 0, 0)]
    assert collude_bits(copies, "random", seed=5) == collude_bits(copies, "random", seed=5)


def test_min_max_strategies_and_validation() -> None:
    copies = [(0, 1), (1, 0)]
    assert collude_bits(copies, "min") == (0, 0)
    assert collude_bits(copies, "max") == (1, 1)
    with pytest.raises(ValueError, match="strategy"):
        collude_bits(copies, "unknown")
    with pytest.raises(ValueError, match="equal length"):
        collude_bits([(0,), (0, 1)], "majority")
