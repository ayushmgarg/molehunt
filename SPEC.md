# MoleHunt specification

> Source: Sections 1–8 of `MoleHunt_Project_Plan.docx`. This file is the implementation reference.

> Stack override: `docs/STACK_DECISION.md` selects Python 3.11 + PySide6. UI direction override: `docs/DESIGN.md` specifies the native forensic bench. Other requirements in Sections 1–8 remain in force.


# 1. Project overview

Pitch. A company issues each employee a uniquely fingerprinted copy of a confidential document. When a copy leaks (edited, normalized, partial, printed, or merged from several copies), the tool recovers the fingerprint, ranks suspects with a statistical confidence, fuses the result with access/print/auth logs, and writes a court-style report. A guided casebook teaches the same techniques as seven investigations inside a Mini-Autopsy workbench, and a Red Team mode lets you attack the fingerprint to measure how well it holds.


### Three modes on one engine

| Mode | What it does | User | Nature |
| --- | --- | --- | --- |
| Lab | Register master, issue N fingerprinted copies, analyze a suspect file (txt, docx, png scan), output ranked attribution plus report | Examiner | Real working tool |
| Casebook | 7 seeded cases solved inside the workbench; each unlocks a technique and a tool | Player | Training on the real engine |
| Red Team | You are the mole: scrub a copy under a utility constraint while the detector tries to catch you | Attacker | Benchmark plus game |


### Hard constraints

Python 3.11, fully deterministic, no ML training, no neural libraries. Statistics only (binomial, z-score, likelihood ratio, Tardos scoring).

Synthetic documents and synthetic employees only. No real PII, no malware, no network scanning. It protects documents you own.

Offline, runs on a laptop, one command to start: molehunt serve.

Every claim of robustness must come from measured benchmark output, not from the code or from GPT.


### Syllabus mapping (why this earns the 10 marks)

| Forensics topic | Where it appears |
| --- | --- |
| Evidence acquisition, hashing, working copies | Custody intake; SHA-256 on every evidence file; read-only original |
| Chain of custody | Hash-chained append-only log with custody verify and a tamper demo |
| File and format forensics | UTF-8/Unicode code points, OOXML package structure, PNG dot grid, hex view |
| Metadata forensics | Case 4: core.xml, app.xml, rsid, tracked-change remnants |
| Data hiding and detection | Zero-width, whitespace, homoglyph, lexical, print-dot channels |
| Anti-forensics and counter-measures | Attack catalogue (Section 6) and Red Team mode |
| Log analysis and timelines | Access, print, badge, auth, DHCP logs correlated in Cases 3, 5, 7 |
| Printer and device forensics | Case 3 (machine identification dots) |
| Reporting, admissibility, error rates | Likelihood-ratio report, verbal scale, benchmark error rates (Daubert-style) |
| Tool validation | Cross-check hex view and hashes against xxd, sha256sum, exiftool; benchmark as validation evidence |


# 2. Novelty (what makes this more than a game)

These are the contributions to claim in the report and viva. Phrase them as “implemented and measured”, not “first ever”.

| # | Contribution | Why it goes beyond a typical student tool | Demo proof |
| --- | --- | --- | --- |
| N1 | Multi-channel keyed fingerprint with measured survival matrix | Most projects use one channel (zero-width) that dies on paste. Here 7 channels, each tested against each attack, results tabulated | Heatmap: attack x channel survival |
| N2 | Likelihood-ratio attribution with verbal scale | Outputs a quantified, court-style statement and an explicit false-accusation probability instead of “best match” | Report page 2 |
| N3 | Collusion tracing (Tardos codes) | Two or more employees merge copies; tool names the colluders without accusing innocents | Case 6, collusion benchmark |
| N4 | Bayesian fusion with logs | Fingerprint evidence combined with access, print, badge, auth logs into one posterior; handles ties the fingerprint cannot break | Case 5 |
| N5 | Copy-level vs person-level attribution | Tool states that a fingerprint identifies a copy, then tests account-takeover and sharing hypotheses | Case 7 |
| N6 | Print channel (machine identification dots) | Attribution that survives photocopy and photo of a printed page, with parity-checked grid decoding from an image | Case 3 |
| N7 | Adversarial self-benchmark (Red Team) | The attack harness is also the game boss, so the system is evaluated against its own best attacker | Red Team leaderboard + curves |
| N8 | Tamper-evident custody plus report generator | Hash-chained log, verify command, auto-generated examiner report with tool versions and hashes | Flip one byte, verify fails |
| N9 | Calibration scoring in the casebook | Players give a confidence with each answer; overconfidence is penalised (Brier score). Teaches that “cannot distinguish” is a valid finding | Case 5 grading |


