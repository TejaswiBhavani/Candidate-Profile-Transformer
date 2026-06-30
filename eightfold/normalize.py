"""
Field-level normalizers.

Each function takes a raw value and returns a normalized value, or None
if the value can't be confidently normalized (never invent/guess — an
unparseable phone number becomes None, not a best-effort fabrication).

Phone normalization note: we don't have network access to install the
`phonenumbers` library in this environment, so this is a deliberately
scoped-down E.164 normalizer: it assumes a single configurable default
region (India, matching the sample data) for bare national numbers, and
passes through anything that already looks like it has a country code.
This is called out explicitly as a descoped corner in the design doc —
a production version would use `phonenumbers` for proper multi-region
parsing.
"""

import re
from dateutil import parser as dateutil_parser

from .skills_map import canonicalize_skill

DEFAULT_COUNTRY_CODE = "91"  # India, matches sample inputs. Configurable via normalize_phone(default_cc=...)

_DIGITS_RE = re.compile(r"\d+")


def normalize_text(raw):
    if raw is None:
        return None
    cleaned = " ".join(str(raw).strip().split())
    return cleaned or None


def normalize_name(raw):
    return normalize_text(raw)


def normalize_email(raw):
    if raw is None:
        return None
    cleaned = str(raw).strip().lower()
    if not cleaned or "@" not in cleaned:
        return None
    return cleaned


def normalize_phone(raw, default_cc=DEFAULT_COUNTRY_CODE):
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    has_plus = s.startswith("+")
    digits = "".join(_DIGITS_RE.findall(s))
    if not digits:
        return None

    if has_plus:
        # already has an explicit country code
        if 8 <= len(digits) <= 15:
            return "+" + digits
        return None

    if len(digits) == 10:
        # bare national number (no trunk prefix) -> assume default region
        return f"+{default_cc}{digits}"

    if len(digits) == 11 and digits.startswith("0"):
        # national number with trunk prefix '0' -> strip it, assume default region
        return f"+{default_cc}{digits[1:]}"

    if len(digits) in (11, 12) and digits.startswith(default_cc):
        # looks like it already includes the default country code, just missing '+'
        return "+" + digits

    return None


_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}


def normalize_date(raw):
    """Normalizes month-granularity dates to 'YYYY-MM'. Returns the literal
    string 'present' for ongoing/ current roles, and None if unparseable."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s.lower() in ("present", "current", "ongoing", "now"):
        return "present"
    try:
        dt = dateutil_parser.parse(s, default=_DATE_DEFAULT())
        return dt.strftime("%Y-%m")
    except (ValueError, OverflowError, TypeError):
        return None


def _DATE_DEFAULT():
    import datetime
    # day=1 sentinel avoids dateutil silently substituting "today's day number"
    # when the input only specifies month + year (our expected granularity).
    return datetime.datetime(2000, 1, 1)


def normalize_skill(raw):
    canonical, _known = canonicalize_skill(raw)
    return canonical


def normalize_dict(raw):
    if not isinstance(raw, dict):
        return raw
    return raw

# Maps canonical field name -> normalizer function. Used by the normalize
# pipeline stage to dispatch each Evidence record to the right normalizer.
FIELD_NORMALIZERS = {
    "full_name": normalize_name,
    "emails": normalize_email,
    "phones": normalize_phone,
    "current_company": normalize_text,
    "current_title": normalize_text,
    "department": normalize_text,
    "manager_name": normalize_text,
    "employment_status": normalize_text,
    "skills": normalize_skill,
    "experience_start_date": normalize_date,
    "experience_end_date": normalize_date,
    "extra_attributes": normalize_dict,
}


def normalize_evidence(evidence):
    """Takes an Evidence with value == raw_value (as produced by extractors)
    and returns a new Evidence with `.value` normalized. `.raw_value` is
    left untouched so it's always available for provenance/debugging."""
    normalizer = FIELD_NORMALIZERS.get(evidence.field_name, normalize_text)
    new_value = normalizer(evidence.raw_value)
    return evidence.with_value(new_value)
