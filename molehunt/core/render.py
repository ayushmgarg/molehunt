"""Render employee codewords into text, DOCX (C6 metadata), PDF and PNG (C7 dots) copies.

PDF and PNG copies use the monospace OCR font so a scan can be read back."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

from docx import Document

from molehunt.channels.docx_meta import embed_docx_metadata
from molehunt.channels.printdots import ROWS, DotMetadata, encode_dot_grid
from molehunt.core.canaries import fill
from molehunt.core.keys import digest
from molehunt.core.slots import Slot, bits_in_source_order
from molehunt.core.template import Template

Facts = Mapping[str, str] | None


def render_text(template: Template, slots: Sequence[Slot], codeword: Sequence[int],
                canary: Facts = None) -> str:
    """Render the selected variants in template order, then fill canary facts."""
    return fill(template.render(bits_in_source_order(slots, codeword)), canary)


def render_txt(template: Template, slots: Sequence[Slot], codeword: Sequence[int]) -> bytes:
    """Return the rendered text encoded as UTF-8."""
    return render_text(template, slots, codeword).encode("utf-8")


def render_docx(
    template: Template,
    slots: Sequence[Slot],
    codeword: Sequence[int],
    key: bytes,
    employee_id: str,
    canary: Facts = None,
) -> bytes:
    """Create a simple DOCX copy and add the keyed C6 metadata channel."""
    document = Document()
    text = render_text(template, slots, codeword, canary)
    for line in text.split("\n"):
        document.add_paragraph(line)
    output = BytesIO()
    document.save(output)
    return embed_docx_metadata(output.getvalue(), key, employee_id)


def pdf_dot_metadata(key: bytes, employee_id: str, issued: datetime) -> DotMetadata:
    """C7 payload for a PDF copy: keyed 8-bit station id, issue date, issue minute."""
    station = digest(key, "pdf-dots", employee_id)[0]
    return DotMetadata(station, issued.date(), issued.hour * 60 + issued.minute)


def render_pdf(
    template: Template,
    slots: Sequence[Slot],
    codeword: Sequence[int],
    metadata: DotMetadata,
    *,
    cell: float = 4.0,
    canary: Facts = None,
) -> bytes:
    """Typeset the copy with reportlab and tile faint yellow C7 dot grids per page.

    The 8x15 grid (row/column parity) repeats in the top and bottom margins of
    every page, so a crop of one tile or a photo of part of a page still carries it.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    matrix = encode_dot_grid(metadata)
    width, height = A4

    def dots(canvas, _document) -> None:
        canvas.saveState()
        canvas.setFillColorRGB(0.95, 0.83, 0.0)
        for y_top in (height - 20, 20 + ROWS * cell):
            for x0 in range(24, int(width) - 80, 140):
                for row, values in enumerate(matrix):
                    for column, bit in enumerate(values):
                        if bit:
                            canvas.circle(x0 + column * cell, y_top - row * cell, 0.7,
                                          stroke=0, fill=1)
        canvas.restoreState()

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    from molehunt.channels.ocr import font_path

    if "MoleHuntMono" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("MoleHuntMono", font_path()))
    styles = getSampleStyleSheet()
    body = styles["BodyText"].clone("mono", fontName="MoleHuntMono", fontSize=10, leading=16)
    story = []
    for line in render_text(template, slots, codeword, canary).split("\n"):
        story.append(Paragraph(escape(line), body) if line.strip()
                     else Spacer(1, 6))
    output = BytesIO()
    SimpleDocTemplate(output, pagesize=A4, topMargin=60, bottomMargin=60, invariant=1).build(
        story, onFirstPage=dots, onLaterPages=dots)
    return output.getvalue()


def render_png(template: Template, slots: Sequence[Slot], codeword: Sequence[int],
               metadata: DotMetadata, canary: Facts = None) -> bytes:
    """A print-like page image: OCR font text plus a yellow C7 grid in the margin."""
    from molehunt.channels.ocr import render_page
    from molehunt.channels.printdots import render_dot_grid

    page = render_page(render_text(template, slots, codeword, canary))
    marked = render_dot_grid(page, metadata, origin=(20, 20), cell_size=6, radius=1,
                             color="#F2D400")
    output = BytesIO()
    marked.save(output, format="PNG")
    return output.getvalue()
