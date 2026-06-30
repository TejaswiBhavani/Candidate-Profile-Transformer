"""
Gemini Insights — generates recruiter-facing AI analysis from the
finalized canonical profile.

CRITICAL DESIGN RULE: Gemini is an *enrichment layer* only. It receives
the already-merged, already-scored canonical profile and generates
human-readable summaries and recommendations. It NEVER invents factual
profile fields (name, email, skills, etc.) — those come exclusively
from the deterministic extraction pipeline.

If the GEMINI_API_KEY env var is missing or the API call fails, this
module returns None and the pipeline continues without AI insights.
"""

import json
import os
from typing import Any, Dict, Optional


def _get_api_key() -> Optional[str]:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return key if key else None


SYSTEM_PROMPT = """You are a senior technical recruiter assistant. You will receive a candidate's profile data that has been deterministically extracted and merged from multiple sources (resumes, CSVs, LinkedIn, GitHub).

Your job is to analyze the profile and generate recruiter insights. You must:
1. ONLY reference information that exists in the provided profile data
2. NEVER invent facts, skills, or experiences not present in the data
3. Be honest about gaps and missing information
4. Provide actionable insights for recruiters

Respond with a JSON object (no markdown, no code fences) containing exactly these keys:
{
    "summary": "2-3 sentence professional summary of this candidate",
    "strengths": ["strength 1", "strength 2", ...],
    "recommended_roles": ["role 1", "role 2", ...],
    "missing_information": ["missing item 1", "missing item 2", ...],
    "potential_concerns": ["concern 1", ...]
}"""


def generate_insights(profile_output: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Sends the finalized profile to Gemini and returns recruiter insights.
    Returns None on any failure (missing key, API error, parse error)."""
    api_key = _get_api_key()
    if not api_key:
        return None

    try:
        from google import genai

        client = genai.Client(api_key=api_key)

        # Build a clean prompt with only the profile data
        profile_text = json.dumps(profile_output, indent=2, default=str)
        user_prompt = f"Analyze this candidate profile and generate recruiter insights:\n\n{profile_text}"

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=user_prompt,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "temperature": 0.3,
                "response_mime_type": "application/json",
            },
        )

        # Parse the JSON response
        raw_text = response.text.strip()
        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            raw_text = "\n".join(lines)

        insights = json.loads(raw_text)

        # Validate expected keys exist
        expected_keys = {"summary", "strengths", "recommended_roles",
                         "missing_information", "potential_concerns"}
        if not expected_keys.issubset(set(insights.keys())):
            # If some keys are differently named, map them or try fallback
            mapped_insights = {
                "summary": insights.get("summary") or insights.get("recruiter_summary") or "",
                "strengths": insights.get("strengths") or [],
                "recommended_roles": insights.get("recommended_roles") or [],
                "missing_information": insights.get("missing_information") or insights.get("missing_info") or [],
                "potential_concerns": insights.get("potential_concerns") or insights.get("concerns") or []
            }
            return mapped_insights

        return insights

    except Exception:
        # Any failure: import error, API error, JSON parse error, etc.
        # The pipeline continues without AI insights.
        return None
