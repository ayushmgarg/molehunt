"""Shared test hygiene: destroy Qt windows between tests, not at a random GC time."""

import gc

import pytest


@pytest.fixture(autouse=True)
def _flush_qt_objects():
    yield
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        return
    application = QApplication.instance()
    if application is None:
        return
    for widget in QApplication.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    QApplication.sendPostedEvents(None, 0)
    application.processEvents()
    gc.collect()
    QApplication.sendPostedEvents(None, 0)
    application.processEvents()
