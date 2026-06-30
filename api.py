from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware

from eightfold.pipeline import run


ROOT = Path(__file__).resolve().parent
CONFIGS_DIR = ROOT / "configs"


app = FastAPI(title="Eightfold Pipeline API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
        }

if __name__ == "__main__":
    import uvicorn
    # Allow the user to run the file directly via their IDE's Run/Debug button
    uvicorn.run(app, host="127.0.0.1", port=8000)
