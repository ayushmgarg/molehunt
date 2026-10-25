"""Scrub detector: did someone deliberately clean the fingerprint out of a leak?

Idea. A plain forwarded or copy-pasted copy loses marks at about the same rate in
every layer, because all layers are spread through the same text. Anti-forensic
cleaning is selective: the wording survives but a whole hidden layer vanishes.

Let w = survival of the word layer (lex, spl, num, dat slots read / total). For
each hidden layer L (zw, nbsp, hom) with survival s_L and at least 5 slots:

    stripped(L)  if  w >= 0.3  and  s_L <= 0.1 * w

Typographic and word layers cannot be stripped, only flattened: a tool rewrites
every quote to straight, or every synonym to one dictionary form. A genuine copy
has keyed random bits, so a layer whose reads are all one value is tested with the
two-sided binomial balance test p = 2 * P(X <= minority), X ~ Bin(n, 0.5); p < 1e-6
(the same rule as ``erase_uniform_channels``) counts as flattened.

Score = triggered signals / applicable signals (0..1). Verdict by the number of
independent layers hit: >= 3 "deliberately sanitised" (three layers gone at once
is not an accident), 1-2 "partly sanitised", 0 "no sign of sanitising". With
w < 0.3 there is too little text to judge.

Limit: retyping a copy or printing and photographing it also removes the hidden
layers. The finding is "the hidden layers were removed while the text survived",
which is itself an anti-forensic act (laundering); it is not proof of a tool.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from scipy.stats import binom

from molehunt.analysis import AnalysisResult

WORD_LAYERS = ("lex", "spl", "num", "dat")
HIDDEN = {"zw": "zero-width characters", "nbsp": "special spaces (NBSP)",
          "hom": "look-alike letters (Cyrillic/Greek)"}
FLATTEN = {"pun": "punctuation (quotes, commas, ellipses)", "spc": "sentence spacing",
           "lex": "synonym choices", "spl": "spelling variants"}
P_CUT = 1e-6


@dataclass(frozen=True, slots=True)
class ScrubSignal:
    """One check: what was tested, whether it fired, and the plain-English reason."""

    layer: str
    fired: bool
    reason: str


@dataclass(frozen=True, slots=True)
class ScrubReport:
    """Overall sanitising score, verdict, and the individual signals."""

    word_survival: float
    score: float
    verdict: str
    signals: tuple[ScrubSignal, ...]


def _counts(text: str) -> dict[str, int]:
    return {
        "zw": sum(unicodedata.category(ch) == "Cf" for ch in text),
        "nbsp": sum(ch in "  " for ch in text),
        "hom": sum(ord(ch) > 0x36f and unicodedata.category(ch).startswith("L")
                   and ("CYRILLIC" in unicodedata.name(ch, "") or
                        "GREEK" in unicodedata.name(ch, "")) for ch in text),
    }


def detect_scrub(result: AnalysisResult, text: str) -> ScrubReport:
    """Score how selectively the hidden and typographic layers were removed."""
    raw = {item.slot_index: item.bit for item in result.extracted}
    totals: dict[str, list[int]] = {}
    for slot in result.prepared.slots:
        totals.setdefault(slot.channel, []).append(raw[slot.index])
    seen = {ch: sum(bit is not None for bit in bits) for ch, bits in totals.items()}
    word_total = sum(len(totals.get(ch, [])) for ch in WORD_LAYERS)
    word_seen = sum(seen.get(ch, 0) for ch in WORD_LAYERS)
    w = word_seen / word_total if word_total else 0.0
    if w < 0.3:
        return ScrubReport(w, 0.0, "too little text to judge", ())
    chars = _counts(text)
    signals = []
    for layer, label in HIDDEN.items():
        total = len(totals.get(layer, []))
        if total < 5:
            continue
        survival = seen.get(layer, 0) / total
        fired = survival <= 0.1 * w
        signals.append(ScrubSignal(layer, fired, (
            f"{label}: {seen.get(layer, 0)}/{total} marks left ({chars[layer]} in the text) "
            f"while {w:.0%} of the wording survived" + (" - layer removed" if fired else ""))))
    for layer, label in FLATTEN.items():
        reads = [bit for bit in totals.get(layer, []) if bit is not None]
        if len(reads) < 6:
            continue
        same = max(reads.count(0), reads.count(1))
        p_value = min(1.0, 2 * float(binom.cdf(len(reads) - same, len(reads), 0.5)))
        fired = p_value < P_CUT
        signals.append(ScrubSignal(layer, fired, (
            f"{label}: {same}/{len(reads)} reads use one variant"
            + (f" (p = {p_value:.1e}) - flattened" if fired else ""))))
    if not signals:
        return ScrubReport(w, 0.0, "too little text to judge", ())
    fired = sum(item.fired for item in signals)
    verdict = ("deliberately sanitised" if fired >= 3 else
               "partly sanitised" if fired else "no sign of sanitising")
    score = fired / len(signals)
    return ScrubReport(w, score, verdict, tuple(signals))
