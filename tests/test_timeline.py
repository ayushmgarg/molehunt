"""Tests for merged synthetic event timelines."""

import pytest

from molehunt.game.timeline import load_timeline


def test_timeline_merges_sources_in_utc_order(tmp_path) -> None:
    early = tmp_path / "badge.csv"
    early.write_text(
        "timestamp,employee_id,event,device_id\n"
        "2025-01-01T09:00:00+00:00,E001,badge_entry,D-1\n",
        encoding="utf-8",
    )
    late = tmp_path / "print.csv"
    late.write_text(
        "timestamp,employee_id,event,device_id,printer_id\n"
        "2025-01-01T10:00:00Z,E001,print_job,PRN-4,4\n",
        encoding="utf-8",
    )

    events = load_timeline((late, early))

    assert [event.event for event in events] == ["badge_entry", "print_job"]
    assert events[0].timestamp.isoformat() == "2025-01-01T09:00:00+00:00"
    assert events[1].printer_id == "4"
    assert events[1].source == "print.csv"


def test_timeline_treats_naive_timestamps_as_utc(tmp_path) -> None:
    source = tmp_path / "events.csv"
    source.write_text(
        "ts,employee_id,action\n2025-02-03 12:30:00,E002,open\n",
        encoding="utf-8",
    )

    event = load_timeline((source,))[0]

    assert event.timestamp.isoformat() == "2025-02-03T12:30:00+00:00"
    assert event.event == "open"


@pytest.mark.parametrize(
    "content",
    [
        "employee_id,event\nE001,print_job\n",
        "timestamp,employee_id,event\nnot-a-date,E001,print_job\n",
        "timestamp,event\n2025-01-01T00:00:00Z,print_job\n",
    ],
)
def test_timeline_rejects_missing_or_invalid_required_fields(tmp_path, content) -> None:
    source = tmp_path / "bad.csv"
    source.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError):
        load_timeline((source,))
