"""
Top-level pipeline orchestrator.

run() is the single entry point both the CLI and tests use. It's
intentionally a thin coordinator: extraction lives in sources/, merging
in merge.py/canonical.py, projection in project.py, validation in
validate.py. This file just sequences them and makes sure a bad source
degrades gracefully instead of raising.

Enhanced with URL discovery, APIFY enrichment, and Gemini insights.
"""

import os

from .models import SourceResult
from .sources import csv_source, json_source, pdf_source
from .canonical import build_canonical_profile
from .project import project, project_default, ProjectionError
from .validate import validate, ValidationError, DEFAULT_OUTPUT_SCHEMA, build_schema_from_config, validate_runtime_config
from .url_discovery import discover_urls
from .enrichment.apify_client import enrich as apify_enrich
from .enrichment.gemini_insights import generate_insights

EXTRACTORS = {
    ".csv": csv_source.extract,
    ".json": json_source.extract,
    ".pdf": pdf_source.extract,
    ".txt": csv_source.extract,
}


class PipelineResult:
    def __init__(self, output, canonical, warnings, validation_errors=None,
                 discovered_urls=None, enrichment_status=None, gemini_insights=None):
        self.output = output
        self.canonical = canonical
        self.warnings = warnings
        self.validation_errors = validation_errors or []
        self.discovered_urls = discovered_urls or {}
        self.enrichment_status = enrichment_status or "skipped"
        self.gemini_insights = gemini_insights
        self.candidate_outputs = None

    @property
    def ok(self):
        return not self.validation_errors


def _finalize_source_results(source_results, source_ids_in_order, config=None):
    canonical = build_canonical_profile(source_results, source_order=source_ids_in_order)

    warnings = []
    validation_errors = []
    output = None

    try:
        if config is None:
            output = project_default(canonical)
            schema = DEFAULT_OUTPUT_SCHEMA
        else:
            validate_runtime_config(config)
            output = project(canonical, config)
            schema = build_schema_from_config(config)
        validate(output, schema)
    except ProjectionError as e:
        validation_errors.extend(f"projection: {err}" for err in e.errors)
    except ValidationError as e:
        validation_errors.extend(f"validation: {err}" for err in e.errors)

    if output:
        has_email = bool(output.get("emails"))
        has_phone = bool(output.get("phones"))
        has_skills = bool(output.get("skills"))
        if not (has_email or has_phone or has_skills):
            warnings.append("Profile incomplete: missing email, phone, skills")

    for sr in source_results:
        if not sr.ok:
            warnings.append(f"source '{sr.source_id}' skipped: {sr.error}")
        if getattr(sr, "warnings", None):
            warnings.extend(sr.warnings)

    for skipped in canonical["_meta"]["skipped_evidence"]:
        warnings.append(
            f"dropped unparseable {skipped['field']} value "
            f"{skipped['raw_value']!r} from {skipped['source_id']}"
        )

    for field_name in ("full_name", "current_company", "current_title"):
        field = canonical[field_name]
        if field.get("conflict"):
            warnings.append(
                f"conflict on '{field_name}': resolved to {field['value']!r} "
                f"(other values seen: {field['conflicting_values']})"
            )

    return canonical, output, warnings, validation_errors


def _extract_one(path):
    source_id = os.path.basename(path)
    ext = os.path.splitext(path)[1].lower()
    extractor = EXTRACTORS.get(ext)
    if extractor is None:
        return SourceResult(source_id, "unknown", ok=False,
                             error=f"unsupported file type '{ext}'")
    try:
        return extractor(path, source_id=source_id)
    except Exception as e:  # last-resort guard: a single bad source must never crash the whole run
        return SourceResult(source_id, "unknown", ok=False, error=f"unexpected error: {e}")


def _collect_raw_texts(source_paths, source_results):
    """Collect raw text from all sources for URL discovery."""
    texts = []
    for path, sr in zip(source_paths, source_results):
        if not sr.ok:
            continue
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == ".pdf":
                import pdfplumber
                with pdfplumber.open(path) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            texts.append(t)
            elif ext in (".txt", ".csv"):
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    texts.append(f.read())
            elif ext == ".json":
                import json
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                texts.append(json.dumps(data))
        except Exception:
            continue
    return texts


