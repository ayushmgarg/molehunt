"""Append and verify custody events using a SHA-256 linked hash chain."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

GENESIS_HASH = "0" * 64
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class CustodyVerification:
    """Integrity status and the first invalid one-based sequence, if any."""

    valid: bool
    entries: int
    broken_seq: int | None = None


def _canonical(payload: dict[str, Any]) -> bytes:
    """Serialize payload keys and values deterministically for hashing."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _entry_hash(previous: str, payload: dict[str, Any]) -> str:
    """Hash the prior lowercase hex digest followed by canonical event JSON."""
    return hashlib.sha256(previous.encode("ascii") + _canonical(payload)).hexdigest()


def sha256_file(path: str | Path) -> str:
    """Hash a file incrementally without loading its contents into memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_custody(path: str | Path) -> CustodyVerification:
    """Check sequence numbers, previous hashes, and event hashes from genesis."""
    ledger = Path(path)
    previous = GENESIS_HASH
    count = 0
    with ledger.open("r", encoding="utf-8") as stream:
        for expected_seq, line in enumerate(stream, start=1):
            try:
                entry = json.loads(line)
                payload = {
                    field: entry[field]
                    for field in ("seq", "ts", "actor", "action", "object_sha256", "details")
                }
                valid = (
                    payload["seq"] == expected_seq
                    and entry["prev_hash"] == previous
                    and _DIGEST.fullmatch(entry["object_sha256"]) is not None
                    and entry["entry_hash"] == _entry_hash(previous, payload)
                )
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                return CustodyVerification(False, count, expected_seq)
            if not valid:
                return CustodyVerification(False, count, expected_seq)
            previous = entry["entry_hash"]
            count += 1
    return CustodyVerification(True, count)


def append_custody_entry(
    path: str | Path,
    object_sha256: str,
    *,
    actor: str,
    action: str,
    details: str = "",
) -> dict[str, Any]:
    """Append a UTC-stamped event after verifying the existing ledger."""
    ledger = Path(path)
    if _DIGEST.fullmatch(object_sha256) is None:
        raise ValueError("object SHA-256 must be 64 lowercase hexadecimal characters")
    if not actor.strip() or not action.strip():
        raise ValueError("actor and action must not be empty")
    if ledger.exists():
        verification = verify_custody(ledger)
        if not verification.valid:
            raise ValueError(f"custody log is broken at seq {verification.broken_seq}")
        with ledger.open("rb") as stream:
            lines = stream.readlines()
        previous = json.loads(lines[-1])["entry_hash"] if lines else GENESIS_HASH
        sequence = verification.entries + 1
    else:
        previous = GENESIS_HASH
        sequence = 1
    payload = {
        "seq": sequence,
        "ts": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "actor": actor.strip(),
        "action": action.strip(),
        "object_sha256": object_sha256,
        "details": details,
    }
    entry = {
        **payload,
        "prev_hash": previous,
        "entry_hash": _entry_hash(previous, payload),
    }
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
        stream.write("\n")
    return entry
