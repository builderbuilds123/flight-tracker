"""Audit event emitter — creates AuditEvent domain objects.

This module provides a thin helper that services call after
state-changing operations to build and persist audit events.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Protocol

from src.domain.enums import ActorType, AuditAction
from src.domain.models.audit_event import AuditEvent
from src.observability.redaction import redact_state


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
        actor_id: str,
        actor_type: ActorType,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        prior_state: Optional[dict[str, Any]] = None,
        new_state: Optional[dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> AuditEvent:
        """Build, redact, and persist an audit event."""
        redacted_prior, fields_prior = redact_state(prior_state)
        redacted_new, fields_new = redact_state(new_state)
        all_redacted = sorted(set(fields_prior + fields_new))

        event = AuditEvent(
            id=uuid.uuid4(),
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            prior_state=redacted_prior,
            new_state=redacted_new,
            redacted_fields=all_redacted,
            trace_id=trace_id,
            created_at=datetime.now(timezone.utc),
        )
        return await self._repo.create(event)
