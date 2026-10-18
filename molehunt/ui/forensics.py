"""Format hexadecimal rows and map UTF-8 bytes to visible Unicode facts."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ByteInspection:
    """Byte selection and its decoded character, when its UTF-8 is valid."""

    byte_offset: int
    byte_value: int
    character_offset: int | None
    codepoint: str | None
    utf8_bytes: tuple[int, ...]
    character: str | None


@dataclass(frozen=True, slots=True)
class InvisibleCharacter:
    """A non-printing code point and its location in the decoded text."""

    character_offset: int
    character: str
    codepoint: str
    name: str
    category: str
    utf8_bytes: tuple[int, ...]


def format_hex_rows(
    data: bytes, *, width: int = 16, start_offset: int = 0
) -> tuple[tuple[int, str, str], ...]:
    """Split bytes into fixed-width rows with hex and printable ASCII columns."""
    if width < 1:
        raise ValueError("width must be positive")
    if start_offset < 0:
        raise ValueError("offset must not be negative")
    rows = []
    for index in range(0, len(data), width):
        chunk = data[index : index + width]
        hexadecimal = " ".join(f"{byte:02X}" for byte in chunk)
        ascii_text = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in chunk)
        rows.append((start_offset + index, hexadecimal, ascii_text))
    return tuple(rows)


def _utf8_sequence(data: bytes, offset: int) -> tuple[str, int] | None:
    """Return the valid UTF-8 scalar and its length starting at one byte offset."""
    lead = data[offset]
    if lead < 0x80:
        length = 1
    elif 0xC2 <= lead <= 0xDF:
        length = 2
    elif 0xE0 <= lead <= 0xEF:
        length = 3
    elif 0xF0 <= lead <= 0xF4:
        length = 4
    else:
        return None
    sequence = data[offset : offset + length]
    if len(sequence) != length:
        return None
    try:
        character = sequence.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None
    return character, length


def inspect_byte(data: bytes, offset: int) -> ByteInspection:
    """Map a selected byte, including a continuation byte, to its Unicode scalar."""
    if not 0 <= offset < len(data):
        raise ValueError("byte offset is outside the evidence")
    cursor = 0
    while cursor < len(data):
        decoded = _utf8_sequence(data, cursor)
        if decoded is None:
            if cursor == offset:
                return ByteInspection(offset, data[offset], None, None, (data[offset],), None)
            cursor += 1
            continue
        character, length = decoded
        if cursor <= offset < cursor + length:
            return ByteInspection(
                byte_offset=offset,
                byte_value=data[offset],
                character_offset=len(data[:cursor].decode("utf-8", errors="replace")),
                codepoint=f"U+{ord(character):04X}",
                utf8_bytes=tuple(data[cursor : cursor + length]),
                character=character,
            )
        cursor += length
    return ByteInspection(offset, data[offset], None, None, (data[offset],), None)


def invisible_characters(text: str) -> tuple[InvisibleCharacter, ...]:
    """Return non-printing Unicode scalars with code point and UTF-8 details."""
    results = []
    for index, character in enumerate(text):
        if character.isprintable():
            continue
        encoded = character.encode("utf-8")
        results.append(
            InvisibleCharacter(
                character_offset=index,
                character=character,
                codepoint=f"U+{ord(character):04X}",
                name=unicodedata.name(character, "UNNAMED"),
                category=unicodedata.category(character),
                utf8_bytes=tuple(encoded),
            )
        )
    return tuple(results)
