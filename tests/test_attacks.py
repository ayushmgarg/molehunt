"""Tests for deterministic text and print-scan attacks."""

from PIL import Image

from molehunt.attacks.transform import attack_text, simulate_print_scan


def test_a1_strips_invisible_format_characters() -> None:
    assert attack_text("A\u200bB", "A1", strength=1) == "AB"


def test_a2_applies_nfkc() -> None:
    assert attack_text("\uff21\uff22\uff23", "A2", strength=1) == "ABC"


def test_a2b_maps_supported_confusables() -> None:
    assert attack_text("p\u0430yp\u0430l", "A2b", strength=1) == "paypal"


def test_a3_collapses_whitespace_and_nbsp() -> None:
    assert attack_text("A\u00a0  B\nC", "A3", strength=1) == "A B C"


def test_a4_normalizes_punctuation() -> None:
    assert attack_text("\u201cwait\u201d\u2014yes\u2026", "A4", strength=1) == '"wait"-yes...'


def test_a5_plain_retype_removes_invisibles_and_metadata_like_spacing() -> None:
    assert attack_text("A\u200b  B\r\nC", "A5", strength=1) == "A B C"


def test_a6_canonicalizes_supplied_variants() -> None:
    assert attack_text("The colour is here.", "A6", variants=[("color", "colour")]) == (
        "The color is here."
    )


def test_a7_paraphrase_uses_seeded_suggestions() -> None:
    assert attack_text("Please begin now.", "A7", strength=1, seed=12) == (
        attack_text("Please begin now.", "A7", strength=1, seed=12)
    )
    assert attack_text("Please begin now.", "A7", strength=1, seed=1) != "Please begin now."


def test_a8_truncates_by_retained_paragraph_fraction() -> None:
    assert attack_text("One\n\nTwo\n\nThree\n\nFour", "A8", strength=0.5) == "One\n\nTwo"


def test_a9_reorders_paragraphs_with_seed() -> None:
    first = attack_text("One\n\nTwo\n\nThree", "A9", strength=1, seed=2)
    assert first == attack_text("One\n\nTwo\n\nThree", "A9", strength=1, seed=2)
    assert sorted(first.split("\n\n")) == ["One", "Three", "Two"]


def test_a10_noise_is_seeded_and_strength_zero_is_identity() -> None:
    text = "Synthetic evidence text."
    assert attack_text(text, "A10", strength=0) == text
    assert attack_text(text, "A10", strength=1, seed=5) == attack_text(
        text, "A10", strength=1, seed=5
    )
    assert attack_text(text, "A10", strength=1, seed=5) != text


def test_a11_print_scan_preserves_dimensions_and_is_seeded() -> None:
    source = Image.new("RGB", (96, 64), "white")
    first = simulate_print_scan(source, strength=0.5, seed=7)
    second = simulate_print_scan(source, strength=0.5, seed=7)
    assert first.size == source.size
    assert first.tobytes() == second.tobytes()


def test_unknown_attack_is_rejected() -> None:
    try:
        attack_text("text", "A99")
    except ValueError as error:
        assert "attack" in str(error)
    else:
        raise AssertionError("unknown attack must fail")


def test_a11_text_ocr_model_drops_invisible_and_typography_then_adds_char_errors() -> None:
    text = "Plan\u200b to \u0420ay \u201cnow\u201d\u00a0\u2014 fast.  " * 40
    clean = attack_text(text, "A11", strength=0.0001, seed=3)
    assert "\u200b" not in clean and "\u0420" not in clean and "\u00a0" not in clean
    assert "\u201c" not in clean and "\u2014" not in clean and "  " not in clean
    noisy = attack_text(text, "A11", strength=1.0, seed=3)
    assert noisy == attack_text(text, "A11", strength=1.0, seed=3)
    changed = sum(a != b for a, b in zip(clean, noisy, strict=False))
    assert 0 < changed < 0.06 * len(clean)


def test_attack_chain_applies_steps_in_order_with_derived_seeds() -> None:
    from molehunt.attacks.transform import attack_chain

    text = "Begin\u200b \u201cthe\u201d   plan.\n\nSecond part.\n\nThird part."
    chained = attack_chain(text, ("A1", "A3", "A4"), strength=1.0, seed=2)
    assert chained == 'Begin "the" plan. Second part. Third part.'
    assert chained == attack_chain(text, ("A1", "A3", "A4"), strength=1.0, seed=2)
