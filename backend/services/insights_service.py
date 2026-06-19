"""
Insights Service - Handles district narrative insights from JSONL.
"""

import json
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any

class InsightsService:
    def __init__(self):
        self.artifacts_dir = Path(__file__).parent.parent.parent / "artifacts"
        self.insights_df = None

    def initialize(self):
        """Load insights on startup."""
        self._load_insights()

    def _load_insights(self):
        """Load district_insights_final.jsonl."""
        insights_path = self.artifacts_dir / "district_insights_final.jsonl"
        if not insights_path.exists():
            print(f"[WARNING] Missing: {insights_path}")
            self.insights_df = pd.DataFrame()
            return
        
        insights_data = []
        with open(insights_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    insights_data.append(json.loads(line))
        
        self.insights_df = pd.DataFrame(insights_data) if insights_data else pd.DataFrame()
        print(f"[OK] Loaded {len(self.insights_df)} district insights")

    def get_insights(self, district_id: str) -> Optional[Dict[str, Any]]:
        """Get insights for a single district."""
        if self.insights_df.empty:
            return None
        
        result = self.insights_df[self.insights_df["district_id"] == district_id]
        if result.empty:
            return None
        
        return result.iloc[0].to_dict()
