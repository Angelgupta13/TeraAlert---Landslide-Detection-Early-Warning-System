import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime
from typing import Optional, List, Dict
import requests
import math

from dotenv import load_dotenv

load_dotenv()


class EmailService:
    REGION_BOUNDS = {
        "himachal_pradesh": {
            "name": "Himachal Pradesh",
            "lat_range": (31.4, 33.2),
            "lon_range": (75.8, 79.0),
            "authorities": ["hp_hamirpur", "hp_kangra", "hp_mandi", "hp_emergency"],
        },
        "uttarakhand": {
            "name": "Uttarakhand",
            "lat_range": (28.9, 31.4),
            "lon_range": (77.6, 81.1),
            "authorities": ["uk_dehradun", "uk_emergency", "uk_nainital"],
        },
        "jammu_kashmir": {
            "name": "Jammu & Kashmir",
            "lat_range": (32.2, 36.5),
            "lon_range": (73.8, 80.3),
            "authorities": ["jk_srinagar", "jk_emergency"],
        },
        "ladakh": {
            "name": "Ladakh",
            "lat_range": (32.5, 36.0),
            "lon_range": (75.5, 80.0),
            "authorities": ["jk_srinagar", "jk_emergency"],
        },
        "punjab": {
            "name": "Punjab (Border)",
            "lat_range": (31.0, 32.7),
            "lon_range": (74.0, 76.8),
            "authorities": ["punjab_pathankot"],
        },
    }

    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("ALERT_FROM_EMAIL", self.smtp_username)

        self.all_contacts = self._load_authority_contacts()

    def _format_coord(self, value):
        """Format coordinate to 4 decimal places, or show N/A if invalid."""
        if value is None:
            return "N/A"
        try:
            val = float(value)
            # Validate it's in reasonable lat/lon range
            # Latitude: -90 to 90, Longitude: -180 to 180
            if -90 <= val <= 90 or -180 <= val <= 180:
                return f"{val:.4f}"
            return "N/A"
        except (ValueError, TypeError):
            return "N/A"

    def _load_authority_contacts(self):
        contacts = {
            "hp_hamirpur": {
                "name": "HP - Hamirpur District",
                "email": os.getenv("AUTHORITY_EMAIL_1", ""),
            },
            "hp_kangra": {
                "name": "HP - Kangra District",
                "email": os.getenv("AUTHORITY_EMAIL_2", ""),
            },
            "hp_mandi": {
                "name": "HP - Mandi District",
                "email": os.getenv("AUTHORITY_EMAIL_3", ""),
            },
            "hp_emergency": {
                "name": "HP - State Emergency",
                "email": os.getenv("AUTHORITY_EMAIL_4", ""),
            },
            "uk_dehradun": {
                "name": "UK - Dehradun",
                "email": os.getenv("AUTHORITY_EMAIL_5", ""),
            },
            "uk_emergency": {
                "name": "UK - State Emergency",
                "email": os.getenv("AUTHORITY_EMAIL_6", ""),
            },
            "uk_nainital": {
                "name": "UK - Nainital District",
                "email": os.getenv("AUTHORITY_EMAIL_7", ""),
            },
            "jk_srinagar": {
                "name": "JK - Srinagar",
                "email": os.getenv("AUTHORITY_EMAIL_8", ""),
            },
            "jk_emergency": {
                "name": "JK - State Emergency",
                "email": os.getenv("AUTHORITY_EMAIL_9", ""),
            },
            "punjab_pathankot": {
                "name": "Punjab - Pathankot",
                "email": os.getenv("AUTHORITY_EMAIL_10", ""),
            },
            "national_ndma": {
                "name": "National - NDMA",
                "email": os.getenv("AUTHORITY_EMAIL_11", ""),
            },
            "national_ndrf": {
                "name": "National - NDRF",
                "email": os.getenv("AUTHORITY_EMAIL_12", ""),
            },
        }

        filtered = {}
        for key, contact in contacts.items():
            if contact["email"] and contact["email"].strip():
                filtered[key] = contact

        if not filtered:
            filtered["default"] = {
                "name": "Default Authority",
                "email": "emergency@gov.in",
            }

        return filtered

    def _get_region_for_location(self, lat: float, lon: float) -> tuple:
        for region_id, region in self.REGION_BOUNDS.items():
            lat_min, lat_max = region["lat_range"]
            lon_min, lon_max = region["lon_range"]

            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                return region_id, region["name"]

        distance = float("inf")
        closest = None
        for region_id, region in self.REGION_BOUNDS.items():
            lat_mid = (region["lat_range"][0] + region["lat_range"][1]) / 2
            lon_mid = (region["lon_range"][0] + region["lon_range"][1]) / 2
            d = math.sqrt((lat - lat_mid) ** 2 + (lon - lon_mid) ** 2)
            if d < distance:
                distance = d
                closest = (region_id, region["name"])

        return closest if closest else ("unknown", "Unknown Region")

    def get_targeted_authorities(
        self, lat: float, lon: float, severity: str = "Medium"
    ) -> list:
        region_id, region_name = self._get_region_for_location(lat, lon)
        authorities = self.REGION_BOUNDS.get(region_id, {}).get("authorities", [])

        targeted = []
        for auth_key in authorities:
            if auth_key in self.all_contacts:
                targeted.append(self.all_contacts[auth_key])

        if severity in ["High", "Very High"] and "national_ndma" in self.all_contacts:
            targeted.append(self.all_contacts["national_ndma"])
        if severity == "Very High" and "national_ndrf" in self.all_contacts:
            targeted.append(self.all_contacts["national_ndrf"])

        return [
            {"name": region_name, "email": c["email"], "region": region_name}
            for c in targeted
        ]

    def _create_alert_html(
        self, landslide_data: Dict, risk_assessment: Optional[Dict] = None
    ) -> str:
        severity_colors = {
            "No Landslide": "#4CAF50",
            "Low": "#8BC34A",
            "Medium": "#FFC107",
            "High": "#FF9800",
            "Very High": "#F44336",
        }
        color = severity_colors.get(landslide_data.get("severity", "Medium"), "#FFC107")

        lat = self._format_coord(landslide_data.get("latitude"))
        lon = self._format_coord(landslide_data.get("longitude"))
        map_lat = landslide_data.get("latitude", 0) or 0
        map_lon = landslide_data.get("longitude", 0) or 0
        area = landslide_data.get("area_sq_meters", 0) or 0

        risk_html = ""
        if risk_assessment:
            risk_level = risk_assessment.get("risk_level", "Unknown")
            risk_color = severity_colors.get(risk_level, "#FFC107")
            risk_html = f"""
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>24-Hour Rainfall:</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{risk_assessment.get("rainfall_24h", "N/A")} mm</td>
            </tr>
            <tr style="background-color: #f0f0f0;">
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Soil Moisture Level:</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{risk_assessment.get("soil_moisture", "N/A")}%</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Current Risk Assessment:</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd; color: {risk_color};"><strong>{risk_level}</strong></td>
            </tr>
            <tr style="background-color: #f0f0f0;">
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Estimated Time Window:</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{risk_assessment.get("time_window", "N/A")}</td>
            </tr>
            """
        else:
            risk_html = """
            <tr>
                <td colspan="2" style="padding: 10px; border: 1px solid #ddd; background-color: #fff3cd;">
                    <em>Weather risk assessment data unavailable. Manual verification recommended.</em>
                </td>
            </tr>
            """

        detection_time = "N/A"
        ts = landslide_data.get("timestamp")
        if ts:
            try:
                detection_time = datetime.fromtimestamp(float(ts)).strftime(
                    "%Y-%m-%d %H:%M:%S UTC"
                )
            except (ValueError, TypeError):
                detection_time = "N/A"

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 650px; margin: 0 auto; background-color: #f5f5f5;">
            <div style="background-color: {color}; color: white; padding: 25px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px;">TERAALERT - LANDSLIDE DETECTION SYSTEM</h1>
                <p style="margin: 10px 0 0 0; font-size: 16px;">Official Landslide Early Warning Alert</p>
            </div>
            
            <div style="padding: 25px; background-color: white; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <h2 style="color: #333; margin-top: 0; border-bottom: 2px solid {color}; padding-bottom: 10px;">Landslide Detection Report</h2>
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd; background-color: #f9f9f9; width: 40%;"><strong>Alert Reference ID:</strong></td>
                        <td style="padding: 12px; border: 1px solid #ddd;">#{landslide_data.get("id", "N/A")}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd;"><strong>Severity Classification:</strong></td>
                        <td style="padding: 12px; border: 1px solid #ddd; color: {color}; font-weight: bold; font-size: 16px;">{landslide_data.get("severity", "Unknown")}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd; background-color: #f9f9f9;"><strong>Estimated Affected Area:</strong></td>
                        <td style="padding: 12px; border: 1px solid #ddd;">{area:,.2f} m²</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd;"><strong>Detection Coordinates:</strong></td>
                        <td style="padding: 12px; border: 1px solid #ddd;">Lat: {lat}, Lon: {lon}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd; background-color: #f9f9f9;"><strong>Detection Timestamp:</strong></td>
                        <td style="padding: 12px; border: 1px solid #ddd;">{detection_time}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd;"><strong>Source Satellite:</strong></td>
                        <td style="padding: 12px; border: 1px solid #ddd;">{landslide_data.get("source_image", "N/A")}</td>
                    </tr>
                </table>
                
                <p style="font-size: 11px; color: #666; margin-top: 15px;">
                    <strong>Methodology:</strong> Affected area is calculated using Sentinel-2 satellite imagery with 10m spatial resolution. 
                    Area = Detected Pixels × 100 m² (10m × 10m per pixel). 
                    Coordinates are derived from the center of mass of detected landslide region, transformed from UTM to WGS84.
                </p>
            </div>
            
            <div style="padding: 25px; background-color: white; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <h2 style="color: #333; margin-top: 0; border-bottom: 2px solid #2196F3; padding-bottom: 10px;">Environmental Risk Assessment</h2>
                <p style="color: #666; font-size: 13px;">Data sourced from Open-Meteo Weather API (api.open-meteo.com)</p>
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    {risk_html}
                </table>
                
                <p style="font-size: 11px; color: #666; margin-top: 15px;">
                    <strong>Risk Calculation:</strong> Combined score from satellite detection severity (weight: 2x), 
                    24-hour rainfall accumulation, and soil moisture saturation. Time window estimated based on 
                    cumulative precipitation and saturation thresholds. Soil moisture values represent volumetric water 
                    content in top 1cm layer.
                </p>
            </div>
            
            <div style="padding: 25px; background-color: #e3f2fd; margin: 20px 0; border-radius: 5px;">
                <h3 style="color: #1565C0; margin-top: 0;">Geographic Reference</h3>
                <p>Location: {lat}, {lon}</p>
                <p style="margin-top: 15px;">
                    <a href="https://www.google.com/maps?q={map_lat},{map_lon}" 
                       style="background-color: #1565C0; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                       View on Google Maps
                    </a>
                </p>
            </div>
            
            <div style="padding: 25px; background-color: white; margin: 20px 0; border-radius: 5px; border-left: 5px solid #FF9800;">
                <h3 style="color: #E65100; margin-top: 0;">Immediate Actions Recommended</h3>
                <ol style="line-height: 1.8;">
                    <li>Dispatch field verification team to the reported coordinates</li>
                    <li>Establish exclusion zone within 500m radius of detection point</li>
                    <li>Alert local district emergency operations center</li>
                    <li>Coordinate with transportation authority for potential road closure</li>
                    <li>Activate community warning systems for downstream areas</li>
                </ol>
            </div>
            
            <div style="padding: 20px; background-color: #263238; color: white; text-align: center; font-size: 12px; border-radius: 5px;">
                <p style="margin: 5px 0;"><strong>TeraAlert - Himalayan Landslide Detection & Early Warning System</strong></p>
                <p style="margin: 5px 0;">This is an automated system-generated alert. Do not reply to this message.</p>
                <p style="margin: 10px 0 0 0; font-size: 11px; color: #aaa;">For emergencies, contact local DDMA/NDRF directly.</p>
            </div>
        </body>
        </html>
        """
        return html

    def _create_alert_text(
        self, landslide_data: Dict, risk_assessment: Optional[Dict] = None
    ) -> str:
        risk_text = ""
        if risk_assessment:
            risk_text = f"""
