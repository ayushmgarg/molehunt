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
