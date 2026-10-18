"""Controller actions for loading, filtering, and pinning timeline evidence."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QTableWidgetItem

from molehunt.game.timeline import TimelineEvent, load_timeline


def _event_search_text(event: TimelineEvent) -> str:
    """Combine searchable timeline fields into one case-folded string."""
    return (
        f"{event.timestamp.isoformat()} {event.employee_id} {event.event} "
        f"{event.device_id} {event.printer_id} {event.source}"
    ).casefold()


class TimelineActions:
    """Methods backing the synthetic event timeline in the Evidence tools tab."""

    _timeline_events: tuple[TimelineEvent, ...] = ()
    _timeline_visible: tuple[TimelineEvent, ...] = ()
    _timeline_pinned: list[TimelineEvent]

    def _timeline_load(self) -> None:
        try:
            raw_paths = self.timeline_paths.text().replace("\n", ";")
            paths = tuple(Path(item.strip()) for item in raw_paths.split(";") if item.strip())
            if not paths:
                raise ValueError("enter at least one timestamped event CSV path")
            self._start_task(lambda: load_timeline(paths), self._timeline_loaded)
        except (OSError, ValueError) as error:
            self.status.setText(f"Timeline error: {error}")

    def _timeline_loaded(self, events: tuple[TimelineEvent, ...]) -> None:
        self._timeline_events = events
        self._timeline_pinned = []
        self._timeline_filter(self.timeline_filter.text())
        self.status.setText(f"Timeline loaded: {len(events)} event(s)")

    def _timeline_filter(self, query: str) -> None:
        normalized = query.strip().casefold()
        visible = tuple(
            event
            for event in self._timeline_events
            if not normalized
            or normalized in _event_search_text(event)
        )
        self._timeline_visible = visible
        self.timeline_table.setRowCount(len(visible))
        for row_index, event in enumerate(visible):
            values = (
                event.timestamp.isoformat(timespec="seconds"),
                event.employee_id,
                event.event,
                event.device_id,
                event.printer_id,
                event.source,
            )
            for column, value in enumerate(values):
                self.timeline_table.setItem(row_index, column, QTableWidgetItem(value))

    def _timeline_pin_selected(self) -> None:
        rows = self.timeline_table.selectionModel().selectedRows()
        if not rows:
            self.status.setText("Select a timeline event before pinning it")
            return
        event = self._timeline_visible[rows[0].row()]
        if event not in self._timeline_pinned:
            self._timeline_pinned.append(event)
        self.timeline_pins.setPlainText(
            "\n".join(
                f"{item.timestamp.isoformat(timespec='seconds')} · {item.employee_id} · "
                f"{item.event} · {item.source}"
                for item in self._timeline_pinned
            )
        )
        self.status.setText(f"Pinned {event.event} from {event.source}")
