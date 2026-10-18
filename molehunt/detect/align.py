"""Locate variation slots between a canonical master and suspect text.

Algorithm (SPEC 5.5). Both the canonical master (every slot at its bit-0 variant)
and the suspect are reduced to the same skeleton: invisible format characters are
dropped, no-break spaces become spaces, look-alike letters map to Latin, curly
quotes and dashes become ASCII, text is lower-cased, and every authored word
variant is rewritten to one label per variant group (union-find over pairs, so a
word used in two pairs, e.g. take/need and need/require, still has one label).
Each skeleton character remembers the span of original characters it came from. ``difflib.SequenceMatcher`` blocks on the
two skeletons act as anchors; a slot's skeleton bounds are carried through the
nearest anchor and then mapped back to an original-text window in the suspect.
"""

from __future__ import annotations

import re
import unicodedata
from bisect import bisect_left
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

from molehunt.channels.homoglyph import CONFUSABLE_TO_LATIN
from molehunt.core.slots import Slot
from molehunt.core.template import Template

WORD_CHANNELS = frozenset({"lex", "spl", "spelling", "date", "dat", "number", "num"})
_CHAR_MAP = {
    "\u00a0": " ", "\u202f": " ", "\u2007": " ", "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-", "\u2026": "...",
    **CONFUSABLE_TO_LATIN,
}


@dataclass(frozen=True, slots=True)
class SlotWindow:
    """Suspect-text bounds around one source slot; absent bounds mean no alignment."""

    slot: Slot
    start: int | None
    end: int | None


@dataclass(frozen=True, slots=True)
class Skeleton:
    """Normalised text and, per character, the original span it represents."""

    text: str
    starts: tuple[int, ...]
    ends: tuple[int, ...]
    length: int


def _char_skeleton(text: str) -> tuple[list[str], list[int], list[int]]:
    chars: list[str] = []
    starts: list[int] = []
    ends: list[int] = []
    for index, character in enumerate(text):
        if unicodedata.category(character) == "Cf":
            continue
        for output in _CHAR_MAP.get(character, character).lower():
            chars.append(output)
            starts.append(index)
            ends.append(index + 1)
    return chars, starts, ends


def _variant_groups(variants: Sequence[tuple[str, str]]) -> dict[str, str]:
    """Union-find over variant pairs: every word maps to its group's smallest member."""
    parent: dict[str, str] = {}

    def find(word: str) -> str:
        while parent.setdefault(word, word) != word:
            word = parent[word]
        return word

    for zero, one in variants:
        left, right = "".join(_char_skeleton(zero)[0]), "".join(_char_skeleton(one)[0])
        if left and right:
            first, second = sorted((find(left), find(right)))
            parent[second] = first
    return {word: find(word) for word in parent if find(word) != word}


def build_skeleton(text: str, variants: Sequence[tuple[str, str]] = ()) -> Skeleton:
    """Normalise characters, then rewrite every word variant to its group label."""
    chars, starts, ends = _char_skeleton(text)
    flat = "".join(chars)
    mapping = _variant_groups(variants)
    if not mapping:
        return Skeleton(flat, tuple(starts), tuple(ends), len(text))
    pattern = re.compile(
        r"(?<!\w)(" + "|".join(re.escape(one) for one in sorted(mapping, key=len, reverse=True))
        + r")(?!\w)"
    )
    out: list[str] = []
    new_starts: list[int] = []
    new_ends: list[int] = []
    cursor = 0
    for match in pattern.finditer(flat):
        out.extend(flat[cursor : match.start()])
        new_starts.extend(starts[cursor : match.start()])
        new_ends.extend(ends[cursor : match.start()])
        replacement = mapping[match.group(1)]
        out.extend(replacement)
        new_starts.extend([starts[match.start()]] * len(replacement))
        new_ends.extend([ends[match.end() - 1]] * len(replacement))
        cursor = match.end()
    out.extend(flat[cursor:])
    new_starts.extend(starts[cursor:])
    new_ends.extend(ends[cursor:])
    return Skeleton("".join(out), tuple(new_starts), tuple(new_ends), len(text))


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


def _skeleton_index(skeleton: Skeleton, original_offset: int) -> int:
    """First skeleton character produced at or after an original offset."""
    return bisect_left(skeleton.starts, original_offset)


def _original_start(skeleton: Skeleton, index: int) -> int:
    return skeleton.ends[index - 1] if index > 0 else 0


def _original_end(skeleton: Skeleton, index: int) -> int:
    return skeleton.starts[index] if index < len(skeleton.text) else skeleton.length


def align_to_master(
    template: Template,
    slots: Sequence[Slot],
    suspect_text: str,
) -> tuple[SlotWindow, ...]:
    """Bound each source slot in the suspect via anchors between the two skeletons."""
    canonical = template.render([0] * len(template.choices))
    variants = [
        (choice.zero, choice.one) for choice in template.choices if choice.channel in WORD_CHANNELS
    ]
    master = build_skeleton(canonical, variants)
    suspect = build_skeleton(suspect_text, variants)
    blocks = SequenceMatcher(None, master.text, suspect.text, autojunk=False).get_matching_blocks()
    result = []
    for slot in slots:
        source_start = _skeleton_index(master, slot.source_offset)
        source_end = _skeleton_index(master, slot.source_offset + len(slot.zero))
        start = _mapped_position(source_start, blocks)
        end = _mapped_position(source_end, blocks)
        start = 0 if start is None else start
        end = len(suspect.text) if end is None else end
        if end < start:
            result.append(SlotWindow(slot, None, None))
            continue
        original_start = _original_start(suspect, start)
        original_end = _original_end(suspect, end)
        original_end = max(original_end, original_start)
        result.append(SlotWindow(slot, original_start, original_end))
    return tuple(result)
