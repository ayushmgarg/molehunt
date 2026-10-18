"""One engine entry point shared by the CLI, the workbench, and the benchmark.

Pipeline (SPEC 5.5): prepare master (template + keyed slots) -> align suspect text
-> extract bit / erasure per slot -> score every candidate codeword.
Observations are returned in codeword order, so position i is slot index i.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from molehunt.core.autoslots import PreparedMaster, prepare_master
from molehunt.core.codes import Codeword, generate_codewords
from molehunt.core.keys import KEY_BYTES
from molehunt.detect.align import align_to_master
from molehunt.detect.extract import SlotObservation, extract_variants
from molehunt.detect.score import CandidateScore, score_candidates


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Everything a caller needs to display or report one attribution run."""

    prepared: PreparedMaster
    extracted: tuple[SlotObservation, ...]
    observations: tuple[int | None, ...]
    codewords: dict[str, Codeword]
    scores: tuple[CandidateScore, ...]

    @property
    def observed_slots(self) -> int:
        """Number of non-erased slots."""
        return sum(bit is not None for bit in self.observations)

    def channel_survival(self) -> dict[str, tuple[int, int]]:
        """Per channel: (observed, total) slot counts."""
        result: dict[str, list[int]] = {}
        for slot in self.prepared.slots:
            bucket = result.setdefault(slot.channel, [0, 0])
            bucket[1] += 1
            bucket[0] += int(self.observations[slot.index] is not None)
        return {channel: (seen, total) for channel, (seen, total) in sorted(result.items())}


def observe(prepared: PreparedMaster, text: str) -> tuple[tuple[SlotObservation, ...], tuple]:
    """Align and extract; return raw observations and bits in codeword order."""
    extracted = extract_variants(text, align_to_master(prepared.template, prepared.slots, text))
    by_index = {item.slot_index: item.bit for item in extracted}
    return extracted, tuple(by_index[index] for index in range(len(prepared.slots)))


def analyze_prepared(
    prepared: PreparedMaster,
    text: str,
    codewords: Mapping[str, Sequence[int]],
    *,
    flip_rate: float = 0.15,
) -> AnalysisResult:
    """Score a suspect text against pre-computed candidate codewords."""
    extracted, observations = observe(prepared, text)
    scores = score_candidates(observations, codewords, flip_rate=flip_rate)
    frozen = {candidate: tuple(bits) for candidate, bits in codewords.items()}
    return AnalysisResult(prepared, extracted, observations, frozen, scores)


def analyze_text(
    master_source: str,
    key: bytes,
    employee_ids: Sequence[str],
    text: str,
    *,
    flip_rate: float = 0.15,
) -> AnalysisResult:
    """Run the full single-leaker pipeline for one suspect text."""
    if len(key) != KEY_BYTES:
        raise ValueError(f"key must contain {KEY_BYTES} bytes")
    prepared = prepare_master(master_source, key)
    codewords = generate_codewords(key, list(employee_ids), len(prepared.slots))
    return analyze_prepared(prepared, text, codewords, flip_rate=flip_rate)
