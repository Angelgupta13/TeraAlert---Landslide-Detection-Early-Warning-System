"""
TeraAlert - Himalayan Landslide Detection & Early Warning System
Final Year Project - ML-Based Landslide Detection

Author: Angel Gupta
"""

import os
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

# Optional imports - graceful degradation
MONITOR_AVAILABLE = False
background_monitor = None
satellite_client = None

try:
    from services.worker import background_monitor as _bm
    from services.satellite_api import satellite_client as _sc

    background_monitor = _bm
    satellite_client = _sc
    MONITOR_AVAILABLE = True
except ImportError:
    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    global MONITOR_AVAILABLE

    if MONITOR_AVAILABLE and background_monitor:
        try:
            import pystac_client
            import planetary_computer

            if satellite_client:
                satellite_client.catalog = pystac_client.Client.open(
                    satellite_client.STAC_URL, modifier=planetary_computer.sign_inplace
                )
                background_monitor.stac_available = True
                print("[STARTUP] STAC API connected - Real satellite imagery enabled")
        except ImportError:
            print("[STARTUP] STAC libraries not installed - Using simulated data")
        except Exception as e:
            print(f"[STARTUP] STAC connection failed: {e}")

        background_monitor.satellite = satellite_client
        background_monitor.start()
        print("[STARTUP] Background monitoring started")

    yield

    if MONITOR_AVAILABLE and background_monitor:
        background_monitor.stop()
        print("[SHUTDOWN] Background monitoring stopped")


