"""Tests for SQLite registry schema, master slots, employees, and copies."""

import hashlib
import sqlite3

import pytest

from molehunt.core.slots import allocate_slots
from molehunt.core.template import parse_template
from molehunt.registry import (
    add_employee,
    get_master,
    get_master_by_path,
    initialize_database,
    record_copy,
    record_custody_entry,
    record_evidence,
    register_master,
)


def test_initialize_registry_is_idempotent_and_creates_domain_tables(tmp_path) -> None:
    database = tmp_path / "state" / "molehunt.sqlite3"
    initialize_database(database)
    initialize_database(database)
    with sqlite3.connect(database) as connection:
        names = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    assert {"masters", "slots", "employees", "copies", "evidence", "custody_log"} <= names
    assert {"cases", "progress", "submissions", "access_log", "aux_logs"} <= names
    with sqlite3.connect(database) as connection:
        progress_columns = {row[1] for row in connection.execute("PRAGMA table_info(progress)")}
        versions = {row[0] for row in connection.execute("SELECT version FROM schema_meta")}
    assert {"score", "hints_used", "started_at", "finished_at"} <= progress_columns
    assert versions == {2}


def test_initialize_database_migrates_existing_progress_rows(tmp_path) -> None:
    database = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            "CREATE TABLE cases (case_id TEXT PRIMARY KEY, player_id TEXT NOT NULL, "
            "seed INTEGER NOT NULL, status TEXT NOT NULL, score INTEGER NOT NULL DEFAULT 0, "
            "hints_used INTEGER NOT NULL DEFAULT 0, started_at TEXT NOT NULL, finished_at TEXT);"
            "CREATE TABLE progress (player_id TEXT NOT NULL, case_id TEXT NOT NULL, "
            "status TEXT NOT NULL, unlocked_tools_json TEXT NOT NULL DEFAULT '[]', "
            "PRIMARY KEY(player_id, case_id));"
            "INSERT INTO cases VALUES ('C-01','legacy',1,'done',0,0,'now',NULL);"
            "INSERT INTO progress VALUES ('legacy','C-01','complete','[]');"
        )
    initialize_database(database)
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT status, score, hints_used, started_at, finished_at FROM progress"
        ).fetchone()
    assert row == ("complete", 0, 0, None, None)


def test_registered_master_slots_and_copy_hash_are_persisted(tmp_path) -> None:
    database = initialize_database(tmp_path / "registry.sqlite3")
    source = "A {{lex:begin|start}} record. B {{pun:,|}} end."
    template_path = tmp_path / "master.md"
    template_path.write_text(source, encoding="utf-8")
    slots = allocate_slots(parse_template(source), bytes(range(32)))

    register_master(database, "M-01", "Demo master", template_path, source, slots)
    master = get_master(database, "M-01")
    assert get_master_by_path(database, template_path)["id"] == "M-01"
    assert master["n_slots"] == 2
    assert master["sha256"] == hashlib.sha256(source.encode()).hexdigest()
    with sqlite3.connect(database) as connection:
        stored_slots = connection.execute(
            "SELECT idx, channel, variant_a, variant_b, anchor_hash FROM slots "
            "WHERE master_id = ? ORDER BY idx",
            ("M-01",),
        ).fetchall()
    assert len(stored_slots) == 2
    assert all(len(row[4]) == 64 for row in stored_slots)

    add_employee(database, "E001")
    copy = tmp_path / "copy.txt"
    copy.write_bytes(b"synthetic copy")
    copy_id = record_copy(database, "M-01", "E001", copy)
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT format, sha256, path FROM copies WHERE copy_id = ?", (copy_id,)
        ).fetchone()
    assert row == (
        "txt",
        hashlib.sha256(copy.read_bytes()).hexdigest(),
        str(copy.resolve()),
    )


def test_master_registration_rolls_back_on_duplicate_id(tmp_path) -> None:
    database = initialize_database(tmp_path / "registry.sqlite3")
    source = "{{lex:left|right}}"
    slots = allocate_slots(parse_template(source), bytes(range(32)))
    register_master(database, "M-01", "Master", tmp_path / "master.md", source, slots)
    with pytest.raises(sqlite3.IntegrityError):
        register_master(database, "M-01", "Duplicate", tmp_path / "other.md", source, slots)
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM masters").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM slots").fetchone()[0] == 1


def test_evidence_and_custody_metadata_are_persisted(tmp_path) -> None:
    database = initialize_database(tmp_path / "registry.sqlite3")
    original = tmp_path / "original.txt"
    working = tmp_path / "working.txt"
    original.write_text("synthetic evidence", encoding="utf-8")
    working.write_bytes(original.read_bytes())
    digest = hashlib.sha256(original.read_bytes()).hexdigest()
    evidence_id = record_evidence(database, "CASE-01", original, working, digest)
    entry = {
        "seq": 1,
        "ts": "2026-10-18T00:00:00Z",
        "actor": "examiner-01",
        "action": "intake",
        "object_sha256": digest,
        "details": "original/original.txt",
        "prev_hash": "0" * 64,
        "entry_hash": "1" * 64,
    }
    record_custody_entry(database, entry)
    with sqlite3.connect(database) as connection:
        evidence = connection.execute(
            "SELECT case_id, path, sha256, working_copy_path FROM evidence WHERE id = ?",
            (evidence_id,),
        ).fetchone()
        custody = connection.execute(
            "SELECT seq, actor, action, object_sha256, prev_hash, entry_hash FROM custody_log"
        ).fetchone()
    assert evidence == ("CASE-01", str(original.resolve()), digest, str(working.resolve()))
    assert custody == (1, "examiner-01", "intake", digest, "0" * 64, "1" * 64)


def test_custody_registry_rejects_missing_chain_fields(tmp_path) -> None:
    database = initialize_database(tmp_path / "registry.sqlite3")
    with pytest.raises(ValueError, match="required chain fields"):
        record_custody_entry(database, {"seq": 1})
