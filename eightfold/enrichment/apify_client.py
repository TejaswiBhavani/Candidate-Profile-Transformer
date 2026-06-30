"""
APIFY enrichment client — scrapes LinkedIn and GitHub profiles using
the official apify-client package and APIFY cloud actors.

This is an *enrichment* layer only: it adds supplemental Evidence
objects to the pipeline but never replaces the deterministic extractors.
If the APIFY_API_TOKEN env var is missing or empty, or if the API call
fails for any reason, this module returns an empty result and the
pipeline continues without it.
"""

import os
from typing import Any, Dict, List, Optional
from apify_client import ApifyClient

from ..models import Evidence

# Community actor IDs
LINKEDIN_ACTOR = "harvestapi/linkedin-profile-scraper"
GITHUB_ACTOR = "saswave/github-profile-scraper"


def _get_token() -> Optional[str]:
    token = os.environ.get("APIFY_API_TOKEN", "").strip()
    return token if token else None


def enrich_linkedin(linkedin_url: str) -> Dict[str, Any]:
    """Scrapes a LinkedIn profile using harvestapi/linkedin-profile-scraper.
    Returns empty dict on failure."""
    token = _get_token()
    if not token or not linkedin_url:
        return {}

    try:
        client = ApifyClient(token)
        run_input = {
            "profileScraperMode": "Profile details no email ($4 per 1k)",
            "queries": [linkedin_url]
        }
        run = client.actor(LINKEDIN_ACTOR).call(run_input=run_input)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        if items:
            return items[0]
        return {}
    except Exception as e:
        print(f"Apify LinkedIn scraper failed: {e}")
        return {}


def enrich_github(github_url: str) -> Dict[str, Any]:
    """Scrapes a GitHub profile using saswave/github-profile-scraper.
    Returns empty dict on failure."""
    token = _get_token()
    if not token or not github_url:
        return {}

    try:
        client = ApifyClient(token)
        run_input = {
            "repo_link": "",
            "peoples_links": [github_url]
        }
        run = client.actor(GITHUB_ACTOR).call(run_input=run_input)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        if items:
            return items[0]
        return {}
    except Exception as e:
        print(f"Apify GitHub scraper failed: {e}")
        return {}


def _parse_experience(exp_list: Any) -> List[Dict[str, Any]]:
    parsed = []
    if not isinstance(exp_list, list):
        return parsed
    for item in exp_list:
        if not isinstance(item, dict):
            continue
        company = item.get("companyName") or item.get("company")
        title = item.get("title")
        start = item.get("start") or item.get("startDate")
        end = item.get("end") or item.get("endDate")
        summary = item.get("description") or item.get("summary")
        if company or title:
            parsed.append({
                "company": company,
                "title": title,
                "start": start,
                "end": end,
                "summary": summary
            })
    return parsed


def _parse_education(edu_list: Any) -> List[Dict[str, Any]]:
    parsed = []
    if not isinstance(edu_list, list):
        return parsed
    for item in edu_list:
        if not isinstance(item, dict):
            continue
        school = item.get("schoolName") or item.get("school") or item.get("university") or item.get("college")
        degree = item.get("degreeName") or item.get("degree") or item.get("qualification")
        field = item.get("fieldOfStudy") or item.get("field")
        start = item.get("start") or item.get("startDate")
        end = item.get("end") or item.get("endDate")
        
        # Build description or label
        edu_str = ""
        if degree:
            edu_str += degree
        if field:
            edu_str += f" in {field}"
        if school:
            edu_str += f" at {school}"
        if start or end:
            edu_str += f" ({start or ''} - {end or ''})"
            
        if edu_str.strip():
            parsed.append({
                "school": school,
                "degree": degree,
                "field": field,
                "start": start,
                "end": end,
                "description": edu_str.strip()
            })
    return parsed


