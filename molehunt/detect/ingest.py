"""Read supported evidence formats without modifying their source files."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from docx.text.paragraph import Paragraph
from PIL import Image, UnidentifiedImageError

from molehunt.channels.printdots import DotMetadata, read_dot_grid


@dataclass(frozen=True, slots=True)
class IngestedEvidence:
    """Immutable acquisition facts plus decoded text or image metadata."""

    path: str
    format: str
    sha256: str
    size_bytes: int
    text: str | None
    image_size: tuple[int, int] | None = None
    dot_metadata: DotMetadata | None = None


def _docx_text(raw: bytes) -> str:
    try:
        document = Document(BytesIO(raw))
    except (BadZipFile, PackageNotFoundError, KeyError, ValueError) as error:
        raise ValueError("invalid DOCX evidence") from error
    blocks: list[str] = []
    for block in document.iter_inner_content():
        if isinstance(block, Paragraph):
            blocks.append(block.text)
        elif isinstance(block, Table):
            blocks.extend("\t".join(cell.text for cell in row.cells) for row in block.rows)
    return "\n".join(blocks)


def ingest(
    path: str | Path,
    *,
    dot_origin: tuple[int, int] | None = None,
    dot_cell_size: int = 6,
) -> IngestedEvidence:
    """Hash raw evidence bytes, then decode UTF-8 text, DOCX text, or PNG metadata."""
    target = Path(path)
    try:
        raw = target.read_bytes()
    except OSError as error:
        raise ValueError(f"cannot read evidence: {target}") from error
    suffix = target.suffix.casefold()
    sha256 = hashlib.sha256(raw).hexdigest()
    decoded_text: str | None = None
    image_size = None
    dot_metadata = None

    if suffix in {".txt", ".md"}:
        try:
            decoded_text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise ValueError("text evidence must be valid UTF-8") from error
        file_format = "txt" if suffix == ".txt" else "md"
    elif suffix == ".docx":
        decoded_text = _docx_text(raw)
        file_format = "docx"
    elif suffix == ".png":
        try:
            with Image.open(BytesIO(raw)) as image:
                image.load()
                image_size = image.size
                if dot_origin is not None:
                    dot_metadata = read_dot_grid(
                        image,
                        origin=dot_origin,
                        cell_size=dot_cell_size,
                    )
        except (UnidentifiedImageError, OSError, ValueError) as error:
            raise ValueError("invalid PNG evidence or dot grid") from error
        file_format = "png"
    else:
        raise ValueError("supported evidence formats: txt, md, docx, png")

    return IngestedEvidence(
        path=str(target),
        format=file_format,
        sha256=sha256,
        size_bytes=len(raw),
        text=decoded_text,
        image_size=image_size,
        dot_metadata=dot_metadata,
    )
