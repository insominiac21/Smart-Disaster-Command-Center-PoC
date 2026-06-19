# 🚨 Smart Disaster Command Center PoC

An interactive, production-style Emergency Operations Center (EOC) dashboard for monitoring **Floods** and **Heatwaves** across Indian districts.

Built with a **FastAPI backend** and a lightweight **HTML/CSS/Vanilla JavaScript frontend**, the system combines:
- geospatial district intelligence,
- deterministic disaster logic,
- district drilldown and filtering,
- a grounded AI operator assistant,
- and a fallback chain for reliability.

**Live Demo:** https://smart-disaster-command-center.vercel.app/

---

## 1. Project Overview

The Smart Disaster Command Center is a district-level disaster intelligence platform designed to help emergency operators quickly understand flood and heatwave risk, identify high-priority districts, and ask natural-language questions over the current command-center state.

Instead of a generic chat app or a static map, this project models:
- **Flood risk**
- **Heatwave risk**
- **Dual-hazard conditions**
- **Operational priority**
- **Actionable district summaries**

The final dashboard is a lightweight operations room interface with:
- KPI cards,
- interactive district map,
- live alert stream,
- district intelligence database,
- drilldown drawer,
- and grounded AI assistant.

---

## 2. Problem Statement

Emergency teams often struggle with:
- fragmented data from multiple sources,
- inconsistent district naming,
- geospatial mismatch across datasets,
- difficulty prioritizing districts,
- and unsafe AI responses that hallucinate facts.

This project addresses those problems by:

1. **Harmonizing district-level spatial data**
2. **Aggregating flood and weather signals into district intelligence**
3. **Computing deterministic risk tiers**
4. **Generating human-readable district summaries**
5. **Using a grounded AI assistant that only answers from current command-center data**

---

## 3. Why These Datasets?

### Flood Dataset
Used to model flood risk because it contains:
- latitude / longitude
- rainfall
- river discharge
- water level
- elevation
- land cover
- soil type
- historical flood occurrence

These variables are directly relevant to flood severity, water-danger thresholds, and hotspot detection.

### Weather Dataset
Used to model heatwave risk because it contains:
- date
- average temperature
- minimum temperature
- maximum temperature
- precipitation
- city

These variables support heat-stress estimation and heatwave alert tiering.

### GIS District Boundaries
Used to convert point-level flood/weather observations into **district-level intelligence**.

This is what makes the system operationally useful:
- maps
- district drilldowns
- district search
- district-based alerts
- operator queries

---

## 4. Data Engineering & Matching Workflow

The hardest part of the project was not the UI — it was making the datasets consistent.

### Challenges Solved
- district name mismatches
- spelling variations
- old administrative names
- duplicate district-state combinations
- polygon/point mismatch
- geospatial alignment issues

### What We Did
1. Normalized district and state names
2. Matched flood points to GIS districts using spatial joins
3. Matched weather cities to district buckets
4. Aggregated flood and weather signals by district
5. Built a canonical district master table
6. Enriched the GeoJSON with operational risk fields

### Final Validation
- **556 district rows**
- **0 duplicate district-state pairs**
- **0 missing geometries**
- **2,833 flood joined rows**
- **5,112 weather matched rows**

---

## 5. Disaster Logic & Data Modeling

The platform models **exactly two disaster types**:

### A. Floods
Tracked metrics:
- water level above danger line
- rainfall intensity
- active flood hotspots
- response teams deployed

Derived fields:
- flood risk score
- flood severity
- flood risk flag

### B. Heatwaves
Tracked metrics:
- ambient temperature
- WBGT proxy / heat stress proxy
- vulnerable clusters
- heat alert tier

Derived fields:
- heat risk score
- heat alert tier
- heat severity flag

### Dual Hazard
A district is marked as dual hazard when both flood and heat risk are active at the same time.

---

## 6. Risk Scoring Methodology

Risk scoring is deterministic and explainable.

### Flood Risk Score
Flood risk is derived from:
- flood occurrence rate
- rainfall intensity
- river discharge
- water level above danger line
- historical flood signal

### Heat Risk Score
Heat risk is derived from:
- average temperature
- maximum temperature
- precipitation deficit proxy
- heat stress / WBGT proxy

### Overall Risk Score
Overall risk combines flood and heat signals into a single operational priority score.

