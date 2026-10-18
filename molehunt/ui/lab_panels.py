"""Lab panels inside Evidence tools: OOXML explorer, image dot analyzer, Tardos
scorer with a threshold slider, and examiner notes. Heavy work (dot search,
Tardos calibration) runs on the worker thread; widgets only display results."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from molehunt.analysis import analyze_collusion
from molehunt.channels.dot_locate import _dark_mask, scan_dot_grid
from molehunt.channels.printdots import COLUMNS, ROWS
from molehunt.core.autoslots import split_front_matter
from molehunt.core.template import parse_template
from molehunt.detect.tardos import (
    accuse,
    calibrate_threshold,
    false_accusation_rate,
    score_tardos_candidates,
)
from molehunt.game.tools import document_order_bits, read_registry
from molehunt.ui.ooxml_view import explore_docx, pretty_part

LAB_TOOLS = ("ooxml", "image_dots", "tardos", "notes")


def _page(tabs: QTabWidget, title: str) -> QVBoxLayout:
    page = QWidget()
    layout = QVBoxLayout(page)
    tabs.addTab(page, title)
    return layout


def build_lab_panels(owner, tabs: QTabWidget) -> None:
    """Add the four Lab sub-tabs to the Evidence tools tab widget."""
    ooxml = _page(tabs, "OOXML explorer")
    row = QHBoxLayout()
    for label, callback in (("Explore DOCX", owner._ooxml_explore),
                            ("Show selected part XML", owner._ooxml_part)):
        button = QPushButton(label)
        button.clicked.connect(callback)
        row.addWidget(button)
    owner.ooxml_parts = QComboBox()
    row.addWidget(owner.ooxml_parts, 1)
    ooxml.addLayout(row)
    owner.ooxml_summary = QTextEdit()
    owner.ooxml_summary.setReadOnly(True)
    owner.ooxml_xml = QTextEdit()
    owner.ooxml_xml.setReadOnly(True)
    ooxml.addWidget(owner.ooxml_summary)
    ooxml.addWidget(owner.ooxml_xml)

    dots = _page(tabs, "Image dots")
    row = QHBoxLayout()
    owner.dot_channel = QComboBox()
    owner.dot_channel.addItem("Blue channel (yellow dots)", "B")
    owner.dot_channel.addItem("Luminance (grey dots)", "L")
    row.addWidget(owner.dot_channel)
    button = QPushButton("Find grid, check parity, decode")
    button.clicked.connect(owner._dots_analyse)
    row.addWidget(button)
    dots.addLayout(row)
    owner.dot_result = QLabel("Load a PNG photo or scan in the Evidence file field.")
    owner.dot_result.setWordWrap(True)
    owner.dot_preview = QLabel()
    owner.dot_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
    dots.addWidget(owner.dot_result)
    dots.addWidget(owner.dot_preview, 1)

    tardos = _page(tabs, "Tardos scorer")
    button = QPushButton("Score candidates and simulate innocent scores")
    button.clicked.connect(owner._tardos_score)
    tardos.addWidget(button)
    owner.tardos_table = QTableWidget(0, 2)
    owner.tardos_table.setHorizontalHeaderLabels(["Candidate", "Tardos score"])
    owner.tardos_table.horizontalHeader().setStretchLastSection(True)
    tardos.addWidget(owner.tardos_table)
    owner.tardos_slider = QSlider(Qt.Orientation.Horizontal)
    owner.tardos_slider.setRange(0, 1000)
    owner.tardos_slider.valueChanged.connect(owner._tardos_threshold_moved)
    tardos.addWidget(owner.tardos_slider)
    owner.tardos_readout = QLabel("Threshold Z: -")
    tardos.addWidget(owner.tardos_readout)

    notes = _page(tabs, "Notes and findings")
    owner.notes_text = QTextEdit()
    owner.notes_text.setPlaceholderText("Examiner notes. Tag artefacts to cite them in the report.")
    notes.addWidget(owner.notes_text)
    row = QHBoxLayout()
    for label, callback in (("Tag current artefact", owner._notes_tag),
                            ("Save notes", owner._notes_save),
                            ("Report with notes", owner._notes_report)):
        button = QPushButton(label)
        button.clicked.connect(callback)
        row.addWidget(button)
    notes.addLayout(row)
    owner._tardos_state = None


def _dot_preview(path: Path, channel: str) -> tuple[str, bytes]:
    with Image.open(path) as image:
        scan = scan_dot_grid(image, channel=channel)
        upright = image.convert("RGB").rotate(-scan.angle, fillcolor="white")
    mask = Image.fromarray((~_dark_mask(upright, channel)).astype("uint8") * 255).convert("RGB")
    draw = ImageDraw.Draw(mask)
    x0, y0 = scan.origin
    draw.rectangle((x0, y0, x0 + COLUMNS * 6, y0 + ROWS * 6), outline="#D9822B", width=2)
    crop = mask.crop((max(0, x0 - 30), max(0, y0 - 30), x0 + COLUMNS * 6 + 30, y0 + ROWS * 6 + 30))
    buffer = BytesIO()
    crop.resize((crop.width * 4, crop.height * 4), Image.Resampling.NEAREST).save(buffer, "PNG")
    meta = scan.metadata
    text = (f"Printer {meta.printer_id}, printed {meta.printed_on.isoformat()}, minute "
            f"{meta.minute_of_day} ({meta.minute_of_day // 60:02d}:{meta.minute_of_day % 60:02d}). "
            f"Angle {scan.angle:+.2f} deg, grid origin {scan.origin}, parity "
            + ("valid" if scan.repaired_cell is None else f"repaired at cell {scan.repaired_cell}"))
    return text, buffer.getvalue()


def _tardos_inputs(evidence: Path, master: Path, roster: Path | None, key: Path | None):
    """Casebook mode uses the public Tardos registry; Lab mode uses the key."""
    registry = evidence.parent / "tardos_registry.csv"
    text = evidence.read_text(encoding="utf-8")
    if registry.is_file():
        codewords = {k: [int(b) for b in v] for k, v in read_registry(registry).items()}
        with (evidence.parent / "tardos_biases.csv").open(encoding="utf-8") as stream:
            biases = [float(row["bias"]) for row in csv.DictReader(stream)]
        template = parse_template(split_front_matter(master.read_text(encoding="utf-8"))[1])
        observed = document_order_bits(template, text)
        scores = score_tardos_candidates(observed, biases, codewords)
        return scores, calibrate_threshold(observed, biases, candidates=len(codewords))
    if roster is None or key is None:
        raise ValueError("Lab mode needs the roster and key from the analysis tab")
    from molehunt.cli_app import read_employee_ids, read_key

    result = analyze_collusion(master.read_text(encoding="utf-8"), read_key(key),
                               read_employee_ids(roster), text)
    return result.scores, result.calibration


class LabPanelActions:
    """Controller methods for the Lab panels."""

    def _lab_evidence(self) -> Path:
        return self._field_path("forensics", "evidence")

    def _ooxml_explore(self) -> None:
        try:
            report = explore_docx(self._lab_evidence())
        except (OSError, ValueError) as error:
            self.status.setText(f"OOXML error: {error}")
            return
        self.ooxml_parts.clear()
        self.ooxml_parts.addItems([name for name, _ in report.parts if name.endswith(".xml")])
        lines = [f"Parts: {len(report.parts)}"]
        lines += [f"core.{k} = {v!r}" for k, v in report.core.items()]
        lines += [f"app.{k} = {v!r}" for k, v in report.app.items() if k in {
            "Template", "TotalTime", "Application", "Company"}]
        lines += [f"custom.{k} = {v!r}" for k, v in report.custom.items()]
        lines.append(f"rsidRoot (settings.xml) = {report.rsid_root}")
        lines.append("settings rsids: " + ", ".join(report.settings_rsids[:20]))
        lines.append("rsids on content (value x uses): " + ", ".join(
            f"{value} x{count}" for value, count in report.content_rsids[:12]))
        lines.append(f"tracked changes: {len(report.tracked_changes)}")
        lines += [f"  {kind} by {author} at {date}: {text[:60]}"
                  for kind, author, date, text in report.tracked_changes]
        self.ooxml_summary.setPlainText("\n".join(lines))
        self.status.setText("OOXML explored; editable fields (core/app) rank below rsids.")

    def _ooxml_part(self) -> None:
        try:
            self.ooxml_xml.setPlainText(
                pretty_part(self._lab_evidence(), self.ooxml_parts.currentText()))
        except (OSError, ValueError, KeyError) as error:
            self.status.setText(f"OOXML error: {error}")

    def _dots_analyse(self) -> None:
        try:
            path, channel = self._lab_evidence(), self.dot_channel.currentData()
        except ValueError as error:
            self.status.setText(f"Dot analyzer error: {error}")
            return
        self._start_task(lambda: _dot_preview(path, channel), self._dots_render)

    def _dots_render(self, result: tuple[str, bytes]) -> None:
        text, png = result
        pixmap = QPixmap()
        pixmap.loadFromData(png)
        self.dot_preview.setPixmap(pixmap)
        self.dot_result.setText(text)
        self.status.setText("Dot grid decoded. A printer and time narrow a pool, not a person.")

    def _tardos_score(self) -> None:
        try:
            evidence = self._lab_evidence()
            master = self._field_path("analysis", "master")
            roster = Path(self.fields["analysis"]["employees"].text().strip() or ".")
            key = Path(self.fields["analysis"]["key"].text().strip() or ".")
        except ValueError as error:
            self.status.setText(f"Tardos error: {error}")
            return
        self._start_task(
            lambda: _tardos_inputs(evidence, master, roster if roster.is_file() else None,
                                   key if key.is_file() else None),
            self._tardos_render,
        )

    def _tardos_render(self, result) -> None:
        scores, calibration = result
        self._tardos_state = (scores, calibration)
        self.tardos_table.setRowCount(len(scores))
        for row, item in enumerate(scores):
            self.tardos_table.setItem(row, 0, QTableWidgetItem(item.candidate_id))
            self.tardos_table.setItem(row, 1, QTableWidgetItem(f"{item.score:.2f}"))
        high = max(scores[0].score, calibration.threshold) * 1.2
        self._tardos_range = (0.0, max(high, 1.0))
        self.tardos_slider.setValue(round(1000 * calibration.threshold / self._tardos_range[1]))
        self._tardos_threshold_moved(self.tardos_slider.value())

    def _tardos_threshold_moved(self, value: int) -> None:
        if self._tardos_state is None:
            return
        scores, calibration = self._tardos_state
        threshold = self._tardos_range[1] * value / 1000
        rate = false_accusation_rate(calibration, threshold)
        accused = ", ".join(accuse(scores, threshold)) or "none"
        self.tardos_readout.setText(
            f"Threshold Z = {threshold:.1f} (calibrated {calibration.threshold:.1f} for target "
            f"{calibration.target:g}). Estimated chance an innocent is accused: {rate:.4f}. "
            f"Accused: {accused}")

    def _notes_tag(self) -> None:
        stamp = datetime.now(UTC).isoformat(timespec="seconds")
        evidence = self.fields["forensics"]["evidence"].text().strip() or "(no file)"
        pins = self.timeline_pins.toPlainText().strip().splitlines()
        tag = f"- [{stamp}] {evidence} @ byte {self.hex_offset.value()}"
        if pins:
            tag += f"; pinned: {pins[-1]}"
        self.notes_text.append(tag)

    def _notes_path(self) -> Path:
        case = self.case_instance.definition.case_id if self.case_instance else "lab"
        return Path(".molehunt") / "notes" / f"{case}.md"

    def _notes_save(self) -> None:
        path = self._notes_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.notes_text.toPlainText(), encoding="utf-8")
        self.status.setText(f"Notes saved: {path}")

    def _notes_report(self) -> None:
        self._report_notes = tuple(
            line for line in self.notes_text.toPlainText().splitlines() if line.strip())
        self._write_report()
