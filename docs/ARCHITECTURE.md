# MoleHunt codebase map

Read this first. It says what every folder and file does, how a copy is made,
how a leak is examined, and where each game lives. Each module also has a short
viva note in `docs/EXPLAIN_<module>.md` (index: `EXPLAIN_INDEX.md`).

## 1. The big picture

```text
master.md --prepare--> template + keyed slots --render(codeword, facts)--> copy per holder
                                                                              |
                                                       leaked, edited, scrubbed, forwarded
                                                                              v
leak --intake (hash, custody)--> align --> extract bits --> score every holder (LR)
     --> decide (Bonferroni + margin) --> canaries, scrub check, heatmap, meter, tree
```

Everything random comes from HMAC-SHA256 with the secret key K (or a seeded RNG),
so the same key always gives the same copies and the same answers.

## 2. Folders

| Folder | What lives there |
|---|---|
| `molehunt/core/` | making copies: keys, template, slots, codes, canary facts, forward lineage, rendering |
| `molehunt/channels/` | one file per hiding channel (zero-width, spaces, punctuation, look-alikes, synonyms, spelling, DOCX metadata, printer dots, OCR) |
| `molehunt/detect/` | reading a leak: ingest, align, extract, score, decide, fuse, scrub check, heatmap |
| `molehunt/attacks/` | what a leaker might do (A1-A12) and the benchmark harness |
| `molehunt/game/` | casebook cases, red team, Find the Mole, escape room |
| `molehunt/web/` | the LAN server and every web page (Halloween theme, assets in `static/`) |
| `molehunt/ui/` | PySide6 desktop app (`molehunt serve`) |
| `data/masters/` | synthetic documents; `live/m8_midnight_carnival.md` is the game master |
| `tests/` | pytest suite, one file per module |
| `docs/` | explanations, decisions, benchmark results, plan audit |

## 3. Files you will talk about most

| File | One line |
|---|---|
| `core/keys.py` | `digest(K, domain, parts)` = HMAC-SHA256; `keyed_order` = keyed shuffle |
| `core/template.py` | parses `{{lex:start|begin}}` into choices |
| `core/autoslots.py` | `prepare_master`: front matter, canary sentinels, auto zero-width/NBSP/look-alike slots |
| `core/slots.py` | keyed slot -> codeword position map with anchor text |
| `core/codes.py` | codeword bit i = lowest bit of HMAC(K, "cw", holder, i) |
| `core/canaries.py` | per-copy facts (codename, budget, venue, date) and fact matching |
| `core/lineage.py` | layered codewords for forwarded copies; `ForwardLog` table; text tree |
| `core/render.py` | txt / docx / pdf / png copies (PDF and PNG carry yellow dots) |
| `detect/align.py` | finds each slot in a messy leak (skeleton, token anchors, reorder) |
| `detect/extract.py` | bit or erasure per slot; flattened channels become erasures |
| `detect/score.py` | matches, binomial p, log10 LR per holder |
| `detect/decide.py` | attribute / cannot distinguish / no attribution, verbal scale |
| `detect/scrub.py` | "were hidden layers removed while the words survived?" |
| `detect/heatmap.py` | per-slot colours and the evidence curve |
| `analysis.py` | `analyze_text`: the core attribution pipeline |
| `forensics.py` | `examine`: attribution + canaries + scrub + heatmap + lineage in one call |
| `intake_service.py`, `custody.py` | evidence intake and the hash-chained custody log |
| `live.py` | lab state and `make_server` |
| `game/mole_game.py` | Find the Mole rules and scoring |
| `game/escape_case.py` | builds one team's six locks from the key |
| `game/escape_room.py` | teams, clock, answers, hints, tools |
| `web/server.py` | request parsing and app dispatch |
| `web/findings.py` | the findings block shown everywhere |

## 4. Commands

| Command | Module |
|---|---|
| `init`, `register`, `issue`, `analyze`, `attack`, `roster`, `suggest-slots`, `serve` (desktop app) | `cli_lab.py` |
| `intake`, `custody ...`, `report` | `cli_evidence.py` |
| `bench`, `redteam` | `cli_bench.py` |
| `live`, `examine`, `forward` | `cli_live.py` |

## 5. Web routes (molehunt live)

| Route | Who | What |
|---|---|---|
| `/` | everyone | three doors |
| `/host?k=...` | host | PIN, address, projector links |
| `/game`, `/game/screen` | phones, projector | Find the Mole |
| `/escape`, `/escape/screen` | teams, projector | Escape Room |
| `/lab`, `/board`, `/lab/case/<id>` | everyone, projector | Forensic Lab |
| `/static/<file>` | everyone | fonts and icons (bundled, offline) |

## 6. Where to change things

- New fact family: add it under `canaries:` in the master front matter and use `{{can:name}}`.
- New scrub tool in the game: one line in `TOOLS` in `game/mole_game.py`.
- New escape lock: add a `Lock(...)` in `game/escape_case.py` and, if it needs a tool,
  a function in `game/escape_room.py` plus a branch in `web/escape_app.py::_run_tool`.
- Colours and fonts: `web/theme.py` (CSS variables at the top).
