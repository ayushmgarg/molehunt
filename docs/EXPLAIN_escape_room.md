# Explain: escape room (game/escape_case.py, game/escape_room.py)

Teams race one clock through six forensic locks. Each team's case comes from
`random.Random(HMAC(K, "escape", seed, team))`: own mole, station, time, files.
Answers are computed from the generated evidence, never typed by hand (rule 6).

| Lock | Evidence | Tool | Answer |
|---|---|---|---|
| 1 Doctored voicemail | 4 transcripts + custody hash | SHA-256 | the file whose hash matches |
| 2 Invisible ink | ransom note | ZW revealer | U+200B = 0, U+200C = 1, 8 bits/letter |
| 3 Ghost editor | run_sheet.docx | core.xml reader | lastModifiedBy (an editor, not the leaker) |
| 4 Yellow dots | photo of the printed leak | C7 decoder | minute m -> HH:MM = m//60 : m%60 |
| 5 Printer log | CSV | your eyes | the one row with station S (lock 1) at the time (lock 4) |
| 6 Fingerprint | leaked memo + roster | MoleHunt examiner | the attributed copy; agrees with lock 5 |

Holder ids are team-scoped (`night-owls:A03`), so one team's files never solve
another team's case. Decoys: a row at the same time on another station and one at
the same station 7 minutes later.

Time: final = elapsed + 120 s per hint + 30 s per wrong answer. Rank: more locks,
then less time. After the clock ends answers are refused.

Worked example: dots decode minute 1380 -> 23:00. The log has one row
"23:00, Station 4, A06"; the examiner attributes the leak to A06 (margin > 2).
