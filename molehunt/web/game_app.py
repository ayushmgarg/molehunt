"""Find the Mole routes. Players are identified by a random cookie set when they join.

GET  /game          join form, or this player's phone view
POST /game/join     nickname + PIN -> cookie ``mh_game``
POST /game/leak     mole's scrub tools (checkboxes ``t_<tool>``)
POST /game/probe    spend tokens on a forensic tool
POST /game/bet      suspect + chips
GET  /game/copy.txt this player's fingerprinted copy
GET  /game/v        version number (pages poll it and reload on change)
GET  /game/screen   projector (host only); POST /game/start, /game/reveal (host only)
"""

from __future__ import annotations

import threading

from molehunt.game.mole_game import TOOLS, MoleGame
from molehunt.web.game_pages import join_page, phone_page, screen_page
from molehunt.web.hub import Site
from molehunt.web.server import Request, Response


def game_app(game: MoleGame, site: Site):
    lock = threading.Lock()

    def handle(request: Request) -> Response | None:
        if not request.path.startswith("/game"):
            return None
        with lock:
            return _route(game, site, request)

    return handle


def _route(game: MoleGame, site: Site, request: Request) -> Response | None:
    path = request.path
    me = game.players.get(request.cookies.get("mh_game", ""))
    if path == "/game/v":
        return Response.text(str(game.version))
    if path == "/game/screen":
        site.need_host(request)
        join = site.join_urls[0] + "game" if site.join_urls else "/game"
        return Response(screen_page(game, join, site.pin))
    if request.method == "GET":
        if path == "/game":
            return Response(phone_page(game, me) if me else join_page())
        if path == "/game/copy.txt" and me:
            return Response(game.copy_text(me.agent).encode("utf-8"),
                            kind="text/plain; charset=utf-8", headers={
                                "Content-Disposition": f'attachment; filename="{me.agent}.txt"'})
        return None
    if path == "/game/join":
        site.check_pin(request.fields.get("pin", ""))
        token = game.join(request.fields.get("name", ""))
        return Response.redirect("/game", f"mh_game={token}")
    if path in {"/game/start", "/game/reveal"}:
        site.need_host(request)
        if path == "/game/start":
            game.start_round(request.fields.get("mode", "solo"))
        else:
            game.reveal()
        return Response.redirect("/game/screen")
    if me is None:
        raise PermissionError("join the game first")
    fields = request.fields
    if path == "/game/leak":
        game.submit_leak(me.agent, [key for key in TOOLS if fields.get(f"t_{key}")])
    elif path == "/game/probe":
        game.probe(me.agent, fields.get("probe", ""), fields.get("target", ""))
    elif path == "/game/bet":
        game.bet(me.agent, fields.get("suspect", ""), int(fields.get("chips", "1") or 1))
    else:
        return None
    return Response.redirect("/game")
