"""
A minimal, hand-rolled JSON-shape validator.

We don't have network access in this environment to install the
`jsonschema` package, so this implements just the subset of JSON Schema
this project actually needs: type checking (string/number/boolean/array/
object/null), `required`, and `items` for arrays of a single scalar
type. This is called out as a deliberate scope cut in the design doc —
swapping in real `jsonschema` later is a drop-in change since the schema
dicts here use the same `type`/`properties`/`required` shape.
"""


class ValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("; ".join(errors))


_PY_TYPES = {
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _check_type(value, expected_type, path, errors):
    if expected_type == "null":
        if value is not None:
            errors.append(f"{path}: expected null, got {type(value).__name__}")
        return
    if value is None:
        return  # nullability is handled by `required`, not `type`
    py_type = _PY_TYPES.get(expected_type)
    if py_type is None:
        return  # unknown declared type: skip rather than fail the run
    if expected_type == "boolean" and isinstance(value, bool):
        return
    if expected_type in ("number", "integer") and isinstance(value, bool):
        errors.append(f"{path}: expected {expected_type}, got boolean")
        return
    if not isinstance(value, py_type):
        errors.append(f"{path}: expected {expected_type}, got {type(value).__name__}")


def validate(data, schema, path="$"):
    errors = []
    _validate_node(data, schema, path, errors)
    if errors:
        raise ValidationError(errors)
    return True


def _validate_node(data, schema, path, errors):
    expected_type = schema.get("type")
    if expected_type:
        _check_type(data, expected_type, path, errors)

    if expected_type == "object" and isinstance(data, dict):
        for req in schema.get("required", []):
            if req not in data or data[req] is None:
                errors.append(f"{path}: missing required field '{req}'")
        for key, sub_schema in schema.get("properties", {}).items():
            if key in data:
                _validate_node(data[key], sub_schema, f"{path}.{key}", errors)

    if expected_type == "array" and isinstance(data, list):
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(data):
                _validate_node(item, item_schema, f"{path}[{i}]", errors)


# ---- Default output schema ----

DEFAULT_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["candidate_id", "full_name", "overall_confidence"],
    "properties": {
        "candidate_id": {"type": "string"},
        "full_name": {"type": "string"},
        "emails": {"type": "array", "items": {"type": "string"}},
        "phones": {"type": "array", "items": {"type": "string"}},
        "current_company": {"type": "string"},
        "current_title": {"type": "string"},
        "department": {"type": "string"},
        "manager_name": {"type": "string"},
        "employment_status": {"type": "string"},
        "extra_attributes": {"type": "object"},
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "confidence", "sources"],
                "properties": {
                    "name": {"type": "string"},
                    "confidence": {"type": "number"},
                    "sources": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "overall_confidence": {"type": "number"},
    },
}

_CONFIG_TYPE_MAP = {
    "string": "string",
    "string[]": "array",
    "number": "number",
    "boolean": "boolean",
}

_ALLOWED_ON_MISSING = {"null", "omit", "error"}
_ALLOWED_NORMALIZE = {"E164", "canonical", "national", "upper", "lower", "title"}


def build_schema_from_config(config):
    """Builds a JSON-Schema-shaped dict from a runtime projection config,
    used to validate that config's output. Fields without a declared
    `type` aren't type-checked (we still check required-ness)."""
    properties = {}
    required = []
    for field_cfg in config.get("fields", []):
        key = field_cfg["path"]
        declared = field_cfg.get("type")
        schema_type = _CONFIG_TYPE_MAP.get(declared)
        if schema_type == "array":
            properties[key] = {"type": "array", "items": {"type": "string"}}
        elif schema_type:
            properties[key] = {"type": schema_type}
        else:
            properties[key] = {}
        if field_cfg.get("required") and config.get("on_missing") != "omit":
            required.append(key)
    return {"type": "object", "properties": properties, "required": required}


def validate_runtime_config(config):
    errors = []
    if not isinstance(config, dict):
        raise ValidationError(["config must be a JSON object"])

    fields = config.get("fields")
    if not isinstance(fields, list):
        errors.append("config.fields must be an array")
        fields = []

    if "include_confidence" in config and not isinstance(config["include_confidence"], bool):
        errors.append("config.include_confidence must be a boolean")
    if "include_provenance" in config and not isinstance(config["include_provenance"], bool):
        errors.append("config.include_provenance must be a boolean")

    on_missing = config.get("on_missing", "null")
    if on_missing not in _ALLOWED_ON_MISSING:
        errors.append(f"config.on_missing must be one of {sorted(_ALLOWED_ON_MISSING)!r}")

    for i, field_cfg in enumerate(fields):
        if not isinstance(field_cfg, dict):
            errors.append(f"config.fields[{i}] must be an object")
            continue
        path = field_cfg.get("path")
        if not isinstance(path, str) or not path.strip():
            errors.append(f"config.fields[{i}].path must be a non-empty string")
        if "from" in field_cfg and not isinstance(field_cfg["from"], str):
            errors.append(f"config.fields[{i}].from must be a string")
        if "type" in field_cfg and field_cfg["type"] not in _CONFIG_TYPE_MAP:
            errors.append(f"config.fields[{i}].type must be one of {sorted(_CONFIG_TYPE_MAP)!r}")
        if "required" in field_cfg and not isinstance(field_cfg["required"], bool):
            errors.append(f"config.fields[{i}].required must be a boolean")
        if "normalize" in field_cfg and field_cfg["normalize"] not in _ALLOWED_NORMALIZE:
            errors.append(f"config.fields[{i}].normalize must be one of {sorted(_ALLOWED_NORMALIZE)!r}")

    if errors:
        raise ValidationError(errors)
    return True
