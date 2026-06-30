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

    linkedin = None
    # Match full linkedin URL first
    m = re.search(r'(?:https?://)?(?:www\.)?linkedin\.com/in/([\w\-%.]+)', combined, re.IGNORECASE)
    if m:
        linkedin = "https://linkedin.com/in/" + m.group(1).rstrip("/.,!?;:")
    else:
        # Match label-based pattern: linkedin: johndoe
        m = re.search(r'linkedin\s*[:/]\s*(?:in/)?([\w\-%.]+)', combined, re.IGNORECASE)
        if m:
            linkedin = "https://linkedin.com/in/" + m.group(1).rstrip("/.,!?;:")

    github = None
    # Match full github URL first
    m = re.search(r'(?:https?://)?(?:www\.)?github\.com/([\w\-%.]+)', combined, re.IGNORECASE)
    if m:
        github = "https://github.com/" + m.group(1).rstrip("/.,!?;:")
    else:
        # Match label-based pattern: github: @johndoe
        m = re.search(r'github\s*[:/]\s*@?([\w\-%.]+)', combined, re.IGNORECASE)
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
