"""Analysis and benchmark workbench actions, with all I/O kept off Qt widgets."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem

from molehunt.attacks.harness import run_text_benchmark, write_benchmark
from molehunt.core.codes import generate_codewords
from molehunt.core.keys import KEY_BYTES
from molehunt.core.slots import allocate_slots
from molehunt.core.template import parse_template
from molehunt.detect.align import align_to_master
from molehunt.detect.extract import extract_variants
from molehunt.detect.fuse import FusedScore, fuse_scores
from molehunt.detect.ingest import IngestedEvidence, ingest
from molehunt.detect.logs import read_fusion_logs
from molehunt.detect.score import CandidateScore, score_candidates
from molehunt.report import write_analysis_report


@dataclass(frozen=True, slots=True)
class AnalysisBundle:
    """Engine results transferred from a worker to the Qt main thread."""

    evidence: IngestedEvidence
    slot_count: int
    observations: tuple[int | None, ...]
    codewords: dict[str, tuple[int, ...]]
    scores: tuple[CandidateScore, ...]
    fused_scores: tuple[FusedScore, ...] | None


def _employee_ids(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or "id" not in reader.fieldnames:
            raise ValueError("employee CSV must contain an id column")
        ids = [row["id"].strip() for row in reader if row.get("id", "").strip()]
    if len(ids) < 2 or len(set(ids)) != len(ids):
        raise ValueError("roster needs at least two unique synthetic employee IDs")
    return ids


def _key(path: Path) -> bytes:
    key = path.read_bytes()
    if len(key) != KEY_BYTES:
        raise ValueError(f"key file must contain {KEY_BYTES} bytes")
    return key


def _analyze_inputs(
    evidence_path: Path,
    master_path: Path,
    roster_path: Path,
    key_path: Path,
    logs_path: Path | None = None,
) -> AnalysisBundle:
    """Read, align, extract and score evidence without touching Qt widgets."""
    key = _key(key_path)
    template = parse_template(master_path.read_text(encoding="utf-8"))
    slots = allocate_slots(template, key)
    employee_ids = _employee_ids(roster_path)
    evidence = ingest(evidence_path)
    if evidence.text is None:
        raise ValueError("PNG text OCR is unavailable")
    extracted = extract_variants(
        evidence.text, align_to_master(template, slots, evidence.text)
    )
    by_index = {item.slot_index: item.bit for item in extracted}
    observations = tuple(by_index[index] for index in range(len(slots)))
    codewords = {
        employee_id: tuple(bits)
        for employee_id, bits in generate_codewords(key, employee_ids, len(slots)).items()
    }
    scores = score_candidates(observations, codewords)
    fused_scores = None
    if logs_path is not None:
        log_evidence = read_fusion_logs(logs_path, set(employee_ids))
        fused_scores = fuse_scores(scores, log_evidence.access, log_evidence.events)
    return AnalysisBundle(evidence, len(slots), observations, codewords, scores, fused_scores)


def _benchmark_inputs(
    master_path: Path,
    roster_path: Path,
    key_path: Path,
    output_path: Path,
) -> tuple[float, dict[str, Path]]:
    """Run the workbench's seeded attack set and persist its result artifacts."""
    key = _key(key_path)
    template = parse_template(master_path.read_text(encoding="utf-8"))
    roster = _employee_ids(roster_path)
    slots = allocate_slots(template, key)
    rows = run_text_benchmark(
        template, slots, key, roster,
        attack_ids=("A1", "A3", "A8"), strengths=(0, 0.5, 1), seeds=(0,),
    )
    artifacts = write_benchmark(rows, output_path)
    accuracy = sum(row.top1_correct for row in rows) / len(rows)
    return accuracy, artifacts


