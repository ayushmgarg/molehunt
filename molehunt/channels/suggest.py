"""Find curated variation suggestions without changing the examiner's master."""

from __future__ import annotations

import re
from dataclasses import dataclass

from molehunt.channels.lexical import SYNONYM_SUGGESTIONS
from molehunt.channels.spelling import SPELLING_SUGGESTIONS


@dataclass(frozen=True, slots=True)
class SlotSuggestion:
    """One contextual suggestion that still needs human meaning review."""

    channel: str
    offset: int
    line: int
    original: str
    alternative: str
    context: str


def _match_case(source: str, alternative: str) -> str:
    """Copy lower, upper, or title casing from the matched source token."""
    if source.isupper():
        return alternative.upper()
    if source.istitle():
        return alternative.title()
    return alternative.lower()


def suggest_slots(text: str, *, context_chars: int = 48) -> tuple[SlotSuggestion, ...]:
    """Find whole-word lexical and spelling pairs with line and nearby context."""
    if context_chars < 0:
        raise ValueError("context_chars must not be negative")
    pairs = [
        ("lex", pair.zero, pair.one) for pair in SYNONYM_SUGGESTIONS
    ] + [
        ("spl", pair.zero, pair.one) for pair in SPELLING_SUGGESTIONS
    ]
    suggestions: list[SlotSuggestion] = []
    for channel, zero, one in pairs:
        pattern = re.compile(rf"(?<!\w){re.escape(zero)}(?!\w)", re.IGNORECASE)
        for match in pattern.finditer(text):
            start, end = match.span()
            suggestions.append(
                SlotSuggestion(
                    channel=channel,
                    offset=start,
                    line=text.count("\n", 0, start) + 1,
                    original=match.group(),
                    alternative=_match_case(match.group(), one),
                    context=text[max(0, start - context_chars) : min(len(text), end + context_chars)]
                    .replace("\n", " ")
                    .strip(),
                )
            )
    return tuple(sorted(suggestions, key=lambda item: (item.offset, item.channel, item.original)))
