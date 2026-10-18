"""Scenario-specific evidence for the seven cases (SPEC Section 9).

Each builder receives the rendered inputs and a seeded ``random.Random`` and
returns (evidence path, auxiliary paths, truth fields). Every planted fact goes
into ``ground_truth.json``; nothing is hard-coded in the UI or validator.
Background rows come from ``logs_gen`` so a join is never a one-row lookup.
"""

from __future__ import annotations

import csv
import random
from datetime import UTC, date, datetime, time, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree
from PIL import Image, ImageDraw

from molehunt.attacks.transform import attack_text, simulate_print_scan
from molehunt.channels.docx_meta import derive_rsid
from molehunt.channels.printdots import DotMetadata, render_dot_grid
from molehunt.core.template import Choice, Template
from molehunt.game.logs_gen import background_events, device_for, ip_for, write_events_csv

THIRD_WORD = {"begin": "commence", "start": "commence", "check": "examine", "verify": "examine"}
CP_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NS = "http://purl.org/dc/elements/1.1/"
APP_NS = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"


def write_rows(path: Path, header: list[str], rows: list[tuple]) -> Path:
    """Write a small CSV with a header row."""
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def rewrite_slots(
    template: Template, leaker_bits: list[int], twin_bits: list[int], rng: random.Random,
    *, tie_slots: int = 20, extra_rate: float = 0.15,
) -> tuple[str, list[int]]:
    """Case 2: the reporter rewrites some slot words (erasures). Early slots where
    leaker and twin differ are rewritten until 20 slots agree, so the two members
    tie on the first 20 readable slots; later slots separate them."""
    erased: list[int] = []
    agreed = 0
    out = []
    slot = 0
    for node in template.nodes:
        if not isinstance(node, Choice):
            out.append(node.text)
            continue
        chosen = node.zero if leaker_bits[slot] == 0 else node.one
        early_conflict = agreed < tie_slots and leaker_bits[slot] != twin_bits[slot]
        if early_conflict or rng.random() < extra_rate:
            erased.append(slot)
            out.append(THIRD_WORD.get(chosen.casefold(), "the"))
        else:
            agreed += 1
            out.append(chosen)
        slot += 1
    return "".join(out), erased


def print_case(public: Path, roster: list[str], leaker: str, rng: random.Random) -> tuple:
    """Case 3: aligned scan, rotated phone photo, print/badge logs, directory."""
    printed_on = date(2025, 1, 1) + timedelta(days=rng.randrange(365))
    minute = rng.randrange(60, 1380)
    printer_id = rng.randrange(1, 256)
    metadata = DotMetadata(printer_id, printed_on, minute)
    page = Image.new("RGB", (1024, 1400), "white")
    draw = ImageDraw.Draw(page)
    for line in range(30):
        draw.rectangle((140, 260 + line * 34, 140 + rng.randrange(500, 760), 268 + line * 34),
                       fill="#C8C8C8")
    scan = public / "scan.png"
    render_dot_grid(page, metadata, origin=(16, 16), cell_size=6, radius=1).save(scan)
    yellow = render_dot_grid(page, metadata, origin=(40, 40), cell_size=6, radius=1,
                             color="#F2D400")
    angle = rng.choice((-1, 1)) * rng.uniform(2.0, 4.0)
    photo = yellow.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor="white")
    photo_path = public / "photo.png"
    simulate_print_scan(photo, strength=0.2, seed=rng.randrange(1 << 30)).save(photo_path)
    at = datetime.combine(printed_on, time.min, tzinfo=UTC) + timedelta(minutes=minute)
    co_printer = rng.choice([item for item in roster if item != leaker])
    device = f"PRN-{printer_id:03d}"
    planted = [
        (at - timedelta(minutes=45), leaker, "badge_entry"),
        (at - timedelta(minutes=18), leaker, "document_open"),
        (at, leaker, "print_job"),
        (at + timedelta(minutes=2), co_printer, "print_job"),
        (at + timedelta(minutes=12), leaker, "badge_exit"),
    ]
    events = write_rows(public / "print_events.csv",
                        ["timestamp", "employee_id", "event", "device_id", "printer_id"],
                        [(t.isoformat(timespec="seconds"), who, what, device, printer_id)
                         for t, who, what in planted])
    noise = background_events(roster, at - timedelta(hours=8), days=1, rng=rng, daily_rate=2)
    jobs = [(e.timestamp, e.employee_id, f"PRN-{rng.randrange(1, 256):03d}") for e in noise
            if e.event == "print_job"]
    jobs += [(at, leaker, device), (at + timedelta(minutes=2), co_printer, device)]
    jobs_path = write_rows(public / "print_jobs.csv", ["timestamp", "employee_id", "printer"],
                           [(t.isoformat(timespec="seconds"), w, p) for t, w, p in sorted(jobs)])
    badge = [(at - timedelta(minutes=45), leaker, "badge_entry"),
             (at - timedelta(minutes=30), co_printer, "badge_entry")]
    badge += [(e.timestamp, e.employee_id, e.event) for e in noise if e.event.startswith("badge")]
    badge_path = write_rows(public / "badge_log.csv", ["timestamp", "employee_id", "event"],
                            [(t.isoformat(timespec="seconds"), w, e) for t, w, e in sorted(badge)])
    directory = write_rows(public / "directory.csv", ["printer", "floor"],
                           [(device, "3"), ("PRN-000", "1")])
    truth = {"printer_id": printer_id, "printed_on": printed_on.isoformat(),
             "minute_of_day": minute, "grid_origin": [16, 16], "grid_cell_size": 6,
             "photo_angle": round(angle, 3), "pool": sorted({leaker, co_printer})}
    return scan, (events, photo_path, jobs_path, badge_path, directory), truth