def run(source_paths, config=None):
    """source_paths: list of file paths (csv/json/pdf).
    config: dict (parsed runtime config) or None for the default schema.
    Returns a PipelineResult. Never raises for source-level problems —
    only raises for programmer errors (e.g. malformed config path syntax)."""
    source_ids_in_order = [os.path.basename(p) for p in source_paths]
    source_results = [_extract_one(p) for p in source_paths]

    candidate_outputs = []
    batch_csv_paths = [p for p in source_paths if p.lower().endswith(".csv")]
    if len(batch_csv_paths) == 1 and len(source_paths) == 1:
        batch_results, csv_warnings, csv_error = csv_source.extract_rows(batch_csv_paths[0], source_id=os.path.basename(batch_csv_paths[0]))
        if csv_error:
            return PipelineResult(
                output=None,
                canonical={"_meta": {"skipped_evidence": []}},
                warnings=csv_warnings or [],
                validation_errors=[csv_error.error or "CSV error"],
            )
        if len(batch_results) > 1:
            for row_result in batch_results:
                canonical, output, warnings, validation_errors = _finalize_source_results(
                    [row_result],
                    [row_result.source_id],
                    config=config,
                )
                candidate_outputs.append({
                    "source_id": row_result.source_id,
                    "canonical": canonical,
                    "output": output,
                    "warnings": (csv_warnings or []) + warnings,
                    "validation_errors": validation_errors,
                })
            canonical, output, warnings, validation_errors = _finalize_source_results(
                [batch_results[0]],
                [batch_results[0].source_id],
                config=config,
            )
            result = PipelineResult(output, canonical, (csv_warnings or []) + warnings, validation_errors)
            result.candidate_outputs = candidate_outputs
            return result

    # --- URL Discovery ---
    raw_texts = _collect_raw_texts(source_paths, source_results)
    discovered_urls = discover_urls(raw_texts)

    # Convert discovered URLs into Evidence so they merge into canonical["links"]
    url_evidence = []
    from .models import Evidence
    for link_type, url in discovered_urls.items():
        if url:
            url_evidence.append(Evidence(
                field_name="links",
                value={link_type: url},
                raw_value={link_type: url},
                source_id="url_discovery",
                source_type="unstructured",
                method="regex:url_discovery"
            ))
    if url_evidence:
        url_sr = SourceResult(
            source_id="url_discovery",
            source_type="unstructured",
            ok=True,
            evidence=url_evidence,
        )
        source_results.append(url_sr)
        source_ids_in_order.append("url_discovery")

    # --- APIFY Enrichment ---
    enrichment_result = apify_enrich(discovered_urls)
    enrichment_status = enrichment_result.get("status", "skipped")

    # If APIFY returned extra evidence, inject it as a synthetic source
    apify_evidence = enrichment_result.get("evidence", [])
    if apify_evidence:
        apify_sr = SourceResult(
            source_id="apify_enrichment",
            source_type="semistructured",
            ok=True,
            evidence=apify_evidence,
        )
        source_results.append(apify_sr)
        source_ids_in_order.append("apify_enrichment")

    # --- Canonical Build ---
    canonical = build_canonical_profile(source_results, source_order=source_ids_in_order)

    warnings = []
    if discovered_urls.get("linkedin") and not enrichment_result.get("linkedin"):
        warnings.append("LinkedIn enrichment unavailable")
    if discovered_urls.get("github") and not enrichment_result.get("github"):
        warnings.append("GitHub enrichment unavailable")
    for sr in source_results:
        if not sr.ok:
            warnings.append(f"source '{sr.source_id}' skipped: {sr.error}")
        if getattr(sr, "warnings", None):
            warnings.extend(sr.warnings)
    for skipped in canonical["_meta"]["skipped_evidence"]:
        warnings.append(
            f"dropped unparseable {skipped['field']} value "
            f"{skipped['raw_value']!r} from {skipped['source_id']}"
        )
    for f in ("full_name", "current_company", "current_title"):
        field = canonical[f]
        if field.get("conflict"):
            warnings.append(
                f"conflict on '{f}': resolved to {field['value']!r} "
                f"(other values seen: {field['conflicting_values']})"
            )

    validation_errors = []
    output = None
    try:
        if config is None:
            output = project_default(canonical)
            schema = DEFAULT_OUTPUT_SCHEMA
        else:
            validate_runtime_config(config)
            output = project(canonical, config)
            schema = build_schema_from_config(config)
        validate(output, schema)
    except ProjectionError as e:
        validation_errors.extend(f"projection: {err}" for err in e.errors)
    except ValidationError as e:
        validation_errors.extend(f"validation: {err}" for err in e.errors)

    if output:
        has_email = bool(output.get("emails"))
        has_phone = bool(output.get("phones"))
        has_skills = bool(output.get("skills"))
        if not (has_email or has_phone or has_skills):
            warnings.append("Profile incomplete: missing email, phone, skills")

    # --- Gemini Insights ---
    gemini_insights = None
    if output:
        gemini_insights = generate_insights(output)
    result = PipelineResult(
        output=output,
        canonical=canonical,
        warnings=warnings,
        validation_errors=validation_errors,
        discovered_urls=discovered_urls,
        enrichment_status=enrichment_status,
        gemini_insights=gemini_insights,
    )
    if candidate_outputs:
        result.candidate_outputs = candidate_outputs
    return result
