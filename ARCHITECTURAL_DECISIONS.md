# Architectural Decisions - TeraAlert

This document records key architectural decisions and the reasoning behind them.

---

## Decision 1: DeepLabV3+ Over U-Net for Satellite Imagery

**Context:** Landslide detection on 10m resolution Sentinel-2 imagery.

**Constraint:** Sentinel-2 tiles are 10980x10980 pixels - need efficient processing of large images with multi-scale features.

**Reasoning:** 
- DeepLabV3+ uses Atrous Spatial Pyramid Pooling (ASPP) which captures multi-scale context without losing resolution
- Landslides appear at varying scales (some large, some small debris)
- ASPP's dilated convolutions handle this better than U-Net's skip connections
- ResNet50 encoder provides good balance between accuracy and inference speed

**Decision:** DeepLabV3+ with ResNet50 encoder

**Impact:** 
- Achieved 92% Dice score, 89% IoU
- Inference time: ~180ms on CPU, ~30ms on GPU
- Model size: ~250MB (acceptable for deployment)

**Alternative Considered:** U-Net - rejected because ASPP module handles variable-scale landslide features better

---

## Decision 2: Coordinate System Transformation (PyProj)

**Context:** Sentinel-2 data comes in UTM (EPSG:32643), API consumers expect WGS84 (lat/lon).

**Constraint:** Simple offset calculation results in ~1km error at Himalayan latitudes.

**Reasoning:**
- UTM projections have significant distortion away from the central meridian
- Hamirpur (76.52°E) is ~1° from UTM zone 43's central meridian (75°E)
- pyproj's Transformer uses accurate datum transformations

**Decision:** Use pyproj for coordinate transformation
```python
from pyproj import Transformer
transformer = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)
lon, lat = transformer.transform(utm_x, utm_y)
```

**Impact:**
- Coordinates now accurate to <1m (previously off by ~1km)
- Dashboard markers display correctly on Leaflet maps

---

## Decision 3: Genetic Algorithm for Safe Routing Over A*

**Context:** Calculate safe routes avoiding active landslide danger zones.

**Constraint:** Danger zones are dynamic (new detections every 5 minutes) and may block multiple roads simultaneously.

**Reasoning:**
- A* finds shortest path but is sensitive to obstacle changes - requires full recalculation
- GA's population-based search finds routes that avoid multiple danger zones simultaneously
- Multi-objective: can optimize for both distance AND safety in the fitness function

**Decision:** Genetic Algorithm with custom fitness function
```python
fitness = (1.0 / distance) + (safety_weight / min_distance_to_landslide)
```

**Impact:**
- Routes avoid all active danger zones (300m radius)
- Graceful degradation: finds "good enough" routes when optimal is blocked
- 1.5-2x computation time but more robust for dynamic obstacles

---

## Decision 4: Open-Meteo Over Paid Weather APIs

**Context:** Weather-based risk prediction requires rainfall and soil moisture data.

**Constraint:** Budget for FYP - cannot afford paid APIs like WeatherStack or Tomorrow.io.

**Reasoning:**
- Open-Meteo provides free access to all required parameters:
  - Rainfall (precipitation)
  - Soil moisture levels (soil_moisture)
  - Temperature, wind, humidity
- No API key required - reduces deployment complexity
- Historical data available for model training

**Decision:** Open-Meteo Weather API (free tier)

**Impact:**
- Zero cost for weather data
- Risk calculations based on real weather data (not hardcoded)
- 72-hour forecast enables proactive warnings

---

## Decision 5: JSON File-Based Storage Over Database

**Context:** Storing landslide detection history and user data.

**Constraint:** FYP scope - no production database infrastructure available.

**Reasoning:**
- SQLite would require additional setup
- JSON files work out-of-the-box with Python
- Active landslides are small dataset (<1000 entries)
- No concurrent writes in production (single backend instance)

**Decision:** JSON file storage (active_landslides.json, users.json)

**Impact:**
- Simple deployment - no database setup
- Easy backup (just copy the JSON file)
- For production: migrate to PostgreSQL with proper indexing

---

## Summary

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| DeepLabV3+ | Multi-scale features | 92% Dice |
| PyProj | Coordinate accuracy | <1m error |
| GA Routing | Dynamic obstacles | Safe routes |
| Open-Meteo | Free/Cost-effective | Zero cost |
| JSON storage | FYP simplicity | Easy deploy |

Each decision balances immediate FYP constraints with future production considerations.