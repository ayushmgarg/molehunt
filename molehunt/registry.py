"""Persist masters, keyed slots, synthetic employees, copies, and cases in SQLite."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from molehunt.core.slots import Slot

_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS masters (
    id TEXT PRIMARY KEY, title TEXT NOT NULL, template_path TEXT NOT NULL,
    n_slots INTEGER NOT NULL CHECK (n_slots >= 0), sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS slots (
    master_id TEXT NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL, source_index INTEGER NOT NULL, channel TEXT NOT NULL,
    variant_a TEXT NOT NULL, variant_b TEXT NOT NULL, anchor_hash TEXT NOT NULL,
    anchor_ctx TEXT NOT NULL, PRIMARY KEY (master_id, idx),
    UNIQUE (master_id, source_index)
);
CREATE TABLE IF NOT EXISTS employees (
    id TEXT PRIMARY KEY, name TEXT NOT NULL DEFAULT 'Synthetic employee',
    dept TEXT NOT NULL DEFAULT 'Synthetic department',
    role TEXT NOT NULL DEFAULT 'Synthetic role'
);
CREATE TABLE IF NOT EXISTS copies (
    copy_id TEXT PRIMARY KEY, master_id TEXT NOT NULL REFERENCES masters(id),
    employee_id TEXT NOT NULL REFERENCES employees(id), issued_at TEXT NOT NULL,
    format TEXT NOT NULL, sha256 TEXT NOT NULL, path TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL,
    employee_id TEXT REFERENCES employees(id), action TEXT NOT NULL,
    device_id TEXT, ip TEXT, copy_id TEXT REFERENCES copies(copy_id)
);
CREATE TABLE IF NOT EXISTS aux_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL,
    path TEXT NOT NULL, sha256 TEXT NOT NULL, imported_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY, case_id TEXT NOT NULL, path TEXT NOT NULL,
    sha256 TEXT NOT NULL, intake_ts TEXT NOT NULL, working_copy_path TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS custody_log (
    seq INTEGER PRIMARY KEY, ts TEXT NOT NULL, actor TEXT NOT NULL,
    action TEXT NOT NULL, object_sha256 TEXT NOT NULL, details TEXT NOT NULL,
    prev_hash TEXT NOT NULL, entry_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY, player_id TEXT NOT NULL, seed INTEGER NOT NULL,
    status TEXT NOT NULL, score INTEGER NOT NULL DEFAULT 0,
    hints_used INTEGER NOT NULL DEFAULT 0, started_at TEXT NOT NULL, finished_at TEXT
);
CREATE TABLE IF NOT EXISTS progress (
    player_id TEXT NOT NULL, case_id TEXT NOT NULL REFERENCES cases(case_id),
    status TEXT NOT NULL, unlocked_tools_json TEXT NOT NULL DEFAULT '[]',
    score INTEGER NOT NULL DEFAULT 0, hints_used INTEGER NOT NULL DEFAULT 0,
    started_at TEXT, finished_at TEXT,
    PRIMARY KEY (player_id, case_id)
);
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL REFERENCES cases(case_id),
    player_id TEXT NOT NULL, answers_json TEXT NOT NULL,
    correct INTEGER NOT NULL CHECK (correct IN (0, 1)), submitted_at TEXT NOT NULL
);
"""


def _connect(path: str | Path) -> sqlite3.Connection:
    """Open a row-aware SQLite connection with foreign-key checks enabled."""
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(path: str | Path) -> Path:
    """Create the project registry tables idempotently and return its path."""
    database = Path(path)
    database.parent.mkdir(parents=True, exist_ok=True)
    with _connect(database) as connection:
        connection.executescript(_SCHEMA)
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_meta "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        progress_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(progress)")
        }
        for name, definition in (
            ("score", "INTEGER NOT NULL DEFAULT 0"),
            ("hints_used", "INTEGER NOT NULL DEFAULT 0"),
            ("started_at", "TEXT"),
            ("finished_at", "TEXT"),
        ):
            if name not in progress_columns:
                connection.execute(f"ALTER TABLE progress ADD COLUMN {name} {definition}")
        connection.execute(
            "INSERT OR IGNORE INTO schema_meta(version, applied_at) VALUES (?, ?)",
            (2, datetime.now(UTC).isoformat(timespec="seconds")),
        )
    return database


