# MoleHunt

**Find which copy of a confidential document leaked.**

Each employee gets their own copy of a document with a hidden fingerprint: invisible
characters, look-alike letters, special spaces, synonym and spelling choices, Word
metadata, and printer dots. When a copy leaks (edited, retyped, cut down, printed and
photographed, or two copies merged), MoleHunt reads what is left of the fingerprint,
ranks the copies with a likelihood ratio, and writes a forensic report.

Offline. Synthetic people and documents only. No AI or machine learning, just statistics.
A match tells you **which copy** leaked, not **who** leaked it.

---

## 1. Install (once)

Needs [uv](https://docs.astral.sh/uv/) (Python manager).

```bash
uv python install 3.11
uv sync --python 3.11
uv run molehunt init
```

`init` creates `.molehunt/` with your secret key, the database, and the custody log.

Check it works:

```bash
uv run pytest -q
```

---

## 2. Open the app

```bash
uv run molehunt serve
```

| Tab | What you do there |
|---|---|
| Evidence analysis | Pick a leaked file, master, roster, key, click **Run analysis**. See the ranking, slot matrix, and finding. Write a report. |
| Issue copy | Register a master document, then issue a fingerprinted copy for an employee. |
| Intake and custody | Bring evidence in (hash + read-only original + working copy), verify the custody log. |
| Red Team bench | Run the benchmark, or play the mole: scrub your copy and try to fool the detector. |
| Casebook | Play the 7 training cases. Tick "Casebook mode" so tools unlock as you progress. |
| Evidence tools | Hex view, invisible character reveal, diff vs master, timeline, Word metadata explorer, printer dot decoder, collusion scorer, notes. |

---

## 3. The basic flow from the command line

```bash
# give every employee a copy
uv run molehunt register data/masters/m1_roadmap.md --master-id M1
uv run molehunt issue --master M1 --employees data/demo/roster50.csv --format txt,docx,pdf,png

# pretend someone leaked E007's copy after retyping it
uv run molehunt attack --name A5 data/demo/issued/E007.txt -o reports/generated/leak.txt

# take it in as evidence and analyse it
uv run molehunt intake reports/generated/leak.txt C-001 --actor EX-01
uv run molehunt analyze reports/generated/leak.txt --master data/masters/m1_roadmap.md --employees data/demo/roster50.csv

# full examiner report (DOCX or PDF)
uv run molehunt report --case C-001 -o reports/generated/C-001.docx --master data/masters/m1_roadmap.md --employees data/demo/roster50.csv

# show that tampering with the custody log is caught
uv run molehunt custody demo
```

Evidence can be `.txt`, `.md`, `.docx`, or a `.png` / `.jpg` scan of a printed copy.

---

## 4. Live demo with two laptops (same Wi-Fi)

On the presenting laptop:

```bash
uv run molehunt live
```

It prints a **PIN** and a **Join** link. On the second laptop or a phone:

1. Open the Join link, pick an employee, enter the PIN, download the copy.
2. Edit it, retype it, or print it and take a photo.
3. Upload it back on the same page.

Open the **Board** link on the projector. Each leak appears within 3 seconds with its
hash, the ranking, and the finding. Full steps: [docs/LIVE_DEMO.md](docs/LIVE_DEMO.md).
If the other laptop can't connect, set the Wi-Fi to **Private** and allow Python
through the firewall.

---

## 5. Other things you can run

| Command | What it does |
|---|---|
| `uv run molehunt redteam --tools strip,collapse,truncate:0.8` | Red Team: try to scrub your copy and evade the detector |
| `uv run molehunt issue E003 --master M1 -o x.txt --code tardos` then `analyze x.txt ... --collusion` | Catch two people who merged their copies |
| `uv run molehunt analyze leak.txt ... --logs access.csv` | Combine the fingerprint with access/print logs |
| `uv run molehunt bench` | Full benchmark (about 20 min); results in `bench/` |
| `uv run molehunt --help` | Every command |

---

## 6. Results

Benchmark: 25,200 attacked leaks, all 9 plan targets passed, 2 wrong accusations in
25,200. The weak spots are listed honestly in [docs/BENCHMARK.md](docs/BENCHMARK.md).

## 7. Where things are

```text
molehunt/      the code (core, channels, detect, attacks, game, ui)
data/masters/  7 synthetic documents (3 benchmark + 4 case stories)
docs/          explanations per module, decisions, benchmark, validation
tests/         314 tests
```

Viva notes: [docs/EXPLAIN_INDEX.md](docs/EXPLAIN_INDEX.md). Plan coverage: [docs/PLAN_AUDIT.md](docs/PLAN_AUDIT.md).
