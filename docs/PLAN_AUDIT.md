# Plan audit (Section 12 checklist vs repository)

Baseline audited: commit `fce4b9b` (233 tests). This pass ends at the commit
that adds this file's final version. Status key: **Done** = exit test met and
covered by tests; **Partial** = works with a stated gap; **User** = a human
deliverable (report, slides, rehearsal); **Changed** = replaced by a logged decision.

## P0 Setup

| ID | Item | Before | Now | Evidence |
|---|---|---|---|---|
| P0.1 | Python 3.11, venv | Done | Done | `requires-python`, `uv.lock` |
| P0.2 | AGENTS.md, SPEC.md | Done | Done | |
| P0.3 | Makefile test/bench/serve/lint | Partial (`make bench` broke) | Done | `bench` runs the protocol with no arguments |
| P0.4 | 3 masters 600-900 words; 7 by P7 | Missing | Done | `data/masters/m1..m3` (647-814 words, 262-267 slots) + `data/masters/cases/m4..m7`; every case uses a story master |
| P0.5 | Roster + log generator | Missing | Done | `game/logs_gen.py`, `molehunt roster` |

## P1 Core

| ID | Item | Before | Now | Evidence |
|---|---|---|---|---|
| P1.1-P1.2, P1.4-P1.6 | keys, template, codes, tardos, EXPLAIN | Done | Done | |
| P1.3 | allocator, keyed shuffle, 250+ slots | Partial | Done | `core/autoslots.py` inserts keyed C1/C2/C3b slots; each master >= 250 slots |

## P2 Channels

| ID | Item | Before | Now | Evidence |
|---|---|---|---|---|
| P2.1-P2.6 | C1, C2, C3, C3b, C4, C5 in issued copies | Partial | Done | all channels reach `issue`, `analyze`, `bench`; survival measured per channel |
| P2.7 | C6 DOCX | Done | Done | ZIP times fixed, byte-deterministic; LibreOffice check still outstanding (not installed) |
| P2.8 | C7 decode from rotated noisy photo | Partial | Done | `channels/dot_locate.py`: angle search, parity, single-bit repair, voting |
| P2.9 | txt, docx, pdf copies | Partial | Done | `render_pdf` tiles yellow C7 grids; `issue -o x.pdf` |

## P3 Detector

| ID | Item | Before | Now | Evidence |
|---|---|---|---|---|
| P3.1-P3.3 | ingest (incl. PNG/JPG via classical OCR), align, extract | Done | Done | align now skeletonises both sides, uses token anchors and an anchor-context check (no anchor = erasure) |
| P3.4 | decision rule, cannot distinguish, verbal scale | Partial | Done | `detect/decide.py` (Bonferroni alpha/N + LR margin, ENFSI scale) |
| P3.5 | Tardos threshold by simulation | Partial | Done | `calibrate_threshold`, `analyze --collusion` |
| P3.6 | fusion | Done | Done | |
| P3.7 | CLI verbal statement | Partial | Done | `Finding (attribute): ... extremely strong support ...` |

## P4 Attacks and benchmark

| ID | Item | Before | Now | Evidence |
|---|---|---|---|---|
| P4.1 | A1-A12 | Partial | Done | A11 OCR model on text + image print-scan; A12 in collusion bench; A10 now flips slots as specified |
| P4.2 | harness + `make bench` | Partial | Done | full protocol, 24,600+ runs, parallel |
| P4.3 | plots incl. ROC, collusion | Partial | Done | `bench/plots/*.png` |
| P4.4 | targets checked | Missing | Done | `targets.csv`; see `docs/BENCHMARK.md` |
| P4.5 | fix weakest part, rerun | Missing | Done | fixes driven by results: paragraph-preserving A3, correct-read survival, anchor check; rerun archived |

## P5 Custody and report

| ID | Item | Before | Now | Evidence |
|---|---|---|---|---|
| P5.1 | intake | Done | Done | also `custody intake` |
| P5.2 | verify + tamper demo | Partial | Done | `custody demo` -> `BROKEN at seq 7` |
| P5.3 | report with all Section 8 parts | Partial | Done | `report.py` sections, `report --case` |
| P5.4 | tool validation note | Missing | Done | `docs/VALIDATION.md` (sha256sum, certutil, xxd, unzip) |

## P6 Workbench (Changed: PySide6 desktop, `STACK_DECISION.md`)

| ID | Item | Before | Now | Evidence |
|---|---|---|---|---|
| P6.1, P6.2, P6.4 | evidence tree, hex, diff, slot matrix | Done | Done | |
| P6.3 | revealer + bit decoder | Partial | Done | bit meaning column and C1 bit string |
| P6.5 | OOXML explorer + rsid table | Missing | Done | `ui/ooxml_view.py`, Lab panel |
| P6.6 | timeline (filter, brush, pin), notes, report button | Partial | Done | brush selects a time window; notes panel, "Report with notes" |
| P6.7 | image dot analyzer | Missing | Done | Lab panel with mask preview |

## P7 Casebook

| ID | Item | Before | Now | Evidence |
|---|---|---|---|---|
| P7.1 | schema, generator, truth, validator, scoring | Partial | Done | `game/validator.py` Section 10 points |
| P7.2-P7.8 | Cases 1-7 playable | Partial | Done (automated) | `tests/test_case_solutions.py` solves all 7 from public files with >= 90 points; "solved by a friend" (P7.2) is a User check |
| P7.9 | progress, hints, calibration, leaderboard | Partial | Done | `game/leaderboard.py`, 3-wrong close, advance at 60 |

## P8 Red Team

| ID | Item | Before | Now | Evidence |
|---|---|---|---|---|
| P8.1 | toolkit with utility meter | Missing | Done | `game/redteam.py`, Red Team panel, `molehunt redteam` |
| P8.2 | live verdict, score, leaderboard | Missing | Done | same |

## P9 Polish

| ID | Item | Before | Now | Evidence |
|---|---|---|---|---|
| P9.1 | README install/run/demo | Partial | Done | quick start verified end-to-end |
| P9.2 | EXPLAIN per module | Partial | Done | `docs/EXPLAIN_INDEX.md` |
| P9.3 | final benchmark archived | Missing | Done | `docs/benchmark/`, `docs/BENCHMARK.md` |
| P9.4-P9.6 | report, PPT, rehearsal, viva | User | User | |
| P9.7 | fresh-clone test | User | User | |

## Rule checks

- Rule 9: every module is under 300 lines (`cli.py` was 442; now split).
- Rule 4: robustness numbers appear only in `docs/BENCHMARK.md`, copied from `bench/results`.
- Rule 6: the detector never imports `game/`; validator reads only `ground_truth.json`.
- Rule 7: one approved exception, the opt-in `molehunt live` LAN demo (logged in DECISIONS.md).
- No ML anywhere: statistics, HMAC, template matching. OCR is template matching, not Tesseract (an LSTM network).
