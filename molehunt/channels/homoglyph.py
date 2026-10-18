"""Embed and extract C3b single-code-point confusables using a curated map."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

# This deliberately small table covers frequent Greek/Cyrillic look-alikes.
CONFUSABLE_TO_LATIN = {
    "А": "A", "В": "B", "С": "C", "Е": "E", "Н": "H", "І": "I",
    "Ј": "J", "К": "K", "М": "M", "О": "O", "Р": "P", "Ѕ": "S",
    "Т": "T", "У": "Y", "Х": "X", "а": "a", "в": "b", "с": "c",
    "е": "e", "н": "h", "і": "i", "ј": "j", "к": "k", "м": "m",
    "о": "o", "р": "p", "ѕ": "s", "т": "t", "у": "y", "х": "x",
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I",
    "Κ": "K", "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T",
    "Υ": "Y", "Χ": "X", "α": "a", "ι": "i", "κ": "k", "ο": "o",
    "ρ": "p", "υ": "u", "χ": "x",
}


@dataclass(frozen=True, slots=True)
class ConfusableInsertion:
    """A Latin/confusable pair at one code-point offset."""

    offset: int
    latin: str
    confusable: str
    bit: int


@dataclass(frozen=True, slots=True)
class ConfusableLocation:
    """Expected Latin and confusable code points for extraction."""

    offset: int
    latin: str
    confusable: str


@dataclass(frozen=True, slots=True)
class EmbeddedConfusables:
    """Rendered text and slot locations in source order."""

    text: str
    locations: tuple[ConfusableLocation, ...]


def confusable_skeleton(text: str) -> str:
    """Map the curated confusable subset to its Latin ASCII skeleton."""
    return "".join(CONFUSABLE_TO_LATIN.get(character, character) for character in text)


def embed_confusables(
    text: str,
    slots: Sequence[ConfusableInsertion],
) -> EmbeddedConfusables:
    """Replace selected Latin letters with their one-code-point look-alikes."""
    output = list(text)
    locations = []
    used_offsets: set[int] = set()
    for slot in slots:
        if not 0 <= slot.offset < len(text):
            raise ValueError("confusable offset must point inside the text")
        if slot.offset in used_offsets:
            raise ValueError("confusable slots must use distinct offsets")
        used_offsets.add(slot.offset)
        if slot.bit not in (0, 1):
            raise ValueError("confusable bit must be 0 or 1")
        if len(slot.latin) != 1 or not slot.latin.isascii() or not slot.latin.isalpha():
            raise ValueError("Latin variant must be one ASCII letter")
        if CONFUSABLE_TO_LATIN.get(slot.confusable) != slot.latin:
            raise ValueError("confusable character must map to the Latin variant")
        if text[slot.offset] != slot.latin:
            raise ValueError("Latin variant does not match master at offset")
        output[slot.offset] = slot.latin if slot.bit == 0 else slot.confusable
        locations.append(ConfusableLocation(slot.offset, slot.latin, slot.confusable))
    return EmbeddedConfusables("".join(output), tuple(locations))


def extract_confusables(
    text: str,
    locations: Sequence[ConfusableLocation],
) -> tuple[int | None, ...]:
    """Read one mapped code point at each aligned offset; unrecognized is erased."""
    result = []
    for location in locations:
        if not 0 <= location.offset < len(text):
            result.append(None)
        elif text[location.offset] == location.latin:
            result.append(0)
        elif text[location.offset] == location.confusable:
            result.append(1)
        else:
            result.append(None)
    return tuple(result)
