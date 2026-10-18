"""Generate reproducible synthetic evidence packages from answer-free cases."""

from __future__ import annotations

import csv
import hashlib
import json
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from PIL import Image

from molehunt.attacks.collusion import collude_bits
from molehunt.attacks.transform import attack_text
from molehunt.channels.printdots import DotMetadata, render_dot_grid
from molehunt.channels.zerowidth import embed_zero_width
from molehunt.core.codes import generate_codeword
from molehunt.core.render import render_docx, render_text
from molehunt.core.slots import Slot, allocate_slots, bits_in_source_order
from molehunt.core.tardos import generate_tardos_biases, generate_tardos_codeword
from molehunt.core.template import Choice, Template, parse_template
from molehunt.game.casebook import CaseDefinition


@dataclass(frozen=True, slots=True)
class CaseInstance:
    """Paths to player-visible artifacts and separately stored generated truth."""

    definition: CaseDefinition
    seed: int
    master_path: Path
    public_dir: Path
    evidence_path: Path
    roster_path: Path
    auxiliary_paths: tuple[Path, ...]
    ground_truth_path: Path


def _write_roster(path: Path, employee_ids: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["id"])
        writer.writerows((employee_id,) for employee_id in employee_ids)


def _write_logs(path: Path, rows: list[tuple[str, str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["employee_id", "access_level", "event"])
        writer.writerows(rows)


def _render_with_zero_width(
    template: Template, slots: tuple[Slot, ...], codeword: tuple[int, ...]
) -> tuple[str, tuple[int, ...]]:
    """Render the visible variants and put each C1 bit after its chosen word."""
    source_bits = bits_in_source_order(slots, codeword)
    chunks: list[str] = []
    insertions: list[tuple[int, int]] = []
    offset = 0
    source_index = 0
    for node in template.nodes:
        if isinstance(node, Choice):
            chosen = node.zero if source_bits[source_index] == 0 else node.one
            chunks.append(chosen)
            offset += len(chosen)
            insertions.append((offset, source_bits[source_index]))
            source_index += 1
        else:
            chunks.append(node.text)
            offset += len(node.text)
    rendered = embed_zero_width("".join(chunks), insertions)
    index_by_source = {
        slot.source_index: slot.index for slot in slots
    }
    offsets_by_index = [0] * len(slots)
    for source_index, offset in enumerate(rendered.slot_offsets):
        offsets_by_index[index_by_source[source_index]] = offset
    return rendered.text, tuple(offsets_by_index)


def _single_copy(
    definition: CaseDefinition,
    template: Template,
    slots: tuple[Slot, ...],
    key: bytes,
    employee_id: str,
    public_dir: Path,
    rng: random.Random,
) -> tuple[Path, dict[str, Any], tuple[Path, ...]]:
    """Create one case's evidence and scenario-specific truth metadata."""
    codeword = generate_codeword(key, employee_id, len(slots))
    visible = render_text(template, slots, codeword)
    auxiliary: tuple[Path, ...] = ()
    if definition.generator == "invisible_copy":
        evidence = public_dir / "leak.txt"
        rendered, offsets = _render_with_zero_width(template, slots, codeword)
        evidence.write_text(rendered, encoding="utf-8")
        truth = {"copy_owner": employee_id, "slot_offsets": offsets, "codeword": codeword}
    elif definition.generator == "edited_text":
        evidence = public_dir / "leak.txt"
        strength = 0.35 + rng.random() * 0.4
        evidence.write_text(
            attack_text(visible, "A3", strength=strength, seed=rng.randrange(1 << 32)),
            encoding="utf-8",
        )
        truth = {"copy_owner": employee_id, "attack": "A3", "strength": strength}
    elif definition.generator == "print_timeline":
        evidence = public_dir / "scan.png"
        printed_on = date(2025, 1, 1) + timedelta(days=rng.randrange(365))
        minute = rng.randrange(1440)
        printer_id = rng.randrange(1, 256)
        metadata = DotMetadata(printer_id, printed_on, minute)
        page = Image.new("RGB", (1024, 1400), "white")
        render_dot_grid(page, metadata, origin=(16, 16), cell_size=6, radius=1).save(evidence)
        log_path = public_dir / "print_events.csv"
        _write_logs(log_path, [(employee_id, "direct", "print_job")])
        auxiliary = (log_path,)
        truth = {
            "copy_owner": employee_id,
            "printer_id": printer_id,
            "printed_on": printed_on.isoformat(),
            "minute_of_day": minute,
            "grid_origin": [16, 16],
            "grid_cell_size": 6,
        }
    elif definition.generator == "ooxml_metadata":
        evidence = public_dir / "leak.docx"
        evidence.write_bytes(render_docx(template, slots, codeword, key, employee_id))
        truth = {"copy_owner": employee_id, "custom_property": employee_id}
    else:
        evidence = public_dir / "leak.txt"
        evidence.write_text(visible, encoding="utf-8")
        truth = {"copy_owner": employee_id, "codeword": codeword}
    return evidence, truth, auxiliary


def generate_case(
    definition: CaseDefinition,
    output_dir: str | Path,
    *,
    seed: int,
    master_path: str | Path | None = None,
    employee_count: int = 10,
) -> CaseInstance:
    """Create a fresh deterministic case folder with public files and private truth."""
    if seed < 0:
        raise ValueError("seed must not be negative")
    if employee_count < 3:
        raise ValueError("case generation needs at least three synthetic employees")
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(f"case output directory already exists: {output}")
    source_path = Path(master_path or definition.master)
    if not source_path.is_absolute():
        source_path = Path.cwd() / source_path
    source = source_path.read_text(encoding="utf-8")
    template = parse_template(source)
    effective_seed = seed + definition.seed_offset
    rng = random.Random(effective_seed)
    key = hashlib.sha256(
        f"MoleHunt case seed v1\0{definition.case_id}\0{effective_seed}".encode()
    ).digest()
    slots = allocate_slots(template, key)
    employee_ids = [f"E{index:03}" for index in range(1, employee_count + 1)]
    output.mkdir(parents=True)
    public_dir = output / "public"
    private_dir = output / "private"
    public_dir.mkdir()
    private_dir.mkdir()
    roster = public_dir / "employees.csv"
    _write_roster(roster, employee_ids)

    if definition.generator == "collusion":
        biases = generate_tardos_biases(key, len(slots))
        codewords = {
            employee_id: generate_tardos_codeword(key, employee_id, biases)
            for employee_id in employee_ids
        }
        colluders = tuple(sorted(rng.sample(employee_ids, 2)))
        merged = collude_bits([codewords[item] for item in colluders], "majority", seed=effective_seed)
        evidence = public_dir / "leak.txt"
        evidence.write_text(template.render(bits_in_source_order(slots, merged)), encoding="utf-8")
        truth: dict[str, Any] = {
            "colluders": colluders,
            "biases": biases,
            "candidate_codewords": codewords,
            "strategy": "majority",
        }
        auxiliary = ()
    else:
        employee_id = rng.choice(employee_ids)
        evidence, truth, auxiliary = _single_copy(
            definition, template, slots, key, employee_id, public_dir, rng
        )
        if definition.generator == "log_fusion":
            rows = [
                (candidate, "direct" if candidate == employee_id else "indirect",
                 "after_hours_download" if candidate == employee_id else "")
                for candidate in employee_ids
            ]
            log_path = public_dir / "access_logs.csv"
            _write_logs(log_path, rows)
            auxiliary += (log_path,)
        elif definition.generator == "account_sharing":
            account = next(candidate for candidate in employee_ids if candidate != employee_id)
            log_path = public_dir / "account_logs.csv"
            _write_logs(
                log_path,
                [
                    (employee_id, "direct", "badge_entry"),
                    (account, "indirect", "unusual_auth"),
                ],
            )
            auxiliary = (log_path,)
            truth.update({"account_sharing_hypothesis": account, "copy_owner": employee_id})

    private_dir.joinpath("ground_truth.json").write_text(
        json.dumps(
            {"case_id": definition.case_id, "seed": effective_seed, **truth},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return CaseInstance(
        definition, effective_seed, source_path.resolve(), public_dir, evidence,
        roster, auxiliary, private_dir / "ground_truth.json",
    )
