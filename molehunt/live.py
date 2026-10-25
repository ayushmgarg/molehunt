"""Live LAN mode: the forensic lab state, plus the factory that builds the server.

Opt-in exception to the no-network rule (logged in docs/DECISIONS.md). The lab
issues fingerprinted copies and examines uploaded leaks: every upload is taken in
as evidence first (SHA-256, read-only original, custody entry), then examined
with ``forensics.examine`` (fingerprint, canaries, scrub check, heatmap, tree).
Uploads are capped at 2 MB, saved under generated names (no client path is
trusted), and only .txt/.md/.docx/.png/.jpg are accepted.
A PNG is read with the classical OCR and attributed like text; if it holds no
readable text, its C7 dots are decoded and the station byte is matched against
each employee's keyed station id, naming candidate copies.
"""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http.server import ThreadingHTTPServer
from pathlib import Path

from molehunt.analysis import evidence_text
from molehunt.channels.dot_locate import scan_dot_grid
from molehunt.core.keys import digest
from molehunt.detect.ingest import ingest
from molehunt.forensics import Examination, examine
from molehunt.intake_service import intake_case
from molehunt.issuance import issue_registered_copy, register_master_file
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
    host_key: str = field(default_factory=lambda: secrets.token_urlsafe(9))
    leaks: list[dict] = field(default_factory=list)
    findings: dict[str, Examination] = field(default_factory=dict)
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
            found = examine(self.master.read_text(encoding="utf-8"), self.key, self.roster, text)
            result, decision = found.result, found.decision
            top = result.scores[0]
            self.findings[case_id] = found
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


def make_server(state: LiveState, host: str, port: int, *, game=None, escape=None,
                join_urls: tuple[str, ...] = ()) -> ThreadingHTTPServer:
    """Create (not start) the LAN server with the hub, lab, and optional games."""
    from molehunt.web.escape_app import escape_app
    from molehunt.web.game_app import game_app
    from molehunt.web.hub import Site, hub_app
    from molehunt.web.lab_app import lab_app
    from molehunt.web.server import serve

    state.prepare()
    site = Site(state.pin, state.host_key, join_urls)
    apps = [hub_app(site), lab_app(state, site)]
    if game is not None:
        apps.append(game_app(game, site))
    if escape is not None:
        apps.append(escape_app(escape, site))
    return serve(apps, host, port)
