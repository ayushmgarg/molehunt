"""Locate variation slots between a canonical master and suspect text."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

from molehunt.core.slots import Slot
from molehunt.core.template import Template


@dataclass(frozen=True, slots=True)
class SlotWindow:
    """Suspect-text bounds around one source slot; absent bounds mean no alignment."""

    slot: Slot
    start: int | None
    end: int | None


def _mapped_position(
    position: int,
    blocks: Sequence[tuple[int, int, int]],
) -> int | None:
    """Map a source boundary through a matching block when possible."""
    containing = [
        (a, b, size)
        for a, b, size in blocks
        if size and a <= position <= a + size
    ]
    if containing:
        a, b, _ = min(containing, key=lambda block: block[0])
        return b + position - a
    preceding = [block for block in blocks if block[2] and block[0] + block[2] <= position]
    if preceding:
        a, b, size = max(preceding, key=lambda block: block[0] + block[2])
        return b + size
    following = [block for block in blocks if block[2] and block[0] >= position]
    if following:
        a, b, _ = min(following, key=lambda block: block[0])
        return b
    return None


def align_to_master(
    template: Template,
    slots: Sequence[Slot],
    suspect_text: str,
) -> tuple[SlotWindow, ...]:
    """Use exact blocks from `SequenceMatcher` to bound each source slot."""
    canonical = template.render([0] * len(template.choices))
    blocks = SequenceMatcher(None, canonical, suspect_text, autojunk=False).get_matching_blocks()
    result = []
    for slot in slots:
        source_start = slot.source_offset
        source_end = source_start + len(slot.zero)
        start = _mapped_position(source_start, blocks)
        end = _mapped_position(source_end, blocks)
        if start is None:
            start = 0
        if end is None:
            end = len(suspect_text)
        if end < start:
            result.append(SlotWindow(slot, None, None))
        else:
            result.append(SlotWindow(slot, start, end))
    return tuple(result)
