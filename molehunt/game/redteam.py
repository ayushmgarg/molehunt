"""Red Team boss: you hold one fingerprinted copy and try to beat the detector.

Utility = word-token similarity between the attacked text and the master, as
``difflib.SequenceMatcher.ratio`` = 2 * matched tokens / (tokens_a + tokens_b),
computed on skeleton words (invisible marks dropped, look-alikes folded, lower
case, variant pairs folded to one label, punctuation ignored),
so invisible edits cost nothing and real rewording costs utility. It must stay
>= 0.70. The opponent is the Lab detector with its decision rule (hidden alpha).
Win = utility >= 0.70 and the detector does not attribute the leak to you.
Score = 100 x utility x (slot reduction + LR reduction) / 2, plus 100 for a win,
where slot reduction = 1 - n / n0 and LR reduction = 1 - max(LR, 0) / LR0.
"""

from __future__ import annotations

import json
import random
import re
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path

from molehunt.analysis import AnalysisResult, analyze_prepared
from molehunt.attacks.harness import bench_key
from molehunt.attacks.transform import attack_text
from molehunt.core.autoslots import PreparedMaster, prepare_master
from molehunt.core.codes import generate_codewords
from molehunt.core.render import render_text
from molehunt.detect.align import WORD_CHANNELS, build_skeleton

UTILITY_FLOOR = 0.70
_WORDS = re.compile(r"\w+")
TOOLS = {
    "strip": "A1", "normalize": "A2", "confusables": "A2b", "collapse": "A3",
    "punctuation": "A4", "canonicalize": "A6", "paraphrase": "A7", "truncate": "A8",
    "reorder": "A9", "noise": "A10",
}
_SCHEMA = """CREATE TABLE IF NOT EXISTS redteam_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT, player_id TEXT NOT NULL, score INTEGER NOT NULL,
    utility REAL NOT NULL, outcome TEXT NOT NULL, win INTEGER NOT NULL,
    steps_json TEXT NOT NULL, played_at TEXT NOT NULL)"""


@dataclass(frozen=True)
class Session:
    """One mole's copy, the roster's codewords, and the detector's baseline."""

    prepared: PreparedMaster
    codewords: dict[str, tuple[int, ...]]
    mole: str
    copy_text: str
    baseline: AnalysisResult


@dataclass(frozen=True, slots=True)
class Verdict:
    """What the detector concluded about an attacked copy, and the score."""

    utility: float
    observed_slots: int
    baseline_slots: int
    mole_log10_lr: float
    outcome: str
    accused: str | None
    win: bool
    score: int
    statement: str


def start_session(master_path: str | Path, *, seed: int = 0, employees: int = 50) -> Session:
    """Issue the mole a copy from a seeded roster; the key never leaves the engine."""
    key = bench_key(10_000 + seed)
    prepared = prepare_master(Path(master_path).read_text(encoding="utf-8"), key)
    roster = [f"E{index:03}" for index in range(1, employees + 1)]
    codewords = generate_codewords(key, roster, len(prepared.slots))
    mole = random.Random(f"redteam:{seed}").choice(roster)
    text = render_text(prepared.template, prepared.slots, codewords[mole])
    return Session(prepared, codewords, mole, text, analyze_prepared(prepared, text, codewords))


def utility(session: Session, text: str) -> float:
    """Word-token similarity of the attacked text to the canonical master."""
    canonical = session.prepared.template.render([0] * len(session.prepared.template.choices))
    pairs = [(c.zero, c.one) for c in session.prepared.template.choices if c.channel in WORD_CHANNELS]
    master_words = _WORDS.findall(build_skeleton(canonical, pairs).text)
    leak_words = _WORDS.findall(build_skeleton(text, pairs).text)
    return SequenceMatcher(None, master_words, leak_words, autojunk=False).ratio()


def apply_tools(session: Session, steps: list[tuple[str, float]], *, seed: int = 0,
                dictionary: list[tuple[str, str]] | None = None) -> str:
    """Apply named tools in order; canonicalize only uses pairs the player found."""
    text = session.copy_text
    for index, (tool, strength) in enumerate(steps):
        if tool not in TOOLS:
            raise ValueError(f"unknown tool {tool!r}; choose from {', '.join(TOOLS)}")
        text = attack_text(text, TOOLS[tool], strength=strength, seed=seed * 100 + index,
                           variants=dictionary or [])
    return text


def evaluate(session: Session, text: str) -> Verdict:
    """Run the real detector on the attacked text and score the attempt."""
    result = analyze_prepared(session.prepared, text, session.codewords)
    decision = result.decision()
    mole_score = next(s for s in result.scores if s.candidate_id == session.mole)
    base = next(s for s in session.baseline.scores if s.candidate_id == session.mole)
    kept = utility(session, text)
    caught = decision.outcome == "attribute" and decision.candidate_id == session.mole
    win = kept >= UTILITY_FLOOR and not caught
    slot_cut = 1 - result.observed_slots / max(1, session.baseline.observed_slots)
    lr_cut = min(1.0, max(0.0, 1 - max(mole_score.log10_lr, 0) / max(base.log10_lr, 1e-9)))
    score = round(100 * kept * (slot_cut + lr_cut) / 2) + (100 if win else 0)
    return Verdict(round(kept, 4), result.observed_slots, session.baseline.observed_slots,
                   round(mole_score.log10_lr, 2), decision.outcome, decision.candidate_id,
                   win, score if kept >= UTILITY_FLOOR else 0, decision.statement)


def record_score(database: str | Path, player_id: str, verdict: Verdict,
                 steps: list[tuple[str, float]]) -> None:
    """Append one attempt to the Red Team leaderboard table."""
    with sqlite3.connect(database) as connection:
        connection.execute(_SCHEMA)
        connection.execute(
            "INSERT INTO redteam_scores(player_id, score, utility, outcome, win, steps_json, "
            "played_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (player_id, verdict.score, verdict.utility, verdict.outcome, int(verdict.win),
             json.dumps({"steps": steps, "verdict": asdict(verdict)}),
             datetime.now(UTC).isoformat(timespec="seconds")),
        )


def redteam_leaderboard(database: str | Path, limit: int = 10) -> list[tuple[str, int, float, str]]:
    """Best score per player: (player, score, utility, outcome)."""
    with sqlite3.connect(database) as connection:
        connection.execute(_SCHEMA)
        rows = connection.execute(
            "SELECT player_id, score, utility, outcome FROM redteam_scores "
            "ORDER BY score DESC, utility DESC, id"
        ).fetchall()
    best: dict[str, tuple[str, int, float, str]] = {}
    for row in rows:
        best.setdefault(row[0], (row[0], int(row[1]), float(row[2]), row[3]))
    return list(best.values())[:limit]
