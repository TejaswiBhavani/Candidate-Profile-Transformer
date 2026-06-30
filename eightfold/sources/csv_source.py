"""Structured source: recruiter-style CSV (one row per candidate)."""

import csv
import os
import re

from ..models import Evidence, SourceResult

# canonical_field -> tuple of acceptable column-header aliases (normalized: alphanumeric lowercase)
COLUMN_ALIASES = {
    "full_name": ("employeename", "name", "candidatename", "fullname"),
    "emails": ("email", "emailaddress", "primaryemail"),
    "phones": ("phone", "phonenumber", "mobile", "contactnumber"),
    "current_company": ("currentcompany", "company", "employer"),
    "current_title": ("position", "jobtitle", "role", "currenttitle", "title", "designation"),
    "department": ("department",),
    "manager_name": ("managername",),
    "employment_status": ("employmentstatus",),
    "skills": ("skills", "skill", "technologies", "techstack"),
}

def _normalize_header(header: str) -> str:
    if not header:
        return ""
    return re.sub(r'[^a-z0-9]', '', header.strip().lower())



def extract(path: str, source_id: str = None) -> SourceResult:
    source_id = source_id or os.path.basename(path)
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            sample = f.read(2048)
            f.seek(0)
            
            # Use sniffer to detect tab/csv properly
            try:
                dialect = csv.Sniffer().sniff(sample)
                if dialect.delimiter not in (",", "\t", ";", "|"):
                    dialect = "excel"
            except csv.Error:
                dialect = "excel"  # Fallback

            # Force all columns to be read strictly as strings
            reader = csv.DictReader(f, dialect=dialect, quoting=csv.QUOTE_MINIMAL)
            if reader.fieldnames is None:
                return SourceResult(source_id, "structured", ok=False,
                                     error="CSV has no header row")
            # map original header to normalized header
            header_lookup = {h: _normalize_header(h) for h in reader.fieldnames if h}
            rows = list(reader)
    except FileNotFoundError:
        return SourceResult(source_id, "structured", ok=False, error="file not found")
    except (OSError, csv.Error, UnicodeDecodeError) as e:
        return SourceResult(source_id, "structured", ok=False, error=f"unreadable CSV: {e}")

    if not rows:
        return SourceResult(source_id, "structured", ok=False, error="CSV has no data rows")

    warnings = []
    if len(rows) > 1:
        warnings.append(f"CSV contains {len(rows)} rows; defaulting to the first row.")

    row = rows[0]
    evidence = []
    
    # Reverse mapping for faster lookup
    normalized_to_canonical = {}
    for canonical_field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            normalized_to_canonical[alias] = canonical_field

    for original_col, normalized_col in header_lookup.items():
        val = str(row.get(original_col, "")).strip()
        if not val:
            continue
        
        if normalized_col in normalized_to_canonical:
            canonical_field = normalized_to_canonical[normalized_col]
            
            if canonical_field == "skills":
                # Split by comma, pipe, or semicolon
                raw_skills = re.split(r'[,|;]', val)
                for s in raw_skills:
                    s_clean = s.strip()
                    if s_clean:
                        evidence.append(Evidence(
                            field_name="skills",
                            value=s_clean,
                            raw_value=s_clean,
                            source_id=source_id,
                            source_type="structured",
                            method=f"csv_column:{original_col}",
                        ))
            else:
                evidence.append(Evidence(
                    field_name=canonical_field,
                    value=val,
                    raw_value=val,
                    source_id=source_id,
                    source_type="structured",
                    method=f"csv_column:{original_col}",
                ))
        else:
            # Dynamic discovery / extra_attributes
            evidence.append(Evidence(
                field_name="extra_attributes",
                value={original_col: val},
                raw_value={original_col: val},
                source_id=source_id,
                source_type="structured",
                method=f"csv_column:{original_col}",
            ))

    return SourceResult(source_id, "structured", ok=True, warnings=warnings, evidence=evidence)
