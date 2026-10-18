# Explain: punctuation channel

C3 stores two authored punctuation variants, such as straight/curly quotes,
hyphen/en dash, or an Oxford comma. The left variant is bit 0; the right is bit 1.
Embedding applies replacements from the end so earlier offsets stay stable.

Each output slot stores an adjusted offset and 16 following characters from the
rendered text. This anchor makes an empty variant readable and rejects many edits.
If neither variant and its following anchor match, extraction returns an erasure.

Worked example: `red, blue, and gold` can remove the comma before `and` for bit 1.
The following ` and gold` anchor confirms the omission at the aligned slot.
