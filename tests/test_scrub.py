"""Scrub detector: selective removal of hidden layers is flagged, plain copies are not."""

from pathlib import Path

import pytest

from molehunt.analysis import analyze_text
from molehunt.attacks.transform import attack_chain
from molehunt.core.autoslots import prepare_master
from molehunt.core.codes import generate_codewords
from molehunt.core.render import render_text
from molehunt.detect.scrub import detect_scrub

KEY = bytes(range(32))
MASTER = Path(__file__).parents[1] / "data" / "masters" / "m2_zoning.md"
ROSTER = [f"E{i:03}" for i in range(1, 21)]


@pytest.fixture(scope="module")
def copy() -> tuple[str, str]:
    source = MASTER.read_text(encoding="utf-8")
    prepared = prepare_master(source, KEY)
    bits = generate_codewords(KEY, ["E004"], len(prepared.slots))["E004"]
    return source, render_text(prepared.template, prepared.slots, bits)


def _report(source: str, text: str):
    return detect_scrub(analyze_text(source, KEY, ROSTER, text), text)


def test_clean_and_cut_down_copies_show_no_sanitising(copy) -> None:
    source, text = copy
    assert _report(source, text).verdict == "no sign of sanitising"
    excerpt = text[: len(text) // 2]
    assert _report(source, excerpt).score == 0.0


def test_stripping_tool_is_flagged_with_reasons(copy) -> None:
    source, text = copy
    report = _report(source, attack_chain(text, ["A1", "A2b", "A3", "A4"]))
    assert report.verdict == "deliberately sanitised"
    fired = {signal.layer for signal in report.signals if signal.fired}
    assert {"zw", "nbsp", "hom"} <= fired
    assert any("layer removed" in signal.reason for signal in report.signals)


def test_one_stripped_layer_is_partial(copy) -> None:
    source, text = copy
    report = _report(source, attack_chain(text, ["A1"]))
    assert [signal.layer for signal in report.signals if signal.fired] == ["zw"]
    assert report.verdict == "partly sanitised"


def test_tiny_fragment_is_not_judged(copy) -> None:
    source, text = copy
    assert _report(source, text[:200]).verdict == "too little text to judge"
