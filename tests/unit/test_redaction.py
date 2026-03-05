"""Unit tests for the redaction utility (S6-05)."""
import pytest

from src.observability.redaction import REDACTED, redact_state


class TestRedactState:
    """Tests for redact_state()."""

    def test_none_input_returns_none(self):
        result, fields = redact_state(None)
        assert result is None
        assert fields == []

    def test_empty_dict(self):
        result, fields = redact_state({})
        assert result == {}
        assert fields == []

    def test_no_sensitive_fields(self):
        state = {"origin_iata": "JFK", "status": "active", "price": 199.99}
        result, fields = redact_state(state)
        assert result == state
        assert fields == []

    # -- Keyword-based sensitive fields --

    @pytest.mark.parametrize("field_name", [
        "token", "api_token", "access_token", "Token",
        "secret", "client_secret", "SECRET_VALUE",
        "key", "api_key", "API_KEY",
        "password", "Password", "user_password",
        "credential", "credentials", "Credential",
    ])
    def test_sensitive_keyword_redacted(self, field_name: str):
        state = {field_name: "super-secret-value", "safe_field": "visible"}
        result, fields = redact_state(state)
        assert result[field_name] == REDACTED
        assert result["safe_field"] == "visible"
        assert field_name in fields

    # -- PII fields --

    @pytest.mark.parametrize("field_name", [
        "email", "phone", "telegram_chat_id",
    ])
    def test_pii_field_redacted(self, field_name: str):
        state = {field_name: "user@example.com", "status": "ok"}
        result, fields = redact_state(state)
        assert result[field_name] == REDACTED
        assert result["status"] == "ok"
        assert field_name in fields

    def test_multiple_sensitive_fields_sorted(self):
        state = {
            "email": "a@b.com",
            "api_key": "k-123",
            "status": "active",
            "password": "hunter2",
        }
        result, fields = redact_state(state)
        assert result["email"] == REDACTED
        assert result["api_key"] == REDACTED
        assert result["password"] == REDACTED
        assert result["status"] == "active"
        # Fields should be sorted alphabetically
        assert fields == ["api_key", "email", "password"]

    def test_original_dict_not_mutated(self):
        state = {"api_key": "secret123"}
        original_value = state["api_key"]
        redact_state(state)
        assert state["api_key"] == original_value
