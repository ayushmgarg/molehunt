"""Tests for append-only hash-chained custody events."""

import hashlib
import json

import pytest

from molehunt.custody import append_custody_entry, verify_custody


def test_append_and_verify_custody_chain(tmp_path) -> None:
    ledger = tmp_path / "custody.log"
    digest = hashlib.sha256(b"synthetic evidence").hexdigest()
    first = append_custody_entry(
        ledger, digest, actor="examiner-01", action="intake", details="demo case"
    )
    second = append_custody_entry(
        ledger, digest, actor="examiner-01", action="analysis", details="working copy"
    )

    assert first["seq"] == 1
    assert second["seq"] == 2
    assert second["prev_hash"] == first["entry_hash"]
    result = verify_custody(ledger)
    assert result.valid
    assert result.entries == 2
    assert result.broken_seq is None


def test_verification_reports_first_tampered_sequence(tmp_path) -> None:
    ledger = tmp_path / "custody.log"
    digest = hashlib.sha256(b"synthetic evidence").hexdigest()
    append_custody_entry(ledger, digest, actor="examiner-01", action="intake")
    append_custody_entry(ledger, digest, actor="examiner-01", action="analysis")
    lines = ledger.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[0])
    tampered["action"] = "modified"
    lines[0] = json.dumps(tampered, sort_keys=True, separators=(",", ":"))
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = verify_custody(ledger)
    assert not result.valid
    assert result.broken_seq == 1


def test_append_rejects_invalid_object_digest(tmp_path) -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        append_custody_entry(tmp_path / "custody.log", "not-a-hash", actor="x", action="y")
