"""Locate variation slots between a canonical master and suspect text.

Algorithm (SPEC 5.5). Both the canonical master (every slot at its bit-0 variant)
and the suspect are reduced to the same skeleton: invisible format characters are
dropped, no-break spaces become spaces, look-alike letters map to Latin, curly
quotes and dashes become ASCII, text is lower-cased, and every authored word
variant is rewritten to one label per variant group (union-find over pairs, so a
word used in two pairs, e.g. take/need and need/require, still has one label).
Each skeleton character remembers the span of original characters it came from. ``difflib.SequenceMatcher`` blocks on the
two skeletons' token sequences (words and symbols, spaces skipped) act as anchors; a
slot's skeleton bounds are carried through the nearest anchor and then mapped
back to an original-text window in the suspect. Token-level matching keeps the
quadratic matcher small (about 1,500 tokens instead of 6,000 characters).
"""

from __future__ import annotations

import re
import unicodedata
from bisect import bisect_left
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache

from molehunt.channels.homoglyph import CONFUSABLE_TO_LATIN
from molehunt.core.slots import Slot
from molehunt.core.template import Template

_TOKEN = re.compile(r"\w+|[^\w\s]")
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


@dataclass(frozen=True, slots=True)
class _Tokens:
    """Skeleton tokens (words and single symbols; spaces skipped) and char starts."""

    words: tuple[str, ...]
    starts: tuple[int, ...]  # one extra sentinel: len(skeleton text)


def _tokenize(text: str) -> _Tokens:
    matches = list(_TOKEN.finditer(text))
    return _Tokens(
        tuple(match.group(0) for match in matches),
        tuple(match.start() for match in matches) + (len(text),),
    )


@lru_cache(maxsize=16)
def _master_side(template: Template) -> tuple[Skeleton, _Tokens, tuple[tuple[str, str], ...]]:
    """Canonical skeleton and tokens of a master; cached because masters repeat."""
    canonical = template.render([0] * len(template.choices))
    variants = tuple(
        (choice.zero, choice.one) for choice in template.choices if choice.channel in WORD_CHANNELS
    )
    skeleton = build_skeleton(canonical, variants)
    return skeleton, _tokenize(skeleton.text), variants


def _block_of(token: int, blocks: Sequence[tuple[int, int, int]]) -> int | None:
    """Suspect token index paired with a master token, if a block covers it."""
    for a, b, size in blocks:
        if size and a <= token < a + size:
            return b + token - a
    return None


def _map_char(
    position: int,
    end_side: bool,
    master: _Tokens,
    suspect: _Tokens,
    blocks: Sequence[tuple[int, int, int]],
) -> int | None:
    """Map a master skeleton char position to the suspect skeleton via token blocks.

    Positions inside or on the edge of a matched token map exactly. In a gap
    between tokens a window start goes to the end of the previous suspect token
    and a window end to the start of the next, so the gap's spaces and invisible
    marks stay inside the window.
    """
    count = len(master.words)
    following = bisect_left(master.starts, position, 0, count)
    previous = following - 1
    previous_end = master.starts[previous] + len(master.words[previous]) if previous >= 0 else 0
    if previous >= 0 and position < previous_end:
        paired = _block_of(previous, blocks)
        if paired is not None:
            return suspect.starts[paired] + position - master.starts[previous]
        boundary = previous + 1 if end_side else previous
    elif not end_side and following < count and position == master.starts[following]:
        paired = _block_of(following, blocks)
        if paired is not None:
            return suspect.starts[paired]
        boundary = following
    elif end_side and previous >= 0 and position == previous_end:
        paired = _block_of(previous, blocks)
        if paired is not None:
            return suspect.starts[paired] + len(suspect.words[paired])
        boundary = following
    else:
        boundary = following
    mapped = _mapped_position(boundary, blocks)
    if mapped is None:
        return None
    if end_side:
        return suspect.starts[mapped]
    return suspect.starts[mapped - 1] + len(suspect.words[mapped - 1]) if mapped > 0 else 0


def align_to_master(
    template: Template,
    slots: Sequence[Slot],
    suspect_text: str,
) -> tuple[SlotWindow, ...]:
    """Bound each source slot in the suspect via token anchors between skeletons."""
    master, master_tokens, variants = _master_side(template)
    suspect = build_skeleton(suspect_text, variants)
    suspect_tokens = _tokenize(suspect.text)
    blocks = SequenceMatcher(
        None, master_tokens.words, suspect_tokens.words, autojunk=False
    ).get_matching_blocks()
    result = []
    for slot in slots:
        source_start = _skeleton_index(master, slot.source_offset)
        source_end = _skeleton_index(master, slot.source_offset + len(slot.zero))
        start = _map_char(source_start, False, master_tokens, suspect_tokens, blocks)
        end = _map_char(source_end, True, master_tokens, suspect_tokens, blocks)
        start = 0 if start is None else start
        end = len(suspect.text) if end is None else end
        if end < start:
            result.append(SlotWindow(slot, None, None))
            continue
        original_start = _original_start(suspect, start)
        original_end = max(_original_end(suspect, end), original_start)
        result.append(SlotWindow(slot, original_start, original_end))
    return tuple(result)
