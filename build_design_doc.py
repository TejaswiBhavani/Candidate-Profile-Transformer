from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib import colors

styles = getSampleStyleSheet()

title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=16, leading=18, spaceAfter=2)
subtitle_style = ParagraphStyle("subtitle", parent=styles["Normal"], fontSize=9, leading=10.6,
                                 textColor=colors.HexColor("#555555"), spaceAfter=6)
h_style = ParagraphStyle("h", parent=styles["Heading2"], fontSize=10.8, leading=12.4, spaceBefore=7,
                          spaceAfter=3, textColor=colors.HexColor("#1a1a2e"))
body_style = ParagraphStyle("body", parent=styles["Normal"], fontSize=8.6, leading=10.8, spaceAfter=2.5)
bullet_style = ParagraphStyle("bullet", parent=body_style, leftIndent=12, bulletIndent=0, spaceAfter=2.5)
mono_style = ParagraphStyle("mono", parent=styles["Normal"], fontName="Courier", fontSize=7.9, leading=9.6,
                             backColor=colors.HexColor("#f4f4f7"), borderPadding=4)

def B(text):
    return Paragraph(text, body_style)

def Bu(text):
    return Paragraph(f"&bull;&nbsp; {text}", bullet_style)

doc = SimpleDocTemplate(
    "__Eightfold.pdf", pagesize=letter,
    topMargin=0.4 * inch, bottomMargin=0.35 * inch,
    leftMargin=0.55 * inch, rightMargin=0.55 * inch,
)

story = []
story.append(Paragraph("Eightfold — Candidate Profile Aggregation Engine", title_style))
story.append(Paragraph(
    "Technical design, Step 1 &mdash; pipeline plan, canonical schema, merge/confidence policy, "
    "runtime config handling, and edge cases. No code; see the repo for the implementation.",
    subtitle_style))
story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#cccccc"), spaceAfter=4))

# ---- Pipeline ----
story.append(Paragraph("1. Pipeline", h_style))
story.append(B(
    "<b>Extract</b> (per source, type-specific reader: CSV column map, JSON key map, PDF regex/heuristics) "
    "&rarr; <b>Normalize</b> (phone/date/skill/text, per-field functions, unparseable &rarr; null, never invented) "
    "&rarr; <b>Group evidence by field</b> &rarr; <b>Merge &amp; resolve conflicts</b> (per field, single- vs. "
    "multi-valued policy) &rarr; <b>Score confidence</b> (deterministic formula, no model calls) &rarr; "
    "<b>Assemble canonical profile</b> &rarr; <b>Project</b> (runtime config reshapes output) &rarr; "
    "<b>Validate</b> (schema-check before returning). Every source is wrapped so one bad/missing source degrades "
    "to a warning, not a crash."
))

# ---- Canonical schema ----
story.append(Paragraph("2. Canonical schema &amp; normalized formats", h_style))
story.append(B(
    "Each candidate is one record: <font face='Courier' size=7.9>candidate_id, full_name, emails[], phones[], "
    "current_company, current_title, skills[], overall_confidence, _meta</font>. Internally, every scalar field "
    "is <font face='Courier' size=7.9>{value, confidence, sources, conflict, conflicting_values}</font> &mdash; "
    "not a bare value &mdash; so provenance survives until projection time decides whether to expose it. "
    "Multi-valued fields (<font face='Courier' size=7.9>emails, phones, skills</font>) are lists of the same "
    "shape, one entry per distinct value. <font face='Courier' size=7.9>_meta</font> records which sources were "
    "used, which failed (with why), and which raw values were dropped for failing normalization."
))
story.append(Bu("<b>Phone</b> &rarr; E.164 (<font face='Courier' size=7.9>+&lt;cc&gt;&lt;digits&gt;</font>); "
                "bare 10-digit numbers assume one configurable default region (India, matching sample data); "
                "already-prefixed numbers pass through. Unparseable &rarr; null."))
story.append(Bu("<b>Dates</b> &rarr; <font face='Courier' size=7.9>YYYY-MM</font> (month granularity matches the "
                "resume's own granularity); &ldquo;Present/Current&rdquo; &rarr; sentinel "
                "<font face='Courier' size=7.9>\"present\"</font>, not a date."))
story.append(Bu("<b>Skills</b> &rarr; canonical display name via an explicit synonym table "
                "(<font face='Courier' size=7.9>reactjs/react.js/react &rarr; React</font>); unrecognized terms "
                "are cleaned up (trim/case) and kept, not dropped &mdash; we don't get a canonicalization "
                "confidence bonus for them, but we never discard a stated skill."))
story.append(Bu("<b>Email</b> &rarr; lowercase + trim. <b>Text fields</b> (name, company, title) &rarr; "
                "whitespace-collapsed, casing preserved from source."))

