"""Fraud analyst agent: turns audit-log statistics into a report for the security manager.

Statistics are computed locally by stats.py. Only those aggregated numbers are sent
to the model, never single transactions, card numbers or customer IDs.

Usage:
    python analyst_agent.py audit.jsonl --fake          # no model, no cost
    python analyst_agent.py audit.jsonl                 # model chosen by ANALYST_PROVIDER

Environment:
    ANALYST_PROVIDER   anthropic (default) or bedrock
    ANTHROPIC_API_KEY  for the anthropic provider
    AWS_REGION         for the bedrock provider (credentials come from the AWS profile or role)
"""

import argparse
import json
import os
from pathlib import Path

from stats import compute_stats, load_events

MODEL = "claude-opus-5"
PROMPT_FILE = Path(__file__).parent / "prompts" / "fraud_analyst.md"


def build_message(stats: dict) -> str:
    """The only data that leaves this machine: aggregated statistics as JSON."""
    return "Write the report for these statistics:\n\n" + json.dumps(stats, indent=2)


def ask_model(stats: dict) -> str:
    """Send the statistics to Claude, directly or through Amazon Bedrock."""
    system = PROMPT_FILE.read_text(encoding="utf-8")
    messages = [{"role": "user", "content": build_message(stats)}]
    provider = os.getenv("ANALYST_PROVIDER", "anthropic")

    if provider == "bedrock":
        from anthropic import AnthropicBedrockMantle

        client = AnthropicBedrockMantle(
            aws_region=os.getenv("AWS_REGION", "eu-central-1")
        )
        response = client.messages.create(
            model=f"anthropic.{MODEL}",
            max_tokens=4000,
            system=system,
            messages=messages,
        )
    else:
        import anthropic

        client = anthropic.Anthropic()
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=system,
            messages=messages,
            # If the model declines, retry on Anthropic's recommended fallback model.
            betas=["server-side-fallback-2026-07-01"],
            extra_body={"fallbacks": "default"},
        )

    if response.stop_reason == "refusal":
        raise RuntimeError("The model declined to write the report")
    return "\n".join(block.text for block in response.content if block.type == "text")


def fake_report(stats: dict) -> str:
    """A fixed-template report from the same numbers, for development without a model."""
    totals = stats["totals"]
    caught = stats["fraud_caught"]
    currency = ", ".join(stats["currencies"]) or "no currency"
    top_reasons = (
        ", ".join(
            f"{name} ({count})" for name, count in list(stats["reasons"].items())[:3]
        )
        or "none"
    )
    return "\n".join(
        [
            "[FAKE REPORT: generated without a model]",
            "",
            "Summary",
            (
                f"{totals['transactions_checked']} transactions checked between "
                f"{stats['period']['from']} and {stats['period']['to']}. "
                f"{totals['reject_rate_percent']}% were rejected."
            ),
            "",
            "Fraud caught",
            (
                f"{caught['rejected_transactions']} transactions rejected, "
                f"{caught['amount_stopped']:,.2f} {currency} stopped. "
                f"{caught['cards_blocked_automatically']} cards blocked automatically, "
                f"{caught['cards_blocked_manually']} manually, {caught['cards_released']} released."
            ),
            "",
            "Patterns",
            f"Most frequent rules: {top_reasons}.",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Fraud analyst agent")
    parser.add_argument("audit_log", help="path to the audit log (JSON Lines)")
    parser.add_argument(
        "--fake", action="store_true", help="template report, no model call"
    )
    parser.add_argument(
        "--show-stats", action="store_true", help="print the numbers sent to the model"
    )
    args = parser.parse_args()

    stats = compute_stats(load_events(args.audit_log))
    if args.show_stats:
        print(build_message(stats), end="\n\n")
    print(fake_report(stats) if args.fake else ask_model(stats))


if __name__ == "__main__":
    main()
