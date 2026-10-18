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
from bisect import bisect_left, bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache

from molehunt.core.slots import Slot
from molehunt.core.template import Template
from molehunt.detect.reorder import map_back, restore_order
from molehunt.detect.skeleton import Skeleton, _char_skeleton, build_skeleton

_TOKEN = re.compile(r"\w+|[^\w\s]")
WORD_CHANNELS = frozenset({"lex", "spl", "spelling", "date", "dat", "number", "num"})


@dataclass(frozen=True, slots=True)
class SlotWindow:
    """Suspect-text bounds around one source slot; absent bounds mean no alignment."""

    slot: Slot
    start: int | None
    end: int | None
    anchored: bool = True


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


def _volatile_tokens(template: Template, slots: Sequence[Slot], master: Skeleton,
                     tokens: _Tokens) -> set[int]:
    """Master tokens inside slots whose two variants differ after skeletonising
    (e.g. an Oxford comma vs nothing); they may be absent, so never anchor on them."""
    volatile: set[int] = set()
    for slot in slots:
        if slot.channel in WORD_CHANNELS:
            continue
        if "".join(_char_skeleton(slot.zero)[0]) == "".join(_char_skeleton(slot.one)[0]):
            continue
        start = _skeleton_index(master, slot.source_offset)
        end = _skeleton_index(master, slot.source_offset + len(slot.zero))
        first = bisect_right(tokens.starts, start, 0, len(tokens.words)) - 1
        for index in range(max(first, 0), len(tokens.words)):
            if tokens.starts[index] >= end:
                break
            if tokens.starts[index] + len(tokens.words[index]) > start:
                volatile.add(index)
    return volatile


def _anchored(start: int, end: int, master: _Tokens, paired: list[int],
              volatile: set[int]) -> bool:
    """Anchor check (SPEC 5.5): the two nearest stable master tokens on each side
    of the slot must be aligned, contiguous, and in order in the suspect;
    otherwise the context is missing and the slot is an erasure."""
    ends = [first + len(word) for first, word in zip(master.starts, master.words, strict=False)]
    left_last = bisect_right(ends, start) - 1
    right_first = bisect_left(master.starts, end, 0, len(master.words))
    left = [i for i in range(left_last, -1, -1) if i not in volatile][:2][::-1]
    right = [i for i in range(right_first, len(master.words)) if i not in volatile][:2]
    if not left and not right:
        return False
    if any(paired[i] < 0 for i in left + right):
        return False
    for side in (left, right):
        if len(side) == 2 and paired[side[1]] - paired[side[0]] > side[1] - side[0]:
            return False
        if len(side) == 2 and paired[side[1]] <= paired[side[0]]:
            return False
    if left and right:
        gap = paired[right[0]] - paired[left[-1]]
        return 0 < gap <= right[0] - left[-1] + 2
    return True


def _align_ordered(
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
    volatile = _volatile_tokens(template, slots, master, master_tokens)
    paired = [-1] * len(master_tokens.words)
    for a, b, size in blocks:
        for step in range(size):
            paired[a + step] = b + step
    result = []
    for slot in slots:
        source_start = _skeleton_index(master, slot.source_offset)
        source_end = _skeleton_index(master, slot.source_offset + len(slot.zero))
        anchored = _anchored(source_start, source_end, master_tokens, paired, volatile)
        start = _map_char(source_start, False, master_tokens, suspect_tokens, blocks)
        end = _map_char(source_end, True, master_tokens, suspect_tokens, blocks)
        start = 0 if start is None else start
        end = len(suspect.text) if end is None else end
        if end < start:
            result.append(SlotWindow(slot, None, None))
            continue
        original_start = _original_start(suspect, start)
        original_end = max(_original_end(suspect, end), original_start)
        if not anchored:
            original_end = original_start
        result.append(SlotWindow(slot, original_start, original_end, anchored))
    return tuple(result)


def align_to_master(
    template: Template,
    slots: Sequence[Slot],
    suspect_text: str,
) -> tuple[SlotWindow, ...]:
    """Restore paragraph order if shuffled, then align; windows use original offsets."""
    restored = restore_order(template, suspect_text)
    if restored is None:
        return _align_ordered(template, slots, suspect_text)
    text, segments = restored
    result = []
    for window in _align_ordered(template, slots, text):
        start, end = map_back(window.start, segments), map_back(window.end, segments)
        if start is None or end is None or end < start:
            result.append(SlotWindow(window.slot, None, None))
        else:
            result.append(SlotWindow(window.slot, start, end, window.anchored))
    return tuple(result)
