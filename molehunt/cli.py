"""Initial CLI for key setup and local leak analysis."""

import csv
import json
import sqlite3
from pathlib import Path
from typing import Annotated

import typer

from molehunt import __version__
from molehunt.attacks.harness import run_text_benchmark, write_benchmark
from molehunt.attacks.transform import attack_text
from molehunt.channels.suggest import suggest_slots as find_slot_suggestions
from molehunt.core.codes import generate_codewords
from molehunt.core.keys import KEY_BYTES, load_or_create_key
from molehunt.core.slots import allocate_slots
from molehunt.core.template import parse_template
from molehunt.custody import append_custody_entry, sha256_file, verify_custody
from molehunt.detect.align import align_to_master
from molehunt.detect.extract import extract_variants
from molehunt.detect.fuse import fuse_scores
from molehunt.detect.ingest import ingest
from molehunt.detect.logs import read_fusion_logs
from molehunt.detect.score import score_candidates
from molehunt.intake import intake_evidence
from molehunt.issuance import issue_registered_copy, register_master_file
from molehunt.registry import (
    initialize_database,
    record_custody_entry,
    record_evidence,
)
from molehunt.report import write_analysis_report

app = typer.Typer(
    name="molehunt",
    help="Synthetic document forensics and casebook.",
    no_args_is_help=True,
)
custody_app = typer.Typer(help="Append and verify evidence custody entries.")
app.add_typer(custody_app, name="custody")
DEFAULT_DB = Path(".molehunt/molehunt.sqlite3")
DEFAULT_CUSTODY_LOG = Path(".molehunt/custody.log")


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
    key_file: Annotated[Path, typer.Option("--key-file")] = Path(".molehunt/master.key"),
    db_file: Annotated[Path, typer.Option("--db-file")] = DEFAULT_DB,
    custody_log: Annotated[Path, typer.Option("--custody-log")] = DEFAULT_CUSTODY_LOG,
) -> None:
    """Create or verify the local key, SQLite registry, and custody log."""
    try:
        load_or_create_key(key_file)
        initialize_database(db_file)
        custody_log.parent.mkdir(parents=True, exist_ok=True)
        custody_log.touch(exist_ok=True)
    except (OSError, ValueError, sqlite3.Error) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error
    typer.echo(f"Key ready: {key_file} ({KEY_BYTES} bytes)")
    typer.echo(f"Registry ready: {db_file}")
    typer.echo(f"Custody log ready: {custody_log}")


@app.command("suggest-slots")
def suggest_slots_command(
    master: Annotated[Path, typer.Argument(help="Text or Markdown master to inspect")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="CSV proposal file")]
    = None,
    context_chars: Annotated[int, typer.Option("--context-chars", min=0)] = 48,
) -> None:
    """Export contextual lexical and spelling slot proposals for human review."""
    try:
        text = master.read_text(encoding="utf-8")
        suggestions = find_slot_suggestions(text, context_chars=context_chars)
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(("line", "offset", "channel", "original", "alternative", "context"))
                writer.writerows(
                    (
                        item.line, item.offset, item.channel, item.original,
                        item.alternative, item.context,
                    )
                    for item in suggestions
                )
    except (OSError, UnicodeError, ValueError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error
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
    master_id: Annotated[str | None, typer.Option("--master-id", help="Registry ID; defaults to filename")]
    = None,
    title: Annotated[str | None, typer.Option("--title", help="Human-readable synthetic master title")]
    = None,
    key_file: Annotated[Path, typer.Option("--key-file")] = Path(".molehunt/master.key"),
    db_file: Annotated[Path, typer.Option("--db-file")] = DEFAULT_DB,
) -> None:
    """Register a master and its keyed slot map in the local SQLite registry."""
    try:
        key = key_file.read_bytes()
        slot_count = register_master_file(
            db_file, key, master, master_id=master_id, title=title
        )
    except (OSError, UnicodeError, ValueError, sqlite3.Error) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error
    typer.echo(f"Registered {master_id or master.stem}: {slot_count} slots ({master})")


