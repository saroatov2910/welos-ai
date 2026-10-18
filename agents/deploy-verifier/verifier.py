"""Deploy verifier: checks that every environment runs what the code says.

Usage (from the repo root, with the decision-service virtualenv):
    services/decision-service/.venv/bin/python agents/deploy-verifier/verifier.py

Exit code 0 when every check passes, 1 otherwise, so it can gate a pipeline.
"""

import argparse
import sys
from pathlib import Path

from checks import (
    CheckResult,
    check_health,
    check_pods,
    check_requires_api_key,
    check_routes_match_code,
    check_site,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RENDER_URL = "https://veloce-decision-service.onrender.com"
K8S_URL = "https://veloce.localhost:8443"
SITE_URL = "https://veloce-ai-demo.vercel.app"


def expected_paths() -> set[str]:
    """The endpoints defined by the current code, read from the FastAPI app itself."""
    sys.path.insert(0, str(REPO_ROOT / "services" / "decision-service"))
    from app.main import app

    return set(app.openapi()["paths"])


def run_checks(k8s_ca: str | None) -> list[CheckResult]:
    paths = expected_paths()
    results = [
        check_health("Render API health", RENDER_URL),
        check_routes_match_code(RENDER_URL, paths),
        check_requires_api_key(RENDER_URL),
        check_pods("veloce", "decision-service"),
        check_site(SITE_URL, "Veloce AI"),
    ]
    if k8s_ca:
        results.append(check_health("Kubernetes HTTPS health", K8S_URL, cafile=k8s_ca))
    return results


def print_report(results: list[CheckResult]) -> None:
    width = max(len(r.name) for r in results)
    for r in results:
        print(f"{'PASS' if r.ok else 'FAIL'}  {r.name.ljust(width)}  {r.detail}")
    failed = sum(1 for r in results if not r.ok)
    print(f"\n{len(results) - failed}/{len(results)} checks passed")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify that deployments match the code"
    )
    parser.add_argument(
        "--k8s-ca", help="CA file to verify the Kubernetes HTTPS ingress"
    )
    args = parser.parse_args()

    results = run_checks(args.k8s_ca)
    print_report(results)
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
