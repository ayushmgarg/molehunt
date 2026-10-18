"""Tests for secret slot placement, anchors, and channel capacity."""

import pytest

from molehunt.core.keys import keyed_order
from molehunt.core.slots import allocate_slots, bits_in_source_order, capacity_report
from molehunt.core.template import parse_template


def test_allocate_slots_assigns_a_keyed_permutation() -> None:
    template = parse_template("{{lex:a|b}} {{spc:x|y}} {{pun:,|}} {{dat:one|two}}")
    slots = allocate_slots(template, b"k" * 32)
    assert [slot.index for slot in slots] == list(range(4))
    assert sorted(slot.source_index for slot in slots) == list(range(4))
    assert {slot.index for slot in slots} == set(keyed_order(b"k" * 32, "slot-order", 4))


def test_slot_mapping_is_deterministic_and_key_dependent() -> None:
    template = parse_template("{{lex:a|b}} {{spc:x|y}} {{pun:,|}} {{dat:one|two}}")
    first = allocate_slots(template, b"k" * 32)
    assert first == allocate_slots(template, b"k" * 32)
    assert first != allocate_slots(template, b"z" * 32)


def test_slot_context_and_offset_use_zero_variant_skeleton() -> None:
    template = parse_template("North {{lex:gate|door}} stays closed.")
    slot = allocate_slots(template, b"k" * 32, context_chars=8)[0]
    assert slot.source_offset == len("North ")
    assert slot.anchor_before == "North "
    assert slot.anchor_after == " stays c"


def test_capacity_report_counts_each_channel() -> None:
    template = parse_template("{{lex:a|b}}{{lex:c|d}}{{pun:,|}}{{spc:x|y}}")
    assert capacity_report(allocate_slots(template, b"k" * 32)) == {
        "lex": 2,
        "pun": 1,
        "spc": 1,
    }


def test_bits_are_returned_in_template_order() -> None:
    template = parse_template("{{lex:a|b}} {{spc:x|y}} {{pun:,|}}")
    slots = allocate_slots(template, b"k" * 32)
    codeword = [0, 1, 0]
    result = bits_in_source_order(slots, codeword)
    assert result == [codeword[next(slot.index for slot in slots if slot.source_index == i)] for i in range(3)]
    assert (" x " in template.render(result)) == (result[1] == 0)


def test_slot_allocator_rejects_invalid_context_and_word() -> None:
    template = parse_template("{{lex:a|b}}")
    with pytest.raises(ValueError, match="context"):
        allocate_slots(template, b"k" * 32, context_chars=0)
    with pytest.raises(ValueError, match="codeword length"):
        bits_in_source_order(allocate_slots(template, b"k" * 32), [])


def test_capacity_report_rejects_duplicate_indices() -> None:
    template = parse_template("{{lex:a|b}} {{spc:x|y}}")
    slots = allocate_slots(template, b"k" * 32)
    with pytest.raises(ValueError, match="unique slot indices"):
        capacity_report((slots[0], slots[0]))
