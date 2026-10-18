import json

from checks import check_pods, check_requires_api_key, check_routes_match_code


def fake_fetch(responses):
    return lambda url, *args: responses[url]


def test_routes_match_when_live_equals_code():
    live = json.dumps({"paths": {"/health": {}, "/blocks": {}}})
    result = check_routes_match_code(
        "https://api",
        {"/health", "/blocks"},
        fake_fetch({"https://api/openapi.json": (200, live)}),
    )

    assert result.ok


def test_routes_drift_is_reported():
    live = json.dumps({"paths": {"/health": {}, "/is_entity_blocked/{entity_id}": {}}})
    result = check_routes_match_code(
        "https://api",
        {"/health", "/blocks"},
        fake_fetch({"https://api/openapi.json": (200, live)}),
    )

    assert not result.ok
    assert "/blocks" in result.detail
    assert "/is_entity_blocked/{entity_id}" in result.detail


def test_api_without_key_must_return_401():
    assert check_requires_api_key(
        "https://api", fake_fetch({"https://api/blocks": (401, "")})
    ).ok
    assert not check_requires_api_key(
        "https://api", fake_fetch({"https://api/blocks": (200, "")})
    ).ok


def _pods(phase, ready, restarts=0):
    return json.dumps(
        {
            "items": [
                {
                    "metadata": {"name": "decision-service-1"},
                    "status": {
                        "phase": phase,
                        "containerStatuses": [
                            {"ready": ready, "restartCount": restarts}
                        ],
                    },
                }
            ]
        }
    )


def test_running_ready_pod_passes():
    assert check_pods(
        "veloce", "decision-service", lambda args: _pods("Running", True)
    ).ok


def test_crashing_pod_fails():
    result = check_pods(
        "veloce", "decision-service", lambda args: _pods("Running", True, restarts=7)
    )

    assert not result.ok
    assert "restarted 7 times" in result.detail


def test_no_pods_fails():
    assert not check_pods(
        "veloce", "decision-service", lambda args: json.dumps({"items": []})
    ).ok
