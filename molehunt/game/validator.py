"""Grade a casebook submission against generated ground truth (SPEC Section 10).

Points: correct finding 50; procedure 20 (hash before analysis 5, working copy 5,
notes kept 5, original untouched 5); evidence quality 15 (case-specific check
that the cited artefacts support the finding); calibration 10 x (1 - Brier);
time bonus up to 5, linear under par; -5 per hint; -10 per earlier wrong
submission. Advance at 60. The validator only reads ``ground_truth.json`` passed
in by the caller; it never derives answers itself.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

ADVANCE_POINTS = 60
MAX_WRONG = 3


@dataclass(frozen=True)
class Submission:
    """Primary answer, stated confidence, and optional ``key=value`` details."""

    answer: str
    confidence: float
    details: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Procedure:
    """Forensic hygiene observed by the workbench."""

    hashed: bool = False
    working_copy: bool = False
    notes: bool = False
    original_untouched: bool = False


@dataclass(frozen=True, slots=True)
class CaseScore:
    """Component points, total, correctness, and feedback lines."""

    finding: int
    procedure: int
    evidence: int
    calibration: float
    time_bonus: float
    penalties: int
    total: int
    correct: bool
    feedback: tuple[str, ...]


def parse_details(text: str) -> dict[str, str]:
    """Parse ``bits=0101; pool=E001,E002`` into a dict (keys lower-case)."""
    result = {}
    for part in text.split(";"):
        if "=" in part:
            key, value = part.split("=", 1)
            result[key.strip().casefold()] = value.strip()
    return result


def _ids(value: str) -> set[str]:
    return {item.strip().casefold() for item in value.replace(" ", ",").split(",") if item.strip()}


def _same(left: Any, right: Any) -> bool:
    return str(left).strip().casefold() == str(right).strip().casefold()


def _check(kind: str, truth: Mapping[str, Any], sub: Submission) -> tuple[int, int, bool, list[str]]:
    """Return (finding points, evidence points, correct, feedback) for one case type."""
    details, notes = sub.details, []
    if kind == "collusion":
        named, guilty = _ids(sub.answer), {item.casefold() for item in truth["colluders"]}
        caught, innocent = len(named & guilty), len(named - guilty)
        notes.append(f"{caught} colluder(s) named, {innocent} innocent(s) accused")
        finding = max(0, 25 * caught - 25 * innocent)
        return finding, 15 if caught and not innocent else 0, named == guilty, notes
    if kind == "print_timeline":
        correct = _same(sub.answer, truth["printer_id"])
        for key in ("printed_on", "minute_of_day"):
            if key in details and not _same(details[key], truth[key]):
                correct = False
                notes.append(f"{key} does not match the decoded grid")
        pool, expected = _ids(details.get("pool", "")), {i.casefold() for i in truth["pool"]}
        evidence = 15 if pool == expected else 0
        if len(pool) == 1 and len(expected) > 1:
            evidence -= 15
            notes.append("named one person where the evidence supports only a pool")
        return (50 if correct else 0), evidence, correct, notes
    owner = truth["copy_owner"]
    correct = _same(sub.answer, owner)
    finding, evidence = (50 if correct else 0), 0
    if kind == "invisible_copy":
        bits, expected = details.get("bits", ""), "".join(map(str, truth["source_bits"]))
        agree = sum(a == b for a, b in zip(bits, expected, strict=False)) / len(expected)
        evidence = 15 if len(bits) == len(expected) and agree >= 0.9 else 0
        notes.append(f"bit string agreement {agree:.0%}")
    elif kind == "edited_text":
        marked = {int(x) - 1 for x in _ids(details.get("erased", "")) if x.isdigit()}
        actual = set(truth["erased"])
        overlap = len(marked & actual) / max(1, len(marked | actual))
        evidence = 15 if overlap >= 0.8 else 0
        notes.append(f"erasure marking overlap {overlap:.0%} (erasures are not mismatches)")
    elif kind == "ooxml_metadata":
        order = [item.strip().casefold() for item in details.get("ranking", "").split(",")]
        ok = "rsid" in order and "last_modified_by" in order and order.index("rsid") < order.index(
            "last_modified_by")
        evidence = 15 if ok else 0
        notes.append("rsid ranked above lastModifiedBy" if ok else "reliability ranking missing")
    elif kind == "log_fusion":
        tied = _ids(details.get("tied", ""))
        evidence = 15 if truth["tied_with"].casefold() in tied else 0
        notes.append("tie before fusion stated" if evidence else "tie before fusion not stated")
    elif kind == "account_sharing":
        actor_ok = _same(details.get("actor", ""), truth["probable_actor"])
        finding = 25 * int(correct) * (1 + int(actor_ok))
        open_alternative = bool(details.get("alternative", "").strip())
        evidence = 15 if open_alternative else -10
        notes.append("copy owner and actor kept separate" if actor_ok else "actor hypothesis wrong")
        if not open_alternative:
            notes.append("open alternative ignored")
        correct = correct and actor_ok
    return finding, evidence, correct, notes


def grade_case(
    kind: str,
    truth: Mapping[str, Any],
    submission: Submission,
    *,
    procedure: Procedure,
    elapsed_seconds: float,
    par_seconds: float = 900,
    hints_used: int = 0,
    wrong_before: int = 0,
) -> CaseScore:
    """Combine the Section 10 components into one score."""
    if not 0 <= submission.confidence <= 1:
        raise ValueError("confidence must be between zero and one")
    finding, evidence, correct, notes = _check(kind, truth, submission)
    hygiene = 5 * sum((procedure.hashed, procedure.working_copy, procedure.notes,
                       procedure.original_untouched))
    calibration = 10 * (1 - (submission.confidence - float(correct)) ** 2)
    time_bonus = 5 * max(0.0, 1 - elapsed_seconds / par_seconds) if correct else 0.0
    penalties = 5 * hints_used + 10 * wrong_before
    total = max(0, round(finding + hygiene + evidence + calibration + time_bonus - penalties))
    return CaseScore(finding, hygiene, evidence, round(calibration, 2), round(time_bonus, 2),
                     penalties, total, correct, tuple(notes))
