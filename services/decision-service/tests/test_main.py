from fastapi.testclient import TestClient

from app.main import app
from app.services import decisions_store

client = TestClient(app)


def setup_function():
    decisions_store.clear()


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_returns_ready_true():
    response = client.get("/readiness")

    assert response.status_code == 200
    assert response.json() == {"ready": True}


def test_decide_transaction_and_fetch_by_id():
    payload = {
        "customer_id": "cust-1",
        "transaction_id": "tx-001",
        "amount": 125.5,
        "currency": "USD",
        "card_number": "4242 4242 4242 4242",
        "card_cvv": "123",
        "card_expiry": "12/99",
        "timestamp": "2026-10-04T10:00:00Z",
    }

    create_response = client.post("/decide_transaction", json=payload)

    assert create_response.status_code == 200
    body = create_response.json()
    assert body["decision_id"] == "tx-001"
    assert body["decision"] == "accept"
    assert body["risk_score"] < 40
    assert body["reasons"] == []
    assert body["card_number_masked"] == "************4242"
    assert "card_cvv" not in body

    get_response = client.get("/decisions/tx-001")

    assert get_response.status_code == 200
    assert get_response.json()["transaction_id"] == "tx-001"


def test_decide_transaction_rejects_invalid_cvv():
    payload = {
        "customer_id": "cust-1",
        "transaction_id": "tx-002",
        "amount": 80.0,
        "currency": "USD",
        "card_number": "4242424242424242",
        "card_cvv": "12a",
        "card_expiry": "12/99",
        "timestamp": "2026-10-04T10:00:00Z",
    }

    response = client.post("/decide_transaction", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid CVV"


def test_decide_transaction_rejects_invalid_expiry_format():
    payload = {
        "customer_id": "cust-1",
        "transaction_id": "tx-003",
        "amount": 80.0,
        "currency": "USD",
        "card_number": "4242424242424242",
        "card_cvv": "123",
        "card_expiry": "13/30",
        "timestamp": "2026-10-04T10:00:00Z",
    }

    response = client.post("/decide_transaction", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid card expiry format, expected MM/YY"


def test_get_decision_by_id_returns_404_when_missing():
    response = client.get("/decisions/not-found")

    assert response.status_code == 404
    assert response.json()["detail"] == "Decision not found"


def test_decide_transaction_returns_review_for_elevated_risk():
    payload = {
        "customer_id": "cust-1",
        "transaction_id": "tx-004",
        "amount": 1200.0,
        "currency": "USD",
        "card_number": "4242424242424242",
        "card_cvv": "123",
        "card_expiry": "12/99",
        "timestamp": "2026-10-04T10:00:00Z",
    }

    response = client.post("/decide_transaction", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "review"
    assert body["risk_score"] >= 40
    assert "amount_high" in body["reasons"]


def test_decide_transaction_returns_reject_for_high_risk():
    payload = {
        "customer_id": "cust-1",
        "transaction_id": "tx-005",
        "amount": 3500.0,
        "currency": "USD",
        "card_number": "4242424242424242",
        "card_cvv": "123",
        "card_expiry": "12/99",
        "timestamp": "2026-10-04T02:10:00Z",
    }

    response = client.post("/decide_transaction", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "reject"
    assert body["risk_score"] >= 70
    assert "amount_extremely_high" in body["reasons"]


def test_decide_transaction_allows_any_currency_when_whitelist_disabled():
    payload = {
        "customer_id": "cust-1",
        "transaction_id": "tx-006",
        "amount": 150.0,
        "currency": "XYZ",
        "card_number": "4242424242424242",
        "card_cvv": "123",
        "card_expiry": "12/99",
        "timestamp": "2026-10-04T10:00:00Z",
    }

    response = client.post("/decide_transaction", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert "unsupported_currency" not in body["reasons"]


def test_decide_transaction_rejects_timestamp_without_timezone():
    payload = {
        "customer_id": "cust-1",
        "transaction_id": "tx-007",
        "amount": 100.0,
        "currency": "USD",
        "card_number": "4242424242424242",
        "card_cvv": "123",
        "card_expiry": "12/99",
        "timestamp": "2026-10-04T10:00:00",
    }

    response = client.post("/decide_transaction", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "Timestamp must include timezone (e.g. Z)"


def test_s3_debug_endpoints_are_not_exposed():
    assert client.get("/s3/connection").status_code == 404
    assert client.get("/s3/files", params={"bucket_name": "any"}).status_code == 404


def _decide(transaction_id, customer_id, timestamp):
    return client.post(
        "/decide_transaction",
        json={
            "customer_id": customer_id,
            "transaction_id": transaction_id,
            "amount": 10.0,
            "currency": "USD",
            "card_number": "4242424242424242",
            "card_cvv": "123",
            "card_expiry": "12/99",
            "timestamp": timestamp,
        },
    )


def test_velocity_ignores_other_customers():
    for i in range(3):
        _decide(f"other-{i}", "cust-A", "2026-10-04T10:00:00Z")

    body = _decide("tx-v1", "cust-B", "2026-10-04T10:05:00Z").json()

    assert "too_many_attempts_10m" not in body["reasons"]


def test_velocity_flags_same_customer():
    for i in range(3):
        _decide(f"same-{i}", "cust-A", "2026-10-04T10:00:00Z")

    body = _decide("tx-v2", "cust-A", "2026-10-04T10:05:00Z").json()

    assert "too_many_attempts_10m" in body["reasons"]
