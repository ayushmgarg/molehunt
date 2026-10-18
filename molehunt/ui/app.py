"""Build the native Qt workbench around the MoleHunt engine APIs."""

from __future__ import annotations

import csv
import json
import re
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Slot
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QMainWindow, QTableWidgetItem

from molehunt.attacks.harness import run_text_benchmark, write_benchmark
from molehunt.core.codes import generate_codewords
from molehunt.core.keys import KEY_BYTES
from molehunt.core.slots import allocate_slots
from molehunt.core.template import parse_template
from molehunt.custody import verify_custody
from molehunt.detect.align import align_to_master
from molehunt.detect.extract import extract_variants
from molehunt.detect.fuse import FusedScore, fuse_scores
from molehunt.detect.ingest import IngestedEvidence, ingest
from molehunt.detect.logs import read_fusion_logs
from molehunt.detect.score import CandidateScore, score_candidates
from molehunt.game.casebook import CaseDefinition, load_casebook
from molehunt.game.generator import CaseInstance, generate_case
from molehunt.game.progression import (
    CaseProgress,
    get_case_progress,
    initialize_casebook,
    start_case,
    submit_answer,
    use_hint,
)
from molehunt.intake_service import RegisteredIntake, intake_case
from molehunt.issuance import IssueResult, issue_registered_copy, register_master_file
from molehunt.report import write_analysis_report
from molehunt.ui.pages import build_pages
from molehunt.ui.worker import TaskWorker


@dataclass(frozen=True, slots=True)
class AnalysisBundle:
    """Engine results transferred from a worker to the Qt main thread."""

    evidence: IngestedEvidence
    slot_count: int
    observations: tuple[int | None, ...]
    codewords: dict[str, tuple[int, ...]]
    scores: tuple[CandidateScore, ...]
    fused_scores: tuple[FusedScore, ...] | None


def _analyze_inputs(
    evidence_path: Path,
    master_path: Path,
    roster_path: Path,
    key_path: Path,
    logs_path: Path | None = None,
) -> AnalysisBundle:
    """Read and score one evidence item without touching any Qt widgets."""
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
    """Run the desktop's fixed seeded attack set and persist its artifacts."""
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


def _load_fallback_font() -> None:
    """Register an installed system sans font when Qt has no discovered fonts."""
    if QFontDatabase.families():
        return
    candidates = (
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    )
    for font_path in candidates:
        if font_path.is_file():
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            families = QFontDatabase.applicationFontFamilies(font_id)
            if font_id >= 0 and families:
                QApplication.instance().setFont(QFont(families[0], 10))
                return


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


def _register_inputs(
    master_path: Path, key_path: Path, database_path: Path, master_id: str
) -> tuple[str, int]:
    """Register one master for UI issuance and return its ID and slot count."""
    key = _key(key_path)
    registry_id = master_id.strip() or master_path.stem
    slot_count = register_master_file(
        database_path, key, master_path, master_id=registry_id
    )
    return registry_id, slot_count


def _issue_inputs(
    master_reference: str, employee_id: str, output_path: Path,
    key_path: Path, database_path: Path,
) -> IssueResult:
    """Issue a copy through the same registered-master API as the CLI."""
    return issue_registered_copy(
        database_path, _key(key_path), employee_id, master_reference, output_path
    )


