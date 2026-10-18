"""Tests for the Red Team boss: utility floor, live verdict, scoring, leaderboard."""

from pathlib import Path

import pytest

from molehunt.game.redteam import (
    UTILITY_FLOOR,
    apply_tools,
    evaluate,
    record_score,
    redteam_leaderboard,
    start_session,
    utility,
)

MASTER = Path(__file__).parents[1] / "data" / "masters" / "m1_roadmap.md"


@pytest.fixture(scope="module")
def session():
    return start_session(MASTER, seed=3)


def test_untouched_copy_is_caught_with_full_utility(session) -> None:
    verdict = evaluate(session, session.copy_text)
    assert verdict.utility == 1.0
    assert verdict.outcome == "attribute" and verdict.accused == session.mole
    assert not verdict.win and verdict.score == 0


def test_invisible_scrub_keeps_utility_but_detector_still_wins(session) -> None:
    text = apply_tools(session, [("strip", 1.0), ("collapse", 1.0), ("confusables", 1.0)])
    verdict = evaluate(session, text)
    assert verdict.utility > 0.99
    assert verdict.observed_slots < verdict.baseline_slots
    assert verdict.accused == session.mole and not verdict.win
    assert verdict.score > 0


def test_heavy_truncation_drops_utility_below_floor_and_scores_zero(session) -> None:
    text = apply_tools(session, [("truncate", 0.2)])
    assert utility(session, text) < UTILITY_FLOOR
    assert evaluate(session, text).score == 0


def test_unknown_tool_is_rejected_and_leaderboard_keeps_best(session, tmp_path) -> None:
    with pytest.raises(ValueError, match="unknown tool"):
        apply_tools(session, [("shred", 1.0)])
    database = tmp_path / "r.sqlite3"
    weak = evaluate(session, session.copy_text)
    strong = evaluate(session, apply_tools(session, [("strip", 1.0)]))
    record_score(database, "mole-a", weak, [])
    record_score(database, "mole-a", strong, [("strip", 1.0)])
    record_score(database, "mole-b", weak, [])
    board = redteam_leaderboard(database)
    assert board[0][0] == "mole-a" and board[0][1] == strong.score
    assert [row[0] for row in board] == ["mole-a", "mole-b"]
