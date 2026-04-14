import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import statistics


class AnalyticsService:
    def __init__(self):
        self.analytics_dir = Path(__file__).parent.parent / "analytics"
        self.analytics_dir.mkdir(exist_ok=True)
        self.predictions_file = self.analytics_dir / "predictions.json"
        self.metrics_file = self.analytics_dir / "metrics.json"
        self._init_files()

    def _init_files(self):
        if not self.predictions_file.exists():
            with open(self.predictions_file, "w") as f:
                json.dump({"predictions": []}, f)
        if not self.metrics_file.exists():
            with open(self.metrics_file, "w") as f:
                json.dump({"daily_stats": {}, "model_metrics": {}}, f)

    def _load_predictions(self) -> Dict:
        try:
            with open(self.predictions_file, "r") as f:
                return json.load(f)
        except:
            return {"predictions": []}

    def _save_predictions(self, data: Dict):
        with open(self.predictions_file, "w") as f:
            json.dump(data, f, indent=2)

    def _load_metrics(self) -> Dict:
        try:
            with open(self.metrics_file, "r") as f:
                return json.load(f)
        except:
            return {"daily_stats": {}, "model_metrics": {}}

    def _save_metrics(self, data: Dict):
        with open(self.metrics_file, "w") as f:
            json.dump(data, f, indent=2)

    def log_prediction(self, prediction: Dict):
        data = self._load_predictions()
        record = {**prediction, "logged_at": datetime.now().isoformat()}
        data["predictions"].append(record)

        if len(data["predictions"]) > 10000:
            data["predictions"] = data["predictions"][-5000:]

        self._save_predictions(data)
        self._update_daily_stats(prediction)
        return record

    def _update_daily_stats(self, prediction: Dict):
        today = datetime.now().strftime("%Y-%m-%d")
        metrics = self._load_metrics()

        if today not in metrics["daily_stats"]:
            metrics["daily_stats"][today] = {
                "total_predictions": 0,
                "landslides_detected": 0,
                "severity_breakdown": {
                    "Low": 0,
                    "Medium": 0,
                    "High": 0,
                    "Very High": 0,
                },
                "total_area": 0,
                "avg_area": 0,
                "unique_locations": set(),
                "response_times": [],
            }

        stats = metrics["daily_stats"][today]
        stats["total_predictions"] += 1

        severity = prediction.get("severity", "No Landslide")
        if severity != "No Landslide":
            stats["landslides_detected"] += 1
            stats["severity_breakdown"][severity] = (
                stats["severity_breakdown"].get(severity, 0) + 1
            )
            stats["total_area"] += prediction.get("area_sq_meters", 0)
            stats["avg_area"] = stats["total_area"] / stats["landslides_detected"]

        lat = prediction.get("latitude")
        lon = prediction.get("longitude")
        if lat and lon:
            stats["unique_locations"].add(f"{lat:.2f},{lon:.2f}")

        self._save_metrics(metrics)

    def get_daily_summary(self, days: int = 7) -> Dict:
        metrics = self._load_metrics()
        summaries = []

        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            stats = metrics["daily_stats"].get(date, {})

            if stats:
                summaries.append(
                    {
                        "date": date,
                        "total_predictions": stats.get("total_predictions", 0),
                        "landslides_detected": stats.get("landslides_detected", 0),
                        "severity_breakdown": stats.get("severity_breakdown", {}),
                        "total_area_sq_meters": round(stats.get("total_area", 0), 2),
                        "avg_area_sq_meters": round(stats.get("avg_area", 0), 2),
                        "unique_locations": len(stats.get("unique_locations", set())),
                    }
                )

        return {
            "period_days": days,
            "daily_summaries": summaries,
            "totals": self._calculate_totals(summaries),
        }

    def _calculate_totals(self, summaries: List[Dict]) -> Dict:
        if not summaries:
            return {}

        total_predictions = sum(s.get("total_predictions", 0) for s in summaries)
        total_landslides = sum(s.get("landslides_detected", 0) for s in summaries)
        total_area = sum(s.get("total_area_sq_meters", 0) for s in summaries)

        all_severities = {}
        for s in summaries:
            for sev, count in s.get("severity_breakdown", {}).items():
                all_severities[sev] = all_severities.get(sev, 0) + count

        return {
            "total_predictions": total_predictions,
            "total_landslides_detected": total_landslides,
            "total_area_sq_meters": round(total_area, 2),
            "detection_rate": round(total_landslides / total_predictions * 100, 2)
            if total_predictions > 0
            else 0,
            "severity_distribution": all_severities,
        }

    def get_weekly_trends(self) -> Dict:
        data = self._load_predictions()
        predictions = data.get("predictions", [])

        if not predictions:
            return {"trends": [], "insights": []}

        recent = [
            p
            for p in predictions
            if datetime.fromisoformat(p.get("logged_at", datetime.now().isoformat()))
            > datetime.now() - timedelta(days=7)
        ]

        daily_counts = {}
        for p in recent:
            date = datetime.fromisoformat(p.get("logged_at")).strftime("%Y-%m-%d")
            daily_counts[date] = daily_counts.get(date, 0) + 1

        return {
            "total_events_7d": len(recent),
            "daily_breakdown": daily_counts,
            "avg_daily_events": round(
                statistics.mean(daily_counts.values()) if daily_counts else 0, 2
            ),
            "peak_day": max(daily_counts, key=daily_counts.get)
            if daily_counts
            else None,
            "trend": "increasing" if len(recent) > 10 else "stable",
        }

    def get_model_performance(self) -> Dict:
        predictions = self._load_predictions().get("predictions", [])

        if not predictions:
            return {
                "total_predictions": 0,
                "model_uptime": "N/A",
                "avg_confidence": "N/A",
                "accuracy_estimate": "N/A",
            }

        recent_predictions = predictions[-100:]
        successful = [
            p for p in recent_predictions if p.get("severity") != "No Landslide"
        ]

        confidences = [
            p.get("confidence", 0)
            for p in recent_predictions
            if p.get("confidence") is not None and p.get("confidence") > 0
        ]

        processing_times = [
            p.get("processing_time_ms", 0)
            for p in recent_predictions
            if p.get("processing_time_ms") is not None
            and p.get("processing_time_ms") > 0
        ]

        total_recent = len(recent_predictions)
        avg_confidence = (
            round(statistics.mean(confidences), 3) if confidences else "N/A"
        )
        avg_processing = (
            round(statistics.mean(processing_times), 1) if processing_times else "N/A"
        )

        return {
            "total_predictions": len(predictions),
            "successful_detections": len(successful),
            "detection_rate": round(len(successful) / total_recent * 100, 2)
            if total_recent > 0
            else 0,
            "avg_confidence": avg_confidence,
            "avg_processing_time_ms": avg_processing,
            "model_version": "DeepLabV3Plus-ResNet50 v1.0",
            "last_updated": datetime.now().isoformat(),
        }

    def export_analytics(self, format: str = "json") -> Dict:
        predictions = self._load_predictions().get("predictions", [])
        metrics = self._load_metrics()
        daily_summary = self.get_daily_summary()
        trends = self.get_weekly_trends()

        return {
            "exported_at": datetime.now().isoformat(),
            "predictions": predictions,
            "metrics": metrics,
            "daily_summary": daily_summary,
            "trends": trends,
            "model_performance": self.get_model_performance(),
        }


analytics_service = AnalyticsService()
