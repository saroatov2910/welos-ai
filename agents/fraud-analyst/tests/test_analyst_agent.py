from analyst_agent import build_message, fake_report
from stats import compute_stats

EVENTS = [
    {
        "event": "decision_created",
        "payload": {
            "decision": "reject",
            "amount": 3500,
            "risk_score": 95,
            "currency": "USD",
            "reasons": ["amount_extremely_high"],
            "timestamp": "2026-10-11T02:00:00Z",
            "customer_id": "dana-cohen",
            "transaction_id": "tx-secret-42",
            "card_number_masked": "************4242",
            "card_expiry": "12/29",
        },
    },
    {
        "event": "card_blocked",
        "payload": {
            "blocked_by": "system",
            "card_last4": "4242",
            "block_id": "a91f3c8e",
        },
    },
]


def test_message_to_model_has_no_customer_or_card_data():
    message = build_message(compute_stats(EVENTS))

    for private in ("dana-cohen", "tx-secret-42", "4242", "12/29", "a91f3c8e"):
        assert private not in message


def test_message_to_model_has_the_aggregates():
    message = build_message(compute_stats(EVENTS))

    assert '"transactions_checked": 1' in message
    assert '"amount_stopped": 3500' in message


def test_fake_report_uses_the_numbers():
    report = fake_report(compute_stats(EVENTS))

    assert "1 transactions checked" in report
    assert "3,500.00 USD stopped" in report
    assert "1 cards blocked automatically" in report
