"""Cross-layer import test.

Ensure API and worker layers import the exact same domain model classes,
preventing drift between separate model definitions.
"""
from src.domain.models import User, Alert, PriceSnapshot, NotificationEvent, ProviderQuotaUsage
from src.domain.enums import AlertStatus, NotificationStatus
from src.infrastructure.db.models import (
    UserORM,
    AlertORM,
    PriceSnapshotORM,
    NotificationEventORM,
    ProviderQuotaUsageORM,
)


class TestCrossLayerImports:
    """All layers reference the same canonical classes."""

    def test_domain_models_importable_from_single_boundary(self):
        """All five domain entities importable from src.domain.models."""
        assert User is not None
        assert Alert is not None
        assert PriceSnapshot is not None
        assert NotificationEvent is not None
        assert ProviderQuotaUsage is not None

    def test_enums_importable_from_single_boundary(self):
        assert AlertStatus is not None
        assert NotificationStatus is not None

    def test_orm_models_importable(self):
        assert UserORM is not None
        assert AlertORM is not None
        assert PriceSnapshotORM is not None
        assert NotificationEventORM is not None
        assert ProviderQuotaUsageORM is not None

    def test_orm_uses_same_enum_types(self):
        """ORM status columns should reference the canonical enum classes."""
        # AlertORM.status column should use AlertStatus enum
        assert AlertORM.status_enum is AlertStatus
        # NotificationEventORM.status column should use NotificationStatus enum
        assert NotificationEventORM.status_enum is NotificationStatus
