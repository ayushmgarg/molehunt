"""Escape Room screens and routes.

GET  /escape              join form, or the team's current lock
POST /escape/join         team name + PIN -> cookie ``mh_team``
POST /escape/answer       answer for the current lock
POST /escape/hint         reveal the hint (+120 s)
POST /escape/tool         run the lock's tool on an uploaded file or pasted text
GET  /escape/file/<name>  download evidence from a reached lock
GET  /escape/v            version (pages poll and reload)
GET  /escape/screen       projector scoreboard with the clock (host); POST /escape/start

Tools run outside the room lock, so a slow dot decode never stalls other teams.
"""

from __future__ import annotations

import threading
from html import escape

from molehunt.game.escape_room import (
    TOOL_NAMES,
    EscapeRoom,
    Team,
    dots_tool,
    hash_tool,
    ink_tool,
    meta_tool,
)
from molehunt.web.findings import METER_SCRIPT, findings_html
from molehunt.web.hub import Site
from molehunt.web.server import Request, Response
from molehunt.web.theme import icon, page, pill

_CLOCK = """<script>(function(){var e=document.getElementById('clock');if(!e)return;
var s=parseInt(e.dataset.left,10),run=e.dataset.run==='1';function f(){var m=Math.floor(s/60),
r=s%60;e.textContent=(m<10?'0':'')+m+':'+(r<10?'0':'')+r;if(run&&s>0){s--;}}f();
setInterval(f,1000)})();</script>"""


def _clock(room: EscapeRoom) -> str:
    run = "1" if room.started is not None else "0"
    return f"<span id=clock class=timer data-left={room.remaining()} data-run={run}></span>"


def join_page() -> str:
    return page("Escape Room", f"""<h1>Escape Room</h1><div class=card>
<h2>{icon('lock-keyhole')}Midnight at Hollowmere</h2><p>The carnival memo leaked tonight.
Open six forensic locks before the lanterns go out.</p><form method=post action=/escape/join>
<label>Team name</label><input name=name maxlength=20 required autocomplete=off>
<label>PIN</label><input name=pin inputmode=numeric required><button class=big>Enter</button>
</form></div>""")


def _tool_form(tool: str) -> str:
    if tool == "none":
        return "<p class=dim>No special tool: open the file and read it carefully.</p>"
    note = ("<p class=dim>Upload the file itself: pasting can change line endings, and one "
            "changed byte changes the whole hash.</p>") if tool == "hash" else ""
    return (f"{note}<form method=post action=/escape/tool enctype=multipart/form-data>"
            f"<label>Upload a file</label><input type=file name=file>"
            f"<label>or paste text</label><textarea name=text rows=3></textarea>"
            f"<button>{icon('search')}Run {escape(TOOL_NAMES[tool])}</button></form>")


def team_page(room: EscapeRoom, team: Team, output: str) -> str:
    total = len(team.locks)
    head = (f"<h1>{escape(team.name)}</h1><p>{_clock(room)} &nbsp; lock "
            f"<b>{min(team.stage + 1, total)}/{total}</b> &nbsp; penalty {room.penalty(team)} s</p>")
    solved = "".join(f"<li>{pill('open', 'good')} {escape(lock.title)}</li>"
                     for lock in team.locks[: team.stage])
    if team.stage >= total:
        body = (f"<div class=card><h2>{icon('trophy')}Case closed!</h2><p>You escaped in "
                f"{int(team.finished or 0) + room.penalty(team)} s (with penalties).</p>"
                f"<ul>{solved}</ul></div>")
        return page("Escaped", head + body, poll=("/escape/v", str(room.version)), script=_CLOCK)
    lock = team.locks[team.stage]
    if room.started is None:
        body = "<div class=card><h2>Waiting for the host to start the clock...</h2></div>"
        return page("Waiting", head + body, poll=("/escape/v", str(room.version)), script=_CLOCK)
    files = "".join(f"<a class='btn ghost' href=/escape/file/{escape(name)}>{escape(name)}</a> "
                    for name in lock.files)
    hint = (f"<p>{pill('hint', 'warn')} {escape(lock.hint)}</p>" if team.stage in team.hints
            else "<form method=post action=/escape/hint><button class=ghost>Hint (+120 s)"
                 "</button></form>")
    body = f"""<div class=card><h2>{icon('hourglass')}{escape(lock.title)}</h2>
<p>{escape(lock.story)}</p><p>{files}</p></div>
<div class=card><h2>{icon('search')}{escape(TOOL_NAMES[lock.tool])}</h2>{_tool_form(lock.tool)}
{output}</div><div class=card><h2>{icon('lock-keyhole')}{escape(lock.question)}</h2>
<form method=post action=/escape/answer><input name=answer required autocomplete=off>
<button class=big>Try the lock</button></form>{hint}<p class=dim>Wrong answers: {team.wrong}
(+30 s each)</p></div><ul>{solved}</ul>"""
    return page(lock.title, head + body, script=_CLOCK + (METER_SCRIPT if "meter" in output
                                                           else ""))


