# Case response scoring

- The player gives a confidence value from 0 to 1 with each answer.
- Correctness is supplied by the case checker from generated ground truth.
- Binary Brier loss is `(confidence - outcome)^2`, where correct is 1 and incorrect is 0.
- Points are `round(100 * (1 - Brier loss))` using half-up rounding.
- Example: a correct answer at 0.9 confidence scores 99; a wrong answer at 0.9 scores 19.
- This penalizes confident mistakes and rewards calibrated uncertainty.
