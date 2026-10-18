# Explain: print-dot channel

C7 encodes a version, 8-bit printer id, days since 2020-01-01, and minute of day.
The 7x14 data area sits inside an 8x15 grid; the last row and column hold parity.
Dots are rendered into a copy of the page image at a caller-selected margin.

The decoder checks every row and column parity before reading metadata.
`read_dot_grid` samples an aligned grid with a grayscale threshold. Rotation correction,
perspective correction, and noisy-photo decoding remain future work.

Worked example: printer 17, 2026-10-18, minute 142 encodes to a parity-valid grid.
Changing any single sampled bit causes a parity error instead of a silent decode.
