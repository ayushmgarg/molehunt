# Explain: evidence ingestion

Ingestion reads raw bytes once and records size plus SHA-256 before decoding.
UTF-8 text keeps its original code points, including invisible characters.
DOCX paragraphs and table cells become a plain text stream for analysis.
PNG evidence keeps its dimensions and can optionally decode an aligned C7 grid.

The source path is read only. Unsupported formats and malformed input raise a clear
error instead of silently replacing characters or guessing an encoding.

Worked check: the SHA-256 is computed from the exact bytes on disk; a visible text
stream may lose formatting, but the hash still identifies the original artifact.
