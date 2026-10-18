"""Each case is solvable end-to-end with library tools; wrong answers earn no finding."""

import csv
import json
import re
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from PIL import Image

from molehunt.channels.dot_locate import scan_dot_grid
from molehunt.core.autoslots import split_front_matter
from molehunt.core.template import parse_template
from molehunt.detect.tardos import accuse, calibrate_threshold, score_tardos_candidates
from molehunt.game.casebook import load_casebook
from molehunt.game.generator import generate_case
from molehunt.game.tools import document_order_bits, match_registry, read_registry
from molehunt.game.validator import Procedure, Submission, grade_case, parse_details

MASTER = "data/demo/master.md"
CASES = {definition.generator: definition for definition in load_casebook()}
CLEAN = Procedure(hashed=True, working_copy=True, notes=True, original_untouched=True)


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


TEMPLATE: dict[str, object] = {}


def _template():
    return TEMPLATE["current"]


def solve(kind: str, public: Path) -> Submission:
    """A player's reasoning, written as code against public files only."""
    if kind == "invisible_copy":
        text = (public / "leak.txt").read_text(encoding="utf-8")
        bits = [0 if ch == "\u200b" else 1 for ch in text if ch in "\u200b\u200c"]
        best = match_registry(bits, read_registry(public / "registry.csv"))[0]
        return Submission(best.employee_id, 0.95, {"bits": "".join(map(str, bits))})
    if kind == "edited_text":
        observed = document_order_bits(_template(), (public / "newspaper.txt").read_text("utf-8"))
        best = match_registry(observed, read_registry(public / "registry.csv"))[0]
        erased = ",".join(str(i + 1) for i, bit in enumerate(observed) if bit is None)
        return Submission(best.employee_id, 0.9, {"erased": erased})
    if kind == "print_timeline":
        with Image.open(public / "photo.png") as photo:
            found = scan_dot_grid(photo, channel="B", window=80).metadata
        moment = datetime.fromisoformat(found.printed_on.isoformat()) + timedelta(
            minutes=found.minute_of_day)
        pool = sorted({
            row["employee_id"] for row in _rows(public / "print_jobs.csv")
            if row["printer"] == f"PRN-{found.printer_id:03d}"
            and abs(datetime.fromisoformat(row["timestamp"]).replace(tzinfo=None) - moment)
            <= timedelta(minutes=5)
        })
        return Submission(str(found.printer_id), 0.9, {
            "printed_on": found.printed_on.isoformat(),
            "minute_of_day": str(found.minute_of_day), "pool": ",".join(pool)})
    if kind == "ooxml_metadata":
        with zipfile.ZipFile(public / "leak.docx") as package:
            settings = package.read("word/settings.xml").decode("utf-8")
        root = re.search(r'w:rsidRoot="([0-9A-F]{8})"', settings).group(1)
        owner = next(r["employee_id"] for r in _rows(public / "rsid_registry.csv")
                     if r["rsid_root"] == root)
        return Submission(owner, 0.9, {"ranking": "rsid,custom_property,app_template,"
                                                  "last_modified_by"})
    if kind == "log_fusion":
        observed = document_order_bits(_template(), (public / "forum_post.txt").read_text("utf-8"))
        ranked = match_registry(observed, read_registry(public / "registry.csv"))
        tied = [row.employee_id for row in ranked if row.disagreements == ranked[0].disagreements]
        on_leave = {row["employee_id"] for row in _rows(public / "leave_calendar.csv")}
        answer = next(item for item in tied if item not in on_leave)
        return Submission(answer, 0.85, {"tied": ",".join(tied)})
    if kind == "collusion":
        observed = document_order_bits(_template(), (public / "leak.txt").read_text("utf-8"))
        registry = {k: [int(b) for b in v]
                    for k, v in read_registry(public / "tardos_registry.csv").items()}
        biases = [float(r["bias"]) for r in _rows(public / "tardos_biases.csv")]
        scores = score_tardos_candidates(observed, biases, registry)
        threshold = calibrate_threshold(observed, biases, candidates=len(registry)).threshold
        return Submission(",".join(accuse(scores, threshold)), 0.9)
    observed = document_order_bits(_template(), (public / "leak.txt").read_text("utf-8"))
    owner = match_registry(observed, read_registry(public / "registry.csv"))[0].employee_id
    mac = _rows(public / "vpn_log.csv")[0]["client_mac"]
    host = next(r["hostname"] for r in _rows(public / "dhcp_leases.csv") if r["mac"] == mac)
    return Submission(owner, 0.7, {"actor": host.removeprefix("WS-"),
                                   "alternative": "owner may have shared credentials"})


@pytest.mark.parametrize("kind", sorted(CASES))
def test_case_is_solvable_with_full_marks_and_wrong_answer_gets_no_finding(
    kind: str, tmp_path: Path
) -> None:
    master = None if kind == "collusion" else MASTER
    instance = generate_case(CASES[kind], tmp_path / kind, seed=7, master_path=master)
    source = split_front_matter(instance.master_path.read_text(encoding="utf-8"))[1]
    TEMPLATE["current"] = parse_template(source)
    truth = json.loads(instance.ground_truth_path.read_text(encoding="utf-8"))
    submission = solve(kind, instance.public_dir)
    score = grade_case(kind, truth, submission, procedure=CLEAN, elapsed_seconds=300)
    assert score.correct, score.feedback
    assert score.total >= 90, score
    wrong = "E999" if kind != "print_timeline" else "0"
    bad = grade_case(kind, truth, Submission(wrong, 0.99, submission.details),
                     procedure=CLEAN, elapsed_seconds=300)
    assert not bad.correct and bad.finding == 0
    assert bad.calibration < 1


def test_hints_wrong_attempts_and_details_parsing() -> None:
    truth = {"copy_owner": "E001", "codeword": [0]}
    sub = Submission("E001", 1.0, parse_details("note = x ; other=y"))
    assert sub.details == {"note": "x", "other": "y"}
    clean = grade_case("leak_only", truth, sub, procedure=CLEAN, elapsed_seconds=0)
    penalised = grade_case("leak_only", truth, sub, procedure=Procedure(), elapsed_seconds=900,
                           hints_used=2, wrong_before=1)
    assert clean.total - penalised.total == 20 + 5 + 20
