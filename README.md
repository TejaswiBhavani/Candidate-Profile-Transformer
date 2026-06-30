# Eightfold — Candidate Profile Aggregation Pipeline

Merges candidate data from multiple sources (structured + unstructured)
into one canonical profile, with provenance and confidence on every
field, and projects that profile into whatever output shape a runtime
config asks for — without touching the engine.

See `docs/Eightfold.pdf` for the one-page design write-up this
implements (the Step 1 deliverable, submitted separately).

## Quick start

### Command Line Interface (CLI)

```bash
pip install -r requirements.txt   # pdfplumber, pypdf, reportlab, python-dateutil
                                   # (reportlab/pypdf are only needed to regenerate the sample PDF)

# Default output schema, all three sample sources
python cli.py --sources sample_inputs/recruiter.csv sample_inputs/resume.pdf sample_inputs/linkedin.json

# A custom runtime config (selects/renames fields, toggles confidence/provenance independently, normalize hints, on_missing policy)
python cli.py --sources sample_inputs/recruiter.csv sample_inputs/resume.pdf sample_inputs/linkedin.json \
    --config configs/public_profile.json

# Write to a file instead of stdout, and also dump the internal canonical profile (with full provenance) to stderr
python cli.py --sources sample_inputs/recruiter.csv sample_inputs/resume.pdf sample_inputs/linkedin.json \
    --out outputs/default_output.json --show-canonical
```

### Dashboard UI

You can also run the interactive web dashboard to visualize the pipeline in action.

```bash
# Terminal 1: Start the backend API
uvicorn api:app --reload

# Terminal 2: Start the frontend development server
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser to view the interactive candidate profile transformer.

No CLI flag is needed to pick structured vs. unstructured — the file
extension routes to the right extractor (`.csv`, `.json`, `.pdf`).
Pass sources in priority order; that order is the tiebreaker whenever
the merge logic genuinely can't otherwise distinguish two equally-
supported values.

Pre-generated outputs from the commands above are already checked in
under `outputs/`.

## Tests

```bash
python -m unittest discover -s tests -v
```

38 tests, stdlib `unittest` only (no `pytest` required, though it'll
also pick these up fine if you have it). Covers normalization, merge/
conflict resolution, confidence scoring, end-to-end runs on the sample
inputs, and edge cases (missing file, corrupt PDF, malformed CSV,
on_missing policies, single-source fields).

## Architecture

```
sources (csv/json/pdf) --extract--> raw Evidence
                        --normalize--> normalized Evidence (phone/date/skill/text)
                        --group by field, merge--> canonical profile
                                                     (value + confidence + sources + conflict info, per field)
                        --project(config)--> output shape the config asks for
                        --validate--> schema-checked JSON
