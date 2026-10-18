"""Tests for 8x15 print-dot metadata and parity checks."""

from datetime import date

import pytest
from PIL import Image

from molehunt.channels.printdots import (
    DotMetadata,
    decode_dot_grid,
    encode_dot_grid,
    read_dot_grid,
    render_dot_grid,
)


def test_matrix_round_trip_encodes_printer_date_and_minute() -> None:
    original = DotMetadata(printer_id=17, printed_on=date(2026, 10, 18), minute_of_day=142)
    matrix = encode_dot_grid(original)
    assert len(matrix) == 8
    assert all(len(row) == 15 for row in matrix)
    assert decode_dot_grid(matrix) == original


def test_bad_parity_is_rejected() -> None:
    matrix = [list(row) for row in encode_dot_grid(DotMetadata(1, date(2026, 1, 1), 0))]
    matrix[2][3] ^= 1
    with pytest.raises(ValueError, match="parity"):
        decode_dot_grid(matrix)


def test_rendered_dot_grid_can_be_read_from_png_pixels() -> None:
    metadata = DotMetadata(printer_id=201, printed_on=date(2025, 12, 31), minute_of_day=1439)
    source = Image.new("RGB", (240, 160), "white")
    marked = render_dot_grid(source, metadata, origin=(20, 30), cell_size=8)
    assert read_dot_grid(marked, origin=(20, 30), cell_size=8) == metadata


@pytest.mark.parametrize(
    "metadata",
    [
        DotMetadata(-1, date(2026, 1, 1), 0),
        DotMetadata(256, date(2026, 1, 1), 0),
        DotMetadata(1, date(2019, 12, 31), 0),
        DotMetadata(1, date(2026, 1, 1), 1440),
    ],
)
def test_invalid_metadata_is_rejected(metadata: DotMetadata) -> None:
    with pytest.raises(ValueError):
        encode_dot_grid(metadata)


def test_too_small_image_is_rejected() -> None:
    with pytest.raises(ValueError, match="fit"):
        render_dot_grid(Image.new("RGB", (30, 30), "white"), DotMetadata(1, date(2026, 1, 1), 0), cell_size=8)
