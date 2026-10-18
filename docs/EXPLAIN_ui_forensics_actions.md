# Evidence inspection panel

- The evidence tree reads registry rows ordered by intake time and identifies both original and working-copy paths.
- Selecting a row fills the working-copy path into the inspection field.
- The panel reads the file without writing to either copy and displays at most 256 bytes per page.
- Every hex row starts with its absolute byte offset and shows byte values plus printable ASCII.
- Clicking one byte maps its offset back through the UTF-8 sequence decoder.
- Example: bytes `C3 A9` encode `é`; clicking either byte reports U+00E9 and both bytes.
- Decoded text is scanned with `str.isprintable()` and lists character offsets, code points, Unicode names, and categories.
- PNG files have raw bytes but no decoded text in the current ingestion pipeline, so their hidden-character table is empty.
