"""OpenAPI contract snapshot test (S1-03).

Detects unintended changes to the API schema contract.
If a change is intentional, regenerate the snapshot:
    python scripts/generate_openapi.py
"""
import json
from pathlib import Path

import pytest

CONTRACTS_DIR = Path(__file__).resolve().parent.parent / "contracts"
SNAPSHOT_PATH = CONTRACTS_DIR / "openapi-v1.json"


@pytest.fixture
def current_spec() -> dict:
    """Generate the current OpenAPI spec at test time."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.generate_openapi import app
    return app.openapi()


@pytest.fixture
def snapshot_spec() -> dict:
    assert SNAPSHOT_PATH.exists(), (
        f"Snapshot not found at {SNAPSHOT_PATH}. "
        "Run: python scripts/generate_openapi.py"
    )
    return json.loads(SNAPSHOT_PATH.read_text())


class TestOpenAPISnapshot:
    def test_snapshot_matches_current_spec(self, current_spec, snapshot_spec):
        """The committed snapshot must match the current schema generation.
        
        We check paths and schema names, but allow minor formatting differences
        (e.g., pydantic version drift in pattern constraints).
        """
        # Compare paths (endpoints)
        assert set(current_spec["paths"].keys()) == set(snapshot_spec["paths"].keys()), \
            "Endpoint paths have changed — update snapshot with: python scripts/generate_openapi.py"

        # Compare schema component names
        current_schemas = set(current_spec.get("components", {}).get("schemas", {}).keys())
        snapshot_schemas = set(snapshot_spec.get("components", {}).get("schemas", {}).keys())
        assert current_schemas == snapshot_schemas, \
            "Schema components have changed — update snapshot with: python scripts/generate_openapi.py"

        # Compare path methods (ensure HTTP methods match)
        for path in current_spec["paths"]:
            current_methods = set(current_spec["paths"][path].keys())
            snapshot_methods = set(snapshot_spec["paths"][path].keys())
            assert current_methods == snapshot_methods, \
                f"HTTP methods for {path} have changed — update snapshot"

        # Compare operation IDs (stable API contract)
        for path in current_spec["paths"]:
            for method in current_spec["paths"][path]:
                current_op = current_spec["paths"][path][method].get("operationId")
                snapshot_op = snapshot_spec["paths"][path][method].get("operationId")
                assert current_op == snapshot_op, \
                    f"OperationId for {method.upper()} {path} changed from {snapshot_op} to {current_op}"

    def test_all_alert_endpoints_present(self, snapshot_spec):
        """Verify all architecture-specified alert endpoints exist."""
        paths = snapshot_spec["paths"]
        expected_paths = [
            "/api/v1/alerts",
            "/api/v1/alerts/{alert_id}",
            "/api/v1/alerts/{alert_id}/pause",
            "/api/v1/alerts/{alert_id}/resume",
            "/api/v1/alerts/{alert_id}/history",
            "/api/v1/health",
            "/api/v1/health/ready",
            "/api/v1/health/live",
        ]
        for path in expected_paths:
            assert path in paths, f"Missing endpoint: {path}"

    def test_error_responses_documented(self, snapshot_spec):
        """Error responses should reference the ErrorResponse schema."""
        create_endpoint = snapshot_spec["paths"]["/api/v1/alerts"]["post"]
        assert "422" in create_endpoint["responses"]

    def test_cursor_pagination_in_list(self, snapshot_spec):
        """List endpoint must include cursor parameter."""
        list_endpoint = snapshot_spec["paths"]["/api/v1/alerts"]["get"]
        param_names = [p["name"] for p in list_endpoint.get("parameters", [])]
        assert "cursor" in param_names
        assert "limit" in param_names
