"""Smoke tests for the native PySide6 workbench shell."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

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
