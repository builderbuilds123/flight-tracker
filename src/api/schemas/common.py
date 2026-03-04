"""Shared schema primitives: validators, pagination, error envelope."""
from __future__ import annotations

import re
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, field_validator

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Reusable validators
# ---------------------------------------------------------------------------
_IATA_RE = re.compile(r"^[A-Z]{3}$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


def validate_iata(value: str) -> str:
    if not _IATA_RE.match(value):
        raise ValueError("Must be exactly 3 uppercase letters (IATA code)")
    return value


def validate_currency(value: str) -> str:
    if not _CURRENCY_RE.match(value):
        raise ValueError("Must be exactly 3 uppercase letters (ISO 4217 currency)")
    return value


# ---------------------------------------------------------------------------
# Cursor pagination wrapper
# ---------------------------------------------------------------------------
class CursorPage(BaseModel, Generic[T]):
    """Stable cursor-based pagination envelope."""

    model_config = ConfigDict(frozen=True)

    items: list[T]
    cursor: Optional[str] = None
    has_more: bool = False


# ---------------------------------------------------------------------------
# Error envelope
# ---------------------------------------------------------------------------
class ErrorDetail(BaseModel):
    """Machine-readable error detail."""

    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    details: Optional[list[dict[str, Any]]] = None


class ErrorResponse(BaseModel):
    """Consistent error envelope returned by all endpoints."""

    model_config = ConfigDict(frozen=True)

    error: ErrorDetail
