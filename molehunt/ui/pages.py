"""Construct the compact PySide6 workbench forms and evidence table."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

_STYLE = """
QMainWindow, QWidget { background: #14171A; color: #EFE9DC; font-size: 14px; }
QTabWidget::pane { border: 1px solid #3A4048; background: #1B1F24; }
QTabBar::tab { background: #3A4048; padding: 10px 18px; margin-right: 2px; }
QTabBar::tab:selected { background: #D9822B; color: #1B1F24; }
QLineEdit, QTextEdit, QTableWidget { background: #EFE9DC; color: #1B1F24; border: 1px solid #3A4048; padding: 6px; }
QPushButton { background: #D9822B; color: #1B1F24; border: 0; padding: 9px 14px; font-weight: bold; }
QPushButton:focus, QLineEdit:focus { outline: 2px solid #EFE9DC; }
QLabel#status { padding: 8px; color: #D9822B; }
"""


def _add_field(form: QFormLayout, fields: dict[str, QLineEdit], key: str, label: str, default: str = "") -> None:
    field = QLineEdit(default)
    fields[key] = field
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(field, 1)
    browse = QPushButton("Browse")
    browse.clicked.connect(lambda: _browse(field, key in {"output", "report"}))
    layout.addWidget(browse)
    form.addRow(label, row)


def _browse(field: QLineEdit, save: bool = False) -> None:
    if save:
        path, _ = QFileDialog.getSaveFileName(None, "Choose output")
    else:
        path, _ = QFileDialog.getOpenFileName(None, "Choose file")
    if path:
        field.setText(path)


def _form_page(owner, name: str) -> tuple[QWidget, QFormLayout, dict[str, QLineEdit]]:
    page = QWidget()
    layout = QVBoxLayout(page)
    form = QFormLayout()
    form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
    fields: dict[str, QLineEdit] = {}
    owner.fields[name] = fields
    layout.addLayout(form)
    return page, form, fields


def build_pages(owner) -> QTabWidget:
    """Build tabs and expose their widgets on the window controller."""
    tabs = QTabWidget()
    analysis, form, fields = _form_page(owner, "analysis")
    for key, label, default in (
        ("evidence", "Evidence", ""), ("master", "Master template", ""),
        ("employees", "Synthetic roster", ""), ("key", "Secret key", ".molehunt/master.key"),
        ("report", "Optional DOCX report", ""),
    ):
        _add_field(form, fields, key, label, default)
    run = QPushButton("Run analysis")
    run.clicked.connect(owner._analyze)
    export = QPushButton("Write report")
    export.clicked.connect(owner._write_report)
    actions = QHBoxLayout()
    actions.addWidget(run)
    actions.addWidget(export)
    form.addRow("", actions)
    owner.results = QTableWidget(0, 6)
    owner.results.setHorizontalHeaderLabels(
        ["Candidate", "Matches", "Observed", "Match fraction", "P(null)", "log10 LR"]
    )
    owner.results.horizontalHeader().setStretchLastSection(True)
    analysis.layout().addWidget(owner.results)
    owner.slot_matrix = QTableWidget(0, 1)
    owner.slot_matrix.setHorizontalHeaderLabels(["Candidate"])
    owner.slot_matrix.setMinimumHeight(220)
    analysis.layout().addWidget(QLabel("Slot matrix: ○ match   × mismatch   — erasure"))
    analysis.layout().addWidget(owner.slot_matrix)
    owner.analysis_detail = QTextEdit()
    owner.analysis_detail.setReadOnly(True)
    owner.analysis_detail.setMaximumHeight(110)
    analysis.layout().addWidget(owner.analysis_detail)
    tabs.addTab(analysis, "Evidence analysis")

    for name, title, specs, button_text, callback in (
        (
            "issue", "Issue copy",
            (("master", "Master template", ""), ("employee", "Synthetic employee ID", ""),
             ("key", "Secret key", ".molehunt/master.key"),
             ("output", "Copy output (.txt, .md, .docx)", "")),
            "Issue fingerprinted copy", owner._issue,
        ),
        (
            "intake", "Intake and custody",
            (("evidence", "Evidence file", ""), ("case_id", "Case ID", ""),
             ("actor", "Synthetic examiner ID", ""), ("root", "Case storage root", "evidence"),
             ("ledger", "Custody log to verify", "")),
            "Intake evidence", owner._intake,
        ),
        (
            "bench", "Red Team bench",
            (("master", "Master template", ""), ("employees", "Synthetic roster", ""),
             ("key", "Secret key", ".molehunt/master.key"), ("output", "Output directory", "bench")),
            "Run A1, A3, A8 benchmark", owner._bench,
        ),
    ):
        page, form, fields = _form_page(owner, name)
        for key, label, default in specs:
            _add_field(form, fields, key, label, default)
        button = QPushButton(button_text)
        button.clicked.connect(callback)
        form.addRow("", button)
        if name == "intake":
            verify = QPushButton("Verify custody log")
            verify.clicked.connect(owner._verify)
            form.addRow("", verify)
        elif name == "bench":
            page.layout().addWidget(QLabel("Seeded transforms; output includes CSV and PNG plots."))
        tabs.addTab(page, title)
    tabs.setStyleSheet(_STYLE)
    return tabs
