# Disaster Command Center - Data Lifecycle & Operations Workflow

This document details the operational workflow, data pipeline stages, pre-processing joins, Qwen narrative generation, and AI query execution life cycle.

---

## 1. Data Pipeline Overview

```
 [Raw Flood Points]       [Raw Weather Cities]
         │                          │
         └───────────┬──────────────┘
                     │ (Spatial Join — GeoPandas sjoin)
                     ▼
             [GIS Boundaries]
                     │ (Polygon Match — 556 districts)
                     ▼
       [556 Aggregated Districts]
                     │ (Risk Scoring Engine)
                     ▼
    [district_master_enriched.geojson]
         │                          │
         │ (District profiles)      ├───────────────────┐
         ▼                          ▼                   ▼
    [Qwen 2.5 7B offline]      [Leaflet Map]       [KPI Metrics]
         │ (Narrative Gen)
         ▼ (cleaner.py schema parse)
  [district_insights_final.jsonl]
         │
         └─────────────────── [FastAPI REST API]
                                      │
                                      ▼
                          [Grounded AI Copilot]
                      (Three-Tier Failover Model)
```

---

## 2. Pre-Processing Pipelines

### Step 1: Raw Datasets

| Dataset | Fields |
|---------|--------|
| Flood Dataset | Lat/Lon, rainfall_mm, water_level_m, danger_level_m, discharge_m3s, historical_flood_occurrences |
| Weather Dataset | Date, Tmin, Tavg, Tmax, precipitation_mm, WBGT_index, city_name |
| GIS Boundaries | Indian district MultiPolygon shapefile (district_id, district_name, state) |

### Step 2: Spatial Joins

- GIS shapes loaded using **GeoPandas**
- Flood lat/lon points converted to Shapely Points and joined via `sjoin("within")` to district polygons
- Weather cities resolved using nearest-boundary coordinate matching
- **Results**: 556 matched districts, 2,833 flood records joined, 5,112 weather records matched
- **Quality**: 0 duplicate districts, 0 missing geometries, 0 unresolved weather cities

### Step 3: District Aggregation

- Flood records grouped by `district_id`:
  - `max_water_level_m`, `avg_discharge_m3s`, `historical_flood_ratio`, `active_flood_hotspots`
  - `water_level_above_danger_m = max_water_level_m - danger_level_m`
- Weather attributes aggregated per district:
  - `avg_Tmax`, `avg_WBGT`, `precip_deficit`

### Step 4: Risk Computation

```
Flood Risk Score (0–100):
  Normalized weighted sum of:
    water_level_above_danger_m  (primary weight)
    avg_discharge_m3s            (secondary weight)
    historical_flood_ratio       (tertiary weight)
    active_flood_hotspots        (supplemental)

Heat Risk Score (0–100):
  Normalized weighted sum of:
    avg_Tmax     (primary)
    avg_WBGT     (secondary)
    precip_deficit (tertiary)

Overall Risk Score = (0.6 × Flood Risk) + (0.4 × Heat Risk)

Dual Hazard Flag:
  SET dual_hazard_flag = True
  IF flood_severity IN ["Critical", "High", "Moderate"]
  AND heat_alert_tier IN ["Red", "Orange", "Yellow"]
```

### Step 5: Severity Classification

| Metric | Threshold | Severity |
|--------|-----------|----------|
| Water above danger | > 1.5m | Critical |
| Water above danger | 1.0–1.5m | High |
| Water above danger | 0.5–1.0m | Moderate |
| Water above danger | < 0.5m | Low |
| WBGT | > 32°C | Red |
| WBGT | 30–32°C | Orange |
| WBGT | 28–30°C | Yellow |
| WBGT | < 28°C | Normal |

---

## 3. Qwen Narrative Summaries

### Model Used
- **Model**: `Qwen/Qwen2.5-7B-Instruct`
- **Inference Type**: Offline batch inference (local Qwen run during data preparation)
- **Output**: 556 narrative summaries stored in `district_insights_final.jsonl`

### Input Schema (per district)
```json
{
  "district_id": "D0001",
  "district": "Thane",
  "state": "Maharashtra",
  "flood_severity": "Critical",
  "heat_alert_tier": "Orange",
  "overall_risk_score": 87.4,
  "water_level_above_danger_m": 2.1,
  "response_teams_deployed": 3,
  "active_flood_hotspots": 5,
  "dual_hazard_flag": true
}
```

