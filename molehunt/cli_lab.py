"""Lab-mode commands: key setup, masters, copy issuance, analysis, single attacks."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Annotated

import typer

from molehunt import __version__
from molehunt.analysis import analyze_collusion, analyze_text
from molehunt.attacks.transform import attack_text
from molehunt.channels.suggest import suggest_slots as find_slot_suggestions
from molehunt.cli_app import (
    DEFAULT_DB,
    DEFAULT_KEY,
    app,
    fail,
    read_employee_ids,
    read_key,
    split_list,
)
from molehunt.core.keys import KEY_BYTES, load_or_create_key
from molehunt.detect.fuse import fuse_scores
from molehunt.detect.ingest import ingest
from molehunt.detect.logs import read_fusion_logs
from molehunt.game.logs_gen import synthetic_roster, write_roster_csv
from molehunt.issuance import issue_registered_copy, register_master_file
from molehunt.registry import initialize_database
from molehunt.report import write_analysis_report

KeyOption = Annotated[Path, typer.Option("--key-file")]
DbOption = Annotated[Path, typer.Option("--db-file")]


@app.command()
def version() -> None:
    """Print the installed MoleHunt version."""
    typer.echo(f"MoleHunt {__version__}")


@app.command()
def serve() -> None:
    """Open the native PySide6 forensic workbench."""
    from molehunt.ui.app import run_app

    raise typer.Exit(code=run_app())


@app.command()
def init(
    key_file: KeyOption = DEFAULT_KEY,
    db_file: DbOption = DEFAULT_DB,
    custody_log: Annotated[Path, typer.Option("--custody-log")] = Path(".molehunt/custody.log"),
) -> None:
    """Create or verify the local key, SQLite registry, and custody log."""
    try:
        load_or_create_key(key_file)
        initialize_database(db_file)
        custody_log.parent.mkdir(parents=True, exist_ok=True)
        custody_log.touch(exist_ok=True)
    except (OSError, ValueError, sqlite3.Error) as error:
        fail(error)
    typer.echo(f"Key ready: {key_file} ({KEY_BYTES} bytes)")
    typer.echo(f"Registry ready: {db_file}")
    typer.echo(f"Custody log ready: {custody_log}")


@app.command("suggest-slots")
def suggest_slots_command(
    master: Annotated[Path, typer.Argument(help="Text or Markdown master to inspect")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="CSV proposal file")] = None,
    context_chars: Annotated[int, typer.Option("--context-chars", min=0)] = 48,
) -> None:
    """Export contextual lexical and spelling slot proposals for human review."""
    try:
        suggestions = find_slot_suggestions(
            master.read_text(encoding="utf-8"), context_chars=context_chars
        )
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(("line", "offset", "channel", "original", "alternative", "context"))
                writer.writerows(
                    (i.line, i.offset, i.channel, i.original, i.alternative, i.context)
                    for i in suggestions
                )
    except (OSError, UnicodeError, ValueError) as error:
        fail(error)
    if output is not None:
        typer.echo(f"Suggestions: {len(suggestions)} ({output})")
    elif suggestions:
        typer.echo("Line  Offset  Channel  Original  Alternative  Context")
        for item in suggestions:
            typer.echo(
                f"{item.line:>4}  {item.offset:>6}  {item.channel:<7}  "
                f"{item.original:<12} {item.alternative:<12} {item.context}"
            )
        typer.echo(f"Suggestions: {len(suggestions)}; review every pair before editing the master.")
    else:
        typer.echo("No curated slot suggestions found.")


@app.command()
def register(
    master: Annotated[Path, typer.Argument(help="Variation-marked master document")],
    master_id: Annotated[str | None, typer.Option("--master-id", help="Registry ID")] = None,
    title: Annotated[str | None, typer.Option("--title", help="Synthetic master title")] = None,
    key_file: KeyOption = DEFAULT_KEY,
    db_file: DbOption = DEFAULT_DB,
) -> None:
    """Register a master and its keyed slot map in the local SQLite registry."""
    try:
        count = register_master_file(
            db_file, read_key(key_file), master, master_id=master_id, title=title
        )
    except (OSError, UnicodeError, ValueError, sqlite3.Error) as error:
        fail(error)
    typer.echo(f"Registered {master_id or master.stem}: {count} slots ({master})")


@app.command()
def roster(
    output: Annotated[Path, typer.Option("--output", "-o", help="Roster CSV to write")],
    count: Annotated[int, typer.Option("--count", min=1)] = 50,
    seed: Annotated[int, typer.Option("--seed")] = 0,
) -> None:
    """Write a seeded synthetic roster (id, name, dept, role)."""
    try:
        write_roster_csv(output, synthetic_roster(count, seed))
    except (OSError, ValueError) as error:
        fail(error)
    typer.echo(f"Roster: {count} synthetic employees ({output})")


@app.command()
def issue(
    master: Annotated[str, typer.Option("--master", help="Registered master ID or path")],
    employee_id: Annotated[str | None, typer.Argument(help="One synthetic employee ID")] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Single copy path")] = None,
    employees: Annotated[Path | None, typer.Option("--employees", help="Roster CSV")] = None,
    formats: Annotated[str, typer.Option("--format", help="Batch formats: txt,docx")] = "txt",
    out_dir: Annotated[Path, typer.Option("--out-dir", help="Batch output folder")]
    = Path("data/demo/issued"),
    code: Annotated[str, typer.Option("--code", help="single or tardos")] = "single",
    key_file: KeyOption = DEFAULT_KEY,
    db_file: DbOption = DEFAULT_DB,
) -> None:
    """Issue one copy (ID + --output) or a copy per roster row (--employees)."""
    try:
        key = read_key(key_file)
        if employees is not None:
            jobs = [
                (person, out_dir / f"{person}.{fmt}")
                for person in read_employee_ids(employees)
                for fmt in split_list(formats)
            ]
        elif employee_id and output is not None:
            jobs = [(employee_id, output)]
        else:
            raise ValueError("give an EMPLOYEE_ID with --output, or --employees roster.csv")
        for person, path in jobs:
            result = issue_registered_copy(db_file, key, person, master, path, code=code)
            typer.echo(
                f"Issued copy {result.copy_id} for {person}: {path} ({result.slot_count} slots)"
            )
    except (OSError, UnicodeError, ValueError, sqlite3.Error) as error:
        fail(error)


def _print_collusion(source: str, key: bytes, ids: list[str], text: str, target: float) -> None:
    result = analyze_collusion(source, key, ids, text, target=target)
    calibration = result.calibration
    typer.echo(f"Observed slots: {sum(b is not None for b in result.observations)} / "
               f"{len(result.observations)} (Tardos mode)")
    typer.echo(f"Threshold Z = {calibration.threshold:.2f} (simulated, {calibration.trials} "
               f"innocent draws; Gaussian check {calibration.gaussian_threshold:.2f})")
    typer.echo("Candidate  Tardos score")
    for item in result.scores:
        typer.echo(f"{item.candidate_id:<10} {item.score:>12.2f}")
    typer.echo(f"Accused (family-wise false-accusation target {target:g}): "
               f"{', '.join(result.accused) or 'none'}")
    if result.accused:
        typer.echo(f"Marking-assumption violations: {len(result.violations)}")


@app.command()
def analyze(
    evidence: Annotated[Path, typer.Argument(help="Evidence file: txt, md, docx, or png")],
    master: Annotated[Path, typer.Option("--master", help="Variation-marked master document")],
    employees: Annotated[Path, typer.Option("--employees", help="Roster CSV with id column")],
    key_file: KeyOption = DEFAULT_KEY,
    flip_rate: Annotated[float, typer.Option("--flip-rate", min=0.000001, max=0.499999)] = 0.15,
    report: Annotated[Path | None, typer.Option("--report", help="DOCX or PDF report")] = None,
    logs: Annotated[Path | None, typer.Option("--logs", help="Fusion CSV log evidence")] = None,
    case_id: Annotated[str, typer.Option("--case-id", help="Case ID for the report")]
    = "Not provided",
    collusion: Annotated[bool, typer.Option("--collusion", help="Tardos-mode copies")] = False,
    target: Annotated[float, typer.Option("--target", help="False-accusation target")] = 0.001,
) -> None:
    """Rank synthetic copy candidates for one evidence file and state a finding."""
    try:
        key = read_key(key_file)
        source = master.read_text(encoding="utf-8")
        employee_ids = read_employee_ids(employees)
        record = ingest(evidence)
        if record.text is None:
            raise ValueError("PNG dot metadata is available; text OCR is not implemented")
        if collusion:
            typer.echo(f"Evidence SHA-256: {record.sha256}")
            _print_collusion(source, key, employee_ids, record.text, target)
            return
        result = analyze_text(source, key, employee_ids, record.text, flip_rate=flip_rate)
        decision = result.decision(alpha=target)
        fused = None
        if logs is not None:
            evidence_logs = read_fusion_logs(logs, set(employee_ids))
            fused = fuse_scores(result.scores, evidence_logs.access, evidence_logs.events)
        report_path = None
        if report is not None:
            report_path = write_analysis_report(
                report, evidence_name=evidence.name, evidence_sha256=record.sha256,
                observed_slots=result.observed_slots, total_slots=len(result.observations),
                scores=result.scores, flip_rate=flip_rate, case_id=case_id,
                fused_scores=fused, decision=decision, channels=result.channel_survival(),
            )
    except (OSError, UnicodeError, ValueError) as error:
        fail(error)
    typer.echo(f"Evidence SHA-256: {record.sha256}")
    typer.echo(f"Observed slots: {result.observed_slots} / {len(result.observations)}")
    typer.echo("Candidate  Matches  N  Z  P(null)  log10 LR")
    for score in result.scores:
        typer.echo(
            f"{score.candidate_id:<10} {score.matches:>7} {score.observed_slots:>3} "
            f"{score.z_score:>5.2f} {score.binomial_p:>8.4g} {score.log10_lr:>9.3f}"
        )
    if fused is not None:
        typer.echo("Log fusion (explicit demo assumptions; not calibrated):")
        typer.echo("Candidate  Prior   Posterior       Applied evidence")
        for item in fused:
            posterior = "Cannot distinguish" if item.posterior is None else f"{item.posterior:.6f}"
            typer.echo(f"{item.candidate_id:<10} {item.prior:>5.3f} {posterior:>14}  "
                       f"{'; '.join(item.rationale)}")
    typer.echo(f"Finding ({decision.outcome}): {decision.statement}")
    if report_path is not None:
        typer.echo(f"Report: {report_path}")


@app.command()
def attack(
    name: Annotated[str, typer.Option("--name", help="Attack ID: A1-A11 or A2b")],
    evidence: Annotated[Path, typer.Argument(help="Input .txt or .md copy")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Scrubbed .txt or .md")],
    strength: Annotated[float, typer.Option("--strength", min=0, max=1)] = 1.0,
    seed: Annotated[int, typer.Option("--seed", help="Seed for deterministic choices")] = 0,
) -> None:
    """Apply one seeded text attack to a copy and write the transformed output."""
    attack_id = name.upper() if name.upper() != "A2B" else "A2b"
    try:
        if evidence.suffix.casefold() not in {".txt", ".md"}:
            raise ValueError("attack input must use .txt or .md")
        if output.suffix.casefold() not in {".txt", ".md"}:
            raise ValueError("attack output must use .txt or .md")
        if evidence.resolve() == output.resolve():
            raise ValueError("attack output must not overwrite the input copy")
        attacked = attack_text(
            evidence.read_text(encoding="utf-8"), attack_id, strength=strength, seed=seed
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(attacked, encoding="utf-8", newline="")
    except (OSError, UnicodeError, ValueError) as error:
        fail(error)
    typer.echo(f"Applied {attack_id} at strength {strength:g} (seed {seed}): {output}")
