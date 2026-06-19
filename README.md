# 🚨 Smart Disaster Command Center

An interactive, production-grade Emergency Operations Center (EOC) dashboard for monitoring **Floods** and **Heatwaves** across Indian districts in real-time.

Built using a **FastAPI backend** (REST API) and a lightweight **HTML/CSS/Vanilla JS frontend** featuring a **Leaflet.js choropleth map**, driven by three final data artifacts and a grounded, rate-limiting round-robin Gemini AI operator assistant with Qwen 2.5 7B fallback.

**Live Demo: https://smart-disaster-command-center.vercel.app/**
---

## 1. Project Overview

During extreme weather events, emergency operators are overwhelmed with raw, disconnected streams of data. The **Smart Disaster Command Center** is a state-of-the-art situational monitoring platform that gathers regional geospatial boundaries, weather metrics, and water levels into a single control screen.

The dashboard enables operators to instantly filter hazard types, inspect district-level risk intelligence narratives, check operational recommendations, and query an on-duty grounded AI assistant using natural language.

---

## 2. Problem Statement

Prototype dashboards built with generic tools like Streamlit are hard to maintain, slow to reload, prone to schema mismatch issues, and difficult to customize for real-time operation feeds. Additionally, generic LLM implementations in emergency applications suffer from **hallucinations**, which are dangerous when making decisions about evacuation or resource deployment.

This project addresses these challenges by:
1. Moving away from Streamlit to a professional **FastAPI backend** and **HTML/CSS/JS frontend** for speed and UI control.
2. Integrating **Leaflet.js** to map actual district MultiPolygon boundaries instead of simple point coordinates.
3. Implementing a **Rule Engine First** grounded AI assistant which deterministic-filters the local GeoJSON dataset before querying the LLM, eliminating hallucinations.

---

## 3. System Design & Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       LIGHTWEIGHT CLIENT                    │
│   - index.html (Teal light-mode EOC UI)                     │
│   - styles.css (Outfit font, rounded cards, soft shadows)   │
│   - app.js (Leaflet choropleth layer, click/hover handlers) │
└──────────────────────────────┬──────────────────────────────┘
                               │ (HTTP REST /api)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                        FASTAPI BACKEND                      │
│   - main.py (FastAPI App, endpoints, static mounts)         │
│   - services/geo_service.py (DataFrame/GeoJSON filtering)   │
│   - services/insights_service.py (JSONL narrative loader)   │
│   - services/gemini_service.py (Grounded copilot engine)    │
└──────────────────────────────┬──────────────────────────────┘
                               │ (GenAI SDK / HF Inference API)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                       EXTERNAL ENGINES                      │
│   - gemini_round_robin.py (Key manager, rotation logs)      │
│   - Gemini 2.5 Flash (Primary AI synthesis)                 │
│   - Qwen 2.5 7B via HuggingFace Inference API (Fallback)    │
│   - Rule Engine (Final deterministic fallback)              │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. AI Model Architecture

### Three-Tier Failover System

The AI assistant uses a **Rule Engine First + Three-Tier Failover** design that structurally prevents hallucinations and eliminates single points of failure:

```
User Query
   │
   ▼
Intent Classification (Regex + Keyword Matcher)
   │  ┌── Cross Disaster Analysis
   │  ├── Threshold Filtering (e.g. water_level > 1.5m)
   │  ├── Resource Optimization (zero response teams)
   │  ├── Risk Ranking (top 10 by score)
   │  └── State / District Summary
   │
   ▼
District Filtering (Deterministic — Pandas DataFrame)
   │  Only matching records injected into LLM context
   │  LLM cannot see data outside this window
   │
   ├──[TIER 1]─► Gemini 2.5 Flash (Round Robin, Keys 1–5)
   │             On quota / rate-limit / failure ↓
   │
   ├──[TIER 2]─► Qwen 2.5 7B — HuggingFace Inference API
   │             Provider: together (serverless, no GPU)
   │             On failure ↓
   │
   └──[TIER 3]─► Rule-Based Engine (deterministic synthesis)
                 Always available — never crashes
```

### Model Details

| Tier | Model | Provider | Env Variable |
|------|-------|----------|-------------|
| 1 (Primary) | Gemini 2.5 Flash | Google AI Studio | `GEMINI_API_KEY1..5` |
| 2 (Fallback) | Qwen/Qwen2.5-7B-Instruct | HuggingFace `together` | `HF_TOKEN` |
| 3 (Final) | Rule Engine | Local deterministic | — |

### Why Hallucinations Are Minimized

1. **Context isolation** — The LLM prompt only contains filtered districts matching the query, never the full 556-district dataset.
2. **Grounding constraint** — System prompt explicitly forbids inventing facts or using external knowledge.
3. **Deterministic pre-filter** — Numeric thresholds (e.g. `water_level > 1.5m`) extracted by regex *before* the LLM sees any data.
4. **Refusal instruction** — If no records match, model must respond: *"Information unavailable in current command center dataset."*
5. **Fallback chain** — If both LLMs fail, a deterministic rule summary is generated directly from Pandas data with zero hallucination risk.

---

