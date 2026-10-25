"""Both LAN games played over real HTTP on loopback, with cookies like phones."""

import http.cookiejar
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from molehunt.game.escape_room import EscapeRoom
from molehunt.game.mole_game import MoleGame
from molehunt.live import LiveState, make_server

KEY = bytes(range(32))
ROOT = Path(__file__).parents[1]
MASTER = ROOT / "data" / "masters" / "live" / "m8_midnight_carnival.md"


@pytest.fixture
def site(tmp_path):
    state = LiveState(MASTER, [f"A{i:02}" for i in range(1, 6)], KEY,
                      tmp_path / "r.sqlite3", tmp_path / "live")
    game, room = MoleGame(MASTER, KEY, seed=5), EscapeRoom(MASTER, KEY, seed=5)
    httpd = make_server(state, "127.0.0.1", 0, game=game, escape=room)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield state, game, room, f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()
    httpd.server_close()


class Phone:
    """A browser with its own cookie jar."""

    def __init__(self, base: str) -> None:
        self.base = base
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def get(self, path: str) -> str:
        return self.opener.open(self.base + path, timeout=60).read().decode()

    def post(self, path: str, **fields) -> str:
        data = urllib.parse.urlencode(fields).encode()
        return self.opener.open(self.base + path, data, timeout=60).read().decode()


def test_static_assets_and_host_lock(site) -> None:
    state, _, _, base = site
    phone = Phone(base)
    assert "Creepster" in phone.get("/game")
    font = urllib.request.urlopen(base + "/static/Creepster-Regular.ttf", timeout=10)
    assert font.headers["Content-Type"] == "font/ttf"
    with pytest.raises(urllib.error.HTTPError) as caught:
        phone.get("/static/../live.py")
    assert caught.value.code == 404
    with pytest.raises(urllib.error.HTTPError) as caught:
        phone.get("/game/screen")
    assert caught.value.code == 403
    host = Phone(base)
    assert "Host console" in host.get(f"/host?k={state.host_key}")
    assert state.pin in host.get("/game/screen")


def test_find_the_mole_round_over_http(site) -> None:
    state, game, _, base = site
    host = Phone(base)
    host.get(f"/host?k={state.host_key}")
    phones = [Phone(base) for _ in range(4)]
    with pytest.raises(urllib.error.HTTPError):
        phones[0].post("/game/join", name="x", pin="bad")
    for index, phone in enumerate(phones):
        assert "Agent A0" in phone.post("/game/join", name=f"ghoul{index}", pin=state.pin)
    host.post("/game/start", mode="solo")
    mole = game.round.moles[0]
    mole_phone = phones[int(mole[1:]) - 1]
    assert "You are the mole" in mole_phone.get("/game")
    mole_phone.post("/game/leak", t_strip="on", t_quotes="on")
    detective = phones[0] if mole_phone is not phones[0] else phones[1]
    page = detective.post("/game/probe", probe="ink", target=mole)
    assert "Scrub check" in page
    detective.post("/game/bet", suspect=mole, chips="2")
    reveal = host.post("/game/reveal")
    assert "Forensic reveal" in reveal and "caught" in reveal and "id=meter" in reveal
    assert re.search(r"This round: <b>\+\d+", detective.get("/game"))


def test_escape_room_over_http(site) -> None:
    state, _, _, base = site
    host, team = Phone(base), Phone(base)
    host.get(f"/host?k={state.host_key}")
    assert "Waiting for the host" in team.post("/escape/join", name="Night Owls", pin=state.pin)
    host.post("/escape/start")
    page = team.get("/escape")
    assert "The doctored voicemail" in page and "voicemail_A.txt" in page
    record = team.get("/escape/file/custody_record.txt")
    hashes = {}
    for letter in "ABCD":
        data = team.get(f"/escape/file/voicemail_{letter}.txt")
        result = team.post("/escape/tool", text=data)
        hashes[letter] = re.search(r"SHA-256: <code[^>]*>([0-9a-f]{64})", result).group(1)
    original = next(letter for letter, value in hashes.items() if value in record)
    after = team.post("/escape/answer", answer=original)
    assert "Invisible ink" in after
    with pytest.raises(urllib.error.HTTPError):
        team.get("/escape/file/leaked_memo.txt")
    assert "Night Owls" in host.get("/escape/screen")
