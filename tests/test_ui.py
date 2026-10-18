"""Smoke tests for the native PySide6 workbench shell."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from molehunt.core.codes import generate_codeword
from molehunt.core.render import render_text
from molehunt.core.slots import allocate_slots
from molehunt.core.template import parse_template
from molehunt.ui.app import MoleHuntWindow


def test_workbench_builds_engine_tabs() -> None:
    application = QApplication.instance() or QApplication([])
    window = MoleHuntWindow()
    tabs = window.centralWidget()
    assert window.windowTitle() == "MoleHunt | Forensic Desk"
    assert tabs.count() == 4
    assert [tabs.tabText(index) for index in range(tabs.count())] == [
        "Evidence analysis", "Issue copy", "Intake and custody", "Red Team bench"
    ]
    window.close()
    application.processEvents()


def test_workbench_analysis_populates_candidate_slot_matrix(tmp_path) -> None:
    application = QApplication.instance() or QApplication([])
    key = bytes(range(32))
    master_path = tmp_path / "master.md"
    master_path.write_text(
        "\n".join(f"Record {index:02}: {{{{lex:begin|start}}}}." for index in range(64)),
        encoding="utf-8",
    )
    template = parse_template(master_path.read_text(encoding="utf-8"))
    slots = allocate_slots(template, key)
    evidence_path = tmp_path / "leak.txt"
    evidence_path.write_text(
        render_text(template, slots, generate_codeword(key, "E002", len(slots))),
        encoding="utf-8",
    )
    roster_path = tmp_path / "employees.csv"
    roster_path.write_text("id\nE001\nE002\nE003\n", encoding="utf-8")
    key_path = tmp_path / "key"
    key_path.write_bytes(key)

    window = MoleHuntWindow()
    fields = window.fields["analysis"]
    fields["evidence"].setText(str(evidence_path))
    fields["master"].setText(str(master_path))
    fields["employees"].setText(str(roster_path))
    fields["key"].setText(str(key_path))
    window._analyze()

    assert window.status.text().startswith("Analysis complete")
    assert window.slot_matrix.columnCount() == 65
    assert window.slot_matrix.rowCount() == 3
    assert window.slot_matrix.item(0, 0).text() == "E002"
    symbols = {
        window.slot_matrix.item(0, column).text()
        for column in range(1, window.slot_matrix.columnCount())
    }
    assert symbols == {"○"}
    window.close()
    application.processEvents()
