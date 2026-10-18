"""Tests for conservative single-character homoglyph slots."""

import pytest

from molehunt.channels.homoglyph import (
    ConfusableInsertion,
    confusable_skeleton,
    embed_confusables,
    extract_confusables,
)


def test_cyrillic_confusable_round_trip() -> None:
    embedded = embed_confusables(
        "MARK",
        [ConfusableInsertion(1, "A", "А", 1)],
    )
    assert embedded.text == "MАRK"
    assert extract_confusables(embedded.text, embedded.locations) == (1,)


def test_skeleton_maps_common_cyrillic_and_greek_characters() -> None:
    assert confusable_skeleton("pаypаl") == "paypal"
    assert confusable_skeleton("ΑLPHA") == "ALPHA"


def test_skeleton_attack_removes_confusable_signal() -> None:
    embedded = embed_confusables(
        "MARK",
        [ConfusableInsertion(1, "A", "А", 1)],
    )
    assert confusable_skeleton(embedded.text) == "MARK"
    assert extract_confusables(confusable_skeleton(embedded.text), embedded.locations) == (0,)


def test_invalid_pair_and_offset_are_rejected() -> None:
    with pytest.raises(ValueError, match="confusable"):
        embed_confusables("MARK", [ConfusableInsertion(1, "A", "B", 1)])
    with pytest.raises(ValueError, match="offset"):
        embed_confusables("MARK", [ConfusableInsertion(9, "A", "А", 1)])
