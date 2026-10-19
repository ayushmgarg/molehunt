"""Coordinate filesystem evidence staging with SQLite registry records."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from molehunt.intake import IntakeResult, intake_evidence
from molehunt.registry import (
    initialize_database,
    record_custody_entry,
    record_evidence,
)


@dataclass(frozen=True, slots=True)
class RegisteredIntake:
    """Staged evidence plus its persistent registry identity."""

    intake: IntakeResult
    evidence_id: str


def intake_case(
    source: str | Path,
    case_id: str,
    *,
    actor: str,
    root: str | Path,
    database: str | Path,
) -> RegisteredIntake:
    """Stage original/working files and persist evidence and custody metadata."""
    initialize_database(database)
    result = intake_evidence(source, case_id, actor=actor, root=root)
    evidence_id = record_evidence(
        database, case_id, result.original, result.working_copy, result.sha256
    )
    record_custody_entry(database, result.custody_entry, ledger=str(result.custody_log))
    return RegisteredIntake(result, evidence_id)
