# Explain: log fusion

Access levels start with weights 1.0 (direct), 0.05 (indirect), and 0 (none).
Named events multiply a candidate's weight by explicit documented factors.
The fingerprint's log10 LR contributes `log(LR)` in log space.
The resulting weights are normalized into posteriors.

If every candidate has zero prior weight, fusion returns no posterior instead of
inventing a ranking. The output retains the prior and each event factor so the
examiner can see what moved a candidate.

Worked example: one after-hours download multiplies prior weight by 3. A candidate
with direct access and that event has weight `1 × 3 × LR` before normalization.
