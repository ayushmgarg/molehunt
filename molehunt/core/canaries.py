"""Fact-level canaries: each copy states a few facts (codename, figure, room) differently.

Invisible marks die when a leaker retypes or summarises the document; a fact does
not. The master declares fact families in front matter and uses them in the body::

    ---
    canaries:
      codename: [Nightjar, Kestrel, Osprey, Merlin]
      budget: [4.2 million, 4.6 million, 5.1 million, 5.4 million]
    ---
    Project {{can:codename}} has a budget of {{can:budget}}.

Choice. For family f with v values, holder h gets value index
``HMAC(K, "canary", f, h) mod v``. Without K nobody can predict another copy's facts.

Placement. ``{{can:f}}`` is replaced in the master by a sentinel ``§i§`` (digits
only), so keyed auto slots never land inside a fact and every copy shares one slot
map. The sentinel is swapped for the holder's value only at render time.

Matching. A leak (even a paraphrase or a headline) is searched for every value of
every family (case-insensitive, whole words). For each family that shows up:
P(match | holder) = 0.95 and P(match | someone else) = 1/v, so a match adds
log10(0.95 v) and a mismatch adds log10(0.05 / (1 - 1/v)). Families that do not
appear are missing data (rule 13). Two values of one family in a single leak mean
copies were merged.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from molehunt.core.keys import digest

SENTINEL = "§{}§"
_TOKEN = re.compile(r"\{\{can:(?P<name>[a-z][a-z0-9_]*)\}\}")
HIT, MISS = 0.95, 0.05


@dataclass(frozen=True, slots=True)
class CanaryFamily:
    """One fact family: its name, sentinel text, and the allowed values."""

    name: str
    sentinel: str
    values: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CanaryScore:
    """Fact evidence for one holder."""

    holder: str
    hits: int
    misses: int
    log10_lr: float


@dataclass(frozen=True, slots=True)
class CanaryReport:
    """Facts seen in a leak and every holder ranked by fact evidence."""

    seen: dict[str, tuple[str, ...]]
    scores: tuple[CanaryScore, ...]

    @property
    def merged_families(self) -> tuple[str, ...]:
        """Families with two or more values present: a sign of merged copies."""
        return tuple(name for name, values in self.seen.items() if len(values) > 1)


def parse_canaries(raw: object, body: str) -> tuple[str, tuple[CanaryFamily, ...]]:
    """Validate the ``canaries`` mapping and put sentinels in place of ``{{can:f}}``."""
    if raw in (None, {}):
        if _TOKEN.search(body):
            raise ValueError("{{can:...}} used but no canaries declared in front matter")
        return body, ()
    if not isinstance(raw, dict):
        raise TypeError("canaries must map a family name to a list of values")
    families: list[CanaryFamily] = []
    for index, (name, values) in enumerate(raw.items()):
        if not isinstance(values, list) or len(values) < 2:
            raise ValueError(f"canary family {name!r} needs a list of at least two values")
        clean = tuple(str(value).strip() for value in values)
        if len({value.casefold() for value in clean}) != len(clean) or not all(clean):
            raise ValueError(f"canary family {name!r} has empty or repeated values")
        families.append(CanaryFamily(str(name), SENTINEL.format(index), clean))
    by_name = {family.name: family for family in families}
    used = set()

    def swap(match: re.Match) -> str:
        family = by_name.get(match.group("name"))
        if family is None:
            raise ValueError(f"unknown canary family {match.group('name')!r}")
        used.add(family.name)
        return family.sentinel

    replaced = _TOKEN.sub(swap, body)
    if used != set(by_name):
        raise ValueError(f"canary families never used: {', '.join(sorted(set(by_name) - used))}")
    for family in families:
        for value in family.values:
            if fact_pattern(value).search(replaced):
                raise ValueError(f"canary value {value!r} already appears in the master text")
    return replaced, tuple(families)


def holder_values(families: Sequence[CanaryFamily], key: bytes, holder: str) -> dict[str, str]:
    """Sentinel -> value chosen for one holder by the keyed HMAC."""
    chosen = {}
    for family in families:
        index = int.from_bytes(digest(key, "canary", family.name, holder)[:4], "big")
        chosen[family.sentinel] = family.values[index % len(family.values)]
    return chosen


def fill(text: str, values: Mapping[str, str] | None) -> str:
    """Replace sentinels in rendered text with the holder's fact values."""
    for sentinel, value in (values or {}).items():
        text = text.replace(sentinel, value)
    return text


def fact_pattern(value: str) -> re.Pattern:
    """Whole-word, case-insensitive pattern for one value; any run of spaces between words."""
    words = (re.escape(part) for part in value.split())
    return re.compile(r"(?<!\w)" + r"\s+".join(words) + r"(?!\w)", re.IGNORECASE)


def mask(text: str, families: Sequence[CanaryFamily]) -> str:
    """Put sentinels back where any fact value appears, so alignment sees the master."""
    for family in families:
        for value in sorted(family.values, key=len, reverse=True):
            text = fact_pattern(value).sub(family.sentinel, text)
    return text


def seen_facts(text: str, families: Sequence[CanaryFamily]) -> dict[str, tuple[str, ...]]:
    """Family -> values that occur in the text (families with none are left out)."""
    seen = {}
    for family in families:
        found = tuple(value for value in family.values if fact_pattern(value).search(text))
        if found:
            seen[family.name] = found
    return seen


def match_canaries(text: str, families: Sequence[CanaryFamily], key: bytes,
                   holders: Sequence[str]) -> CanaryReport:
    """Rank holders by how many of their facts appear in the leak."""
    seen = seen_facts(text, families)
    scores = []
    for holder in holders:
        values = holder_values(families, key, holder)
        hits = misses = 0
        total = 0.0
        for family in families:
            if family.name not in seen:
                continue
            size = len(family.values)
            if values[family.sentinel] in seen[family.name]:
                hits += 1
                total += math.log10(HIT * size)
            else:
                misses += 1
                total += math.log10(MISS / (1 - 1 / size))
        scores.append(CanaryScore(holder, hits, misses, total))
    ranked = sorted(scores, key=lambda item: (-item.log10_lr, item.holder))
    return CanaryReport(seen, tuple(ranked))
