"""Tests for byte-level and Unicode visibility helpers in the workbench."""

import pytest

from molehunt.ui.forensics import format_hex_rows, inspect_byte, invisible_characters


def test_hex_rows_keep_offsets_and_ascii_column() -> None:
    rows = format_hex_rows(bytes.fromhex("41 00 7e ff 42"), width=4)

    assert rows == ((0, "41 00 7E FF", "A.~."), (4, "42", "B"))


def test_hex_rows_reject_invalid_width_and_negative_offset() -> None:
    with pytest.raises(ValueError, match="width"):
        format_hex_rows(b"x", width=0)
    with pytest.raises(ValueError, match="offset"):
        format_hex_rows(b"x", start_offset=-1)


def test_byte_inspection_maps_continuation_byte_to_utf8_character() -> None:
    raw = "AéZ".encode()

    detail = inspect_byte(raw, 2)

    assert detail.byte_offset == 2
    assert detail.byte_value == 0xA9
    assert detail.character_offset == 1
    assert detail.codepoint == "U+00E9"
    assert detail.utf8_bytes == (0xC3, 0xA9)
    assert detail.character == "é"


def test_byte_inspection_marks_invalid_utf8_without_guessing() -> None:
    detail = inspect_byte(b"A\xffB", 1)

    assert detail.codepoint is None
    assert detail.character is None
    assert detail.utf8_bytes == (0xFF,)


def test_invisible_character_finds_zero_width_and_nonbreaking_space() -> None:
    found = invisible_characters("A\u200bB\u00a0C")

    assert [(item.character_offset, item.codepoint) for item in found] == [
        (1, "U+200B"),
        (3, "U+00A0"),
    ]
    assert found[0].name == "ZERO WIDTH SPACE"
    assert found[1].utf8_bytes == (0xC2, 0xA0)
