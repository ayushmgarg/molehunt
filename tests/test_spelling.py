"""Tests for spelling, date, and number-format slots."""

import pytest

from molehunt.channels.spelling import (
    FormatKind,
    SpellingInsertion,
    embed_spelling,
    extract_spelling,
)


def test_regional_spelling_round_trip() -> None:
    embedded = embed_spelling(
        "The color is noted.",
        [SpellingInsertion(4, "color", "colour", 1, FormatKind.SPELLING)],
    )
    assert embedded.text == "The colour is noted."
    assert extract_spelling(embedded.text, embedded.locations) == (1,)


def test_date_order_round_trip() -> None:
    embedded = embed_spelling(
        "The date is 18 March 2025.",
        [SpellingInsertion(12, "18 March", "March 18", 1, FormatKind.DATE)],
    )
    assert embedded.text == "The date is March 18 2025."
    assert extract_spelling(embedded.text, embedded.locations) == (1,)


def test_number_separator_round_trip() -> None:
    embedded = embed_spelling(
        "Total: 1,500 units.",
        [SpellingInsertion(7, "1,500", "1 500", 1, FormatKind.NUMBER)],
    )
    assert embedded.text == "Total: 1 500 units."
    assert extract_spelling(embedded.text, embedded.locations) == (1,)


def test_rewritten_anchor_is_erasure() -> None:
    embedded = embed_spelling(
        "The color is noted.",
        [SpellingInsertion(4, "color", "colour", 0, FormatKind.SPELLING)],
    )
    assert extract_spelling("The color was changed.", embedded.locations) == (None,)


@pytest.mark.parametrize(
    "source,slot",
    [
        ("color", SpellingInsertion(0, "color", "colour", 2, FormatKind.SPELLING)),
        ("color", SpellingInsertion(0, "color", "colour", 0, FormatKind.DATE)),
        ("18 March", SpellingInsertion(0, "18 March", "March", 0, FormatKind.DATE)),
        ("1,500", SpellingInsertion(0, "1,500", "one thousand", 0, FormatKind.NUMBER)),
    ],
)
def test_invalid_format_variants_are_rejected(source: str, slot: SpellingInsertion) -> None:
    with pytest.raises(ValueError):
        embed_spelling(source, [slot])
