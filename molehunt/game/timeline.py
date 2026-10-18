"""Read timestamped synthetic event CSVs and merge them into one UTC timeline."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    """One normalized event from an input log source."""

    timestamp: datetime
    employee_id: str
    event: str
    device_id: str
    printer_id: str
    source: str


def _timestamp(value: str, source: Path, row_number: int) -> datetime:
    """Parse ISO timestamps and normalize naive values as UTC."""
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError as error:
        raise ValueError(f"invalid timestamp in {source.name} row {row_number}") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def load_timeline(paths: Iterable[str | Path]) -> tuple[TimelineEvent, ...]:
    """Merge CSV rows and sort by UTC timestamp with stable tie-break fields."""
    events: list[TimelineEvent] = []
    for value in paths:
        source = Path(value)
        with source.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            fields = set(reader.fieldnames or ())
            timestamp_field = "timestamp" if "timestamp" in fields else "ts"
            event_field = "event" if "event" in fields else "action"
            required = {timestamp_field, event_field, "employee_id"}
            if not fields or not required <= fields:
                raise ValueError(
                    f"{source.name} needs timestamp, employee_id, and event/action columns"
                )
            for row_number, row in enumerate(reader, start=2):
                employee_id = (row.get("employee_id") or "").strip()
                event_name = (row.get(event_field) or "").strip()
                stamp = (row.get(timestamp_field) or "").strip()
                if not employee_id or not event_name or not stamp:
                    raise ValueError(f"empty required field in {source.name} row {row_number}")
                events.append(
                    TimelineEvent(
                        timestamp=_timestamp(stamp, source, row_number),
                        employee_id=employee_id,
                        event=event_name,
                        device_id=(row.get("device_id") or row.get("device") or "").strip(),
                        printer_id=(row.get("printer_id") or "").strip(),
                        source=source.name,
                    )
                )
    return tuple(
        sorted(events, key=lambda item: (item.timestamp, item.source, item.employee_id, item.event))
    )
