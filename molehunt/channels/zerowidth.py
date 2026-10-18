"""Embed C1 bits as invisible Unicode marks and ignore known decoy marks."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

ZERO = "\u200b"
ONE = "\u200c"
DECOYS = frozenset({"\u200d", "\u2060"})


@dataclass(frozen=True, slots=True)
class EmbeddedText:
    """Text after embedding and the resulting marker offsets per input slot."""

    text: str
    slot_offsets: tuple[int, ...]


def embed_zero_width(
    text: str,
    slots: Sequence[tuple[int, int]],
    *,
    decoys: Sequence[tuple[int, str]] = (),
) -> EmbeddedText:
    """Insert bit markers and decoys at code-point offsets without changing text."""
    slot_groups: dict[int, list[tuple[int, int]]] = defaultdict(list)
    decoy_groups: dict[int, list[str]] = defaultdict(list)
    for slot_index, (offset, bit) in enumerate(slots):
        if not 0 <= offset <= len(text):
            raise ValueError("slot offset must be within the text")
        if bit not in (0, 1):
            raise ValueError("slot bit must be 0 or 1")
        slot_groups[offset].append((slot_index, bit))
    for offset, character in decoys:
        if not 0 <= offset <= len(text):
            raise ValueError("decoy offset must be within the text")
        if character not in DECOYS:
            raise ValueError("decoy must be U+200D or U+2060")
        decoy_groups[offset].append(character)

    output: list[str] = []
    output_length = 0
    slot_offsets = [0] * len(slots)
    for offset in range(len(text) + 1):
        for character in decoy_groups[offset]:
            output.append(character)
            output_length += 1
        for slot_index, bit in slot_groups[offset]:
            slot_offsets[slot_index] = output_length
            output.append(ZERO if bit == 0 else ONE)
            output_length += 1
        if offset < len(text):
            output.append(text[offset])
            output_length += 1
    return EmbeddedText("".join(output), tuple(slot_offsets))


def extract_zero_width(
    text: str,
    slot_offsets: Sequence[int],
) -> tuple[int | None, ...]:
    """Read C1 markers at aligned offsets; missing or undecodable marks are erasures."""
    if any(offset < 0 for offset in slot_offsets):
        raise ValueError("slot offsets must be non-negative")
    values: list[int | None] = []
    for offset in slot_offsets:
        cursor = offset
        while cursor < len(text) and text[cursor] in DECOYS:
            cursor += 1
        if cursor >= len(text):
            values.append(None)
        elif text[cursor] == ZERO:
            values.append(0)
        elif text[cursor] == ONE:
            values.append(1)
        else:
            values.append(None)
    return tuple(values)