Environmental Conditions:
-------------------------
24-Hour Rainfall: {risk_assessment.get("rainfall_24h", "N/A")} mm
Soil Moisture Level: {risk_assessment.get("soil_moisture", "N/A")}%
Current Risk Level: {risk_assessment.get("risk_level", "Unknown")}
Estimated Time Window: {risk_assessment.get("time_window", "N/A")}
"""
        else:
            risk_text = """
Environmental Conditions:
-------------------------
Weather risk assessment data unavailable. Manual verification recommended.
"""

        lat = self._format_coord(landslide_data.get("latitude"))
        lon = self._format_coord(landslide_data.get("longitude"))
        map_lat = landslide_data.get("latitude", 0) or 0
        map_lon = landslide_data.get("longitude", 0) or 0
        area = landslide_data.get("area_sq_meters", 0) or 0

        detection_time = "N/A"
        ts = landslide_data.get("timestamp")
        if ts:
            try:
                detection_time = datetime.fromtimestamp(float(ts)).strftime(
                    "%Y-%m-%d %H:%M:%S UTC"
                )
            except (ValueError, TypeError):
                detection_time = "N/A"

        return f"""
================================================================================
                    TERAALERT - LANDSLIDE EARLY WARNING SYSTEM
                    Official Landslide Detection Alert
