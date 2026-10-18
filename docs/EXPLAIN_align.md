# Explain: slot alignment

Alignment renders a canonical master using each slot's bit-0 variant. Both the
master and the suspect are then reduced to one skeleton:

- drop invisible format characters (Unicode category Cf, e.g. U+200B);
- map NBSP / narrow NBSP to space, curly quotes and dashes to ASCII;
- fold Cyrillic/Greek look-alikes to Latin, lower-case everything;
- rewrite every authored word variant (lex, spl, dat, num) to its group label;
  pairs sharing a word (take/need, need/require) form one group via union-find.

Every skeleton character keeps the original span it came from. The skeletons are
split into tokens (words and symbols; spaces skipped) and `difflib.SequenceMatcher`
finds matching token blocks. A slot edge inside or on a matched token maps exactly;
an edge in a gap widens to the neighbouring tokens so spaces and invisible marks
stay in the window. Token anchors keep the matcher about 30x faster than
character anchors (about 0.06 s per 800-word leak) with the same slot recovery.

Because attacks such as A1 (strip) or A3 (collapse) change only characters the
skeleton already ignores, they no longer fragment the anchors. Missing anchors or
crossed bounds give an erasure, never a forced bit.

Worked example: master `A begin now` (zw slot after "now"), suspect
`A start now<U+200C>`. Both skeletons read `a begin now`. The lex window maps back to
`start` (bit 1); the zero-length zw window maps to the dropped `U+200C` (bit 1).
