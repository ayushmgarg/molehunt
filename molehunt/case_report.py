"""Build a full examiner report for a registered case (``molehunt report --case``).

Steps: read the case's evidence rows from SQLite; re-hash each read-only
original and compare with the intake SHA-256; verify the case custody chain;
analyse the first text working copy against the master; add a slot-matrix
excerpt (top candidates x first observed slots) and a hex excerpt; render.
Also provides the custody tamper demonstration (flip one byte, verify fails).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from molehunt.analysis import analyze_text
from molehunt.custody import append_custody_entry, sha256_file, verify_custody
from molehunt.detect.ingest import ingest
from molehunt.report import EvidenceItem, ReportInput, write_report
from molehunt.ui.forensics import format_hex_rows

_SYMBOL = {True: "o", False: "x"}


def case_evidence(database: Path, case_id: str) -> list[sqlite3.Row]:
    """Evidence rows registered for one case, in intake order."""
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute(
            "SELECT id, path, sha256, intake_ts, working_copy_path FROM evidence "
            "WHERE case_id = ? ORDER BY intake_ts, id",
            (case_id,),
        ).fetchall()


def custody_status(case_dir: Path, original: Path, expected_sha256: str) -> str:
    """Hash check of the original plus the case custody-chain verdict."""
    hashed = "hash ok" if original.is_file() and sha256_file(original) == expected_sha256 else (
        "HASH MISMATCH"
    )
    ledger = case_dir / "custody.log"
    if not ledger.is_file():
        return f"{hashed}; no custody log"
    result = verify_custody(ledger)
    chain = f"chain verified ({result.entries})" if result.valid else (
        f"chain BROKEN at seq {result.broken_seq}"
    )
    return f"{hashed}; {chain}"


def build_case_report(
    output: Path,
    *,
    case_id: str,
    database: Path,
    root: Path,
    master: Path,
    roster_ids: list[str],
    key: bytes,
    examiner: str = "Not provided",
    candidates_shown: int = 5,
    slots_shown: int = 24,
) -> Path:
    """Analyse the case's first text evidence and write the full report."""
    rows = case_evidence(database, case_id)
    if not rows:
        raise ValueError(f"no evidence registered for case {case_id}")
    items = tuple(
        EvidenceItem(
            Path(row["path"]).name, row["sha256"], row["intake_ts"],
            custody_status(root / case_id, Path(row["path"]), row["sha256"]),
        )
        for row in rows
    )
    target = next(
        (Path(row["working_copy_path"]) for row in rows
         if Path(row["working_copy_path"]).suffix.casefold() in {".txt", ".md", ".docx"}),
        None,
    )
    if target is None:
        raise ValueError("case has no text or DOCX working copy to analyse")
    record = ingest(target)
    result = analyze_text(master.read_text(encoding="utf-8"), key, roster_ids, record.text or "")
    observed = [index for index, bit in enumerate(result.observations) if bit is not None]
    columns = observed[:slots_shown]
    matrix = tuple(
        (score.candidate_id, *(
            _SYMBOL[result.observations[i] == result.codewords[score.candidate_id][i]]
            for i in columns
        ))
        for score in result.scores[:candidates_shown]
    )
    hex_lines = tuple(
        f"{offset:08X}  {hexes:<47}  {text}"
        for offset, hexes, text in format_hex_rows(target.read_bytes()[:128])
    )
    return write_report(output, ReportInput(
        evidence=items, scores=result.scores, observed_slots=result.observed_slots,
        total_slots=len(result.observations), flip_rate=0.15, case_id=case_id,
        examiner=examiner, channels=result.channel_survival(), decision=result.decision(),
        slot_matrix=matrix, hex_excerpt=hex_lines,
    ))


def tamper_demo(ledger: Path, *, entries: int = 8, flip_seq: int = 7) -> tuple[str, str]:
    """Write a fresh demo chain, flip one byte in entry ``flip_seq``, re-verify."""
    if ledger.exists():
        raise FileExistsError(f"demo ledger already exists: {ledger}")
    for index in range(1, entries + 1):
        digest = f"{index:064x}"
        append_custody_entry(ledger, digest, actor="EX-DEMO", action=f"step-{index}")
    before = verify_custody(ledger)
    raw = bytearray(ledger.read_bytes())
    line_start = 0
    for _ in range(flip_seq - 1):
        line_start = raw.index(b"\n", line_start) + 1
    position = raw.index(b"EX-DEMO", line_start) + len("EX-DEM")
    raw[position] ^= 0x1F  # flip bits of one byte: "O" becomes "P"
    ledger.write_bytes(bytes(raw))
    after = verify_custody(ledger)
    first = f"VERIFIED: {before.entries} entries" if before.valid else "BROKEN before tamper"
    second = f"BROKEN at seq {after.broken_seq}" if not after.valid else "still verified"
    return first, second