def screen_page(room: EscapeRoom, join: str, pin: str) -> str:
    rows = "".join(
        f"<tr><td>{i}</td><td>{escape(team.name)}</td><td>{team.stage}/{len(team.locks)}</td>"
        f"<td>{seconds // 60}:{seconds % 60:02}</td><td>{len(team.hints)}</td>"
        f"<td>{team.wrong}</td></tr>" for i, (team, seconds) in enumerate(room.scoreboard(), 1))
    start = ("" if room.started is not None else
             "<form method=post action=/escape/start><button class=big>Start the clock</button>"
             "</form>")
    body = (f"<h1>Escape Room</h1><div class=card><p>Join at <b>{escape(join)}</b> - PIN "
            f"<b class=pin style='font-size:40px'>{escape(pin)}</b></p><p>{_clock(room)}</p>"
            f"{start}</div><div class=card><h2>{icon('trophy')}Teams</h2><table><tr><th>#</th>"
            f"<th>Team</th><th>Locks</th><th>Time</th><th>Hints</th><th>Wrong</th></tr>{rows}"
            "</table></div>")
    return page("Escape Room screen", body, poll=("/escape/v", str(room.version)), script=_CLOCK)


def _run_tool(room: EscapeRoom, team: Team, request: Request) -> str:
    lock = team.locks[min(team.stage, len(team.locks) - 1)]
    data = request.upload[1] if request.upload else request.fields.get("text", "").encode()
    if not data.strip():
        raise ValueError("upload a file or paste text first")
    if lock.tool == "hash":
        return f"<p>SHA-256: <code style='word-break:break-all'>{hash_tool(data)}</code></p>"
    if lock.tool == "ink":
        parts = []
        for kind, shown in ink_tool(data.decode("utf-8", "replace")):
            parts.append(escape(shown) if kind == "text" else
                         f"<b style='color:{'#7cfc00' if kind == 'bit' else '#ffd166'}'>"
                         f"[{escape(shown)}]</b>")
        return f"<div class=copy>{''.join(parts)}</div>"
    if lock.tool == "meta":
        rows = "".join(f"<tr><td>{escape(k)}</td><td>{escape(v)}</td></tr>"
                       for k, v in meta_tool(data).items())
        return f"<p class=dim>docProps/core.xml</p><table>{rows}</table>"
    if lock.tool == "dots":
        rows = "".join(f"<tr><td>{escape(k)}</td><td>{escape(v)}</td></tr>"
                       for k, v in dots_tool(data).items())
        return f"<p class=dim>Decoded C7 grid</p><table>{rows}</table>"
    if lock.tool == "examine":
        found = room.examine_leak(team.token, data.decode("utf-8", "replace"))
        return findings_html(found).replace(f"{team.slug}:", "")
    raise ValueError("this lock has no tool")


def escape_app(room: EscapeRoom, site: Site):
    lock = threading.Lock()
    outputs: dict[str, str] = {}

    def handle(request: Request) -> Response | None:
        path = request.path
        if not path.startswith("/escape"):
            return None
        token = request.cookies.get("mh_team", "")
        if path == "/escape/tool" and request.method == "POST":
            team = room.team(token)
            outputs[token] = _run_tool(room, team, request)
            return Response.redirect("/escape")
        with lock:
            return _route(room, site, request, token, outputs)

    return handle


def _route(room: EscapeRoom, site: Site, request: Request, token: str,
           outputs: dict[str, str]) -> Response | None:
    path = request.path
    if path == "/escape/v":
        return Response.text(str(room.version))
    if path == "/escape/screen":
        site.need_host(request)
        join = site.join_urls[0] + "escape" if site.join_urls else "/escape"
        return Response(screen_page(room, join, site.pin))
    if request.method == "GET":
        if path == "/escape":
            if token not in room.teams:
                return Response(join_page())
            return Response(team_page(room, room.teams[token], outputs.get(token, "")))
        if path.startswith("/escape/file/"):
            name = path.removeprefix("/escape/file/")
            return Response(room.file(token, name), kind="application/octet-stream",
                            headers={"Content-Disposition": f'attachment; filename="{name}"'})
        return None
    if path == "/escape/join":
        site.check_pin(request.fields.get("pin", ""))
        return Response.redirect("/escape", f"mh_team={room.join(request.fields.get('name', ''))}")
    if path == "/escape/start":
        site.need_host(request)
        room.start()
        return Response.redirect("/escape/screen")
    if path == "/escape/answer":
        if room.answer(token, request.fields.get("answer", "")):
            outputs.pop(token, None)
        return Response.redirect("/escape")
    if path == "/escape/hint":
        room.hint(token)
        return Response.redirect("/escape")
    return None
