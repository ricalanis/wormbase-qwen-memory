"""Canonical JSON encoding + SHA256 entry hashing + chain verification.

Clean-room port of WormBase's ledger hash semantics (credited): the entry
hash is ``sha256(canonical_json(entry minus the hash field))``. Because
``prev_hash`` lives inside the hashed body, the chain is tamper-evident — any
single-field change anywhere in history breaks verification from that point on.

Canonical JSON rules (byte-identical for byte-identical inputs):
- UTF-8, separators ``,`` / ``:`` only, keys sorted ascending.
- tz-aware datetimes -> RFC 3339 with trailing ``Z`` (fractional zeros trimmed).
- ``bytes`` -> lowercase hex.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

GENESIS_PREV_HASH: bytes = b"\x00" * 32


def _default(o: Any) -> Any:
    if isinstance(o, UUID):
        return str(o)
    if isinstance(o, datetime):
        if o.tzinfo is None:
            raise ValueError("datetimes must be tz-aware to be canonicalized")
        u = o.astimezone(UTC).replace(tzinfo=UTC)
        base = u.strftime("%Y-%m-%dT%H:%M:%S")
        frac = ""
        if u.microsecond:
            frac = f".{u.microsecond:06d}".rstrip("0").rstrip(".")
        return base + frac + "Z"
    if isinstance(o, (bytes, bytearray)):
        return bytes(o).hex()
    raise TypeError(f"Unserializable type: {type(o).__name__}")


def canonical_json(entry: dict[str, Any]) -> str:
    """Render ``entry`` (minus the ``hash`` field) as canonical UTF-8 JSON."""
    view = {k: v for k, v in entry.items() if k != "hash"}
    return json.dumps(
        view,
        sort_keys=True,
        separators=(",", ":"),
        default=_default,
        ensure_ascii=False,
    )


def compute_entry_hash(entry: dict[str, Any]) -> bytes:
    """32-byte SHA256 of ``canonical_json(entry minus hash)``."""
    return hashlib.sha256(canonical_json(entry).encode("utf-8")).digest()


def content_hash(obj: Any) -> str:
    """Stable hex digest of an arbitrary JSON-able object (for value/input hashes)."""
    payload = json.dumps(
        obj, sort_keys=True, separators=(",", ":"), default=_default, ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_chain(entries: Iterable[dict[str, Any]]) -> tuple[bool, int | None]:
    """Walk ``entries`` in seq order and verify the hash chain.

    Returns ``(ok, broken_at)`` where ``broken_at`` is the 0-based index of the
    first failing entry, or ``None`` when the whole chain is intact.
    """
    prev = GENESIS_PREV_HASH
    for i, e in enumerate(entries):
        if e.get("prev_hash") != prev:
            return False, i
        expected = compute_entry_hash(e)
        if e.get("hash") != expected:
            return False, i
        prev = expected
    return True, None
