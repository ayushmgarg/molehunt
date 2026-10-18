"""Tests for slot windows located by exact SequenceMatcher blocks."""

from molehunt.core.slots import allocate_slots
from molehunt.core.template import parse_template
from molehunt.detect.align import align_to_master


def test_clean_master_maps_each_slot_window() -> None:
    template = parse_template("A {{lex:begin|start}}. Then {{lex:end|finish}}.")
    slots = allocate_slots(template, b"k" * 32)
    observed = template.render([0, 0])
    windows = align_to_master(template, slots, observed)
    regions = {window.slot.zero: observed[window.start : window.end] for window in windows}
    assert regions == {"begin": "begin", "end": "end"}


def test_changed_variants_are_inside_aligned_windows() -> None:
    template = parse_template("A {{lex:begin|start}}. Then {{lex:end|finish}}.")
    slots = allocate_slots(template, b"k" * 32)
    observed = template.render([1, 1])
    windows = align_to_master(template, slots, observed)
    regions = {window.slot.zero: observed[window.start : window.end] for window in windows}
    assert regions == {"begin": "start", "end": "finish"}


def test_truncated_slot_gets_empty_window_at_evidence_end() -> None:
    template = parse_template("A {{lex:begin|start}}. Then {{lex:end|finish}}. More text.")
    slots = allocate_slots(template, b"k" * 32)
    observed = "A start. Then"
    windows = align_to_master(template, slots, observed)
    missing = next(window for window in windows if window.slot.zero == "end")
    assert missing.start == missing.end == len(observed)
