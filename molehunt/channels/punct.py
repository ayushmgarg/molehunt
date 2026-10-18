"""Encode typography and punctuation choices as explicit text variants."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

_ANCHOR_CHARS = 16


@dataclass(frozen=True, slots=True)
class PunctuationInsertion:
    """A two-variant punctuation slot at an offset in the master text."""

    offset: int
    zero: str
    one: str
    bit: int


@dataclass(frozen=True, slots=True)
class PunctuationLocation:
    """Rendered slot location and following text used to validate empty variants."""

    offset: int
    zero: str
    one: str
    anchor_after: str


@dataclass(frozen=True, slots=True)
class EmbeddedPunctuation:
    """Rendered master and extraction locations in authored slot order."""

    text: str
    locations: tuple[PunctuationLocation, ...]


def embed_punctuation(
    text: str,
    slots: Sequence[PunctuationInsertion],
) -> EmbeddedPunctuation:
    """Replace non-overlapping authored variants while retaining anchor context."""
    edits: list[tuple[int, int, str, str]] = []
    for slot in slots:
        if not 0 <= slot.offset <= len(text):
            raise ValueError("punctuation offset must be within the text")
        if slot.bit not in (0, 1):
            raise ValueError("punctuation bit must be 0 or 1")
        if slot.zero == slot.one:
            raise ValueError("punctuation variants must differ")
        if not text.startswith(slot.zero, slot.offset):
            raise ValueError("zero variant does not match master at offset")
        replacement = slot.zero if slot.bit == 0 else slot.one
        edits.append((slot.offset, slot.offset + len(slot.zero), replacement, ""))

    ordered = sorted(edits, key=lambda edit: edit[0])
    for previous, current in pairwise(ordered):
        if current[0] == previous[0] or current[0] < previous[1]:
            raise ValueError("punctuation slots must not overlap")

    rendered = text
    for start, end, replacement, _ in reversed(ordered):
        rendered = rendered[:start] + replacement + rendered[end:]

    locations = []
    for slot, (start, end, actual_variant, _) in zip(slots, edits, strict=True):
        shift = sum(
            len(other_replacement) - (other_end - other_start)
            for other_start, other_end, other_replacement, _ in edits
            if other_start < start
        )
        output_offset = start + shift
        anchor_start = output_offset + len(actual_variant)
        anchor_after = rendered[anchor_start : anchor_start + _ANCHOR_CHARS]
        locations.append(
            PunctuationLocation(output_offset, slot.zero, slot.one, anchor_after)
        )
    return EmbeddedPunctuation(rendered, tuple(locations))


def extract_punctuation(
    text: str,
    locations: Sequence[PunctuationLocation],
) -> tuple[int | None, ...]:
    """Return a bit only when its variant and following anchor both match."""
    result: list[int | None] = []
    for location in locations:
        matched = None
        for bit, variant in ((0, location.zero), (1, location.one)):
            end = location.offset + len(variant)
            if end <= len(text) and text.startswith(variant, location.offset):
                expected_anchor = location.anchor_after
                if text.startswith(expected_anchor, end):
                    matched = bit
                    break
        result.append(matched)
    return tuple(result)
