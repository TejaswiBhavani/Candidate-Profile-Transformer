"""
Merge & conflict resolution.

Two kinds of fields are handled differently:

SINGLE-VALUED fields (full_name, current_company, current_title) — there
can only be one true answer, so disagreement is a real conflict:
  1. Group evidence by a normalized comparison key (casefold + collapsed
     whitespace).
  2. One group -> unanimous agreement -> high confidence.
  3. Multiple groups, and the field allows the "containment" heuristic
     (currently just full_name) and the groups form a clean superset
     chain (e.g. "Tejaswi Bhavani" vs "Tejaswi Bhavani Hari") -> treat as
     a refinement, not a contradiction: pick the most complete value.
  4. Multiple groups, one strictly larger than the rest (a real majority
     of sources) -> pick it, but mark the field as a soft conflict and
     keep the minority value(s) in `conflicting_values` for audit.
  5. Multiple groups, no group strictly larger (e.g. every source
     disagrees, 1-1-1) -> can't adjudicate -> value is null, confidence
     0.0, hard conflict. We never invent a winner out of a true tie.

MULTI-VALUED fields (emails, phones, skills) — there isn't one "true"
answer to pick, so we union all distinct normalized values instead, and
score each value's own confidence by how many sources corroborate it.
Ordering (used by config paths like `emails[0]`) is by confidence desc,
then by source priority (order sources were passed on the CLI), then
alphabetically, so ordering is fully deterministic.
"""

from collections import defaultdict

from . import confidence as conf
from .skills_map import canonicalize_skill

CONTAINMENT_FIELDS = {"full_name"}


def _norm_key(value):
    return " ".join(str(value).strip().split()).casefold()


def _is_token_subset(short, long_):
    """True if every word in `short` appears, in order, as a subsequence
    of the words in `long_` — i.e. `short` looks like an abbreviated /
    less-complete version of `long_`, not a different value entirely."""
    s_tokens = _norm_key(short).split()
    l_tokens = _norm_key(long_).split()
    if not s_tokens or len(s_tokens) >= len(l_tokens):
        return False
    it = iter(l_tokens)
    return all(tok in it for tok in s_tokens)


def merge_single_valued(field_name, evidences, source_order):
    """evidences: list[Evidence] for ONE field, with non-null .value.
    source_order: list[str] of source_ids in CLI-argument order, used as
    a deterministic tiebreaker.
    Returns dict: value, confidence, sources, conflict(bool),
    conflicting_values(dict or None)."""
    usable = [e for e in evidences if e.value not in (None, "")]
    if not usable:
        return {"value": None, "confidence": conf.no_confidence(), "sources": [],
                "methods": [], "conflict": False, "conflicting_values": None}

    groups = defaultdict(list)
    for e in usable:
        groups[_norm_key(e.value)].append(e)

    source_types = [e.source_type for e in usable]
    all_sources = [e.source_id for e in usable]

    if len(groups) == 1:
        rep = max(usable, key=lambda e: len(str(e.value)))  # prefer fullest casing if they differ trivially
        return {"value": rep.value, "confidence": conf.agreement_confidence(source_types),
                "sources": all_sources, "methods": [e.method for e in usable],
                "conflict": False, "conflicting_values": None}

    # multiple distinct values -> real disagreement
    sorted_keys = sorted(groups.keys(), key=lambda k: len(groups[k]), reverse=True)
    top_key, second_key = sorted_keys[0], sorted_keys[1]

    if field_name in CONTAINMENT_FIELDS and len(groups) >= 2:
        # look for a containment chain: is there a value that is a
        # superset of every other distinct value present?
        candidates = list(groups.keys())
        superset_key = None
        for k in candidates:
            if all(k == other or _is_token_subset(other, k) for other in candidates):
                superset_key = k
                break
        if superset_key is not None:
            winners = groups[superset_key]
            rep = max(winners, key=lambda e: len(str(e.value)))
            conflicting = {k: [e.raw_value for e in v] for k, v in groups.items() if k != superset_key}
            return {"value": rep.value,
                    "confidence": conf.partial_agreement_confidence(source_types),
                    "sources": all_sources, "methods": [e.method for e in winners], "conflict": True,
                    "conflicting_values": conflicting}

    if len(groups[top_key]) > len(groups[second_key]):
        # clear majority/plurality
        winners = groups[top_key]
        rep = max(winners, key=lambda e: len(str(e.value)))
        winner_types = [e.source_type for e in winners]
        conflicting = {k: [e.raw_value for e in v] for k, v in groups.items() if k != top_key}
        return {"value": rep.value, "confidence": conf.partial_agreement_confidence(winner_types),
            "sources": [e.source_id for e in winners], "methods": [e.method for e in winners], "conflict": True,
                "conflicting_values": conflicting}

    # true tie -> cannot adjudicate -> never guess
    conflicting = {k: [e.raw_value for e in v] for k, v in groups.items()}
    return {"value": None, "confidence": conf.no_confidence(), "sources": all_sources,
            "methods": [e.method for e in usable], "conflict": True, "conflicting_values": conflicting}


def _source_rank(source_id, source_order):
    sid = str(source_id).lower()
    if sid.endswith(".pdf") or "resume" in sid:
        return 0
    if "linkedin_apify" in sid:
        return 1
    if "github_apify" in sid:
        return 2
    if sid.endswith(".json"):
        return 3
    if sid.endswith(".csv"):
        return 4
    if sid.endswith(".txt"):
        return 5
    # Fallback to source_order CLI priority
    try:
        return source_order.index(source_id) + 10
    except (ValueError, TypeError):
        return (len(source_order) if source_order else 0) + 10


def merge_emails_or_phones(field_name, evidences, source_order):
    """Union of distinct normalized values, each scored by corroboration."""
    usable = [e for e in evidences if e.value not in (None, "")]
    by_value = defaultdict(list)
    for e in usable:
        by_value[e.value].append(e)

    items = []
    for value, evs in by_value.items():
        types = [e.source_type for e in evs]
        c = conf.agreement_confidence(types) if len(evs) > 1 else conf.single_source_confidence(types)
        items.append({
            "value": value,
            "confidence": c,
            "sources": [e.source_id for e in evs],
            "methods": [e.method for e in evs],
        })

    items.sort(key=lambda it: (
        -it["confidence"],
        min(_source_rank(s, source_order) for s in it["sources"]),
        it["value"],
    ))
    return items


def merge_skills(evidences, source_order):
    """Canonicalizes each skill mention, unions by canonical name, scores
    by corroboration. A skill that wasn't recognized in the synonym table
    gets a small confidence haircut since we can't vouch for the spelling
    being canonical."""
    usable = [e for e in evidences if e.value not in (None, "")]
    by_canonical = defaultdict(list)
    known_flag = {}
    for e in usable:
        canonical, known = canonicalize_skill(e.raw_value)
        if not canonical:
            continue
        by_canonical[canonical].append(e)
        known_flag[canonical] = known_flag.get(canonical, False) or known

    items = []
    for name, evs in by_canonical.items():
        types = [ev.source_type for ev in evs]
        c = conf.agreement_confidence(types) if len(evs) > 1 else conf.single_source_confidence(types)
        if not known_flag[name]:
            c = round(c * conf.UNKNOWN_SKILL_FACTOR, 2)
        items.append({
            "name": name,
            "confidence": c,
            "sources": sorted({ev.source_id for ev in evs}, key=lambda s: _source_rank(s, source_order)),
            "methods": [ev.method for ev in evs],
        })

    items.sort(key=lambda it: (-it["confidence"], it["name"]))
    return items
