"""Load and validate answer-free, seeded casebook scenario definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_GENERATORS = {
    "invisible_copy", "edited_text", "print_timeline", "ooxml_metadata",
    "log_fusion", "collusion", "account_sharing",
}
_TOOLS = {
    "intake", "hex", "invisible", "diff", "slot_matrix", "ooxml",
    "image_dots", "timeline", "auto_detector", "tardos", "notes", "report",
}
_FIELDS = {
    "case_id", "title", "brief", "objective", "generator", "master",
    "seed_offset", "tools", "hints",
}


@dataclass(frozen=True, slots=True)
class CaseDefinition:
    """Validated case instructions and generation parameters without a solution."""

    case_id: str
    title: str
    brief: str
    objective: str
    generator: str
    master: str
    seed_offset: int
    tools: tuple[str, ...]
    hints: tuple[str, ...]


def _text_field(data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"case field {field!r} must be a non-empty string")
    return value.strip()


def load_case_definition(path: str | Path) -> CaseDefinition:
    """Parse one safe YAML document and enforce the answer-free schema."""
    with Path(path).open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise TypeError("case definition must be a YAML mapping")
    unknown = set(data) - _FIELDS
    missing = _FIELDS - set(data)
    if unknown:
        raise ValueError(f"unknown case fields: {', '.join(sorted(unknown))}")
    if missing:
        raise ValueError(f"missing case fields: {', '.join(sorted(missing))}")
    generator = _text_field(data, "generator")
    if generator not in _GENERATORS:
        raise ValueError(f"unknown case generator: {generator}")
    case_id = _text_field(data, "case_id")
    if not case_id.startswith("C-") or len(case_id) > 32:
        raise ValueError("case ID must begin with C- and be at most 32 characters")
    tools = data["tools"]
    hints = data["hints"]
    seed_offset = data["seed_offset"]
    if not isinstance(tools, list) or not all(isinstance(item, str) for item in tools):
        raise ValueError("case tools must be a list of names")
    if len(set(tools)) != len(tools) or set(tools) - _TOOLS:
        raise ValueError("case tools contain duplicates or unknown tool names")
    if not isinstance(hints, list) or len(hints) != 3 or not all(
        isinstance(item, str) and item.strip() for item in hints
    ):
        raise ValueError("each case must contain exactly three non-empty hints")
    if not isinstance(seed_offset, int) or isinstance(seed_offset, bool):
        raise TypeError("seed_offset must be an integer")
    brief = _text_field(data, "brief")
    if len(brief.split()) > 50:
        raise ValueError("case brief must not exceed 50 words")
    return CaseDefinition(
        case_id=case_id,
        title=_text_field(data, "title"),
        brief=brief,
        objective=_text_field(data, "objective"),
        generator=generator,
        master=_text_field(data, "master"),
        seed_offset=seed_offset,
        tools=tuple(tools),
        hints=tuple(item.strip() for item in hints),
    )


def load_casebook(directory: str | Path | None = None) -> tuple[CaseDefinition, ...]:
    """Load sorted case definitions and reject duplicate IDs."""
    source = Path(directory) if directory is not None else Path(__file__).with_name("cases")
    definitions = tuple(
        load_case_definition(path) for path in sorted(source.glob("case-*.yaml"))
    )
    if not definitions:
        raise ValueError(f"no case definitions found in {source}")
    ids = [definition.case_id for definition in definitions]
    if len(ids) != len(set(ids)):
        raise ValueError("case IDs must be unique")
    return definitions
