"""Create a read-only evidence original, writable working copy, and custody entry."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from molehunt.custody import append_custody_entry, sha256_file

_CASE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


@dataclass(frozen=True, slots=True)
class IntakeResult:
    """Paths and hash for an evidence file copied into a case directory."""

    case_id: str
    original: Path
    working_copy: Path
    custody_log: Path
    sha256: str


def _remove_tree(path: Path) -> None:
    """Remove an incomplete temporary intake tree, including read-only files."""
    def retry(function, target, _error) -> None:
        os.chmod(target, 0o600)
        function(target)

    shutil.rmtree(path, onerror=retry)


def intake_evidence(
    source: str | Path,
    case_id: str,
    *,
    actor: str,
    root: str | Path = "evidence",
) -> IntakeResult:
    """Stage evidence atomically as original/ and working/ inside a new case."""
    source_path = Path(source)
    case_root = Path(root)
    if _CASE_ID.fullmatch(case_id) is None:
        raise ValueError("case ID may contain only letters, digits, underscore, or hyphen")
    if not actor.strip():
        raise ValueError("actor must not be empty")
    if not source_path.is_file():
        raise ValueError(f"evidence file does not exist: {source_path}")
    destination = case_root / case_id
    temporary = case_root / f".{case_id}.intake"
    case_root.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"case already exists: {destination}")
    temporary.mkdir(exist_ok=False)
    try:
        original_dir = temporary / "original"
        working_dir = temporary / "working"
        original_dir.mkdir()
        working_dir.mkdir()
        original = original_dir / source_path.name
        working_copy = working_dir / source_path.name
        shutil.copyfile(source_path, original)
        original.chmod(0o444)
        digest = sha256_file(original)
        shutil.copyfile(original, working_copy)
        working_copy.chmod(0o644)
        custody_log = temporary / "custody.log"
        append_custody_entry(
            custody_log,
            digest,
            actor=actor,
            action="intake",
            details=f"original/{source_path.name}",
        )
        os.replace(temporary, destination)
    except BaseException:
        _remove_tree(temporary)
        raise
    return IntakeResult(
        case_id=case_id,
        original=destination / "original" / source_path.name,
        working_copy=destination / "working" / source_path.name,
        custody_log=destination / "custody.log",
        sha256=digest,
    )
