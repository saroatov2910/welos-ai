"""Guardian step 2: explain why a pod is unhealthy.

Read-only: reads the pod's warning events and recent logs with kubectl, then matches the
problem against a playbook. It suggests a next step but never runs it; a person decides.

Usage:
    python diagnose.py               # namespace veloce
    python diagnose.py other-ns
"""

import json
import logging
import subprocess
import sys
from dataclasses import dataclass

from detect import Problem, find_problems, get_pods

EVIDENCE_LIMIT = 5  # newest events and log lines shown per problem
ERROR_WORDS = ("error", "exception", "traceback", "fatal", "killed")

logger = logging.getLogger("guardian.diagnose")


@dataclass
class Diagnosis:
    problem: Problem
    cause: str
    evidence: list[str]
    suggestion: str


# Symptom (the reason detect.py found) -> (likely cause, suggested next step).
PLAYBOOKS = {
    "CrashLoopBackOff": (
        "The application starts and then exits, so Kubernetes keeps restarting it.",
        "Read the error in the logs. If it started after a deploy, roll back to the previous revision.",
    ),
    "Error": (
        "The container exited with an error.",
        "Read the error in the logs. If it started after a deploy, roll back to the previous revision.",
    ),
    "OOMKilled": (
        "The container used more memory than its limit and was killed.",
        "Raise the memory limit in k8s/deployment.yaml, or find what uses the memory.",
    ),
    "ImagePullBackOff": (
        "Kubernetes cannot find the image for this version.",
        "Roll back: the image tag was never imported into the cluster.",
    ),
    "ErrImagePull": (
        "Kubernetes cannot find the image for this version.",
        "Roll back: the image tag was never imported into the cluster.",
    ),
    "NotReady": (
        "The container runs but fails its readiness probe, so it receives no traffic.",
        "Check /readiness. If it started after a deploy, roll back; if the node is overloaded, wait.",
    ),
    "Pending": (
        "No node can run the pod.",
        "Read the FailedScheduling event: usually not enough CPU or memory on the nodes.",
    ),
}
UNKNOWN = (
    "There is no playbook for this reason yet.",
    "Investigate with: kubectl describe pod and kubectl logs.",
)


def run_kubectl(args: list[str]) -> str:
    """Run a read-only kubectl command and return its output."""
    return subprocess.run(
        ["kubectl", *args], capture_output=True, text=True, check=True
    ).stdout


def warning_messages(events: dict) -> list[str]:
    """'Reason: message' for every Warning event, oldest first."""
    warnings = [e for e in events.get("items", []) if e.get("type") == "Warning"]
    warnings.sort(key=lambda e: e.get("lastTimestamp") or "")
    return [f"{e.get('reason', '')}: {e.get('message', '').strip()}" for e in warnings]


def error_lines(log: str) -> list[str]:
    """Log lines that look like errors."""
    return [
        line.strip()
        for line in log.splitlines()
        if any(word in line.lower() for word in ERROR_WORDS)
    ]


def pod_events(namespace: str, pod: str) -> list[str]:
    output = run_kubectl(
        [
            "get",
            "events",
            "-n",
            namespace,
            "--field-selector",
            f"involvedObject.name={pod}",
            "-o",
            "json",
        ]
    )
    return warning_messages(json.loads(output))


def pod_logs(namespace: str, pod: str, container: str) -> str:
    """Logs of the crashed run and of the current run, whichever are available."""
    if container == "-":  # the pod never started, so there are no logs
        return ""
    base = ["logs", pod, "-c", container, "-n", namespace, "--tail=50"]
    parts = []
    # The previous run's logs may already be gone; the current run usually repeats the error.
    for args in ([*base, "--previous"], base):
        try:
            parts.append(run_kubectl(args))
        except subprocess.CalledProcessError:
            logger.debug("no logs from: kubectl %s", " ".join(args))
    return "\n".join(parts)


def diagnose(problem: Problem, events: list[str], log: str) -> Diagnosis:
    """Match the problem to a playbook and attach the newest evidence."""
    cause, suggestion = PLAYBOOKS.get(problem.reason, UNKNOWN)
    evidence = events[-EVIDENCE_LIMIT:] + error_lines(log)[-EVIDENCE_LIMIT:]
    return Diagnosis(problem, cause, evidence, suggestion)


def print_report(d: Diagnosis) -> None:
    p = d.problem
    print(f"\n{p.pod}/{p.container}: {p.reason} (restarts: {p.restarts})")
    print(f"  Cause:      {d.cause}")
    for line in d.evidence or ["(no warning events or error lines)"]:
        print(f"  Evidence:   {line}")
    print(f"  Suggestion: {d.suggestion}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    namespace = sys.argv[1] if len(sys.argv) > 1 else "veloce"
    problems = find_problems(get_pods(namespace))
    if not problems:
        print(f"healthy: nothing to diagnose in namespace {namespace}")
    for problem in problems:
        logger.info("diagnosing %s/%s", problem.pod, problem.container)
        print_report(
            diagnose(
                problem,
                pod_events(namespace, problem.pod),
                pod_logs(namespace, problem.pod, problem.container),
            )
        )
