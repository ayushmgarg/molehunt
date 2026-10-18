"""Generate reproducible synthetic evidence packages from answer-free cases.

Input: a case definition + player seed. The effective seed (seed + case offset)
drives one ``random.Random`` and a case key SHA-256(case id, seed), so every
player gets different but reproducible evidence. Only authored slots are used
(front matter is stripped), because a player reads slots without the key. Output: ``public/`` (what the
player sees) and ``private/ground_truth.json`` (leaker, slots, planted events),
which only the validator reads. Scenario details live in ``case_evidence.py``.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from molehunt.attacks.collusion import collude_bits
from molehunt.attacks.transform import attack_text
from molehunt.channels.zerowidth import embed_zero_width
from molehunt.core.autoslots import split_front_matter
from molehunt.core.codes import generate_codeword
from molehunt.core.render import render_docx, render_text
from molehunt.core.slots import Slot, allocate_slots, bits_in_source_order
from molehunt.core.tardos import generate_tardos_biases, generate_tardos_codeword
from molehunt.core.template import Choice, Template, parse_template
from molehunt.game import case_evidence as ce
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


def _write_logs(path: Path, rows: list[tuple[str, str, str]]) -> Path:
    return ce.write_rows(path, ["employee_id", "access_level", "event"], rows)


def _render_with_zero_width(
    template: Template, slots: tuple[Slot, ...], codeword: tuple[int, ...], rng: random.Random,
) -> tuple[str, tuple[int, ...], list[int]]:
    """Put each C1 bit after its chosen word, plus one CMS decoy ZWJ off-slot."""
    source_bits = bits_in_source_order(slots, codeword)
    chunks: list[str] = []
    insertions: list[tuple[int, int]] = []
    literal_spans: list[tuple[int, int]] = []
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
            if len(node.text) > 4:
                literal_spans.append((offset + 2, offset + len(node.text) - 2))
            chunks.append(node.text)
            offset += len(node.text)
    decoys = [(rng.randrange(*span), "\u200d") for span in rng.sample(literal_spans, 1)]
    rendered = embed_zero_width("".join(chunks), insertions, decoys=decoys)
    index_by_source = {slot.source_index: slot.index for slot in slots}
    offsets_by_index = [0] * len(slots)
    for source, slot_offset in enumerate(rendered.slot_offsets):
        offsets_by_index[index_by_source[source]] = slot_offset
    return rendered.text, tuple(offsets_by_index), source_bits


def _write_registry(path: Path, slots: tuple[Slot, ...], codewords: dict) -> Path:
    """Issuance registry: each employee's bits in document (reading) order."""
    return ce.write_rows(path, ["employee_id", "bits"], [
        (item, "".join(map(str, bits_in_source_order(slots, word))))
        for item, word in codewords.items()])


def _access_rows(roster: list[str], key: dict[str, tuple[str, str]]) -> list[tuple[str, str, str]]:
    return [(item, *key.get(item, ("indirect", ""))) for item in roster]


def _single_copy(
    definition: CaseDefinition, template: Template, slots: tuple[Slot, ...], key: bytes,
    roster: list[str], employee_id: str, public: Path, rng: random.Random,
) -> tuple[Path, dict[str, Any], tuple[Path, ...]]:
    """Create one case's evidence and scenario-specific truth metadata."""
    codeword = generate_codeword(key, employee_id, len(slots))
    visible = render_text(template, slots, codeword)
    others = [item for item in roster if item != employee_id]
    kind = definition.generator
    if kind == "invisible_copy":
        evidence = public / "leak.txt"
        rendered, offsets, source_bits = _render_with_zero_width(template, slots, codeword, rng)
        evidence.write_text(rendered, encoding="utf-8")
        decoy = [index for index, ch in enumerate(rendered) if ch == "\u200d"]
        log = _write_logs(public / "access_log.csv",
                          _access_rows(roster, {item: ("direct", "") for item in roster}))
        return evidence, {"copy_owner": employee_id, "slot_offsets": offsets,
                          "codeword": codeword, "source_bits": source_bits,
                          "decoy_offsets": decoy}, (log,)
    if kind == "edited_text":
        twin = rng.choice(others)
        twin_word = generate_codeword(key, twin, len(slots))
        text, erased = ce.rewrite_slots(template, bits_in_source_order(slots, codeword),
                                        bits_in_source_order(slots, twin_word), rng)
        evidence = public / "newspaper.txt"
        evidence.write_text(attack_text(text, "A5", strength=1.0), encoding="utf-8")
        delivery = ce.write_rows(public / "copy_delivery.csv", ["employee_id", "copy"],
                                 [(item, f"copy-{item}") for item in roster])
        return evidence, {"copy_owner": employee_id, "tied_with": twin, "erased": erased,
                          "attack": "rewrite+A5"}, (delivery,)
    if kind == "print_timeline":
        evidence, auxiliary, truth = ce.print_case(public, roster, employee_id, rng)
        return evidence, {"copy_owner": employee_id, **truth}, auxiliary
    if kind == "ooxml_metadata":
        docx, decoy, template_name = ce.ooxml_decoys(
            render_docx(template, slots, codeword, key, employee_id), roster, employee_id, rng)
        evidence = public / "leak.docx"
        evidence.write_bytes(docx)
        auxiliary = ce.rsid_registry(public, key, roster, template_name, decoy)
        return evidence, {
            "copy_owner": employee_id, "custom_property": employee_id,
            "decoy_last_modified_by": decoy, "template": template_name,
            "reliability": ["rsid", "custom_property", "app_template", "last_modified_by"],
        }, auxiliary
    evidence = public / "leak.txt"
    evidence.write_text(visible, encoding="utf-8")
    return evidence, {"copy_owner": employee_id, "codeword": codeword}, ()