# 3. Threat model and definitions

Defender holds a master document and a secret key K. Issues one copy per employee, records copy-to-employee mapping and access logs.

Attacker (mole) holds one copy (or k copies for collusion). Knows the system exists and knows the general techniques. Does not know K or which slots carry bits. Wants the leak to stay useful (utility constraint) and untraceable.

Observation. Defender sees only the leaked artefact: text, docx, or image of a print.

Slot. One position where the master allows two variants (bit 0 or 1). Erasure. A slot whose value cannot be read after attacks. Codeword. The L-bit string assigned to an employee, one bit per slot.

Attribution scope. A matching fingerprint proves the leak derives from that copy. It does not by itself prove who acted. Reports must say so; Case 7 is built around this.


# 4. Architecture


### Components

+--------------------+

master.md --------> |  Template parser   |  {{lex:begin|start}} variation points

+---------+----------+

v

key K ----> Code layer (keyed codewords, Tardos) ---> Channels C1..C7 (embed)

v                               v

Registry (SQLite)          copies: txt / docx / pdf / png

|

leak.* ---> Ingest -> Align to master -> Extract slots (erasures)

-> Score -> Fuse(logs) -> Report

|

Attack harness (A1..A12) <---- benchmark / Red Team ------+

Custody log (hash chain) wraps every evidence action

Web workbench (Mini-Autopsy) + Casebook engine call the same Python API


### Tech stack

| Layer | Choice |
| --- | --- |
| Language | Python 3.11 |
| Libraries | typer (CLI), fastapi + uvicorn + jinja2 (web), sqlite3 (store), python-docx + lxml (OOXML), pillow + numpy (images, dot grid), scipy.stats (binomial tail), matplotlib (benchmark plots), pyyaml (case files), pytest, reportlab or python-docx (reports), optional reedsolo, optional nltk WordNet only as a lexicon to suggest synonym pairs (no training) |
| Frontend | Server-rendered HTML + vanilla JS. Custom hex viewer and diff viewer. No heavy framework (easier for GPT and for viva) |
| Not allowed | torch, tensorflow, sklearn, transformers, any model download |


### Repository layout

molehunt/

AGENTS.md  SPEC.md  README.md  pyproject.toml  Makefile

molehunt/

core/      keys.py codes.py template.py slots.py render.py

channels/  base.py zerowidth.py whitespace.py punct.py homoglyph.py

lexical.py spelling.py docx_meta.py printdots.py

detect/    ingest.py align.py extract.py score.py tardos.py fuse.py

attacks/   a01_strip.py ... a12_*.py  collusion.py  harness.py

custody/   hashchain.py intake.py

report/    builder.py  templates/

