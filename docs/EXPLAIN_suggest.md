# Slot suggestions

- The scanner looks for whole-word occurrences from the curated lexical and spelling lists.
- Each result includes its channel, character offset, line number, variant pair, and nearby context.
- Uppercase and title case are copied to the suggested alternative.
- The scanner never edits the source master or inserts a variation marker.
- Example: `The color is gray` yields `color|colour` and `gray|grey` proposals.
- A human must review meaning and grammar in context before approving a pair.
- The current lists are starter dictionaries, not the roughly 150 pairs in the target plan.