## 5. The Data Pipeline

### Data Quality Metrics

| Step | Records | Quality |
|------|---------|---------|
| GIS Boundaries | 556 unique district polygons | 0 missing geometries |
| Flood Spatial Join | 2,833 joined records | 0 duplicates |
| Weather Join | 5,112 matched records | 0 missing entries |
| Qwen Narrative Gen | 556 district summaries | All schema-validated |

### Risk Scoring Methodology

```
Flood Risk Score  = f(water_level_above_danger, discharge_rate,
                      historical_flood_ratio, active_hotspots)

Heat Risk Score   = f(Tmax, Tavg, WBGT, precip_deficit)

Overall Risk Score = (0.6 × Flood Risk) + (0.4 × Heat Risk)
                    + Dual Hazard Escalation bonus

Severity Tiers:
  Score  0 – 25  →  Low Risk       (Soft Green)
  Score 26 – 50  →  Moderate Risk  (Amber)
  Score 51 – 75  →  High Risk      (Orange)
  Score 76 – 90  →  Critical Risk  (Red)
  Score 91 – 100 →  Extreme Risk   (Dark Red)
```

---

## 6. Qwen Offline Narrative Generation

To populate the intelligence drawers:
1. Prompts mapped to district risk scores and operational statistics are compiled.
2. An offline **Qwen 2.5 7B model** runs inference to generate a narrative summary, identify flags (e.g. "Dual Hazard"), and compile recommended actions for each district.
3. Raw logs are cleaned, validated against schema constraints (`cleaner.py`), and stored in the final production file: `artifacts/district_insights_final.jsonl`.

---

## 7. FIN100 Evaluation Mapping

| FIN100 Requirement | Dashboard Feature | Implementation |
|--------------------|-------------------|----------------|
| Cross Disaster Analysis | Dual Hazard filter + AI query | `dual_hazard_flag == True`, Cross Disaster intent |
| Threshold Filtering | Water level filter + AI query | `water_level_above_danger_m > threshold` (regex) |
| Resource Optimization | Zero-teams filter | `response_teams_deployed == 0` + hotspot check |
| Grounded AI | Three-tier failover AI | Gemini → Qwen → Rule Engine |
| Operational Decision Support | SOPs in drilldown drawer | `district_insights_final.jsonl` recommended_actions |

---

## 8. Dashboard Features

- **Light-Mode EOC Interface**: Teal headers, rounded cards, Outfit typography.
- **Leaflet Map Layers**: Color-coded district boundaries by risk score, with popups.
- **KPI Indicators**: Active Alerts, Dual Hazards, Critical Floods, Extreme Risk.
- **District Intelligence Database**: Search + 8-dimension filters + 5-column sort + CSV export.
- **Drilldown Drawer**: Hydrological metrics, thermal metrics, Qwen AI narratives, SOPs.
- **Grounded AI Copilot**: Three-tier model with in-dashboard architecture transparency panel.
- **Collapsible Framework Cards**: Risk scoring, alert logic, priority tiers, SOP references.
- **Executive Situation Room**: Dynamic national overview from local data.

---

## 9. Repository Structure

```
smart-disaster-command-center/
├── backend/
│   ├── main.py                    # FastAPI Web App Controller
│   └── services/
│       ├── geo_service.py         # GeoJSON loading, filters, KPIs
│       ├── insights_service.py    # District JSONL narratives parser
│       └── gemini_service.py      # Grounded Copilot (3-Tier Engine)
├── frontend/
│   ├── index.html                 # EOC Dashboard Layout
│   ├── css/styles.css             # EOC theme, drawer, table styles
│   └── js/app.js                  # Leaflet choropleth & REST binding
├── artifacts/                     # Locked Final Production Data
│   ├── district_master_enriched.geojson
│   ├── district_insights_final.jsonl
│   └── thresholds.json
├── docs/
│   ├── ARCHITECTURE.md            # Technical System Details
│   ├── WORKFLOW.md                # Data Lifecycle charts
│   └── DEPLOYMENT.md              # Cloud deployment instructions
├── gemini_round_robin.py          # Gemini API Key rotating client
├── requirements.txt               # Project dependencies
├── .env.example                   # Environment variable template
└── LICENSE                        # MIT License
```

---

## 10. Deployment Instructions

### Local Start
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Fill in GEMINI_API_KEY1..5 and HF_TOKEN

# 3. Start server
python backend/main.py
```
Open **`http://localhost:8000`** in your browser.

### Cloud Start
- **Frontend**: Deploy to Vercel — static routing handled by `vercel.json`.
- **Backend**: Deploy to Render/Railway. Set `GEMINI_API_KEY1..5` + `HF_TOKEN` in dashboard environment variables.

---

## 11. Technical Decisions

- **Leaflet over Plotly**: Faster, handles complex MultiPolygon boundaries natively.
- **Python Rule Engine over Vector RAG**: Deterministic, fewer tokens, zero hallucination risk.
- **Three-Tier AI Failover**: Eliminates single points of failure — dashboard never crashes on API quota exhaustion.
- **HF Inference API over local models**: No GPU required, no model downloads, pure serverless hosted inference.
