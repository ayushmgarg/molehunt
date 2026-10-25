"""Escape room over LAN: teams race through six forensic locks against the clock.

Flow. Teams join with a name and get their own keyed case (``escape_case.py``).
The host starts one shared timer (default 30 minutes). A team sees only the
current lock's story, files, and tool; a correct answer unlocks the next clue.

Time and score. Final time = elapsed seconds + 120 per hint + 30 per wrong
answer. Ranking: more locks opened first, then lower final time. After the timer
runs out answers are refused, so the board freezes.

Tools are the real forensic functions, run on whatever file the team uploads:
SHA-256 (``hashlib``), invisible-character reveal, DOCX core.xml reader, the C7
dot decoder, and the full MoleHunt examiner (``forensics.examine``).
"""

from __future__ import annotations

import hashlib
import io
import re
import secrets
import time
import unicodedata
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree

from molehunt.core.autoslots import prepare_master
from molehunt.forensics import Examination, examine
from molehunt.game.escape_case import AGENTS, Lock, build_case, holder, normalise

TOOL_NAMES = {"hash": "Hash workstation", "ink": "Invisible-ink revealer",
              "meta": "DOCX metadata inspector", "dots": "Yellow-dot decoder",
              "examine": "MoleHunt examiner", "none": "Your eyes (open the file)"}
HINT_PENALTY, WRONG_PENALTY = 120, 30


@dataclass
class Team:
    token: str
    name: str
    slug: str
    locks: list[Lock]
    stage: int = 0
    hints: set[int] = field(default_factory=set)
    wrong: int = 0
    finished: float | None = None


class EscapeRoom:
    """Shared timer, teams, and answer checking."""

    def __init__(self, master: Path, key: bytes, *, seed: int | None = None,
                 duration: int = 1800, clock: Callable[[], float] = time.monotonic) -> None:
        self.source = master.read_text(encoding="utf-8")
        self.prepared = prepare_master(self.source, key)
        self.key = key
        self.seed = secrets.randbits(32) if seed is None else seed
        self.duration = duration
        self.clock = clock
        self.started: float | None = None
        self.teams: dict[str, Team] = {}
        self.version = 0

    def join(self, name: str) -> str:
        name = " ".join(name.split())[:20]
        slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
        if not slug:
            raise ValueError("pick a team name")
        if any(team.slug == slug for team in self.teams.values()):
            raise ValueError("that team name is taken")
        token = secrets.token_urlsafe(12)
        locks = build_case(self.prepared, self.key, self.seed, slug)
        self.teams[token] = Team(token, name, slug, locks)
        self.version += 1
        return token

    def start(self) -> None:
        if self.started is None:
            self.started = self.clock()
            self.version += 1

    def elapsed(self) -> float:
        return 0.0 if self.started is None else self.clock() - self.started

    def remaining(self) -> int:
        return max(0, int(self.duration - self.elapsed())) if self.started is not None else (
            self.duration)

    def penalty(self, team: Team) -> int:
        return HINT_PENALTY * len(team.hints) + WRONG_PENALTY * team.wrong

    def team(self, token: str) -> Team:
        if token not in self.teams:
            raise ValueError("join a team first")
        return self.teams[token]

    def answer(self, token: str, text: str) -> bool:
        """Check the current lock's answer; a correct one opens the next lock."""
        team = self.team(token)
        if self.started is None:
            raise ValueError("wait for the host to start the clock")
        if self.remaining() == 0:
            raise ValueError("time is up")
        if team.stage >= len(team.locks):
            return True
        correct = normalise(text) == normalise(team.locks[team.stage].answer)
        if correct:
            team.stage += 1
            if team.stage == len(team.locks):
                team.finished = self.elapsed()
        else:
            team.wrong += 1
        self.version += 1
        return correct

    def hint(self, token: str) -> str:
        team = self.team(token)
        if team.stage >= len(team.locks):
            return ""
        if team.stage not in team.hints:
            team.hints.add(team.stage)
            self.version += 1
        return team.locks[team.stage].hint

    def file(self, token: str, name: str) -> bytes:
        """A file from any lock the team has reached."""
        team = self.team(token)
        for lock in team.locks[: team.stage + 1]:
            if name in lock.files:
                return lock.files[name]
        raise ValueError("no such file (yet)")

    def scoreboard(self) -> list[tuple[Team, int]]:
        """(team, final seconds) sorted by locks opened, then time."""
        rows = []
        for team in self.teams.values():
            spent = team.finished if team.finished is not None else self.elapsed()
            rows.append((team, int(spent) + self.penalty(team)))
        return sorted(rows, key=lambda row: (-row[0].stage, row[1], row[0].name))

    def examine_leak(self, token: str, text: str) -> Examination:
        team = self.team(token)
        holders = [holder(team.slug, agent) for agent in AGENTS]
        return examine(self.source, self.key, holders, text)


def hash_tool(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ink_tool(text: str) -> list[tuple[str, str]]:
    """Split text into (kind, shown) pieces: plain text, bit marks, other invisibles."""
    pieces: list[tuple[str, str]] = []
    for character in text:
        if character == "\u200b":
            pieces.append(("bit", "0"))
        elif character == "‌":
            pieces.append(("bit", "1"))
        elif unicodedata.category(character) == "Cf" or character in "  ":
            pieces.append(("odd", f"U+{ord(character):04X}"))
        elif pieces and pieces[-1][0] == "text":
            pieces[-1] = ("text", pieces[-1][1] + character)
        else:
            pieces.append(("text", character))
    return pieces


def meta_tool(data: bytes) -> dict[str, str]:
    """Fields of docProps/core.xml inside a DOCX (tag without namespace -> text)."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            root = ElementTree.fromstring(archive.read("docProps/core.xml"))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as error:
        raise ValueError("not a DOCX with core metadata") from error
    return {element.tag.split("}")[-1]: (element.text or "") for element in root}


def dots_tool(data: bytes) -> dict[str, str]:
    """Decode the yellow C7 grid: try the top-left margin first (fast), then the whole image."""
    from PIL import Image

    from molehunt.channels.dot_locate import scan_dot_grid

    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
        try:
            meta = scan_dot_grid(image.crop((0, 0, 420, 320)), channel="B", window=200).metadata
        except ValueError:
            meta = scan_dot_grid(image, channel="B", window=200).metadata
    except (OSError, ValueError) as error:
        raise ValueError(f"no dot grid found: {error}") from error
    return {"station": str(meta.printer_id), "date": meta.printed_on.isoformat(),
            "minute of day": str(meta.minute_of_day)}
