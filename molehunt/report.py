"""Assemble the examiner report skeleton of SPEC Section 8 from analysis results.

Sections, in order: case and scope; evidence table (file, SHA-256, intake time,
custody status); method (channels, LR formula, tool version, benchmark hash);
findings (per-channel survival, ranking, decision and verbal statement);
correlation (log fusion posterior, timeline); limitations (copy vs person,
erasure rate, alternatives, measured error rate); conclusion; appendices
(slot matrix excerpt, hex excerpt). Missing inputs are stated, never invented.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from molehunt import __version__
from molehunt.detect.decide import COPY_CAVEAT, Decision
from molehunt.detect.fuse import FusedScore
from molehunt.detect.score import CandidateScore
from molehunt.report_render import ReportTable, Section, render

UNCALIBRATED = (
    "The decision threshold has not been calibrated unless a separate benchmark "
    "establishes its error rate."
)


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    """One evidence row in the report's evidence table."""

    name: str
    sha256: str
    intake_ts: str = "not recorded"
    custody: str = "not recorded"


@dataclass(frozen=True)
class ReportInput:
    """All facts the report may state; optional parts are reported as absent."""

    evidence: tuple[EvidenceItem, ...]
    scores: tuple[CandidateScore, ...]
    observed_slots: int
    total_slots: int
    flip_rate: float
    case_id: str = "Not provided"
    examiner: str = "Not provided"
    question: str = "Which issued copy does the questioned document derive from?"
    channels: dict[str, tuple[int, int]] = field(default_factory=dict)
    decision: Decision | None = None
    fused_scores: tuple[FusedScore, ...] | None = None
    timeline: tuple[tuple[str, str, str], ...] = ()
    slot_matrix: tuple[tuple[str, ...], ...] = ()
    hex_excerpt: tuple[str, ...] = ()
    bench_dir: Path = Path("bench")


def benchmark_reference(bench_dir: Path) -> tuple[str, str]:
    """Return (runs.csv SHA-256, measured false-accusation statement)."""
    runs = bench_dir / "results" / "runs.csv"
    summary = bench_dir / "results" / "summary.json"
    digest = hashlib.sha256(runs.read_bytes()).hexdigest() if runs.is_file() else "none on file"
    if summary.is_file():
        data = json.loads(summary.read_text(encoding="utf-8"))
        rate = data.get("false_accusation_rate")
        runs_count = data.get("runs")
        error = f"measured false-accusation rate {rate} over {runs_count} benchmark runs"
    else:
        error = "no benchmark summary on file; error rate unknown"
    return digest, error


def _evidence_table(items: Sequence[EvidenceItem]) -> tuple[ReportTable, ...]:
    """Tabulate evidence once intake or custody facts exist (or several files)."""
    recorded = any(item.intake_ts != "not recorded" for item in items)
    if len(items) < 2 and not recorded:
        return ()
    return (ReportTable(
        ("File", "SHA-256", "Intake (UTC)", "Custody"),
        tuple((item.name, item.sha256, item.intake_ts, item.custody) for item in items),
    ),)


def _ranking(scores: Sequence[CandidateScore], limit: int = 15) -> ReportTable:
    rows = tuple(
        (
            str(rank), score.candidate_id, str(score.matches), str(score.observed_slots),
            "-" if score.match_fraction is None else f"{score.match_fraction:.3f}",
            f"{score.binomial_p:.4g}", f"{score.log10_lr:.3f}",
        )
        for rank, score in enumerate(scores[:limit], start=1)
    )
    return ReportTable(
        ("Rank", "ID", "Matches", "Observed", "Match fraction", "P(null)", "log10 LR"), rows
    )


