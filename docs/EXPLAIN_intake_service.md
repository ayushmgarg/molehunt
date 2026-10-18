# Registered intake

- The service initializes the SQLite registry and calls the filesystem intake routine.
- Intake creates a read-only original, working copy, and hash-chained JSONL event.
- The service mirrors the evidence identity and exact custody event into SQLite.
- It returns the staged paths and a generated evidence ID to callers.
- Example: `CASE-01` links a source hash to `original/` and `working/` paths.
- The JSONL chain remains the verification source; the database is a searchable registry mirror.
