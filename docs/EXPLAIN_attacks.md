# Seeded text attacks

- `attack_text` models A1–A11 as transformations of one rendered copy; A12 (collusion merge) works on codewords in `collusion.py` and the harness.
- Every random choice uses a local pseudorandom generator initialized from the supplied seed.
- Strength `s` is the probability of applying an eligible edit, except paragraph truncation and reorder, where it controls the retained/reordered fraction.
- A1 removes selected Unicode format characters; A2 normalizes selected characters; A2b substitutes selected confusables.
- A3 collapses selected whitespace runs to one space but keeps blank-line paragraph breaks (so a later A8 still truncates); A4 replaces selected typography; A5 combines common cleanup operations.
- A6 maps marked lexical alternatives to the zero form; A7 applies the small reviewed synonym starter list.
- A8 keeps the first `ceil(n*s)` paragraphs; at strength zero it removes all paragraphs.
- A9 shuffles a seeded prefix of paragraphs; A10 (noise injection) swaps variant words for their partner and toggles single/double spaces, each with probability s, which raises the flip rate e.
- Example: with seed 7, the same text, attack ID, and strength always produce the same output.
- A11 on text models print-then-OCR: drop Cf marks, NFKC, fold look-alikes, ASCII typography, collapse spaces, then misread each letter with probability 0.02 x strength.
- `attack_chain` applies several attacks in order (e.g. A1+A2+A3+A4) with seed `seed*100+k` for step k.
- `simulate_print_scan` rotates, blurs, adds seeded pixel noise, then JPEG-encodes the page.
- These are attack models for experiments; they do not demonstrate resistance to real-world editing.
