"""End-to-end test of the live LAN demo server on loopback."""

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from molehunt.attacks.transform import attack_text
from molehunt.live import LiveState, make_server

MASTER = Path(__file__).parents[1] / "data" / "masters" / "m2_zoning.md"


@pytest.fixture
def server(tmp_path):
    state = LiveState(MASTER, [f"E{i:03}" for i in range(1, 13)], bytes(range(32)),
                      tmp_path / "r.sqlite3", tmp_path / "live")
    httpd = make_server(state, "127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield state, f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()
    httpd.server_close()


def _post(url: str, data: bytes, kind: str) -> bytes:
    request = urllib.request.Request(url, data=data, headers={"Content-Type": kind})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def test_issue_leak_and_board_round_trip(server) -> None:
    state, base = server
    page = urllib.request.urlopen(base + "/", timeout=10).read().decode()
    assert "Get your copy" in page and "E012" in page
    form = urllib.parse.urlencode({"employee": "E005", "format": "txt", "pin": state.pin})
    copy = _post(base + "/issue", form.encode(), "application/x-www-form-urlencoded")
    leak = attack_text(copy.decode("utf-8"), "A5", strength=1.0)

    boundary = "XyZ"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"pin\"\r\n\r\n{state.pin}\r\n"
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"leak.txt\"\r\nContent-Type: text/plain\r\n\r\n{leak}\r\n"
            f"--{boundary}--\r\n").encode()
    result = _post(base + "/leak", body, f"multipart/form-data; boundary={boundary}").decode()
    assert "LIVE-001" in result and "copy issued to E005" in result

    board = json.loads(urllib.request.urlopen(base + "/board.json", timeout=10).read())
    assert board[0]["outcome"] == "attribute" and board[0]["top"] == "E005"
    assert "E005" in urllib.request.urlopen(base + "/board", timeout=10).read().decode()
    assert (state.workdir / "evidence" / "LIVE-001" / "custody.log").is_file()


def test_wrong_pin_and_bad_requests_are_refused(server) -> None:
    state, base = server
    form = urllib.parse.urlencode({"employee": "E001", "pin": "000000x"}).encode()
    with pytest.raises(urllib.error.HTTPError) as caught:
        _post(base + "/issue", form, "application/x-www-form-urlencoded")
    assert caught.value.code == 403
    form = urllib.parse.urlencode({"employee": "E999", "pin": state.pin}).encode()
    with pytest.raises(urllib.error.HTTPError) as caught:
        _post(base + "/issue", form, "application/x-www-form-urlencoded")
    assert caught.value.code == 400
    form = urllib.parse.urlencode({"text": "", "pin": state.pin}).encode()
    with pytest.raises(urllib.error.HTTPError) as caught:
        _post(base + "/leak", form, "application/x-www-form-urlencoded")
    assert caught.value.code == 400
