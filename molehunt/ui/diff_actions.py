"""Compare decoded leak lines with a master and expose authored A/B slots."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from PySide6.QtWidgets import QTableWidgetItem

from molehunt.core.template import parse_template
from molehunt.detect.ingest import ingest


@dataclass(frozen=True, slots=True)
class DiffRow:
    """One aligned line pair classified as equal, replace, insert, or delete."""

    kind: str
    master: str
    evidence: str


@dataclass(frozen=True, slots=True)
class MasterComparison:
    """Line comparison plus explicit authored variation alternatives."""

    rows: tuple[DiffRow, ...]
    variations: tuple[tuple[int, str, str, str], ...]


def compare_master(master_source: str, evidence_text: str) -> MasterComparison:
    """Render A variants, align lines with SequenceMatcher, and retain A/B choices."""
    template = parse_template(master_source)
    canonical = template.render([0] * len(template.choices))
    master_lines = canonical.splitlines()
    evidence_lines = evidence_text.splitlines()
    matcher = SequenceMatcher(None, master_lines, evidence_lines, autojunk=False)
    rows: list[DiffRow] = []
    for kind, master_start, master_end, evidence_start, evidence_end in matcher.get_opcodes():
        left = master_lines[master_start:master_end]
        right = evidence_lines[evidence_start:evidence_end]
        if kind == "equal":
            rows.extend(DiffRow("equal", line, line) for line in left)
        elif kind == "delete":
            rows.extend(DiffRow("delete", line, "") for line in left)
        elif kind == "insert":
            rows.extend(DiffRow("insert", "", line) for line in right)
        else:
            paired = min(len(left), len(right))
            rows.extend(
                DiffRow("replace", left[index], right[index])
                for index in range(paired)
            )
            rows.extend(DiffRow("delete", line, "") for line in left[paired:])
            rows.extend(DiffRow("insert", "", line) for line in right[paired:])
    variations = tuple(
        (index, choice.channel, choice.zero, choice.one)
        for index, choice in enumerate(template.choices, start=1)
    )
    return MasterComparison(tuple(rows), variations)


def _compare_inputs(master_path: Path, evidence_path: Path) -> MasterComparison:
    """Decode supported text evidence and compare it with the selected master."""
    evidence = ingest(evidence_path)
    if evidence.text is None:
        raise ValueError("diff view needs decoded text evidence")
    return compare_master(master_path.read_text(encoding="utf-8"), evidence.text)


class DiffActions:
    """Methods backing the side-by-side master diff in the Evidence tools tab."""

    def _diff(self) -> None:
        try:
            master = self._field_path("analysis", "master")
            evidence = self._field_path("analysis", "evidence")
            self._start_task(
                lambda: _compare_inputs(master, evidence), self._render_diff
            )
        except (OSError, ValueError) as error:
            self.status.setText(f"Diff error: {error}")

    def _render_diff(self, comparison: MasterComparison) -> None:
        self.diff_table.setRowCount(len(comparison.rows))
        for row_index, row in enumerate(comparison.rows):
            for column, value in enumerate((row.kind, row.master, row.evidence)):
                self.diff_table.setItem(row_index, column, QTableWidgetItem(value))
        self.diff_variations.setPlainText(
            "\n".join(
                f"Slot {index} ({channel}): A={variant_a!r} | B={variant_b!r}"
                for index, channel, variant_a, variant_b in comparison.variations
            )
            or "No authored variation points found."
        )
        self.status.setText(f"Diff complete: {len(comparison.rows)} aligned line(s)")
