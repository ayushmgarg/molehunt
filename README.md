# MoleHunt

Forensic document attribution suite with an investigation casebook. A company
issues each employee a uniquely fingerprinted copy of a confidential document.
When a copy leaks (edited, normalised, partial, printed, or merged from several
copies), MoleHunt recovers the fingerprint, ranks the issued copies with a
likelihood ratio, fuses that with access/print/auth logs, and writes an
examiner-style report.

Offline, synthetic data only, no machine learning. It ranks **copies**, not
people: a match says which issued copy a leak derives from, never who sent it.

Three modes on one engine:

| Mode | What you do |
|---|---|
| Lab | register a master, issue copies, intake evidence, analyse, report |
| Casebook | solve 7 seeded investigations; tools unlock as you progress |
| Red Team | scrub your own copy under a 70% utility floor and try to evade the detector |

## Install

Needs [uv](https://docs.astral.sh/uv/). The project pins Python 3.11.

```bash
uv python install 3.11
uv sync --python 3.11
uv run pytest -q
```

## Quick start (Lab mode, CLI)

```bash
uv run molehunt init
uv run molehunt roster --count 50 -o data/demo/roster50.csv
uv run molehunt register data/masters/m1_roadmap.md --master-id M1
uv run molehunt issue --master M1 --employees data/demo/roster50.csv --format txt,docx,pdf,png
uv run molehunt attack --name A5 --strength 1 data/demo/issued/E007.txt -o reports/generated/leak.txt
uv run molehunt intake reports/generated/leak.txt C-001 --actor EX-01
uv run molehunt analyze reports/generated/leak.txt --master data/masters/m1_roadmap.md --employees data/demo/roster50.csv
uv run molehunt report --case C-001 -o reports/generated/C-001.docx --master data/masters/m1_roadmap.md --employees data/demo/roster50.csv --examiner EX-01
uv run molehunt custody demo
```

Evidence can be .txt, .md, .docx, or a .png/.jpg scan of a printed copy (read
with a classical, non-ML template OCR; see `docs/EXPLAIN_ocr.md`).

`analyze` prints the ranking (matches, z, binomial p, log10 LR) and a finding:
`attribute` (with the ENFSI-style verbal scale), `cannot distinguish`, or
`no attribution`. `custody demo` builds an 8-entry hash chain, flips one byte,
and shows `BROKEN at seq 7`.

Other commands: `suggest-slots`, `issue --code tardos` + `analyze --collusion`
(collusion tracing), `analyze --logs access.csv` (log fusion), `custody add |
verify | show | intake`, `redteam --tools strip,collapse,truncate:0.8`,
`bench`. Run `uv run molehunt --help` for all options.

## Workbench (desktop UI)

```bash
uv run molehunt serve
```

Tabs: Evidence analysis (ranking, slot matrix, report), Issue copy, Intake and
custody, Red Team bench (benchmark runner + Red Team boss with utility meter
and leaderboard), Casebook (seeded cases, hints, Section 10 grading), Evidence
tools (bytes and invisible characters, diff vs master, timeline, OOXML
explorer, image dot analyser, Tardos scorer with threshold slider, notes).
Tick "Casebook mode" to lock tools until each case earns them.

## Live demo across laptops (same Wi-Fi)

```bash
uv run molehunt live
```

The host prints a URL and a 6-digit PIN. On another laptop or phone, open the URL,
pick an employee, and download a fingerprinted copy (txt, docx, or pdf). Edit or
scrub it (or print the PDF and photograph it), then upload it on the same page.
The host's `/board` page (put it on the projector) refreshes every 3 seconds with
the hash, custody entry, ranking, and finding for each leak. Allow Python through
the Windows firewall when asked. This is the only network feature; it is opt-in.
Step-by-step test: `docs/LIVE_DEMO.md`.

## Benchmark

```bash
uv run molehunt bench            # same as: make bench
```

Runs the Section 6 protocol: 3 masters x 50 employees x 20 leakers x 12 attacks
(A1-A11, A2b) x 3 strengths x 10 seeds, plus chains and Tardos collusion trials,
in parallel workers (about 20 minutes on 8 cores). Writes `bench/results/*.csv`,
`summary.json`, `targets.csv`, and plots. The archived run and its numbers are in
[docs/BENCHMARK.md](docs/BENCHMARK.md); every claim about attack survival comes
from there, not from the code.

## Six-minute demo

| Time | Action |
|---|---|
| 0:00 | Pitch: three modes, one engine; copies not people |
| 0:30 | `register` + batch `issue`; Evidence tools > Diff vs master on one copy |
| 1:30 | `attack` (A5 + truncate) then `analyze` and `report --case`; show LR and verbal scale |
| 2:30 | `custody verify` passes; `custody demo` shows `BROKEN at seq 7` |
| 3:30 | Casebook Case 1: hex view, invisible revealer bit string, submit, score |
| 4:30 | `docs/benchmark/plots/survival.png` and `targets.csv`; state the weak spots |
| 5:15 | Red Team boss: 30-second attempt to beat the detector |
| 5:45 | Limits: copy vs person, heavy paraphrase, very short leaks |

## Layout

```text
molehunt/core      keys, template, slots, autoslots (C1/C2/C3b), codes, tardos, render
molehunt/channels  zerowidth, whitespace, punct, homoglyph, lexical, spelling, docx_meta, printdots, dot_locate
molehunt/detect    ingest, align, extract, score, decide, tardos, fuse, logs
molehunt/attacks   transform (A1-A11), collusion (A12), harness, bench_artifacts, collusion_bench
molehunt/game      casebook, generator, case_evidence, tools, validator, leaderboard, redteam, cases/*.yaml
molehunt/ui        PySide6 workbench
data/masters       three benchmark masters (650-815 words, 262-267 slots) + cases/ four case masters
docs               SPEC overrides, DECISIONS, EXPLAIN_<module> viva notes, VALIDATION, BENCHMARK, PLAN_AUDIT
```

## Rules

Python 3.11, deterministic (HMAC-SHA256 or seeded RNGs), statistics only, no
network features, synthetic people and documents only. See `AGENTS.md`,
`SPEC.md`, and `docs/DECISIONS.md`.
