"""Unstructured source: a free-text resume PDF.

There's no schema here, so extraction is regex/heuristic-based instead
of key-lookup-based like the structured sources. Each heuristic is kept
narrow and documented so failures are predictable rather than silently
wrong, and every extractor is wrapped so a malformed/corrupt/scanned PDF
degrades to an empty, error-flagged SourceResult instead of crashing the
whole pipeline run.
"""

import os
import re

from ..models import Evidence, SourceResult

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(\+?\d[\d \-]{7,}\d)")


def _extract_text(path):
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        pages_text = [p.extract_text() or "" for p in pdf.pages]
    return "\n".join(pages_text)


# Resumes are often laid out without blank-line separators between
# sections once PDF text extraction collapses whitespace, so we stop a
# section's content at the next recognized header line, not just a
# blank line.
SECTION_ALIASES = {
    "skills": ["skills", "technical skills", "technnical skills", "core competencies", "expertise", "technologies"],
    "experience": ["experience", "work experience", "professional experience", "employment history", "work history"],
    "education": ["education", "academic background", "qualifications"],
    "summary": ["summary", "objective", "professional summary"],
    "projects": ["projects", "personal projects"],
    "certifications": ["certifications", "licenses", "certificates"],
    "awards": ["honors & awards", "honors", "awards", "honors and awards"],
    "community": ["community", "activities"]
}

def _normalize_header(line):
    """Returns the canonical section name if found, else None."""
    clean_line = re.sub(r'\s+', '', line.strip().rstrip(":").strip().lower())
    for canonical, aliases in SECTION_ALIASES.items():
        for alias in aliases:
            if clean_line == re.sub(r'\s+', '', alias.lower()):
                return canonical
    return None

def _is_header_line(line):
    return _normalize_header(line) is not None


LOCATION_HINTS = {
    "india", "remote", "hyderabad", "telangana", "bangalore", "bengaluru",
    "delhi", "mumbai", "pune", "chennai", "karnataka", "maharashtra",
    "andhra pradesh", "india", "usa", "united states", "california",
}


def _looks_like_name_line(line):
    clean_line = re.sub(r"\s+", " ", line.strip())
    if len(clean_line) < 3:
        return False
    if clean_line.lower() in ("resume", "cv", "curriculum vitae"):
        return False
    if "@" in clean_line or PHONE_RE.search(clean_line) or re.search(r'https?://|www\.', clean_line, re.IGNORECASE):
        return False
    if re.search(r'\d', clean_line):
        return False
    if "," in clean_line and any(hint in clean_line.lower() for hint in LOCATION_HINTS):
        return False
    words = clean_line.split()
    if len(words) < 2 or len(words) > 5:
        return False
    if sum(1 for w in words if re.search(r'[A-Za-z]', w)) != len(words):
        return False
    # Prefer title case or all-caps display names.
    alpha_chars = [ch for ch in clean_line if ch.isalpha()]
    if not alpha_chars:
        return False
    upper_ratio = sum(1 for ch in alpha_chars if ch.isupper()) / len(alpha_chars)
    if upper_ratio >= 0.6:
        return True
    if clean_line == clean_line.title():
        return True
    return False


def _pick_name_line(lines):
    candidates = []
    for idx, line in enumerate(lines[:10]):
        if _looks_like_name_line(line):
            score = 0
            clean_line = line.strip()
            if clean_line == clean_line.upper():
                score += 3
            if len(clean_line.split()) in (2, 3):
                score += 2
            if idx <= 3:
                score += 1
            if not any(hint in clean_line.lower() for hint in LOCATION_HINTS):
                score += 2
            candidates.append((score, clean_line))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], -len(item[1]), item[1]))
    return candidates[0][1]


def _find_section(lines, canonical_name):
    """Returns the lines immediately following a section header (e.g.
    'Skills:'), stopping at the next known section header.
    Returns [] if the header isn't found."""
    for i, line in enumerate(lines):
        if _normalize_header(line) == canonical_name:
            collected = []
            for nxt in lines[i + 1:]:
                # Stop if we hit another header
                if _is_header_line(nxt):
                    break
                # But do NOT stop on empty lines; just skip them
                if nxt.strip():
                    collected.append(nxt.strip())
            return collected
    return []


