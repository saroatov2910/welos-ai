"""Sample data for the tests.

The card numbers are public test cards: they pass the Luhn check but belong to
no one and can never be charged. Never put a real card number in a test.
"""

VISA = "4242424242424242"
MASTERCARD = "5555555555554444"


def transaction(**changes):
    """A valid, low-risk transaction. Pass only the fields a test cares about."""
    data = {
        "customer_id": "cust-1",
        "transaction_id": "tx-1",
        "amount": 100.0,
        "currency": "USD",
        "card_number": VISA,
        "card_cvv": "123",
        "card_expiry": "12/99",
        "timestamp": "2026-10-04T10:00:00Z",
    }
    return {**data, **changes}
