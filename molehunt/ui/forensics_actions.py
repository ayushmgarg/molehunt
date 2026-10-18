"""Evidence tree and interactive byte/Unicode inspection actions for the workbench."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import QTableWidgetItem

from molehunt.detect.ingest import IngestedEvidence, ingest
from molehunt.ui.forensics import (
    ByteInspection,
    InvisibleCharacter,
    format_hex_rows,
    inspect_byte,
    invisible_characters,
)

# Revealer bit mapping (SPEC C1/C2): which hidden character means what.
BIT_MEANING = {
    "\u200b": "C1 bit 0", "\u200c": "C1 bit 1", "\u200d": "decoy", "\u2060": "decoy",
    "\u00a0": "C2 nbsp bit 0", "\u202f": "C2 nbsp bit 1",
}


@dataclass(frozen=True, slots=True)
class EvidenceRow:
    """Registry fields displayed in the evidence tree."""

    evidence_id: str
    case_id: str
    sha256: str
    intake_ts: str
    original_path: str
    working_path: str


@dataclass(frozen=True, slots=True)
class InspectionBundle:
    """Read-only evidence metadata, a bounded hex page, and Unicode findings."""

    evidence: IngestedEvidence
    raw: bytes
    hex_rows: tuple[tuple[int, str, str], ...]
    hidden: tuple[InvisibleCharacter, ...]
    selected: ByteInspection


def _list_evidence(database: Path) -> tuple[EvidenceRow, ...]:
    """Read evidence registry rows in intake order without modifying the database."""
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT id, case_id, sha256, intake_ts, path, working_copy_path "
            "FROM evidence ORDER BY intake_ts, id"
        ).fetchall()
    return tuple(EvidenceRow(*row) for row in rows)


def _inspect_inputs(path: Path, byte_offset: int) -> InspectionBundle:
    """Load one evidence artifact and calculate its requested 256-byte hex page."""
    evidence = ingest(path)
    raw = path.read_bytes()
    if not raw:
        raise ValueError("evidence file is empty")
    if not 0 <= byte_offset < len(raw):
        raise ValueError(f"byte offset must be between 0 and {len(raw) - 1}")
    page = raw[byte_offset : byte_offset + 256]
    rows = format_hex_rows(page, start_offset=byte_offset)
    hidden = invisible_characters(evidence.text) if evidence.text is not None else ()
    selected = inspect_byte(raw, byte_offset)
    return InspectionBundle(evidence, raw, rows, hidden, selected)


class ForensicsActions:
    """Controller methods called by the Evidence tools tab."""

    _forensic_view: InspectionBundle | None = None

    def _evidence_refresh(self) -> None:
        try:
            database = self._field_path("forensics", "database")
            self._start_task(lambda: _list_evidence(database), self._render_evidence_tree)
        except (OSError, ValueError, sqlite3.Error) as error:
            self.status.setText(f"Evidence tree error: {error}")

    def _render_evidence_tree(self, rows: tuple[EvidenceRow, ...]) -> None:
        self.evidence_tree.setRowCount(len(rows))
        for row_index, evidence in enumerate(rows):
            values = (
                evidence.evidence_id,
                evidence.case_id,
                evidence.sha256,
                evidence.intake_ts,
                evidence.original_path,
                evidence.working_path,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self.evidence_tree.setItem(row_index, column, item)
        self.status.setText(f"Evidence tree loaded: {len(rows)} item(s)")

    def _evidence_tree_selected(self, row: int, _column: int) -> None:
        item = self.evidence_tree.item(row, 5)
        if item is not None:
            self.fields["forensics"]["evidence"].setText(item.text())

    def _forensics_inspect(self) -> None:
        try:
            path = self._field_path("forensics", "evidence")
            offset = self.hex_offset.value()
            self._start_task(
                lambda: _inspect_inputs(path, offset), self._render_inspection
            )
        except (OSError, ValueError) as error:
            self.status.setText(f"Inspection error: {error}")

    def _render_inspection(self, bundle: InspectionBundle) -> None:
        self._forensic_view = bundle
        self.hex_offset.setMaximum(max(0, len(bundle.raw) - 1))
        self.hex_table.setRowCount(len(bundle.hex_rows))
        for row_index, (offset, hexadecimal, ascii_text) in enumerate(bundle.hex_rows):
            self.hex_table.setItem(row_index, 0, QTableWidgetItem(str(offset)))
            byte_values = hexadecimal.split()
            for column in range(16):
                value = byte_values[column] if column < len(byte_values) else ""
                self.hex_table.setItem(row_index, column + 1, QTableWidgetItem(value))
            self.hex_table.setItem(row_index, 17, QTableWidgetItem(ascii_text))
        self.invisible_table.setRowCount(len(bundle.hidden))
        for row_index, item in enumerate(bundle.hidden):
            values = (
                str(item.character_offset),
                item.codepoint,
                item.name,
                item.category,
                " ".join(f"{byte:02X}" for byte in item.utf8_bytes),
                BIT_MEANING.get(item.character, "-"),
            )
            for column, value in enumerate(values):
                self.invisible_table.setItem(row_index, column, QTableWidgetItem(value))
        bits = "".join(
            BIT_MEANING[item.character][-1] for item in bundle.hidden
            if BIT_MEANING.get(item.character, "").startswith("C1 bit")
        )
        self.invisible_bits.setText(
            f"C1 bit string (reading order, decoys skipped): {bits or '-'} ({len(bits)} bits)"
        )
        self._render_byte_detail(bundle.selected)
        self.status.setText(
            f"Inspected {bundle.evidence.format}: {bundle.evidence.size_bytes} bytes; "
            f"SHA-256 {bundle.evidence.sha256}"
        )

    def _hex_byte_selected(self, row: int, column: int) -> None:
        if column < 1 or column > 16 or self._forensic_view is None:
            return
        offset_item = self.hex_table.item(row, 0)
        byte_item = self.hex_table.item(row, column)
        if offset_item is None or byte_item is None or not byte_item.text():
            return
        offset = int(offset_item.text()) + column - 1
        self._render_byte_detail(inspect_byte(self._forensic_view.raw, offset))

    def _render_byte_detail(self, item: ByteInspection) -> None:
        sequence = " ".join(f"{byte:02X}" for byte in item.utf8_bytes)
        if item.codepoint is None:
            description = "invalid UTF-8 byte; no character assigned"
        else:
            description = (
                f"character {item.character!r}, {item.codepoint}, "
                f"character offset {item.character_offset}"
            )
        self.byte_detail.setText(
            f"Byte {item.byte_offset}: 0x{item.byte_value:02X}; UTF-8 sequence {sequence}; {description}"
        )
