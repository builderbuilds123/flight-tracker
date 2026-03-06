"""Redaction utilities for audit payloads."""
from __future__ import annotations

import os
from typing import Any

_BASELINE_FIELDS: frozenset[str] = frozenset(
    {"telegram_chat_id", "user_id", "raw_payload"}
)
_ADDITIVE_ENV_VAR = "AUDIT_REDACT_ADDITIONAL_FIELDS"

REDACTED = "***REDACTED***"


def _configured_fields() -> set[str]:
    raw = os.getenv(_ADDITIVE_ENV_VAR, "")
    additive = {item.strip().lower() for item in raw.split(",") if item.strip()}
    return set(_BASELINE_FIELDS).union(additive)


def _redact(value: Any, sensitive_fields: set[str]) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in sensitive_fields:
                redacted[key] = REDACTED
            else:
                redacted[key] = _redact(item, sensitive_fields)
        return redacted
    if isinstance(value, list):
        return [_redact(item, sensitive_fields) for item in value]
    return value


def redact_payload(payload: Any) -> Any:
    """Return a deep-redacted copy of payload using baseline+env fields."""
    if payload is None:
        return None
    return _redact(payload, _configured_fields())


def redact_state(state: dict[str, Any] | None) -> tuple[dict[str, Any] | None, list[str]]:
    """Backward-compatible wrapper for existing callers."""
    if state is None:
        return None, []
    sensitive = _configured_fields()
    redacted = _redact(state, sensitive)
    fields = sorted(k for k in state.keys() if k.lower() in sensitive)
    return redacted, fields
