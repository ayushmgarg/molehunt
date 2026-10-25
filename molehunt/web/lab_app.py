"""Forensic Lab screens: get a fingerprinted copy, leak it, see the full examination.

Routes: ``/lab`` (two forms), ``/issue`` (POST -> copy download), ``/leak`` (POST
file or pasted text -> intake + examine -> findings page), ``/lab/case/<id>``
(findings again), ``/board`` (projector list, live), ``/board.json``.
Every POST needs the PIN.
"""

from __future__ import annotations

import json
from html import escape

from molehunt.live import LiveState
from molehunt.web.findings import METER_SCRIPT, findings_html
from molehunt.web.hub import Site
from molehunt.web.server import Request, Response
from molehunt.web.theme import icon, page, pill


def lab_page(roster: list[str]) -> str:
    options = "".join(f"<option>{escape(item)}</option>" for item in roster)
    return page("Forensic Lab", f"""<h1>Forensic Lab</h1>
<p class=dim>Each copy is fingerprinted to the employee you pick. Ask the host for the PIN.</p>
<div class=card><h2>{icon('ghost')}1. Get your copy</h2><form method=post action=/issue>
<label>Employee</label><select name=employee>{options}</select>
<label>Format</label><select name=format><option>txt</option><option>docx</option>
<option>pdf</option><option>png</option></select>
<label>PIN</label><input name=pin inputmode=numeric required>
<button class=big>Download my copy</button></form></div>
<div class=card><h2>{icon('skull')}2. Leak it</h2>
<p class=dim>Edit it, cut it, retype it, scrub it, or photograph a print. Then send it in.</p>
<form method=post action=/leak enctype=multipart/form-data>
<label>File (.txt .md .docx .png .jpg)</label><input type=file name=file>
<label>or paste text</label><textarea name=text rows=6></textarea>
<label>PIN</label><input name=pin inputmode=numeric required>
<button class=big>Send to the examiner</button></form></div>
<p><a href=/board>Examiner board</a></p>""")


def case_page(state: LiveState, case: str) -> str:
    record = next((item for item in state.leaks if item["case"] == case), None)
    if record is None:
        raise ValueError("unknown case")
    head = (f"<h1>{escape(case)}</h1><div class=card><p>Evidence <b>{escape(record['file'])}"
            f"</b> received {escape(record['received'])} UTC.</p><p class=dim>SHA-256 "
            f"{escape(record['sha256'])} - custody entry written, original kept read-only.</p>"
            f"<p>{escape(str(record['statement']))}</p></div>")
    found = state.findings.get(case)
    body = findings_html(found) if found else ""
    return page(case, head + body + "<p><a href=/lab>Back to the lab</a></p>",
                script=METER_SCRIPT if found else "")


def board_page(state: LiveState) -> str:
    cards = []
    for record in reversed(state.leaks):
        tone = "bad" if record["outcome"] == "attribute" else "warn"
        cards.append(
            f"<a class=card style='display:block;text-decoration:none' "
            f"href=/lab/case/{escape(record['case'])}><h2>{escape(record['case'])}</h2>"
            f"<p>{pill(str(record['outcome']), tone)} <b>{escape(str(record['top']))}</b> - "
            f"slots {escape(str(record['observed']))}</p>"
            f"<p class=dim>{escape(record['file'])} - SHA-256 {escape(record['sha256'][:16])}"
            f"...</p></a>")
    body = "".join(cards) or "<div class=card><p>Waiting for leaks...</p></div>"
    return page("Examiner board", f"<h1>Examiner board</h1>{body}",
                poll=("/board/v", str(len(state.leaks))))


def lab_app(state: LiveState, site: Site):
    def handle(request: Request) -> Response | None:
        path = request.path
        if request.method == "GET":
            if path == "/lab":
                return Response(lab_page(state.roster))
            if path == "/board":
                return Response(board_page(state))
            if path == "/board/v":
                return Response.text(str(len(state.leaks)))
            if path == "/board.json":
                return Response(json.dumps(state.leaks), kind="application/json")
            if path.startswith("/lab/case/"):
                return Response(case_page(state, path.removeprefix("/lab/case/")))
            return None
        if path not in {"/issue", "/leak"}:
            return None
        site.check_pin(request.fields.get("pin", ""))
        if path == "/issue":
            copy = state.issue(request.fields.get("employee", ""),
                               request.fields.get("format", "txt"))
            return Response(copy.read_bytes(), kind="application/octet-stream", headers={
                "Content-Disposition": f'attachment; filename="{copy.name}"'})
        if request.upload is not None:
            name, data = request.upload
        else:
            name, data = "pasted.txt", request.fields.get("text", "").encode("utf-8")
        if not data.strip():
            raise ValueError("nothing uploaded")
        record = state.analyse(name, data)
        return Response(case_page(state, record["case"]))

    return handle
