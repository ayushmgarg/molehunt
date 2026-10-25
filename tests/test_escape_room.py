"""Escape room: every lock is solvable from the files with the bundled tools alone."""

import csv
import io
from pathlib import Path

import pytest

from molehunt.game.escape_case import hide_word, normalise
from molehunt.game.escape_room import (
    EscapeRoom,
    dots_tool,
    hash_tool,
    ink_tool,
    meta_tool,
)

KEY = bytes(range(32))
MASTER = Path(__file__).parents[1] / "data" / "masters" / "live" / "m8_midnight_carnival.md"


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _solve(room: EscapeRoom, token: str) -> list[str]:
    """Play like a team: use only files and tools, never the stored answers."""
    get = lambda name: room.file(token, name)
    custody = get("custody_record.txt").decode()
    original = next(letter for letter in "ABCD"
                    if hash_tool(get(f"voicemail_{letter}.txt")) in custody)
    station = get(f"voicemail_{original}.txt").decode().split("Station ")[1].split()[0]
    answers = [original]
    assert room.answer(token, original)
    bits = "".join(shown for kind, shown in ink_tool(get("ransom_note.txt").decode())
                   if kind == "bit")
    word = "".join(chr(int(bits[i:i + 8], 2)) for i in range(0, len(bits), 8))
    answers.append(word)
    assert room.answer(token, word)
    editor = meta_tool(get("run_sheet.docx"))["lastModifiedBy"]
    answers.append(editor)
    assert room.answer(token, editor)
    dots = dots_tool(get("leak_photo.png"))
    assert dots["station"] == station
    minute = int(dots["minute of day"])
    clock = f"{minute // 60}:{minute % 60:02}"
    answers.append(clock)
    assert room.answer(token, clock)
    rows = list(csv.DictReader(io.StringIO(get("printer_log.csv").decode())))
    match = [r for r in rows if r["station"] == f"Station {station}"
             and normalise(r["time"]) == normalise(clock)]
    assert len(match) == 1
    answers.append(match[0]["agent"])
    assert room.answer(token, match[0]["agent"])
    found = room.examine_leak(token, get("leaked_memo.txt").decode())
    culprit = found.decision.candidate_id.split(":")[1]
    assert culprit == match[0]["agent"]
    answers.append(culprit)
    assert room.answer(token, culprit)
    return answers


def test_two_teams_get_different_cases_and_both_can_escape() -> None:
    clock = Clock()
    room = EscapeRoom(MASTER, KEY, seed=11, clock=clock)
    first, second = room.join("Night Owls"), room.join("Grave Diggers")
    with pytest.raises(ValueError, match="host"):
        room.answer(first, "A")
    room.start()
    clock.now = 100
    one = _solve(room, first)
    clock.now = 400
    two = _solve(room, second)
    assert one != two
    board = room.scoreboard()
    assert [team.name for team, _ in board] == ["Night Owls", "Grave Diggers"]
    assert board[0][1] == 100


def test_files_stay_locked_and_penalties_add_up() -> None:
    clock = Clock()
    room = EscapeRoom(MASTER, KEY, seed=3, clock=clock)
    token = room.join("Bats")
    with pytest.raises(ValueError, match="no such file"):
        room.file(token, "printer_log.csv")
    room.start()
    assert not room.answer(token, "wrong")
    assert "Hash" in room.hint(token)
    room.hint(token)  # same lock: charged once
    assert room.penalty(room.team(token)) == 120 + 30
    clock.now = 5000
    with pytest.raises(ValueError, match="time is up"):
        room.answer(token, "A")
    with pytest.raises(ValueError, match="taken"):
        room.join("bats")


def test_answer_normalising_and_hidden_word_roundtrip() -> None:
    assert normalise("a3") == normalise("A03") == normalise("3") == "A03"
    assert normalise("9.05") == normalise("09:05")
    note = hide_word("one two three four five six seven eight nine ten eleven " * 2, "OK")
    bits = "".join(shown for kind, shown in ink_tool(note) if kind == "bit")
    assert bits == f"{ord('O'):08b}{ord('K'):08b}"
