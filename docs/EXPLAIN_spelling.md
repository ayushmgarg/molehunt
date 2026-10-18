# Explain: spelling and format channel

C5 offers spelling, date-order, and number-separator variants. The left form is bit 0.
Date pairs must parse to the same day, month, and optional year. Number pairs must
contain the same digits after common grouping separators are removed.
Spelling suggestions are starter candidates and require contextual approval.

Embedding replaces from right to left and records adjusted offsets plus nearby text.
Extraction requires a whole-token variant and its following anchor; otherwise it erases.

Worked example: `18 March` and `March 18` both parse to day 18, month March.
For number `1,500` versus `1 500`, both digit signatures are `1500`.
