"""Benchmark command: the SPEC Section 6 protocol, or a quick single-master run."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer

from molehunt.attacks.collusion_bench import run_collusion
from molehunt.attacks.harness import (
    TEXT_ATTACKS,
    ProtocolConfig,
    run_protocol,
    run_text_benchmark,
    write_benchmark,
)
from molehunt.cli_app import (
    DEFAULT_KEY,
    DEFAULT_MASTERS,
    app,
    fail,
    read_employee_ids,
    read_key,
    split_list,
)
from molehunt.core.autoslots import prepare_master


def _report(rows, artifacts: dict[str, Path]) -> None:
    top1 = sum(row.top1_correct for row in rows) / len(rows)
    typer.echo(f"Runs: {len(rows)}")
    typer.echo(f"Overall top-1 accuracy: {top1:.3f}")
    if "targets" in artifacts:
        for line in artifacts["targets"].read_text(encoding="utf-8").splitlines()[1:]:
            typer.echo(f"  target: {line}")
    for label, path in artifacts.items():
        typer.echo(f"{label}: {path}")
    typer.echo("Results apply only to these synthetic inputs and configured runs.")


@app.command()
def bench(
    master: Annotated[Path | None, typer.Option("--master", help="Quick mode: one master")]
    = None,
    employees: Annotated[Path | None, typer.Option("--employees", help="Quick mode: roster")]
    = None,
    key_file: Annotated[Path, typer.Option("--key-file", help="Quick mode key")] = DEFAULT_KEY,
    masters: Annotated[int, typer.Option("--masters", help="Protocol: masters to use")] = 3,
    masters_dir: Annotated[Path, typer.Option("--masters-dir")] = DEFAULT_MASTERS,
    roster_size: Annotated[int, typer.Option("--roster-size")] = 50,
    leakers: Annotated[int, typer.Option("--leakers")] = 20,
    attacks: Annotated[str, typer.Option(help="Comma-separated attack IDs")]
    = ",".join(TEXT_ATTACKS),
    strengths: Annotated[str, typer.Option(help="Comma-separated strengths")] = "0.15,0.5,1.0",
    seeds: Annotated[str, typer.Option(help="Protocol: seed count; quick mode: seed list")]
    = "10",
    collusion: Annotated[bool, typer.Option("--collusion/--no-collusion")] = True,
    workers: Annotated[int, typer.Option("--workers", min=1)] = max(1, (os.cpu_count() or 2) - 1),
    output: Annotated[Path, typer.Option("--output", help="Artifact directory")] = Path("bench"),
    flip_rate: Annotated[float, typer.Option("--flip-rate", min=0.000001, max=0.499999)] = 0.15,
) -> None:
    """Measure attack survival, accuracy, false accusations, and collusion tracing."""
    try:
        attack_ids = split_list(attacks)
        strength_values = split_list(strengths, float)
        if master is not None:
            if employees is None:
                raise ValueError("quick mode needs --employees with --master")
            key = read_key(key_file)
            prepared = prepare_master(master.read_text(encoding="utf-8"), key)
            rows = run_text_benchmark(
                prepared.template, prepared.slots, key, read_employee_ids(employees),
                attack_ids=attack_ids, strengths=strength_values,
                seeds=split_list(seeds, int), flip_rate=flip_rate,
            )
            artifacts = write_benchmark(rows, output)
        else:
            paths = tuple(sorted(masters_dir.glob("*.md")))[:masters]
            if not paths:
                raise ValueError(f"no masters found in {masters_dir}")
            seed_values = tuple(range(int(seeds)))
            typer.echo(f"Protocol: {len(paths)} masters x {roster_size} employees x {leakers} "
                       f"leakers x {len(attack_ids)} attacks x {len(strength_values)} strengths "
                       f"x {len(seed_values)} seeds + chains, {workers} workers")
            config = ProtocolConfig(
                masters=paths, employees=roster_size, leakers=leakers, seeds=seed_values,
                strengths=tuple(strength_values), attacks=tuple(attack_ids),
                flip_rate=flip_rate, workers=workers,
            )
            rows = run_protocol(config)
            colluded = (
                run_collusion(paths, seed_values, employees=roster_size, workers=workers)
                if collusion else ()
            )
            artifacts = write_benchmark(rows, output, collusion=colluded)
    except (OSError, UnicodeError, ValueError) as error:
        fail(error)
    _report(rows, artifacts)
