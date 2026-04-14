import os
import requests
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from datetime import datetime, timedelta
import time
import threading
from concurrent.futures import ThreadPoolExecutor

try:
    import pystac_client
    import planetary_computer

    STAC_AVAILABLE = True
except ImportError:
    STAC_AVAILABLE = False

# Cache directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEED_DIR = os.path.join(BASE_DIR, "simulated_satellite_feed")


class SatelliteAPI:
    """
    Microsoft Planetary Computer STAC API integration for Sentinel-2 imagery.
    Downloads real satellite images for landslide detection.
    """

    STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"

    # Himalayan monitoring zones
    ZONES = [
        {"name": "Hamirpur", "lat": 31.52, "lon": 76.52, "buffer": 0.1},
        {"name": "Kangra", "lat": 32.09, "lon": 76.32, "buffer": 0.1},
        {"name": "Mandi", "lat": 31.71, "lon": 76.93, "buffer": 0.1},
        {"name": "Shimla", "lat": 31.10, "lon": 77.17, "buffer": 0.1},
        {"name": "Kullu", "lat": 31.96, "lon": 77.11, "buffer": 0.1},
        {"name": "Chamba", "lat": 32.55, "lon": 76.12, "buffer": 0.1},
        {"name": "Kinnaur", "lat": 31.56, "lon": 78.59, "buffer": 0.1},
        {"name": "Dehradun", "lat": 30.32, "lon": 78.03, "buffer": 0.1},
        {"name": "Tehri", "lat": 30.38, "lon": 78.48, "buffer": 0.1},
        {"name": "Chamoli", "lat": 30.73, "lon": 79.60, "buffer": 0.1},
        {"name": "Rudraprayag", "lat": 30.28, "lon": 78.97, "buffer": 0.1},
        {"name": "Nainital", "lat": 29.38, "lon": 79.45, "buffer": 0.1},
        {"name": "Pithoragarh", "lat": 29.58, "lon": 80.22, "buffer": 0.1},
        {"name": "Srinagar", "lat": 34.08, "lon": 74.80, "buffer": 0.1},
        {"name": "Gulmarg", "lat": 34.15, "lon": 74.38, "buffer": 0.1},
        {"name": "Pahalgam", "lat": 34.01, "lon": 75.31, "buffer": 0.1},
        {"name": "Leh", "lat": 34.15, "lon": 77.58, "buffer": 0.15},
        {"name": "Kargil", "lat": 34.55, "lon": 76.13, "buffer": 0.1},
    ]

    def __init__(self):
        self.catalog = None
        self.last_fetch = {}
        self.cache_dir = os.path.join(FEED_DIR, "satellite_cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_catalog(self):
        """Get authenticated STAC catalog connection."""
        if not STAC_AVAILABLE:
            raise RuntimeError(
                "STAC libraries not available. Install: pip install pystac-client planetary-computer"
            )

        if self.catalog is None:
            self.catalog = pystac_client.Client.open(
                self.STAC_URL, modifier=planetary_computer.sign_inplace
            )
        return self.catalog

    def fetch_latest_imagery(self, lat, lon, buffer=0.1, days_back=30):
        """
        Fetch the most recent cloud-free Sentinel-2 image for a location.

        Args:
            lat: Latitude
            lon: Longitude
            buffer: Bounding box buffer in degrees
            days_back: Days to look back for imagery

        Returns:
            dict with image data or None if no image found
        """
        if not STAC_AVAILABLE:
            return self._fetch_fallback(lat, lon)

        try:
            catalog = self._get_catalog()

            # Bounding box
            bbox = [lon - buffer, lat - buffer, lon + buffer, lat + buffer]

            # Time range - last N days
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)

            print(
                "[STAC] Searching for imagery at ("
                + str(lat)
                + ", "
                + str(lon)
                + ")..."
            )

            # Search for Sentinel-2 L2A (atmospherically corrected)
            search = catalog.search(
                collections=["sentinel-2-l2a"],
                bbox=bbox,
                datetime=f"{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}",
                query={"eo:cloud_cover": {"lt": 30}},  # Less than 30% clouds
            )

            items = list(search.items())

            if not items:
                print("[STAC] No imagery found, using fallback")
                return self._fetch_fallback(lat, lon)

            # Get most recent
            latest = items[0]
            print(
                "[STAC] Found: "
                + str(latest.id)
                + " from "
                + str(latest.datetime.date())
            )

            # Get the visual (RGB) asset - already processed for display
            asset = latest.assets.get("visual")
            if not asset:
                asset = latest.assets.get("B04")  # Fallback to band 4

            # Get the actual href string (might be wrapped)
            asset_href = str(asset.href) if hasattr(asset, "href") else str(asset)
            asset_href = asset_href.replace("<Asset href=", "").replace(">", "").strip()

            # Download the image
            return self._download_and_process(asset_href, latest.id, lat, lon)

        except Exception as e:
            print("[STAC] Error: " + str(e))
            return self._fetch_fallback(lat, lon)

    def _download_and_process(self, href, item_id, lat, lon):
        """Download image and process as array."""
        try:
            print("[STAC] Downloading " + str(item_id) + "...")

            # Download with streaming
            response = requests.get(href, stream=True, timeout=120)
            response.raise_for_status()

            # Read into memory first
            with MemoryFile(response.content) as memfile:
                with memfile.open() as src:
                    # Read as array
                    data = src.read()

                    # Convert to (H, W, C) format
                    if len(data) >= 3:
                        image = np.moveaxis(data[:3], 0, -1)
                    else:
                        image = np.moveaxis(data, 0, -1)

                    # Normalize
                    if image.max() > 1:
                        image = (
                            (image / 65535.0 * 255).astype(np.uint8)
                            if image.dtype == np.uint16
                            else image.astype(np.uint8)
                        )

                    bounds = src.bounds
                    crs = src.crs
                    transform = src.transform

            return {
                "image": image,
                "bounds": bounds,
                "crs": crs,
                "transform": transform,
                "source": "Microsoft Planetary Computer",
                "item_id": item_id,
                "lat": lat,
                "lon": lon,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            print("[STAC] Download error: " + str(e))
            return self._fetch_fallback(lat, lon)

    def _fetch_fallback(self, lat, lon):
        """Generate demo data when API unavailable."""
        print(
            "[FALLBACK] Generating simulated data for ("
            + str(lat)
            + ", "
            + str(lon)
            + ")"
        )

        # Create a simulated "satellite image" - 256x256 RGB
        np.random.seed(int(lat * 100 + lon * 100) % 1000)

        # Simulate terrain with some variation
        base = np.ones((256, 256, 3), dtype=np.uint8) * 150

        # Add some noise for realism
        noise = np.random.randint(-20, 20, (256, 256, 3), dtype=np.int16)
        image = np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Add some "vegetation" (green patches)
        green_mask = np.random.random((256, 256)) > 0.7
        image[green_mask] = [80, 120, 60]

        # Add some "bare soil" (potential landslide areas)
        soil_mask = np.random.random((256, 256)) > 0.85
        image[soil_mask] = [160, 140, 120]

        # Calculate approximate bounds
        buffer = 0.05
        bounds_dict = {
            "left": lon - buffer,
            "right": lon + buffer,
            "top": lat + buffer,
            "bottom": lat - buffer,
        }

        # Create bounds object
        bounds = type("Bounds", (), bounds_dict)()

        # Create transform
        from rasterio.transform import from_bounds
        transform = from_bounds(
            bounds.left, bounds.bottom, bounds.right, bounds.top, 256, 256
        )

        return {
            "image": image,
            "bounds": bounds,
            "crs": "EPSG:4326",
            "transform": transform,
            "source": "Simulated (STAC unavailable)",
            "item_id": f"sim_{lat:.2f}_{lon:.2f}",
            "lat": lat,
            "lon": lon,
            "timestamp": datetime.now().isoformat(),
        }

    def fetch_all_zones(self, parallel=True):
        """Fetch latest imagery for all monitoring zones."""
        results = {}

        def fetch_zone(zone):
            print("[WORKER] Fetching " + zone["name"] + "...")
            data = self.fetch_latest_imagery(
                zone["lat"], zone["lon"], buffer=zone.get("buffer", 0.1)
            )
            return zone["name"], data

        if parallel and STAC_AVAILABLE:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(fetch_zone, z): z for z in self.ZONES}
                for future in futures:
                    name, data = future.result()
                    results[name] = data
        else:
            for zone in self.ZONES:
                name, data = fetch_zone(zone)
                results[name] = data

        return results

    def get_zone_image(self, zone_name):
        """Get the most recent image for a specific zone."""
        for zone in self.ZONES:
            if zone["name"].lower() == zone_name.lower():
                return self.fetch_latest_imagery(
                    zone["lat"], zone["lon"], zone.get("buffer", 0.1)
                )
        return None


# Global instance
satellite_client = SatelliteAPI()
