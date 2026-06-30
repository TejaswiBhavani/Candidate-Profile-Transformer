# Multi-Source Candidate Data Transformer
**Eightfold Engineering Intern (Jul-Dec 2026) - Technical Design**

## 1. Pipeline Architecture
Our transformation engine is a deterministic, unidirectional pipeline that cleanly separates extraction from merging, and merging from output shaping.
1. **Extraction (Sources -> Evidence):** Parsers (Resume heuristics, ATS JSON mappings, Apify LinkedIn/GitHub REST clients) read raw data and emit atomic `Evidence` objects. Each object asserts one fact (e.g., `field="full_name", value="Tejaswi Bhavani", source="resume.pdf", method="heuristic"`).
2. **Standardization (Evidence -> Normalized Evidence):** Values are cast to expected types. Phones are stripped of punctuation. Dates are coerced to YYYY-MM.
3. **Canonical Merge (Normalized Evidence -> Canonical Profile):** The core engine groups evidence by field and resolves conflicts to build a single internal record containing values, confidences, and full provenance trails.
4. **AI Insights (Canonical Profile -> Gemini Enrichment):** The canonical JSON is sent to a Gemini 3.5 / Gemma 4 fallback model array to safely infer unstructured recruiter insights (missing data, warnings) without hallucinating facts.
5. **Projection (Canonical Profile + Config -> Projected Output):** A stateless projector shapes the internal record into the final requested schema based on a runtime JSON configuration.
6. **Validation:** The projected output is validated against expected structural constraints (e.g., `candidate_id` present, arrays typed correctly).

## 2. Canonical Schema & Normalization
The internal canonical schema is deeply nested to retain full auditability. Every field is an object containing `{"value", "confidence", "sources", "methods", "conflict", "conflicting_values"}`. 
**Normalized Formats:**
- **Phones:** Standardized to E.164 (e.g., `+918919546693`).
- **Dates (Experience):** Coerced strictly to `YYYY-MM`.
- **Skills:** Canonicalized via a synonym map (e.g., "JS", "NodeJS" -> "JavaScript").
- **Country:** ISO-3166 alpha-2 mapping.

## 3. Merge & Conflict Resolution Policy
We categorize fields into two types to resolve conflicts mathematically:
- **Single-Valued Fields (e.g., `full_name`, `current_company`):**
  - **Match Key:** Case-folded, whitespace-collapsed strings.
  - **Resolution:** If multiple sources agree, confidence increases. If sources disagree, we check for a *containment chain* (e.g., "Tejaswi" vs "Tejaswi Bhavani"). If one is a strict subset, the larger value wins (viewed as a refinement). If there is a true tie between disparate values (e.g., "Byungjin Park" vs "Tejaswi Bhavani"), the system refuses to guess—the field resolves to `null`, `conflict` is marked `true`, and confidence drops to `0`. 
- **Multi-Valued Fields (e.g., `emails`, `skills`):**
  - **Resolution:** Instead of picking a single winner, we union all distinct normalized values into an array. Each individual element's confidence is independently scored based on corroboration count across sources.

## 4. Configurable Output (Projection Layer)
The pipeline strictly separates the *Canonical Merge* from the *Projected Output*. The projection layer accepts a JSON config to dynamically reshape the output without altering the merge engine.
- **Field Selection & Mapping:** Uses path syntax (e.g., `"from": "skills[].name"`) to extract values, confidences, or sources from the canonical record.
- **Normalization Hints:** Supports runtime display formatting (e.g., `normalize: "national"` strips the E.164 country code for domestic display).
- **Missing Data Policies:** `on_missing` configures whether missing fields should emit `null`, be `omit`ted from the JSON, or raise a hard `error` (ProjectionError) to fail the build.

## 5. Edge Cases & Scope
1. **Garbage or Malformed Sources:** If a recruiter uploads a broken PDF or a severely malformed JSON, the parser gracefully yields an empty Evidence list rather than crashing. The canonical merge safely proceeds with remaining sources.
2. **Third-Party API Outages:** If Apify or Gemini endpoints timeout, rate-limit, or crash, the pipeline catches the exception, logs a warning, and continues generating the deterministic canonical profile. We implemented automatic fallback cascades across multiple Gemini/Gemma endpoints.
3. **Severe Candidate Collisions:** If two resumes for completely different people are uploaded simultaneously, the engine mathematically detects the contradiction across names and emails, drops the confidence score to near-zero, and flags a conflict for human review.
4. **Descoped - Semantic Skill Merging:** Under time pressure, complex semantic taxonomy matching (e.g., knowing "AWS" implies "Cloud") was descoped in favor of direct synonym mapping and Gemini qualitative insights.
