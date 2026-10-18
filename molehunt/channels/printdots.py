"""Encode and render a parity-checked 8x15 printer-identification dot grid."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from PIL import Image, ImageDraw

ROWS = 8
COLUMNS = 15
DATA_ROWS = ROWS - 1
DATA_COLUMNS = COLUMNS - 1
EPOCH = date(2020, 1, 1)


@dataclass(frozen=True, slots=True)
class DotMetadata:
    """Synthetic printer id, print date, and minute of day."""

    printer_id: int
    printed_on: date
    minute_of_day: int


def _validate(metadata: DotMetadata) -> int:
    if not 0 <= metadata.printer_id <= 255:
        raise ValueError("printer id must fit in 8 bits")
    day_count = (metadata.printed_on - EPOCH).days
    if not 0 <= day_count <= 65535:
        raise ValueError("print date must be within the 16-bit epoch range")
    if not 0 <= metadata.minute_of_day < 1440:
        raise ValueError("minute of day must be between 0 and 1439")
    return day_count


def _bits(value: int, width: int) -> list[int]:
    return [(value >> shift) & 1 for shift in range(width - 1, -1, -1)]


def _value(bits: Sequence[int]) -> int:
    result = 0
    for bit in bits:
        result = (result << 1) | bit
    return result


def encode_dot_grid(metadata: DotMetadata) -> tuple[tuple[int, ...], ...]:
    """Build a row-major 8x15 matrix with one parity bit per row and column."""
    day_count = _validate(metadata)
    payload = _bits(1, 4) + _bits(metadata.printer_id, 8) + _bits(day_count, 16)
    payload += _bits(metadata.minute_of_day, 11)
    payload.extend([0] * (DATA_ROWS * DATA_COLUMNS - len(payload)))
    grid = []
    for row in range(DATA_ROWS):
        values = payload[row * DATA_COLUMNS : (row + 1) * DATA_COLUMNS]
        grid.append(values + [sum(values) % 2])
    bottom = [sum(grid[row][column] for row in range(DATA_ROWS)) % 2 for column in range(DATA_COLUMNS)]
    bottom.append(sum(row[-1] for row in grid) % 2)
    grid.append(bottom)
    return tuple(tuple(row) for row in grid)


def decode_dot_grid(matrix: Sequence[Sequence[int]]) -> DotMetadata:
    """Validate 2D parity and decode the versioned printer/date/minute payload."""
    if len(matrix) != ROWS or any(len(row) != COLUMNS for row in matrix):
        raise ValueError("dot grid must be exactly 8 by 15")
    if any(bit not in (0, 1) for row in matrix for bit in row):
        raise ValueError("dot grid must contain only binary values")
    if any(sum(row) % 2 for row in matrix):
        raise ValueError("dot grid row parity failure")
    if any(sum(matrix[row][column] for row in range(ROWS)) % 2 for column in range(COLUMNS)):
        raise ValueError("dot grid column parity failure")

    payload = [matrix[row][column] for row in range(DATA_ROWS) for column in range(DATA_COLUMNS)]
    if _value(payload[:4]) != 1:
        raise ValueError("unsupported dot grid version")
    printer_id = _value(payload[4:12])
    day_count = _value(payload[12:28])
    minute_of_day = _value(payload[28:39])
    if minute_of_day >= 1440:
        raise ValueError("dot grid minute is outside the day")
    return DotMetadata(printer_id, EPOCH + timedelta(days=day_count), minute_of_day)


def render_dot_grid(
    image: Image.Image,
    metadata: DotMetadata,
    *,
    origin: tuple[int, int] = (0, 0),
    cell_size: int = 6,
    radius: int = 1,
    color: str = "#777777",
) -> Image.Image:
    """Draw faint dots into a copy of an image, leaving the source unchanged."""
    matrix = encode_dot_grid(metadata)
    x0, y0 = origin
    if cell_size < 3 or radius < 1 or radius * 2 >= cell_size:
        raise ValueError("dot cell and radius are too small or overlap")
    if x0 < 0 or y0 < 0 or x0 + COLUMNS * cell_size > image.width or y0 + ROWS * cell_size > image.height:
        raise ValueError("dot grid does not fit inside image")
    output = image.copy()
    draw = ImageDraw.Draw(output)
    for row, values in enumerate(matrix):
        for column, bit in enumerate(values):
            if bit:
                center_x = x0 + column * cell_size + cell_size // 2
                center_y = y0 + row * cell_size + cell_size // 2
                draw.ellipse(
                    (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
                    fill=color,
                )
    return output


def read_dot_grid(
    image: Image.Image,
    *,
    origin: tuple[int, int] = (0, 0),
    cell_size: int = 6,
    threshold: int = 200,
) -> DotMetadata:
    """Sample dot centers from a cleanly aligned image and validate parity."""
    x0, y0 = origin
    if cell_size < 3 or not 0 <= threshold <= 255:
        raise ValueError("invalid cell size or grayscale threshold")
    if x0 < 0 or y0 < 0 or x0 + COLUMNS * cell_size > image.width or y0 + ROWS * cell_size > image.height:
        raise ValueError("dot grid does not fit inside image")
    gray = image.convert("L")
    matrix = []
    for row in range(ROWS):
        values = []
        for column in range(COLUMNS):
            x = x0 + column * cell_size + cell_size // 2
            y = y0 + row * cell_size + cell_size // 2
            values.append(int(gray.getpixel((x, y)) < threshold))
        matrix.append(values)
    return decode_dot_grid(matrix)
