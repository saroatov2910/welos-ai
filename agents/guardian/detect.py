"""Guardian step 1: detect unhealthy pods.

Read-only: only runs `kubectl get`. Never changes anything in the cluster.

Usage:
    python detect.py               # namespace veloce
    python detect.py other-ns
"""

import json
import logging
import subprocess
import sys
from dataclasses import dataclass

RESTART_LIMIT = 3

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


def find_problems(pods: list[dict]) -> list[Problem]:
    """Every container that is waiting, crashed recently or restarts too often."""
    problems = []
    for pod in pods:
        name = pod["metadata"]["name"]
        for container in pod["status"].get("containerStatuses", []):
            waiting = container.get("state", {}).get("waiting", {})
            last_crash = container.get("lastState", {}).get("terminated", {})
            restarts = container.get("restartCount", 0)

            if waiting:
                reason = waiting.get("reason", "Waiting")
                message = waiting.get("message", "")
            elif not container.get("ready", False):
                reason = "NotReady"
                message = "container is running but not ready"
            elif restarts > RESTART_LIMIT:
                reason = last_crash.get("reason", "Restarting")
                message = f"restarted {restarts} times"
            else:
                logger.debug("%s/%s is healthy", name, container["name"])
                continue

            if last_crash.get("reason") == "OOMKilled":
                reason = "OOMKilled"
            logger.warning("%s/%s has a problem: %s", name, container["name"], reason)
            problems.append(Problem(name, container["name"], reason, restarts, message))
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
