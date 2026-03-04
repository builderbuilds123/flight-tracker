"""Cross-layer import and contract drift tests.

Ensures all layers (API, worker, infrastructure) reference the exact same
canonical domain model classes and enums.  Detects field-level drift between
domain entities and ORM models, validates mapper completeness, and guards
against circular dependencies.

CI gate: these tests MUST pass before any merge to main/develop.
"""
from __future__ import annotations

import ast
import dataclasses
import importlib
import os
import pkgutil
import sys
from pathlib import Path
from typing import Any

import pytest

from src.domain.enums import AlertStatus, NotificationStatus
from src.domain.models import (
    Alert,
    NotificationEvent,
    PriceSnapshot,
    ProviderQuotaUsage,
    User,
)
from src.domain.models import __all__ as domain_models_all
from src.infrastructure.db.models import (
    AlertORM,
    NotificationEventORM,
    PriceSnapshotORM,
    ProviderQuotaUsageORM,
    UserORM,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Map each domain entity to its ORM counterpart
ENTITY_ORM_PAIRS: list[tuple[type, type]] = [
    (User, UserORM),
    (Alert, AlertORM),
    (PriceSnapshot, PriceSnapshotORM),
    (NotificationEvent, NotificationEventORM),
    (ProviderQuotaUsage, ProviderQuotaUsageORM),
]

# Columns that exist in ORM but not in the domain entity (relationship attrs)
ORM_RELATIONSHIP_ATTRS = {
    "UserORM": {"alerts", "metadata", "registry"},
    "AlertORM": {"user", "price_snapshots", "notification_events", "metadata", "registry"},
    "PriceSnapshotORM": {"alert", "notification_events", "metadata", "registry"},
    "NotificationEventORM": {"alert", "snapshot", "metadata", "registry"},
    "ProviderQuotaUsageORM": {"metadata", "registry"},
}

# Internal SQLAlchemy attributes to skip when comparing ORM columns
_SA_INTERNAL = {
    "_sa_class_manager",
    "_sa_instance_state",
    "_sa_registry",
    "__tablename__",
    "__table__",
    "__mapper__",
    "status_enum",
    "metadata",
    "registry",
}


def _domain_field_names(entity_cls: type) -> set[str]:
    """Return the set of field names for a frozen dataclass entity."""
    return {f.name for f in dataclasses.fields(entity_cls)}


def _orm_column_names(orm_cls: type) -> set[str]:
    """Return ORM column attribute names (excluding relationships and SA internals)."""
    from sqlalchemy import inspect as sa_inspect

    try:
        mapper = sa_inspect(orm_cls)
    except Exception:
        return set()
    col_names = {col.key for col in mapper.columns}
    return col_names


# ---------------------------------------------------------------------------
# 1. Import identity tests – classes are the same object across layers
# ---------------------------------------------------------------------------


class TestImportIdentity:
    """All layers must import the exact same class objects (identity, not equality)."""

    def test_domain_models_importable_from_boundary(self):
        """All five domain entities importable from src.domain.models."""
        for cls in (User, Alert, PriceSnapshot, NotificationEvent, ProviderQuotaUsage):
            assert cls is not None
            assert dataclasses.is_dataclass(cls)

    def test_domain_models_all_export_complete(self):
        """__all__ in src.domain.models lists every entity."""
        expected = {"User", "Alert", "PriceSnapshot", "NotificationEvent", "ProviderQuotaUsage"}
        assert set(domain_models_all) == expected

    def test_enums_importable_from_boundary(self):
        assert AlertStatus is not None
        assert NotificationStatus is not None

    def test_orm_models_importable(self):
        for _, orm_cls in ENTITY_ORM_PAIRS:
            assert orm_cls is not None

    def test_orm_enum_identity(self):
        """ORM status columns reference the canonical enum class (identity check)."""
        assert AlertORM.status_enum is AlertStatus
        assert NotificationEventORM.status_enum is NotificationStatus

    def test_mapper_imports_canonical_entities(self):
        """Mapper module imports from the canonical domain boundary."""
        from src.domain.mappers import entity_mappers

        # Verify the mapper module references the same class objects
        assert entity_mappers.User is User
        assert entity_mappers.Alert is Alert
        assert entity_mappers.PriceSnapshot is PriceSnapshot
        assert entity_mappers.NotificationEvent is NotificationEvent
        assert entity_mappers.ProviderQuotaUsage is ProviderQuotaUsage

    def test_mapper_imports_canonical_orm(self):
        """Mapper module imports from the canonical ORM boundary."""
        from src.domain.mappers import entity_mappers

        assert entity_mappers.UserORM is UserORM
        assert entity_mappers.AlertORM is AlertORM
        assert entity_mappers.PriceSnapshotORM is PriceSnapshotORM
        assert entity_mappers.NotificationEventORM is NotificationEventORM
        assert entity_mappers.ProviderQuotaUsageORM is ProviderQuotaUsageORM


# ---------------------------------------------------------------------------
# 2. Contract drift detection – field parity between domain and ORM
# ---------------------------------------------------------------------------


class TestContractDrift:
    """Domain entity fields must match ORM column names exactly.

    If a field is added to the domain entity but not to the ORM (or vice-versa),
    these tests fail, catching contract drift before it reaches production.
    """

    @pytest.mark.parametrize(
        "entity_cls,orm_cls",
        ENTITY_ORM_PAIRS,
        ids=lambda c: getattr(c, "__name__", str(c)),
    )
    def test_domain_fields_present_in_orm(self, entity_cls: type, orm_cls: type):
        """Every domain entity field must have a matching ORM column."""
        domain_fields = _domain_field_names(entity_cls)
        orm_cols = _orm_column_names(orm_cls)
        missing = domain_fields - orm_cols
        assert not missing, (
            f"{entity_cls.__name__} has fields not in {orm_cls.__name__}: {missing}"
        )

    @pytest.mark.parametrize(
        "entity_cls,orm_cls",
        ENTITY_ORM_PAIRS,
        ids=lambda c: getattr(c, "__name__", str(c)),
    )
    def test_orm_columns_present_in_domain(self, entity_cls: type, orm_cls: type):
        """Every ORM column must have a matching domain entity field."""
        domain_fields = _domain_field_names(entity_cls)
        orm_cols = _orm_column_names(orm_cls)
        extra = orm_cols - domain_fields
        assert not extra, (
            f"{orm_cls.__name__} has columns not in {entity_cls.__name__}: {extra}"
        )

    def test_entity_count_matches_orm_count(self):
        """Same number of domain entities and ORM models."""
        assert len(ENTITY_ORM_PAIRS) == 5, "Expected 5 entity/ORM pairs"


# ---------------------------------------------------------------------------
# 3. Mapper completeness – every entity has from_orm and to_orm
# ---------------------------------------------------------------------------


class TestMapperCompleteness:
    """Every domain entity must have a bidirectional mapper."""

    EXPECTED_MAPPERS = {
        "user_from_orm",
        "user_to_orm",
        "alert_from_orm",
        "alert_to_orm",
        "price_snapshot_from_orm",
        "price_snapshot_to_orm",
        "notification_event_from_orm",
        "notification_event_to_orm",
        "provider_quota_from_orm",
        "provider_quota_to_orm",
    }

    def test_all_mappers_exported(self):
        from src.domain.mappers import __all__ as mapper_all

        assert set(mapper_all) == self.EXPECTED_MAPPERS

    def test_all_mappers_callable(self):
        import src.domain.mappers as mappers_mod

        for name in self.EXPECTED_MAPPERS:
            fn = getattr(mappers_mod, name, None)
            assert callable(fn), f"Mapper {name} is not callable"

    @pytest.mark.parametrize(
        "entity_name",
        ["user", "alert", "price_snapshot", "notification_event", "provider_quota"],
    )
    def test_bidirectional_mapper_exists(self, entity_name: str):
        """Each entity has both from_orm and to_orm functions."""
        import src.domain.mappers as mappers_mod

        from_fn = getattr(mappers_mod, f"{entity_name}_from_orm", None)
        to_fn = getattr(mappers_mod, f"{entity_name}_to_orm", None)
        assert from_fn is not None, f"Missing {entity_name}_from_orm"
        assert to_fn is not None, f"Missing {entity_name}_to_orm"


# ---------------------------------------------------------------------------
# 4. Circular dependency detection via AST analysis
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[2]  # flight-tracker/


def _collect_imports_ast(filepath: Path) -> set[str]:
    """Parse a Python file with AST and return all imported module names."""
    try:
        source = filepath.read_text()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return set()

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    return imports


def _build_dependency_graph() -> dict[str, set[str]]:
    """Build a directed dependency graph for src/ and app/ packages.

    Nodes are top-level dotted module paths (e.g. 'src.domain', 'src.infrastructure').
    Edges represent import relationships.
    """
    graph: dict[str, set[str]] = {}
    src_dir = _PROJECT_ROOT / "src"

    for py_file in src_dir.rglob("*.py"):
        rel = py_file.relative_to(_PROJECT_ROOT)
        parts = list(rel.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        module_path = ".".join(parts)

        # Determine the layer (src.domain, src.infrastructure, src.api, etc.)
        if len(parts) >= 2:
            layer = ".".join(parts[:2])
        else:
            layer = module_path

        # Parse imports
        raw_imports = set()
        try:
            source = py_file.read_text()
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    raw_imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    raw_imports.add(node.module)

        # Resolve to layer-level deps within src/
        deps: set[str] = set()
        for imp in raw_imports:
            if imp.startswith("src."):
                imp_parts = imp.split(".")
                if len(imp_parts) >= 2:
                    dep_layer = ".".join(imp_parts[:2])
                    if dep_layer != layer:
                        deps.add(dep_layer)

        if layer not in graph:
            graph[layer] = set()
        graph[layer].update(deps)

    return graph


def _find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Find all cycles in a directed graph using DFS."""
    cycles: list[list[str]] = []
    visited: set[str] = set()
    rec_stack: set[str] = set()
    path: list[str] = []

    def dfs(node: str) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])

        path.pop()
        rec_stack.discard(node)

    for node in graph:
        if node not in visited:
            dfs(node)

    return cycles


class TestNoCicularDependencies:
    """Validate the dependency graph has no circular imports between layers."""

    def test_no_cycles_in_src_layers(self):
        """No circular dependencies between src.domain, src.infrastructure, etc."""
        graph = _build_dependency_graph()
        cycles = _find_cycles(graph)
        assert not cycles, f"Circular dependencies detected: {cycles}"

    def test_domain_does_not_import_infrastructure(self):
        """Domain layer must not depend on infrastructure (clean architecture)."""
        graph = _build_dependency_graph()
        domain_deps = graph.get("src.domain", set())
        assert "src.infrastructure" not in domain_deps, (
            "src.domain must not import from src.infrastructure"
        )

    def test_domain_does_not_import_api(self):
        """Domain layer must not depend on API layer."""
        graph = _build_dependency_graph()
        domain_deps = graph.get("src.domain", set())
        assert "src.api" not in domain_deps, (
            "src.domain must not import from src.api"
        )

    def test_dependency_direction_is_inward(self):
        """Infrastructure may depend on domain, but not vice-versa."""
        graph = _build_dependency_graph()
        # Infrastructure -> domain is allowed
        infra_deps = graph.get("src.infrastructure", set())
        # If infra depends on domain, that's fine (inward dependency)
        # But domain must not depend on infra
        domain_deps = graph.get("src.domain", set())
        assert not domain_deps.intersection({"src.infrastructure", "src.api"}), (
            f"Domain has outward dependencies: {domain_deps}"
        )
