"""Embed authored synonym choices and align them with surrounding text."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

_ANCHOR_CHARS = 20


@dataclass(frozen=True, slots=True)
class SynonymSuggestion:
    """A candidate synonym pair requiring a human equivalence review."""

    zero: str
    one: str
    part_of_speech: str


# Suggestions only; the examiner must approve a pair in its sentence context.
SYNONYM_SUGGESTIONS = (
    SynonymSuggestion("begin", "start", "verb"),
    SynonymSuggestion("end", "finish", "verb"),
    SynonymSuggestion("help", "assist", "verb"),
    SynonymSuggestion("buy", "purchase", "verb"),
    SynonymSuggestion("choose", "select", "verb"),
    SynonymSuggestion("show", "display", "verb"),
    SynonymSuggestion("get", "receive", "verb"),
    SynonymSuggestion("need", "require", "verb"),
    SynonymSuggestion("tell", "inform", "verb"),
    SynonymSuggestion("ask", "request", "verb"),
    SynonymSuggestion("allow", "permit", "verb"),
    SynonymSuggestion("make", "create", "verb"),
    SynonymSuggestion("keep", "retain", "verb"),
    SynonymSuggestion("remove", "delete", "verb"),
    SynonymSuggestion("check", "verify", "verb"),
    SynonymSuggestion("leave", "depart", "verb"),
    SynonymSuggestion("send", "dispatch", "verb"),
    SynonymSuggestion("find", "locate", "verb"),
    SynonymSuggestion("quick", "rapid", "adjective"),
    SynonymSuggestion("safe", "secure", "adjective"),
)


@dataclass(frozen=True, slots=True)
class LexicalInsertion:
    """A two-word variant slot at an offset in the master text."""

    offset: int
    zero: str
    one: str
    bit: int


@dataclass(frozen=True, slots=True)
class LexicalLocation:
    """Rendered slot variants and following context for extraction."""

    offset: int
    zero: str
    one: str
    anchor_after: str


@dataclass(frozen=True, slots=True)
class EmbeddedLexical:
    """Rendered text and extraction locations in authored order."""

    text: str
    locations: tuple[LexicalLocation, ...]


def _word_character(character: str) -> bool:
    return character.isalnum() or character == "_"


def _whole_word(text: str, offset: int, word: str) -> bool:
    end = offset + len(word)
    before_is_boundary = offset == 0 or not _word_character(text[offset - 1])
    after_is_boundary = end >= len(text) or not _word_character(text[end])
    return text.startswith(word, offset) and before_is_boundary and after_is_boundary


def embed_lexical(
    text: str,
    slots: Sequence[LexicalInsertion],
) -> EmbeddedLexical:
    """Replace approved whole-word variants and retain following text anchors."""
    edits: list[tuple[int, int, str]] = []
    for slot in slots:
        if not 0 <= slot.offset <= len(text):
            raise ValueError("lexical offset must be within the text")
        if slot.bit not in (0, 1):
            raise ValueError("lexical bit must be 0 or 1")
        if not slot.zero or not slot.one or slot.zero == slot.one:
            raise ValueError("lexical variants must be distinct non-empty words")
        if not _whole_word(text, slot.offset, slot.zero):
            raise ValueError("zero variant must match a whole word at the offset")
        if not slot.one[0].isalnum() or not slot.one[-1].isalnum():
            raise ValueError("lexical variants must begin and end with a word character")
        replacement = slot.zero if slot.bit == 0 else slot.one
        edits.append((slot.offset, slot.offset + len(slot.zero), replacement))

    ordered = sorted(edits, key=lambda edit: edit[0])
    for previous, current in pairwise(ordered):
        if current[0] == previous[0] or current[0] < previous[1]:
            raise ValueError("lexical slots must not overlap")

    rendered = text
    for start, end, replacement in reversed(ordered):
        rendered = rendered[:start] + replacement + rendered[end:]

    locations = []
    for slot, (start, end, actual) in zip(slots, edits, strict=True):
        shift = sum(
            len(other_replacement) - (other_end - other_start)
            for other_start, other_end, other_replacement in edits
            if other_start < start
        )
        output_offset = start + shift
        anchor_start = output_offset + len(actual)
        anchor_after = rendered[anchor_start : anchor_start + _ANCHOR_CHARS]
        locations.append(LexicalLocation(output_offset, slot.zero, slot.one, anchor_after))
    return EmbeddedLexical(rendered, tuple(locations))


def extract_lexical(
    text: str,
    locations: Sequence[LexicalLocation],
) -> tuple[int | None, ...]:
    """Read a whole-word variant only when its following anchor still matches."""
    result = []
    for location in locations:
        observed = None
        for bit, variant in ((0, location.zero), (1, location.one)):
            end = location.offset + len(variant)
            if (
                end <= len(text)
                and _whole_word(text, location.offset, variant)
                and text.startswith(location.anchor_after, end)
            ):
                observed = bit
                break
        result.append(observed)
    return tuple(result)
