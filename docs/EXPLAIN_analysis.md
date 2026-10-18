# Explain: shared analysis entry point

`analysis.py` is the single engine call used by the CLI, the Qt workbench, and
the casebook, so every surface computes the same numbers.

Steps for one suspect text:
1. `prepare_master(source, K)`: parse front matter and template, insert keyed
   auto slots, allocate keyed codeword indexes.
2. `align_to_master` + `extract_variants`: a bit or an erasure (None) per slot.
3. `score_candidates`: matches m over observed slots n, z, binomial tail, log10 LR.

`channel_survival()` reports observed/total per channel, the raw input for the
survival matrix.

Worked example: 32 slots (12 zw, 4 hom, 8 lex, 8 spl). After A1 strip the 12 zw
slots are erasures, n = 20. The owner still matches 20/20; an innocent matches
about 10/20. Erasures never count as mismatches.
