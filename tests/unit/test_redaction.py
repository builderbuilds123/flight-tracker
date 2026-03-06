"""Unit tests for the redaction utility (S6-05)."""
import pytest

from src.observability.redaction import REDACTED, redact_payload


class TestRedactPayload:
    """Tests for redact_payload()."""

    def test_none_input_returns_none(self):
        assert redact_payload(None) is None

    def test_empty_dict(self):
        assert redact_payload({}) == {}

    def test_no_sensitive_fields(self):
        state = {"origin_iata": "JFK", "status": "active", "price": 199.99}
        result = redact_payload(state)
        assert result == state

    @pytest.mark.parametrize("field_name", ["telegram_chat_id", "user_id", "raw_payload"])
    def test_baseline_field_redacted(self, field_name: str):
        state = {field_name: "secret-value", "safe_field": "visible"}
        result = redact_payload(state)
        assert result[field_name] == REDACTED
        assert result["safe_field"] == "visible"

    def test_nested_redaction(self):
        state = {
            "status": "ok",
            "details": {"telegram_chat_id": "1234"},
            "items": [{"raw_payload": {"secret": "x"}}],
        }
        result = redact_payload(state)
        assert result["details"]["telegram_chat_id"] == REDACTED
        assert result["items"][0]["raw_payload"] == REDACTED

    def test_env_additive_redaction(self, monkeypatch):
        monkeypatch.setenv("AUDIT_REDACT_ADDITIONAL_FIELDS", "booking_url,token")
        state = {"booking_url": "http://example.com", "token": "abc", "status": "ok"}
        result = redact_payload(state)
        assert result["booking_url"] == REDACTED
        assert result["token"] == REDACTED
        assert result["status"] == "ok"

    def test_env_whitespace_and_case_handled(self, monkeypatch):
        monkeypatch.setenv("AUDIT_REDACT_ADDITIONAL_FIELDS", "  Booking_URL , TOKEN ")
        state = {"booking_url": "x", "token": "y", "status": "ok"}
        result = redact_payload(state)
        assert result["booking_url"] == REDACTED
        assert result["token"] == REDACTED
        assert result["status"] == "ok"

    def test_original_dict_not_mutated(self):
        state = {"raw_payload": {"a": 1}}
        original_value = state["raw_payload"]
        redact_payload(state)
        assert state["raw_payload"] == original_value
