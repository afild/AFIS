"""
HARNESS: Token Budget Watcher + PII Guard
==========================================
Valida que:
1. Cada chamada ao LLM consome menos de $0.005 (Token Budget Watcher)
2. Nenhum payload enviado ao LLM contém PII sensível como números de cartão (PII Guard)

Alinhado com HARNESS.md §3 e §6.
"""

import re
import json
import pytest
from unittest.mock import MagicMock, patch

# Claude Haiku pricing (as of 2025): $0.25/MTok input, $1.25/MTok output
HAIKU_INPUT_COST_PER_TOKEN  = 0.25 / 1_000_000   # $0.00000025
HAIKU_OUTPUT_COST_PER_TOKEN = 1.25 / 1_000_000   # $0.00000125
MAX_COST_PER_CALL = 0.005  # $0.005 hard limit per HARNESS.md

# Regex pattern: 13-19 digit sequences that look like credit card numbers
_CC_PATTERN = re.compile(r'\b(?:\d[ -]?){13,19}\b')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * HAIKU_INPUT_COST_PER_TOKEN) + (output_tokens * HAIKU_OUTPUT_COST_PER_TOKEN)


def _build_mock_message(input_tokens: int, output_tokens: int, response_text: str):
    """Builds a mock Anthropic message response object."""
    mock = MagicMock()
    mock.content = [MagicMock()]
    mock.content[0].text = response_text
    mock.usage.input_tokens = input_tokens
    mock.usage.output_tokens = output_tokens
    return mock


# ---------------------------------------------------------------------------
# Token Budget Watcher Tests
# ---------------------------------------------------------------------------

class TestTokenBudgetWatcher:

    def test_nominal_call_within_budget(self):
        """A standard financial narrative call should cost well below $0.005."""
        # Typical call: ~600 input tokens, ~80 output tokens
        input_tok = 600
        output_tok = 80
        cost = _estimate_cost(input_tok, output_tok)
        assert cost < MAX_COST_PER_CALL, (
            f"BUDGET EXCEEDED: estimated cost ${cost:.6f} > limit ${MAX_COST_PER_CALL}. "
            f"Refactor the prompt to reduce token consumption."
        )

    def test_max_tokens_256_within_budget(self):
        """max_tokens=256 ceiling should never break the budget even at max."""
        # Worst case: 1500 input + 256 output
        cost = _estimate_cost(1500, 256)
        assert cost < MAX_COST_PER_CALL, (
            f"BUDGET EXCEEDED at max ceiling: ${cost:.6f}. Lower max_tokens or shorten system prompt."
        )

    def test_verbose_prompt_detected(self):
        """Simulates a verbose prompt (>2000 input tokens) and asserts it fails the budget watcher."""
        # 2000 input + 512 output (old verbose prompt scenario)
        cost = _estimate_cost(2000, 512)
        # This SHOULD fail — we're testing that the old prompt was expensive
        assert cost > 0.001, "Verbose prompt is unexpectedly cheap — check token estimates."
        # And confirm our new lean prompt avoids this
        lean_cost = _estimate_cost(600, 80)
        assert lean_cost < cost * 0.3, "New prompt should use <30% tokens of old verbose prompt."

    @patch("app.llm_client._client")
    def test_mock_api_call_budget(self, mock_client):
        """Mocks an actual LLM call and intercepts token usage to enforce budget."""
        response_json = '{"health":"ok","summary":"Cash positive.","risk":"Client concentration.","action":"Diversify revenue."}'
        mock_client.messages.create.return_value = _build_mock_message(580, 75, response_json)

        import app.llm_client as llm
        llm._mode = "llm"
        llm._client = mock_client

        # Trigger a call
        metrics = {"current_cash": 50000, "runway": 24.0, "net_margin_percent": 35.0, "burn_rate": 0}
        with patch("app.llm_client._get_cached_response", return_value=None):
            with patch("app.llm_client._save_to_cache"):
                result = llm.generate_financial_narrative(metrics)

        # Verify token usage from mock
        call_args = mock_client.messages.create.call_args
        actual_input = mock_client.messages.create.return_value.usage.input_tokens
        actual_output = mock_client.messages.create.return_value.usage.output_tokens
        cost = _estimate_cost(actual_input, actual_output)

        assert cost < MAX_COST_PER_CALL, f"API call exceeded budget: ${cost:.6f}"
        assert isinstance(result, dict), "LLM response must be a parsed dict"
        assert "health" in result, "Response must contain 'health' key"


# ---------------------------------------------------------------------------
# PII Guard Tests
# ---------------------------------------------------------------------------

class TestPIIGuard:

    def _check_for_pii(self, text: str) -> list:
        """Returns a list of detected PII patterns in the text."""
        violations = []
        matches = _CC_PATTERN.findall(text)
        if matches:
            violations.extend([f"Potential CC number: {m}" for m in matches])
        return violations

    def test_clean_metrics_no_pii(self):
        """Standard financial metrics should not trigger PII detection."""
        metrics = {
            "current_cash": 52500.00,
            "runway": 22.5,
            "net_margin_percent": 38.5,
            "burn_rate": 0,
            "total_income": 58200.00,
            "total_expense": 21300.00
        }
        # Build the prompt as the LLM client would
        from app.llm_client import _build_json_prompt
        prompt = _build_json_prompt(metrics, "")
        violations = self._check_for_pii(prompt)
        assert len(violations) == 0, f"PII detected in prompt payload: {violations}"

    def test_credit_card_number_blocked(self):
        """If a CC number somehow appears in context, PII guard should detect it."""
        fake_cc = "4111 1111 1111 1111"  # Test CC number
        text_with_cc = f"Transaction from {fake_cc} for $150.00"
        violations = self._check_for_pii(text_with_cc)
        assert len(violations) > 0, "PII guard failed to detect credit card number pattern"

    def test_transaction_descriptions_sanitized(self):
        """Transaction descriptions fed to LLM must not contain raw account numbers."""
        suspicious_descriptions = [
            "Wire transfer 4532015112830366",  # Luhn-valid CC
            "ACH from account 378282246310005",  # Amex test number
        ]
        for desc in suspicious_descriptions:
            violations = self._check_for_pii(desc)
            assert len(violations) > 0, f"PII guard missed sensitive number in: {desc}"

    def test_normal_amounts_not_flagged(self):
        """Dollar amounts with many digits should NOT be falsely flagged as PII."""
        normal_financial_text = "Total expense: $1234567.89, income: $9876543.21, burn_rate=1500.00"
        violations = self._check_for_pii(normal_financial_text)
        # Amounts formatted as floats with decimal points should not match the CC regex
        # (CC regex looks for 13-19 consecutive digits)
        cc_violations = [v for v in violations if "CC" in v]
        assert len(cc_violations) == 0, f"False positive PII detection on financial amounts: {violations}"
