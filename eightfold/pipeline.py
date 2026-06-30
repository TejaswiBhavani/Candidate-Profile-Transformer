"""
Top-level pipeline orchestrator.

run() is the single entry point both the CLI and tests use. It's
intentionally a thin coordinator: extraction lives in sources/, merging
in merge.py/canonical.py, projection in project.py, validation in
validate.py. This file just sequences them and makes sure a bad source
degrades gracefully instead of raising.
"""

import os

from .models import SourceResult
from .sources import csv_source, json_source, pdf_source
from .canonical import build_canonical_profile
from .project import project, project_default, ProjectionError
from .validate import validate, ValidationError, DEFAULT_OUTPUT_SCHEMA, build_schema_from_config, validate_runtime_config

EXTRACTORS = {
    ".csv": csv_source.extract,
    ".json": json_source.extract,
    ".pdf": pdf_source.extract,
    ".txt": csv_source.extract,
}


class PipelineResult:
    def __init__(self, output, canonical, warnings, validation_errors=None):
        self.output = output
        self.canonical = canonical
        self.warnings = warnings
        self.validation_errors = validation_errors or []

    @property
    def ok(self):
        return not self.validation_errors


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


def run(source_paths, config=None):
    """source_paths: list of file paths (csv/json/pdf).
    config: dict (parsed runtime config) or None for the default schema.
    Returns a PipelineResult. Never raises for source-level problems —
    only raises for programmer errors (e.g. malformed config path syntax)."""
    source_ids_in_order = [os.path.basename(p) for p in source_paths]
    source_results = [_extract_one(p) for p in source_paths]

    canonical = build_canonical_profile(source_results, source_order=source_ids_in_order)

    warnings = []
    for sr in source_results:
        if not sr.ok:
            warnings.append(f"source '{sr.source_id}' skipped: {sr.error}")
        if hasattr(sr, 'warnings') and sr.warnings:
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

    return PipelineResult(output=output, canonical=canonical, warnings=warnings,
                           validation_errors=validation_errors)
