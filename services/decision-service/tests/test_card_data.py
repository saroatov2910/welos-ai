"""PCI DSS: the full card number and the CVV never leave the service.

Every test sends a test card and a CVV, then searches everything the service
returns or writes for them: responses, error responses and the audit log.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app import blocklist
from app.main import app
from app.services import decisions_store
from tests.conftest import TEST_API_KEY
from tests.data import VISA, transaction

CVV = "987"

client = TestClient(app, headers={"X-API-Key": TEST_API_KEY})


@pytest.fixture(autouse=True)
def audit_log(tmp_path, monkeypatch):
    decisions_store.clear()
    blocklist.clear()
    path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("AUDIT_LOG_PATH", str(path))
    return path


def assert_no_card_data(text):
    assert VISA not in text, "full card number leaked"
    assert f'"{CVV}"' not in text, "CVV leaked"


def test_responses_never_contain_card_data():
    responses = [
        client.post("/decide_transaction", json=transaction(card_cvv=CVV)),
        client.get("/decisions/tx-1"),
        client.post("/get_check_transaction", json={"transaction_id": "tx-1"}),
        client.post("/blocks", json={"card_number": VISA, "reason": "stolen"}),
        client.get("/blocks"),
    ]

    for response in responses:
        assert response.status_code < 300, response.text
        assert_no_card_data(response.text)


def test_audit_log_never_contains_card_data(audit_log):
    client.post("/decide_transaction", json=transaction(card_cvv=CVV))
    client.post("/decide_transaction", json=transaction(transaction_id="tx-2", amount=9000.0, card_cvv=CVV))
    client.post("/blocks", json={"card_number": VISA, "reason": "stolen"})

    text = audit_log.read_text(encoding="utf-8")
    assert len(text.splitlines()) >= 3  # the events were really written
    assert_no_card_data(text)
    assert all("card_cvv" not in json.loads(line)["payload"] for line in text.splitlines())


# FastAPI's default 422 response echoes the request body back, card number and CVV included.
@pytest.mark.parametrize(
    "body",
    [
        {k: v for k, v in transaction(card_cvv=CVV).items() if k != "timestamp"},  # missing field
        transaction(card_cvv=CVV, amount="abc"),  # wrong type
        {"card_number": VISA},  # block without a reason
    ],
)
def test_validation_errors_never_echo_card_data(body):
    path = "/blocks" if "customer_id" not in body else "/decide_transaction"
    response = client.post(path, json=body)

    assert response.status_code == 422
    assert_no_card_data(response.text)
    assert response.json()["detail"][0]["loc"]  # still says which field failed
