# Tool validation note (P5.4)

Purpose: show that MoleHunt's hashes and byte views agree with independent,
standard tools, so an examiner can trust the numbers in the report.

Run on 2026-10-18, Windows 11, Git Bash tools, MoleHunt at this commit.
Evidence: a synthetic copy issued for E007 from `data/masters/m1_roadmap.md`
(`molehunt issue E007 --master M1 -o E007.txt`, and the same as `.docx`).

## SHA-256

| Source | E007.txt |
|---|---|
| `molehunt intake` (custody log, report) | `17bfc970b379b8bbf5f7efa7845ee2a41983d176c0603c501aa33f350135f2a6` |
| `sha256sum E007.txt` (GNU coreutils) | `17bfc970b379b8bbf5f7efa7845ee2a41983d176c0603c501aa33f350135f2a6` |
| `certutil -hashfile E007.txt SHA256` (Windows) | `17bfc970b379b8bbf5f7efa7845ee2a41983d176c0603c501aa33f350135f2a6` |
| SQLite `copies.sha256` (issuance registry) | `17bfc970b379b8bbf5f7efa7845ee2a41983d176c0603c501aa33f350135f2a6` |

The DOCX copy matched the same way (`8a7d1d78...0094` in registry and `sha256sum`).

## Hex view

`xxd -l 48 E007.txt` and the workbench hex rows (`ui/forensics.format_hex_rows`)
show the same bytes and ASCII column:

```text
xxd       00000000: 2320 5a65 7068 7972 204c 6162 733a 2051  # Zephyr Labs: Q
molehunt  00000000: 23 20 5A 65 70 68 79 72 20 4C 61 62 73 3A 20 51  # Zephyr Labs: Q
```

## Hidden characters

`xxd -p E007.txt | grep -o "e2808b\|e2808c" | wc -l` counts 70 zero-width
sequences (UTF-8 `E2 80 8B` = U+200B, `E2 80 8C` = U+200C). The master declares
`zw: 70`, and the revealer lists the same 70 marks with their bit meaning.

## OOXML package

`unzip -l E007.docx` lists the same parts as the OOXML explorer, including
`docProps/custom.xml` and `word/settings.xml` (where the keyed rsidRoot sits).
exiftool was not installed on the test machine; the core/app properties were
cross-checked by reading the XML parts directly.

## Determinism check (plan, Section 13)

Issuing the same employee twice gives byte-identical TXT, DOCX, and PDF copies
(ZIP entry times are fixed and the PDF is written in reportlab invariant mode);
tests `test_rendered_docx_package_is_byte_deterministic` and
`test_pdf_copy_carries_text_and_keyed_dot_metadata` enforce this.

## How to repeat

```bash
uv run molehunt init
uv run molehunt register data/masters/m1_roadmap.md --master-id M1
uv run molehunt issue E007 --master M1 -o E007.txt
uv run molehunt intake E007.txt C-VAL --actor EX-01
sha256sum E007.txt
xxd -l 48 E007.txt
```
