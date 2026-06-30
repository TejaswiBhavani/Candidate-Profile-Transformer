"""
Projection layer — turns the rich internal canonical profile into
whatever shape a runtime config asks for.

This module deliberately knows NOTHING about how values were merged or
scored; it just reads three parallel views of the canonical profile
(values / confidences / sources) by path, and applies config-level
concerns: field selection, renaming, per-field normalize hints, the
include_confidence toggle, and the on_missing policy. That's the "clean
separation between canonical record and projection layer" the brief
asks for — the engine doesn't change when a config changes.
"""

import re

PATH_SEGMENT_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)(\[(\d*)\])?$")


class ProjectionError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("; ".join(errors))


def flatten_canonical(canonical):
    """Builds three parallel dict views of the canonical profile, all
    addressable by the same canonical paths (e.g. 'emails[0]',
    'skills[].name'): values, per-value confidence, and per-value
    source list."""
    values = {
        "candidate_id": canonical["candidate_id"],
        "full_name": canonical["full_name"]["value"],
        "emails": [e["value"] for e in canonical["emails"]],
        "phones": [p["value"] for p in canonical["phones"]],
        "current_company": canonical["current_company"]["value"],
        "current_title": canonical["current_title"]["value"],
        "department": canonical.get("department", {}).get("value"),
        "manager_name": canonical.get("manager_name", {}).get("value"),
        "employment_status": canonical.get("employment_status", {}).get("value"),
        "location": canonical.get("location", {}).get("value"),
        "headline": canonical.get("headline", {}).get("value"),
        "years_experience": canonical.get("years_experience", {}).get("value"),
        "extra_attributes": canonical.get("extra_attributes", {}),
        "skills": [{"name": s["name"]} for s in canonical["skills"]],
        "overall_confidence": canonical["overall_confidence"],
    }
    confidences = {
        "candidate_id": None,
        "full_name": canonical["full_name"]["confidence"],
        "emails": [e["confidence"] for e in canonical["emails"]],
        "phones": [p["confidence"] for p in canonical["phones"]],
        "current_company": canonical["current_company"]["confidence"],
        "current_title": canonical["current_title"]["confidence"],
        "department": canonical.get("department", {}).get("confidence"),
        "manager_name": canonical.get("manager_name", {}).get("confidence"),
        "employment_status": canonical.get("employment_status", {}).get("confidence"),
        "location": canonical.get("location", {}).get("confidence"),
        "headline": canonical.get("headline", {}).get("confidence"),
        "years_experience": canonical.get("years_experience", {}).get("confidence"),
        "extra_attributes": None,
        "skills": [{"name": s["confidence"]} for s in canonical["skills"]],
        "overall_confidence": None,
    }
    sources = {
        "candidate_id": None,
        "full_name": canonical["full_name"]["sources"],
        "emails": [e["sources"] for e in canonical["emails"]],
        "phones": [p["sources"] for p in canonical["phones"]],
        "current_company": canonical["current_company"]["sources"],
        "current_title": canonical["current_title"]["sources"],
        "department": canonical.get("department", {}).get("sources"),
        "manager_name": canonical.get("manager_name", {}).get("sources"),
        "employment_status": canonical.get("employment_status", {}).get("sources"),
        "location": canonical.get("location", {}).get("sources"),
        "headline": canonical.get("headline", {}).get("sources"),
        "years_experience": canonical.get("years_experience", {}).get("sources"),
        "extra_attributes": None,
        "skills": [{"name": s["sources"]} for s in canonical["skills"]],
        "overall_confidence": None,
    }
    methods = {
        "candidate_id": None,
        "full_name": canonical["full_name"].get("methods", []),
        "emails": [e.get("methods", []) for e in canonical["emails"]],
        "phones": [p.get("methods", []) for p in canonical["phones"]],
        "current_company": canonical["current_company"].get("methods", []),
        "current_title": canonical["current_title"].get("methods", []),
        "department": canonical.get("department", {}).get("methods", []),
        "manager_name": canonical.get("manager_name", {}).get("methods", []),
        "employment_status": canonical.get("employment_status", {}).get("methods", []),
        "location": canonical.get("location", {}).get("methods", []),
        "headline": canonical.get("headline", {}).get("methods", []),
        "years_experience": canonical.get("years_experience", {}).get("methods", []),
        "extra_attributes": None,
        "skills": [{"name": s.get("methods", [])} for s in canonical["skills"]],
        "overall_confidence": None,
    }
    return values, confidences, sources, methods


