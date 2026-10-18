"""Restore the paragraph order of a shuffled leak before alignment (A9 defence).

Alignment anchors are monotonic, so shuffled paragraphs lose their slots. Each
suspect paragraph is placed at the master paragraph whose word set overlaps it
most (Jaccard = |A and B| / |A or B|); the text is rebuilt in that order and every
window is mapped back to original offsets through the recorded segments.
"""

from __future__ import annotations

import re

from molehunt.core.template import Template
from molehunt.detect.skeleton import build_skeleton

_PARAGRAPH = re.compile(r"\n\s*\n")
_WORD = re.compile(r"\w+")


def _paragraphs(text: str) -> list[tuple[int, int]]:
    spans, start = [], 0
    for match in _PARAGRAPH.finditer(text):
        spans.append((start, match.start()))
        start = match.end()
    spans.append((start, len(text)))
    return [(a, b) for a, b in spans if text[a:b].strip()]


def restore_order(template: Template, text: str) -> tuple[str, list[tuple[int, int, int]]] | None:
    """Put shuffled suspect paragraphs back in master order (A9 defence).

    Each suspect paragraph is placed at the master paragraph sharing the most
    words (Jaccard overlap of word sets). Returns the reordered text and segments
    (new start, original start, length), or None when the order is unchanged.
    """
    spans = _paragraphs(text)
    if len(spans) < 2:
        return None
    canonical = build_skeleton(template.render([0] * len(template.choices))).text
    masters = [set(_WORD.findall(canonical[a:b])) for a, b in _paragraphs(canonical)]

    def place(span: tuple[int, int]) -> int:
        words = set(_WORD.findall(build_skeleton(text[span[0]:span[1]]).text))
        return max(range(len(masters)),
                   key=lambda i: len(words & masters[i]) / max(1, len(words | masters[i])))

    ordered = sorted(spans, key=place)
    if ordered == spans:
        return None
    pieces, segments, cursor = [], [], 0
    for start, end in ordered:
        segments.append((cursor, start, end - start))
        pieces.append(text[start:end])
        cursor += end - start + 2
    return "\n\n".join(pieces), segments


def map_back(position: int | None, segments: list[tuple[int, int, int]]) -> int | None:
    if position is None:
        return None
    for new_start, old_start, length in segments:
        if new_start <= position <= new_start + length:
            return old_start + position - new_start
    return None
