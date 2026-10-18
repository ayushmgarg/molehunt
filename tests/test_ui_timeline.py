"""Workbench tests for filtering and pinning normalized timeline events."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

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
    QTimer.singleShot(10000, loop.quit)
    loop.exec()
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
