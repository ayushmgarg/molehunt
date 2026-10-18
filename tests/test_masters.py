"""Checks that bundled synthetic masters meet the plan's size and capacity targets."""

import re
from pathlib import Path

import pytest

from molehunt.analysis import analyze_prepared
from molehunt.core.autoslots import master_title, prepare_master, split_front_matter
from molehunt.core.codes import generate_codewords
from molehunt.core.render import render_text
from molehunt.core.slots import capacity_report

MASTERS = sorted(Path(__file__).parents[1].joinpath("data", "masters").glob("*.md"))
KEY = bytes(range(32))
_CHOICE = re.compile(r"\{\{[a-z]+:([^{}|]*)\|[^{}|]*\}\}")


def test_at_least_three_masters_are_bundled() -> None:
    assert len(MASTERS) >= 3


@pytest.mark.parametrize("path", MASTERS, ids=lambda path: path.stem)
def test_master_size_and_channel_capacity(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    assert master_title(source)
    words = len(_CHOICE.sub(r"\1", split_front_matter(source)[1]).split())
    assert 600 <= words <= 900
    prepared = prepare_master(source, KEY)
    report = capacity_report(prepared.slots)
    assert len(prepared.slots) >= 250
    assert report["lex"] >= 60
    assert report.get("spl", 0) + report.get("dat", 0) + report.get("num", 0) >= 60
    assert all(choice.zero != choice.one for choice in prepared.template.choices)


@pytest.mark.parametrize("path", MASTERS, ids=lambda path: path.stem)
def test_clean_copies_of_fifty_employees_are_attributed(path: Path) -> None:
    prepared = prepare_master(path.read_text(encoding="utf-8"), KEY)
    roster = [f"E{index:03}" for index in range(1, 51)]
    codewords = generate_codewords(KEY, roster, len(prepared.slots))
    for employee in roster[::7]:
        copy = render_text(prepared.template, prepared.slots, codewords[employee])
        result = analyze_prepared(prepared, copy, codewords)
        assert result.observations == codewords[employee]
        assert result.scores[0].candidate_id == employee
