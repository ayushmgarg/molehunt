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
