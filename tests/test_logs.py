"""Tests for explicit synthetic log fusion CSV ingestion."""

from pathlib import Path

import pytest

from molehunt.detect.logs import read_fusion_logs


def test_log_rows_consolidate_strongest_access_and_unique_events(tmp_path: Path) -> None:
    path = tmp_path / "logs.csv"
    path.write_text(
        "employee_id,access_level,event\n"
        "E1,indirect,print_job\n"
        "E1,direct,after_hours_download\n"
        "E1,direct,print_job\n"
        "E2,none,\n",
        encoding="utf-8",
    )
    logs = read_fusion_logs(path, {"E1", "E2"})
    assert logs.access == {"E1": "direct", "E2": "none"}
    assert logs.events == {
        "E1": ("after_hours_download", "print_job"),
    }


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("id,access_level,event\nE1,direct,\n", "employee_id and access_level"),
        ("employee_id,access_level,event\n,none,\n", "empty employee_id"),
        ("employee_id,access_level,event\nE1,private,\n", "invalid access_level"),
        ("employee_id,access_level,event\nE1,direct,odd_event\n", "unknown event"),
        ("employee_id,access_level,event\nE3,direct,\n", "unknown candidate"),
    ],
)
def test_log_csv_rejects_bad_rows(tmp_path: Path, content: str, message: str) -> None:
    path = tmp_path / "logs.csv"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        read_fusion_logs(path, {"E1", "E2"})


def test_log_csv_requires_data_rows(tmp_path: Path) -> None:
    path = tmp_path / "logs.csv"
    path.write_text("employee_id,access_level,event\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no data rows"):
        read_fusion_logs(path)
