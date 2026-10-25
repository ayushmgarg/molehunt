"""Fingerprint heatmap and attribution-o-meter for one analysed leak.

Heatmap. The leak text is cut into segments. Every slot window found by the
aligner is coloured by comparing the read bit with the named candidate's codeword:
``match`` (green), ``mismatch`` (red), or ``erased`` (grey: missing data, never a
mismatch, rule 13). Canary facts are segments of kind ``fact``. Invisible variants
(zero-width characters, special spaces) are kept in the segment text; the page
draws a visible marker for them.

Meter. Walk the observed slots in reading order and add each slot's log-likelihood
ratio of the leader against the runner-up:

    step = log10 P(bit | leader) - log10 P(bit | runner-up)
    P(bit | c) = 1 - e if bit equals c's bit, else e        (e = flip rate)

Slots where both candidates agree add 0. The running sum is the evidence curve;
its last value equals the leader's log10 LR minus the runner-up's, which is the
separability margin used by ``detect/decide.py`` (attribute at >= 2).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from molehunt.analysis import AnalysisResult
from molehunt.core.canaries import CanaryFamily, fact_pattern
from molehunt.detect.align import align_to_master


@dataclass(frozen=True, slots=True)
class Segment:
    """A run of leak text and how it is coloured."""

    text: str
    kind: str  # plain | match | mismatch | erased | fact
    channel: str = ""


def _masked(text: str, families: tuple[CanaryFamily, ...]) -> tuple[str, dict[int, str]]:
    """Mask fact values with sentinels; remember original value at each masked offset."""
    hits: list[tuple[int, int, str, str]] = []
    for family in families:
        for value in sorted(family.values, key=len, reverse=True):
            for match in fact_pattern(value).finditer(text):
                if all(match.end() <= a or match.start() >= b for a, b, _, _ in hits):
                    hits.append((match.start(), match.end(), family.sentinel, match.group(0)))
    pieces, originals, cursor, length = [], {}, 0, 0
    for start, end, sentinel, original in sorted(hits):
        pieces.append(text[cursor:start])
        length += start - cursor
        originals[length] = original
        pieces.append(sentinel)
        length += len(sentinel)
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces), originals


def heatmap(result: AnalysisResult, text: str, candidate: str) -> list[Segment]:
    """Colour each slot window of the leak against ``candidate``'s codeword."""
    prepared = result.prepared
    masked, originals = _masked(text, prepared.canaries)
    word = result.codewords[candidate]
    marks: list[tuple[int, int, str, str]] = []
    for window in align_to_master(prepared.template, prepared.slots, masked):
        if window.start is None or window.end is None:
            continue
        bit = result.observations[window.slot.index]
        kind = "erased" if bit is None else "match" if bit == word[window.slot.index] else "mismatch"
        marks.append((window.start, window.end, kind, window.slot.channel))
    sentinel = re.compile("§\\d+§")
    for found in sentinel.finditer(masked):
        if found.start() in originals:
            marks.append((found.start(), found.end(), "fact", ""))
    segments, cursor = [], 0
    for start, end, kind, channel in sorted(marks):
        if start < cursor:
            continue
        if start > cursor:
            segments.append(Segment(masked[cursor:start], "plain"))
        shown = originals[start] if kind == "fact" else masked[start:end]
        segments.append(Segment(shown, kind, channel))
        cursor = end
    if cursor < len(masked):
        segments.append(Segment(masked[cursor:], "plain"))
    return segments


def evidence_curve(result: AnalysisResult, text: str, *, flip_rate: float = 0.15
                   ) -> tuple[str, str, list[float]]:
    """Leader, runner-up, and the running log10 LR margin in reading order."""
    if len(result.scores) < 2:
        raise ValueError("the meter needs at least two candidates")
    leader, runner = result.scores[0].candidate_id, result.scores[1].candidate_id
    first, second = result.codewords[leader], result.codewords[runner]
    hit, miss = math.log10(1 - flip_rate), math.log10(flip_rate)
    ordered = sorted((item for item in result.extracted if result.observations[item.slot_index]
                      is not None), key=lambda item: (item.offset or 0, item.slot_index))
    curve, total = [], 0.0
    for item in ordered:
        bit = result.observations[item.slot_index]
        total += (hit if bit == first[item.slot_index] else miss) - (
            hit if bit == second[item.slot_index] else miss)
        curve.append(round(total, 3))
    return leader, runner, curve