game/      cases/*.yaml generator.py logs_gen.py validator.py scoring.py

web/       app.py templates/ static/ (hex.js diff.js slotmatrix.js timeline.js)

cli.py

data/masters/     synthetic master documents (7)

bench/            results/*.csv  plots/*.png

docs/             EXPLAIN_<module>.md  DECISIONS.md

tests/


### CLI surface

molehunt init                         # create db, key file, custody log

molehunt suggest-slots master.md      # propose safe variation points

molehunt register master.md           # parse, allocate slots, store

molehunt issue --master M1 --employees roster.csv --format docx,txt

molehunt analyze leak.docx --master M1 [--logs access.csv] [--collusion 2]

molehunt attack --name A3 --strength 0.5 copy.txt -o scrubbed.txt

molehunt bench --masters 3 --leakers 20 --seeds 10   # writes bench/results

molehunt custody intake leak.docx | custody verify | custody show

molehunt report --case C-001 -o report.docx

molehunt serve                        # workbench + casebook + red team


### Data model (SQLite)

| Table | Columns |
| --- | --- |
| masters | id, title, template_path, n_slots, sha256 |
| slots | master_id, idx, channel, variant_a, variant_b, anchor_hash, anchor_ctx |
| employees | id, name, dept, role (synthetic) |
| copies | copy_id, master_id, employee_id, issued_at, format, sha256 |
| access_log | ts, employee_id, action (open/download/print/share), device_id, ip, copy_id |
| aux_logs | print_jobs, badge_log, auth_log, dhcp_leases, leave_calendar (CSV-backed) |
| evidence | id, case_id, path, sha256, intake_ts, working_copy_path |
| custody_log | seq, ts, actor, action, object_sha256, details, prev_hash, entry_hash |
| cases / progress / submissions | case_id, player_id, seed, status, score, hints_used, answers_json, started_at, finished_at |


# 5. Fingerprint engine specification


## 5.1 Master template and slots

The author writes the master in Markdown with explicit variation points: {{lex:begin|start}}, {{pun:,|}} (Oxford comma), {{spl:colour|color}}, {{spc:.  |. }} (double vs single space), {{dat:18 March|March 18}}. A curated list of about 150 meaning-preserving synonym pairs and spelling pairs drives suggest-slots; a human approves each. Meaning must not change; this is also what makes the fingerprint defensible.

Zero-width and homoglyph slots are not authored; the allocator inserts them after chosen words. A 2-page document (about 700 words) should yield 250 or more slots across channels.


## 5.2 Channels

| ID | Channel | Encoding (bit 0 / bit 1) | Dies to | Survives | Priority |
| --- | --- | --- | --- | --- | --- |
| C1 | Zero-width | U+200B / U+200C inserted after slot word (U+200D, U+2060 as decoys) | A1 strip, A2 normalize, plain retype, OCR | Copy-paste of rich text, chat apps, many CMS | Must |
| C2 | Whitespace | Single / double space after full stop; NBSP vs space; trailing space | A3 collapse, retype | Straight paste | Must |
| C3 | Punctuation and typography | Straight / curly quotes; hyphen / en dash; Oxford comma; ... / ellipsis char | A4 punct normalize, retype | Paste, partial edits | Must |
| C3b | Homoglyph | Latin letter / look-alike (e.g. Cyrillic) in a few slot words | A2b confusables map (UTS #39), OCR, retype | Copy-paste of plain text | Should |
| C4 | Lexical | Synonym A / synonym B | A6 canonicalize with dictionary, A7 paraphrase | Retype, OCR, print, photo | Must |
| C5 | Spelling, date, number formats | UK / US spelling; date and number formats | A6, A7 (if rewritten) | Retype, OCR, print, photo | Must |
| C6 | DOCX metadata | Per-employee rsid values in settings.xml and runs, custom doc property, run-splitting pattern | Paste into new doc, convert to PDF or txt | Direct file forward, rename, light edit | Must (Case 4) |
| C7 | Print dots | Faint 8x15 dot grid with row/column parity: printer id, date, minute | Heavy blur, grayscale, crop under one grid tile | Print, photocopy, phone photo | Should (Case 3) |

The survival column is a hypothesis. The benchmark in Section 6 produces the real matrix, and the report must use the measured values.


## 5.3 Code layer (keyed, explainable)

Secret key K (32 bytes). PRF = HMAC-SHA256. Slots are mapped to document positions by a keyed shuffle, so an attacker cannot predict which words carry bits.

Single-leaker mode (Cases 1, 2, 4, 5, 7): employee e gets x[e][i] = lowest bit of HMAC(K, “cw” || e || i). A random code of length L; decoding is nearest codeword. No hand-written ECC needed: with erasures ignored, the random code is itself error-tolerant. Explain this in viva with the table in 5.6.

Collusion mode (Case 6): symmetric Tardos code. Per slot i draw bias p_i = sin^2(r), r uniform in [t, pi/2 - t] (cut-off t about 0.03 for demo sizes). x[e][i] = 1 iff u(e,i) < p_i with u from HMAC(K, “u” || e || i). Thresholds are calibrated by simulation, not taken from asymptotic theory (demo lengths are far below theoretical bounds).

Optional: wrap a 12-bit employee id with Reed-Solomon (reedsolo) in channel C1 only, as an easy header for Case 1. Not required for scoring.


## 5.4 Embedding algorithm

Parse master into text with variation points and compute slot list with channel tags.

For each employee compute codeword bits for all slots; for each slot render the variant for that bit.

Insert C1/C3b slots at keyed positions. Render outputs: txt, docx (python-docx, then patch XML for C6), pdf with C7 dots.

Store copy hash, slot map, and issue record in the registry; log issuance in the custody log.


## 5.5 Detection pipeline

Ingest. Read txt/docx/png. Keep the raw code-point stream (needed for C1, C3b) and a normalized token stream. For png, run the Case 3 dot decoder.

Align. Build a skeleton of both documents (lowercase, variants canonicalised so a different variant does not break matching). Use difflib.SequenceMatcher blocks as anchors. Each slot is located through its anchor_ctx. No anchor found means erasure.

Extract. Per slot, read the observed variant in that region: bit 0, bit 1, or erasure (variant missing, both present, rewritten).

Score. For every employee j, with n observed slots and m matches: match fraction, z-score against n/2, binomial tail p-value, log10 LR (5.6).

Rank and decide. Report top candidates with scores. Apply a decision rule calibrated by the benchmark (target false-accusation rate, e.g. 0.1 percent). If the top two are not separable, the output is “cannot distinguish”, not a guess.

Fuse. Combine with log-based priors (5.7). Report.


## 5.6 Scoring mathematics

Match test. Under H0 (j is not the source) each observed slot matches with probability 0.5, so matches ~ Binomial(n, 0.5). Under H1 (j is the source) match probability is 1 - e, where e is the per-slot flip rate after attacks (estimated by the benchmark; default 0.1 to 0.2).

Likelihood ratio. LR_j = [(1-e)^m * e^(n-m)] / 0.5^n. Report log10 LR_j. Posterior with prior pi_j: posterior odds = prior odds x LR.

Verbal scale (ENFSI-style, adapt and cite). LR 1 to 10 weak support; 10 to 100 moderate; 100 to 1,000 moderately strong; 1,000 to 10,000 strong; 10,000 to 1,000,000 very strong; above 1,000,000 extremely strong.

Tardos accusation score for candidate j, observed leak bit y_i, code bit x_ji, bias p_i: if y_i = 1 add +sqrt((1-p_i)/p_i) when x_ji = 1, else add -sqrt(p_i/(1-p_i)). If y_i = 0 add +sqrt(p_i/(1-p_i)) when x_ji = 0, else add -sqrt((1-p_i)/p_i). Accuse j when score exceeds threshold Z calibrated for the false-accusation target. Erased slots contribute 0.

Marking assumption check (collusion). At every slot where all colluders hold the same bit, the leak must show that bit. Violations mean the leak was altered beyond collusion (extra noise), lowering confidence.

Why enough surviving slots matters (normal approximation, N = 50 employees, leaker flip rate e = 0.2). Use this table in viva:

| Surviving slots n | Separation of leaker from an innocent (sigma) | Approx. chance that some innocent of 50 scores as high as the average leaker |
| --- | --- | --- |
| 16 | 2.4 | about 0.4 (unreliable) |
| 32 | 3.4 | about 0.02 |
| 64 | 4.8 | about 4e-5 |
| 128 | 6.8 | negligible (below 1e-9) |

Design consequence: allocate at least 250 slots and keep at least 2 channels that survive retyping (C4, C5) with 60+ slots each.


## 5.7 Fusion with logs

Prior for employee j: pi_j proportional to 1 if j had access to the leaked master version in the window, 0.05 if only indirect access (shared drive), 0 if no access (but see copy sharing below).

Boost for behavioural evidence (after-hours download, print job, USB event): multiply prior by a documented factor, never hidden in code.

Output posterior table and state which evidence moved it. Copy sharing / account takeover: if the top copy owner has an alibi (leave, badge-out) and auth logs show an anomalous session, report copy-level attribution plus the competing hypotheses (Case 7).


# 6. Attack catalogue and benchmark

Attacks are applied to your own fingerprinted documents to measure robustness. They are the evaluation harness and the Red Team toolkit.

| ID | Attack | What it does | Expected to kill |
| --- | --- | --- | --- |
| A1 | Strip invisible | Remove Unicode category Cf and zero-width code points | C1 |
| A2 | NFKC normalize | Unicode normalization | C1 partially, some C2 |
| A2b | Confusables map | Map look-alike characters to Latin (UTS #39 skeleton) | C3b |
| A3 | Whitespace collapse | Collapse runs of spaces, strip trailing, NBSP to space | C2 |
| A4 | Punctuation normalize | Curly to straight quotes, dashes to hyphen, ellipsis to dots | C3 |
| A5 | Plain retype | Lowercase-preserving rewrite through plain text; docx to txt | C1 C2 C3 C6 |
| A6 | Canonicalize variants | Smart attacker with the synonym and spelling dictionary maps every pair to one form | C4 C5 (the hard case) |
| A7 | Random paraphrase | Replace p percent of content words from a thesaurus | C4 C5 partially |
| A8 | Truncate | Keep x percent of paragraphs | Reduces n for all channels |
| A9 | Reorder | Shuffle paragraphs or list items | Tests alignment robustness |
| A10 | Noise injection | Random synonym/space flips to corrupt slots | Raises e |
| A11 | Print-scan sim | Render page, add blur, noise, rotation, JPEG; for C7 and OCR-like loss | C1 C2 C3 C6 |
| A12 | Collusion merge | k copies merged slot-wise: majority, minority, random, min/max | Targets single-source scoring |


### Benchmark protocol (make bench)

3 master documents x 50 employees x 20 random leakers x each attack at 3 strengths x 10 seeds. Also combined chains: A1+A2+A3+A4, then + A8 at 25/50/75 percent, then + A7.

Record per run: n observed slots, matches, top-1 correct, LR, false accusation (innocent above threshold), runtime.

Outputs: bench/results/*.csv, survival matrix (attack x channel, fraction of slots surviving), accuracy vs attack strength curves, ROC-style curve (true accusation vs false accusation as threshold varies), collusion plot (colluders k vs fraction fully identified), runtime table.

Targets: 100 percent top-1 under each single attack A1 to A5 (C4/C5 intact); at least 95 percent under A1 to A4 plus 50 percent truncation; at least 80 percent under A7 at 15 percent word replacement; false accusation at most 0.1 percent at the chosen threshold; collusion k=2 both identified at least 80 percent with Tardos mode. If a target fails, report it honestly and discuss.


# 7. Workbench (Mini-Autopsy)

A real Autopsy is Java-heavy and not embeddable; build a lite workbench you can fully explain. It is the same screen for Lab mode and Casebook mode; the casebook just locks tools until earned.

| Panel / tool | Function | Priority | Unlocks at |
| --- | --- | --- | --- |
| Evidence tree | Lists evidence with SHA-256, size, intake time, working-copy status | Must | Case 1 |
| Hex viewer | Offsets, bytes, ASCII; click a byte to see code point and UTF-8 sequence | Must | Case 1 |
| Invisible-char revealer | Highlights non-printing code points, shows bit mapping | Must | Case 1 |
| Diff vs master | Side-by-side with variation points overlaid (A/B chosen) | Must | Case 2 |
| Slot matrix | Rows = candidates, columns = slots, cells coloured match / mismatch / erasure | Must | Case 2 |
| OOXML explorer | Unzip tree, pretty XML, core.xml/app.xml/settings.xml viewers, rsid table, tracked changes | Must | Case 4 |
| Image dot analyzer | Channel split, contrast stretch, threshold, grid overlay, parity check | Should | Case 3 |
| Timeline view | Merged log events with filters, brush selection, pinned evidence | Must | Case 3 |
| Auto detector | One-click ranked attribution with LR | Must | Case 5 (earned) |
| Tardos scorer | Accusation scores with threshold slider and false-accusation estimate | Should | Case 6 |
| Notes and findings | Examiner notes, tagged artefacts feeding the report | Must | Case 1 |
| Report builder | Select findings, generate DOCX/PDF | Must | Case 1 |

Rule: a one-click “find the mole” button in Case 1 destroys the learning. The automatic detector is the reward at Case 5, and always available in Lab mode.


# 8. Chain of custody and reporting

Evidence intake (follows ISO/IEC 27037 ideas)

Copy evidence into evidence/<id>/original and mark it read-only (chmod 444). Record SHA-256 (also MD5 only if you want to show why it is weak).

Create working copy; all tools operate on the working copy. Any write to original is blocked and penalised in the casebook.

Append a custody entry: seq, UTC timestamp, actor, action, object hash, details.

Hash chain

entry_hash = SHA256( prev_hash || canonical_json(seq, ts, actor, action, object_sha256, details) )

verify: recompute from genesis; report first broken seq. Optional: HMAC each entry with the examiner key.

demo: edit one byte in custody.log -> verify prints 'BROKEN at seq 7'.

Report skeleton (auto-generated DOCX/PDF)

Case id, examiner, date, scope and question asked.

Evidence table: file, SHA-256, intake time, custody status (verified).

Method: fingerprint design, channels used, tool version, validation reference (benchmark hash).

Findings: extracted slots, per-channel survival, ranking table, LR, verbal statement.

Correlation: log events, timeline, posterior.

Limitations: copy vs person, erasure rate, alternative hypotheses, known error rate from benchmark.

Conclusion in standard wording, appendices (slot matrix, hex excerpts).
