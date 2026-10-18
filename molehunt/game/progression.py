"""Persist per-player case locks, hints, submissions, and earned tools."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from molehunt.game.casebook import CaseDefinition
from molehunt.game.scoring import SubmissionGrade, grade_response
from molehunt.registry import initialize_database


@dataclass(frozen=True, slots=True)
class CaseProgress:
    """One player's current state for a single case."""

    case_id: str
    status: str
    score: int
    hints_used: int
    unlocked_tools: tuple[str, ...]
    started_at: str | None
    finished_at: str | None


@dataclass(frozen=True, slots=True)
class SubmissionResult:
    """Confidence grade, attempt-adjusted points, completion, and new tools."""

    grade: SubmissionGrade
    points: int
    completed: bool
    unlocked_tools: tuple[str, ...]


def _connect(database: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _definitions(definitions: tuple[CaseDefinition, ...]) -> dict[str, CaseDefinition]:
    if not definitions:
        raise ValueError("casebook needs at least one definition")
    result = {item.case_id: item for item in definitions}
    if len(result) != len(definitions):
        raise ValueError("case IDs must be unique")
    return result


def initialize_casebook(
    database: str | Path,
    player_id: str,
    definitions: tuple[CaseDefinition, ...],
) -> None:
    """Register case catalog rows and initialize one player's ordered progress."""
    if not player_id.strip():
        raise ValueError("player ID must not be empty")
    by_id = _definitions(definitions)
    initialize_database(database)
    stamp = _now()
    with _connect(database) as connection:
        for index, definition in enumerate(definitions):
            connection.execute(
                "INSERT OR IGNORE INTO cases(case_id, player_id, seed, status, started_at) "
                "VALUES (?, 'casebook', ?, 'available', ?)",
                (definition.case_id, definition.seed_offset, stamp),
            )
            tools = definition.tools if index == 0 else ()
            initial_status = "available" if index == 0 else "locked"
            connection.execute(
                "INSERT OR IGNORE INTO progress(player_id, case_id, status, unlocked_tools_json) "
                "VALUES (?, ?, ?, ?)",
                (
                    player_id.strip(), definition.case_id, initial_status,
                    json.dumps(tools, separators=(",", ":")),
                ),
            )
        known = set(by_id)
        stored = {
            row[0]
            for row in connection.execute(
                "SELECT case_id FROM progress WHERE player_id = ?", (player_id.strip(),)
            )
        }
        if stored != known:
            raise ValueError("stored case progress does not match this casebook definition set")


def _progress(row: sqlite3.Row) -> CaseProgress:
    tools = json.loads(row["unlocked_tools_json"])
    return CaseProgress(
        row["case_id"], row["status"], row["score"], row["hints_used"],
        tuple(tools), row["started_at"], row["finished_at"],
    )


def get_case_progress(database: str | Path, player_id: str) -> tuple[CaseProgress, ...]:
    """Return a player's case progress in case-ID order."""
    with _connect(database) as connection:
        rows = connection.execute(
            "SELECT p.case_id, p.status, p.score, p.hints_used, p.unlocked_tools_json, "
            "p.started_at, p.finished_at FROM progress p JOIN cases c USING(case_id) "
            "WHERE p.player_id = ? ORDER BY c.seed, p.case_id",
            (player_id,),
        ).fetchall()
    return tuple(_progress(row) for row in rows)


def start_case(
    database: str | Path,
    player_id: str,
    case_id: str,
    definitions: tuple[CaseDefinition, ...],
) -> CaseProgress:
    """Start an available case only after the prior case is completed."""
    by_id = _definitions(definitions)
    if case_id not in by_id:
        raise ValueError(f"unknown case ID: {case_id}")
    initialize_casebook(database, player_id, definitions)
    index = next(index for index, item in enumerate(definitions) if item.case_id == case_id)
    stamp = _now()
    with _connect(database) as connection:
        row = connection.execute(
            "SELECT * FROM progress WHERE player_id = ? AND case_id = ?",
            (player_id, case_id),
        ).fetchone()
        if row["status"] == "locked" and index > 0:
            previous = connection.execute(
                "SELECT status FROM progress WHERE player_id = ? AND case_id = ?",
                (player_id, definitions[index - 1].case_id),
            ).fetchone()
            if previous is None or previous["status"] != "complete":
                raise ValueError(f"case {case_id} is locked")
            tools = set(json.loads(row["unlocked_tools_json"]))
            tools.update(definitions[index].tools)
            prior_tools = connection.execute(
                "SELECT unlocked_tools_json FROM progress WHERE player_id = ? AND case_id = ?",
                (player_id, definitions[index - 1].case_id),
            ).fetchone()
            tools.update(json.loads(prior_tools[0]))
            connection.execute(
                "UPDATE progress SET status = 'available', unlocked_tools_json = ? "
                "WHERE player_id = ? AND case_id = ?",
                (json.dumps(sorted(tools)), player_id, case_id),
            )
            row = connection.execute(
                "SELECT * FROM progress WHERE player_id = ? AND case_id = ?",
                (player_id, case_id),
            ).fetchone()
        if row["status"] == "locked":
            raise ValueError(f"case {case_id} is locked")
        if row["status"] == "complete":
            raise ValueError(f"case {case_id} is already complete")
        if row["status"] == "available":
            connection.execute(
                "UPDATE progress SET status = 'in_progress', started_at = ? "
                "WHERE player_id = ? AND case_id = ?",
                (stamp, player_id, case_id),
            )
            row = connection.execute(
                "SELECT * FROM progress WHERE player_id = ? AND case_id = ?",
                (player_id, case_id),
            ).fetchone()
    return _progress(row)


def use_hint(
    database: str | Path, player_id: str, definition: CaseDefinition
) -> str:
    """Return the next hint and increment its persisted use count."""
    with _connect(database) as connection:
        row = connection.execute(
            "SELECT status, hints_used FROM progress WHERE player_id = ? AND case_id = ?",
            (player_id, definition.case_id),
        ).fetchone()
        if row is None or row["status"] != "in_progress":
            raise ValueError("case must be in progress before using hints")
        index = row["hints_used"]
        if index >= len(definition.hints):
            raise ValueError("all hints for this case have been used")
        connection.execute(
            "UPDATE progress SET hints_used = hints_used + 1 WHERE player_id = ? AND case_id = ?",
            (player_id, definition.case_id),
        )
    return definition.hints[index]


def submit_answer(
    database: str | Path,
    player_id: str,
    definitions: tuple[CaseDefinition, ...],
    case_id: str,
    *,
    answer: str,
    correct: bool,
    confidence: float,
) -> SubmissionResult:
    """Persist a response checked against generated truth and unlock on success."""
    if not answer.strip():
        raise ValueError("answer must not be empty")
    by_id = _definitions(definitions)
    if case_id not in by_id:
        raise ValueError(f"unknown case ID: {case_id}")
    definition = by_id[case_id]
    grade = grade_response(correct, confidence)
    with _connect(database) as connection:
        progress = connection.execute(
            "SELECT status, score, hints_used FROM progress "
            "WHERE player_id = ? AND case_id = ?",
            (player_id, case_id),
        ).fetchone()
        if progress is None or progress["status"] != "in_progress":
            raise ValueError("case must be in progress before submitting an answer")
        attempts = connection.execute(
            "SELECT COUNT(*) FROM submissions WHERE player_id = ? AND case_id = ?",
            (player_id, case_id),
        ).fetchone()[0]
        penalty = attempts * 10 + progress["hints_used"] * 5
        points = max(0, grade.points - penalty)
        answers = json.dumps(
            {
                "answer": answer.strip(),
                "confidence": confidence,
                "brier_score": grade.brier_score,
                "base_points": grade.points,
                "penalty": penalty,
                "points": points,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        connection.execute(
            "INSERT INTO submissions(case_id, player_id, answers_json, correct, submitted_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (case_id, player_id, answers, int(correct), _now()),
        )
        completed = correct
        if completed:
            connection.execute(
                "UPDATE progress SET status = 'complete', score = score + ?, finished_at = ? "
                "WHERE player_id = ? AND case_id = ?",
                (points, _now(), player_id, case_id),
            )
            index = next(i for i, item in enumerate(definitions) if item.case_id == case_id)
            current_tools = set(json.loads(
                connection.execute(
                    "SELECT unlocked_tools_json FROM progress WHERE player_id = ? AND case_id = ?",
                    (player_id, case_id),
                ).fetchone()[0]
            ))
            current_tools.update(definition.tools)
            connection.execute(
                "UPDATE progress SET unlocked_tools_json = ? WHERE player_id = ? AND case_id = ?",
                (json.dumps(sorted(current_tools)), player_id, case_id),
            )
            if index + 1 < len(definitions):
                next_definition = definitions[index + 1]
                next_row = connection.execute(
                    "SELECT unlocked_tools_json FROM progress WHERE player_id = ? AND case_id = ?",
                    (player_id, next_definition.case_id),
                ).fetchone()
                next_tools = set(json.loads(next_row[0])) | current_tools | set(next_definition.tools)
                connection.execute(
                    "UPDATE progress SET status = 'available', unlocked_tools_json = ? "
                    "WHERE player_id = ? AND case_id = ? AND status = 'locked'",
                    (json.dumps(sorted(next_tools)), player_id, next_definition.case_id),
                )
        row = connection.execute(
            "SELECT unlocked_tools_json FROM progress WHERE player_id = ? AND case_id = ?",
            (player_id, case_id),
        ).fetchone()
        tools = tuple(json.loads(row[0]))
    return SubmissionResult(grade, points, completed, tools)
