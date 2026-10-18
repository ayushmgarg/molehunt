"""Tests for case locks, hints, calibrated submissions, and tool unlocks."""

import json
import sqlite3

import pytest

from molehunt.game.casebook import load_casebook
from molehunt.game.progression import (
    get_case_progress,
    initialize_casebook,
    start_case,
    submit_answer,
    use_hint,
)


def test_cases_unlock_in_order_and_hints_are_limited(tmp_path) -> None:
    database = tmp_path / "registry.sqlite3"
    cases = load_casebook()
    initialize_casebook(database, "player-01", cases)
    progress = get_case_progress(database, "player-01")
    assert progress[0].status == "available"
    assert all(item.status == "locked" for item in progress[1:])
    with pytest.raises(ValueError, match="locked"):
        start_case(database, "player-01", "C-02", cases)

    current = start_case(database, "player-01", "C-01", cases)
    assert current.status == "in_progress"
    assert {"intake", "hex", "invisible", "notes", "report"} <= set(current.unlocked_tools)
    assert use_hint(database, "player-01", cases[0]) == cases[0].hints[0]
    assert use_hint(database, "player-01", cases[0]) == cases[0].hints[1]
    assert use_hint(database, "player-01", cases[0]) == cases[0].hints[2]
    with pytest.raises(ValueError, match="all hints"):
        use_hint(database, "player-01", cases[0])


def test_submissions_use_generated_truth_boolean_and_unlock_next_case(tmp_path) -> None:
    database = tmp_path / "registry.sqlite3"
    cases = load_casebook()
    initialize_casebook(database, "player-01", cases)
    start_case(database, "player-01", "C-01", cases)
    wrong = submit_answer(
        database, "player-01", cases, "C-01",
        answer="E002", correct=False, confidence=0.9,
    )
    assert not wrong.grade.correct
    assert wrong.grade.brier_score == pytest.approx(0.81)
    assert wrong.points == 19
    assert not wrong.completed
    with pytest.raises(ValueError, match="locked"):
        start_case(database, "player-01", "C-02", cases)

    correct = submit_answer(
        database, "player-01", cases, "C-01",
        answer="E001", correct=True, confidence=0.8,
    )
    assert correct.grade.correct
    assert correct.completed
    assert correct.points == 86  # 96 base points minus the second-attempt penalty.
    progress = get_case_progress(database, "player-01")
    assert progress[0].status == "complete"
    assert progress[0].score == 86
    assert progress[1].status == "available"
    assert {"diff", "slot_matrix", "intake"} <= set(progress[1].unlocked_tools)
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT answers_json, correct FROM submissions ORDER BY id DESC LIMIT 1"
        ).fetchone()
    answer_record = json.loads(row[0])
    assert answer_record["answer"] == "E001"
    assert answer_record["brier_score"] == pytest.approx(0.04)
    assert row[1] == 1


def test_case_progress_is_independent_between_players(tmp_path) -> None:
    database = tmp_path / "registry.sqlite3"
    cases = load_casebook()
    initialize_casebook(database, "player-01", cases)
    initialize_casebook(database, "player-02", cases)
    start_case(database, "player-01", "C-01", cases)
    assert get_case_progress(database, "player-01")[0].status == "in_progress"
    assert get_case_progress(database, "player-02")[0].status == "available"
