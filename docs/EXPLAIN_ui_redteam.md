# Explain: Red Team panel

Inside the "Red Team bench" tab, under the benchmark form. Tick tools (strip,
normalize, confusables, collapse, punctuation, canonicalize, paraphrase,
truncate, reorder, noise), set each strength, optionally type word pairs you
discovered for canonicalize, then submit. The engine (`game/redteam.py`) runs on
the worker thread.

The meter shows utility (word similarity to the master, floor 70%). The verdict
line shows the copy you held, the detector's outcome, slots read, your log10 LR,
and the score; the table shows each player's best score.

Worked example: strip + collapse keeps utility 100% but the detector still
attributes your copy from lexical and spelling slots, so the verdict is CAUGHT.
