from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from eightfold.pipeline import run


ROOT = Path(__file__).resolve().parent
CONFIGS_DIR = ROOT / "configs"


def _parse_cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ALLOW_ORIGINS", "").strip()
    if not raw:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _cors_origin_regex() -> str | None:
    raw = os.environ.get("CORS_ALLOW_ORIGIN_REGEX", "").strip()
    if raw:
        return raw
    return r"https://.*\.vercel\.app"


app = FastAPI(title="Eightfold Pipeline API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_origin_regex=_cors_origin_regex(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/configs")
def list_configs() -> dict:
    presets = ["default"]
    if CONFIGS_DIR.exists():
        for p in sorted(CONFIGS_DIR.glob("*.json")):
            presets.append(p.stem)
    return {"presets": presets}


@app.get("/workflow")
def get_workflow() -> dict:
    """Returns the pipeline stage descriptions for the workflow modal."""
    return {
        "stages": [
            {
                "id": "upload",
                "label": "File Upload",
                "icon": "📄",
                "description": "Resume PDFs, recruiter CSVs, ATS JSON exports, and recruiter notes are accepted.",
            },
            {
                "id": "detection",
                "label": "Source Detection",
                "icon": "🔍",
                "description": "Each file is classified as structured, semi-structured, or unstructured based on its format.",
            },
            {
                "id": "extraction",
                "label": "Data Extraction",
                "icon": "⚙️",
                "description": "Deterministic extractors pull fields using regex, heuristics, and schema mapping — no LLMs.",
            },
            {
                "id": "url_discovery",
                "label": "URL Discovery",
                "icon": "🔗",
                "description": "LinkedIn, GitHub, and portfolio URLs are automatically detected from uploaded documents.",
            },
            {
                "id": "enrichment",
                "label": "APIFY Enrichment",
                "icon": "🌐",
                "description": "Discovered profile URLs are scraped via APIFY actors to pull additional skills, experience, and education.",
            },
            {
                "id": "merge",
                "label": "Canonical Merge",
                "icon": "🔀",
                "description": "All evidence from every source is merged using majority voting and conflict resolution.",
            },
            {
                "id": "confidence",
                "label": "Confidence Scoring",
                "icon": "📊",
                "description": "Each field receives a confidence score (0-1) based on source corroboration and authority.",
            },
            {
                "id": "gemini",
                "label": "Gemini Insights",
                "icon": "🤖",
                "description": "The finalized profile is analyzed by Gemini AI to generate recruiter summaries and recommendations.",
            },
            {
                "id": "projection",
                "label": "Final Profile",
                "icon": "✅",
                "description": "The canonical profile is projected into the requested output schema with provenance tracking.",
            },
        ]
    }


def _load_config(config_name: str | None, config_json: str | None):
    if config_json:
        try:
            return json.loads(config_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid config_json: {exc}") from exc

    if not config_name or config_name == "default":
        return None

    config_path = CONFIGS_DIR / f"{config_name}.json"
    if not config_path.exists():
        raise HTTPException(status_code=400, detail=f"Unknown config preset: {config_name}")

    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid config file {config_path.name}") from exc


@app.post("/run")
async def run_pipeline(
    files: list[UploadFile] = File(...),
    config_name: str | None = Form(default="default"),
    config_json: str | None = Form(default=None),
):
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    config = _load_config(config_name, config_json)

    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_paths: list[str] = []
        for idx, upload in enumerate(files):
            original_name = upload.filename or f"source_{idx}.dat"
            safe_name = Path(original_name).name
            suffix = Path(safe_name).suffix
            if suffix.lower() not in {".csv", ".json", ".pdf", ".txt"}:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {upload.filename}. Allowed: .csv, .json, .pdf, .txt",
                )

            data = await upload.read()
            path = os.path.join(tmp_dir, safe_name)
            with open(path, "wb") as f:
                f.write(data)
            temp_paths.append(path)

        result = run(temp_paths, config=config)

        return {
            "ok": result.ok,
            "warnings": result.warnings,
            "validation_errors": result.validation_errors,
            "canonical": jsonable_encoder(result.canonical),
            "output": jsonable_encoder(result.output),
            "discovered_urls": result.discovered_urls,
            "enrichment_status": result.enrichment_status,
            "gemini_insights": result.gemini_insights,
        }

if __name__ == "__main__":
    import uvicorn
    # Allow the user to run the file directly via their IDE's Run/Debug button
    uvicorn.run(app, host="127.0.0.1", port=8000)
