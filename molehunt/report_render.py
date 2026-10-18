"""Render a neutral list of report sections to DOCX (python-docx) or PDF (reportlab).

A section is a heading, paragraphs, and tables (header row + body rows). Keeping
the content model separate from the two renderers guarantees that the DOCX and
the PDF carry exactly the same findings.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from docx.shared import Inches, Pt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


@dataclass(frozen=True, slots=True)
class ReportTable:
    """Header row plus body rows of plain strings."""

    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    monospace: bool = False


@dataclass(frozen=True, slots=True)
class Section:
    """One headed report section."""

    heading: str
    paragraphs: tuple[str, ...] = ()
    tables: tuple[ReportTable, ...] = field(default_factory=tuple)


def render_docx(title: str, sections: Sequence[Section], output: Path) -> None:
    """Write sections as headings, paragraphs, and shaded tables."""
    document = Document()
    page = document.sections[0]
    page.top_margin = page.bottom_margin = Inches(0.65)
    document.add_heading(title, level=0)
    for section in sections:
        document.add_heading(section.heading, level=1)
        for text in section.paragraphs:
            document.add_paragraph(text)
        for table_data in section.tables:
            table = document.add_table(rows=1, cols=len(table_data.header))
            table.style = "Light Shading Accent 1"
            for cell, header in zip(table.rows[0].cells, table_data.header, strict=True):
                cell.text = header
            for values in table_data.rows:
                cells = table.add_row().cells
                for cell, value in zip(cells, values, strict=True):
                    cell.text = value
                    if table_data.monospace:
                        for run in cell.paragraphs[0].runs:
                            run.font.name = "Consolas"
                            run.font.size = Pt(7)
    document.save(output)


def _pdf_table(table_data: ReportTable) -> Table:
    body = [list(table_data.header)] + [
        [escape(value) for value in row] for row in table_data.rows
    ]
    table = Table(body, repeatRows=1)
    font = "Courier" if table_data.monospace else "Helvetica"
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3A4048")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#808080")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), font),
                ("FONTSIZE", (0, 0), (-1, -1), 7 if table_data.monospace else 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EFE9DC")]),
            ]
        )
    )
    return table


def render_pdf(title: str, sections: Sequence[Section], output: Path) -> None:
    """Write the same sections as a paginated PDF."""
    styles = getSampleStyleSheet()
    story: list = [Paragraph(escape(title), styles["Title"])]
    for section in sections:
        story.append(Paragraph(escape(section.heading), styles["Heading2"]))
        story.extend(Paragraph(escape(text), styles["BodyText"]) for text in section.paragraphs)
        for table_data in section.tables:
            story.extend([Spacer(1, 0.08 * inch), _pdf_table(table_data)])
        story.append(Spacer(1, 0.12 * inch))
    SimpleDocTemplate(
        str(output), pagesize=letter, rightMargin=0.5 * inch, leftMargin=0.5 * inch,
        topMargin=0.55 * inch, bottomMargin=0.55 * inch, title=title,
    ).build(story)


def render(title: str, sections: Sequence[Section], output_path: str | Path) -> Path:
    """Choose the renderer from the file extension (.docx or .pdf)."""
    output = Path(output_path)
    suffix = output.suffix.casefold()
    if suffix not in {".docx", ".pdf"}:
        raise ValueError("reports must use the .docx or .pdf extension")
    output.parent.mkdir(parents=True, exist_ok=True)
    (render_docx if suffix == ".docx" else render_pdf)(title, sections, output)
    return output
