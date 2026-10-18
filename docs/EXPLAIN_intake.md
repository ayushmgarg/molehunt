# Evidence intake

- Intake accepts a source file, case ID, and examiner ID.
- It copies the file to `case/original/` and marks that copy read-only.
- It creates a second file in `case/working/` with write permission for analysis.
- The SHA-256 of the staged original is recorded in the case's JSONL custody log.
- Intake builds the case in a temporary sibling directory, then renames it into place.
- An existing case ID is refused so the command cannot overwrite a previous case.
- Example: identical original and working bytes produce the same SHA-256 at intake.
- Read-only permissions deter ordinary edits; they do not prevent an administrator from changing the file.
