"""Tests for punctuation and typography variation slots."""

import pytest

from molehunt.channels.punct import (
    PunctuationInsertion,
    embed_punctuation,
    extract_punctuation,
)


def test_curly_quote_variant_round_trip() -> None:
    embedded = embed_punctuation(
        'She said "go".',
        [PunctuationInsertion(9, '"', "“", 1)],
    )
    assert embedded.text[9] == "“"
    assert extract_punctuation(embedded.text, embedded.locations) == (1,)


def test_dash_variant_round_trip() -> None:
    embedded = embed_punctuation(
        "north-south route",
        [PunctuationInsertion(5, "-", "–", 1)],
    )
    assert embedded.text == "north–south route"
    assert extract_punctuation(embedded.text, embedded.locations) == (1,)


def test_optional_oxford_comma_round_trip() -> None:
    with_comma = embed_punctuation(
        "red, blue, and gold",
        [PunctuationInsertion(9, ",", "", 0)],
    )
    without_comma = embed_punctuation(
        "red, blue, and gold",
        [PunctuationInsertion(9, ",", "", 1)],
    )
    assert with_comma.text == "red, blue, and gold"
    assert without_comma.text == "red, blue and gold"
    assert extract_punctuation(with_comma.text, with_comma.locations) == (0,)
    assert extract_punctuation(without_comma.text, without_comma.locations) == (1,)


def test_unknown_punctuation_is_erasure() -> None:
    embedded = embed_punctuation(
        "north-south",
        [PunctuationInsertion(5, "-", "–", 0)],
    )
    normalized = embedded.text.replace("-", "/", 1)
    assert extract_punctuation(normalized, embedded.locations) == (None,)


def test_changed_optional_comma_is_erasure_when_anchor_breaks() -> None:
    embedded = embed_punctuation(
        "red, blue, and gold",
        [PunctuationInsertion(9, ",", "", 0)],
    )
    attacked = embedded.text.replace(", and", "; and")
    assert extract_punctuation(attacked, embedded.locations) == (None,)


def test_multiple_slots_adjust_offsets_and_keep_order() -> None:
    embedded = embed_punctuation(
        "A-B, C",
        [
            PunctuationInsertion(1, "-", "–", 1),
            PunctuationInsertion(3, ",", "", 1),
        ],
    )
    assert embedded.text == "A–B C"
    assert extract_punctuation(embedded.text, embedded.locations) == (1, 1)


@pytest.mark.parametrize(
    "source,slot",
    [
        ("abc", PunctuationInsertion(4, "a", "b", 0)),
        ("abc", PunctuationInsertion(0, "a", "a", 1)),
        ("abc", PunctuationInsertion(1, "z", "q", 0)),
        ("abc", PunctuationInsertion(1, "b", "c", 2)),
    ],
)
def test_invalid_slots_are_rejected(source: str, slot: PunctuationInsertion) -> None:
    with pytest.raises(ValueError):
        embed_punctuation(source, [slot])


def test_overlapping_slots_are_rejected() -> None:
    with pytest.raises(ValueError, match="overlap"):
        embed_punctuation(
            "abc",
            [PunctuationInsertion(0, "ab", "AB", 0), PunctuationInsertion(1, "bc", "BC", 1)],
        )
