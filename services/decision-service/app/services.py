import json
import os
import re
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException

try:
    import boto3
except ImportError:  # pragma: no cover - optional in local dev until installed
    boto3 = None


decisions_store: dict[str, dict[str, Any]] = {}
card_fingerprints: dict[str, dict] = {}


POLICY_THRESHOLDS = {
    "review_min_score": 40,
    "reject_min_score": 70,
}


VELOCITY_WINDOW_MINUTES = 10


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _get_s3_client():
    if boto3 is None:
        return None

    region_name = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    return boto3.client("s3", region_name=region_name)


def store_audit_event(event_name: str, payload: dict[str, Any]) -> None:
    if not _env_flag("ENABLE_S3_AUDIT"):
        return

    bucket_name = os.getenv("S3_AUDIT_BUCKET")
    if not bucket_name:
        raise HTTPException(status_code=500, detail="S3_AUDIT_BUCKET is not configured")

    s3_client = _get_s3_client()
    if s3_client is None:
        raise HTTPException(status_code=500, detail="boto3 is not installed")

    prefix = os.getenv("S3_AUDIT_PREFIX", "audit").strip().strip("/")
    event_timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    object_key = f"{prefix}/{event_name}/{event_timestamp}-{payload.get('transaction_id', 'event')}.json"

    s3_client.put_object(
        Bucket=bucket_name,
        Key=object_key,
        Body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )


def validate_currency_code(currency: str) -> None:
    if not re.fullmatch(r"[A-Za-z]{3}", currency):
        raise HTTPException(status_code=400, detail="Invalid currency code")


def calculate_velocity_risk(transaction_id: str, event_timestamp: str) -> tuple[int, list[str]]:
    event_time = _parse_timestamp(event_timestamp)
    attempts_in_window = 0

    for existing_transaction_id, decision in decisions_store.items():
        if existing_transaction_id == transaction_id:
            continue

        stored_timestamp = decision.get("timestamp")
        if not isinstance(stored_timestamp, str):
            continue

        stored_time = _parse_timestamp(stored_timestamp)
        delta_seconds = (event_time - stored_time).total_seconds()

        # Count only historical attempts that occurred in the last 10 minutes.
        if 0 <= delta_seconds <= VELOCITY_WINDOW_MINUTES * 60:
            attempts_in_window += 1

    if attempts_in_window >= 5:
        return 30, ["too_many_attempts_10m_critical"]
    if attempts_in_window >= 3:
        return 15, ["too_many_attempts_10m"]
    return 0, []


def mask_card_number(card_number: str) -> str:
    visible_digits = 4
    if len(card_number) <= visible_digits:
        return card_number
    return "*" * (len(card_number) - visible_digits) + card_number[-visible_digits:]


def _digits_only(value: str) -> str:
    return re.sub(r"\D", "", value)


def _is_luhn_valid(card_number: str) -> bool:
    total = 0
    reverse_digits = card_number[::-1]
    for idx, char in enumerate(reverse_digits):
        digit = int(char)
        if idx % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def validate_card_number(card_number: str) -> str:
    normalized = _digits_only(card_number)
    if not normalized.isdigit() or not 12 <= len(normalized) <= 19:
        raise HTTPException(status_code=400, detail="Invalid card number format")
    if not _is_luhn_valid(normalized):
        raise HTTPException(status_code=400, detail="Invalid card number")
    return normalized


def validate_cvv(card_cvv: str) -> None:
    if not re.fullmatch(r"\d{3,4}", card_cvv):
        raise HTTPException(status_code=400, detail="Invalid CVV")


def validate_card_expiry(card_expiry: str) -> None:
    match = re.fullmatch(r"(0[1-9]|1[0-2])/(\d{2})", card_expiry)
    if match is None:
        raise HTTPException(status_code=400, detail="Invalid card expiry format, expected MM/YY")

    month = int(match.group(1))
    year = 2000 + int(match.group(2))
    now = datetime.now(UTC)
    current_month_start = datetime(now.year, now.month, 1)
    expiry_month_start = datetime(year, month, 1)
    if expiry_month_start < current_month_start:
        raise HTTPException(status_code=400, detail="Card is expired")


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


def calculate_risk_score_and_reasons(
    transaction_id: str,
    amount: float,
    currency: str,
    timestamp: str,
) -> tuple[int, list[str]]:
    risk_score = 0
    reasons: list[str] = []

    if amount >= 3000:
        risk_score += 80
        reasons.append("amount_extremely_high")
    elif amount >= 1000:
        risk_score += 45
        reasons.append("amount_high")
    elif amount >= 400:
        risk_score += 25
        reasons.append("amount_elevated")

    event_time = _parse_timestamp(timestamp)
    if event_time.hour < 5:
        risk_score += 15
        reasons.append("off_hours_transaction")

    if amount >= 1000 and amount.is_integer():
        risk_score += 10
        reasons.append("round_amount_pattern")

    velocity_score, velocity_reasons = calculate_velocity_risk(transaction_id, timestamp)
    risk_score += velocity_score
    reasons.extend(velocity_reasons)

    return min(risk_score, 100), reasons


def make_policy_decision(risk_score: int) -> str:
    if risk_score >= POLICY_THRESHOLDS["reject_min_score"]:
        return "reject"
    if risk_score >= POLICY_THRESHOLDS["review_min_score"]:
        return "review"
    return "accept"


def save_transaction_decision(
    transaction_id: str,
    amount: float,
    currency: str,
    card_number: str,
    card_cvv: str,
    card_expiry: str,
    timestamp: str,
) -> dict[str, Any]:
    validate_currency_code(currency)
    normalized_card_number = validate_card_number(card_number)
    validate_cvv(card_cvv)
    validate_card_expiry(card_expiry)
    risk_score, reasons = calculate_risk_score_and_reasons(transaction_id, amount, currency, timestamp)
    decision_status = make_policy_decision(risk_score)

    masked_card = mask_card_number(normalized_card_number)
    decision = {
        "decision_id": transaction_id,
        "transaction_id": transaction_id,
        "decision": decision_status,
        "risk_score": risk_score,
        "reasons": reasons,
        "policy_thresholds": POLICY_THRESHOLDS,
        "amount": amount,
        "currency": currency,
        "card_number_masked": masked_card,
        "card_expiry": card_expiry,
        "timestamp": timestamp,
    }
    decisions_store[transaction_id] = decision
    try:
        store_audit_event("decision_created", decision)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - audit should not break core flow
        raise HTTPException(status_code=500, detail=f"Failed to write S3 audit event: {exc}") from exc
    return decision


def get_decision_or_404(decision_id: str) -> dict[str, Any]:
    decision = decisions_store.get(decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision
