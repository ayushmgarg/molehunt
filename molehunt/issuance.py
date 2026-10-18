"""Shared master registration and fingerprinted-copy issuance workflows."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from molehunt.core.codes import generate_codewords
from molehunt.core.keys import KEY_BYTES
from molehunt.core.render import render_docx, render_text
from molehunt.core.slots import allocate_slots
from molehunt.core.template import parse_template
from molehunt.registry import (
    add_employee,
    get_master,
    get_master_by_path,
    initialize_database,
    record_copy,
    register_master,
)


@dataclass(frozen=True, slots=True)
class IssueResult:
    """Identifier and slot count for one persisted issued copy."""

    copy_id: str
    master_id: str
    employee_id: str
    output_path: Path
    slot_count: int


def register_master_file(
    database: str | Path,
    key: bytes,
    master_path: str | Path,
    *,
    master_id: str | None = None,
    title: str | None = None,
) -> int:
    """Parse a template and transactionally register its keyed slot map."""
    if len(key) != KEY_BYTES:
        raise ValueError(f"key must contain {KEY_BYTES} bytes")
    path = Path(master_path)
    source = path.read_text(encoding="utf-8")
    template = parse_template(source)
    slots = allocate_slots(template, key)
    registry_id = master_id or path.stem
    registry_title = title or path.stem.replace("_", " ").title()
    initialize_database(database)
    register_master(database, registry_id, registry_title, path, source, slots)
    return len(slots)


def issue_registered_copy(
    database: str | Path,
    key: bytes,
    employee_id: str,
    master_reference: str | Path,
    output_path: str | Path,
) -> IssueResult:
    """Verify a registered master and write and record a fingerprinted copy."""
    if len(key) != KEY_BYTES:
        raise ValueError(f"key must contain {KEY_BYTES} bytes")
    if not employee_id.strip():
        raise ValueError("employee ID must not be empty")
    database_path = Path(database)
    if not database_path.is_file():
        raise ValueError("registry is not initialized; run molehunt init")
    reference = Path(master_reference)
    record = (
        get_master_by_path(database_path, reference)
        if reference.is_file()
        else get_master(database_path, str(master_reference))
    )
    if record is None:
        raise ValueError("master is not registered; run molehunt register first")
    source_path = Path(record["template_path"])
    source = source_path.read_text(encoding="utf-8")
    if hashlib.sha256(source.encode("utf-8")).hexdigest() != record["sha256"]:
        raise ValueError("registered master changed after registration")
    template = parse_template(source)
    slots = allocate_slots(template, key)
    bits = generate_codewords(key, [employee_id], len(slots))[employee_id]
    output = Path(output_path)
    if output.suffix.casefold() == ".docx":
        content = render_docx(template, slots, bits, key, employee_id)
    elif output.suffix.casefold() in {".txt", ".md"}:
        content = render_text(template, slots, bits).encode("utf-8")
    else:
        raise ValueError("output file must use .txt, .md, or .docx")
    if output.exists():
        raise FileExistsError(f"copy output already exists: {output}")
    add_employee(database_path, employee_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(content)
    try:
        copy_id = record_copy(database_path, record["id"], employee_id, output)
    except sqlite3.Error:
        output.unlink(missing_ok=True)
        raise
    return IssueResult(copy_id, record["id"], employee_id, output, len(slots))
