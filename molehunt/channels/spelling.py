"""Embed authored regional spelling, date, and number-format variants."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from itertools import pairwise

_ANCHOR_CHARS = 20
_MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
)
_DAY_FIRST = re.compile(rf"(?i)(\d{{1,2}})\s+({_MONTHS})(?:\s+(\d{{4}}))?")
_MONTH_FIRST = re.compile(rf"(?i)({_MONTHS})\s+(\d{{1,2}})(?:,?\s+(\d{{4}}))?")
_NUMBER = re.compile(r"[0-9][0-9 ,.\u00a0]*[0-9]|[0-9]")


class FormatKind(str, Enum):
    """The C5 variant family."""

    SPELLING = "spelling"
    DATE = "date"
    NUMBER = "number"


@dataclass(frozen=True, slots=True)
class SpellingSuggestion:
    """Candidate C5 pair requiring contextual approval."""

    zero: str
    one: str


SPELLING_SUGGESTIONS = (
    SpellingSuggestion("color", "colour"),
    SpellingSuggestion("favorite", "favourite"),
    SpellingSuggestion("center", "centre"),
    SpellingSuggestion("theater", "theatre"),
    SpellingSuggestion("organize", "organise"),
    SpellingSuggestion("analyze", "analyse"),
    SpellingSuggestion("traveling", "travelling"),
    SpellingSuggestion("canceled", "cancelled"),
    SpellingSuggestion("labor", "labour"),
    SpellingSuggestion("defense", "defence"),
    SpellingSuggestion("gray", "grey"),
    SpellingSuggestion("catalog", "catalogue"),
)


@dataclass(frozen=True, slots=True)
class SpellingInsertion:
    """A two-format C5 slot at an offset in the master text."""

    offset: int
    zero: str
    one: str
    bit: int
    kind: FormatKind


@dataclass(frozen=True, slots=True)
class SpellingLocation:
    """Rendered slot variants and following context for extraction."""

    offset: int
    zero: str
    one: str
    kind: FormatKind
    anchor_after: str


@dataclass(frozen=True, slots=True)
class EmbeddedSpelling:
    """Rendered text and extraction locations in authored slot order."""

    text: str
    locations: tuple[SpellingLocation, ...]


def _date_signature(value: str) -> tuple[int, str, int | None] | None:
    match = _DAY_FIRST.fullmatch(value) or _MONTH_FIRST.fullmatch(value)
    if match is None:
        return None
    if match.re is _DAY_FIRST:
        day, month, year = match.groups()
    else:
        month, day, year = match.groups()
    day_number = int(day)
    if not 1 <= day_number <= 31:
        return None
    return day_number, month.casefold(), int(year) if year else None


def _valid_pair(kind: FormatKind, zero: str, one: str) -> bool:
    if not zero or not one or zero == one:
        return False
    if kind is FormatKind.SPELLING:
        return zero.isalpha() and one.isalpha()
    if kind is FormatKind.DATE:
        left, right = _date_signature(zero), _date_signature(one)
        return left is not None and left == right
    if kind is FormatKind.NUMBER:
        if not (_NUMBER.fullmatch(zero) and _NUMBER.fullmatch(one)):
            return False
        digits = lambda value: re.sub(r"[ ,.\u00a0]", "", value)
        return digits(zero) == digits(one)
    return False


def _word_character(character: str) -> bool:
    return character.isalnum() or character == "_"


def _whole_token(text: str, offset: int, variant: str) -> bool:
    end = offset + len(variant)
    left = offset == 0 or not _word_character(text[offset - 1])
    right = end >= len(text) or not _word_character(text[end])
    return text.startswith(variant, offset) and left and right


def embed_spelling(
    text: str,
    slots: Sequence[SpellingInsertion],
) -> EmbeddedSpelling:
    """Render validated C5 variants and retain nearby extraction anchors."""
    edits: list[tuple[int, int, str]] = []
    for slot in slots:
        if not 0 <= slot.offset <= len(text):
            raise ValueError("C5 offset must be within the text")
        if slot.bit not in (0, 1):
            raise ValueError("C5 bit must be 0 or 1")
        if not _valid_pair(slot.kind, slot.zero, slot.one):
            raise ValueError("C5 variants are invalid or not equivalent in format")
        if not _whole_token(text, slot.offset, slot.zero):
            raise ValueError("zero variant must match a whole token at the offset")
        replacement = slot.zero if slot.bit == 0 else slot.one
        edits.append((slot.offset, slot.offset + len(slot.zero), replacement))

    ordered = sorted(edits, key=lambda edit: edit[0])
    for previous, current in pairwise(ordered):
        if current[0] == previous[0] or current[0] < previous[1]:
            raise ValueError("C5 slots must not overlap")
    rendered = text
    for start, end, replacement in reversed(ordered):
        rendered = rendered[:start] + replacement + rendered[end:]

    locations = []
    for slot, (start, end, actual) in zip(slots, edits, strict=True):
        shift = sum(
            len(other_replacement) - (other_end - other_start)
            for other_start, other_end, other_replacement in edits
            if other_start < start
        )
        output_offset = start + shift
        anchor_start = output_offset + len(actual)
        anchor_after = rendered[anchor_start : anchor_start + _ANCHOR_CHARS]
        locations.append(
            SpellingLocation(output_offset, slot.zero, slot.one, slot.kind, anchor_after)
        )
    return EmbeddedSpelling(rendered, tuple(locations))


def extract_spelling(
    text: str,
    locations: Sequence[SpellingLocation],
) -> tuple[int | None, ...]:
    """Read a C5 variant only when its whole token and following context match."""
    result = []
    for location in locations:
        observed = None
        for bit, variant in ((0, location.zero), (1, location.one)):
            end = location.offset + len(variant)
            if (
                end <= len(text)
                and _whole_token(text, location.offset, variant)
                and text.startswith(location.anchor_after, end)
            ):
                observed = bit
                break
        result.append(observed)
    return tuple(result)
