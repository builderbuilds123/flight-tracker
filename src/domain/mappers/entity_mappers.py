"""Typed mapping helpers for domain entity <-> ORM conversion."""
from __future__ import annotations

from src.domain.models.user import User
from src.domain.models.alert import Alert
from src.domain.models.price_snapshot import PriceSnapshot
from src.domain.models.notification_event import NotificationEvent
from src.domain.models.provider_quota_usage import ProviderQuotaUsage
from src.domain.models.audit_event import AuditEvent
from src.infrastructure.db.models import (
    UserORM,
    AlertORM,
    PriceSnapshotORM,
    NotificationEventORM,
    ProviderQuotaUsageORM,
    AuditEventORM,
)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
def user_from_orm(orm: UserORM) -> User:
    return User(
        id=orm.id,
        telegram_chat_id=orm.telegram_chat_id,
        timezone=orm.timezone,
        locale=orm.locale,
        created_at=orm.created_at,
    )


def user_to_orm(entity: User) -> UserORM:
    return UserORM(
        id=entity.id,
        telegram_chat_id=entity.telegram_chat_id,
        timezone=entity.timezone,
        locale=entity.locale,
        created_at=entity.created_at,
    )


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------
def alert_from_orm(orm: AlertORM) -> Alert:
    return Alert(
        id=orm.id,
        user_id=orm.user_id,
        origin_iata=orm.origin_iata,
        destination_iata=orm.destination_iata,
        depart_date_start=orm.depart_date_start,
        depart_date_end=orm.depart_date_end,
        max_price=orm.max_price,
        currency=orm.currency,
        check_interval_min=orm.check_interval_min,
        status=orm.status,
        last_checked_at=orm.last_checked_at,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def alert_to_orm(entity: Alert) -> AlertORM:
    return AlertORM(
        id=entity.id,
        user_id=entity.user_id,
        origin_iata=entity.origin_iata,
        destination_iata=entity.destination_iata,
        depart_date_start=entity.depart_date_start,
        depart_date_end=entity.depart_date_end,
        max_price=entity.max_price,
        currency=entity.currency,
        check_interval_min=entity.check_interval_min,
        status=entity.status,
        last_checked_at=entity.last_checked_at,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


# ---------------------------------------------------------------------------
# PriceSnapshot
# ---------------------------------------------------------------------------
def price_snapshot_from_orm(orm: PriceSnapshotORM) -> PriceSnapshot:
    return PriceSnapshot(
        id=orm.id,
        alert_id=orm.alert_id,
        provider=orm.provider,
        price=orm.price,
        currency=orm.currency,
        itinerary_hash=orm.itinerary_hash,
        raw_payload=orm.raw_payload,
        observed_at=orm.observed_at,
    )


def price_snapshot_to_orm(entity: PriceSnapshot) -> PriceSnapshotORM:
    return PriceSnapshotORM(
        id=entity.id,
        alert_id=entity.alert_id,
        provider=entity.provider,
        price=entity.price,
        currency=entity.currency,
        itinerary_hash=entity.itinerary_hash,
        raw_payload=entity.raw_payload,
        observed_at=entity.observed_at,
    )


# ---------------------------------------------------------------------------
# NotificationEvent
# ---------------------------------------------------------------------------
def notification_event_from_orm(orm: NotificationEventORM) -> NotificationEvent:
    return NotificationEvent(
        id=orm.id,
        alert_id=orm.alert_id,
        snapshot_id=orm.snapshot_id,
        channel=orm.channel,
        idempotency_key=orm.idempotency_key,
        status=orm.status,
        attempt_count=orm.attempt_count,
        last_error=orm.last_error,
        sent_at=orm.sent_at,
        created_at=orm.created_at,
    )


def notification_event_to_orm(entity: NotificationEvent) -> NotificationEventORM:
    return NotificationEventORM(
        id=entity.id,
        alert_id=entity.alert_id,
        snapshot_id=entity.snapshot_id,
        channel=entity.channel,
        idempotency_key=entity.idempotency_key,
        status=entity.status,
        attempt_count=entity.attempt_count,
        last_error=entity.last_error,
        sent_at=entity.sent_at,
        created_at=entity.created_at,
    )


# ---------------------------------------------------------------------------
# ProviderQuotaUsage
# ---------------------------------------------------------------------------
def provider_quota_from_orm(orm: ProviderQuotaUsageORM) -> ProviderQuotaUsage:
    return ProviderQuotaUsage(
        id=orm.id,
        provider=orm.provider,
        window_start=orm.window_start,
        window_end=orm.window_end,
        requests_used=orm.requests_used,
        requests_limit=orm.requests_limit,
    )


def provider_quota_to_orm(entity: ProviderQuotaUsage) -> ProviderQuotaUsageORM:
    return ProviderQuotaUsageORM(
        id=entity.id,
        provider=entity.provider,
        window_start=entity.window_start,
        window_end=entity.window_end,
        requests_used=entity.requests_used,
        requests_limit=entity.requests_limit,
    )


# ---------------------------------------------------------------------------
# AuditEvent
# ---------------------------------------------------------------------------
def audit_event_from_orm(orm: AuditEventORM) -> AuditEvent:
    return AuditEvent(
        id=orm.id,
        actor_id=orm.actor_id,
        actor_type=orm.actor_type,
        action=orm.action,
        entity_type=orm.entity_type,
        entity_id=orm.entity_id,
        old_state=orm.old_state,
        new_state=orm.new_state,
        metadata=orm.metadata_ or {},
        created_at=orm.created_at,
    )


def audit_event_to_orm(entity: AuditEvent) -> AuditEventORM:
    return AuditEventORM(
        id=entity.id,
        actor_id=entity.actor_id,
        actor_type=entity.actor_type,
        action=entity.action,
        entity_type=entity.entity_type,
        entity_id=entity.entity_id,
        old_state=entity.old_state,
        new_state=entity.new_state,
        metadata_=entity.metadata,
        created_at=entity.created_at,
    )
