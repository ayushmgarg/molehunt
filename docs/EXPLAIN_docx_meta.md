# Explain: DOCX metadata channel

C6 derives an eight-hex-digit RSID from the secret key and synthetic employee ID.
It writes the ID into document settings and paragraph metadata; each run receives a
separately keyed RSID. Text runs with spaces split at a deterministic keyed boundary.

The package also receives one `MoleHuntTag` custom property. ZIP entries and visible
paragraph text are preserved. The module updates custom-property relationships and
content types when adding the part, and replaces the tag rather than duplicating it.

Worked check: embed tag `E001`, reopen the DOCX with python-docx, and compare the
paragraph text. XML checks confirm the settings RSID, per-run IDs, and custom tag.
LibreOffice is not installed on this machine, so its headless-open check remains open.
