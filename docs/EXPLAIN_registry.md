# SQLite registry

- initialize_database creates the relational schema idempotently and enables foreign-key checks.
- The schema stores masters and slots, synthetic employees, issued copies, evidence, custody mirrors, auxiliary logs, and case progress.
- Registering a master stores its source SHA-256 and keyed slot map in one transaction.
- Each slot stores variants, channel, source index, hashed anchors, and canonical anchor context.
- Issued copies store format, path, timestamp, UUID, and SHA-256 of the actual output file.
- Example: two authored choices produce two rows with the master ID and private slot indices.
- Employee defaults are explicitly synthetic; callers may add synthetic department and role values.
- This schema is the local project store; it does not encrypt the database or authenticate its operator.
