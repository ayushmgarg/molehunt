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


def test_protocol_runs_chains_and_writes_targets(tmp_path) -> None:
    import csv
    import json
    from pathlib import Path

    from molehunt.attacks.collusion_bench import run_collusion
    from molehunt.attacks.harness import CHAINS, ProtocolConfig, run_protocol

    master = Path(__file__).parents[1] / "data" / "masters" / "m1_roadmap.md"
    config = ProtocolConfig(
        masters=(master,), employees=8, leakers=2, seeds=(0,), strengths=(0.5,),
        attacks=("A1", "A7"), chains={"A1-A4+A8@0.5": CHAINS["A1-A4+A8@0.5"]},
    )
    rows = run_protocol(config)
    assert len(rows) == 2 * (2 + 1)
    assert rows[0].observed_slots == run_protocol(config)[0].observed_slots
    assert {row.attack_id for row in rows} == {"A1", "A7", "A1-A4+A8@0.5"}
    assert all(row.master == "m1_roadmap" for row in rows)
    a1 = [row for row in rows if row.attack_id == "A1"]
    for row in a1:
        survived = {channel: (seen, total) for channel, seen, total in row.channel_survival}
        assert survived["zw"][0] < survived["zw"][1]
        assert survived["lex"][0] == survived["lex"][1]
    collusion = run_collusion((master,), (0,), ks=(2,), strategies=("majority",), employees=10)
    assert len(collusion) == 1 and collusion[0].k == 2
    artifacts = write_benchmark(rows, tmp_path, collusion=collusion)
    for label in ("runs", "survival", "runtime", "roc", "targets", "summary", "collusion",
                  "accuracy_plot", "survival_plot", "roc_plot", "collusion_plot"):
        assert artifacts[label].exists(), label
    with artifacts["targets"].open(encoding="utf-8", newline="") as stream:
        targets = list(csv.DictReader(stream))
    assert {row["verdict"] for row in targets} <= {"PASS", "FAIL", "NO DATA"}
    assert any(row["target"].startswith("top-1 under A1-A4") for row in targets)
    summary = json.loads(artifacts["summary"].read_text(encoding="utf-8"))
    assert summary["runs"] == len(rows)
