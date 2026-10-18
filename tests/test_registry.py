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
