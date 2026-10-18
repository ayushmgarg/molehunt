# Explain: slots

An authored choice is a potential fingerprint slot with two candidate variants.
The allocator builds a canonical text by choosing the left variant at every slot.
It records each slot's code-point offset and nearby before/after anchor text.

HMAC-based `keyed_order` assigns each source slot a private codeword index.
`source_index` preserves the slot's position in the master template.
`bits_in_source_order` maps issued bits back to render order.
The capacity report counts slots by channel without claiming survival.

Worked example: three source slots receive keyed indices `[2, 0, 1]`.
Given codeword `[1, 0, 1]`, source-order bits become `[1, 1, 0]`.
The renderer then selects variants 1, 1, and 0 at those source positions.

Offsets and anchors are measured in Python Unicode code points, not UTF-8 bytes.
