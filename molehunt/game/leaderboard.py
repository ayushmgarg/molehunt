"""Record Section 10 graded submissions and rank players.

Rules: a correct submission with total >= 60 completes the case (advance); the
third wrong submission closes it with partial credit; either way the next case
unlocks with the tools earned so far. Leaderboard = sum of case scores.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from molehunt.game.casebook import CaseDefinition
from molehunt.game.progression import _connect, _definitions, _now
from molehunt.game.validator import ADVANCE_POINTS, MAX_WRONG, CaseScore


def record_graded(
    database: str | Path,
    player_id: str,
    definitions: tuple[CaseDefinition, ...],
    case_id: str,
    score: CaseScore,
    answers: dict,
) -> str:
    """Store a Section 10 graded submission; return the new case status.

    complete: correct and total >= 60 (advance). closed: third wrong submission,
    partial credit kept. Either way the next case unlocks with earned tools.
    """
    by_id = _definitions(definitions)
    if case_id not in by_id:
        raise ValueError(f"unknown case ID: {case_id}")
    with _connect(database) as connection:
        row = connection.execute(
            "SELECT status FROM progress WHERE player_id = ? AND case_id = ?",
            (player_id, case_id),
        ).fetchone()
        if row is None or row["status"] != "in_progress":
            raise ValueError("case must be in progress before submitting an answer")
        wrong_before = connection.execute(
            "SELECT COUNT(*) FROM submissions WHERE player_id = ? AND case_id = ? AND correct = 0",
            (player_id, case_id),
        ).fetchone()[0]
        payload = json.dumps({**answers, "score": asdict(score)}, sort_keys=True, default=str)
        connection.execute(
            "INSERT INTO submissions(case_id, player_id, answers_json, correct, submitted_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (case_id, player_id, payload, int(score.correct), _now()),
        )
        if score.correct and score.total >= ADVANCE_POINTS:
            status = "complete"
        elif not score.correct and wrong_before + 1 >= MAX_WRONG:
            status = "closed"
        else:
            return "in_progress"
        connection.execute(
            "UPDATE progress SET status = ?, score = ?, finished_at = ? "
            "WHERE player_id = ? AND case_id = ?",
            (status, score.total, _now(), player_id, case_id),
        )
        index = next(i for i, item in enumerate(definitions) if item.case_id == case_id)
        if index + 1 < len(definitions):
            earned = set(json.loads(connection.execute(
                "SELECT unlocked_tools_json FROM progress WHERE player_id = ? AND case_id = ?",
                (player_id, case_id),
            ).fetchone()[0])) | set(by_id[case_id].tools)
            following = definitions[index + 1]
            connection.execute(
                "UPDATE progress SET status = 'available', unlocked_tools_json = ? "
                "WHERE player_id = ? AND case_id = ? AND status = 'locked'",
                (json.dumps(sorted(earned | set(following.tools))), player_id, following.case_id),
            )
    return status


def leaderboard(database: str | Path) -> list[tuple[str, int, int]]:
    """(player, total points, cases finished) sorted by points, then finished cases."""
    with _connect(database) as connection:
        rows = connection.execute(
            "SELECT player_id, SUM(score), SUM(status IN ('complete', 'closed')) "
            "FROM progress GROUP BY player_id"
        ).fetchall()
    return sorted(((r[0], int(r[1] or 0), int(r[2] or 0)) for r in rows),
                  key=lambda item: (-item[1], -item[2], item[0]))
