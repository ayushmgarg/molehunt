"""Tests for the shared registered-master issuance API."""

from pathlib import Path

import pytest

from molehunt.issuance import issue_registered_copy, register_master_file
from molehunt.registry import initialize_database


def test_issue_api_requires_registration_and_records_copy(tmp_path: Path) -> None:
    database = initialize_database(tmp_path / "registry.sqlite3")
    key = bytes(range(32))
    master = tmp_path / "master.md"
    master.write_text("A {{lex:begin|start}} line.", encoding="utf-8")
    output = tmp_path / "issued" / "E001.txt"
    with pytest.raises(ValueError, match="not registered"):
        issue_registered_copy(database, key, "E001", "M1", output)
    assert register_master_file(database, key, master, master_id="M1") == 1
    result = issue_registered_copy(database, key, "E001", "M1", output)
    assert result.master_id == "M1"
    assert result.employee_id == "E001"
    assert result.copy_id
    assert result.slot_count == 1
    assert output.is_file()
    with pytest.raises(FileExistsError, match="already exists"):
        issue_registered_copy(database, key, "E001", "M1", output)


def test_issue_api_detects_master_edits_after_registration(tmp_path: Path) -> None:
    database = initialize_database(tmp_path / "registry.sqlite3")
    key = bytes(range(32))
    master = tmp_path / "master.md"
    master.write_text("A {{lex:begin|start}} line.", encoding="utf-8")
    register_master_file(database, key, master, master_id="M1")
    master.write_text("Edited after registration.", encoding="utf-8")
    with pytest.raises(ValueError, match="changed after registration"):
        issue_registered_copy(database, key, "E001", "M1", tmp_path / "copy.txt")


def test_register_api_validates_key_size(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        register_master_file(tmp_path / "registry.sqlite3", b"small", tmp_path / "missing.md")


def test_tardos_copy_uses_keyed_tardos_codeword(tmp_path) -> None:
    from molehunt.core.autoslots import prepare_master
    from molehunt.core.render import render_text
    from molehunt.core.tardos import generate_tardos_biases, generate_tardos_codeword
    from molehunt.issuance import issue_registered_copy, register_master_file

    key = bytes(range(32))
    master = tmp_path / "m.md"
    master.write_text("Please {{lex:begin|start}} and {{lex:check|verify}} now.", encoding="utf-8")
    database = tmp_path / "r.sqlite3"
    register_master_file(database, key, master, master_id="M")
    output = tmp_path / "copy.txt"
    issue_registered_copy(database, key, "E01", "M", output, code="tardos")
    prepared = prepare_master(master.read_text(encoding="utf-8"), key)
    bits = generate_tardos_codeword(key, "E01", generate_tardos_biases(key, 2))
    assert output.read_text(encoding="utf-8") == render_text(prepared.template, prepared.slots, bits)