class MoleHuntWindow(QMainWindow):
    """Desktop tabs for issuing copies, analyzing leaks, intake, and benchmarks."""

    def __init__(self) -> None:
        super().__init__()
        _load_fallback_font()
        self.setWindowTitle("MoleHunt | Forensic Desk")
        self.resize(1180, 780)
        self.fields: dict[str, dict[str, QLineEdit]] = {}
        self.case_definitions = load_casebook()
        self.case_instance: CaseInstance | None = None
        self.case_progress: dict[str, CaseProgress] = {}
        self.scores: tuple[CandidateScore, ...] = ()
        self._analysis: AnalysisBundle | None = None
        self._thread: QThread | None = None
        self._worker: TaskWorker | None = None
        self._task_success: Callable[[object], None] | None = None
        self.setCentralWidget(build_pages(self))
        self.status = QLabel("Synthetic evidence only. Results rank copies, not people.")
        self.status.setObjectName("status")
        self.statusBar().addWidget(self.status, 1)

    def _field_path(self, tab: str, name: str) -> Path:
        value = self.fields[tab][name].text().strip()
        if not value:
            raise ValueError(f"{name} path is required")
        return Path(value)

    def _start_task(self, operation: Callable[[], object], on_success: Callable[[object], None]) -> None:
        """Run an engine callable on a QThread and marshal its result to the UI."""
        if self._thread is not None and self._thread.isRunning():
            self.status.setText("Another operation is still running.")
            return
        self._task_success = on_success
        self.centralWidget().setEnabled(False)
        self.status.setText("Working…")
        thread = QThread(self)
        worker = TaskWorker(operation)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.completed.connect(self._task_completed)
        worker.failed.connect(self._task_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._task_finished)
        self._thread = thread
        self._worker = worker
        thread.start()

    @Slot(object)
    def _task_completed(self, result: object) -> None:
        try:
            if self._task_success is None:
                raise RuntimeError("task result has no UI handler")
            self._task_success(result)
        except Exception as error:  # noqa: BLE001 - Qt callbacks must not unwind through the event loop.
            self.status.setText(f"Operation error: {error}")

    @Slot(str)
    def _task_failed(self, message: str) -> None:
        self.status.setText(f"Operation error: {message}")

    @Slot()
    def _task_finished(self) -> None:
        self.centralWidget().setEnabled(True)
        self._worker = None
        self._thread = None

    def closeEvent(self, event) -> None:
        """Wait for any active evidence operation before destroying the window."""
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()
        super().closeEvent(event)

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
        """Render worker results in the main thread and optionally export a report."""
        self._analysis = bundle
        self.scores = bundle.scores
        observations = bundle.observations
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
        self.fusion_results.setVisible(bundle.fused_scores is not None)
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

    def _issue(self) -> None:
        try:
            fields = self.fields["issue"]
            master_reference = fields["master_id"].text().strip() or fields["master"].text().strip()
            if not master_reference:
                raise ValueError("registered master ID or path is required")
            employee = fields["employee"].text().strip()
            if not employee:
                raise ValueError("synthetic employee ID is required")
            output = self._field_path("issue", "output")
            key_path = self._field_path("issue", "key")
            database = self._field_path("issue", "database")
            self._start_task(
                lambda: _issue_inputs(master_reference, employee, output, key_path, database),
                self._render_issued,
            )
        except (OSError, UnicodeError, ValueError) as error:
            self.status.setText(f"Issue error: {error}")

    def _register(self) -> None:
        try:
            fields = self.fields["issue"]
            master = self._field_path("issue", "master")
            key = self._field_path("issue", "key")
            database = self._field_path("issue", "database")
            master_id = fields["master_id"].text().strip()
            self._start_task(
                lambda: _register_inputs(master, key, database, master_id),
                self._render_registered,
            )
        except (OSError, UnicodeError, ValueError) as error:
            self.status.setText(f"Registration error: {error}")

    def _render_registered(self, result: tuple[str, int]) -> None:
        master_id, slot_count = result
        self.fields["issue"]["master_id"].setText(master_id)
        self.status.setText(f"Registered master {master_id}: {slot_count} slots")

    def _render_issued(self, result: IssueResult) -> None:
        self.status.setText(
            f"Issued copy {result.copy_id} for {result.employee_id}: {result.output_path}"
        )

    def _intake(self) -> None:
        try:
            fields = self.fields["intake"]
            evidence = self._field_path("intake", "evidence")
            case_id = fields["case_id"].text().strip()
            actor = fields["actor"].text().strip()
            root = self._field_path("intake", "root")
            database = self._field_path("intake", "database")
            self._start_task(
                lambda: intake_case(
                    evidence, case_id, actor=actor, root=root, database=database
                ),
                self._render_intake,
            )
        except (OSError, ValueError) as error:
            self.status.setText(f"Intake error: {error}")

    def _render_intake(self, registered: RegisteredIntake) -> None:
        result = registered.intake
        self.fields["intake"]["ledger"].setText(str(result.custody_log))
        self.status.setText(
            f"Intake complete: evidence {registered.evidence_id}; hash {result.sha256[:8]}…"
        )

    def _casebook_refresh(self) -> None:
        try:
            fields = self.fields["casebook"]
            player_id = fields["player"].text().strip()
            database = self._field_path("casebook", "database")
            initialize_casebook(database, player_id, self.case_definitions)
            self.case_progress = {
                progress.case_id: progress
                for progress in get_case_progress(database, player_id)
            }
            self._casebook_show_selected()
            self.status.setText(f"Casebook progress loaded for {player_id}")
        except (OSError, ValueError, sqlite3.Error) as error:
            self.status.setText(f"Casebook error: {error}")

    def _casebook_show_selected(self) -> None:
        definition = self._case_definition()
        progress = self.case_progress.get(definition.case_id)
        status = progress.status if progress is not None else "not started"
        tools = ", ".join(progress.unlocked_tools) if progress else "none"
        self.case_details.setPlainText(
            f"{definition.brief}\n\nObjective: {definition.objective}\n\n"
            f"Status: {status}\nAvailable tools: {tools}\n"
            "Start the case to generate its seeded evidence package."
        )

    def _case_definition(self) -> CaseDefinition:
        case_id = self.case_selector.currentData()
        return next(case for case in self.case_definitions if case.case_id == case_id)

    def _casebook_start(self) -> None:
        try:
            fields = self.fields["casebook"]
            player_id = fields["player"].text().strip()
            if not player_id:
                raise ValueError("player ID is required")
            seed = int(fields["seed"].text().strip())
            if seed < 0:
                raise ValueError("seed must not be negative")
            definition = self._case_definition()
            database = self._field_path("casebook", "database")
            initialize_casebook(database, player_id, self.case_definitions)
            start_case(database, player_id, definition.case_id, self.case_definitions)
            root = self._field_path("casebook", "output_root")
            player_slug = re.sub(r"[^A-Za-z0-9_-]", "_", player_id)[:32]
            base = root / player_slug / definition.case_id / f"seed-{seed}"
            output = base
            run_number = 2
            while output.exists():
                output = base.with_name(f"seed-{seed}-run-{run_number}")
                run_number += 1
            master = Path(definition.master)
            self._start_task(
                lambda: generate_case(
                    definition, output, seed=seed, master_path=master
                ),
                self._casebook_case_ready,
            )
        except (OSError, ValueError, sqlite3.Error) as error:
            self.status.setText(f"Casebook error: {error}")

    def _casebook_case_ready(self, instance: CaseInstance) -> None:
        self.case_instance = instance
        definition = instance.definition
        self.case_details.setPlainText(
            f"{definition.brief}\n\nObjective: {definition.objective}\n\n"
            f"Generated evidence: {instance.evidence_path}\n"
            f"Roster: {instance.roster_path}\n"
            f"Auxiliary logs: {', '.join(str(path) for path in instance.auxiliary_paths) or 'none'}\n"
            "Generated answers are checked privately when you submit."
        )
        self._casebook_refresh()
        self.status.setText(f"Generated {definition.case_id}: {instance.evidence_path}")

    def _casebook_hint(self) -> None:
        try:
            definition = self._case_definition()
            player_id = self.fields["casebook"]["player"].text().strip()
            database = self._field_path("casebook", "database")
            hint = use_hint(database, player_id, definition)
            self.case_details.append(f"\nHint: {hint}")
            self.status.setText(f"Hint used for {definition.case_id}")
        except (OSError, ValueError, sqlite3.Error) as error:
            self.status.setText(f"Hint error: {error}")

    def _casebook_submit(self) -> None:
        try:
            definition = self._case_definition()
            instance = self.case_instance
            if instance is None or instance.definition.case_id != definition.case_id:
                raise ValueError("start this case before submitting an answer")
            fields = self.fields["casebook"]
            answer = fields["answer"].text().strip()
            if not answer:
                raise ValueError("enter an answer first")
            truth = json.loads(instance.ground_truth_path.read_text(encoding="utf-8"))
            if definition.generator == "collusion":
                expected = {item.casefold() for item in truth["colluders"]}
                submitted = {item.strip().casefold() for item in answer.split(",") if item.strip()}
                correct = submitted == expected
            elif definition.generator == "print_timeline":
                correct = answer == str(truth["printer_id"])
            else:
                correct = answer.casefold() == str(truth["copy_owner"]).casefold()
            result = submit_answer(
                self._field_path("casebook", "database"),
                fields["player"].text().strip(),
                self.case_definitions,
                definition.case_id,
                answer=answer,
                correct=correct,
                confidence=self.case_confidence.value(),
            )
            self._casebook_refresh()
            verdict = "Correct" if result.completed else "Not correct yet"
            self.status.setText(
                f"{verdict}: {result.points} points; Brier {result.grade.brier_score:.3f}"
            )
        except (OSError, ValueError, KeyError, sqlite3.Error, json.JSONDecodeError) as error:
            self.status.setText(f"Submission error: {error}")

    def _verify(self) -> None:
        try:
            ledger = self._field_path("intake", "ledger")
            self._start_task(lambda: verify_custody(ledger), self._render_verification)
        except (OSError, ValueError) as error:
            self.status.setText(f"Custody error: {error}")

    def _render_verification(self, result) -> None:
        self.status.setText(
            f"VERIFIED: {result.entries} custody events"
            if result.valid
            else f"BROKEN at seq {result.broken_seq}"
        )

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

    def _render_benchmark(self, result) -> None:
        accuracy, artifacts = result
        self.status.setText(f"Benchmark complete: top-1 {accuracy:.1%}; {artifacts['runs']}")


def run_app() -> int:
    """Launch the native workbench and return its Qt event-loop status."""
    application = QApplication.instance() or QApplication([])
    window = MoleHuntWindow()
    window.show()
    return application.exec()
