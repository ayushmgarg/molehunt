"""Tests for allocator-inserted C1, C2, and C3b slots declared in master front matter."""

import unicodedata

import pytest

from molehunt.attacks.transform import attack_text
from molehunt.channels.homoglyph import CONFUSABLE_TO_LATIN, confusable_skeleton
from molehunt.core.autoslots import HOMOGLYPH_PAIRS, prepare_master, split_front_matter
from molehunt.core.codes import generate_codewords
from molehunt.core.render import render_text
from molehunt.core.slots import allocate_slots, capacity_report
from molehunt.core.template import parse_template
from molehunt.detect.align import align_to_master
from molehunt.detect.extract import extract_variants
from molehunt.detect.score import score_candidates

KEY = bytes(range(32))
BODY = "\n\n".join(
    f"Paragraph {index:02}: The board will {{{{lex:begin|start}}}} the audit of Project "
    f"Orion records today, and Mark Tomas will {{{{lex:check|verify}}}} the stored copies "
    "before the formal meeting opens."
    for index in range(12)
)
SOURCE = "---\nauto_slots:\n  zw: 30\n  nbsp: 12\n  hom: 10\n---\n" + BODY


def _observe(prepared, text: str) -> list[int | None]:
    windows = align_to_master(prepared.template, prepared.slots, text)
    by_index = {item.slot_index: item.bit for item in extract_variants(text, windows)}
    return [by_index[index] for index in range(len(prepared.slots))]


def test_master_without_front_matter_matches_plain_allocation() -> None:
    prepared = prepare_master(BODY, KEY)
    template = parse_template(BODY)
    assert prepared.template == template
    assert prepared.slots == allocate_slots(template, KEY)
    assert prepared.auto_counts == {"zw": 0, "nbsp": 0, "hom": 0}


def test_front_matter_is_split_and_validated() -> None:
    settings, body = split_front_matter(SOURCE)
    assert settings == {"auto_slots": {"zw": 30, "nbsp": 12, "hom": 10}}
    assert body == BODY
    with pytest.raises(ValueError, match="unknown front matter"):
        split_front_matter("---\nsecret: 1\n---\nText")
    with pytest.raises(ValueError, match="non-negative"):
        prepare_master("---\nauto_slots:\n  zw: -1\n---\nSome words here.", KEY)


def test_declared_counts_are_inserted_deterministically_and_keyed() -> None:
    prepared = prepare_master(SOURCE, KEY)
    report = capacity_report(prepared.slots)
    assert report == {"hom": 10, "lex": 24, "nbsp": 12, "zw": 30}
    assert prepare_master(SOURCE, KEY) == prepared
    other = prepare_master(SOURCE, bytes(reversed(range(32))))
    assert other.template != prepared.template


def test_too_many_requested_auto_slots_is_an_error() -> None:
    with pytest.raises(ValueError, match="eligible"):
        prepare_master("---\nauto_slots:\n  zw: 50\n---\nOnly four words here.", KEY)


def test_homoglyph_pairs_map_to_their_latin_letter() -> None:
    for latin, (first, second) in HOMOGLYPH_PAIRS.items():
        assert CONFUSABLE_TO_LATIN[first] == latin
        assert CONFUSABLE_TO_LATIN[second] == latin


def test_rendered_copy_reads_as_master_after_mark_removal() -> None:
    prepared = prepare_master(SOURCE, KEY)
    codeword = generate_codewords(KEY, ["E01"], len(prepared.slots))["E01"]
    rendered = render_text(prepared.template, prepared.slots, codeword)
    visible = confusable_skeleton(
        "".join(ch for ch in rendered if unicodedata.category(ch) != "Cf")
    ).replace("\u00a0", " ").replace("\u202f", " ")
    plain = render_text(parse_template(BODY), allocate_slots(parse_template(BODY), KEY),
                        [0] * 24)
    lexical_free = visible.replace("start", "begin").replace("verify", "check")
    assert lexical_free == plain


def test_clean_copy_recovers_every_bit_and_attacks_erase_their_channel() -> None:
    prepared = prepare_master(SOURCE, KEY)
    roster = [f"E{index:02}" for index in range(8)]
    codewords = generate_codewords(KEY, roster, len(prepared.slots))
    copy = render_text(prepared.template, prepared.slots, codewords["E03"])
    assert _observe(prepared, copy) == list(codewords["E03"])
    channels = [slot.channel for slot in prepared.slots]
    for attack_id, channel in (("A1", "zw"), ("A2b", "hom"), ("A3", "nbsp")):
        observed = _observe(prepared, attack_text(copy, attack_id, strength=1.0))
        erased = {channels[index] for index, bit in enumerate(observed) if bit is None}
        assert channel in erased
        assert all(
            bit is None for index, bit in enumerate(observed) if channels[index] == channel
        )
        known = [
            (bit, codewords["E03"][index]) for index, bit in enumerate(observed) if bit is not None
        ]
        assert known and all(bit == expected for bit, expected in known)
        assert score_candidates(observed, codewords)[0].candidate_id == "E03"
