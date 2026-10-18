# Explain: variant extraction

Extraction receives slot windows from alignment and compares only the candidate text.
An exact left variant means bit 0; an exact right variant means bit 1.
For word channels it also checks whole-token boundaries.

Missing, altered, ambiguous, and truncated values become `None` (an erasure).
The scorer skips those entries, because unreadable slots carry no match evidence.

Worked example: candidate window `start` against variants `begin` / `start`
returns bit 1. Window `commenced` matches neither and returns an erasure.
