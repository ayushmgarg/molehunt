# Explain: fact-level canaries (core/canaries.py)

Invisible marks die when a leaker retypes or summarises; a *fact* survives.

Master front matter declares fact families; the body uses `{{can:name}}`:

    canaries:
      codename: [Nightjar, Kestrel, Osprey, Merlin, Harrier, Condor, Heron, Petrel]
    Project {{can:codename}} launches soon.

- Choice: holder h gets value index `HMAC(K, "canary", family, h) mod v`.
- Placement: `{{can:f}}` becomes a sentinel `§i§` in the master, so keyed auto slots
  never land inside a fact and all copies share one slot map. The sentinel is filled
  at render time; before alignment the analyser masks values back to sentinels.
- Matching: search the leak for every value (whole word, any case).
  Match adds `log10(0.95 v)`, mismatch adds `log10(0.05 / (1 - 1/v))`.
  Families not mentioned are missing data. Two values of one family = merged copies.

Worked example (v = 8, four families): a headline names codename Kestrel, budget
5.4 million, launch 30 October, venue Greywick. A07's copy has all four:
log10 LR = 4 x log10(7.6) = 3.52 (LR ~ 3,300). A holder with one match and three
mismatches scores 0.88 - 3 x 1.24 = -2.84.

Limit: with 8^4 = 4,096 combinations two holders can share facts; then facts name
a small set and the fingerprint decides. Facts are evidence about the copy, not the person.
