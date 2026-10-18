"""Controller actions for seeded casebook progress, hints, and answers."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from molehunt.game.casebook import CaseDefinition
from molehunt.game.generator import CaseInstance, generate_case
from molehunt.game.leaderboard import record_graded
from molehunt.game.progression import (
    get_case_progress,
    initialize_casebook,
    start_case,
    use_hint,
)
from molehunt.game.validator import Procedure, Submission, grade_case, parse_details


class CasebookActions:
    """Methods backing the Casebook tab of the desktop workbench."""

    def _casebook_refresh(self) -> None:
        try:
            fields = self.fields["casebook"]
            player_id = fields["player"].text().strip()
            database = self._field_path("casebook", "database")
            initialize_casebook(database, player_id, self.case_definitions)
            self.case_progress = {
                progress.case_id: progress
                for progress in get_case_progress(database, player_id)
            }
            self._casebook_show_selected()
            self.status.setText(f"Casebook progress loaded for {player_id}")
        except (OSError, ValueError, sqlite3.Error) as error:
            self.status.setText(f"Casebook error: {error}")

    def _casebook_show_selected(self) -> None:
        definition = self._case_definition()
        progress = self.case_progress.get(definition.case_id)
        status = progress.status if progress is not None else "not started"
        tools = ", ".join(progress.unlocked_tools) if progress else "none"
        self.case_details.setPlainText(
            f"{definition.brief}\n\nObjective: {definition.objective}\n\n"
            f"Status: {status}\nAvailable tools: {tools}\n"
            "Start the case to generate its seeded evidence package."
        )
        self._apply_tool_locks()

    def _apply_tool_locks(self, _checked: bool = False) -> None:
        """Enable only tabs and subtools earned by the selected Casebook progress."""
        locked = self.casebook_lock.isChecked()
        definition = self._case_definition()
        progress = self.case_progress.get(definition.case_id)
        tools = set(progress.unlocked_tools) if progress is not None else set()
        if not locked:
            for index in range(self.tabs.count()):
                self.tabs.setTabEnabled(index, True)
            self.evidence_tree.setVisible(True)
            self.evidence_refresh_button.setEnabled(True)
            self.inspect_evidence_button.setEnabled(True)
            self.diff_evidence_button.setEnabled(True)
            self.hex_table.setVisible(True)
            self.byte_detail.setVisible(True)
            self.invisible_label.setVisible(True)
            self.invisible_table.setVisible(True)
            self.diff_label.setVisible(True)
            self.diff_table.setVisible(True)
            self.diff_variations.setVisible(True)
            self.timeline_load_button.setEnabled(True)
            self.timeline_filter.setEnabled(True)
            self.timeline_table.setVisible(True)
            self.timeline_pin_button.setEnabled(True)
            self.timeline_pins.setVisible(True)
            self.results.setVisible(True)
            self.fusion_results.setVisible(False)
            self.slot_matrix.setVisible(True)
            self.run_analysis_button.setText("Run analysis")
            for index in range(self.evidence_tabs.count()):
                self.evidence_tabs.setTabEnabled(index, True)
            return

        available = {
            0: bool({"auto_detector", "slot_matrix"} & tools),
            1: False,
            2: "intake" in tools,
            3: False,
            4: True,
            5: bool(
                {
                    "intake", "hex", "invisible", "diff", "ooxml", "image_dots", "tardos",
                    "timeline", "notes", "report",
                }
                & tools
            ),
        }
        for index, enabled in available.items():
            self.tabs.setTabEnabled(index, enabled)

        has_intake = "intake" in tools
        has_hex = "hex" in tools
        has_invisible = "invisible" in tools
        has_diff = "diff" in tools
        has_timeline = "timeline" in tools
        has_auto_detector = "auto_detector" in tools
        has_slot_matrix = "slot_matrix" in tools
        self.evidence_tree.setVisible(has_intake)
        self.evidence_refresh_button.setEnabled(has_intake)
        self.inspect_evidence_button.setEnabled(has_hex or has_invisible)
        self.hex_table.setVisible(has_hex)
        self.byte_detail.setVisible(has_hex)
        self.invisible_label.setVisible(has_invisible)
        self.invisible_table.setVisible(has_invisible)
        self.diff_evidence_button.setEnabled(has_diff)
        self.diff_label.setVisible(has_diff)
        self.diff_table.setVisible(has_diff)
        self.diff_variations.setVisible(has_diff)
        self.timeline_load_button.setEnabled(has_timeline)
        self.timeline_filter.setEnabled(has_timeline)
        self.timeline_table.setVisible(has_timeline)
        self.timeline_pin_button.setEnabled(has_timeline)
        self.timeline_pins.setVisible(has_timeline)
        self.results.setVisible(has_auto_detector)
        self.fusion_results.setVisible(has_auto_detector)
        self.slot_matrix.setVisible(has_auto_detector or has_slot_matrix)
        self.run_analysis_button.setText(
            "Run analysis" if has_auto_detector else "Build slot matrix"
        )
        sub_tools = ({"intake", "hex", "invisible"}, {"diff"}, {"timeline"}, {"ooxml"},
                     {"image_dots"}, {"tardos"}, {"notes", "report"})
        for index, needed in enumerate(sub_tools):
            self.evidence_tabs.setTabEnabled(index, bool(needed & tools))

    def _case_definition(self) -> CaseDefinition:
        case_id = self.case_selector.currentData()
        return next(case for case in self.case_definitions if case.case_id == case_id)

    def _casebook_start(self) -> None:
        try:
            fields = self.fields["casebook"]
            player_id = fields["player"].text().strip()
            if not player_id:
                raise ValueError("player ID is required")
            seed = int(fields["seed"].text().strip())
            if seed < 0:
                raise ValueError("seed must not be negative")
            self.casebook_lock.setChecked(True)
            definition = self._case_definition()
            database = self._field_path("casebook", "database")
            initialize_casebook(database, player_id, self.case_definitions)
            start_case(database, player_id, definition.case_id, self.case_definitions)
            root = self._field_path("casebook", "output_root")
            player_slug = re.sub(r"[^A-Za-z0-9_-]", "_", player_id)[:32]
            base = root / player_slug / definition.case_id / f"seed-{seed}"
            output = base
            run_number = 2
            while output.exists():
                output = base.with_name(f"seed-{seed}-run-{run_number}")
                run_number += 1
            master = Path(definition.master)
            self._start_task(
                lambda: generate_case(
                    definition, output, seed=seed, master_path=master
                ),
                self._casebook_case_ready,
            )
        except (OSError, ValueError, sqlite3.Error) as error:
            self.status.setText(f"Casebook error: {error}")

    def _casebook_case_ready(self, instance: CaseInstance) -> None:
        self.case_instance = instance
        definition = instance.definition
        self.case_details.setPlainText(
            f"{definition.brief}\n\nObjective: {definition.objective}\n\n"
            f"Generated evidence: {instance.evidence_path}\n"
            f"Roster: {instance.roster_path}\n"
            f"Auxiliary logs: {', '.join(str(path) for path in instance.auxiliary_paths) or 'none'}\n"
            "Generated answers are checked privately when you submit."
        )
        timeline_paths = []
        for path in instance.auxiliary_paths:
            if path.suffix.casefold() != ".csv":
                continue
            with path.open("r", encoding="utf-8-sig", newline="") as stream:
                if "timestamp" in (csv.DictReader(stream).fieldnames or ()):
                    timeline_paths.append(str(path))
        self.timeline_paths.setText(";".join(timeline_paths))
        self._casebook_refresh()
        self.status.setText(f"Generated {definition.case_id}: {instance.evidence_path}")

    def _casebook_hint(self) -> None:
        try:
            definition = self._case_definition()
            player_id = self.fields["casebook"]["player"].text().strip()
            database = self._field_path("casebook", "database")
            hint = use_hint(database, player_id, definition)
            self.case_details.append(f"\nHint: {hint}")
            self.status.setText(f"Hint used for {definition.case_id}")
        except (OSError, ValueError, sqlite3.Error) as error:
            self.status.setText(f"Hint error: {error}")

    def _casebook_procedure(self, instance: CaseInstance, truth: dict) -> Procedure:
        """Hygiene observed by the workbench: intake hash, notes, original untouched."""
        database = self._field_path("casebook", "database")
        digest = truth.get("evidence_sha256", "")
        with sqlite3.connect(database) as connection:
            taken = connection.execute(
                "SELECT COUNT(*) FROM evidence WHERE sha256 = ?", (digest,)
            ).fetchone()[0]
        current = hashlib.sha256(instance.evidence_path.read_bytes()).hexdigest()
        notes = bool(getattr(self, "notes_text", None) and self.notes_text.toPlainText().strip())
        return Procedure(hashed=bool(taken), working_copy=bool(taken), notes=notes,
                         original_untouched=current == digest)

    def _casebook_submit(self) -> None:
        try:
            definition = self._case_definition()
            instance = self.case_instance
            if instance is None or instance.definition.case_id != definition.case_id:
                raise ValueError("start this case before submitting an answer")
            fields = self.fields["casebook"]
            answer = fields["answer"].text().strip()
            if not answer:
                raise ValueError("enter an answer first")
            truth = json.loads(instance.ground_truth_path.read_text(encoding="utf-8"))
            database = self._field_path("casebook", "database")
            player = fields["player"].text().strip()
            progress = self.case_progress.get(definition.case_id)
            started = datetime.fromisoformat(progress.started_at) if progress and (
                progress.started_at) else datetime.now(UTC)
            with sqlite3.connect(database) as connection:
                wrong = connection.execute(
                    "SELECT COUNT(*) FROM submissions WHERE player_id = ? AND case_id = ? "
                    "AND correct = 0", (player, definition.case_id)).fetchone()[0]
            submission = Submission(answer, self.case_confidence.value(),
                                    parse_details(fields["details"].text()))
            score = grade_case(
                definition.generator, truth, submission,
                procedure=self._casebook_procedure(instance, truth),
                elapsed_seconds=(datetime.now(UTC) - started).total_seconds(),
                hints_used=progress.hints_used if progress else 0, wrong_before=wrong,
            )
            status = record_graded(database, player, self.case_definitions, definition.case_id,
                                   score, {"answer": answer, "details": dict(submission.details)})
            self._casebook_refresh()
            verdict = "Correct" if score.correct else "Not correct yet"
            self.status.setText(
                f"{verdict}: {score.total} points (finding {score.finding}, procedure "
                f"{score.procedure}, evidence {score.evidence}, calibration {score.calibration}, "
                f"time {score.time_bonus}, penalties -{score.penalties}); case {status}. "
                + " ".join(score.feedback)
            )
        except (OSError, ValueError, KeyError, sqlite3.Error, json.JSONDecodeError) as error:
            self.status.setText(f"Submission error: {error}")