def _half_page(template: Template, slots: tuple[Slot, ...], key: bytes, roster: list[str],
               leaker: str, public: Path, rng: random.Random) -> tuple[Path, dict, tuple]:
    """Case 5: ~35% of lines survive, chosen where leaker and twin agree, plus logs."""
    twin = rng.choice([item for item in roster if item != leaker])
    words = {item: generate_codeword(key, item, len(slots)) for item in (leaker, twin)}
    text = render_text(template, slots, words[leaker])
    canonical = template.render([0] * len(template.choices))
    lines, start, agree = canonical.split("\n"), 0, []
    for number, line in enumerate(lines):
        inside = [s for s in slots if start <= s.source_offset < start + len(line) + 1]
        if inside and all(words[leaker][s.index] == words[twin][s.index] for s in inside):
            agree.append(number)
        start += len(line) + 1
    keep = sorted(rng.sample(agree, max(1, min(len(agree), round(0.35 * len(lines))))))
    evidence = public / "forum_post.txt"
    evidence.write_text(ce.partial_leak(text, keep), encoding="utf-8")
    opened = rng.sample([item for item in roster if item not in (leaker, twin)], 4)
    access = {leaker: ("direct", "after_hours_download"), twin: ("indirect", "")}
    access.update({item: ("direct", "") for item in opened})
    logs = _write_logs(public / "access_logs.csv", _access_rows(roster, access))
    leave = ce.write_rows(public / "leave_calendar.csv", ["employee_id", "note"],
                          [(twin, "on leave during the leak window")])
    return evidence, {"copy_owner": leaker, "tied_with": twin, "kept_lines": keep}, (logs, leave)


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
    template = parse_template(split_front_matter(source_path.read_text(encoding="utf-8"))[1])
    effective_seed = seed + definition.seed_offset
    rng = random.Random(effective_seed)
    key = hashlib.sha256(
        f"MoleHunt case seed v1\0{definition.case_id}\0{effective_seed}".encode()
    ).digest()
    slots = allocate_slots(template, key)
    roster = [f"E{index:03}" for index in range(1, employee_count + 1)]
    public, private = output / "public", output / "private"
    public.mkdir(parents=True)
    private.mkdir()
    roster_path = public / "employees.csv"
    _write_roster(roster_path, roster)

    if definition.generator == "collusion":
        biases = generate_tardos_biases(key, len(slots))
        codewords = {item: generate_tardos_codeword(key, item, biases) for item in roster}
        colluders = tuple(sorted(rng.sample(roster, 2)))
        merged = list(collude_bits([codewords[i] for i in colluders], "majority", seed=effective_seed))
        noisy = sorted(rng.sample(range(len(merged)), max(1, len(merged) // 50)))
        for index in noisy:
            merged[index] ^= 1
        evidence = public / "leak.txt"
        evidence.write_text(template.render(bits_in_source_order(slots, merged)), encoding="utf-8")
        _write_registry(public / "tardos_registry.csv", slots, codewords)
        ce.write_rows(public / "tardos_biases.csv", ["slot", "bias"], [
            (slot.source_index + 1, f"{biases[slot.index]:.6f}")
            for slot in sorted(slots, key=lambda item: item.source_index)])
        truth: dict[str, Any] = {"colluders": colluders, "biases": biases,
                                 "candidate_codewords": codewords, "strategy": "majority",
                                 "noise_slots": noisy}
        auxiliary: tuple[Path, ...] = ()
    else:
        employee_id = rng.choice(roster)
        if definition.generator == "log_fusion":
            evidence, truth, auxiliary = _half_page(template, slots, key, roster, employee_id,
                                                    public, rng)
        else:
            evidence, truth, auxiliary = _single_copy(
                definition, template, slots, key, roster, employee_id, public, rng)
        _write_registry(public / "registry.csv", slots, {
            item: generate_codeword(key, item, len(slots)) for item in roster})
        if definition.generator == "account_sharing":
            account = next(candidate for candidate in roster if candidate != employee_id)
            fusion = _write_logs(public / "account_logs.csv",
                                 [(employee_id, "direct", "badge_entry"),
                                  (account, "indirect", "unusual_auth")])
            logs, extra = ce.account_logs(public, roster, employee_id, account, rng)
            auxiliary = (fusion, *logs)
            truth.update({"account_sharing_hypothesis": account, "copy_owner": employee_id,
                          **extra})

    private.joinpath("ground_truth.json").write_text(
        json.dumps({"case_id": definition.case_id, "seed": effective_seed,
                    "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(), **truth},
                   indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return CaseInstance(definition, effective_seed, source_path.resolve(), public, evidence,
                        roster_path, auxiliary, private / "ground_truth.json")
