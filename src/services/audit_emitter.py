"""Audit event emitter — creates AuditEvent domain objects.

This module provides a thin helper that services call after
state-changing operations to build and persist audit events.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from src.domain.enums import AuditAction
from src.domain.models.audit_event import ActorContext, AuditEvent
from src.observability.redaction import redact_payload


class AuditRepoProtocol(Protocol):
    """Minimal write interface expected from the audit repository."""

    async def create(self, event: AuditEvent) -> AuditEvent: ...


class AuditEmitter:
    """Emits audit events through the configured repository."""

    def __init__(self, repo: AuditRepoProtocol) -> None:
        self._repo = repo

    async def emit(
        self,
        *,
        actor: ActorContext,
        action: AuditAction,
        entity_type: str,
        entity_id: uuid.UUID,
        old_state: dict[str, Any] | None = None,
        new_state: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Build, redact, and persist an audit event."""
        event = AuditEvent(
            id=uuid.uuid4(),
            actor_id=actor.actor_id,
            actor_type=actor.actor_type,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_state=redact_payload(old_state),
            new_state=redact_payload(new_state),
            metadata=redact_payload(metadata) or {},
            created_at=datetime.now(timezone.utc),
        )
        return await self._repo.create(event)
