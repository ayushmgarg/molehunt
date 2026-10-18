# Explain: finding print dots in a photo (C7, Case 3)

Input: a phone photo of a printed page, rotated a few degrees, blurred, noisy, JPEG.

1. Channel split: yellow dots are dark in the blue channel (yellow = red + green).
2. Threshold: paper = median pixel, ink = 0.02nd percentile. Dark if below their
   midpoint. A 3x3 box vote (>= 4 of 9 dark) removes single noisy pixels.
3. Search: for angles -6..+6 degrees in 0.25 steps, rotate the photo back, then
   sample the 8x15 cell centres at every origin in a window (NumPy, all at once).
4. Parity: keep placements whose row and column parities all hold and whose
   version nibble is 0001. If exactly one row and one column fail, flip the cell
   where they cross (single-bit repair).
5. Vote: the real grid decodes the same at many neighbouring origins and angles;
   a chance parity pass is isolated. The most frequent decode wins.

Why parity helps: 22 independent parity checks pass by chance with probability
about 2^-22 for a random placement, and one flipped dot is located and fixed.

Worked example: dots for printer 88, 2025-06-09, minute 1312, photo rotated 2.5
degrees with noise. Exact-parity votes at angles 2.0-2.75 all give that metadata,
so it is returned with angle ~2.5.
