# Implementation decisions

## Core

- Variation bits use left variant = 0 and right variant = 1.
- Slot offsets count Unicode code points. The canonical alignment skeleton selects each left variant.
- Keyed slot order ranks HMAC digests by source index; equal digests break ties by index.
- HMAC inputs are versioned, domain-separated, and length-framed.

## Channel C2

- Trailing-space slots encode one versus two ASCII spaces. This preserves an observable value for both bits; if normalization removes the run, extraction returns an erasure.

## Channel C5

- Number-format pairs must retain the same digits when comma, dot, ordinary space, and NBSP grouping marks are removed. Human review remains required for the intended locale and meaning.

## Channel C6

- Existing visible text is preserved while eligible text runs are split at keyed whitespace boundaries. DOCX validation currently uses python-docx; LibreOffice headless validation remains outstanding because LibreOffice is not installed.
