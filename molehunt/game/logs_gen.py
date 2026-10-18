"""Generate synthetic rosters and Poisson-style background log events.

Roster: names are built from two invented syllable lists, so no real person's
data is used. Each employee gets a department and role from small fixed lists.

Background events: for each employee and day, the number of events is drawn as
a Poisson process (exponential gaps, rate ``daily_rate`` per working day between
08:00 and 18:00 UTC). Each event is one of open, download, print_job,
badge_entry, badge_exit, or login with a synthetic device and private IP. All
randomness comes from the ``random.Random`` passed in.
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

_FIRST = ("Avo", "Bel", "Cai", "Dre", "Eli", "Fen", "Gai", "Hal", "Iro", "Jas", "Kev",
          "Lio", "Mar", "Nev", "Ori", "Pel", "Qui", "Ras", "Sol", "Tav", "Ulo", "Vey")
_SECOND = ("ran", "dor", "lin", "mas", "nis", "ric", "sel", "ten", "vik", "wen", "zar", "bel")
_LAST = ("Ashcombe", "Brightley", "Corran", "Dunmere", "Elstow", "Farrow", "Greyholt",
         "Harlowe", "Ivesby", "Kettering", "Lowden", "Marsh", "Northam", "Oakridge",
         "Pellow", "Quarry", "Rendle", "Stanway", "Thorne", "Underhill", "Vance", "Wyle")
_DEPTS = ("Engineering", "Finance", "Legal", "Operations", "Product", "Sales", "Security")
_ROLES = ("Analyst", "Engineer", "Manager", "Specialist", "Lead", "Associate")
EVENT_KINDS = ("open", "download", "print_job", "badge_entry", "badge_exit", "login")


@dataclass(frozen=True, slots=True)
class Employee:
    """One synthetic staff record."""

    id: str
    name: str
    dept: str
    role: str


@dataclass(frozen=True, slots=True)
class LogEvent:
    """One timestamped synthetic log row."""

    timestamp: datetime
    employee_id: str
    event: str
    device_id: str
    ip: str


def synthetic_roster(count: int, seed: int) -> list[Employee]:
    """Return ``count`` employees E001.. with unique invented names."""
    if count < 1:
        raise ValueError("roster count must be positive")
    rng = random.Random(seed)
    names: set[str] = set()
    roster = []
    for index in range(1, count + 1):
        while True:
            name = f"{rng.choice(_FIRST)}{rng.choice(_SECOND)} {rng.choice(_LAST)}"
            if name not in names:
                names.add(name)
                break
        roster.append(Employee(f"E{index:03}", name, rng.choice(_DEPTS), rng.choice(_ROLES)))
    return roster


def write_roster_csv(path: str | Path, roster: list[Employee]) -> Path:
    """Write id, name, dept, role rows."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["id", "name", "dept", "role"])
        writer.writerows((item.id, item.name, item.dept, item.role) for item in roster)
    return target


def device_for(employee_id: str) -> str:
    """Deterministic workstation id for an employee (synthetic)."""
    return f"WS-{employee_id}"


def ip_for(employee_id: str) -> str:
    """Deterministic office IP for an employee (RFC 1918 range)."""
    number = int("".join(ch for ch in employee_id if ch.isdigit()) or "0")
    return f"10.20.{number // 250}.{number % 250 + 1}"


def background_events(
    employee_ids: list[str],
    start: datetime,
    *,
    days: int,
    rng: random.Random,
    daily_rate: float = 2.0,
) -> list[LogEvent]:
    """Draw Poisson-style office-hours events for every employee and day."""
    if days < 1 or daily_rate <= 0:
        raise ValueError("days and daily_rate must be positive")
    window = 10 * 60.0
    events = []
    for day in range(days):
        office_open = start + timedelta(days=day, hours=8)
        for employee_id in employee_ids:
            minute = rng.expovariate(daily_rate / window)
            while minute < window:
                events.append(
                    LogEvent(
                        office_open + timedelta(minutes=round(minute, 2)),
                        employee_id,
                        rng.choice(EVENT_KINDS),
                        device_for(employee_id),
                        ip_for(employee_id),
                    )
                )
                minute += rng.expovariate(daily_rate / window)
    return sorted(events, key=lambda item: (item.timestamp, item.employee_id, item.event))


def write_events_csv(path: str | Path, events: list[LogEvent]) -> Path:
    """Write timestamp, employee_id, event, device_id, ip rows."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["timestamp", "employee_id", "event", "device_id", "ip"])
        writer.writerows(
            (item.timestamp.isoformat(timespec="seconds"), item.employee_id, item.event,
             item.device_id, item.ip)
            for item in events
        )
    return target
