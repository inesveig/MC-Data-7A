"""
API FastAPI — endpoint /predict
Reçoit une image, applique le prétraitement, envoie à MedGemma,
applique les garde-fous et journalise le résultat.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
import time
import io
from pathlib import Path
from PIL import Image

from src.guardrails import validate_and_apply
from src.database import log_prediction
from src.preprocessing import preprocess_image, assess_image_quality

app = FastAPI(
    title="Assistant Radiologue Virtuel",
    description="Prototype pédagogique EFREI — NON destiné au diagnostic médical.",
    version="0.2.0",
)

PROMPT_BASELINE = Path("prompts/prompt_baseline.txt")
PROMPT_AMELIORE = Path("prompts/prompt_ameliore.txt")
MODEL_NAME = "medgemma-4b"
USE_TOY_MODE = True  # Passer à False une fois MedGemma accessible


@app.get("/")
def root():
    return {
        "status": "ok",
        "mode": "toy" if USE_TOY_MODE else "medgemma",
        "warning": "Prototype pédagogique uniquement. Non clinique.",
    }


@app.post("/predict")
async def predict(
    file: UploadFile = File(...),
    prompt: str = Query(default="baseline", enum=["baseline", "ameliore"]),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Fichier image requis.")

    start = time.time()

    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image invalide : {e}")

    # Prétraitement
    image = preprocess_image(image)
    quality_hint = assess_image_quality(image)

    # Sélection du prompt
    prompt_path = PROMPT_AMELIORE if prompt == "ameliore" else PROMPT_BASELINE

    if USE_TOY_MODE:
        from src.inference import run_inference_toy
        raw_output, latency_ms = run_inference_toy(file.filename)
        raw_output["image_quality"] = quality_hint
        prompt_version = f"toy_{prompt}"
        model_used = "toy_model"
    else:
        from src.inference import run_inference
        raw_output, latency_ms = run_inference(image, prompt_path)
        prompt_version = prompt_path.stem
        model_used = MODEL_NAME

    try:
        result = validate_and_apply(raw_output)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Sortie modèle invalide : {e}")

    log_prediction(
        image_name=file.filename,
        prompt_version=prompt_version,
        model_name=model_used,
        result=result,
        latency_ms=latency_ms,
    )

    return JSONResponse(content={
        "latency_ms": latency_ms,
        "prompt_used": prompt,
        "result": result,
    })
