# Explain: whitespace channel

C2 supports three explicit carriers: one versus two spaces after a period,
ASCII space versus NBSP, and one versus two trailing ASCII spaces.
Slots use original code-point offsets; the embedding result returns adjusted offsets.

Extraction accepts only a valid carrier value. A tab, a collapsed run, or missing
trailing spaces is an erasure. The surrounding aligner must refresh offsets after edits.

Worked example: in `A. B`, bit 1 at the space after the period renders `A.  B`.
The decoder counts exactly two ASCII spaces and returns 1.
Unicode NBSP is tested as U+00A0, distinct from U+0020.
