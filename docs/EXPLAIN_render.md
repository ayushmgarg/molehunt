# Explain: rendering issued copies

Text: every slot shows the variant chosen by the employee's codeword bit (bit 0 =
left variant, bit 1 = right), mapped from keyed codeword order back to reading order.

DOCX: the text as paragraphs, then C6 metadata (keyed rsidRoot and run rsids,
run splits, a custom property) is patched into the OOXML package.

PDF: the text typeset with reportlab, plus faint yellow C7 dot grids tiled in the
top and bottom margins of every page. Payload = (station id, issue date, issue
minute) where station id = first byte of HMAC(K, "pdf-dots", employee). A photo or
photocopy of any part of a margin carries a full parity-checked grid.

Worked example: E001 issued 2025-03-04 13:45 UTC -> grid encodes station
HMAC-byte, day 1889 since 2020-01-01, minute 825.
