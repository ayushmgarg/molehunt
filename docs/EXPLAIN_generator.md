# Seeded case evidence

- Each case combines the player's seed with a fixed case offset: `effective_seed = seed + seed_offset`.
- A seeded Python RNG selects synthetic employee IDs and scenario values reproducibly.
- Public evidence and auxiliary CSV files are written under `public/`; expected answers stay in `private/ground_truth.json`.
- Case 3's print mark and timeline share one generated date, minute, printer ID, and synthetic employee ID.
- The timeline writes badge entry 45 minutes before print, document open 18 minutes before, print, then badge exit 12 minutes after.
- Timestamps use UTC ISO format so timeline ordering is independent of the computer's local timezone.
- Example: a print at 10:00 UTC produces related events at 09:15, 09:42, 10:00, and 10:12 UTC.
