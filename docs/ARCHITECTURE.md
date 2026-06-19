# Disaster Command Center - System Architecture

This document provides a technical deep-dive into the architectural components, data pipelines, AI grounding strategies, and deployment patterns of the Disaster Command Center.

---

## 1. System Components

The dashboard is built on a decoupled, lightweight stack designed for fast response, high rendering fidelity, and strict AI reliability.

```
┌────────────────────────────────────────────────────────────────────────┐
│                              BROWSER CLIENT                            │
│   ┌─────────────────────────┐           ┌─────────────────────────┐    │
│   │   Vanilla JS (app.js)   │◄─────────►│  Leaflet.js Map Layer   │    │
│   └────────────┬────────────┘           └─────────────────────────┘    │
│                │                                                       │
└────────────────┼───────────────────────────────────────────────────────┘
                 │ (HTTP REST Requests)
                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│                            FASTAPI WEB APP                             │
│   ┌─────────────────────────┐                                          │
│   │    Uvicorn Web Engine   │                                          │
│   └────────────┬────────────┘                                          │
│                ▼                                                       │
│   ┌───────────────────────────────────────────────────────────────┐    │
│   │    SERVICES CONTROLLER LAYER                                  │    │
│   │    ├─ geo_service.py (GeoJSON, Pandas, Filtering)             │    │
│   │    ├─ insights_service.py (District JSONL Summaries)          │    │
│   │    └─ gemini_service.py (Intent Parsing & Three-Tier AI)      │    │
│   └────────────┬─────────────────────────────┬────────────────────┘    │
│                │                             │                         │
│                ▼                             ▼                         │
│   ┌─────────────────────────┐   ┌─────────────────────────┐            │
│   │   Gemini Key Manager    │   │  Local Data Artifacts   │            │
│   │  (gemini_round_robin.py)│   │  (district_master, etc) │            │
│   └────────────┬────────────┘   └─────────────────────────┘            │
└────────────────┼───────────────────────────────────────────────────────┘
                 │
      ┌──────────┴──────────┐
      │    PRIMARY MODEL     │        FALLBACK MODEL
      │  Gemini 2.5 Flash   │──────► Qwen 2.5 7B
      │  (google-genai SDK) │        (HuggingFace Inference API)
      └─────────────────────┘        provider: together
```

---

## 2. AI Model Strategy

### Primary: Gemini 2.5 Flash

- **SDK**: `google-genai` (`from google import genai`)
- **Key Management**: `gemini_round_robin.py` manages 5 API keys (`GEMINI_API_KEY1..5`) via round-robin scheduling
- **Quota Handling**: On 429 / rate-limit errors, keys are cooled down for 60 seconds before retry
- **Startup**: Keys are loaded with `status = "active"` without API pinging (quota conservation)

### Fallback: Qwen/Qwen2.5-7B-Instruct

- **SDK**: `huggingface_hub` (`from huggingface_hub import InferenceClient`)
- **Provider**: `together` (serverless hosted inference — no GPU, no model download)
- **Trigger**: Automatically invoked when all Gemini keys are rate-limited or unavailable
- **Token**: `HF_TOKEN` environment variable

### Final Fallback: Rule-Based Engine

- **Implementation**: `get_deterministic_rule_response()` in `gemini_service.py`
- **Mechanism**: Generates structured operational text directly from the filtered Pandas DataFrame
- **Guarantee**: Always available — never requires an external API call

### Failover Logic

```
get_available_key() → Gemini 2.5 Flash
      │
      └── Exception (quota / rate-limit / provider error)
            │
            ▼
      query_qwen_fallback(prompt) → Qwen 2.5 7B via HF API
            │
            └── Exception (HF_TOKEN missing / API error)
                  │
                  ▼
            get_deterministic_rule_response(intent, entities, filtered)
                  │
                  └── Returns structured rule-based summary
```

---

## 3. Risk Scoring Methodology

### Exact Weighting Formulas

