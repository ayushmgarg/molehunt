"""HMAC-SHA256 primitives with explicit domain separation and length framing."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from pathlib import Path

KEY_BYTES = 32
_PREFIX = b"molehunt:v1"


def _frame(value: bytes) -> bytes:
    """Encode a byte string with a two-byte length prefix."""
    if len(value) > 0xFFFF:
        raise ValueError("HMAC parts must be shorter than 65536 bytes")
    return len(value).to_bytes(2, "big") + value


def digest(key: bytes, domain: str, *parts: bytes | str) -> bytes:
    """Return a framed HMAC digest; a domain prevents cross-purpose reuse."""
    if len(key) != KEY_BYTES:
        raise ValueError(f"key must contain {KEY_BYTES} bytes")
    domain_bytes = domain.encode("utf-8")
    if not domain_bytes:
        raise ValueError("domain must not be empty")
    message = bytearray(_PREFIX)
    message.extend(_frame(domain_bytes))
    for part in parts:
        message.extend(_frame(part.encode("utf-8") if isinstance(part, str) else part))
    return hmac.new(key, message, hashlib.sha256).digest()


def lowest_bit(value: bytes) -> int:
    """Return the least significant bit of the final digest byte."""
    if not value:
        raise ValueError("value must not be empty")
    return value[-1] & 1


def create_key(nbytes: int = KEY_BYTES) -> bytes:
    """Create cryptographically random key material."""
    if nbytes < 16:
        raise ValueError("keys must contain at least 16 bytes")
    return secrets.token_bytes(nbytes)


def load_or_create_key(path: str | Path, nbytes: int = KEY_BYTES) -> bytes:
    """Read an existing key or atomically create it without replacing data."""
    if nbytes < 16:
        raise ValueError("keys must contain at least 16 bytes")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        key = target.read_bytes()
        if len(key) != nbytes:
            raise ValueError(f"key file must contain {nbytes} bytes")
        return key
    key = create_key(nbytes)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(key)
        stream.flush()
        os.fsync(stream.fileno())
    return key


def keyed_order(key: bytes, domain: str, size: int) -> list[int]:
    """Return a deterministic pseudorandom permutation of ``range(size)``."""
    if size < 0:
        raise ValueError("size must be non-negative")
    return sorted(
        range(size),
        key=lambda index: (digest(key, domain, index.to_bytes(8, "big")), index),
    )
