"""Fact-level canaries: keyed per-copy facts that survive paraphrase."""

from pathlib import Path

import pytest

from molehunt.analysis import analyze_text
from molehunt.core.autoslots import prepare_master
from molehunt.core.canaries import holder_values, mask, match_canaries, parse_canaries
from molehunt.core.codes import generate_codewords
from molehunt.core.render import render_text

KEY = bytes(range(32))
MASTER = Path(__file__).parents[1] / "data" / "masters" / "live" / "m8_midnight_carnival.md"
ROSTER = [f"A{i:02}" for i in range(1, 21)]


def _copy(prepared, holder: str) -> str:
    bits = generate_codewords(KEY, [holder], len(prepared.slots))[holder]
    return render_text(prepared.template, prepared.slots, bits,
                       holder_values(prepared.canaries, KEY, holder))


def test_master_declares_four_families_and_copies_differ() -> None:
    prepared = prepare_master(MASTER.read_text(encoding="utf-8"), KEY)
    assert [family.name for family in prepared.canaries] == ["codename", "budget", "venue",
                                                             "launch"]
    first, second = _copy(prepared, "A01"), _copy(prepared, "A02")
    assert "§" not in first and "{{" not in first
    assert holder_values(prepared.canaries, KEY, "A01") == holder_values(prepared.canaries,
                                                                         KEY, "A01")
    assert first != second


def test_a_one_line_paraphrase_still_points_at_the_holder() -> None:
    prepared = prepare_master(MASTER.read_text(encoding="utf-8"), KEY)
    facts = list(holder_values(prepared.canaries, KEY, "A07").values())
    headline = (f"Exclusive: studio's secret project {facts[0]} costs {facts[1]}, "
                f"launching {facts[3]} at {facts[2]}")
    report = match_canaries(headline, prepared.canaries, KEY, ROSTER)
    assert len(report.seen) == 4
    assert report.scores[0].holder == "A07" and report.scores[0].hits == 4
    assert report.scores[0].log10_lr > 3


def test_merged_copies_show_two_values_of_one_family() -> None:
    prepared = prepare_master(MASTER.read_text(encoding="utf-8"), KEY)
    names = [family.name for family in prepared.canaries]
    holders = next((a, b) for a in ROSTER for b in ROSTER
                   if holder_values(prepared.canaries, KEY, a)["§0§"]
                   != holder_values(prepared.canaries, KEY, b)["§0§"])
    text = " ".join(holder_values(prepared.canaries, KEY, h)["§0§"] for h in holders)
    report = match_canaries(text, prepared.canaries, KEY, ROSTER)
    assert report.merged_families == (names[0],)


def test_fingerprint_analysis_still_attributes_a_canary_copy() -> None:
    source = MASTER.read_text(encoding="utf-8")
    prepared = prepare_master(source, KEY)
    result = analyze_text(source, KEY, ROSTER, _copy(prepared, "A05"))
    assert result.decision().candidate_id == "A05"
    assert result.observed_slots == len(prepared.slots)


def test_mask_restores_sentinels_case_insensitively() -> None:
    body, families = parse_canaries({"room": ["Vault 9", "Crypt 4"]}, "Meet in {{can:room}}.")
    assert body == "Meet in §0§."
    assert mask("Meet in crypt  4.", families) == "Meet in §0§."


@pytest.mark.parametrize(("raw", "body", "message"), [
    ({"room": ["Vault 9"]}, "{{can:room}}", "at least two"),
    ({"room": ["A1", "a1"]}, "{{can:room}}", "repeated"),
    ({"room": ["Vault 9", "Crypt 4"]}, "{{can:hall}}", "unknown"),
    ({"room": ["Vault 9", "Crypt 4"]}, "no token", "never used"),
    ({"room": ["Vault 9", "Crypt 4"]}, "{{can:room}} Vault 9", "already appears"),
    (None, "{{can:room}}", "no canaries"),
])
def test_bad_declarations_are_rejected(raw, body, message) -> None:
    with pytest.raises(ValueError, match=message):
        parse_canaries(raw, body)