def register_master(
    database: str | Path,
    master_id: str,
    title: str,
    template_path: str | Path,
    source: str,
    slots: Sequence[Slot],
) -> None:
    """Store the master digest and keyed slot map in one SQLite transaction."""
    if not master_id.strip() or not title.strip():
        raise ValueError("master ID and title must not be empty")
    target = Path(template_path).resolve()
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    created_at = datetime.now(UTC).isoformat(timespec="seconds")
    with _connect(database) as connection:
        connection.execute(
            "INSERT INTO masters(id, title, template_path, n_slots, sha256, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (master_id.strip(), title.strip(), str(target), len(slots), digest, created_at),
        )
        connection.executemany(
            "INSERT INTO slots(master_id, idx, source_index, channel, variant_a, variant_b, "
            "anchor_hash, anchor_ctx) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    master_id.strip(), slot.index, slot.source_index, slot.channel,
                    slot.zero, slot.one,
                    hashlib.sha256(
                        f"{slot.anchor_before}\0{slot.anchor_after}".encode()
                    ).hexdigest(),
                    json.dumps(
                        {"before": slot.anchor_before, "after": slot.anchor_after},
                        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                    ),
                )
                for slot in slots
            ],
        )


def get_master(database: str | Path, master_id: str) -> sqlite3.Row | None:
    """Return one registered master row, or None when it is unknown."""
    with _connect(database) as connection:
        return connection.execute("SELECT * FROM masters WHERE id = ?", (master_id,)).fetchone()


def get_master_by_path(database: str | Path, template_path: str | Path) -> sqlite3.Row | None:
    """Return a master registered from the same resolved template path."""
    resolved = str(Path(template_path).resolve())
    with _connect(database) as connection:
        return connection.execute(
            "SELECT * FROM masters WHERE template_path = ?", (resolved,)
        ).fetchone()


def add_employee(
    database: str | Path,
    employee_id: str,
    *,
    name: str = "Synthetic employee",
    dept: str = "Synthetic department",
    role: str = "Synthetic role",
) -> None:
    """Register synthetic employee metadata without real-person defaults."""
    if not employee_id.strip():
        raise ValueError("employee ID must not be empty")
    with _connect(database) as connection:
        connection.execute(
            "INSERT OR IGNORE INTO employees(id, name, dept, role) VALUES (?, ?, ?, ?)",
            (employee_id.strip(), name, dept, role),
        )


def record_copy(
    database: str | Path,
    master_id: str,
    employee_id: str,
    output_path: str | Path,
) -> str:
    """Record an issued copy by UUID, output format, SHA-256, and destination."""
    output = Path(output_path)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    copy_id = str(uuid.uuid4())
    with _connect(database) as connection:
        connection.execute(
            "INSERT INTO copies(copy_id, master_id, employee_id, issued_at, format, sha256, path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                copy_id, master_id, employee_id,
                datetime.now(UTC).isoformat(timespec="seconds"),
                output.suffix.lower().lstrip("."), digest, str(output.resolve()),
            ),
        )
    return copy_id


def record_evidence(
    database: str | Path,
    case_id: str,
    original_path: str | Path,
    working_copy_path: str | Path,
    sha256: str,
) -> str:
    """Store evidence identity, immutable source location, and working-copy path."""
    if not case_id.strip() or len(sha256) != 64:
        raise ValueError("case ID and a 64-character SHA-256 are required")
    evidence_id = str(uuid.uuid4())
    with _connect(database) as connection:
        connection.execute(
            "INSERT INTO evidence(id, case_id, path, sha256, intake_ts, working_copy_path) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                evidence_id, case_id.strip(), str(Path(original_path).resolve()), sha256,
                datetime.now(UTC).isoformat(timespec="seconds"),
                str(Path(working_copy_path).resolve()),
            ),
        )
    return evidence_id


def record_custody_entry(database: str | Path, entry: dict[str, object]) -> None:
    """Mirror a verified JSONL custody event into the SQLite registry."""
    required = (
        "seq", "ts", "actor", "action", "object_sha256", "details", "prev_hash", "entry_hash"
    )
    if any(field not in entry for field in required):
        raise ValueError("custody entry is missing required chain fields")
    with _connect(database) as connection:
        connection.execute(
            "INSERT INTO custody_log(seq, ts, actor, action, object_sha256, details, "
            "prev_hash, entry_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            tuple(entry[field] for field in required),
        )
