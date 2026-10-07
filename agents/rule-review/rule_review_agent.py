"""Rule Review Agent - reviews fraud-rule changes in pull requests.

Run from the repo root:
    agents/rule-review/.venv/bin/python agents/rule-review/rule_review_agent.py --fake
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Literal

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

# Load ANTHROPIC_API_KEY from the .env file next to this script.
load_dotenv(Path(__file__).parent / ".env", override=True)

MODEL = "claude-opus-5"
SYSTEM_PROMPT = "You review code changes in a fraud-detection engine. Find bugs."
BLOCKING_SEVERITIES = {"critical", "high"}


# Step 3: the fixed structure the model must answer in
class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Literal["critical", "high", "medium", "low"]
    file: str
    line: int
    title: str
    explanation: str


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    findings: list[Finding]


# Step 1: get the diff
def get_diff(base: str) -> str:
    result = subprocess.run(
        ["git", "diff", f"{base}...HEAD", "--", "services/decision-service/"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


# Step 2: ask the model - returns its answer as JSON text
def ask_model(diff: str) -> str:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": diff}],
        output_config={"format": {"type": "json_schema", "schema": Review.model_json_schema()}},
    )
    return next(block.text for block in response.content if block.type == "text")


# Fake mode: a fixed answer shaped exactly like the model's, so we can build for free
def ask_fake_model(diff: str) -> str:
    return """{
        "summary": "Fake review for local testing.",
        "findings": [
            {
                "severity": "high",
                "file": "services/decision-service/app/services.py",
                "line": 17,
                "title": "Example finding",
                "explanation": "This is a fake finding to test the decision logic."
            }
        ]
    }"""


# Step 4: decide - fail (exit code 1) if any finding is blocking
def decide(review: Review) -> int:
    blocking = [f for f in review.findings if f.severity in BLOCKING_SEVERITIES]
    return 1 if blocking else 0


def print_review(review: Review) -> None:
    print(review.summary)
    for f in review.findings:
        print(f"[{f.severity.upper()}] {f.file}:{f.line} - {f.title}")
        print(f"    {f.explanation}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="HEAD~2", help="git ref to compare against")
    parser.add_argument("--fake", action="store_true", help="use a fake answer instead of calling the model")
    args = parser.parse_args()

    diff = get_diff(args.base)
    answer = ask_fake_model(diff) if args.fake else ask_model(diff)
    review = Review.model_validate_json(answer)

    print_review(review)
    sys.exit(decide(review))
