"""Live LAN demo: one laptop hosts, others request copies and upload leaks.

Opt-in exception to the no-network rule (logged in docs/DECISIONS.md). The host
runs a stdlib ``ThreadingHTTPServer``. Every action needs a 6-digit PIN shown on
the host screen. Routes: ``/`` join page, ``/issue`` (POST: employee id + format
-> fingerprinted copy download), ``/leak`` (POST: uploaded file or pasted text ->
intake with hash + custody, then analysis), ``/board`` (host dashboard, refreshes
itself), ``/board.json``. Uploads are capped at 2 MB, saved under generated
names (no client path is trusted), and only .txt/.md/.docx/.png are accepted.
A PNG is read with the classical OCR and attributed like text; if it holds no
readable text, its C7 dots are decoded and the station byte is matched against
each employee's keyed station id, naming candidate copies.
"""

from __future__ import annotations

import hmac
import json
import secrets
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.parser import BytesParser
from email.policy import default as email_policy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from molehunt.analysis import analyze_text, evidence_text
from molehunt.channels.dot_locate import scan_dot_grid
from molehunt.core.keys import digest
from molehunt.detect.ingest import ingest
from molehunt.intake_service import intake_case
from molehunt.issuance import issue_registered_copy, register_master_file
from molehunt.live_pages import board_page, join_page, result_page
from molehunt.registry import get_master, initialize_database

MAX_UPLOAD = 2 * 1024 * 1024
ALLOWED = {".txt", ".md", ".docx", ".png", ".jpg", ".jpeg"}


@dataclass
class LiveState:
    """Host configuration plus the in-memory list of analysed leaks."""

    master: Path
    roster: list[str]
    key: bytes
    database: Path
    workdir: Path
    pin: str = field(default_factory=lambda: f"{secrets.randbelow(10**6):06d}")
    master_id: str = "LIVE"
    leaks: list[dict] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def prepare(self) -> None:
        """Register the master once so issued copies are recorded."""
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.master_id = f"LIVE-{self.master.stem}"
        initialize_database(self.database)
        if get_master(self.database, self.master_id) is None:
            register_master_file(self.database, self.key, self.master, master_id=self.master_id)

    def issue(self, employee: str, fmt: str) -> Path:
        if employee not in self.roster:
            raise ValueError("unknown employee id")
        if fmt not in {"txt", "docx", "pdf", "png"}:
            raise ValueError("format must be txt, docx, pdf, or png")
        with self.lock:
            stamp = datetime.now(UTC).strftime("%H%M%S%f")
            path = self.workdir / "issued" / f"{employee}-{stamp}.{fmt}"
            issue_registered_copy(self.database, self.key, employee, self.master_id, path)
        return path

    def analyse(self, name: str, data: bytes) -> dict:
        """Intake the upload (hash + custody) and attribute it."""
        suffix = Path(name).suffix.casefold() or ".txt"
        if suffix not in ALLOWED:
            raise ValueError("upload must be .txt, .md, .docx, .png, or .jpg")
        with self.lock:
            existing = [int(path.name.split("-")[1]) for path in
                        (self.workdir / "evidence").glob("LIVE-[0-9][0-9][0-9]")]
            number = max([len(self.leaks), *existing]) + 1
            case_id = f"LIVE-{number:03d}"
            upload = self.workdir / "uploads" / f"{case_id}{suffix}"
            upload.parent.mkdir(parents=True, exist_ok=True)
            upload.write_bytes(data)
            intake = intake_case(upload, case_id, actor="live-host",
                                 root=self.workdir / "evidence", database=self.database)
        record = {"case": case_id, "received": datetime.now(UTC).isoformat(timespec="seconds"),
                  "file": name, "sha256": intake.intake.sha256}
        evidence = ingest(intake.intake.working_copy)
        text = evidence_text(evidence)
        if suffix in {".png", ".jpg", ".jpeg"} and len(text.split()) < 20:
            record.update(self._dots(upload))
        else:
            result = analyze_text(self.master.read_text(encoding="utf-8"), self.key,
                                  self.roster, text)
            decision = result.decision()
            top = result.scores[0]
            record.update({
                "outcome": decision.outcome, "top": top.candidate_id,
                "log10_lr": round(top.log10_lr, 2),
                "observed": f"{result.observed_slots}/{len(result.observations)}",
                "statement": decision.statement,
                "ranking": [(s.candidate_id, s.matches, s.observed_slots, round(s.log10_lr, 2))
                            for s in result.scores[:5]],
            })
        with self.lock:
            self.leaks.append(record)
        return record

    def _dots(self, path: Path) -> dict:
        from PIL import Image

        with Image.open(path) as image:
            meta = scan_dot_grid(image, channel="B", window=200).metadata
        matches = [item for item in self.roster
                   if digest(self.key, "pdf-dots", item)[0] == meta.printer_id]
        return {"outcome": "print dots decoded", "top": ", ".join(matches) or "none",
                "log10_lr": "-", "observed": "C7 grid",
                "statement": (f"Station {meta.printer_id}, printed {meta.printed_on}, minute "
                              f"{meta.minute_of_day}. Station matches copies of: "
                              f"{', '.join(matches) or 'nobody'} (a pool, not a person)."),
                "ranking": []}


