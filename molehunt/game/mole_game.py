"""Find the Mole: a live LAN party game played on phones, judged by real forensics.

Round, step by step:

1. Lobby. Players join with a nickname and become agents A01, A02, ... Each agent
   can read their own fingerprinted copy (real keyed codeword + canary facts).
2. Leak. The host starts a round. A seeded RNG (seed logged) picks the mole, or two
   double agents. Modes: ``solo``; ``forward`` (the mole's copy is re-stamped for a
   journalist J<round>, and two innocent decoy forwards are logged too); ``double``
   (two moles merge their copies bit by bit). Each mole picks up to two scrub tools
   (real attacks A1-A9). The leak is the real attacked text.
3. Investigate. Everyone gets 3 forensic tokens: facts (1), ink scan (1), lineage
   trace (1), slot sample against one agent (2). Then each agent bets on a suspect
   with 1-3 chips. A mole's bet is a frame-up attempt.
4. Reveal. ``forensics.examine`` runs on the leak over all agents and forward paths.
   The forensic suspects are the first hops of the attributed (or tied) paths.

Scoring: investigator +100 x chips if right, -50 x chips if wrong, +20 per unused
token. Mole +200 if the forensics do not name them, +50 for each wrong bet, +50
more if the frame-up target got the most bets.
"""

from __future__ import annotations

import random
import secrets
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from molehunt.attacks.collusion import collude_bits
from molehunt.attacks.transform import attack_chain
from molehunt.core.autoslots import prepare_master
from molehunt.core.canaries import holder_values
from molehunt.core.lineage import SEP, path_codeword
from molehunt.core.render import render_text
from molehunt.forensics import Examination, examine

TOOLS = {"strip": ("Strip invisible characters", "A1", 1.0),
         "fold": ("Replace look-alike letters", "A2b", 1.0),
         "spaces": ("Collapse special spaces", "A3", 1.0),
         "quotes": ("Straighten quotes", "A4", 1.0),
         "synonyms": ("Swap words for synonyms", "A7", 0.5),
         "cut": ("Leak only the first half", "A8", 0.5),
         "shuffle": ("Shuffle the paragraphs", "A9", 1.0),
         "retype": ("Retype it by hand", "A5", 1.0)}
PROBES = {"facts": (1, "Fact check"), "ink": (1, "Invisible-ink scan"),
          "trace": (1, "Lineage trace"), "sample": (2, "Slot sample vs one agent")}
MODES = {"solo": "One mole", "forward": "Mole forwards to a journalist",
         "double": "Two double agents"}
MOLE_TOOLS, TOKENS, MAX_PLAYERS = 2, 3, 30


@dataclass
class Player:
    token: str
    name: str
    agent: str
    score: int = 0


@dataclass
class Round:
    number: int
    mode: str
    moles: list[str]
    forwards: list[str] = field(default_factory=list)
    tools: dict[str, list[str]] = field(default_factory=dict)
    leak: str = ""
    found: Examination | None = None
    spent: dict[str, int] = field(default_factory=dict)
    notes: dict[str, list[str]] = field(default_factory=dict)
    bets: dict[str, tuple[str, int]] = field(default_factory=dict)
    deltas: dict[str, int] = field(default_factory=dict)
    suspects: tuple[str, ...] = ()


