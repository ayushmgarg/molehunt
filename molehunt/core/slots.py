"""Allocate authored variation slots to keyed codeword positions."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from molehunt.core.keys import keyed_order
from molehunt.core.template import Choice, Template


@dataclass(frozen=True, slots=True)
class Slot:
    """One authored choice with keyed bit index and alignment context."""

    index: int
    source_index: int
    channel: str
    zero: str
    one: str
    source_offset: int
    anchor_before: str
    anchor_after: str


def _skeleton(template: Template) -> tuple[str, list[tuple[Choice, int]]]:
    """Render the canonical zero variant and retain each choice's offset."""
    chunks: list[str] = []
    locations: list[tuple[Choice, int]] = []
    offset = 0
    for node in template.nodes:
        if isinstance(node, Choice):
            locations.append((node, offset))
            chunks.append(node.zero)
            offset += len(node.zero)
        else:
            chunks.append(node.text)
            offset += len(node.text)
    return "".join(chunks), locations


def allocate_slots(
    template: Template,
    key: bytes,
    context_chars: int = 32,
) -> tuple[Slot, ...]:
    """Bind source choices to HMAC-shuffled code positions and anchor text."""
    if context_chars < 1:
        raise ValueError("context length must be at least one character")
    skeleton, locations = _skeleton(template)
    permutation = keyed_order(key, "slot-order", len(locations))
    slots = []
    for source_index, (choice, offset) in enumerate(locations):
        start = max(0, offset - context_chars)
        end = min(len(skeleton), offset + len(choice.zero) + context_chars)
        slots.append(
            Slot(
                index=permutation[source_index],
                source_index=source_index,
                channel=choice.channel,
                zero=choice.zero,
                one=choice.one,
                source_offset=offset,
                anchor_before=skeleton[start:offset],
                anchor_after=skeleton[offset + len(choice.zero) : end],
            )
        )
    return tuple(sorted(slots, key=lambda slot: slot.index))


def bits_in_source_order(slots: Sequence[Slot], codeword: Sequence[int]) -> list[int]:
    """Map codeword-indexed bits back to the order required by template rendering."""
    _validate_slots(slots)
    if len(codeword) != len(slots):
        raise ValueError(f"codeword length must equal slot count ({len(slots)})")
    if any(bit not in (0, 1) for bit in codeword):
        raise ValueError("each codeword bit must be 0 or 1")
    by_source = [0] * len(slots)
    for slot in slots:
        by_source[slot.source_index] = codeword[slot.index]
    return by_source


def _validate_slots(slots: Sequence[Slot]) -> None:
    indices = [slot.index for slot in slots]
    sources = [slot.source_index for slot in slots]
    if len(set(indices)) != len(indices) or len(set(sources)) != len(sources):
        raise ValueError("slots must have unique slot indices and source indices")


def capacity_report(slots: Sequence[Slot]) -> dict[str, int]:
    """Count authored slots per channel in stable alphabetical order."""
    _validate_slots(slots)
    return dict(sorted(Counter(slot.channel for slot in slots).items()))
