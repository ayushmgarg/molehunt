# Explain: Find the Mole (game/mole_game.py)

1. Lobby: players join with a nickname -> agents A01, A02, ... Each phone shows
   that agent's fingerprinted copy (keyed codeword + canary facts).
2. Leak: a seeded RNG (seed printed by `molehunt live`) picks the mole. Modes:
   `solo`; `forward` (mole's copy re-stamped for journalist J01x; two innocent
   decoy forwards are logged so the tree is no giveaway); `double` (two moles,
   copies merged bit by bit with `collude_bits(..., "random")`, facts mixed).
   Each mole picks <= 2 scrub tools = real attacks (A1 strip, A2b fold, A3 spaces,
   A4 quotes, A7 synonyms, A8 cut, A9 shuffle, A5 retype). Max 3 steps in total.
3. Investigate: 3 forensic tokens each. Fact check (1): leak's facts vs yours.
   Ink scan (1): scrub verdict. Lineage trace (1): forwarded or not. Slot sample
   (2): k/24 random observed slots agree with one agent (innocent ~ 12/24).
   Then a bet: suspect + 1-3 chips. The mole's bet is a frame-up.
4. Reveal: `forensics.examine` over all agents and forward paths. Suspects = first
   hop of the attributed path (or of every tied path).

Scoring: investigator +100 x chips if right, -50 x chips if wrong, +20 per unused
token. Mole +200 if not named by forensics, +50 per wrong bet, +50 if the frame
target got the most bets.

Worked example: 4 players, solo, A03 strips invisibles and swaps synonyms. A01
spends 2 tokens on a slot sample of A03 (21/24 agree) and bets 3 chips on A03:
+300 + 20 = +320. Forensics attribute A03, so A03 gets 0 + 50 per wrong bet.
