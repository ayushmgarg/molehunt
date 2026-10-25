"""Escape-room case generator: one keyed case per team, six forensic locks.

Every value is drawn from ``random.Random(HMAC(K, "escape", seed, team))``, so each
team gets its own mole, station, time, files, and answers, and answers are computed
from the generated evidence (rule 6), never written by hand.

Story "Midnight at Hollowmere": the carnival memo leaked at night. Locks:

1. Hash check: four voicemail transcripts, three doctored by one character. Only one
   matches the SHA-256 in the custody record. Answer: its letter. Its text names the
   printer station S that matters later.
2. Invisible ink: a ransom note hides a word in zero-width characters
   (U+200B = 0, U+200C = 1, 8 bits per letter, most significant bit first).
3. Ghost editor: a DOCX whose docProps/core.xml says who last modified it. Answer:
   that agent (an editor, not the leaker: metadata shows editing, not leaking).
4. Yellow dots: a photo of the printed leak carries a C7 dot grid. Answer: the
   print time HH:MM (decoded minute of day m -> m // 60, m % 60).
5. Printer log: exactly one row has station S at that time. Answer: its agent.
6. Fingerprint: the leaked text goes through the MoleHunt examiner. Answer: the
   agent whose copy leaked. It agrees with lock 5, closing the case.
"""

from __future__ import annotations

import hashlib
import io
import random
import re
from dataclasses import dataclass
from datetime import date

from molehunt.attacks.transform import attack_chain
from molehunt.channels.printdots import DotMetadata
from molehunt.core.autoslots import PreparedMaster
from molehunt.core.canaries import holder_values
from molehunt.core.codes import generate_codeword
from molehunt.core.keys import digest
from molehunt.core.render import render_png, render_text

WORDS = ("RAVEN", "GHOUL", "CRYPT", "WITCH", "COVEN", "SKULL", "BONES", "FANGS",
         "GRAVE", "SPOOK", "CURSE", "TOMBS")
AGENTS = tuple(f"A{i:02}" for i in range(1, 9))
CASE_DAY = date(2026, 10, 31)


@dataclass(frozen=True)
class Lock:
    """One stage: story clue, downloadable files, tool to use, question, answer."""

    title: str
    story: str
    files: dict[str, bytes]
    tool: str
    question: str
    answer: str
    hint: str


def holder(team: str, agent: str) -> str:
    """Team-scoped holder id, so one team's files never solve another team's case."""
    return f"{team}:{agent}"


def normalise(answer: str) -> str:
    """Compare answers case-blind; accept A3 / a03 / 3 for agents and 9:05 for 09:05."""
    text = answer.strip().upper().replace(" ", "")
    if re.fullmatch(r"A?0*\d{1,2}", text):
        return f"A{int(text.lstrip('A')):02}"
    if re.fullmatch(r"\d{1,2}[:.]\d{2}", text):
        hours, minutes = re.split(r"[:.]", text)
        return f"{int(hours):02}:{minutes}"
    return text


def hide_word(cover: str, word: str) -> str:
    """Put the word's bits (ZWSP = 0, ZWNJ = 1) after successive spaces of the cover."""
    bits = "".join(f"{ord(ch):08b}" for ch in word)
    parts = cover.split(" ")
    if len(parts) <= len(bits):
        raise ValueError("cover text too short")
    marks = ["\u200b" if bit == "0" else "‌" for bit in bits]
    text = parts[0]
    for index, part in enumerate(parts[1:]):
        text += " " + (marks[index] if index < len(marks) else "") + part
    return text


