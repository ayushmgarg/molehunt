"""Offscreen tests for the Lab panels and the Red Team boss panel."""

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QThread, QTimer
from PySide6.QtWidgets import QApplication

from molehunt.game.casebook import load_casebook
from molehunt.game.generator import generate_case
from molehunt.ui.app import MoleHuntWindow

CASES = {definition.generator: definition for definition in load_casebook()}


def _wait(window: MoleHuntWindow, application: QApplication) -> None:
    thread = window._thread
    assert thread is not None
    done = QEventLoop()
    thread.finished.connect(done.quit)
    guard = QTimer()
    guard.setSingleShot(True)
    guard.timeout.connect(done.quit)
    guard.start(60000)
    done.exec()
    guard.stop()
    for _ in range(200):
        application.processEvents()
        if window._thread is None:
            break
        QThread.msleep(25)
    assert window._thread is None


def _dispose(window: MoleHuntWindow, application: QApplication) -> None:
    """Close and delete the window now so no queued signal reaches it later."""
    window.close()
    window.deleteLater()
    application.sendPostedEvents(None, 0)
    application.processEvents()


def test_lab_panels_explore_docx_decode_dots_and_score_tardos(tmp_path) -> None:
    application = QApplication.instance() or QApplication([])
    window = MoleHuntWindow()
    c4 = generate_case(CASES["ooxml_metadata"], tmp_path / "c4", seed=2,
                       master_path="data/demo/master.md")
    window.fields["forensics"]["evidence"].setText(str(c4.evidence_path))
    window._ooxml_explore()
    truth = json.loads(c4.ground_truth_path.read_text(encoding="utf-8"))
    assert f"core.lastModifiedBy = '{truth['decoy_last_modified_by']}'" in (
        window.ooxml_summary.toPlainText())
    window.ooxml_parts.setCurrentText("word/settings.xml")
    window._ooxml_part()
    assert "rsidRoot" in window.ooxml_xml.toPlainText()

    c3 = generate_case(CASES["print_timeline"], tmp_path / "c3", seed=2,
                       master_path="data/demo/master.md")
    window.fields["forensics"]["evidence"].setText(str(c3.public_dir / "photo.png"))
    window._dots_analyse()
    _wait(window, application)
    truth = json.loads(c3.ground_truth_path.read_text(encoding="utf-8"))
    assert f"Printer {truth['printer_id']}, printed {truth['printed_on']}" in (
        window.dot_result.text())
    assert not window.dot_preview.pixmap().isNull()

    c6 = generate_case(CASES["collusion"], tmp_path / "c6", seed=2)
    window.fields["forensics"]["evidence"].setText(str(c6.evidence_path))
    window.fields["analysis"]["master"].setText(str(c6.master_path))
    window._tardos_score()
    _wait(window, application)
    truth = json.loads(c6.ground_truth_path.read_text(encoding="utf-8"))
    top_two = {window.tardos_table.item(row, 0).text() for row in (0, 1)}
    assert top_two == set(truth["colluders"])
    second = float(window.tardos_table.item(1, 1).text())
    window.tardos_slider.setValue(int(1000 * (second - 0.5) / window._tardos_range[1]))
    readout = window.tardos_readout.text()
    assert all(item in readout.split("Accused:")[1] for item in truth["colluders"])
    window.tardos_slider.setValue(0)
    assert "Estimated chance an innocent is accused: 0.99" in window.tardos_readout.text()

    window._notes_tag()
    assert str(c6.evidence_path) in window.notes_text.toPlainText()
    _dispose(window, application)


def test_redteam_panel_scores_attempt_and_fills_leaderboard(tmp_path) -> None:
    application = QApplication.instance() or QApplication([])
    window = MoleHuntWindow()
    window.fields["casebook"]["database"].setText(str(tmp_path / "r.sqlite3"))
    window.redteam_player.setText("panel-mole")
    window.redteam_tools["strip"][0].setChecked(True)
    window.redteam_tools["collapse"][0].setChecked(True)
    from molehunt.ui.redteam_panel import DEFAULT_MASTER, _attempt

    steps = [(name, box[1].value()) for name, box in window.redteam_tools.items()
             if box[0].isChecked()]
    window._redteam_render(_attempt(DEFAULT_MASTER, 0, steps, [], tmp_path / "r.sqlite3",
                                    "panel-mole"))
    assert window.redteam_meter.value() == 100
    assert "Detector: attribute" in window.redteam_verdict.text()
    assert window.redteam_board.item(0, 0).text() == "panel-mole"
    _dispose(window, application)
