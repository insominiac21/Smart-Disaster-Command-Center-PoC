# 🚨 Smart Disaster Command Center PoC

An AI-powered Emergency Operations Center (EOC) dashboard for monitoring **Floods** and **Heatwaves** across Indian districts.

The platform combines geospatial intelligence, deterministic disaster analytics, district-level risk assessment, and a grounded AI assistant to help emergency operators identify critical regions, prioritize response efforts, and retrieve actionable insights through natural language queries.

---

## 🌐 Live Demo

Frontend: https://smart-disaster-command-center.vercel.app

---

# 📌 Project Overview

The Smart Disaster Command Center is designed as a district-level disaster intelligence platform that transforms heterogeneous disaster datasets into operationally useful insights.

The system provides:

* Interactive district map
* Executive KPI dashboard
* Flood and heatwave monitoring
* Dual-hazard detection
* District drilldowns
* Operational alert feed
* Grounded AI operator assistant

Unlike traditional dashboards that only visualize data, this platform generates explainable district intelligence and supports natural language exploration of current disaster conditions.

---

# 🎯 Objectives

The platform helps answer questions such as:

* Which districts require immediate intervention?
* Which districts exceed critical flood thresholds?
* Which districts face simultaneous flood and heatwave risks?
* Where should emergency resources be prioritized?
* Which districts currently have insufficient response capacity?

---

# 🏗️ System Architecture

```text
                  ┌─────────────────┐
                  │   Frontend UI   │
                  │ HTML/CSS/JS     │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ FastAPI Backend │
                  └────────┬────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼

  District Data      AI Assistant      Alert Engine
  Processing         Grounding         Risk Logic

        ▼                  ▼                  ▼

 Flood Dataset     Gemini/Qwen      Risk Scores
 Weather Dataset   Fallback Chain   Severity Tiers
 GIS Boundaries    Query Routing    Alerts
```

---

# 📊 Datasets Used

## 1. Flood Dataset

Used for flood-risk estimation.

Features include:

* Latitude
* Longitude
* Rainfall
* River discharge
* Water level
* Elevation
* Land cover
* Soil type
* Historical flood occurrence

---

## 2. Weather Dataset

Used for heatwave modeling.

Features include:

* Average temperature
* Maximum temperature
* Minimum temperature
* Precipitation
* Wind speed
* Atmospheric pressure

---

## 3. GIS District Boundaries

District shapefiles are used to:

* Map observations to districts
* Aggregate risk metrics
* Enable district drilldowns
* Support district-level intelligence

---

# ⚙️ Data Engineering Pipeline

The project performs extensive preprocessing and harmonization.

## Challenges Solved

* District naming inconsistencies
* State naming mismatches
* Duplicate administrative entries
* Spatial alignment issues
* Point-to-polygon mapping

## Workflow

1. Clean district and state names
2. Perform geospatial joins
3. Match weather observations to districts
4. Aggregate flood signals
5. Aggregate weather signals
6. Generate district-level intelligence
7. Export enriched GeoJSON

### Final Dataset Statistics

| Metric                         | Value |
| ------------------------------ | ----- |
| Districts                      | 556   |
| Flood Records Joined           | 2,833 |
| Weather Records Matched        | 5,112 |
| Duplicate District-State Pairs | 0     |
| Missing Geometries             | 0     |

---

# 🌊 Flood Risk Modeling

Flood risk is calculated using:

* Rainfall intensity
* River discharge
* Water level
* Historical flood occurrence
* Elevation-based vulnerability

Derived outputs:

* Flood Risk Score
* Flood Severity
* Danger Line Exceedance
* Flood Alert Status

---

# 🌡️ Heatwave Risk Modeling

Heatwave risk is estimated using:

* Average temperature
* Maximum temperature
* Heat stress proxy
* Precipitation deficit proxy

Derived outputs:

* Heat Risk Score
* Heat Alert Tier
* Heat Severity

---

# ⚠️ Dual Hazard Detection

Districts are flagged as **Dual Hazard** when:

* Significant flood risk exists
* Significant heatwave risk exists

simultaneously.

This enables prioritization of regions facing compound disasters.

---

# 📈 Risk Scoring Framework

The system combines flood and heatwave indicators into a unified operational score.

Severity buckets:

* Low
* Moderate
* High
* Critical
* Extreme

The scoring framework is deterministic and explainable, allowing operators to trace every risk classification back to measurable inputs.

---

# 🤖 AI District Intelligence Generation

Structured district signals are converted into human-readable intelligence using Qwen.

Inputs:

* Flood severity
* Heat alert tier
* Risk score
* Dual hazard flag
* Response team count
* Danger line exceedance

Generated outputs:

* District archetype
* Summary
* Risk flags
* Recommended actions

Example:

> Critical Flood Severity
> Water levels significantly exceed danger threshold.
> Immediate deployment and evacuation preparation recommended.

