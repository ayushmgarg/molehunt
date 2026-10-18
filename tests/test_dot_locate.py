"""Tests for locating and decoding C7 dots in rotated, noisy photos."""

from datetime import date

import pytest
from PIL import Image

from molehunt.attacks.transform import simulate_print_scan
from molehunt.channels.dot_locate import repair_single_error, scan_dot_grid
from molehunt.channels.printdots import DotMetadata, encode_dot_grid, render_dot_grid

META = DotMetadata(printer_id=88, printed_on=date(2025, 6, 9), minute_of_day=1312)


def test_single_flipped_bit_is_located_and_repaired() -> None:
    matrix = [list(row) for row in encode_dot_grid(META)]
    matrix[3][5] ^= 1
    fixed, cell = repair_single_error(matrix)
    assert cell == (3, 5)
    assert fixed == [list(row) for row in encode_dot_grid(META)]
    matrix[4][6] ^= 1
    with pytest.raises(ValueError, match="more than one"):
        repair_single_error(matrix)


@pytest.mark.parametrize("angle", [2.5, -3.0])
def test_yellow_grid_is_found_after_rotation_noise_and_jpeg(angle: float) -> None:
    page = Image.new("RGB", (420, 300), "white")
    marked = render_dot_grid(page, META, origin=(40, 50), cell_size=6, radius=1, color="#F2D400")
    photo = marked.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor="white")
    photo = simulate_print_scan(photo, strength=0.2, seed=4)
    scan = scan_dot_grid(photo, channel="B", window=120)
    assert scan.metadata == META
    assert abs(scan.angle - angle) <= 1.0


def test_blank_page_has_no_grid() -> None:
    with pytest.raises(ValueError, match="no parity-valid"):
        scan_dot_grid(Image.new("RGB", (200, 120), "white"), max_angle=0.5)
