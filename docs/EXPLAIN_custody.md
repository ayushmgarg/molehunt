# Custody hash chain

- Each JSONL event stores a sequence, UTC time, actor, action, evidence SHA-256, details, previous hash, and its own hash.
- The event payload is encoded as UTF-8 canonical JSON: sorted keys and compact separators.
- `entry_hash = SHA256(previous_hash_hex || canonical_json(payload))`.
- The first previous hash is 64 zeroes; every later entry links to the prior entry hash.
- Verification recomputes each event in order and reports the first invalid sequence.
- Example: editing the action in entry 1 changes its digest, so verification reports `BROKEN at seq 1`.
- Appending first verifies the existing chain and refuses to extend a broken log.
- The chain detects accidental or partial edits; a holder who can rewrite the entire file can rebuild it.
- External signatures or protected storage are needed to establish who created the log and prevent full replacement.
