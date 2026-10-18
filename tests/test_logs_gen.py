"""Tests for synthetic roster and background log generation."""

import csv
import random
from datetime import UTC, datetime

from molehunt.game.logs_gen import (
    background_events,
    synthetic_roster,
    write_events_csv,
    write_roster_csv,
)
from molehunt.game.timeline import load_timeline


def test_roster_is_seeded_unique_and_synthetic(tmp_path) -> None:
    first = synthetic_roster(50, seed=3)
    assert first == synthetic_roster(50, seed=3)
    assert first != synthetic_roster(50, seed=4)
    assert [person.id for person in first] == [f"E{index:03}" for index in range(1, 51)]
    assert len({person.name for person in first}) == 50
    assert all(person.dept and person.role for person in first)
    path = write_roster_csv(tmp_path / "roster.csv", first)
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0].keys() == {"id", "name", "dept", "role"}
    assert len(rows) == 50


def test_background_events_are_seeded_sorted_and_loadable(tmp_path) -> None:
    roster = [person.id for person in synthetic_roster(12, seed=1)]
    start = datetime(2025, 3, 3, tzinfo=UTC)
    events = background_events(roster, start, days=5, rng=random.Random(9), daily_rate=3.0)
    assert events == background_events(roster, start, days=5, rng=random.Random(9), daily_rate=3.0)
    assert len(events) > 50
    assert [event.timestamp for event in events] == sorted(event.timestamp for event in events)
    assert all(start <= event.timestamp < datetime(2025, 3, 8, tzinfo=UTC) for event in events)
    assert {event.employee_id for event in events} <= set(roster)
    path = write_events_csv(tmp_path / "access.csv", events)
    loaded = load_timeline([path])
    assert len(loaded) == len(events)
