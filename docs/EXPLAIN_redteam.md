# Explain: Red Team boss ("Be the Mole")

You get one fingerprinted copy (a seeded employee of 50) and a tool box:
strip (A1), normalize (A2), confusables (A2b), collapse (A3), punctuation (A4),
canonicalize (A6, only with word pairs you discovered), paraphrase (A7),
truncate (A8), reorder (A9), noise (A10). Tools run in your chosen order.

Utility = SequenceMatcher ratio over skeleton words = 2M / (T_master + T_leak),
M = matched words. Invisible edits cost 0; cutting or rewording costs utility.
It must stay >= 0.70 or the attempt scores 0.

Opponent: the Lab detector and its decision rule (Bonferroni alpha = 0.001,
LR separation 2). You win if utility >= 0.70 and it does not attribute the
leak to your copy (it says "cannot distinguish", "no attribution", or names
someone else).

Score = 100 x utility x (slot cut + LR cut) / 2 + 100 if you win, with
slot cut = 1 - n / n0 and LR cut = 1 - max(log10 LR, 0) / log10 LR0.

Worked example: strip + collapse + confusables keeps utility 1.0 but cuts n
from 265 to 149; the lexical and spelling slots still give log10 LR ~ 31, so
the detector attributes your copy: no win, score 47 for the cut.
Every attempt is stored; the leaderboard keeps each player's best score.
