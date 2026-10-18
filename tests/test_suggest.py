"""Tests for contextual variation-slot suggestions."""

import pytest

from molehunt.channels.suggest import suggest_slots


def test_suggest_slots_reports_offsets_context_and_case() -> None:
    text = "We Begin safely. The color is gray. A beginner can help.\nThey ORGANIZE records."
    suggestions = suggest_slots(text, context_chars=12)
    assert [(item.channel, item.original, item.alternative) for item in suggestions] == [
        ("lex", "Begin", "Start"),
        ("spl", "color", "colour"),
        ("spl", "gray", "grey"),
        ("lex", "help", "assist"),
        ("spl", "ORGANIZE", "ORGANISE"),
    ]
    assert suggestions[0].line == 1
    assert suggestions[-1].line == 2
    assert "safely" in suggestions[0].context
    assert suggestions[0].offset == text.index("Begin")


@pytest.mark.parametrize("context_chars", [-1, -10])
def test_suggest_slots_rejects_negative_context(context_chars: int) -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        suggest_slots("text", context_chars=context_chars)
