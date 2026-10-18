# Master comparison view

- The master parser renders every authored variation as variant A to create the comparison baseline.
- `SequenceMatcher` aligns baseline and evidence lines with automatic junk filtering disabled.
- Each aligned line is labelled equal, replace, insert, or delete.
- The view separately lists every variation point with its channel and A/B wording.
- This preserves the alternatives even when the leaked copy uses variant B.
- Example: master `begin|start` displays `begin` in the baseline and lists both choices beside the diff.
- Supported decoded evidence uses the same ingestion path as analysis; PNG evidence has no text diff yet.
