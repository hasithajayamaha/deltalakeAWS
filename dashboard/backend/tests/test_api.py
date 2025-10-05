"""Basic API tests for DataLake Discovery Dashboard."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns correct response."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_version_endpoint():
    """Test version endpoint."""
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    data = response.json()
    assert "api_version" in data
    assert "deltalake_aws_version" in data


def test_discover_endpoint_structure():
    """Test discover endpoint returns correct structure."""
    response = client.get("/api/v1/discover")
    # May fail if AWS credentials not configured, but structure should be correct
    if response.status_code == 200:
        data = response.json()
        assert "timestamp" in data
        assert "region" in data
        assert "resources" in data


def test_cost_estimate_endpoint():
    """Test cost estimate endpoint."""
    response = client.get("/api/v1/cost/estimate?scenario=medium")
    assert response.status_code == 200
    data = response.json()
    assert "monthly_cost" in data
    assert "currency" in data
    assert "breakdown" in data
    assert "assumptions" in data


def test_cost_scenarios_endpoint():
    """Test cost scenarios endpoint."""
    response = client.get("/api/v1/cost/scenarios")
    assert response.status_code == 200
    data = response.json()
    # Should have multiple scenarios
    assert len(data) >= 3


def test_deployment_history_stub():
    """Test deployment history endpoint (stub)."""
    response = client.get("/api/v1/deploy/history")
    assert response.status_code == 200
    data = response.json()
    assert "deployments" in data


def test_invalid_endpoint():
    """Test invalid endpoint returns 404."""
    response = client.get("/api/v1/invalid")
    assert response.status_code == 404
