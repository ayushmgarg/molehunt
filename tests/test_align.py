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


def test_skeleton_drops_marks_folds_lookalikes_and_canonicalises_variants() -> None:
    from molehunt.detect.align import build_skeleton

    skeleton = build_skeleton("Start\u200b n\u043ew\u00a0\u201cok\u201d", [("begin", "start")])
    assert skeleton.text == 'begin now "ok"'
    assert (skeleton.starts[0], skeleton.ends[4]) == (0, 5)
    assert skeleton.starts[6] == 7


def test_stripped_repetitive_copy_does_not_read_a_neighbouring_paragraph() -> None:
    source = "\n\n".join(
        f"Item {index}: please {{{{lex:begin|start}}}} now\u200b and {{{{lex:check|verify}}}} it."
        for index in range(10)
    )
    template = parse_template(source)
    slots = allocate_slots(template, b"k" * 32)
    bits = [index % 2 for index in range(len(slots))]
    from molehunt.core.render import render_text
    from molehunt.detect.extract import extract_variants

    stripped = render_text(template, slots, bits).replace("\u200b", "")
    observed = extract_variants(stripped, align_to_master(template, slots, stripped))
    assert {item.slot_index: item.bit for item in observed} == dict(enumerate(bits))
