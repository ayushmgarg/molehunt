# Explain: zero-width channel

C1 stores zero as U+200B and one as U+200C after an aligned text position.
U+200D and U+2060 are recognized decoys and do not encode bits.
Embedding returns offsets for each inserted slot marker in the resulting text.

Extraction uses aligned marker offsets. If the expected marker is absent, it returns
`None`; later scoring treats that slot as an erasure. Decoys immediately before a
marker are skipped. Text offsets count Unicode code points.

Worked example: inserting bit 1 after `A` in `ABC` yields `A<U+200C>BC`.
Extraction at the returned marker offset yields 1. If both data marks are stripped,
each expected offset yields `None` and no marker is counted as a mismatch.
