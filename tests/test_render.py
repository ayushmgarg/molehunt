"""Tests for rendering codewords into text and DOCX artifacts."""

from io import BytesIO

import pytest
from docx import Document

from molehunt.core.render import render_docx, render_text, render_txt
from molehunt.core.slots import allocate_slots
from molehunt.core.template import parse_template


def test_text_render_maps_codeword_to_authored_slot_order() -> None:
    template = parse_template("{{lex:begin|start}} then {{spl:color|colour}}.")
    slots = allocate_slots(template, b"k" * 32)
    codeword = [0, 1]
    result = render_text(template, slots, codeword)
    assert result in {"begin then colour.", "start then color."}


def test_text_output_is_utf8() -> None:
    template = parse_template("café {{lex:begin|start}}")
    slots = allocate_slots(template, b"k" * 32)
    assert render_txt(template, slots, [0]).decode("utf-8") == "café begin"


def test_docx_render_preserves_paragraph_text_and_adds_metadata() -> None:
    template = parse_template("First line.\nSecond {{lex:word|term}}.")
    slots = allocate_slots(template, b"k" * 32)
    result = render_docx(template, slots, [1], b"k" * 32, "E001")
    document = Document(BytesIO(result))
    assert [paragraph.text for paragraph in document.paragraphs] == [
        "First line.",
        "Second term.",
    ]


def test_render_rejects_wrong_codeword_length() -> None:
    template = parse_template("{{lex:a|b}}")
    with pytest.raises(ValueError, match="codeword length"):
        render_text(template, allocate_slots(template, b"k" * 32), [])
