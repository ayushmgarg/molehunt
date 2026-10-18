# Shared issuance API

- Registration validates the 32-byte key, parses the template, allocates keyed slots, and stores its digest.
- Issuance looks up a master by registered ID or exact resolved path.
- It rechecks the master SHA-256 before deriving the employee codeword.
- Text, Markdown, and DOCX copies use the same renderer as the application.
- A successful copy gets a synthetic employee row and a UUID registry record with output hash.
- Existing output files are refused to avoid silently replacing an issued copy.
- Example: register `M1`, then issue `E001` from `M1` to `E001.txt`.