Generated intelligence is stored in:

```text
artifacts/district_insights_final.jsonl
```

---

# 🧠 AI Reliability & Grounding

One of the primary goals of this project is reliable AI behavior.

## Grounding Strategy

The assistant never relies solely on model memory.

Pipeline:

1. Intent Classification
2. Entity Extraction
3. Threshold Parsing
4. Deterministic Dataset Filtering
5. Context Injection
6. LLM Synthesis
7. Fallback Routing

---

## Example Query

Operator asks:

> List all districts where water levels exceed the danger line by more than 1.5 meters.

The system:

* Extracts threshold value
* Filters district dataset
* Retrieves matching districts
* Injects only those records
* Generates grounded response

No hallucinated district information is permitted.

---

## Fallback Chain

Primary:

* Gemini 2.5 Flash

Secondary:

* Qwen 2.5 7B Instruct

Final:

* Deterministic rule-based response

This ensures graceful degradation during API failures or rate limits.

---

## Refusal Policy

If information does not exist in the loaded command-center dataset, the assistant responds:

> Information unavailable in current command center dataset.

---

# 🖥️ Dashboard Features

## Executive Metrics

Displays:

* Active Alerts
* High Risk Districts
* Active Flood Hotspots
* Response Teams
* Dual Hazard Districts
* Critical Flood Districts
* Extreme Risk Districts

---

## Interactive District Map

Provides:

* District selection
* Risk visualization
* Severity overlays
* Geographic exploration

---

## Alert Feed

Real-time operational stream displaying:

* Flood alerts
* Heatwave alerts
* Dual hazard alerts
* Critical district alerts

---

## District Explorer

Search and filter by:

* District
* State
* Flood severity
* Heat tier
* Dual hazard
* Risk score

---

## District Drilldown

Displays:

* Flood metrics
* Heat metrics
* Response status
* Summary
* Risk indicators
* Recommended actions

---

## AI Operator Assistant

Supports:

* Threshold filtering
* District summaries
* State summaries
* Resource allocation queries
* Cross-disaster analysis
* Risk ranking

---

# 📁 Repository Structure

```text
smart-disaster-command-center/
│
├── backend/
│   ├── main.py
│   ├── services/
│   └── routers/
│
├── frontend/
│   ├── index.html
│   ├── css/
│   └── js/
│
├── artifacts/
│   ├── district_master_enriched.geojson
│   ├── district_insights_final.jsonl
│   └── thresholds.json
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── WORKFLOW.md
│   └── DEPLOYMENT.md
│
├── requirements.txt
├── .env.example
└── README.md
```

---

# 🚀 Local Setup

## Prerequisites

* Python 3.9+
* Git

---

## Clone Repository

```bash
git clone https://github.com/insominiac21/Smart-Disaster-Command-Center-PoC.git

cd Smart-Disaster-Command-Center-PoC
```

---

## Create Virtual Environment

Windows

```bash
python -m venv .venv

.venv\Scripts\activate
```

Linux/macOS

```bash
python -m venv .venv

source .venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configure Environment

```bash
cp .env.example .env
```

Add API keys.

---

## Run Backend

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Open Application

```text
http://localhost:8000
```

---

# 🔑 Environment Variables

```env
GEMINI_API_KEY1=
GEMINI_API_KEY2=
GEMINI_API_KEY3=
GEMINI_API_KEY4=
GEMINI_API_KEY5=

HF_TOKEN=

FRONTEND_URL=https://smart-disaster-command-center.vercel.app
```

---

# ☁️ Deployment

## Backend

Recommended:

* Render
* Railway

Health Endpoint:

```text
/api/health
```

---

## Frontend

Recommended:

* Vercel

---

## Deployment Workflow

1. Deploy backend
2. Verify health endpoint
3. Deploy frontend
4. Configure CORS
5. Redeploy backend

---

# 📋 FIN100 Evaluation Mapping

| Requirement         | Implementation                                       |
| ------------------- | ---------------------------------------------------- |
| AI Reliability      | Grounding, fallback chain, refusal policy            |
| Disaster Modeling   | Flood, heatwave and dual-hazard logic                |
| Dashboard Usability | KPI cards, map, drilldowns, filtering                |
| Documentation       | README, workflow, architecture docs                  |
| Explainability      | Deterministic risk scoring and district intelligence |

---

# ⚠️ Limitations

* Uses static disaster datasets
* Not connected to live government feeds
* Severity buckets are calibrated for demonstration
* Proof-of-concept system only
* Not intended for real emergency deployment

---

# 🔮 Future Enhancements

* Live IMD integration
* NDMA integration
* Historical trend analytics
* Resource optimization engine
* SMS alerting
* WhatsApp notifications
* Mobile operator interface

---

# 📄 License

MIT License
