"""Player-side helpers: read slots in reading order and match an issuance registry.

``document_order_bits`` aligns a suspect text to the master and returns one value
per authored slot in reading order: 0, 1, or None (erasure). Slot order does not
need the secret key because the registry lists bits in reading order too.
``match_registry`` counts agreements over non-erased slots only (rule 13):
distance = disagreements, score = matches / observed.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from molehunt.core.slots import allocate_slots
from molehunt.core.template import Template
from molehunt.detect.align import align_to_master
from molehunt.detect.extract import extract_variants

_ORDER_KEY = bytes(32)


@dataclass(frozen=True, slots=True)
class RegistryMatch:
    """Agreement of one registry row with observed slots."""

    employee_id: str
    matches: int
    observed: int
    disagreements: int


def document_order_bits(template: Template, text: str) -> list[int | None]:
    """Observed bit per authored slot in reading order (None = erasure)."""
    slots = allocate_slots(template, _ORDER_KEY)
    found = extract_variants(text, align_to_master(template, slots, text))
    by_source = {item.source_index: item.bit for item in found}
    return [by_source[index] for index in range(len(slots))]


def read_registry(path: str | Path) -> dict[str, str]:
    """Read ``employee_id,bits`` rows."""
    with Path(path).open(encoding="utf-8", newline="") as stream:
        return {row["employee_id"]: row["bits"] for row in csv.DictReader(stream)}


def match_registry(observed: list[int | None], registry: dict[str, str]) -> list[RegistryMatch]:
    """Rank registry rows by matches over observed slots; erasures are skipped."""
    rows = []
    for employee, bits in registry.items():
        pairs = [(o, int(b)) for o, b in zip(observed, bits, strict=True) if o is not None]
        matches = sum(o == b for o, b in pairs)
        rows.append(RegistryMatch(employee, matches, len(pairs), len(pairs) - matches))
    return sorted(rows, key=lambda row: (row.disagreements, row.employee_id))
