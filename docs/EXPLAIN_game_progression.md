# Case progression

- Each player starts with C-01 available; later cases stay locked until the previous case is solved.
- Each case stores its own status, earned tools, score, hint count, and timestamps in SQLite.
- Hints are shown in order and stop after three uses.
- The answer checker supplies correctness from the generated private truth; submissions store the player's answer and confidence.
- Points use the Brier grade, minus 10 per prior attempt and 5 per hint used.
- A correct answer completes the case and makes the next case available with cumulative tools.
- Example: a correct 0.8-confidence answer scores 96 base points before attempt and hint penalties.
