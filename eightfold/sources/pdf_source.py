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

DATE_LINE_RE = re.compile(
    r"(?i)(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|"
    r"[0-9]{4}).*?[-–—].*?(Present|Current|[0-9]{4}|[A-Za-z]{3,9}\s+[0-9]{4})"
)

JOB_TITLE_HINTS = {
    "intern", "engineer", "developer", "analyst", "manager", "associate",
    "consultant", "scientist", "lead", "specialist", "architect", "researcher",
    "trainee", "fellow", "designer", "administrator", "software", "data",
}

COMPANY_HINTS = {
    "pvt", "ltd", "inc", "corp", "llc", "llp", "company", "technologies",
    "solutions", "systems", "labs", "group", "studio", "consulting", "services",
}

NAME_BLACKLIST = {
    "skills", "skill", "experience", "education", "projects", "project",
    "certifications", "certification", "awards", "award", "summary",
    "objective", "community", "activities", "activity", "extracurricular",
    "extracirricular", "technical", "professional", "profile", "contact",
    "links", "link", "work", "internship", "internships", "achievements",
    "leadership", "languages", "languages & proficiency", "technical skills",
    "additional information", "additional",
}


def _looks_like_name_line(line):
    clean_line = re.sub(r"\s+", " ", line.strip())
    if len(clean_line) < 3:
        return False
    if _normalize_header(clean_line) is not None:
        return False
    if clean_line.lower() in ("resume", "cv", "curriculum vitae"):
        return False
    if "@" in clean_line or PHONE_RE.search(clean_line) or re.search(r'https?://|www\.', clean_line, re.IGNORECASE):
        return False
    if re.search(r'\d', clean_line):
        return False
    if any(token in clean_line.lower() for token in NAME_BLACKLIST):
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
    section_cutoff = len(lines)
    for idx, line in enumerate(lines):
        if _is_header_line(line):
            section_cutoff = idx
            break

    def _collect(search_lines, position_bonus_base):
        collected = []
        for idx, line in enumerate(search_lines):
            if _looks_like_name_line(line):
                score = 0
                clean_line = line.strip()
                if clean_line == clean_line.upper():
                    score += 1
                if len(clean_line.split()) in (2, 3):
                    score += 2
                if idx <= 3:
                    score += 1
                if not any(hint in clean_line.lower() for hint in LOCATION_HINTS):
                    score += 2
                if clean_line == clean_line.title():
                    score += 3
                score += max(position_bonus_base - idx, 0)
                collected.append((score, idx, clean_line))
        return collected

    candidates = _collect(lines[:section_cutoff], position_bonus_base=6)
    if not candidates:
        candidates = _collect(lines, position_bonus_base=3)

    if not candidates:
        return None

    candidates.sort(key=lambda item: (-item[0], item[1], -len(item[2]), item[2]))
    return candidates[0][2]


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


def _looks_like_date_line(line):
    return bool(DATE_LINE_RE.search(line or ""))


def _looks_like_job_title(line):
    text = re.sub(r"^[\s\u2022•·\-*]+", "", (line or "")).strip()
    if not text or _looks_like_date_line(text) or _is_header_line(text):
        return False
    lowered = text.casefold()
    return any(hint in lowered for hint in JOB_TITLE_HINTS)


def _looks_like_company_line(line):
    text = re.sub(r"^[\s\u2022•·\-*]+", "", (line or "")).strip()
    if not text or _looks_like_date_line(text) or _is_header_line(text):
        return False
    lowered = text.casefold()
    if any(hint in lowered for hint in COMPANY_HINTS):
        return True
    words = [w for w in re.split(r"\s+", text) if w]
    titleish_words = sum(1 for w in words if w[:1].isupper())
    return len(words) >= 2 and titleish_words >= max(2, len(words) - 1)


def _experience_block_to_evidence(block, source_id):
    if not block.get("company") and not block.get("title") and not block.get("summary"):
        return []

    summary = " ".join(block.get("summary", [])).strip() or None
    experience_value = {
        "company": block.get("company"),
        "title": block.get("title"),
        "start": block.get("start"),
        "end": block.get("end"),
        "summary": summary,
    }
    evidence = [Evidence("experience", experience_value, experience_value, source_id, "unstructured", "heuristic:experience_block")]

    if block.get("title"):
        evidence.append(Evidence("current_title", block["title"], block["title"], source_id, "unstructured", "heuristic:experience_block"))
    if block.get("company"):
        evidence.append(Evidence("current_company", block["company"], block["company"], source_id, "unstructured", "heuristic:experience_block"))

    return evidence


def _extract_experience_entries(exp_lines, source_id):
    entries = []
    block = {"company": None, "title": None, "start": None, "end": None, "summary": []}

    def flush_block():
        nonlocal block
        entries.extend(_experience_block_to_evidence(block, source_id))
        block = {"company": None, "title": None, "start": None, "end": None, "summary": []}

    for raw_line in exp_lines:
        line = re.sub(r"^[\s\u2022•·\-*]+", "", (raw_line or "")).strip()
        if not line:
            continue

        if _looks_like_date_line(line):
            date_text = line
            match = DATE_LINE_RE.search(date_text)
            if match:
                block["start"] = date_text.split(match.group(0), 1)[0].strip() or block.get("start")
                block["end"] = match.group(0).split("-", 1)[-1].strip() if "-" in match.group(0) or "–" in match.group(0) or "—" in match.group(0) else block.get("end")
            continue

        if _looks_like_company_line(line) and block.get("company") and (block.get("title") or block.get("summary")):
            flush_block()

        if block.get("company") is None and _looks_like_company_line(line):
            block["company"] = line
            continue

        if block.get("title") is None and _looks_like_job_title(line):
            block["title"] = line
            continue

        if any(hint in line.casefold() for hint in LOCATION_HINTS):
            continue

        if line.startswith("•") or line.startswith("-") or line.startswith("*") or block.get("title") or block.get("company"):
            block["summary"].append(line)

    flush_block()
    return entries


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
            cleaned_chunk = re.sub(r"^[\s\u2022•·\-*]+", "", chunk).strip().rstrip(".,;:")
            if ":" in cleaned_chunk:
                _, after = cleaned_chunk.split(":", 1)
                after = after.strip()
                if after:
                    cleaned_chunk = after
            raw_skills = re.split(r'[,|•·\-\*]', cleaned_chunk)
            for s in raw_skills:
                s = re.sub(r"^[\s\u2022•·\-*]+", "", s).strip().rstrip(".,;:")
                if len(s) > 1:
                    evidence.append(Evidence("skills", s, s, source_id, "unstructured",
                                              "heuristic:skills_multi_split"))

    exp_lines = _find_section(lines, "experience")
    if exp_lines:
        evidence.extend(_extract_experience_entries(exp_lines, source_id))

    edu_lines = _find_section(lines, "education")
    if edu_lines:
        for line in edu_lines:
            line = line.strip()
            # Simple heuristic for degree/university
            if any(degree in line.lower() for degree in ["b.s", "bachelor", "master", "m.s", "ph.d", "doctorate", "university", "college", "institute"]):
                evidence.append(Evidence("education", line, line, source_id, "unstructured", "heuristic:education_keyword"))

    return SourceResult(source_id, "unstructured", ok=True, evidence=evidence)