class AnalysisActions:
    """Methods backing candidate analysis, report export, and the Red Team bench."""

    def _analyze(self) -> None:
        try:
            evidence = self._field_path("analysis", "evidence")
            master = self._field_path("analysis", "master")
            roster = self._field_path("analysis", "employees")
            key = self._field_path("analysis", "key")
            logs_text = self.fields["analysis"]["logs"].text().strip()
            logs = Path(logs_text) if logs_text else None
            self._start_task(
                lambda: _analyze_inputs(evidence, master, roster, key, logs),
                self._render_analysis,
            )
        except (OSError, UnicodeError, ValueError) as error:
            self.status.setText(f"Analysis error: {error}")

    def _render_analysis(self, bundle: AnalysisBundle) -> None:
        """Render scores and slot states; erasures remain distinct from mismatches."""
        self._analysis = bundle
        self.scores = bundle.scores
        observations = bundle.observations
        selected = self._case_definition()
        progress = self.case_progress.get(selected.case_id)
        earned = set(progress.unlocked_tools) if progress is not None else set()
        casebook_mode = self.casebook_lock.isChecked()
        show_rankings = not casebook_mode or "auto_detector" in earned
        show_matrix = not casebook_mode or bool({"auto_detector", "slot_matrix"} & earned)
        self.results.setVisible(show_rankings)
        self.slot_matrix.setVisible(show_matrix)
        self.results.setRowCount(len(self.scores))
        self.slot_matrix.setColumnCount(len(observations) + 1)
        self.slot_matrix.setHorizontalHeaderLabels(
            ["Candidate", *(f"{index + 1:02}" for index in range(len(observations)))]
        )
        self.slot_matrix.setRowCount(len(self.scores))
        for row_index, score in enumerate(self.scores):
            values = (
                score.candidate_id, str(score.matches), str(score.observed_slots),
                "—" if score.match_fraction is None else f"{score.match_fraction:.3f}",
                f"{score.binomial_p:.4g}", f"{score.log10_lr:.3f}",
            )
            for column, value in enumerate(values):
                self.results.setItem(row_index, column, QTableWidgetItem(value))
            self.slot_matrix.setItem(row_index, 0, QTableWidgetItem(score.candidate_id))
            for index, expected in enumerate(bundle.codewords[score.candidate_id]):
                observed = observations[index]
                symbol = "—" if observed is None else "○" if observed == expected else "×"
                item = QTableWidgetItem(symbol)
                state = (
                    "erasure" if observed is None
                    else "match" if observed == expected
                    else "mismatch"
                )
                item.setToolTip(f"Slot {index + 1}: {state}")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.slot_matrix.setItem(row_index, index + 1, item)
        self.fusion_results.setVisible(bundle.fused_scores is not None and show_rankings)
        if bundle.fused_scores is not None:
            self.fusion_results.setRowCount(len(bundle.fused_scores))
            for row_index, item in enumerate(bundle.fused_scores):
                values = (
                    item.candidate_id,
                    f"{item.prior:.4f}",
                    "Cannot distinguish" if item.posterior is None else f"{item.posterior:.6f}",
                    "; ".join(item.rationale),
                )
                for column, value in enumerate(values):
                    self.fusion_results.setItem(row_index, column, QTableWidgetItem(value))
        self.analysis_detail.setPlainText(
            f"SHA-256: {bundle.evidence.sha256}\nObserved slots: "
            f"{sum(bit is not None for bit in observations)} / {bundle.slot_count}\n"
            "Interpretation: ranked copy candidates only; threshold is uncalibrated."
        )
        self.status.setText("Analysis complete. No person-level conclusion is made.")
        if self.fields["analysis"]["report"].text().strip():
            self._write_report()

    def _write_report(self) -> None:
        try:
            if self._analysis is None:
                raise ValueError("run analysis before writing a report")
            fields = self.fields["analysis"]
            evidence = self._field_path("analysis", "evidence")
            output = fields["report"].text().strip() or str(evidence.with_suffix(".report.docx"))
            write_analysis_report(
                output,
                evidence_name=evidence.name,
                evidence_sha256=self._analysis.evidence.sha256,
                observed_slots=sum(bit is not None for bit in self._analysis.observations),
                total_slots=self._analysis.slot_count,
                scores=self.scores,
                flip_rate=0.15,
                fused_scores=self._analysis.fused_scores,
            )
            self.status.setText(f"Report written: {output}")
        except (OSError, ValueError, StopIteration) as error:
            self.status.setText(f"Report error: {error}")

    def _bench(self) -> None:
        try:
            master = self._field_path("bench", "master")
            employees = self._field_path("bench", "employees")
            key = self._field_path("bench", "key")
            output = self._field_path("bench", "output")
            self._start_task(
                lambda: _benchmark_inputs(master, employees, key, output),
                self._render_benchmark,
            )
        except (OSError, UnicodeError, ValueError) as error:
            self.status.setText(f"Benchmark error: {error}")

    def _render_benchmark(self, result: tuple[float, dict[str, Path]]) -> None:
        accuracy, artifacts = result
        self.status.setText(f"Benchmark complete: top-1 {accuracy:.1%}; {artifacts['runs']}")
