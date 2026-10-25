"""Find the Mole screens: one phone view per phase and one projector view per phase.

Phones show only what that player may know (their copy, their tokens, their notes;
the mole sees the leak console). The projector shows the lobby, the leaked text,
bet progress, and the forensic reveal. Both reload themselves when the game's
version number changes.
"""

from __future__ import annotations

from html import escape

from molehunt.game.mole_game import MODES, MOLE_TOOLS, PROBES, TOKENS, TOOLS, MoleGame, Player
from molehunt.web.findings import METER_SCRIPT, findings_html
from molehunt.web.theme import icon, page, pill

POLL = "/game/v"


def _wrap(game: MoleGame, title: str, body: str, script: str = "") -> str:
    return page(title, body, poll=(POLL, str(game.version)), script=script)


def join_page() -> str:
    return page("Find the Mole", f"""<h1>Find the Mole</h1>
<div class=card><h2>{icon('ghost')}Join the game</h2><form method=post action=/game/join>
<label>Nickname</label><input name=name maxlength=16 required autocomplete=off>
<label>PIN (on the big screen)</label><input name=pin inputmode=numeric required>
<button class=big>Join</button></form></div>""")


def _copy_box(text: str, label: str = "Your copy") -> str:
    return (f"<details class=card><summary><b>{escape(label)}</b> (tap to open)</summary>"
            f"<div class=copy>{escape(text)}</div></details>")


def _scores(game: MoleGame) -> str:
    rows = "".join(f"<tr><td>{i}</td><td>{escape(p.name)}</td><td>{p.agent}</td>"
                   f"<td>{p.score}</td></tr>" for i, p in enumerate(game.leaderboard(), 1))
    return f"<table><tr><th>#</th><th>Player</th><th>Agent</th><th>Score</th></tr>{rows}</table>"


def phone_page(game: MoleGame, me: Player) -> str:
    head = f"<h1>Agent {me.agent}</h1><p class=dim>{escape(me.name)} - score {me.score}</p>"
    game_round, phase = game.round, game.phase
    copy = _copy_box(game.copy_text(me.agent))
    download = "<p><a href=/game/copy.txt>Download my copy (.txt)</a></p>"
    if phase == "lobby" or game_round is None:
        body = ("<div class=card><h2>Waiting for the host</h2><p>Read your copy. Remember "
                "your facts: codename, budget, venue, date.</p></div>" + copy + download)
        return _wrap(game, "Lobby", head + body)
    is_mole = me.agent in game_round.moles
    if phase == "leak":
        if not is_mole:
            body = ("<div class=card><h2>Lights out...</h2><p>Someone is leaking the memo "
                    "right now. Act normal.</p></div>" + copy)
        elif me.agent in game_round.tools:
            body = "<div class=card><h2>Done</h2><p>Waiting for your partner to leak.</p></div>"
        else:
            partner = [a for a in game_round.moles if a != me.agent]
            team = (f"<p>Your partner is <b>{partner[0]} ({escape(game.name_of(partner[0]))})"
                    "</b>. Your copies will be merged.</p>") if partner else ""
            ways = ("<p>Your copy goes to a journalist first; the system re-stamps it.</p>"
                    if game_round.mode == "forward" else "")
            boxes = "".join(f"<label><input type=checkbox name=t_{key} style='width:auto'> "
                            f"{escape(label)}</label>" for key, (label, _, _) in TOOLS.items())
            body = (f"<div class=card style='border-color:#ff3b3b'><h2>{icon('skull')}You are "
                    f"the mole</h2>{team}{ways}<p>Pick up to {MOLE_TOOLS} scrub tools to hide "
                    f"your fingerprint.</p><form method=post action=/game/leak>{boxes}"
                    "<button class=big>Leak it</button></form></div>" + copy)
        return _wrap(game, "Leak", head + body)
    if phase == "investigate":
        left = TOKENS - game_round.spent.get(me.agent, 0)
        targets = "".join(f"<option value={a}>{a} - {escape(game.name_of(a))}</option>"
                          for a in game.agents if a != me.agent)
        probes = "".join(
            f"<button name=probe value={key} class=ghost {'disabled' if cost > left else ''}>"
            f"{escape(label)} ({cost})</button> " for key, (cost, label) in PROBES.items())
        notes = "".join(f"<li>{escape(note)}</li>" for note in game_round.notes.get(me.agent, []))
        bet = game_round.bets.get(me.agent)
        placed = f"<p>{pill(f'bet on {bet[0]} x{bet[1]}', 'warn')}</p>" if bet else ""
        role = ("<p style='color:#ff3b3b'>You are the mole: act natural. Your bet is a "
                "frame-up.</p>") if is_mole else ""
        body = f"""<div class=card><h2>{icon('search')}Investigate</h2>{role}
<p>Forensic tokens left: <b>{left}</b></p><form method=post action=/game/probe>
<label>Target (for the slot sample)</label><select name=target>{targets}</select>
<p>{probes}</p></form><ul>{notes}</ul></div>
<div class=card><h2>{icon('trophy')}Place your bet</h2>{placed}
<form method=post action=/game/bet><select name=suspect>{targets}</select>
<select name=chips><option>1</option><option>2</option><option>3</option></select>
<button class=big>Bet</button></form></div>
{_copy_box(game_round.leak, 'The leak')}{copy}"""
        return _wrap(game, "Investigate", head + body)
    delta = game_round.deltas.get(me.agent, 0)
    moles = ", ".join(f"{a} ({escape(game.name_of(a))})" for a in game_round.moles)
    body = (f"<div class=card><h2>Reveal</h2><p>The mole was <b>{moles}</b>.</p>"
            f"<p>This round: <b>{delta:+d}</b></p></div><div class=card>{_scores(game)}</div>")
    return _wrap(game, "Reveal", head + body)


