"""Workbench tests for filtering and pinning normalized timeline events."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from molehunt.game.timeline import load_timeline
from molehunt.ui.app import MoleHuntWindow


def test_workbench_loads_filters_and_pins_timeline_events(tmp_path) -> None:
    application = QApplication.instance() or QApplication([])
    source = tmp_path / "events.csv"
    source.write_text(
        "timestamp,employee_id,event,device_id,printer_id\n"
        "2025-01-01T09:15:00Z,E001,badge_entry,PRN-004,4\n"
        "2025-01-01T09:42:00Z,E001,document_open,PRN-004,4\n"
        "2025-01-01T10:00:00Z,E001,print_job,PRN-004,4\n",
        encoding="utf-8",
    )
    window = MoleHuntWindow()
    window.timeline_paths.setText(str(source))

    window._timeline_load()
    thread = window._thread
    assert thread is not None
    loop = QEventLoop()
    thread.finished.connect(loop.quit)
    guard = QTimer()
    guard.setSingleShot(True)
    guard.timeout.connect(loop.quit)
    guard.start(10000)
    loop.exec()
    guard.stop()
    application.processEvents()
    assert window._thread is None
    assert window.timeline_table.rowCount() == 3
    assert window.timeline_table.item(2, 2).text() == "print_job"

    window.timeline_filter.setText("print")
    assert window.timeline_table.rowCount() == 1
    window.timeline_table.selectRow(0)
    window._timeline_pin_selected()
    assert "print_job" in window.timeline_pins.toPlainText()

    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    application.processEvents()


def test_brush_selection_reports_window_and_pins_all(tmp_path) -> None:
    from PySide6.QtCore import QItemSelectionModel

    application = QApplication.instance() or QApplication([])
    window = MoleHuntWindow()
    log = tmp_path / "events.csv"
    log.write_text(
        "timestamp,employee_id,event\n2025-01-01T01:50:00,E002,badge_entry\n"
        "2025-01-01T02:13:00,E001,login\n2025-01-01T02:14:00,E001,download\n",
        encoding="utf-8",
    )
    window._timeline_loaded(load_timeline([log]))
    model = window.timeline_table.selectionModel()
    flags = QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows
    for row in (0, 2):
        model.select(window.timeline_table.model().index(row, 0), flags)
    assert "2025-01-01 01:50 to 02:14 UTC, 2 events, 24 min" in window.timeline_window.text()
    window._timeline_pin_selected()
    assert window.timeline_pins.toPlainText().count("\n") == 1
    window.close()
    application.processEvents()
