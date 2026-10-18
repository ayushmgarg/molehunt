# Analysis report

- The DOCX report records the case ID, evidence filename and SHA-256, observed-slot count, and generation time.
- It includes each candidate's matches, null-model probability, and log10 likelihood ratio.
- When log evidence is supplied, it adds access priors, normalized posteriors, and the factors applied.
- The report labels demo log multipliers as assumptions rather than calibrated probabilities.
- For `m` matches among `n` observed slots, `LR = (1-e)^m e^(n-m) / 0.5^n`.
- Erasures do not contribute to `n` or `m`.
- Example: 3 matches in 3 slots with `e=0.15` gives `LR = 0.85^3 / 0.5^3`.
- The report labels the ranking as copy attribution and explains that it does not identify the person who disclosed the file.
- Decision thresholds remain unset until an independent benchmark estimates their error rate.
- Reports can be generated in DOCX or PDF; casebook-linked findings are future work.
