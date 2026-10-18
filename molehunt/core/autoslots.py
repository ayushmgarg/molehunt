"""Insert keyed C1, C2, and C3b slots that the master author does not write by hand.

A master may start with YAML front matter::

    ---
    auto_slots: {zw: 90, nbsp: 40, hom: 40}
    ---

Algorithm. Collect every eligible position in the literal (non-authored) text:
word ends followed by punctuation or space (C1 ``zw``), single spaces between two
letters (C2 ``nbsp``), and letters that have two look-alikes (C3b ``hom``). For each
channel rank the candidates with the keyed HMAC permutation ``keyed_order`` and keep
the first k, so without K an attacker cannot predict which positions carry bits.
Each pick becomes an ordinary two-variant ``Choice``. Both variants are
non-canonical (ZWSP/ZWNJ, NBSP/NNBSP, Cyrillic/Greek), so a normalising attack
maps both to the same plain form and the slot reads as an erasure, not as bit 0.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml

from molehunt.core.keys import keyed_order
from molehunt.core.slots import Slot, allocate_slots
from molehunt.core.template import Choice, Literal, Node, Template, parse_template

AUTO_CHANNELS = ("zw", "nbsp", "hom")
ZW_VARIANTS = ("\u200b", "\u200c")
NBSP_VARIANTS = ("\u00a0", "\u202f")
# Latin letter -> (Cyrillic look-alike, Greek look-alike); bit 0 / bit 1.
HOMOGLYPH_PAIRS = {
    "o": ("\u043e", "\u03bf"), "A": ("\u0410", "\u0391"), "B": ("\u0412", "\u0392"),
    "E": ("\u0415", "\u0395"), "H": ("\u041d", "\u0397"), "K": ("\u041a", "\u039a"),
    "M": ("\u041c", "\u039c"), "O": ("\u041e", "\u039f"), "P": ("\u0420", "\u03a1"),
    "T": ("\u0422", "\u03a4"), "X": ("\u0425", "\u03a7"),
}
_WORD = re.compile(r"[A-Za-z]{3,}")
_FRONT = re.compile(r"\A---\r?\n(?P<yaml>.*?)\r?\n---\r?\n", re.DOTALL)
_ALLOWED_FRONT = {"auto_slots", "title"}


@dataclass(frozen=True, slots=True)
class PreparedMaster:
    """Template with auto slots inserted, its keyed slot map, and declared counts."""

    template: Template
    slots: tuple[Slot, ...]
    auto_counts: dict[str, int]


def split_front_matter(source: str) -> tuple[dict[str, Any], str]:
    """Return the YAML settings mapping and the template body after it."""
    match = _FRONT.match(source)
    if match is None:
        return {}, source
    settings = yaml.safe_load(match.group("yaml")) or {}
    if not isinstance(settings, dict):
        raise TypeError("front matter must be a YAML mapping")
    unknown = set(settings) - _ALLOWED_FRONT
    if unknown:
        raise ValueError(f"unknown front matter keys: {', '.join(sorted(unknown))}")
    return settings, source[match.end() :]


def _counts(settings: dict[str, Any]) -> dict[str, int]:
    raw = settings.get("auto_slots") or {}
    if not isinstance(raw, dict) or set(raw) - set(AUTO_CHANNELS):
        raise ValueError(f"auto_slots may only set {', '.join(AUTO_CHANNELS)}")
    counts = {channel: raw.get(channel, 0) for channel in AUTO_CHANNELS}
    for channel, value in counts.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"auto_slots.{channel} must be a non-negative integer")
    return counts


def _candidates(template: Template) -> dict[str, list[tuple[int, int]]]:
    """List (node index, character offset) positions eligible for each channel."""
    found: dict[str, list[tuple[int, int]]] = {channel: [] for channel in AUTO_CHANNELS}
    for node_index, node in enumerate(template.nodes):
        if not isinstance(node, Literal):
            continue
        text = node.text
        for match in _WORD.finditer(text):
            end = match.end()
            if end < len(text) and text[end] in " ,.;:\n":
                found["zw"].append((node_index, end))
            for offset in range(match.start(), end):
                if text[offset] in HOMOGLYPH_PAIRS:
                    found["hom"].append((node_index, offset))
        for offset in range(1, len(text) - 1):
            if text[offset] == " " and text[offset - 1].isalpha() and text[offset + 1].isalpha():
                found["nbsp"].append((node_index, offset))
    return found


def _pick(key: bytes, channel: str, pool: list[tuple[int, int]], count: int) -> set:
    if count > len(pool):
        raise ValueError(f"auto_slots.{channel}={count} exceeds {len(pool)} eligible positions")
    order = keyed_order(key, f"auto-{channel}", len(pool))
    return {pool[index] for index in order[:count]}


def insert_auto_slots(template: Template, key: bytes, counts: dict[str, int]) -> Template:
    """Split literals at keyed positions and add zw, nbsp, and hom choices."""
    pools = _candidates(template)
    zw = _pick(key, "zw", pools["zw"], counts.get("zw", 0))
    pools["nbsp"] = [item for item in pools["nbsp"] if item not in zw]
    nbsp = _pick(key, "nbsp", pools["nbsp"], counts.get("nbsp", 0))
    hom = _pick(key, "hom", pools["hom"], counts.get("hom", 0))
    nodes: list[Node] = []
    for node_index, node in enumerate(template.nodes):
        if not isinstance(node, Literal):
            nodes.append(node)
            continue
        text = node.text
        edits: list[tuple[int, int, Choice]] = []
        for _, offset in sorted(item for item in zw if item[0] == node_index):
            edits.append((offset, offset, Choice("zw", *ZW_VARIANTS)))
        for _, offset in sorted(item for item in nbsp if item[0] == node_index):
            edits.append((offset, offset + 1, Choice("nbsp", *NBSP_VARIANTS)))
        for _, offset in sorted(item for item in hom if item[0] == node_index):
            edits.append((offset, offset + 1, Choice("hom", *HOMOGLYPH_PAIRS[text[offset]])))
        cursor = 0
        for start, end, choice in sorted(edits, key=lambda edit: (edit[0], edit[1])):
            if start > cursor:
                nodes.append(Literal(text[cursor:start]))
            nodes.append(choice)
            cursor = end
        if cursor < len(text):
            nodes.append(Literal(text[cursor:]))
    return Template(tuple(nodes))


def prepare_master(source: str, key: bytes) -> PreparedMaster:
    """Parse front matter and body, insert declared auto slots, then allocate keys."""
    settings, body = split_front_matter(source)
    counts = _counts(settings)
    template = parse_template(body)
    if any(counts.values()):
        template = insert_auto_slots(template, key, counts)
    return PreparedMaster(template, allocate_slots(template, key), counts)


def master_title(source: str) -> str | None:
    """Return the optional front-matter title of a master."""
    title = split_front_matter(source)[0].get("title")
    return title.strip() if isinstance(title, str) and title.strip() else None
