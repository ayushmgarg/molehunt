"""One call that runs every examination on a leak: the hub for the CLI, web lab, and games.

Steps, in the order an examiner would explain them:

1. Fingerprint attribution over every holder and every registered forward path
   (``core/lineage.py``: direct copies use the ordinary codeword).
2. Decision with the Bonferroni + separation rule (``detect/decide.py``).
3. Canary facts, if the master declares them (``core/canaries.py``): works even
   on a paraphrase that kept no fingerprint.
4. Scrub detector (``detect/scrub.py``): signs of deliberate cleaning.
5. Heatmap and evidence curve for the leader (``detect/heatmap.py``).
6. Lineage: matches per hop and the forward tree with the leak path marked.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from molehunt.analysis import AnalysisResult, analyze_prepared
from molehunt.core.autoslots import prepare_master
from molehunt.core.canaries import CanaryReport, match_canaries
from molehunt.core.keys import KEY_BYTES
from molehunt.core.lineage import LayerEvidence, layer_evidence, path_codewords, tree_lines
from molehunt.detect.decide import Decision
from molehunt.detect.heatmap import Segment, evidence_curve, heatmap
from molehunt.detect.scrub import ScrubReport, detect_scrub


@dataclass(frozen=True)
class Examination:
    """Everything shown on a findings page."""

    result: AnalysisResult
    decision: Decision
    canaries: CanaryReport | None
    scrub: ScrubReport
    segments: list[Segment]
    leader: str
    runner_up: str
    curve: list[float]
    hops: tuple[LayerEvidence, ...]
    tree: list[str]


def examine(master_source: str, key: bytes, holders: Sequence[str], text: str,
            forwards: Sequence[str] = ()) -> Examination:
    """Run attribution, canaries, scrub check, heatmap, and lineage on one leak."""
    if len(key) != KEY_BYTES:
        raise ValueError(f"key must contain {KEY_BYTES} bytes")
    if len(set(holders)) < 2:
        raise ValueError("need at least two holders to compare")
    prepared = prepare_master(master_source, key)
    candidates = list(dict.fromkeys([*holders, *forwards]))
    result = analyze_prepared(prepared, text, path_codewords(key, candidates, len(prepared.slots)))
    decision = result.decision()
    canaries = (match_canaries(text, prepared.canaries, key, candidates)
                if prepared.canaries else None)
    leader, runner, curve = evidence_curve(result, text)
    return Examination(
        result=result, decision=decision, canaries=canaries,
        scrub=detect_scrub(result, text), segments=heatmap(result, text, leader),
        leader=leader, runner_up=runner, curve=curve,
        hops=layer_evidence(key, leader, result.observations),
        tree=tree_lines(forwards, leader if decision.outcome == "attribute" else None),
    )