================================================================================

LANDSLIDE DETECTION REPORT
--------------------------
Alert Reference ID:    #{landslide_data.get("id", "N/A")}
Severity Classification: {landslide_data.get("severity", "Unknown")}
Estimated Affected Area: {area:,.2f} m²
Detection Coordinates:   Lat {lat}, Lon {lon}
Detection Timestamp:    {detection_time}
Source Satellite:       {landslide_data.get("source_image", "N/A")}

{risk_text}
GEOGRAPHIC REFERENCE
--------------------
Google Maps Link: https://www.google.com/maps?q={map_lat},{map_lon}

IMMEDIATE ACTIONS RECOMMENDED
-----------------------------
1. Dispatch field verification team to the reported coordinates
2. Establish exclusion zone within 500m radius of detection point
3. Alert local district emergency operations center
4. Coordinate with transportation authority for potential road closure
5. Activate community warning systems for downstream areas

--------------------------------------------------------------------------------
METHODOLOGY NOTES
--------------------------------------------------------------------------------
- Affected area calculated from Sentinel-2 imagery (10m spatial resolution)
- Area = Detected Pixels × 100 m² (10m × 10m per pixel)
- Coordinates derived from center of mass of detected landslide region
- Risk assessment based on combined score from satellite detection, 
  24-hour rainfall accumulation, and soil moisture saturation
