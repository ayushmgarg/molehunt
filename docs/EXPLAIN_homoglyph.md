# Explain: homoglyph channel

C3b changes selected Latin letters to one-code-point Greek or Cyrillic look-alikes.
The current table is a conservative subset for common examples; it is not the full
Unicode UTS #39 confusables table. Each slot records its Latin/confusable pair.

The skeleton helper maps only listed characters back to Latin. Extraction returns
0 for Latin, 1 for the selected look-alike, and an erasure for anything else.
Applying the skeleton to a marked copy removes the distinction by design.

Worked example: `MАRK` uses Cyrillic U+0410 for its second character.
Its mapped skeleton is `MARK`; after skeleton normalization, the original bit cannot
be distinguished. This optional channel needs the full official table before claiming
complete UTS #39 coverage.
