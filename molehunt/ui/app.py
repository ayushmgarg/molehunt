"""Build the native Qt workbench around the MoleHunt engine APIs."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QThread, Slot
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QMainWindow

from molehunt.custody import verify_custody
from molehunt.detect.score import CandidateScore
from molehunt.game.casebook import load_casebook
from molehunt.game.generator import CaseInstance
from molehunt.game.progression import CaseProgress
from molehunt.intake_service import RegisteredIntake, intake_case
from molehunt.issuance import IssueResult, issue_registered_copy, register_master_file
from molehunt.ui.analysis_actions import AnalysisActions, AnalysisBundle, _key
from molehunt.ui.casebook_actions import CasebookActions
from molehunt.ui.diff_actions import DiffActions
from molehunt.ui.forensics_actions import ForensicsActions
from molehunt.ui.lab_panels import LabPanelActions
from molehunt.ui.pages import build_pages
from molehunt.ui.redteam_panel import RedTeamActions
from molehunt.ui.timeline_actions import TimelineActions
from molehunt.ui.worker import TaskWorker


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


class MoleHuntWindow(
    AnalysisActions, CasebookActions, DiffActions, ForensicsActions, TimelineActions,
    LabPanelActions, RedTeamActions, QMainWindow,
):
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



def run_app() -> int:
    """Launch the native workbench and return its Qt event-loop status."""
    application = QApplication.instance() or QApplication([])
    window = MoleHuntWindow()
    window.show()
    return application.exec()
