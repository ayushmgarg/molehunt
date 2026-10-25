"""Find the Mole: rounds are judged by the real forensic pipeline."""

from pathlib import Path

import pytest

from molehunt.game.mole_game import TOKENS, MoleGame

KEY = bytes(range(32))
MASTER = Path(__file__).parents[1] / "data" / "masters" / "live" / "m8_midnight_carnival.md"


def _game(players: int = 5, seed: int = 7) -> MoleGame:
    game = MoleGame(MASTER, KEY, seed=seed)
    for index in range(players):
        game.join(f"player{index}")
    return game


def test_join_rules_and_personal_copies() -> None:
    game = _game(3)
    assert game.agents == ["A01", "A02", "A03"]
    with pytest.raises(ValueError, match="taken"):
        game.join("PLAYER0")
    with pytest.raises(ValueError, match="nickname"):
        game.join("   ")
    assert game.copy_text("A01") != game.copy_text("A02")
    with pytest.raises(ValueError, match="at least 4"):
        game.start_round("double")


def test_solo_round_forensics_name_the_real_mole_and_scores_follow() -> None:
    game = _game()
    round_ = game.start_round("solo")
    mole = round_.moles[0]
    with pytest.raises(ValueError, match="only the mole"):
        game.submit_leak(next(a for a in game.agents if a != mole), [])
    game.submit_leak(mole, ["strip", "quotes"])
    assert game.phase == "investigate" and round_.suspects == (mole,)
    detective = next(a for a in game.agents if a != mole)
    assert game.probe(detective, "ink").startswith("Scrub check")
    note = game.probe(detective, "sample", mole)
    assert "sampled slots agree" in note
    with pytest.raises(ValueError, match="tokens"):
        game.probe(detective, "sample", mole)
    game.bet(detective, mole, 3)
    game.reveal()
    assert round_.deltas[detective] == 300 + 20 * (TOKENS - 3)
    assert round_.deltas[mole] == 0
    assert game.leaderboard()[0].agent == detective


def test_forward_round_tree_marks_the_journalist_path() -> None:
    game = _game()
    round_ = game.start_round("forward")
    game.submit_leak(round_.moles[0], ["cut"])
    found = round_.found
    assert len(round_.forwards) == 3
    assert found.decision.candidate_id == round_.forwards[0]
    assert any("<== leak" in line for line in found.tree)
    assert round_.suspects == (round_.moles[0],)


def test_double_agents_are_both_flagged_or_one_escapes_honestly() -> None:
    game = _game(6)
    round_ = game.start_round("double")
    for mole in round_.moles:
        assert game.phase == "leak"
        game.submit_leak(mole, [])
    assert game.phase == "investigate"
    assert set(round_.suspects) <= set(round_.moles)
    assert round_.found.canaries is not None
    game.reveal()
    with pytest.raises(ValueError):
        game.reveal()