@app.command()
def issue(
    employee_id: Annotated[str, typer.Argument(help="Synthetic employee ID")],
    master: Annotated[str, typer.Option("--master", help="Registered master ID or its registered path")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Copy output path (.txt, .md, or .docx)")],
    key_file: Annotated[Path, typer.Option("--key-file")] = Path(".molehunt/master.key"),
    db_file: Annotated[Path, typer.Option("--db-file")] = DEFAULT_DB,
) -> None:
    """Issue and registry-record a deterministic fingerprinted copy."""
    try:
        key = key_file.read_bytes()
        result = issue_registered_copy(db_file, key, employee_id, master, output)
    except (OSError, UnicodeError, ValueError, sqlite3.Error) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error

    typer.echo(
        f"Issued copy {result.copy_id} for {employee_id}: {output} ({result.slot_count} slots)"
    )


def _read_employee_ids(path: Path) -> list[str]:
    """Read synthetic employee IDs from a CSV file with an `id` column."""
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames or "id" not in reader.fieldnames:
                raise ValueError("employee CSV must have an 'id' column")
            employee_ids = [
                row.get("id", "").strip()
                for row in reader
                if row.get("id", "").strip()
            ]
    except OSError as error:
        raise ValueError(f"cannot read employee CSV: {path}") from error
    if not employee_ids:
        raise ValueError("employee CSV contains no IDs")
    if len(set(employee_ids)) != len(employee_ids):
        raise ValueError("employee IDs must be unique")
    return employee_ids


@app.command()
def analyze(
    evidence: Annotated[Path, typer.Argument(help="Evidence file: txt, md, docx, or png")],
    master: Annotated[Path, typer.Option("--master", help="Variation-marked master document")],
    employees: Annotated[Path, typer.Option("--employees", help="Synthetic roster CSV with id column")],
    key_file: Annotated[Path, typer.Option("--key-file")] = Path(".molehunt/master.key"),
    flip_rate: Annotated[float, typer.Option("--flip-rate", min=0.000001, max=0.499999)] = 0.15,
    report: Annotated[Path | None, typer.Option("--report", help="Optional DOCX report path")]
    = None,
    logs: Annotated[Path | None, typer.Option("--logs", help="Optional fusion CSV log evidence")]
    = None,
    case_id: Annotated[str, typer.Option("--case-id", help="Case ID for the report")]
    = "Not provided",
) -> None:
    """Rank synthetic copy candidates for one evidence file."""
    try:
        key = key_file.read_bytes()
        if len(key) != KEY_BYTES:
            raise ValueError(f"key file must contain {KEY_BYTES} bytes")
        source = master.read_text(encoding="utf-8")
        employee_ids = _read_employee_ids(employees)
        evidence_record = ingest(evidence)
        if evidence_record.text is None:
            raise ValueError("PNG dot metadata is available; text OCR is not implemented")
        template = parse_template(source)
        slots = allocate_slots(template, key)
        codewords = generate_codewords(key, employee_ids, len(slots))
        windows = align_to_master(template, slots, evidence_record.text)
        extracted = extract_variants(evidence_record.text, windows)
        by_index = {item.slot_index: item.bit for item in extracted}
        observations = [by_index[index] for index in range(len(slots))]
        scores = score_candidates(observations, codewords, flip_rate=flip_rate)
        fused_scores = None
        if logs is not None:
            log_evidence = read_fusion_logs(logs, set(employee_ids))
            fused_scores = fuse_scores(scores, log_evidence.access, log_evidence.events)
        report_path = None
        if report is not None:
            report_path = write_analysis_report(
                report,
                evidence_name=evidence.name,
                evidence_sha256=evidence_record.sha256,
                observed_slots=sum(bit is not None for bit in observations),
                total_slots=len(slots),
                scores=scores,
                flip_rate=flip_rate,
                case_id=case_id,
                fused_scores=fused_scores,
            )
    except (OSError, UnicodeError, ValueError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error

    typer.echo(f"Evidence SHA-256: {evidence_record.sha256}")
    typer.echo(f"Observed slots: {sum(bit is not None for bit in observations)} / {len(slots)}")
    typer.echo("Candidate  Matches  N  Z  P(null)  log10 LR")
    for score in scores:
        typer.echo(
            f"{score.candidate_id:<10} {score.matches:>7} {score.observed_slots:>3} "
            f"{score.z_score:>5.2f} {score.binomial_p:>8.4g} {score.log10_lr:>9.3f}"
        )
    if fused_scores is not None:
        typer.echo("Log fusion (explicit demo assumptions; not calibrated):")
        typer.echo("Candidate  Prior   Posterior       Applied evidence")
        for item in fused_scores:
            posterior = "Cannot distinguish" if item.posterior is None else f"{item.posterior:.6f}"
            rationale = "; ".join(item.rationale)
            typer.echo(f"{item.candidate_id:<10} {item.prior:>5.3f} {posterior:>14}  {rationale}")
    if not any(bit is not None for bit in observations):
        typer.echo("Finding: cannot distinguish; no slots were observed.")
    else:
        typer.echo("Finding: ranked candidates only; decision threshold needs benchmark calibration.")
    if report_path is not None:
        typer.echo(f"Report: {report_path}")


@app.command()
def attack(
    name: Annotated[str, typer.Option("--name", help="Attack ID: A1 through A10, or A2b")],
    evidence: Annotated[Path, typer.Argument(help="Input .txt or .md copy")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Scrubbed output .txt or .md")],
    strength: Annotated[float, typer.Option("--strength", min=0, max=1)] = 1.0,
    seed: Annotated[int, typer.Option("--seed", help="Seed for deterministic choices")] = 0,
) -> None:
    """Apply one seeded text attack to a copy and write the transformed output."""
    try:
        if evidence.suffix.casefold() not in {".txt", ".md"}:
            raise ValueError("attack input must use .txt or .md")
        if output.suffix.casefold() not in {".txt", ".md"}:
            raise ValueError("attack output must use .txt or .md")
        if evidence.resolve() == output.resolve():
            raise ValueError("attack output must not overwrite the input copy")
        source = evidence.read_text(encoding="utf-8")
        attacked = attack_text(source, name.upper(), strength=strength, seed=seed)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(attacked, encoding="utf-8", newline="")
    except (OSError, UnicodeError, ValueError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error
    typer.echo(f"Applied {name.upper()} at strength {strength:g} (seed {seed}): {output}")


@app.command()
def bench(
    master: Annotated[Path, typer.Option("--master", help="Variation-marked synthetic master")],
    employees: Annotated[Path, typer.Option("--employees", help="Synthetic roster CSV with id column")],
    key_file: Annotated[Path, typer.Option("--key-file")] = Path(".molehunt/master.key"),
    attacks: Annotated[str, typer.Option(help="Comma-separated attack IDs, A1 through A10")]
    = "A1,A2,A3,A4,A5,A6,A7,A8,A9,A10",
    strengths: Annotated[str, typer.Option(help="Comma-separated strengths from 0 to 1")]
    = "0.25,0.5,0.75,1.0",
    seeds: Annotated[str, typer.Option(help="Comma-separated deterministic RNG seeds")]
    = "0",
    output: Annotated[Path, typer.Option("--output", help="Benchmark artifact directory")]
    = Path("bench"),
    flip_rate: Annotated[float, typer.Option("--flip-rate", min=0.000001, max=0.499999)]
    = 0.15,
) -> None:
    """Measure text attack survival and candidate ranking on synthetic copies."""
    try:
        key = key_file.read_bytes()
        if len(key) != KEY_BYTES:
            raise ValueError(f"key file must contain {KEY_BYTES} bytes")
        template = parse_template(master.read_text(encoding="utf-8"))
        slots = allocate_slots(template, key)
        employee_ids = _read_employee_ids(employees)
        attack_ids = [value.strip() for value in attacks.split(",") if value.strip()]
        strength_values = [float(value.strip()) for value in strengths.split(",")]
        seed_values = [int(value.strip()) for value in seeds.split(",")]
        rows = run_text_benchmark(
            template,
            slots,
            key,
            employee_ids,
            attack_ids=attack_ids,
            strengths=strength_values,
            seeds=seed_values,
            flip_rate=flip_rate,
        )
        artifacts = write_benchmark(rows, output)
    except (OSError, UnicodeError, ValueError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error

    top1 = sum(row.top1_correct for row in rows) / len(rows)
    typer.echo(f"Runs: {len(rows)}")
    typer.echo(f"Overall top-1 accuracy: {top1:.3f}")
    for label, path in artifacts.items():
        typer.echo(f"{label}: {path}")
    typer.echo("Results apply only to these synthetic inputs and configured runs.")


@custody_app.command("add")
def custody_add(
    evidence: Annotated[Path, typer.Argument(help="Evidence file to record")],
    actor: Annotated[str, typer.Option("--actor", help="Synthetic examiner ID")],
    action: Annotated[str, typer.Option("--action", help="Custody event action")],
    details: Annotated[str, typer.Option("--details", help="Event details")]
    = "",
    ledger: Annotated[Path, typer.Option("--ledger", help="JSONL custody log")]
    = DEFAULT_CUSTODY_LOG,
    db_file: Annotated[Path, typer.Option("--db-file", help="SQLite registry path")]
    = DEFAULT_DB,
) -> None:
    """Append an evidence hash event to JSONL and mirror it in SQLite."""
    try:
        initialize_database(db_file)
        digest = sha256_file(evidence)
        entry = append_custody_entry(
            ledger, digest, actor=actor, action=action, details=details
        )
        record_custody_entry(db_file, entry)
    except (OSError, ValueError, sqlite3.Error) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error
    typer.echo(f"Recorded seq {entry['seq']} for SHA-256 {digest}")


@custody_app.command("verify")
def custody_verify(
    ledger: Annotated[Path, typer.Option("--ledger", help="JSONL custody log")]
    = DEFAULT_CUSTODY_LOG,
) -> None:
    """Verify every entry and link in the custody log."""
    try:
        result = verify_custody(ledger)
    except OSError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error
    if not result.valid:
        typer.echo(f"BROKEN at seq {result.broken_seq}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"VERIFIED: {result.entries} entries")


@custody_app.command("show")
def custody_show(
    ledger: Annotated[Path, typer.Option("--ledger", help="JSONL custody log")]
    = DEFAULT_CUSTODY_LOG,
) -> None:
    """Display custody events in sequence order from the JSONL ledger."""
    try:
        entries = [
            json.loads(line)
            for line in ledger.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if any(not isinstance(entry, dict) for entry in entries):
            raise ValueError("custody ledger entries must be JSON objects")
    except (OSError, json.JSONDecodeError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error
    if not entries:
        typer.echo("No custody entries")
        return
    for entry in entries:
        typer.echo(
            f"{entry.get('seq', '?')} | {entry.get('ts', '?')} | "
            f"{entry.get('actor', '?')} | {entry.get('action', '?')} | "
            f"{entry.get('object_sha256', '?')} | {entry.get('details', '')}"
        )


@app.command()
def intake(
    evidence: Annotated[Path, typer.Argument(help="Evidence file to copy into a case")],
    case_id: Annotated[str, typer.Argument(help="New case ID")],
    actor: Annotated[str, typer.Option("--actor", help="Synthetic examiner ID")],
    root: Annotated[Path, typer.Option("--root", help="Evidence case directory")]
    = Path("evidence"),
    db_file: Annotated[Path, typer.Option("--db-file", help="SQLite registry path")]
    = DEFAULT_DB,
) -> None:
    """Stage evidence and register its hash and custody entry in SQLite."""
    try:
        initialize_database(db_file)
        result = intake_evidence(evidence, case_id, actor=actor, root=root)
        evidence_id = record_evidence(
            db_file, case_id, result.original, result.working_copy, result.sha256
        )
        record_custody_entry(db_file, result.custody_entry)
    except (OSError, ValueError, sqlite3.Error) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error
    typer.echo(f"Case: {result.case_id}")
    typer.echo(f"Evidence ID: {evidence_id}")
    typer.echo(f"Original: {result.original}")
    typer.echo(f"Working copy: {result.working_copy}")
    typer.echo(f"SHA-256: {result.sha256}")


if __name__ == "__main__":
    app()


def main() -> None:
    """Run the command-line application."""
    app()
