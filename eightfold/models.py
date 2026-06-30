"""
Core data model for the pipeline.

An Evidence record is the atomic unit the whole engine works with: one
field, one value, one source. Every later stage (normalize, merge,
confidence, project) consumes and/or produces Evidence records, which is
what keeps every value in the final output traceable back to where it
came from.
"""

from dataclasses import dataclass, field, replace
from typing import Any, List, Optional


@dataclass(frozen=True)
class Evidence:
    field_name: str        # canonical field this evidence is for, e.g. "full_name", "skills"
    value: Any              # value AFTER normalization (None if normalization couldn't parse it)
    raw_value: Any           # value exactly as extracted from the source, pre-normalization
    source_id: str            # human-readable source identifier, e.g. "recruiter.csv"
    source_type: str           # "structured" | "semistructured" | "unstructured"
    method: str                 # how it was pulled, e.g. "csv_column:phone", "regex:email"

    def with_value(self, new_value: Any) -> "Evidence":
        return replace(self, value=new_value)


@dataclass
class SourceResult:
    source_id: str
    source_type: str
    ok: bool
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)
