from datetime import datetime
from typing import Any

from fastapi import HTTPException


decisions_store: dict[str, dict[str, Any]] = {}


def mask_card_number(card_number: str) -> str:
    visible_digits = 4
    if len(card_number) <= visible_digits:
        return card_number
    return "*" * (len(card_number) - visible_digits) + card_number[-visible_digits:]


def _parse_timestamp(timestamp: str) -> datetime:
    # Accept a common Z-suffixed ISO timestamp and normalize to datetime.
    
    normalized = timestamp.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid timestamp format") from exc
    if parsed.tzinfo is None:
        raise HTTPException(status_code=400, detail="Timestamp must include timezone (e.g. Z)")
    return parsed


def save_transaction_decision(
    transaction_id: str,
    amount: float,
    currency: str,
    card_number: str,
    card_expiry: str,
    timestamp: str,
) -> dict[str, Any]:
    masked_card = mask_card_number(card_number)
    decision = {
        "decision_id": transaction_id,
        "transaction_id": transaction_id,
        "decision": "transaction accepted",
        "amount": amount,
        "currency": currency,
        "card_number_masked": masked_card,
        "card_expiry": card_expiry,
        "timestamp": timestamp,
    }
    decisions_store[transaction_id] = decision
    return decision


def get_decision_or_404(decision_id: str) -> dict[str, Any]:
    decision = decisions_store.get(decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision
