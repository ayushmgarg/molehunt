# Explain: fingerprint core

The engine keeps deterministic primitives small so a single step can be traced.

- `keys.py` frames data and derives domain-separated HMAC-SHA256 bits.
- `template.py` parses authored two-choice variation points.
- `slots.py` records anchors and assigns secret codeword indexes.
- `codes.py` derives one keyed bit per employee and slot.
- `tardos.py` generates biased collusion codes and scores observations.

Worked example: a source template has slots A, B, C; the keyed permutation assigns
codeword positions 2, 0, 1. Employee bits `[1, 0, 1]` then map to source bits
`[1, 1, 0]` before rendering. When analyzing a leak, unreadable positions are
erasures and do not count as mismatches or Tardos score contributions.

Each module has a short explanation and focused tests beside its implementation.
