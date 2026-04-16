import os
from typing import Optional, Dict, Any, Tuple
import torch
import numpy as np
import cv2
import rasterio
from rasterio.io import MemoryFile
from scipy.ndimage import center_of_mass
from datetime import datetime

from core.config import settings

# GPU is faster but we fall back to CPU gracefully
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Only GeoTIFF has the coordinate metadata needed for accurate detection
SUPPORTED_FORMATS = {".tif", ".tiff", ".gtiff"}


class LandslideDetector:
    """
    Landslide detection using DeepLabV3+ model trained on satellite imagery.
    
    Why DeepLabV3+: ASPP module handles multi-scale landslide features better 
    than alternatives. ResNet50 encoder balances accuracy vs inference speed 
    for 10m resolution Sentinel-2 imagery.
    """

    def __init__(self):
        self.model = None
        self.load_model()

    def load_model(self):
        """Load the trained DeepLabV3+ model."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Use path from config (defaults to ../twentyeight.pkt)
        model_path = os.path.join(base_dir, settings.MODEL_PATH)

        if not os.path.exists(model_path):
            print("[WARNING] Model not found at " + str(model_path))
            print("[INFO] Expected: " + str(model_path))
            self.model = None
            return

        try:
            from segmentation_models_pytorch import DeepLabV3Plus

            print("[LOADING] DeepLabV3+ model from " + str(model_path) + "...")
            self.model = DeepLabV3Plus(
                encoder_name=settings.ENCODER, in_channels=3, classes=1
            )
            self.model.load_state_dict(
                torch.load(model_path, map_location=device, weights_only=False)
            )
            self.model.to(device)
            self.model.eval()
            print("[OK] Model loaded successfully!")

        except ImportError:
            print("⚠️ segmentation_models_pytorch not installed")
            print("   Run: pip install segmentation_models_pytorch albumentations")
            self.model = None
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            self.model = None

    def preprocess_image(self, image):
        """Preprocess image for model input."""
        import albumentations as A
        from albumentations.pytorch import ToTensorV2

        transform = A.Compose(
            [
                A.Resize(settings.IMG_SIZE[0], settings.IMG_SIZE[1]),
                A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
                ToTensorV2(),
            ]
        )

        augmented = transform(image=image)
        return augmented["image"].unsqueeze(0).to(device)

    def run_inference(self, image):
        """Run model inference on preprocessed image."""
        if self.model is None:
            return None

        with torch.no_grad():
            output = self.model(image)
            pred_mask = (torch.sigmoid(output) > 0.5).cpu().squeeze()

        return pred_mask.numpy()

    def predict_from_bytes(self, file_bytes, filename):
        """Process uploaded GeoTIFF with DeepLabV3+ model.
        
        Why GeoTIFF: Standard image formats (JPG, PNG) lose geographic metadata.
        GeoTIFF contains transform matrix and CRS needed to convert detection
        pixel coordinates back to real-world lat/lon for map display.
        """
        file_ext = os.path.splitext(filename.lower())[1]

        if file_ext not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format. Use GeoTIFF (.tif, .tiff)")

        try:
            with MemoryFile(file_bytes) as memfile:
                with memfile.open() as src:
                    # Read image bands
                    bands = src.read()

                    # Use RGB bands
                    if len(bands) >= 3:
                        image = np.moveaxis(bands[:3], 0, -1)
                    else:
                        image = np.moveaxis(bands, 0, -1)

                    transform = src.transform
                    crs = src.crs
                    bounds = src.bounds

                    # Normalize
                    if image.max() > 255:
                        if image.dtype == np.uint16:
                            image = (image / 65535.0 * 255).astype(np.uint8)
                        else:
                            image = image.astype(np.uint8)

                    # Ensure 3 channels
                    if image.shape[2] > 3:
                        image = image[:, :, :3]
                    if len(image.shape) == 2:
                        image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

                    # Run inference
                    result = self._analyze_image(image, transform, crs, bounds)
                    result["source"] = "upload"
                    return result

        except Exception as e:
            raise ValueError(f"Failed to process image: {str(e)}")

    def analyze_satellite_data(self, image_data):
        """Analyze image from satellite API with DeepLabV3+."""
        if image_data is None or "image" not in image_data:
            return {"severity": "Unknown", "error": "No image data"}

        image = image_data["image"]
        transform = image_data.get("transform")
        crs = image_data.get("crs")
        bounds = image_data.get("bounds")

        return self._analyze_image(image, transform, crs, bounds)

    def _analyze_image(self, image, transform, crs, bounds):
        """Internal method to analyze image with model.
        
        Why transform coordinates: Sentinel-2 data comes in UTM (EPSG:32643).
        API consumers expect WGS84 (lat/lon). We use pyproj Transformer for
        accurate conversion - simple offset would be off by ~1km at these latitudes.
        """
        # Preprocess
        input_tensor = self.preprocess_image(image)

        # Run inference
        if self.model is not None:
            pred_mask = self.run_inference(input_tensor)
        else:
            # Fallback: rule-based detection
            pred_mask = self._rule_based_detection(image)

        # Calculate area
        num_pixels = np.sum(pred_mask > 0.5)
        
        # Calculate confidence (percentage of detected pixels)
        # If detected pixels < 0.1% of image, treat as noise
        total_pixels = pred_mask.size
        confidence = num_pixels / total_pixels if total_pixels > 0 else 0
        
        # Only count as landslide if confidence > 0.3% of pixels
        # This filters out false positives from model artifacts
        if num_pixels < (total_pixels * 0.003):
            num_pixels = 0
            confidence = 0
        
        area_sq_meters = num_pixels * (settings.SPATIAL_RESOLUTION**2)

        # Determine severity
        if area_sq_meters == 0:
            severity = "No Landslide"
        elif area_sq_meters < 1000:
            severity = "Low"
        elif area_sq_meters < 10000:
            severity = "Medium"
        elif area_sq_meters < 100000:
            severity = "High"
        else:
            severity = "Very High"

        # Get center of detection for coordinates
        lat, lon = None, None
        if num_pixels > 0:
            try:
                # Find center of mass
                mask_binary = (pred_mask > 0.5).astype(np.uint8)
                contours, _ = cv2.findContours(
                    mask_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )

                if contours:
                    largest = max(contours, key=cv2.contourArea)
                    M = cv2.moments(largest)
                    if M["m00"] > 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])

                        # Convert pixel to lat/lon using rasterio transform
                        if transform is not None and crs is not None:
                            from rasterio.transform import rowcol, xy

                            # Get the x,y coordinates in the image's CRS
                            px, py = xy(transform, cy, cx)

                            # Check if we need to transform to WGS84
                            try:
                                from rasterio.crs import CRS

                                image_crs = CRS.from_user_input(crs)
                                wgs84 = CRS.from_epsg(4326)

                                if image_crs != wgs84:
                                    from pyproj import Transformer

                                    transformer = Transformer.from_crs(
                                        image_crs, wgs84, always_xy=True
                                    )
                                    lon, lat = transformer.transform(px, py)
                                else:
                                    lon, lat = px, py
                            except Exception as e:
                                print(
                                    f"[COORD] CRS transform error: {e}, using bounds fallback"
                                )
                                # Fallback: assume bounds are in WGS84
                                if bounds:
                                    x = bounds.left + (cx / image.shape[1]) * (
                                        bounds.right - bounds.left
                                    )
                                    y = bounds.top - (cy / image.shape[0]) * (
                                        bounds.top - bounds.bottom
                                    )
                                    lon, lat = x, y
                        elif bounds:
                            # Fallback: assume bounds are in WGS84
                            x = bounds.left + (cx / image.shape[1]) * (
                                bounds.right - bounds.left
                            )
                            y = bounds.top - (cy / image.shape[0]) * (
                                bounds.top - bounds.bottom
                            )
                            lon, lat = x, y

            except Exception as e:
                print(f"⚠️ Coordinate calculation error: {e}")

        return {
            "severity": severity,
            "area_sq_meters": float(area_sq_meters),
            "latitude": float(lat) if lat else None,
            "longitude": float(lon) if lon else None,
            "detected_pixels": int(num_pixels),
            "confidence": float(np.mean(pred_mask)) if num_pixels > 0 else 0.0,
            "timestamp": datetime.now().isoformat(),
        }

    def _rule_based_detection(self, image):
        """Fallback detection when model unavailable."""
        # Convert to HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)

        # Detect exposed soil (brown/tan)
        lower_brown = np.array([10, 30, 50], dtype=np.uint8)
        upper_brown = np.array([35, 255, 255], dtype=np.uint8)
        soil_mask = cv2.inRange(hsv, lower_brown, upper_brown)

        # Detect erosion (dark areas)
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        dark_mask = (gray < 70).astype(np.uint8) * 255

        # Combine
        combined = cv2.bitwise_or(soil_mask, dark_mask)

        # Resize to model input size for consistency
        combined = cv2.resize(combined, (settings.IMG_SIZE[0], settings.IMG_SIZE[1]))

        return combined / 255.0


# Global instance
model_service = LandslideDetector()
