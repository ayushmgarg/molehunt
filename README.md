# MoleHunt

**Find which copy of a confidential document leaked.**

Everyone gets their own copy of a document with a hidden fingerprint. When a copy
leaks, even edited, retyped, printed and photographed, or forwarded, MoleHunt reads
what is left of the fingerprint and tells you which copy it came from, and how sure
it is.

Cyber Forensics project, SVKM's MPSTME. Eshan Shukla (B124) and Ayush Garg (B143).
Offline, synthetic data only, no AI or machine learning: just keyed hashing and statistics.

---

## What it does

| Feature | In one line |
|---|---|
| Fingerprinted copies | Invisible characters, look-alike letters, special spaces, word and spelling choices, Word metadata, printer dots |
| Evidence handling | SHA-256 at intake, read-only original, tamper-evident custody log |
| Statistical verdict | Likelihood ratio per copy; names a copy only when it is 100x ahead and under a 0.1% false-accusation bound |
| Canary facts | Each copy has a different codename, budget, venue and date, so even a paraphrase can be traced |
| Scrub detector | Flags deliberate cleaning of the hidden marks |
| Leak family tree | A forwarded copy reveals the whole path, e.g. Company -> E007 -> C12 |
| Meter and heatmap | Shows the evidence building up slot by slot |
| Games | Find the Mole (party game), Escape Room (six forensic locks), Casebook, Red Team |

A match identifies **which copy** leaked, not **who** leaked it.

---

## Install (once)

Needs [uv](https://docs.astral.sh/uv/).

```bash
uv sync --python 3.11
uv run molehunt init
uv run pytest -q
```

`init` creates `.molehunt/` with the secret key, the database and the custody log.

---

## Run it

**LAN games and lab** (phones on the same Wi-Fi or hotspot):

```bash
uv run molehunt live
```

It prints a PIN, the players' address and a Host console link. Open the Host console on
the presenting laptop; players open the address and pick Find the Mole, Escape Room or
Forensic Lab. Step-by-step guide: [docs/LIVE_DEMO.md](docs/LIVE_DEMO.md).

**Desktop app:**

```bash
uv run molehunt serve
```

**Command line, one full case:**

```bash
uv run molehunt register data/masters/m1_roadmap.md --master-id M1
uv run molehunt issue E007 --master M1 -o demo/E007.txt
uv run molehunt attack --name A5 demo/E007.txt -o demo/leak.txt
uv run molehunt intake demo/leak.txt C-001 --actor EX-01
uv run molehunt examine demo/leak.txt --master data/masters/m1_roadmap.md --employees data/demo/roster50.csv --html demo/findings.html
uv run molehunt report --case C-001 -o demo/C-001.docx --master data/masters/m1_roadmap.md --employees data/demo/roster50.csv
```

`uv run molehunt --help` lists every command.

---

## Results

- 25,200 simulated leaks across 12 attack types: all 9 targets met, 2 wrong accusations (0.008%).
- 352 automated tests.
- Weak spots, honestly: [docs/BENCHMARK.md](docs/BENCHMARK.md).

---

## Where things are

```text
molehunt/   code: core, channels, detect, attacks, game, web, ui
data/       synthetic master documents and roster
docs/       how it works (ARCHITECTURE.md), one note per module, benchmark
tests/      pytest suite
```