app = FastAPI(
    title="TeraAlert",
    description="Himalayan Landslide Detection & Early Warning System",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import services
from services.db_service import db_service
from services.weather_service import weather_service
from services.email_service import email_service
from services.risk_prediction_service import risk_prediction_service


# ==================== FRONTEND ROUTES ====================


def _read_html(filename: str) -> str:
    """Read HTML file from frontend directory."""
    path = os.path.join(os.path.dirname(__file__), "..", "frontend", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/", response_class=HTMLResponse)
async def home():
    return _read_html("index.html")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return _read_html("dashboard.html")


@app.get("/route", response_class=HTMLResponse)
async def route():
    return _read_html("route.html")


# ==================== API ROUTES ====================


@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "service": "TeraAlert v2.0.0",
        "ml_monitoring_active": MONITOR_AVAILABLE and background_monitor.running
        if background_monitor
        else False,
    }


@app.get("/api/ml/status")
async def ml_status():
    if not MONITOR_AVAILABLE:
        return {"available": False, "error": "ML service not available"}

    monitor_status = background_monitor.get_status()

    model_loaded = False
    try:
        from services.ml_service import model_service

        model_loaded = model_service.model is not None
    except Exception:
        pass

    return {
        "available": True,
        "monitor_running": monitor_status.get("running", False),
        "model_loaded": model_loaded,
        "stac_available": monitor_status.get("stac_available", False),
        "last_scan": monitor_status.get("last_scan"),
        "scan_interval_seconds": monitor_status.get("scan_interval", 300),
    }


@app.get("/api/landslides")
async def get_landslides():
    landslides = db_service.get_all()
    return {"landslides": landslides, "total": len(landslides)}


@app.get("/api/landslides/active")
async def get_active_landslides():
    landslides = db_service.get_all()
    return {"danger_zones": landslides, "count": len(landslides)}


@app.get("/api/weather")
async def weather(lat: float, lon: float):
    try:
        return weather_service.get_comprehensive_weather_data(lat, lon)
    except Exception as e:
        print(f"Weather error: {e}")
        return {"error": str(e), "current": {}, "forecast_24h": {}}


@app.get("/api/prediction")
async def get_prediction(lat: float = 31.5, lon: float = 77.0):
    """Get 72-hour landslide risk prediction based on weather data."""
    try:
        forecast = risk_prediction_service.predict_future_risk(lat, lon, hours_ahead=72)

        high_risk = [
            f for f in forecast if f.get("risk_level") in ["Very High", "High"]
        ]
        medium_risk = [f for f in forecast if f.get("risk_level") == "Medium"]

        return {
            "location": {"lat": lat, "lon": lon},
            "prediction_hours": 72,
            "current_conditions": forecast[0] if forecast else None,
            "highest_risk": high_risk[0] if high_risk else None,
            "first_medium_risk": medium_risk[0] if medium_risk else None,
            "timeline": forecast[:12] if forecast else [],
            "high_risk_periods": len(high_risk),
        }
    except Exception as e:
        return {"error": str(e)}


MONITORING_ZONES = [
    {"name": "Hamirpur District", "lat": 31.52, "lon": 76.52},
    {"name": "Kangra Valley", "lat": 32.09, "lon": 76.32},
    {"name": "Mandi Region", "lat": 31.71, "lon": 76.93},
    {"name": "Shimla Hills", "lat": 31.10, "lon": 77.17},
    {"name": "Kullu Valley", "lat": 31.96, "lon": 77.11},
    {"name": "Chamba District", "lat": 32.55, "lon": 76.12},
    {"name": "Dehradun Valley", "lat": 30.32, "lon": 78.03},
    {"name": "Tehri Garhwal", "lat": 30.38, "lon": 78.48},
    {"name": "Chamoli Region", "lat": 30.73, "lon": 79.60},
    {"name": "Rudraprayag", "lat": 30.28, "lon": 78.97},
    {"name": "Srinagar Valley", "lat": 34.08, "lon": 74.80},
    {"name": "Leh Ladakh", "lat": 34.15, "lon": 77.58},
]


@app.get("/api/risk-zones")
async def get_risk_zones():
    """Get real-time risk assessment for all monitoring zones.

    Data Source: Open-Meteo Weather API
    Calculation: Based on 24-hour rainfall + soil moisture levels
    """
    risk_zones = []

    for zone in MONITORING_ZONES:
        try:
            risk_data = risk_prediction_service.get_zone_risk_assessment(
                zone["lat"], zone["lon"], detected_severity="Low"
            )
            current_risk = risk_data.get("current_risk", {})
            weather_summary = risk_data.get("weather_summary", {})
            forecast_24h = weather_summary.get("forecast_24h", {})

            risk_zones.append(
                {
                    "name": zone["name"],
                    "lat": zone["lat"],
                    "lon": zone["lon"],
                    "risk_level": current_risk.get("risk_level", "Unknown"),
                    "risk_score": current_risk.get("risk_score", 0),
                    "rainfall_24h_mm": forecast_24h.get("rainfall_24h", 0),
                    "soil_moisture_percent": current_risk.get("soil_moisture", 0),
                    "time_window": current_risk.get("time_window", "N/A"),
                }
            )
        except Exception as e:
            risk_zones.append(
                {
                    "name": zone["name"],
                    "lat": zone["lat"],
                    "lon": zone["lon"],
                    "risk_level": "Unknown",
                    "risk_score": 0,
                    "error": str(e),
                }
            )

    order = {
        "Very High": 0,
        "High": 1,
        "Medium": 2,
        "Low": 3,
        "Minimal": 4,
        "Unknown": 5,
    }
    risk_zones.sort(key=lambda x: order.get(x["risk_level"], 5))

    return {
        "zones": risk_zones,
        "count": len(risk_zones),
        "data_source": "Open-Meteo Weather API",
    }


@app.get("/api/email/status")
async def email_status():
    return {
        "configured": bool(email_service.smtp_username),
        "smtp_username": email_service.smtp_username.split("@")[0] + "@..."
        if email_service.smtp_username
        else "not configured",
        "authorities_count": len(email_service.all_contacts),
    }


@app.post("/api/report")
async def report_landslide(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    severity: str = "Medium",
    request: dict = None,
):
    """Submit manual landslide report."""
    if request:
        lat = lat or request.get("latitude")
        lon = lon or request.get("longitude")
        severity = request.get("severity", severity)
        description = request.get("description", "")
    else:
        description = ""

    data = {
        "latitude": lat or 0.0,
        "longitude": lon or 0.0,
        "severity": severity,
        "source": "manual_report",
        "description": description,
        "timestamp": int(time.time()),
    }

    landslide_id = db_service.add_landslide(data)
    return {"status": "submitted", "id": landslide_id}


@app.get("/api/monitor/zones")
async def get_monitor_zones():
    return {
        "zones": [
            {"name": z["name"], "lat": z["lat"], "lon": z["lon"]}
            for z in MONITORING_ZONES
        ],
        "total_zones": len(MONITORING_ZONES),
        "scan_interval_seconds": 300,
    }


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("  TeraAlert - Himalayan Landslide Detection System")
    print("  Version: 2.0.0")
    print("=" * 60)
    print("  Dashboard: http://localhost:8000/")
    print("  API Docs:  http://localhost:8000/docs")
    print("=" * 60)
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000)
