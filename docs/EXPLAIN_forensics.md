# Explain: examine() hub (forensics.py)

One function runs every check on a leak, in the order an examiner explains them:

1. Fingerprint attribution over all holders *and* registered forward paths.
2. Decision: Bonferroni alpha/N plus LR separation 2 (detect/decide.py).
3. Canary facts (if the master declares them): survives paraphrase.
4. Scrub detector: hidden layers removed while text survived?
5. Heatmap segments and evidence curve for the leader.
6. Lineage: matches per hop, and the forward tree with the leak path marked.

Used by `molehunt examine` (CLI + HTML page), the web lab, and both LAN games, so
every screen shows the same numbers.

Worked example: A05 forwards to X01; X01 strips invisible characters and leaks.
examine() returns: decision "attribute A05>X01", scrub "deliberately sanitised"
(zero-width, NBSP, look-alike layers gone, words intact), hops A05 and X01 each
matching > 80 percent of their layer, tree `A05 * -> X01 <== leak`, and canary
facts pointing at X01's copy.
