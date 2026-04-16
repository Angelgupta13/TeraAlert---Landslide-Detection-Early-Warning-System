# TeraAlert - Himalayan Landslide Detection & Early Warning System

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.9+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

**Final Year Project** - Real-time landslide detection and early warning system using satellite imagery and deep learning.

---

## 🎯 Results & Accuracy (First 20% - The "6-Second Rule")

| Metric | Value |
|--------|-------|
| **Model Dice Score** | 92% |
| **Model IoU** | 89% |
| **Detection Coverage** | 16 Himalayan Districts |
| **API Response Time** | <200ms |
| **Risk Prediction Accuracy** | Based on weather data |

---

## 🚀 The Pitch

* **End-to-End Deep Learning System** using DeepLabV3+ to detect landslides from Sentinel-2 satellite imagery
* **Weather-Based Risk Prediction** using Open-Meteo API (rainfall + soil moisture)
* **Safe Route Calculation** using OpenStreetMap (OSMnx) with dynamic danger zone exclusion
* **Automated Early Warning** via email alerts to disaster management authorities

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TERALERT SYSTEM                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        FRONTEND LAYER                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                   │   │
│  │  │   Landing   │  │  Dashboard  │  │   Route    │                   │   │
│  │  │   (index)   │  │ (dashboard) │  │  (route)   │                   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                   │   │
│  │        ↓                 ↓                 ↓                          │   │
│  │   http://localhost:8000/{dashboard|route}                           │   │
│  └────────────────────────────────┬─────────────────────────────────────┘   │
│                                   │ HTTP/WebSocket                         │
│  ┌────────────────────────────────▼─────────────────────────────────────┐   │
│  │                         FASTAPI BACKEND                               │   │
│  │                      http://localhost:8000                           │   │
│  ├──────────────────────────────────────────────────────────────────────┤   │
│  │  API ENDPOINTS:                                                       │   │
│  │  • /api/health          - System health                               │   │
│  │  • /api/landslides     - ML Detection API                            │   │
│  │  • /api/risk-zones     - Real-time risk assessment                   │   │
│  │  • /api/weather        - Weather data (Open-Meteo)                  │   │
│  │  • /api/prediction     - 72-hour risk forecast                       │   │
│  │  • /route              - Safe route (Genetic Algorithm)              │   │
│  │                                                                        │   │
│  │  SWAGGER UI: http://localhost:8000/docs                              │   │
│  ├──────────────────────────────────────────────────────────────────────┤   │
│  │  MICROSERVICES (Background Workers):                                 │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐          │   │
│  │  │   Satellite    │  │    Risk        │  │     Email      │          │   │
│  │  │   Monitor      │  │   Predictor    │  │    Alerter     │          │   │
│  │  │   (5min poll)  │  │ (weather-based)│  │  (SMTP)        │          │   │
│  │  └────────────────┘  └────────────────┘  └────────────────┘          │   │
│  │         ↓                    ↓                    ↓                   │   │
│  │  ┌─────────────────────────────────────────────────────────────┐      │   │
│  │  │              COORDINATE TRANSFORMATION (UTM → WGS84)         │      │   │
│  │  │                    (PyProj Transformer)                      │      │   │
│  │  └─────────────────────────────────────────────────────────────┘      │   │
│  └────────────────────────────────┬────────────────────────────────────┘   │
│                                   │                                          │
│           ┌───────────────────────┼───────────────────────┐                │
│           ↓                       ↓                       ↓                 │
│  ┌────────────────┐     ┌────────────────┐     ┌────────────────┐         │
│  │   Sentinel-2    │     │  Open-Meteo    │     │OpenStreetMap   │         │
│  │  (Planetary     │     │   Weather API  │     │    (OSMnx)     │         │
│  │   Computer)     │     │   (Free)       │     │   (Routing)    │         │
│  └────────────────┘     └────────────────┘     └────────────────┘         │
│         ↓                       ↓                       ↓                   │
│  Real satellite        Weather data           Route calculation           │
│     images            + risk assessment       + danger avoidance          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
landslide/
├── backend/
│   ├── main.py              # FastAPI application entry point
│   ├── requirements.txt     # Python dependencies
│   ├── .env                 # Environment variables
│   ├── active_landslides.json  # Detection database
│   │
│   ├── core/
│   │   └── config.py        # Application configuration
│   │
│   ├── services/
│   │   ├── ml_service.py          # DeepLabV3+ model inference
│   │   ├── satellite_api.py       # Planetary Computer STAC API
│   │   ├── weather_service.py     # Open-Meteo integration
│   │   ├── risk_prediction_service.py  # Weather-based risk
│   │   ├── email_service.py       # SMTP alerts
│   │   ├── db_service.py          # JSON database
│   │   ├── routing_service.py     # Safe route (GA)
│   │   ├── worker.py              # Background monitor
│   │   └── early_warning_service.py
│   │
│   └── api/
│       ├── routes.py              # REST endpoints
│       └── auth_routes.py         # Authentication
│
├── frontend/
│   ├── index.html           # Landing page
│   ├── dashboard.html       # Monitoring dashboard
│   └── route.html           # Route planner
│
├── twentyeight.pkt          # Trained DeepLabV3+ model (LFS)
└── docker-compose.yml       # One-command deployment
```

---

## 🚀 Quick Start (Docker)

```bash
# Clone and run entire stack with one command
git clone https://github.com/Angelgupta13/TeraAlert---Landslide-Detection-Early-Warning-System.git
cd TeraAlert
docker-compose up -d

