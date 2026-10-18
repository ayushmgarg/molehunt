"""Tests for master-to-evidence diff rows and authored variation overlays."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from molehunt.ui.app import MoleHuntWindow
from molehunt.ui.diff_actions import compare_master


def test_diff_normalizes_variation_markers_and_shows_a_b_choices() -> None:
    comparison = compare_master(
        "Title\nThe {{lex:begin|start}} here.\nKeep this.",
        "Title\nThe start here.\nKeep this.\nAdded line.",
    )

    assert comparison.variations == ((1, "lex", "begin", "start"),)
    assert any(
        row.kind == "replace"
        and row.master == "The begin here."
        and row.evidence == "The start here."
        for row in comparison.rows
    )
    assert comparison.rows[-1].kind == "insert"
    assert comparison.rows[-1].evidence == "Added line."


def test_diff_reports_deleted_and_replaced_lines() -> None:
    comparison = compare_master("A\nB\nC", "A\nnew\nC")

    assert [(row.kind, row.master, row.evidence) for row in comparison.rows] == [
        ("equal", "A", "A"),
        ("replace", "B", "new"),
        ("equal", "C", "C"),
    ]


def test_workbench_renders_diff_and_variation_slots(tmp_path) -> None:
    application = QApplication.instance() or QApplication([])
    master = tmp_path / "master.md"
    master.write_text("A {{lex:begin|start}}.\nB.", encoding="utf-8")
    evidence = tmp_path / "leak.txt"
    evidence.write_text("A start.\nB.\nC.", encoding="utf-8")
    window = MoleHuntWindow()
    window.fields["analysis"]["master"].setText(str(master))
    window.fields["analysis"]["evidence"].setText(str(evidence))

    window._diff()
    thread = window._thread
    assert thread is not None
    loop = QEventLoop()
    thread.finished.connect(loop.quit)
    QTimer.singleShot(10000, loop.quit)
    loop.exec()
    application.processEvents()

    assert window.diff_table.rowCount() == 3
    assert "Slot 1 (lex): A='begin' | B='start'" in window.diff_variations.toPlainText()
    window.close()
    application.processEvents()
