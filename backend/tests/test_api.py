import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)


class TestHealthEndpoints:
    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()

    def test_health_check(self):
        response = client.get("/api/v1/health-check")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data


class TestAuthEndpoints:
    def test_register_user(self):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "testpass123",
                "name": "Test User",
            },
        )
        assert response.status_code in [200, 400]

    def test_login(self):
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "admin@landslide.local", "password": "admin123"},
        )
        assert response.status_code in [200, 401]

    def test_login_invalid(self):
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "invalid@example.com", "password": "wrongpass"},
        )
        assert response.status_code == 401


class TestLandslideEndpoints:
    def test_get_active_landslides(self):
        response = client.get("/api/v1/active_landslides")
        assert response.status_code == 200
        assert "danger_zones" in response.json()

    def test_predict_requires_geotiff(self):
        files = {"file": ("test.png", b"fake image data", "image/png")}
        response = client.post("/api/v1/predict", files=files)
        assert response.status_code == 400


class TestWeatherEndpoints:
    def test_get_weather(self):
        response = client.get("/api/v1/weather?lat=31.52&lon=76.52")
        assert response.status_code == 200
        data = response.json()
        assert "current" in data or "location" in data

    def test_get_weather_missing_params(self):
        response = client.get("/api/v1/weather")
        assert response.status_code == 422


class TestEarlyWarningEndpoints:
    def test_get_early_warning_status(self):
        response = client.get("/api/v1/early-warning/status")
        assert response.status_code == 200
        data = response.json()
        assert "monitored_zones" in data

    def test_get_monitored_zones(self):
        response = client.get("/api/v1/early-warning/zones")
        assert response.status_code == 200
        data = response.json()
        assert "zones" in data

    def test_add_monitored_zone(self):
        response = client.post(
            "/api/v1/early-warning/zones?name=TestZone&lat=31.0&lon=76.0"
        )
        assert response.status_code == 200


class TestRouteEndpoint:
    def test_route_missing_data(self):
        response = client.post("/api/v1/route", json={})
        assert response.status_code in [400, 422]


class TestDashboard:
    def test_dashboard_loads(self):
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
