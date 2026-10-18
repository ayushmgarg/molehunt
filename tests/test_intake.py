"""Tests for evidence intake originals, working copies, and initial custody."""

import hashlib
import os

import pytest

from molehunt.custody import verify_custody
from molehunt.intake import intake_evidence


def test_intake_creates_read_only_original_and_working_copy(tmp_path) -> None:
    source = tmp_path / "leak.txt"
    source.write_text("synthetic evidence", encoding="utf-8")
    result = intake_evidence(source, "CASE-01", actor="examiner-01", root=tmp_path / "cases")

    assert result.original.read_bytes() == source.read_bytes()
    assert result.working_copy.read_bytes() == source.read_bytes()
    assert os.stat(result.original).st_mode & 0o222 == 0
    assert os.stat(result.working_copy).st_mode & 0o200
    assert result.sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert verify_custody(result.custody_log).valid


def test_intake_rejects_duplicate_case_directory(tmp_path) -> None:
    source = tmp_path / "leak.txt"
    source.write_text("synthetic evidence", encoding="utf-8")
    root = tmp_path / "cases"
    intake_evidence(source, "CASE-01", actor="examiner-01", root=root)
    with pytest.raises(FileExistsError):
        intake_evidence(source, "CASE-01", actor="examiner-01", root=root)


@pytest.mark.parametrize("case_id", ["../outside", "", "two words"])
def test_intake_rejects_unsafe_case_id(tmp_path, case_id: str) -> None:
    source = tmp_path / "leak.txt"
    source.write_text("synthetic evidence", encoding="utf-8")
    with pytest.raises(ValueError, match="case ID"):
        intake_evidence(source, case_id, actor="examiner-01", root=tmp_path / "cases")
