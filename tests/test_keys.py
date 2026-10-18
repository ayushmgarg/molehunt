"""Contract tests for deterministic, domain-separated keyed primitives."""

import hashlib
import hmac

import pytest

from molehunt.core.keys import create_key, digest, keyed_order, load_or_create_key, lowest_bit


def test_digest_matches_hmac_sha256_with_framed_domain() -> None:
    key = bytes(range(32))
    expected = hmac.new(key, b"molehunt:v1\x00\x03doc\x00\x01a", hashlib.sha256).digest()
    assert digest(key, "doc", b"a") == expected


def test_digest_separates_domains_and_parts() -> None:
    key = b"k" * 32
    assert digest(key, "copy", b"ab") != digest(key, "slot", b"ab")
    assert digest(key, "copy", b"a", b"b") != digest(key, "copy", b"ab")


def test_lowest_bit_is_stable_and_binary() -> None:
    value = digest(b"k" * 32, "codeword", b"employee-1", b"0")
    assert lowest_bit(value) == (value[-1] & 1)
    assert lowest_bit(value) in (0, 1)


def test_keyed_order_is_a_stable_permutation() -> None:
    first = keyed_order(b"k" * 32, "placement", 128)
    assert first == keyed_order(b"k" * 32, "placement", 128)
    assert sorted(first) == list(range(128))
    assert first != keyed_order(b"z" * 32, "placement", 128)


def test_keyed_order_rejects_negative_size() -> None:
    with pytest.raises(ValueError):
        keyed_order(b"k" * 32, "placement", -1)


def test_create_key_has_requested_length() -> None:
    assert len(create_key()) == 32
    assert len(create_key(48)) == 48


def test_load_or_create_key_is_idempotent(tmp_path) -> None:
    path = tmp_path / "molehunt.key"
    first = load_or_create_key(path)
    assert len(first) == 32
    assert load_or_create_key(path) == first


def test_load_or_create_key_rejects_invalid_existing_key(tmp_path) -> None:
    path = tmp_path / "bad.key"
    path.write_bytes(b"short")
    with pytest.raises(ValueError, match="32 bytes"):
        load_or_create_key(path)