```
Flood Risk Score = normalize(
    w1 × water_level_above_danger_m +
    w2 × avg_discharge_m3s +
    w3 × historical_flood_ratio +
    w4 × active_flood_hotspots
)

Heat Risk Score = normalize(
    w1 × Tmax +
    w2 × Tavg +
    w3 × WBGT_index +
    w4 × precip_deficit
)

Overall Risk Score = (0.6 × Flood Risk Score) + (0.4 × Heat Risk Score)

Dual Hazard Escalation:
  IF flood_severity != "Low" AND heat_alert_tier != "Normal":
      SET dual_hazard_flag = True
      Overall Risk Score += escalation_bonus
```

### Severity Classification Tiers

| Score Range | Tier | Map Color |
|-------------|------|-----------|
| 0 – 25 | Low Risk | `#81c784` (Soft Green) |
| 26 – 50 | Moderate Risk | `#f9a825` (Amber) |
| 51 – 75 | High Risk | `#ef6c00` (Orange) |
| 76 – 90 | Critical Risk | `#c62828` (Red) |
| 91 – 100 | Extreme Risk | `#800000` (Dark Red) |

---

## 4. Rule Engine & AI Grounding Strategy

### Step-by-Step Grounding Pipeline

```
[Operator Query]
       │
       ▼
1. Intent Classification (Regex & Keyword Matcher in classify_and_filter())
       │  Supported intents:
       │  ├── Cross Disaster Analysis  (both/dual/simultaneous keywords)
       │  ├── Threshold Filtering      (water level / danger mark + numeric)
       │  ├── Resource Optimization    (team/hotspot + zero/no/0)
       │  ├── Risk Ranking             (highest-risk/extreme/top keywords)
       │  ├── Operational Recommendation (recommend/priority/deployment)
       │  ├── State Summary            (matched state name in query)
       │  └── District Summary         (matched district name in query)
       │
       ▼
2. Entity & Threshold Extraction (regex: r"(\d+(?:\.\d+)?)")
       │  Extracts numeric values like 1.5 from "exceeding 1.5 meters"
       │
       ▼
3. Deterministic GeoJSON Filter (Pandas DataFrame scan)
       │  Applies filters: e.g. df[df.water_level_above_danger_m > 1.5]
       │  Returns only matching district rows
       │
       ▼
4. Context Assembly
       │  Top 40 matching districts formatted as structured text
       │  Injected into system prompt with strict grounding constraints
       │
       ▼
5. [TIER 1] Gemini 2.5 Flash synthesis
       │  → On failure:
       ▼
6. [TIER 2] Qwen 2.5 7B (HF Inference API) synthesis
       │  → On failure:
       ▼
7. [TIER 3] Rule Engine deterministic summary
```

### Why Hallucinations Are Minimized

- **Closed context**: LLM only sees the filtered district subset — not external web or general knowledge
- **Explicit refusal**: System prompt: *"If requested information is not present, respond: Information unavailable in current command center dataset."*
- **No retrieval augmentation**: No vector search, no RAG — fully deterministic pre-filter
- **Verification fallback**: Even if both AI models fail, the rule engine produces an accurate, data-driven summary

---

## 5. Rate Limit Resilience

| Layer | Mechanism |
|-------|-----------|
| Gemini Key Rotation | Round-robin across 5 keys; 429 triggers 60-second cooldown |
| Gemini Failure | Key marked `rate_limited` or `disabled`; next key in pool used |
| All Gemini Keys Exhausted | Automatic switch to Qwen 2.5 7B via HF Inference API |
| HF API Failure | Automatic switch to deterministic Rule Engine |
| Rule Engine | No external dependency — guaranteed response |

---

## 6. Deployment Architecture

- **Frontend (Static Hosting)**: Deployed on **Vercel** (`vercel.json`) serving `index.html`, `styles.css`, `app.js`
- **Backend (Web Server)**: Deployed on **Render** or **Railway** running Uvicorn
- **Environment Variables**:
  - `GEMINI_API_KEY1` through `GEMINI_API_KEY5` — Gemini round-robin keys
  - `HF_TOKEN` — HuggingFace Inference API token (together provider)
  - `PYTHONIOENCODING=utf-8` — recommended for consistent logging
