# Explain: Lab panels (Evidence tools sub-tabs)

Evidence tools is split into sub-tabs: Bytes and invisibles, Diff vs master,
Timeline, OOXML explorer, Image dots, Tardos scorer, Notes and findings. In
Casebook mode each sub-tab unlocks with its tool (ooxml at Case 4, image_dots at
Case 3, tardos at Case 6, notes from Case 1).

- Revealer: every hidden character gets its meaning (U+200B = C1 bit 0,
  U+200C = bit 1, U+200D / U+2060 = decoy, NBSP / NNBSP = C2 bits) and the
  C1 bit string is shown in reading order with decoys skipped.
- OOXML explorer: parts, core/app/custom properties, rsidRoot, rsid use on
  content, tracked changes, and pretty XML of any part.
- Image dots: runs the dot locator on the worker thread and shows the decoded
  printer/date/minute, angle, origin, parity status, and the thresholded mask
  with the grid box.
- Tardos scorer: scores, simulated threshold, and a slider. Moving Z shows
  1 - (1 - P(null > Z))^N, the estimated chance an innocent is accused.
- Notes: tag the current file, byte offset, and last pinned event; save as
  Markdown; "Report with notes" adds them to the report.

Worked example: Case 6 with Z = 40 accuses one colluder; sliding Z to 36.5 names
both while the innocent-accusation estimate rises - the trade-off the case teaches.
