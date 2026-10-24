from detect import Problem
from diagnose import EVIDENCE_LIMIT, UNKNOWN, diagnose, error_lines, warning_messages


def problem(reason, container="app"):
    return Problem("decision-service-1", container, reason, 3, "")


def event(type_, reason, message, time="2026-10-22T10:00:00Z"):
    return {"type": type_, "reason": reason, "message": message, "lastTimestamp": time}


def test_crash_loop_shows_the_error_from_the_logs():
    log = "INFO starting\nKeyError: 'API_KEY'\nINFO bye"

    d = diagnose(problem("CrashLoopBackOff"), [], log)

    assert "exits" in d.cause
    assert d.evidence == ["KeyError: 'API_KEY'"]
    assert "roll back" in d.suggestion


def test_out_of_memory_points_to_the_memory_limit():
    d = diagnose(problem("OOMKilled"), [], "")

    assert "memory" in d.cause
    assert "memory limit" in d.suggestion


def test_missing_image_suggests_rollback():
    d = diagnose(problem("ImagePullBackOff"), ["Failed: image not found"], "")

    assert "image" in d.cause
    assert d.evidence == ["Failed: image not found"]


def test_not_ready_keeps_the_readiness_event_as_evidence():
    events = ["Unhealthy: Readiness probe failed: context deadline exceeded"]

    d = diagnose(problem("NotReady"), events, "")

    assert "readiness" in d.cause
    assert d.evidence == events


def test_unknown_reason_falls_back_to_manual_investigation():
    d = diagnose(problem("SomethingNew"), [], "")

    assert (d.cause, d.suggestion) == UNKNOWN


def test_evidence_keeps_only_the_newest_events():
    events = [f"Unhealthy: probe failed {i}" for i in range(10)]

    d = diagnose(problem("NotReady"), events, "")

    assert d.evidence == events[-EVIDENCE_LIMIT:]


def test_only_warning_events_are_kept_oldest_first():
    events = {
        "items": [
            event("Warning", "Unhealthy", "probe failed", "2026-10-22T10:05:00Z"),
            event("Normal", "Pulled", "image present"),
            event("Warning", "BackOff", "restarting", "2026-10-22T10:01:00Z"),
        ]
    }

    assert warning_messages(events) == [
        "BackOff: restarting",
        "Unhealthy: probe failed",
    ]


def test_error_lines_ignore_normal_log_lines():
    log = "INFO started\nTraceback (most recent call last):\nValueError: bad amount\nINFO ok"

    assert error_lines(log) == [
        "Traceback (most recent call last):",
        "ValueError: bad amount",
    ]
