"""Card blocklist.

A blocked card is identified by an HMAC fingerprint of its number, keyed with
CARD_HASH_KEY. The card number itself is never stored, and the fingerprint is
useless without the key. Only blocked cards get a fingerprint.
"""

import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException

AUTO_BLOCK_MIN_SCORE = 90
AUTO_BLOCK_HOURS = 24

# fingerprint -> block record. In memory for now; Redis is on the roadmap.
_blocks: dict[str, dict[str, Any]] = {}


def _now() -> datetime:
    return datetime.now(UTC)


def card_fingerprint(card_number: str) -> str:
    key = os.getenv("CARD_HASH_KEY", "")
    if not key:
        # Fail closed, like the API key: no key, no blocking, no decisions.
        raise HTTPException(status_code=503, detail="Card blocking is not configured")
    return hmac.new(key.encode(), card_number.encode(), hashlib.sha256).hexdigest()


def _public(record: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in record.items() if k != "fingerprint"}


def get_active_block(card_number: str) -> dict[str, Any] | None:
    fingerprint = card_fingerprint(card_number)
    record = _blocks.get(fingerprint)
    if record is None:
        return None
    expires_at = record["expires_at"]
    if expires_at is not None and datetime.fromisoformat(expires_at) <= _now():
        del _blocks[fingerprint]
        return None
    return _public(record)


def block_card(card_number: str, reason: str, blocked_by: str, hours: int | None) -> dict[str, Any]:
    fingerprint = card_fingerprint(card_number)
    now = _now()
    record = {
        "block_id": fingerprint[:16],
        "fingerprint": fingerprint,
        "card_last4": card_number[-4:],
        "reason": reason,
        "blocked_by": blocked_by,
        "blocked_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(hours=hours)).isoformat().replace("+00:00", "Z") if hours else None,
    }
    _blocks[fingerprint] = record
    return _public(record)


def list_blocks() -> list[dict[str, Any]]:
    return [_public(record) for record in _blocks.values()]


def unblock(block_id: str) -> dict[str, Any] | None:
    for fingerprint, record in list(_blocks.items()):
        if record["block_id"] == block_id:
            del _blocks[fingerprint]
            return _public(record)
    return None


def clear() -> None:
    _blocks.clear()
