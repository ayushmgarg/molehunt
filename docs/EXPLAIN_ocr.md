# Explain: classical OCR (no machine learning)

Why not Tesseract: since version 4 it recognises text with an LSTM neural network,
which this project excludes. MoleHunt prints copies (PDF, PNG) in one known
monospace font, DejaVu Sans Mono (bundled with matplotlib), so a simple, fully
explainable reader is enough.

1. Binarise: ink = darker than the midpoint of paper (median) and ink (0.5th percentile).
2. Deskew: rotate -3..+3 degrees in 0.25 steps; keep the angle whose row-ink
   profile has the largest variance (level text lines give sharp peaks).
3. Lines = runs of inked rows. Font size = median line pitch / 1.6.
4. Characters: fixed-pitch cells (monospace advance width). Each cell becomes a
   20 x 10 grid of ink fractions and is matched to the 94 printable ASCII glyph
   templates by cosine similarity, trying small vertical shifts; each line's x
   origin is found by testing small offsets. Nothing is trained.

Like any OCR it loses invisible marks, look-alike letters and curly quotes, so
attribution comes from the lexical, spelling, date and number slots.

Worked example: a copy of the zoning master printed as PNG, then rotated, blurred,
noised and JPEG-compressed (simulate_print_scan 0.4), reads back well enough that
the analysis still attributes it to the right copy (tests/test_ocr.py).
