"""Build the native Qt workbench around the MoleHunt engine APIs."""

from __future__ import annotations

import csv
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QMainWindow, QTableWidgetItem

from molehunt.attacks.harness import run_text_benchmark, write_benchmark
from molehunt.core.codes import generate_codewords
from molehunt.core.keys import KEY_BYTES
from molehunt.core.render import render_docx, render_text
from molehunt.core.slots import allocate_slots
from molehunt.core.template import parse_template
from molehunt.custody import verify_custody
from molehunt.detect.align import align_to_master
from molehunt.detect.extract import extract_variants
from molehunt.detect.ingest import ingest
from molehunt.detect.score import CandidateScore, score_candidates
from molehunt.intake import intake_evidence
from molehunt.report import write_analysis_report
from molehunt.ui.pages import build_pages


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


class MoleHuntWindow(QMainWindow):
    """Desktop tabs for issuing copies, analyzing leaks, intake, and benchmarks."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MoleHunt | Forensic Desk")
        self.resize(1180, 780)
        self.fields: dict[str, dict[str, QLineEdit]] = {}
        self.scores: tuple[CandidateScore, ...] = ()
        self.setCentralWidget(build_pages(self))
        self.status = QLabel("Synthetic evidence only. Results rank copies, not people.")
        self.status.setObjectName("status")
        self.statusBar().addWidget(self.status, 1)

    def _field_path(self, tab: str, name: str) -> Path:
        value = self.fields[tab][name].text().strip()
        if not value:
            raise ValueError(f"{name} path is required")
        return Path(value)

    def _analyze(self) -> None:
        try:
            fields = self.fields["analysis"]
            evidence = self._field_path("analysis", "evidence")
            master = parse_template(self._field_path("analysis", "master").read_text(encoding="utf-8"))
            roster = _employee_ids(self._field_path("analysis", "employees"))
            key = _key(self._field_path("analysis", "key"))
            slots = allocate_slots(master, key)
            evidence_record = ingest(evidence)
            if evidence_record.text is None:
                raise ValueError("PNG text OCR is unavailable")
            extracted = extract_variants(
                evidence_record.text, align_to_master(master, slots, evidence_record.text)
            )
            by_index = {item.slot_index: item.bit for item in extracted}
            observations = [by_index[index] for index in range(len(slots))]
            codewords = generate_codewords(key, roster, len(slots))
            self.scores = score_candidates(observations, codewords)
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
                for index, expected in enumerate(codewords[score.candidate_id]):
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
            self.analysis_detail.setPlainText(
                f"SHA-256: {evidence_record.sha256}\nObserved slots: "
                f"{sum(bit is not None for bit in observations)} / {len(slots)}\n"
                "Interpretation: ranked copy candidates only; threshold is uncalibrated."
            )
            self.status.setText("Analysis complete. No person-level conclusion is made.")
            report_path = fields["report"].text().strip()
            if report_path:
                self._write_report()
        except (OSError, UnicodeError, ValueError) as error:
            self.status.setText(f"Analysis error: {error}")

    def _write_report(self) -> None:
        try:
            if not self.scores:
                raise ValueError("run analysis before writing a report")
            fields = self.fields["analysis"]
            evidence = self._field_path("analysis", "evidence")
            details = self.analysis_detail.toPlainText()
            digest = next(line.removeprefix("SHA-256: ") for line in details.splitlines() if line.startswith("SHA-256:"))
            observed = int(next(line.split(": ")[1].split(" /")[0] for line in details.splitlines() if line.startswith("Observed slots:")))
            total = int(next(line.split("/")[1] for line in details.splitlines() if line.startswith("Observed slots:")))
            output = fields["report"].text().strip() or str(evidence.with_suffix(".report.docx"))
            write_analysis_report(
                output,
                evidence_name=evidence.name,
                evidence_sha256=digest,
                observed_slots=observed,
                total_slots=total,
                scores=self.scores,
                flip_rate=0.15,
            )
            self.status.setText(f"Report written: {output}")
        except (OSError, ValueError, StopIteration) as error:
            self.status.setText(f"Report error: {error}")

    def _issue(self) -> None:
        try:
            fields = self.fields["issue"]
            key = _key(self._field_path("issue", "key"))
            template = parse_template(self._field_path("issue", "master").read_text(encoding="utf-8"))
            employee = fields["employee"].text().strip()
            if not employee:
                raise ValueError("synthetic employee ID is required")
            output = self._field_path("issue", "output")
            slots = allocate_slots(template, key)
            codeword = generate_codewords(key, [employee], len(slots))[employee]
            if output.suffix.casefold() == ".docx":
                content = render_docx(template, slots, codeword, key, employee)
            elif output.suffix.casefold() in {".txt", ".md"}:
                content = render_text(template, slots, codeword).encode("utf-8")
            else:
                raise ValueError("copy output must use .txt, .md, or .docx")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(content)
            self.status.setText(f"Issued synthetic copy {employee}: {output}")
        except (OSError, UnicodeError, ValueError) as error:
            self.status.setText(f"Issue error: {error}")

    def _intake(self) -> None:
        try:
            fields = self.fields["intake"]
            result = intake_evidence(
                self._field_path("intake", "evidence"),
                fields["case_id"].text().strip(),
                actor=fields["actor"].text().strip(),
                root=self._field_path("intake", "root"),
            )
            fields["ledger"].setText(str(result.custody_log))
            self.status.setText(f"Intake complete: original {result.sha256[:8]}…")
        except (OSError, ValueError) as error:
            self.status.setText(f"Intake error: {error}")

    def _verify(self) -> None:
        try:
            result = verify_custody(self._field_path("intake", "ledger"))
            self.status.setText(
                f"VERIFIED: {result.entries} custody events"
                if result.valid
                else f"BROKEN at seq {result.broken_seq}"
            )
        except OSError as error:
            self.status.setText(f"Custody error: {error}")

    def _bench(self) -> None:
        try:
            template = parse_template(self._field_path("bench", "master").read_text(encoding="utf-8"))
            roster = _employee_ids(self._field_path("bench", "employees"))
            key = _key(self._field_path("bench", "key"))
            slots = allocate_slots(template, key)
            rows = run_text_benchmark(
                template, slots, key, roster, attack_ids=("A1", "A3", "A8"),
                strengths=(0, 0.5, 1), seeds=(0,),
            )
            artifacts = write_benchmark(rows, self._field_path("bench", "output"))
            accuracy = sum(row.top1_correct for row in rows) / len(rows)
            self.status.setText(f"Benchmark complete: top-1 {accuracy:.1%}; {artifacts['runs']}")
        except (OSError, UnicodeError, ValueError) as error:
            self.status.setText(f"Benchmark error: {error}")


def run_app() -> int:
    """Launch the native workbench and return its Qt event-loop status."""
    application = QApplication.instance() or QApplication([])
    window = MoleHuntWindow()
    window.show()
    return application.exec()
