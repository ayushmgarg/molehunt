# Explain: fingerprint heatmap and attribution-o-meter (detect/heatmap.py)

Heatmap: the leak text is split into segments. Each slot window is coloured by
comparing the read bit with the leader's codeword:

- green `match`, red `mismatch`, grey `erased` (missing data, never a mismatch),
  gold `fact` (a canary value), plain text uncoloured.
- Invisible variants stay in the text; the web page draws a small marker for them.

Meter: walk observed slots in reading order and add

    step = log10 P(bit | leader) - log10 P(bit | runner-up)
    P(bit | c) = 0.85 if bit = c's bit else 0.15

Slots where both candidates agree add 0; a slot only the leader matches adds
log10(0.85/0.15) = 0.75. The last value equals the leader's log10 LR minus the
runner-up's: the separation margin. The decision rule attributes at >= 2.

Worked example: 6 observed slots, leader and runner-up disagree on 3 of them and
the leak sides with the leader each time -> curve 0, 0.75, 0.75, 1.51, 1.51, 2.26.
The needle crosses 2 ("attribute") on the sixth slot.
