"""Halloween look for every LAN page: one stylesheet, page wrapper, icons, static files.

Assets live in ``molehunt/web/static`` and are served by the LAN server itself, so
the pages work with no internet: Creepster (titles, SIL OFL) and Special Elite
(case-file typewriter body, Apache 2.0) from Google Fonts, and Lucide icons (ISC).
Bats, moon, and fog are drawn with inline SVG and CSS. Licences sit next to the files.

Live updates: a page can pass ``poll=(url, version)``. A tiny script fetches the
url every 2 seconds and reloads the page when the returned version changes, so
phones and the projector follow the game without any framework.
"""

from __future__ import annotations

import base64
from html import escape
from pathlib import Path

STATIC = Path(__file__).with_name("static")
_TYPES = {".ttf": "font/ttf", ".svg": "image/svg+xml", ".txt": "text/plain; charset=utf-8"}

CSS = """
@font-face{font-family:Creepster;src:url(/static/Creepster-Regular.ttf)}
@font-face{font-family:Elite;src:url(/static/SpecialElite-Regular.ttf)}
:root{--bg:#0b0710;--panel:#1a1122cc;--line:#3b2650;--text:#f3e9d2;--dim:#a99bb5;
--pumpkin:#ff7518;--slime:#7cfc00;--blood:#ff3b3b;--ghost:#7d7590;--gold:#ffd166;--violet:#b48cff}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;color:var(--text);font:17px/1.5 Elite,'Courier New',monospace;
background:radial-gradient(ellipse at 50% -10%,#3a1b55 0,#0b0710 60%) fixed,var(--bg)}
main{max-width:980px;margin:0 auto;padding:24px 16px 80px;position:relative;z-index:2}
h1,h2{font-family:Creepster,Elite,cursive;letter-spacing:2px;color:var(--pumpkin);
text-shadow:0 0 12px #ff751866;margin:.2em 0;font-weight:normal}
h1{font-size:clamp(38px,8vw,64px)} h2{font-size:clamp(26px,5vw,36px)}
a{color:var(--gold)} small,.dim{color:var(--dim)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;
margin:16px 0;box-shadow:0 0 30px #00000088;backdrop-filter:blur(2px)}
.big{display:block;width:100%;text-align:center;padding:18px;font-size:22px;margin:10px 0}
button,.btn{font:inherit;cursor:pointer;background:var(--pumpkin);color:#1a0b00;border:0;
border-radius:10px;padding:10px 18px;font-weight:bold;text-decoration:none;display:inline-block}
button:hover,.btn:hover{filter:brightness(1.15);box-shadow:0 0 16px #ff7518aa}
button.ghost,.btn.ghost{background:transparent;color:var(--text);border:1px solid var(--line)}
input,select,textarea{font:inherit;background:#120a18;color:var(--text);border:1px solid var(--line);
border-radius:8px;padding:10px;width:100%;margin:6px 0}
label{display:block;margin-top:8px;color:var(--dim)}
table{border-collapse:collapse;width:100%} td,th{border-bottom:1px solid var(--line);padding:8px;text-align:left}
.pill{display:inline-block;border-radius:999px;padding:2px 12px;font-size:15px;border:1px solid}
.good{color:var(--slime);border-color:var(--slime)} .bad{color:var(--blood);border-color:var(--blood)}
.warn{color:var(--gold);border-color:var(--gold)}
.icon{width:1.3em;height:1.3em;vertical-align:-.25em;margin-right:6px}
.pin{font-size:clamp(40px,10vw,90px);color:var(--slime);font-family:Creepster,cursive;letter-spacing:8px}
.copy{white-space:pre-wrap;max-height:55vh;overflow:auto;background:#0e0814;padding:14px;
border-radius:10px;border:1px dashed var(--line);font-size:15px}
.heat{white-space:pre-wrap;line-height:1.9;font-size:15px}
.heat .match{background:#7cfc0033;border-bottom:2px solid var(--slime)}
.heat .mismatch{background:#ff3b3b44;border-bottom:2px solid var(--blood)}
.heat .erased{background:#7d759044;color:var(--dim);border-bottom:2px dotted var(--ghost)}
.heat .fact{background:#ffd16633;color:var(--gold);outline:1px solid var(--gold);border-radius:4px}
.heat .inv{font-size:10px;vertical-align:super;opacity:.9}
.heat .reveal{display:none}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
.moon{position:fixed;top:24px;right:5vw;width:110px;height:110px;border-radius:50%;z-index:0;
background:radial-gradient(circle at 35% 35%,#fff6d5,#f2d27a 60%,#c99a3b);box-shadow:0 0 80px #f2d27a88}
.fog{position:fixed;left:-50%;bottom:-40px;width:200%;height:180px;z-index:1;pointer-events:none;
background:radial-gradient(ellipse at center,#cfc3e033 0,transparent 60%);animation:fog 22s linear infinite}
@keyframes fog{from{transform:translateX(0)}to{transform:translateX(25%)}}
.bat{position:fixed;width:46px;z-index:1;fill:#2a1638;opacity:.9;filter:drop-shadow(0 0 3px #ff7518aa);animation:fly 18s linear infinite}
.bat.b2{top:22vh;animation-duration:24s;animation-delay:-8s;width:30px}
.bat.b3{top:12vh;animation-duration:30s;animation-delay:-15s;width:38px}
@keyframes fly{0%{transform:translate(-10vw,10vh)}50%{transform:translate(55vw,2vh)}
100%{transform:translate(110vw,14vh)}}
.gauge text{font-family:Elite,monospace;fill:var(--text)}
.timer{font-family:Creepster,cursive;font-size:48px;color:var(--gold)}
@media (prefers-reduced-motion:reduce){.bat,.fog{animation:none}}
"""

