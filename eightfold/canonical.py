"""
Builds the internal canonical profile from a list of SourceResult objects.

This is the boundary the brief asks for: everything above this module
(sources/, normalize.py) only knows how to read one source at a time;
everything below it (project.py) only knows how to read the canonical
profile and a config. Nothing here knows about output schemas, and
nothing in project.py knows how merging/confidence works. That
separation is what lets the runtime config reshape output without any
changes to the engine.
"""

import hashlib
from collections import defaultdict

from .normalize import normalize_evidence
from .merge import merge_single_valued, merge_emails_or_phones, merge_skills

SINGLE_VALUED_FIELDS = ["full_name", "current_company", "current_title", "department", "manager_name", "employment_status"]
MULTI_VALUED_SIMPLE_FIELDS = ["emails", "phones"]


def _candidate_id(full_name_field, emails_field, phones_field):
    if emails_field["value"]:
        basis = "email:" + emails_field["value"]
    elif phones_field["value"]:
        basis = "phone:" + phones_field["value"]
    elif full_name_field["value"]:
        basis = "name:" + full_name_field["value"].casefold()
    else:
        basis = "unknown"
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:10]
    return f"cand_{digest}"


def build_canonical_profile(source_results, source_order=None):
    """source_results: list[SourceResult] (already extracted, NOT yet normalized).
    source_order: list[str] of source_ids in the order they were passed on
    the CLI, used as a deterministic tiebreaker downstream. Defaults to
    the order source_results were given in.
    Returns the canonical profile dict."""
    source_order = source_order or [sr.source_id for sr in source_results]

    sources_used, sources_failed = [], []
    by_field = defaultdict(list)
    skipped_evidence = []

    for sr in source_results:
        if not sr.ok:
            sources_failed.append({"source_id": sr.source_id, "error": sr.error})
            continue
        sources_used.append(sr.source_id)
        for ev in sr.evidence:
            normalized = normalize_evidence(ev)
            if normalized.value is None:
                skipped_evidence.append({
                    "field": ev.field_name, "raw_value": ev.raw_value,
                    "source_id": ev.source_id, "reason": "failed normalization",
                })
                continue
            by_field[ev.field_name].append(normalized)

    canonical = {}
    for f in SINGLE_VALUED_FIELDS:
        canonical[f] = merge_single_valued(f, by_field.get(f, []), source_order)
    for f in MULTI_VALUED_SIMPLE_FIELDS:
        canonical[f] = merge_emails_or_phones(f, by_field.get(f, []), source_order)
    canonical["skills"] = merge_skills(by_field.get("skills", []), source_order)

    # Accumulate extra_attributes
    canonical["extra_attributes"] = {}
    for ev in by_field.get("extra_attributes", []):
        for k, v in ev.value.items():
            if k not in canonical["extra_attributes"]:
                canonical["extra_attributes"][k] = v

    # experience dates: not central to the brief's example schema and only
    # captured as supporting fields for current_title/current_company
    # (which are merged above). We deliberately don't build a full job
    # history / timeline reconciliation — see README "Descoped" section.

    candidate_id = _candidate_id(canonical["full_name"],
                                  {"value": canonical["emails"][0]["value"] if canonical["emails"] else None},
                                  {"value": canonical["phones"][0]["value"] if canonical["phones"] else None})

    has_name = bool(canonical["full_name"]["value"])
    has_title = bool(canonical["current_title"]["value"])
    has_contact = bool(canonical["emails"] or canonical["phones"])
    
    if has_name and has_title and has_contact:
        overall_confidence = 0.9
    elif has_name and has_title:
        overall_confidence = 0.6
    elif has_name:
        overall_confidence = 0.3
    else:
        overall_confidence = 0.1

    return {
        "candidate_id": candidate_id,
        "full_name": canonical["full_name"],
        "emails": canonical["emails"],
        "phones": canonical["phones"],
        "current_company": canonical["current_company"],
        "current_title": canonical["current_title"],
        "department": canonical["department"],
        "manager_name": canonical["manager_name"],
        "employment_status": canonical["employment_status"],
        "skills": canonical["skills"],
        "extra_attributes": canonical["extra_attributes"],
        "overall_confidence": overall_confidence,
        "_meta": {
            "sources_used": sources_used,
            "sources_failed": sources_failed,
            "skipped_evidence": skipped_evidence,
        },
    }
