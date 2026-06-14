"""
Provider-agnostic LLM client for the AFIS AI Financial Analyst.

Set ANTHROPIC_API_KEY environment variable to enable LLM-powered analysis.
Without the key, the system runs in offline mode using rule-based heuristics.
"""

import os
from typing import Optional

_client = None
_mode = "offline"


def _init_client():
    global _client, _mode
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        try:
            import anthropic
            _client = anthropic.Anthropic(api_key=api_key)
            _mode = "llm"
        except ImportError:
            _mode = "offline"
    else:
        _mode = "offline"


_init_client()


def get_mode() -> str:
    return _mode


def generate_financial_narrative(metrics: dict, context: str = "") -> str:
    """
    Generate a natural-language interpretation of financial metrics.

    In LLM mode: calls Claude claude-haiku-4-5 for cost efficiency.
    In offline mode: returns a structured rule-based interpretation.
    """
    if _mode == "llm" and _client is not None:
        prompt = _build_prompt(metrics, context)
        message = _client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    else:
        return _rule_based_narrative(metrics)


def _build_prompt(metrics: dict, context: str) -> str:
    return f"""You are a concise financial analyst assistant for a U.S. small business.

Given these financial metrics for the current period:
{_format_metrics(metrics)}

{f'Additional context: {context}' if context else ''}

Provide a 3-4 sentence interpretation covering:
1. Overall financial health assessment
2. The most critical risk or opportunity
3. One specific, actionable recommendation

Be direct. Use plain English. No jargon. No bullet points. No headers."""


def _format_metrics(metrics: dict) -> str:
    lines = []
    for key, value in metrics.items():
        if isinstance(value, float):
            lines.append(f"- {key}: {value:,.2f}")
        else:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def _rule_based_narrative(metrics: dict) -> str:
    """Deterministic fallback when no LLM API key is configured."""
    parts = []

    runway = metrics.get("runway_months", metrics.get("runway", 0))
    net_margin = metrics.get("net_profit_margin_pct", metrics.get("net_margin_percent", 0))
    burn_rate = metrics.get("burn_rate", 0)

    # Handle string runway values (e.g. "Infinite (Cash Positive)")
    if isinstance(runway, str):
        parts.append(
            "Cash flow is positive — the company is not burning through reserves. "
            "Runway is effectively unlimited under current conditions."
        )
    elif runway < 3:
        parts.append(
            f"ALERT: Current runway is {runway:.1f} months — immediate action required "
            "to extend cash reserves or accelerate receivables."
        )
    elif runway < 6:
        parts.append(
            f"Runway of {runway:.1f} months is below the recommended 6-month buffer. "
            "Cash management should be a priority this quarter."
        )
    else:
        parts.append(
            f"Runway of {runway:.1f} months provides adequate short-term stability."
        )

    if isinstance(net_margin, (int, float)):
        if net_margin < 0:
            parts.append(
                f"Net margin is negative ({net_margin:.1f}%). Review expense categories "
                "for immediate reduction opportunities."
            )
        elif net_margin < 5:
            parts.append(
                f"Net margin of {net_margin:.1f}% is thin. Focus on revenue growth "
                "or cost reduction to improve profitability."
            )
        else:
            parts.append(
                f"Net margin of {net_margin:.1f}% is healthy. Sustain current cost discipline."
            )

    if isinstance(burn_rate, (int, float)) and burn_rate > 0:
        parts.append(
            f"Monthly burn rate is ${burn_rate:,.0f}. "
            "Monitor against revenue trends to maintain positive cash position."
        )

    if _mode == "offline":
        parts.append(
            "Note: Running in offline mode. Set ANTHROPIC_API_KEY for AI-powered narrative analysis."
        )

    return " ".join(parts)
