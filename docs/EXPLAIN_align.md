# Explain: slot alignment

Alignment renders a canonical master using each slot's bit-0 variant. Both the
master and the suspect are then reduced to one skeleton:

- drop invisible format characters (Unicode category Cf, e.g. U+200B);
- map NBSP / narrow NBSP to space, curly quotes and dashes to ASCII;
- fold Cyrillic/Greek look-alikes to Latin, lower-case everything;
- rewrite every authored word variant (lex, spl, dat, num) to its bit-0 form.

Every skeleton character keeps the original span it came from. `difflib.SequenceMatcher`
finds exact blocks between the two skeletons; a slot's skeleton bounds go through
the nearest block and back to an original window in the suspect.

Because attacks such as A1 (strip) or A3 (collapse) change only characters the
skeleton already ignores, they no longer fragment the anchors. Missing anchors or
crossed bounds give an erasure, never a forced bit.

Worked example: master `A begin now` (zw slot after "now"), suspect
`A start now<U+200C>`. Both skeletons read `a begin now`. The lex window maps back to
`start` (bit 1); the zero-length zw window maps to the dropped `U+200C` (bit 1).
