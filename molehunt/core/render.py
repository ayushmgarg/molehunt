"""Render employee codewords into deterministic text and DOCX copies."""

from __future__ import annotations

from collections.abc import Sequence
from io import BytesIO

from docx import Document

from molehunt.channels.docx_meta import embed_docx_metadata
from molehunt.core.slots import Slot, bits_in_source_order
from molehunt.core.template import Template


def render_text(template: Template, slots: Sequence[Slot], codeword: Sequence[int]) -> str:
    """Render the selected variants in template order from indexed code bits."""
    return template.render(bits_in_source_order(slots, codeword))


def render_txt(template: Template, slots: Sequence[Slot], codeword: Sequence[int]) -> bytes:
    """Return the rendered text encoded as UTF-8."""
    return render_text(template, slots, codeword).encode("utf-8")


def render_docx(
    template: Template,
    slots: Sequence[Slot],
    codeword: Sequence[int],
    key: bytes,
    employee_id: str,
) -> bytes:
    """Create a simple DOCX copy and add the keyed C6 metadata channel."""
    document = Document()
    text = render_text(template, slots, codeword)
    for line in text.split("\n"):
        document.add_paragraph(line)
    output = BytesIO()
    document.save(output)
    return embed_docx_metadata(output.getvalue(), key, employee_id)