class MoleGame:
    """All game state; the web layer only calls these methods."""

    def __init__(self, master: Path, key: bytes, seed: int | None = None) -> None:
        self.source = master.read_text(encoding="utf-8")
        self.key = key
        self.prepared = prepare_master(self.source, key)
        self.seed = secrets.randbits(32) if seed is None else seed
        self.rng = random.Random(self.seed)
        self.players: dict[str, Player] = {}
        self.phase = "lobby"
        self.round: Round | None = None
        self.version = 0

    def _bump(self) -> None:
        self.version += 1

    @property
    def agents(self) -> list[str]:
        return [player.agent for player in self.players.values()]

    def name_of(self, agent: str) -> str:
        return next((p.name for p in self.players.values() if p.agent == agent), agent)

    def join(self, name: str) -> str:
        """Add a player and return their secret token."""
        name = " ".join(name.split())[:16]
        if not name:
            raise ValueError("pick a nickname")
        if any(p.name.casefold() == name.casefold() for p in self.players.values()):
            raise ValueError("that nickname is taken")
        if len(self.players) >= MAX_PLAYERS:
            raise ValueError("the game is full")
        token = secrets.token_urlsafe(12)
        self.players[token] = Player(token, name, f"A{len(self.players) + 1:02}")
        self._bump()
        return token

    def copy_text(self, holder: str) -> str:
        """The fingerprinted copy for an agent or a forward path."""
        bits = path_codeword(self.key, holder.split(SEP), len(self.prepared.slots))
        return render_text(self.prepared.template, self.prepared.slots, bits,
                           holder_values(self.prepared.canaries, self.key, holder))

    def start_round(self, mode: str) -> Round:
        if self.phase not in {"lobby", "reveal"}:
            raise ValueError("a round is already running")
        if mode not in MODES:
            raise ValueError("unknown mode")
        need = 4 if mode == "double" else 3
        if len(self.players) < need:
            raise ValueError(f"{MODES[mode]} needs at least {need} players")
        number = (self.round.number + 1) if self.round else 1
        moles = sorted(self.rng.sample(self.agents, 2 if mode == "double" else 1))
        self.round = Round(number, mode, moles)
        if mode == "forward":
            innocents = [a for a in self.agents if a not in moles]
            senders = [moles[0], *self.rng.sample(innocents, min(2, len(innocents)))]
            letters = self.rng.sample("ABC", len(senders))
            self.round.forwards = [f"{a}{SEP}J{number:02}{x}" for a, x in zip(senders, letters)]
        self.phase = "leak"
        self._bump()
        return self.round

    def submit_leak(self, agent: str, tools: list[str]) -> None:
        """A mole picks scrub tools; the leak is built once every mole has chosen."""
        game = self._need("leak")
        if agent not in game.moles:
            raise ValueError("only the mole can leak")
        if len(tools) > MOLE_TOOLS or any(tool not in TOOLS for tool in tools):
            raise ValueError(f"pick at most {MOLE_TOOLS} tools")
        game.tools[agent] = list(dict.fromkeys(tools))
        if len(game.tools) < len(game.moles):
            self._bump()
            return
        game.leak = self._build_leak(game)
        holders = self.agents
        game.found = examine(self.source, self.key, holders, game.leak, game.forwards)
        decision = game.found.decision
        named = (decision.candidate_id,) if decision.outcome == "attribute" else decision.tied
        game.suspects = tuple(dict.fromkeys(item.split(SEP)[0] for item in named if item))
        self.phase = "investigate"
        self._bump()

    def _build_leak(self, game: Round) -> str:
        steps = [TOOLS[t] for agent in game.moles for t in game.tools[agent]]
        steps = list(dict.fromkeys(steps))[:3]
        if game.mode == "double":
            length = len(self.prepared.slots)
            words = [path_codeword(self.key, [m], length) for m in game.moles]
            bits = collude_bits(words, "random", seed=self.rng.randrange(2**31))
            facts = [holder_values(self.prepared.canaries, self.key, m) for m in game.moles]
            merged = {k: self.rng.choice([f[k] for f in facts]) for k in facts[0]}
            text = render_text(self.prepared.template, self.prepared.slots, bits, merged)
        else:
            source = game.forwards[0] if game.mode == "forward" else game.moles[0]
            text = self.copy_text(source)
        seed = self.rng.randrange(2**31)
        for index, (_, attack, strength) in enumerate(steps):
            text = attack_chain(text, [attack], strength=strength, seed=seed + index)
        return text

    def probe(self, agent: str, probe: str, target: str = "") -> str:
        """Spend tokens on one forensic tool and return its plain-English result."""
        game = self._need("investigate")
        if probe not in PROBES:
            raise ValueError("unknown tool")
        cost = PROBES[probe][0]
        if game.spent.get(agent, 0) + cost > TOKENS:
            raise ValueError("not enough forensic tokens")
        found = game.found
        if probe == "facts":
            seen = found.canaries.seen if found.canaries else {}
            mine = holder_values(self.prepared.canaries, self.key, agent)
            own = {fam.name: mine[fam.sentinel] for fam in self.prepared.canaries}
            text = ("Leak mentions: " + (", ".join(f"{k} {'/'.join(v)}" for k, v in seen.items())
                                         or "no facts") + ". Your copy says: "
                    + ", ".join(f"{k} {v}" for k, v in own.items()) + ".")
        elif probe == "ink":
            text = f"Scrub check: {found.scrub.verdict}. " + " ".join(
                s.reason for s in found.scrub.signals if s.fired)
        elif probe == "trace":
            hops = len(found.leader.split(SEP))
            text = ("The leaked copy was forwarded outside the team." if hops > 1
                    else "The leaked copy was never forwarded.")
        else:
            if target not in self.agents:
                raise ValueError("pick an agent to sample")
            word = path_codeword(self.key, [target], len(self.prepared.slots))
            seen = [i for i, bit in enumerate(found.result.observations) if bit is not None]
            picked = self.rng.sample(seen, min(24, len(seen)))
            agree = sum(found.result.observations[i] == word[i] for i in picked)
            text = (f"{agree}/{len(picked)} sampled slots agree with {target}'s copy "
                    f"(an unrelated copy agrees with about half).")
        game.spent[agent] = game.spent.get(agent, 0) + cost
        game.notes.setdefault(agent, []).append(f"{PROBES[probe][1]}: {text}")
        return text

    def bet(self, agent: str, suspect: str, chips: int) -> None:
        game = self._need("investigate")
        if suspect not in self.agents or suspect == agent:
            raise ValueError("pick another agent")
        if chips not in (1, 2, 3):
            raise ValueError("bet 1, 2, or 3 chips")
        game.bets[agent] = (suspect, chips)
        self._bump()

    def reveal(self) -> Round:
        """Score the round against the truth and the forensic verdict."""
        game = self._need("investigate")
        moles = set(game.moles)
        honest = {a: b for a, b in game.bets.items() if a not in moles}
        popular = Counter(s for s, _ in honest.values()).most_common(1)
        top_pick = popular[0][0] if popular else None
        deltas = {}
        for agent in self.agents:
            if agent in moles:
                wrong = sum(1 for s, _ in honest.values() if s not in moles)
                frame = game.bets.get(agent, ("", 0))[0]
                deltas[agent] = ((200 if agent not in game.suspects else 0) + 50 * wrong
                                 + (50 if frame and frame == top_pick else 0))
            elif agent in honest:
                suspect, chips = honest[agent]
                deltas[agent] = (100 * chips if suspect in moles else -50 * chips) + 20 * (
                    TOKENS - game.spent.get(agent, 0))
            else:
                deltas[agent] = 0
        for player in self.players.values():
            player.score += deltas.get(player.agent, 0)
        game.deltas = deltas
        self.phase = "reveal"
        self._bump()
        return game

    def leaderboard(self) -> list[Player]:
        return sorted(self.players.values(), key=lambda p: (-p.score, p.agent))

    def _need(self, phase: str) -> Round:
        if self.phase != phase or self.round is None:
            raise ValueError(f"not in the {phase} phase")
        return self.round
