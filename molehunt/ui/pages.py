"""Construct the compact PySide6 workbench forms and evidence table."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
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

from molehunt.ui.evidence_page import build_evidence_page
from molehunt.ui.redteam_panel import build_redteam_panel

_STYLE = """
QMainWindow, QWidget { background: #14171A; color: #EFE9DC; font-family: "Segoe UI", Arial, sans-serif; font-size: 14px; }
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
    browse.clicked.connect(
        lambda: _browse(
            field,
            key in {"output", "report", "database"},
            directory=key == "output_root",
        )
    )
    layout.addWidget(browse)
    form.addRow(label, row)

def _browse(field: QLineEdit, save: bool = False, *, directory: bool = False) -> None:
    if directory:
        path = QFileDialog.getExistingDirectory(None, "Choose case output folder")
    elif save:
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
    owner.tabs = tabs
    analysis, form, fields = _form_page(owner, "analysis")
    for key, label, default in (
        ("evidence", "Evidence", ""), ("master", "Master template", ""),
        ("employees", "Synthetic roster", ""), ("key", "Secret key", ".molehunt/master.key"),
        ("logs", "Optional fusion CSV logs", ""),
        ("report", "Optional DOCX or PDF report", ""),
    ):
        _add_field(form, fields, key, label, default)
    run = QPushButton("Run analysis")
    owner.run_analysis_button = run
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
    owner.fusion_results = QTableWidget(0, 4)
    owner.fusion_results.setHorizontalHeaderLabels(
        ["Candidate", "Prior", "Posterior", "Access and event evidence"]
    )
    owner.fusion_results.horizontalHeader().setStretchLastSection(True)
    owner.fusion_results.setVisible(False)
    analysis.layout().addWidget(owner.fusion_results)
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
            (("master", "Master template to register", ""), ("master_id", "Registered master ID", ""),
             ("database", "SQLite registry", ".molehunt/molehunt.sqlite3"),
             ("employee", "Synthetic employee ID", ""),
             ("key", "Secret key", ".molehunt/master.key"),
             ("output", "Copy output (.txt, .md, .docx)", "")),
            "Issue registered copy", owner._issue,
        ),
        (
            "intake", "Intake and custody",
            (("evidence", "Evidence file", ""), ("case_id", "Case ID", ""),
             ("actor", "Synthetic examiner ID", ""), ("root", "Case storage root", "evidence"),
             ("database", "SQLite registry", ".molehunt/molehunt.sqlite3"),
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
        if name == "issue":
            register = QPushButton("Register master")
            register.clicked.connect(owner._register)
            form.addRow("", register)
        elif name == "intake":
            verify = QPushButton("Verify custody log")
            verify.clicked.connect(owner._verify)
            form.addRow("", verify)
        elif name == "bench":
            page.layout().addWidget(QLabel("Seeded transforms; output includes CSV and PNG plots."))
            build_redteam_panel(owner, page.layout())
        tabs.addTab(page, title)

    casebook, case_form, case_fields = _form_page(owner, "casebook")
    owner.casebook_lock = QCheckBox("Casebook mode: restrict tools to earned unlocks")
    owner.casebook_lock.setChecked(False)
    owner.casebook_lock.toggled.connect(owner._apply_tool_locks)
    case_form.addRow("", owner.casebook_lock)
    case_fields["player"] = QLineEdit("player-01")
    case_form.addRow("Synthetic player ID", case_fields["player"])
    _add_field(case_form, case_fields, "database", "SQLite registry", ".molehunt/molehunt.sqlite3")
    _add_field(case_form, case_fields, "output_root", "Generated cases folder", ".molehunt/cases")
    owner.case_selector = QComboBox()
    for definition in owner.case_definitions:
        owner.case_selector.addItem(f"{definition.case_id} · {definition.title}", definition.case_id)
    case_form.addRow("Case", owner.case_selector)
    case_fields["seed"] = QLineEdit("0")
    case_form.addRow("Base seed", case_fields["seed"])
    case_buttons = QHBoxLayout()
    for label, callback in (
        ("Refresh progress", owner._casebook_refresh),
        ("Start / generate", owner._casebook_start),
        ("Use next hint", owner._casebook_hint),
    ):
        button = QPushButton(label)
        button.clicked.connect(callback)
        case_buttons.addWidget(button)
    case_form.addRow("", case_buttons)
    owner.case_details = QTextEdit()
    owner.case_details.setReadOnly(True)
    owner.case_details.setMinimumHeight(170)
    casebook.layout().addWidget(owner.case_details)
    answer_row = QHBoxLayout()
    case_fields["answer"] = QLineEdit()
    case_fields["answer"].setPlaceholderText("Candidate ID, printer ID, or comma-separated colluders")
    answer_row.addWidget(case_fields["answer"], 1)
    owner.case_confidence = QDoubleSpinBox()
    owner.case_confidence.setRange(0.0, 1.0)
    owner.case_confidence.setSingleStep(0.05)
    owner.case_confidence.setValue(0.8)
    owner.case_confidence.setPrefix("Confidence ")
    answer_row.addWidget(owner.case_confidence)
    submit = QPushButton("Submit answer")
    submit.clicked.connect(owner._casebook_submit)
    answer_row.addWidget(submit)
    casebook.layout().addLayout(answer_row)
    case_fields["details"] = QLineEdit()
    case_fields["details"].setPlaceholderText(
        "Evidence details: bits=0101...; erased=3,7; pool=E001,E004; ranking=rsid,...; "
        "tied=E002,E005; actor=E003; alternative=...")
    casebook.layout().addWidget(case_fields["details"])
    owner.case_selector.currentIndexChanged.connect(owner._casebook_show_selected)
    tabs.addTab(casebook, "Casebook")

    build_evidence_page(owner, tabs)
    owner._casebook_show_selected()
    tabs.setStyleSheet(_STYLE)
    return tabs
