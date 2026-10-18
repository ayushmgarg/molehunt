# Explain: lexical channel

C4 embeds one of two human-approved word variants at an authored whole-word offset.
The current starter list contains suggestions only; context and meaning need review.
The left word is bit 0 and the right word is bit 1.

The renderer checks word boundaries and applies replacements from right to left.
Extraction checks both the full word and following rendered context, avoiding prefix
matches such as `start` inside `starting`. A missing anchor or rewritten word is erased.

Worked example: replace `begin` with `start` in `Please begin the review.`.
The detector reads `start` only while the following ` the review.` anchor remains.
