"""Tests for the initial command-line engine workflow."""

import hashlib
import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from molehunt.cli import app
from molehunt.core.codes import generate_codeword
from molehunt.core.render import render_text
from molehunt.core.slots import allocate_slots
from molehunt.core.template import parse_template

runner = CliRunner()


def test_init_creates_key_without_printing_secret(tmp_path: Path) -> None:
    key_path = tmp_path / "private" / "master.key"
    db_path = tmp_path / "private" / "registry.sqlite3"
    custody_path = tmp_path / "private" / "custody.log"
    result = runner.invoke(
        app,
        [
            "init", "--key-file", str(key_path), "--db-file", str(db_path),
            "--custody-log", str(custody_path),
        ],
    )
    assert result.exit_code == 0
    assert key_path.read_bytes() and len(key_path.read_bytes()) == 32
    assert key_path.read_bytes().hex() not in result.stdout
    assert custody_path.is_file()
    with sqlite3.connect(db_path) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
    assert {"masters", "slots", "employees", "copies", "cases"} <= tables


def test_analyze_ranks_clean_rendered_copy(tmp_path: Path) -> None:
    key = bytes(range(32))
    key_path = tmp_path / "master.key"
    key_path.write_bytes(key)
    master_path = tmp_path / "master.md"
    master_text = "\n".join(
        f"Section {index:02}: " + "{{lex:begin|start}}."
        for index in range(64)
    )
    master_path.write_text(master_text, encoding="utf-8")
    employees = [f"E{i:03}" for i in range(1, 11)]
    roster_path = tmp_path / "employees.csv"
    roster_path.write_text("id\n" + "\n".join(employees), encoding="utf-8")
    template = parse_template(master_path.read_text(encoding="utf-8"))
    slots = allocate_slots(template, key)
    leak_path = tmp_path / "leak.txt"
    report_path = tmp_path / "analysis.docx"
    leak_path.write_text(
        render_text(template, slots, generate_codeword(key, "E007", len(slots))),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "analyze",
            str(leak_path),
            "--master",
            str(master_path),
            "--employees",
            str(roster_path),
            "--key-file",
            str(key_path),
            "--report",
            str(report_path),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "E007" in result.stdout
    assert "SHA-256" in result.stdout
    candidate_rows = [line.split()[0] for line in result.stdout.splitlines() if line.startswith("E0")]
    assert candidate_rows[0] == "E007"
    assert report_path.is_file()
    assert str(report_path) in result.stdout


def test_issue_creates_copy_that_analyze_identifies(tmp_path: Path) -> None:
    key_path = tmp_path / "master.key"
    key_path.write_bytes(bytes(range(32)))
    master_path = tmp_path / "master.md"
    master_path.write_text(
        "\n".join(
            f"Section {index:02}: " + "{{lex:begin|start}}."
            for index in range(64)
        ),
        encoding="utf-8",
    )
    roster_path = tmp_path / "employees.csv"
    roster_path.write_text("id\nE001\nE002\nE003\n", encoding="utf-8")
    copy_path = tmp_path / "issued.txt"
    db_path = tmp_path / "registry.sqlite3"

    registered = runner.invoke(
        app,
        ["register", str(master_path), "--master-id", "M1", "--key-file", str(key_path),
         "--db-file", str(db_path)],
    )
    assert registered.exit_code == 0, registered.stdout

    issued = runner.invoke(
        app,
        [
            "issue", "E002", "--master", "M1", "--key-file", str(key_path),
            "--db-file", str(db_path), "--output", str(copy_path),
        ],
    )
    assert issued.exit_code == 0, issued.stdout
    assert "E002" in issued.stdout
    analyzed = runner.invoke(
        app,
        [
            "analyze", str(copy_path), "--master", str(master_path),
            "--employees", str(roster_path), "--key-file", str(key_path),
        ],
    )
    assert analyzed.exit_code == 0, analyzed.stdout
    first_candidate = next(
        line.split()[0]
        for line in analyzed.stdout.splitlines()
        if line.startswith(("E001", "E002", "E003"))
    )
    assert first_candidate == "E002"
    with sqlite3.connect(db_path) as connection:
        employee = connection.execute("SELECT id FROM employees").fetchone()
        copy = connection.execute(
            "SELECT master_id, employee_id, format, sha256, path FROM copies"
        ).fetchone()
    assert employee == ("E002",)
    assert copy == (
        "M1", "E002", "txt", hashlib.sha256(copy_path.read_bytes()).hexdigest(),
        str(copy_path.resolve()),
    )


def test_register_rejects_duplicate_master_id_cleanly(tmp_path: Path) -> None:
    key_path = tmp_path / "master.key"
    key_path.write_bytes(bytes(range(32)))
    master_path = tmp_path / "master.md"
    master_path.write_text("A {{lex:begin|start}} phrase.", encoding="utf-8")
    db_path = tmp_path / "registry.sqlite3"
    args = ["register", str(master_path), "--master-id", "M1", "--key-file", str(key_path),
            "--db-file", str(db_path)]
    first = runner.invoke(app, args)
    second = runner.invoke(app, args)
    assert first.exit_code == 0, first.stdout
    assert second.exit_code == 2
    assert "UNIQUE constraint failed" in second.stderr


def test_issue_rejects_unregistered_or_changed_master(tmp_path: Path) -> None:
    key_path = tmp_path / "master.key"
    key_path.write_bytes(bytes(range(32)))
    master_path = tmp_path / "master.md"
    master_path.write_text("A {{lex:begin|start}} phrase.", encoding="utf-8")
    db_path = tmp_path / "registry.sqlite3"
    output_path = tmp_path / "issued.txt"
    initialized = runner.invoke(
        app,
        ["init", "--key-file", str(key_path), "--db-file", str(db_path),
         "--custody-log", str(tmp_path / "custody.log")],
    )
    assert initialized.exit_code == 0, initialized.stdout
    common = ["issue", "E001", "--key-file", str(key_path), "--db-file", str(db_path),
              "--output", str(output_path)]
    missing = runner.invoke(app, [*common, "--master", "MISSING"])
    assert missing.exit_code == 2
    assert "not registered" in missing.stderr
    registered = runner.invoke(
        app,
        ["register", str(master_path), "--master-id", "M1", "--key-file", str(key_path),
         "--db-file", str(db_path)],
    )
    assert registered.exit_code == 0, registered.stdout
    master_path.write_text("Changed after registration.", encoding="utf-8")
    changed = runner.invoke(app, [*common, "--master", "M1"])
    assert changed.exit_code == 2
    assert "changed after registration" in changed.stderr
    assert not output_path.exists()


def test_analyze_rejects_roster_without_id_column(tmp_path: Path) -> None:
    key_path = tmp_path / "master.key"
    key_path.write_bytes(b"k" * 32)
    master_path = tmp_path / "master.md"
    master_path.write_text("Plain text.", encoding="utf-8")
    employees = tmp_path / "employees.csv"
    employees.write_text("name\nSynthetic Person", encoding="utf-8")
    evidence = tmp_path / "leak.txt"
    evidence.write_text("Plain text.", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "analyze",
            str(evidence),
            "--master",
            str(master_path),
            "--employees",
            str(employees),
            "--key-file",
            str(key_path),
        ],
    )
    assert result.exit_code != 0
    assert "id" in result.stderr.lower()


