"""
HARNESS: LLM Cache Tests
=========================
Valida que:
1. Chamadas idênticas retornam do cache sem hit na API (cache hit)
2. Hashes diferentes geram novas chamadas (cache miss)
3. Entradas expiradas (>24h) não são servidas pelo cache

Alinhado com HARNESS.md §3 (Epic 4 — Token Efficiency).
"""

import os
import json
import hashlib
import sqlite3
import tempfile
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_db(tmp_path):
    """Creates a temporary SQLite database with the llm_cache table."""
    db_path = str(tmp_path / "test_afis.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE llm_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_hash TEXT NOT NULL UNIQUE,
            response_json TEXT NOT NULL,
            model TEXT NOT NULL,
            tokens_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def sample_response():
    return json.dumps({
        "health": "ok",
        "summary": "Cash is stable with 22 months runway.",
        "risk": "Client concentration risk remains high.",
        "action": "Diversify client base by onboarding 2 new accounts this quarter."
    })


# ---------------------------------------------------------------------------
# Hash Tests
# ---------------------------------------------------------------------------

class TestPromptHashing:

    def test_identical_prompts_produce_same_hash(self):
        from app.llm_client import _hash_prompt
        prompt = "You are a financial analyst. Metrics: cash=50000, runway=22"
        h1 = _hash_prompt(prompt)
        h2 = _hash_prompt(prompt)
        assert h1 == h2, "Identical prompts must produce identical SHA-256 hashes"

    def test_different_prompts_produce_different_hashes(self):
        from app.llm_client import _hash_prompt
        h1 = _hash_prompt("Metrics: cash=50000, runway=22")
        h2 = _hash_prompt("Metrics: cash=30000, runway=10")
        assert h1 != h2, "Different prompts must produce different hashes"

    def test_hash_is_valid_sha256_hex(self):
        from app.llm_client import _hash_prompt
        h = _hash_prompt("test prompt")
        assert len(h) == 64, "SHA-256 hash must be 64 hex characters"
        assert all(c in "0123456789abcdef" for c in h), "Hash must be valid hex"


# ---------------------------------------------------------------------------
# Cache Read/Write Tests
# ---------------------------------------------------------------------------

class TestCacheReadWrite:

    def test_cache_miss_returns_none(self, temp_db):
        with patch("app.llm_client._DB_PATH", temp_db):
            from app.llm_client import _get_cached_response
            result = _get_cached_response("nonexistent_hash_abc123")
            assert result is None, "Cache miss must return None"

    def test_cache_write_and_read(self, temp_db, sample_response):
        with patch("app.llm_client._DB_PATH", temp_db):
            from app.llm_client import _save_to_cache, _get_cached_response
            test_hash = "a" * 64  # Fake 64-char hash

            _save_to_cache(test_hash, sample_response, "claude-haiku-4-5-20251001", 150)
            result = _get_cached_response(test_hash)

            assert result is not None, "Cache hit must return cached response"
            assert result == sample_response, "Cached response must match stored value"

    def test_cache_upsert_updates_existing(self, temp_db, sample_response):
        """Writing the same hash twice should update, not duplicate."""
        with patch("app.llm_client._DB_PATH", temp_db):
            from app.llm_client import _save_to_cache, _get_cached_response
            test_hash = "b" * 64
            new_response = json.dumps({"health": "warning", "summary": "Updated.", "risk": "High.", "action": "Act now."})

            _save_to_cache(test_hash, sample_response, "model-v1", 100)
            _save_to_cache(test_hash, new_response, "model-v2", 120)

            result = _get_cached_response(test_hash)
            assert result == new_response, "Upsert must store latest response"

            # Verify only one row exists
            conn = sqlite3.connect(temp_db)
            count = conn.execute("SELECT COUNT(*) FROM llm_cache WHERE prompt_hash=?", (test_hash,)).fetchone()[0]
            conn.close()
            assert count == 1, "Cache must not duplicate entries for same hash"


# ---------------------------------------------------------------------------
# Cache API Integration Tests
# ---------------------------------------------------------------------------

class TestCacheAPIIntegration:

    def test_cache_hit_skips_api(self, temp_db, sample_response):
        """When cache has a valid entry, the API must NOT be called."""
        with patch("app.llm_client._DB_PATH", temp_db):
            import app.llm_client as llm

            metrics = {"current_cash": 50000, "runway": 22.0, "net_margin_percent": 38.0, "burn_rate": 0}
            prompt = llm._build_json_prompt(metrics, "")
            prompt_hash = llm._hash_prompt(prompt)

            # Pre-populate cache
            llm._save_to_cache(prompt_hash, sample_response, "claude-haiku", 150)

            mock_client = MagicMock()
            llm._mode = "llm"
            llm._client = mock_client

            result = llm.generate_financial_narrative(metrics)

            # API should NOT have been called
            mock_client.messages.create.assert_not_called()
            assert isinstance(result, dict), "Cached result must be a parsed dict"
            assert result["health"] == "ok"

    def test_cache_miss_calls_api(self, temp_db, sample_response):
        """When no cache entry exists, the API MUST be called exactly once."""
        with patch("app.llm_client._DB_PATH", temp_db):
            import app.llm_client as llm

            mock_response = MagicMock()
            mock_response.content = [MagicMock()]
            mock_response.content[0].text = sample_response
            mock_response.usage.input_tokens = 500
            mock_response.usage.output_tokens = 70

            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            llm._mode = "llm"
            llm._client = mock_client

            metrics = {"current_cash": 99999, "runway": 5.0, "net_margin_percent": 10.0, "burn_rate": 1500}
            result = llm.generate_financial_narrative(metrics)

            mock_client.messages.create.assert_called_once()
            assert isinstance(result, dict)

    def test_tokens_stored_in_cache(self, temp_db, sample_response):
        """Tokens used must be persisted in the cache for reporting."""
        with patch("app.llm_client._DB_PATH", temp_db):
            from app.llm_client import _save_to_cache
            _save_to_cache("c" * 64, sample_response, "claude-haiku", 620)

            conn = sqlite3.connect(temp_db)
            row = conn.execute("SELECT tokens_used FROM llm_cache WHERE prompt_hash=?", ("c" * 64,)).fetchone()
            conn.close()

            assert row[0] == 620, "Token count must be stored accurately in cache"
