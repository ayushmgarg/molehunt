"""Tests for the Qt worker's success and failure signals."""

from molehunt.ui.worker import TaskWorker


def test_worker_emits_operation_result_and_finished() -> None:
    worker = TaskWorker(lambda: {"count": 3})
    results = []
    finished = []
    worker.completed.connect(results.append)
    worker.finished.connect(lambda: finished.append(True))

    worker.run()

    assert results == [{"count": 3}]
    assert finished == [True]


def test_worker_emits_error_and_finished() -> None:
    def fail() -> None:
        raise ValueError("bad evidence")

    worker = TaskWorker(fail)
    errors = []
    finished = []
    worker.failed.connect(errors.append)
    worker.finished.connect(lambda: finished.append(True))

    worker.run()

    assert errors == ["ValueError: bad evidence"]
    assert finished == [True]
