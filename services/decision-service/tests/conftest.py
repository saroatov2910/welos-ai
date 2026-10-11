import pytest

TEST_API_KEY = "test-api-key"
TEST_CARD_HASH_KEY = "test-card-hash-key"


@pytest.fixture(autouse=True)
def api_key_env(monkeypatch):
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    monkeypatch.setenv("CARD_HASH_KEY", TEST_CARD_HASH_KEY)
