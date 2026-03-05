"""Redaction utility for audit event state payloads.

Redacts sensitive field values in-place (returns new dict) based on
field-name patterns. Tracks which fields were redacted so the audit
trail can record the list without exposing the values.
"""
from __future__ import annotations

import re
from typing import Any

# Fields whose *names* match any of these patterns are considered sensitive.
_SENSITIVE_NAME_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"key", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"credential", re.IGNORECASE),
]

# PII field names (exact match, case-insensitive).
_PII_FIELDS: frozenset[str] = frozenset({
    "email",
    "phone",
    "telegram_chat_id",
})

REDACTED = "***REDACTED***"


def _is_sensitive(field_name: str) -> bool:
    """Return True if the field name matches a sensitive pattern or is PII."""
    lower = field_name.lower()
    if lower in _PII_FIELDS:
        return True
    return any(pat.search(field_name) for pat in _SENSITIVE_NAME_PATTERNS)


def redact_state(state: dict[str, Any] | None) -> tuple[dict[str, Any] | None, list[str]]:
    """Return a redacted copy of *state* and the list of redacted field names.

    Only top-level keys are inspected. Nested dicts are not traversed.

    Returns:
        (redacted_copy, redacted_field_names)
    """
    if state is None:
        return None, []

    redacted_fields: list[str] = []
    result: dict[str, Any] = {}

    for key, value in state.items():
        if _is_sensitive(key):
            result[key] = REDACTED
            redacted_fields.append(key)
        else:
            result[key] = value

    return result, sorted(redacted_fields)
