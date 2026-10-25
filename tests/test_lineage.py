"""Leak family tree: layered codewords reveal the forwarding path."""

from pathlib import Path

import pytest

from molehunt.analysis import analyze_prepared
from molehunt.attacks.transform import attack_text
from molehunt.core.autoslots import prepare_master
from molehunt.core.codes import generate_codeword
from molehunt.core.lineage import (
    ForwardLog,
    layer_evidence,
    layer_of,
    path_codeword,
    path_codewords,
    path_id,
    tree_lines,
)
from molehunt.core.render import render_text

KEY = bytes(range(32))
MASTER = Path(__file__).parents[1] / "data" / "masters" / "m1_roadmap.md"
ROSTER = [f"E{i:03}" for i in range(1, 13)]


def test_direct_copy_is_the_ordinary_codeword_and_layers_split_the_slots() -> None:
    assert path_codeword(KEY, ["E007"], 200) == generate_codeword(KEY, "E007", 200)
    layers = [layer_of(KEY, index) for index in range(2000)]
    assert 0.45 < layers.count(0) / 2000 < 0.55 and layers.count(2) > 400


def test_forwarded_leak_reveals_the_full_path(tmp_path) -> None:
    log = ForwardLog(tmp_path / "r.sqlite3")
    middle = log.forward("E007", "C12")
    press = log.forward(middle, "P01")
    log.forward("E003", "C02")
    paths = ROSTER + log.paths()
    prepared = prepare_master(MASTER.read_text(encoding="utf-8"), KEY)
    bits = path_codeword(KEY, press.split(">"), len(prepared.slots))
    leak = attack_text(render_text(prepared.template, prepared.slots, bits), "A5")
    result = analyze_prepared(prepared, leak, path_codewords(KEY, paths, len(prepared.slots)))
    assert result.decision().candidate_id == "E007>C12>P01"
    evidence = layer_evidence(KEY, press, result.observations)
    assert [item.holder for item in evidence] == ["E007", "C12", "P01"]
    assert all(item.matches > 0.8 * item.slots for item in evidence)
    drawing = "\n".join(tree_lines(paths, "E007>C12>P01"))
    assert "P01  <== leak" in drawing and "C12 *" in drawing and "C02" in drawing


def test_middle_holder_leak_is_not_blamed_on_the_recipient(tmp_path) -> None:
    log = ForwardLog(tmp_path / "r.sqlite3")
    log.forward("E007", "C12")
    paths = ROSTER + log.paths()
    prepared = prepare_master(MASTER.read_text(encoding="utf-8"), KEY)
    bits = path_codeword(KEY, ["E007"], len(prepared.slots))
    text = render_text(prepared.template, prepared.slots, bits)
    result = analyze_prepared(prepared, text, path_codewords(KEY, paths, len(prepared.slots)))
    assert result.decision().candidate_id == "E007"


@pytest.mark.parametrize("bad", [[], ["a", "b", "c", "d"], ["a>b"], [""]])
def test_bad_paths_are_rejected(bad) -> None:
    with pytest.raises(ValueError):
        path_id(bad)
