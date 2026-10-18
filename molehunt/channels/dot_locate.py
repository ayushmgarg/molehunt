"""Find and read a C7 dot grid in a rotated, noisy photo of a printed page.

Steps (Case 3 player steps, automated):
1. Channel split: yellow dots are dark in the blue channel; grey dots in luminance.
2. Contrast: paper = median value, ink = 0.02nd percentile (dots cover well under
   1 percent of the page); threshold at their midpoint, then require 4 of 9
   pixels in a 3x3 box so one noisy pixel cannot flip a sample.
3. Search: for each candidate angle, undo the rotation about the image centre,
   then sample the 8x15 cell centres for every origin in a search window
   (vectorised with NumPy).
4. Keep every placement whose row and column parities hold (or whose single bad
   row and single bad column meet at one cell, which is flipped: single-bit
   repair) and whose version nibble is 1.
5. Vote: the true grid decodes identically at many neighbouring origins and
   angles, while chance parity passes are isolated, so the most frequent
   metadata wins (exact-parity votes before repaired ones); the reported angle
   and origin are those of the winner's median-angle hit.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np
from PIL import Image

from molehunt.channels.printdots import COLUMNS, ROWS, DotMetadata, decode_dot_grid


@dataclass(frozen=True, slots=True)
class DotScan:
    """Decoded metadata plus where and how it was found."""

    metadata: DotMetadata
    angle: float
    origin: tuple[int, int]
    repaired_cell: tuple[int, int] | None


def repair_single_error(matrix: list[list[int]]) -> tuple[list[list[int]], tuple[int, int] | None]:
    """Fix one flipped bit located by one failing row and one failing column."""
    bad_rows = [r for r in range(ROWS) if sum(matrix[r]) % 2]
    bad_cols = [c for c in range(COLUMNS) if sum(matrix[r][c] for r in range(ROWS)) % 2]
    if not bad_rows and not bad_cols:
        return matrix, None
    if len(bad_rows) == 1 and len(bad_cols) == 1:
        fixed = [row[:] for row in matrix]
        fixed[bad_rows[0]][bad_cols[0]] ^= 1
        return fixed, (bad_rows[0], bad_cols[0])
    raise ValueError("dot grid has more than one parity error")


def _dark_mask(image: Image.Image, channel: str) -> np.ndarray:
    rgb = np.asarray(image.convert("RGB"), dtype=float)
    plane = rgb[:, :, 2] if channel == "B" else rgb @ np.array([0.299, 0.587, 0.114])
    paper, ink = np.median(plane), np.percentile(plane, 0.02)
    if paper - ink < 40:
        return np.zeros(plane.shape, dtype=bool)
    dark = (plane < (paper + ink) / 2).astype(float)
    padded = np.pad(dark, 1, mode="edge")
    smooth = sum(
        padded[1 + dy : 1 + dy + dark.shape[0], 1 + dx : 1 + dx + dark.shape[1]]
        for dy in (-1, 0, 1)
        for dx in (-1, 0, 1)
    ) / 9
    return smooth >= 4 / 9


def _candidates(mask: np.ndarray, cell: int, window: int) -> np.ndarray:
    """Return sampled grids, shape (origins_y, origins_x, ROWS, COLUMNS)."""
    half = cell // 2
    rows = np.arange(ROWS) * cell + half
    cols = np.arange(COLUMNS) * cell + half
    oy = np.arange(min(window, mask.shape[0] - ROWS * cell))
    ox = np.arange(min(window, mask.shape[1] - COLUMNS * cell))
    ys = oy[:, None, None, None] + rows[None, None, :, None]
    xs = ox[None, :, None, None] + cols[None, None, None, :]
    return mask[ys, xs].astype(np.int8)


def scan_dot_grid(
    image: Image.Image,
    *,
    cell_size: int = 6,
    channel: str = "L",
    max_angle: float = 6.0,
    angle_step: float = 0.25,
    window: int = 96,
) -> DotScan:
    """Search angles and origins for a parity-valid grid; repair one bad bit."""
    if channel not in {"L", "B"}:
        raise ValueError("channel must be 'L' (grey dots) or 'B' (yellow dots)")
    steps = round(max_angle / angle_step)
    votes: Counter = Counter()
    repairs: Counter = Counter()
    hits: dict[DotMetadata, list[DotScan]] = {}
    for k in range(-steps, steps + 1):
        angle = k * angle_step
        upright = image.convert("RGB").rotate(
            -angle, resample=Image.Resampling.BICUBIC, fillcolor="white"
        )
        grids = _candidates(_dark_mask(upright, channel), cell_size, window)
        bad_rows = (grids.sum(axis=3) % 2).sum(axis=2)
        bad_cols = (grids.sum(axis=2) % 2).sum(axis=2)
        version = grids[:, :, 0, :4] @ np.array([8, 4, 2, 1])
        plausible = (bad_rows <= 1) & (bad_cols <= 1) & (bad_rows == bad_cols) & (version == 1)
        for y, x in zip(*np.nonzero(plausible), strict=True):
            try:
                fixed, cell = repair_single_error(grids[y, x].tolist())
                metadata = decode_dot_grid(fixed)
            except ValueError:
                continue
            (repairs if cell else votes)[metadata] += 1
            hits.setdefault(metadata, []).append(
                DotScan(metadata, angle, (int(x), int(y)), cell)
            )
    tally = votes or repairs
    if not tally:
        raise ValueError("no parity-valid dot grid found")
    winner, _ = tally.most_common(1)[0]
    found = [hit for hit in hits[winner] if (hit.repaired_cell is None) == bool(votes)]
    return sorted(found, key=lambda hit: hit.angle)[len(found) // 2]
