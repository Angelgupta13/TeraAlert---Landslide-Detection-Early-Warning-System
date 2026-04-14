from datetime import datetime, timedelta
from typing import Dict, List, Optional
from services.weather_service import weather_service


class RiskPredictionService:
    RAINFALL_THRESHOLDS = {"low": 10, "moderate": 25, "high": 50, "very_high": 100}

    SOIL_MOISTURE_THRESHOLDS = {"low": 30, "moderate": 50, "high": 70, "very_high": 85}

    def __init__(self):
        self.historical_risks = {}

    def calculate_instant_risk(self, severity: str, weather_data: Dict) -> Dict:
        severity_scores = {
            "No Landslide": 0,
            "Low": 1,
            "Medium": 2,
            "High": 3,
            "Very High": 4,
        }

        base_score = severity_scores.get(severity, 0)

        rainfall_24h = weather_data.get("forecast_24h", {}).get("rainfall_24h", 0)
        soil_moisture = weather_data.get("forecast_24h", {}).get("max_soil_moisture", 0)

        rainfall_score = 0
        if rainfall_24h >= self.RAINFALL_THRESHOLDS["very_high"]:
            rainfall_score = 4
        elif rainfall_24h >= self.RAINFALL_THRESHOLDS["high"]:
            rainfall_score = 3
        elif rainfall_24h >= self.RAINFALL_THRESHOLDS["moderate"]:
            rainfall_score = 2
        elif rainfall_24h >= self.RAINFALL_THRESHOLDS["low"]:
            rainfall_score = 1

        moisture_score = 0
        if soil_moisture >= self.SOIL_MOISTURE_THRESHOLDS["very_high"]:
            moisture_score = 4
        elif soil_moisture >= self.SOIL_MOISTURE_THRESHOLDS["high"]:
            moisture_score = 3
        elif soil_moisture >= self.SOIL_MOISTURE_THRESHOLDS["moderate"]:
            moisture_score = 2
        elif soil_moisture >= self.SOIL_MOISTURE_THRESHOLDS["low"]:
            moisture_score = 1

        combined_score = (base_score * 2) + rainfall_score + moisture_score

        if combined_score >= 8:
            risk_level = "Very High"
            time_window = "Immediate - Within 2 hours"
        elif combined_score >= 6:
            risk_level = "High"
            time_window = "2-6 hours"
        elif combined_score >= 4:
            risk_level = "Medium"
            time_window = "6-24 hours"
        elif combined_score >= 2:
            risk_level = "Low"
            time_window = "24-48 hours"
        else:
            risk_level = "Minimal"
            time_window = "48+ hours"

        return {
            "risk_level": risk_level,
            "risk_score": combined_score,
            "time_window": time_window,
            "components": {
                "detected_severity": severity,
                "severity_weight": base_score * 2,
                "rainfall_score": rainfall_score,
                "soil_moisture_score": moisture_score,
            },
            "rainfall_24h": rainfall_24h,
            "soil_moisture": soil_moisture,
            "recommendations": self._get_recommendations(risk_level, rainfall_24h),
        }

    def predict_future_risk(
        self, lat: float, lon: float, hours_ahead: int = 72
    ) -> List[Dict]:
        extended_forecast = weather_service.get_extended_forecast(
            lat, lon, hours=hours_ahead
        )

        risk_timeline = []
        cumulative_rainfall = 0

        for i, hour_data in enumerate(extended_forecast):
            precip = hour_data.get("precipitation", 0) or 0
            cumulative_rainfall += precip

            if i % 6 == 0:
                soil_moisture = hour_data.get("soil_moisture", 0)
                if soil_moisture:
                    soil_moisture = soil_moisture * 100

                risk_score = self._calculate_hourly_risk(
                    cumulative_rainfall, soil_moisture, precip
                )

                risk_timeline.append(
                    {
                        "time": hour_data.get("time"),
                        "hours_ahead": i,
                        "risk_level": risk_score["level"],
                        "risk_score": risk_score["score"],
                        "cumulative_rainfall": round(cumulative_rainfall, 2),
                        "precipitation": precip,
                        "soil_moisture": soil_moisture,
                    }
                )

        return risk_timeline

    def _calculate_hourly_risk(
        self, cumulative_rain: float, soil_moisture: float, current_precip: float
    ) -> Dict:
        score = 0

        if cumulative_rain >= 100:
            score += 4
        elif cumulative_rain >= 50:
            score += 3
        elif cumulative_rain >= 25:
            score += 2
        elif cumulative_rain >= 10:
            score += 1

        if soil_moisture >= 80:
            score += 3
        elif soil_moisture >= 60:
            score += 2
        elif soil_moisture >= 40:
            score += 1

        if current_precip >= 5:
            score += 2
        elif current_precip >= 2:
            score += 1

        if score >= 7:
            level = "Very High"
        elif score >= 5:
            level = "High"
        elif score >= 3:
            level = "Medium"
        elif score >= 1:
            level = "Low"
        else:
            level = "Minimal"

        return {"score": score, "level": level}

    def _get_recommendations(self, risk_level: str, rainfall: float) -> List[str]:
        recommendations = {
            "Very High": [
                "EVACUATE immediately - imminent landslide risk",
                "Close all roads in affected area NOW",
                "Deploy emergency response teams",
                "Alert all residents in evacuation zone",
                "Establish emergency shelters",
            ],
            "High": [
                "Prepare for potential evacuation",
                "Monitor conditions continuously",
                "Pre-position emergency supplies",
                "Alert evacuation teams on standby",
                "Consider proactive road closures",
            ],
            "Medium": [
                "Increase monitoring frequency",
                "Prepare evacuation plans",
                "Alert field teams for rapid response",
                "Monitor weather radar for intensification",
                "Keep evacuation routes clear",
            ],
            "Low": [
                "Continue normal monitoring",
                "Review emergency protocols",
                "Ensure drainage systems are clear",
                "Monitor weather updates",
                "Be prepared to act if conditions change",
            ],
            "Minimal": [
                "Standard monitoring protocols",
                "Routine maintenance of drainage",
                "Continue weather monitoring",
                "No immediate action required",
            ],
        }
        return recommendations.get(risk_level, recommendations["Low"])

    def get_zone_risk_assessment(
        self, lat: float, lon: float, detected_severity: str
    ) -> Dict:
        weather_data = weather_service.get_comprehensive_weather_data(lat, lon)
        instant_risk = self.calculate_instant_risk(detected_severity, weather_data)
        future_risk = self.predict_future_risk(lat, lon, hours_ahead=72)

        critical_hours = [
            r for r in future_risk if r["risk_level"] in ["Very High", "High"]
        ]

        return {
            "location": {"lat": lat, "lon": lon},
            "current_risk": instant_risk,
            "72h_forecast": future_risk[:12],
            "critical_windows": critical_hours[:3] if critical_hours else [],
            "weather_summary": {
                "current": weather_data.get("current", {}),
                "24h_forecast": weather_data.get("forecast_24h", {}),
                "7d_historical": weather_data.get("historical_7d", {}),
            },
            "generated_at": datetime.now().isoformat(),
        }

    def generate_evacuation_timeline(self, risk_assessment: Dict) -> List[Dict]:
        timeline = []
        current_time = datetime.now()

        risk_level = risk_assessment.get("current_risk", {}).get("risk_level", "Low")

        level_timestamps = {
            "Very High": 0,
            "High": 2,
            "Medium": 6,
            "Low": 12,
            "Minimal": 24,
        }

        hours_until_action = level_timestamps.get(risk_level, 24)
        action_time = current_time + timedelta(hours=hours_until_action)

        timeline.append(
            {
                "phase": "Immediate Monitoring",
                "time": current_time.strftime("%Y-%m-%d %H:%M"),
                "hours_from_now": 0,
                "action": "Activate continuous monitoring and deploy field observers",
            }
        )

        if risk_level in ["High", "Very High"]:
            timeline.append(
                {
                    "phase": "Pre-Evacuation Alert",
                    "time": (current_time + timedelta(hours=1)).strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                    "hours_from_now": 1,
                    "action": "Issue advisory to residents, prepare evacuation transport",
                }
            )

        timeline.append(
            {
                "phase": "Evacuation Ready",
                "time": action_time.strftime("%Y-%m-%d %H:%M"),
                "hours_from_now": hours_until_action,
                "action": f"Begin evacuation procedures - {risk_assessment.get('current_risk', {}).get('time_window', 'N/A')}",
            }
        )

        timeline.append(
            {
                "phase": "Post-Event Monitoring",
                "time": (action_time + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M"),
                "hours_from_now": hours_until_action + 24,
                "action": "Continue monitoring for secondary slides, assess damage",
            }
        )

        return timeline


risk_prediction_service = RiskPredictionService()
