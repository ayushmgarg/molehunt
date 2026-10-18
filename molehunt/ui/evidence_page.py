"""Evidence tools tab: registry tree, hex viewer, invisible-character revealer,
master diff, timeline, and the Lab panels (OOXML, image dots, Tardos, notes),
arranged as sub-tabs so each tool gets the full window height."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def _table(columns: list[str]) -> QTableWidget:
    table = QTableWidget(0, len(columns))
    table.setHorizontalHeaderLabels(columns)
    table.horizontalHeader().setStretchLastSection(True)
    return table


def _sub_page(tabs: QTabWidget, title: str) -> QVBoxLayout:
    page = QWidget()
    layout = QVBoxLayout(page)
    tabs.addTab(page, title)
    return layout


def _bytes_page(owner, layout: QVBoxLayout) -> None:
    owner.evidence_tree = _table(
        ["Evidence ID", "Case", "SHA-256", "Intake UTC", "Original", "Working copy"]
    )
    owner.evidence_tree.setMaximumHeight(150)
    owner.evidence_tree.cellClicked.connect(owner._evidence_tree_selected)
    layout.addWidget(owner.evidence_tree)
    offset_row = QHBoxLayout()
    offset_row.addWidget(QLabel("Byte offset"))
    owner.hex_offset = QSpinBox()
    owner.hex_offset.setRange(0, 2_147_483_647)
    offset_row.addWidget(owner.hex_offset)
    offset_row.addWidget(QLabel("Select a hex byte to inspect its UTF-8 scalar."))
    layout.addLayout(offset_row)
    owner.hex_table = _table(["Offset", *(f"{index:02X}" for index in range(16)), "ASCII"])
    owner.hex_table.cellClicked.connect(owner._hex_byte_selected)
    layout.addWidget(owner.hex_table)
    owner.byte_detail = QLabel("Select a byte to show its decoded character, if valid UTF-8.")
    layout.addWidget(owner.byte_detail)
    owner.invisible_label = QLabel("Non-printing characters in decoded text (UV view)")
    owner.invisible_table = _table(
        ["Character offset", "Code point", "Unicode name", "Category", "UTF-8 bytes", "Bit"]
    )
    layout.addWidget(owner.invisible_label)
    layout.addWidget(owner.invisible_table)
    owner.invisible_bits = QLabel("Bit string (reading order): -")
    owner.invisible_bits.setWordWrap(True)
    layout.addWidget(owner.invisible_bits)


def build_evidence_page(owner, tabs: QTabWidget) -> None:
    """Build the Evidence tools tab and expose its widgets on ``owner``."""
    from molehunt.ui.lab_panels import build_lab_panels
    from molehunt.ui.pages import _add_field, _form_page

    forensic, form, fields = _form_page(owner, "forensics")
    _add_field(form, fields, "database", "SQLite registry", ".molehunt/molehunt.sqlite3")
    _add_field(form, fields, "evidence", "Evidence file", "")
    _add_field(form, fields, "timeline_paths", "Timestamped timeline CSVs (; separated)", "")
    owner.timeline_paths = fields["timeline_paths"]
    actions = QHBoxLayout()
    for attribute, label, callback in (
        ("evidence_refresh_button", "Refresh evidence tree", owner._evidence_refresh),
        ("inspect_evidence_button", "Inspect selected file", owner._forensics_inspect),
        ("diff_evidence_button", "Diff against selected master", owner._diff),
    ):
        button = QPushButton(label)
        button.clicked.connect(callback)
        setattr(owner, attribute, button)
        actions.addWidget(button)
    form.addRow("", actions)
    owner.evidence_tabs = QTabWidget()
    forensic.layout().addWidget(owner.evidence_tabs, 1)
    _bytes_page(owner, _sub_page(owner.evidence_tabs, "Bytes and invisibles"))

    diff = _sub_page(owner.evidence_tabs, "Diff vs master")
    owner.diff_label = QLabel("Master diff; variation slots render as variant A.")
    owner.diff_table = _table(["Change", "Master", "Evidence"])
    owner.diff_variations = QTextEdit()
    owner.diff_variations.setReadOnly(True)
    owner.diff_variations.setMaximumHeight(120)
    for widget in (owner.diff_label, owner.diff_table, owner.diff_variations):
        diff.addWidget(widget)

    timeline = _sub_page(owner.evidence_tabs, "Timeline")
    row = QHBoxLayout()
    owner.timeline_load_button = QPushButton("Load timeline")
    owner.timeline_load_button.clicked.connect(owner._timeline_load)
    row.addWidget(owner.timeline_load_button)
    row.addWidget(QLabel("Filter events"))
    owner.timeline_filter = QLineEdit()
    owner.timeline_filter.textChanged.connect(owner._timeline_filter)
    row.addWidget(owner.timeline_filter, 1)
    owner.timeline_pin_button = QPushButton("Pin selected event")
    owner.timeline_pin_button.clicked.connect(owner._timeline_pin_selected)
    row.addWidget(owner.timeline_pin_button)
    timeline.addLayout(row)
    owner.timeline_table = _table(["Timestamp UTC", "Employee", "Event", "Device", "Printer",
                                   "Source"])
    owner.timeline_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    timeline.addWidget(owner.timeline_table)
    owner.timeline_pins = QTextEdit()
    owner.timeline_pins.setReadOnly(True)
    owner.timeline_pins.setMaximumHeight(100)
    timeline.addWidget(QLabel("Pinned timeline findings"))
    timeline.addWidget(owner.timeline_pins)

    build_lab_panels(owner, owner.evidence_tabs)
    tabs.addTab(forensic, "Evidence tools")
