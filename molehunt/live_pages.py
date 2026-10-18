"""Server-rendered HTML for the live LAN demo (no JavaScript framework).

All dynamic values pass through ``html.escape``; the board refreshes itself every
3 seconds with a meta tag so the projector view updates while leaks arrive.
"""

from __future__ import annotations

from html import escape

_STYLE = """<style>
body{background:#14171A;color:#EFE9DC;font-family:Segoe UI,Arial,sans-serif;margin:24px;max-width:960px}
h1,h2{color:#D9822B} input,select,textarea,button{font-size:16px;padding:8px;margin:4px 0}
button{background:#D9822B;color:#1B1F24;border:0;font-weight:bold}
table{border-collapse:collapse;width:100%} td,th{border:1px solid #3A4048;padding:6px;text-align:left}
.card{background:#1B1F24;border:1px solid #3A4048;padding:16px;margin:16px 0}
.attribute{color:#ff8a80}.ok{color:#9be29b}
</style>"""


def _page(title: str, body: str, refresh: bool = False) -> str:
    meta = '<meta http-equiv="refresh" content="3">' if refresh else ""
    return (f"<!doctype html><html><head><meta charset='utf-8'>{meta}"
            f"<meta name='viewport' content='width=device-width'><title>{escape(title)}</title>"
            f"{_STYLE}</head><body>{body}</body></html>")


def join_page(roster: list[str]) -> str:
    """Participant page: get a copy, or leak one."""
    options = "".join(f"<option>{escape(item)}</option>" for item in roster)
    return _page("MoleHunt Live", f"""
<h1>MoleHunt Live</h1><p>Synthetic demo. Each copy is fingerprinted to the employee
you pick. Ask the host for the PIN.</p>
<div class=card><h2>1. Get your copy</h2><form method=post action=/issue>
Employee <select name=employee>{options}</select>
Format <select name=format><option>txt</option><option>docx</option><option>pdf</option><option>png</option></select>
PIN <input name=pin size=6 required> <button>Download my copy</button></form></div>
<div class=card><h2>2. Leak it (edited, pasted, or photographed)</h2>
<form method=post action=/leak enctype=multipart/form-data>
File (.txt .md .docx .png .jpg) <input type=file name=file><br>
or paste text<br><textarea name=text rows=6 cols=80></textarea><br>
PIN <input name=pin size=6 required> <button>Send leak to the examiner</button></form></div>
<p><a href=/board style="color:#D9822B">Examiner board</a></p>""")


def result_page(record: dict) -> str:
    """Shown to the leaker after upload."""
    return _page("Leak received", f"""
<h1>Leak received: {escape(record['case'])}</h1>
<p>SHA-256 {escape(record['sha256'])} (custody entry written).</p>
<div class=card><b>Detector: {escape(str(record['outcome']))}</b>
<p>{escape(str(record['statement']))}</p></div><p><a href=/ style="color:#D9822B">Back</a></p>""")


def board_page(leaks: list[dict]) -> str:
    """Projector view: newest leak first, with the top of the ranking."""
    cards = []
    for record in reversed(leaks):
        ranking = "".join(
            f"<tr><td>{escape(c)}</td><td>{m}/{n}</td><td>{lr}</td></tr>"
            for c, m, n, lr in record.get("ranking", []))
        table = (f"<table><tr><th>Copy</th><th>Matches</th><th>log10 LR</th></tr>{ranking}"
                 "</table>") if ranking else ""
        css = "attribute" if record["outcome"] == "attribute" else "ok"
        cards.append(
            f"<div class=card><h2>{escape(record['case'])} - {escape(record['file'])}</h2>"
            f"<p>{escape(record['received'])} UTC - SHA-256 {escape(record['sha256'][:16])}... "
            f"- slots {escape(str(record['observed']))}</p>"
            f"<p class={css}><b>{escape(str(record['outcome']))}: {escape(str(record['top']))}"
            f"</b></p><p>{escape(str(record['statement']))}</p>{table}</div>")
    body = "".join(cards) or "<p>Waiting for leaks...</p>"
    return _page("MoleHunt Live board", f"<h1>Examiner board</h1>{body}", refresh=True)
