"""Tests for the shared single-leaker analysis entry point."""

import pytest

from molehunt.analysis import analyze_text
from molehunt.attacks.transform import attack_text
from molehunt.core.autoslots import prepare_master
from molehunt.core.codes import generate_codewords
from molehunt.core.render import render_text

KEY = bytes(range(32))
SOURCE = (
    "---\nauto_slots:\n  zw: 12\n  hom: 4\n---\n"
    + "\n\n".join(
        f"Section {index}: we {{{{lex:begin|start}}}} the review and {{{{spl:analyze|analyse}}}} "
        "each stored ledger before Monday."
        for index in range(8)
    )
)
ROSTER = [f"E{index:02}" for index in range(10)]


def _copy(employee: str) -> str:
    prepared = prepare_master(SOURCE, KEY)
    bits = generate_codewords(KEY, ROSTER, len(prepared.slots))[employee]
    return render_text(prepared.template, prepared.slots, bits)


def test_clean_copy_ranks_owner_first_with_all_slots_observed() -> None:
    result = analyze_text(SOURCE, KEY, ROSTER, _copy("E04"))
    assert result.scores[0].candidate_id == "E04"
    assert result.observed_slots == len(result.prepared.slots) == 32
    assert result.channel_survival() == {"hom": (4, 4), "lex": (8, 8), "spl": (8, 8), "zw": (12, 12)}


def test_stripped_copy_erases_zero_width_but_keeps_owner_first() -> None:
    result = analyze_text(SOURCE, KEY, ROSTER, attack_text(_copy("E07"), "A1"))
    assert result.channel_survival()["zw"] == (0, 12)
    assert result.scores[0].candidate_id == "E07"
    top = result.scores[0]
    assert top.matches == top.observed_slots == 20


def test_rejects_short_key() -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        analyze_text(SOURCE, b"short", ROSTER, "text")


def test_decision_attributes_clean_copy_and_withholds_on_empty_text() -> None:
    clean = analyze_text(SOURCE, KEY, ROSTER, _copy("E02")).decision()
    assert clean.outcome == "attribute" and clean.candidate_id == "E02"
    empty = analyze_text(SOURCE, KEY, ROSTER, "unrelated words only").decision()
    assert empty.outcome == "no attribution"


def test_collusion_mode_accuses_both_colluders_only() -> None:
    from pathlib import Path

    from molehunt.analysis import analyze_collusion, tardos_codewords
    from molehunt.attacks.collusion import collude_bits

    source = Path(__file__).parents[1].joinpath("data", "masters", "m2_zoning.md").read_text(
        encoding="utf-8"
    )
    roster = [f"E{index:03}" for index in range(1, 31)]
    prepared = prepare_master(source, KEY)
    _, codewords = tardos_codewords(KEY, roster, len(prepared.slots))
    merged = collude_bits([codewords["E005"], codewords["E021"]], "majority", seed=3)
    leak = render_text(prepared.template, prepared.slots, merged)
    result = analyze_collusion(source, KEY, roster, leak)
    assert set(result.accused) == {"E005", "E021"}
    assert result.violations == ()
    assert result.calibration.threshold > 0