# ---- Merge & confidence ----
story.append(Paragraph("3. Merge / conflict-resolution policy &amp; confidence", h_style))
story.append(B(
    "<b>Single-valued fields</b> (name, company, title): group evidence by a normalized comparison key. "
    "All sources agree &rarr; high confidence, no conflict. Disagreement: for <font face='Courier' size=7.9>"
    "full_name</font> specifically, if one value is a token-subset of another (&ldquo;Tejaswi Bhavani&rdquo; "
    "&sub; &ldquo;Tejaswi Bhavani Hari&rdquo;) we treat it as a refinement and keep the fuller one. Otherwise, a "
    "strict majority/plurality wins (flagged as a soft conflict, minority kept for audit); a true tie (every "
    "source disagrees, no majority) resolves to <b>null, confidence 0.0</b> &mdash; we never guess a winner out "
    "of a genuine contradiction."
))
story.append(B(
    "<b>Multi-valued fields</b> (emails, phones, skills): union of distinct normalized values, each scored "
    "independently by how many sources corroborate it &mdash; not a single winner-take-all pick. Ordering "
    "(for paths like <font face='Courier' size=7.9>emails[0]</font>) is confidence desc, then source-priority "
    "order (CLI argument order), then alphabetical, so it's fully deterministic."
))
story.append(B(
    "<b>Confidence formula:</b> source-type base weight (structured &gt; semi-structured &gt; unstructured) "
    "+ a bonus per corroborating source, capped at 0.98; a 0.85&times; haircut when a value was picked despite "
    "disagreement; 0.0 for an unresolved conflict or no evidence. Same inputs &rarr; same number, always."
))

# ---- Config handling ----
story.append(Paragraph("4. Runtime custom-output config", h_style))
story.append(B(
    "The projection layer (<font face='Courier' size=7.9>project.py</font>) never touches merge/confidence logic "
    "&mdash; it only reads three parallel flattened views of the canonical profile (values / confidences / "
    "sources), addressable by the same path syntax the config uses (<font face='Courier' size=7.9>full_name, "
    "emails[0], skills[].name</font>). Per requested field: resolve <font face='Courier' size=7.9>from</font> "
    "(or <font face='Courier' size=7.9>path</font> if no remap), apply a <font face='Courier' size=7.9>"
    "normalize</font> hint if given (mostly confirmations since canonical values are pre-normalized; "
    "<font face='Courier' size=7.9>national</font> is the one real re-format), then apply "
    "<font face='Courier' size=7.9>on_missing</font> (null/omit/error) if nothing resolved. "
    "<font face='Courier' size=7.9>include_confidence</font> adds a <font face='Courier' size=7.9>"
    "&lt;field&gt;_confidence/_sources</font> sibling per field, globally. Output is then validated against "
    "either the fixed default schema or a schema built dynamically from the config's own "
    "<font face='Courier' size=7.9>type</font>/<font face='Courier' size=7.9>required</font> declarations &mdash; "
    "so a new config never needs an engine code change, only a new config file."
))

# ---- Edge cases ----
story.append(Paragraph("5. Edge cases &amp; deliberate scope cuts", h_style))
story.append(Bu("<b>Hard conflict, no majority</b> (e.g. three sources, three different companies) &rarr; null + "
                "confidence 0, all raw values kept in <font face='Courier' size=7.9>conflicting_values</font> "
                "for audit. Never invented."))
story.append(Bu("<b>Corrupt / missing / malformed source</b> (unreadable PDF, missing file, header-less CSV) "
                "&rarr; caught per-source, run continues on whatever's left, source listed in "
                "<font face='Courier' size=7.9>_meta.sources_failed</font> and surfaced as a CLI warning."))
story.append(Bu("<b>Same skill, different spelling</b> across sources (React/ReactJS) &rarr; canonicalized into "
                "one entry; this also means corroboration counts correctly even when sources never used the "
                "exact same string."))
story.append(Bu("<b>Config asks for a field that doesn't exist anywhere</b> in the canonical data &rarr; handled "
                "purely by <font face='Courier' size=7.9>on_missing</font>, never fabricated."))
story.append(Bu("<b>Multiple distinct emails/phones</b> across sources, only some overlapping &rarr; unioned with "
                "per-value confidence, not forced into one arbitrary &ldquo;truth.&rdquo;"))
story.append(B(
    "<b>Left out under time pressure:</b> full multi-job work-history/timeline reconciliation (only current "
    "role tracked); cross-candidate dedup/entity-resolution across a batch (one input set = one candidate per "
    "run); a polished UI (CLI only, per the brief's stated priority); the <font face='Courier' size=7.9>"
    "phonenumbers</font>/<font face='Courier' size=7.9>jsonschema</font> libraries (hand-rolled, swap-in "
    "compatible equivalents used instead, due to a network-restricted build environment)."
))

doc.build(story)
print("built")
