"""Tiny LAN web server: parses requests once and hands them to the app modules.

Stdlib only (``ThreadingHTTPServer``). Each app (hub, lab, game, escape) has a
``handle(request) -> Response | None``; the first app that answers wins. Errors
come back as a themed page with the right status code.

Safety: bodies over 2 MB are refused, uploads are kept in memory and never saved
under a client-chosen name, static files come only from ``web/static``, joining
needs the 6-digit PIN, and host actions need the host key (a cookie set from the
link printed in the host console). No internet access, no scanning. Apps keep
their own locks, so a slow tool (dot decoding) never freezes the other screens.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from email.parser import BytesParser
from email.policy import default as email_policy
from html import escape
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from molehunt.web.theme import page, static_file

MAX_BODY = 2 * 1024 * 1024


@dataclass
class Request:
    method: str
    path: str
    query: dict[str, str]
    fields: dict[str, str]
    cookies: dict[str, str]
    upload: tuple[str, bytes] | None = None


@dataclass
class Response:
    body: bytes | str
    status: int = 200
    kind: str = "text/html; charset=utf-8"
    headers: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def redirect(location: str, cookie: str = "") -> Response:
        headers = {"Location": location}
        if cookie:
            headers["Set-Cookie"] = f"{cookie}; Path=/; SameSite=Lax; HttpOnly"
        return Response(b"", 303, "text/plain", headers)

    @staticmethod
    def text(message: str, status: int = 200) -> Response:
        return Response(message, status, "text/plain; charset=utf-8")

    @staticmethod
    def oops(message: str, status: int) -> Response:
        body = (f"<div class=card><h2>Spooky error</h2><p>{escape(message)}</p>"
                "<p><a class=btn href='javascript:history.back()'>Go back</a></p></div>")
        return Response(page("Error", body), status)


App = Callable[[Request], "Response | None"]


def _parse(handler: BaseHTTPRequestHandler, method: str) -> Request:
    url = urlsplit(handler.path)
    query = {k: v[0] for k, v in parse_qs(url.query).items()}
    cookies = {k: m.value for k, m in SimpleCookie(handler.headers.get("Cookie", "")).items()}
    fields: dict[str, str] = {}
    upload = None
    if method == "POST":
        length = int(handler.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise OverflowError
        body = handler.rfile.read(length)
        kind = handler.headers.get("Content-Type", "")
        if kind.startswith("multipart/form-data"):
            message = BytesParser(policy=email_policy).parsebytes(
                f"Content-Type: {kind}\r\n\r\n".encode() + body)
            for part in message.iter_parts():
                name = part.get_param("name", header="content-disposition") or ""
                data = part.get_payload(decode=True) or b""
                if part.get_filename():
                    if data:
                        upload = (part.get_filename(), data)
                else:
                    fields[name] = data.decode("utf-8", "replace")
        else:
            fields = {k: v[0] for k, v in parse_qs(body.decode("utf-8", "replace")).items()}
    return Request(method, url.path, query, fields, cookies, upload)


def make_handler(apps: Sequence[App]) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args) -> None:  # keep the host console quiet
            return

        def _send(self, response: Response) -> None:
            body = response.body.encode() if isinstance(response.body, str) else response.body
            self.send_response(response.status)
            self.send_header("Content-Type", response.kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for name, value in response.headers.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def _serve(self, method: str) -> None:
            try:
                request = _parse(self, method)
            except OverflowError:
                self._send(Response.text("upload too large (2 MB limit)", 413))
                return
            if request.path.startswith("/static/"):
                found = static_file(request.path.removeprefix("/static/"))
                self._send(Response(found[0], 200, found[1]) if found
                           else Response.text("not found", 404))
                return
            try:
                for app in apps:
                    response = app(request)
                    if response is not None:
                        break
                else:
                    response = Response.oops("Nothing haunts this address.", 404)
            except PermissionError as error:
                response = Response.oops(str(error) or "wrong PIN", 403)
            except (ValueError, OSError) as error:
                response = Response.oops(f"error: {error}", 400)
            self._send(response)

        def do_GET(self) -> None:
            self._serve("GET")

        def do_POST(self) -> None:
            self._serve("POST")

    return Handler


class _Server(ThreadingHTTPServer):
    # On Windows SO_REUSEADDR lets a second server silently share a busy port.
    allow_reuse_address = sys.platform != "win32"
    daemon_threads = True


def serve(apps: Sequence[App], host: str, port: int) -> ThreadingHTTPServer:
    """Create (not start) the server; a busy port raises OSError."""
    return _Server((host, port), make_handler(apps))