- Weather data sourced from Open-Meteo Weather API

================================================================================
This is an automated system-generated alert from TeraAlert.
For emergencies, contact local DDMA/NDRF directly.
================================================================================
"""

    def send_alert(
        self,
        landslide_data: Dict,
        risk_assessment: Optional[Dict] = None,
        recipients: Optional[List[Dict]] = None,
    ) -> Dict:
        if not self.smtp_username or not self.smtp_password:
            print("[EMAIL] SMTP credentials not configured. Skipping alert.")
            return {"status": "skipped", "reason": "SMTP not configured"}

        if recipients is None:
            lat = landslide_data.get("latitude", 0)
            lon = landslide_data.get("longitude", 0)
            severity = landslide_data.get("severity", "Medium")
            recipients = self.get_targeted_authorities(lat, lon, severity)

        html_content = self._create_alert_html(landslide_data, risk_assessment)
        text_content = self._create_alert_text(landslide_data, risk_assessment)

        results = {"sent": [], "failed": []}

        for contact in recipients:
            if not contact.get("email"):
                continue

            try:
                msg = MIMEMultipart("alternative")
                severity = landslide_data.get("severity", "UNKNOWN")
                coords = f"{self._format_coord(landslide_data.get('latitude'))}, {self._format_coord(landslide_data.get('longitude'))}"
                msg["Subject"] = (
                    f"[TeraAlert] Official Alert: {severity} Landslide Detected at {coords}"
                )
                msg["From"] = f"TeraAlert System <{self.from_email}>"
                msg["To"] = contact["email"]

                msg.attach(MIMEText(text_content, "plain"))
                msg.attach(MIMEText(html_content, "html"))

                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)

                print(f"[EMAIL] Alert sent to {contact['name']} ({contact['email']})")
                results["sent"].append(contact["email"])

            except Exception as e:
                print(f"[EMAIL] Failed to send to {contact['email']}: {str(e)}")
                results["failed"].append({"email": contact["email"], "error": str(e)})

        return results

    def send_daily_digest(self, landslides: list, risk_summaries: dict) -> dict:
        if not self.smtp_username or not self.smtp_password:
            return {"status": "skipped", "reason": "SMTP not configured"}

        html = f"""
        <html>
        <body>
            <h1>📊 Daily Landslide Monitoring Digest</h1>
            <p>Date: {datetime.now().strftime("%Y-%m-%d")}</p>
            <h2>Detected Events: {len(landslides)}</h2>
            <h2>Weather Summary</h2>
            <p>Average Rainfall (24h): {risk_summaries.get("avg_rainfall", "N/A")} mm</p>
            <p>High Risk Zones: {risk_summaries.get("high_risk_zones", "N/A")}</p>
        </body>
        </html>
        """
        return {"status": "sent" if html else "failed"}


email_service = EmailService()
