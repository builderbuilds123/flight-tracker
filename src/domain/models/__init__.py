"""Canonical domain entities – single import boundary.

Usage:
    from src.domain.models import User, Alert, PriceSnapshot, ...
"""
from src.domain.models.user import User
from src.domain.models.alert import Alert
from src.domain.models.price_snapshot import PriceSnapshot
from src.domain.models.notification_event import NotificationEvent
from src.domain.models.provider_quota_usage import ProviderQuotaUsage
from src.domain.models.audit_event import AuditEvent

__all__ = [
    "User",
    "Alert",
    "PriceSnapshot",
    "NotificationEvent",
    "ProviderQuotaUsage",
    "AuditEvent",
]
