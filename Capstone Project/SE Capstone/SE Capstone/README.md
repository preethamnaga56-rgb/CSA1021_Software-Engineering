# CivicScale 🏛️⚡

> **A Cloud-Native Public Service Platform Utilizing Serverless Predictive Analytics and Automated Horizontal Pod Autoscaling for Dynamic Resource Allocation**

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-2.0-teal.svg)](https://fastapi.tiangolo.com)
[![Open Data](https://img.shields.io/badge/Open_Data-311_Civic_Records-blueviolet.svg)](https://data.gov)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

CivicScale is a full-stack, cloud-native public service platform engineered with a clean, decoupled 3-folder architecture (**Frontend**, **Backend**, and **API**). It combines an **authentic Open Data 311 public civic dataset (260+ entries)** with **serverless predictive machine learning** and **dynamic Horizontal Pod Autoscaling (HPA)** to guarantee sub-second citizen response times and eliminate scaling lag during civic demand surges.

---

## 📁 3 Main Segregated Folders

The codebase is segregated into **3 main folders**:

```
SE Capstone/
├── Frontend/                 # 1. Citizen Interface & Visual Analytics
│   ├── index.html            # Public Portal & Scaling Dashboard (HTML5)
│   ├── css/
│   │   └── styles.css        # Obsidian Cyber Design System & Glassmorphism
│   └── js/
│       └── app.js            # Real-time search, filters, pagination, WebSocket client
│
├── Backend/                  # 2. Core Business Logic, ML Models & Data
│   ├── config.py             # System thresholds, SLAs, HPA parameters
│   ├── data/
│   │   └── public_311_service_requests.json  # 260+ authentic open civic records
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py        # Pydantic schemas for public requests & telemetry
│   └── services/
│       ├── __init__.py
│       ├── civic_service.py  # Public request search, filtering, and pagination
│       ├── cluster_simulator.py  # Autonomous K8s pod lifecycle & HPA controller
│       ├── predictive_engine.py  # Serverless Scikit-Learn ML regression on 311 data
│       └── workload_generator.py # Realistic continuous civic traffic model
│
├── API/                      # 3. Gateway, Microservice Endpoints & Exporters
│   ├── main.py               # FastAPI gateway, WebSocket telemetry broadcaster
│   ├── civic.py              # Citizen public request search, filter, and submit
│   ├── telemetry.py          # Cluster and HPA autoscaling telemetry
│   ├── predictive.py         # ML forecast inference endpoints
│   └── metrics.py            # Prometheus OpenMetrics exporter
│
├── run.py                    # Root single-command launcher
├── start.bat                 # Windows one-click starter
├── requirements.txt          # Python dependencies
├── ARCHITECTURE.md           # Technical formulations & mathematical proofs
└── README.md                 # Public documentation
```

---

## 🌟 What the Public Can Do (Zero Friction, Instant Access)

1. **🏛️ Explore & Search 260+ Public 311 Records with Advanced Data Handling:**
   - Real-time indexed search across street addresses, request IDs, descriptors, and citizen names.
   - Multi-column sorting: Created Date, Priority (Critical First), Target SLA, Elapsed Hours, Agency, and Status.
   - Multi-attribute filtering: Municipal Agency (DEP, DOT, DOB, DSNY, DOHMH), District (Districts 1 to 8), Ticket Status, and Priority level.
   - **📥 1-Click Export:** Download filtered or full records directly as standardized **RFC 4180 CSV** or formatted **JSON**.
   - Detailed modal inspection with verified GPS coordinates, assigned worker pod, and SLA timers.

2. **⚡ File a Public Service Request in 3 Clicks:**
   - Click **"+ File Public Service Request"**.
   - Fill in name, email, category, address, and description.
   - Instantly receives an official tracking code (e.g. `SR-311-100261`) with atomic file persistence and guaranteed SLA routing.

3. **📊 High-End Quantile Gradient Boosted Predictive Autoscaling:**
   - **High-End Ensemble Algorithm:** Combines Quantile Gradient Boosted Regression (HistGradientBoostingRegressor with Pinball Loss), Bagged Random Forest, and Cross-Validated RidgeCV.
   - **Live Model Accuracy Dashboard:** Live evaluation metrics: $R^2$ Score, MAE, RMSE, MAPE, and 95% Quantile Band Coverage.
   - **Interactive Autonomous Workload & Chaos Controller:** Test live cloud autoscaling by injecting real traffic surges (Normal, Morning Rush, Storm Emergency, Tax Deadline) or crashing a random worker pod with 1 click to watch self-healing in action.
   - 15-minute forward quantile prediction curve with non-parametric confidence bands.
   - Live visual worker pod topology showing dynamic scaling across availability zones.

---

## 🚀 Quick Start (Single-Click Launch)

### On Windows:
Double-click `start.bat` or run:
```bash
python run.py
```

### On Linux / macOS:
```bash
pip install -r requirements.txt
python run.py
```

Open your browser to:
- **Public Service Platform:** [`http://localhost:8000`](http://localhost:8000)
- **API Documentation (Swagger UI):** [`http://localhost:8000/docs`](http://localhost:8000/docs)
- **OpenMetrics / Prometheus Telemetry:** [`http://localhost:8000/metrics`](http://localhost:8000/metrics)

---

## 📄 License
This project is licensed under the MIT License.
