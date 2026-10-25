# Explain: leak family tree (core/lineage.py)

Setting: the document system re-stamps a copy whenever it is forwarded (like a
mail gateway). Company -> E007 -> contractor C12 -> press. The press copy should
reveal the whole path.

- Each codeword position i gets a keyed layer from u = HMAC(K, "lineage", i)/2^32:
  layer 0 if u < 0.5, layer 1 if u < 0.75, else layer 2.
- Path p = (p0 .. p_{L-1}): a slot of layer l carries the bit of node p[min(l, L-1)].
  Node ids are prefixes (`E007`, `E007>C12`); node bits are the normal codeword.
- A direct copy (L = 1) is exactly the ordinary copy. Max three hops.
- Attribution: every registered path is one candidate; the usual LR ranking runs.
  E007 and E007>C12 share layer 0 and differ at random on the rest, so the true path
  wins by about log10(0.85/0.15) = 0.75 per differing slot.
- Forwards are logged in SQLite table `lineage(path, parent, holder, ts)`.

Worked example (m1, 265 slots): about 133 slots are layer 0, 66 layer 1, 66 layer 2.
The press copy matches E007 on layer 0, C12 on layer 1, P01 on layer 2. Against
E007>C12 it differs on about 33 of the layer-2 slots: margin ~ 33 x 0.75 = 25 in
log10, far above the separation of 2. The tree prints:

    Company
    `-- E007 *
        `-- C12 *
            `-- P01  <== leak
