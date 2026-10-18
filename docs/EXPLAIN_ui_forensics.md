# Byte and Unicode inspection

- Hex rows group raw bytes by a fixed width; offsets count bytes from the evidence start.
- Printable ASCII bytes (0x20–0x7E) appear as characters; all other byte values appear as dots.
- UTF-8 stores one Unicode scalar in one to four bytes.
- A selected continuation byte maps back to the lead byte's decoded scalar.
- Invalid UTF-8 is displayed as a raw byte and is not assigned a guessed character.
- For example, `C3 A9` decodes to `é` (U+00E9); selecting byte offset 1 still identifies U+00E9.
- Unicode visibility uses Python's `str.isprintable()` classification.
- Each hidden or non-printing scalar includes its character offset, Unicode name, category, and UTF-8 bytes.
- For example, U+200B is ZERO WIDTH SPACE and encodes as `E2 80 8B`.
