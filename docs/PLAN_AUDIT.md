# Plan audit (Section 12 checklist vs repository)

Baseline audited: commit `fce4b9b` (233 tests passing, ruff clean, Python 3.11).
Status key: **Done** = exit test met; **Partial** = code exists but plan item incomplete;
**Missing** = not in repo; **Changed** = deliberately replaced by a logged decision.

## P0 Setup

| ID | Item | Baseline | Evidence / gap |
|---|---|---|---|
| P0.1 | Python 3.11, git, venv | Done | `requires-python = ">=3.11,<3.12"`, `uv.lock` |
| P0.2 | AGENTS.md, SPEC.md | Done | both in root |
| P0.3 | pyproject + Makefile test/bench/serve/lint | Partial | `make bench` fails: `bench` needs `--master/--employees`, no defaults |
| P0.4 | 3 masters 600–900 words; 7 by P7 | Missing | only `data/demo/master.md`: 64 identical lines, one `lex` pair |
| P0.5 | Roster generator, log generator stub | Missing | static 10-row CSV; no generator |

## P1 Core

| ID | Item | Baseline | Evidence / gap |
|---|---|---|---|
| P1.1 | keys.py HMAC PRF, key file | Done | `core/keys.py`, tests |
| P1.2 | template.py parse, validate, errors | Done | `core/template.py` (equivalence list check is review-only via `suggest-slots`) |
| P1.3 | slots.py keyed shuffle, capacity, 250+ slots | Partial | allocator OK; no master reaches 250 slots; C1/C3b never inserted by allocator |
| P1.4 | codes.py determinism, uniqueness, min Hamming | Done | min distance 102 for 50×256 in `EXPLAIN_codes.md` |
| P1.5 | tardos.py bias, codewords, scoring | Done | `core/tardos.py` |
| P1.6 | EXPLAIN_core.md | Done | |

## P2 Channels

| ID | Item | Baseline | Evidence / gap |
|---|---|---|---|
| P2.1–P2.6 | C1, C2, C3, C3b, C4, C5 embed/extract | Partial | modules + round-trip tests exist, but only authored template slots reach issued copies; C1/C3b/NBSP are not in `issue`/`analyze`/`bench` |
| P2.7 | C6 DOCX rsid/custom property | Done | `channels/docx_meta.py`; LibreOffice check outstanding (logged) |
| P2.8 | C7 dots decode from rotated noisy PNG | Partial | encode/parity/decode OK; reader needs exact origin, no rotation search, no single-bit repair |
| P2.9 | render txt, docx, pdf | Partial | no PDF copy, no C7 page image |

## P3 Detector

| ID | Item | Baseline | Evidence / gap |
|---|---|---|---|
| P3.1 | ingest txt/docx/png | Done | `detect/ingest.py` |
| P3.2 | align skeleton + SequenceMatcher | Done | `detect/align.py` |
| P3.3 | extract 0/1/erasure | Done | `detect/extract.py` |
| P3.4 | z, binomial p, LR, ranking, **decision rule** | Partial | no decision rule, no "cannot distinguish" separability test, no ENFSI verbal scale anywhere |
| P3.5 | Tardos scoring + **threshold by simulation** | Partial | scoring only; no calibration, no `--collusion` |
| P3.6 | fuse.py priors, posterior, rationale | Done | `detect/fuse.py` |
| P3.7 | CLI analyze ranked table + **verbal statement** | Partial | table only |

## P4 Attacks and benchmark

| ID | Item | Baseline | Evidence / gap |
|---|---|---|---|
| P4.1 | A1–A12 with strength + seed | Partial | A1–A10 text, A11 image-only, A12 bits-only; harness accepts A1–A10 only |
| P4.2 | harness + `make bench` CSVs | Partial | single master, no chains, no false-accusation column, `make bench` broken |
| P4.3 | plots: survival, accuracy, ROC, collusion | Partial | survival + accuracy only |
| P4.4 | targets checked, failures documented | Missing | no targets file, no archived results |
| P4.5 | fix weakest channel, rerun | Missing | depends on P4.4 |

## P5 Custody and report

| ID | Item | Baseline | Evidence / gap |
|---|---|---|---|
| P5.1 | intake read-only original, working copy, custody | Done | `intake.py`, `intake_service.py` |
| P5.2 | verify + tamper demo script | Partial | verify done; no tamper demo |
| P5.3 | report DOCX/PDF, all Section 8 parts | Partial | no verbal statement, tool version, benchmark reference, slot-matrix appendix; no `molehunt report --case` |
| P5.4 | tool validation note (sha256sum, xxd) | Missing | |

## P6 Workbench (Changed: PySide6 desktop replaces FastAPI, see `STACK_DECISION.md`)

| ID | Item | Baseline | Evidence / gap |
|---|---|---|---|
| P6.1 | app, evidence tree | Done | `ui/forensics_actions.py` |
| P6.2 | hex viewer + code-point popover | Done | `ui/forensics.py` |
| P6.3 | invisible-char revealer + bit decoder | Partial | lists characters; no bit mapping |
| P6.4 | diff vs master; slot matrix | Done | `ui/diff_actions.py`, analysis matrix |
| P6.5 | OOXML explorer + rsid table | Missing | tool name exists in locks, no panel |
| P6.6 | timeline; notes and findings; report button | Partial | timeline + report done; no notes/findings |
| P6.7 | image dot analyzer | Missing | |

## P7 Casebook

| ID | Item | Baseline | Evidence / gap |
|---|---|---|---|
| P7.1 | yaml schema, generator, ground_truth, **validator**, scoring | Partial | answer check lives in UI code; scoring is Brier-only, not the Section 10 table |
| P7.2–P7.8 | Cases 1–7 | Partial | all 7 generate, but scenarios are thinner than Section 9 (no tie in Case 5, no decoy metadata in Case 4, clean unrotated scan in Case 3, two-row logs in Case 7, A3-only edit in Case 2); no automated solve tests |
| P7.9 | progress, hints, calibration, **leaderboard** | Partial | no leaderboard |

## P8 Red Team

| ID | Item | Baseline | Evidence / gap |
|---|---|---|---|
| P8.1 | attack toolkit UI with utility meter | Missing | "Red Team bench" tab is the benchmark runner |
| P8.2 | live verdict, score, leaderboard | Missing | |

## P9 Polish (user-owned items marked)

| ID | Item | Baseline | Evidence / gap |
|---|---|---|---|
| P9.1 | README install/run/demo | Partial | no demo script steps for the 6-minute demo |
| P9.2 | EXPLAIN docs for every module | Partial | several UI and game modules lack one |
| P9.3 | final benchmark archived | Missing | |
| P9.4–P9.6 | report, PPT, rehearsal, viva | User | not code |
| P9.7 | fresh-clone test | User | |

## Rule checks

- Rule 9 (modules under 300 lines): `cli.py` is 442 lines.
- Rule 4 (no robustness claims): no violations found in code, comments, or README.
- Rule 6 (no hard-coded answers): detector does not import `game/`; answers come from `ground_truth.json`.