def resolve_path(data, path):
    """Resolves a canonical path like 'full_name', 'emails[0]', or
    'skills[].name' against a flattened view. Returns (value, is_missing).
    A wildcard segment ('[]') makes the result a list even if empty."""
    segments = path.split(".")
    current = [data]
    is_multi = False
    for seg in segments:
        m = PATH_SEGMENT_RE.match(seg)
        if not m:
            raise ValueError(f"invalid path segment '{seg}' in '{path}'")
        key, bracket, idx = m.groups()
        nxt = []
        for item in current:
            if not isinstance(item, dict) or key not in item:
                continue
            val = item[key]
            if bracket is None:
                nxt.append(val)
            elif idx == "":
                is_multi = True
                if isinstance(val, list):
                    nxt.extend(val)
            else:
                i = int(idx)
                if isinstance(val, list) and -len(val) <= i < len(val):
                    nxt.append(val[i])
        current = nxt
    if is_multi:
        return current, False
    if not current:
        return None, True
    return current[0], False


def _apply_normalize_hint(value, hint):
    """Projection-level re-formatting requests. Canonical values are
    already normalized to one representation, so most hints here are
    confirmations/no-ops; 'national' is the one genuine re-format
    (strips the E.164 country code for display)."""
    if value is None or hint is None:
        return value
    if hint in ("E164", "canonical"):
        return value
    if hint == "national":
        if isinstance(value, str) and value.startswith("+"):
            digits = value[1:]
            return digits[-10:] if len(digits) > 10 else digits
        return value
    if hint == "upper":
        return value.upper() if isinstance(value, str) else value
    if hint == "lower":
        return value.lower() if isinstance(value, str) else value
    if hint == "title":
        return value.title() if isinstance(value, str) else value
    return value  # unknown hint: pass through rather than fail the run


def project(canonical, config):
    """Returns the projected output dict for the given config. Raises
    ProjectionError if any required field is missing and on_missing=='error'."""
    values, confidences, sources, methods = flatten_canonical(canonical)
    include_confidence = bool(config.get("include_confidence", False))
    include_provenance = bool(config.get("include_provenance", False))
    on_missing = config.get("on_missing", "null")
    if on_missing not in ("null", "omit", "error"):
        raise ValueError(f"invalid on_missing policy: {on_missing!r}")

    out = {}
    errors = []
    
    # Store accumulated provenance here
    global_provenance = []

    for field_cfg in config.get("fields", []):
        out_key = field_cfg["path"]
        source_path = field_cfg.get("from", out_key)
        required = bool(field_cfg.get("required", False))

        try:
            value, missing = resolve_path(values, source_path)
        except ValueError as e:
            errors.append(str(e))
            continue

        if not missing:
            normalize_hint = field_cfg.get("normalize")
            if isinstance(value, list):
                value = [_apply_normalize_hint(v, normalize_hint) for v in value]
            else:
                value = _apply_normalize_hint(value, normalize_hint)
            # treat empty list / empty string as "present but empty", not missing,
            # EXCEPT when the field is required, in which case we hold it to the
            # same on_missing policy as a truly absent value.
            if value in (None, [], "") and required:
                missing = True

        if missing:
            if on_missing == "error":
                errors.append(f"field '{out_key}' (from '{source_path}') is missing")
                continue
            if on_missing == "omit":
                continue
            out[out_key] = None
            continue

        out[out_key] = value
        
        if include_confidence:
            conf_val, _ = resolve_path(confidences, source_path)
            out[f"{out_key}_confidence"] = conf_val
            
        if include_provenance:
            src_val, _ = resolve_path(sources, source_path)
            meth_val, _ = resolve_path(methods, source_path)
            out[f"{out_key}_sources"] = src_val
            out[f"{out_key}_methods"] = meth_val
            
            # Zip and add
            if isinstance(src_val, list) and isinstance(meth_val, list):
                for s, m in zip(src_val, meth_val):
                    entry = {"field": out_key, "source": s, "method": m}
                    if entry not in global_provenance:
                        global_provenance.append(entry)
            elif src_val and meth_val:
                entry = {"field": out_key, "source": src_val, "method": meth_val}
                if entry not in global_provenance:
                    global_provenance.append(entry)

    if errors:
        raise ProjectionError(errors)
        
    if include_provenance:
        out["provenance"] = global_provenance
        
    return out