def ooxml_decoys(docx: bytes, roster: list[str], leaker: str, rng: random.Random) -> tuple:
    """Case 4: clear the author, point lastModifiedBy and Template at decoys."""
    decoy = rng.choice([item for item in roster if item != leaker])
    template = f"Template-{rng.randrange(10, 99)}.dotx"
    with ZipFile(BytesIO(docx)) as source:
        parts = {info: source.read(info.filename) for info in source.infolist()}
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as package:
        for info, data in parts.items():
            if info.filename == "docProps/core.xml":
                root = etree.fromstring(data)
                for tag, value in ((f"{{{DC_NS}}}creator", ""),
                                   (f"{{{CP_NS}}}lastModifiedBy", decoy)):
                    node = root.find(tag)
                    if node is None:
                        node = etree.SubElement(root, tag)
                    node.text = value
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            elif info.filename == "docProps/app.xml":
                root = etree.fromstring(data)
                node = root.find(f"{{{APP_NS}}}Template")
                if node is None:
                    node = etree.SubElement(root, f"{{{APP_NS}}}Template")
                node.text = template
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            package.writestr(info, data)
    return output.getvalue(), decoy, template


def rsid_registry(public: Path, key: bytes, roster: list[str], template: str, decoy: str) -> tuple:
    """IT registry of each employee's rsidRoot plus the template owner record."""
    rsids = write_rows(public / "rsid_registry.csv", ["employee_id", "rsid_root"],
                       [(item, derive_rsid(key, item)) for item in roster])
    templates = write_rows(public / "template_registry.csv", ["template", "owner"],
                           [(template, decoy)])
    return rsids, templates


def partial_leak(text: str, keep: list[int]) -> str:
    """Case 5: keep the chosen paragraphs (lines), then normalise lightly."""
    lines = text.split("\n")
    kept = "\n".join(lines[index] for index in keep)
    return attack_text(attack_text(kept, "A5", strength=1.0), "A4", strength=1.0)


def account_logs(public: Path, roster: list[str], owner: str, actor: str,
                 rng: random.Random) -> tuple[tuple[Path, ...], dict[str, Any]]:
    """Case 7: owner on leave; login 02:13 and download 02:14 from a VPN IP that
    DHCP maps to the actor's workstation, actor badged in at 01:50."""
    day = date(2025, 1, 1) + timedelta(days=rng.randrange(300))
    night = datetime.combine(day, time(2, 13), tzinfo=UTC)
    vpn_ip = f"10.99.{rng.randrange(1, 250)}.{rng.randrange(2, 250)}"
    mac = ":".join(f"{rng.randrange(256):02x}" for _ in range(6))
    noise = background_events(roster, night - timedelta(days=1, hours=2), days=2, rng=rng)
    auth = [(e.timestamp, e.employee_id, "login", e.ip) for e in noise if e.event == "login"]
    auth += [(night, owner, "login", vpn_ip), (night + timedelta(minutes=1), owner, "download", vpn_ip)]
    paths = (
        write_rows(public / "auth_log.csv", ["timestamp", "employee_id", "event", "ip"],
                   [(t.isoformat(timespec="seconds"), w, e, i) for t, w, e, i in sorted(auth)]),
        write_rows(public / "vpn_log.csv", ["timestamp", "account", "vpn_ip", "client_mac"],
                   [(night.isoformat(timespec="seconds"), owner, vpn_ip, mac)]),
        write_rows(public / "dhcp_leases.csv", ["ip", "mac", "hostname", "lease_start"],
                   [(vpn_ip, mac, device_for(actor), (night - timedelta(hours=1)).isoformat())]
                   + [(ip_for(item), f"02:00:00:00:00:{index:02x}", device_for(item), "")
                      for index, item in enumerate(roster)]),
        write_rows(public / "badge_log.csv", ["timestamp", "employee_id", "event"],
                   [((night - timedelta(minutes=23)).isoformat(timespec="seconds"), actor,
                     "badge_entry")]),
        write_rows(public / "leave_calendar.csv", ["employee_id", "from", "to", "note"],
                   [(owner, (day - timedelta(days=3)).isoformat(),
                     (day + timedelta(days=4)).isoformat(), "annual leave abroad")]),
    )
    events = write_events_csv(public / "office_events.csv", noise)
    truth = {"probable_actor": actor, "vpn_ip": vpn_ip, "mac": mac,
             "login_at": night.isoformat(), "alternative": "owner shared credentials"}
    return (*paths, events), truth
