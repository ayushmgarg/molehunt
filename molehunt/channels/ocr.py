"""Classical OCR for scans of MoleHunt print copies (no machine learning).

Copies meant for printing use one known monospace font (DejaVu Sans Mono, shipped
with matplotlib, so it works offline). Reading a scan back:

1. Binarise: ink = pixels darker than the midpoint of paper (median) and ink
   (0.5th percentile) brightness.
2. Deskew: try angles -3..+3 degrees; keep the one whose row-ink profile has the
   largest variance (text lines become sharp peaks when level).
3. Lines: runs of rows containing ink. Size: line pitch / LINE_SPACING gives the
   font size; the font's advance width at that size gives the character pitch.
4. Characters: cut the line into fixed-pitch cells from the left margin, scale each
   cell to a 20 x 10 ink grid, and pick the printable ASCII glyph whose template
   grid has the highest cosine similarity (nearest neighbour against fixed font
   templates; nothing is trained). Near-empty cells are spaces. Each line's x
   origin is found by testing small offsets on its first cells.

Limits: needs this font and a roughly flat scan or photo; invisible characters,
look-alike letters and typography are lost, exactly as in real OCR.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont

LINE_SPACING = 1.6
COLUMNS = 78
_GLYPHS = [chr(code) for code in range(33, 127)]
_GRID = (20, 10)


def font_path() -> str:
    """Path of the bundled DejaVu Sans Mono TrueType font."""
    return font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans Mono"))


def _wrap(text: str, width: int = COLUMNS) -> list[str]:
    lines: list[str] = []
    for paragraph in text.replace("\r", "").split("\n"):
        line = ""
        for word in paragraph.split(" "):
            if line and len(line) + 1 + len(word) > width:
                lines.append(line)
                line = word
            else:
                line = f"{line} {word}" if line else word
        lines.append(line)
    return lines


def render_page(text: str, *, size: int = 28, margin: int = 80) -> Image.Image:
    """Render text as a white page in the OCR font (one tall page)."""
    font = ImageFont.truetype(font_path(), size)
    lines = _wrap(text)
    pitch = round(size * LINE_SPACING)
    advance = font.getlength("M")
    width = int(margin * 2 + advance * COLUMNS)
    page = Image.new("RGB", (width, margin * 2 + pitch * len(lines)), "white")
    draw = ImageDraw.Draw(page)
    for row, line in enumerate(lines):
        draw.text((margin, margin + row * pitch), line, font=font, fill="black")
    return page


@lru_cache(maxsize=8)
def _templates(size: int) -> tuple[np.ndarray, float, int]:
    """Glyph grids at this font size, plus advance width and the cap-top offset."""
    font = ImageFont.truetype(font_path(), size)
    advance = font.getlength("M")
    height = round(size * LINE_SPACING)
    cells = []
    for glyph in _GLYPHS:
        cell = Image.new("L", (round(advance), height), 255)
        ImageDraw.Draw(cell).text((0, 0), glyph, font=font, fill=0)
        cells.append(_grid(np.asarray(cell) < 128))
    probe = Image.new("L", (round(advance), height), 255)
    ImageDraw.Draw(probe).text((0, 0), "H", font=font, fill=0)
    cap_top = int(np.nonzero((np.asarray(probe) < 128).any(axis=1))[0][0])
    return np.stack(cells), advance, cap_top


def _grid(cell: np.ndarray) -> np.ndarray:
    """Ink fraction in a 20 x 10 grid over the whole cell (no cropping, so letter
    case and baseline position still count)."""
    image = Image.fromarray((cell * 255).astype(np.uint8))
    small = image.resize((_GRID[1], _GRID[0]), Image.Resampling.BOX)
    return (np.asarray(small, dtype=np.float32) / 255).ravel()


def _ink(image: Image.Image) -> np.ndarray:
    gray = np.asarray(image.convert("L"), dtype=np.float32)
    paper, ink = np.median(gray), np.percentile(gray, 0.5)
    return gray < (paper + ink) / 2


def _deskew(image: Image.Image) -> Image.Image:
    best, best_angle = -1.0, 0.0
    small = image.convert("L").reduce(2)
    for step in range(-12, 13):
        angle = step * 0.25
        profile = _ink(small.rotate(angle, fillcolor=255)).sum(axis=1)
        if profile.var() > best:
            best, best_angle = float(profile.var()), angle
    return image.convert("L").rotate(best_angle, resample=Image.Resampling.BICUBIC, fillcolor=255)


def _lines(ink: np.ndarray) -> list[tuple[int, int]]:
    rows = ink.sum(axis=1) > max(2, ink.shape[1] // 400)
    spans, start = [], None
    for index, flag in enumerate(rows):
        if flag and start is None:
            start = index
        elif not flag and start is not None:
            spans.append((start, index))
            start = None
    if start is not None:
        spans.append((start, len(rows)))
    return [span for span in spans if span[1] - span[0] > 3]


def ocr_image(image: Image.Image) -> str:
    """Read printed MoleHunt text back from a scan or flat photo."""
    upright = _deskew(image)
    ink = _ink(upright)
    lines = _lines(ink)
    if len(lines) < 2:
        return ""
    tops = [top for top, _ in lines]
    pitch = float(np.median(np.diff(tops)))
    size = max(8, round(pitch / LINE_SPACING))
    templates, advance, cap_top = _templates(size)
    height = round(size * LINE_SPACING)
    output = []
    for top, bottom in lines:
        used = np.nonzero(ink[top:bottom].any(axis=0))[0]
        if not used.size:
            output.append("")
            continue
        left = int(used.min())
        rows_with_ink = np.nonzero(ink[max(0, top - size // 3):bottom].any(axis=1))[0]
        top = max(0, top - size // 3) + int(rows_with_ink[0])
        count = int((used.max() - left) // advance) + 1

        def read(x0: float, *, shifts=(-2, -1, 0, 1, 2), top: int = top) -> tuple[float, str]:
            best, glyph = float("inf"), " "
            for shift in shifts:
                y0 = max(0, top - cap_top + shift)
                cell = ink[y0:y0 + height, round(x0):round(x0 + advance)]
                if cell.shape[0] < height // 2 or cell.shape[1] < 2 or cell.sum() < 4:
                    continue
                vector = _grid(cell)
                distances = 1 - (templates @ vector) / (
                    np.linalg.norm(templates, axis=1) * np.linalg.norm(vector) + 1e-9)
                index = int(distances.argmin())
                if distances[index] < best:
                    best, glyph = float(distances[index]), _GLYPHS[index]
            return best, glyph

        # Side bearing: find the x offset that best explains the first cells.
        offset = min(range(-6, 3), key=lambda dx: sum(
            min(read(left + dx + k * advance, shifts=(-1, 0, 1))[0], 1.0) for k in range(8)))
        chars = [read(left + offset + column * advance)[1] for column in range(count)]
        output.append("".join(chars).rstrip())
    return "\n".join(output)
