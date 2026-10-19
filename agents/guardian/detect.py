"""Guardian step 1: detect unhealthy pods.

Read-only: only runs `kubectl get`. Never changes anything in the cluster.
Judges the current state of each pod, not its history, so normal rollouts
and old crashes do not raise false alarms.

Usage:
    python detect.py               # namespace veloce
    python detect.py other-ns
"""

import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

RESTART_LIMIT = 3
RECENT_CRASH_WINDOW = timedelta(minutes=10)
# Normal states while a pod starts up: not a problem.
STARTING_REASONS = {"ContainerCreating", "PodInitializing"}

logger = logging.getLogger("guardian.detect")


@dataclass
class Problem:
    pod: str
    container: str
    reason: str
    restarts: int
    message: str


def get_pods(namespace: str) -> list[dict]:
    """All pods in the namespace, as kubectl returns them in JSON."""
    logger.info("listing pods in namespace %s", namespace)
    output = subprocess.run(
        ["kubectl", "get", "pods", "-n", namespace, "-o", "json"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    pods = json.loads(output)["items"]
    logger.info("found %d pods", len(pods))
    return pods


def crashed_recently(last_crash: dict, now: datetime | None = None) -> bool:
    """True if the container's last crash ended within the recent window."""
    finished_at = last_crash.get("finishedAt")
    if not finished_at:
        return False
    finished = datetime.fromisoformat(finished_at)
    return (now or datetime.now(UTC)) - finished <= RECENT_CRASH_WINDOW


def container_problem(
    container: dict, now: datetime | None = None
) -> tuple[str, str] | None:
    """(reason, message) if the container has a current problem, else None."""
    waiting = container.get("state", {}).get("waiting", {})
    last_crash = container.get("lastState", {}).get("terminated", {})
    restarts = container.get("restartCount", 0)
    recent = crashed_recently(last_crash, now)

    if waiting and waiting.get("reason") not in STARTING_REASONS:
        reason, message = waiting.get("reason", "Waiting"), waiting.get("message", "")
    elif restarts > RESTART_LIMIT and recent:
        reason, message = (
            last_crash.get("reason", "Restarting"),
            f"restarted {restarts} times",
        )
    elif not container.get("ready", False) and not waiting:
        reason, message = "NotReady", "container is running but not ready"
    else:
        return None

    # A recent out-of-memory crash explains the problem better than the generic reason.
    if recent and last_crash.get("reason") == "OOMKilled":
        reason = "OOMKilled"
    return reason, message


def find_problems(pods: list[dict], now: datetime | None = None) -> list[Problem]:
    """Every pod or container with a problem right now."""
    problems = []
    for pod in pods:
        name = pod["metadata"]["name"]
        status = pod["status"]

        if pod["metadata"].get("deletionTimestamp"):
            logger.debug("%s is shutting down, skipped", name)
            continue
        if status.get("phase") == "Succeeded":
            logger.debug("%s finished successfully, skipped", name)
            continue
        if status.get("phase") == "Pending" and not status.get("containerStatuses"):
            logger.warning("%s could not start: still pending", name)
            problems.append(
                Problem(name, "-", "Pending", 0, "pod could not be scheduled")
            )
            continue

        for container in status.get("containerStatuses", []):
            found = container_problem(container, now)
            if found is None:
                logger.debug("%s/%s is healthy", name, container["name"])
                continue
            reason, message = found
            logger.warning("%s/%s has a problem: %s", name, container["name"], reason)
            problems.append(
                Problem(
                    name,
                    container["name"],
                    reason,
                    container.get("restartCount", 0),
                    message,
                )
            )
    return problems


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    namespace = sys.argv[1] if len(sys.argv) > 1 else "veloce"
    found = find_problems(get_pods(namespace))
    if not found:
        print(f"healthy: no problems in namespace {namespace}")
    for p in found:
        print(f"{p.pod}/{p.container}: {p.reason} (restarts: {p.restarts}) {p.message}")
