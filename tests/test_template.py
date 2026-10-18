"""Tests for parsing and rendering authored variation slots."""

import pytest

from molehunt.core.template import Choice, Literal, parse_template


def test_parse_keeps_literals_and_choice_order() -> None:
    parsed = parse_template("A {{lex:begin|start}} B")
    assert parsed.nodes == (
        Literal("A "),
        Choice("lex", "begin", "start"),
        Literal(" B"),
    )


def test_render_selects_each_variant() -> None:
    parsed = parse_template("{{spl:colour|color}}, {{pun:,|}}")
    assert parsed.render([0, 0]) == "colour, ,"
    assert parsed.render([1, 1]) == "color, "


def test_template_without_choices_is_valid() -> None:
    parsed = parse_template("Plain master text.")
    assert parsed.render([]) == "Plain master text."


@pytest.mark.parametrize(
    "source",
    [
        "{{bad}}",
        "{{lex:a|b",
        "a }} b",
        "{{:a|b}}",
        "{{lex:a|b}}}}",
    ],
)
def test_malformed_markers_are_rejected(source: str) -> None:
    with pytest.raises(ValueError, match="variation marker"):
        parse_template(source)


def test_render_requires_exact_binary_codeword() -> None:
    parsed = parse_template("{{lex:a|b}}")
    with pytest.raises(ValueError, match="bit count"):
        parsed.render([])
    with pytest.raises(ValueError, match="0 or 1"):
        parsed.render([2])


def test_empty_variant_is_allowed() -> None:
    parsed = parse_template("word{{pun:,|}} next")
    assert parsed.render([0]) == "word, next"
    assert parsed.render([1]) == "word next"
