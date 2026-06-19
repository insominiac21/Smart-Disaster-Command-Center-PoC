"""
Geo Service - Handles GeoJSON loading and geospatial queries.
"""

import json
import geopandas as gpd
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional

class GeoService:
    def __init__(self):
        self.artifacts_dir = Path(__file__).parent.parent.parent / "artifacts"
        self.gdf = None
        self.df = None
        self.thresholds = None

    def initialize(self):
        """Load all data on startup."""
        self._load_geojson()
        self._load_thresholds()

    def _load_geojson(self):
        """Load and parse district_master_enriched.geojson."""
        geojson_path = self.artifacts_dir / "district_master_enriched.geojson"
        if not geojson_path.exists():
            raise FileNotFoundError(f"Missing: {geojson_path}")
        
        self.gdf = gpd.read_file(geojson_path)
        if "state" not in self.gdf.columns and "st_nm" in self.gdf.columns:
            self.gdf["state"] = self.gdf["st_nm"]
        self.df = pd.DataFrame(self.gdf.drop(columns=['geometry']))
        print(f"[OK] Loaded {len(self.df)} districts from GeoJSON")

    def _load_thresholds(self):
        """Load thresholds.json."""
        thresholds_path = self.artifacts_dir / "thresholds.json"
        if not thresholds_path.exists():
            raise FileNotFoundError(f"Missing: {thresholds_path}")
        
        with open(thresholds_path, "r") as f:
            self.thresholds = json.load(f)
        print("[OK] Loaded thresholds")

    def get_thresholds(self) -> Dict[str, Any]:
        """Return thresholds."""
        return self.thresholds

    def _filter_districts(
        self,
        df: pd.DataFrame,
        disaster_type: str = "All",
        severity: str = "All",
        search: str = None,
    ) -> pd.DataFrame:
        """Apply filters to district dataframe."""
        result = df.copy()

        # Disaster type filter
        if disaster_type == "Floods":
            result = result[result["flood_severity"] != "Low"]
        elif disaster_type == "Heatwaves":
            result = result[result["heat_alert_tier"] != "None"]
        # else: "All" - no filter

        # Severity filter
        if severity != "All":
            if disaster_type == "Floods" or disaster_type == "All":
                result = result[result["flood_severity"] == severity]

        # Search filter
        if search:
            result = result[result["district"].str.contains(search, case=False, na=False)]

        return result

    def get_kpis(
        self,
        disaster_type: str = "All",
        severity: str = "All",
        search: str = None,
    ) -> Dict[str, int]:
        """Compute KPI metrics."""
        df = self._filter_districts(self.df, disaster_type, severity, search)

        # Total active alerts
        total_alerts = len(
            df[
                (df["flood_severity"] != "Low") | 
                (df["heat_alert_tier"] != "None")
            ]
        )

        # Dual hazard
        dual_hazard = len(df[df["dual_hazard_flag"] == True])

        # Critical floods
        critical_floods = len(df[df["flood_severity"] == "Critical"])

        # Extreme risk (top 10 within filtered dataset)
        extreme_risk = len(df.nlargest(10, "overall_risk_score"))

        return {
            "total_active_alerts": total_alerts,
            "dual_hazard_count": dual_hazard,
            "critical_flood_count": critical_floods,
            "extreme_risk_count": extreme_risk,
        }

    def generate_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Generate alert entries from GeoJSON data."""
        alerts = []

        for idx, row in self.df.iterrows():
            district_id = row.get("district_id")
            district = row.get("district", "Unknown")
            state = row.get("state", "Unknown")
            flood_severity = row.get("flood_severity", "Low")
            heat_alert_tier = row.get("heat_alert_tier", "None")
            dual_hazard = row.get("dual_hazard_flag", False)

            # Critical Flood
            if flood_severity == "Critical":
                alerts.append({
                    "severity": "Extreme",
                    "type": "CRITICAL FLOOD",
                    "district": district,
                    "state": state,
                    "message": f"Water level exceeds danger threshold in {district}",
                    "district_id": district_id,
                })
            elif flood_severity == "High":
                alerts.append({
                    "severity": "High",
                    "type": "CRITICAL FLOOD",
                    "district": district,
                    "state": state,
                    "message": f"High flood risk in {district}",
                    "district_id": district_id,
                })

            # Heat Alert
            if heat_alert_tier == "Red":
                alerts.append({
                    "severity": "Extreme",
                    "type": "HEAT ALERT",
                    "district": district,
                    "state": state,
                    "message": f"Red heat alert active in {district}",
                    "district_id": district_id,
                })
            elif heat_alert_tier == "Orange":
                alerts.append({
                    "severity": "High",
                    "type": "HEAT ALERT",
                    "district": district,
                    "state": state,
                    "message": f"Orange heat alert in {district}",
                    "district_id": district_id,
                })

            # Dual Hazard
            if dual_hazard:
                alerts.append({
                    "severity": "Extreme",
                    "type": "DUAL HAZARD",
                    "district": district,
                    "state": state,
                    "message": f"Dual hazard risk (flood + heatwave) in {district}",
                    "district_id": district_id,
                })

        # Sort by severity
        severity_order = {"Extreme": 0, "High": 1, "Moderate": 2, "Low": 3}
        alerts.sort(key=lambda x: severity_order.get(x["severity"], 4))

        return alerts[:limit]

    def list_districts(
        self,
        disaster_type: str = "All",
        severity: str = "All",
        search: str = None,
    ) -> List[Dict[str, Any]]:
        """List all districts with optional filtering."""
        df = self._filter_districts(self.df, disaster_type, severity, search)
        return df.to_dict("records")

    def get_district(self, district_id: str) -> Optional[Dict[str, Any]]:
        """Get a single district by ID."""
        result = self.df[self.df["district_id"] == district_id]
        if result.empty:
            return None
        return result.iloc[0].to_dict()

    def get_districts_by_ids(self, district_ids: List[str]) -> List[Dict[str, Any]]:
        """Get multiple districts by IDs."""
        result = self.df[self.df["district_id"].isin(district_ids)]
        return result.to_dict("records")

    def get_map_geojson(
        self,
        disaster_type: str = "All",
        severity: str = "All",
        search: str = None,
    ) -> Dict[str, Any]:
        """Get filtered GeoJSON for map."""
        df = self._filter_districts(self.df, disaster_type, severity, search)
        gdf_filtered = self.gdf[self.gdf["district_id"].isin(df["district_id"])]
        return json.loads(gdf_filtered.to_json())