def _docx(editor: str, owner: str, stamp: str) -> bytes:
    from docx import Document

    document = Document()
    document.add_paragraph("Hollowmere Studios - launch night run sheet (draft).")
    document.add_paragraph("Lanterns at the gate, fog at nine, reveal at midnight.")
    props = document.core_properties
    props.author, props.last_modified_by = owner, editor
    props.title, props.revision = "Run sheet", 7
    props.comments = f"exported {stamp}"
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def build_case(prepared: PreparedMaster, key: bytes, seed: int, team: str) -> list[Lock]:
    """Generate the six locks for one team."""
    rng = random.Random(digest(key, "escape", str(seed), team))
    mole, editor, owner = rng.sample(AGENTS, 3)
    station = rng.randint(2, 19)
    minute = rng.randint(22 * 60, 23 * 60 + 50)
    clock = f"{minute // 60:02}:{minute % 60:02}"
    word = rng.choice(WORDS)

    stations = rng.sample([s for s in range(2, 20) if s != station], 3)
    letters = ["A", "B", "C", "D"]
    genuine = rng.choice(letters)
    voicemail = ("VOICEMAIL 23:12. Caller: night guard. 'Someone used the printer at "
                 "Station {s} tonight. I saw the yellow light blink. Check the dots.'\n")
    files, others = {}, iter(stations)
    for letter in letters:
        s = station if letter == genuine else next(others)
        files[f"voicemail_{letter}.txt"] = voicemail.format(s=s).encode()
    true_hash = hashlib.sha256(files[f"voicemail_{genuine}.txt"]).hexdigest()
    files["custody_record.txt"] = (f"CUSTODY RECORD - item VM-1\nSHA-256 at seizure: {true_hash}\n"
                                   "Three copies on the shared drive were edited later.\n").encode()

    cover = ("Do not look for us. The memo is already out and the carnival secret goes to the "
             "highest bidder before dawn. If you want the rest, you will need the password "
             "we hid in plain sight inside this very note. Search every gap between the words "
             "and you might find it, but the clock is ticking and the lanterns are going dark "
             "one by one. The guard saw nothing. The cameras saw nothing. Only the paper "
             "remembers what happened here tonight, so read carefully and trust no copy.")
    note = hide_word(cover, word)

    bits = generate_codeword(key, holder(team, mole), len(prepared.slots))
    facts = holder_values(prepared.canaries, key, holder(team, mole))
    copy = render_text(prepared.template, prepared.slots, bits, facts)
    leak = attack_chain(copy, ["A4", "A8"], strength=0.75, seed=rng.randrange(2**31))
    photo = render_png(prepared.template, prepared.slots, bits,
                       DotMetadata(station, CASE_DAY, minute), facts)

    rows = []
    for agent in AGENTS:
        for _ in range(4):
            s, m = rng.randint(2, 19), rng.randint(21 * 60, 23 * 60 + 59)
            if (s, m) != (station, minute):
                rows.append((m, s, agent))
    decoy = rng.choice([a for a in AGENTS if a != mole])
    rows += [(minute, station, mole), (minute, stations[0], decoy), (minute + 7, station, decoy)]
    log = "time,station,agent,pages\n" + "".join(
        f"{m // 60:02}:{m % 60:02},Station {s},{a},{rng.randint(1, 9)}\n"
        for m, s, a in sorted(rows))
    roster = "agent\n" + "".join(f"{a}\n" for a in AGENTS)

    return [
        Lock("The doctored voicemail", "11:47 pm. The night guard left a voicemail, but three "
             "copies on the shared drive were edited. Only the original matches the hash in "
             "the custody record.", files, "hash",
             "Which voicemail file is the original? (A, B, C or D)", genuine,
             "Hash each file with the Hash workstation and compare with the custody record."),
        Lock("Invisible ink", "A ransom note was slipped under the door. It looks normal, "
             "but the gaps between words hide something.", {"ransom_note.txt": note.encode()},
             "ink", "What is the hidden password?", word,
             "Reveal invisible characters: each mark after a space is one bit (0 or 1). Group "
             "8 bits per letter and convert binary to ASCII (01000001 = A)."),
        Lock("The ghost editor", "Security pulled the run-sheet draft from the shared drive. "
             "Someone touched it after the owner.", {"run_sheet.docx": _docx(editor, owner,
                                                                              clock)},
             "meta", "Which agent last modified the draft?", editor,
             "Open the DOCX metadata (docProps/core.xml) and read lastModifiedBy."),
        Lock("Yellow dots", "Editing is not leaking. A photo of the printed memo surfaced "
             "online. Printers hide a yellow dot pattern on every page.",
             {"leak_photo.png": photo}, "dots", "At what time was it printed? (HH:MM)", clock,
             "Decode the dots. The minute of day m means hour m // 60 and minute m % 60."),
        Lock("The printer log", "IT exported the printer log for the night. Use the station "
             "from the true voicemail and the time from the dots.",
             {"printer_log.csv": log.encode()}, "none",
             "Which agent printed at that station and time?", mole,
             "Filter the log for the station named in the original voicemail, then the time."),
        Lock("Fingerprint", "The text of the leak was posted on a forum. Every agent's copy "
             "is fingerprinted. Confirm whose copy it was.",
             {"leaked_memo.txt": leak.encode(), "roster.csv": roster.encode()}, "examine",
             "Whose copy leaked?", mole,
             "Run the leaked memo through the MoleHunt examiner and read the verdict."),
    ]
