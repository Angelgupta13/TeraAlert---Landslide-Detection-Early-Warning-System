import csv
import io
import json
from datetime import datetime
from typing import Dict, List, Optional
from services.analytics_service import analytics_service
from services.db_service import db_service


class ExportService:
    def export_to_csv(self, data_type: str = "landslides", days: int = 30) -> str:
        if data_type == "landslides":
            return self._export_landslides_csv(days)
        elif data_type == "weather":
            return self._export_weather_csv(days)
        elif data_type == "analytics":
            return self._export_analytics_csv()
        else:
            raise ValueError(f"Unknown data type: {data_type}")

    def _export_landslides_csv(self, days: int) -> str:
        landslides = db_service.get_all()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "ID",
                "Severity",
                "Area (sq m)",
                "Latitude",
                "Longitude",
                "Timestamp",
                "Source Image",
                "Email Sent",
                "Risk Level",
            ]
        )

        for slide in landslides:
            writer.writerow(
                [
                    slide.get("id", ""),
                    slide.get("severity", ""),
                    round(slide.get("area_sq_meters", 0), 2),
                    slide.get("latitude", ""),
                    slide.get("longitude", ""),
                    datetime.fromtimestamp(slide.get("timestamp", 0)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if slide.get("timestamp")
                    else "",
                    slide.get("source_image", ""),
                    "Yes" if slide.get("email_sent") else "No",
                    slide.get("risk_assessment", {}).get("risk_level", "N/A")
                    if slide.get("risk_assessment")
                    else "N/A",
                ]
            )

        return output.getvalue()

    def _export_weather_csv(self, days: int) -> str:
        from services.weather_service import weather_service
        from services.risk_prediction_service import risk_prediction_service

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "Date",
                "Zone",
                "Latitude",
                "Longitude",
                "Rainfall 24h (mm)",
                "Soil Moisture (%)",
                "Risk Level",
                "Time Window",
            ]
        )

        zones = [
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

        for zone in zones:
            try:
                risk_data = risk_prediction_service.get_zone_risk_assessment(
                    zone["lat"], zone["lon"], detected_severity="Low"
                )
                current_risk = risk_data.get("current_risk", {})
                weather_summary = risk_data.get("weather_summary", {})
                forecast_24h = weather_summary.get("forecast_24h", {})

                rainfall = forecast_24h.get("rainfall_24h", "N/A")
                soil_moisture = current_risk.get("soil_moisture", "N/A")
                risk_level = current_risk.get("risk_level", "Unknown")
                time_window = current_risk.get("time_window", "N/A")
            except Exception:
                rainfall = "N/A"
                soil_moisture = "N/A"
                risk_level = "Unknown"
                time_window = "N/A"

            writer.writerow(
                [
                    datetime.now().strftime("%Y-%m-%d"),
                    zone["name"],
                    zone["lat"],
                    zone["lon"],
                    rainfall,
                    soil_moisture,
                    risk_level,
                    time_window,
                ]
            )

        return output.getvalue()

    def _export_analytics_csv(self) -> str:
        analytics = analytics_service.get_daily_summary()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "Date",
                "Total Predictions",
                "Landslides Detected",
                "Detection Rate (%)",
                "Total Area (sq m)",
                "Unique Locations",
            ]
        )

        for summary in analytics.get("daily_summaries", []):
            writer.writerow(
                [
                    summary.get("date", ""),
                    summary.get("total_predictions", 0),
                    summary.get("landslides_detected", 0),
                    round(
                        summary.get("landslides_detected", 0)
                        / max(summary.get("total_predictions", 1), 1)
                        * 100,
                        2,
                    ),
                    round(summary.get("total_area_sq_meters", 0), 2),
                    summary.get("unique_locations", 0),
                ]
            )

        return output.getvalue()

    def generate_pdf_content(self) -> Dict:
        landslides = db_service.get_all()
        analytics = analytics_service.get_daily_summary(7)
        trends = analytics_service.get_weekly_trends()

        high_severity = [
            l for l in landslides if l.get("severity") in ["High", "Very High"]
        ]

        return {
            "title": "Landslide Monitoring Report",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_events": len(landslides),
                "high_risk_events": len(high_severity),
                "alerts_sent": sum(1 for l in landslides if l.get("email_sent")),
                "total_area_affected": round(
                    sum(l.get("area_sq_meters", 0) for l in landslides), 2
                ),
            },
            "analytics": analytics,
            "trends": trends,
            "recent_events": landslides[-10:] if len(landslides) > 10 else landslides,
            "recommendations": self._generate_recommendations(high_severity, trends),
        }

    def _generate_recommendations(self, high_risk: List, trends: Dict) -> List[str]:
        recommendations = []

        if len(high_risk) > 5:
            recommendations.append(
                "URGENT: Multiple high-risk events detected. Immediate action required."
            )

        if trends.get("trend") == "increasing":
            recommendations.append(
                "Warning: Detection rate is increasing. Consider enhanced monitoring."
            )

        if not recommendations:
            recommendations.append("Continue standard monitoring protocols.")
            recommendations.append(
                "Maintain regular communication with local authorities."
            )

        return recommendations


export_service = ExportService()
