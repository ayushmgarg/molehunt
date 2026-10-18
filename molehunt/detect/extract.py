"""Extract observed bits from aligned slot windows, keeping erasures explicit."""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from scipy.stats import binom

from molehunt.core.slots import Slot
from molehunt.detect.align import SlotWindow

_WORD_CHANNELS = frozenset({"lex", "spl", "spelling", "date", "dat", "number", "num"})


@dataclass(frozen=True, slots=True)
class SlotObservation:
    """One extracted binary value or an erasure, with source and evidence offsets."""

    slot_index: int
    source_index: int
    bit: int | None
    offset: int | None


def _word_character(character: str) -> bool:
    return character.isalnum() or character == "_"


def _blank(region: str) -> bool:
    """True when a region holds only whitespace or invisible format characters."""
    return all(ch.isspace() or unicodedata.category(ch) == "Cf" for ch in region)


def _matches(region: str, variant: str, channel: str) -> list[int]:
    if not variant:
        return [0] if _blank(region) else []
    positions = []
    start = 0
    while True:
        index = region.find(variant, start)
        if index < 0:
            break
        end = index + len(variant)
        left = index == 0 or channel not in _WORD_CHANNELS or not _word_character(region[index - 1])
        right = end == len(region) or channel not in _WORD_CHANNELS or not _word_character(region[end])
        if left and right:
            positions.append(index)
        start = index + 1
    return positions


def _classify(region: str, slot: Slot) -> tuple[int | None, int | None]:
    if slot.zero == slot.one:
        return None, None
    if region == slot.zero:
        return 0, 0
    if region == slot.one:
        return 1, 0
    candidates = []
    for bit, variant in ((0, slot.zero), (1, slot.one)):
        candidates.extend((bit, index) for index in _matches(region, variant, slot.channel))
    unique = set(candidates)
    if len(unique) == 1:
        return next(iter(unique))
    return None, None


def extract_variants(
    suspect_text: str,
    windows: Sequence[SlotWindow],
) -> tuple[SlotObservation, ...]:
    """Extract unique slot variants; missing, changed, or ambiguous values are None."""
    observations = []
    for window in windows:
        slot = window.slot
        if window.start is None or window.end is None or not window.anchored:
            observations.append(SlotObservation(slot.index, slot.source_index, None, None))
            continue
        start = min(window.start, len(suspect_text))
        end = min(window.end, len(suspect_text))
        if end < start:
            observations.append(SlotObservation(slot.index, slot.source_index, None, None))
            continue
        bit, relative_offset = _classify(suspect_text[start:end], slot)
        offset = start + relative_offset if relative_offset is not None else None
        observations.append(SlotObservation(slot.index, slot.source_index, bit, offset))
    return tuple(observations)


def erase_uniform_channels(
    slots: Sequence[Slot],
    bits: Sequence[int | None],
    *,
    p_cut: float = 1e-6,
    min_observed: int = 12,
) -> tuple[tuple[int | None, ...], tuple[str, ...]]:
    """Erase channels whose reads are almost all one value (a forged channel).

    A genuine copy carries keyed random bits, so within a channel about half the
    reads are 0. Normalising attacks (A4 punctuation, A6 dictionary
    canonicalisation) rewrite every slot to one variant and forge a constant bit.
    Two-sided binomial test of the 0/1 balance: p = 2 * P(X <= min(k0, k1)),
    X ~ Binomial(n, 0.5). If p < 1e-6 the channel's reads become erasures.
    """
    by_channel: dict[str, list[int]] = {}
    for slot in slots:
        if bits[slot.index] is not None:
            by_channel.setdefault(slot.channel, []).append(bits[slot.index])
    forged = []
    for channel, values in by_channel.items():
        n, ones = len(values), sum(values)
        if n >= min_observed and 2 * binom.cdf(min(ones, n - ones), n, 0.5) < p_cut:
            forged.append(channel)
    cleaned = list(bits)
    for slot in slots:
        if slot.channel in forged:
            cleaned[slot.index] = None
    return tuple(cleaned), tuple(sorted(forged))
