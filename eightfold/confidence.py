"""
Confidence scoring.

Everything here is a pure function of (how many sources, what type of
sources, did they agree) so the same inputs always produce the same
confidence — required by the brief ('deterministic & explainable').

The formula, in words:
  - Start from the strongest source type involved (structured sources are
    trusted slightly more than free-text extraction, since there's no
    parsing ambiguity).
  - Add a bonus for each additional source that corroborates the same
    value, capped so confidence never claims false certainty.
  - A field resolved despite some sources disagreeing (majority/plurality
    pick, or the name-containment refinement) gets a 0.85x haircut.
  - A field that genuinely couldn't be adjudicated (no majority, true
    conflict) is null with confidence 0.0 — we'd rather say "unknown"
    than guess.
"""

SOURCE_BASE_WEIGHT = {
    "structured": 0.65,
    "semistructured": 0.60,
    "unstructured": 0.50,
}
AGREEMENT_BONUS_PER_EXTRA_SOURCE = 0.15
MAX_CONFIDENCE = 0.98
PARTIAL_AGREEMENT_FACTOR = 0.85
UNKNOWN_SKILL_FACTOR = 0.9  # slight haircut when a skill isn't in our canonical synonym table


def _base(source_types):
    return max(SOURCE_BASE_WEIGHT.get(t, 0.5) for t in source_types)


def agreement_confidence(source_types):
    """All contributing sources agree on the same (normalized) value."""
    base = _base(source_types)
    bonus = AGREEMENT_BONUS_PER_EXTRA_SOURCE * (len(source_types) - 1)
    return round(min(MAX_CONFIDENCE, base + bonus), 2)


def single_source_confidence(source_types):
    return round(_base(source_types), 2)


def partial_agreement_confidence(source_types):
    """A winner was picked (majority/plurality, or name-containment
    refinement) despite some disagreement among sources."""
    return round(agreement_confidence(source_types) * PARTIAL_AGREEMENT_FACTOR, 2)


def no_confidence():
    return 0.0
