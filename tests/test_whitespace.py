"""Tests for spacing, nonbreaking-space, and trailing-space channel slots."""

import pytest

from molehunt.channels.whitespace import (
    WhitespaceInsertion,
    WhitespaceMode,
    embed_whitespace,
    extract_whitespace,
)


def test_period_spacing_round_trip() -> None:
    source = "See you. tomorrow"
    embedded = embed_whitespace(
        source,
        [WhitespaceInsertion(8, WhitespaceMode.PERIOD_SPACING, 1)],
    )
    assert embedded.text == "See you.  tomorrow"
    assert extract_whitespace(embedded.text, embedded.locations) == (1,)


def test_nbsp_round_trip() -> None:
    embedded = embed_whitespace(
        "A report",
        [WhitespaceInsertion(1, WhitespaceMode.SPACE_KIND, 1)],
    )
    assert embedded.text == "A\u00a0report"
    assert extract_whitespace(embedded.text, embedded.locations) == (1,)


def test_trailing_space_round_trip_and_absent_bit() -> None:
    for bit, suffix in ((0, " "), (1, "  ")):
        embedded = embed_whitespace(
            "End",
            [WhitespaceInsertion(3, WhitespaceMode.TRAILING, bit)],
        )
        assert embedded.text == "End" + suffix
        assert extract_whitespace(embedded.text, embedded.locations) == (bit,)


def test_removed_trailing_marks_are_erasure() -> None:
    embedded = embed_whitespace(
        "End",
        [WhitespaceInsertion(3, WhitespaceMode.TRAILING, 1)],
    )
    assert extract_whitespace(embedded.text.rstrip(), embedded.locations) == (None,)


def test_multiple_slots_map_offsets_after_expansion() -> None:
    source = "A. B C"
    embedded = embed_whitespace(
        source,
        [
            WhitespaceInsertion(2, WhitespaceMode.PERIOD_SPACING, 1),
            WhitespaceInsertion(4, WhitespaceMode.SPACE_KIND, 1),
        ],
    )
    assert embedded.text == "A.  B\u00a0C"
    assert extract_whitespace(embedded.text, embedded.locations) == (1, 1)


def test_missing_or_altered_channel_value_is_erasure() -> None:
    embedded = embed_whitespace(
        "A. B",
        [WhitespaceInsertion(2, WhitespaceMode.PERIOD_SPACING, 1)],
    )
    attacked = embedded.text.replace("  ", "\t", 1)
    assert extract_whitespace(attacked, embedded.locations) == (None,)


@pytest.mark.parametrize(
    "source,slot",
    [
        ("No period", WhitespaceInsertion(2, WhitespaceMode.PERIOD_SPACING, 0)),
        ("A\u00a0B", WhitespaceInsertion(1, WhitespaceMode.SPACE_KIND, 0)),
        ("End", WhitespaceInsertion(2, WhitespaceMode.TRAILING, 1)),
        ("A. B", WhitespaceInsertion(2, WhitespaceMode.PERIOD_SPACING, 2)),
    ],
)
def test_invalid_slots_are_rejected(source: str, slot: WhitespaceInsertion) -> None:
    with pytest.raises(ValueError):
        embed_whitespace(source, [slot])
