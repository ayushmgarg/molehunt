"""Tests for measured attack runs and persisted benchmark artifacts."""

from molehunt.attacks.harness import run_text_benchmark, write_benchmark
from molehunt.core.slots import allocate_slots
from molehunt.core.template import parse_template


def test_small_benchmark_records_runs_and_channel_survival(tmp_path) -> None:
    source = "\n".join(
        f"Record {index:02}: " + "{{lex:begin|start}}."
        for index in range(32)
    )
    template = parse_template(source)
    key = bytes(range(32))
    slots = allocate_slots(template, key)
    rows = run_text_benchmark(
        template,
        slots,
        key,
        ["E01", "E02", "E03"],
        attack_ids=["A1", "A3"],
        strengths=[0.0, 1.0],
        seeds=[1, 2],
    )
    assert len(rows) == 2 * 2 * 2 * 3
    clean_rows = [row for row in rows if row.strength == 0]
    assert all(row.top1_correct for row in clean_rows)
    assert all(row.observed_slots == 32 for row in clean_rows)
    artifacts = write_benchmark(rows, tmp_path)
    assert artifacts["runs"].exists()
    assert artifacts["survival"].exists()
    assert artifacts["accuracy_plot"].exists()
    assert artifacts["survival_plot"].exists()
