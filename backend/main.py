"""
Smart Disaster Command Center - FastAPI Backend

Provides REST API for:
- District data and geospatial queries
- Alert stream generation
- Grounded AI assistant queries
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.geo_service import GeoService
from backend.services.insights_service import InsightsService
from backend.services.gemini_service import GeminiService

# Initialize FastAPI app
app = FastAPI(
    title="Smart Disaster Command Center",
    description="Grounded AI assistant for flood & heatwave monitoring",
    version="1.0.0",
)

# CORS — reads FRONTEND_URL from environment, always allows localhost for local dev
_frontend_url = os.getenv("FRONTEND_URL", "").strip()
_cors_origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if _frontend_url:
    _cors_origins.append(_frontend_url)
    # Also allow the bare domain without trailing slash
    _cors_origins.append(_frontend_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Serve static files (frontend)
frontend_dir = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_dir), name="frontend")

# Initialize services
geo_service = GeoService()
insights_service = InsightsService()
gemini_service = GeminiService()

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class DistrictQuery(BaseModel):
    disaster_type: Optional[str] = "All"  # All, Floods, Heatwaves
    severity: Optional[str] = "All"
    search: Optional[str] = None

class AssistantQuery(BaseModel):
    question: str
    filtered_districts: Optional[List[str]] = None  # district_ids to pass

class AlertResponse(BaseModel):
    severity: str
    type: str
    district: str
    state: str
    message: str
    district_id: str

class KPIResponse(BaseModel):
    total_active_alerts: int
    dual_hazard_count: int
    critical_flood_count: int
    extreme_risk_count: int

class DistrictResponse(BaseModel):
    district_id: str
    district: str
    state: str
    flood_severity: str
    heat_alert_tier: str
    overall_risk_score: float
    dual_hazard_flag: bool
    flood_risk_score: float
    heat_risk_score: float
    water_level_above_danger_m: float
    response_teams_deployed: int
    active_flood_hotspots: int
    historical_flood_ratio: float

class DistrictDetailResponse(BaseModel):
    district: DistrictResponse
    insights: Optional[Dict[str, Any]] = None

class AssistantResponse(BaseModel):
    success: bool
    answer: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# HEALTH CHECK
# ============================================================================
from fastapi import Response

@app.get("/health")
async def health_root():
    return {
        "status": "healthy",
        "service": "disaster-command-center-backend",
        "version": "1.0.0",
    }

@app.head("/health")
async def health_root_head():
    return Response(status_code=200)


@app.get("/api/health")
async def health_api():
    return {
        "status": "healthy",
        "service": "disaster-command-center-backend",
        "version": "1.0.0",
    }

@app.head("/api/health")
async def health_api_head():
    return Response(status_code=200)

# ============================================================================
# KPI ENDPOINTS
# ============================================================================

@app.get("/api/kpis", response_model=KPIResponse)
async def get_kpis(query: DistrictQuery = Query(default=DistrictQuery())):
    """Get executive KPI metrics."""
    try:
        kpis = geo_service.get_kpis(
            disaster_type=query.disaster_type,
            severity=query.severity,
            search=query.search,
        )
        return kpis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ALERTS ENDPOINT
# ============================================================================

@app.get("/api/alerts", response_model=List[AlertResponse])
async def get_alerts(limit: int = Query(20, ge=1, le=100)):
    """Get live alert stream."""
    try:
        alerts = geo_service.generate_alerts(limit=limit)
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# DISTRICTS ENDPOINTS
# ============================================================================

@app.get("/api/districts", response_model=List[DistrictResponse])
async def list_districts(query: DistrictQuery = Query(default=DistrictQuery())):
    """List all districts with optional filtering."""
    try:
        districts = geo_service.list_districts(
            disaster_type=query.disaster_type,
            severity=query.severity,
            search=query.search,
        )
        return districts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/districts/{district_id}", response_model=DistrictDetailResponse)
async def get_district(district_id: str):
    """Get detailed view for a single district."""
    try:
        district = geo_service.get_district(district_id)
        if not district:
            raise HTTPException(status_code=404, detail="District not found")
        
        # Get insights
        insights = insights_service.get_insights(district_id)
        
        return {
            "district": district,
            "insights": insights,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/districts/geojson/map")
async def get_map_geojson(query: DistrictQuery = Query(default=DistrictQuery())):
    """Get GeoJSON for map visualization."""
    try:
        geojson = geo_service.get_map_geojson(
            disaster_type=query.disaster_type,
            severity=query.severity,
            search=query.search,
        )
        return geojson
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ASSISTANT ENDPOINT
# ============================================================================

@app.post("/api/assistant", response_model=AssistantResponse)
async def query_assistant(query: AssistantQuery):
    """
    Query the grounded AI assistant.
    
    Grounding strategy:
    1. If filtered_districts provided, use only those
    2. Otherwise, get all districts
    3. Pass filtered districts to Gemini
    4. Gemini cannot hallucinate data it doesn't see
    """
    try:
        if not query.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        # Get filtered districts
        if query.filtered_districts:
            districts = geo_service.get_districts_by_ids(query.filtered_districts)
        else:
            # Default: get all active alerts
            districts = geo_service.list_districts(disaster_type="All")
        
        # Query Gemini with grounded data
        response = gemini_service.query(query.question, districts)
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# THRESHOLDS ENDPOINT
# ============================================================================

@app.get("/api/thresholds")
async def get_thresholds():
    """Get severity thresholds."""
    try:
        thresholds = geo_service.get_thresholds()
        return thresholds
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ROOT
# ============================================================================

@app.get("/")
async def root():
    """Serve the frontend HTML."""
    return FileResponse(str(frontend_dir / "index.html"))

# ============================================================================
# STARTUP
# ============================================================================

@app.on_event("startup")
async def startup():
    """Initialize services on startup."""
    try:
        geo_service.initialize()
        insights_service.initialize()
        gemini_service.initialize(geo_service=geo_service)
        print("[OK] All services initialized successfully")
    except Exception as e:
        print(f"[ERROR] Startup error: {e}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
