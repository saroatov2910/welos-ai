"""Rule-review agent: reviews fraud-rule changes in a PR before they are merged.

Sends only the code diff to Claude - never transaction or card data.
Exits with code 1 when a critical/high finding is reported, so CI blocks the merge.

Local usage:
    python review.py --base origin/main             # review current branch vs main
    python review.py --base origin/main --dry-run   # print the prompt, no API call
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import subprocess
import sys
from pathlib import Path
from typing import Literal

import anthropic
from pydantic import BaseModel, ConfigDict

MODEL = "claude-opus-5"
REVIEW_PATHS = ["services/decision-service/"]
# Never send these to the API, even if they somehow end up in a diff.
EXCLUDED_PATTERNS = [".env", ".env.*", "*.pem", "*.key"]
BLOCKING_SEVERITIES = {"critical", "high"}

SYSTEM_PROMPT = """\
You are a senior engineer reviewing changes to a real-time card-fraud decision engine \
(Python, FastAPI). The engine runs on-premises inside banks and stores, must decide in \
under 15 ms, and card data must never leave the customer's network.

Review the diff for problems that would cause wrong fraud decisions or security/privacy \
issues. Focus on:
- Logic errors in risk rules: wrong thresholds, inverted comparisons, off-by-one in time \
windows, rules that can never fire, scores that can exceed bounds.
- Weakened fraud detection: a change that silently lets more fraud through (raised \
thresholds, removed checks, broader exceptions) without a test that justifies it.
- Card data handling (PCI DSS): full card numbers or CVV logged, stored, returned in \
responses, or sent to external services (S3, HTTP, analytics). CVV must never be stored.
- Input validation gaps: negative/zero amounts, naive vs. timezone-aware datetimes, \
missing format checks.
- Security: unauthenticated endpoints exposing internal data, secrets in code, injection.
- Latency: blocking I/O, network calls, or heavy computation in the decision hot path.
- Missing tests for changed rule behaviour.

Severity guide:
- critical: card data exposure, auth bypass, or a bug that approves clearly fraudulent \
transactions.
- high: wrong decisions in realistic cases, or a crash (500) reachable from input.
- medium: edge-case bugs, missing tests for changed rules.
- low: readability or maintainability.

Report only real problems in the changed code, with the exact file and line. Do not \
report style nits that a linter would catch. If the change is fine, return no findings."""


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Literal["critical", "high", "medium", "low"]
    file: str
    line: int
    title: str
    explanation: str
    suggestion: str


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    findings: list[Finding]


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def _is_excluded(path: str) -> bool:
    name = Path(path).name
    return any(fnmatch.fnmatch(name, pattern) for pattern in EXCLUDED_PATTERNS)


def changed_files(base: str) -> list[str]:
    out = _git("diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD", "--", *REVIEW_PATHS)
    return [f for f in out.splitlines() if f and not _is_excluded(f)]


def build_prompt(base: str, files: list[str], language: str) -> str:
    diff = _git("diff", "--unified=5", f"{base}...HEAD", "--", *files)
    full_files = "\n\n".join(f'<file path="{f}">\n{Path(f).read_text()}\n</file>' for f in files)
    return (
        f"<diff>\n{diff}\n</diff>\n\n"
        f"Full content of the changed files, for context:\n{full_files}\n\n"
        f"Review the diff. Write summary, title, explanation and suggestion in {language}."
    )


def run_review(prompt: str) -> Review:
    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        thinking={"type": "adaptive"},
        output_config={
            "effort": "high",
            "format": {"type": "json_schema", "schema": Review.model_json_schema()},
        },
        # Security reviews can trip safety classifiers; retry on a fallback model instead of failing.
        betas=["server-side-fallback-2026-07-01"],
        extra_body={"fallbacks": "default"},
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Review was declined by the model: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Review output was cut off (max_tokens)")
    text = next(block.text for block in response.content if block.type == "text")
    return Review.model_validate_json(text)


def to_markdown(review: Review) -> str:
    icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}
    lines = ["## 🤖 Rule Review Agent", "", review.summary, ""]
    if not review.findings:
        lines.append("✅ No issues found.")
    for f in sorted(review.findings, key=lambda f: list(icons).index(f.severity)):
        lines += [
            f"### {icons[f.severity]} {f.severity.upper()}: {f.title}",
            f"`{f.file}:{f.line}`",
            "",
            f.explanation,
            "",
            f"**Suggestion:** {f.suggestion}",
            "",
        ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default="origin/main", help="git ref to diff against")
    parser.add_argument("--output", help="also write the markdown review to this file")
    parser.add_argument("--dry-run", action="store_true", help="print the prompt and exit")
    args = parser.parse_args()

    files = changed_files(args.base)
    if not files:
        print("No reviewable changes.")
        return 0

    prompt = build_prompt(args.base, files, os.getenv("REVIEW_LANGUAGE", "Hebrew"))
    if args.dry_run:
        print(prompt)
        return 0

    review = run_review(prompt)
    markdown = to_markdown(review)
    print(markdown)
    if args.output:
        Path(args.output).write_text(markdown)

    blocking = [f for f in review.findings if f.severity in BLOCKING_SEVERITIES]
    if blocking:
        print(f"\n{len(blocking)} blocking finding(s) - failing the check.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
