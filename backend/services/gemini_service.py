"""
Gemini Service - Handles grounded AI queries with intent classification and deterministic filters.
"""

import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from gemini_round_robin import GeminiKeyManager

class GeminiService:
    def __init__(self):
        self.key_manager = None
        self.geo_service = None

    def initialize(self, geo_service=None):
        """Initialize key manager and geo_service reference on startup."""
        self.geo_service = geo_service
        try:
            self.key_manager = GeminiKeyManager(count=5)
            self.key_manager.check_all_keys()
            print("[OK] Gemini service initialized")
        except Exception as e:
            print(f"[WARNING] Gemini initialization failed: {e}")
            self.key_manager = None

    def classify_and_filter(self, question: str, districts: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]]]:
        """
        Step 1: Classify intent.
        Step 2: Extract entities & thresholds.
        Step 3: Run deterministic filtering directly on GeoJSON records.
        """
        q_lower = question.lower()
        intent = "General Inquiry"
        entities = {}
        filtered_districts = []

        # Find matching state or district in query (for cross-filtering)
        states = ["Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", 
                  "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", 
                  "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", 
                  "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", 
                  "Uttarakhand", "West Bengal", "Delhi", "Jammu and Kashmir", "Ladakh", "Puducherry"]
        
        matched_state = None
        for state in states:
            if state.lower() in q_lower:
                matched_state = state
                break

        matched_district = None
        for d in districts:
            dist_name = d.get("district", "").lower()
            if len(dist_name) > 3 and dist_name in q_lower:
                matched_district = d.get("district")
                break

        # 1. Cross Disaster Analysis
        # "Which districts are currently experiencing both a heatwave alert and an active flood risk?"
        if (any(k in q_lower for k in ["both", "dual", "simultaneous", "co-occurring", "concurrent", "double", "together"]) or
            (any(k in q_lower for k in ["flood", "water", "discharge"]) and any(k in q_lower for k in ["heat", "temp", "wave", "wbgt"]))):
            intent = "Cross Disaster Analysis"
            filtered_districts = [
                d for d in districts 
                if d.get("dual_hazard_flag") == True or 
                   (d.get("flood_severity") != "Low" and d.get("heat_alert_tier") not in ["None", "Normal"])
            ]
            
            # Apply state or district filters if mentioned
            if matched_state:
                entities["state"] = matched_state
                filtered_districts = [d for d in filtered_districts if d.get("state", "").lower() == matched_state.lower() or d.get("st_nm", "").lower() == matched_state.lower()]
            if matched_district:
                entities["district"] = matched_district
                filtered_districts = [d for d in filtered_districts if d.get("district", "").lower() == matched_district.lower()]
                
            return intent, entities, filtered_districts

        # 2. Threshold Filtering
        # "List all districts where water levels have exceeded the danger line by more than 1.5 meters."
        if any(k in q_lower for k in ["water level", "danger line", "danger level", "danger mark", "exceed", "exceeds", "exceeding", "above", "more than", ">"]):
            # Extract number
            match = re.search(r"(?:exceeded|exceeds|exceeding|exceed|above|by|level|of|than|more|>)\s*(\d+(?:\.\d+)?)", q_lower)
            if match:
                val = float(match.group(1))
                intent = "Threshold Filtering"
                entities = {"metric": "water_level_above_danger_m", "operator": ">", "value": val}
                filtered_districts = [d for d in districts if d.get("water_level_above_danger_m", 0.0) > val]
                
                # Apply state or district filters if mentioned
                if matched_state:
                    entities["state"] = matched_state
                    filtered_districts = [d for d in filtered_districts if d.get("state", "").lower() == matched_state.lower() or d.get("st_nm", "").lower() == matched_state.lower()]
                if matched_district:
                    entities["district"] = matched_district
                    filtered_districts = [d for d in filtered_districts if d.get("district", "").lower() == matched_district.lower()]
                    
                return intent, entities, filtered_districts

        # 3. Resource Optimization
        # "Identify which high-severity flood hotspots currently have zero response teams deployed."
        if any(k in q_lower for k in ["team", "responder", "deployment", "hotspot"]) and \
           any(k in q_lower for k in ["zero", "no", "0"]):
            intent = "Resource Optimization"
            filtered_districts = [
                d for d in districts 
                if (d.get("active_flood_hotspots", 0) > 0 or d.get("flood_severity") in ["Critical", "High"]) 
                and d.get("response_teams_deployed", 0) == 0
            ]
            
            # Apply state or district filters if mentioned
            if matched_state:
                entities["state"] = matched_state
                filtered_districts = [d for d in filtered_districts if d.get("state", "").lower() == matched_state.lower() or d.get("st_nm", "").lower() == matched_state.lower()]
            if matched_district:
                entities["district"] = matched_district
                filtered_districts = [d for d in filtered_districts if d.get("district", "").lower() == matched_district.lower()]
                
            return intent, entities, filtered_districts

        # 4. Risk Ranking
        if any(k in q_lower for k in ["highest-risk", "highest risk", "extreme risk", "rank", "top risk", "most vulnerable"]):
            intent = "Risk Ranking"
            sorted_districts = sorted(districts, key=lambda x: x.get("overall_risk_score", 0.0), reverse=True)
            
            # Apply state filter if mentioned
            if matched_state:
                entities["state"] = matched_state
                sorted_districts = [d for d in sorted_districts if d.get("state", "").lower() == matched_state.lower() or d.get("st_nm", "").lower() == matched_state.lower()]
                
            filtered_districts = sorted_districts[:10]
            return intent, entities, filtered_districts

        # 5. Operational Recommendation
        if any(k in q_lower for k in ["recommend", "priority", "priorities", "mitigation", "action", "deployment"]):
            intent = "Operational Recommendation"
            filtered_districts = [
                d for d in districts 
                if d.get("overall_risk_score", 0.0) > 50.0 or 
                   d.get("flood_severity") in ["Critical", "High"] or 
                   d.get("heat_alert_tier") in ["Yellow", "Orange", "Red"] or
                   d.get("dual_hazard_flag") == True
            ]
            
            # Apply state or district filters if mentioned
            if matched_state:
                entities["state"] = matched_state
                filtered_districts = [d for d in filtered_districts if d.get("state", "").lower() == matched_state.lower() or d.get("st_nm", "").lower() == matched_state.lower()]
            if matched_district:
                entities["district"] = matched_district
                filtered_districts = [d for d in filtered_districts if d.get("district", "").lower() == matched_district.lower()]
                
            return intent, entities, filtered_districts

        # 6. State Summary
        if matched_state:
            intent = "State Summary"
            entities = {"state": matched_state}
            filtered_districts = [
                d for d in districts 
                if d.get("state", "").lower() == matched_state.lower() or 
                   d.get("st_nm", "").lower() == matched_state.lower()
            ]
            return intent, entities, filtered_districts

        # 7. District Summary
        if matched_district:
            intent = "District Summary"
            entities = {"district": matched_district}
            filtered_districts = [d for d in districts if d.get("district", "").lower() == matched_district.lower()]
            return intent, entities, filtered_districts

        # Default fallback: return input list
        return intent, entities, districts

    def query(
        self,
        question: str,
        districts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Query with EOC grounded dataset using the three-tier failover:
        Tier 1: Gemini 2.5 Flash (Round Robin)
        Tier 2: Qwen 2.5 7B (HuggingFace Inference API with together provider)
        Tier 3: Rule-Based Engine (Deterministic synthesis)
        """
        # Step 1: Base list is master list if GeoService reference is loaded
        base_districts = districts
        if self.geo_service and self.geo_service.df is not None:
            base_districts = self.geo_service.list_districts(disaster_type="All")

        # Step 2: Run deterministic query classification and filter
        intent, entities, filtered = self.classify_and_filter(question, base_districts)
        
        # Sort by overall risk score descending to prioritize critical cases in the display limit
        filtered = sorted(filtered, key=lambda x: x.get("overall_risk_score", 0.0), reverse=True)
        
        print(f"[RULE ENGINE] Classified Intent: {intent}")
        print(f"[RULE ENGINE] Extracted Entities: {entities}")
        print(f"[RULE ENGINE] Filtered Records: {len(filtered)} districts matching query")

        # Format district data for display context
        display_limit = 40
        displayed_districts = filtered[:display_limit]

        formatted_districts = "\n".join([
            f"  - {d['district']} ({d.get('state') or d.get('st_nm') or 'N/A'}): "
            f"Flood Severity={d.get('flood_severity', 'N/A')}, "
            f"Water Level Above Danger={d.get('water_level_above_danger_m', 0.0)}m, "
            f"Active Flood Hotspots={d.get('active_flood_hotspots', 0)}, "
            f"Heat Alert Tier={d.get('heat_alert_tier', 'N/A')}, "
            f"Overall Risk Score={d.get('overall_risk_score', 'N/A')}, "
            f"Response Teams Deployed={d.get('response_teams_deployed', 0)}, "
            f"Dual Hazard={d.get('dual_hazard_flag', False)}"
            for d in displayed_districts
        ])

        # Build prompt
        grounding_prompt = f"""You are a Disaster Operations Copilot in an Emergency Command Center.

CRITICAL RULES:
1. You may ONLY answer queries using the supplied district records below.
2. Never invent facts, figures, or metrics.
3. Never use external knowledge or make inferences not supported by the data.
4. Never infer missing values or make predictions.
5. If requested information is not present in the supplied records, or if no matching records exist, you MUST respond exactly: "Information unavailable in current command center dataset."

SUPPLIED DISTRICT RECORDS ({len(filtered)} matching records):
{formatted_districts}

{f'(Showing top {display_limit} of {len(filtered)} matching records)' if len(filtered) > display_limit else ''}

METADATA CONTEXT:
- Classified Query Intent: {intent}
- Extracted Entities: {entities}
- Match Count: {len(filtered)}

USER QUESTION: {question}

INSTRUCTIONS:
1. State the classified intent and match count clearly at the beginning of your response.
2. Provide specific names, states, and metrics (e.g. water levels, risk scores, teams) of the relevant districts.
3. If no matching records exist in the supplied dataset, state exactly: "Information unavailable in current command center dataset."
4. Provide actionable operational insights prioritizing public safety and resource allocation (e.g. recommend response deployments).
5. Always explain your reasoning using only the district records.

Answer now:"""

        # TIER 1: Try ALL available Gemini keys before giving up
        if self.key_manager:
            from google import genai
            attempted = 0
            total_keys = len(self.key_manager.api_keys)
            while attempted < total_keys:
                api_key = None
                try:
                    api_key = self.key_manager.get_available_key()
                except RuntimeError:
                    # All keys exhausted / rate limited
                    print("[TIER 1] All Gemini keys exhausted. Moving to Tier 2.")
                    break
                try:
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=grounding_prompt
                    )
                    answer = response.text if response.text else ""
                    if self._is_valid_answer(answer):
                        print(f"[TIER 1 OK] Gemini answered ({len(answer)} chars)")
                        return {"success": True, "answer": answer}
                    else:
                        print(f"[TIER 1 WARN] Gemini returned empty/invalid response. Trying next key.")
                        attempted += 1
                        continue
                except Exception as e:
                    err = str(e)
                    print(f"[TIER 1 ERROR] Gemini key failed: {err[:120]}")
                    self.key_manager.mark_key_failed(api_key, err)
                    attempted += 1
                    # On 429 / quota exhausted try next key immediately
                    continue
        else:
            print("[TIER 1 SKIP] Key manager not initialized.")

        # TIER 2: Fallback to Qwen/Qwen2.5-7B-Instruct via HF Inference API
        print("[TIER 2] Attempting Qwen 2.5 7B via HuggingFace Inference API...")
        try:
            answer = self.query_qwen_fallback(grounding_prompt)
            if self._is_valid_answer(answer):
                print(f"[TIER 2 OK] Qwen answered ({len(answer)} chars)")
                return {"success": True, "answer": answer}
            else:
                print("[TIER 2 WARN] Qwen returned empty/invalid response. Moving to Tier 3.")
        except Exception as e:
            print(f"[TIER 2 ERROR] Qwen fallback failed: {str(e)[:120]}")

        # TIER 3: Deterministic Rule Engine — guaranteed response
        print("[TIER 3] Generating deterministic rule-based response...")
        try:
            answer = self.get_deterministic_rule_response(intent, entities, filtered)
            return {"success": True, "answer": answer}
        except Exception as e:
            print(f"[TIER 3 ERROR] Final fallback failed: {e}")
            return {
                "success": False,
                "error": "All AI tiers failed. Please try again shortly.",
            }

    def _is_valid_answer(self, answer: str) -> bool:
        """Returns True only if the answer is a non-empty, meaningful string."""
        if not answer or not isinstance(answer, str):
            return False
        stripped = answer.strip()
        if len(stripped) < 20:
            return False
        # Reject raw error/exception text passed as a response
        reject_prefixes = ("error", "exception", "traceback", "429", "503", "quota")
        if any(stripped.lower().startswith(p) for p in reject_prefixes):
            return False
        return True

    def query_qwen_fallback(self, grounding_prompt: str) -> str:
        """
        Query Qwen/Qwen2.5-7B-Instruct via Hugging Face Inference API using partner serverless together hardware.
        """
        import os
        from huggingface_hub import InferenceClient
        
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            raise ValueError("HF_TOKEN environment variable not set.")
            
        client = InferenceClient(
            provider="together",
            api_key=hf_token
        )
        
        print("[FALLBACK] Querying Qwen 2.5 7B via Hugging Face Inference API...")
        response = client.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=[
                {
                    "role": "user",
                    "content": grounding_prompt
                }
            ],
            max_tokens=800
        )
        return response.choices[0].message.content

    def get_deterministic_rule_response(self, intent: str, entities: dict, filtered: List[Dict[str, Any]]) -> str:
        """
        Final fallback: Generate a clean, structured text summary directly from filtered data without LLM.
        """
        total = len(filtered)
        if total == 0:
            return "**[RULE ENGINE RESPONSE]**\n\nInformation unavailable in current command center dataset."
            
        response = f"**[RULE-BASED EOC FALLBACK RESPONSE]**\n\n"
        response += f"**Operational Summary (Query Intent: {intent})**\n"
        response += f"Processed {total} matching district records in the current grounding scope.\n\n"
        
        # List top 5 priority districts
        response += "**Active Priorities:**\n"
        for d in filtered[:5]:
            state = d.get('state') or d.get('st_nm') or 'N/A'
            priority = "Critical" if d.get('overall_risk_score', 0) > 75 else "High" if d.get('overall_risk_score', 0) > 50 else "Moderate"
            response += f"- **{d['district']} ({state})**: Overall Risk = {d.get('overall_risk_score', 0.0):.1f} | Severity: Flood = {d.get('flood_severity', 'Low')}, Heatwave = {d.get('heat_alert_tier', 'None')} (Priority: {priority})\n"
            
        if total > 5:
            response += f"- *And {total - 5} other matching districts.*\n"
            
        # Add dynamic recommended actions based on criteria
        response += "\n**Standard Operating Procedures (SOP):**\n"
        criticals = [d for d in filtered if d.get('overall_risk_score', 0) > 75]
        if criticals:
            response += f"- **Evacuation Alert**: Initialize evacuation protocols in {len(criticals)} critical risk zones.\n"
        
        duals = [d for d in filtered if d.get('dual_hazard_flag')]
        if duals:
            response += f"- **Dual Hazard Coordination**: Initialize joint agency operations (flood rescue + heat relief) in {len(duals)} active dual-hazard districts.\n"
            
        zero_teams = [d for d in filtered if d.get('response_teams_deployed', 0) == 0 and d.get('overall_risk_score', 0) > 50]
        if zero_teams:
            response += f"- **Response Gaps**: Urgent deployment of emergency teams needed in {len(zero_teams)} high-risk districts with zero teams currently deployed.\n"
            
        response += "\n*Note: This is a deterministic rule-based operational synthesis generated because the primary (Gemini) and secondary (Qwen) AI models are currently offline.*"
        return response

