import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List


class WeatherService:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"

    def __init__(self):
        self.cache = {}
        self.cache_duration = 300

    def get_current_weather(self, lat: float, lon: float) -> Dict:
        cache_key = f"current_{lat:.4f}_{lon:.4f}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        params = {
            "latitude": lat,
            "longitude": lon,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "precipitation",
                "rain",
                "soil_moisture_0_to_1cm",
                "wind_speed_10m",
            ],
            "timezone": "auto",
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            result = {
                "temperature": data.get("current", {}).get("temperature_2m"),
                "humidity": data.get("current", {}).get("relative_humidity_2m"),
                "precipitation": data.get("current", {}).get("precipitation"),
                "rain": data.get("current", {}).get("rain"),
                "soil_moisture": data.get("current", {}).get("soil_moisture_0_to_1cm"),
                "wind_speed": data.get("current", {}).get("wind_speed_10m"),
                "timestamp": datetime.now().isoformat(),
            }
            self.cache[cache_key] = result
            return result
        except Exception as e:
            print(f"❌ [WEATHER] Failed to fetch current weather: {e}")
            return {}

    def get_forecast_24h(self, lat: float, lon: float) -> Dict:
        cache_key = f"forecast_24h_{lat:.4f}_{lon:.4f}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ["precipitation", "rain", "soil_moisture_0_to_1cm"],
            "forecast_days": 2,
            "timezone": "auto",
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            hourly = data.get("hourly", {})
            precipitation = hourly.get("precipitation", [])
            soil_moisture = hourly.get("soil_moisture_0_to_1cm", [])

            rainfall_24h = sum(precipitation[:24])
            max_soil_moisture = max(soil_moisture[:24]) if soil_moisture else 0

            result = {
                "rainfall_24h": round(rainfall_24h, 2),
                "max_soil_moisture": round(max_soil_moisture * 100, 1)
                if max_soil_moisture
                else 0,
                "hourly_forecast": precipitation[:24],
                "timestamp": datetime.now().isoformat(),
            }
            self.cache[cache_key] = result
            return result
        except Exception as e:
            print(f"❌ [WEATHER] Failed to fetch 24h forecast: {e}")
            return {}

    def get_historical_rainfall(self, lat: float, lon: float, days: int = 7) -> Dict:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "daily": ["precipitation_sum", "rain_sum"],
            "timezone": "auto",
        }

        try:
            response = requests.get(self.HISTORICAL_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            daily = data.get("daily", {})
            precip = daily.get("precipitation_sum", [])

            total_rainfall = sum(p for p in precip if p is not None)
            avg_rainfall = total_rainfall / len(precip) if precip else 0

            return {
                "total_rainfall_mm": round(total_rainfall, 2),
                "avg_daily_rainfall_mm": round(avg_rainfall, 2),
                "rainy_days": sum(1 for p in precip if p and p > 0),
                "period_days": days,
                "daily_breakdown": precip,
            }
        except Exception as e:
            print(f"❌ [WEATHER] Failed to fetch historical rainfall: {e}")
            return {}

    def get_extended_forecast(
        self, lat: float, lon: float, hours: int = 72
    ) -> List[Dict]:
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": [
                "temperature_2m",
                "precipitation",
                "rain",
                "soil_moisture_0_to_1cm",
                "wind_speed_10m",
            ],
            "forecast_days": 4,
            "timezone": "auto",
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            hourly = data.get("hourly", {})
            times = hourly.get("time", [])[:hours]

            forecast = []
            for i, t in enumerate(times):
                forecast.append(
                    {
                        "time": t,
                        "temperature": hourly.get(
                            "temperature_2m", [None] * len(times)
                        )[i],
                        "precipitation": hourly.get(
                            "precipitation", [None] * len(times)
                        )[i],
                        "rain": hourly.get("rain", [None] * len(times))[i],
                        "soil_moisture": hourly.get(
                            "soil_moisture_0_to_1cm", [None] * len(times)
                        )[i],
                        "wind_speed": hourly.get("wind_speed_10m", [None] * len(times))[
                            i
                        ],
                    }
                )
            return forecast
        except Exception as e:
            print(f"❌ [WEATHER] Failed to fetch extended forecast: {e}")
            return []

    def get_comprehensive_weather_data(self, lat: float, lon: float) -> Dict:
        current = self.get_current_weather(lat, lon)
        forecast_24h = self.get_forecast_24h(lat, lon)
        historical = self.get_historical_rainfall(lat, lon, days=7)
        extended = self.get_extended_forecast(lat, lon, hours=48)

        return {
            "current": current,
            "forecast_24h": forecast_24h,
            "historical_7d": historical,
            "extended_48h": extended,
            "location": {"lat": lat, "lon": lon},
            "fetched_at": datetime.now().isoformat(),
        }


weather_service = WeatherService()
