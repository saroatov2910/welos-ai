import pytest

TEST_API_KEY = "test-api-key"


@pytest.fixture(autouse=True)
def api_key_env(monkeypatch):
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
