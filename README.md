# Eightfold — Candidate Profile Aggregation Pipeline

A robust, multi-source candidate data transformer built for the **Eightfold Engineering Intern** assignment. 

This pipeline ingests candidate data from unstructured sources (Resume PDFs, GitHub API, LinkedIn API, Recruiter Notes) and structured sources (ATS JSON, Recruiter CSV). It merges these overlapping and often contradictory inputs into a single **Canonical Profile**, maintaining strict mathematical confidence scoring and full provenance tracking. Finally, it projects that canonical record into any requested JSON schema at runtime.

---

## 🚀 Key Features

- **Algorithmic Conflict Resolution:** Mathematically resolves data contradictions across sources. True ties result in `null` rather than hallucinations, preserving data integrity.
- **Configurable Projection (The Twist):** Reshape the internal canonical profile at runtime using a JSON config (select fields, apply normalizations like E.164, toggle provenance, define `on_missing` policies).
- **AI Recruiter Insights:** Integrates with Google Gemini (cascading across Gemini 3.5, 2.5, 1.5, and Gemma 4) to intelligently analyze the parsed profile and identify missing data or potential concerns.
- **Live Web Scraping:** Integrates with Apify to dynamically extract structured data from live LinkedIn and GitHub URLs discovered in the candidate's resume.
- **Graceful Degradation:** Malformed PDFs, broken JSONs, or rate-limited APIs will not crash the pipeline. The system tracks failed sources and continues processing.

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

See `__Eightfold.md` for the comprehensive technical design document.