def _handler(state: LiveState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: bytes, kind: str = "text/html; charset=utf-8",
                  status: int = 200, extra: dict | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            for header, value in (extra or {}).items():
                self.send_header(header, value)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args) -> None:  # keep the host console quiet
            return

        def _pin_ok(self, value: str) -> bool:
            return hmac.compare_digest(value.strip(), state.pin)

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path == "/":
                self._send(join_page(state.roster).encode())
            elif path == "/board":
                self._send(board_page(state.leaks).encode())
            elif path == "/board.json":
                self._send(json.dumps(state.leaks).encode(), "application/json")
            else:
                self._send(b"not found", "text/plain", 404)

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_UPLOAD:
                self._send(b"upload too large (2 MB limit)", "text/plain", 413)
                return
            body = self.rfile.read(length)
            kind = self.headers.get("Content-Type", "")
            try:
                if kind.startswith("multipart/form-data"):
                    message = BytesParser(policy=email_policy).parsebytes(
                        f"Content-Type: {kind}\r\n\r\n".encode() + body)
                    form = {part.get_param("name", header="content-disposition"): part
                            for part in message.iter_parts()}
                    fields = {k: v.get_content() for k, v in form.items()
                              if not v.get_filename()}
                    upload = next((v for v in form.values() if v.get_filename()), None)
                else:
                    fields = {k: v[0] for k, v in parse_qs(body.decode("utf-8")).items()}
                    upload = None
                fields = {k: v if isinstance(v, str) else v.decode() for k, v in fields.items()}
                if not self._pin_ok(fields.get("pin", "")):
                    self._send(b"wrong PIN", "text/plain", 403)
                    return
                if self.path == "/issue":
                    copy = state.issue(fields.get("employee", ""), fields.get("format", "txt"))
                    self._send(copy.read_bytes(), "application/octet-stream", extra={
                        "Content-Disposition": f'attachment; filename="{copy.name}"'})
                elif self.path == "/leak":
                    if upload is not None and upload.get_payload(decode=True):
                        name, data = upload.get_filename(), upload.get_payload(decode=True)
                    else:
                        name, data = "pasted.txt", fields.get("text", "").encode("utf-8")
                    if not data.strip():
                        raise ValueError("nothing uploaded")
                    self._send(result_page(state.analyse(name, data)).encode())
                else:
                    self._send(b"not found", "text/plain", 404)
            except (ValueError, OSError) as error:
                self._send(f"error: {error}".encode(), "text/plain", 400)

    return Handler


def make_server(state: LiveState, host: str, port: int) -> ThreadingHTTPServer:
    """Create (not start) the HTTP server for the live demo."""
    state.prepare()
    return ThreadingHTTPServer((host, port), _handler(state))
