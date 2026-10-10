# Submission Writeup: Stubble Smoke Alert

## Problem

Every autumn, crop residue (stubble) burning in Punjab and Haryana sends thick smoke plumes into Delhi-NCR, pushing the Air Quality Index (AQI) into hazardous ranges. In November 2023, Delhi's AQI exceeded 400 for multiple consecutive days — classifying as "Severe" under CPCB standards.

Schools bear the brunt. With little advance warning, students attend PE, morning assemblies, and outdoor activities in dangerously polluted air. By the time CPCB bulletins are issued or news coverage peaks, the damage is done.

**Stubble Smoke Alert** provides next-day AQI band predictions for Delhi-NCR, translating each forecast into a specific, bounded action for school administrators: "Move PE indoors" rather than "air quality is poor."

## What We Built

### Data Pipeline
- **Weather ingestion**: Historical daily wind, temperature, and humidity from Open-Meteo (ERA5 reanalysis). No API key required.
- **Fire detection**: Satellite-based active fire detections from NASA FIRMS (VIIRS sensor, 375m resolution). Requires a free MAP_KEY.
- **AQI data**: Supports real CPCB data (CSV drop-in) or synthetic data calibrated to Delhi's seasonal patterns.

### Geospatial Feature Engineering
For each day, we compute:
- Fire counts in distance rings (0-200km, 200-400km) from Delhi
- Upwind weighting using haversine distance and bearing
- Cosine-weighted fire influence based on wind direction alignment
- All implemented in pure numpy — no heavy GIS dependencies

### ML Model
- GradientBoostingClassifier predicting next-day AQI band (5 classes)
- Chronological train/test split (no data leakage)
- Compared against a "tomorrow = today" baseline — reported honestly

### Policy Layer
- Rule-based mapping from AQI band to school action
- Independent of the ML model, fully unit-tested (21 tests)
- Each output includes the band, action, and a plain-language reason

### Frontend
- Single-page app: HTML + vanilla JS + Leaflet.js
- Dark theme, mobile-responsive, glassmorphism design
- Interactive fire map with wind direction overlay
- AQI band color coding and severity indicators

## Where AWS Fits

| Service | Role |
|---------|------|
| **Amazon S3** | Stores forecast data, model artifacts, and hosts the static frontend via S3 website hosting |
| **AWS Lambda** | Serverless API serving GET /forecast and GET /fires — reads pre-computed JSON from S3 |
| **Amazon API Gateway** | HTTP API with CORS, routing requests to Lambda |
| **AWS SAM** | Infrastructure-as-code for reproducible deployment |

AWS was chosen for:
- **Zero-server operations**: S3 static hosting + Lambda = no servers to manage
- **Cost efficiency**: Pay-per-request pricing means near-zero cost at hackathon scale
- **Reproducibility**: SAM template deploys the entire stack in one command
- **Scalability**: If this tool were adopted by schools across Delhi-NCR, it scales automatically

## AI Tools Used

- **Antigravity IDE / Claude**: Code generation, data source research, test creation, documentation
- All code was reviewed and understood by the developer
- All architectural decisions, policy rules, and data schemas were human-directed
- AI assistance was used transparently and is documented in the README

## Key Numbers

- **64 automated tests** passing across 4 test modules
- **822 days** of training data (Oct 2022 - Dec 2024)
- **69.7% model accuracy** vs. 79.4% baseline (honestly reported)
- **96% recall on "Very Poor"** days — the most safety-critical class
- **5 CPCB AQI bands** with corresponding school actions
