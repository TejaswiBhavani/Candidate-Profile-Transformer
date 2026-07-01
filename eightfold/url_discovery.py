"""
URL Discovery — extracts LinkedIn, GitHub, and portfolio URLs from
raw text pulled out of uploaded candidate documents.

This runs after extraction but before APIFY enrichment. Found URLs
are passed to the enrichment layer for scraping. Users never manually
enter URLs — they are always auto-discovered from the source files.
"""

import re
from typing import Dict, List, Optional

# Patterns for common profile URLs
LINKEDIN_RE = re.compile(
    r'https?://(?:www\.)?linkedin\.com/in/[\w\-%.]+/?',
    re.IGNORECASE,
)
GITHUB_RE = re.compile(
    r'https?://(?:www\.)?github\.com/[\w\-]+/?',
    re.IGNORECASE,
)
PORTFOLIO_RE = re.compile(
    r'https?://(?!(?:www\.)?(?:linkedin|github|google|facebook|twitter|instagram|youtube)\.com)'
    r'[\w\-]+\.[\w\-]+(?:\.[\w\-]+)*(?:/[\w\-./]*)?',
    re.IGNORECASE,
)


def _compact(text: str) -> str:
    return re.sub(r'\s+', '', text)


def _normalize_linkedin_path(path: str) -> Optional[str]:
    path = path.strip("/.,!?;:")
    if not path:
        return None

    segments = [segment for segment in path.split("/") if segment]
    if not segments:
        return None

    first = segments[0].casefold()
    if first in {"in", "company", "jobs", "school", "feed", "search", "learning", "pulse", "posts", "events"}:
        if first == "in" and len(segments) >= 2:
            return f"https://linkedin.com/in/{segments[1]}"
        return None

    # Resume URLs often omit the /in/ segment and only carry the public identifier.
    return f"https://linkedin.com/in/{segments[0]}"


def discover_urls(texts: List[str]) -> Dict[str, Optional[str]]:
    """Scans a list of raw text blobs (one per source file) and returns
    the first LinkedIn, GitHub, and portfolio URL found.

    Returns:
        {
            "linkedin": "https://linkedin.com/in/..." or None,
            "github": "https://github.com/..." or None,
            "portfolio": "https://example.dev" or None,
        }
    """
    combined = "\n".join(texts)
    compact = _compact(combined)

    linkedin = None
    # Match full linkedin URL first. PDFs often insert whitespace between
    # the domain and path segments, so we also search a compacted copy.
    m = re.search(r'(?:https?://)?(?:www\.)?linkedin\.com\s*/\s*in\s*/\s*([\w\-%.]+)', combined, re.IGNORECASE)
    if m:
        linkedin = "https://linkedin.com/in/" + m.group(1).rstrip("/.,!?;:")
    else:
        # Match label-based pattern: linkedin: johndoe
        m = re.search(r'linkedin\s*[:/]\s*(?:in/)?([\w\-%.]+)', combined, re.IGNORECASE)
        if m:
            linkedin = "https://linkedin.com/in/" + m.group(1).rstrip("/.,!?;:")
        else:
            m = re.search(r'(?:https?://)?(?:www\.)?linkedin\.com\s*/\s*([A-Za-z0-9_.%-]+)', combined, re.IGNORECASE)
            if m:
                normalized = _normalize_linkedin_path(m.group(1))
                if normalized:
                    linkedin = normalized

    github = None
    # Match full github URL first. PDFs often insert whitespace between
    # the domain and path segments, so we also search a compacted copy.
    m = re.search(r'(?:https?://)?(?:www\.)?github\.com\s*/\s*([\w\-%.]+)', combined, re.IGNORECASE)
    if m:
        github = "https://github.com/" + m.group(1).rstrip("/.,!?;:")
    else:
        # Match label-based pattern: github: @johndoe
        m = re.search(r'github\s*[:/]\s*@?([\w\-%.]+)', combined, re.IGNORECASE)
        if m:
            github = "https://github.com/" + m.group(1).rstrip("/.,!?;:")
        else:
            m = re.search(r'(?:https?://)?(?:www\.)?github\.com\s*/\s*([A-Za-z0-9_.%-]+)', combined, re.IGNORECASE)
            if m:
                github = "https://github.com/" + m.group(1).rstrip("/.,!?;:")

    portfolio = None
    # Portfolio: look for https:// or www.
    for m in re.finditer(r'(?:https?://|www\.)(?!(?:www\.)?(?:linkedin|github|google|facebook|twitter|instagram|youtube)\.com)[\w\-]+\.[\w\-]+(?:\.[\w\-]+)*(?:/[\w\-./]*)?', combined, re.IGNORECASE):
        candidate = m.group(0).rstrip("/")
        if not candidate.startswith("http"):
            candidate = "https://" + candidate
            
        # Skip if it's actually linkedin or github that slipped through
        if "linkedin.com" in candidate.lower() or "github.com" in candidate.lower():
            continue
        # Skip common non-portfolio domains
        skip_domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
                        "fonts.googleapis.com", "cdnjs.cloudflare.com"]
        if any(d in candidate.lower() for d in skip_domains):
            continue
        portfolio = candidate
        break

    return {
        "linkedin": linkedin,
        "github": github,
        "portfolio": portfolio,
    }