def test_bench_writes_measurements_for_requested_attacks(tmp_path: Path) -> None:
    key_path = tmp_path / "master.key"
    key_path.write_bytes(bytes(range(32)))
    master_path = tmp_path / "master.md"
    master_path.write_text(
        "\n".join(
            f"Section {index:02}: " + "{{lex:begin|start}}."
            for index in range(32)
        ),
        encoding="utf-8",
    )
    roster_path = tmp_path / "employees.csv"
    roster_path.write_text("id\nE001\nE002\n", encoding="utf-8")
    result_dir = tmp_path / "bench-output"

    result = runner.invoke(
        app,
        [
            "bench",
            "--master", str(master_path),
            "--employees", str(roster_path),
            "--key-file", str(key_path),
            "--attacks", "A1,A3",
            "--strengths", "0,1",
            "--seeds", "7",
            "--output", str(result_dir),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "Runs: 8" in result.stdout
    assert (result_dir / "results" / "runs.csv").is_file()
    assert (result_dir / "results" / "survival.csv").is_file()
    assert (result_dir / "plots" / "accuracy.png").is_file()
    assert (result_dir / "plots" / "survival.png").is_file()


def test_custody_cli_records_and_verifies_evidence(tmp_path: Path) -> None:
    evidence = tmp_path / "leak.txt"
    evidence.write_text("synthetic evidence", encoding="utf-8")
    ledger = tmp_path / "custody.log"
    database = tmp_path / "registry.sqlite3"
    added = runner.invoke(
        app,
        [
            "custody", "add", str(evidence), "--actor", "examiner-01", "--action", "intake",
            "--ledger", str(ledger), "--db-file", str(database),
        ],
    )
    assert added.exit_code == 0, added.stdout
    verified = runner.invoke(app, ["custody", "verify", "--ledger", str(ledger)])
    assert verified.exit_code == 0
    assert "VERIFIED: 1 entries" in verified.stdout
    shown = runner.invoke(app, ["custody", "show", "--ledger", str(ledger)])
    assert shown.exit_code == 0
    assert "examiner-01" in shown.stdout
    assert "intake" in shown.stdout
    with sqlite3.connect(database) as connection:
        stored = connection.execute(
            "SELECT seq, actor, action, object_sha256 FROM custody_log"
        ).fetchone()
    assert stored[0:3] == (1, "examiner-01", "intake")
    assert stored[3] == hashlib.sha256(evidence.read_bytes()).hexdigest()


def test_intake_cli_creates_case_files(tmp_path: Path) -> None:
    source = tmp_path / "leak.txt"
    source.write_text("synthetic evidence", encoding="utf-8")
    case_root = tmp_path / "cases"
    db_path = tmp_path / "registry.sqlite3"
    result = runner.invoke(
        app,
        [
            "intake", str(source), "CASE-02", "--actor", "examiner-01", "--root", str(case_root),
            "--db-file", str(db_path),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert (case_root / "CASE-02" / "original" / "leak.txt").is_file()
    assert (case_root / "CASE-02" / "working" / "leak.txt").is_file()
    assert "SHA-256:" in result.stdout
    assert "Evidence ID:" in result.stdout
    with sqlite3.connect(db_path) as connection:
        evidence = connection.execute(
            "SELECT case_id, sha256, working_copy_path FROM evidence"
        ).fetchone()
        custody = connection.execute(
            "SELECT seq, actor, action, object_sha256 FROM custody_log"
        ).fetchone()
    assert evidence[0] == "CASE-02"
    assert evidence[1] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert Path(evidence[2]).parts[-3:] == ("CASE-02", "working", "leak.txt")
    assert custody == (1, "examiner-01", "intake", evidence[1])
