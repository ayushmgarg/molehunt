"""Controller actions for seeded casebook progress, hints, and answers."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from molehunt.game.casebook import CaseDefinition
from molehunt.game.generator import CaseInstance, generate_case
from molehunt.game.progression import (
    get_case_progress,
    initialize_casebook,
    start_case,
    submit_answer,
    use_hint,
)


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
            if definition.generator == "collusion":
                expected = {item.casefold() for item in truth["colluders"]}
                submitted = {item.strip().casefold() for item in answer.split(",") if item.strip()}
                correct = submitted == expected
            elif definition.generator == "print_timeline":
                correct = answer == str(truth["printer_id"])
            else:
                correct = answer.casefold() == str(truth["copy_owner"]).casefold()
            result = submit_answer(
                self._field_path("casebook", "database"),
                fields["player"].text().strip(),
                self.case_definitions,
                definition.case_id,
                answer=answer,
                correct=correct,
                confidence=self.case_confidence.value(),
            )
            self._casebook_refresh()
            verdict = "Correct" if result.completed else "Not correct yet"
            self.status.setText(
                f"{verdict}: {result.points} points; Brier {result.grade.brier_score:.3f}"
            )
        except (OSError, ValueError, KeyError, sqlite3.Error, json.JSONDecodeError) as error:
            self.status.setText(f"Submission error: {error}")
