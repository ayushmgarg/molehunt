"""Heatmap, evidence meter, and the examine() hub."""

from pathlib import Path

from molehunt.attacks.transform import attack_chain
from molehunt.core.autoslots import prepare_master
from molehunt.core.canaries import holder_values
from molehunt.core.lineage import path_codeword
from molehunt.core.render import render_text
from molehunt.forensics import examine

KEY = bytes(range(32))
MASTER = Path(__file__).parents[1] / "data" / "masters" / "live" / "m8_midnight_carnival.md"
ROSTER = [f"A{i:02}" for i in range(1, 13)]


def _copy(path: list[str]) -> str:
    prepared = prepare_master(MASTER.read_text(encoding="utf-8"), KEY)
    bits = path_codeword(KEY, path, len(prepared.slots))
    return render_text(prepared.template, prepared.slots, bits,
                       holder_values(prepared.canaries, KEY, ">".join(path)))


def test_clean_copy_heatmap_is_all_green_and_meter_climbs() -> None:
    text = _copy(["A03"])
    found = examine(MASTER.read_text(encoding="utf-8"), KEY, ROSTER, text)
    assert found.decision.candidate_id == "A03" and found.leader == "A03"
    kinds = {segment.kind for segment in found.segments}
    assert "mismatch" not in kinds and {"match", "fact", "plain"} <= kinds
    assert "".join(s.text for s in found.segments) == text
    assert found.curve[-1] >= 2 and found.curve[-1] == max(found.curve[-5:])
    assert found.canaries.scores[0].holder == "A03"
    assert found.scrub.verdict == "no sign of sanitising"


def test_scrubbed_forward_shows_grey_erasures_scrub_flag_and_tree() -> None:
    text = attack_chain(_copy(["A05", "X01"]), ["A1", "A2b", "A3"])
    found = examine(MASTER.read_text(encoding="utf-8"), KEY, ROSTER, text,
                    forwards=["A05>X01", "A02>X09"])
    assert found.decision.candidate_id == "A05>X01"
    assert any(segment.kind == "erased" for segment in found.segments)
    assert found.scrub.verdict == "deliberately sanitised"
    assert [hop.holder for hop in found.hops] == ["A05", "X01"]
    assert any("X01  <== leak" in line for line in found.tree)


def test_paraphrase_without_fingerprint_is_still_caught_by_facts() -> None:
    prepared = prepare_master(MASTER.read_text(encoding="utf-8"), KEY)
    facts = list(holder_values(prepared.canaries, KEY, "A09").values())
    rumour = (f"I heard the new carnival game, codename {facts[0]}, will be shown on "
              f"{facts[3]} at {facts[2]} and it cost {facts[1]}. " * 3)
    found = examine(MASTER.read_text(encoding="utf-8"), KEY, ROSTER, rumour)
    assert found.decision.outcome != "attribute"
    assert found.canaries.scores[0].holder == "A09"
