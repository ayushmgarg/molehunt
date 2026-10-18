"""Tests for zero-width channel insertion, extraction, and decoys."""

import pytest

from molehunt.channels.zerowidth import embed_zero_width, extract_zero_width


def test_round_trip_preserves_text_and_slot_bits() -> None:
    text = "Meet at north gate."
    result = embed_zero_width(text, [(8, 0), (13, 1)])
    assert result.text.replace("\u200b", "").replace("\u200c", "") == text
    assert extract_zero_width(result.text, result.slot_offsets) == (0, 1)


def test_decoys_are_skipped_before_a_slot_mark() -> None:
    result = embed_zero_width(
        "ABC",
        [(1, 1)],
        decoys=[(1, "\u200d"), (1, "\u2060")],
    )
    assert extract_zero_width(result.text, result.slot_offsets) == (1,)


def test_stripped_marks_are_erasures() -> None:
    result = embed_zero_width("A short master.", [(1, 0), (7, 1), (14, 0)])
    stripped = "".join(
        character
        for character in result.text
        if character not in {"\u200b", "\u200c", "\u200d", "\u2060"}
    )
    assert extract_zero_width(stripped, result.slot_offsets) == (None, None, None)


def test_multiple_slots_at_same_offset_keep_input_order() -> None:
    result = embed_zero_width("xy", [(1, 0), (1, 1)])
    assert extract_zero_width(result.text, result.slot_offsets) == (0, 1)


@pytest.mark.parametrize(
    "slots,decoys",
    [
        ([(4, 0)], []),
        ([(-1, 0)], []),
        ([(0, 2)], []),
        ([], [(0, "x")]),
    ],
)
def test_embed_rejects_invalid_offsets_bits_and_decoys(slots, decoys) -> None:
    with pytest.raises(ValueError):
        embed_zero_width("abc", slots, decoys=decoys)


def test_extract_rejects_negative_offsets() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        extract_zero_width("abc", [-1])
