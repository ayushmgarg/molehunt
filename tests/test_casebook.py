"""Tests for the seven answer-free case definitions."""

from pathlib import Path

import pytest

from molehunt.game.casebook import load_case_definition, load_casebook


def test_packaged_casebook_has_seven_valid_progression_scenarios() -> None:
    cases = load_casebook()
    assert len(cases) == 7
    assert [case.case_id for case in cases] == [f"C-{index:02}" for index in range(1, 8)]
    assert [case.generator for case in cases] == [
        "invisible_copy", "edited_text", "print_timeline", "ooxml_metadata",
        "log_fusion", "collusion", "account_sharing",
    ]
    assert all(len(case.brief.split()) <= 50 and len(case.hints) == 3 for case in cases)


def test_case_definition_rejects_embedded_solution_fields(tmp_path: Path) -> None:
    path = tmp_path / "case.yaml"
    path.write_text(
        "case_id: C-01\ntitle: Test\nbrief: Short\nobjective: Solve\n"
        "generator: invisible_copy\nmaster: master.md\nseed_offset: 1\n"
        "tools: [hex]\nhints: [one, two, three]\nground_truth: E001\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown case fields"):
        load_case_definition(path)


def test_casebook_rejects_duplicate_ids(tmp_path: Path) -> None:
    definition = (
        "case_id: C-01\ntitle: Test\nbrief: Short\nobjective: Solve\n"
        "generator: invisible_copy\nmaster: master.md\nseed_offset: 1\n"
        "tools: [hex]\nhints: [one, two, three]\n"
    )
    (tmp_path / "case-a.yaml").write_text(definition, encoding="utf-8")
    (tmp_path / "case-b.yaml").write_text(definition, encoding="utf-8")
    with pytest.raises(ValueError, match="IDs must be unique"):
        load_casebook(tmp_path)
