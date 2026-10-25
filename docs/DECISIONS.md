# Implementation decisions

## Core

- Variation bits use left variant = 0 and right variant = 1.
- Slot offsets count Unicode code points. The canonical alignment skeleton selects each left variant.
- Keyed slot order ranks HMAC digests by source index; equal digests break ties by index.
- HMAC inputs are versioned, domain-separated, and length-framed.

## Channel C2

- Trailing-space slots encode one versus two ASCII spaces. This preserves an observable value for both bits; if normalization removes the run, extraction returns an erasure.

## Channel C5

- Number-format pairs must retain the same digits when comma, dot, ordinary space, and NBSP grouping marks are removed. Human review remains required for the intended locale and meaning.

## Channel C6

- Existing visible text is preserved while eligible text runs are split at keyed whitespace boundaries. DOCX validation currently uses python-docx; LibreOffice headless validation remains outstanding because LibreOffice is not installed.

## Channel C7

- The 8x15 grid uses a 7x14 data area and a final row and column for two-dimensional parity. Date is a day count from 2020-01-01; minute is encoded as minute-of-day. The current image reader requires a caller-supplied aligned origin and cell size.

## Log fusion

- Event multipliers are explicit demo factors (`after_hours_download` 3, `print_job` 2, `badge_entry` 1.5, `unknown_ip` 2, `unusual_auth` 2). They are assumptions for the seeded cases, not calibrated probabilities; output lists every applied factor.

## Timeline

- Naive ISO timestamps in synthetic event CSVs are interpreted as UTC. Timezone-aware values are converted to UTC before sorting and display.

## Allocator slots (C1, C2, C3b)

- Masters opt in through YAML front matter `auto_slots: {zw, nbsp, hom}` with explicit counts. Masters without front matter keep the previous slot map, so older issued copies stay decodable.
- C2 auto slots use NBSP vs narrow NBSP instead of NBSP vs space, and C3b uses Cyrillic vs Greek instead of Latin vs look-alike. Normalising attacks then produce erasures rather than forged bit-0 values (rule 13). Authored `{{pun:...}}` and `{{spc:...}}` slots keep their plain variant as bit 0.

## Alignment skeleton

- Both master and suspect are skeletonised (Cf removed, look-alikes folded, word variants mapped to bit 0) before `SequenceMatcher`, as SPEC 5.5 requires. Previously only the master side was canonical, and stripped copies of repetitive text could read a neighbouring paragraph's slot.

## Live LAN demo (rule 7 exception)

- Approved by the project owner on 2026-10-18 for showcasing. `molehunt live` uses the stdlib `ThreadingHTTPServer` (no new dependency), only when started by hand. Every POST needs the host's random 6-digit PIN (constant-time compare); uploads are capped at 2 MB, stored under generated names, limited to .txt/.md/.docx/.png, and go through the normal intake (read-only original, SHA-256, custody entry). No outbound connections and no scanning.

## Weak-spot fixes after the benchmark

- Forged channels: a genuine copy's bits are keyed random (about half 0). If a channel's reads are almost all one value (two-sided binomial p < 1e-6, at least 12 reads), the channel was normalised (A4/A6) and its reads become erasures. This turns dictionary-canonicalisation false accusations into "no attribution".
- Shuffled paragraphs (A9): suspect paragraphs are put back in master order by word-set overlap (Jaccard) before alignment; windows map back to original offsets.
- Full-variant flipping (A10 at strength 1) is left as measured: an attacker who can flip every pair already holds the dictionary, and the copy then reads as noise.
- Fusion weights stay documented assumptions (no labelled real incidents exist to measure them). `analyze --logs` now prints a sensitivity line: the top candidate when every event factor f becomes f^0.5 and f^2. If the top changes, the output says the conclusion depends on the assumed weights.

## Revamp (forensic extras and LAN games)

- Canary facts use a sentinel (`§i§`) in the master rather than a new template node,
  so the slot allocator and aligner are unchanged. Match/mismatch probabilities 0.95/0.05
  are stated assumptions, not measured.
- Scrub verdict counts independent layers hit (>= 3 = deliberate) instead of a
  weighted score: simplest rule that is easy to defend.
- Lineage reuses the ordinary codeword at depth 0, so existing copies and the
  benchmark are unaffected. Layer split 50/25/25, max three hops.
- Forwarding assumes the copy is re-stamped by the system (gateway model). A copy
  forwarded outside the system keeps its parent's fingerprint only.
- The heatmap re-runs alignment on the masked leak to get window positions for
  erased slots; it costs one extra alignment per leak.
- Web assets (Creepster, Special Elite from Google Fonts; Lucide icons) are downloaded
  once into `molehunt/web/static` with their licences and served by the LAN server, so
  the games need no internet at run time.
- The LAN server turns off `allow_reuse_address` on Windows: otherwise a second
  `molehunt live` silently shares the port and players reach the wrong server.
- Find the Mole and the escape room use a seeded RNG whose seed is printed at start, so
  any round can be replayed; answers come only from generated evidence.
- Pages update by polling a version number every 2 s and reloading: no WebSocket, no JS
  framework, easy to explain.
- The old `/` join page of `molehunt live` moved to `/lab`; `/` is now the hub.
