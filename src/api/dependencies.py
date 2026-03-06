"""Shared FastAPI dependencies for the src API layer."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    api_key: str | None = Security(_api_key_header),
) -> dict:
    """Validate the request carries a valid API key.

    Returns a minimal user-like dict for downstream code.
    Raises 401 if the key is missing or invalid.
    """
    if not api_key or api_key != settings.SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )
    return {"api_key": api_key}