def screen_page(game: MoleGame, join: str, pin: str) -> str:
    game_round, phase = game.round, game.phase
    if phase in {"lobby", "reveal"}:
        buttons = "".join(f"<button name=mode value={key} class=big>{escape(label)}</button>"
                          for key, label in MODES.items())
        start = f"<form method=post action=/game/start>{buttons}</form>"
    if phase == "lobby" or game_round is None:
        names = "".join(f"<span class='pill good'>{p.agent} {escape(p.name)}</span> "
                        for p in game.players.values()) or "<span class=dim>nobody yet</span>"
        body = (f"<h1>Find the Mole</h1><div class=card><p>Join at <b>{escape(join)}</b></p>"
                f"<p class=dim>PIN</p><div class=pin>{escape(pin)}</div></div>"
                f"<div class=card><h2>Agents</h2><p>{names}</p></div><div class=card>{start}</div>")
        return _wrap(game, "Find the Mole", body)
    title = f"<h1>Round {game_round.number}: {escape(MODES[game_round.mode])}</h1>"
    if phase == "leak":
        done = len(game_round.tools)
        body = (f"{title}<div class=card><h2>{icon('moon')}The lights flicker...</h2><p>The "
                f"mole is scrubbing their copy ({done}/{len(game_round.moles)} ready).</p></div>")
        return _wrap(game, "Leak", body)
    if phase == "investigate":
        bets = len(game_round.bets)
        body = (f"{title}<div class=card><h2>{icon('eye')}The leak is out</h2><p>Compare it "
                f"with your own copy. Bets placed: <b>{bets}/{len(game.players)}</b></p>"
                f"<form method=post action=/game/reveal><button class=big>Run the forensics"
                f"</button></form></div><div class=card><div class=copy>"
                f"{escape(game_round.leak)}</div></div>")
        return _wrap(game, "Investigate", body)
    moles = ", ".join(f"{a} ({escape(game.name_of(a))})" for a in game_round.moles)
    named = ", ".join(game_round.suspects) or "nobody"
    caught = set(game_round.suspects) == set(game_round.moles)
    tone = "good" if caught else "warn"
    legend = ", ".join(f"{p.agent} = {escape(p.name)}" for p in game.players.values())
    used = "; ".join(f"{a}: {', '.join(TOOLS[t][0] for t in tools) or 'no tools'}"
                     for a, tools in game_round.tools.items())
    body = (f"{title}{findings_html(game_round.found, title='Forensic reveal')}"
            f"<div class=card><h2>{icon('skull')}The truth</h2><p>Mole: <b>{moles}</b>"
            f". Forensics named: <b>{escape(named)}</b> {pill('caught' if caught else 'escaped', tone)}"
            f"</p><p class=dim>Scrub tools used - {escape(used)}</p><p class=dim>{legend}</p></div>"
            f"<div class=card><h2>{icon('trophy')}Leaderboard</h2>{_scores(game)}</div>"
            f"<div class=card><h2>Next round</h2>{start}</div>")
    return _wrap(game, "Reveal", body, METER_SCRIPT)
