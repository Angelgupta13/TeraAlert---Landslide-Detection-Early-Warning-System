import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List
from services.weather_service import weather_service
from services.risk_prediction_service import risk_prediction_service
from services.email_service import email_service
from services.db_service import db_service


class EarlyWarningSystem:
    CRITICAL_RAINFALL_THRESHOLD = 50.0
    HIGH_RAINFALL_THRESHOLD = 25.0

    def __init__(self):
        # Himalayan Range Coverage - Major Districts & Risk Zones
        self.monitored_zones = [
            # Himachal Pradesh
            {"name": "Hamirpur District", "lat": 31.52, "lon": 76.52, "state": "HP"},
            {"name": "Kangra Valley", "lat": 32.09, "lon": 76.32, "state": "HP"},
            {"name": "Mandi Region", "lat": 31.71, "lon": 76.93, "state": "HP"},
            {"name": "Shimla Hills", "lat": 31.10, "lon": 77.17, "state": "HP"},
            {"name": "Kullu Valley", "lat": 31.96, "lon": 77.11, "state": "HP"},
            {"name": "Chamba Region", "lat": 32.55, "lon": 76.13, "state": "HP"},
            {"name": "Kinnaur Valley", "lat": 31.58, "lon": 78.25, "state": "HP"},
            {"name": "Lahaul & Spiti", "lat": 32.13, "lon": 77.62, "state": "HP"},
            # Uttarakhand
            {"name": "Dehradun Valley", "lat": 30.32, "lon": 78.03, "state": "UK"},
            {"name": "Tehri Garhwal", "lat": 30.38, "lon": 78.48, "state": "UK"},
            {"name": "Chamoli (Joshimath)", "lat": 30.73, "lon": 79.60, "state": "UK"},
            {"name": "Rudraprayag", "lat": 30.27, "lon": 78.97, "state": "UK"},
            {"name": "Nainital (Kumaon)", "lat": 29.38, "lon": 79.46, "state": "UK"},
            {"name": "Almora Region", "lat": 29.60, "lon": 79.67, "state": "UK"},
            {"name": "Pithoragarh", "lat": 29.58, "lon": 80.22, "state": "UK"},
            {"name": "Badrinath Route", "lat": 30.74, "lon": 79.49, "state": "UK"},
            # Jammu & Kashmir
            {"name": "Kashmir Valley", "lat": 34.08, "lon": 74.80, "state": "JK"},
            {"name": "Gulmarg Region", "lat": 34.05, "lon": 74.38, "state": "JK"},
            {"name": "Pahalgam Route", "lat": 34.01, "lon": 75.32, "state": "JK"},
            {"name": "Sonmarg (Kashmir)", "lat": 34.30, "lon": 75.28, "state": "JK"},
            {"name": "Katra (Vaishno Devi)", "lat": 32.99, "lon": 74.95, "state": "JK"},
            {"name": "Patnitop Region", "lat": 33.08, "lon": 75.33, "state": "JK"},
            {"name": "Kishtwar District", "lat": 33.32, "lon": 75.77, "state": "JK"},
            # Ladakh
            {"name": "Leh Town", "lat": 34.15, "lon": 77.58, "state": "Ladakh"},
            {"name": "Kargil Region", "lat": 34.55, "lon": 76.10, "state": "Ladakh"},
            {"name": "Zanskar Valley", "lat": 33.62, "lon": 76.88, "state": "Ladakh"},
            # Border Regions
            {"name": "Pathankot (Border)", "lat": 32.27, "lon": 75.65, "state": "PB"},
        ]
        self.last_check = None
        self.alert_history = []

    async def run_hourly_check(self):
        print("\n" + "=" * 60)
        print("🌧️  EARLY WARNING SYSTEM - Weather Risk Assessment")
        print("=" * 60)

        warnings = []

        for zone in self.monitored_zones:
            print(
                f"\n📍 Checking: {zone['name']} ({zone['lat']:.2f}, {zone['lon']:.2f})"
            )

            weather_data = weather_service.get_comprehensive_weather_data(
                zone["lat"], zone["lon"]
            )

            rainfall_24h = weather_data.get("forecast_24h", {}).get("rainfall_24h", 0)
            soil_moisture = weather_data.get("forecast_24h", {}).get(
                "max_soil_moisture", 0
            )
            historical_rain = weather_data.get("historical_7d", {}).get(
                "total_rainfall_mm", 0
            )

            print(f"   24h Forecast: {rainfall_24h} mm")
            print(f"   Soil Moisture: {soil_moisture}%")
            print(f"   7d Historical: {historical_rain} mm")

            risk_level = self._calculate_risk_level(
                rainfall_24h, soil_moisture, historical_rain
            )
            print(f"   Risk Level: {risk_level['level']}")

            if risk_level["level"] in ["High", "Very High"]:
                warning = {
                    "zone": zone,
                    "timestamp": datetime.now().isoformat(),
                    "risk_level": risk_level["level"],
                    "rainfall_24h": rainfall_24h,
                    "soil_moisture": soil_moisture,
                    "7d_rainfall": historical_rain,
                    "recommendations": risk_level["recommendations"],
                }
                warnings.append(warning)

                self._create_early_warning_log(warning)

                if risk_level["level"] == "Very High":
                    print(f"   🚨 CRITICAL WARNING!")

        self.last_check = datetime.now()

        if warnings:
            print(f"\n⚠️  {len(warnings)} zone(s) flagged for elevated risk!")
            self.alert_history.extend(warnings)
            self._send_aggregated_alert(warnings)
        else:
            print(f"\n✅ All monitored zones within safe thresholds")

        print("=" * 60)
        return warnings

    def _calculate_risk_level(
        self, rainfall_24h: float, soil_moisture: float, historical_rain: float
    ) -> Dict:
        score = 0

        if rainfall_24h >= self.CRITICAL_RAINFALL_THRESHOLD:
            score += 4
        elif rainfall_24h >= self.HIGH_RAINFALL_THRESHOLD:
            score += 2
        elif rainfall_24h >= 10:
            score += 1

        if soil_moisture >= 80:
            score += 3
        elif soil_moisture >= 60:
            score += 2
        elif soil_moisture >= 40:
            score += 1

        if historical_rain >= 150:
            score += 3
        elif historical_rain >= 100:
            score += 2
        elif historical_rain >= 50:
            score += 1

        if score >= 8:
            level = "Very High"
        elif score >= 5:
            level = "High"
        elif score >= 3:
            level = "Medium"
        elif score >= 1:
            level = "Low"
        else:
            level = "Minimal"

        return {
            "level": level,
            "score": score,
            "recommendations": self._get_zone_recommendations(level),
        }

    def _get_zone_recommendations(self, risk_level: str) -> List[str]:
        recs = {
            "Very High": [
                "Deploy emergency response teams immediately",
                "Issue evacuation warnings for high-risk areas",
                "Close susceptible roads and hiking trails",
                "Establish emergency shelters",
                "Continuous monitoring every 30 minutes",
            ],
            "High": [
                "Pre-position emergency supplies",
                "Alert local response teams",
                "Monitor drainage systems",
                "Prepare for possible evacuation",
                "Check on vulnerable populations",
            ],
            "Medium": [
                "Increase monitoring frequency",
                "Review evacuation routes",
                "Alert field observers",
                "Monitor weather radar",
                "Ensure drainage is clear",
            ],
            "Low": [
                "Standard monitoring",
                "Review emergency protocols",
                "Continue weather watching",
                "No immediate action needed",
            ],
            "Minimal": ["Continue routine monitoring", "Normal operations"],
        }
        return recs.get(risk_level, recs["Low"])

    def _create_early_warning_log(self, warning: Dict):
        log_entry = {
            "type": "early_warning",
            "zone_name": warning["zone"]["name"],
            "lat": warning["zone"]["lat"],
            "lon": warning["zone"]["lon"],
            "risk_level": warning["risk_level"],
            "rainfall_24h": warning["rainfall_24h"],
            "soil_moisture": warning["soil_moisture"],
            "timestamp": warning["timestamp"],
            "severity": "High" if warning["risk_level"] == "Very High" else "Medium",
        }
        print(f"   📝 Early warning logged: {log_entry['type']}")

    def _send_aggregated_alert(self, warnings: List[Dict]):
        critical_warnings = [w for w in warnings if w["risk_level"] == "Very High"]

        if critical_warnings:
            alert_text = f"""
⚠️ EARLY WARNING: LANDSLIDE RISK ALERT ⚠️

{len(critical_warnings)} zone(s) at CRITICAL risk level!

"""
            for w in critical_warnings:
                alert_text += f"""
📍 {w["zone"]["name"]}
   Risk Level: {w["risk_level"]}
   24h Rainfall: {w["rainfall_24h"]} mm
   Soil Moisture: {w["soil_moisture"]}%
   
"""
            alert_text += """
RECOMMENDED ACTIONS:
1. Deploy emergency teams
2. Issue evacuation warnings
3. Close at-risk roads

---
Early Warning System - Auto-generated
"""
            print(f"   📧 Critical alert prepared for {len(critical_warnings)} zones")

    def get_watchlist(self) -> List[Dict]:
        return self.monitored_zones

    def add_zone(self, name: str, lat: float, lon: float):
        self.monitored_zones.append({"name": name, "lat": lat, "lon": lon})
        print(f"✅ Added zone to monitoring: {name}")

    def get_alert_history(self, hours: int = 24) -> List[Dict]:
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [
            a
            for a in self.alert_history
            if datetime.fromisoformat(a["timestamp"]) > cutoff
        ]
        return recent

    def generate_daily_report(self) -> Dict:
        all_alerts = self.get_alert_history(24)

        risk_counts = {"Very High": 0, "High": 0, "Medium": 0, "Low": 0, "Minimal": 0}
        for alert in all_alerts:
            risk_counts[alert["risk_level"]] = (
                risk_counts.get(alert["risk_level"], 0) + 1
            )

        zones_affected = len(set(a["zone"]["name"] for a in all_alerts))

        return {
            "report_date": datetime.now().strftime("%Y-%m-%d"),
            "total_checks": len(all_alerts),
            "zones_affected": zones_affected,
            "risk_distribution": risk_counts,
            "critical_events": risk_counts.get("Very High", 0),
            "high_events": risk_counts.get("High", 0),
            "monitored_zones": len(self.monitored_zones),
            "recommendations": self._get_daily_recommendations(risk_counts),
        }

    def _get_daily_recommendations(self, risk_counts: Dict) -> List[str]:
        if risk_counts.get("Very High", 0) > 0:
            return [
                "Immediate deployment of emergency resources recommended",
                "Consider statewide alert",
                "Review hospital and shelter capacity",
            ]
        elif risk_counts.get("High", 0) >= 2:
            return [
                "Pre-position emergency response teams",
                "Alert district authorities",
                "Monitor continuously",
            ]
        elif risk_counts.get("High", 0) > 0 or risk_counts.get("Medium", 0) >= 3:
            return [
                "Increase monitoring frequency",
                "Alert field teams",
                "Review contingency plans",
            ]
        else:
            return ["Continue standard monitoring", "Normal operations"]


early_warning_system = EarlyWarningSystem()


async def early_warning_worker():
    print("🌧️  Early Warning System Started - Monitoring weather conditions...")
    check_interval = 3600

    while True:
        try:
            await early_warning_system.run_hourly_check()
        except Exception as e:
            print(f"❌ Early Warning Error: {e}")

        await asyncio.sleep(check_interval)
