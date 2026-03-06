"""Unit tests for alert service audit emission with explicit ActorContext."""
from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.domain.enums import ActorType, AlertStatus, AuditAction
from src.domain.models.alert import Alert
from src.domain.models.audit_event import ActorContext, AuditEvent
from src.services.alert_service import AlertService


def _make_alert(**overrides) -> Alert:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        origin_iata="JFK",
        destination_iata="LHR",
        depart_date_start=now,
        depart_date_end=now,
        max_price=Decimal("100.00"),
        currency="USD",
        check_interval_min=60,
        status=AlertStatus.ACTIVE,
        last_checked_at=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return Alert(**defaults)


class _AlertsRepo:
    def __init__(self) -> None:
        self.data: dict[uuid.UUID, Alert] = {}

    async def create(self, alert: Alert) -> Alert:
        self.data[alert.id] = alert
        return alert

    async def get_by_id(self, alert_id: uuid.UUID) -> Alert | None:
        return self.data.get(alert_id)

    async def update(self, alert: Alert) -> Alert:
        self.data[alert.id] = alert
        return alert


class _AuditRepo:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def create(self, event: AuditEvent) -> AuditEvent:
        self.events.append(event)
        return event


@pytest.mark.asyncio
async def test_create_alert_emits_audit_event():
    alerts_repo = _AlertsRepo()
    audit_repo = _AuditRepo()
    service = AlertService(alerts_repo=alerts_repo, audit_repo=audit_repo)
    alert = _make_alert()
    actor = ActorContext(actor_type=ActorType.USER, actor_id=uuid.uuid4())

    created = await service.create_alert(alert=alert, actor=actor)

    assert created.id == alert.id
    assert len(audit_repo.events) == 1
    event = audit_repo.events[0]
    assert event.action == AuditAction.ALERT_CREATED
    assert event.entity_type == "Alert"
    assert event.entity_id == alert.id
    assert event.actor_id == actor.actor_id


@pytest.mark.asyncio
async def test_update_alert_status_emits_prior_and_new_state():
    alerts_repo = _AlertsRepo()
    audit_repo = _AuditRepo()
    service = AlertService(alerts_repo=alerts_repo, audit_repo=audit_repo)
    actor = ActorContext(actor_type=ActorType.USER, actor_id=uuid.uuid4())
    alert = _make_alert(status=AlertStatus.ACTIVE)
    await alerts_repo.create(alert)

    updated = await service.update_alert_status(
        alert_id=alert.id,
        target_status=AlertStatus.PAUSED,
        actor=actor,
    )

    assert updated.status == AlertStatus.PAUSED
    event = audit_repo.events[0]
    assert event.action == AuditAction.ALERT_PAUSED
    assert event.old_state == {"status": "active"}
    assert event.new_state == {"status": "paused"}
