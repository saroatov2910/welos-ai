from datetime import UTC, datetime

from detect import find_problems

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
FIVE_MINUTES_AGO = "2026-10-18T11:55:00Z"
LAST_WEEK = "2026-10-11T12:00:00Z"


def pod(phase="Running", containers=(), deleting=False, name="decision-service-1"):
    metadata = {"name": name}
    if deleting:
        metadata["deletionTimestamp"] = "2026-10-18T11:59:00Z"
    return {
        "metadata": metadata,
        "status": {"phase": phase, "containerStatuses": list(containers)},
    }


def container(ready=True, restarts=0, waiting=None, crash=None, crashed_at=None):
    state = {"waiting": {"reason": waiting}} if waiting else {"running": {}}
    result = {"name": "app", "ready": ready, "restartCount": restarts, "state": state}
    if crash:
        result["lastState"] = {
            "terminated": {"reason": crash, "finishedAt": crashed_at}
        }
    return result


def reasons(pods):
    return [p.reason for p in find_problems(pods, now=NOW)]


def test_healthy_pod_has_no_problems():
    assert reasons([pod(containers=[container()])]) == []


def test_crash_loop_is_detected():
    assert reasons([pod(containers=[container(False, 5, "CrashLoopBackOff")])]) == [
        "CrashLoopBackOff"
    ]


def test_recent_oom_kill_is_named_as_the_reason():
    crashing = container(False, 5, "CrashLoopBackOff", "OOMKilled", FIVE_MINUTES_AGO)

    assert reasons([pod(containers=[crashing])]) == ["OOMKilled"]


def test_starting_container_is_not_a_problem():
    assert reasons([pod("Pending", [container(False, 0, "ContainerCreating")])]) == []


def test_unscheduled_pod_is_a_problem():
    assert reasons([pod("Pending", [])]) == ["Pending"]


def test_old_restarts_on_a_healthy_pod_are_ignored():
    assert (
        reasons(
            [pod(containers=[container(True, 5, crash="Error", crashed_at=LAST_WEEK)])]
        )
        == []
    )


def test_recent_restarts_are_a_problem():
    assert reasons(
        [
            pod(
                containers=[
                    container(True, 5, crash="Error", crashed_at=FIVE_MINUTES_AGO)
                ]
            )
        ]
    ) == ["Error"]


def test_old_oom_kill_does_not_hide_the_real_reason():
    not_ready = container(False, 1, crash="OOMKilled", crashed_at=LAST_WEEK)

    assert reasons([pod(containers=[not_ready])]) == ["NotReady"]


def test_finished_job_is_not_a_problem():
    done = {
        "name": "app",
        "ready": False,
        "restartCount": 0,
        "state": {"terminated": {"reason": "Completed"}},
    }

    assert reasons([pod("Succeeded", [done])]) == []


def test_pod_shutting_down_during_rollout_is_not_a_problem():
    assert reasons([pod(containers=[container(False)], deleting=True)]) == []
