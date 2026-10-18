"""Tests for the OOXML explorer logic on a generated Case 4 package."""

import csv
import json
from io import BytesIO
from zipfile import ZipFile

import pytest
from docx import Document

from molehunt.game.casebook import load_casebook
from molehunt.game.generator import generate_case
from molehunt.ui.ooxml_view import explore_docx, pretty_part


def test_case_four_metadata_rsids_and_decoys_are_exposed(tmp_path) -> None:
    definition = next(item for item in load_casebook() if item.generator == "ooxml_metadata")
    instance = generate_case(definition, tmp_path / "c4", seed=3, master_path="data/demo/master.md")
    truth = json.loads(instance.ground_truth_path.read_text(encoding="utf-8"))
    report = explore_docx(instance.evidence_path)
    assert "word/document.xml" in dict(report.parts)
    assert report.core["lastModifiedBy"] == truth["decoy_last_modified_by"]
    assert report.core["creator"] == ""
    assert report.app["Template"] == truth["template"]
    assert report.custom["MoleHuntTag"] == truth["copy_owner"]
    with (instance.public_dir / "rsid_registry.csv").open(encoding="utf-8") as stream:
        registry = {row["employee_id"]: row["rsid_root"] for row in csv.DictReader(stream)}
    assert report.rsid_root == registry[truth["copy_owner"]]
    assert report.rsid_root in report.settings_rsids
    assert report.content_rsids and report.tracked_changes == ()
    assert "<w:document" in pretty_part(instance.evidence_path, "word/document.xml")


def test_tracked_changes_are_listed_with_author(tmp_path) -> None:
    stream = BytesIO()
    Document().save(stream)
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    body = (f'<w:document xmlns:w="{w}"><w:body><w:p><w:ins w:author="EX-9" '
            'w:date="2025-01-01T00:00:00Z"><w:r><w:t>added</w:t></w:r></w:ins></w:p>'
            "</w:body></w:document>")
    target = tmp_path / "tracked.docx"
    with ZipFile(stream) as source, ZipFile(target, "w") as package:
        for info in source.infolist():
            data = body.encode() if info.filename == "word/document.xml" else source.read(info)
            package.writestr(info, data)
    assert explore_docx(target).tracked_changes == (("ins", "EX-9", "2025-01-01T00:00:00Z", "added"),)
    (tmp_path / "bad.docx").write_bytes(b"not a zip")
    with pytest.raises(ValueError, match="not a readable"):
        explore_docx(tmp_path / "bad.docx")
