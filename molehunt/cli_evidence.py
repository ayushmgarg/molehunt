"""Evidence commands: custody chain, intake, tamper demo, and case reports."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Annotated

import typer

from molehunt.case_report import build_case_report, tamper_demo
from molehunt.cli_app import (
    DEFAULT_CUSTODY_LOG,
    DEFAULT_DB,
    DEFAULT_KEY,
    app,
    custody_app,
    fail,
    read_employee_ids,
    read_key,
)
from molehunt.custody import append_custody_entry, sha256_file, verify_custody
from molehunt.intake_service import intake_case
from molehunt.registry import initialize_database, record_custody_entry

LedgerOption = Annotated[Path, typer.Option("--ledger", help="JSONL custody log")]
DbOption = Annotated[Path, typer.Option("--db-file", help="SQLite registry path")]
RootOption = Annotated[Path, typer.Option("--root", help="Evidence case directory")]


@custody_app.command("add")
def custody_add(
    evidence: Annotated[Path, typer.Argument(help="Evidence file to record")],
    actor: Annotated[str, typer.Option("--actor", help="Synthetic examiner ID")],
    action: Annotated[str, typer.Option("--action", help="Custody event action")],
    details: Annotated[str, typer.Option("--details", help="Event details")] = "",
    ledger: LedgerOption = DEFAULT_CUSTODY_LOG,
    db_file: DbOption = DEFAULT_DB,
) -> None:
    """Append an evidence hash event to JSONL and mirror it in SQLite."""
    try:
        initialize_database(db_file)
        digest = sha256_file(evidence)
        entry = append_custody_entry(ledger, digest, actor=actor, action=action, details=details)
        record_custody_entry(db_file, entry)
    except (OSError, ValueError, sqlite3.Error) as error:
        fail(error)
    typer.echo(f"Recorded seq {entry['seq']} for SHA-256 {digest}")


@custody_app.command("verify")
def custody_verify(ledger: LedgerOption = DEFAULT_CUSTODY_LOG) -> None:
    """Verify every entry and link in the custody log from genesis."""
    try:
        result = verify_custody(ledger)
    except OSError as error:
        fail(error)
    if not result.valid:
        typer.echo(f"BROKEN at seq {result.broken_seq}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"VERIFIED: {result.entries} entries")


@custody_app.command("show")
def custody_show(ledger: LedgerOption = DEFAULT_CUSTODY_LOG) -> None:
    """Display custody events in sequence order from the JSONL ledger."""
    try:
        entries = [
            json.loads(line)
            for line in ledger.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if any(not isinstance(entry, dict) for entry in entries):
            raise ValueError("custody ledger entries must be JSON objects")
    except (OSError, ValueError) as error:
        fail(error)
    if not entries:
        typer.echo("No custody entries")
        return
    for entry in entries:
        typer.echo(
            f"{entry.get('seq', '?')} | {entry.get('ts', '?')} | {entry.get('actor', '?')} | "
            f"{entry.get('action', '?')} | {entry.get('object_sha256', '?')} | "
            f"{entry.get('details', '')}"
        )


@custody_app.command("demo")
def custody_demo(
    ledger: Annotated[Path, typer.Option("--ledger", help="New demo ledger path")]
    = Path("reports/tamper-demo/custody.log"),
    flip_seq: Annotated[int, typer.Option("--flip-seq", min=1, max=8)] = 7,
) -> None:
    """Tamper demo: build an 8-entry chain, flip one byte, show verify fail."""
    try:
        before, after = tamper_demo(ledger, flip_seq=flip_seq)
    except (OSError, ValueError) as error:
        fail(error)
    typer.echo(f"Before tamper: {before}")
    typer.echo(f"Flipped one byte in entry {flip_seq} of {ledger}")
    typer.echo(f"After tamper:  {after}")


def _intake(evidence: Path, case_id: str, actor: str, root: Path, db_file: Path) -> None:
    try:
        registered = intake_case(evidence, case_id, actor=actor, root=root, database=db_file)
    except (OSError, ValueError, sqlite3.Error) as error:
        fail(error)
    result = registered.intake
    typer.echo(f"Case: {result.case_id}")
    typer.echo(f"Evidence ID: {registered.evidence_id}")
    typer.echo(f"Original: {result.original}")
    typer.echo(f"Working copy: {result.working_copy}")
    typer.echo(f"SHA-256: {result.sha256}")


@app.command()
def intake(
    evidence: Annotated[Path, typer.Argument(help="Evidence file to copy into a case")],
    case_id: Annotated[str, typer.Argument(help="New case ID")],
    actor: Annotated[str, typer.Option("--actor", help="Synthetic examiner ID")],
    root: RootOption = Path("evidence"),
    db_file: DbOption = DEFAULT_DB,
) -> None:
    """Stage evidence (read-only original + working copy) and log custody."""
    _intake(evidence, case_id, actor, root, db_file)


@custody_app.command("intake")
def custody_intake(
    evidence: Annotated[Path, typer.Argument(help="Evidence file to copy into a case")],
    case_id: Annotated[str, typer.Argument(help="New case ID")],
    actor: Annotated[str, typer.Option("--actor", help="Synthetic examiner ID")],
    root: RootOption = Path("evidence"),
    db_file: DbOption = DEFAULT_DB,
) -> None:
    """Same as ``molehunt intake`` (plan spelling: ``custody intake``)."""
    _intake(evidence, case_id, actor, root, db_file)


@app.command()
def report(
    case_id: Annotated[str, typer.Option("--case", help="Registered case ID")],
    output: Annotated[Path, typer.Option("--output", "-o", help=".docx or .pdf")],
    master: Annotated[Path, typer.Option("--master", help="Variation-marked master")],
    employees: Annotated[Path, typer.Option("--employees", help="Roster CSV")],
    key_file: Annotated[Path, typer.Option("--key-file")] = DEFAULT_KEY,
    examiner: Annotated[str, typer.Option("--examiner")] = "Not provided",
    root: RootOption = Path("evidence"),
    db_file: DbOption = DEFAULT_DB,
) -> None:
    """Write the full Section 8 examiner report for a registered case."""
    try:
        path = build_case_report(
            output, case_id=case_id, database=db_file, root=root, master=master,
            roster_ids=read_employee_ids(employees), key=read_key(key_file), examiner=examiner,
        )
    except (OSError, ValueError, sqlite3.Error) as error:
        fail(error)
    typer.echo(f"Report: {path}")
