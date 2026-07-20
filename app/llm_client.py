"""
Provider-agnostic LLM client for the AFIS AI Financial Analyst.

Set ANTHROPIC_API_KEY environment variable to enable LLM-powered analysis.
Without the key, the system runs in offline mode using rule-based heuristics.

Epic 4 Optimizations:
- Prompts force strict minified JSON output (zero conversational overhead)
- SHA-256 prompt hashing enables SQLite-backed response cache (24h TTL)
- Offline fallback returns identical JSON schema to ensure API contract stability
"""

import os
import json
import hashlib
import sqlite3
from typing import Optional

_client = None
_mode = "offline"

# Path to the database (resolved relative to this file's location)
_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "afis_finance.db"
)

# LLM cache TTL in seconds (24 hours)
_CACHE_TTL_SECONDS = 86400


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


# ---------------------------------------------------------------------------
# Cache Helpers
# ---------------------------------------------------------------------------

def _hash_prompt(prompt: str) -> str:
    """Returns a SHA-256 hex digest of the prompt string for use as cache key."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _get_cached_response(prompt_hash: str) -> Optional[str]:
    """
    Retrieves a cached LLM response if it exists and is within TTL.
    Returns the raw JSON string or None if miss/expired.
    """
    try:
        conn = sqlite3.connect(_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT response_json FROM llm_cache
            WHERE prompt_hash = ?
              AND (julianday('now') - julianday(created_at)) * 86400 < ?
            """,
            (prompt_hash, _CACHE_TTL_SECONDS)
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


def _save_to_cache(prompt_hash: str, response_json: str, model: str, tokens_used: int):
    """
    Upserts a response into the LLM cache table.
    On conflict (same hash), refreshes the entry with latest data and timestamp.
    """
    try:
        conn = sqlite3.connect(_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO llm_cache (prompt_hash, response_json, model, tokens_used, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(prompt_hash) DO UPDATE SET
                response_json = excluded.response_json,
                model = excluded.model,
                tokens_used = excluded.tokens_used,
                created_at = CURRENT_TIMESTAMP
            """,
            (prompt_hash, response_json, model, tokens_used)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # Cache failures are non-fatal; system continues without caching


# ---------------------------------------------------------------------------
# Prompt Builders — Strict JSON Output Schema
# ---------------------------------------------------------------------------

def _build_json_prompt(metrics: dict, context: str = "") -> str:
    """
    Builds a prompt that forces the LLM to return a strict, minified JSON object.
    Schema: {"health":"ok|warning|critical","summary":"<2 sentences>","risk":"<1 sentence>","action":"<1 sentence>"}
    No conversational text, no markdown, no extra keys.
    """
    metrics_str = _format_metrics_compact(metrics)
    ctx_str = f' Context:{context}' if context else ''
    return (
        f'You are a financial analyst AI for a US small business.{ctx_str}'
        f' Metrics:{metrics_str}'
        f' Respond ONLY with this exact JSON, no other text:'
        f' {{"health":"ok|warning|critical","summary":"2-sentence assessment",'
        f'"risk":"1-sentence top risk","action":"1 specific actionable step"}}'
        f' Use actual values from metrics. health=critical if runway<3, warning if runway<12.'
    )


def _format_metrics_compact(metrics: dict) -> str:
    """Returns a compact single-line representation of financial metrics."""
    parts = []
    for key, value in metrics.items():
        if isinstance(value, float):
            parts.append(f"{key}={value:.2f}")
        else:
            parts.append(f"{key}={value}")
    return ",".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_financial_narrative(metrics: dict, context: str = "") -> dict:
    """
    Generates a structured JSON financial interpretation of the given metrics.

    In LLM mode:
        Calls Claude Haiku (cost-optimized). Checks cache first — only calls API
        on cache miss. Result is saved to cache for 24h re-use.

    In offline mode:
        Returns an identical JSON schema built from deterministic rule-based logic.

    Returns:
        dict with keys: health, summary, risk, action
    """
    prompt = _build_json_prompt(metrics, context)
    prompt_hash = _hash_prompt(prompt)

    if _mode == "llm" and _client is not None:
        # 1. Check cache first
        cached = _get_cached_response(prompt_hash)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                pass  # Cache corrupted — fall through to API call

        # 2. Call LLM
        model_id = "claude-haiku-4-5-20251001"
        try:
            message = _client.messages.create(
                model=model_id,
                max_tokens=256,  # Strict JSON needs ~100 tokens max; 256 is safe ceiling
                messages=[{"role": "user", "content": prompt}]
            )
            raw_text = message.content[0].text.strip()
            tokens_used = message.usage.input_tokens + message.usage.output_tokens

            # Validate JSON before caching
            parsed = json.loads(raw_text)

            # 3. Save to cache
            _save_to_cache(prompt_hash, raw_text, model_id, tokens_used)

            return parsed

        except (json.JSONDecodeError, Exception):
            # LLM returned non-JSON or API error — fall through to offline
            pass

    return _rule_based_narrative(metrics)


def _rule_based_narrative(metrics: dict) -> dict:
    """
    Deterministic fallback when no LLM API key is configured or LLM call fails.
    Returns the same JSON schema as the LLM response for API contract stability.
    """
    runway = metrics.get("runway_months", metrics.get("runway", 0))
    net_margin = metrics.get("net_profit_margin_pct", metrics.get("net_margin_percent", 0))
    burn_rate = metrics.get("burn_rate", 0)
    current_cash = metrics.get("current_cash", 0)

    # Determine health level
    if isinstance(runway, str):
        health = "ok"
    elif runway < 3:
        health = "critical"
    elif runway < 12:
        health = "warning"
    else:
        health = "ok"

    # Build summary
    if isinstance(runway, str):
        summary = (
            "Cash flow is positive — the business is generating more than it spends. "
            "Runway is effectively unlimited under current operational conditions."
        )
    elif runway < 3:
        summary = (
            f"CRITICAL: Cash runway is {runway:.1f} months — immediate intervention required. "
            f"Current cash balance of ${current_cash:,.0f} is critically low."
        )
    elif runway < 12:
        summary = (
            f"Runway of {runway:.1f} months is below the recommended 12-month buffer. "
            f"Cash management must be a Q1 priority to extend operational stability."
        )
    else:
        summary = (
            f"Cash position is stable with {runway:.1f} months of runway. "
            f"Net margin of {net_margin:.1f}% supports continued growth."
        )

    # Build risk
    if isinstance(net_margin, (int, float)) and net_margin < 0:
        risk = f"Negative net margin ({net_margin:.1f}%) indicates expenses exceed revenue — unsustainable without immediate cost correction."
    elif isinstance(burn_rate, (int, float)) and burn_rate > 0:
        risk = f"Monthly burn rate of ${burn_rate:,.0f} will deplete reserves if revenue growth stalls or client churn increases."
    else:
        risk = "Primary risk is client concentration — revenue appears dependent on a limited number of accounts."

    # Build action
    if health == "critical":
        action = "Immediately freeze non-essential OpEx, accelerate receivables collection, and explore emergency credit lines."
    elif health == "warning":
        action = "Reduce infrastructure costs by 15%, renegotiate vendor contracts, and accelerate client onboarding pipeline."
    else:
        action = "Reinvest net profits into product development or capital reserves to sustain competitive advantage."

    return {
        "health": health,
        "summary": summary,
        "risk": risk,
        "action": action
    }