### Severity Buckets
For dashboard usability, severity buckets are **calibrated** so the command center has meaningful distribution and not every district falls into the same category.

The final severity tiers are:

- **Low**
- **Moderate**
- **High**
- **Critical**
- **Extreme**

> Note: The assistant still preserves the hard operational threshold for queries such as “water levels have exceeded the danger line by more than 1.5 meters.”  
> The 1.5m rule is a strict command-center threshold and is not relaxed.

---

## 7. Qwen Intelligence Generation

The project uses Qwen offline to convert structured district signals into readable operational intelligence.

### Inputs
For each district:
- flood severity
- heat alert tier
- overall risk score
- dual hazard flag
- response team status
- water level above danger line

### Outputs
Qwen generates:
- archetype name
- risk flags
- district summary
- recommended actions

### Why It Matters
The dashboard is not just scoring districts — it explains them.

Example output:
- “Critical Flood Severity”
- “Dual Hazard”
- “Deploy additional response teams”
- “Prepare for potential evacuation”

The raw Qwen output is cleaned and stored in:

`artifacts/district_insights_final.jsonl`

---

## 8. AI Reliability & Grounding Strategy

This is one of the core evaluation criteria of the assignment.

### Grounding Approach
The assistant **never answers from model memory alone**.

It follows a strict pipeline:

1. **Intent classification**
2. **Threshold/entity extraction**
3. **Deterministic filtering over the district dataset**
4. **Context injection of only matching districts**
5. **LLM response synthesis**
6. **Fallback to a second model**
7. **Final deterministic fallback if needed**

### Supported Intent Types
- Cross-disaster analysis
- Threshold filtering
- Resource optimization
- District summary
- State summary
- Risk ranking
- Operational recommendation

### Example
If the operator asks:

> “List all districts where water levels have exceeded the danger line by more than 1.5 meters.”

the system:
- extracts `water_level_above_danger_m > 1.5`,
- filters the local district data,
- passes only matching rows to the assistant,
- and returns a grounded answer.

### Fallback Chain
1. **Gemini 2.5 Flash** via round robin
2. **Qwen 2.5 7B Instruct** via HuggingFace Inference API
3. **Rule-based deterministic response**

This means the dashboard does not fail when one provider is rate-limited.

### Refusal Policy
If a query is outside the current command-center dataset, the assistant responds gracefully:

> “Information unavailable in current command center dataset.”

---

## 9. Dashboard Features

### Executive Metrics Grid
Top summary cards for:
- Total Active Alerts
- High-Risk Districts
- Active Flood Hotspots
- Total Response Teams Deployed
- Dual Hazard Districts
- Critical Flood Districts
- Extreme Risk Districts

### Live Alert Stream
A scrollable tactical feed of:
- flood alerts
- heat alerts
- dual hazard alerts
- critical districts

### District Intelligence Database
Searchable, filterable district explorer with:
- district search
- state filter
- flood severity
- heat alert tier
- dual hazard
- operational priority
- response teams
- risk score range

### District Drilldown Drawer
When a district is selected, the UI shows:
- district profile
- flood metrics
- heat metrics
- risk indicators
- risk flags
- summary
- recommended actions
- operational priority

### Grounded AI Operator Assistant
A chat interface that can answer only from the current district intelligence data.

---

## 10. Why the Dashboard Is Useful

The dashboard is designed for emergency operators, not casual browsing.

It helps answer:
- Which districts are critical right now?
- Which districts need immediate deployment?
- Which districts face both heat and flood risk?
- Which districts exceed water danger thresholds?
- Which hotspots have zero response teams?

This directly matches the assignment’s expected use cases.

---

## 11. Repository Structure

```text
smart-disaster-command-center/
├── backend/
│   ├── main.py
│   └── services/
│       ├── geo_service.py
│       ├── insights_service.py
│       └── gemini_service.py
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── styles.css
│   └── js/
│       └── app.js
├── artifacts/
│   ├── district_master_enriched.geojson
│   ├── district_insights_final.jsonl
│   └── thresholds.json
├── docs/
│   ├── ARCHITECTURE.md
│   ├── WORKFLOW.md
│   └── DEPLOYMENT.md
├── gemini_round_robin.py
├── requirements.txt
├── .env.example
└── LICENSE