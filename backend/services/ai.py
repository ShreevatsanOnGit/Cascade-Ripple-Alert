import os
import json
import urllib.request
import urllib.error
import logging
from config import settings

logger = logging.getLogger("ai_service")

def _rule_based_fallback(simulation_result: dict) -> dict:
    affected = len(simulation_result.get("affected_routes", []))
    stranded = len(simulation_result.get("stranded_nodes", []))
    impact = simulation_result.get("impact_score", 0.0)

    if impact == 0:
        narrative = f"The selected failure has limited network impact. No nodes are stranded, and the calculated impact score is {impact:.2f}."
        rec = "No immediate action required. The network retains sufficient redundancy."
    elif stranded > 0:
        narrative = f"The simulated failure resulted in an impact score of {impact:.2f}. This failure structurally isolates {stranded} nodes from essential services, and forces rerouting for {affected} other locations."
        rec = "Emergency dispatch required for stranded zones. Prioritize immediate structural repair to restore connectivity to isolated nodes."
    else:
        narrative = f"The simulated failure resulted in an impact score of {impact:.2f}. While no nodes are completely isolated, {affected} routes are experiencing delays due to forced rerouting."
        rec = "Deploy traffic management to alternate routes to alleviate congestion."

    return {
        "narrative": narrative,
        "recommendation": rec
    }

def generate_incident_brief(simulation_result: dict) -> dict:
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("No GEMINI_API_KEY found, falling back to rule-based summary.")
        return _rule_based_fallback(simulation_result)

    prompt = f"""You are an emergency infrastructure resilience analyst for a city disaster management operations center.
Analyze this simulated infrastructure network failure event data:
{json.dumps(simulation_result, indent=2)}

Guidelines:
- Reference the concrete numbers from the data (impact score, number of stranded nodes, affected routes).
- Explain the real-world operational consequence for emergency services and civilians (e.g. access to hospitals, rerouting delays).
- Tone: Crisp, professional, and actionable for city planners and emergency dispatchers.
- Return ONLY valid JSON in this exact structure:
{{
  "narrative": "3-4 sentence incident brief describing the failure and direct human impact.",
  "recommendation": "1-2 sentence high-priority tactical mitigation actions."
}}
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            result = json.loads(text)
            if "narrative" in result and "recommendation" in result:
                return result
    except Exception as e:
        logger.error(f"Gemini API generation error: {e}. Falling back to rule-based brief.")

    return _rule_based_fallback(simulation_result)
