# Explain: allocator-inserted slots (C1, C2, C3b)

Authors write lexical/spelling/punctuation slots by hand. Invisible slots are
inserted by the allocator, declared in the master's front matter:

    ---
    auto_slots: {zw: 90, nbsp: 40, hom: 40}
    ---

Eligible positions in literal text:
- `zw` (C1): after a word, before space/punctuation. Bit 0 = U+200B, bit 1 = U+200C.
- `nbsp` (C2): a single space between letters. Bit 0 = U+00A0, bit 1 = U+202F.
- `hom` (C3b): a letter with two look-alikes. Bit 0 = Cyrillic, bit 1 = Greek.

Selection: positions are ranked by `keyed_order(K, "auto-<channel>")`, an HMAC
permutation; the first k are used. Without K the positions are unpredictable.

Both variants are non-canonical on purpose: A1 strip removes both ZW marks, A3/NFKC
turn both spaces into a plain space, A2b maps both look-alikes to Latin. The slot
then reads as an erasure (missing data), never as a false bit 0.

Worked example: literal `Mark will review.` with zw=1, hom=1. Keyed order picks
the end of `will` and the `M`. Copy for bit pattern (1, 0) renders
`<Cyrillic M>ark will<ZWNJ> review.`
