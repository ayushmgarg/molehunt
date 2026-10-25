"""Leak family tree: a forwarded copy carries the fingerprint of every hand it passed.

Setting. The document system re-stamps a copy whenever it is forwarded (like a
mail gateway that watermarks attachments). Company -> E007 -> contractor C12 ->
press: the press copy should reveal the whole path, not only the last holder.

Layers. Each slot index i gets a keyed layer
``layer(i) = 0 if u < 0.5, 1 if u < 0.75, else 2`` with
``u = HMAC(K, "lineage", i) / 2^32``. A path p = (p0, p1, ..., p_{L-1}) uses, at a
slot of layer l, the bit of node ``p[min(l, L-1)]``. Node ids are path prefixes
(``E007``, ``E007>C12``), and a node's bits are the ordinary codeword
``HMAC(K, "cw", node_id, i)``. A direct copy (L = 1) is therefore exactly the
normal single-holder copy, so nothing changes for copies that were never forwarded.

Attribution. Every registered path becomes one candidate codeword and the usual
LR ranking runs over all of them. E007 and E007>C12 share the layer-0 half and
differ (at random) on the other half, so the true path wins by about
log10(0.85/0.15) per differing slot. Depth is capped at three hops.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from molehunt.core.codes import Codeword, generate_codeword
from molehunt.core.keys import digest

SEP = ">"
MAX_DEPTH = 3
_CUTS = (0.5, 0.75)


def layer_of(key: bytes, index: int) -> int:
    """Keyed layer (0, 1, or 2) of one codeword position."""
    u = int.from_bytes(digest(key, "lineage", index.to_bytes(8, "big"))[:4], "big") / 2**32
    return 0 if u < _CUTS[0] else 1 if u < _CUTS[1] else 2


def path_id(path: Sequence[str]) -> str:
    """Join holders into one node id, e.g. ``E007>C12``."""
    if not path or len(path) > MAX_DEPTH or any(not part or SEP in part for part in path):
        raise ValueError(f"a path needs 1-{MAX_DEPTH} non-empty holder ids without '{SEP}'")
    return SEP.join(path)


def path_codeword(key: bytes, path: Sequence[str], length: int) -> Codeword:
    """Layered codeword: layer l slots carry the bits of the l-th hop's node."""
    nodes = [generate_codeword(key, path_id(path[: depth + 1]), length)
             for depth in range(len(path))]
    return tuple(nodes[min(layer_of(key, index), len(path) - 1)][index]
                 for index in range(length))


def path_codewords(key: bytes, paths: Iterable[str], length: int) -> dict[str, Codeword]:
    """Candidate codewords for every path id."""
    return {item: path_codeword(key, item.split(SEP), length) for item in paths}


@dataclass(frozen=True, slots=True)
class LayerEvidence:
    """How well one hop of the attributed path is supported."""

    holder: str
    slots: int
    matches: int


def layer_evidence(key: bytes, path: str, observations: Sequence[int | None]
                   ) -> tuple[LayerEvidence, ...]:
    """Matches per hop: hop d is read from the slots of layer d (last hop takes the rest)."""
    hops = path.split(SEP)
    word = path_codeword(key, hops, len(observations))
    found = []
    for depth, holder in enumerate(hops):
        positions = [index for index, bit in enumerate(observations) if bit is not None
                     and min(layer_of(key, index), len(hops) - 1) == depth]
        found.append(LayerEvidence(holder, len(positions),
                                   sum(observations[index] == word[index] for index in positions)))
    return tuple(found)


def tree(paths: Iterable[str]) -> dict:
    """Nested dict of the forward graph: {holder: {forwarded-to: {...}}}."""
    root: dict = {}
    for item in sorted(paths):
        node = root
        for holder in item.split(SEP):
            node = node.setdefault(holder, {})
    return root


def tree_lines(paths: Iterable[str], highlight: str | None = None) -> list[str]:
    """Text drawing of the tree; the attributed path is marked with ``<== leak``."""
    marked = set()
    if highlight:
        hops = highlight.split(SEP)
        marked = {SEP.join(hops[: depth + 1]) for depth in range(len(hops))}
    lines = ["Company"]

    def walk(node: Mapping, prefix: str, trail: str) -> None:
        items = sorted(node.items())
        for position, (holder, children) in enumerate(items):
            last = position == len(items) - 1
            here = f"{trail}{SEP}{holder}" if trail else holder
            tag = "  <== leak" if here == highlight else " *" if here in marked else ""
            lines.append(f"{prefix}{'`-- ' if last else '|-- '}{holder}{tag}")
            walk(children, prefix + ("    " if last else "|   "), here)

    walk(tree(paths), "", "")
    return lines


class ForwardLog:
    """SQLite table of forwards: which path was created from which parent, and when."""

    def __init__(self, database: str | Path) -> None:
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS lineage (path TEXT PRIMARY KEY, "
                               "parent TEXT NOT NULL, holder TEXT NOT NULL, ts TEXT NOT NULL)")

    def forward(self, parent: str, recipient: str) -> str:
        """Record parent -> recipient and return the new path id."""
        child = path_id([*parent.split(SEP), recipient])
        with sqlite3.connect(self.database) as connection:
            connection.execute("INSERT OR IGNORE INTO lineage VALUES (?, ?, ?, ?)",
                               (child, parent, recipient,
                                datetime.now(UTC).isoformat(timespec="seconds")))
        return child

    def paths(self) -> list[str]:
        """Every forwarded path, oldest first."""
        with sqlite3.connect(self.database) as connection:
            return [row[0] for row in connection.execute("SELECT path FROM lineage ORDER BY ts")]