_BAT = ("<svg class='bat {cls}' viewBox='0 0 100 40' aria-hidden=true><path d='M50 12c3-6 5-6 6 0 "
        "6-8 14-10 24-8-6 3-8 8-7 14-5-4-10-3-13 2-3-4-7-4-10 0-3-5-8-6-13-2 1-6-1-11-7-14 "
        "10-2 18 0 24 8 1-6 3-6 6 0z'/></svg>")
DECOR = ("<div class=moon></div><div class=fog></div>"
         + "".join(_BAT.format(cls=cls) for cls in ("", "b2", "b3")))

_POLL = """<script>
(function(){var url=%r,v=%r;setInterval(function(){fetch(url,{cache:'no-store'})
.then(function(r){return r.text()}).then(function(t){if(t.trim()!==v){location.reload()}})
.catch(function(){})},2000)})();
</script>"""


def page(title: str, body: str, *, poll: tuple[str, str] | None = None, script: str = "",
         standalone: bool = False) -> str:
    """Wrap body HTML in the themed document; ``poll`` reloads on version change.

    ``standalone`` embeds the fonts as data URIs so a saved file looks the same offline."""
    extra = _POLL % poll if poll else ""
    css = CSS
    if standalone:
        for name in ("Creepster-Regular.ttf", "SpecialElite-Regular.ttf"):
            data = base64.b64encode((STATIC / name).read_bytes()).decode()
            css = css.replace(f"url(/static/{name})", f"url(data:font/ttf;base64,{data})")
    return (
        "<!doctype html><html lang=en><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>{escape(title)}</title><style>{css}</style></head>"
        f"<body>{DECOR}<main>{body}</main>{extra}{script}</body></html>"
    )


def icon(name: str) -> str:
    """Inline a Lucide icon (stroke follows the text colour)."""
    path = STATIC / f"{name}.svg"
    if not path.is_file():
        return ""
    svg = path.read_text(encoding="utf-8")
    svg = svg[svg.index("<svg"):]
    return svg.replace("<svg", "<svg class=icon", 1)


def static_file(name: str) -> tuple[bytes, str] | None:
    """Bytes and content type of a bundled asset; None for anything not in the folder."""
    if "/" in name or "\\" in name or name.startswith("."):
        return None
    path = STATIC / name
    if not path.is_file() or path.suffix not in _TYPES:
        return None
    return path.read_bytes(), _TYPES[path.suffix]


def pill(text: str, tone: str) -> str:
    """Small rounded label; tone is good, bad, or warn."""
    return f"<span class='pill {tone}'>{escape(text)}</span>"
