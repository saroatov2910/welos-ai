"""Compute fraud statistics from the local audit log.

Runs entirely on the local machine: no network, no AI. Only the aggregated
numbers it returns are ever sent to the analyst model, never single
transactions, card numbers or customer IDs.

Usage:
    python stats.py path/to/decisions.jsonl
"""

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

DECISIONS = ("accept", "review", "reject")
BANDS = ("under 400", "400-999", "1000-2999", "3000+")


def load_events(path: str) -> list[dict]:
    """Read the audit log: one JSON object per line."""
    events = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def amount_band(amount: float) -> str:
    """Put an amount into the same bands the risk rules use."""
    if amount >= 3000:
        return "3000+"
    if amount >= 1000:
        return "1000-2999"
    if amount >= 400:
        return "400-999"
    return "under 400"


def count_decisions(decisions: list[dict]) -> dict:
    """How many transactions were accepted, sent to review and rejected."""
    counts = Counter(d["decision"] for d in decisions)
    total = len(decisions)
    return {
        "transactions_checked": total,
        **{name: counts[name] for name in DECISIONS},
        "reject_rate_percent": round(100 * counts["reject"] / total, 1)
        if total
        else 0.0,
    }


def count_blocks(events: list[dict]) -> dict:
    """Cards blocked automatically or by the security manager, and cards released."""
    blocked = [e["payload"] for e in events if e["event"] == "card_blocked"]
    released = [e for e in events if e["event"] == "card_unblocked"]
    return {
        "cards_blocked_automatically": sum(
            1 for b in blocked if b.get("blocked_by") == "system"
        ),
        "cards_blocked_manually": sum(
            1 for b in blocked if b.get("blocked_by") != "system"
        ),
        "cards_released": len(released),
    }


def amount_stats(decisions: list[dict]) -> dict:
    """Total, average and largest amount for each decision."""
    result = {}
    for name in DECISIONS:
        amounts = [d["amount"] for d in decisions if d["decision"] == name]
        result[name] = {
            "count": len(amounts),
            "total": round(sum(amounts), 2),
            "average": round(sum(amounts) / len(amounts), 2) if amounts else 0.0,
            "largest": max(amounts, default=0),
        }
    return result


def band_stats(decisions: list[dict]) -> dict:
    """Transactions and rejections in each amount band."""
    result = {band: {"transactions": 0, "rejected": 0} for band in BANDS}
    for d in decisions:
        band = result[amount_band(d["amount"])]
        band["transactions"] += 1
        if d["decision"] == "reject":
            band["rejected"] += 1
    return result


def reason_counts(decisions: list[dict]) -> dict:
    """How often each risk rule fired, most frequent first."""
    counts = Counter(reason for d in decisions for reason in d.get("reasons", []))
    return dict(counts.most_common())


def hourly_counts(decisions: list[dict]) -> dict:
    """Transactions per hour of the day (UTC), only hours that had traffic."""
    hours = Counter(
        datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")).hour
        for d in decisions
    )
    return {f"{hour:02d}:00": hours[hour] for hour in sorted(hours)}


def time_period(decisions: list[dict]) -> dict:
    """First and last transaction time covered by these statistics."""
    times = sorted(d["timestamp"] for d in decisions)
    return {"from": times[0] if times else None, "to": times[-1] if times else None}


def compute_stats(events: list[dict]) -> dict:
    """Turn raw audit events into the aggregated statistics the analyst receives."""
    decisions = [e["payload"] for e in events if e["event"] == "decision_created"]
    currencies = sorted({d["currency"] for d in decisions})
    return {
        "period": time_period(decisions),
        "currencies": currencies,
        "totals": count_decisions(decisions),
        "fraud_caught": {
            "rejected_transactions": sum(
                1 for d in decisions if d["decision"] == "reject"
            ),
            "amount_stopped": round(
                sum(d["amount"] for d in decisions if d["decision"] == "reject"), 2
            ),
            **count_blocks(events),
        },
        "amounts": amount_stats(decisions),
        "amount_bands": band_stats(decisions),
        "reasons": reason_counts(decisions),
        "transactions_per_hour": hourly_counts(decisions),
    }


if __name__ == "__main__":
    stats = compute_stats(load_events(sys.argv[1]))
    print(json.dumps(stats, indent=2))
