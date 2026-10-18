"""Wrap blocking engine work in a Qt object that can run on a QThread."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Signal, Slot


class TaskWorker(QObject):
    """Execute one operation and report its result or error through Qt signals."""

    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, operation: Callable[[], object]) -> None:
        super().__init__()
        self._operation = operation

    @Slot()
    def run(self) -> None:
        """Run the operation once and always notify the owning thread."""
        try:
            self.completed.emit(self._operation())
        except Exception as error:  # noqa: BLE001 - relay engine errors to the UI
            self.failed.emit(f"{type(error).__name__}: {error}")
        finally:
            self.finished.emit()
