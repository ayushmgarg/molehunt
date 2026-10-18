"""Tests for the initial command-line engine workflow."""

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
    result = runner.invoke(app, ["init", "--key-file", str(key_path)])
    assert result.exit_code == 0
    assert key_path.read_bytes() and len(key_path.read_bytes()) == 32
    assert key_path.read_bytes().hex() not in result.stdout


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
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "E007" in result.stdout
    assert "SHA-256" in result.stdout
    candidate_rows = [line.split()[0] for line in result.stdout.splitlines() if line.startswith("E0")]
    assert candidate_rows[0] == "E007"


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

    issued = runner.invoke(
        app,
        [
            "issue", "E002", "--master", str(master_path), "--key-file", str(key_path),
            "--output", str(copy_path),
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
    added = runner.invoke(
        app,
        [
            "custody", "add", str(evidence), "--actor", "examiner-01", "--action", "intake",
            "--ledger", str(ledger),
        ],
    )
    assert added.exit_code == 0, added.stdout
    verified = runner.invoke(app, ["custody", "verify", "--ledger", str(ledger)])
    assert verified.exit_code == 0
    assert "VERIFIED: 1 entries" in verified.stdout


def test_intake_cli_creates_case_files(tmp_path: Path) -> None:
    source = tmp_path / "leak.txt"
    source.write_text("synthetic evidence", encoding="utf-8")
    case_root = tmp_path / "cases"
    result = runner.invoke(
        app,
        [
            "intake", str(source), "CASE-02", "--actor", "examiner-01", "--root", str(case_root),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert (case_root / "CASE-02" / "original" / "leak.txt").is_file()
    assert (case_root / "CASE-02" / "working" / "leak.txt").is_file()
    assert "SHA-256:" in result.stdout
