"""Read a small, explicit CSV schema for log-to-fingerprint fusion."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from molehunt.detect.fuse import ACCESS_PRIORS, EVENT_FACTORS


@dataclass(frozen=True, slots=True)
class LogEvidence:
    """Consolidated access level and unique named events for each employee."""

    access: dict[str, str]
    events: dict[str, tuple[str, ...]]


def read_fusion_logs(
    path: str | Path, candidate_ids: set[str] | None = None
) -> LogEvidence:
    """Read employee_id, access_level, event rows and consolidate repeated events."""
    access_rank = {"none": 0, "indirect": 1, "direct": 2}
    access: dict[str, str] = {}
    events: dict[str, set[str]] = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not {"employee_id", "access_level"} <= set(reader.fieldnames):
            raise ValueError("log CSV must have employee_id and access_level columns")
        if "event" not in reader.fieldnames:
            raise ValueError("log CSV must have an event column (leave it empty when unused)")
        for row_number, row in enumerate(reader, start=2):
            employee_id = (row.get("employee_id") or "").strip()
            access_level = (row.get("access_level") or "").strip().casefold()
            event = (row.get("event") or "").strip().casefold()
            if not employee_id:
                raise ValueError(f"log CSV row {row_number} has an empty employee_id")
            if candidate_ids is not None and employee_id not in candidate_ids:
                raise ValueError(f"log CSV row {row_number} names unknown candidate {employee_id}")
            if access_level not in ACCESS_PRIORS:
                raise ValueError(f"log CSV row {row_number} has invalid access_level {access_level!r}")
            if event and event not in EVENT_FACTORS:
                raise ValueError(f"log CSV row {row_number} has unknown event {event!r}")
            previous = access.get(employee_id, "none")
            if access_rank[access_level] > access_rank[previous]:
                access[employee_id] = access_level
            else:
                access.setdefault(employee_id, previous)
            if event:
                events.setdefault(employee_id, set()).add(event)
    if not access:
        raise ValueError("log CSV contains no data rows")
    return LogEvidence(
        access=access,
        events={employee_id: tuple(sorted(items)) for employee_id, items in events.items()},
    )