def extract(path: str, source_id: str = None) -> SourceResult:
    source_id = source_id or os.path.basename(path)
    try:
        text = _extract_text(path)
    except FileNotFoundError:
        return SourceResult(source_id, "unstructured", ok=False, error="file not found")
    except Exception as e:  # pdfplumber/pypdf can raise a variety of error types on corrupt files
        return SourceResult(source_id, "unstructured", ok=False, error=f"could not read PDF: {e}")

    if not text.strip():
        return SourceResult(source_id, "unstructured", ok=False,
                             error="PDF produced no extractable text (likely scanned/image-only)")

    lines = [l for l in text.split("\n")]
    non_empty_lines = [l for l in lines if l.strip()]
    evidence = []

    # Name: look for the best candidate in the top of the document.
    name_line = _pick_name_line(non_empty_lines)
    if name_line:
        evidence.append(Evidence("full_name", name_line, name_line, source_id, "unstructured",
                                 "heuristic:smart_first_line"))

    email_match = EMAIL_RE.search(text)
    if email_match:
        raw = email_match.group(0)
        evidence.append(Evidence("emails", raw, raw, source_id, "unstructured", "regex:email"))

    phone_match = PHONE_RE.search(text)
    if phone_match:
        raw = phone_match.group(0).strip()
        evidence.append(Evidence("phones", raw, raw, source_id, "unstructured", "regex:phone"))

    skill_lines = _find_section(lines, "skills")
    if skill_lines:
        for chunk in skill_lines:
            raw_skills = re.split(r'[,|•·\-\*]', chunk)
            for s in raw_skills:
                s = s.strip()
                if len(s) > 1:
                    evidence.append(Evidence("skills", s, s, source_id, "unstructured",
                                              "heuristic:skills_multi_split"))

    exp_lines = _find_section(lines, "experience")
    if exp_lines:
        DATE_RANGE_RE = re.compile(r"(?i)(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|[0-9]{4}).*?[-–].*?(Present|Current|[0-9]{4})")
        
        for i, line in enumerate(exp_lines):
            date_m = DATE_RANGE_RE.search(line)
            if date_m:
                raw_date = date_m.group(0).strip()
                evidence.append(Evidence("experience_dates", raw_date, raw_date, source_id, 
                                         "unstructured", "regex:date_anchor"))
                
                if "present" in line.lower() or "current" in line.lower():
                    # Extract title and company from the preceding line if possible
                    if i > 0:
                        role_line = exp_lines[i-1]
                        parts = [p.strip() for p in re.split(r'[|\-,]', role_line) if p.strip()]
                        if len(parts) >= 2:
                            title_raw, company_raw = parts[0], parts[1]
                        else:
                            at_parts = re.split(r'(?i)\s+at\s+', role_line, maxsplit=1)
                            if len(at_parts) == 2:
                                title_raw, company_raw = at_parts[0].strip(), at_parts[1].strip()
                            else:
                                title_raw = company_raw = parts[0]
                            
                        evidence.append(Evidence("current_title", title_raw, title_raw, source_id, 
                                                 "unstructured", "heuristic:anchored_role"))
                        evidence.append(Evidence("current_company", company_raw, company_raw, source_id, 
                                                 "unstructured", "heuristic:anchored_role"))
                    break # Usually the top role is current

    edu_lines = _find_section(lines, "education")
    if edu_lines:
        for line in edu_lines:
            line = line.strip()
            # Simple heuristic for degree/university
            if any(degree in line.lower() for degree in ["b.s", "bachelor", "master", "m.s", "ph.d", "doctorate", "university", "college", "institute"]):
                evidence.append(Evidence("education", line, line, source_id, "unstructured", "heuristic:education_keyword"))

    return SourceResult(source_id, "unstructured", ok=True, evidence=evidence)
