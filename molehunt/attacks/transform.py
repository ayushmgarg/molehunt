"""Apply deterministic, seeded text attacks and print-scan image degradation."""

from __future__ import annotations

import math
import random
import re
import string
import unicodedata
from collections.abc import Sequence
from io import BytesIO

import numpy as np
from PIL import Image, ImageFilter

from molehunt.channels.homoglyph import confusable_skeleton
from molehunt.channels.lexical import SYNONYM_SUGGESTIONS

_PUNCTUATION = {
    "“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-", "…": "...",
}


def _validate_strength(strength: float) -> None:
    if not math.isfinite(strength) or not 0 <= strength <= 1:
        raise ValueError("attack strength must be between zero and one")


def _case_like(source: str, target: str) -> str:
    if source.isupper():
        return target.upper()
    if source.istitle():
        return target.title()
    return target


def _synonym_map() -> dict[str, str]:
    mapping = {}
    for pair in SYNONYM_SUGGESTIONS:
        mapping[pair.zero.casefold()] = pair.one
        mapping[pair.one.casefold()] = pair.zero
    return mapping


def attack_text(
    text: str,
    attack_id: str,
    *,
    strength: float = 1.0,
    seed: int = 0,
    variants: Sequence[tuple[str, str]] = (),
) -> str:
    """Apply one A1–A11 transform; each random choice derives from ``seed``."""
    _validate_strength(strength)
    rng = random.Random(seed)
    if strength == 0 and attack_id != "A8":
        return text
    if attack_id == "A1":
        return "".join(
            character
            for character in text
            if not (unicodedata.category(character) == "Cf" and rng.random() < strength)
        )
    if attack_id == "A2":
        return "".join(
            unicodedata.normalize("NFKC", character) if rng.random() < strength else character
            for character in text
        )
    if attack_id == "A2b":
        return "".join(
            confusable_skeleton(character) if rng.random() < strength else character
            for character in text
        )
    if attack_id == "A3":
        return re.sub(
            r"\s+",
            lambda match: " " if rng.random() < strength else match.group(0),
            text,
        ).strip()
    if attack_id == "A4":
        return "".join(
            _PUNCTUATION.get(character, character)
            if character in _PUNCTUATION and rng.random() < strength
            else character
            for character in text
        )
    if attack_id == "A5":
        plain = "".join(
            unicodedata.normalize("NFKC", character)
            if rng.random() < strength
            else character
            for character in text
        )
        plain = "".join(
            character
            for character in plain
            if not (unicodedata.category(character) == "Cf" and rng.random() < strength)
        )
        return re.sub(
            r"\s+",
            lambda match: " " if rng.random() < strength else match.group(0),
            plain,
        ).strip()
    if attack_id == "A6":
        result = text
        for zero, one in variants:
            if not zero or not one:
                continue
            pattern = re.compile(rf"(?<!\w){re.escape(one)}(?!\w)", re.IGNORECASE)

            def canonicalize(match: re.Match[str], zero_variant: str = zero) -> str:
                return (
                    _case_like(match.group(0), zero_variant)
                    if rng.random() < strength
                    else match.group(0)
                )

            result = pattern.sub(canonicalize, result)
        return result
    if attack_id == "A7":
        suggestions = _synonym_map()
        pattern = re.compile(r"(?<!\w)[A-Za-z]+(?!\w)")

        def paraphrase(match: re.Match[str]) -> str:
            target = suggestions.get(match.group(0).casefold())
            if target is None or rng.random() >= strength:
                return match.group(0)
            return _case_like(match.group(0), target)

        return pattern.sub(paraphrase, text)
    if attack_id == "A8":
        paragraphs = text.split("\n\n")
        if strength == 0:
            return ""
        keep = min(len(paragraphs), max(1, math.ceil(len(paragraphs) * strength)))
        return "\n\n".join(paragraphs[:keep])
    if attack_id == "A9":
        paragraphs = text.split("\n\n")
        count = min(len(paragraphs), max(2, math.ceil(len(paragraphs) * strength)))
        selected = paragraphs[:count]
        rng.shuffle(selected)
        paragraphs[:count] = selected
        return "\n\n".join(paragraphs)
    if attack_id == "A10":
        def inject(match: re.Match[str]) -> str:
            word = match.group(0)
            output = []
            for character in word:
                if rng.random() < strength:
                    alphabet = string.ascii_uppercase if character.isupper() else string.ascii_lowercase
                    choices = alphabet.replace(character, "")
                    output.append(rng.choice(choices))
                else:
                    output.append(character)
            return "".join(output)

        return re.sub(r"[A-Za-z]+", inject, text)
    if attack_id == "A11":
        return _ocr_model(text, strength, rng)
    raise ValueError(f"unknown text attack: {attack_id}")


OCR_CHAR_ERROR = 0.02


def _ocr_model(text: str, strength: float, rng: random.Random) -> str:
    """A11 on text: a print-then-OCR pass keeps only visible plain characters.

    Invisible marks are lost, look-alikes read as Latin, typography and spacing are
    normalised, then each letter is misread with probability 0.02 * strength.
    """
    plain = "".join(
        _PUNCTUATION.get(character, character)
        for character in confusable_skeleton(unicodedata.normalize("NFKC", text))
        if unicodedata.category(character) != "Cf"
    )
    plain = re.sub(r"\s+", " ", plain).strip()
    output = []
    for character in plain:
        if character.isalpha() and rng.random() < OCR_CHAR_ERROR * strength:
            alphabet = string.ascii_uppercase if character.isupper() else string.ascii_lowercase
            output.append(rng.choice(alphabet.replace(character, "")))
        else:
            output.append(character)
    return "".join(output)


def attack_chain(
    text: str,
    attack_ids: Sequence[str],
    *,
    strength: float = 1.0,
    seed: int = 0,
    variants: Sequence[tuple[str, str]] = (),
) -> str:
    """Apply attacks in order; step k uses seed ``seed * 100 + k`` for independence."""
    for step, attack_id in enumerate(attack_ids):
        text = attack_text(
            text, attack_id, strength=strength, seed=seed * 100 + step, variants=variants
        )
    return text


def simulate_print_scan(
    image: Image.Image,
    *,
    strength: float = 0.5,
    seed: int = 0,
) -> Image.Image:
    """Rotate, blur, add seeded sensor noise, then JPEG-round-trip a page image."""
    _validate_strength(strength)
    output = image.convert("RGB")
    if strength == 0:
        return output.copy()
    rng = random.Random(seed)
    angle = rng.uniform(-4.0, 4.0) * strength
    output = output.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor="white")
    output = output.filter(ImageFilter.GaussianBlur(0.8 * strength))
    array = np.asarray(output).astype(np.float32)
    noise = np.random.default_rng(seed).normal(0, 7.0 * strength, array.shape)
    noisy = np.clip(array + noise, 0, 255).astype(np.uint8)
    output = Image.fromarray(noisy, mode="RGB")
    stream = BytesIO()
    output.save(stream, format="JPEG", quality=max(30, int(95 - 55 * strength)))
    stream.seek(0)
    with Image.open(stream) as scanned:
        return scanned.convert("RGB").copy()
