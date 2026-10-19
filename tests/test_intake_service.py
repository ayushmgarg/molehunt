"""Tests for filesystem intake synchronized with registry references."""

import hashlib
import sqlite3
from pathlib import Path

from molehunt.intake_service import intake_case


def test_intake_case_persists_matching_evidence_and_custody_records(tmp_path: Path) -> None:
    source = tmp_path / "leak.txt"
    source.write_text("synthetic evidence", encoding="utf-8")
    database = tmp_path / "registry.sqlite3"
    result = intake_case(
        source,
        "CASE-01",
        actor="examiner-01",
        root=tmp_path / "cases",
        database=database,
    )
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert result.intake.sha256 == digest
    with sqlite3.connect(database) as connection:
        evidence = connection.execute(
            "SELECT case_id, path, sha256, working_copy_path FROM evidence WHERE id = ?",
            (result.evidence_id,),
        ).fetchone()
        custody = connection.execute(
            "SELECT seq, actor, action, object_sha256, entry_hash FROM custody_log"
        ).fetchone()
    assert evidence == (
        "CASE-01", str(result.intake.original.resolve()), digest,
        str(result.intake.working_copy.resolve()),
    )
    assert custody == (1, "examiner-01", "intake", digest, result.intake.custody_entry["entry_hash"])


def test_second_and_later_intakes_share_one_registry(tmp_path) -> None:
    import sqlite3

    from molehunt.intake_service import intake_case

    database = tmp_path / "registry.sqlite3"
    for number in (1, 2, 3):
        source = tmp_path / f"leak{number}.txt"
        source.write_text(f"leak {number}", encoding="utf-8")
        intake_case(source, f"C-{number}", actor="EX-01", root=tmp_path / "evidence",
                    database=database)
    with sqlite3.connect(database) as connection:
        rows = connection.execute("SELECT seq FROM custody_log").fetchall()
    assert rows == [(1,), (1,), (1,)]


def test_old_registry_is_migrated_without_losing_custody_rows(tmp_path) -> None:
    import sqlite3

    from molehunt.registry import initialize_database

    database = tmp_path / "old.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE custody_log (seq INTEGER PRIMARY KEY, ts TEXT NOT NULL, actor TEXT "
            "NOT NULL, action TEXT NOT NULL, object_sha256 TEXT NOT NULL, details TEXT NOT "
            "NULL, prev_hash TEXT NOT NULL, entry_hash TEXT NOT NULL)")
        connection.execute("INSERT INTO custody_log VALUES (1,'t','a','intake','h','d','p','e')")
    initialize_database(database)
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT ledger, seq, action FROM custody_log").fetchall() == [
            ("default", 1, "intake")]
