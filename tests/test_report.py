"""Tests for generated analysis report content."""

from docx import Document

from molehunt.detect.score import score_candidates
from molehunt.report import write_analysis_report


def test_analysis_report_records_hash_rankings_and_limitations(tmp_path) -> None:
    scores = score_candidates([1, 0, 1], {"E001": [1, 0, 1], "E002": [0, 0, 0]})
    output = tmp_path / "analysis.docx"
    write_analysis_report(
        output,
        evidence_name="leak.txt",
        evidence_sha256="a" * 64,
        observed_slots=3,
        total_slots=4,
        scores=scores,
        flip_rate=0.15,
    )

    document = Document(output)
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "leak.txt" in text
    assert "a" * 64 in text
    assert "threshold has not been calibrated" in text.lower()
    assert any(cell.text == "E001" for row in document.tables[0].rows for cell in row.cells)


def test_analysis_report_can_be_written_as_pdf(tmp_path) -> None:
    output = tmp_path / "analysis.pdf"
    scores = score_candidates([1, 0], {"E001": [1, 0]})
    write_analysis_report(
        output,
        evidence_name="leak.txt",
        evidence_sha256="b" * 64,
        observed_slots=2,
        total_slots=2,
        scores=scores,
        flip_rate=0.15,
    )
    assert output.read_bytes().startswith(b"%PDF-")
