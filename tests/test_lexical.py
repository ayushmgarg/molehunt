"""Tests for authored lexical replacement slots."""

import pytest

from molehunt.channels.lexical import LexicalInsertion, embed_lexical, extract_lexical


def test_synonym_slot_round_trip() -> None:
    embedded = embed_lexical(
        "Please begin the review.",
        [LexicalInsertion(7, "begin", "start", 1)],
    )
    assert embedded.text == "Please start the review."
    assert extract_lexical(embedded.text, embedded.locations) == (1,)


def test_variant_anchor_rejects_paraphrased_context() -> None:
    embedded = embed_lexical(
        "Please begin the review.",
        [LexicalInsertion(7, "begin", "start", 0)],
    )
    rewritten = embedded.text.replace("the review", "this work")
    assert extract_lexical(rewritten, embedded.locations) == (None,)


def test_word_boundary_prevents_matching_prefixes() -> None:
    embedded = embed_lexical(
        "The beginning matters.",
        [LexicalInsertion(4, "beginning", "start", 1)],
    )
    assert embedded.text == "The start matters."
    assert extract_lexical("The starting matters.", embedded.locations) == (None,)


def test_multiple_variants_adjust_offsets_in_input_order() -> None:
    embedded = embed_lexical(
        "begin then end",
        [LexicalInsertion(0, "begin", "start", 1), LexicalInsertion(11, "end", "finish", 1)],
    )
    assert embedded.text == "start then finish"
    assert extract_lexical(embedded.text, embedded.locations) == (1, 1)


@pytest.mark.parametrize(
    "text,slot",
    [
        ("beginning", LexicalInsertion(0, "begin", "start", 0)),
        ("begin", LexicalInsertion(0, "begin", "begin", 0)),
        ("begin", LexicalInsertion(2, "begin", "start", 0)),
        ("begin", LexicalInsertion(0, "begin", "start", 2)),
    ],
)
def test_invalid_lexical_slots_are_rejected(text: str, slot: LexicalInsertion) -> None:
    with pytest.raises(ValueError):
        embed_lexical(text, [slot])
