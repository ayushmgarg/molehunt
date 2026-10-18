# Explain: slot alignment

Alignment renders a canonical master using each slot's left variant.
`difflib.SequenceMatcher` finds exact character blocks in the suspect text.
The nearest matching boundaries around each source slot define a candidate window.

Short or truncated evidence can leave one boundary missing; the text edge is used.
If boundaries cross, the slot is erased. Major rewrites may make a window broad or
ambiguous; extraction handles that as missing evidence rather than a forced guess.

Worked example: the canonical `A begin. Then B` and suspect `A start. Then B`
share text before and after the slot. The window contains only `start`.
