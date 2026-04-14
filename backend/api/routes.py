from fastapi import APIRouter, File, UploadFile, HTTPException, Query
from typing import Optional, List
import os
from services.ml_service import model_service
from services.routing_service import routing_service
from services.db_service import db_service
from services.email_service import email_service
from services.weather_service import weather_service
from services.risk_prediction_service import risk_prediction_service
from services.early_warning_service import early_warning_system
from services.worker import background_monitor
from schemas import (
    PredictResponse,
    RouteRequest,
    RouteResponse,
    RiskPredictionResponse,
    EmailAlertRequest,
    EmailAlertResponse,
)

router = APIRouter()

# ============================================
# CORE FEATURE 1: Background Monitoring (PRIMARY)
# ============================================


@router.get("/monitor/status")
async def get_monitor_status():
    """Get background monitoring status."""
    return background_monitor.get_status()


@router.post("/monitor/start")
async def start_monitor():
    """Start background satellite monitoring."""
    if background_monitor.running:
        return {"status": "already_running", "message": "Monitor already running"}

    background_monitor.start()
    return {"status": "started", "message": "Background monitoring started"}


@router.post("/monitor/stop")
async def stop_monitor():
    """Stop background satellite monitoring."""
    background_monitor.stop()
    return {"status": "stopped", "message": "Background monitoring stopped"}


@router.post("/monitor/scan")
async def trigger_manual_scan():
    """Manually trigger a scan of all zones."""
    if not background_monitor.running:
        return {"status": "warning", "message": "Monitor not running. Starting..."}

    background_monitor._scan_all_zones()
    return {"status": "scanning", "message": "Manual scan triggered"}


@router.get("/monitor/zones")
async def get_monitor_zones():
    """Get list of zones being monitored."""
    return {
        "zones": [
            {"name": "Hamirpur", "lat": 31.52, "lon": 76.52, "state": "HP"},
            {"name": "Kangra", "lat": 32.09, "lon": 76.32, "state": "HP"},
            {"name": "Mandi", "lat": 31.71, "lon": 76.93, "state": "HP"},
            {"name": "Shimla", "lat": 31.10, "lon": 77.17, "state": "HP"},
            {"name": "Kullu", "lat": 31.96, "lon": 77.11, "state": "HP"},
            {"name": "Chamba", "lat": 32.55, "lon": 76.12, "state": "HP"},
            {"name": "Dehradun", "lat": 30.32, "lon": 78.03, "state": "UK"},
            {"name": "Tehri", "lat": 30.38, "lon": 78.48, "state": "UK"},
            {"name": "Chamoli", "lat": 30.73, "lon": 79.60, "state": "UK"},
            {"name": "Rudraprayag", "lat": 30.28, "lon": 78.97, "state": "UK"},
            {"name": "Nainital", "lat": 29.38, "lon": 79.45, "state": "UK"},
            {"name": "Srinagar", "lat": 34.08, "lon": 74.80, "state": "JK"},
            {"name": "Gulmarg", "lat": 34.15, "lon": 74.38, "state": "JK"},
            {"name": "Pahalgam", "lat": 34.01, "lon": 75.31, "state": "JK"},
            {"name": "Leh", "lat": 34.15, "lon": 77.58, "state": "Ladakh"},
            {"name": "Kargil", "lat": 34.55, "lon": 76.13, "state": "Ladakh"},
        ]
    }


# ============================================
# CORE FEATURE 2: Routing (SEPARATE)
# ============================================


@router.post("/route", response_model=RouteResponse)
async def calculate_route(request: RouteRequest):
    """Calculate safe route avoiding danger zones."""
    try:
        active_landslides = db_service.get_all()
        route_response = routing_service.calculate_safe_route(
            request, active_landslides
        )
        return route_response
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Routing calculation failed: {str(e)}"
        )


# ============================================
# SECONDARY FEATURE: Manual Image Upload
# ============================================


@router.post("/predict", response_model=PredictResponse)
async def predict_landslide(file: UploadFile = File(...)):
    """
    Upload a GeoTIFF image for landslide analysis.
    This is a secondary feature - primary monitoring runs automatically in background.
    """
    filename = file.filename or "upload.tif"
    file_ext = os.path.splitext(filename.lower())[1]

    if file_ext not in {".tif", ".tiff", ".gtiff"}:
        raise HTTPException(
            status_code=400, detail=f"Unsupported format. Use GeoTIFF (.tif, .tiff)"
        )

    try:
        file_bytes = await file.read()
        result = model_service.predict_from_bytes(file_bytes, filename)
        return PredictResponse(**result)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# ============================================
# Landslide Data Endpoints
# ============================================


