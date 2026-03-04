"""User domain entity."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class User:
    """Canonical user entity – maps to the ``users`` table."""

    id: uuid.UUID
    telegram_chat_id: str
    timezone: str
    locale: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.telegram_chat_id:
            raise ValueError("telegram_chat_id is required")