```

| Stage | Module |
|---|---|
| Extract | `eightfold/sources/{csv,json,pdf}_source.py` |
| Normalize | `eightfold/normalize.py`, `eightfold/skills_map.py` |
| Merge + confidence | `eightfold/merge.py`, `eightfold/confidence.py` |
| Canonical profile assembly | `eightfold/canonical.py` |
| Runtime-config projection | `eightfold/project.py` |
| Validation | `eightfold/validate.py` |
| Orchestration / CLI | `eightfold/pipeline.py`, `cli.py` |

The canonical profile (`canonical.py`'s output) and the projection
layer (`project.py`) are deliberately separate modules that don't import
each other's internals — `project.py` only reads three flattened views
(values/confidences/sources) of the canonical profile by path. That's
what lets a runtime config reshape output with zero engine changes.

### Merge / conflict-resolution policy

- **Single-valued fields** (`full_name`, `current_company`,
  `current_title`): group evidence by a normalized comparison key.
  - All sources agree → high confidence, no conflict.
  - For `full_name` specifically, if the disagreeing values form a
    containment chain (e.g. "Tejaswi Bhavani" is a subset of "Tejaswi
    Bhavani Hari") → treat it as a refinement, not a contradiction, and
    pick the more complete one.
  - Otherwise, if one value has strict majority/plurality support →
    pick it, flag the field as a soft conflict, keep the minority
    value(s) for audit. (Rationale: when independent sources corroborate
    a value, discarding it would lose useful signal. Confidence penalties
    and conflict tracking keep the uncertainty visible.)
  - If it's a true tie (every source disagrees, no majority) → **null**,
    confidence 0.0. We never invent a winner out of a genuine tie.
- **Multi-valued fields** (`emails`, `phones`, `skills`): union of
  distinct normalized values, each scored independently by how many
  sources corroborate it. Ordering (for `emails[0]`-style config paths)
  is confidence desc, then source-priority order, then alphabetical —
  fully deterministic.

### Confidence formula

`confidence.py` — a source-type base weight (structured > semi-
structured > unstructured) plus a bonus per corroborating source,
capped at 0.98; a 0.85x haircut when a value was picked despite some
disagreement; 0.0 for a genuine unresolved conflict. Same inputs always
produce the same number — no randomness, no LLM calls in the scoring
path.

### Runtime config → output

`project.py` resolves each `fields[].path`/`from` against the canonical
profile using a small path syntax: `full_name`, `emails[0]`,
`skills[].name`. Two independent toggles control metadata exposure:

- `include_confidence`: adds a `<field>_confidence` sibling for every
  projected field, showing the corroboration-weighted confidence (0.0–0.98).
- `include_provenance`: adds `<field>_sources` (list of source IDs) and
  `<field>_methods` (extraction method per source, e.g. `csv_column:name`) for
  every projected field, enabling full auditability of how each value was sourced.

Both toggles default to false. Set either or both to true in the config to expose
that metadata. `on_missing` (`null`/`omit`/`error`) controls what happens when a
requested path resolves to nothing — including paths that don't exist
in the canonical schema at all (see `linkedin_url` in
`configs/public_profile.json`, which is genuinely absent from every
sample source and gets `omit`ted).

## Sample inputs

`sample_inputs/recruiter.csv` (structured), `sample_inputs/resume.pdf`
(unstructured, real PDF — generated with reportlab from plain text so
the PDF extraction path is genuinely exercised, not faked), and
`sample_inputs/linkedin.json` (semi-structured) describe the same
candidate with deliberately overlapping-but-not-identical data, so the
sample run exercises every merge case in one go:

- name: 2/3 sources agree on the full name, 1 gives a shorter version → containment refinement
- email: 2 sources agree on one address, 1 source has a different address → union, ranked
- phone: same number in three different formats → normalization makes it a clean 3/3 agreement
- company: full 3/3 agreement
- title: 2/3 agree, 1 gives a more specific variant → majority resolution
- skills: "React" / "ReactJS" from different sources → canonicalized into one entry

`sample_inputs/corrupt_resume.pdf` and `sample_inputs/malformed.csv`
are intentionally broken, used by the edge-case tests to prove a bad
source degrades gracefully instead of crashing the run.

## Assumptions

- One input set = one candidate per run (no cross-candidate dedup/entity
  resolution within a batch).
- Default phone region is India (`+91`) for bare national numbers,
  matching the sample data — configurable via
  `normalize_phone(default_cc=...)` but not currently CLI-exposed.
- Resume parsing assumes a loosely structured plain-text resume with
  `Skills:` / `Experience:` style section headers; it's a heuristic
  extractor, not a general-purpose resume parser.
- "Scale to thousands of candidates" is addressed by the pipeline being
  per-candidate and stateless (no shared mutable state across runs), so
  it parallelizes trivially across processes/workers; this repo doesn't
  include a batch/queue runner, just the single-candidate engine that
  one would be built on top of.

## Deliberately descoped (and why)

- **`phonenumbers` library** — no network access in the build
  environment to install it, so phone normalization is a hand-rolled,
  single-default-region E.164 normalizer (`normalize.py`). A real
  deployment should swap this for `phonenumbers`; the function signature
  (`raw -> E.164 string | None`) is designed so that's a one-function
  swap.
- **`jsonschema` library** — same network constraint;
  `eightfold/validate.py` is a small hand-rolled validator covering just
  the `type`/`required`/`items` subset this project needs. The schema
  dicts use the same shape as real JSON Schema, so swapping in the real
  library later is a drop-in change, not a rewrite.
- **Full work-history reconciliation** — only the *current* role
  (title/company, derived from the most recent experience entry) is
  merged; a full timeline of past roles with overlap/gap detection
  across sources is out of scope for this exercise.
- **Cross-candidate dedup at scale** (e.g. "is this resume the same
  person as that LinkedIn profile, across thousands of records") — this
  pipeline assumes the caller already knows which files belong to which
  candidate; it doesn't do identity resolution across a batch.
- **A polished UI** — per the brief, this is intentionally CLI-only (though a UI is provided for visualization).

## Future Enhancements (Production Architecture)

To move this pipeline from a heuristic-based parser to a fully production-grade ATS system, the following enhancements are recommended:

- **Context-Aware NLP (NER Models)**: Move beyond keyword dictionaries and regex to use Named Entity Recognition (e.g., fine-tuned spaCy/transformer models). This allows the system to differentiate between "I used AWS" (skill) and "I worked at AWS" (company) based on contextual depth.
- **Bias Mitigation & Anonymization**: Strip Personally Identifiable Information (PII) like names, graduation years, and locations during the initial parsing phase to promote fair, skills-based screening before the human review stage.
- **Human-in-the-Loop (HITL)**: Implement a routing mechanism for low-confidence canonical extractions. If the `overall_confidence` drops below a configurable threshold (e.g., 0.50), the profile should be routed to a manual review queue for human validation instead of auto-failing.
- **Visual OCR Processing**: For complex, multi-column resume layouts or scanned images, integrate an OCR layer (like AWS Textract or Tesseract) rather than relying solely on pure text-extraction paths.

## Demo video checklist

(For the ≈2 min recording: run the default-schema command, run the
custom-config command, then talk through one design decision — e.g. the
name-containment refinement vs. true-conflict logic in `merge.py` — and
one edge case, e.g. the corrupt-PDF test in
`tests/test_edge_cases.py::test_corrupt_pdf_is_skipped_not_fatal`.)