@router.get("/landslides")
async def get_landslides(
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)
):
    """Get all detected landslides."""
    try:
        all_data = db_service.get_all()
        return {
            "landslides": all_data[offset : offset + limit],
            "total": len(all_data),
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/landslides/active")
async def get_active_landslides():
    """Get currently active/high-risk landslides."""
    try:
        all_data = db_service.get_all()
        active = [
            l for l in all_data if l.get("severity") in ["High", "Very High", "Medium"]
        ]
        return {"danger_zones": active, "total_count": len(active)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/landslides/{landslide_id}")
async def get_landslide_detail(landslide_id: int):
    """Get details of a specific landslide."""
    landslide = db_service.get_by_id(landslide_id)
    if not landslide:
        raise HTTPException(status_code=404, detail="Landslide not found")
    return landslide


@router.post("/landslides/{landslide_id}/send-alert")
async def send_alert_for_landslide(
    landslide_id: int, alert_request: Optional[EmailAlertRequest] = None
):
    """Send email alert for a specific landslide."""
    landslide = db_service.get_by_id(landslide_id)
    if not landslide:
        raise HTTPException(status_code=404, detail="Landslide not found")

    recipients = alert_request.recipients if alert_request else None
    result = email_service.send_alert(
        landslide, landslide.get("risk_assessment"), recipients or []
    )

    if result.get("sent"):
        db_service.update_email_status(landslide_id, True, result["sent"])

    return EmailAlertResponse(
        status="sent" if result.get("sent") else "failed",
        sent=result.get("sent", []),
        failed=result.get("failed", []),
    )


@router.get("/landslides/{landslide_id}/risk")
async def get_landslide_risk(landslide_id: int):
    """Get risk assessment for a landslide."""
    landslide = db_service.get_by_id(landslide_id)
    if not landslide:
        raise HTTPException(status_code=404, detail="Landslide not found")

    lat = landslide.get("latitude")
    lon = landslide.get("longitude")
    severity = landslide.get("severity")

    if not lat or not lon:
        raise HTTPException(status_code=400, detail="Location data not available")

    risk_data = risk_prediction_service.get_zone_risk_assessment(lat, lon, severity)
    return risk_data


# ============================================
# Manual Report Endpoints
# ============================================


@router.post("/report-landslide")
async def report_landslide(
    lat: float,
    lon: float,
    severity: str = "Medium",
    description: str = "",
    source: str = "manual_report",
):
    """
    Manually report a suspected landslide location.
    Sends targeted alerts to regional authorities.
    """
    try:
        import uuid
        import time

        landslide_data = {
            "latitude": lat,
            "longitude": lon,
            "severity": severity,
            "description": description,
            "source": source,
            "source_image": f"manual_{uuid.uuid4().hex[:8]}",
            "timestamp": int(time.time()),
        }

        landslide_id = db_service.add_landslide(landslide_data)

        targeted_recipients = email_service.get_targeted_authorities(lat, lon, severity)
        risk_data = risk_prediction_service.get_zone_risk_assessment(lat, lon, severity)

        recipients = [
            {"name": r["name"], "email": r["email"]} for r in targeted_recipients
        ]
        email_result = email_service.send_alert(
            landslide_data, risk_data.get("current_risk"), recipients
        )

        _, region_name = email_service._get_region_for_location(lat, lon)

        return {
            "status": "success",
            "landslide_id": landslide_id,
            "region": region_name,
            "risk_level": risk_data.get("current_risk", {}).get("risk_level", severity),
            "alerts_sent": len(email_result.get("sent", [])),
            "targeted_authorities": [r["name"] for r in targeted_recipients],
        }
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Weather Endpoints
# ============================================


@router.get("/weather")
async def get_weather(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
):
    """Get comprehensive weather data for a location."""
    try:
        weather_data = weather_service.get_comprehensive_weather_data(lat, lon)
        return weather_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Weather API Error: {str(e)}")


@router.get("/weather/forecast")
async def get_forecast(
    lat: float = Query(...),
    lon: float = Query(...),
    hours: int = Query(72, ge=1, le=168),
):
    """Get extended weather forecast."""
    try:
        forecast = weather_service.get_extended_forecast(lat, lon, hours=hours)
        return {"forecast": forecast, "location": {"lat": lat, "lon": lon}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecast Error: {str(e)}")


@router.post("/risk-predict")
async def predict_risk(
    lat: float = Query(...), lon: float = Query(...), severity: str = Query("Medium")
):
    """Get risk prediction for a location."""
    try:
        risk_data = risk_prediction_service.get_zone_risk_assessment(lat, lon, severity)
        return risk_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk Prediction Error: {str(e)}")


# ============================================
# Early Warning Endpoints
# ============================================


@router.get("/early-warning/status")
async def get_early_warning_status():
    """Get early warning system status."""
    try:
        zones = early_warning_system.get_watchlist()
        alerts = early_warning_system.get_alert_history(hours=24)
        report = early_warning_system.generate_daily_report()
        return {
            "monitored_zones": zones,
            "recent_alerts": alerts,
            "daily_report": report,
            "last_check": early_warning_system.last_check.isoformat()
            if early_warning_system.last_check
            else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/early-warning/check")
async def trigger_early_warning_check():
    """Trigger manual early warning check."""
    try:
        warnings = await early_warning_system.run_hourly_check()
        return {"status": "completed", "warnings": warnings, "count": len(warnings)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/early-warning/report")
async def get_daily_report():
    """Get daily early warning report."""
    return early_warning_system.generate_daily_report()


# ============================================
# Health Check
# ============================================


@router.get("/health")
async def health_check():
    """Check system health status."""
    monitor_status = background_monitor.get_status()

    weather_ok = False
    try:
        weather_service.get_current_weather(31.52, 76.52)
        weather_ok = True
    except:
        pass

    return {
        "status": "healthy",
        "timestamp": str(db_service.get_all().__len__()),
        "monitor": monitor_status,
        "weather_api": "ok" if weather_ok else "error",
        "db_entries": len(db_service.get_all()),
    }
