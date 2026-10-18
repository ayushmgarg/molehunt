"""Write a DOCX analysis report with evidence identity, rankings, and limitations."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from docx.shared import Inches
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from molehunt.detect.score import CandidateScore


def write_analysis_report(
    output_path: str | Path,
    *,
    evidence_name: str,
    evidence_sha256: str,
    observed_slots: int,
    total_slots: int,
    scores: Sequence[CandidateScore],
    flip_rate: float,
    case_id: str = "Not provided",
) -> Path:
    """Create a DOCX report; likelihood ratio uses a binomial null and flip model."""
    if len(evidence_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in evidence_sha256
    ):
        raise ValueError("evidence SHA-256 must be 64 lowercase hexadecimal characters")
    if not 0 <= observed_slots <= total_slots:
        raise ValueError("observed slot count must be between zero and total slots")
    if not 0 < flip_rate < 0.5:
        raise ValueError("flip rate must be strictly between zero and 0.5")
    output = Path(output_path)
    if output.suffix.casefold() not in {".docx", ".pdf"}:
        raise ValueError("analysis reports must use the .docx or .pdf extension")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.casefold() == ".pdf":
        _write_pdf_report(
            output,
            evidence_name=evidence_name,
            evidence_sha256=evidence_sha256,
            observed_slots=observed_slots,
            total_slots=total_slots,
            scores=scores,
            flip_rate=flip_rate,
            case_id=case_id,
        )
        return output

    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    document.add_heading("MoleHunt Evidence Analysis", level=0)
    document.add_paragraph(f"Generated UTC: {datetime.now(UTC).isoformat(timespec='seconds')}")
    document.add_heading("Case and evidence", level=1)
    document.add_paragraph(f"Case ID: {case_id}")
    document.add_paragraph(f"Evidence file: {evidence_name}")
    document.add_paragraph(f"Evidence SHA-256: {evidence_sha256}")
    document.add_paragraph(f"Observed slots: {observed_slots} / {total_slots}")

    document.add_heading("Method", level=1)
    document.add_paragraph(
        "Candidate codewords are compared with observed bits. Erased slots are omitted. "
        "The null model uses a 0.5 match probability; the alternative uses the configured "
        f"flip rate e={flip_rate:g}. LR = (1-e)^m e^(n-m) / 0.5^n, where m is matches "
        "and n is observed slots."
    )

    document.add_heading("Candidate ranking", level=1)
    table = document.add_table(rows=1, cols=7)
    table.style = "Light Shading Accent 1"
    headers = ("Rank", "ID", "Matches", "Observed", "Match fraction", "P(null)", "log10 LR")
    for cell, header in zip(table.rows[0].cells, headers, strict=True):
        cell.text = header
    for rank, score in enumerate(scores, start=1):
        row = table.add_row().cells
        values = (
            str(rank),
            score.candidate_id,
            str(score.matches),
            str(score.observed_slots),
            "—" if score.match_fraction is None else f"{score.match_fraction:.3f}",
            f"{score.binomial_p:.4g}",
            f"{score.log10_lr:.3f}",
        )
        for cell, value in zip(row, values, strict=True):
            cell.text = value

    document.add_heading("Interpretation and limitations", level=1)
    document.add_paragraph(
        "This table ranks synthetic copy fingerprints. It does not identify who handled or "
        "disclosed a document. The decision threshold has not been calibrated unless a "
        "separate benchmark establishes its error rate. Results depend on the supplied "
        "master, roster, observed evidence, and flip-rate assumption. Erasures reduce the "
        "number of scored slots."
    )
    document.save(output)
    return output


def _write_pdf_report(
    output: Path,
    *,
    evidence_name: str,
    evidence_sha256: str,
    observed_slots: int,
    total_slots: int,
    scores: Sequence[CandidateScore],
    flip_rate: float,
    case_id: str,
) -> None:
    """Render the same ranked evidence summary as a paginated PDF."""
    styles = getSampleStyleSheet()
    story = [
        Paragraph("MoleHunt Evidence Analysis", styles["Title"]),
        Paragraph(
            f"Generated UTC: {datetime.now(UTC).isoformat(timespec='seconds')}",
            styles["Normal"],
        ),
        Spacer(1, 0.15 * inch),
        Paragraph("Case and evidence", styles["Heading2"]),
        Paragraph(f"Case ID: {escape(case_id)}", styles["BodyText"]),
        Paragraph(f"Evidence file: {escape(evidence_name)}", styles["BodyText"]),
        Paragraph(f"Evidence SHA-256: {evidence_sha256}", styles["BodyText"]),
        Paragraph(f"Observed slots: {observed_slots} / {total_slots}", styles["BodyText"]),
        Spacer(1, 0.12 * inch),
        Paragraph("Method", styles["Heading2"]),
        Paragraph(
            "Erased slots are omitted. The null uses a 0.5 match probability; the "
            f"alternative uses flip rate e={flip_rate:g}. LR = "
            "(1-e)^m e^(n-m) / 0.5^n, where m is matches and n is observed slots.",
            styles["BodyText"],
        ),
        Spacer(1, 0.12 * inch),
        Paragraph("Candidate ranking", styles["Heading2"]),
    ]
    data = [["Rank", "ID", "Matches", "Observed", "Match fraction", "P(null)", "log10 LR"]]
    for rank, score in enumerate(scores, start=1):
        data.append(
            [
                str(rank), escape(score.candidate_id), str(score.matches),
                str(score.observed_slots),
                "—" if score.match_fraction is None else f"{score.match_fraction:.3f}",
                f"{score.binomial_p:.4g}", f"{score.log10_lr:.3f}",
            ]
        )
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3A4048")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#808080")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EFE9DC")]),
            ]
        )
    )
    story.extend(
        [
            table,
            Spacer(1, 0.15 * inch),
            Paragraph("Interpretation and limitations", styles["Heading2"]),
            Paragraph(
                "This table ranks synthetic copy fingerprints. It does not identify who handled "
                "or disclosed a document. The decision threshold has not been calibrated unless "
                "a separate benchmark establishes its error rate. Results depend on the supplied "
                "master, roster, evidence, and flip-rate assumption.",
                styles["BodyText"],
            ),
        ]
    )
    SimpleDocTemplate(
        str(output), pagesize=letter, rightMargin=0.5 * inch, leftMargin=0.5 * inch,
        topMargin=0.55 * inch, bottomMargin=0.55 * inch,
    ).build(story)
