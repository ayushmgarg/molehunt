# Explain: analysis CLI

`init` creates the local 32-byte key file without printing its contents.
`analyze` reads a master template, CSV roster IDs, and evidence; then calls the same
parse, slot, align, extract, and score functions used by the library.

The printed ranking is not a final accusation. Its threshold stays unset until the
benchmark measures an error rate. PNG input currently reports C7 metadata only; OCR is
not implemented.

Worked run: initialize once, then pass the leak path, `--master`, and `--employees`.
The report begins with the raw evidence SHA-256 for traceability.
