"""Tests for seeded synthetic case evidence generation."""

import json
from pathlib import Path

import pytest
from PIL import Image

from molehunt.channels.printdots import read_dot_grid
from molehunt.channels.zerowidth import extract_zero_width
from molehunt.game.casebook import load_casebook
from molehunt.game.generator import generate_case


def test_all_seven_cases_generate_public_evidence_and_separate_truth(tmp_path: Path) -> None:
    cases = load_casebook()
    instances = [
        generate_case(
            definition,
            tmp_path / definition.case_id,
            seed=19,
            master_path="data/demo/master.md",
        )
        for definition in cases
    ]
    for instance in instances:
        assert instance.evidence_path.is_file()
        assert instance.roster_path.is_file()
        assert instance.public_dir.parent.joinpath("private").is_dir()
        assert "private" not in instance.public_dir.parts
        truth = json.loads(instance.ground_truth_path.read_text(encoding="utf-8"))
        assert truth["case_id"] == instance.definition.case_id
        assert truth["seed"] == 19 + instance.definition.seed_offset

    invisible = instances[0]
    truth = json.loads(invisible.ground_truth_path.read_text(encoding="utf-8"))
    observed = extract_zero_width(
        invisible.evidence_path.read_text(encoding="utf-8"), truth["slot_offsets"]
    )
    assert list(observed) == truth["codeword"]

    printed = instances[2]
    truth = json.loads(printed.ground_truth_path.read_text(encoding="utf-8"))
    with Image.open(printed.evidence_path) as image:
        metadata = read_dot_grid(image, origin=tuple(truth["grid_origin"]), cell_size=truth["grid_cell_size"])
    assert metadata.printer_id == truth["printer_id"]
    assert metadata.printed_on.isoformat() == truth["printed_on"]
    assert metadata.minute_of_day == truth["minute_of_day"]

    collusion = instances[5]
    truth = json.loads(collusion.ground_truth_path.read_text(encoding="utf-8"))
    assert len(truth["colluders"]) == 2
    assert len(truth["candidate_codewords"]) == 10


def test_same_case_and_seed_reproduce_public_and_private_content(tmp_path: Path) -> None:
    definition = load_casebook()[0]
    first = generate_case(
        definition, tmp_path / "first", seed=42, master_path="data/demo/master.md"
    )
    second = generate_case(
        definition, tmp_path / "second", seed=42, master_path="data/demo/master.md"
    )
    assert first.evidence_path.read_bytes() == second.evidence_path.read_bytes()
    assert first.ground_truth_path.read_bytes() == second.ground_truth_path.read_bytes()


def test_generator_refuses_existing_output_and_too_small_roster(tmp_path: Path) -> None:
    definition = load_casebook()[0]
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(FileExistsError):
        generate_case(definition, output, seed=1, master_path="data/demo/master.md")
    with pytest.raises(ValueError, match="at least three"):
        generate_case(
            definition, tmp_path / "too-small", seed=1,
            master_path="data/demo/master.md", employee_count=2,
        )
