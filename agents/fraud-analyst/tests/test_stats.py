from stats import amount_band, compute_stats, load_events


def test_load_events_reads_every_line(tmp_path):
    log = tmp_path / "audit.jsonl"
    log.write_text('{"event": "decision_created"}\n{"event": "card_blocked"}\n')

    events = load_events(str(log))

    assert len(events) == 2
    assert events[0]["event"] == "decision_created"


def test_load_events_skips_empty_lines(tmp_path):
    log = tmp_path / "audit.jsonl"
    log.write_text('{"event": "decision_created"}\n\n\n{"event": "card_blocked"}\n')

    assert len(load_events(str(log))) == 2


def _decision(decision, amount, reasons=(), timestamp="2026-10-11T10:00:00Z"):
    return {
        "event": "decision_created",
        "payload": {
            "decision": decision,
            "amount": amount,
            "currency": "USD",
            "reasons": list(reasons),
            "timestamp": timestamp,
        },
    }


EVENTS = [
    _decision("accept", 120),
    _decision("review", 1200, ["amount_high", "round_amount_pattern"]),
    _decision(
        "reject",
        3500,
        ["amount_extremely_high", "off_hours_transaction"],
        "2026-10-11T02:00:00Z",
    ),
    {"event": "card_blocked", "payload": {"blocked_by": "system"}},
    {"event": "card_blocked", "payload": {"blocked_by": "security-manager"}},
    {"event": "card_unblocked", "payload": {}},
]


def test_amount_band_uses_rule_thresholds():
    assert [amount_band(a) for a in (399, 400, 1000, 3000)] == [
        "under 400",
        "400-999",
        "1000-2999",
        "3000+",
    ]


def test_totals_and_reject_rate():
    totals = compute_stats(EVENTS)["totals"]

    assert totals["transactions_checked"] == 3
    assert (totals["accept"], totals["review"], totals["reject"]) == (1, 1, 1)
    assert totals["reject_rate_percent"] == 33.3


def test_fraud_caught_counts_blocks_and_stopped_amount():
    caught = compute_stats(EVENTS)["fraud_caught"]

    assert caught["rejected_transactions"] == 1
    assert caught["amount_stopped"] == 3500
    assert caught["cards_blocked_automatically"] == 1
    assert caught["cards_blocked_manually"] == 1
    assert caught["cards_released"] == 1


def test_bands_reasons_and_hours():
    stats = compute_stats(EVENTS)

    assert stats["amount_bands"]["3000+"] == {"transactions": 1, "rejected": 1}
    assert stats["reasons"]["amount_high"] == 1
    assert stats["transactions_per_hour"] == {"02:00": 1, "10:00": 2}


def test_empty_log_gives_zeros_not_errors():
    stats = compute_stats([])

    assert stats["totals"]["transactions_checked"] == 0
    assert stats["totals"]["reject_rate_percent"] == 0.0
    assert stats["period"] == {"from": None, "to": None}
