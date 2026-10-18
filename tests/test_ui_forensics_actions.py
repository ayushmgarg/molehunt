"""Integration tests for evidence tree and byte/Unicode workbench tools."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from molehunt.intake_service import intake_case
from molehunt.ui.app import MoleHuntWindow


def _finish(window: MoleHuntWindow, application: QApplication) -> None:
    thread = window._thread
    assert thread is not None
    loop = QEventLoop()
    thread.finished.connect(loop.quit)
    QTimer.singleShot(10000, loop.quit)
    loop.exec()
    application.processEvents()
    assert window._thread is None


def test_evidence_tools_inspect_bytes_and_list_registry(tmp_path) -> None:
    application = QApplication.instance() or QApplication([])
    source = tmp_path / "sample.txt"
    source.write_text("Aé\u200bB", encoding="utf-8")
    database = tmp_path / "registry.sqlite3"
    registered = intake_case(
        source,
        "C-TEST",
        actor="examiner-01",
        root=tmp_path / "evidence",
        database=database,
    )
    window = MoleHuntWindow()
    fields = window.fields["forensics"]
    fields["database"].setText(str(database))
    fields["evidence"].setText(str(registered.intake.working_copy))

    window._evidence_refresh()
    _finish(window, application)
    assert window.evidence_tree.rowCount() == 1
    assert window.evidence_tree.item(0, 0).text() == registered.evidence_id

    window._forensics_inspect()
    _finish(window, application)
    assert window.hex_table.rowCount() == 1
    assert window.invisible_table.rowCount() == 1
    assert window.invisible_table.item(0, 1).text() == "U+200B"

    # Byte offset 2 is the continuation byte of UTF-8 `é`.
    window.hex_offset.setValue(2)
    window._hex_byte_selected(0, 3)
    assert "U+00E9" in window.byte_detail.text()
    window.close()
    application.processEvents()
