import asyncio
import os
import time
import threading
from datetime import datetime
from services.ml_service import model_service
from services.db_service import db_service
from services.email_service import email_service
from services.risk_prediction_service import risk_prediction_service

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEED_DIR = os.path.join(BASE_DIR, "simulated_satellite_feed")
PROCESSED_DIR = os.path.join(FEED_DIR, "processed")

os.makedirs(PROCESSED_DIR, exist_ok=True)


class BackgroundMonitor:
    """
    Background worker that continuously monitors satellite imagery
    and runs landslide detection using DeepLabV3+ model.
    """

    def __init__(self):
        self.running = False
        self.thread = None
        self.last_scan = None
        self.scan_interval = 300  # 5 minutes
        self.status = "stopped"
        self.satellite = None
        self.stac_available = False

    def start(self):
        """Start background monitoring."""
        if self.running:
            print("⚠️ Monitor already running")
            return

        self.running = True
        self.status = "running"
        self.thread = threading.Thread(target=self._run_monitor, daemon=True)
        self.thread.start()
        print("🚀 Background monitor started!")
        print(f"   - Scan interval: {self.scan_interval}s")
        print(
            f"   - STAC API: {'Connected' if self.stac_available else 'Unavailable (using fallback)'}"
        )
        print("   - DeepLabV3+ Model: Ready")
        print("   - Email Alerts: Enabled")

    def stop(self):
        """Stop background monitoring."""
        self.running = False
        self.status = "stopped"
        if self.thread:
            self.thread.join(timeout=5)
        print("⏹️ Background monitor stopped")

    def _run_monitor(self):
        """Main monitoring loop."""
        while self.running:
            try:
                self._scan_all_zones()
            except Exception as e:
                print("[ERROR] Monitor error: " + str(e))

            time.sleep(self.scan_interval)

    def _scan_all_zones(self):
        """Scan all monitoring zones for landslides."""
        zones = [
            {"name": "Hamirpur", "lat": 31.52, "lon": 76.52},
            {"name": "Kangra", "lat": 32.09, "lon": 76.32},
            {"name": "Mandi", "lat": 31.71, "lon": 76.93},
            {"name": "Shimla", "lat": 31.10, "lon": 77.17},
            {"name": "Kullu", "lat": 31.96, "lon": 77.11},
            {"name": "Chamba", "lat": 32.55, "lon": 76.12},
            {"name": "Dehradun", "lat": 30.32, "lon": 78.03},
            {"name": "Tehri", "lat": 30.38, "lon": 78.48},
            {"name": "Chamoli", "lat": 30.73, "lon": 79.60},
            {"name": "Rudraprayag", "lat": 30.28, "lon": 78.97},
            {"name": "Nainital", "lat": 29.38, "lon": 79.45},
            {"name": "Srinagar", "lat": 34.08, "lon": 74.80},
            {"name": "Gulmarg", "lat": 34.15, "lon": 74.38},
            {"name": "Pahalgam", "lat": 34.01, "lon": 75.31},
            {"name": "Leh", "lat": 34.15, "lon": 77.58},
            {"name": "Kargil", "lat": 34.55, "lon": 76.13},
        ]

        print("")
        print("=" * 50)
        print("[SCAN] Starting cycle: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("=" * 50)

        detections = 0

        for zone in zones:
            try:
                result = self._scan_zone(zone)
                if result:
                    detections += 1
            except Exception as e:
                print("   [ERROR] " + zone["name"] + ": " + str(e))

        self.last_scan = datetime.now()
        print("")
        print(
            "[DONE] Scan complete: "
            + str(len(zones))
            + " zones, "
            + str(detections)
            + " detections"
        )

    def _scan_zone(self, zone):
        """Scan a single zone for landslides."""
        name = zone["name"]
        lat = zone["lat"]
        lon = zone["lon"]

        print("")
        print("[SCANNING] " + name + " (" + str(lat) + ", " + str(lon) + ")...")

        # Fetch satellite imagery
        if self.satellite:
            image_data = self.satellite.fetch_latest_imagery(lat, lon)
        else:
            image_data = self._generate_demo_data(lat, lon)

        if not image_data or "image" not in image_data:
            print("   [WARNING] No imagery available")
            return None

        # Run model inference
        result = model_service.analyze_satellite_data(image_data)

        if result.get("severity") and result.get("severity") != "No Landslide":
            print("   [ALERT] DETECTED: " + result["severity"])
            area = float(result.get("area_sq_meters", 0) or 0)
            print("      Area: " + str(round(area, 2)) + " m2")

            # Store landslide
            landslide_data = {
                "latitude": result.get("latitude") or lat,
                "longitude": result.get("longitude") or lon,
                "severity": result["severity"],
                "area_sq_meters": result.get("area_sq_meters", 0),
                "source": "satellite_monitoring",
                "source_image": image_data.get("item_id", "unknown"),
                "zone_name": name,
                "confidence": result.get("confidence", 0),
                "timestamp": int(time.time()),
            }

            landslide_id = db_service.add_landslide(landslide_data)

            # Get risk assessment
            risk = risk_prediction_service.get_zone_risk_assessment(
                lat, lon, result["severity"]
            )
            risk_level = risk.get("current_risk", {}).get("risk_level", "Unknown")

            print("      Risk Level: " + risk_level)

            # Send alerts for high severity ONLY if not in cooldown
            if result["severity"] in ["High", "Very High"]:
                if db_service.can_send_alert(name):
                    print("      [SENDING] Alerts...")
                    email_result = email_service.send_alert(
                        {**landslide_data, "id": landslide_id}, risk.get("current_risk")
                    )

                    if email_result.get("sent"):
                        print(
                            "      [OK] Alerts sent to "
                            + str(len(email_result["sent"]))
                            + " recipients"
                        )
                        db_service.update_email_status(
                            landslide_id, True, email_result["sent"]
                        )
                else:
                    recent = db_service.get_recent_alert_for_zone(name)
                    recent_time = recent.get("email_timestamp", 0)
                    hours_ago = int((time.time() - recent_time) / 3600)
                    print(
                        f"      [SKIPPED] Alert suppressed - already sent {hours_ago}h ago"
                    )

            return {"zone": name, "result": result, "landslide_id": landslide_id}
        else:
            print("   [OK] Clear - No landslide detected")
            return None

    def _generate_demo_data(self, lat, lon):
        """Generate demo data when STAC unavailable."""
        import numpy as np
        from rasterio.transform import from_bounds

        np.random.seed(int(lat * 100 + lon * 100) % 1000)
        image = np.random.randint(80, 180, (256, 256, 3), dtype=np.uint8)
        green = np.random.random((256, 256)) > 0.7
        image[green] = [80, 120, 60]

        buffer = 0.05
        left = lon - buffer
        right = lon + buffer
        top = lat + buffer
        bottom = lat - buffer

        class DemoBounds:
            def __init__(self, l, r, t, b):
                self.left = l
                self.right = r
                self.top = t
                self.bottom = b

        bounds = DemoBounds(left, right, top, bottom)
        transform = from_bounds(left, bottom, right, top, 256, 256)

        return {
            "image": image,
            "bounds": bounds,
            "transform": transform,
            "crs": "EPSG:4326",
            "source": "demo",
            "item_id": f"demo_{lat:.2f}_{lon:.2f}",
            "lat": lat,
            "lon": lon,
        }

    def get_status(self):
        """Get current monitor status."""
        return {
            "running": self.running,
            "status": self.status,
            "last_scan": self.last_scan.isoformat() if self.last_scan else None,
            "scan_interval": self.scan_interval,
            "stac_available": self.stac_available,
        }


# Global instance
background_monitor = BackgroundMonitor()


async def satellite_monitoring_worker():
    """Legacy worker function - now uses BackgroundMonitor."""
    background_monitor.start()

    while True:
        await asyncio.sleep(60)
