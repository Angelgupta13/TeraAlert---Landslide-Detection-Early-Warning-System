# TeraAlert - Himalayan Landslide Detection & Early Warning System

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.9+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

**Final Year Project** - A real-time landslide detection and early warning system using satellite imagery and machine learning.

## 🚀 The Pitch

* **End-to-End Deep Learning System** using DeepLabV3+ to detect landslides from Sentinel-2 satellite imagery
* **Weather-Based Risk Prediction** using Open-Meteo API (rainfall + soil moisture)
* **Safe Route Calculation** using OpenStreetMap (OSMnx) with dynamic danger zone exclusion
* **Automated Early Warning** via email alerts to disaster management authorities

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Dashboard                        │
│              http://localhost:8000/dashboard                  │
│                   (Real-time Updates)                        │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────┐
│                      FastAPI Backend                         │
│                   http://localhost:8000                      │
├─────────────────────────────────────────────────────────────┤
│  📡 API Endpoints:                                          │
│  ├── /api/landslides/* - ML Detection & Management          │
│  ├── /api/weather/* - Weather data (Open-Meteo)            │
│  ├── /api/risk-zones - Real-time risk assessment            │
│  ├── /api/prediction - 72-hour risk forecast                │
│  └── /route - Safe Route Calculation (Genetic Algorithm)      │
├─────────────────────────────────────────────────────────────┤
│  ⚙️ Background Workers:                                     │
│  ├── Satellite Monitoring (5 min polling)                    │
│  └── Coordinate Transformation (UTM → WGS84)                 │
├─────────────────────────────────────────────────────────────┤
│  📊 Services Layer:                                         │
│  ├── ML Service (DeepLabV3+ Inference)                     │
│  ├── Weather Service (Open-Meteo API)                       │
│  ├── Risk Prediction (Weather-based)                        │
│  ├── Email Service (SMTP Alerts)                            │
│  └── Routing Service (OSMnx + GA)                           │
└─────────────────────────────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Sentinel-2       │ │ Open-Meteo      │ │ OpenStreetMap   │
│ (Planetary      │ │ Weather API     │ │ (Routing)       │
│  Computer)       │ │ (Free, No Key) │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

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
│   │   ├── ml_service.py          # DeepLabV3+ model
│   │   ├── satellite_api.py       # Planetary Computer STAC
│   │   ├── weather_service.py     # Open-Meteo integration
│   │   ├── risk_prediction_service.py  # Weather-based risk
│   │   ├── email_service.py       # SMTP alerts
│   │   ├── db_service.py          # JSON database
│   │   ├── routing_service.py      # Safe route (GA)
│   │   └── worker.py              # Background monitor
│   │
│   └── api/
│       └── routes.py              # Additional routes
│
├── frontend/
│   ├── index.html           # Landing page
│   ├── dashboard.html       # Monitoring dashboard
│   └── route.html           # Route planner
│
└── twentyeight.pkt          # Trained DeepLabV3+ model
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Git

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd landslide

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac

# Install dependencies
cd backend
pip install -r requirements.txt
```

### Configuration

Create `backend/.env`:

```env
# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_FROM_EMAIL=your-email@gmail.com

# Authority Emails
AUTHORITY_EMAIL_1=ddma-hamirpur@gov.in
AUTHORITY_EMAIL_8=ddma-srinagar@jk.gov.in
AUTHORITY_EMAIL_11=ndma@nic.in
AUTHORITY_EMAIL_12=controlroom@ndrf.gov.in
```

### Run

```bash
cd backend
python main.py
```

Open http://localhost:8000

## 📊 Data Sources

| Source | Purpose | Cost |
|--------|---------|------|
| Sentinel-2 (Planetary Computer) | Satellite imagery | Free |
| Open-Meteo Weather API | Rainfall, soil moisture | Free |
| OpenStreetMap | Routing data | Free |

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

## 🌐 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | System health |
| `/api/ml/status` | GET | ML model status |
| `/api/landslides` | GET | All detections |
| `/api/risk-zones` | GET | Weather risk zones |
| `/api/weather?lat=&lon=` | GET | Weather data |
| `/api/prediction?lat=&lon=` | GET | 72h risk forecast |

## 📧 Alert System

### Email Recipients by Severity
| Severity | Recipients |
|----------|------------|
| Low/Medium | State DDMA |
| High | + National DM (NDMA) |
| Very High | + NDRF |

### Cooldown
- No repeat alerts for same zone within 24 hours

## 🛠️ Tech Stack

| Category | Technologies |
|----------|--------------|
| ML | PyTorch, DeepLabV3+, ResNet50, OpenCV |
| Geospatial | Rasterio, PyProj, OSMnx, Shapely |
| Backend | FastAPI, Uvicorn, Pydantic |
| APIs | Planetary Computer (STAC), Open-Meteo |
| Email | SMTP/Gmail |

## 📝 Development Notes

### Monitoring Zones
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

## 🔒 Production Deployment

```bash
pip install gunicorn
cd backend
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## 👨‍💻 Author

**Angel Gupta**  
Final Year Project

## 📄 License

MIT License
