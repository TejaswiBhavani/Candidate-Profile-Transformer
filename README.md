# Candidate Profile Transformer

A multi-source candidate aggregation pipeline that transforms fragmented recruiting data into a single trusted candidate profile.

Recruiters often receive information about the same candidate from multiple places: resumes, ATS exports, recruiter notes, LinkedIn profiles, GitHub profiles, and internal systems. These sources frequently contain conflicting, incomplete, or differently formatted information.

This system ingests structured and unstructured candidate data, normalizes and reconciles conflicting values, generates a canonical candidate profile with confidence scoring and provenance tracking, and projects that profile into configurable output schemas without changing pipeline logic.

The design prioritizes:

* Deterministic and explainable processing
* Source traceability and auditability
* Robust handling of incomplete or malformed inputs
* Configurable downstream data contracts
* Recruiter-focused candidate insights

---

## Key Features

### Multi-Source Candidate Fusion

Supports both structured and unstructured candidate data:

**Structured Sources**
* Recruiter CSV exports
* ATS JSON records

**Unstructured Sources**
* Resume PDFs
* Recruiter notes
* LinkedIn profiles (via Apify enrichment)
* GitHub profiles (via Apify enrichment)

### Canonical Profile Generation

Transforms multiple overlapping sources into a single canonical profile while preserving:
* Confidence scores
* Source provenance
* Conflict history
* Normalized formats

The system never invents values. When evidence is insufficient or conflicting, fields resolve to `null` instead of making assumptions.

### Configurable Output Projection

A runtime configuration layer can:
* Select fields
* Rename fields
* Apply normalization rules
* Toggle confidence metadata
* Toggle provenance metadata
* Control missing-value behavior

The canonical profile remains unchanged while output contracts can vary for different consumers.

### Recruiter AI Insights

Google Gemini is used only after deterministic profile generation. It does not participate in extraction, normalization, conflict resolution, confidence scoring, or canonical profile creation.

Gemini generates:
* Candidate summary
* Key strengths
* Recommended roles
* Missing information
* Potential concerns

### Profile Enrichment

LinkedIn and GitHub URLs discovered inside uploaded resumes are automatically enriched using Apify. No manual URL entry is required.

---

## 🛠️ Quick Start

### 1. Interactive Dashboard (Full Stack)
The easiest way to experience the pipeline is through the modern React web dashboard.

```bash
# Install dependencies for both the backend and frontend
pip install -r requirements.txt
npm --prefix frontend install

# Start the full stack (FastAPI backend + React frontend) concurrently
npm run dev
```
Open **`http://localhost:5173`** in your browser to view the interactive candidate profile transformer.

### 2. Command Line Interface (CLI)
If you prefer a pure terminal experience, the CLI natively handles the projection and canonical merging.

```bash
# Run the pipeline with the default output schema across three sample sources
python cli.py --sources sample_inputs/recruiter.csv sample_inputs/resume.pdf sample_inputs/linkedin.json

# Run with a custom runtime config (reshapes JSON, normalizes data, toggles metadata)
python cli.py --sources sample_inputs/recruiter.csv sample_inputs/resume.pdf \
    --config configs/public_profile.json

# Save the output to a file and dump the internal canonical profile to stderr
python cli.py --sources sample_inputs/recruiter.csv sample_inputs/resume.pdf \
    --out outputs/default_output.json --show-canonical
```

*(Note: API integrations require `APIFY_API_TOKEN` and `GEMINI_API_KEY` to be set in a `.env` file at the root. If absent, the pipeline will gracefully skip these enrichments).*

---

## 🏗️ Architecture

```text
Sources (PDF/JSON/CSV/APIs) 
    │
    ├── extract()    ──> Raw Evidence
    │
    ├── normalize()  ──> Normalized Evidence (E.164 phones, canonical skills, YYYY-MM dates)
    │
    ├── merge()      ──> Canonical Profile (Resolves conflicts, assigns confidence, tracks provenance)
    │
    ├── project()    ──> Projected Output (Reshaped based on config.json)
    │
    └── validate()   ──> Validated final JSON Output
```

### The Canonical Merge Policy
The system categorizes fields into two types to resolve conflicts mathematically:
- **Single-Valued Fields** (e.g., `full_name`, `current_company`): Groups evidence by normalized keys. If sources disagree, the engine checks for a *containment chain* (e.g., "Tejaswi" vs "Tejaswi Bhavani") and picks the refinement. If independent sources have a true tie (e.g., two distinct names), the system refuses to guess—the field resolves to `null` and confidence drops to `0`. 
- **Multi-Valued Fields** (e.g., `emails`, `skills`): Unions all distinct normalized values into an array. Each element's confidence is independently scored based on corroboration count across sources.

### Confidence Formula
Confidence is derived mathematically: a source-type base weight (structured > semi-structured > unstructured) plus a bonus per corroborating source, capped at 0.98. A 0.85x penalty is applied when a value wins despite disagreement. 0.0 is assigned for genuine unresolved conflicts.

---

## 🧪 Testing

The pipeline is thoroughly tested against extreme edge cases (severe candidate contradictions across multiple documents, corrupt PDFs, malformed CSVs).

```bash
# Run the test suite
python -m unittest discover -s tests -v
```
