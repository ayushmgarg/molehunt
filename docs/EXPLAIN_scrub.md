# Explain: scrub detector (detect/scrub.py)

Question: did someone deliberately clean the fingerprint out before leaking?

Idea: ordinary loss (cut paragraphs, forwarding) hits all layers equally because
the layers are spread through the same text. Cleaning is *selective*: the words
survive but a whole hidden layer vanishes.

- w = word-layer survival (lex, spl, num, dat slots read / total). w < 0.3: too
  little text, no verdict.
- Hidden layer L (zero-width, NBSP, look-alike letters), >= 5 slots:
  `stripped if s_L <= 0.1 w`.
- Flattened layer (punctuation, spacing, synonyms, spelling), >= 6 reads: genuine
  copies have random bits, so all-one-variant is tested with the two-sided binomial
  balance test `p = 2 P(X <= minority), X ~ Bin(n, 0.5)`; flattened if p < 1e-6.
- Verdict by layers hit: >= 3 "deliberately sanitised", 1-2 "partly sanitised",
  0 "no sign of sanitising". Score = hit / applicable.

Worked example (m2, E004 copy run through strip + homoglyph fold + space collapse):
words survive (w = 1.0) but zero-width 0/66, NBSP 0/24, look-alikes 0/22 remain.
Three layers hit -> "deliberately sanitised". Half the document cut off: every
layer drops together -> "no sign of sanitising".

Limit: retyping or print-and-photograph also removes hidden layers. The finding is
"hidden layers removed while the text survived" (laundering), not proof of a tool.
