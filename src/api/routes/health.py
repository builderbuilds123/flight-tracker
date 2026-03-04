"""Re-export the health router for the src layer.

The actual implementation lives in ``app.api.health`` so that
FastAPI router registration stays in one place.  This module exists
as the canonical import path referenced by the story (S6-01).
"""
from app.api.health import router  # noqa: F401

__all__ = ["router"]