### Output Schema (per district)
```json
{
  "district_id": "D0001",
  "summary": "Thane district is experiencing critical flood conditions...",
  "risk_flags": ["Dual Hazard Active", "Water Level +2.1m Above Danger", "High Discharge Rate"],
  "recommended_actions": [
    "Deploy additional flood response teams immediately.",
    "Activate evacuation corridors for low-lying areas.",
    "Coordinate heat relief shelters for dual-hazard population."
  ]
}
```

### Validation (`cleaner.py`)
- Parses raw Qwen output using regex schema extraction
- Validates `summary`, `risk_flags` (list), `recommended_actions` (list) against Pydantic schema
- Rejects malformed entries; only 556 fully valid records written to final JSONL

---

## 4. Live Dashboard Consumption

When the FastAPI backend starts:

1. `geo_service.initialize()` — Loads `district_master_enriched.geojson` into a GeoPandas GeoDataFrame
2. `insights_service.initialize()` — Loads `district_insights_final.jsonl` into an indexed dict by `district_id`
3. `gemini_service.initialize()` — Creates `GeminiKeyManager(count=5)`, marks all keys active (no startup pinging)

Client startup sequence (`app.js`):
```
loadKPIs()          → GET /api/kpis
loadAlerts()        → GET /api/alerts?limit=25
loadMasterDistricts() → GET /api/districts (all 556, cached client-side)
loadMap()           → GET /api/districts/geojson/map
```

---

## 5. AI Query Execution Workflow

When an operator submits an inquiry:

```
[1] User types query in AI Assistant textarea
         │
         ▼
[2] submitQuestion() in app.js
    → Fetches current district IDs (filtered or all)
    → POST /api/assistant { question, filtered_districts }
         │
         ▼
[3] FastAPI /api/assistant endpoint
    → Resolves districts from geo_service
    → Calls gemini_service.query(question, districts)
         │
         ▼
[4] classify_and_filter(question, districts)
    → Natural Language → Intent classification
    → Entity + threshold extraction (regex)
    → Deterministic Pandas filter → filtered subset
         │
         ▼
[5] Build grounding prompt
    → Inject only filtered districts (max 40)
    → Include intent, entity metadata
    → Include strict hallucination refusal rules
         │
         ▼
[6] TIER 1 — Gemini 2.5 Flash (google-genai SDK)
    → Round-robin across GEMINI_API_KEY1..5
    → On success → return answer
    → On failure (quota/rate-limit) → TIER 2
         │
         ▼
[7] TIER 2 — Qwen 2.5 7B (HuggingFace Inference API)
    → InferenceClient(provider="together", api_key=HF_TOKEN)
    → model="Qwen/Qwen2.5-7B-Instruct"
    → On success → return answer
    → On failure → TIER 3
         │
         ▼
[8] TIER 3 — Deterministic Rule Engine
    → get_deterministic_rule_response(intent, entities, filtered)
    → Structured text summary from Pandas data
    → Always succeeds — guaranteed response
         │
         ▼
[9] Response returned to frontend
    → formatMarkdown() renders bold/list markdown
    → Displayed in ASSISTANT LOG CONSOLE
    → queryCounter incremented in footer stats
```

---

## 6. Supported AI Query Intents

| Intent | Example Query | Deterministic Filter Applied |
|--------|--------------|------------------------------|
| Cross Disaster Analysis | "Which districts face both flood and heatwave?" | `dual_hazard_flag == True` |
| Threshold Filtering | "Districts exceeding 1.5m above danger" | `water_level_above_danger_m > 1.5` |
| Resource Optimization | "Critical flood zones with no teams" | `flood_severity == "Critical" AND response_teams == 0` |
| Risk Ranking | "Show highest risk districts" | `sort by overall_risk_score DESC, top 10` |
| Operational Recommendation | "Recommend deployment priorities" | `overall_risk_score > 50 OR dual_hazard` |
| State Summary | "Summarize Maharashtra" | `state == "Maharashtra"` |
| District Summary | "Tell me about Thane" | `district == "Thane"` |