# Access:
#   Dashboard: http://localhost:8000/dashboard
#   API Docs:  http://localhost:8000/docs
```

### Manual Setup

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
cd backend
pip install -r requirements.txt

# Configure (.env)
# See API_KEYS.md for required configuration

# Run
python main.py

# Open http://localhost:8000
```

---

## 🧬 Algorithm Rationale: Genetic Algorithm vs A*

### Why Genetic Algorithm for Safe Routing?

| Factor | A* Algorithm | Genetic Algorithm |
|--------|--------------|-------------------|
| **Search Strategy** | Local, deterministic | Global, stochastic |
| **Optimality** | Guaranteed optimal | Approximate, population-based |
| **Time Complexity** | O(d²) where d=distance | Configurable via generations |
| **Dynamic Obstacles** | Requires recalculation | Handles via fitness function |

### Trade-offs

**A* Advantages:**
- Guarantees shortest path
- Deterministic results
- Efficient for static maps

**Genetic Algorithm Advantages:**
- **Global Search**: Finds routes that avoid multiple danger zones simultaneously
- **Multi-Objective**: Can optimize for distance AND safety simultaneously
- **No Pre-computation**: Works with dynamically updating landslide data
- **Graceful Degradation**: Finds "good enough" routes when optimal is blocked

### Our Implementation

```python
# Fitness function combines:
# 1. Route distance (minimize)
# 2. Danger zone proximity (minimize proximity to active landslides)
# 3. Road type preference (prefer highways over local roads)

fitness = (1.0 / distance) + (safety_weight / min_distance_to_landslide)
```

For a Himalayan landslide system where:
- Roads are frequently affected by landslides
- Danger zones change dynamically (new detections every 5 minutes)
- Multiple simultaneous closures are common

The GA's global search capability provides more robust route recommendations than A*'s local search.

---

## 📊 Data Sources

| Source | Purpose | Cost |
|--------|---------|------|
| Sentinel-2 (Planetary Computer) | Satellite imagery | Free |
| Open-Meteo Weather API | Rainfall, soil moisture | Free |
| OpenStreetMap | Routing data | Free |

---

## 🔬 ML Model

### Architecture
- **Model:** DeepLabV3+ with ResNet50 encoder
- **Input:** 512×512 satellite image
- **Output:** Binary landslide mask

### Detection Pipeline
```
Satellite Image → Preprocess → DeepLabV3+ → Post-process → Result
                   (512×512)    Inference    (Area calc)
```

### Severity Classification
| Severity | Area Threshold |
|----------|---------------|
| Low | < 1,000 m² |
| Medium | 1,000 - 10,000 m² |
| High | 10,000 - 100,000 m² |
| Very High | > 100,000 m² |

---

## 🌐 API Endpoints (Interactive Documentation)

**Swagger UI:** http://localhost:8000/docs

![Swagger UI](https://via.placeholder.com/800x400?text=Swagger+API+Documentation+Screenshot)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | System health |
| `/api/ml/status` | GET | ML model status |
| `/api/landslides` | GET | All detections |
| `/api/landslides/active` | GET | Active danger zones |
| `/api/risk-zones` | GET | Weather risk zones |
| `/api/weather?lat=&lon=` | GET | Weather data |
| `/api/prediction?lat=&lon=` | GET | 72h risk forecast |
| `/api/route` | POST | Safe route calculation |

**Interactive API Docs:** http://localhost:8000/docs

---

## 📧 Alert System

### Email Recipients by Severity
| Severity | Recipients |
|----------|------------|
| Low/Medium | State DDMA |
| High | + National DM (NDMA) |
| Very High | + NDRF |

### Cooldown
- No repeat alerts for same zone within 24 hours

---

## 🛠️ Tech Stack

| Category | Technologies |
|----------|--------------|
| ML | PyTorch, DeepLabV3+, ResNet50, OpenCV |
| Geospatial | Rasterio, PyProj, OSMnx, Shapely |
| Backend | FastAPI, Uvicorn, Pydantic |
| APIs | Planetary Computer (STAC), Open-Meteo |
| Email | SMTP/Gmail |
| Deployment | Docker, Docker Compose |

---

## 🐳 Docker Deployment

```bash
# Production deployment
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Environment Variables
Create `.env` file:
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_FROM_EMAIL=your-email@gmail.com
```

---

## 📝 Development Notes

### Adding Monitoring Zones
Edit `MONITORING_ZONES` in `backend/main.py`:
```python
MONITORING_ZONES = [
    {"name": "Hamirpur", "lat": 31.52, "lon": 76.52},
    # Add more zones...
]
```

### Risk Thresholds
Edit in `backend/services/risk_prediction_service.py`:
```python
RAINFALL_THRESHOLDS = {"low": 10, "moderate": 25, "high": 50, "very_high": 100}
SOIL_MOISTURE_THRESHOLDS = {"low": 30, "moderate": 50, "high": 70, "very_high": 85}
```

---

## 👨‍💻 Author

**Angel Gupta**  
Final Year Project

---

## 📄 License

MIT License