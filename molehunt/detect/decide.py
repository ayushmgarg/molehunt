"""Turn a candidate ranking into a stated finding with a bounded error rate.

Decision rule (SPEC 5.5 "rank and decide"):

1. Significance. Under H0 an innocent's matches ~ Binomial(n, 0.5). With N
   candidates, flag j when p_j <= alpha / N (Bonferroni). The chance that *any*
   innocent is flagged is then at most alpha (default 0.001, the 0.1 percent
   false-accusation target). The benchmark measures the empirical rate.
2. Separability. Attribute the leader only if its log10 LR beats the runner-up
   by at least ``separation`` (default 2, i.e. 100 times more likely).
   If two or more flagged candidates are within that margin -> "cannot distinguish".
3. Otherwise -> "no attribution" (insufficient evidence).

Verbal scale (ENFSI 2015 style, adapted): LR 1-10 weak, 10-100 moderate,
100-1,000 moderately strong, 1,000-10,000 strong, 10,000-1,000,000 very strong,
above 1,000,000 extremely strong.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from molehunt.detect.score import CandidateScore

_SCALE = (
    (6.0, "extremely strong support"),
    (4.0, "very strong support"),
    (3.0, "strong support"),
    (2.0, "moderately strong support"),
    (1.0, "moderate support"),
    (0.0, "weak support"),
)
COPY_CAVEAT = (
    "A fingerprint match identifies the copy the leak derives from; it does not by "
    "itself establish who disclosed it."
)


@dataclass(frozen=True, slots=True)
class Decision:
    """Outcome, the attributed candidate or tied set, and report wording."""

    outcome: str
    candidate_id: str | None
    tied: tuple[str, ...]
    familywise_bound: float
    statement: str


def verbal_scale(log10_lr: float) -> str:
    """Map log10 LR to the verbal support phrase; LR <= 1 gives no support."""
    if log10_lr <= 0:
        return "no support"
    for lower, phrase in _SCALE:
        if log10_lr > lower:
            return phrase
    return "weak support"


def decide(
    scores: Sequence[CandidateScore],
    *,
    candidates: int,
    alpha: float = 0.001,
    separation: float = 2.0,
) -> Decision:
    """Apply the Bonferroni significance test and the LR separability margin."""
    if not scores:
        raise ValueError("at least one candidate score is required")
    if not 0 < alpha < 1 or separation < 0 or candidates < 1:
        raise ValueError("alpha must be in (0, 1), separation >= 0, candidates >= 1")
    cutoff = alpha / candidates
    flagged = [score for score in scores if score.observed_slots and score.binomial_p <= cutoff]
    leader = scores[0]
    if not flagged:
        return Decision(
            "no attribution", None, (), alpha,
            f"No candidate reaches the significance cutoff p <= {cutoff:.2g} "
            f"over {leader.observed_slots} observed slots; the evidence is insufficient "
            "to attribute the leak.",
        )
    best = max(flagged, key=lambda item: item.log10_lr)
    close = tuple(
        item.candidate_id for item in flagged if best.log10_lr - item.log10_lr < separation
    )
    if len(close) > 1:
        return Decision(
            "cannot distinguish", None, close, alpha,
            f"Candidates {', '.join(close)} fit the leak almost equally well "
            f"(log10 LR within {separation:g}); the fingerprint cannot distinguish "
            f"between them. {COPY_CAVEAT}",
        )
    phrase = verbal_scale(best.log10_lr)
    return Decision(
        "attribute", best.candidate_id, (), alpha,
        f"The observed fingerprint ({best.matches}/{best.observed_slots} slots match) "
        f"provides {phrase} (log10 LR = {best.log10_lr:.1f}) for the proposition that "
        f"the leak derives from the copy issued to {best.candidate_id} rather than from "
        f"an unrelated copy. Family-wise false-accusation bound: {alpha:g}. {COPY_CAVEAT}",
    )
