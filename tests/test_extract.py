"""Tests for per-slot variant extraction and erasure semantics."""

from molehunt.core.render import render_text
from molehunt.core.slots import allocate_slots
from molehunt.core.template import parse_template
from molehunt.detect.align import align_to_master
from molehunt.detect.extract import extract_variants


def observe(template_text: str, bits: list[int], key: bytes = b"k" * 32):
    template = parse_template(template_text)
    slots = allocate_slots(template, key)
    rendered = render_text(template, slots, bits)
    windows = align_to_master(template, slots, rendered)
    return rendered, extract_variants(rendered, windows)


def test_clean_and_changed_copies_extract_source_order_bits() -> None:
    template_text = "A {{lex:begin|start}}. Then {{lex:end|finish}}."
    for bits in ([0, 0], [1, 1]):
        _, observations = observe(template_text, list(bits))
        assert {item.slot_index: item.bit for item in observations} == dict(enumerate(bits))


def test_truncated_slots_are_erasures() -> None:
    template = parse_template("A {{lex:begin|start}}. Then {{lex:end|finish}}. More text.")
    slots = allocate_slots(template, b"k" * 32)
    evidence = "A start. Then"
    observations = extract_variants(evidence, align_to_master(template, slots, evidence))
    assert any(item.bit is None for item in observations)


def test_missing_or_rewritten_variant_is_erasure() -> None:
    template = parse_template("A {{lex:begin|start}} now.")
    slots = allocate_slots(template, b"k" * 32)
    evidence = "A commenced now."
    observations = extract_variants(evidence, align_to_master(template, slots, evidence))
    assert len(observations) == 1 and observations[0].bit is None


def test_empty_punctuation_variant_can_be_extracted() -> None:
    template_text = "red, blue{{pun:,|}} and gold"
    _, with_comma = observe(template_text, [0])
    _, without_comma = observe(template_text, [1])
    assert with_comma[0].bit == 0
    assert without_comma[0].bit == 1
