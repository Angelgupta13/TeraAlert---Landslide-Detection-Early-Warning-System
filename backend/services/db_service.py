import json
import os
import time
import copy

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "active_landslides.json"
)

EMAIL_COOLDOWN_HOURS = 24


class DatabaseService:
    def __init__(self):
        if not os.path.exists(DB_PATH):
            with open(DB_PATH, "w") as f:
                json.dump([], f)

    def get_all(self):
        try:
            with open(DB_PATH, "r") as f:
                return json.load(f)
        except:
            return []

    def get_by_id(self, landslide_id: int):
        landslides = self.get_all()
        for slide in landslides:
            if slide.get("id") == landslide_id:
                return slide
        return None

    def add_landslide(self, data: dict):
        landslides = self.get_all()
        data["timestamp"] = time.time()
        data["id"] = len(landslides) + 1
        data["email_sent"] = False
        data["email_recipients"] = []

        landslides.append(data)
        with open(DB_PATH, "w") as f:
            json.dump(landslides, f, indent=4)

        return data["id"]

    def get_recent_alert_for_zone(
        self, zone_name: str, hours: int = EMAIL_COOLDOWN_HOURS
    ) -> dict:
        """Check if an alert was sent for this zone within the cooldown period."""
        landslides = self.get_all()
        cutoff_time = time.time() - (hours * 3600)

        for slide in landslides:
            if (
                slide.get("zone_name", "").lower() == zone_name.lower()
                and slide.get("email_sent", False)
                and slide.get("email_timestamp", 0) > cutoff_time
            ):
                return slide
        return None

    def can_send_alert(self, zone_name: str) -> bool:
        """Check if an alert can be sent for this zone (not in cooldown)."""
        recent = self.get_recent_alert_for_zone(zone_name)
        return recent is None

    def update_email_status(
        self, landslide_id: int, sent: bool, recipients: list = None
    ):
        landslides = self.get_all()
        for slide in landslides:
            if slide.get("id") == landslide_id:
                slide["email_sent"] = sent
                slide["email_recipients"] = recipients or []
                slide["email_timestamp"] = time.time()
                break

        with open(DB_PATH, "w") as f:
            json.dump(landslides, f, indent=4)

    def update_risk_assessment(self, landslide_id: int, risk_data: dict):
        landslides = self.get_all()
        for slide in landslides:
            if slide.get("id") == landslide_id:
                slide["risk_assessment"] = risk_data
                break

        with open(DB_PATH, "w") as f:
            json.dump(landslides, f, indent=4)

    def clear(self):
        with open(DB_PATH, "w") as f:
            json.dump([], f)

    def get_active_count(self):
        return len([s for s in self.get_all() if s.get("severity") != "No Landslide"])


db_service = DatabaseService()
