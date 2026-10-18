"""Classical OCR reads scanned print copies well enough to attribute them."""

from pathlib import Path

from typer.testing import CliRunner

from molehunt.analysis import analyze_text
from molehunt.attacks.transform import simulate_print_scan
from molehunt.channels.ocr import ocr_image, render_page
from molehunt.cli import app
from molehunt.core.autoslots import prepare_master
from molehunt.core.codes import generate_codewords
from molehunt.core.render import render_text

MASTER = Path(__file__).parents[1] / "data" / "masters" / "m2_zoning.md"
KEY = bytes(range(32))


def test_template_ocr_reads_clean_text_exactly() -> None:
    text = "Plan to begin the audit on 18 March.\nThe board will verify 1,200 copies."
    assert ocr_image(render_page(text)) == text


def test_noisy_scan_of_a_copy_is_still_attributed() -> None:
    source = MASTER.read_text(encoding="utf-8")
    prepared = prepare_master(source, KEY)
    roster = [f"E{index:03}" for index in range(1, 21)]
    codewords = generate_codewords(KEY, roster, len(prepared.slots))
    page = render_page(render_text(prepared.template, prepared.slots, codewords["E013"]))
    scan = simulate_print_scan(page, strength=0.4, seed=5)
    decision = analyze_text(source, KEY, roster, ocr_image(scan)).decision()
    assert decision.outcome == "attribute" and decision.candidate_id == "E013"


def test_cli_issues_png_print_copy_and_analyses_it(tmp_path: Path) -> None:
    runner = CliRunner()
    key, db = tmp_path / "k.key", tmp_path / "r.sqlite3"
    runner.invoke(app, ["init", "--key-file", str(key), "--db-file", str(db),
                        "--custody-log", str(tmp_path / "c.log")])
    roster = tmp_path / "roster.csv"
    runner.invoke(app, ["roster", "--count", "10", "-o", str(roster)])
    runner.invoke(app, ["register", str(MASTER), "--master-id", "M", "--key-file", str(key),
                        "--db-file", str(db)])
    copy = tmp_path / "E004.png"
    issued = runner.invoke(app, ["issue", "E004", "--master", "M", "-o", str(copy),
                                 "--key-file", str(key), "--db-file", str(db)])
    assert issued.exit_code == 0, issued.stdout
    result = runner.invoke(app, ["analyze", str(copy), "--master", str(MASTER),
                                 "--employees", str(roster), "--key-file", str(key)])
    assert result.exit_code == 0, result.stdout
    assert "copy issued to E004" in result.stdout
