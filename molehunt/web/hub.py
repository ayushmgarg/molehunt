"""Front door of the LAN server: the home screen, the host console, PIN and host checks.

Home ``/`` shows three big doors: Find the Mole, Escape Room, Forensic Lab.
Host ``/host?k=<host key>`` stores the key in a cookie, then shows the PIN, the
join address, and links to each projector screen. The host key is printed only
in the terminal of the laptop that runs ``molehunt live``.
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from html import escape

from molehunt.web.server import Request, Response
from molehunt.web.theme import icon, page


@dataclass
class Site:
    """Shared secrets and addresses."""

    pin: str
    host_key: str
    join_urls: tuple[str, ...] = ()

    def check_pin(self, value: str) -> None:
        if not hmac.compare_digest(value.strip(), self.pin):
            raise PermissionError("wrong PIN - ask the host")

    def is_host(self, request: Request) -> bool:
        return hmac.compare_digest(request.cookies.get("mh_host", ""), self.host_key)

    def need_host(self, request: Request) -> None:
        if not self.is_host(request):
            raise PermissionError("host only - open the host link from the terminal")


def _door(href: str, name: str, title: str, text: str) -> str:
    return (f"<a class='card' href={href} style='display:block;text-decoration:none'>"
            f"<h2>{icon(name)}{escape(title)}</h2><p class=dim>{escape(text)}</p></a>")


def home_page() -> str:
    doors = (_door("/game", "ghost", "Find the Mole",
                   "Everyone gets a fingerprinted copy. One of you leaks it. Can the forensics "
                   "catch the mole before you do?")
             + _door("/escape", "lock-keyhole", "Escape Room",
                     "Six forensic locks, one clock. Hashes, invisible ink, metadata, "
                     "printer dots, logs, fingerprints.")
             + _door("/lab", "fingerprint", "Forensic Lab",
                     "Get a copy, leak it any way you like, and watch the examiner trace it."))
    return page("MoleHunt Live", "<h1>MoleHunt</h1><p class=dim>Halloween night at Hollowmere "
                "Studios. A secret memo is about to leak. All people and documents are "
                f"synthetic.</p><div class=grid>{doors}</div>")


def host_page(site: Site) -> str:
    urls = "".join(f"<p><b>{escape(url)}</b></p>" for url in site.join_urls) or (
        "<p class=dim>Open this server's address on the other devices.</p>")
    screens = "".join(f"<a class='btn big' href={href}>{icon(name)}{escape(label)}</a>"
                      for href, name, label in (("/game/screen", "ghost", "Find the Mole screen"),
                                                ("/escape/screen", "hourglass",
                                                 "Escape Room screen"),
                                                ("/board", "fingerprint", "Lab board")))
    return page("Host console", f"""<h1>Host console</h1>
<div class=card><p class=dim>PIN for players</p><div class=pin>{escape(site.pin)}</div>
<p class=dim>Players open:</p>{urls}</div><div class=card>{screens}</div>""")


def hub_app(site: Site):
    def handle(request: Request) -> Response | None:
        if request.path == "/":
            return Response(home_page())
        if request.path == "/host":
            key = request.query.get("k", "")
            if key and hmac.compare_digest(key, site.host_key):
                return Response.redirect("/host", f"mh_host={site.host_key}")
            site.need_host(request)
            return Response(host_page(site))
        return None

    return handle
