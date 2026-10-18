"""Deployment checks: is what runs in each environment what the code says?

Every check returns a CheckResult. Checks only read: they never deploy, restart
or change anything. Network and kubectl calls go through small helpers so tests
can replace them.
"""

import json
import ssl
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def http_get(url: str, cafile: str | None = None, timeout: int = 90) -> tuple[int, str]:
    """GET a URL and return (status code, body). Network errors become status 0."""
    context = ssl.create_default_context(cafile=cafile) if cafile else None
    try:
        with urllib.request.urlopen(url, timeout=timeout, context=context) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, ""
    except (urllib.error.URLError, TimeoutError) as error:
        return 0, str(error)


def run_kubectl(args: list[str]) -> str:
    """Run a read-only kubectl command and return its stdout."""
    result = subprocess.run(
        ["kubectl", *args], capture_output=True, text=True, check=True
    )
    return result.stdout


def check_health(
    name: str, base_url: str, fetch=http_get, cafile: str | None = None
) -> CheckResult:
    """The service answers /health with 200."""
    status, _ = (
        fetch(f"{base_url}/health", cafile) if cafile else fetch(f"{base_url}/health")
    )
    return CheckResult(name, status == 200, f"/health returned {status}")


def check_routes_match_code(
    base_url: str, expected_paths: set[str], fetch=http_get
) -> CheckResult:
    """The live API exposes exactly the endpoints the code defines (drift detection)."""
    status, body = fetch(f"{base_url}/openapi.json")
    if status != 200:
        return CheckResult(
            "API matches code", False, f"/openapi.json returned {status}"
        )
    live = set(json.loads(body)["paths"])
    missing, extra = sorted(expected_paths - live), sorted(live - expected_paths)
    if not missing and not extra:
        return CheckResult("API matches code", True, f"{len(live)} endpoints match")
    return CheckResult(
        "API matches code",
        False,
        f"missing: {missing or 'none'}; unexpected: {extra or 'none'}",
    )


def check_requires_api_key(base_url: str, fetch=http_get) -> CheckResult:
    """A protected endpoint refuses requests without X-API-Key."""
    status, _ = fetch(f"{base_url}/blocks")
    return CheckResult(
        "API requires key",
        status == 401,
        f"/blocks without a key returned {status} (want 401)",
    )


def check_pods(namespace: str, app: str, kubectl=run_kubectl) -> CheckResult:
    """Every pod of the app is running and ready."""
    try:
        pods = json.loads(
            kubectl(["get", "pods", "-n", namespace, "-l", f"app={app}", "-o", "json"])
        )["items"]
    except (subprocess.CalledProcessError, FileNotFoundError) as error:
        return CheckResult("Kubernetes pods", False, f"kubectl failed: {error}")
    if not pods:
        return CheckResult(
            "Kubernetes pods", False, f"no pods with app={app} in {namespace}"
        )
    problems = []
    for pod in pods:
        statuses = pod["status"].get("containerStatuses", [])
        ready = bool(statuses) and all(c["ready"] for c in statuses)
        restarts = sum(c["restartCount"] for c in statuses)
        if pod["status"]["phase"] != "Running" or not ready:
            problems.append(
                f"{pod['metadata']['name']} is {pod['status']['phase']}, ready={ready}"
            )
        elif restarts > 3:
            problems.append(f"{pod['metadata']['name']} restarted {restarts} times")
    if problems:
        return CheckResult("Kubernetes pods", False, "; ".join(problems))
    return CheckResult("Kubernetes pods", True, f"{len(pods)} pod(s) running and ready")


def check_site(url: str, must_contain: str, fetch=http_get) -> CheckResult:
    """The website answers and shows the expected content."""
    status, body = fetch(url)
    ok = status == 200 and must_contain in body
    return CheckResult(
        "Website",
        ok,
        f"returned {status}, contains '{must_contain}': {must_contain in body}",
    )
