"""Structured/semi-structured source: JSON profile export (e.g. a
LinkedIn-style export). Tolerant of a few common key spellings since
exports from different tools/platforms vary."""

import json
import os

from ..models import Evidence, SourceResult

KEY_ALIASES = {
    "full_name": ("full_name", "name", "fullName"),
    "emails": ("email", "email_address", "emailAddress"),
    "phones": ("phone", "phone_number", "phoneNumber"),
    "current_company": ("company", "current_company", "employer"),
    "current_title": ("position", "title", "current_title", "headline"),
}


def extract(path: str, source_id: str = None) -> SourceResult:
    source_id = source_id or os.path.basename(path)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return SourceResult(source_id, "semistructured", ok=False, error="file not found")
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        return SourceResult(source_id, "semistructured", ok=False, error=f"invalid JSON: {e}")

    if not isinstance(data, dict):
        return SourceResult(source_id, "semistructured", ok=False,
                             error="expected a JSON object at the top level")

    evidence = []
    for canonical_field, aliases in KEY_ALIASES.items():
        for alias in aliases:
            if alias in data and str(data[alias]).strip():
                raw = data[alias]
                evidence.append(Evidence(
                    field_name=canonical_field,
                    value=raw,
                    raw_value=raw,
                    source_id=source_id,
                    source_type="semistructured",
                    method=f"json_key:{alias}",
                ))
                break

    skills = data.get("skills")
    if isinstance(skills, list):
        for s in skills:
            if str(s).strip():
                evidence.append(Evidence(
                    field_name="skills",
                    value=s,
                    raw_value=s,
                    source_id=source_id,
                    source_type="semistructured",
                    method="json_key:skills[]",
                ))

    return SourceResult(source_id, "semistructured", ok=True, evidence=evidence)
