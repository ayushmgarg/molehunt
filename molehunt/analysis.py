"""One engine entry point shared by the CLI, the workbench, and the benchmark.

Pipeline (SPEC 5.5): prepare master (template + keyed slots) -> align suspect text
-> extract bit / erasure per slot -> score every candidate codeword.
Observations are returned in codeword order, so position i is slot index i.
Collusion mode swaps the random code for a keyed symmetric Tardos code and the
LR ranking for Tardos scores with a simulated threshold (detect/tardos.py).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from molehunt.core.autoslots import PreparedMaster, prepare_master
from molehunt.core.codes import Codeword, generate_codewords
from molehunt.core.keys import KEY_BYTES
from molehunt.core.tardos import (
    generate_tardos_biases,
    generate_tardos_codeword,
    marking_violations,
)
from molehunt.detect.align import align_to_master
from molehunt.detect.decide import Decision, decide
from molehunt.detect.extract import SlotObservation, erase_uniform_channels, extract_variants
from molehunt.detect.ingest import IngestedEvidence
from molehunt.detect.score import CandidateScore, score_candidates
from molehunt.detect.tardos import (
    TardosCalibration,
    TardosCandidateScore,
    accuse,
    calibrate_threshold,
    score_tardos_candidates,
)


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Everything a caller needs to display or report one attribution run."""

    prepared: PreparedMaster
    extracted: tuple[SlotObservation, ...]
    observations: tuple[int | None, ...]
    codewords: dict[str, Codeword]
    scores: tuple[CandidateScore, ...]
    forged_channels: tuple[str, ...] = ()

    @property
    def observed_slots(self) -> int:
        """Number of non-erased slots."""
        return sum(bit is not None for bit in self.observations)

    def decision(self, *, alpha: float = 0.001, separation: float = 2.0) -> Decision:
        """Apply the Bonferroni + separability rule over all candidates."""
        return decide(
            self.scores, candidates=len(self.codewords), alpha=alpha, separation=separation
        )

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
    observations, forged = erase_uniform_channels(prepared.slots, observations)
    scores = score_candidates(observations, codewords, flip_rate=flip_rate)
    frozen = {candidate: tuple(bits) for candidate, bits in codewords.items()}
    return AnalysisResult(prepared, extracted, observations, frozen, scores, forged)


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


@dataclass(frozen=True)
class CollusionResult:
    """Tardos-mode scores, simulated threshold, accused set, and marking check."""

    prepared: PreparedMaster
    observations: tuple[int | None, ...]
    biases: tuple[float, ...]
    codewords: dict[str, tuple[int, ...]]
    scores: tuple[TardosCandidateScore, ...]
    calibration: TardosCalibration
    accused: tuple[str, ...]
    violations: tuple[int, ...]


def tardos_codewords(
    key: bytes, employee_ids: Sequence[str], length: int
) -> tuple[tuple[float, ...], dict[str, tuple[int, ...]]]:
    """Keyed biases and one Tardos codeword per employee."""
    biases = generate_tardos_biases(key, length)
    return biases, {
        employee: generate_tardos_codeword(key, employee, biases) for employee in employee_ids
    }


def analyze_collusion(
    master_source: str,
    key: bytes,
    employee_ids: Sequence[str],
    text: str,
    *,
    target: float = 0.001,
    seed: int = 0,
) -> CollusionResult:
    """Score Tardos codewords, calibrate Z by simulation, and accuse above Z."""
    if len(key) != KEY_BYTES:
        raise ValueError(f"key must contain {KEY_BYTES} bytes")
    prepared = prepare_master(master_source, key)
    biases, codewords = tardos_codewords(key, employee_ids, len(prepared.slots))
    _, observations = observe(prepared, text)
    scores = score_tardos_candidates(observations, biases, codewords)
    calibration = calibrate_threshold(
        observations, biases, candidates=len(codewords), target=target, seed=seed
    )
    accused = accuse(scores, calibration.threshold)
    violations = (
        tuple(marking_violations([codewords[item] for item in accused], observations))
        if accused
        else ()
    )
    return CollusionResult(
        prepared, observations, biases, codewords, scores, calibration, accused, violations
    )


def evidence_text(record: IngestedEvidence) -> str:
    """Decoded text of an evidence file; PNG scans are read with the classical OCR."""
    if record.text is not None:
        return record.text
    from PIL import Image

    from molehunt.channels.ocr import ocr_image

    with Image.open(record.path) as image:
        return ocr_image(image)
