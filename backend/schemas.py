from pydantic import BaseModel
from typing import List, Optional, Tuple, Dict, Any


class PredictResponse(BaseModel):
    severity: str
    area_sq_meters: float
    longitude: Optional[float]
    latitude: Optional[float]


class Location(BaseModel):
    lat: float
    lon: float


class RouteRequest(BaseModel):
    origin: Location
    destination: Location


class RouteResponse(BaseModel):
    path_coordinates: List[Tuple[float, float]]
    total_distance_meters: float
    directions: List[str]
    gmaps_link: Optional[str]


class RiskAssessment(BaseModel):
    risk_level: str
    risk_score: int
    time_window: str
    rainfall_24h: Optional[float] = None
    soil_moisture: Optional[float] = None
    recommendations: List[str] = []


class RiskPredictionResponse(BaseModel):
    location: Dict[str, float]
    current_risk: RiskAssessment
    forecast_72h: List[Dict[str, Any]]
    critical_windows: List[Dict[str, Any]]
    weather_summary: Dict[str, Any]
    generated_at: str


class EvacuationTimeline(BaseModel):
    phase: str
    time: str
    hours_from_now: int
    action: str


class LandslideAlert(BaseModel):
    id: int
    severity: str
    area_sq_meters: float
    latitude: float
    longitude: float
    timestamp: float
    source_image: Optional[str] = None
    risk_assessment: Optional[RiskAssessment] = None
    evacuation_timeline: Optional[List[EvacuationTimeline]] = None
    email_sent: Optional[bool] = False
    email_recipients: Optional[List[str]] = None


class WeatherData(BaseModel):
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    precipitation: Optional[float] = None
    rain: Optional[float] = None
    soil_moisture: Optional[float] = None
    wind_speed: Optional[float] = None
    timestamp: Optional[str] = None


class EmailAlertRequest(BaseModel):
    landslide_id: int
    recipients: Optional[List[str]] = None


class EmailAlertResponse(BaseModel):
    status: str
    sent: List[str]
    failed: List[Dict[str, str]]
