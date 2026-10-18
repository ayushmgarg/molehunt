"""Encode spacing, NBSP, and trailing-space variants as C2 slots."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum


class WhitespaceMode(str, Enum):
    """Supported whitespace carriers."""

    PERIOD_SPACING = "period_spacing"
    SPACE_KIND = "space_kind"
    TRAILING = "trailing"


@dataclass(frozen=True, slots=True)
class WhitespaceInsertion:
    """A whitespace slot offset in the unmodified master and selected bit."""

    offset: int
    mode: WhitespaceMode
    bit: int


@dataclass(frozen=True, slots=True)
class WhitespaceLocation:
    """Mode and adjusted offset used to extract a slot from rendered text."""

    offset: int
    mode: WhitespaceMode


@dataclass(frozen=True, slots=True)
class EmbeddedWhitespace:
    """Rendered text and extraction locations in input slot order."""

    text: str
    locations: tuple[WhitespaceLocation, ...]


def _replacement(text: str, slot: WhitespaceInsertion) -> tuple[int, int, str]:
    offset = slot.offset
    if not 0 <= offset <= len(text):
        raise ValueError("whitespace offset must be within the text")
    if slot.bit not in (0, 1):
        raise ValueError("whitespace bit must be 0 or 1")
    if slot.mode is WhitespaceMode.PERIOD_SPACING:
        if offset == 0 or offset >= len(text) or text[offset - 1] != "." or text[offset] != " ":
            raise ValueError("period-spacing slot must point to a space after a period")
        return offset, offset + 1, " " * (1 + slot.bit)
    if slot.mode is WhitespaceMode.SPACE_KIND:
        if offset >= len(text) or text[offset] != " ":
            raise ValueError("space-kind slot must point to an ASCII space")
        return offset, offset + 1, " " if slot.bit == 0 else "\u00a0"
    if slot.mode is WhitespaceMode.TRAILING:
        if offset != len(text):
            raise ValueError("trailing-space slot must point to end of text")
        return offset, offset, " " * (1 + slot.bit)
    raise ValueError(f"unsupported whitespace mode: {slot.mode}")


def embed_whitespace(
    text: str,
    slots: Sequence[WhitespaceInsertion],
) -> EmbeddedWhitespace:
    """Apply non-overlapping whitespace replacements and preserve slot order."""
    offsets = [slot.offset for slot in slots]
    if len(set(offsets)) != len(offsets):
        raise ValueError("whitespace slots must use distinct offsets")
    edits = [_replacement(text, slot) for slot in slots]
    rendered = text
    for start, end, replacement in sorted(edits, key=lambda edit: edit[0], reverse=True):
        rendered = rendered[:start] + replacement + rendered[end:]

    locations = []
    for slot, (start, end, replacement) in zip(slots, edits, strict=True):
        shift = sum(
            len(other_replacement) - (other_end - other_start)
            for other_start, other_end, other_replacement in edits
            if other_start < start
        )
        locations.append(WhitespaceLocation(start + shift, slot.mode))
    return EmbeddedWhitespace(rendered, tuple(locations))


def extract_whitespace(
    text: str,
    locations: Sequence[WhitespaceLocation],
) -> tuple[int | None, ...]:
    """Read C2 variants; any unsupported spelling of a carrier is an erasure."""
    result: list[int | None] = []
    for location in locations:
        offset = location.offset
        if offset < 0:
            raise ValueError("whitespace offsets must be non-negative")
        if location.mode is WhitespaceMode.PERIOD_SPACING:
            if offset == 0 or offset > len(text) or text[offset - 1] != ".":
                result.append(None)
                continue
            run = 0
            while offset + run < len(text) and text[offset + run] == " ":
                run += 1
            result.append(0 if run == 1 else 1 if run == 2 else None)
        elif location.mode is WhitespaceMode.SPACE_KIND:
            if offset >= len(text):
                result.append(None)
            elif text[offset] == " ":
                result.append(0)
            elif text[offset] == "\u00a0":
                result.append(1)
            else:
                result.append(None)
        elif location.mode is WhitespaceMode.TRAILING:
            if offset > len(text):
                result.append(None)
                continue
            tail = text[offset:]
            result.append(0 if tail == " " else 1 if tail == "  " else None)
        else:
            raise ValueError(f"unsupported whitespace mode: {location.mode}")
    return tuple(result)
