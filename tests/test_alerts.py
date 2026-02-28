"""
Tests for alert API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.alert import Alert


# Test database setup (SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

test_async_session_maker = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    """Override database dependency for testing"""
    async with test_async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Override database dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function", autouse=True)
async def setup_database():
    """Create tables before each test"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestAlertsAPI:
    """Test cases for alerts API"""
    
    def test_create_alert(self, client):
        """Test creating a new alert"""
        alert_data = {
            "user_id": "123456789",
            "origin": "JFK",
            "destination": "LHR",
            "max_price": 500.00,
            "currency": "USD",
            "check_frequency_hours": 6,
        }
        
        response = client.post("/api/v1/alerts/", json=alert_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == "123456789"
        assert data["origin"] == "JFK"
        assert data["destination"] == "LHR"
        assert data["max_price"] == 500.00
        assert data["is_active"] is True
    
    def test_create_alert_invalid_iata(self, client):
        """Test creating alert with invalid IATA code"""
        alert_data = {
            "user_id": "123456789",
            "origin": "INVALID",
            "destination": "LHR",
            "max_price": 500.00,
        }
        
        response = client.post("/api/v1/alerts/", json=alert_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_list_alerts(self, client):
        """Test listing alerts for a user"""
        # Create first alert
        alert1 = {
            "user_id": "123456789",
            "origin": "JFK",
            "destination": "LHR",
            "max_price": 500.00,
        }
        client.post("/api/v1/alerts/", json=alert1)
        
        # Create second alert
        alert2 = {
            "user_id": "123456789",
            "origin": "LAX",
            "destination": "CDG",
            "max_price": 600.00,
        }
        client.post("/api/v1/alerts/", json=alert2)
        
        # List alerts
        response = client.get("/api/v1/alerts/?user_id=123456789")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_get_alert(self, client):
        """Test getting a specific alert"""
        # Create alert
        alert_data = {
            "user_id": "123456789",
            "origin": "JFK",
            "destination": "LHR",
            "max_price": 500.00,
        }
        create_response = client.post("/api/v1/alerts/", json=alert_data)
        alert_id = create_response.json()["id"]
        
        # Get alert
        response = client.get(f"/api/v1/alerts/{alert_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == alert_id
        assert data["origin"] == "JFK"
    
    def test_get_alert_not_found(self, client):
        """Test getting non-existent alert"""
        response = client.get("/api/v1/alerts/9999")
        
        assert response.status_code == 404
    
    def test_update_alert(self, client):
        """Test updating an alert"""
        # Create alert
        alert_data = {
            "user_id": "123456789",
            "origin": "JFK",
            "destination": "LHR",
            "max_price": 500.00,
        }
        create_response = client.post("/api/v1/alerts/", json=alert_data)
        alert_id = create_response.json()["id"]
        
        # Update alert
        update_data = {"max_price": 450.00, "is_active": False}
        response = client.put(f"/api/v1/alerts/{alert_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["max_price"] == 450.00
        assert data["is_active"] is False
    
    def test_delete_alert(self, client):
        """Test deleting an alert"""
        # Create alert
        alert_data = {
            "user_id": "123456789",
            "origin": "JFK",
            "destination": "LHR",
            "max_price": 500.00,
        }
        create_response = client.post("/api/v1/alerts/", json=alert_data)
        alert_id = create_response.json()["id"]
        
        # Delete alert
        response = client.delete(f"/api/v1/alerts/{alert_id}")
        
        assert response.status_code == 204
        
        # Verify deletion
        get_response = client.get(f"/api/v1/alerts/{alert_id}")
        assert get_response.status_code == 404
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/api/v1/health/")
        
        assert response.status_code in [200, 503]  # May be degraded in test env
        data = response.json()
        assert "status" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
