"""Skeleton text for alignment (SPEC 5.5: "lowercase, variants canonicalised").

Characters: drop Unicode format characters (Cf, e.g. zero-width marks), map no-break
spaces to a space, curly quotes and dashes to ASCII, Cyrillic/Greek look-alikes to
Latin, then lower-case. Words: every authored variant word is rewritten to one
label per variant group (union-find over pairs; the label is the group's smallest
member). Each skeleton character keeps the [start, end) span of original text it
came from, so positions found in the skeleton map back to the original document.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from molehunt.channels.homoglyph import CONFUSABLE_TO_LATIN

_CHAR_MAP = {
    "\u00a0": " ", "\u202f": " ", "\u2007": " ", "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-", "\u2026": "...",
    **CONFUSABLE_TO_LATIN,
}


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