def build_sections(data: ReportInput) -> list[Section]:
    """Produce the ordered report sections without touching the filesystem."""
    if data.fused_scores is not None and {s.candidate_id for s in data.scores} != {
        s.candidate_id for s in data.fused_scores
    }:
        raise ValueError("fusion and fingerprint rankings must contain the same candidates")
    bench_hash, bench_error = benchmark_reference(data.bench_dir)
    erasure_rate = 1 - data.observed_slots / data.total_slots if data.total_slots else 1.0
    sections = [
        Section("Case and scope", (
            f"Case ID: {data.case_id}", f"Examiner: {data.examiner}",
            f"Generated UTC: {datetime.now(UTC).isoformat(timespec='seconds')}",
            f"Question: {data.question}",
        )),
        Section("Evidence", tuple(
            f"Evidence file: {item.name}; SHA-256: {item.sha256}" for item in data.evidence
        ), _evidence_table(data.evidence)),
        Section("Method", (
            ("Each issued copy carries a keyed binary codeword in variation slots across "
            f"channels: {', '.join(data.channels) or 'not recorded'}. Slots are aligned to the "
            "master, read as bit 0, bit 1, or erasure; erasures are omitted, never mismatches."),
            ("Null model: an unrelated copy matches each observed slot with probability 0.5. "
            f"Alternative: the source copy matches with probability 1 - e, e = {data.flip_rate:g}. "
            "LR = (1-e)^m e^(n-m) / 0.5^n for m matches over n observed slots."),
            (f"Tool: MoleHunt {__version__}. Validation reference (benchmark runs.csv "
            f"SHA-256): {bench_hash}."),
        )),
    ]
    findings = [f"Observed slots: {data.observed_slots} / {data.total_slots}."]
    findings.append(data.decision.statement if data.decision else UNCALIBRATED)
    survival = ReportTable(
        ("Channel", "Observed", "Total"),
        tuple((name, str(seen), str(total)) for name, (seen, total) in data.channels.items()),
    )
    tables = (survival, _ranking(data.scores)) if data.channels else (_ranking(data.scores),)
    sections.append(Section("Findings", tuple(findings), tables))
    if data.fused_scores is not None or data.timeline:
        correlation_tables = []
        if data.fused_scores is not None:
            correlation_tables.append(ReportTable(
                ("ID", "Prior", "Posterior", "Applied evidence"),
                tuple(
                    (
                        item.candidate_id, f"{item.prior:.4f}",
                        "Cannot distinguish" if item.posterior is None else f"{item.posterior:.6f}",
                        "; ".join(item.rationale),
                    )
                    for item in data.fused_scores
                ),
            ))
        if data.timeline:
            correlation_tables.append(ReportTable(("Time (UTC)", "Employee", "Event"), data.timeline))
        sections.append(Section(
            "Log fusion",
            (("Posterior combines the fingerprint likelihood with explicit access weights and "
             "event multipliers. These demo weights are assumptions, not calibrated probabilities."),),
            tuple(correlation_tables),
        ))
    sections.append(Section("Interpretation and limitations", (
        COPY_CAVEAT + " Copy sharing, account takeover, or a copy obtained outside the "
        "issuing system remain alternative hypotheses until excluded by other evidence.",
        f"Erasure rate: {erasure_rate:.1%} of slots could not be read. "
        f"Known error rate: {bench_error}. {'' if data.decision else UNCALIBRATED}".strip(),
        "Results depend on the supplied master, roster, evidence, and flip-rate assumption.",
    )))
    if data.decision is not None:
        outcome = {
            "attribute": f"The questioned document derives from the copy issued to "
                         f"{data.decision.candidate_id}.",
            "cannot distinguish": "The fingerprint cannot distinguish between "
                                  f"{', '.join(data.decision.tied)}.",
            "no attribution": "No attribution is made; the evidence is insufficient.",
        }[data.decision.outcome]
        sections.append(Section("Conclusion", (outcome, COPY_CAVEAT)))
    appendix = []
    if data.slot_matrix:
        width = len(data.slot_matrix[0]) - 1
        appendix.append(ReportTable(
            ("Candidate", *(str(i) for i in range(1, width + 1))), data.slot_matrix, True
        ))
    if data.hex_excerpt:
        appendix.append(ReportTable(("Hex excerpt",), tuple((line,) for line in data.hex_excerpt), True))
    if appendix:
        sections.append(Section(
            "Appendix", ("Slot matrix: o match, x mismatch, - erasure.",), tuple(appendix)
        ))
    return sections


def write_report(output_path: str | Path, data: ReportInput) -> Path:
    """Build sections and render them to .docx or .pdf."""
    if not 0 <= data.observed_slots <= data.total_slots:
        raise ValueError("observed slot count must be between zero and total slots")
    if not 0 < data.flip_rate < 0.5:
        raise ValueError("flip rate must be strictly between zero and 0.5")
    for item in data.evidence:
        if len(item.sha256) != 64 or any(ch not in "0123456789abcdef" for ch in item.sha256):
            raise ValueError("evidence SHA-256 must be 64 lowercase hexadecimal characters")
    return render("MoleHunt Evidence Analysis", build_sections(data), output_path)


def write_analysis_report(
    output_path: str | Path,
    *,
    evidence_name: str,
    evidence_sha256: str,
    observed_slots: int,
    total_slots: int,
    scores: Sequence[CandidateScore],
    flip_rate: float,
    case_id: str = "Not provided",
    fused_scores: Sequence[FusedScore] | None = None,
    decision: Decision | None = None,
    channels: dict[str, tuple[int, int]] | None = None,
) -> Path:
    """Single-evidence convenience wrapper around :func:`write_report`."""
    return write_report(output_path, ReportInput(
        evidence=(EvidenceItem(evidence_name, evidence_sha256),),
        scores=tuple(scores), observed_slots=observed_slots, total_slots=total_slots,
        flip_rate=flip_rate, case_id=case_id, decision=decision, channels=channels or {},
        fused_scores=tuple(fused_scores) if fused_scores is not None else None,
    ))