# ---- Default schema projection (no config supplied) ----

DEFAULT_FIELDS_CONFIG = {
    "fields": [
        {"path": "candidate_id"},
        {"path": "full_name"},
        {"path": "emails"},
        {"path": "phones"},
        {"path": "current_company"},
        {"path": "current_title"},
        {"path": "department"},
        {"path": "manager_name"},
        {"path": "employment_status"},
        {"path": "extra_attributes"}
    ],
    "include_confidence": False,
    "on_missing": "null",
}


def project_default(canonical):
    """The default output schema: flat scalar/list fields plus skills
    and experience mappings."""
    out = project(canonical, DEFAULT_FIELDS_CONFIG)
    
    # Enforce strict schema keys (null or empty arrays for missing data)
    out["location"] = canonical.get("location", {}).get("value")
    out["headline"] = canonical.get("headline", {}).get("value")
    
    y_exp = canonical.get("years_experience", {}).get("value")
    if y_exp is not None:
        try:
            out["years_experience"] = float(y_exp)
        except (ValueError, TypeError):
            out["years_experience"] = y_exp
    else:
        out["years_experience"] = None
        
    out["links"] = canonical.get("links") or None
    out["education"] = canonical.get("education") or []
    
    # Skills mapping
    out["skills"] = [
        {"name": s["name"], "confidence": s["confidence"], "sources": s["sources"]}
        for s in canonical["skills"]
    ]
    
    # Experience mapping
    exp_list = canonical.get("experience") or []
    if exp_list:
        out["experience"] = exp_list
    else:
        out["experience"] = []
        if canonical["current_company"]["value"] or canonical["current_title"]["value"]:
            out["experience"].append({
                "company": canonical["current_company"]["value"],
                "title": canonical["current_title"]["value"],
                "start": None,
                "end": None,
                "summary": None
            })
        
    out["overall_confidence"] = canonical["overall_confidence"]
    
    # Build Top-Level Provenance as requested
    provenance = []
    seen_prov = set()
    
    # helper for adding to provenance
    def add_prov(field_name, metadata_obj):
        if not metadata_obj: return
        sources = metadata_obj.get("sources", [])
        methods = metadata_obj.get("methods", [])
        
        def _add_single(s, m):
            key = (field_name, s, m)
            if key not in seen_prov:
                seen_prov.add(key)
                provenance.append({"field": field_name, "source": s, "method": m})

        # Sometimes sources is a list of lists if we fetched from a multi-value source
        if isinstance(sources, list) and len(sources) > 0 and isinstance(sources[0], list):
            for s_list, m_list in zip(sources, methods):
                for s, m in zip(s_list, m_list):
                     _add_single(s, m)
        else:
            if isinstance(sources, list) and isinstance(methods, list):
                for s, m in zip(sources, methods):
                    _add_single(s, m)
            elif sources and methods:
                _add_single(sources, methods)
                
    add_prov("full_name", canonical["full_name"])
    add_prov("current_company", canonical["current_company"])
    add_prov("current_title", canonical["current_title"])
    add_prov("location", canonical.get("location"))
    add_prov("headline", canonical.get("headline"))
    add_prov("years_experience", canonical.get("years_experience"))
    
    for e in canonical["emails"]: add_prov("emails", e)
    for p in canonical["phones"]: add_prov("phones", p)
    for s in canonical["skills"]: add_prov("skills", s)
    
    out["provenance"] = provenance
    
    return out
