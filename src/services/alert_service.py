"""Alert mutation service with explicit audit emission."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Protocol

from src.domain.enums import AlertStatus, AuditAction
from src.domain.models.alert import Alert
from src.domain.models.audit_event import ActorContext, AuditEvent
from src.observability.redaction import redact_payload


class AlertsRepoProtocol(Protocol):
    async def create(self, alert: Alert) -> Alert: ...
    async def get_by_id(self, alert_id: uuid.UUID) -> Alert | None: ...
    async def update(self, alert: Alert) -> Alert: ...


class AuditRepoProtocol(Protocol):
    async def create(self, event: AuditEvent) -> AuditEvent: ...


class AlertService:
    def __init__(self, alerts_repo: AlertsRepoProtocol, audit_repo: AuditRepoProtocol) -> None:
        self._alerts_repo = alerts_repo
        self._audit_repo = audit_repo

    async def create_alert(self, *, alert: Alert, actor: ActorContext) -> Alert:
        created = await self._alerts_repo.create(alert)
        event = AuditEvent(
            id=uuid.uuid4(),
            actor_id=actor.actor_id,
            actor_type=actor.actor_type,
            action=AuditAction.ALERT_CREATED,
            entity_type="Alert",
            entity_id=created.id,
            old_state=None,
            new_state=redact_payload({"status": created.status.value}),
            metadata={},
            created_at=datetime.now(timezone.utc),
        )
        await self._audit_repo.create(event)
        return created

    async def update_alert_status(
        self,
        *,
        alert_id: uuid.UUID,
        target_status: AlertStatus,
        actor: ActorContext,
    ) -> Alert:
        current = await self._alerts_repo.get_by_id(alert_id)
        if current is None:
            raise ValueError(f"Alert {alert_id} not found")

        updated = await self._alerts_repo.update(current.transition_to(target_status))
        action_map = {
            AlertStatus.PAUSED: AuditAction.ALERT_PAUSED,
            AlertStatus.ACTIVE: AuditAction.ALERT_RESUMED,
            AlertStatus.ARCHIVED: AuditAction.ALERT_ARCHIVED,
        }
        event = AuditEvent(
            id=uuid.uuid4(),
            actor_id=actor.actor_id,
            actor_type=actor.actor_type,
            action=action_map.get(target_status, AuditAction.ALERT_UPDATED),
            entity_type="Alert",
            entity_id=updated.id,
            old_state=redact_payload({"status": current.status.value}),
            new_state=redact_payload({"status": updated.status.value}),
            metadata={},
            created_at=datetime.now(timezone.utc),
        )
        await self._audit_repo.create(event)
        return updated
