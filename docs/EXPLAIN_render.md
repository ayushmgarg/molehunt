# Explain: rendering

The renderer receives a parsed template, its keyed slot map, and an employee codeword.
`bits_in_source_order` maps private code positions back to authored positions.
The template then chooses the left or right variant for each slot.

Text exports are UTF-8. DOCX exports create one paragraph per source line, then apply
the keyed OOXML metadata channel. This first renderer keeps text and slot selection
simple; richer Markdown formatting and PDF output are separate future work.

Worked example: codeword `[0, 1]` with source slots indexed `[1, 0]` maps to source
bits `[1, 0]`, so the first choice uses its right variant and the second its left.
