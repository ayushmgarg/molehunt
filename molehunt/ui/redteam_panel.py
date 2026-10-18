"""Red Team boss panel: pick tools and strengths, watch the utility meter, submit
the scrubbed copy to the real detector, and see the leaderboard."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from molehunt.game.redteam import (
    TOOLS,
    UTILITY_FLOOR,
    Verdict,
    apply_tools,
    evaluate,
    record_score,
    redteam_leaderboard,
    start_session,
)

DEFAULT_MASTER = Path("data/masters/m1_roadmap.md")


def build_redteam_panel(owner, layout: QVBoxLayout) -> None:
    """Append the Red Team boss controls under the benchmark form."""
    layout.addWidget(QLabel("Red Team: be the mole. Keep utility >= 70% and avoid attribution."))
    row = QHBoxLayout()
    owner.redteam_player = QLineEdit("mole-01")
    owner.redteam_seed = QSpinBox()
    owner.redteam_seed.setRange(0, 9999)
    owner.redteam_dictionary = QLineEdit()
    owner.redteam_dictionary.setPlaceholderText("Pairs you discovered for canonicalize: a=b, c=d")
    for label, widget in (("Player", owner.redteam_player), ("Copy seed", owner.redteam_seed),
                          ("Dictionary", owner.redteam_dictionary)):
        row.addWidget(QLabel(label))
        row.addWidget(widget, 1 if widget is owner.redteam_dictionary else 0)
    layout.addLayout(row)
    grid = QGridLayout()
    owner.redteam_tools = {}
    for index, name in enumerate(TOOLS):
        box = QCheckBox(name)
        strength = QDoubleSpinBox()
        strength.setRange(0.0, 1.0)
        strength.setSingleStep(0.05)
        strength.setValue(1.0 if name != "truncate" else 0.8)
        owner.redteam_tools[name] = (box, strength)
        grid.addWidget(box, index // 5, (index % 5) * 2)
        grid.addWidget(strength, index // 5, (index % 5) * 2 + 1)
    layout.addLayout(grid)
    button = QPushButton("Scrub my copy and face the detector")
    button.clicked.connect(owner._redteam_run)
    layout.addWidget(button)
    owner.redteam_meter = QProgressBar()
    owner.redteam_meter.setRange(0, 100)
    owner.redteam_meter.setFormat(f"Utility %p%  (floor {UTILITY_FLOOR:.0%})")
    layout.addWidget(owner.redteam_meter)
    owner.redteam_verdict = QLabel("No attempt yet.")
    owner.redteam_verdict.setWordWrap(True)
    layout.addWidget(owner.redteam_verdict)
    owner.redteam_board = QTableWidget(0, 4)
    owner.redteam_board.setHorizontalHeaderLabels(["Player", "Best score", "Utility", "Outcome"])
    owner.redteam_board.horizontalHeader().setStretchLastSection(True)
    layout.addWidget(owner.redteam_board)


def _attempt(master: Path, seed: int, steps, dictionary, database: Path, player: str) -> tuple:
    session = start_session(master, seed=seed)
    verdict = evaluate(session, apply_tools(session, steps, seed=seed, dictionary=dictionary))
    database.parent.mkdir(parents=True, exist_ok=True)
    record_score(database, player, verdict, steps)
    return session.mole, verdict, redteam_leaderboard(database)


class RedTeamActions:
    """Controller methods for the Red Team boss panel."""

    def _redteam_run(self) -> None:
        steps = [(name, strength.value()) for name, (box, strength) in self.redteam_tools.items()
                 if box.isChecked()]
        pairs = [tuple(item.strip().split("=", 1)) for item in
                 self.redteam_dictionary.text().split(",") if "=" in item]
        master_text = self.fields["bench"]["master"].text().strip()
        master = Path(master_text) if master_text else DEFAULT_MASTER
        database = Path(self.fields["casebook"]["database"].text().strip()
                        or ".molehunt/molehunt.sqlite3")
        player = self.redteam_player.text().strip() or "mole"
        seed = self.redteam_seed.value()
        self._start_task(lambda: _attempt(master, seed, steps, pairs, database, player),
                         self._redteam_render)

    def _redteam_render(self, result: tuple[str, Verdict, list]) -> None:
        mole, verdict, board = result
        self.redteam_meter.setValue(round(100 * verdict.utility))
        outcome = "YOU EVADED THE DETECTOR" if verdict.win else (
            "Utility below floor: attempt void" if verdict.utility < UTILITY_FLOOR else "CAUGHT")
        self.redteam_verdict.setText(
            f"You held copy {mole}. {outcome}. Detector: {verdict.outcome}"
            + (f" -> {verdict.accused}" if verdict.accused else "")
            + f". Slots read {verdict.observed_slots}/{verdict.baseline_slots}; your log10 LR "
            f"{verdict.mole_log10_lr}. Score {verdict.score}.")
        self.redteam_board.setRowCount(len(board))
        for row, (name, score, kept, result_text) in enumerate(board):
            for column, value in enumerate((name, str(score), f"{kept:.1%}", result_text)):
                self.redteam_board.setItem(row, column, QTableWidgetItem(value))
        self.status.setText(f"Red Team attempt scored {verdict.score}.")
