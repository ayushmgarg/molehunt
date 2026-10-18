# Explain: template

Masters mark a two-way variation as `{{channel:variant0|variant1}}`.
`parse_template` turns the document into immutable literal and choice nodes.
Choices keep their authored order; bit 0 selects the left variant, bit 1 the right.
An empty variant is valid, for example the optional Oxford comma.

The parser rejects unmatched, nested, or malformed double-brace markers.
This prevents a typo from silently becoming ordinary document text.
`render` requires exactly one binary value per choice and preserves all literals.

Worked example: `Colour {{spl:colour|color}}.` with bit `[1]` renders as
`Colour color.`. The channel label remains attached for later slot accounting.
Variant equivalence is an authoring responsibility; this parser checks syntax only.