def build_enrichment_evidence(
    linkedin_data: Dict[str, Any],
    github_data: Dict[str, Any],
) -> List[Evidence]:
    """Converts APIFY enrichment data into Evidence objects that can be
    fed back into the canonical merge engine."""
    evidence: List[Evidence] = []

    # LinkedIn evidence
    if linkedin_data:
        src = "linkedin_apify"
        if linkedin_data.get("fullName"):
            evidence.append(Evidence(
                "full_name", linkedin_data["fullName"], linkedin_data["fullName"],
                src, "semistructured", "apify:linkedin_fullname",
            ))
        if linkedin_data.get("headline"):
            evidence.append(Evidence(
                "headline", linkedin_data["headline"], linkedin_data["headline"],
                src, "semistructured", "apify:linkedin_headline",
            ))
        if linkedin_data.get("about"):
            evidence.append(Evidence(
                "extra_attributes", {"linkedin_about": linkedin_data["about"]}, linkedin_data["about"],
                src, "semistructured", "apify:linkedin_about",
            ))
        if linkedin_data.get("location"):
            evidence.append(Evidence(
                "location", linkedin_data["location"], linkedin_data["location"],
                src, "semistructured", "apify:linkedin_location",
            ))
        
        # Skills
        for skill in linkedin_data.get("skills", []):
            skill_name = None
            if isinstance(skill, str) and skill.strip():
                skill_name = skill.strip()
            elif isinstance(skill, dict) and skill.get("name"):
                skill_name = skill["name"].strip()
            if skill_name and len(skill_name) <= 45:
                evidence.append(Evidence(
                    "skills", skill_name, skill_name,
                    src, "semistructured", "apify:linkedin_skills",
                ))

        # Experience
        exp = _parse_experience(linkedin_data.get("experience"))
        if exp:
            evidence.append(Evidence(
                "experience", exp, exp,
                src, "semistructured", "apify:linkedin_experience"
            ))
            # Also pull current company and title from top experience if available
            top = exp[0]
            if top.get("company"):
                evidence.append(Evidence(
                    "current_company", top["company"], top["company"],
                    src, "semistructured", "apify:linkedin_experience_company"
                ))
            if top.get("title"):
                evidence.append(Evidence(
                    "current_title", top["title"], top["title"],
                    src, "semistructured", "apify:linkedin_experience_title"
                ))

        # Education
        edu = _parse_education(linkedin_data.get("education"))
        if edu:
            evidence.append(Evidence(
                "education", edu, edu,
                src, "semistructured", "apify:linkedin_education"
            ))

        # Additional LinkedIn fields
        for field in ("certifications", "projects", "languages"):
            if linkedin_data.get(field):
                evidence.append(Evidence(
                    "extra_attributes", {f"linkedin_{field}": linkedin_data[field]}, linkedin_data[field],
                    src, "semistructured", f"apify:linkedin_{field}"
                ))

    # GitHub evidence
    if github_data:
        src = "github_apify"
        gh_name = github_data.get("name")
        if gh_name and "http" not in gh_name.lower() and "github.com" not in gh_name.lower():
            evidence.append(Evidence(
                "full_name", gh_name, gh_name,
                src, "semistructured", "apify:github_name",
            ))
        if github_data.get("bio"):
            evidence.append(Evidence(
                "headline", github_data["bio"], github_data["bio"],
                src, "semistructured", "apify:github_bio",
            ))
        if github_data.get("location"):
            evidence.append(Evidence(
                "location", github_data["location"], github_data["location"],
                src, "semistructured", "apify:github_location",
            ))
        
        # Map useful metadata fields into extra_attributes
        extra_fields = ["username", "followers", "organization", "websites", "linkedin", "pinned_repos", "achievements", "readme"]
        for field in extra_fields:
            if github_data.get(field):
                evidence.append(Evidence(
                    "extra_attributes", {f"github_{field}": github_data[field]}, github_data[field],
                    src, "semistructured", f"apify:github_{field}"
                ))

    return evidence


def enrich(discovered_urls: Dict[str, Optional[str]]) -> Dict[str, Any]:
    """Top-level enrichment function. Takes discovered URLs, calls APIFY,
    returns a dict with enrichment results and Evidence objects.
    
    Always safe to call — returns empty results if no token or on failure."""
    linkedin_data = {}
    github_data = {}
    evidence: List[Evidence] = []
    status = "skipped"

    token = _get_token()
    if not token:
        return {
            "status": status,
            "linkedin": linkedin_data,
            "github": github_data,
            "evidence": evidence,
        }

    status = "completed"

    if discovered_urls.get("linkedin"):
        try:
            linkedin_data = enrich_linkedin(discovered_urls["linkedin"])
        except Exception:
            linkedin_data = {}

    if discovered_urls.get("github"):
        try:
            github_data = enrich_github(discovered_urls["github"])
        except Exception:
            github_data = {}

    evidence = build_enrichment_evidence(linkedin_data, github_data)

    return {
        "status": status,
        "linkedin": linkedin_data,
        "github": github_data,
        "evidence": evidence,
    }
